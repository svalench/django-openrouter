from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync

from django_openrouter.client import (
    AsyncOpenRouterClient,
    OpenRouterClient,
    achat,
    astream,
    chat,
    compute_cost,
    stream,
)
from django_openrouter.exceptions import (
    BudgetExceeded,
    ConfigurationError,
    ModelDisabled,
    OpenRouterAPIError,
    OpenRouterDisabled,
)
from django_openrouter.models import (
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MESSAGES = [{"role": "user", "content": "Hi"}]


@respx.mock
def test_chat_success_logs_and_cost(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json=completion_payload(content="pong", prompt_tokens=10, completion_tokens=5),
        )
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "pong"
    assert result.model_used == "anthropic/claude-3.5-sonnet"
    expected = Decimal("0.000003") * 10 + Decimal("0.000015") * 5
    assert result.cost_usd == expected
    assert result.catalog_cost_usd == expected
    log = RequestLog.objects.get()
    assert log.status_code == 200
    assert log.cost_usd == expected
    assert log.prompt_tokens == 10
    assert log.profile_id == profile.pk
    assert log.username == "anonymous"


@respx.mock
def test_client_class_same_as_facade(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    result = OpenRouterClient("chat").chat(MESSAGES)
    assert result.content == "Hello"


@respx.mock
def test_skips_inactive_primary(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    paid_model.is_active = False
    paid_model.save()
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json=completion_payload(content="next", model="openai/gpt-4o-mini"),
        )
    )
    result = chat("chat", messages=MESSAGES)
    assert result.model_used == "openai/gpt-4o-mini"
    assert result.content == "next"


@respx.mock
def test_fallback_on_429(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate"}),
            httpx.Response(
                200,
                json=completion_payload(
                    content="fallback-ok",
                    model="openai/gpt-4o-mini",
                ),
            ),
        ]
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "fallback-ok"
    assert result.model_used == "openai/gpt-4o-mini"
    assert RequestLog.objects.count() == 2
    assert list(RequestLog.objects.order_by("id").values_list("status_code", flat=True)) == [
        429,
        200,
    ]


@respx.mock
def test_fallback_on_402_and_500(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
    free_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    UsageProfileFallback.objects.create(profile=profile, model=free_model, order=1)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(402, json={"error": "credits"}),
            httpx.Response(500, json={"error": "boom"}),
            httpx.Response(
                200,
                json=completion_payload(
                    content="third",
                    model="meta-llama/llama-3-8b-instruct:free",
                ),
            ),
        ]
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "third"
    assert RequestLog.objects.count() == 3


@respx.mock
def test_client_error_does_not_fallback(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(OpenRouterAPIError) as exc:
        chat("chat", messages=MESSAGES)
    assert exc.value.status_code == 400
    assert RequestLog.objects.count() == 1


@respx.mock
def test_budget_exceeded_stops_before_http(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model,
) -> None:
    profile.budget_usd_per_day = Decimal("0.01")
    profile.save()
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("0.01"),
    )
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    with pytest.raises(BudgetExceeded):
        chat("chat", messages=MESSAGES)
    assert route.call_count == 0


@respx.mock
def test_only_free_models_blocks_paid(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    profile.only_free_models = True
    profile.save(update_fields=["only_free_models"])
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    with pytest.raises(ModelDisabled, match=r"only free|No allowed"):
        chat("chat", messages=MESSAGES)
    assert route.call_count == 0


def test_stream_disabled_in_settings(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError, match="Streaming is disabled"):
        chat("chat", messages=MESSAGES, stream=True)
    with pytest.raises(ConfigurationError, match="Streaming is disabled"):
        list(stream("chat", messages=MESSAGES))


def test_disabled_kill_switch(or_settings: OpenRouterSettings) -> None:
    or_settings.enabled = False
    or_settings.save()
    with pytest.raises(OpenRouterDisabled):
        chat("chat", messages=MESSAGES)


def test_missing_api_key(or_settings: OpenRouterSettings, monkeypatch: pytest.MonkeyPatch) -> None:
    or_settings.api_key = ""
    or_settings.save()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="API key"):
        chat("chat", messages=MESSAGES)


def test_unknown_profile(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        chat("missing", messages=MESSAGES)


def test_profile_without_models(or_settings: OpenRouterSettings) -> None:
    # Профиль без моделей валиден в БД, но не попадает в runtime-конфиг.
    UsageProfile.objects.create(name="empty", is_active=True)
    with pytest.raises(ConfigurationError, match="not found or inactive"):
        chat("empty", messages=MESSAGES)


def test_messages_required(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(TypeError):
        chat("chat")


@respx.mock
@pytest.mark.django_db(transaction=True)
def test_async_chat(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="async-ok"))
    )
    result = async_to_sync(achat)("chat", messages=MESSAGES)
    assert result.content == "async-ok"
    result2 = async_to_sync(AsyncOpenRouterClient("chat").chat)(MESSAGES)
    assert result2.content == "async-ok"
    assert RequestLog.objects.count() == 2


def test_compute_cost_from_catalog() -> None:
    cost, catalog = compute_cost(
        10,
        5,
        {"prompt": "0.000003", "completion": "0.000015"},
        usage_cost="9.99",
    )
    assert catalog == Decimal("0.000003") * 10 + Decimal("0.000015") * 5
    assert cost == catalog


def test_compute_cost_from_usage_when_no_pricing() -> None:
    cost, catalog = compute_cost(1, 1, None, usage_cost="0.42")
    assert cost == Decimal("0.42")
    assert catalog is None


@respx.mock
def test_headers_sent(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    chat("chat", messages=MESSAGES)
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert request.headers["HTTP-Referer"] == "https://example.com"
    assert request.headers["X-Title"] == "django-openrouter-tests"


@respx.mock
def test_profile_params_in_payload(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    profile.max_tokens = 128
    profile.temperature = 0.2
    profile.save()
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    chat("chat", messages=MESSAGES)
    body = json.loads(route.calls.last.request.content)
    assert body["max_tokens"] == 128
    assert body["temperature"] == 0.2


@respx.mock
def test_default_profile_when_name_omitted(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="default"))
    )
    result = chat(messages=MESSAGES)
    assert result.content == "default"


def test_no_default_profile_raises(or_settings: OpenRouterSettings) -> None:
    or_settings.default_profile = None
    or_settings.save()
    with pytest.raises(ConfigurationError, match="No usage profile"):
        chat(messages=MESSAGES)


@respx.mock
def test_unknown_model_override(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    with pytest.raises(ConfigurationError, match="Unknown model"):
        chat("chat", messages=MESSAGES, model="does/not-exist")


@respx.mock
def test_list_content_and_empty_choices(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    payload = completion_payload()
    payload["choices"] = [
        {"message": {"role": "assistant", "content": [{"type": "text", "text": "chunk"}]}}
    ]
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    result = chat("chat", messages=MESSAGES)
    assert result.content == "chunk"


@respx.mock
def test_transport_error_becomes_api_error(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(OpenRouterAPIError, match="boom"):
        chat("chat", messages=MESSAGES)
    assert RequestLog.objects.filter(status_code=0).exists()


@respx.mock
def test_all_models_fail_with_429(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(429, json={"error": "rate"}))
    with pytest.raises(OpenRouterAPIError) as exc:
        chat("chat", messages=MESSAGES)
    assert exc.value.status_code == 429


@respx.mock
def test_5xx_retries_same_model(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    or_settings.max_retries = 1
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "x"}),
            httpx.Response(200, json=completion_payload(content="recovered")),
        ]
    )
    result = chat("chat", messages=MESSAGES)
    assert result.content == "recovered"


def _sse_body(*events: dict) -> bytes:
    chunks = [f"data: {json.dumps(event)}\n\n" for event in events]
    chunks.append("data: [DONE]\n\n")
    return "".join(chunks).encode()


def _sse_response(
    content: str = "Hello",
    *,
    model: str = "anthropic/claude-3.5-sonnet",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> httpx.Response:
    mid = max(1, len(content) // 2)
    events: list[dict] = [
        {"model": model, "choices": [{"delta": {"content": content[:mid]}}]},
    ]
    if content[mid:]:
        events.append({"choices": [{"delta": {"content": content[mid:]}}]})
    events.append(
        {
            "model": model,
            "choices": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }
    )
    return httpx.Response(
        200,
        content=_sse_body(*events),
        headers={"content-type": "text/event-stream"},
    )


def _enable_streaming(or_settings: OpenRouterSettings) -> None:
    or_settings.streaming_enabled = True
    or_settings.save()


@respx.mock
def test_stream_yields_deltas(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("Hello"))
    chunks = list(stream("chat", messages=MESSAGES))
    deltas = [chunk.delta for chunk in chunks if not chunk.done]
    assert "".join(deltas) == "Hello"
    assert chunks[-1].done is True
    assert chunks[-1].result is not None
    assert chunks[-1].result.content == "Hello"
    log = RequestLog.objects.get()
    assert log.status_code == 200
    assert log.prompt_tokens == 10
    assert log.completion_tokens == 5


@respx.mock
def test_chat_stream_true_collects(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("pong"))
    result = chat("chat", messages=MESSAGES, stream=True)
    assert result.content == "pong"


@respx.mock
def test_chat_uses_sse_when_setting_on(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    route = respx_mock.post(CHAT_URL).mock(return_value=_sse_response("streamed"))
    result = chat("chat", messages=MESSAGES)
    assert result.content == "streamed"
    body = json.loads(route.calls.last.request.content)
    assert body["stream"] is True
    assert body["stream_options"] == {"include_usage": True}


@respx.mock
def test_chat_stream_false_keeps_json(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="json-ok"))
    )
    result = chat("chat", messages=MESSAGES, stream=False)
    assert result.content == "json-ok"
    body = json.loads(route.calls.last.request.content)
    assert "stream" not in body


@respx.mock
def test_stream_fallback_on_429(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    _enable_streaming(or_settings)
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate"}),
            _sse_response("fallback-ok", model="openai/gpt-4o-mini"),
        ]
    )
    result = chat("chat", messages=MESSAGES, stream=True)
    assert result.content == "fallback-ok"
    assert result.model_used == "openai/gpt-4o-mini"
    assert RequestLog.objects.count() == 2


@respx.mock
def test_stream_skips_comments_and_list_delta(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    payload = {
        "choices": [
            {"delta": {"content": [{"type": "text", "text": "A"}]}}
        ]
    }
    body = (
        ": ping\n\n"
        f"data: {json.dumps(payload)}\n\n"
        "data: not-json\n\n"
        "data: [DONE]\n\n"
    )
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            content=body.encode(),
            headers={"content-type": "text/event-stream"},
        )
    )
    result = chat("chat", messages=MESSAGES, stream=True)
    assert result.content == "A"


