"""Адаптер Pydantic AI поверх профилей django-openrouter.

Свой ``Model``, а не ``Provider``: провайдер отдал бы pydantic-ai только HTTP-клиент,
и его ``OpenRouterModel`` обошёл бы цепочку моделей, резерв бюджета, kill switch,
журнал и ``bound_username``. Здесь сообщения и инструменты собираются в chat payload,
а вызов идёт в ``AsyncOpenRouterClient`` — sync и async агент оба крутят async-методы
модели, ORM остаётся на ``sync_to_async(thread_sensitive=True)``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NamedTuple

import httpx

try:
    from pydantic_ai.exceptions import UserError
    from pydantic_ai.messages import (
        BinaryContent,
        CachePoint,
        FinishReason,
        ImageUrl,
        ModelMessage,
        ModelRequest,
        ModelResponse,
        ModelResponseStreamEvent,
        SystemPromptPart,
        TextContent,
        TextPart,
        ThinkingPart,
        ToolCallPart,
        ToolReturnPart,
        UserContent,
        UserPromptPart,
    )
    from pydantic_ai.models import (
        Model,
        ModelRequestParameters,
        StreamedResponse,
        check_allow_model_requests,
    )
    from pydantic_ai.models._tool_choice import resolve_tool_choice
    from pydantic_ai.profiles import ModelProfile, ModelProfileSpec, merge_profile
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import RequestUsage
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pydantic AI is not installed. "
        'Install it with: pip install "django-openrouter[pydantic-ai]"'
    ) from exc

# Имя output-tool по умолчанию в pydantic-ai, если схема его не задала.
_DEFAULT_OUTPUT_NAME = "final_result"
_PROVIDER_NAME = "openrouter"
_TEMPERATURE_MAX = 2.0
_FINISH_REASONS: dict[str, FinishReason] = {
    "stop": "stop",
    "length": "length",
    "tool_calls": "tool_call",
    "function_call": "tool_call",
    "content_filter": "content_filter",
    "error": "error",
}


class _PreparedCall(NamedTuple):
    overrides: dict[str, Any]
    base_url: str


class OpenRouterProfileModel(Model):
    """Модель Pydantic AI, которая ходит в OpenRouter через профиль использования.

    ``profile`` — слаг ``UsageProfile`` (``chat``), не профиль возможностей pydantic-ai.
    Тот передаётся как ``model_profile``. ``None`` берёт профиль по умолчанию из админки.
    ``model_name`` — этот слаг; фактическая модель ответа лежит в ``ModelResponse.model_name``.
    """

    _unsupported_file_inputs = frozenset({"audio", "video", "document"})
    # max_retries / extra_* меняют гарантии вызова, в OpenRouter не уходят.
    unsupported_settings = frozenset({"max_retries", "extra_headers", "extra_body"})

    def __init__(
        self,
        profile: str | None = None,
        *,
        settings: ModelSettings | None = None,
        model_profile: ModelProfileSpec | None = None,
    ) -> None:
        if profile is not None and not isinstance(profile, str):
            raise TypeError("profile must be a usage-profile slug or None")
        if isinstance(profile, str) and not profile.strip():
            raise ValueError("profile slug must not be empty")
        self.usage_profile = profile
        super().__init__(settings=settings, profile=model_profile)

    @property
    def model_name(self) -> str:
        if self.usage_profile is not None:
            return self.usage_profile
        return "default"

    @property
    def system(self) -> str:
        return _PROVIDER_NAME

    @property
    def provider(self) -> None:
        return None

    def _instance_profile_defaults(self, profile: ModelProfile) -> ModelProfile:
        # JSON schema / object и thinking можно выключить через model_profile=.
        return merge_profile(
            profile,
            ModelProfile(
                supports_json_schema_output=True,
                supports_json_object_output=True,
                supports_thinking=True,
            ),
        )

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        check_allow_model_requests()
        try:
            model_settings, model_request_parameters = self.prepare_request(
                model_settings, model_request_parameters
            )
            payload = _map_messages(messages, model_request_parameters)
            prepared = await _prepare_on_db_thread(
                self.usage_profile, model_settings, model_request_parameters
            )
            from django_openrouter.client import AsyncOpenRouterClient

            prepared.overrides.update(_grouping_overrides(messages))
            result = await AsyncOpenRouterClient(self.usage_profile).chat(
                payload, **prepared.overrides
            )
            return _to_model_response(result, prepared.base_url, self.model_name)
        finally:
            await _close_worker_connections()

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: Any = None,
    ) -> AsyncGenerator[StreamedResponse]:
        check_allow_model_requests()
        streamed: _OpenRouterStreamedResponse | None = None
        try:
            model_settings, model_request_parameters = self.prepare_request(
                model_settings, model_request_parameters
            )
            payload = _map_messages(messages, model_request_parameters)
            prepared = await _prepare_on_db_thread(
                self.usage_profile, model_settings, model_request_parameters
            )
            from django_openrouter.client import AsyncOpenRouterClient

            prepared.overrides.update(_grouping_overrides(messages))
            chunks = AsyncOpenRouterClient(self.usage_profile).stream(
                payload, **prepared.overrides
            )
            streamed = _OpenRouterStreamedResponse(
                model_request_parameters=model_request_parameters,
                _chunks=chunks,
                _profile_name=self.model_name,
                _provider_url=prepared.base_url,
                _timestamp=datetime.now(UTC),
            )
            yield streamed
        finally:
            if streamed is not None:
                await streamed.close_stream()
            await _close_worker_connections()


@dataclass
class _OpenRouterStreamedResponse(StreamedResponse):
    """SSE django-openrouter: текст чанками, reasoning и tool_calls — на финальном результате."""

    _chunks: AsyncGenerator[Any, None]
    _profile_name: str
    _provider_url: str
    _timestamp: datetime
    _answered_model: str = ""
    _closed: bool = False

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        emitted = ""
        async for chunk in self._chunks:
            model_used = chunk.model_used
            if isinstance(model_used, str) and model_used:
                self._answered_model = model_used
            delta = chunk.delta
            if isinstance(delta, str) and delta:
                emitted += delta
                for event in self._parts_manager.handle_text_delta(
                    vendor_part_id="content", content=delta
                ):
                    yield event
            if chunk.done and chunk.result is not None:
                for event in self._finish(chunk.result, emitted):
                    yield event

    def _finish(self, result: Any, emitted: str) -> Iterator[ModelResponseStreamEvent]:
        if result.model_used:
            self._answered_model = result.model_used
        self.finish_reason = _finish_reason(result.finish_reason)
        self.provider_response_id = _response_id(result)
        self.provider_details = _provider_details(result)
        if result.incomplete:
            self.state = "incomplete"
        self._add_usage(_request_usage(result), reported=True, cumulative=True)
        if result.reasoning:
            yield from self._parts_manager.handle_thinking_delta(
                vendor_part_id="reasoning",
                content=result.reasoning,
                provider_name=_PROVIDER_NAME,
            )
        full = result.content if isinstance(result.content, str) else ""
        if full.startswith(emitted):
            suffix = full[len(emitted) :]
        else:
            suffix = ""
        if suffix:
            yield from self._parts_manager.handle_text_delta(
                vendor_part_id="content", content=suffix
            )
        for index, call in enumerate(result.tool_calls):
            event = _tool_call_event(self, index, call)
            if event is not None:
                yield event

    async def close_stream(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._chunks.aclose()

    @property
    def model_name(self) -> str:
        if self._answered_model:
            return self._answered_model
        return self._profile_name

    @property
    def provider_name(self) -> str:
        return _PROVIDER_NAME

    @property
    def provider_url(self) -> str:
        return self._provider_url

    @property
    def timestamp(self) -> datetime:
        return self._timestamp


def _tool_call_event(
    streamed: _OpenRouterStreamedResponse, index: int, call: object
) -> ModelResponseStreamEvent | None:
    name, arguments, call_id = _split_tool_call(call)
    return streamed._parts_manager.handle_tool_call_delta(
        vendor_part_id=f"tool-{index}",
        tool_name=name or None,
        args=arguments,
        tool_call_id=call_id,
        provider_name=_PROVIDER_NAME,
    )


def _grouping_overrides(messages: Sequence[ModelMessage]) -> dict[str, Any]:
    """session_id и metadata для журнала и тела chat.

    ``bound_session`` важнее ``conversation_id`` агента. ``trace_id`` не
    передаём: его берёт активный спан OpenTelemetry либо генерирует клиент.
    """
    from django_openrouter.call_context import current_metadata, current_session_id

    overrides: dict[str, Any] = {}
    session_id = current_session_id()
    if session_id is None:
        session_id = _conversation_session_id(messages)
    if session_id is not None:
        overrides["session_id"] = session_id
    metadata = current_metadata()
    if metadata:
        overrides["metadata"] = metadata
    return overrides


def _conversation_session_id(messages: Sequence[ModelMessage]) -> str | None:
    from django_openrouter.call_context import coerce_session_id
    from django_openrouter.exceptions import ConfigurationError

    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        conversation_id = message.conversation_id
        if not isinstance(conversation_id, str):
            return None
        try:
            return coerce_session_id(conversation_id)
        except ConfigurationError:
            return None
    return None


async def _prepare_on_db_thread(
    profile_name: str | None,
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> _PreparedCall:
    from asgiref.sync import sync_to_async

    return await sync_to_async(_prepare_call, thread_sensitive=True)(
        profile_name, model_settings, model_request_parameters
    )


async def _close_worker_connections() -> None:
    # Тот же thread_sensitive-поток, что писал RequestLog: при CONN_MAX_AGE=0
    # соединение там иначе остаётся до конца процесса (run_sync крутит свой loop).
    from asgiref.sync import sync_to_async
    from django.db import close_old_connections

    await sync_to_async(close_old_connections, thread_sensitive=True)()


def _prepare_call(
    profile_name: str | None,
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> _PreparedCall:
    from django_openrouter.config import get_runtime_config
    from django_openrouter.models import OpenRouterSettings, UsageProfile

    if profile_name is not None:
        profile = UsageProfile.objects.filter(name=profile_name).first()
    else:
        settings_obj = OpenRouterSettings.load()
        profile = settings_obj.default_profile if settings_obj.default_profile_id else None
    overrides: dict[str, Any] = {}
    _apply_sampling(overrides, profile, model_settings)
    overrides.update(_tool_overrides(model_settings, model_request_parameters))
    _apply_output_format(overrides, model_request_parameters)
    if model_request_parameters.thinking is not None:
        overrides["reasoning"] = _reasoning_body(model_request_parameters.thinking)
    return _PreparedCall(overrides=overrides, base_url=get_runtime_config().base_url)


def _apply_sampling(
    overrides: dict[str, Any],
    profile: Any,
    model_settings: ModelSettings | None,
) -> None:
    if not model_settings:
        return
    if "max_tokens" in model_settings:
        requested = int(model_settings["max_tokens"])
        ceiling = profile.max_tokens if profile is not None else None
        if isinstance(ceiling, int):
            requested = min(requested, ceiling)
        overrides["max_tokens"] = requested
    if "temperature" in model_settings:
        requested_temperature = float(model_settings["temperature"])
        if requested_temperature < 0:
            requested_temperature = 0.0
        elif requested_temperature > _TEMPERATURE_MAX:
            requested_temperature = _TEMPERATURE_MAX
        ceiling_temperature = profile.temperature if profile is not None else None
        if isinstance(ceiling_temperature, int | float) and not isinstance(
            ceiling_temperature, bool
        ):
            requested_temperature = min(requested_temperature, float(ceiling_temperature))
        overrides["temperature"] = requested_temperature
    timeout = _timeout_seconds(model_settings.get("timeout"))
    if timeout is not None:
        overrides["request_timeout"] = timeout
    if "stop_sequences" in model_settings:
        overrides["stop"] = list(model_settings["stop_sequences"])
    if "top_p" in model_settings:
        overrides["top_p"] = model_settings["top_p"]
    if "top_k" in model_settings:
        overrides["top_k"] = model_settings["top_k"]
    if "seed" in model_settings:
        overrides["seed"] = model_settings["seed"]
    if "presence_penalty" in model_settings:
        overrides["presence_penalty"] = model_settings["presence_penalty"]
    if "frequency_penalty" in model_settings:
        overrides["frequency_penalty"] = model_settings["frequency_penalty"]
    if "logit_bias" in model_settings:
        overrides["logit_bias"] = model_settings["logit_bias"]
    if "parallel_tool_calls" in model_settings:
        overrides["parallel_tool_calls"] = model_settings["parallel_tool_calls"]


def _timeout_seconds(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        if value > 0:
            return float(value)
        return None
    if isinstance(value, httpx.Timeout):
        read = value.read
        if isinstance(read, int | float) and not isinstance(read, bool) and read > 0:
            return float(read)
    return None


def _tool_overrides(
    model_settings: ModelSettings | None,
    params: ModelRequestParameters,
) -> dict[str, Any]:
    resolved = resolve_tool_choice(model_settings, params)
    if resolved == "none":
        return {}
    chosen: set[str] | None
    choice: Any
    if resolved == "auto":
        chosen = None
        choice = "auto"
    elif resolved == "required":
        chosen = None
        choice = "required"
    else:
        mode, chosen = resolved
        if mode == "required" and len(chosen) == 1:
            only = next(iter(chosen))
            choice = {"type": "function", "function": {"name": only}}
        else:
            choice = mode
    tools: list[dict[str, Any]] = []
    for tool in params.declared_tool_defs.values():
        if chosen is not None and tool.name not in chosen:
            continue
        function: dict[str, Any] = {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.parameters_json_schema,
        }
        if tool.strict:
            function["strict"] = True
        tools.append({"type": "function", "function": function})
    if not tools:
        return {}
    return {"tools": tools, "tool_choice": choice}


def _apply_output_format(overrides: dict[str, Any], params: ModelRequestParameters) -> None:
    if params.output_mode == "native" and params.output_object is not None:
        output_object = params.output_object
        schema: dict[str, Any] = {
            "name": output_object.name or _DEFAULT_OUTPUT_NAME,
            "schema": output_object.json_schema,
        }
        if output_object.description:
            schema["description"] = output_object.description
        if output_object.strict is not None:
            schema["strict"] = output_object.strict
        overrides["response_format"] = {"type": "json_schema", "json_schema": schema}
    elif params.output_mode == "prompted":
        overrides["response_format"] = {"type": "json_object"}


def _reasoning_body(thinking: ThinkingLevel) -> dict[str, Any]:
    if thinking is False:
        return {"enabled": False}
    if thinking is True or thinking == "medium":
        effort = "medium"
    elif thinking in ("minimal", "low"):
        effort = "low"
    elif thinking in ("high", "xhigh"):
        effort = "high"
    elif thinking == "max":
        effort = "max"
    else:
        raise UserError(f"Unsupported thinking level: {thinking!r}")
    return {"enabled": True, "effort": effort}


def _map_messages(
    messages: Sequence[ModelMessage],
    params: ModelRequestParameters,
) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, ModelRequest):
            mapped.extend(_map_request(message))
        elif isinstance(message, ModelResponse):
            assistant = _map_response_message(message)
            if assistant is not None:
                mapped.append(assistant)
        else:
            raise UserError(
                f"OpenRouterProfileModel cannot send {type(message).__name__} to chat completions."
            )
    instruction_parts = Model._get_instruction_parts(messages, params) or []
    if instruction_parts:
        index = 0
        while index < len(mapped) and mapped[index].get("role") == "system":
            index += 1
        block = [{"role": "system", "content": part.content} for part in instruction_parts]
        mapped[index:index] = block
    return mapped


def _map_request(message: ModelRequest) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for part in message.parts:
        if isinstance(part, SystemPromptPart):
            mapped.append({"role": "system", "content": part.content})
        elif isinstance(part, UserPromptPart):
            mapped.append({"role": "user", "content": _user_content(part)})
        elif isinstance(part, ToolReturnPart):
            text, files = part.model_response_str_and_user_content()
            mapped.append({"role": "tool", "tool_call_id": part.tool_call_id, "content": text})
            if files:
                mapped.append({"role": "user", "content": _content_items(files)})
        else:
            raise UserError(
                f"OpenRouterProfileModel cannot send {type(part).__name__} to chat completions."
            )
    return mapped


def _map_response_message(message: ModelResponse) -> dict[str, Any] | None:
    texts: list[str] = []
    thoughts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for part in message.parts:
        if isinstance(part, TextPart):
            texts.append(part.content)
        elif isinstance(part, ThinkingPart):
            thoughts.append(part.content)
        elif isinstance(part, ToolCallPart):
            tool_calls.append(
                {
                    "id": part.tool_call_id,
                    "type": "function",
                    "function": {
                        "name": part.tool_name,
                        "arguments": part.args_as_json_str(),
                    },
                }
            )
        else:
            kind = type(part).__name__
            raise UserError(f"OpenRouterProfileModel cannot send {kind} back to chat completions.")
    if not texts and not thoughts and not tool_calls:
        return None
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": "\n\n".join(texts) if texts else None,
    }
    if thoughts:
        payload["reasoning"] = "\n\n".join(thoughts)
    if tool_calls:
        payload["tool_calls"] = tool_calls
    return payload


def _user_content(part: UserPromptPart) -> str | list[dict[str, Any]]:
    if isinstance(part.content, str):
        return part.content
    return _content_items(part.content)


def _content_items(items: Sequence[UserContent]) -> str | list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for item in items:
        piece = _map_user_item(item)
        if piece is not None:
            mapped.append(piece)
    if len(mapped) == 1 and mapped[0].get("type") == "text":
        text = mapped[0].get("text")
        if isinstance(text, str):
            return text
    return mapped


def _map_user_item(item: UserContent) -> dict[str, Any] | None:
    if isinstance(item, str):
        return {"type": "text", "text": item}
    if isinstance(item, TextContent):
        return {"type": "text", "text": item.content}
    if isinstance(item, CachePoint):
        return None
    if isinstance(item, ImageUrl):
        return _image_part(item.url, item.vendor_metadata)
    if isinstance(item, BinaryContent):
        if item.is_image:
            return _image_part(item.data_uri, item.vendor_metadata)
        raise UserError(
            "OpenRouterProfileModel only sends image binary content. "
            f"Got media type {item.media_type!r}."
        )
    raise UserError(f"OpenRouterProfileModel cannot send {type(item).__name__} in a user message.")


def _image_part(url: str, vendor_metadata: dict[str, Any] | None) -> dict[str, Any]:
    image_url: dict[str, Any] = {"url": url}
    if vendor_metadata is not None:
        detail = vendor_metadata.get("detail")
        if isinstance(detail, str):
            image_url["detail"] = detail
    return {"type": "image_url", "image_url": image_url}


def _to_model_response(result: Any, base_url: str, fallback_model_name: str) -> ModelResponse:
    parts: list[TextPart | ThinkingPart | ToolCallPart] = []
    if result.reasoning:
        parts.append(ThinkingPart(content=result.reasoning))
    if result.content:
        parts.append(TextPart(content=result.content))
    for call in result.tool_calls:
        name, arguments, call_id = _split_tool_call(call)
        if call_id is None:
            parts.append(ToolCallPart(tool_name=name, args=arguments))
        else:
            parts.append(ToolCallPart(tool_name=name, args=arguments, tool_call_id=call_id))
    model_name = result.model_used if result.model_used else fallback_model_name
    return ModelResponse(
        parts,
        usage=_request_usage(result),
        model_name=model_name,
        provider_name=_PROVIDER_NAME,
        provider_url=base_url,
        provider_response_id=_response_id(result),
        provider_details=_provider_details(result),
        finish_reason=_finish_reason(result.finish_reason),
        state="incomplete" if result.incomplete else "complete",
    )


def _split_tool_call(call: object) -> tuple[str, str | dict[str, Any], str | None]:
    if not isinstance(call, dict):
        raise UserError("OpenRouter tool call payload must be an object.")
    function = call.get("function")
    if not isinstance(function, dict):
        function = {}
    name = function.get("name")
    arguments = function.get("arguments")
    parsed: str | dict[str, Any]
    if isinstance(arguments, str) or isinstance(arguments, dict):
        parsed = arguments
    elif arguments is None:
        parsed = "{}"
    else:
        parsed = str(arguments)
    call_id = call.get("id")
    return str(name or ""), parsed, call_id if isinstance(call_id, str) and call_id else None


def _request_usage(result: Any) -> RequestUsage:
    raw_usage = _raw_usage(result)
    cache_read = 0
    prompt_details = raw_usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        cached = prompt_details.get("cached_tokens")
        if isinstance(cached, int) and not isinstance(cached, bool):
            cache_read = cached
    reasoning_tokens = 0
    completion_details = raw_usage.get("completion_tokens_details")
    if isinstance(completion_details, dict):
        raw_reasoning = completion_details.get("reasoning_tokens")
        if isinstance(raw_reasoning, int) and not isinstance(raw_reasoning, bool):
            reasoning_tokens = raw_reasoning
    details: dict[str, int] = {}
    if reasoning_tokens:
        details["reasoning_tokens"] = reasoning_tokens
    return RequestUsage(
        input_tokens=result.prompt_tokens,
        output_tokens=result.completion_tokens,
        cache_read_tokens=cache_read,
        output_reasoning_tokens=reasoning_tokens,
        details=details,
        cost=result.cost_usd,
    )


def _raw_usage(result: Any) -> dict[str, Any]:
    raw = result.raw
    if not isinstance(raw, dict):
        return {}
    usage = raw.get("usage")
    if isinstance(usage, dict):
        return usage
    return {}


def _provider_details(result: Any) -> dict[str, Any]:
    details: dict[str, Any] = {"latency_ms": result.latency_ms}
    catalog = result.catalog_cost_usd
    if catalog is not None:
        details["catalog_cost_usd"] = str(catalog)
    return details


def _response_id(result: Any) -> str | None:
    raw = result.raw
    if not isinstance(raw, dict):
        return None
    response_id = raw.get("id")
    if isinstance(response_id, str) and response_id:
        return response_id
    return None


def _finish_reason(value: object) -> FinishReason | None:
    if not isinstance(value, str):
        return None
    return _FINISH_REASONS.get(value)
