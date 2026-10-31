"""Необязательные спаны OpenTelemetry для вызовов OpenRouter.

Зависимость только `opentelemetry-api` (extra `otel`). SDK и экспортёр
выбирает проект-хост. Если пакет не установлен, функции ничего не делают
и не импортируют OpenTelemetry. Спаны выключены, пока `OPENROUTER['OTEL']`
не равен true: наличие пакета само по себе трейсинг не включает.

Родительский спан — один на `chat` / `stream` / `transcribe` / `generate_image`
(и их async-зеркала). Дочерний — на каждую HTTP-попытку, включая retry и
fallback. Активный контекст не сбрасывается, поэтому спан встаёт под спан
Django или Celery, если хост уже его открыл.

Текст промпта и ответа в спан не пишется, пока не включён
`OPENROUTER['OTEL_CAPTURE_CONTENT']`. Хук `OTEL_CONTENT_REDACTOR` —
dotted path `callable(text, *, kind) -> str`, kind это `prompt` или
`completion`. Заголовки Authorization и API-ключ в атрибуты не попадают.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from django.dispatch import receiver
from django.test.signals import setting_changed

from django_openrouter.call_context import (
    CallGrouping,
    _call_grouping,
    coerce_metadata,
    coerce_session_id,
    coerce_trace_id,
    current_grouping,
    current_metadata,
    current_session_id,
    merge_metadata,
)
from django_openrouter.config import get_runtime_config, openrouter_setting
from django_openrouter.current_user import current_username
from django_openrouter.exceptions import ConfigurationError
from django_openrouter.signals import request_logged

logger = logging.getLogger("django_openrouter")

_GEN_AI_SYSTEM = "openrouter"
_CONTENT_LIMIT = 8192
_HOOK_INPUT_LIMIT = 32768
_API_KEY_MIN_LENGTH = 6
_ATTR_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,120}$")
_SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|api[_-]?key|secret|password|access[_-]?token|refresh[_-]?token|^token$)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+")

try:
    from opentelemetry import context as otel_context
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import SpanKind, Status, StatusCode, set_span_in_context

    _HAS_OTEL = True
except ImportError:  # pragma: no cover - ветка без установленного пакета
    otel_context = None  # type: ignore[assignment]
    otel_trace = None  # type: ignore[assignment]
    set_span_in_context = None  # type: ignore[assignment]
    SpanKind = None  # type: ignore[misc, assignment]
    Status = None  # type: ignore[misc, assignment]
    StatusCode = None  # type: ignore[misc, assignment]
    _HAS_OTEL = False

_enabled_cache: bool | None = None
_in_operation: ContextVar[bool] = ContextVar("django_openrouter_in_operation", default=False)
_operation_name: ContextVar[str] = ContextVar("django_openrouter_operation", default="chat")
_operation_span: ContextVar[Any] = ContextVar("django_openrouter_operation_span", default=None)
_attempt_span: ContextVar[Any] = ContextVar("django_openrouter_attempt_span", default=None)
_resolved_profile: ContextVar[str | None] = ContextVar(
    "django_openrouter_resolved_profile",
    default=None,
)
_captured_prompt: ContextVar[str | None] = ContextVar(
    "django_openrouter_captured_prompt",
    default=None,
)
_ttft_recorded: ContextVar[bool] = ContextVar("django_openrouter_ttft", default=False)


@dataclass
class _OutputNote:
    model: str
    finish_reason: str | None
    text: str


_output_note: ContextVar[_OutputNote | None] = ContextVar(
    "django_openrouter_output_note",
    default=None,
)


def otel_enabled() -> bool:
    """True только если пакет импортируется и OPENROUTER['OTEL'] включён.

    По умолчанию выключено, даже когда opentelemetry-api стоит в окружении.
    """
    global _enabled_cache
    if not _HAS_OTEL:
        return False
    if _enabled_cache is None:
        _enabled_cache = bool(openrouter_setting("OTEL", False))
    return _enabled_cache


def _get_tracer() -> Any:
    if otel_trace is None:
        raise RuntimeError("opentelemetry is not installed")
    return otel_trace.get_tracer("django_openrouter")


def _capture_content() -> bool:
    if not otel_enabled():
        return False
    return bool(openrouter_setting("OTEL_CAPTURE_CONTENT", False))


@receiver(setting_changed)
def _reset_otel_cache(*, setting: str, **kwargs: Any) -> None:
    global _enabled_cache
    if setting == "OPENROUTER" or setting.startswith("OPENROUTER_"):
        _enabled_cache = None


def _set(span: Any, key: str, value: Any) -> None:
    if span is None or not span.is_recording():
        return
    if value is None:
        return
    try:
        span.set_attribute(key, value)
    except Exception:
        logger.exception("OpenTelemetry attribute %s was rejected.", key)


def _mark_error(span: Any, exc: BaseException) -> None:
    if span is None or not span.is_recording() or Status is None or StatusCode is None:
        return
    try:
        span.record_exception(exc)
        message = str(exc).strip() or type(exc).__name__
        span.set_status(Status(StatusCode.ERROR, message[:500]))
    except Exception:
        logger.exception("OpenTelemetry error status was not recorded.")


def _scrub_text(text: str) -> str:
    cleaned = _BEARER.sub("Bearer [redacted]", text)
    try:
        api_key = get_runtime_config().api_key
    except Exception:
        api_key = ""
    if api_key and len(api_key) >= _API_KEY_MIN_LENGTH and api_key in cleaned:
        cleaned = cleaned.replace(api_key, "[redacted]")
    return cleaned


def _redact(text: str, kind: str) -> str:
    clipped = _scrub_text(text)[:_HOOK_INPUT_LIMIT]
    dotted = str(openrouter_setting("OTEL_CONTENT_REDACTOR", "") or "")
    if not dotted:
        return clipped[:_CONTENT_LIMIT]
    from django.utils.module_loading import import_string

    try:
        callback = import_string(dotted)
        redacted = callback(clipped, kind=kind)
    except Exception:
        logger.exception("OTEL_CONTENT_REDACTOR failed; content was not recorded.")
        return ""
    if not isinstance(redacted, str):
        logger.error("OTEL_CONTENT_REDACTOR must return str; content was not recorded.")
        return ""
    return _scrub_text(redacted)[:_CONTENT_LIMIT]


def _is_primitive(value: object) -> bool:
    if isinstance(value, bool) or isinstance(value, str):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return value == value and value not in (float("inf"), float("-inf"))
    return False


def _is_attribute_value(value: object) -> bool:
    if _is_primitive(value):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_primitive(item) for item in value)
    return False


def _coerce_trace_attributes(value: object) -> dict[str, Any]:
    """Атрибуты спана из аргумента `trace=`. Секреты по имени ключа отбрасываются."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError("trace must be a mapping of span attributes.")
    clean: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not _ATTR_NAME.fullmatch(key):
            raise ConfigurationError("trace attribute names must be dotted identifiers.")
        if _SENSITIVE_KEY.search(key):
            continue
        if not _is_attribute_value(item):
            raise ConfigurationError("trace attribute values must be strings, numbers or bools.")
        clean[key] = item
    return clean


