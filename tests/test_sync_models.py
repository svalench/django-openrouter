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
    assert models_route.call_count == 1
