"""Проверка лимитов, бюджетов и ограничений профиля перед вызовом API."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext as _

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
        raise ModelDisabled(_("Usage profile %(name)r is disabled.") % {"name": profile.name})

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
                _("Daily request limit (%(limit)s) exceeded for profile %(name)r.")
                % {"limit": locked.max_requests_per_day, "name": locked.name}
            )
        if (
            locked.max_requests_per_month is not None
            and month.request_count >= locked.max_requests_per_month
        ):
            raise RateLimitExceeded(
                _("Monthly request limit (%(limit)s) exceeded for profile %(name)r.")
                % {"limit": locked.max_requests_per_month, "name": locked.name}
            )
        if locked.budget_usd_per_day is not None and day.total_cost >= Decimal(
            str(locked.budget_usd_per_day)
        ):
            raise BudgetExceeded(
                _("Daily budget (%(budget)s USD) exceeded for profile %(name)r.")
                % {"budget": locked.budget_usd_per_day, "name": locked.name}
            )
        if locked.budget_usd_per_month is not None and month.total_cost >= Decimal(
            str(locked.budget_usd_per_month)
        ):
            raise BudgetExceeded(
                _("Monthly budget (%(budget)s USD) exceeded for profile %(name)r.")
                % {"budget": locked.budget_usd_per_month, "name": locked.name}
            )


def assert_model_allowed(profile: UsageProfile, model: OpenRouterModel) -> None:
    """Проверяет, что конкретная модель допустима правилами профиля."""
    if not model.is_active:
        raise ModelDisabled(_("Model %(model_id)r is disabled.") % {"model_id": model.model_id})
    if profile.only_free_models and not model.is_free:
        raise ModelDisabled(
            _("Profile %(name)r allows only free models; %(model_id)r is not free.")
            % {"name": profile.name, "model_id": model.model_id}
        )
