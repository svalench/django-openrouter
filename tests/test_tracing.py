"""OpenTelemetry-спаны вызовов OpenRouter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.test import override_settings
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from django_openrouter import achat, astream, chat, generate_image, stream, tracing, transcribe
from django_openrouter.current_user import bound_username
from django_openrouter.exceptions import BudgetExceeded, RateLimitExceeded
from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    ProfileKind,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
STT_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
MESSAGES = [{"role": "user", "content": "Hi"}]
AUDIO = b"\x1a\x45\xdf\xa3webm"


def redact_content(text: str, *, kind: str) -> str:
    if kind == "prompt":
        return text.replace("Hi", "[prompt]")
    return text.replace("pong", "[completion]")


def broken_redactor(text: str, *, kind: str) -> str:
    raise RuntimeError("redactor failed")


class _Paced(httpx.SyncByteStream):
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


def _otel(**extra: object) -> dict[str, object]:
    options: dict[str, object] = {
        "OTEL": True,
        "RETRY_BACKOFF": 0,
        "CACHE_TIMEOUT": 60,
        "CACHE_ALIAS": "default",
    }
    options.update(extra)
    return options


def _sse(content: str = "Hello", *, model: str = "anthropic/claude-3.5-sonnet") -> httpx.Response:
    events = [
        {"model": model, "choices": [{"delta": {"content": content}, "finish_reason": None}]},
        {
            "model": model,
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": "0.000105"},
        },
    ]
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    body += "data: [DONE]\n\n"
    return httpx.Response(
        200,
        content=body.encode(),
        headers={"content-type": "text/event-stream"},
    )


def _attrs(span: object) -> dict:
    return dict(span.attributes)  # type: ignore[attr-defined]


def _role(spans: list, role: str) -> list:
    return [span for span in spans if _attrs(span).get("openrouter.span.role") == role]


@pytest.fixture(autouse=True)
def _reset_otel_flag() -> None:
    tracing._enabled_cache = None
    yield
    tracing._enabled_cache = None


@pytest.fixture
def otel_exporter(monkeypatch: pytest.MonkeyPatch) -> tuple[InMemorySpanExporter, object]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("django-openrouter-test")
    monkeypatch.setattr(tracing, "_get_tracer", lambda: tracer)
    return exporter, tracer


@pytest.fixture
def whisper() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="openai/whisper-large-v3-turbo",
        name="Whisper",
        context_length=0,
        pricing={"prompt": "0.00000333", "completion": "0"},
        modality="audio->transcription",
        output_modalities=["transcription"],
        is_active=True,
    )


@pytest.fixture
def dictation(whisper: OpenRouterModel) -> UsageProfile:
    return UsageProfile.objects.create(
        name="dictation",
        model=whisper,
        kind=ProfileKind.TRANSCRIPTION,
        language="ru",
        is_active=True,
    )


@pytest.fixture
def stt_settings(or_settings: OpenRouterSettings, dictation: UsageProfile) -> OpenRouterSettings:
    or_settings.default_transcription_profile = dictation
    or_settings.save()
    return or_settings


def test_otel_disabled_by_default_does_not_start_spans(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    monkeypatch.setattr(
        tracing,
        "_get_tracer",
        lambda: (_ for _ in ()).throw(AssertionError("tracer")),
    )

    @respx.mock
    def _run() -> None:
        respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
        result = chat("chat", messages=MESSAGES)
        assert result.content == "Hello"

    _run()
    log = RequestLog.objects.get()
    assert log.trace_id is not None
    assert len(log.trace_id) == 32


def test_missing_opentelemetry_package_does_not_break_calls() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(root), env.get("PYTHONPATH", "")]
    )
    env["DJANGO_SETTINGS_MODULE"] = "tests.settings"
    script = """
import builtins
real_import = builtins.__import__

def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "opentelemetry" or name.startswith("opentelemetry."):
        raise ImportError(name)
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded
import django
django.setup()
from django_openrouter import tracing
assert tracing._HAS_OTEL is False
assert tracing.otel_enabled() is False
print("ok")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr


