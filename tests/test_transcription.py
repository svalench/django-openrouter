"""Транскрипция: конфиг, HTTP, бюджеты, формат и админка."""

from __future__ import annotations

import base64
from decimal import Decimal
from io import BytesIO

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from django_openrouter import atranscribe, transcribe
from django_openrouter.client import AsyncOpenRouterClient, OpenRouterClient
from django_openrouter.config import get_runtime_config
from django_openrouter.exceptions import (
    AudioTooLarge,
    BudgetExceeded,
    ConfigurationError,
    OpenRouterDisabled,
    RateLimitExceeded,
    UnsupportedAudioFormat,
)
from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    ProfileKind,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from django_openrouter.rules import maximum_transcription_cost

pytestmark = pytest.mark.django_db

STT_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
AUDIO = b"\x1a\x45\xdf\xa3webm"


@pytest.fixture
def whisper() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="openai/whisper-large-v3-turbo",
        name="Whisper Large V3 Turbo",
        context_length=0,
        pricing={"prompt": "0.00000333", "completion": "0"},
        modality="audio->transcription",
        output_modalities=["transcription"],
        is_active=True,
    )


@pytest.fixture
def token_stt() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="openai/gpt-4o-mini-transcribe",
        name="GPT-4o mini transcribe",
        context_length=128000,
        pricing={"prompt": "0.00000125", "completion": "0.000005"},
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


def _payload(
    *,
    text: str = "привет",
    cost: str = "0.0001",
    seconds: float = 2.5,
    model: str = "openai/whisper-large-v3-turbo",
    input_tokens: int = 0,
    output_tokens: int = 4,
) -> dict:
    return {
        "text": text,
        "model": model,
        "usage": {
            "cost": cost,
            "seconds": seconds,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


@respx.mock
def test_transcribe_logs_cost_and_uses_profile_language(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
) -> None:
    import json

    route = respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_payload()))
    result = transcribe(AUDIO, filename="note.webm", content_type="audio/webm;codecs=opus")
    assert result.text == "привет"
    assert result.model_used == "openai/whisper-large-v3-turbo"
    assert result.cost_usd == Decimal("0.0001")
    assert result.duration_seconds == Decimal("2.5")
    assert result.completion_tokens == 4
    sent = json.loads(route.calls.last.request.content)
    assert sent["model"] == "openai/whisper-large-v3-turbo"
    assert sent["language"] == "ru"
    assert sent["input_audio"]["format"] == "webm"
    assert sent["input_audio"]["data"] == base64.b64encode(AUDIO).decode("ascii")
    log = RequestLog.objects.get()
    assert log.status_code == 200
    assert log.profile_id == dictation.pk
    assert log.cost_usd == Decimal("0.0001")
    assert log.completion_tokens == 4


@respx.mock
def test_transcribe_async_and_client_classes(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
) -> None:
    respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_payload(text="async")))
    sync_result = OpenRouterClient("dictation").transcribe(
        BytesIO(AUDIO), filename="a.mp3", content_type="audio/mpeg"
    )
    async_result = async_to_sync(atranscribe)(
        AUDIO, filename="a.ogg", profile="dictation", language="en"
    )
    class_result = async_to_sync(AsyncOpenRouterClient("dictation").transcribe)(
        AUDIO, filename="a.wav", content_type="audio/wav", prompt="имена: Наталья"
    )
    assert sync_result.text == "async"
    assert async_result.text == "async"
    assert class_result.text == "async"
    assert RequestLog.objects.filter(status_code=200).count() == 3


@respx.mock
def test_transcribe_falls_back_on_429(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
    token_stt: OpenRouterModel,
) -> None:
    UsageProfileFallback.objects.create(profile=dictation, model=token_stt, order=1)
    respx_mock.post(STT_URL).mock(
        side_effect=[
            httpx.Response(429, json={"error": {"message": "slow down", "code": 429}}),
            httpx.Response(
                200,
                json=_payload(text="next", model="openai/gpt-4o-mini-transcribe"),
            ),
        ]
    )
    result = transcribe(AUDIO, filename="a.webm", profile="dictation", model=None)
    assert result.model_used == "openai/gpt-4o-mini-transcribe"
    assert RequestLog.objects.filter(status_code=429).exists()
    assert RequestLog.objects.filter(status_code=200).exists()


