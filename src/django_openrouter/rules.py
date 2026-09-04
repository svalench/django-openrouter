"""Проверка лимитов, бюджетов и ограничений профиля перед вызовом API."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from django_openrouter.exceptions import (
    BudgetExceeded,
    ModelDisabled,
    RateLimitExceeded,
)
from django_openrouter.models import OpenRouterModel, UsageProfile


def check_limits(profile: UsageProfile) -> None:
    """
    HTTP-стоп при исчерпании лимитов. Fallback по моделям здесь не делается.

    Блокировка строки профиля + агрегация логов в одной транзакции.
    """
    if not profile.is_active:
        raise ModelDisabled(f"Usage profile {profile.name!r} is disabled.")
    if not profile.model.is_active:
        raise ModelDisabled(
            f"Primary model {profile.model.model_id!r} for profile {profile.name!r} is disabled."
        )

    with transaction.atomic():
        locked = (
            UsageProfile.objects.select_for_update().select_related("model").get(pk=profile.pk)
        )
        day = locked.get_usage("day")
        month = locked.get_usage("month")

        if (
            locked.max_requests_per_day is not None
            and day.request_count >= locked.max_requests_per_day
        ):
            raise RateLimitExceeded(
                f"Daily request limit ({locked.max_requests_per_day}) exceeded "
                f"for profile {locked.name!r}."
            )
        if (
            locked.max_requests_per_month is not None
            and month.request_count >= locked.max_requests_per_month
        ):
            raise RateLimitExceeded(
                f"Monthly request limit ({locked.max_requests_per_month}) exceeded "
                f"for profile {locked.name!r}."
            )
        if locked.budget_usd_per_day is not None and day.total_cost >= Decimal(
            str(locked.budget_usd_per_day)
        ):
            raise BudgetExceeded(
                f"Daily budget ({locked.budget_usd_per_day} USD) exceeded "
                f"for profile {locked.name!r}."
            )
        if locked.budget_usd_per_month is not None and month.total_cost >= Decimal(
            str(locked.budget_usd_per_month)
        ):
            raise BudgetExceeded(
                f"Monthly budget ({locked.budget_usd_per_month} USD) exceeded "
                f"for profile {locked.name!r}."
            )


def assert_model_allowed(profile: UsageProfile, model: OpenRouterModel) -> None:
    """Проверяет, что конкретная модель допустима правилами профиля."""
    if not model.is_active:
        raise ModelDisabled(f"Model {model.model_id!r} is disabled.")
    if profile.only_free_models and not model.is_free:
        raise ModelDisabled(
            f"Profile {profile.name!r} allows only free models; {model.model_id!r} is not free."
        )
