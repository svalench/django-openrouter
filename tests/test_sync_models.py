from __future__ import annotations

from decimal import Decimal
from io import StringIO

import httpx
import pytest
import respx
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError

from django_openrouter.models import OpenRouterModel, OpenRouterSettings
from django_openrouter.sync import (
    _best_stats,
    _latency_ms,
    ensure_catalog_fresh,
    sync_openrouter_models,
)

pytestmark = pytest.mark.django_db

MODELS_URL = "https://openrouter.ai/api/v1/models"


def _payload(*items: dict) -> dict:
    return {"data": list(items)}


def _item(model_id: str, name: str, prompt: str = "0") -> dict:
    return {
        "id": model_id,
        "name": name,
        "context_length": 8192,
        "pricing": {"prompt": prompt, "completion": "0"},
        "architecture": {"modality": "text->text"},
        "supported_parameters": ["temperature"],
    }


def _stt_item(model_id: str = "openai/whisper-large-v3-turbo") -> dict:
    return {
        "id": model_id,
        "name": "Whisper Large V3 Turbo",
        "context_length": 0,
        "pricing": {"prompt": "0.00000333", "completion": "0"},
        "architecture": {
            "modality": "audio->transcription",
            "input_modalities": ["audio"],
            "output_modalities": ["transcription"],
        },
        "supported_parameters": [],
    }


def _catalog_by_modality(request: httpx.Request) -> httpx.Response:
    if request.url.params.get("output_modalities") == "transcription":
        return httpx.Response(200, json=_payload(_stt_item()))
    return httpx.Response(200, json=_payload(_item("openai/gpt-4", "GPT-4", "0.03")))


@respx.mock
def test_sync_includes_transcription_models_without_dropping_chat(
    respx_mock: respx.MockRouter,
) -> None:
    OpenRouterModel.objects.create(model_id="legacy/gone", name="Gone", is_active=True)
    respx_mock.get(MODELS_URL).mock(side_effect=_catalog_by_modality)
    summary = sync_openrouter_models(api_key="sk-cli")
    chat = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    stt = OpenRouterModel.objects.get(model_id="openai/whisper-large-v3-turbo")
    assert chat.modality == "text->text"
    assert chat.is_transcription is False
    assert chat.is_active is True
    assert stt.modality == "audio->transcription"
    assert stt.output_modalities == ["transcription"]
    assert stt.is_transcription is True
    assert stt.is_active is True
    assert OpenRouterModel.objects.get(model_id="legacy/gone").is_active is False
    assert summary.created == 2
    assert summary.total_remote == 2


@respx.mock
def test_transcription_catalog_failure_does_not_deactivate_chat(
    respx_mock: respx.MockRouter,
) -> None:
    kept = OpenRouterModel.objects.create(model_id="local/kept", name="Kept", is_active=True)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("output_modalities") == "transcription":
            return httpx.Response(500, json={"error": "stt down"})
        return httpx.Response(200, json=_payload(_item("openai/gpt-4", "GPT-4")))

    respx_mock.get(MODELS_URL).mock(side_effect=handler)
    with pytest.raises(httpx.HTTPStatusError):
        sync_openrouter_models(api_key="sk-cli")
    kept.refresh_from_db()
    assert kept.is_active is True
    assert not OpenRouterModel.objects.filter(model_id="openai/gpt-4").exists()


@respx.mock
def test_sync_models_upsert_and_deactivate(respx_mock: respx.MockRouter) -> None:
    OpenRouterModel.objects.create(
        model_id="legacy/gone",
        name="Gone",
        is_active=True,
        pricing={"prompt": "1", "completion": "1"},
    )
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json=_payload(_item("openai/gpt-4", "GPT-4", "0.03")),
        )
    )
    out = StringIO()
    call_command("sync_models", "--api-key", "sk-cli", stdout=out)
    gpt = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    assert gpt.name == "GPT-4"
    assert gpt.is_active is True
    gone = OpenRouterModel.objects.get(model_id="legacy/gone")
    assert gone.is_active is False
    assert "created=1" in out.getvalue()
    assert "deactivated=1" in out.getvalue()

    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json=_payload(_item("openai/gpt-4", "GPT-4 Turbo", "0.01")),
        )
    )
    call_command("sync_models", api_key="sk-cli")
    gpt.refresh_from_db()
    assert gpt.name == "GPT-4 Turbo"
    assert OpenRouterModel.objects.filter(model_id="legacy/gone").exists()


@respx.mock
def test_sync_parses_parameter_size(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json=_payload(_item("meta-llama/llama-3.1-70b-instruct", "Llama 3.1 70B")),
        )
    )
    call_command("sync_models", "--api-key", "sk-cli")
    model = OpenRouterModel.objects.get(model_id="meta-llama/llama-3.1-70b-instruct")
    assert model.parameter_label == "70B"
    assert model.parameter_count == 70_000_000_000


