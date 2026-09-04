"""Синхронный и асинхронный клиенты OpenRouter (Chat Completions)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from asgiref.sync import sync_to_async
from django.utils.translation import gettext as _

from django_openrouter.concurrency import get_limiter
from django_openrouter.config import (
    ProfileSnapshot,
    RuntimeConfig,
    get_runtime_config,
)
from django_openrouter.exceptions import (
    ConfigurationError,
    ModelDisabled,
    OpenRouterAPIError,
    OpenRouterDisabled,
)
from django_openrouter.log_backends import adispatch_log, dispatch_log, make_record
from django_openrouter.models import OpenRouterModel, UsageProfile
from django_openrouter.rules import assert_model_allowed, check_limits

ChatMessage = Mapping[str, Any]
ChatMessages = Sequence[ChatMessage]

_FALLBACK_STATUSES = frozenset({402, 429})


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


@dataclass(frozen=True)
class ChatChunk:
    """Фрагмент SSE-ответа. У последнего чанка done=True и заполнен result."""

    delta: str
    content: str
    model_used: str = ""
    done: bool = False
    result: ChatResult | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def compute_cost(
    prompt_tokens: int,
    completion_tokens: int,
    pricing: Mapping[str, Any] | None,
    usage_cost: object | None = None,
) -> tuple[Decimal, Decimal | None]:
    """
    Считает стоимость по токенам usage и pricing каталога.

    Возвращает (cost_usd для лога, catalog_cost для сверки).
    Если OpenRouter прислал usage.cost — он используется как fallback,
    когда в каталоге нет цены.
    """
    catalog_cost: Decimal | None = None
    if pricing:
        prompt_price = Decimal(str(pricing.get("prompt") or 0))
        completion_price = Decimal(str(pricing.get("completion") or 0))
        catalog_cost = prompt_price * prompt_tokens + completion_price * completion_tokens
    api_cost = Decimal(str(usage_cost)) if usage_cost is not None else None
    if catalog_cost is not None:
        return catalog_cost, catalog_cost
    return api_cost or Decimal("0"), catalog_cost


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


def _build_payload(
    profile: UsageProfile,
    model_id: str,
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    stream: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model_id, "messages": list(messages)}
    max_tokens = overrides["max_tokens"] if "max_tokens" in overrides else profile.max_tokens
    temperature = overrides["temperature"] if "temperature" in overrides else profile.temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    for key, value in overrides.items():
        if key in {"stream", "max_tokens", "temperature", "model", "stream_options"}:
            continue
        payload[key] = value
    return payload


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") or {}
    content = message.get("content")
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


def _extract_delta(payload: dict[str, Any]) -> str:
    """Текст из choices[0].delta.content SSE-чанка."""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    delta = first.get("delta") or {}
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
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


def _sse_error(event: dict[str, Any]) -> OpenRouterAPIError:
    err = event.get("error")
    if isinstance(err, dict):
        raw_code = err.get("code") if "code" in err else err.get("status")
        try:
            status = int(raw_code) if raw_code is not None else 500
        except (TypeError, ValueError):
            status = 500
        message = str(err.get("message") or err)
    else:
        status = 500
        message = str(err)
    return OpenRouterAPIError(message, status_code=status)


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
        try:
            overridden = OpenRouterModel.objects.get(model_id=override_id)
        except OpenRouterModel.DoesNotExist as exc:
            raise ConfigurationError(
                _("Unknown model %(model_id)r.") % {"model_id": override_id}
            ) from exc
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


def _should_fallback(status_code: int) -> bool:
    return status_code in _FALLBACK_STATUSES or status_code >= 500


def _write_log(
    *,
    profile: UsageProfile,
    model: OpenRouterModel | None,
    status_code: int,
    error_message: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: Decimal = Decimal("0"),
    latency_ms: int = 0,
) -> None:
    dispatch_log(
        make_record(
            profile=profile,
            model=model,
            status_code=status_code,
            error_message=error_message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
    )


def _result_from_payload(
    payload: dict[str, Any],
    model: OpenRouterModel,
    latency_ms: int,
) -> ChatResult:
    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    usage_cost = usage.get("cost")
    cost_usd, catalog_cost = compute_cost(
        prompt_tokens,
        completion_tokens,
        model.pricing,
        usage_cost,
    )
    return ChatResult(
        content=_extract_content(payload),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        catalog_cost_usd=catalog_cost,
        model_used=str(payload.get("model") or model.model_id),
        latency_ms=latency_ms,
        raw=payload,
    )


def _result_from_sse(
    content: str,
    usage: Mapping[str, Any],
    model: OpenRouterModel,
    model_used: str,
    latency_ms: int,
    last_event: dict[str, Any],
) -> ChatResult:
    payload = {
        **last_event,
        "model": model_used or model.model_id,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": dict(usage),
    }
    return _result_from_payload(payload, model, latency_ms)


def _want_sse(cfg: RuntimeConfig, overrides: Mapping[str, Any], *, force: bool = False) -> bool:
    """Нужен ли SSE: явный stream= / дефолт из настроек / метод stream()."""
    if force:
        wanted = True
    elif "stream" in overrides:
        wanted = bool(overrides["stream"])
    else:
        wanted = bool(cfg.streaming_enabled)
    if wanted and not cfg.streaming_enabled:
        raise ConfigurationError(_("Streaming is disabled in admin settings."))
    return wanted


def _prepare(
    profile_name: str | None,
    overrides: dict[str, Any],
) -> tuple[RuntimeConfig, UsageProfile]:
    cfg = get_runtime_config()
    if not cfg.enabled:
        raise OpenRouterDisabled(_("OpenRouter is disabled in admin settings."))
    if not cfg.api_key:
        raise ConfigurationError(_("OpenRouter API key is not configured."))
    snapshot = _resolve_profile(cfg, profile_name)
    profile = UsageProfile.objects.select_related("model").get(pk=snapshot.pk)
    check_limits(profile)
    return cfg, profile


def _collect_result(chunks: Iterator[ChatChunk]) -> ChatResult:
    final: ChatResult | None = None
    for chunk in chunks:
        if chunk.done and chunk.result is not None:
            final = chunk.result
    if final is None:
        raise OpenRouterAPIError(_("All models failed without a specific error."))
    return final


async def _acollect_result(chunks: AsyncIterator[ChatChunk]) -> ChatResult:
    final: ChatResult | None = None
    async for chunk in chunks:
        if chunk.done and chunk.result is not None:
            final = chunk.result
    if final is None:
        raise OpenRouterAPIError(_("All models failed without a specific error."))
    return final


class OpenRouterClient:
    """Синхронный клиент. Конфигурация берётся из runtime cache, не из БД напрямую."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        cfg, profile = _prepare(self.profile_name, overrides)
        if _want_sse(cfg, overrides):
            return _collect_result(_iter_chain_sync(cfg, profile, messages, overrides, emit=False))
        return _collect_result(_iter_json_sync(cfg, profile, messages, overrides))

    def stream(self, messages: ChatMessages, **overrides: Any) -> Iterator[ChatChunk]:
        cfg, profile = _prepare(self.profile_name, overrides)
        _want_sse(cfg, overrides, force=True)
        yield from _iter_chain_sync(cfg, profile, messages, overrides, emit=True)


