"""Проверка лимитов, бюджетов и ограничений профиля перед вызовом API."""

from __future__ import annotations

from decimal import ROUND_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils.translation import gettext as _

from django_openrouter.exceptions import (
    BudgetExceeded,
    ConfigurationError,
    ModelDisabled,
    RateLimitExceeded,
)
from django_openrouter.log_backends import DatabaseBackend, get_log_backends
from django_openrouter.models import OpenRouterModel, RequestLog, UsageProfile

_COST_QUANTUM = Decimal("0.0000000001")


def _maximum_model_cost(model: OpenRouterModel) -> Decimal:
    """Upper bound from catalog prices and the model's context window."""
    pricing = model.pricing or {}
    try:
        prompt = Decimal(str(pricing["prompt"]))
        completion = Decimal(str(pricing["completion"]))
        request = Decimal(str(pricing.get("request") or 0))
        image = Decimal(str(pricing.get("image") or 0))
        extra_prices = [
            Decimal(str(value or 0))
            for key, value in pricing.items()
            if key not in {"prompt", "completion", "request", "image"}
        ]
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ConfigurationError(
            _("Model %(model_id)r needs valid catalog pricing for budget reservations.")
            % {"model_id": model.model_id}
        ) from exc
    prices = (prompt, completion, request, image, *extra_prices)
    if any(not price.is_finite() or price < 0 for price in prices):
        raise ConfigurationError(_("Model pricing must be finite and non-negative."))
    if image or any(extra_prices) or model.modality != "text->text":
        raise ConfigurationError(
            _("Budget reservations require text-to-text models without extra charges.")
        )
    if max(prompt, completion) and not model.context_length:
        raise ConfigurationError(
            _("Model %(model_id)r needs context_length for budget reservations.")
            % {"model_id": model.model_id}
        )
    return (max(prompt, completion) * (model.context_length or 0) + request).quantize(
        _COST_QUANTUM, rounding=ROUND_UP
    )


def reserve_request(profile: UsageProfile, model: OpenRouterModel) -> RequestLog | None:
    """Atomically reserve one request and its worst-case catalog cost."""
    has_limits = any(
        value is not None
        for value in (
            profile.max_requests_per_day,
            profile.max_requests_per_month,
            profile.budget_usd_per_day,
            profile.budget_usd_per_month,
        )
    )
    if not has_limits:
        return None
    has_budget = profile.budget_usd_per_day is not None or profile.budget_usd_per_month is not None
    estimated_cost = _maximum_model_cost(model) if has_budget else Decimal("0")
    with transaction.atomic():
        locked = UsageProfile.objects.select_for_update().get(pk=profile.pk)
        check_limits(locked)
        day = locked.get_usage("day")
        month = locked.get_usage("month")
        if locked.budget_usd_per_day is not None and (
            day.total_cost + estimated_cost > locked.budget_usd_per_day
        ):
            raise BudgetExceeded(_("Insufficient daily budget for a conservative reservation."))
        if locked.budget_usd_per_month is not None and (
            month.total_cost + estimated_cost > locked.budget_usd_per_month
        ):
            raise BudgetExceeded(_("Insufficient monthly budget for a conservative reservation."))
        return RequestLog.objects.create(
            profile=locked,
            model=model,
            status_code=0,
            error_message="Reservation pending completion",
            cost_usd=estimated_cost,
        )


def check_limits(profile: UsageProfile) -> None:
    """
    HTTP-стоп при исчерпании лимитов. Fallback по моделям здесь не делается.

    Блокировка строки профиля + агрегация логов в одной транзакции.
    """
    if not profile.is_active:
        raise ModelDisabled(_("Usage profile %(name)r is disabled.") % {"name": profile.name})

    has_limits = any(
        value is not None
        for value in (
            profile.max_requests_per_day,
            profile.max_requests_per_month,
            profile.budget_usd_per_day,
            profile.budget_usd_per_month,
        )
    )
    has_database_backend = any(
        isinstance(backend, DatabaseBackend) for backend in get_log_backends()
    )
    if has_limits and not has_database_backend:
        raise ConfigurationError(
            _("DatabaseBackend is required when a usage profile has request or budget limits.")
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