def test_transcribe_disabled_and_missing_key(
    stt_settings: OpenRouterSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    stt_settings.enabled = False
    stt_settings.save()
    with pytest.raises(OpenRouterDisabled):
        transcribe(AUDIO, filename="a.webm")
    stt_settings.enabled = True
    stt_settings.api_key = ""
    stt_settings.save()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="API key"):
        transcribe(AUDIO, filename="a.webm")


def test_transcribe_requires_transcription_profile(
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    whisper: OpenRouterModel,
) -> None:
    from django_openrouter import chat

    with pytest.raises(ConfigurationError, match="default_transcription_profile"):
        transcribe(AUDIO, filename="a.webm")
    with pytest.raises(ConfigurationError, match="not a transcription profile"):
        transcribe(AUDIO, filename="a.webm", profile="chat")
    UsageProfile.objects.create(name="dictation", model=whisper, kind=ProfileKind.TRANSCRIPTION)
    with pytest.raises(ConfigurationError, match="transcribe"):
        chat("dictation", messages=[{"role": "user", "content": "hi"}])


def test_transcribe_rejects_format_and_size(
    stt_settings: OpenRouterSettings, dictation: UsageProfile
) -> None:
    with pytest.raises(UnsupportedAudioFormat):
        transcribe(b"not-audio", filename="clip.bin", content_type="application/octet-stream")
    dictation.max_audio_bytes = 4
    dictation.save()
    with pytest.raises(AudioTooLarge):
        transcribe(AUDIO, filename="a.webm")
    with pytest.raises(ConfigurationError, match="empty"):
        transcribe(b"", filename="a.webm")


@respx.mock
def test_uploaded_file_uses_its_name_and_content_type(
    respx_mock: respx.MockRouter, stt_settings: OpenRouterSettings
) -> None:
    import json

    route = respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_payload()))
    upload = SimpleUploadedFile("dictation.webm", AUDIO, content_type="audio/webm")
    result = transcribe(upload)
    assert result.text == "привет"
    sent = json.loads(route.calls.last.request.content)
    assert sent["input_audio"]["format"] == "webm"
    assert sent["language"] == "ru"


def _hook(data: bytes, *, filename: str, content_type: str) -> tuple[bytes, str, str]:
    return data, "ready.wav", "audio/wav"


@respx.mock
@override_settings(OPENROUTER={"AUDIO_PREPARE": "tests.test_transcription._hook"})
def test_audio_prepare_hook_changes_format(
    respx_mock: respx.MockRouter, stt_settings: OpenRouterSettings
) -> None:
    import json

    route = respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_payload()))
    transcribe(b"raw-bytes", filename="clip.bin", content_type="application/octet-stream")
    sent = json.loads(route.calls.last.request.content)
    assert sent["input_audio"]["format"] == "wav"


def test_runtime_config_resolves_transcription_profile(
    stt_settings: OpenRouterSettings, dictation: UsageProfile, profile: UsageProfile
) -> None:
    cfg = get_runtime_config(force_reload=True)
    assert cfg.default_profile_name == "chat"
    assert cfg.default_transcription_profile_name == "dictation"
    assert cfg.api_key == "sk-test"
    snapshot = cfg.profiles["dictation"]
    assert snapshot.kind == ProfileKind.TRANSCRIPTION
    assert snapshot.language == "ru"
    assert snapshot.model.model_id == "openai/whisper-large-v3-turbo"


def test_token_priced_transcription_reserves_context_window(token_stt: OpenRouterModel) -> None:
    cost = maximum_transcription_cost(token_stt, max_audio_seconds=None)
    assert cost == (Decimal("0.000005") * 128000).quantize(Decimal("0.0000000001"))


def test_budget_reservation_uses_audio_seconds(
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
    whisper: OpenRouterModel,
) -> None:
    cost = maximum_transcription_cost(whisper, max_audio_seconds=10)
    assert cost == (Decimal("0.00000333") * 10).quantize(Decimal("0.0000000001"))
    dictation.budget_usd_per_day = Decimal("0.00001")
    dictation.max_audio_seconds = 10
    dictation.save()
    with pytest.raises(BudgetExceeded):
        transcribe(AUDIO, filename="a.webm", profile="dictation")
    assert RequestLog.objects.count() == 0


