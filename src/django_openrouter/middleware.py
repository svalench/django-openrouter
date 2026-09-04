"""Middleware: кладёт request.user в contextvar для логов chat()/stream()."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponseBase

from django_openrouter.current_user import bound_username, username_from_user


class CurrentUserMiddleware:
    """Стоит после AuthenticationMiddleware.

    Пишет username (или 'anonymous') в RequestLog / file / ClickHouse.
    """

    async_capable = True
    sync_capable = True

    def __init__(self, get_response: Callable[[HttpRequest], Any]) -> None:
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> Any:
        if iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        with bound_username(username_from_user(_request_user(request))):
            return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        with bound_username(username_from_user(_request_user(request))):
            return await self.get_response(request)


def _request_user(request: HttpRequest) -> object | None:
    """request.user есть только после AuthenticationMiddleware."""
    try:
        return request.user
    except AttributeError:
        return None