@respx.mock
def test_chat_span_attributes_and_otel_trace_id(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    payload = completion_payload(
        content="pong",
        prompt_tokens=10,
        completion_tokens=5,
        cost="0.000105",
    )
    payload["choices"][0]["finish_reason"] = "stop"
    payload["model"] = "anthropic/claude-3.5-sonnet"
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    with override_settings(OPENROUTER=_otel()), bound_username("alice"):
        result = chat(
            "chat",
            messages=MESSAGES,
            session_id="sess",
            metadata={"feature": "chat", "api_key": "sk-test"},
            trace={"feature.flag": "beta", "authorization": "secret", "n": 1},
        )
    assert result.content == "pong"
    spans = exporter.get_finished_spans()
    operation = _role(spans, "operation")
    attempt = _role(spans, "attempt")
    assert len(operation) == 1
    assert len(attempt) == 1
    parent = operation[0]
    child = attempt[0]
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id
    attributes = _attrs(parent)
    assert attributes["gen_ai.system"] == "openrouter"
    assert attributes["gen_ai.operation.name"] == "chat"
    assert attributes["gen_ai.request.model"] == "anthropic/claude-3.5-sonnet"
    assert attributes["gen_ai.response.model"] == "anthropic/claude-3.5-sonnet"
    assert attributes["gen_ai.usage.input_tokens"] == 10
    assert attributes["gen_ai.usage.output_tokens"] == 5
    assert list(attributes["gen_ai.response.finish_reasons"]) == ["stop"]
    assert attributes["openrouter.cost_usd"] == str(result.cost_usd)
    assert attributes["openrouter.profile"] == "chat"
    assert attributes["openrouter.status_code"] == 200
    assert attributes["openrouter.latency_ms"] >= 0
    assert attributes["openrouter.username"] == "alice"
    assert attributes["openrouter.session_id"] == "sess"
    assert attributes["feature.flag"] == "beta"
    assert attributes["n"] == 1
    assert "authorization" not in attributes
    assert "gen_ai.prompt" not in attributes
    assert "gen_ai.completion" not in attributes
    metadata = json.loads(attributes["openrouter.metadata"])
    assert metadata == {"feature": "chat"}
    assert "api_key" not in attributes["openrouter.metadata"]
    blob = json.dumps(attributes)
    assert "Bearer" not in blob
    assert "sk-test" not in blob
    child_attributes = _attrs(child)
    assert child_attributes["openrouter.fallback_index"] == 0
    assert child_attributes["openrouter.retry_index"] == 0
    assert child_attributes["gen_ai.request.model"] == profile.model.model_id
    log = RequestLog.objects.get()
    assert log.trace_id == f"{parent.context.trace_id:032x}"
    assert log.username == "alice"
    assert log.metadata == {"feature": "chat", "api_key": "sk-test"}
    assert parent.status.status_code == StatusCode.OK


@respx.mock
def test_explicit_trace_id_is_attribute_not_span_context(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with override_settings(OPENROUTER=_otel()):
        chat("chat", messages=MESSAGES, trace_id="custom-trace")
    parent = _role(exporter.get_finished_spans(), "operation")[0]
    assert _attrs(parent)["openrouter.trace_id"] == "custom-trace"
    assert RequestLog.objects.get().trace_id == "custom-trace"
    assert f"{parent.context.trace_id:032x}" != "custom-trace"


@respx.mock
def test_fallback_and_retry_are_child_spans(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model: OpenRouterModel,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    or_settings.max_retries = 1
    or_settings.save()
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "boom"}),
            httpx.Response(429, json={"error": "rate"}),
            httpx.Response(
                200,
                json=completion_payload(content="ok", model=fallback_model.model_id),
            ),
        ]
    )
    with override_settings(OPENROUTER=_otel()):
        result = chat("chat", messages=MESSAGES)
    assert result.model_used == fallback_model.model_id
    attempts = _role(exporter.get_finished_spans(), "attempt")
    assert [
        (_attrs(span)["openrouter.fallback_index"], _attrs(span)["openrouter.retry_index"])
        for span in attempts
    ] == [(0, 0), (0, 1), (1, 0)]
    assert _attrs(attempts[0])["openrouter.status_code"] == 500
    assert attempts[0].status.status_code == StatusCode.ERROR
    assert _attrs(attempts[2])["gen_ai.response.model"] == fallback_model.model_id
    parent = _role(exporter.get_finished_spans(), "operation")[0]
    assert parent.status.status_code == StatusCode.OK
    assert len({log.trace_id for log in RequestLog.objects.all()}) == 1


