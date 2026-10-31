"""Речь-в-текст: POST /api/v1/audio/transcriptions.

Библиотека не тянет ffmpeg. Вызывающий код передаёт уже поддерживаемый
контейнер (webm, ogg, mp3, wav, m4a, flac, aac) либо подключает
OPENROUTER['AUDIO_PREPARE'] — функцию, которая вернёт (bytes, filename, content_type).
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, BinaryIO

import httpx
from asgiref.sync import sync_to_async
from django.core.files.base import File
from django.core.files.uploadedfile import UploadedFile
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from django_openrouter.client import (
    _BODY_ERROR_STATUS,
    _CREDITS_EXHAUSTED_STATUS,
    _ERROR_TEXT_LIMIT,
    _elapsed_ms,
    _error_from_body,
    _headers,
    _http_error,
    _is_retryable,
    _retry_delay,
    _should_fallback,
    _to_decimal,
    _UsageMissing,
    compute_cost,
)
from django_openrouter.concurrency import get_limiter
from django_openrouter.config import RuntimeConfig, get_runtime_config, openrouter_setting
from django_openrouter.exceptions import (
    AudioTooLarge,
    ConfigurationError,
    ModelDisabled,
    OpenRouterAPIError,
    OpenRouterDisabled,
    UnsupportedAudioFormat,
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
from django_openrouter.models import OpenRouterModel, ProfileKind, RequestLog, UsageProfile
from django_openrouter.rules import (
    assert_model_allowed,
    check_limits,
    maximum_transcription_cost,
    reserve_request,
)
from django_openrouter.tracing import (
    note_profile,
    note_request_model,
    open_call,
    remember_output,
    trace_attempt,
)

# OpenRouter принимает эти контейнеры. Opus внутри webm/ogg — дело вызывающего кода.
_FORMAT_BY_TYPE = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "application/ogg": "ogg",
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/aac": "aac",
    "audio/aacp": "aac",
}
_FORMAT_BY_EXT = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".mpeg": "mp3",
    ".flac": "flac",
    ".m4a": "m4a",
    ".mp4": "m4a",
    ".ogg": "ogg",
    ".oga": "ogg",
    ".webm": "webm",
    ".aac": "aac",
}
_SUPPORTED_FORMATS = frozenset(_FORMAT_BY_EXT.values())
# Совпадает с multipart-лимитом OpenRouter. Профиль может поднять или опустить его.
DEFAULT_MAX_AUDIO_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class TranscriptionResult:
    """Результат POST /audio/transcriptions."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    duration_seconds: Decimal | None
    cost_usd: Decimal
    catalog_cost_usd: Decimal | None
    model_used: str
    latency_ms: int
    raw: dict[str, Any]


def transcribe(
    audio: bytes | bytearray | File | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    trace_id: str | None = None,
    trace: dict[str, Any] | None = None,
) -> TranscriptionResult:
    """Синхронная транскрипция. Конфиг: БД → settings → env через get_runtime_config()."""
    with open_call(
        "transcription",
        profile_name=profile,
        overrides=_call_options(session_id, metadata, trace_id, trace),
        prompt_text=prompt,
    ):
        prepared = _prepare_call(
            profile,
            audio,
            filename=filename,
            content_type=content_type,
            model=model,
            language=language,
            prompt=prompt,
        )
        return _run_sync(*prepared)


async def atranscribe(
    audio: bytes | bytearray | File | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    trace_id: str | None = None,
    trace: dict[str, Any] | None = None,
) -> TranscriptionResult:
    """Асинхронное зеркало transcribe()."""
    with open_call(
        "transcription",
        profile_name=profile,
        overrides=_call_options(session_id, metadata, trace_id, trace),
        prompt_text=prompt,
    ):
        prepared = await sync_to_async(_prepare_call, thread_sensitive=True)(
            profile,
            audio,
            filename=filename,
            content_type=content_type,
            model=model,
            language=language,
            prompt=prompt,
        )
        return await _run_async(*prepared)


def _call_options(
    session_id: str | None,
    metadata: dict[str, Any] | None,
    trace_id: str | None,
    trace: dict[str, Any] | None,
) -> dict[str, Any]:
    """Только явно переданные ключи, чтобы пустой аргумент не затёр bound_session."""
    options: dict[str, Any] = {}
    if session_id is not None:
        options["session_id"] = session_id
    if metadata is not None:
        options["metadata"] = metadata
    if trace_id is not None:
        options["trace_id"] = trace_id
    if trace is not None:
        options["trace"] = trace
    return options


