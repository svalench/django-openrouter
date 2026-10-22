"""Синхронный и асинхронный клиенты OpenRouter (Chat Completions)."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import random
import threading
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
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, BinaryIO
from urllib.parse import unquote_to_bytes

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
    OpenRouterTimeout,
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
    ProfileKind,
    RequestLog,
    UsageProfile,
)
from django_openrouter.rules import assert_model_allowed, check_limits, reserve_request

if TYPE_CHECKING:
    from django.core.files.base import File

    from django_openrouter.transcription import TranscriptionResult

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
        "reasoning",
    }
)
# Параметры вызова библиотеки: в тело OpenRouter не попадают.
_CALL_OPTION_KEYS = frozenset({"total_timeout", "deadline_s", "request_timeout"})
_MANAGED_KEYS = frozenset({"stream", "max_tokens", "temperature", "model", "stream_options"})
# OpenRouter-ошибка в теле 200 без кода — считаем upstream-сбоем, чтобы сработал fallback.
_BODY_ERROR_STATUS = 502
_ERROR_TEXT_LIMIT = 2000
_DEFAULT_RETRY_BACKOFF = 0.5
_MAX_RETRY_DELAY = 30.0
# Скачивание картинки по http(s) из ответа модели. Data URL в сеть не уходит.
_MAX_REMOTE_IMAGE_BYTES = 25 * 1024 * 1024
_IMAGE_PART_TYPES = frozenset({"image_url", "image", "output_image"})


class _UsageMissing(OpenRouterAPIError):
    """Ответ получен (и оплачен), но без usage: без retry/fallback, резерв не закрываем."""


@dataclass(frozen=True)
class GeneratedImage:
    """Картинка из ответа модели.

    data URL декодируется в data и mime, url остаётся пустым (сама строка
    data URL уже содержит байты и не дублируется). У http(s) URL байты
    подгружаются отдельным GET без ключа OpenRouter; если скачать не вышло,
    data остаётся None, а url сохраняется.
    """

    data: bytes | None
    mime: str | None
    url: str | None


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
    images: list[GeneratedImage] = field(default_factory=list)
    incomplete: bool = False


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
    images: list[GeneratedImage] | None = None,
    incomplete: bool = False,
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
        images=list(images or []),
        incomplete=incomplete,
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
        images=_images_from_message(message),
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
        self.images: list[GeneratedImage] = []
        self._image_keys: set[tuple[object, ...]] = set()
        self.model_used = model.model_id
        self.usage: dict[str, Any] = {}
        self.last_event: dict[str, Any] = {}
        self.finish_reason: str | None = None
        self.finished = False

    @property
    def has_content(self) -> bool:
        return bool(self.parts)

    def has_output(self) -> bool:
        """Уже есть текст, картинка, tool call, reasoning или usage."""
        return bool(self.parts or self.reasoning or self.tool_calls or self.images or self.usage)

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
        self._add_images(delta)
        message = choice.get("message")
        if isinstance(message, Mapping):
            self._add_images(message)
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

    def _add_images(self, node: Mapping[str, Any]) -> None:
        for image in _images_from_message(node):
            key = _image_identity(image)
            if key in self._image_keys:
                continue
            self._image_keys.add(key)
            self.images.append(image)

    def result(self, *, partial: bool = False, incomplete: bool = False) -> ChatResult:
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
            images=list(self.images),
            incomplete=incomplete,
        )


@dataclass(frozen=True)
class _CallClock:
    """Idle-таймаут между байтами и абсолютный дедлайн вызова (monotonic)."""

    idle_s: float
    deadline_at: float | None

    def due(self) -> bool:
        return self.deadline_at is not None and time.monotonic() >= self.deadline_at

    def bounds_httpx_timeout(self) -> bool:
        """True, если ближайший httpx-таймаут упирается в дедлайн, а не в idle."""
        if self.deadline_at is None:
            return False
        return self.deadline_at - time.monotonic() < self.idle_s

    def httpx_timeout(self) -> httpx.Timeout:
        """Таймаут одного чтения: не длиннее idle и не длиннее остатка дедлайна."""
        idle = self.idle_s
        if self.deadline_at is None:
            return httpx.Timeout(idle)
        remaining = self.deadline_at - time.monotonic()
        if remaining <= 0:
            remaining = 0.001
        bound = min(idle, remaining)
        return httpx.Timeout(connect=bound, read=bound, write=bound, pool=bound)


def _positive_seconds(value: object, name: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            _("%(name)s must be a positive number of seconds.") % {"name": name}
        ) from exc
    if number != number or number <= 0 or number == float("inf"):
        raise ConfigurationError(
            _("%(name)s must be a positive number of seconds.") % {"name": name}
        )
    return number


def _resolve_call_clock(
    overrides: dict[str, Any], profile: UsageProfile, cfg: RuntimeConfig
) -> _CallClock:
    """Снимает таймауты вызова с overrides, чтобы они не ушли в JSON OpenRouter."""
    deadline_s = overrides.pop("deadline_s", None)
    total = overrides.pop("total_timeout", None)
    if deadline_s is not None and total is not None:
        if _positive_seconds(deadline_s, "deadline_s") != _positive_seconds(
            total, "total_timeout"
        ):
            raise ConfigurationError(
                _("total_timeout and deadline_s are the same deadline; pass one value.")
            )
    chosen = deadline_s if deadline_s is not None else total
    if chosen is None:
        chosen = profile.total_timeout if profile.total_timeout is not None else cfg.total_timeout
    idle = overrides.pop("request_timeout", None)
    if idle is None:
        idle = (
            profile.request_timeout if profile.request_timeout is not None else cfg.request_timeout
        )
    total_s = None if chosen is None else _positive_seconds(chosen, "total_timeout")
    deadline_at = None if total_s is None else time.monotonic() + total_s
    return _CallClock(
        idle_s=_positive_seconds(idle, "request_timeout"),
        deadline_at=deadline_at,
    )


def _timeout_exception(state: _SSEState) -> OpenRouterTimeout:
    partial = state.result(partial=True, incomplete=True) if state.has_output() else None
    return OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."), partial=partial)


class _ResponseDeadline:
    """По дедлайну закрывает только этот response, не общий httpx-клиент."""

    def __init__(self, response: httpx.Response, clock: _CallClock) -> None:
        self.clock = clock
        self.fired = False
        self._response = response
        self._timer: threading.Timer | None = None
        if clock.deadline_at is None:
            return
        delay = clock.deadline_at - time.monotonic()
        if delay <= 0:
            self._close()
            return
        timer = threading.Timer(delay, self._close)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _close(self) -> None:
        # Флаг до close(): гонка с чтением всё равно считается дедлайном.
        self.fired = True
        try:
            self._response.close()
        except Exception:
            logger.debug("deadline response close failed", exc_info=True)

    def cancel(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def due(self) -> bool:
        return self.fired or self.clock.due()

    def ensure(self, state: _SSEState) -> None:
        if self.due():
            self._close()
            raise _timeout_exception(state)


def _image_identity(image: GeneratedImage) -> tuple[object, ...]:
    if image.url:
        return ("url", image.url)
    return ("data", image.mime, image.data)


def _image_from_url(url: str) -> GeneratedImage:
    if url.startswith("data:"):
        header, separator, payload = url.partition(",")
        if not separator:
            return GeneratedImage(data=None, mime=None, url=None)
        meta = header[5:]
        mime = meta.split(";", 1)[0].strip() or "application/octet-stream"
        if "base64" in meta:
            try:
                data: bytes | None = base64.b64decode("".join(payload.split()), validate=True)
            except (ValueError, binascii.Error):
                data = None
        else:
            data = unquote_to_bytes(payload)
        if data == b"":
            data = None
        # url не храним: data URL уже содержит байты и может быть на мегабайты.
        return GeneratedImage(data=data, mime=mime, url=None)
    if url.startswith(("http://", "https://")):
        return GeneratedImage(data=None, mime=None, url=url)
    return GeneratedImage(data=None, mime=None, url=None)


def _image_from_inline(inline: Mapping[str, Any]) -> GeneratedImage:
    mime_value = inline.get("mime_type") if "mime_type" in inline else inline.get("mime")
    mime = str(mime_value or "application/octet-stream")
    raw = inline.get("data")
    data: bytes | None
    if isinstance(raw, str) and raw:
        try:
            data = base64.b64decode("".join(raw.split()), validate=True)
        except (ValueError, binascii.Error):
            data = None
    else:
        data = None
    if data == b"":
        data = None
    return GeneratedImage(data=data, mime=mime, url=None)


def _url_of_image_item(item: Mapping[str, Any]) -> str | None:
    image_url = item.get("image_url")
    if isinstance(image_url, str) and image_url:
        return image_url
    if isinstance(image_url, Mapping):
        url = image_url.get("url")
        if isinstance(url, str) and url:
            return url
    if item.get("type") in _IMAGE_PART_TYPES:
        url = item.get("url")
        if isinstance(url, str) and url:
            return url
    return None


def _images_from_message(node: Mapping[str, Any]) -> list[GeneratedImage]:
    """Картинки из message.images и из частей content (data URL и http URL)."""
    blobs: list[object] = []
    images = node.get("images")
    if isinstance(images, list):
        blobs.extend(images)
    content = node.get("content")
    if isinstance(content, list):
        blobs.extend(part for part in content if isinstance(part, Mapping))
    found: list[GeneratedImage] = []
    seen: set[tuple[object, ...]] = set()
    for item in blobs:
        if not isinstance(item, Mapping):
            continue
        inline = item.get("inline_data")
        if isinstance(inline, Mapping) and "data" in inline:
            image = _image_from_inline(inline)
        else:
            url = _url_of_image_item(item)
            if not url:
                continue
            image = _image_from_url(url)
        key = _image_identity(image)
        if key in seen:
            continue
        seen.add(key)
        found.append(image)
    return found


def _read_body_sync(response: httpx.Response, guard: _ResponseDeadline, state: _SSEState) -> bytes:
    chunks: list[bytes] = []
    try:
        for chunk in response.iter_bytes():
            guard.ensure(state)
            chunks.append(chunk)
    except OpenRouterTimeout:
        raise
    except Exception as exc:
        if guard.due():
            raise _timeout_exception(state) from exc
        raise
    guard.ensure(state)
    return b"".join(chunks)


def _rehydrate(response: httpx.Response, raw: bytes) -> httpx.Response:
    return httpx.Response(
        status_code=response.status_code,
        headers=response.headers,
        content=raw,
        request=response.request,
    )


def _materialize_sync(
    http: httpx.Client, image: GeneratedImage, clock: _CallClock
) -> GeneratedImage:
    if image.data is not None or not image.url:
        return image
    if not image.url.startswith(("http://", "https://")) or clock.due():
        return image
    try:
        with http.stream(
            "GET", image.url, timeout=clock.httpx_timeout(), follow_redirects=True
        ) as response:
            if response.status_code != 200:
                logger.warning("Generated image URL returned HTTP %s", response.status_code)
                return image
            mime = response.headers.get("content-type", "").split(";", 1)[0].strip() or image.mime
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > _MAX_REMOTE_IMAGE_BYTES:
                logger.warning("Generated image URL exceeds the size cap: %s", image.url)
                return image
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                if clock.due():
                    return image
                total += len(chunk)
                if total > _MAX_REMOTE_IMAGE_BYTES:
                    logger.warning("Generated image URL exceeds the size cap: %s", image.url)
                    return image
                chunks.append(chunk)
            return GeneratedImage(data=b"".join(chunks), mime=mime, url=image.url)
    except httpx.HTTPError:
        logger.warning("Failed to download generated image %s", image.url, exc_info=True)
        return image


def _materialize_all_sync(
    http: httpx.Client, images: list[GeneratedImage], clock: _CallClock
) -> list[GeneratedImage]:
    return [_materialize_sync(http, image, clock) for image in images]


async def _aclose_response(response: httpx.Response) -> None:
    try:
        await response.aclose()
    except Exception:
        logger.debug("deadline response close failed", exc_info=True)


async def _anext_with_deadline(
    agen: AsyncIterator[Any],
    clock: _CallClock,
    state: _SSEState,
    response: httpx.Response,
) -> Any:
    if clock.deadline_at is None:
        return await agen.__anext__()
    remaining = clock.deadline_at - time.monotonic()
    if remaining <= 0:
        await _aclose_response(response)
        raise _timeout_exception(state)
    try:
        return await asyncio.wait_for(agen.__anext__(), remaining)
    except TimeoutError as exc:
        # wait_for отменяет только это чтение. Клиент процесса не закрываем.
        await _aclose_response(response)
        raise _timeout_exception(state) from exc


async def _aread_body(response: httpx.Response, clock: _CallClock, state: _SSEState) -> bytes:
    chunks: list[bytes] = []
    agen = response.aiter_bytes().__aiter__()
    while True:
        try:
            chunk = await _anext_with_deadline(agen, clock, state, response)
        except StopAsyncIteration:
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def _aread_remote(response: httpx.Response, clock: _CallClock) -> bytes | None:
    """Тело картинки. None — дедлайн или размер больше лимита; вызов чата при этом жив."""
    chunks: list[bytes] = []
    total = 0
    agen = response.aiter_bytes().__aiter__()
    while True:
        if clock.due():
            await _aclose_response(response)
            return None
        try:
            if clock.deadline_at is None:
                chunk = await agen.__anext__()
            else:
                remaining = clock.deadline_at - time.monotonic()
                if remaining <= 0:
                    await _aclose_response(response)
                    return None
                chunk = await asyncio.wait_for(agen.__anext__(), remaining)
        except StopAsyncIteration:
            break
        except TimeoutError:
            await _aclose_response(response)
            return None
        total += len(chunk)
        if total > _MAX_REMOTE_IMAGE_BYTES:
            await _aclose_response(response)
            return None
        chunks.append(chunk)
    return b"".join(chunks)


async def _materialize_async(
    http: httpx.AsyncClient, image: GeneratedImage, clock: _CallClock
) -> GeneratedImage:
    if image.data is not None or not image.url:
        return image
    if not image.url.startswith(("http://", "https://")) or clock.due():
        return image
    try:
        async with http.stream(
            "GET", image.url, timeout=clock.httpx_timeout(), follow_redirects=True
        ) as response:
            if response.status_code != 200:
                logger.warning("Generated image URL returned HTTP %s", response.status_code)
                return image
            mime = response.headers.get("content-type", "").split(";", 1)[0].strip() or image.mime
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > _MAX_REMOTE_IMAGE_BYTES:
                logger.warning("Generated image URL exceeds the size cap: %s", image.url)
                return image
            raw = await _aread_remote(response, clock)
            if raw is None:
                logger.warning("Generated image URL was not fully downloaded: %s", image.url)
                return image
            return GeneratedImage(data=raw, mime=mime, url=image.url)
    except httpx.HTTPError:
        logger.warning("Failed to download generated image %s", image.url, exc_info=True)
        return image


async def _materialize_all_async(
    http: httpx.AsyncClient, images: list[GeneratedImage], clock: _CallClock
) -> list[GeneratedImage]:
    resolved: list[GeneratedImage] = []
    for image in images:
        resolved.append(await _materialize_async(http, image, clock))
    return resolved


def _want_sse(cfg: RuntimeConfig, overrides: Mapping[str, Any], *, force: bool = False) -> bool:
    """Нужен ли SSE: метод stream() или явный chat(stream=True)."""
    wanted = force or bool(overrides.get("stream", False))
    if wanted and not cfg.streaming_enabled:
        raise ConfigurationError(_("Streaming is disabled in admin settings."))
    return wanted


def _prepare(
    profile_name: str | None,
    overrides: dict[str, Any],
) -> tuple[RuntimeConfig, UsageProfile, list[OpenRouterModel], _CallClock]:
    """Конфиг, профиль и допустимая цепочка моделей. Резерв — на каждую попытку."""
    set_active_reservation(None)
    cfg = get_runtime_config()
    if not cfg.enabled:
        raise OpenRouterDisabled(_("OpenRouter is disabled in admin settings."))
    if not cfg.api_key:
        raise ConfigurationError(_("OpenRouter API key is not configured."))
    if "models" in overrides:
        raise ConfigurationError(
            _("models overrides are not allowed; configure fallback models in the usage profile.")
        )
    snapshot = _resolve_profile(cfg, profile_name)
    profile = UsageProfile.objects.select_related("model").get(pk=snapshot.pk)
    if profile.kind != ProfileKind.CHAT:
        raise ConfigurationError(
            _("Profile %(name)r is a %(kind)s profile; use transcribe() for speech-to-text.")
            % {"name": profile.name, "kind": profile.kind}
        )
    check_limits(profile)
    clock = _resolve_call_clock(overrides, profile, cfg)
    chain = _allowed_models(profile, _model_chain(profile, overrides))
    return cfg, profile, chain, clock


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


def _unwrap_result(result: ChatResult) -> ChatResult:
    if result.incomplete:
        raise OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."), partial=result)
    return result


def _collect_result(chunks: Iterator[ChatChunk]) -> ChatResult:
    for chunk in chunks:
        if chunk.done and chunk.result is not None:
            return _unwrap_result(chunk.result)
    raise OpenRouterAPIError(_("All models failed without a specific error."))


async def _acollect_result(chunks: AsyncIterator[ChatChunk]) -> ChatResult:
    async for chunk in chunks:
        if chunk.done and chunk.result is not None:
            return _unwrap_result(chunk.result)
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

    def transcribe(
        self,
        audio: bytes | bytearray | File | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """Транскрипция аудио профилем этого клиента."""
        from django_openrouter.transcription import transcribe

        result = transcribe(
            audio,
            filename=filename,
            content_type=content_type,
            profile=self.profile_name,
            model=model,
            language=language,
            prompt=prompt,
        )
        return result

    def generate_image(
        self, prompt: str, *, model: str | None = None, **overrides: Any
    ) -> ChatResult:
        """Генерация картинки профилем клиента. modalities по умолчанию image+text."""
        return generate_image(prompt, model=model, profile=self.profile_name, **overrides)

    def _run(
        self, messages: ChatMessages, overrides: dict[str, Any], *, emit: bool
    ) -> Generator[ChatChunk, None, None]:
        cfg, profile, chain, clock = _prepare(self.profile_name, overrides)
        sse = _want_sse(cfg, overrides, force=emit)
        with closing(
            _iter_chain_sync(cfg, profile, chain, messages, overrides, clock, sse=sse, emit=emit)
        ) as chunks:
            yield from chunks


def _iter_chain_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    messages: ChatMessages,
    overrides: dict[str, Any],
    clock: _CallClock,
    *,
    sse: bool,
    emit: bool,
) -> Generator[ChatChunk, None, None]:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for model in chain:
        if clock.due():
            raise OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."))
        if credits_exhausted and not model.is_free:
            continue
        payload = _build_payload(profile, model, messages, overrides, stream=sse)
        emitted = False
        try:
            with closing(
                _attempt_sync(cfg, profile, model, payload, clock, sse=sse, emit=emit)
            ) as it:
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


def _emit_timeout_sync(
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
    state: _SSEState,
    exc: OpenRouterTimeout,
) -> Generator[ChatChunk, None, None]:
    """499 в логе. Частичный ответ — финальный чанк, пустой — исключение наружу."""
    dispatch_log(
        _record(
            profile,
            model,
            started,
            status_code=CLIENT_CLOSED_STATUS,
            error_message=str(exc)[:_ERROR_TEXT_LIMIT],
            result=exc.partial,
        )
    )
    if exc.partial is not None:
        yield _done_chunk(exc.partial, state.last_event)
        return
    raise exc


def _attempt_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
    clock: _CallClock,
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
        if clock.due():
            raise OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."))
        _activate_reservation(profile, reserve_request(profile, model, image_count=image_count))
        started = time.perf_counter()
        retry_after: str | None = None
        state = _SSEState(model, started)
        deadline_bound = clock.bounds_httpx_timeout()
        parsed: ChatResult | None = None
        try:
            with limiter.slot(cfg.max_parallel_requests):
                with http.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=_headers(cfg),
                    timeout=clock.httpx_timeout(),
                ) as response:
                    # Таймер закрывает только этот response. Общий клиент не трогаем.
                    guard = _ResponseDeadline(response, clock)
                    try:
                        if response.status_code != 200:
                            retry_after = response.headers.get("Retry-After")
                            raw = _read_body_sync(response, guard, state)
                            raise _http_error(
                                response.status_code, raw.decode("utf-8", errors="replace")
                            )
                        if not sse:
                            raw = _read_body_sync(response, guard, state)
                            parsed = _parse_json_response(
                                _rehydrate(response, raw), model, started
                            )
                        else:
                            parsed = None
                            try:
                                for line in response.iter_lines():
                                    guard.ensure(state)
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
                            except OpenRouterTimeout:
                                raise
                            except Exception as exc:
                                if guard.due():
                                    raise _timeout_exception(state) from exc
                                raise
                            if guard.due() and not state.finished:
                                raise _timeout_exception(state)
                    finally:
                        guard.cancel()
            if not sse:
                assert parsed is not None
                result = replace(
                    parsed,
                    images=_materialize_all_sync(http, parsed.images, clock),
                    latency_ms=_elapsed_ms(started),
                )
                dispatch_log(_record(profile, model, started, status_code=200, result=result))
                yield _done_chunk(result, result.raw)
                return
            state.images = _materialize_all_sync(http, state.images, clock)
            result = state.result()
            dispatch_log(_record(profile, model, started, status_code=200, result=result))
            yield _done_chunk(result, state.last_event)
            return
        except OpenRouterTimeout as exc:
            yield from _emit_timeout_sync(profile, model, started, state, exc)
            return
        except httpx.TimeoutException as exc:
            if deadline_bound or clock.due():
                timeout_exc = _timeout_exception(state)
                yield from _emit_timeout_sync(profile, model, started, state, timeout_exc)
                return
            error = OpenRouterAPIError(str(exc), status_code=None)
            dispatch_log(_record(profile, model, started, status_code=0, error_message=str(exc)))
            if (emit and state.has_content) or attempt >= retries:
                raise error from exc
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
        if clock.deadline_at is not None:
            delay = min(delay, max(0.0, clock.deadline_at - time.monotonic()))
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

    async def transcribe(
        self,
        audio: bytes | bytearray | File | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> TranscriptionResult:
        """Асинхронная транскрипция аудио профилем этого клиента."""
        from django_openrouter.transcription import atranscribe

        result = await atranscribe(
            audio,
            filename=filename,
            content_type=content_type,
            profile=self.profile_name,
            model=model,
            language=language,
            prompt=prompt,
        )
        return result

    async def generate_image(
        self, prompt: str, *, model: str | None = None, **overrides: Any
    ) -> ChatResult:
        """Асинхронная генерация картинки профилем клиента."""
        return await agenerate_image(prompt, model=model, profile=self.profile_name, **overrides)

    async def _run(
        self, messages: ChatMessages, overrides: dict[str, Any], *, emit: bool
    ) -> AsyncGenerator[ChatChunk, None]:
        set_active_reservation(None)
        cfg, profile, chain, clock = await sync_to_async(_prepare, thread_sensitive=True)(
            self.profile_name, overrides
        )
        sse = _want_sse(cfg, overrides, force=emit)
        async with aclosing(
            _aiter_chain(cfg, profile, chain, messages, overrides, clock, sse=sse, emit=emit)
        ) as chunks:
            async for chunk in chunks:
                yield chunk


async def _aiter_chain(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    messages: ChatMessages,
    overrides: dict[str, Any],
    clock: _CallClock,
    *,
    sse: bool,
    emit: bool,
) -> AsyncGenerator[ChatChunk, None]:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for model in chain:
        if clock.due():
            raise OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."))
        if credits_exhausted and not model.is_free:
            continue
        payload = _build_payload(profile, model, messages, overrides, stream=sse)
        emitted = False
        try:
            async with aclosing(
                _attempt_async(cfg, profile, model, payload, clock, sse=sse, emit=emit)
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


async def _emit_timeout_async(
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
    state: _SSEState,
    exc: OpenRouterTimeout,
) -> AsyncGenerator[ChatChunk, None]:
    await adispatch_log(
        _record(
            profile,
            model,
            started,
            status_code=CLIENT_CLOSED_STATUS,
            error_message=str(exc)[:_ERROR_TEXT_LIMIT],
            result=exc.partial,
        )
    )
    if exc.partial is not None:
        yield _done_chunk(exc.partial, state.last_event)
        return
    raise exc


async def _attempt_async(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
    clock: _CallClock,
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
        if clock.due():
            raise OpenRouterTimeout(_("OpenRouter call exceeded the total timeout."))
        reservation = await sync_to_async(reserve_request, thread_sensitive=True)(
            profile, model, image_count=image_count
        )
        _activate_reservation(profile, reservation)
        started = time.perf_counter()
        retry_after: str | None = None
        state = _SSEState(model, started)
        deadline_bound = clock.bounds_httpx_timeout()
        parsed: ChatResult | None = None
        try:
            async with limiter.aslot(cfg.max_parallel_requests):
                async with http.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=_headers(cfg),
                    timeout=clock.httpx_timeout(),
                ) as response:
                    if response.status_code != 200:
                        retry_after = response.headers.get("Retry-After")
                        raw = await _aread_body(response, clock, state)
                        raise _http_error(
                            response.status_code, raw.decode("utf-8", errors="replace")
                        )
                    if not sse:
                        raw = await _aread_body(response, clock, state)
                        parsed = _parse_json_response(_rehydrate(response, raw), model, started)
                    else:
                        agen = response.aiter_lines().__aiter__()
                        try:
                            while True:
                                try:
                                    line = await _anext_with_deadline(agen, clock, state, response)
                                except StopAsyncIteration:
                                    break
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
                        if clock.due() and not state.finished:
                            await _aclose_response(response)
                            raise _timeout_exception(state)
            if not sse:
                assert parsed is not None
                result = replace(
                    parsed,
                    images=await _materialize_all_async(http, parsed.images, clock),
                    latency_ms=_elapsed_ms(started),
                )
                await adispatch_log(
                    _record(profile, model, started, status_code=200, result=result)
                )
                yield _done_chunk(result, result.raw)
                return
            state.images = await _materialize_all_async(http, state.images, clock)
            result = state.result()
            await adispatch_log(_record(profile, model, started, status_code=200, result=result))
            yield _done_chunk(result, state.last_event)
            return
        except OpenRouterTimeout as exc:
            async for chunk in _emit_timeout_async(profile, model, started, state, exc):
                yield chunk
            return
        except httpx.TimeoutException as exc:
            if deadline_bound or clock.due():
                timeout_exc = _timeout_exception(state)
                async for chunk in _emit_timeout_async(
                    profile, model, started, state, timeout_exc
                ):
                    yield chunk
                return
            error = OpenRouterAPIError(str(exc), status_code=None)
            await adispatch_log(
                _record(profile, model, started, status_code=0, error_message=str(exc))
            )
            if (emit and state.has_content) or attempt >= retries:
                raise error from exc
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
        if clock.deadline_at is not None:
            delay = min(delay, max(0.0, clock.deadline_at - time.monotonic()))
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


def _image_prompt_messages(prompt: str) -> list[dict[str, str]]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ConfigurationError(_("Image prompt must be a non-empty string."))
    return [{"role": "user", "content": prompt}]


def generate_image(
    prompt: str,
    *,
    model: str | None = None,
    profile: str | None = None,
    **overrides: Any,
) -> ChatResult:
    """Картинка через chat-completions. По умолчанию modalities=["image", "text"]."""
    overrides.setdefault("modalities", ["image", "text"])
    if model is not None:
        overrides["model"] = model
    return chat(profile, messages=_image_prompt_messages(prompt), **overrides)


async def agenerate_image(
    prompt: str,
    *,
    model: str | None = None,
    profile: str | None = None,
    **overrides: Any,
) -> ChatResult:
    """Асинхронное зеркало generate_image()."""
    overrides.setdefault("modalities", ["image", "text"])
    if model is not None:
        overrides["model"] = model
    return await achat(profile, messages=_image_prompt_messages(prompt), **overrides)