@respx.mock
def test_sync_preserves_admin_inactive_flag(respx_mock: respx.MockRouter) -> None:
    OpenRouterModel.objects.create(
        model_id="openai/gpt-4",
        name="old",
        is_active=False,
        pricing={},
    )
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json=_payload(_item("openai/gpt-4", "GPT-4")))
    )
    call_command("sync_models", api_key="sk-cli")
    model = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    assert model.is_active is False
    assert model.name == "GPT-4"


def test_sync_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    OpenRouterSettings.load()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(CommandError, match="API key"):
        call_command("sync_models")


@respx.mock
def test_sync_rejects_unexpected_payload(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(MODELS_URL).mock(return_value=httpx.Response(200, json={"data": "nope"}))
    with pytest.raises(CommandError):
        call_command("sync_models", api_key="sk-cli")


@respx.mock
def test_sync_skips_items_without_id(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json={"data": [{"name": "broken"}, _item("ok/m", "OK")]})
    )
    call_command("sync_models", api_key="sk-cli")
    assert OpenRouterModel.objects.filter(model_id="ok/m").exists()


def test_latency_ms_converts_seconds() -> None:
    assert _latency_ms(0.25) == pytest.approx(250.0)
    assert _latency_ms(250.0) == pytest.approx(250.0)
    assert _latency_ms(None) is None


def test_best_stats_uses_lowest_latency_endpoint() -> None:
    latency, throughput = _best_stats(
        [
            {"latency_last_30m": {"p50": 1.0}, "throughput_last_30m": {"p50": 10.0}},
            {"latency_last_30m": {"p50": 0.2}, "throughput_last_30m": {"p50": 50.0}},
        ]
    )
    assert latency == pytest.approx(200.0)
    assert throughput == pytest.approx(50.0)


@respx.mock
def test_sync_enriches_endpoint_stats(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json=_payload(_item("openai/gpt-4", "GPT-4", "0.03")))
    )
    respx_mock.get(url__regex=r"https://openrouter\.ai/api/v1/models/.+/endpoints").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "endpoints": [
                        {
                            "latency_last_30m": {"p50": 0.4},
                            "throughput_last_30m": {"p50": 12.5},
                        }
                    ]
                }
            },
        )
    )
    sync_openrouter_models(api_key="sk-cli", enrich_stats=True)
    model = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    assert model.prompt_price == Decimal("0.03")
    assert model.completion_price == Decimal("0")
    assert model.latency_ms == pytest.approx(400.0)
    assert model.throughput == pytest.approx(12.5)


@respx.mock
def test_ensure_catalog_fresh_uses_cache(
    respx_mock: respx.MockRouter, or_settings: OpenRouterSettings
) -> None:
    cache.clear()
    models_route = respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json=_payload(_item("ok/m", "OK")))
    )
    respx_mock.get(url__regex=r"https://openrouter\.ai/api/v1/models/.+/endpoints").mock(
        return_value=httpx.Response(200, json={"data": {"endpoints": []}})
    )
    first = ensure_catalog_fresh()
    assert first is not None
    second = ensure_catalog_fresh()
    assert second is None
    # Чат-каталог и каталог транскрипции — два GET на один и тот же маршрут.
    assert models_route.call_count == 2


@pytest.mark.parametrize(
    "details",
    [
        "https://external.example/endpoints",
        "http://openrouter.ai/api/v1/models/a/b/endpoints",
        "https://openrouter.ai:8443/endpoints",
        "https://user:password@openrouter.ai/endpoints",
        "//external.example/endpoints",
    ],
)
@respx.mock
def test_catalog_links_cannot_redirect_authorization(
    respx_mock: respx.MockRouter, details: str
) -> None:
    item = _item("a/b", "Synthetic")
    item["links"] = {"details": details}
    respx_mock.get(MODELS_URL).mock(return_value=httpx.Response(200, json=_payload(item)))
    canonical = respx_mock.get("https://openrouter.ai/api/v1/models/a/b/endpoints").mock(
        return_value=httpx.Response(200, json={"data": {"endpoints": []}})
    )
    other = respx_mock.route().mock(return_value=httpx.Response(200, json={}))
    sync_openrouter_models(api_key="synthetic-audit-key", enrich_stats=True)
    assert canonical.called
    assert not other.called


@pytest.mark.parametrize(
    "details",
    [
        "https://openrouter.ai/api/v1/models/a/b/endpoints",
        "/api/v1/models/a/b/endpoints",
    ],
)
def test_same_origin_catalog_links_are_supported(details: str) -> None:
    from django_openrouter.sync import _endpoints_url

    assert _endpoints_url(
        "https://openrouter.ai/api/v1", {"links": {"details": details}}, "a/b"
    ) == ("https://openrouter.ai/api/v1/models/a/b/endpoints")


def test_canonical_endpoint_encodes_untrusted_model_id() -> None:
    from django_openrouter.sync import _endpoints_url

    result = _endpoints_url("https://openrouter.ai/api/v1", {}, "../a?x=#part")
    assert result == "https://openrouter.ai/api/v1/models/%2E%2E/a%3Fx%3D%23part/endpoints"
