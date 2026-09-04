from __future__ import annotations

from decimal import Decimal

import pytest

from django_openrouter.concurrency import get_limiter
from django_openrouter.models import OpenRouterModel, OpenRouterSettings, UsageProfile

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_openrouter_limiter() -> None:
    limiter = get_limiter()
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def paid_model() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        context_length=200000,
        pricing={"prompt": "0.000003", "completion": "0.000015"},
        supported_parameters=["temperature", "max_tokens"],
        modality="text->text",
        is_active=True,
    )


@pytest.fixture
def free_model() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="meta-llama/llama-3-8b-instruct:free",
        name="Llama 3 8B Instruct (free)",
        pricing={"prompt": "0", "completion": "0", "request": "0"},
        modality="text->text",
        is_active=True,
    )


@pytest.fixture
def fallback_model() -> OpenRouterModel:
    return OpenRouterModel.objects.create(
        model_id="openai/gpt-4o-mini",
        name="GPT-4o mini",
        pricing={"prompt": "0.00000015", "completion": "0.0000006"},
        modality="text->text",
        is_active=True,
    )


@pytest.fixture
def profile(paid_model: OpenRouterModel) -> UsageProfile:
    return UsageProfile.objects.create(name="chat", model=paid_model, is_active=True)


@pytest.fixture
def or_settings(profile: UsageProfile) -> OpenRouterSettings:
    settings_obj = OpenRouterSettings.load()
    settings_obj.api_key = "sk-test"
    settings_obj.default_profile = profile
    settings_obj.enabled = True
    settings_obj.max_retries = 0
    settings_obj.save()
    return settings_obj


def completion_payload(
    *,
    content: str = "Hello",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    model: str = "anthropic/claude-3.5-sonnet",
    cost: Decimal | None = None,
) -> dict:
    usage: dict = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    if cost is not None:
        usage["cost"] = str(cost)
    return {
        "id": "gen-test",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": usage,
    }
