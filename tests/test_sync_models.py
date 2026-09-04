from __future__ import annotations

from io import StringIO

import httpx
import pytest
import respx
from django.core.management import call_command
from django.core.management.base import CommandError

from django_openrouter.models import OpenRouterModel, OpenRouterSettings

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
