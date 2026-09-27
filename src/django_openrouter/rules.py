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
from django_openrouter.models import (
    RESERVATION_PENDING_MESSAGE,
    OpenRouterModel,
    RequestLog,
    UsageProfile,
)

_COST_QUANTUM = Decimal("0.0000000001")
# Цена за токен: каждый токен контекста тарифицируется не дороже максимальной из них.
_PER_TOKEN_PRICES = frozenset(
    {"prompt", "completion", "input_cache_read", "input_cache_write", "internal_reasoning"}
)
# Фиксированная цена за запрос (web_search — один поиск плагина на запрос).
_PER_REQUEST_PRICES = frozenset({"request", "web_search"})
_PER_IMAGE_PRICE = "image"
# Не цена, а коэффициент скидки.
_NON_PRICE_KEYS = frozenset({"discount"})


def _maximum_model_cost(model: OpenRouterModel, image_count: int = 0) -> Decimal:
    """Upper bound from catalog prices, the context window and input images."""
    pricing = model.pricing or {}
    invalid = ConfigurationError(
        _("Model %(model_id)r needs valid catalog pricing for budget reservations.")
        % {"model_id": model.model_id}
    )
    try:
        prices = {
            str(key): Decimal(str(value or 0))
            for key, value in pricing.items()
            if key not in _NON_PRICE_KEYS
        }
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise invalid from exc
    if "prompt" not in prices or "completion" not in prices:
        raise invalid
    if any(not price.is_finite() or price < 0 for price in prices.values()):
        raise ConfigurationError(_("Model pricing must be finite and non-negative."))
    known = _PER_TOKEN_PRICES | _PER_REQUEST_PRICES | {_PER_IMAGE_PRICE}
    unbounded = sorted(key for key, price in prices.items() if price and key not in known)
    output_modality = model.modality.rpartition("->")[2]
    if unbounded or output_modality != "text":
        raise ConfigurationError(
            _(
                "Budget reservations require models with text output and bounded pricing; "
                "%(model_id)r has unbounded charges: %(keys)s."
            )
            % {"model_id": model.model_id, "keys": ", ".join(unbounded) or model.modality or "-"}
        )
    token_price = max(price for key, price in prices.items() if key in _PER_TOKEN_PRICES)
    if token_price and not model.context_length:
        raise ConfigurationError(
            _("Model %(model_id)r needs context_length for budget reservations.")
            % {"model_id": model.model_id}
        )
    per_request = sum(
        (price for key, price in prices.items() if key in _PER_REQUEST_PRICES), Decimal("0")
    )
    per_image = prices.get(_PER_IMAGE_PRICE, Decimal("0")) * image_count
    return (token_price * (model.context_length or 0) + per_request + per_image).quantize(
        _COST_QUANTUM, rounding=ROUND_UP
    )


def reserve_request(
    profile: UsageProfile, model: OpenRouterModel, *, image_count: int = 0
) -> RequestLog | None:
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
    estimated_cost = _maximum_model_cost(model, image_count) if has_budget else Decimal("0")
    with transaction.atomic():
        locked = UsageProfile.objects.select_for_update().get(pk=profile.pk)
        check_limits(locked)
        day, month = locked.usage_summary()
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
            error_message=RESERVATION_PENDING_MESSAGE,
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
        # Lock only the profile: its nullable model join cannot be locked on PostgreSQL.
        locked = UsageProfile.objects.select_for_update().get(pk=profile.pk)
        day, month = locked.usage_summary()

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