def _iter_json_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    messages: ChatMessages,
    overrides: dict[str, Any],
) -> Iterator[ChatChunk]:
    chain = _allowed_models(profile, _model_chain(profile, overrides))
    url = f"{cfg.base_url}/chat/completions"
    last_error: Exception | None = None
    with httpx.Client(timeout=cfg.request_timeout) as http:
        for model in chain:
            payload = _build_payload(profile, model.model_id, messages, overrides, stream=False)
            result, last_error = _attempt_model_sync(http, url, cfg, profile, model, payload)
            if result is not None:
                yield ChatChunk(
                    delta=result.content,
                    content=result.content,
                    model_used=result.model_used,
                    done=True,
                    result=result,
                    raw=result.raw,
                )
                return
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


def _iter_chain_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    emit: bool,
) -> Iterator[ChatChunk]:
    chain = _allowed_models(profile, _model_chain(profile, overrides))
    url = f"{cfg.base_url}/chat/completions"
    last_error: Exception | None = None
    with httpx.Client(timeout=cfg.request_timeout) as http:
        for model in chain:
            payload = _build_payload(profile, model.model_id, messages, overrides, stream=True)
            emitted = False
            try:
                for chunk in _attempt_stream_sync(http, url, cfg, profile, model, payload):
                    if emit and not chunk.done:
                        emitted = True
                        yield chunk
                    elif chunk.done:
                        yield chunk
                        return
            except OpenRouterAPIError as exc:
                last_error = exc
                if emitted:
                    raise
                status = exc.status_code
                if status is None or _should_fallback(status):
                    continue
                raise
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


