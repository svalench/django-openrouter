from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import respx
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.test import RequestFactory

from django_openrouter.client import chat
from django_openrouter.current_user import (
    ANONYMOUS_USERNAME,
    bound_username,
    current_username,
    username_from_user,
)
from django_openrouter.middleware import CurrentUserMiddleware
from django_openrouter.models import OpenRouterSettings, RequestLog
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MESSAGES = [{"role": "user", "content": "Hi"}]


def test_username_from_user_anonymous_and_missing() -> None:
    assert username_from_user(None) == ANONYMOUS_USERNAME
    assert username_from_user(AnonymousUser()) == ANONYMOUS_USERNAME
    assert username_from_user(object()) == ANONYMOUS_USERNAME
    assert current_username() == ANONYMOUS_USERNAME


def test_username_from_authenticated_user() -> None:
    user = User.objects.create_user("alice", password="x")
    assert username_from_user(user) == "alice"


def test_bound_username_resets() -> None:
    with bound_username("worker"):
        assert current_username() == "worker"
    assert current_username() == ANONYMOUS_USERNAME


@respx.mock
def test_chat_logs_anonymous_without_request(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    chat("chat", messages=MESSAGES)
    assert RequestLog.objects.get().username == ANONYMOUS_USERNAME


@respx.mock
def test_chat_logs_bound_username(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with bound_username("alice"):
        chat("chat", messages=MESSAGES)
    assert RequestLog.objects.get().username == "alice"


@respx.mock
def test_middleware_logs_authenticated_username(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    rf: RequestFactory,
) -> None:
    user = User.objects.create_user("bob", password="x")
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))

    def view(_request: HttpRequest) -> HttpResponse:
        chat("chat", messages=MESSAGES)
        return HttpResponse("ok")

    request = rf.get("/")
    request.user = user
    response = CurrentUserMiddleware(view)(request)
    assert response.status_code == 200
    assert RequestLog.objects.get().username == "bob"


@respx.mock
def test_middleware_logs_anonymous(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    rf: RequestFactory,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))

    def view(_request: HttpRequest) -> HttpResponse:
        chat("chat", messages=MESSAGES)
        return HttpResponse("ok")

    request = rf.get("/")
    request.user = AnonymousUser()
    CurrentUserMiddleware(view)(request)
    assert RequestLog.objects.get().username == ANONYMOUS_USERNAME


def test_middleware_keeps_username_while_streaming(rf: RequestFactory) -> None:
    user = User.objects.create_user("carol", password="x")

    def body() -> Iterator[bytes]:
        yield current_username().encode()
        yield current_username().encode()

    request = rf.get("/")
    request.user = user
    response = CurrentUserMiddleware(lambda _request: StreamingHttpResponse(body()))(request)
    assert current_username() == ANONYMOUS_USERNAME
    assert b"".join(response.streaming_content) == b"carolcarol"
    assert current_username() == ANONYMOUS_USERNAME


async def test_async_middleware_keeps_username_while_streaming(rf: RequestFactory) -> None:
    user = User(username="dave")

    async def body() -> AsyncIterator[bytes]:
        yield current_username().encode()

    async def view(_request: HttpRequest) -> StreamingHttpResponse:
        return StreamingHttpResponse(body())

    request = rf.get("/")
    request.user = user
    response = await CurrentUserMiddleware(view)(request)
    chunks = [chunk async for chunk in response.streaming_content]
    assert chunks == [b"dave"]
    assert current_username() == ANONYMOUS_USERNAME