def _prepare_call(
    profile_name: str | None,
    audio: bytes | bytearray | File | BinaryIO,
    *,
    filename: str | None,
    content_type: str | None,
    model: str | None,
    language: str | None,
    prompt: str | None,
) -> tuple[
    RuntimeConfig,
    UsageProfile,
    list[OpenRouterModel],
    str,
    str,
    str | None,
    str | None,
]:
    set_active_reservation(None)
    cfg = get_runtime_config()
    if not cfg.enabled:
        raise OpenRouterDisabled(_("OpenRouter is disabled in admin settings."))
    if not cfg.api_key:
        raise ConfigurationError(_("OpenRouter API key is not configured."))
    usage_profile = _load_transcription_profile(cfg, profile_name)
    note_profile(usage_profile.name)
    check_limits(usage_profile)
    chain = _transcription_chain(usage_profile, model)
    if chain:
        note_request_model(chain[0].model_id)
    raw, resolved_name, resolved_type = _coerce_audio(audio, filename, content_type)
    raw, resolved_name, resolved_type = _apply_audio_hook(raw, resolved_name, resolved_type)
    _check_size(usage_profile, raw)
    audio_format = resolve_audio_format(resolved_name, resolved_type)
    chosen_language = _normalize_language(
        language if language is not None else usage_profile.language
    )
    chosen_prompt = prompt.strip() if isinstance(prompt, str) and prompt.strip() else None
    encoded = base64.b64encode(raw).decode("ascii")
    return cfg, usage_profile, chain, encoded, audio_format, chosen_language, chosen_prompt


def _load_transcription_profile(cfg: RuntimeConfig, profile_name: str | None) -> UsageProfile:
    name = profile_name or cfg.default_transcription_profile_name
    if not name:
        raise ConfigurationError(
            _("No transcription profile specified and default_transcription_profile is not set.")
        )
    snapshot = cfg.profiles.get(name)
    if snapshot is None:
        raise ConfigurationError(
            _("Usage profile %(name)r is not found or inactive.") % {"name": name}
        )
    if snapshot.kind != ProfileKind.TRANSCRIPTION:
        raise ConfigurationError(
            _("Profile %(name)r is not a transcription profile.") % {"name": name}
        )
    return UsageProfile.objects.select_related("model").get(pk=snapshot.pk)


def _transcription_chain(profile: UsageProfile, model_id: str | None) -> list[OpenRouterModel]:
    chain = list(profile.ordered_models())
    if model_id:
        overridden = next((item for item in chain if item.model_id == model_id), None)
        if overridden is None:
            raise ConfigurationError(
                _("Model %(model_id)r is not configured for profile %(name)r.")
                % {"model_id": model_id, "name": profile.name}
            )
        chain = [overridden] + [item for item in chain if item.pk != overridden.pk]
    allowed: list[OpenRouterModel] = []
    for item in chain:
        try:
            assert_model_allowed(profile, item)
        except ModelDisabled:
            continue
        allowed.append(item)
    if not chain:
        raise ConfigurationError(
            _("Profile %(name)r has no models configured.") % {"name": profile.name}
        )
    if not allowed:
        raise ModelDisabled(
            _("No allowed models left for profile %(name)r.") % {"name": profile.name}
        )
    return allowed


def _coerce_audio(
    audio: bytes | bytearray | File | BinaryIO,
    filename: str | None,
    content_type: str | None,
) -> tuple[bytes, str, str]:
    if isinstance(audio, UploadedFile):
        if filename is None:
            filename = audio.name
        if content_type is None:
            content_type = audio.content_type
        data = audio.read()
    elif isinstance(audio, File):
        if filename is None:
            filename = audio.name
        data = audio.read()
    elif isinstance(audio, (bytes, bytearray)):
        data = bytes(audio)
    else:
        data = audio.read()
    if isinstance(data, str):
        data = data.encode()
    if not isinstance(data, (bytes, bytearray)):
        raise ConfigurationError(_("Audio payload could not be read."))
    payload = bytes(data)
    if not payload:
        raise ConfigurationError(_("Audio payload is empty."))
    return payload, filename or "", content_type or ""


