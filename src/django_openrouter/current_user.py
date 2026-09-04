"""Текущий пользователь для логов запросов (contextvar).

Заполняется `CurrentUserMiddleware` из `request.user`. Вне HTTP-запроса
можно обернуть вызов в `bound_username(...)`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Protocol, runtime_checkable

ANONYMOUS_USERNAME = "anonymous"
_USERNAME_MAX_LENGTH = 150

_current_username: ContextVar[str | None] = ContextVar(
    "django_openrouter_username",
    default=None,
)


@runtime_checkable
class UserLike(Protocol):
    is_authenticated: bool

    def get_username(self) -> str: ...


def _clip(name: str) -> str:
    return name[:_USERNAME_MAX_LENGTH]


def username_from_user(user: object | None) -> str:
    """Username аутентифицированного пользователя либо 'anonymous'."""
    if user is None:
        return ANONYMOUS_USERNAME
    if not isinstance(user, UserLike):
        return ANONYMOUS_USERNAME
    if not user.is_authenticated:
        return ANONYMOUS_USERNAME
    name = user.get_username()
    if not name:
        return ANONYMOUS_USERNAME
    return _clip(str(name))


def current_username() -> str:
    """Username из contextvar (middleware / bound_username) или 'anonymous'."""
    value = _current_username.get()
    if value:
        return value
    return ANONYMOUS_USERNAME


def bind_username(username: str) -> Token[str | None]:
    """Ставит username в contextvar. Сброс — reset_username(token)."""
    clipped = _clip(username) if username else ANONYMOUS_USERNAME
    return _current_username.set(clipped)


def reset_username(token: Token[str | None]) -> None:
    _current_username.reset(token)


@contextmanager
def bound_username(username: str) -> Iterator[None]:
    """with bound_username('alice'): chat(...) — для задач без request."""
    token = bind_username(username)
    try:
        yield
    finally:
        reset_username(token)
