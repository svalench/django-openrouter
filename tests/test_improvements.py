from __future__ import annotations

import asyncio
import json
import threading
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from django_openrouter import client as client_module
from django_openrouter.client import achat, chat, stream
from django_openrouter.concurrency import ParallelismLimiter
from django_openrouter.exceptions import OpenRouterAPIError
from django_openrouter.fields import EncryptedTextField
from django_openrouter.log_backends import LogBackend, LogRecord, dispatch_log, make_record
from django_openrouter.models import (
    CLIENT_CLOSED_STATUS,
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from django_openrouter.signals import request_logged
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MESSAGES = [{"role": "user", "content": "Hi"}]


def _sse(*events: dict) -> httpx.Response:
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    return httpx.Response(
        200, content=body.encode(), headers={"content-type": "text/event-stream"}
    )


def _enable_streaming(or_settings: OpenRouterSettings) -> None:
    or_settings.streaming_enabled = True
    or_settings.save()


# --- резерв лимитов ---------------------------------------------------------


def test_usage_summary_single_query(
    profile: UsageProfile, paid_model: OpenRouterModel, django_assert_num_queries
) -> None:
    RequestLog.objects.create(
        profile=profile, model=paid_model, status_code=200, cost_usd=Decimal("1")
    )
    with django_assert_num_queries(1):
        day, month = profile.usage_summary()
    assert (day.request_count, month.total_cost) == (1, Decimal("1"))


@respx.mock
def test_interrupted_stream_keeps_budget_reservation(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings, profile: UsageProfile
) -> None:
    _enable_streaming(or_settings)
    profile.budget_usd_per_day = Decimal("4.00")
    profile.save()
    respx_mock.post(CHAT_URL).mock(
        return_value=_sse(
            {"choices": [{"delta": {"content": "a"}}]},
            {"choices": [{"delta": {"content": "b"}}]},
        )
    )
    gen = stream("chat", messages=MESSAGES)
    next(gen)
    gen.close()
    log = RequestLog.objects.get()
    assert log.status_code == CLIENT_CLOSED_STATUS
    assert log.cost_usd == Decimal("3.00")


@respx.mock
def test_retry_reserves_each_attempt(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    or_settings.max_retries = 1
    or_settings.save()
    profile.max_requests_per_day = 10
    profile.save()
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "x"}),
            httpx.Response(200, json=completion_payload()),
        ]
    )
    chat("chat", messages=MESSAGES)
    assert sorted(RequestLog.objects.values_list("status_code", flat=True)) == [200, 500]


# --- стоимость и payload ------------------------------------------------------


@respx.mock
def test_usage_cost_is_preferred_and_usage_include_sent(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(cost=Decimal("0.5")))
    )
    result = chat("chat", messages=MESSAGES)
    assert result.cost_usd == Decimal("0.5")
    assert RequestLog.objects.get().cost_usd == Decimal("0.5")
    body = json.loads(route.calls.last.request.content)
    assert body["usage"] == {"include": True}


@respx.mock
def test_tool_calls_and_finish_reason(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    payload = completion_payload(content="")
    payload["choices"] = [
        {
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": None,
                "reasoning": "думаю",
                "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "f"}}],
            },
        }
    ]
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=payload))
    result = chat("chat", messages=MESSAGES)
    assert result.finish_reason == "tool_calls"
    assert result.tool_calls[0]["id"] == "c1"
    assert result.reasoning == "думаю"


def test_unsupported_override_warns(
    profile: UsageProfile, paid_model: OpenRouterModel, caplog: pytest.LogCaptureFixture
) -> None:
    client_module._build_payload(profile, paid_model, MESSAGES, {"tools": [], "provider": {}})
    assert "tools" in caplog.text
    assert "provider" not in caplog.text


# --- ошибки в теле 200 --------------------------------------------------------


@respx.mock
def test_body_error_triggers_fallback(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model: OpenRouterModel,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json={"error": {"message": "upstream down"}}),
            httpx.Response(200, json=completion_payload(content="ok")),
        ]
    )
    assert chat("chat", messages=MESSAGES).content == "ok"
    assert RequestLog.objects.filter(status_code=502).exists()


@respx.mock
def test_invalid_json_is_api_error(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, content=b"<html>"))
    with pytest.raises(OpenRouterAPIError) as exc:
        chat("chat", messages=MESSAGES)
    assert exc.value.status_code == 502


# --- retry --------------------------------------------------------------------


@respx.mock
def test_429_retried_with_retry_after(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    or_settings.max_retries = 1
    or_settings.save()
    sleeps: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", sleeps.append)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "rate"}),
            httpx.Response(200, json=completion_payload(content="after-wait")),
        ]
    )
    assert chat("chat", messages=MESSAGES).content == "after-wait"
    assert sleeps == [2.0]


@override_settings(OPENROUTER={"RETRY_BACKOFF": 1})
def test_retry_delay_exponential() -> None:
    assert 0.5 <= client_module._retry_delay(0) <= 1.0
    assert 2.0 <= client_module._retry_delay(2) <= 4.0
    assert client_module._retry_delay(0, "999") == 30.0