def _attempt_model_sync(
    http: httpx.Client,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> tuple[ChatResult | None, Exception | None]:
    last_error: Exception | None = None
    limiter = get_limiter()
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            with limiter.slot(cfg.max_parallel_requests):
                response = http.post(url, json=payload, headers=_headers(cfg))
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _write_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if attempt >= int(cfg.max_retries):
                return None, last_error
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 200:
            payload_json = response.json()
            result = _result_from_payload(payload_json, model, latency_ms)
            _write_log(
                profile=profile,
                model=model,
                status_code=200,
                error_message=None,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
            )
            return result, None
        error_text = response.text[:2000]
        _write_log(
            profile=profile,
            model=model,
            status_code=response.status_code,
            error_message=error_text,
            latency_ms=latency_ms,
        )
        last_error = OpenRouterAPIError(
            _("OpenRouter returned HTTP %(status)s: %(error)s")
            % {"status": response.status_code, "error": error_text},
            status_code=response.status_code,
        )
        if response.status_code >= 500 and attempt < int(cfg.max_retries):
            continue
        if _should_fallback(response.status_code):
            return None, last_error
        raise last_error
    return None, last_error


def _attempt_stream_sync(
    http: httpx.Client,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> Iterator[ChatChunk]:
    last_error: Exception | None = None
    limiter = get_limiter()
    emitted = False
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            with limiter.slot(cfg.max_parallel_requests):
                with http.stream("POST", url, json=payload, headers=_headers(cfg)) as response:
                    if response.status_code != 200:
                        error_text = response.read().decode("utf-8", errors="replace")[:2000]
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        _write_log(
                            profile=profile,
                            model=model,
                            status_code=response.status_code,
                            error_message=error_text,
                            latency_ms=latency_ms,
                        )
                        last_error = OpenRouterAPIError(
                            _("OpenRouter returned HTTP %(status)s: %(error)s")
                            % {"status": response.status_code, "error": error_text},
                            status_code=response.status_code,
                        )
                        if response.status_code >= 500 and attempt < int(cfg.max_retries):
                            continue
                        raise last_error
                    for chunk in _consume_sse_sync(
                        response.iter_lines(),
                        profile=profile,
                        model=model,
                        started=started,
                    ):
                        if not chunk.done:
                            emitted = True
                        yield chunk
                    return
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _write_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if emitted or attempt >= int(cfg.max_retries):
                raise last_error from exc
            continue
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


def _consume_sse_sync(
    lines: Iterator[str],
    *,
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
) -> Iterator[ChatChunk]:
    parts: list[str] = []
    model_used = model.model_id
    usage: dict[str, Any] = {}
    last_event: dict[str, Any] = {}
    try:
        for line in lines:
            decoded = _decode_sse_line(line)
            if decoded is True:
                break
            if not isinstance(decoded, dict):
                continue
            event = decoded
            if event.get("error"):
                raise _sse_error(event)
            last_event = event
            if event.get("model"):
                model_used = str(event["model"])
            event_usage = event.get("usage")
            if isinstance(event_usage, dict):
                usage = event_usage
            delta = _extract_delta(event)
            if delta:
                parts.append(delta)
                yield ChatChunk(
                    delta=delta,
                    content="".join(parts),
                    model_used=model_used,
                    raw=event,
                )
    except OpenRouterAPIError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        status = exc.status_code or 500
        _write_log(
            profile=profile,
            model=model,
            status_code=status,
            error_message=str(exc),
            latency_ms=latency_ms,
        )
        raise
    latency_ms = int((time.perf_counter() - started) * 1000)
    result = _result_from_sse("".join(parts), usage, model, model_used, latency_ms, last_event)
    _write_log(
        profile=profile,
        model=model,
        status_code=200,
        error_message=None,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        latency_ms=latency_ms,
    )
    yield ChatChunk(
        delta="",
        content=result.content,
        model_used=result.model_used,
        done=True,
        result=result,
        raw=last_event,
    )


class AsyncOpenRouterClient:
    """Асинхронный клиент с тем же интерфейсом, что и OpenRouterClient."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    async def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        cfg, profile = await sync_to_async(_prepare, thread_sensitive=True)(
            self.profile_name, overrides
        )
        if _want_sse(cfg, overrides):
            return await _acollect_result(
                _aiter_chain(cfg, profile, messages, overrides, emit=False)
            )
        return await _acollect_result(_aiter_json(cfg, profile, messages, overrides))

    async def stream(self, messages: ChatMessages, **overrides: Any) -> AsyncIterator[ChatChunk]:
        cfg, profile = await sync_to_async(_prepare, thread_sensitive=True)(
            self.profile_name, overrides
        )
        _want_sse(cfg, overrides, force=True)
        async for chunk in _aiter_chain(cfg, profile, messages, overrides, emit=True):
            yield chunk


async def _awrite_log(
    *,
    profile: UsageProfile,
    model: OpenRouterModel | None,
    status_code: int,
    error_message: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: Decimal = Decimal("0"),
    latency_ms: int = 0,
) -> None:
    await adispatch_log(
        make_record(
            profile=profile,
            model=model,
            status_code=status_code,
            error_message=error_message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
    )


async def _aload_chain(
    profile: UsageProfile, overrides: dict[str, Any]
) -> list[OpenRouterModel]:
    chain = await sync_to_async(_model_chain, thread_sensitive=True)(profile, overrides)
    return await sync_to_async(_allowed_models, thread_sensitive=True)(profile, chain)


async def _aiter_json(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    messages: ChatMessages,
    overrides: dict[str, Any],
) -> AsyncIterator[ChatChunk]:
    chain = await _aload_chain(profile, overrides)
    url = f"{cfg.base_url}/chat/completions"
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=cfg.request_timeout) as http:
        for model in chain:
            payload = _build_payload(profile, model.model_id, messages, overrides, stream=False)
            result, last_error = await _attempt_model_async(
                http, url, cfg, profile, model, payload
            )
            if result is not None:
                yield ChatChunk(
                    delta=result.content,
                    content=result.content,
                    model_used=result.model_used,
                    done=True,
                    result=result,
                    raw=result.raw,
                )
                return
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


async def _aiter_chain(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    messages: ChatMessages,
    overrides: dict[str, Any],
    *,
    emit: bool,
) -> AsyncIterator[ChatChunk]:
    chain = await _aload_chain(profile, overrides)
    url = f"{cfg.base_url}/chat/completions"
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=cfg.request_timeout) as http:
        for model in chain:
            payload = _build_payload(profile, model.model_id, messages, overrides, stream=True)
            emitted = False
            try:
                async for chunk in _attempt_stream_async(
                    http, url, cfg, profile, model, payload
                ):
                    if emit and not chunk.done:
                        emitted = True
                        yield chunk
                    elif chunk.done:
                        yield chunk
                        return
            except OpenRouterAPIError as exc:
                last_error = exc
                if emitted:
                    raise
                status = exc.status_code
                if status is None or _should_fallback(status):
                    continue
                raise
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


async def _attempt_model_async(
    http: httpx.AsyncClient,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> tuple[ChatResult | None, Exception | None]:
    last_error: Exception | None = None
    limiter = get_limiter()
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            async with limiter.aslot(cfg.max_parallel_requests):
                response = await http.post(url, json=payload, headers=_headers(cfg))
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await _awrite_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if attempt >= int(cfg.max_retries):
                return None, last_error
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 200:
            payload_json = response.json()
            result = _result_from_payload(payload_json, model, latency_ms)
            await _awrite_log(
                profile=profile,
                model=model,
                status_code=200,
                error_message=None,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
            )
            return result, None
        error_text = response.text[:2000]
        await _awrite_log(
            profile=profile,
            model=model,
            status_code=response.status_code,
            error_message=error_text,
            latency_ms=latency_ms,
        )
        last_error = OpenRouterAPIError(
            _("OpenRouter returned HTTP %(status)s: %(error)s")
            % {"status": response.status_code, "error": error_text},
            status_code=response.status_code,
        )
        if response.status_code >= 500 and attempt < int(cfg.max_retries):
            continue
        if _should_fallback(response.status_code):
            return None, last_error
        raise last_error
    return None, last_error


async def _attempt_stream_async(
    http: httpx.AsyncClient,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> AsyncIterator[ChatChunk]:
    last_error: Exception | None = None
    limiter = get_limiter()
    emitted = False
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            async with limiter.aslot(cfg.max_parallel_requests):
                async with http.stream(
                    "POST", url, json=payload, headers=_headers(cfg)
                ) as response:
                    if response.status_code != 200:
                        raw = await response.aread()
                        error_text = raw.decode("utf-8", errors="replace")[:2000]
                        latency_ms = int((time.perf_counter() - started) * 1000)
                        await _awrite_log(
                            profile=profile,
                            model=model,
                            status_code=response.status_code,
                            error_message=error_text,
                            latency_ms=latency_ms,
                        )
                        last_error = OpenRouterAPIError(
                            _("OpenRouter returned HTTP %(status)s: %(error)s")
                            % {"status": response.status_code, "error": error_text},
                            status_code=response.status_code,
                        )
                        if response.status_code >= 500 and attempt < int(cfg.max_retries):
                            continue
                        raise last_error
                    async for chunk in _consume_sse_async(
                        response.aiter_lines(),
                        profile=profile,
                        model=model,
                        started=started,
                    ):
                        if not chunk.done:
                            emitted = True
                        yield chunk
                    return
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await _awrite_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if emitted or attempt >= int(cfg.max_retries):
                raise last_error from exc
            continue
    if last_error is not None:
        raise last_error
    raise OpenRouterAPIError(_("All models failed without a specific error."))


async def _consume_sse_async(
    lines: AsyncIterator[str],
    *,
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
) -> AsyncIterator[ChatChunk]:
    parts: list[str] = []
    model_used = model.model_id
    usage: dict[str, Any] = {}
    last_event: dict[str, Any] = {}
    try:
        async for line in lines:
            decoded = _decode_sse_line(line)
            if decoded is True:
                break
            if not isinstance(decoded, dict):
                continue
            event = decoded
            if event.get("error"):
                raise _sse_error(event)
            last_event = event
            if event.get("model"):
                model_used = str(event["model"])
            event_usage = event.get("usage")
            if isinstance(event_usage, dict):
                usage = event_usage
            delta = _extract_delta(event)
            if delta:
                parts.append(delta)
                yield ChatChunk(
                    delta=delta,
                    content="".join(parts),
                    model_used=model_used,
                    raw=event,
                )
    except OpenRouterAPIError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        status = exc.status_code or 500
        await _awrite_log(
            profile=profile,
            model=model,
            status_code=status,
            error_message=str(exc),
            latency_ms=latency_ms,
        )
        raise
    latency_ms = int((time.perf_counter() - started) * 1000)
    result = _result_from_sse("".join(parts), usage, model, model_used, latency_ms, last_event)
    await _awrite_log(
        profile=profile,
        model=model,
        status_code=200,
        error_message=None,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        latency_ms=latency_ms,
    )
    yield ChatChunk(
        delta="",
        content=result.content,
        model_used=result.model_used,
        done=True,
        result=result,
        raw=last_event,
    )


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
) -> Iterator[ChatChunk]:
    """Фасад SSE: for chunk in stream("chat", messages=[...])."""
    if messages is None:
        raise TypeError("stream() missing required argument: 'messages'")
    yield from OpenRouterClient(profile_name).stream(messages, **overrides)


async def astream(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> AsyncIterator[ChatChunk]:
    """Асинхронный фасад SSE, зеркало stream()."""
    if messages is None:
        raise TypeError("astream() missing required argument: 'messages'")
    async for chunk in AsyncOpenRouterClient(profile_name).stream(messages, **overrides):
        yield chunk