def _apply_audio_hook(data: bytes, filename: str, content_type: str) -> tuple[bytes, str, str]:
    """Необязательный хук вызывающего кода. Библиотека сама формат не конвертирует."""
    dotted = str(openrouter_setting("AUDIO_PREPARE", "") or "")
    if not dotted:
        return data, filename, content_type
    callback = import_string(dotted)
    prepared = callback(data, filename=filename, content_type=content_type)
    if not isinstance(prepared, tuple) or len(prepared) != 3:
        raise ConfigurationError(_("AUDIO_PREPARE must return (bytes, filename, content_type)."))
    raw, name, mime = prepared
    if (
        not isinstance(raw, (bytes, bytearray))
        or not isinstance(name, str)
        or not isinstance(mime, str)
    ):
        raise ConfigurationError(_("AUDIO_PREPARE must return (bytes, filename, content_type)."))
    if not raw:
        raise ConfigurationError(_("Audio payload is empty."))
    return bytes(raw), name, mime


def _check_size(profile: UsageProfile, data: bytes) -> None:
    limit = (
        profile.max_audio_bytes if profile.max_audio_bytes is not None else DEFAULT_MAX_AUDIO_BYTES
    )
    if len(data) > limit:
        raise AudioTooLarge(
            _("Audio is %(size)s bytes; the limit is %(limit)s bytes.")
            % {"size": len(data), "limit": limit}
        )


def resolve_audio_format(filename: str, content_type: str) -> str:
    """Формат для input_audio.format. Неизвестный контейнер — UnsupportedAudioFormat."""
    mime = content_type.split(";", 1)[0].strip().lower()
    extension = ""
    if "." in filename:
        extension = filename[filename.rfind(".") :].lower()
    from_mime = _FORMAT_BY_TYPE.get(mime, "")
    from_ext = _FORMAT_BY_EXT.get(extension, "")
    audio_format = from_mime or from_ext
    if audio_format not in _SUPPORTED_FORMATS:
        raise UnsupportedAudioFormat(
            _(
                "Unsupported audio format (filename=%(filename)r, content_type=%(content_type)r). "
                "Send webm, ogg, mp3, wav, m4a, flac or aac, or set OPENROUTER['AUDIO_PREPARE']."
            )
            % {"filename": filename, "content_type": content_type}
        )
    return audio_format