# --- стриминг -----------------------------------------------------------------


@respx.mock
def test_interrupted_stream_is_logged(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    respx_mock.post(CHAT_URL).mock(
        return_value=_sse(
            {"choices": [{"delta": {"content": "a"}}]},
            {"choices": [{"delta": {"content": "b"}}]},
        )
    )
    gen = stream("chat", messages=MESSAGES)
    assert next(gen).delta == "a"
    gen.close()
    log = RequestLog.objects.get()
    assert log.status_code == CLIENT_CLOSED_STATUS


@respx.mock
def test_stream_merges_tool_call_deltas(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    _enable_streaming(or_settings)
    call = {"index": 0, "id": "c1", "function": {"name": "get", "arguments": '{"a"'}}
    tail = {"index": 0, "function": {"arguments": ": 1}"}}
    respx_mock.post(CHAT_URL).mock(
        return_value=_sse(
            {"choices": [{"delta": {"tool_calls": [call]}}]},
            {"choices": [{"delta": {"tool_calls": [tail]}, "finish_reason": "tool_calls"}]},
        )
    )
    result = chat("chat", messages=MESSAGES, stream=True)
    assert result.tool_calls[0]["function"] == {"name": "get", "arguments": '{"a": 1}'}
    assert result.finish_reason == "tool_calls"


@respx.mock
@pytest.mark.django_db(transaction=True)
def test_async_chat_single_log_row(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    assert async_to_sync(achat)("chat", messages=MESSAGES).content == "Hello"
    assert list(RequestLog.objects.values_list("status_code", flat=True)) == [200]


# --- лимитер ------------------------------------------------------------------


def test_async_waiter_woken_by_thread_release() -> None:
    limiter = ParallelismLimiter()
    limiter._acquire(1)

    async def main() -> None:
        threading.Timer(0.05, limiter._release).start()
        await asyncio.wait_for(limiter._acquire_async(1), timeout=2)
        assert limiter.in_flight == 1
        limiter._release()

    asyncio.run(main())
    assert limiter.in_flight == 0


def test_cancelled_async_waiter_is_removed() -> None:
    limiter = ParallelismLimiter()
    limiter._acquire(1)

    async def main() -> None:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(limiter._acquire_async(1), timeout=0.05)

    asyncio.run(main())
    assert not limiter._async_waiters
    limiter._release()
    assert limiter.in_flight == 0


# --- шифрование ---------------------------------------------------------------


def test_secret_key_fallback_decrypts_and_rotates() -> None:
    field = EncryptedTextField()
    with override_settings(SECRET_KEY="old-key"):
        old_token = field.get_prep_value("sk-live")
    with override_settings(SECRET_KEY="new-key", SECRET_KEY_FALLBACKS=["old-key"]):
        assert field.to_python(old_token) == "sk-live"
        rotated = field.get_prep_value(old_token)
        assert rotated != old_token
        assert field.get_prep_value(rotated) == rotated
    with override_settings(SECRET_KEY="new-key", SECRET_KEY_FALLBACKS=[]):
        assert field.to_python(rotated) == "sk-live"


def test_decrypt_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    field = EncryptedTextField()
    with override_settings(SECRET_KEY="one"):
        token = field.get_prep_value("x")
    with override_settings(SECRET_KEY="two", SECRET_KEY_FALLBACKS=[]):
        assert field.to_python(token) == ""
    assert "Cannot decrypt" in caplog.text


# --- лог-бэкенды и сигнал -----------------------------------------------------


class _SlowBackend(LogBackend):
    written = threading.Event()

    def write(self, record: LogRecord) -> None:
        type(self).written.set()


def test_background_backend_and_signal(profile: UsageProfile) -> None:
    received: list[LogRecord] = []

    def _receiver(sender: object, record: LogRecord, **kwargs: object) -> None:
        received.append(record)

    request_logged.connect(_receiver)
    spec = {"BACKEND": "tests.test_improvements._SlowBackend", "BACKGROUND": True}
    try:
        with override_settings(OPENROUTER={"LOG_BACKENDS": [spec]}):
            record = make_record(profile=profile, model=None, status_code=200, error_message=None)
            dispatch_log(record)
            assert _SlowBackend.written.wait(timeout=2)
    finally:
        request_logged.disconnect(_receiver)
    assert received[0].profile_name == "chat"


def test_database_backend_never_background() -> None:
    from django_openrouter.log_backends import DatabaseBackend

    assert DatabaseBackend(BACKGROUND=True).background is False


# --- prune_request_logs -------------------------------------------------------


def test_prune_request_logs(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    fresh = RequestLog.objects.create(profile=profile, model=paid_model, status_code=200)
    old = RequestLog.objects.create(profile=profile, model=paid_model, status_code=200)
    RequestLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=200))
    call_command("prune_request_logs", "--days", "90", "--dry-run")
    assert RequestLog.objects.count() == 2
    call_command("prune_request_logs", "--days", "90")
    assert list(RequestLog.objects.values_list("pk", flat=True)) == [fresh.pk]
