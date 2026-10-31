"""Группировка логов: trace_id, session_id, metadata."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.test import override_settings
from django.urls import reverse

from django_openrouter import chat, transcribe
from django_openrouter.call_context import bound_session
from django_openrouter.client import AsyncOpenRouterClient, OpenRouterClient, achat
from django_openrouter.exceptions import ConfigurationError
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
FILE_BACKEND = "django_openrouter.log_backends.FileBackend"
CLICKHOUSE_BACKEND = "django_openrouter.log_backends.ClickHouseBackend"
CLICKHOUSE_URL = "http://clickhouse.example:8123"
AUDIO = b"\x1a\x45\xdf\xa3webm"


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


def _stt_payload() -> dict:
    return {
        "text": "привет",
        "model": "openai/whisper-large-v3-turbo",
        "usage": {"cost": "0.0001", "seconds": "2.5", "input_tokens": 1, "output_tokens": 4},
    }


@respx.mock
def test_attempts_share_generated_trace_id(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model: OpenRouterModel,
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    respx_mock.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate"}),
            httpx.Response(
                200,
                json=completion_payload(content="ok", model=fallback_model.model_id),
            ),
        ]
    )
    chat("chat", messages=MESSAGES, session_id="ticket-42", metadata={"feature": "support"})
    logs = list(RequestLog.objects.order_by("id"))
    assert [log.status_code for log in logs] == [429, 200]
    assert logs[0].trace_id == logs[1].trace_id
    assert logs[0].trace_id is not None
    assert len(logs[0].trace_id) == 32
    assert logs[0].session_id == logs[1].session_id == "ticket-42"
    assert logs[0].metadata == {"feature": "support"}


@respx.mock
def test_explicit_trace_id_and_call_metadata_override_bound_session(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    route = respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    with bound_session("ticket-42", metadata={"feature": "support", "a": 1}):
        chat(
            "chat",
            messages=MESSAGES,
            session_id="other",
            metadata={"a": 2, "b": 3},
            trace_id="trace-explicit",
            trace={"feature.flag": "beta"},
        )
        chat("chat", messages=MESSAGES)
    logs = list(RequestLog.objects.order_by("id"))
    assert logs[0].session_id == "other"
    assert logs[0].metadata == {"feature": "support", "a": 2, "b": 3}
    assert logs[0].trace_id == "trace-explicit"
    assert logs[1].session_id == "ticket-42"
    assert logs[1].metadata == {"feature": "support", "a": 1}
    assert logs[1].trace_id != logs[0].trace_id
    body = json.loads(route.calls[0].request.content)
    assert body["session_id"] == "other"
    assert body["metadata"] == {"a": 2, "b": 3, "feature": "support"}
    assert "trace_id" not in body
    assert "trace" not in body
    second = json.loads(route.calls[1].request.content)
    assert "session_id" not in second
    assert "metadata" not in second


@respx.mock
def test_clients_and_async_accept_grouping(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    OpenRouterClient("chat").chat(MESSAGES, session_id="sync-client", metadata={"via": "sync"})
    async_to_sync(achat)("chat", messages=MESSAGES, session_id="async-facade")
    async_to_sync(AsyncOpenRouterClient("chat").chat)(
        MESSAGES, metadata={"via": "async-client"}
    )
    rows = list(RequestLog.objects.order_by("id"))
    assert rows[0].session_id == "sync-client"
    assert rows[0].metadata == {"via": "sync"}
    assert rows[1].session_id == "async-facade"
    assert rows[2].metadata == {"via": "async-client"}
    assert all(row.trace_id for row in rows)


@respx.mock
def test_transcribe_stores_grouping_without_sending_it(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
) -> None:
    route = respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_stt_payload()))
    transcribe(
        AUDIO,
        filename="note.webm",
        content_type="audio/webm",
        profile="dictation",
        session_id="dictation-1",
        metadata={"lang": "ru"},
        trace_id="stt-trace",
    )
    sent = json.loads(route.calls.last.request.content)
    assert "session_id" not in sent
    assert "metadata" not in sent
    log = RequestLog.objects.get()
    assert log.session_id == "dictation-1"
    assert log.metadata == {"lang": "ru"}
    assert log.trace_id == "stt-trace"
    assert log.profile_id == dictation.pk


def test_grouping_arguments_are_validated(or_settings: OpenRouterSettings) -> None:
    with pytest.raises(ConfigurationError, match="metadata"):
        chat("chat", messages=MESSAGES, metadata=["nope"])  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError, match="session_id"):
        chat("chat", messages=MESSAGES, session_id="x" * 256)
    with pytest.raises(ConfigurationError, match="trace_id"):
        chat("chat", messages=MESSAGES, trace_id="y" * 65)
    with pytest.raises(ConfigurationError, match="non-empty"):
        with bound_session("  "):
            pass
    assert RequestLog.objects.count() == 0


@respx.mock
def test_file_and_clickhouse_include_grouping(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    or_settings: OpenRouterSettings,
) -> None:
    log_file = tmp_path / "openrouter.jsonl"
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    clickhouse = respx_mock.post(f"{CLICKHOUSE_URL}/").mock(return_value=httpx.Response(200))
    with override_settings(
        OPENROUTER={
            "RETRY_BACKOFF": 0,
            "LOG_BACKENDS": [
                "django_openrouter.log_backends.DatabaseBackend",
                {"BACKEND": FILE_BACKEND, "PATH": str(log_file)},
                {"BACKEND": CLICKHOUSE_BACKEND, "URL": CLICKHOUSE_URL},
            ],
        }
    ):
        chat(
            "chat",
            messages=MESSAGES,
            session_id="file-1",
            metadata={"k": "v"},
            trace_id="file-trace",
        )
    row = json.loads(log_file.read_text(encoding="utf-8"))
    assert row["trace_id"] == "file-trace"
    assert row["session_id"] == "file-1"
    assert json.loads(row["metadata"]) == {"k": "v"}
    remote = json.loads(clickhouse.calls.last.request.content)
    assert remote["trace_id"] == "file-trace"
    assert remote["session_id"] == "file-1"
    assert json.loads(remote["metadata"]) == {"k": "v"}
    assert RequestLog.objects.get().session_id == "file-1"


@respx.mock
def test_reservation_row_keeps_grouping(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    profile.max_requests_per_day = 5
    profile.save()
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    chat("chat", messages=MESSAGES, session_id="reserved", trace_id="reserve-trace")
    log = RequestLog.objects.get()
    assert log.status_code == 200
    assert log.session_id == "reserved"
    assert log.trace_id == "reserve-trace"


def test_admin_filters_session_and_trace(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
) -> None:
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        session_id="sess-1",
        trace_id="a" * 32,
        metadata={"feature": "chat"},
    )
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=429,
        session_id="sess-1",
        trace_id="b" * 32,
    )
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        session_id="sess-2",
        trace_id="a" * 32,
    )
    url = reverse("admin:django_openrouter_requestlog_changelist")
    by_session = admin_client.get(url, {"session_id": "sess-1"})
    assert by_session.status_code == 200
    session_ids = by_session.context["cl"].queryset.order_by("id")
    assert list(session_ids.values_list("session_id", flat=True)) == [
        "sess-1",
        "sess-1",
    ]
    by_trace = admin_client.get(url, {"trace_id": "a" * 32})
    assert list(
        by_trace.context["cl"].queryset.order_by("id").values_list("session_id", flat=True)
    ) == [
        "sess-1",
        "sess-2",
    ]
    found = admin_client.get(url, {"q": "sess-2"})
    assert list(found.context["cl"].queryset.values_list("session_id", flat=True)) == ["sess-2"]
    change = admin_client.get(
        reverse(
            "admin:django_openrouter_requestlog_change",
            args=[RequestLog.objects.order_by("id").first().pk],
        )
    )
    page = change.content.decode()
    assert change.status_code == 200
    assert "all calls in this session" in page
    assert "all calls in this trace" in page
    assert "feature" in page
    assert "chat" in page