def _normalize_language(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if len(normalized) != 2 or not normalized.isalpha():
        raise ConfigurationError(_("Transcription language must be an ISO-639-1 code."))
    return normalized


def _build_body(
    model: OpenRouterModel,
    encoded: str,
    audio_format: str,
    *,
    language: str | None,
    prompt: str | None,
    temperature: float | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model.model_id,
        "input_audio": {"data": encoded, "format": audio_format},
    }
    if language:
        body["language"] = language
    # OpenRouter на multipart игнорирует prompt; в JSON передаём, если вызывающий просил.
    if prompt:
        body["prompt"] = prompt
    if temperature is not None:
        body["temperature"] = temperature
    return body


def _usage_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    usage = payload.get("usage")
    if isinstance(usage, dict):
        return usage
    return {}


def _token_counts(usage: Mapping[str, Any]) -> tuple[int, int]:
    prompt_raw = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    completion_raw = usage.get("output_tokens", usage.get("completion_tokens", 0))
    try:
        prompt_tokens = int(prompt_raw or 0)
        completion_tokens = int(completion_raw or 0)
    except (TypeError, ValueError):
        return 0, 0
    return prompt_tokens, completion_tokens


def _usage_is_present(usage: Mapping[str, Any]) -> bool:
    if usage.get("cost") not in (None, ""):
        return True
    if usage.get("seconds") not in (None, ""):
        return True
    has_prompt = "prompt_tokens" in usage or "input_tokens" in usage
    has_completion = "completion_tokens" in usage or "output_tokens" in usage
    return has_prompt and has_completion


def _costs(
    model: OpenRouterModel, usage: Mapping[str, Any]
) -> tuple[Decimal, Decimal | None, int, int, Decimal | None]:
    prompt_tokens, completion_tokens = _token_counts(usage)
    seconds = _to_decimal(usage.get("seconds"))
    pricing = model.pricing or {}
    catalog: Decimal | None
    if model.context_length:
        cost, catalog = compute_cost(prompt_tokens, completion_tokens, pricing, usage.get("cost"))
        return cost, catalog, prompt_tokens, completion_tokens, seconds
    catalog = None
    if seconds is not None and pricing:
        prompt_price = _to_decimal(pricing.get("prompt")) or Decimal("0")
        request_price = _to_decimal(pricing.get("request")) or Decimal("0")
        catalog = prompt_price * seconds + request_price
    if usage.get("cost") not in (None, ""):
        api_cost = _to_decimal(usage.get("cost"))
        if api_cost is None or not api_cost.is_finite() or api_cost < 0:
            raise OpenRouterAPIError(_("OpenRouter reported invalid usage cost."))
        return api_cost, catalog, prompt_tokens, completion_tokens, seconds
    return catalog or Decimal("0"), catalog, prompt_tokens, completion_tokens, seconds


def _parse_transcription(
    response: httpx.Response, model: OpenRouterModel, started: float
) -> TranscriptionResult:
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
    text = payload.get("text")
    if not isinstance(text, str):
        raise OpenRouterAPIError(
            _("OpenRouter transcription response did not include text."),
            status_code=_BODY_ERROR_STATUS,
        )
    usage = _usage_mapping(payload)
    if has_active_budget_reservation() and not _usage_is_present(usage):
        raise _UsageMissing(
            _("OpenRouter omitted usage for a budgeted request; reservation remains pending.")
        )
    cost, catalog, prompt_tokens, completion_tokens, seconds = _costs(model, usage)
    return TranscriptionResult(
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration_seconds=seconds,
        cost_usd=cost,
        catalog_cost_usd=catalog,
        model_used=str(payload.get("model") or model.model_id),
        latency_ms=_elapsed_ms(started),
        raw=payload,
    )


def _reservation_cost(profile: UsageProfile, model: OpenRouterModel) -> Decimal | None:
    has_budget = profile.budget_usd_per_day is not None or profile.budget_usd_per_month is not None
    if not has_budget:
        return None
    return maximum_transcription_cost(model, max_audio_seconds=profile.max_audio_seconds)


def _success_record(
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
    result: TranscriptionResult,
) -> LogRecord:
    remember_output(text=result.text, model=result.model_used, finish_reason=None)
    return make_record(
        profile=profile,
        model=model,
        status_code=200,
        error_message=None,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        latency_ms=_elapsed_ms(started),
    )


def _failure_record(
    profile: UsageProfile,
    model: OpenRouterModel,
    started: float,
    *,
    status_code: int,
    error_message: str,
) -> LogRecord:
    return make_record(
        profile=profile,
        model=model,
        status_code=status_code,
        error_message=error_message[:_ERROR_TEXT_LIMIT],
        latency_ms=_elapsed_ms(started),
    )


def _activate(profile: UsageProfile, reservation: RequestLog | None) -> None:
    from django_openrouter.client import _activate_reservation

    _activate_reservation(profile, reservation)


def _run_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    encoded: str,
    audio_format: str,
    language: str | None,
    prompt: str | None,
) -> TranscriptionResult:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for fallback_index, model in enumerate(chain):
        if credits_exhausted and not model.is_free:
            continue
        try:
            return _attempt_sync(
                cfg,
                profile,
                model,
                encoded,
                audio_format,
                language=language,
                prompt=prompt,
                fallback_index=fallback_index,
            )
        except OpenRouterAPIError as exc:
            if isinstance(exc, _UsageMissing) or not _should_fallback(exc.status_code):
                raise
            last_error = exc
            credits_exhausted |= exc.status_code == _CREDITS_EXHAUSTED_STATUS
    raise last_error or OpenRouterAPIError(_("All models failed without a specific error."))


def _attempt_sync(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    encoded: str,
    audio_format: str,
    *,
    language: str | None,
    prompt: str | None,
    fallback_index: int = 0,
) -> TranscriptionResult:
    http = get_sync_client()
    url = f"{cfg.base_url}/audio/transcriptions"
    limiter = get_limiter()
    retries = int(cfg.max_retries)
    body = _build_body(
        model,
        encoded,
        audio_format,
        language=language,
        prompt=prompt,
        temperature=profile.temperature,
    )
    estimated = _reservation_cost(profile, model)
    for attempt in range(retries + 1):
        with trace_attempt(
            model_id=model.model_id,
            fallback_index=fallback_index,
            retry_index=attempt,
            stream=False,
        ):
            _activate(profile, reserve_request(profile, model, estimated_cost=estimated))
            started = time.perf_counter()
            retry_after: str | None = None
            try:
                with limiter.slot(cfg.max_parallel_requests):
                    response = http.post(
                        url, json=body, headers=_headers(cfg), timeout=cfg.request_timeout
                    )
                    if response.status_code == 200:
                        result = _parse_transcription(response, model, started)
                        dispatch_log(_success_record(profile, model, started, result))
                        return result
                    retry_after = response.headers.get("Retry-After")
                    raise _http_error(response.status_code, response.text)
            except httpx.RequestError as exc:
                error = OpenRouterAPIError(str(exc), status_code=None)
                dispatch_log(
                    _failure_record(profile, model, started, status_code=0, error_message=str(exc))
                )
                if attempt >= retries:
                    raise error from exc
            except _UsageMissing:
                mark_usage_missing()
                raise
            except OpenRouterAPIError as exc:
                dispatch_log(
                    _failure_record(
                        profile,
                        model,
                        started,
                        status_code=exc.status_code or 0,
                        error_message=str(exc),
                    )
                )
                if attempt >= retries or not _is_retryable(exc.status_code):
                    raise
            except BaseException as exc:
                if _active_reservation_open():
                    dispatch_log(
                        _failure_record(
                            profile,
                            model,
                            started,
                            status_code=499,
                            error_message=f"attempt aborted: {type(exc).__name__}",
                        )
                    )
                raise
        delay = _retry_delay(attempt, retry_after)
        if delay:
            time.sleep(delay)
    raise OpenRouterAPIError(_("All models failed without a specific error."))