@respx.mock
def test_async_chat_span(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="async"))
    )
    with override_settings(OPENROUTER=_otel()):
        result = async_to_sync(achat)("chat", messages=MESSAGES)
    assert result.content == "async"
    assert len(_role(exporter.get_finished_spans(), "operation")) == 1
    assert len(_role(exporter.get_finished_spans(), "attempt")) == 1


@respx.mock
def test_stream_span_covers_consumption_and_records_ttft(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    or_settings.streaming_enabled = True
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(return_value=_sse("Hello"))
    with override_settings(OPENROUTER=_otel()):
        generated = stream("chat", messages=MESSAGES)
        first = next(generated)
        assert first.delta
        assert exporter.get_finished_spans() == ()
        chunks = [first, *list(generated)]
    assert chunks[-1].done is True
    spans = exporter.get_finished_spans()
    parent = _role(spans, "operation")[0]
    child = _role(spans, "attempt")[0]
    assert _attrs(parent)["openrouter.stream"] is True
    assert _attrs(parent)["openrouter.time_to_first_token_ms"] >= 0
    assert _attrs(child)["openrouter.time_to_first_token_ms"] >= 0
    assert parent.status.status_code == StatusCode.OK


@respx.mock
def test_interrupted_stream_is_error(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    or_settings.streaming_enabled = True
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(return_value=_sse("Hello there"))
    with override_settings(OPENROUTER=_otel()):
        generated = stream("chat", messages=MESSAGES)
        next(generated)
        generated.close()
    spans = exporter.get_finished_spans()
    parent = _role(spans, "operation")[0]
    child = _role(spans, "attempt")[0]
    assert parent.status.status_code == StatusCode.ERROR
    assert child.status.status_code == StatusCode.ERROR
    assert _attrs(child)["openrouter.status_code"] == 499
    assert any(event.name == "exception" for event in child.events)
    assert RequestLog.objects.get().status_code == 499


@respx.mock
def test_async_stream_span(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    or_settings.streaming_enabled = True
    or_settings.save()
    respx_mock.post(CHAT_URL).mock(return_value=_sse("async-stream"))

    async def collect() -> str:
        parts: list[str] = []
        async for chunk in astream("chat", messages=MESSAGES):
            if chunk.delta:
                parts.append(chunk.delta)
        return "".join(parts)

    with override_settings(OPENROUTER=_otel()):
        assert async_to_sync(collect)() == "async-stream"
    spans = exporter.get_finished_spans()
    assert _attrs(_role(spans, "operation")[0])["openrouter.time_to_first_token_ms"] >= 0


@respx.mock
def test_budget_and_rate_limit_mark_parent_error(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    profile.budget_usd_per_day = "0.01"
    profile.save()
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd="0.01",
    )
    with override_settings(OPENROUTER=_otel()), pytest.raises(BudgetExceeded):
        chat("chat", messages=MESSAGES)
    parent = _role(exporter.get_finished_spans(), "operation")[0]
    assert parent.status.status_code == StatusCode.ERROR
    assert any(event.name == "exception" for event in parent.events)
    assert _role(exporter.get_finished_spans(), "attempt") == []
    assert route.call_count == 0

    exporter.clear()
    profile.budget_usd_per_day = None
    profile.max_requests_per_day = 1
    profile.save()
    with override_settings(OPENROUTER=_otel()), pytest.raises(RateLimitExceeded):
        chat("chat", messages=MESSAGES)
    parent = _role(exporter.get_finished_spans(), "operation")[0]
    assert parent.status.status_code == StatusCode.ERROR
    assert route.call_count == 0


@respx.mock
def test_timeout_marks_error(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    raw = json.dumps(completion_payload(content="late")).encode()
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, stream=_Paced([raw[:1], raw[1:]], pause=0.4))
    )
    from django_openrouter.exceptions import OpenRouterTimeout

    with override_settings(OPENROUTER=_otel()), pytest.raises(OpenRouterTimeout):
        chat("chat", messages=MESSAGES, total_timeout=0.15)
    spans = exporter.get_finished_spans()
    parent = _role(spans, "operation")[0]
    child = _role(spans, "attempt")[0]
    assert parent.status.status_code == StatusCode.ERROR
    assert child.status.status_code == StatusCode.ERROR
    assert _attrs(child)["openrouter.status_code"] == 499


@respx.mock
def test_content_capture_and_redaction(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="pong"))
    )
    messages = [{"role": "user", "content": "Hi sk-test"}]
    with override_settings(
        OPENROUTER=_otel(
            OTEL_CAPTURE_CONTENT=True,
            OTEL_CONTENT_REDACTOR="tests.test_tracing.redact_content",
        )
    ):
        chat("chat", messages=messages)
    attributes = _attrs(_role(exporter.get_finished_spans(), "operation")[0])
    assert "[prompt]" in attributes["gen_ai.prompt"]
    assert "Hi" not in attributes["gen_ai.prompt"]
    assert "[redacted]" in attributes["gen_ai.prompt"]
    assert "sk-test" not in attributes["gen_ai.prompt"]
    assert attributes["gen_ai.completion"] == "[completion]"
    child = _attrs(_role(exporter.get_finished_spans(), "attempt")[0])
    assert child["gen_ai.prompt"] == attributes["gen_ai.prompt"]


