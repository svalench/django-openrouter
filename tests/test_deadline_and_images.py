"""Дедлайн вызова и картинки в ответе. HTTP замокан."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from base64 import b64decode
from decimal import Decimal

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.db import connection

from django_openrouter.client import (
    agenerate_image,
    astream,
    chat,
    generate_image,
    stream,
)
from django_openrouter.config import get_runtime_config
from django_openrouter.exceptions import ConfigurationError, OpenRouterTimeout
from django_openrouter.http_clients import get_async_client, get_sync_client
from django_openrouter.models import (
    CLIENT_CLOSED_STATUS,
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
)
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MESSAGES = [{"role": "user", "content": "Hi"}]
# 1x1 PNG.
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_DATA_URL = f"data:image/png;base64,{_PNG_B64}"
_REMOTE_URL = "https://cdn.example/crane.png"


def _enable_streaming(or_settings: OpenRouterSettings) -> None:
    or_settings.streaming_enabled = True
    or_settings.request_timeout = 30
    or_settings.save()


def _sse(*events: dict) -> bytes:
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    return f"{body}data: [DONE]\n\n".encode()


class _Paced(httpx.SyncByteStream):
    """Отдаёт куски с паузой и останавливается, когда response.close() закрыл поток."""

    def __init__(self, chunks: list[bytes], pause: float) -> None:
        self.chunks = chunks
        self.pause = pause
        self.closed = False

    def __iter__(self):
        for index, chunk in enumerate(self.chunks):
            if self.closed:
                return
            if index:
                time.sleep(self.pause)
            yield chunk

    def close(self) -> None:
        self.closed = True


class _AsyncHang(httpx.AsyncByteStream):
    def __init__(self, first: bytes) -> None:
        self.first = first

    async def __aiter__(self):
        yield self.first
        await asyncio.sleep(30)

    async def aclose(self) -> None:
        return None


def _image_message(url: str, *, extra_content: bool = False) -> dict:
    payload = completion_payload(content="see", cost=Decimal("0.25"))
    image = {"type": "image_url", "image_url": {"url": url}}
    message = payload["choices"][0]["message"]
    message["images"] = [image]
    if extra_content:
        message["content"] = [
            {"type": "text", "text": "see"},
            image,
        ]
    return payload


@respx.mock
def test_data_url_and_duplicate_parts_become_one_image(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_image_message(_DATA_URL, extra_content=True))
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "see"
    assert result.cost_usd == Decimal("0.25")
    assert result.prompt_tokens == 10
    assert len(result.images) == 1
    image = result.images[0]
    assert image.data == b64decode(_PNG_B64)
    assert image.mime == "image/png"
    assert image.url is None
    assert image.data is not None
    assert image.data.startswith(b"\x89PNG")


@respx.mock
def test_remote_image_is_downloaded_without_api_key(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_image_message(_REMOTE_URL))
    )
    download = respx_mock.get(_REMOTE_URL).mock(
        return_value=httpx.Response(200, content=b"PNGDATA", headers={"content-type": "image/png"})
    )
    result = chat("chat", messages=MESSAGES)
    assert result.images[0].data == b"PNGDATA"
    assert result.images[0].mime == "image/png"
    assert result.images[0].url == _REMOTE_URL
    assert result.cost_usd == Decimal("0.25")
    sent = download.calls.last.request
    assert "authorization" not in {key.lower() for key in sent.headers}


@respx.mock
def test_generate_image_sends_modalities_and_keeps_usage(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    paid_model: OpenRouterModel,
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_image_message(_DATA_URL))
    )
    result = generate_image("a paper crane", profile="chat", model=paid_model.model_id)
    body = json.loads(route.calls.last.request.content)
    assert body["modalities"] == ["image", "text"]
    assert body["model"] == paid_model.model_id
    assert body["messages"] == [{"role": "user", "content": "a paper crane"}]
    assert "total_timeout" not in body
    assert result.images[0].mime == "image/png"
    assert result.completion_tokens == 5
    assert RequestLog.objects.get().cost_usd == Decimal("0.25")


@pytest.mark.django_db(transaction=True)
@respx.mock
def test_agenerate_image(respx_mock: respx.MockRouter, or_settings: OpenRouterSettings) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_image_message(_DATA_URL))
    )
    result = async_to_sync(agenerate_image)("async crane", profile="chat")
    assert result.images[0].data == b64decode(_PNG_B64)


def test_generate_image_rejects_blank_prompt(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError):
        generate_image("  ", profile="chat")


@respx.mock
def test_reasoning_is_forwarded_and_timeouts_stay_local(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    chat(
        "chat",
        messages=MESSAGES,
        reasoning={"enabled": False},
        total_timeout=15,
        request_timeout=9,
    )
    body = json.loads(route.calls.last.request.content)
    assert body["reasoning"] == {"enabled": False}
    assert "request_timeout" not in body
    assert "total_timeout" not in body
    assert "deadline_s" not in body
    assert "reasoning" not in caplog.text


def test_disagreeing_deadlines_are_rejected(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError, match="total_timeout"):
        chat("chat", messages=MESSAGES, total_timeout=5, deadline_s=6)


@respx.mock
def test_stream_final_result_keeps_usage(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(
                {"choices": [{"delta": {"content": "Hi"}}]},
                {
                    "usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 2,
                        "cost": "0.01",
                    }
                },
            ),
        )
    )
    chunks = list(stream("chat", messages=MESSAGES))
    result = chunks[-1].result
    assert result is not None
    assert result.incomplete is False
    assert result.content == "Hi"
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 2
    assert result.cost_usd == Decimal("0.01")


@respx.mock
def test_stream_collects_image_deltas(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=_sse(
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "drawn",
                                "images": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": _DATA_URL},
                                    }
                                ],
                            }
                        }
                    ]
                },
                {"usage": {"prompt_tokens": 4, "completion_tokens": 6, "cost": "0.02"}},
            ),
        )
    )
    result = chat("chat", messages=MESSAGES, stream=True)
    assert result.content == "drawn"
    assert result.images[0].mime == "image/png"
    assert result.prompt_tokens == 4
    assert result.cost_usd == Decimal("0.02")


@respx.mock
def test_chat_deadline_raises_with_partial_usage(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    chunks = [
        _sse(
            {"choices": [{"delta": {"content": "partial"}}]},
            {"usage": {"prompt_tokens": 3, "completion_tokens": 4, "cost": "0.2"}},
        ).removesuffix(b"data: [DONE]\n\n"),
        b": ping\n\n",
        b": ping\n\n",
        b": ping\n\n",
        b": ping\n\n",
        b": ping\n\n",
        b"data: [DONE]\n\n",
    ]
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced(chunks, pause=0.08))
    )
    with pytest.raises(OpenRouterTimeout, match="total timeout") as exc:
        chat("chat", messages=MESSAGES, stream=True, total_timeout=0.2)
    partial = exc.value.partial
    assert partial is not None
    assert partial.incomplete is True
    assert partial.content == "partial"
    assert partial.prompt_tokens == 3
    assert partial.completion_tokens == 4
    log = RequestLog.objects.get()
    assert log.status_code == CLIENT_CLOSED_STATUS
    assert log.prompt_tokens == 3
    assert log.completion_tokens == 4
    assert "total timeout" in (log.error_message or "")


@respx.mock
def test_stream_deadline_yields_incomplete_chunk(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    chunks = [
        b'data: {"choices":[{"delta":{"content":"part"}}]}\n\n',
        b": ping\n\n",
        b": ping\n\n",
        b": ping\n\n",
        b": ping\n\n",
        b"data: [DONE]\n\n",
    ]
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced(chunks, pause=0.08))
    )
    received = list(stream("chat", messages=MESSAGES, deadline_s=0.15))
    assert received[-1].done is True
    assert received[-1].result is not None
    assert received[-1].result.incomplete is True
    assert received[-1].result.content == "part"
    assert get_sync_client().is_closed is False


@respx.mock
def test_json_deadline_raises_before_a_slow_body(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    body = completion_payload(content="late")
    raw = json.dumps(body).encode()
    chunks = [raw[:1], raw[1:]]
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced(chunks, pause=0.4))
    )
    with pytest.raises(OpenRouterTimeout) as exc:
        chat("chat", messages=MESSAGES, total_timeout=0.15)
    assert exc.value.partial is None
    assert get_sync_client().is_closed is False


@respx.mock
def test_profile_timeout_does_not_raise_the_global_one(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    or_settings.request_timeout = 17
    or_settings.streaming_enabled = True
    or_settings.save()
    profile.request_timeout = 40
    profile.save()
    UsageProfile.objects.create(name="fast", model=paid_model, is_active=True)
    seen: list[float | None] = []
    original = httpx.Client.stream

    def wrapped(self: httpx.Client, method: str, url: httpx.URL | str, **kwargs: object):
        if str(url).endswith("/chat/completions"):
            timeout = kwargs.get("timeout")
            read = timeout.read if isinstance(timeout, httpx.Timeout) else None
            seen.append(read)
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(httpx.Client, "stream", wrapped)

    def side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=_sse({"choices": [{"delta": {"content": "s"}}]}),
            )
        return httpx.Response(200, json=completion_payload())

    respx_mock.post(CHAT_URL).mock(side_effect=side_effect)
    chat("fast", messages=MESSAGES)
    list(stream("chat", messages=[{"role": "user", "content": "stream me"}]))
    chat("chat", messages=MESSAGES, request_timeout=8)
    assert seen == [17, 40, 8]
    or_settings.refresh_from_db()
    profile.refresh_from_db()
    assert or_settings.request_timeout == 17
    assert profile.request_timeout == 40
    assert or_settings.streaming_enabled is True


@respx.mock
def test_settings_total_timeout_is_runtime_config(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    or_settings.total_timeout = 12
    or_settings.save()
    assert get_runtime_config().total_timeout == 12
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    assert chat("chat", messages=MESSAGES).content == "Hello"


@pytest.mark.django_db(transaction=True)
@respx.mock
def test_one_stream_deadline_does_not_kill_another(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_streaming(or_settings)
    started = threading.Event()

    def side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        text = body["messages"][0]["content"]
        if text == "slow":
            chunks = [
                b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
                b": ping\n\n",
                b": ping\n\n",
                b": ping\n\n",
                b": ping\n\n",
                b": ping\n\n",
                b": ping\n\n",
                b"data: [DONE]\n\n",
            ]

            class _Marked(_Paced):
                def __iter__(self):
                    started.set()
                    yield from super().__iter__()

            return httpx.Response(200, stream=_Marked(chunks, pause=0.08))
        return httpx.Response(200, json=completion_payload(content="fast-ok"))

    respx_mock.post(CHAT_URL).mock(side_effect=side_effect)

    def _close_client(self: httpx.Client) -> None:
        raise AssertionError("shared client closed")

    monkeypatch.setattr(httpx.Client, "close", _close_client)
    box: dict[str, object] = {}

    def run_slow() -> None:
        try:
            box["slow"] = list(
                stream(
                    "chat",
                    messages=[{"role": "user", "content": "slow"}],
                    total_timeout=0.2,
                )
            )
        except Exception as exc:
            box["slow_error"] = exc
        finally:
            connection.close()

    connection.close()
    worker = threading.Thread(target=run_slow)
    worker.start()
    if not started.wait(2):
        worker.join(timeout=2)
        raise AssertionError(f"slow stream did not start: {box}")
    fast = chat("chat", messages=[{"role": "user", "content": "fast"}])
    worker.join(timeout=3)
    assert not worker.is_alive()
    assert fast.content == "fast-ok"
    assert "slow_error" not in box
    slow_chunks = box["slow"]
    assert isinstance(slow_chunks, list)
    result = slow_chunks[-1].result
    assert result is not None
    assert result.incomplete is True
    assert result.content == "partial"
    assert get_sync_client().is_closed is False
    again = chat("chat", messages=[{"role": "user", "content": "fast"}])
    assert again.content == "fast-ok"


@pytest.mark.django_db(transaction=True)
@respx.mock
def test_async_deadline_does_not_close_shared_client(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_streaming(or_settings)

    def side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        text = body["messages"][0]["content"]
        if text == "slow":
            return httpx.Response(
                200,
                stream=_AsyncHang(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'),
            )
        if text == "json-slow":
            return httpx.Response(200, stream=_AsyncHang(b"{"))
        return httpx.Response(200, json=completion_payload(content="fast-ok"))

    respx_mock.post(CHAT_URL).mock(side_effect=side_effect)

    async def _aclose(self: httpx.AsyncClient) -> None:
        raise AssertionError("shared async client closed")

    monkeypatch.setattr(httpx.AsyncClient, "aclose", _aclose)

    async def slow_stream() -> list:
        return [
            chunk
            async for chunk in astream(
                "chat",
                messages=[{"role": "user", "content": "slow"}],
                total_timeout=0.2,
            )
        ]

    async def fast_chat() -> str:
        await asyncio.sleep(0.05)
        result = await chat_async()
        return result.content

    async def chat_async():
        from django_openrouter.client import achat

        return await achat("chat", messages=[{"role": "user", "content": "fast"}])

    async def json_slow():
        from django_openrouter.client import achat

        return await achat(
            "chat", messages=[{"role": "user", "content": "json-slow"}], total_timeout=0.2
        )

    async def main():
        slow_task = asyncio.create_task(slow_stream())
        fast_task = asyncio.create_task(fast_chat())
        slow_chunks, fast_text = await asyncio.gather(slow_task, fast_task)
        with pytest.raises(OpenRouterTimeout):
            await json_slow()
        follow = await chat_async()
        client = get_async_client()
        return slow_chunks, fast_text, follow.content, client.is_closed

    slow_chunks, fast_text, follow, client_closed = async_to_sync(main)()
    assert fast_text == "fast-ok"
    assert follow == "fast-ok"
    assert slow_chunks[-1].result is not None
    assert slow_chunks[-1].result.incomplete is True
    assert slow_chunks[-1].result.content == "partial"
    assert client_closed is False


@respx.mock
def test_image_shapes_and_failed_downloads(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    payload = completion_payload(content="mix")
    payload["choices"][0]["message"]["content"] = [
        {"type": "text", "text": "mix"},
        {"type": "image_url", "image_url": "data:text/plain,hello%20x"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,!!!!"}},
        {"type": "image_url", "image_url": {"url": "data:image/png"}},
        {"inline_data": {"mime_type": "image/png", "data": _PNG_B64}},
        {"type": "image", "url": "ftp://example/a.png"},
        {"type": "image_url", "image_url": {"url": _REMOTE_URL}},
    ]
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    respx_mock.get(_REMOTE_URL).mock(return_value=httpx.Response(404))
    result = chat("chat", messages=MESSAGES)
    assert result.content == "mix"
    decoded = [image for image in result.images if image.data]
    assert any(image.data == b"hello x" for image in decoded)
    assert any(image.data == b64decode(_PNG_B64) for image in decoded)
    assert any(image.url == _REMOTE_URL and image.data is None for image in result.images)


@respx.mock
def test_oversized_and_unreachable_image_keep_the_url(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    huge = "https://cdn.example/huge.png"
    down = "https://cdn.example/down.png"
    payload = completion_payload(content="x")
    payload["choices"][0]["message"]["images"] = [
        {"type": "image_url", "image_url": {"url": huge}},
        {"type": "image_url", "image_url": {"url": down}},
    ]
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    respx_mock.get(huge).mock(
        return_value=httpx.Response(200, headers={"content-length": str(30 * 1024 * 1024)})
    )
    respx_mock.get(down).mock(side_effect=httpx.ConnectError("no route"))
    result = chat("chat", messages=MESSAGES)
    assert [image.url for image in result.images] == [huge, down]
    assert all(image.data is None for image in result.images)
    assert result.cost_usd >= 0


@pytest.mark.django_db(transaction=True)
@respx.mock
def test_async_remote_image_download(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=_image_message(_REMOTE_URL))
    )
    respx_mock.get(_REMOTE_URL).mock(
        return_value=httpx.Response(200, content=b"PNGDATA", headers={"content-type": "image/png"})
    )
    result = async_to_sync(agenerate_image)("remote", profile="chat")
    assert result.images[0].data == b"PNGDATA"
    assert result.images[0].mime == "image/png"


@respx.mock
def test_stream_without_output_raises_on_deadline(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    chunks = [b": ping\n\n", b": ping\n\n", b": ping\n\n", b": ping\n\n", b"data: [DONE]\n\n"]
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced(chunks, pause=0.08))
    )
    with pytest.raises(OpenRouterTimeout, match="total timeout") as exc:
        list(stream("chat", messages=MESSAGES, deadline_s=0.15))
    assert exc.value.partial is None


def test_bad_timeout_is_rejected(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError, match="total_timeout"):
        chat("chat", messages=MESSAGES, total_timeout=0)
    with pytest.raises(ConfigurationError, match="request_timeout"):
        chat("chat", messages=MESSAGES, request_timeout="later")


@respx.mock
def test_profile_total_timeout_applies_without_a_call_kwarg(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    _enable_streaming(or_settings)
    profile.total_timeout = 1
    profile.save()
    chunks = [b": ping\n\n"] * 8 + [b"data: [DONE]\n\n"]
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced(chunks, pause=0.2))
    )
    with pytest.raises(OpenRouterTimeout):
        list(stream("chat", messages=MESSAGES))
