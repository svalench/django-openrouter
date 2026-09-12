from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import override_settings

from django_openrouter.exceptions import (
    BudgetExceeded,
    ConfigurationError,
    ModelDisabled,
    RateLimitExceeded,
)
from django_openrouter.models import OpenRouterModel, RequestLog, UsageProfile
from django_openrouter.rules import assert_model_allowed, check_limits, reserve_request

pytestmark = pytest.mark.django_db


def _log(profile: UsageProfile, model: OpenRouterModel, cost: str = "0") -> None:
    RequestLog.objects.create(
        profile=profile,
        model=model,
        status_code=200,
        cost_usd=Decimal(cost),
    )


def test_daily_request_limit(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    profile.max_requests_per_day = 2
    profile.save()
    _log(profile, paid_model)
    _log(profile, paid_model)
    with pytest.raises(RateLimitExceeded, match="Daily request"):
        check_limits(profile)


def test_monthly_request_limit(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    profile.max_requests_per_month = 1
    profile.save()
    _log(profile, paid_model)
    with pytest.raises(RateLimitExceeded, match="Monthly request"):
        check_limits(profile)


def test_daily_budget(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    profile.budget_usd_per_day = Decimal("1.00")
    profile.save()
    _log(profile, paid_model, "1.00")
    with pytest.raises(BudgetExceeded, match="Daily budget"):
        check_limits(profile)


def test_monthly_budget(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    profile.budget_usd_per_month = Decimal("5.00")
    profile.save()
    _log(profile, paid_model, "5.00")
    with pytest.raises(BudgetExceeded, match="Monthly budget"):
        check_limits(profile)


def test_no_limits_pass(profile: UsageProfile) -> None:
    check_limits(profile)


@override_settings(OPENROUTER={"LOG_BACKENDS": []})
def test_limits_require_database_backend(profile: UsageProfile) -> None:
    profile.max_requests_per_day = 1
    profile.save()
    with pytest.raises(ConfigurationError, match="DatabaseBackend is required"):
        check_limits(profile)


def test_budget_reservation_blocks_second_in_flight_request(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    profile.budget_usd_per_day = Decimal("4.00")
    profile.save()
    reservation = reserve_request(profile, paid_model)
    assert reservation is not None
    assert reservation.cost_usd == Decimal("3.0000000000")
    with pytest.raises(BudgetExceeded, match="conservative reservation"):
        reserve_request(profile, paid_model)
    reservation.cost_usd = Decimal("0.01")
    reservation.status_code = 200
    reservation.save(update_fields=["cost_usd", "status_code"])
    assert reserve_request(profile, paid_model) is not None


def test_request_limit_reserves_slot_before_http(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    profile.max_requests_per_day = 1
    profile.save()
    assert reserve_request(profile, paid_model) is not None
    with pytest.raises(RateLimitExceeded):
        reserve_request(profile, paid_model)


def test_budget_rejects_unbounded_extra_pricing(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    profile.budget_usd_per_day = Decimal("10")
    profile.save()
    paid_model.pricing = {**paid_model.pricing, "web_search": "0.01"}
    paid_model.save(update_fields=["pricing"])
    with pytest.raises(ConfigurationError, match="without extra charges"):
        reserve_request(profile, paid_model)


@pytest.mark.parametrize("modality", ["", "text+image->text", "text->image"])
def test_budget_rejects_non_text_or_unknown_modality(
    profile: UsageProfile, paid_model: OpenRouterModel, modality: str
) -> None:
    profile.budget_usd_per_day = Decimal("10")
    profile.save(update_fields=["budget_usd_per_day"])
    paid_model.modality = modality
    paid_model.save(update_fields=["modality"])
    with pytest.raises(ConfigurationError, match="text-to-text"):
        reserve_request(profile, paid_model)
    assert RequestLog.objects.count() == 0


def test_disabled_profile(profile: UsageProfile) -> None:
    profile.is_active = False
    profile.save()
    with pytest.raises(ModelDisabled, match="disabled"):
        check_limits(profile)


def test_disabled_primary_does_not_block_limits(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    paid_model.is_active = False
    paid_model.save()
    profile.refresh_from_db()
    check_limits(profile)


def test_only_free_models(
    profile: UsageProfile, paid_model: OpenRouterModel, free_model: OpenRouterModel
) -> None:
    profile.only_free_models = True
    profile.model = free_model
    profile.save()
    assert_model_allowed(profile, free_model)
    with pytest.raises(ModelDisabled, match="only free"):
        assert_model_allowed(profile, paid_model)


def test_assert_inactive_model(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    paid_model.is_active = False
    paid_model.save()
    with pytest.raises(ModelDisabled, match="disabled"):
        assert_model_allowed(profile, paid_model)
