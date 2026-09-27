"""Middleware: кладёт request.user в contextvar для логов chat()/stream()."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterable, Iterator
from typing import Any

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import FileResponse, HttpRequest, HttpResponseBase, StreamingHttpResponse

from django_openrouter.current_user import bound_username, username_from_user


class CurrentUserMiddleware:
    """Стоит после AuthenticationMiddleware.

    Пишет username (или 'anonymous') в RequestLog / file / ClickHouse.
    Для StreamingHttpResponse username держится и во время отдачи тела:
    stream() внутри генератора ответа выполняется уже после выхода из middleware.
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
        username = username_from_user(_request_user(request))
        with bound_username(username):
            response = self.get_response(request)
        return _bind_streaming(response, username)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        username = username_from_user(_request_user(request))
        with bound_username(username):
            response = await self.get_response(request)
        return _bind_streaming(response, username)


def _request_user(request: HttpRequest) -> object | None:
    """request.user есть только после AuthenticationMiddleware."""
    try:
        return request.user
    except AttributeError:
        return None


def _bind_streaming(response: Any, username: str) -> Any:
    # FileResponse отдаётся через wsgi.file_wrapper мимо streaming_content — не трогаем.
    if not isinstance(response, StreamingHttpResponse) or isinstance(response, FileResponse):
        return response
    content = response.streaming_content
    if isinstance(content, AsyncIterable):
        response.streaming_content = _abind_iter(content, username)
    else:
        response.streaming_content = _bind_iter(content, username)
    return response


def _bind_iter(content: Iterable[bytes], username: str) -> Iterator[bytes]:
    # Привязка на каждый next(): сервер может итерировать тело в другом контексте,
    # и token contextvar нельзя держать между yield.
    iterator = iter(content)
    while True:
        with bound_username(username):
            try:
                chunk = next(iterator)
            except StopIteration:
                return
        yield chunk


async def _abind_iter(content: AsyncIterable[bytes], username: str) -> AsyncIterator[bytes]:
    iterator = aiter(content)
    while True:
        with bound_username(username):
            try:
                chunk = await anext(iterator)
            except StopAsyncIteration:
                return
        yield chunk
