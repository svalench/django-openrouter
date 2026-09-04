from __future__ import annotations

from decimal import Decimal

import pytest

from django_openrouter.exceptions import BudgetExceeded, ModelDisabled, RateLimitExceeded
from django_openrouter.models import OpenRouterModel, RequestLog, UsageProfile
from django_openrouter.rules import assert_model_allowed, check_limits

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
