"""Синхронный и асинхронный клиенты OpenRouter (Chat Completions)."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Generator,
    Iterator,
    Mapping,
    Sequence,
)
from contextlib import aclosing, closing
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from asgiref.sync import sync_to_async
from django.utils.translation import gettext as _

from django_openrouter.concurrency import get_limiter
from django_openrouter.config import (
    ProfileSnapshot,
    RuntimeConfig,
    get_runtime_config,
    openrouter_setting,
)
from django_openrouter.exceptions import (
    ConfigurationError,
    ModelDisabled,
    OpenRouterAPIError,
    OpenRouterDisabled,
)
from django_openrouter.http_clients import get_async_client, get_sync_client
from django_openrouter.log_backends import (
    LogRecord,
    active_reservation_id,
    adispatch_log,
    amark_usage_missing,
    dispatch_log,
    has_active_budget_reservation,
    make_record,
    mark_usage_missing,
    set_active_reservation,
)
from django_openrouter.models import (
    CLIENT_CLOSED_STATUS,
    OpenRouterModel,
    RequestLog,
    UsageProfile,
)
from django_openrouter.rules import assert_model_allowed, check_limits, reserve_request

logger = logging.getLogger("django_openrouter")

ChatMessage = Mapping[str, Any]
ChatMessages = Sequence[ChatMessage]

# После исчерпания retry на модели — переходим к следующей в цепочке.
_FALLBACK_STATUSES = frozenset({402, 408, 429})
# Кончились кредиты аккаунта: дальше по цепочке имеют смысл только бесплатные модели.
_CREDITS_EXHAUSTED_STATUS = 402
# Повторяем на той же модели (плюс любые 5xx и транспортные ошибки).
_RETRY_STATUSES = frozenset({408, 425, 429})
# Ключи уровня OpenRouter, а не модели: не сверяются с supported_parameters.
_PASSTHROUGH_KEYS = frozenset(
    {
        "provider",
        "transforms",
        "models",
        "route",
        "usage",
        "user",
        "plugins",
        "prediction",
        "debug",
        "session_id",
        "metadata",
        "modalities",
    }
)
_MANAGED_KEYS = frozenset({"stream", "max_tokens", "temperature", "model", "stream_options"})
# OpenRouter-ошибка в теле 200 без кода — считаем upstream-сбоем, чтобы сработал fallback.
_BODY_ERROR_STATUS = 502
_ERROR_TEXT_LIMIT = 2000
_DEFAULT_RETRY_BACKOFF = 0.5
_MAX_RETRY_DELAY = 30.0


class _UsageMissing(OpenRouterAPIError):
    """Ответ получен (и оплачен), но без usage: без retry/fallback, резерв не закрываем."""


@dataclass(frozen=True)
class ChatResult:
    """Результат chat-completions вызова."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    catalog_cost_usd: Decimal | None
    model_used: str
    latency_ms: int
    raw: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str | None = None


@dataclass(frozen=True)
class ChatChunk:
    """Фрагмент SSE-ответа. У последнего чанка done=True и заполнен result."""

    delta: str
    content: str
    model_used: str = ""
    done: bool = False
    result: ChatResult | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _to_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def compute_cost(
    prompt_tokens: int,
    completion_tokens: int,
    pricing: Mapping[str, Any] | None,
    usage_cost: object | None = None,
) -> tuple[Decimal, Decimal | None]:
    """
    Возвращает (cost_usd для лога, catalog_cost для сверки).

    usage.cost от OpenRouter — фактически списанная сумма (учитывает кэш,
    reasoning-токены, скидки провайдера), поэтому он в приоритете.
    Каталожная оценка (prompt + completion + request) — fallback и сверка.
    """
    catalog_cost: Decimal | None = None
    if pricing:
        prompt_price = _to_decimal(pricing.get("prompt")) or Decimal("0")
        completion_price = _to_decimal(pricing.get("completion")) or Decimal("0")
        request_price = _to_decimal(pricing.get("request")) or Decimal("0")
        catalog_cost = (
            prompt_price * prompt_tokens + completion_price * completion_tokens + request_price
        )
    if usage_cost is None:
        return catalog_cost or Decimal("0"), catalog_cost
    api_cost = _to_decimal(usage_cost)
    if api_cost is None or not api_cost.is_finite() or api_cost < 0:
        raise OpenRouterAPIError(_("OpenRouter reported invalid usage cost."))
    return api_cost, catalog_cost