@respx.mock
def test_redactor_failure_omits_content(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with override_settings(
        OPENROUTER=_otel(
            OTEL_CAPTURE_CONTENT=True,
            OTEL_CONTENT_REDACTOR="tests.test_tracing.broken_redactor",
        )
    ):
        chat("chat", messages=MESSAGES)
    attributes = _attrs(_role(exporter.get_finished_spans(), "operation")[0])
    assert "gen_ai.prompt" not in attributes
    assert "gen_ai.completion" not in attributes


@respx.mock
def test_generate_image_is_one_parent_span(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with override_settings(OPENROUTER=_otel()):
        generate_image("A red crane", profile="chat")
    operations = _role(exporter.get_finished_spans(), "operation")
    assert len(operations) == 1
    assert _attrs(operations[0])["gen_ai.operation.name"] == "generate_image"
    assert _attrs(_role(exporter.get_finished_spans(), "attempt")[0])["gen_ai.operation.name"] == (
        "generate_image"
    )


@respx.mock
def test_transcribe_span(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, _tracer = otel_exporter
    respx_mock.post(STT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "text": "привет",
                "model": "openai/whisper-large-v3-turbo",
                "usage": {"cost": "0.0001", "seconds": "1", "input_tokens": 1, "output_tokens": 2},
            },
        )
    )
    with override_settings(OPENROUTER=_otel(OTEL_CAPTURE_CONTENT=True)):
        result = transcribe(
            AUDIO,
            filename="note.webm",
            content_type="audio/webm",
            profile="dictation",
            prompt="имена",
        )
    parent = _role(exporter.get_finished_spans(), "operation")[0]
    attributes = _attrs(parent)
    assert attributes["gen_ai.operation.name"] == "transcription"
    assert attributes["gen_ai.response.model"] == result.model_used
    assert attributes["openrouter.profile"] == "dictation"
    assert "имена" in attributes["gen_ai.prompt"]
    assert "привет" in attributes["gen_ai.completion"]
    assert "webm" not in attributes["gen_ai.prompt"]
    sent = json.loads(respx_mock.calls.last.request.content)
    assert "data" in sent["input_audio"]


@respx.mock
def test_span_nests_under_active_context(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    otel_exporter: tuple[InMemorySpanExporter, object],
) -> None:
    exporter, tracer = otel_exporter
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with override_settings(OPENROUTER=_otel()):
        with tracer.start_as_current_span("django.request"):  # type: ignore[attr-defined]
            chat("chat", messages=MESSAGES)
    spans = exporter.get_finished_spans()
    host = next(span for span in spans if span.name == "django.request")
    parent = _role(spans, "operation")[0]
    assert parent.parent is not None
    assert parent.parent.span_id == host.context.span_id


@respx.mock
def test_installed_but_disabled_flag_skips_spans(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    monkeypatch.setattr(tracing, "_HAS_OTEL", False)

    def explode() -> None:
        raise AssertionError("otel")

    monkeypatch.setattr(tracing, "_get_tracer", explode)
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    with override_settings(OPENROUTER=_otel()):
        assert chat("chat", messages=MESSAGES).content == "Hello"
