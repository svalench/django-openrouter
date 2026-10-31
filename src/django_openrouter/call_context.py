"""Группировка вызовов: session_id, metadata и trace_id на время одного вызова.

`bound_session` держит сессию между вызовами (Celery, view). На время
`chat()` / `transcribe()` поверх неё кладётся `CallGrouping`: у всех
попыток (retry и fallback) один trace_id.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from django_openrouter.exceptions import ConfigurationError

SESSION_ID_MAX_LENGTH = 255
TRACE_ID_MAX_LENGTH = 64

_bound_session_id: ContextVar[str | None] = ContextVar(
    "django_openrouter_session_id",
    default=None,
)
_bound_metadata: ContextVar[dict[str, Any] | None] = ContextVar(
    "django_openrouter_metadata",
    default=None,
)
_call_grouping: ContextVar[CallGrouping | None] = ContextVar(
    "django_openrouter_call_grouping",
    default=None,
)


@dataclass(frozen=True)
class CallGrouping:
    """Идентификаторы одного логического вызова, общие для всех HTTP-попыток."""

    trace_id: str | None
    session_id: str | None
    metadata: dict[str, Any] | None


def current_session_id() -> str | None:
    """session_id из `bound_session`, без учёта аргумента конкретного вызова."""
    return _bound_session_id.get()


def current_metadata() -> dict[str, Any] | None:
    """metadata из `bound_session`. Словарь не копируется: вызывающий код его не меняет."""
    return _bound_metadata.get()


def current_grouping() -> CallGrouping | None:
    """Группировка текущего вызова или None вне `open_call`."""
    return _call_grouping.get()


def grouping_fields() -> dict[str, Any]:
    """Колонки RequestLog для текущего вызова. Пусто, если вызов не размечен."""
    grouping = _call_grouping.get()
    if grouping is None:
        return {}
    return {
        "trace_id": grouping.trace_id or None,
        "session_id": grouping.session_id or None,
        "metadata": grouping.metadata,
    }


@contextmanager
def bound_call_grouping(grouping: CallGrouping) -> Iterator[None]:
    """Ставит группировку на время одного `chat()` / `transcribe()`."""
    token = _call_grouping.set(grouping)
    try:
        yield
    finally:
        _call_grouping.reset(token)


@contextmanager
def bound_session(
    session_id: str,
    metadata: Mapping[str, Any] | None = None,
) -> Iterator[None]:
    """with bound_session('ticket-42', metadata={'feature': 'support'}): chat(...).

    Аргументы `session_id=` / `metadata=` на конкретном вызове перекрывают
    значения из блока и не снимают привязку для следующих вызовов.
    """
    session = coerce_session_id(session_id)
    if session is None:
        raise ConfigurationError("session_id must be a non-empty string.")
    meta = coerce_metadata(dict(metadata) if metadata is not None else None)
    session_token: Token[str | None] = _bound_session_id.set(session)
    metadata_token: Token[dict[str, Any] | None] = _bound_metadata.set(meta)
    try:
        yield
    finally:
        _bound_metadata.reset(metadata_token)
        _bound_session_id.reset(session_token)


def coerce_session_id(value: object) -> str | None:
    """Пустая строка — это отсутствие сессии. Длиннее лимита колонки — ошибка."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("session_id must be a string.")
    text = value.strip()
    if not text:
        return None
    if len(text) > SESSION_ID_MAX_LENGTH:
        raise ConfigurationError("session_id is too long.")
    return text


def coerce_trace_id(value: object) -> str | None:
    """Явный trace_id. Пустая строка означает «сгенерировать»."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("trace_id must be a string.")
    text = value.strip()
    if not text:
        return None
    if len(text) > TRACE_ID_MAX_LENGTH:
        raise ConfigurationError("trace_id is too long.")
    return text


def coerce_metadata(value: object) -> dict[str, Any] | None:
    """JSON-объект или None. Списки и строки не принимаем: в логе это объект."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigurationError("metadata must be a JSON object.")
    if not value:
        return None
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("metadata must be JSON-serializable.") from exc
    return dict(value)


def merge_metadata(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Ключи вызова перекрывают ключи `bound_session`. Пустой результат — None."""
    if not base and not override:
        return None
    merged = dict(base or {})
    merged.update(override or {})
    return merged or None
