"""Модели каталога OpenRouter, профилей использования и логов."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Avg, Count, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_openrouter.fields import EncryptedTextField

Period = Literal["day", "month"]


def _decimal_from_pricing(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


@dataclass(frozen=True)
class UsageStats:
    """Агрегат расхода профиля за календарный день или месяц."""

    request_count: int
    total_cost: Decimal
    period: Period
    since: datetime


class OpenRouterModel(models.Model):
    """Модель из каталога OpenRouter (GET /api/v1/models)."""

    model_id = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("OpenRouter model id, e.g. anthropic/claude-3.5-sonnet"),
    )
    name = models.CharField(max_length=255)
    context_length = models.PositiveIntegerField(null=True, blank=True)
    pricing = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Per-token prices: prompt, completion, optional request/image."),
    )
    supported_parameters = models.JSONField(default=list, blank=True)
    modality = models.CharField(max_length=64, blank=True)
    prompt_price = models.DecimalField(
        max_digits=20,
        decimal_places=12,
        null=True,
        blank=True,
        help_text=_("Prompt price per token from the catalog, for admin sorting."),
    )
    completion_price = models.DecimalField(
        max_digits=20,
        decimal_places=12,
        null=True,
        blank=True,
        help_text=_("Completion price per token from the catalog, for admin sorting."),
    )
    latency_ms = models.FloatField(
        null=True,
        blank=True,
        help_text=_("p50 TTFT for the best endpoint, in milliseconds."),
    )
    throughput = models.FloatField(
        null=True,
        blank=True,
        help_text=_("p50 throughput (tok/s) for the best endpoint — load."),
    )
    parameter_count = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text=_("Approximate parameter count (70B → 70000000000), for sorting."),
    )
    parameter_label = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=_("Display size with unit, e.g. 70B, 340M, 8×7B."),
    )
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["model_id"]
        verbose_name = _("OpenRouter model")
        verbose_name_plural = _("OpenRouter models")

    def __str__(self) -> str:
        return self.model_id

    @property
    def is_free(self) -> bool:
        """True, если prompt/completion/request в каталоге равны нулю."""
        pricing = self.pricing or {}
        return (
            _decimal_from_pricing(pricing.get("prompt")) == 0
            and _decimal_from_pricing(pricing.get("completion")) == 0
            and _decimal_from_pricing(pricing.get("request")) == 0
        )


class UsageProfile(models.Model):
    """Профиль использования: модель + лимиты + fallback-цепочка."""

    name = models.SlugField(
        max_length=64,
        unique=True,
        help_text=_("Stable slug used in code, e.g. chat, translation."),
    )
    model = models.ForeignKey(
        OpenRouterModel,
        on_delete=models.PROTECT,
        related_name="profiles",
        null=True,
        blank=True,
        help_text=_("First model in the chain (synced from the list)."),
    )
    fallback_models = models.ManyToManyField(
        OpenRouterModel,
        through="UsageProfileFallback",
        related_name="fallback_profiles",
        blank=True,
    )
    max_tokens = models.PositiveIntegerField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    max_requests_per_day = models.PositiveIntegerField(null=True, blank=True)
    max_requests_per_month = models.PositiveIntegerField(null=True, blank=True)
    budget_usd_per_day = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )
    budget_usd_per_month = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )
    only_free_models = models.BooleanField(
        default=False,
        help_text=_("If enabled, only models with zero catalog price may be used."),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Usage profile")
        verbose_name_plural = _("Usage profiles")

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValidationError({"temperature": _("Temperature must be between 0 and 2.")})
        if self.model_id:
            primary = self.model
            if primary is None:
                return
            if not primary.is_active:
                raise ValidationError({"model": _("Primary model must be active.")})
            if self.only_free_models and not primary.is_free:
                raise ValidationError(
                    {"model": _("only_free_models requires a free primary model.")}
                )

    def get_usage(self, period: Period) -> UsageStats:
        """
        Суммирует RequestLog за текущий день или месяц.

        select_for_update вешается на строку профиля (mutex), а не на логи:
        иначе при росте таблицы блокировки взорвутся. Вызов безопасен как
        внутри transaction.atomic(), так и снаружи (обёртка создаётся сама).
        """
        if period not in ("day", "month"):
            raise ValueError("period must be 'day' or 'month'")
        since = _period_start(period)
        if transaction.get_connection().in_atomic_block:
            return self._aggregate_usage(period, since)
        with transaction.atomic():
            return self._aggregate_usage(period, since)

    def _aggregate_usage(self, period: Period, since: datetime) -> UsageStats:
        # Сериализуем проверки лимитов по профилю.
        type(self).objects.select_for_update().filter(pk=self.pk).get()
        aggregated = RequestLog.objects.filter(
            profile_id=self.pk,
            created_at__gte=since,
        ).aggregate(
            request_count=Count("id"),
            total_cost=Coalesce(
                Sum("cost_usd"),
                Value(Decimal("0.00")),
                output_field=models.DecimalField(max_digits=16, decimal_places=10),
            ),
        )
        total_cost = aggregated["total_cost"]
        if not isinstance(total_cost, Decimal):
            total_cost = Decimal(str(total_cost or 0))
        return UsageStats(
            request_count=int(aggregated["request_count"] or 0),
            total_cost=total_cost,
            period=period,
            since=since,
        )

    def ordered_models(self) -> list[OpenRouterModel]:
        """Полная цепочка моделей: приоритет по order, затем id."""
        links = self.fallback_links.select_related("model").order_by("order", "id")
        chain = [link.model for link in links if link.model_id]
        if chain:
            return chain
        if self.model_id:
            primary = self.model
            if primary is not None:
                return [primary]
        return []

    def ordered_fallback_models(self) -> list[OpenRouterModel]:
        """Модели цепочки после первой (совместимость со старым API)."""
        return self.ordered_models()[1:]

    def sync_primary_from_chain(self) -> None:
        """Пишет FK model из первой модели цепочки."""
        cache = getattr(self, "_prefetched_objects_cache", None)
        if isinstance(cache, dict):
            cache.pop("fallback_links", None)
        chain = self.ordered_models()
        first = chain[0] if chain else None
        first_id = first.pk if first is not None else None
        if self.model_id == first_id:
            return
        self.model = first
        self.save(update_fields=["model"])


class UsageProfileFallback(models.Model):
    """Through-модель: упорядоченный fallback UsageProfile → OpenRouterModel."""

    profile = models.ForeignKey(
        UsageProfile,
        on_delete=models.CASCADE,
        related_name="fallback_links",
    )
    model = models.ForeignKey(
        OpenRouterModel,
        on_delete=models.CASCADE,
        related_name="fallback_usages",
        limit_choices_to={"is_active": True},
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "model"],
                name="django_openrouter_fallback_unique",
            ),
        ]
        verbose_name = _("Profile model")
        verbose_name_plural = _("Profile models")

    def __str__(self) -> str:
        return f"{self.profile_id} → {self.model_id} ({self.order})"

    def clean(self) -> None:
        super().clean()
        if not self.model_id:
            return
        if not self.model.is_active:
            raise ValidationError({"model": _("Fallback model must be active.")})
        if self.profile_id and self.profile.only_free_models and not self.model.is_free:
            raise ValidationError(
                {"model": _("only_free_models allows only free fallback models.")}
            )


class OpenRouterSettings(models.Model):
    """Singleton-настройки интеграции. Всегда одна строка с pk=1."""

    api_key = EncryptedTextField(
        blank=True,
        default="",
        help_text=_("Leave empty to use OPENROUTER_API_KEY / settings.OPENROUTER['API_KEY']."),
    )
    base_url = models.URLField(default="https://openrouter.ai/api/v1")
    default_profile = models.ForeignKey(
        UsageProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    request_timeout = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text=_("HTTP timeout in seconds."),
    )
    max_retries = models.PositiveIntegerField(
        default=2,
        help_text=_("Retries per model on transport / 5xx errors before fallback."),
    )
    streaming_enabled = models.BooleanField(
        default=False,
        help_text=_("Allow SSE streaming via stream()/astream() and chat(stream=True)."),
    )
    max_parallel_requests = models.PositiveIntegerField(
        default=10,
        help_text=_(
            "Max concurrent HTTP requests to OpenRouter in this process. 0 = unlimited."
        ),
    )
    enabled = models.BooleanField(
        default=True,
        help_text=_("Global kill switch. When off, every chat() call fails."),
    )

    class Meta:
        verbose_name = _("OpenRouter settings")
        verbose_name_plural = _("OpenRouter settings")

    def __str__(self) -> str:
        return str(_("OpenRouter settings"))

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        # Singleton нельзя удалить.
        return 0, {}

    @classmethod
    def load(cls) -> OpenRouterSettings:
        """Возвращает единственную строку настроек, создавая её при необходимости."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class RequestLog(models.Model):
    """Лог каждого HTTP-вызова (включая неуспешные попытки и fallback)."""

    profile = models.ForeignKey(
        UsageProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="request_logs",
    )
    model = models.ForeignKey(
        OpenRouterModel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="request_logs",
    )
    status_code = models.PositiveIntegerField()
    error_message = models.TextField(null=True, blank=True)  # noqa: DJ001
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=16, decimal_places=10, default=Decimal("0"))
    latency_ms = models.PositiveIntegerField(default=0)
    username = models.CharField(
        max_length=150,
        default="anonymous",
        db_index=True,
        help_text=_("Authenticated user's username, or 'anonymous'."),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Request log")
        verbose_name_plural = _("Request logs")
        indexes = [
            models.Index(fields=["profile", "created_at"], name="or_log_profile_created"),
        ]
        permissions = [
            ("view_usage_logs", _("Can view usage logs")),
        ]

    def __str__(self) -> str:
        return f"{self.status_code} @ {self.created_at}"


@dataclass(frozen=True)
class ProfileUsageTotals:
    """All-time агрегаты RequestLog по одному профилю (для changelist)."""

    request_count: int
    avg_latency_ms: float
    total_latency_ms: int
    avg_cost_usd: Decimal
    total_cost_usd: Decimal


def usage_totals_by_profile(profile_ids: Sequence[int]) -> dict[int, ProfileUsageTotals]:
    """Один GROUP BY profile_id по переданным PK. Пустой список — без запроса."""
    if not profile_ids:
        return {}
    rows = (
        RequestLog.objects.filter(profile_id__in=list(profile_ids))
        .values("profile_id")
        .annotate(
            request_count=Count("id"),
            avg_latency_ms=Avg("latency_ms"),
            total_latency_ms=Sum("latency_ms"),
            avg_cost_usd=Avg("cost_usd"),
            total_cost_usd=Sum("cost_usd"),
        )
    )
    result: dict[int, ProfileUsageTotals] = {}
    for row in rows:
        pk = row["profile_id"]
        if pk is None:
            continue
        avg_cost = row["avg_cost_usd"]
        total_cost = row["total_cost_usd"]
        if not isinstance(avg_cost, Decimal):
            avg_cost = Decimal(str(avg_cost or 0))
        if not isinstance(total_cost, Decimal):
            total_cost = Decimal(str(total_cost or 0))
        result[int(pk)] = ProfileUsageTotals(
            request_count=int(row["request_count"] or 0),
            avg_latency_ms=float(row["avg_latency_ms"] or 0),
            total_latency_ms=int(row["total_latency_ms"] or 0),
            avg_cost_usd=avg_cost,
            total_cost_usd=total_cost,
        )
    return result


def _period_start(period: Period) -> datetime:
    """Начало текущего календарного дня/месяца в активном TIME_ZONE."""
    now = timezone.now()
    local = timezone.localtime(now) if timezone.is_aware(now) else now
    if period == "day":
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if timezone.is_aware(now) and timezone.is_naive(start):
        return timezone.make_aware(start, timezone.get_current_timezone())
    return start