@respx.mock
@pytest.mark.django_db(transaction=True)
def test_async_stream(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("async-stream"))

    async def _collect() -> str:
        parts: list[str] = []
        async for chunk in astream("chat", messages=MESSAGES):
            if chunk.delta:
                parts.append(chunk.delta)
            if chunk.done and chunk.result is not None:
                return chunk.result.content
        return "".join(parts)

    assert async_to_sync(_collect)() == "async-stream"


@respx.mock
def test_client_stream_method(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("via-class"))
    chunks = list(OpenRouterClient("chat").stream(MESSAGES))
    assert chunks[-1].result is not None
    assert chunks[-1].result.content == "via-class"


@respx.mock
def test_chat_uses_max_parallel_setting(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from django_openrouter.concurrency import ParallelismLimiter

    seen: list[int] = []
    original = ParallelismLimiter.slot

    def wrapped(self: ParallelismLimiter, limit: int):
        seen.append(limit)
        return original(self, limit)

    monkeypatch.setattr(ParallelismLimiter, "slot", wrapped)
    or_settings.max_parallel_requests = 3
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    chat("chat", messages=MESSAGES)
    assert seen == [3]


def test_stream_messages_required(or_settings: OpenRouterSettings) -> None:
    _enable_streaming(or_settings)
    with pytest.raises(TypeError):
        list(stream("chat"))