def _active_reservation_open() -> bool:
    return active_reservation_id() is not None


async def _run_async(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    chain: list[OpenRouterModel],
    encoded: str,
    audio_format: str,
    language: str | None,
    prompt: str | None,
) -> TranscriptionResult:
    last_error: OpenRouterAPIError | None = None
    credits_exhausted = False
    for fallback_index, model in enumerate(chain):
        if credits_exhausted and not model.is_free:
            continue
        try:
            return await _attempt_async(
                cfg,
                profile,
                model,
                encoded,
                audio_format,
                language=language,
                prompt=prompt,
                fallback_index=fallback_index,
            )
        except OpenRouterAPIError as exc:
            if isinstance(exc, _UsageMissing) or not _should_fallback(exc.status_code):
                raise
            last_error = exc
            credits_exhausted |= exc.status_code == _CREDITS_EXHAUSTED_STATUS
    raise last_error or OpenRouterAPIError(_("All models failed without a specific error."))


async def _attempt_async(
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    encoded: str,
    audio_format: str,
    *,
    language: str | None,
    prompt: str | None,
    fallback_index: int = 0,
) -> TranscriptionResult:
    http = get_async_client()
    url = f"{cfg.base_url}/audio/transcriptions"
    limiter = get_limiter()
    retries = int(cfg.max_retries)
    body = _build_body(
        model,
        encoded,
        audio_format,
        language=language,
        prompt=prompt,
        temperature=profile.temperature,
    )
    estimated = _reservation_cost(profile, model)
    for attempt in range(retries + 1):
        with trace_attempt(
            model_id=model.model_id,
            fallback_index=fallback_index,
            retry_index=attempt,
            stream=False,
        ):
            reservation = await sync_to_async(reserve_request, thread_sensitive=True)(
                profile, model, estimated_cost=estimated
            )
            _activate(profile, reservation)
            started = time.perf_counter()
            retry_after: str | None = None
            try:
                async with limiter.aslot(cfg.max_parallel_requests):
                    response = await http.post(
                        url, json=body, headers=_headers(cfg), timeout=cfg.request_timeout
                    )
                    if response.status_code == 200:
                        result = _parse_transcription(response, model, started)
                        await adispatch_log(_success_record(profile, model, started, result))
                        return result
                    retry_after = response.headers.get("Retry-After")
                    raise _http_error(response.status_code, response.text)
            except httpx.RequestError as exc:
                error = OpenRouterAPIError(str(exc), status_code=None)
                await adispatch_log(
                    _failure_record(profile, model, started, status_code=0, error_message=str(exc))
                )
                if attempt >= retries:
                    raise error from exc
            except _UsageMissing:
                await amark_usage_missing()
                raise
            except OpenRouterAPIError as exc:
                await adispatch_log(
                    _failure_record(
                        profile,
                        model,
                        started,
                        status_code=exc.status_code or 0,
                        error_message=str(exc),
                    )
                )
                if attempt >= retries or not _is_retryable(exc.status_code):
                    raise
            except BaseException as exc:
                if _active_reservation_open():
                    await adispatch_log(
                        _failure_record(
                            profile,
                            model,
                            started,
                            status_code=499,
                            error_message=f"attempt aborted: {type(exc).__name__}",
                        )
                    )
                raise
        delay = _retry_delay(attempt, retry_after)
        if delay:
            await asyncio.sleep(delay)
    raise OpenRouterAPIError(_("All models failed without a specific error."))