def _headers(cfg: RuntimeConfig) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    if cfg.http_referer:
        headers["HTTP-Referer"] = cfg.http_referer
    if cfg.x_title:
        headers["X-Title"] = cfg.x_title
    return headers


def _warn_unsupported(model: OpenRouterModel, overrides: Mapping[str, Any]) -> None:
    supported = set(model.supported_parameters or [])
    if not supported:
        return
    unknown = sorted(
        key
        for key in overrides
        if key not in supported and key not in _PASSTHROUGH_KEYS and key not in _MANAGED_KEYS
    )
    if unknown:
        logger.warning(
            "Model %s does not declare support for parameters: %s",
            model.model_id,
            ", ".join(unknown),
        )


def _build_payload(
    profile: UsageProfile,
    model: OpenRouterModel,
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    stream: bool = False,
) -> dict[str, Any]:
    _warn_unsupported(model, overrides)
    payload: dict[str, Any] = {"model": model.model_id, "messages": list(messages)}
    max_tokens = overrides["max_tokens"] if "max_tokens" in overrides else profile.max_tokens
    temperature = overrides["temperature"] if "temperature" in overrides else profile.temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    # Без usage.include OpenRouter может не вернуть фактический usage.cost.
    payload["usage"] = {"include": True}
    for key, value in overrides.items():
        if key in _MANAGED_KEYS:
            continue
        payload[key] = value
    return payload


