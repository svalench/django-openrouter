"""Content-Encoding на chat/stream/image: тело распаковывается один раз.

Ответ как у OpenRouter: сырые gzip/br/identity байты и заголовок content-encoding.
httpx.iter_bytes уже снимает кодирование. Повторная распаковка даёт zlib error -3.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal

import brotli
import httpx
import pytest
import respx
from asgiref.sync import async_to_sync

from django_openrouter.client import achat, agenerate_image, astream, chat, generate_image, stream
from django_openrouter.exceptions import OpenRouterAPIError
from django_openrouter.models import OpenRouterSettings
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MESSAGES = [{"role": "user", "content": "Hi"}]
ENCODINGS = ["gzip", "br", "identity"]
# Куски короче заголовка gzip (10 байт), чтобы декодер был инкрементальным.
_CHUNK = 5
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _Chunked(httpx.SyncByteStream, httpx.AsyncByteStream):
    """Отдаёт сжатое тело кусками, как сокет. Не предраспаковывает."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __iter__(self) -> Iterator[bytes]:
        payload = self.payload
        for start in range(0, len(payload), _CHUNK):
            yield payload[start : start + _CHUNK]

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            yield chunk


def _compress(body: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        payload = gzip.compress(body)
        assert payload.startswith(b"\x1f\x8b")
        return payload
    if encoding == "br":
        payload = brotli.compress(body)
        assert payload != body
        return payload
    if encoding == "identity":
        return body
    raise AssertionError(encoding)


def _encoded_response(body: bytes, encoding: str, *, content_type: str) -> httpx.Response:
    payload = _compress(body, encoding)
    return httpx.Response(
        200,
        headers={
            "content-type": content_type,
            "content-encoding": encoding,
            "content-length": str(len(payload)),
        },
        stream=_Chunked(payload),
    )


def _json_response(payload: dict, encoding: str) -> httpx.Response:
    return _encoded_response(
        json.dumps(payload).encode(),
        encoding,
        content_type="application/json",
    )


def _sse_body(content: str) -> bytes:
    mid = max(1, len(content) // 2)
    events: list[dict] = [
        {
            "model": "anthropic/claude-3.5-sonnet",
            "choices": [{"delta": {"content": content[:mid]}}],
        }
    ]
    if content[mid:]:
        events.append({"choices": [{"delta": {"content": content[mid:]}}]})
    events.append(
        {
            "model": "anthropic/claude-3.5-sonnet",
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    )
    lines = [f"data: {json.dumps(event)}\n\n" for event in events]
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def _sse_response(content: str, encoding: str) -> httpx.Response:
    return _encoded_response(
        _sse_body(content),
        encoding,
        content_type="text/event-stream",
    )


def _image_payload() -> dict:
    payload = completion_payload(content="see", cost=Decimal("0.25"))
    payload["choices"][0]["message"]["images"] = [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_PNG_B64}"}}
    ]
    return payload


def _enable_streaming(or_settings: OpenRouterSettings) -> None:
    or_settings.streaming_enabled = True
    or_settings.save()


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
def test_chat_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=_json_response(completion_payload(content="encoded"), encoding)
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "encoded"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
@pytest.mark.django_db(transaction=True)
def test_achat_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=_json_response(completion_payload(content="async-encoded"), encoding)
    )
    result = async_to_sync(achat)("chat", messages=MESSAGES)
    assert result.content == "async-encoded"


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
def test_stream_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("streamed", encoding))
    chunks = list(stream("chat", messages=MESSAGES))
    assert "".join(chunk.delta for chunk in chunks if not chunk.done) == "streamed"
    assert chunks[-1].result is not None
    assert chunks[-1].result.content == "streamed"
    assert chunks[-1].result.incomplete is False


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
@pytest.mark.django_db(transaction=True)
def test_astream_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("async-streamed", encoding))

    async def _collect() -> str:
        content = ""
        async for chunk in astream("chat", messages=MESSAGES):
            if chunk.done and chunk.result is not None:
                content = chunk.result.content
        return content

    assert async_to_sync(_collect)() == "async-streamed"


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
def test_generate_image_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=_json_response(_image_payload(), encoding))
    result = generate_image("a paper crane", profile="chat")
    assert result.content == "see"
    assert result.cost_usd == Decimal("0.25")
    assert len(result.images) == 1
    assert result.images[0].mime == "image/png"
    assert result.images[0].data is not None
    assert result.images[0].data.startswith(b"\x89PNG")


@pytest.mark.parametrize("encoding", ENCODINGS)
@respx.mock
@pytest.mark.django_db(transaction=True)
def test_agenerate_image_decodes_content_encoding(
    encoding: str,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=_json_response(_image_payload(), encoding))
    result = async_to_sync(agenerate_image)("async crane", profile="chat")
    assert result.images[0].data is not None
    assert result.images[0].data.startswith(b"\x89PNG")
    assert result.content == "see"


@respx.mock
def test_chat_reads_respx_gzip_content(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    """Тот же ответ, что собирает respx/MockTransport: content=gzip и заголовок."""
    body = json.dumps(completion_payload(content="from-content")).encode()
    compressed = gzip.compress(body)
    assert compressed.startswith(b"\x1f\x8b")
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            content=compressed,
            headers={
                "content-type": "application/json",
                "content-encoding": "gzip",
                "content-length": str(len(compressed)),
            },
        )
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "from-content"


@respx.mock
def test_chat_decodes_gzip_error_body(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    text = json.dumps({"error": {"message": "no credits", "code": 402}})
    compressed = gzip.compress(text.encode())
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            402,
            stream=_Chunked(compressed),
            headers={
                "content-type": "application/json",
                "content-encoding": "gzip",
                "content-length": str(len(compressed)),
            },
        )
    )
    with pytest.raises(OpenRouterAPIError, match="no credits") as exc_info:
        chat("chat", messages=MESSAGES)
    assert exc_info.value.status_code == 402
