from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)

pytestmark = pytest.mark.django_db


def test_settings_singleton_always_pk_1() -> None:
    first = OpenRouterSettings.load()
    second = OpenRouterSettings(base_url="https://example.test/api/v1")
    second.save()
    assert OpenRouterSettings.objects.count() == 1
    assert OpenRouterSettings.objects.get().pk == 1
    assert OpenRouterSettings.load().pk == first.pk


def test_settings_cannot_be_deleted() -> None:
    obj = OpenRouterSettings.load()
    deleted, _details = obj.delete()
    assert deleted == 0
    assert OpenRouterSettings.objects.filter(pk=1).exists()


def test_api_key_roundtrip_encrypted() -> None:
    obj = OpenRouterSettings.load()
    obj.api_key = "sk-secret-value"
    obj.save()
    loaded = OpenRouterSettings.objects.get(pk=1)
    assert loaded.api_key == "sk-secret-value"


def test_model_is_free(free_model: OpenRouterModel, paid_model: OpenRouterModel) -> None:
    assert free_model.is_free is True
    assert paid_model.is_free is False


def test_usage_profile_clean_rejects_inactive_model(paid_model: OpenRouterModel) -> None:
    paid_model.is_active = False
    paid_model.save()
    profile = UsageProfile(name="bad", model=paid_model)
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_usage_profile_clean_only_free(paid_model: OpenRouterModel) -> None:
    profile = UsageProfile(name="free-only", model=paid_model, only_free_models=True)
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_fallback_clean_rejects_inactive(
    profile: UsageProfile, fallback_model: OpenRouterModel
) -> None:
    fallback_model.is_active = False
    fallback_model.save()
    link = UsageProfileFallback(profile=profile, model=fallback_model, order=0)
    with pytest.raises(ValidationError):
        link.full_clean()


def test_get_usage_day_and_month(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("1.25"),
    )
    old = RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("9.00"),
    )
    RequestLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))

    day = profile.get_usage("day")
    month = profile.get_usage("month")
    assert day.request_count == 1
    assert day.total_cost == Decimal("1.25")
    assert month.request_count == 1
    assert month.total_cost == Decimal("1.25")


def test_get_usage_rejects_bad_period(profile: UsageProfile) -> None:
    with pytest.raises(ValueError):
        profile.get_usage("year")  # type: ignore[arg-type]


def test_ordered_fallback_models(
    profile: UsageProfile, fallback_model: OpenRouterModel, free_model: OpenRouterModel
) -> None:
    UsageProfileFallback.objects.create(profile=profile, model=free_model, order=1)
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=0)
    ordered = profile.ordered_fallback_models()
    assert [m.model_id for m in ordered] == [fallback_model.model_id, free_model.model_id]


def test_temperature_out_of_range(paid_model: OpenRouterModel) -> None:
    profile = UsageProfile(name="hot", model=paid_model, temperature=3)
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_fallback_str_and_clean_without_model(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    link = UsageProfileFallback(profile=profile, model=paid_model, order=0)
    link.save()
    assert str(link)
    empty = UsageProfileFallback(profile=profile, order=1)
    empty.clean()


def test_fallback_only_free_rejects_paid(
    free_model: OpenRouterModel, paid_model: OpenRouterModel
) -> None:
    profile = UsageProfile.objects.create(
        name="free-only",
        model=free_model,
        only_free_models=True,
    )
    link = UsageProfileFallback(profile=profile, model=paid_model, order=0)
    with pytest.raises(ValidationError):
        link.full_clean()


def test_str_helpers(paid_model: OpenRouterModel, profile: UsageProfile) -> None:
    assert str(paid_model) == paid_model.model_id
    assert str(profile) == "chat"
    assert str(OpenRouterSettings.load()) == "OpenRouter settings"
    log = RequestLog.objects.create(profile=profile, model=paid_model, status_code=200)
    assert str(log)


def test_is_free_with_null_prices(paid_model: OpenRouterModel) -> None:
    paid_model.pricing = {"prompt": None, "completion": ""}
    assert paid_model.is_free is True