def _join_content(content: object) -> str:
    """content бывает строкой или списком частей [{type: text, text: ...}]."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return str(content)


def _first_choice(payload: Mapping[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return {}
    return choices[0]


def _decode_sse_line(line: str) -> dict[str, Any] | bool | None:
    """Разбор одной SSE-строки: dict, True=[DONE], None=пропуск."""
    stripped = line.strip()
    if not stripped or stripped.startswith(":"):
        return None
    if not stripped.startswith("data:"):
        return None
    data = stripped[5:].strip()
    if data == "[DONE]":
        return True
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _error_from_body(event: Mapping[str, Any]) -> OpenRouterAPIError | None:
    """OpenRouter может прислать {"error": ...} и в теле 200, и в SSE-событии."""
    err = event.get("error")
    if not err:
        return None
    if isinstance(err, dict):
        raw_code = err.get("code") if "code" in err else err.get("status")
        try:
            status = int(raw_code) if raw_code is not None else _BODY_ERROR_STATUS
        except (TypeError, ValueError):
            status = _BODY_ERROR_STATUS
        message = str(err.get("message") or err)
    else:
        status = _BODY_ERROR_STATUS
        message = str(err)
    return OpenRouterAPIError(message, status_code=status)


def _http_error(status_code: int, text: str) -> OpenRouterAPIError:
    return OpenRouterAPIError(
        _("OpenRouter returned HTTP %(status)s: %(error)s")
        % {"status": status_code, "error": text[:_ERROR_TEXT_LIMIT]},
        status_code=status_code,
    )


def _resolve_profile(cfg: RuntimeConfig, profile_name: str | None) -> ProfileSnapshot:
    name = profile_name or cfg.default_profile_name
    if not name:
        raise ConfigurationError(_("No usage profile specified and default_profile is not set."))
    snapshot = cfg.profiles.get(name)
    if snapshot is None:
        raise ConfigurationError(
            _("Usage profile %(name)r is not found or inactive.") % {"name": name}
        )
    return snapshot


def _model_chain(
    profile: UsageProfile,
    overrides: dict[str, Any],
) -> list[OpenRouterModel]:
    chain: list[OpenRouterModel] = list(profile.ordered_models())
    override_id = overrides.get("model")
    if override_id:
        overridden = next((item for item in chain if item.model_id == override_id), None)
        if overridden is None:
            raise ConfigurationError(
                _("Model %(model_id)r is not configured for profile %(name)r.")
                % {"model_id": override_id, "name": profile.name}
            )
        chain = [overridden] + [item for item in chain if item.pk != overridden.pk]
    return chain


def _allowed_models(profile: UsageProfile, chain: list[OpenRouterModel]) -> list[OpenRouterModel]:
    allowed: list[OpenRouterModel] = []
    for model in chain:
        try:
            assert_model_allowed(profile, model)
        except ModelDisabled:
            continue
        allowed.append(model)
    if not chain:
        raise ConfigurationError(
            _("Profile %(name)r has no models configured.") % {"name": profile.name}
        )
    if not allowed:
        raise ModelDisabled(
            _("No allowed models left for profile %(name)r.") % {"name": profile.name}
        )
    return allowed


def _should_fallback(status_code: int | None) -> bool:
    return status_code is None or status_code in _FALLBACK_STATUSES or status_code >= 500


def _is_retryable(status_code: int | None) -> bool:
    return status_code is None or status_code in _RETRY_STATUSES or status_code >= 500


def _retry_delay(attempt: int, retry_after: str | None = None) -> float:
    """Retry-After от сервера, иначе экспонента с jitter (OPENROUTER['RETRY_BACKOFF'])."""
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), _MAX_RETRY_DELAY)
        except ValueError:
            pass
    base = float(openrouter_setting("RETRY_BACKOFF", _DEFAULT_RETRY_BACKOFF) or 0)
    if base <= 0:
        return 0.0
    return min(base * (2**attempt), _MAX_RETRY_DELAY) * random.uniform(0.5, 1.0)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _record(
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
    *,
    status_code: int,
    error_message: str | None = None,
    result: ChatResult | None = None,
) -> LogRecord:
    return make_record(
        profile=profile,
        model=model,
        status_code=status_code,
        error_message=error_message,
        prompt_tokens=result.prompt_tokens if result else 0,
        completion_tokens=result.completion_tokens if result else 0,
        cost_usd=result.cost_usd if result else Decimal("0"),
        latency_ms=_elapsed_ms(started),
    )


def _build_result(
    *,
    content: str,
    usage: Mapping[str, Any],
    model: OpenRouterModel,
    model_used: str,
    latency_ms: int,
    raw: dict[str, Any],
    finish_reason: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    reasoning: str | None = None,
    require_usage: bool = True,
) -> ChatResult:
    # Без usage резерв бюджета нельзя закрыть фактической суммой — оставляем его pending.
    if (
        require_usage
        and has_active_budget_reservation()
        and not ("cost" in usage or ("prompt_tokens" in usage and "completion_tokens" in usage))
    ):
        raise _UsageMissing(
            _("OpenRouter omitted usage for a budgeted request; reservation remains pending.")
        )
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    cost_usd, catalog_cost = compute_cost(
        prompt_tokens, completion_tokens, model.pricing, usage.get("cost")
    )
    return ChatResult(
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        catalog_cost_usd=catalog_cost,
        model_used=model_used or model.model_id,
        latency_ms=latency_ms,
        raw=raw,
        finish_reason=finish_reason,
        tool_calls=tool_calls or [],
        reasoning=reasoning or None,
    )


def _parse_json_response(
    response: httpx.Response, model: OpenRouterModel, started: float
) -> ChatResult:
    """Разбор 200-ответа. Ошибка в теле или битый JSON → OpenRouterAPIError."""
    try:
        payload = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OpenRouterAPIError(
            _("OpenRouter returned invalid JSON: %(error)s") % {"error": exc},
            status_code=_BODY_ERROR_STATUS,
        ) from exc
    if not isinstance(payload, dict):
        raise OpenRouterAPIError(
            _("OpenRouter returned unexpected payload."), status_code=_BODY_ERROR_STATUS
        )
    body_error = _error_from_body(payload)
    if body_error is not None:
        raise body_error
    choice = _first_choice(payload)
    message = choice.get("message") or {}
    if not isinstance(message, dict):
        message = {}
    tool_calls = message.get("tool_calls")
    return _build_result(
        content=_join_content(message.get("content")),
        usage=payload.get("usage") or {},
        model=model,
        model_used=str(payload.get("model") or ""),
        latency_ms=_elapsed_ms(started),
        raw=payload,
        finish_reason=choice.get("finish_reason"),
        tool_calls=tool_calls if isinstance(tool_calls, list) else None,
        reasoning=message.get("reasoning"),
    )


def _done_chunk(result: ChatResult, raw: dict[str, Any]) -> ChatChunk:
    return ChatChunk(
        delta="",
        content=result.content,
        model_used=result.model_used,
        done=True,
        result=result,
        raw=raw,
    )


class _SSEState:
    """Накопитель SSE-потока: общий для sync/async, без ввода-вывода."""

    def __init__(self, model: OpenRouterModel, started: float) -> None:
        self.model = model
        self.started = started
        self.parts: list[str] = []
        self.reasoning: list[str] = []
        self.tool_calls: dict[int, dict[str, Any]] = {}
        self.model_used = model.model_id
        self.usage: dict[str, Any] = {}
        self.last_event: dict[str, Any] = {}
        self.finish_reason: str | None = None
        self.finished = False

    @property
    def has_content(self) -> bool:
        return bool(self.parts)

    def feed(self, line: str) -> ChatChunk | None:
        """Возвращает чанк с дельтой текста либо None. Ошибка в событии → исключение."""
        decoded = _decode_sse_line(line)
        if decoded is True:
            self.finished = True
            return None
        if not isinstance(decoded, dict):
            return None
        body_error = _error_from_body(decoded)
        if body_error is not None:
            raise body_error
        self.last_event = decoded
        if decoded.get("model"):
            self.model_used = str(decoded["model"])
        event_usage = decoded.get("usage")
        if isinstance(event_usage, dict):
            self.usage = event_usage
        choice = _first_choice(decoded)
        if choice.get("finish_reason"):
            self.finish_reason = str(choice["finish_reason"])
        delta = choice.get("delta") or {}
        if not isinstance(delta, dict):
            return None
        if delta.get("reasoning"):
            self.reasoning.append(str(delta["reasoning"]))
        self._merge_tool_calls(delta.get("tool_calls"))
        text = _join_content(delta.get("content"))
        if not text:
            return None
        self.parts.append(text)
        return ChatChunk(
            delta=text,
            content="".join(self.parts),
            model_used=self.model_used,
            raw=decoded,
        )

    def _merge_tool_calls(self, deltas: object) -> None:
        # Аргументы tool_calls в стриме приходят кусками по index.
        if not isinstance(deltas, list):
            return
        for item in deltas:
            if not isinstance(item, dict):
                continue
            index = int(item.get("index") or 0)
            call = self.tool_calls.setdefault(
                index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
            )
            if item.get("id"):
                call["id"] = item["id"]
            if item.get("type"):
                call["type"] = item["type"]
            function = item.get("function")
            if isinstance(function, dict):
                call["function"]["name"] += str(function.get("name") or "")
                call["function"]["arguments"] += str(function.get("arguments") or "")

    def result(self, *, partial: bool = False) -> ChatResult:
        if not partial and not self.finished:
            raise OpenRouterAPIError(
                _("OpenRouter stream ended before [DONE]."), status_code=_BODY_ERROR_STATUS
            )
        usage = self.usage
        cost = _to_decimal(usage.get("cost"))
        if partial and (cost is None or not cost.is_finite() or cost < 0):
            usage = {key: value for key, value in usage.items() if key != "cost"}
        return _build_result(
            require_usage=not partial,
            content="".join(self.parts),
            usage=usage,
            model=self.model,
            model_used=self.model_used,
            latency_ms=_elapsed_ms(self.started),
            raw=self.last_event,
            finish_reason=self.finish_reason,
            tool_calls=[self.tool_calls[key] for key in sorted(self.tool_calls)],
            reasoning="".join(self.reasoning),
        )


def _want_sse(cfg: RuntimeConfig, overrides: Mapping[str, Any], *, force: bool = False) -> bool:
    """Нужен ли SSE: метод stream() или явный chat(stream=True)."""
    wanted = force or bool(overrides.get("stream", False))
    if wanted and not cfg.streaming_enabled:
        raise ConfigurationError(_("Streaming is disabled in admin settings."))
    return wanted


def _prepare(
    profile_name: str | None,
    overrides: dict[str, Any],
) -> tuple[RuntimeConfig, UsageProfile, list[OpenRouterModel]]:
    """Конфиг, профиль и допустимая цепочка моделей. Резерв — на каждую попытку."""
    set_active_reservation(None)
    cfg = get_runtime_config()
    if not cfg.enabled:
        raise OpenRouterDisabled(_("OpenRouter is disabled in admin settings."))
    if not cfg.api_key:
        raise ConfigurationError(_("OpenRouter API key is not configured."))
    snapshot = _resolve_profile(cfg, profile_name)
    profile = UsageProfile.objects.select_related("model").get(pk=snapshot.pk)
    check_limits(profile)
    chain = _allowed_models(profile, _model_chain(profile, overrides))
    return cfg, profile, chain


def _activate_reservation(profile: UsageProfile, reservation: RequestLog | None) -> None:
    """Делает резерв активным; DatabaseBackend превратит его в лог попытки."""
    set_active_reservation(
        reservation.pk if reservation is not None else None,
        budgeted=profile.budget_usd_per_day is not None
        or profile.budget_usd_per_month is not None,
    )


def _count_images(messages: object) -> int:
    """Картинки во входе: у image-цены нет верхней границы, кроме их числа."""
    if not isinstance(messages, list):
        return 0
    count = 0
    for message in messages:
        content = message.get("content") if isinstance(message, Mapping) else None
        if isinstance(content, list):
            count += sum(
                1 for part in content if isinstance(part, dict) and part.get("type") == "image_url"
            )
    return count


def _abort_record(
    profile: UsageProfile, model: OpenRouterModel, started: float, exc: BaseException
) -> LogRecord | None:
    """Лог для попытки, прерванной отменой/сбоем: без него резерв висит до конца месяца."""
    if active_reservation_id() is None:
        return None
    return _record(
        profile,
        model,
        started,
        status_code=CLIENT_CLOSED_STATUS,
        error_message=f"attempt aborted: {type(exc).__name__}",
    )


def _collect_result(chunks: Iterator[ChatChunk]) -> ChatResult:
    for chunk in chunks:
        if chunk.done and chunk.result is not None:
            return chunk.result
    raise OpenRouterAPIError(_("All models failed without a specific error."))


async def _acollect_result(chunks: AsyncIterator[ChatChunk]) -> ChatResult:
    async for chunk in chunks:
        if chunk.done and chunk.result is not None:
            return chunk.result
    raise OpenRouterAPIError(_("All models failed without a specific error."))


class OpenRouterClient:
    """Синхронный клиент. Конфигурация берётся из runtime cache, не из БД напрямую."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        with closing(self._run(messages, overrides, emit=False)) as chunks:
            return _collect_result(chunks)

    def stream(self, messages: ChatMessages, **overrides: Any) -> Generator[ChatChunk, None, None]:
        with closing(self._run(messages, overrides, emit=True)) as chunks:
            yield from chunks

    def _run(
        self, messages: ChatMessages, overrides: dict[str, Any], *, emit: bool
    ) -> Generator[ChatChunk, None, None]:
        cfg, profile, chain = _prepare(self.profile_name, overrides)
        sse = _want_sse(cfg, overrides, force=emit)
        with closing(
            _iter_chain_sync(cfg, profile, chain, messages, overrides, sse=sse, emit=emit)
        ) as chunks:
            yield from chunks