def _scrub_metadata(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    clean: dict[str, Any] = {}
    for key, value in data.items():
        name = str(key)
        if _SENSITIVE_KEY.search(name):
            continue
        if isinstance(value, dict):
            nested = _scrub_metadata(value)
            if nested:
                clean[name] = nested
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str):
                clean[name] = _scrub_text(value)
            else:
                clean[name] = value
            continue
        try:
            clean[name] = _scrub_text(json.dumps(value, ensure_ascii=False))
        except (TypeError, ValueError):
            continue
    return clean or None


def _message_text(content: object) -> object:
    """Текст сообщения без байтов картинок и аудио."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[object] = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
            continue
        if not isinstance(part, dict):
            continue
        part_type = str(part.get("type") or "")
        if part_type == "text":
            parts.append({"type": "text", "text": part.get("text") or ""})
        elif part_type:
            parts.append({"type": part_type, "omitted": True})
    return parts


def _serialize_prompt(messages: Sequence[Any] | None, prompt_text: str | None) -> str:
    if messages is not None:
        safe: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, Mapping):
                continue
            safe.append(
                {
                    "role": message.get("role"),
                    "content": _message_text(message.get("content")),
                }
            )
        return json.dumps(safe, ensure_ascii=False)
    if prompt_text:
        return prompt_text
    return ""


def _take_call_options(
    overrides: dict[str, Any] | None,
) -> tuple[str | None, str | None, dict[str, Any] | None, dict[str, Any]]:
    """Снимает библиотечные ключи. session_id и metadata остаются в теле чата."""
    raw = overrides if overrides is not None else {}
    trace_attributes = _coerce_trace_attributes(raw.pop("trace")) if "trace" in raw else {}
    explicit_trace = coerce_trace_id(raw.pop("trace_id")) if "trace_id" in raw else None
    if "session_id" in raw:
        session_id = coerce_session_id(raw["session_id"])
        if session_id is None:
            raw.pop("session_id")
        else:
            raw["session_id"] = session_id
    else:
        session_id = current_session_id()
    # В теле чата metadata остаётся только если его передал сам вызов.
    # Ключи bound_session тогда дописываются и в запрос: лог и API совпадают.
    if "metadata" in raw:
        metadata = merge_metadata(current_metadata(), coerce_metadata(raw["metadata"]))
        if metadata is None:
            raw.pop("metadata")
        else:
            raw["metadata"] = metadata
    else:
        metadata = current_metadata()
    return explicit_trace, session_id, metadata, trace_attributes


def _grouping_for(
    explicit_trace: str | None,
    session_id: str | None,
    metadata: dict[str, Any] | None,
    span: Any,
) -> CallGrouping:
    trace_id = explicit_trace
    if trace_id is None and span is not None:
        trace_id = _span_trace_id(span)
    if trace_id is None:
        trace_id = uuid.uuid4().hex
    stored = dict(metadata) if metadata else None
    return CallGrouping(trace_id=trace_id, session_id=session_id, metadata=stored)


def _span_trace_id(span: Any) -> str | None:
    context = span.get_span_context()
    if not context.is_valid or not context.trace_id:
        return None
    return f"{context.trace_id:032x}"


def _base_attributes(
    *,
    operation: str,
    role: str,
    stream: bool,
    trace_id: str | None,
    session_id: str | None,
    metadata: dict[str, Any] | None,
    trace_attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "gen_ai.system": _GEN_AI_SYSTEM,
        "gen_ai.operation.name": operation,
        "openrouter.span.role": role,
        "openrouter.stream": stream,
        "openrouter.username": current_username(),
    }
    if trace_id:
        attributes["openrouter.trace_id"] = trace_id
    if session_id:
        attributes["openrouter.session_id"] = session_id
    profile = _resolved_profile.get()
    if profile:
        attributes["openrouter.profile"] = profile
    scrubbed = _scrub_metadata(metadata)
    if scrubbed:
        attributes["openrouter.metadata"] = json.dumps(
            scrubbed,
            ensure_ascii=False,
            sort_keys=True,
        )
    if trace_attributes:
        attributes.update(trace_attributes)
    return attributes


def note_profile(name: str) -> None:
    """Имя профиля на родительском спане. До HTTP, чтобы бюджетные ошибки его видели."""
    _resolved_profile.set(name)
    if not otel_enabled():
        return
    _set(_operation_span.get(), "openrouter.profile", name)


def note_request_model(model_id: str) -> None:
    """Модель, которую вызвали первой. Повторный вызов имя спана не переписывает."""
    if not otel_enabled():
        return
    span = _operation_span.get()
    if span is None or not span.is_recording():
        return
    try:
        current = span.attributes
        existing = current.get("gen_ai.request.model") if current else None
    except Exception:
        existing = None
    if existing:
        return
    operation = _operation_name.get()
    _set(span, "gen_ai.request.model", model_id)
    try:
        span.update_name(f"{operation} {model_id}")
    except Exception:
        logger.exception("OpenTelemetry span rename failed.")


def note_first_token(attempt_started: float) -> None:
    """Время до первого текстового чанка стрима, миллисекунды от старта попытки."""
    if not otel_enabled() or _ttft_recorded.get():
        return
    elapsed_ms = max(0, int((time.perf_counter() - attempt_started) * 1000))
    recorded = False
    for span in (_attempt_span.get(), _operation_span.get()):
        if span is None or not span.is_recording():
            continue
        _set(span, "openrouter.time_to_first_token_ms", elapsed_ms)
        recorded = True
    if recorded:
        _ttft_recorded.set(True)


def remember_output(*, text: str, model: str, finish_reason: str | None) -> None:
    """Запоминает ответ попытки: сигнал request_logged перенесёт его на спаны."""
    _output_note.set(_OutputNote(model=model, finish_reason=finish_reason, text=text))


class _YieldGate:
    """Держит спан открытым на весь стрим, но снимает contextvar перед yield наружу.

    `aclose` async-генератора выполняется в другом Context, и `Token.reset`
    оттуда не снимает значение у вызывающего кода. Поэтому перед отдачей чанка
    флаг вложенности и текущий спан снимаются в том контексте, где их ставили.
    """

    def __init__(self) -> None:
        self.operation_span: Any = None
        self.operation_token: Any = None
        self.attempt_span: Any = None
        self.attempt_token: Any = None
        self.in_operation_token: Token[bool] | None = None
        self.suspended = False
        self._tokens: list[Token[Any]] = []

    def bind(self, var: ContextVar[Any], value: Any) -> None:
        self._tokens.append(var.set(value))

    def suspend(self) -> None:
        """Снять контекст перед yield вызывающему коду. Спан не закрывается."""
        if self.suspended:
            return
        self._detach()
        _safe_reset(self.in_operation_token)
        self.in_operation_token = None
        self.suspended = True

    def resume(self) -> None:
        """Вернуть контекст, когда генератор продолжили."""
        if not self.suspended:
            return
        self.in_operation_token = _in_operation.set(True)
        self._attach()
        self.suspended = False

    def close(self) -> None:
        """Завершить спаны и сбросить токены. Исключения наружу не выпускает."""
        _end_span(self.attempt_span)
        self.attempt_span = None
        _end_span(self.operation_span)
        self.operation_span = None
        self._detach()
        _safe_reset(self.in_operation_token)
        self.in_operation_token = None
        for token in reversed(self._tokens):
            _safe_reset(token)
        self._tokens.clear()
        self.suspended = False

    def finish_attempt(self, span: Any) -> None:
        """Попытка закончилась: дочерний спан закрыть, родительский оставить."""
        if self.attempt_span is span:
            self._detach_attempt()
            self.attempt_span = None
        _end_span(span)

    def _detach_attempt(self) -> None:
        if self.attempt_token is None:
            return
        _safe_detach(self.attempt_token)
        self.attempt_token = None

    def _detach(self) -> None:
        self._detach_attempt()
        if self.operation_token is None:
            return
        _safe_detach(self.operation_token)
        self.operation_token = None

    def _attach(self) -> None:
        if self.operation_span is not None and _span_recording(self.operation_span):
            self.operation_token = _attach_span(self.operation_span)
        if self.attempt_span is not None and _span_recording(self.attempt_span):
            self.attempt_token = _attach_span(self.attempt_span)


_current_gate: ContextVar[_YieldGate | None] = ContextVar(
    "django_openrouter_yield_gate",
    default=None,
)


def _safe_reset(token: Token[Any] | None) -> None:
    """reset в том же Context. Чужой Context и повторный reset не роняют вызов."""
    if token is None:
        return
    try:
        token.var.reset(token)
    except (ValueError, RuntimeError):
        return


def _span_recording(span: Any) -> bool:
    try:
        return bool(span.is_recording())
    except Exception:
        return False


def _end_span(span: Any) -> None:
    if span is None or not _span_recording(span):
        return
    try:
        span.end()
    except Exception:
        logger.exception("OpenTelemetry span was not ended.")


def _attach_span(span: Any) -> Any:
    if otel_context is None or set_span_in_context is None:
        return None
    try:
        return otel_context.attach(set_span_in_context(span))
    except Exception:
        logger.exception("OpenTelemetry span was not attached.")
        return None


def _safe_detach(token: Any) -> None:
    if token is None or otel_context is None:
        return
    try:
        otel_context.detach(token)
    except (ValueError, RuntimeError):
        return
    except Exception:
        logger.exception("OpenTelemetry context was not detached.")


def _start_span(name: str, attributes: dict[str, Any]) -> Any | None:
    if not otel_enabled() or otel_trace is None or SpanKind is None:
        return None
    try:
        return _get_tracer().start_span(name, kind=SpanKind.CLIENT, attributes=attributes)
    except Exception:
        logger.exception("OpenTelemetry span was not started.")
        return None


@contextmanager
def open_call(
    operation: str,
    *,
    profile_name: str | None,
    overrides: dict[str, Any] | None = None,
    messages: Sequence[Any] | None = None,
    prompt_text: str | None = None,
    stream: bool = False,
) -> Iterator[_YieldGate | None]:
    """Родительский спан и группировка логов на весь вызов, включая стрим.

    Повторный вход (generate_image → chat) новый спан не открывает.
    Для стрима наружу отдаётся gate: перед yield чанка контекст снимается.
    """
    if _in_operation.get():
        yield None
        return
    explicit_trace, session_id, metadata, trace_attributes = _take_call_options(overrides)
    gate = _YieldGate()
    gate.in_operation_token = _in_operation.set(True)
    gate.bind(_operation_name, operation)
    gate.bind(_resolved_profile, profile_name)
    gate.bind(_captured_prompt, None)
    gate.bind(_ttft_recorded, False)
    gate.bind(_output_note, None)
    gate.bind(_current_gate, gate)
    try:
        attributes = _base_attributes(
            operation=operation,
            role="operation",
            stream=stream,
            trace_id=explicit_trace,
            session_id=session_id,
            metadata=metadata,
            trace_attributes=trace_attributes,
        )
        if profile_name:
            attributes["openrouter.profile"] = profile_name
        span = _start_span(operation, attributes)
        gate.operation_span = span
        if span is not None:
            gate.operation_token = _attach_span(span)
            gate.bind(_operation_span, span)
        grouping = _grouping_for(explicit_trace, session_id, metadata, span)
        if span is not None and grouping.trace_id:
            _set(span, "openrouter.trace_id", grouping.trace_id)
        if span is not None:
            _capture_prompt(span, messages, prompt_text)
        gate.bind(_call_grouping, grouping)
        try:
            yield gate
        except BaseException as exc:
            _mark_error(span, exc)
            raise
    finally:
        gate.close()


def _capture_prompt(span: Any, messages: Sequence[Any] | None, prompt_text: str | None) -> None:
    if not _capture_content():
        return
    raw = _serialize_prompt(messages, prompt_text)
    if not raw:
        return
    redacted = _redact(raw, "prompt")
    if not redacted:
        return
    _captured_prompt.set(redacted)
    _set(span, "gen_ai.prompt", redacted)


@contextmanager
def trace_attempt(
    *,
    model_id: str,
    fallback_index: int,
    retry_index: int,
    stream: bool,
) -> Iterator[None]:
    """Дочерний спан одной HTTP-попытки. Без OTEL — пустой контекст."""
    if not otel_enabled() or otel_trace is None or SpanKind is None:
        yield
        return
    operation = _operation_name.get()
    grouping = current_grouping()
    attributes = _base_attributes(
        operation=operation,
        role="attempt",
        stream=stream,
        trace_id=grouping.trace_id if grouping is not None else None,
        session_id=grouping.session_id if grouping is not None else None,
        metadata=grouping.metadata if grouping is not None else None,
    )
    attributes["gen_ai.request.model"] = model_id
    attributes["openrouter.fallback_index"] = fallback_index
    attributes["openrouter.retry_index"] = retry_index
    prompt = _captured_prompt.get()
    if prompt:
        attributes["gen_ai.prompt"] = prompt
    span = _start_span(f"{operation} {model_id}", attributes)
    if span is None:
        yield
        return
    gate = _current_gate.get()
    token = _attempt_span.set(span)
    orphan: Any = None
    if gate is not None:
        gate.attempt_span = span
        gate.attempt_token = _attach_span(span)
    else:
        orphan = _attach_span(span)
    try:
        yield
    except BaseException as exc:
        _mark_error(span, exc)
        raise
    finally:
        _safe_reset(token)
        if gate is not None:
            gate.finish_attempt(span)
        else:
            _safe_detach(orphan)
            _end_span(span)


def _apply_record(span: Any, record: Any, completion: str | None) -> None:
    if span is None or not span.is_recording():
        return
    _set(span, "openrouter.status_code", int(record.status_code))
    _set(span, "openrouter.latency_ms", int(record.latency_ms))
    _set(span, "openrouter.cost_usd", str(record.cost_usd))
    _set(span, "gen_ai.usage.input_tokens", int(record.prompt_tokens))
    _set(span, "gen_ai.usage.output_tokens", int(record.completion_tokens))
    if record.profile_name:
        _set(span, "openrouter.profile", record.profile_name)
    if record.username:
        _set(span, "openrouter.username", record.username)
    if record.model_id:
        try:
            current = span.attributes
            has_model = bool(current and current.get("gen_ai.request.model"))
        except Exception:
            has_model = False
        if not has_model:
            _set(span, "gen_ai.request.model", record.model_id)
    note = _output_note.get()
    if note is not None and note.model:
        _set(span, "gen_ai.response.model", note.model)
    elif record.status_code == 200 and record.model_id:
        _set(span, "gen_ai.response.model", record.model_id)
    if note is not None and note.finish_reason:
        _set(span, "gen_ai.response.finish_reasons", [note.finish_reason])
    if completion:
        _set(span, "gen_ai.completion", completion)
    if Status is None or StatusCode is None:
        return
    try:
        if record.status_code == 200:
            span.set_status(Status(StatusCode.OK))
        else:
            message = record.error_message or str(record.status_code)
            span.set_status(Status(StatusCode.ERROR, str(message)[:500]))
    except Exception:
        logger.exception("OpenTelemetry status was not recorded.")


def _on_request_logged(sender: object, record: Any = None, **kwargs: Any) -> None:
    """Дописывает LogRecord на открытые спаны попытки и вызова."""
    try:
        if record is None or not otel_enabled():
            return
        completion: str | None = None
        note = _output_note.get()
        if note is not None and _capture_content() and note.text:
            completion = _redact(note.text, "completion") or None
        for span in (_attempt_span.get(), _operation_span.get()):
            _apply_record(span, record, completion)
    except Exception:
        logger.exception("OpenTelemetry span update failed.")


request_logged.connect(_on_request_logged, dispatch_uid="django_openrouter_otel_log")
