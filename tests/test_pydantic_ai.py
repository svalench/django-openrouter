"""Pydantic AI ходит в OpenRouter через профиль: бюджет, fallback, журнал."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.test import override_settings
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent, ImageUrl, NativeOutput, PromptedOutput
from pydantic_ai.exceptions import UserError
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters

from django_openrouter import tracing
from django_openrouter.current_user import bound_session, bound_username
from django_openrouter.exceptions import (
    BudgetExceeded,
    OpenRouterAPIError,
    OpenRouterDisabled,
    RateLimitExceeded,
)
from django_openrouter.integrations.pydantic_ai import OpenRouterProfileModel
from django_openrouter.models import (
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db(transaction=True)

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


@pytest.fixture(autouse=True)
def _release_run_sync_clients() -> Iterator[None]:
    # run_sync держит loop через set_event_loop, а AsyncClient живёт на этом loop.
    # Без aclose/close pytest ловит ResourceWarning на сокете и незакрытом loop.
    yield
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    if loop.is_closed() or loop.is_running():
        return
    from django_openrouter import http_clients

    client = http_clients._async_clients.get(loop)
    if client is not None and not client.is_closed:
        loop.run_until_complete(client.aclose())
    if not loop.is_closed():
        loop.close()
    asyncio.set_event_loop(None)


_ROOT = Path(__file__).resolve().parents[1]


def _bodies(route: respx.Route) -> list[dict]:
    return [json.loads(call.request.content) for call in route.calls]


def _tool_payload(*calls: tuple[str, str, str], content: str | None = None) -> dict:
    payload = completion_payload(content=content or "", cost=Decimal("0.001"))
    payload["choices"] = [
        {
            "message": {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": arguments},
                    }
                    for call_id, name, arguments in calls
                ],
            },
            "finish_reason": "tool_calls",
        }
    ]
    return payload


def _sse_response(content: str = "Hello there", *, cost: str = "0.002") -> httpx.Response:
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
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": cost,
                "prompt_tokens_details": {"cached_tokens": 2},
                "completion_tokens_details": {"reasoning_tokens": 1},
            },
        }
    )
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    return httpx.Response(
        200,
        content=body.encode(),
        headers={"content-type": "text/event-stream"},
    )


@respx.mock
def test_run_sync_text_reports_usage_and_log(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    payload = completion_payload(content="Hello", cost=Decimal("0.001"))
    payload["choices"][0]["finish_reason"] = "stop"
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    result = Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert result.output == "Hello"
    assert result.response.model_name == "anthropic/claude-3.5-sonnet"
    assert result.response.provider_name == "openrouter"
    assert result.response.finish_reason == "stop"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.usage.cost == Decimal("0.001")
    log = RequestLog.objects.get(status_code=200)
    assert log.cost_usd == Decimal("0.001")
    assert log.username == "anonymous"


@respx.mock
def test_multiple_tools_round_trip(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json=_tool_payload(
                    ("call_a", "weather", '{"city": "Paris"}'),
                    ("call_b", "clock", '{"city": "Paris"}'),
                ),
            ),
            httpx.Response(
                200,
                json=completion_payload(content="sunny at noon", cost=Decimal("0.001")),
            ),
        ]
    )
    agent = Agent(OpenRouterProfileModel("chat"))

    @agent.tool_plain(strict=True)
    def weather(city: str) -> str:
        return f"sun in {city}"

    @agent.tool_plain
    def clock(city: str) -> str:
        return f"noon in {city}"

    result = agent.run_sync("Paris?")
    assert result.output == "sunny at noon"
    first, second = _bodies(route)
    by_name = {tool["function"]["name"]: tool["function"] for tool in first["tools"]}
    assert "weather" in by_name
    assert "clock" in by_name
    assert by_name["weather"]["strict"] is True
    tool_messages = [message for message in second["messages"] if message["role"] == "tool"]
    assert {message["tool_call_id"] for message in tool_messages} == {"call_a", "call_b"}
    contents = [message["content"] for message in tool_messages]
    assert "sun in Paris" in contents


@respx.mock
def test_structured_output_tool(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    class City(BaseModel):
        name: str

    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json=_tool_payload(("call_out", "final_result", '{"name": "Paris"}')),
        )
    )
    result = Agent(OpenRouterProfileModel("chat"), output_type=City).run_sync("Where?")
    assert result.output == City(name="Paris")
    assert result.usage.cost == Decimal("0.001")


@respx.mock
def test_native_output_sends_json_schema(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    class City(BaseModel):
        name: str

    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json=completion_payload(content='{"name": "Paris"}', cost=Decimal("0.001")),
        )
    )
    result = Agent(
        OpenRouterProfileModel("chat"),
        output_type=NativeOutput(City),
    ).run_sync("Where?")
    assert result.output == City(name="Paris")
    response_format = _bodies(route)[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["schema"]["properties"]["name"]["type"] == "string"


@respx.mock
def test_streaming_text_and_cost(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    or_settings.streaming_enabled = True
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(return_value=_sse_response("Hello there"))
    agent = Agent(OpenRouterProfileModel("chat"))
    with agent.run_stream_sync("Hi") as result:
        chunks = list(result.stream_text(delta=True, debounce_by=None))
        assert "".join(chunks) == "Hello there"
        assert result.usage.cost == Decimal("0.002")
        assert result.usage.input_tokens == 10
        assert result.response.finish_reason == "stop"
        assert result.response.usage.cache_read_tokens == 2
        assert result.response.usage.output_reasoning_tokens == 1
    assert RequestLog.objects.get(status_code=200).completion_tokens == 5


@respx.mock
def test_profile_fallback_on_429(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": "slow down"}),
            httpx.Response(
                200,
                json=completion_payload(
                    content="from fallback",
                    model=fallback_model.model_id,
                    cost=Decimal("0.001"),
                ),
            ),
        ]
    )
    result = Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert result.output == "from fallback"
    assert result.response.model_name == fallback_model.model_id
    statuses = list(RequestLog.objects.order_by("pk").values_list("status_code", flat=True))
    assert statuses == [429, 200]


@respx.mock
def test_chain_exhaustion_is_not_a_silent_extra_model(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "down"}),
            httpx.Response(500, json={"error": "still down"}),
        ]
    )
    with pytest.raises(OpenRouterAPIError):
        Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert route.call_count == 2


@respx.mock
def test_budget_exceeded_is_not_wrapped(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model,
    fallback_model,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
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
        Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert route.call_count == 0


@respx.mock
def test_rate_limit_exceeded(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model,
) -> None:
    profile.max_requests_per_day = 1
    profile.save()
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("0"),
    )
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    with pytest.raises(RateLimitExceeded):
        Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert route.call_count == 0


@respx.mock
def test_async_run(respx_mock: respx.MockRouter, or_settings: OpenRouterSettings) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="async", cost=Decimal("0.001"))
        )
    )
    agent = Agent(OpenRouterProfileModel("chat"))
    result = async_to_sync(agent.run)("Hi")
    assert result.output == "async"
    assert result.usage.cost == Decimal("0.001")


@pytest.mark.asyncio
@respx.mock
async def test_async_run_on_event_loop(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="awaited", cost=Decimal("0.001"))
        )
    )
    result = await Agent(OpenRouterProfileModel("chat")).run("Hi")
    assert result.output == "awaited"


@respx.mock
def test_image_input(respx_mock: respx.MockRouter, or_settings: OpenRouterSettings) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="a png", cost=Decimal("0.001"))
        )
    )
    Agent(OpenRouterProfileModel("chat")).run_sync(
        ["What is this?", BinaryContent(data=b"\x89PNG\r\n", media_type="image/png")]
    )
    content = _bodies(route)[0]["messages"][-1]["content"]
    assert isinstance(content, list)
    image = next(part for part in content if part["type"] == "image_url")
    assert image["image_url"]["url"].startswith("data:image/png;base64,")


@respx.mock
def test_reasoning_and_profile_sampling_caps(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    profile.max_tokens = 32
    profile.temperature = 0.2
    profile.save()
    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json=completion_payload(content="capped", cost=Decimal("0.001"))),
            httpx.Response(200, json=completion_payload(content="lower", cost=Decimal("0.001"))),
            httpx.Response(200, json=completion_payload(content="off", cost=Decimal("0.001"))),
            httpx.Response(200, json=completion_payload(content="high", cost=Decimal("0.001"))),
        ]
    )
    model = OpenRouterProfileModel("chat")
    Agent(model).run_sync("Hi", model_settings={"max_tokens": 1000, "temperature": 1.5})
    Agent(model).run_sync("Hi", model_settings={"temperature": 0.1})
    Agent(model).run_sync("Hi", model_settings={"thinking": False})
    Agent(model).run_sync("Hi", model_settings={"thinking": "high", "stop_sequences": ["END"]})
    capped, lower, off, high = _bodies(route)
    assert capped["max_tokens"] == 32
    assert capped["temperature"] == 0.2
    # Агент не передал max_tokens — в тело уходит потолок профиля, не запрос.
    assert lower["max_tokens"] == 32
    assert lower["temperature"] == 0.1
    assert off["reasoning"] == {"enabled": False}
    assert high["reasoning"] == {"enabled": True, "effort": "high"}
    assert high["stop"] == ["END"]


@respx.mock
def test_temperature_clamped_to_two(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(cost=Decimal("0.001")))
    )
    Agent(OpenRouterProfileModel("chat")).run_sync("Hi", model_settings={"temperature": 3})
    assert _bodies(route)[0]["temperature"] == 2.0


@respx.mock
def test_timeout_is_a_call_option_not_a_json_field(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}
    from django_openrouter.client import AsyncOpenRouterClient

    real_chat = AsyncOpenRouterClient.chat

    async def spy(self: AsyncOpenRouterClient, messages: object, **overrides: object) -> object:
        captured.update(overrides)
        return await real_chat(self, messages, **overrides)

    monkeypatch.setattr(AsyncOpenRouterClient, "chat", spy)
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(cost=Decimal("0.001")))
    )
    Agent(OpenRouterProfileModel("chat")).run_sync("Hi", model_settings={"timeout": 12})
    assert captured["request_timeout"] == 12.0
    assert "request_timeout" not in json.loads(respx_mock.calls[0].request.content)


@respx.mock
def test_bound_username_reaches_the_log(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(cost=Decimal("0.001")))
    )
    with bound_username("celery-worker"):
        Agent(OpenRouterProfileModel("chat")).run_sync("Hi")
    assert RequestLog.objects.get(status_code=200).username == "celery-worker"


def test_kill_switch(or_settings: OpenRouterSettings) -> None:
    or_settings.enabled = False
    or_settings.save()
    with pytest.raises(OpenRouterDisabled):
        Agent(OpenRouterProfileModel("chat")).run_sync("Hi")


def test_package_root_does_not_import_pydantic_ai() -> None:
    root = (_ROOT / "src" / "django_openrouter" / "__init__.py").read_text(encoding="utf-8")
    init = _ROOT / "src" / "django_openrouter" / "integrations" / "__init__.py"
    integrations = init.read_text(encoding="utf-8")
    assert "pydantic_ai" not in root
    assert "pydantic_ai" not in integrations


def test_empty_profile_slug_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        OpenRouterProfileModel("  ")


def test_profile_must_be_a_slug() -> None:
    with pytest.raises(TypeError, match="slug"):
        OpenRouterProfileModel(1)  # type: ignore[arg-type]


@respx.mock
def test_default_profile_forwards_sampling(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(cost=Decimal("0.001")))
    )
    model = OpenRouterProfileModel()
    assert model.model_name == "default"
    assert model.system == "openrouter"
    assert model.provider is None
    Agent(model).run_sync(
        "Hi",
        model_settings={
            "temperature": -1,
            "timeout": httpx.Timeout(5.0),
            "top_p": 0.9,
            "top_k": 10,
            "seed": 1,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "logit_bias": {"15": -1},
            "parallel_tool_calls": False,
        },
    )
    body = _bodies(route)[0]
    assert body["model"] == "anthropic/claude-3.5-sonnet"
    assert body["temperature"] == 0.0
    assert body["top_p"] == 0.9
    assert body["top_k"] == 10
    assert body["seed"] == 1
    assert body["presence_penalty"] == 0.1
    assert body["frequency_penalty"] == 0.2
    assert body["logit_bias"] == {"15": -1}
    assert body["parallel_tool_calls"] is False
    assert "request_timeout" not in body


@respx.mock
def test_prompted_output_and_thinking_levels(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    class City(BaseModel):
        name: str

    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json=completion_payload(content='{"name": "Paris"}', cost=Decimal("0.001")),
            ),
            httpx.Response(200, json=completion_payload(content="yes", cost=Decimal("0.001"))),
            httpx.Response(200, json=completion_payload(content="low", cost=Decimal("0.001"))),
            httpx.Response(200, json=completion_payload(content="max", cost=Decimal("0.001"))),
        ]
    )
    model = OpenRouterProfileModel("chat")
    result = Agent(model, output_type=PromptedOutput(City)).run_sync("Where?")
    assert result.output == City(name="Paris")
    Agent(model).run_sync("Hi", model_settings={"thinking": True})
    Agent(model).run_sync("Hi", model_settings={"thinking": "minimal"})
    Agent(model).run_sync("Hi", model_settings={"thinking": "max"})
    prompted, on, low, high = _bodies(route)
    assert prompted["response_format"] == {"type": "json_object"}
    assert on["reasoning"] == {"enabled": True, "effort": "medium"}
    assert low["reasoning"] == {"enabled": True, "effort": "low"}
    assert high["reasoning"] == {"enabled": True, "effort": "max"}


@respx.mock
def test_instructions_image_url_and_reasoning_round_trip(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    reasoned = completion_payload(content="done", cost=Decimal("0.001"))
    reasoned["choices"][0]["message"]["reasoning"] = "because"
    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json=reasoned),
            httpx.Response(200, json=completion_payload(content="seen", cost=Decimal("0.001"))),
        ]
    )
    model = OpenRouterProfileModel("chat")
    first = Agent(model, instructions="Be brief").run_sync(
        [ImageUrl(url="https://example.com/a.png", vendor_metadata={"detail": "low"})]
    )
    thoughts = [part for part in first.response.parts if isinstance(part, ThinkingPart)]
    assert thoughts[0].content == "because"
    assert first.response.provider_response_id == "gen-test"
    Agent(model).run_sync("Next", message_history=first.all_messages())
    first_body, second_body = _bodies(route)
    assert any("Be brief" in str(message.get("content")) for message in first_body["messages"])
    image_message = next(
        message for message in first_body["messages"] if isinstance(message["content"], list)
    )
    assert image_message["content"][0]["image_url"] == {
        "url": "https://example.com/a.png",
        "detail": "low",
    }
    assistant = next(
        message for message in second_body["messages"] if message["role"] == "assistant"
    )
    assert assistant["reasoning"] == "because"


@respx.mock
def test_tool_choice_none_and_single_required_tool(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json=completion_payload(content="text", cost=Decimal("0.001"))),
            httpx.Response(
                200,
                json=_tool_payload(("call_out", "final_result", '{"name": "Paris"}')),
            ),
        ]
    )
    agent = Agent(OpenRouterProfileModel("chat"))

    @agent.tool_plain(strict=True)
    def weather(city: str) -> str:
        return f"sun in {city}"

    assert agent.run_sync("Hi", model_settings={"tool_choice": "none"}).output == "text"

    class City(BaseModel):
        name: str

    forced_agent = Agent(OpenRouterProfileModel("chat"), output_type=City)

    @forced_agent.tool_plain
    def lookup(city: str) -> str:
        return city

    result = forced_agent.run_sync("Where?", model_settings={"tool_choice": ["final_result"]})
    assert result.output == City(name="Paris")
    skipped, forced = _bodies(route)[:2]
    assert "tools" not in skipped
    names = [tool["function"]["name"] for tool in forced["tools"]]
    assert names == ["final_result"]
    assert forced["tool_choice"] == {"type": "function", "function": {"name": "final_result"}}


@respx.mock
def test_stream_maps_reasoning_and_tool_calls(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    or_settings.streaming_enabled = True
    or_settings.save()
    events = [
        {
            "model": "anthropic/claude-3.5-sonnet",
            "choices": [{"delta": {"content": "Hi"}}],
        },
        {
            "choices": [
                {
                    "delta": {
                        "reasoning": "hmm",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_z",
                                "type": "function",
                                "function": {"name": "weather", "arguments": "{}"},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        {
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "cost": "0.002"},
        },
    ]
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            content=body.encode(),
            headers={"content-type": "text/event-stream"},
        )
    )
    model = OpenRouterProfileModel("chat")
    messages = [ModelRequest(parts=[UserPromptPart(content="Hi")])]

    async def consume() -> tuple[ModelResponse, str]:
        async with model.request_stream(messages, None, ModelRequestParameters()) as streamed:
            async for _event in streamed:
                pass
            return streamed.get(), streamed.model_name

    response, answered = async_to_sync(consume)()
    assert any(isinstance(part, ThinkingPart) and part.content == "hmm" for part in response.parts)
    tool = next(part for part in response.parts if isinstance(part, ToolCallPart))
    assert tool.tool_name == "weather"
    assert tool.tool_call_id == "call_z"
    assert response.finish_reason == "tool_call"
    assert answered == "anthropic/claude-3.5-sonnet"


@pytest.mark.asyncio
async def test_non_image_binary_is_rejected(or_settings: OpenRouterSettings) -> None:
    model = OpenRouterProfileModel("chat")
    messages = [
        ModelRequest(
            parts=[UserPromptPart(content=[BinaryContent(data=b"abc", media_type="audio/wav")])]
        )
    ]
    with pytest.raises(UserError, match="image binary"):
        await model.request(messages, None, ModelRequestParameters())


@respx.mock
def test_conversation_id_is_session_until_bound_session(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="ok", cost=Decimal("0.001"))
        )
    )
    agent = Agent(OpenRouterProfileModel("chat"))
    agent.run_sync("Hi", conversation_id="ticket-42")
    assert _bodies(route)[0]["session_id"] == "ticket-42"
    assert "trace_id" not in _bodies(route)[0]
    log = RequestLog.objects.get(status_code=200)
    assert log.session_id == "ticket-42"
    assert log.trace_id

    with bound_session("celery-job", metadata={"feature": "support"}):
        agent.run_sync("Hi", conversation_id="ticket-42")
    body = _bodies(route)[1]
    assert body["session_id"] == "celery-job"
    assert body["metadata"] == {"feature": "support"}
    bound = RequestLog.objects.get(session_id="celery-job")
    assert bound.metadata == {"feature": "support"}
    assert bound.trace_id != log.trace_id


@respx.mock
def test_parent_span_is_the_log_trace_id(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    tracing._enabled_cache = None
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("pydantic-ai-profile")
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="ok", cost=Decimal("0.001"))
        )
    )
    agent = Agent(OpenRouterProfileModel("chat"))
    with override_settings(OPENROUTER={"OTEL": True, "RETRY_BACKOFF": 0}):
        tracing._enabled_cache = None
        original = tracing._get_tracer
        tracing._get_tracer = lambda: tracer  # type: ignore[method-assign]
        try:
            with tracer.start_as_current_span("agent-run"):
                expected = f"{otel_trace.get_current_span().get_span_context().trace_id:032x}"
                agent.run_sync("Hi", conversation_id="span-session")
        finally:
            tracing._get_tracer = original  # type: ignore[method-assign]
            tracing._enabled_cache = None
    log = RequestLog.objects.get(session_id="span-session")
    assert log.trace_id == expected
    assert exporter.get_finished_spans()


@respx.mock
def test_overlong_conversation_id_is_omitted(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(content="ok", cost=Decimal("0.001"))
        )
    )
    model = OpenRouterProfileModel("chat")
    messages = [ModelRequest(parts=[UserPromptPart(content="Hi")], conversation_id="x" * 300)]

    async_to_sync(model.request)(messages, None, ModelRequestParameters())
    assert "session_id" not in _bodies(route)[0]
    assert RequestLog.objects.get(status_code=200).session_id is None