def _iter_chain_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    sse: bool,
    emit: bool,
) -> Generator[ChatChunk, None, None]:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for model in chain:
        if credits_exhausted and not model.is_free:
            continue
        payload = _build_payload(profile, model, messages, overrides, stream=sse)
        emitted = False
        try:
            with closing(_attempt_sync(cfg, profile, model, payload, sse=sse, emit=emit)) as it:
                for chunk in it:
                    if chunk.done:
                        yield chunk
                        return
                    if emit:
                        emitted = True
                        yield chunk
        except OpenRouterAPIError as exc:
            if emitted or isinstance(exc, _UsageMissing) or not _should_fallback(exc.status_code):
                raise
            last_error = exc
            credits_exhausted |= exc.status_code == _CREDITS_EXHAUSTED_STATUS
    raise last_error or OpenRouterAPIError(_("All models failed without a specific error."))


def _attempt_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
    *,
    sse: bool,
    emit: bool,
) -> Generator[ChatChunk, None, None]:
    """Одна модель с retry. Финальный чанк done=True, либо OpenRouterAPIError."""
    http = get_sync_client()
    url = f"{cfg.base_url}/chat/completions"
    limiter = get_limiter()
    retries = int(cfg.max_retries)
    image_count = _count_images(payload.get("messages"))
    for attempt in range(retries + 1):
        _activate_reservation(profile, reserve_request(profile, model, image_count=image_count))
        started = time.perf_counter()
        retry_after: str | None = None
        state = _SSEState(model, started)
        try:
            with limiter.slot(cfg.max_parallel_requests):
                if not sse:
                    response = http.post(
                        url, json=payload, headers=_headers(cfg), timeout=cfg.request_timeout
                    )
                    if response.status_code == 200:
                        result = _parse_json_response(response, model, started)
                        dispatch_log(
                            _record(profile, model, started, status_code=200, result=result)
                        )
                        yield _done_chunk(result, result.raw)
                        return
                    retry_after = response.headers.get("Retry-After")
                    raise _http_error(response.status_code, response.text)
                with http.stream(
                    "POST", url, json=payload, headers=_headers(cfg), timeout=cfg.request_timeout
                ) as response:
                    if response.status_code != 200:
                        retry_after = response.headers.get("Retry-After")
                        text = response.read().decode("utf-8", errors="replace")
                        raise _http_error(response.status_code, text)
                    try:
                        for line in response.iter_lines():
                            chunk = state.feed(line)
                            if chunk is not None:
                                yield chunk
                            if state.finished:
                                break
                    except GeneratorExit:
                        partial = state.result(partial=True)
                        dispatch_log(
                            _record(
                                profile,
                                model,
                                started,
                                status_code=CLIENT_CLOSED_STATUS,
                                error_message="stream closed by consumer",
                                result=partial,
                            )
                        )
                        raise
                    result = state.result()
                    dispatch_log(_record(profile, model, started, status_code=200, result=result))
                    yield _done_chunk(result, state.last_event)
                    return
        except httpx.RequestError as exc:
            error = OpenRouterAPIError(str(exc), status_code=None)
            dispatch_log(_record(profile, model, started, status_code=0, error_message=str(exc)))
            if (emit and state.has_content) or attempt >= retries:
                raise error from exc
        except _UsageMissing:
            mark_usage_missing()
            raise
        except OpenRouterAPIError as exc:
            dispatch_log(
                _record(
                    profile,
                    model,
                    started,
                    status_code=exc.status_code or 0,
                    error_message=str(exc)[:_ERROR_TEXT_LIMIT],
                )
            )
            if (emit and state.has_content) or attempt >= retries:
                raise
            if not _is_retryable(exc.status_code):
                raise
        except BaseException as exc:
            record = _abort_record(profile, model, started, exc)
            if record is not None:
                dispatch_log(record)
            raise
        delay = _retry_delay(attempt, retry_after)
        if delay:
            time.sleep(delay)
    raise OpenRouterAPIError(_("All models failed without a specific error."))