@respx.mock
def test_budget_reconciles_reported_usage(
    respx_mock: respx.MockRouter,
    stt_settings: OpenRouterSettings,
    dictation: UsageProfile,
) -> None:
    dictation.budget_usd_per_day = Decimal("1")
    dictation.max_audio_seconds = 30
    dictation.max_requests_per_day = 1
    dictation.save()
    respx_mock.post(STT_URL).mock(return_value=httpx.Response(200, json=_payload(cost="0.02")))
    result = transcribe(AUDIO, filename="a.mp3", content_type="audio/mpeg")
    assert result.cost_usd == Decimal("0.02")
    log = RequestLog.objects.get()
    assert log.cost_usd == Decimal("0.02")
    assert log.status_code == 200
    with pytest.raises(RateLimitExceeded):
        transcribe(AUDIO, filename="a.mp3", content_type="audio/mpeg")


def test_duration_budget_requires_max_audio_seconds(
    stt_settings: OpenRouterSettings, dictation: UsageProfile
) -> None:
    dictation.budget_usd_per_month = Decimal("5")
    dictation.max_audio_seconds = None
    dictation.save()
    with pytest.raises(ConfigurationError, match="max_audio_seconds"):
        transcribe(AUDIO, filename="a.webm")


def test_profile_rejects_chat_model_and_bad_language(
    whisper: OpenRouterModel, paid_model: OpenRouterModel
) -> None:
    profile = UsageProfile(
        name="bad-lang",
        model=whisper,
        kind=ProfileKind.TRANSCRIPTION,
        language="russian",
    )
    with pytest.raises(Exception, match="ISO-639-1"):
        profile.full_clean()
    link = UsageProfileFallback(
        profile=UsageProfile.objects.create(
            name="dict", model=whisper, kind=ProfileKind.TRANSCRIPTION
        ),
        model=paid_model,
        order=1,
    )
    with pytest.raises(Exception, match="does not match profile kind"):
        link.full_clean()


def test_admin_transcription_profile_and_catalog_filter(admin_client, whisper, paid_model) -> None:
    from django.urls import reverse

    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    add_url = reverse("admin:django_openrouter_usageprofile_add")
    prefix = "fallback_links"
    response = admin_client.post(
        add_url,
        {
            "name": "dictation",
            "kind": "transcription",
            "language": "EN",
            "max_audio_seconds": "30",
            "is_active": "on",
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-model": str(whisper.pk),
            f"{prefix}-0-order": "0",
        },
        follow=True,
    )
    assert response.status_code == 200
    created = UsageProfile.objects.get(name="dictation")
    assert created.kind == ProfileKind.TRANSCRIPTION
    assert created.language == "en"
    assert created.model_id == whisper.pk

    rejected = admin_client.post(
        add_url,
        {
            "name": "mixed",
            "kind": "transcription",
            "is_active": "on",
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-model": str(paid_model.pk),
            f"{prefix}-0-order": "0",
        },
    )
    assert rejected.status_code == 200
    assert not UsageProfile.objects.filter(name="mixed").exists()

    auto = reverse("admin:autocomplete")
    stt_only = admin_client.get(
        auto,
        {
            "app_label": "django_openrouter",
            "model_name": "usageprofilefallback",
            "field_name": "model",
            "term": "",
            "kind": "transcription",
        },
    )
    ids = {row["id"] for row in stt_only.json()["results"]}
    assert str(whisper.pk) in ids
    assert str(paid_model.pk) not in ids
    chat_only = admin_client.get(
        auto,
        {
            "app_label": "django_openrouter",
            "model_name": "usageprofilefallback",
            "field_name": "model",
            "term": "",
            "kind": "chat",
        },
    )
    chat_ids = {row["id"] for row in chat_only.json()["results"]}
    assert str(paid_model.pk) in chat_ids
    assert str(whisper.pk) not in chat_ids