class AsyncOpenRouterClient:
    """Асинхронный клиент с тем же интерфейсом, что и OpenRouterClient."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    async def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        async with aclosing(self._run(messages, overrides, emit=False)) as chunks:
            return await _acollect_result(chunks)

    async def stream(
        self, messages: ChatMessages, **overrides: Any
    ) -> AsyncGenerator[ChatChunk, None]:
        async with aclosing(self._run(messages, overrides, emit=True)) as chunks:
            async for chunk in chunks:
                yield chunk

    async def _run(
        self, messages: ChatMessages, overrides: dict[str, Any], *, emit: bool
    ) -> AsyncGenerator[ChatChunk, None]:
        set_active_reservation(None)
        cfg, profile, chain = await sync_to_async(_prepare, thread_sensitive=True)(
            self.profile_name, overrides
        )
        sse = _want_sse(cfg, overrides, force=emit)
        async with aclosing(
            _aiter_chain(cfg, profile, chain, messages, overrides, sse=sse, emit=emit)
        ) as chunks:
            async for chunk in chunks:
                yield chunk


async def _aiter_chain(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    sse: bool,
    emit: bool,
) -> AsyncGenerator[ChatChunk, None]:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for model in chain:
        if credits_exhausted and not model.is_free:
            continue
        payload = _build_payload(profile, model, messages, overrides, stream=sse)
        emitted = False
        try:
            async with aclosing(
                _attempt_async(cfg, profile, model, payload, sse=sse, emit=emit)
            ) as it:
                async for chunk in it:
                    if chunk.done:
                        yield chunk
                        return
                    if emit:
                        emitted = True
                        yield chunk
        except OpenRouterAPIError as exc:
            if emitted or isinstance(exc, _UsageMissing) or not _should_fallback(exc.status_code):
                raise
            last_error = exc
            credits_exhausted |= exc.status_code == _CREDITS_EXHAUSTED_STATUS
    raise last_error or OpenRouterAPIError(_("All models failed without a specific error."))


async def _attempt_async(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
    *,
    sse: bool,
    emit: bool,
) -> AsyncGenerator[ChatChunk, None]:
    """Асинхронное зеркало _attempt_sync."""
    http = get_async_client()
    url = f"{cfg.base_url}/chat/completions"
    limiter = get_limiter()
    retries = int(cfg.max_retries)
    image_count = _count_images(payload.get("messages"))
    for attempt in range(retries + 1):
        reservation = await sync_to_async(reserve_request, thread_sensitive=True)(
            profile, model, image_count=image_count
        )
        _activate_reservation(profile, reservation)
        started = time.perf_counter()
        retry_after: str | None = None
        state = _SSEState(model, started)
        try:
            async with limiter.aslot(cfg.max_parallel_requests):
                if not sse:
                    response = await http.post(
                        url, json=payload, headers=_headers(cfg), timeout=cfg.request_timeout
                    )
                    if response.status_code == 200:
                        result = _parse_json_response(response, model, started)
                        await adispatch_log(
                            _record(profile, model, started, status_code=200, result=result)
                        )
                        yield _done_chunk(result, result.raw)
                        return
                    retry_after = response.headers.get("Retry-After")
                    raise _http_error(response.status_code, response.text)
                async with http.stream(
                    "POST", url, json=payload, headers=_headers(cfg), timeout=cfg.request_timeout
                ) as response:
                    if response.status_code != 200:
                        retry_after = response.headers.get("Retry-After")
                        raw = await response.aread()
                        raise _http_error(
                            response.status_code, raw.decode("utf-8", errors="replace")
                        )
                    try:
                        async for line in response.aiter_lines():
                            chunk = state.feed(line)
                            if chunk is not None:
                                yield chunk
                            if state.finished:
                                break
                    except GeneratorExit:
                        partial = state.result(partial=True)
                        await adispatch_log(
                            _record(
                                profile,
                                model,
                                started,
                                status_code=CLIENT_CLOSED_STATUS,
                                error_message="stream closed by consumer",
                                result=partial,
                            )
                        )
                        raise
                    result = state.result()
                    await adispatch_log(
                        _record(profile, model, started, status_code=200, result=result)
                    )
                    yield _done_chunk(result, state.last_event)
                    return
        except httpx.RequestError as exc:
            error = OpenRouterAPIError(str(exc), status_code=None)
            await adispatch_log(
                _record(profile, model, started, status_code=0, error_message=str(exc))
            )
            if (emit and state.has_content) or attempt >= retries:
                raise error from exc
        except _UsageMissing:
            await amark_usage_missing()
            raise
        except OpenRouterAPIError as exc:
            await adispatch_log(
                _record(
                    profile,
                    model,
                    started,
                    status_code=exc.status_code or 0,
                    error_message=str(exc)[:_ERROR_TEXT_LIMIT],
                )
            )
            if (emit and state.has_content) or attempt >= retries:
                raise
            if not _is_retryable(exc.status_code):
                raise
        except BaseException as exc:
            record = _abort_record(profile, model, started, exc)
            if record is not None:
                await adispatch_log(record)
            raise
        delay = _retry_delay(attempt, retry_after)
        if delay:
            await asyncio.sleep(delay)
    raise OpenRouterAPIError(_("All models failed without a specific error."))


def chat(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> ChatResult:
    """Фасад: chat("translation", messages=[...])."""
    if messages is None:
        raise TypeError("chat() missing required argument: 'messages'")
    return OpenRouterClient(profile_name).chat(messages, **overrides)


async def achat(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> ChatResult:
    """Асинхронный фасад, зеркало chat()."""
    if messages is None:
        raise TypeError("achat() missing required argument: 'messages'")
    return await AsyncOpenRouterClient(profile_name).chat(messages, **overrides)


def stream(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> Generator[ChatChunk, None, None]:
    """Фасад SSE: for chunk in stream("chat", messages=[...])."""
    if messages is None:
        raise TypeError("stream() missing required argument: 'messages'")
    yield from OpenRouterClient(profile_name).stream(messages, **overrides)


async def astream(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> AsyncGenerator[ChatChunk, None]:
    """Асинхронный фасад SSE, зеркало stream()."""
    if messages is None:
        raise TypeError("astream() missing required argument: 'messages'")
    async for chunk in AsyncOpenRouterClient(profile_name).stream(messages, **overrides):
        yield chunk
