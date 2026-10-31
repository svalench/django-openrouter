"""Агрегаты RequestLog для staff-дашборда: расход, ошибки, латентность, бюджеты.

Окно и фильтры задаёт вызывающий код. Группировка по часу (период day) или по
дню (период month) идёт через TruncHour/TruncDay, чтобы запрос оставался
переносимым между SQLite и PostgreSQL. p95 считается в Python по ограниченной
выборке: у SQLite нет percentile, а полный скан latency на большой таблице
нельзя тащить в память.
"""

from __future__ import annotations

import calendar
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count, DecimalField, IntegerField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncHour
from django.utils import timezone
from django.utils.translation import gettext

from django_openrouter.models import (
    CLIENT_CLOSED_STATUS,
    OpenRouterModel,
    RequestLog,
    UsageProfile,
    _as_decimal,
)

PeriodName = Literal["day", "month"]
MetricName = Literal["cost", "requests", "error_rate"]
ChartKind = Literal["line", "bar"]
ChartUnit = Literal["usd", "count", "percent", "ms", "tokens"]
DeltaTone = Literal["good", "bad", "neutral", "flat", "none"]

# Не-2xx, включая 402/429/499/5xx и незакрытый резерв (status 0).
NON_2XX = ~Q(status_code__gte=200, status_code__lt=300)
# Как в UsageProfile.usage_summary: HTTP-ошибки не едят лимит запросов, 499 ест.
_COUNTED_REQUEST = ~Q(status_code__gte=400) | Q(status_code=CLIENT_CLOSED_STATUS)

P95_ROW_CAP = 20_000
MAX_SERIES = 8
TOP_N = 10
TABLE_ROW_CAP = 50
_MAX_HOURLY_DAYS = 7
_MAX_DAILY_DAYS = 366
_ZERO = Decimal("0")
_MONEY = DecimalField(max_digits=20, decimal_places=10)
_INT = IntegerField()

# Одна палитра на все графики: индекс серии (по убыванию стоимости) даёт тот же цвет.
_PALETTE = (
    "#3b82f6",
    "#14b8a6",
    "#f59e0b",
    "#a78bfa",
    "#fb7185",
    "#22d3ee",
    "#a3e635",
    "#94a3b8",
)
_OTHER_COLOR = "#64748b"
_AVG_COLOR = "#3b82f6"
_P95_COLOR = "#f59e0b"


@dataclass(frozen=True)
class DashboardFilters:
    """Выбранное окно и фильтры. end включительный, календарный."""

    period: PeriodName
    start: date
    end: date
    profile_id: int | None
    model_id: int | None
    clamped: bool

    @property
    def bucket(self) -> Literal["hour", "day"]:
        return "hour" if self.period == "day" else "day"


@dataclass
class _Agg:
    """Суммы одного бакета или группы. Средние считаются снаружи."""

    request_count: int = 0
    error_count: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    sum_latency: int = 0
    sum_tokens: int = 0

    def add(self, other: _Agg) -> None:
        self.request_count += other.request_count
        self.error_count += other.error_count
        self.cost += other.cost
        self.sum_latency += other.sum_latency
        self.sum_tokens += other.sum_tokens

    def copy(self) -> _Agg:
        return _Agg(
            self.request_count,
            self.error_count,
            self.cost,
            self.sum_latency,
            self.sum_tokens,
        )


@dataclass(frozen=True)
class BucketPoint:
    """Один час или один день на общей временной шкале."""

    start: datetime
    label: str
    request_count: int
    error_count: int
    error_rate: float | None
    cost_usd: Decimal
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_tokens: int
    avg_tokens: float | None
    p95_tokens: float | None


@dataclass(frozen=True)
class GroupRow:
    """Итог по профилю или модели за всё выбранное окно."""

    label: str
    request_count: int
    error_count: int
    error_rate: float | None
    cost_usd: Decimal
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_tokens: int
    avg_tokens: float | None
    p95_tokens: float | None


@dataclass(frozen=True)
class NamedSeries:
    """Линия графика, выровненная по бакетам окна."""

    label: str
    values: tuple[float | None, ...]


@dataclass(frozen=True)
class BudgetRow:
    """Текущие календарные сутки/месяц против лимитов профиля."""

    name: str
    day_requests: int
    day_request_limit: int | None
    day_request_pct: float | None
    month_requests: int
    month_request_limit: int | None
    month_request_pct: float | None
    day_cost: Decimal
    day_budget: Decimal | None
    day_cost_pct: float | None
    month_cost: Decimal
    month_budget: Decimal | None
    month_cost_pct: float | None


@dataclass(frozen=True)
class DashboardData:
    """Готовые числа дашборда. Подписи графиков собираются отдельно."""

    filters: DashboardFilters
    request_count: int
    error_count: int
    error_rate: float | None
    cost_usd: Decimal
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    total_tokens: int
    avg_tokens: float | None
    p95_tokens: float | None
    p95_approximate: bool
    p95_sample_size: int
    buckets: tuple[BucketPoint, ...]
    by_profile: tuple[GroupRow, ...]
    by_model: tuple[GroupRow, ...]
    profiles_truncated: bool
    models_truncated: bool
    top_profiles: tuple[GroupRow, ...]
    top_models: tuple[GroupRow, ...]
    profile_cost_series: tuple[NamedSeries, ...]
    profile_request_series: tuple[NamedSeries, ...]
    profile_error_series: tuple[NamedSeries, ...]
    model_cost_series: tuple[NamedSeries, ...]
    model_request_series: tuple[NamedSeries, ...]
    model_error_series: tuple[NamedSeries, ...]
    budgets: tuple[BudgetRow, ...]
    has_other: bool
    previous: PreviousTotals


@dataclass(frozen=True)
class ChartDataset:
    """Одна линия или группа столбцов. color стабилен для той же серии на соседних графиках."""

    label: str
    data: tuple[float | None, ...]
    color: str


@dataclass(frozen=True)
class ChartBlock:
    """Спека графика для Chart.js. В страницу попадает через json_script, без inline-скрипта."""

    id: str
    title: str
    kind: ChartKind
    unit: ChartUnit
    labels: tuple[str, ...]
    datasets: tuple[ChartDataset, ...]

    @property
    def empty(self) -> bool:
        if not self.labels:
            return True
        return not any(
            value is not None and math.isfinite(value)
            for dataset in self.datasets
            for value in dataset.data
        )


@dataclass(frozen=True)
class PreviousTotals:
    """Окно той же длины непосредственно перед выбранным диапазоном."""

    start: date
    end: date
    request_count: int
    error_count: int
    error_rate: float | None
    cost_usd: Decimal
    p95_latency_ms: float | None


@dataclass(frozen=True)
class ChartSection:
    """Группа графиков с заголовком секции."""

    title: str
    charts: tuple[ChartBlock, ...]


def parse_filters(
    params: Mapping[str, object],
    *,
    today: date | None = None,
) -> DashboardFilters:
    """Читает GET-параметры. Битый ввод заменяется на окно по умолчанию."""
    current = today if today is not None else timezone.localdate()
    period: PeriodName = "month" if _text(params.get("period")) == "month" else "day"
    start = _parse_date(_text(params.get("start")))
    end = _parse_date(_text(params.get("end")))
    if start is None and end is None:
        if period == "day":
            start = end = current
        else:
            start = current.replace(day=1)
            end = _month_end(current)
    elif start is None:
        start = end
    elif end is None:
        end = start
    assert start is not None and end is not None
    if start > end:
        start, end = end, start
    max_days = _MAX_HOURLY_DAYS if period == "day" else _MAX_DAILY_DAYS
    clamped = False
    if (end - start).days + 1 > max_days:
        end = start + timedelta(days=max_days - 1)
        clamped = True
    return DashboardFilters(
        period=period,
        start=start,
        end=end,
        profile_id=_parse_pk(params.get("profile")),
        model_id=_parse_pk(params.get("model")),
        clamped=clamped,
    )


def preset_links(filters: DashboardFilters, *, today: date | None = None) -> dict[str, str]:
    """Ссылки «сегодня» и «этот месяц», сохраняющие фильтр профиля и модели."""
    current = today if today is not None else timezone.localdate()
    return {
        "today": _query(filters, period="day", start=current, end=current),
        "month": _query(
            filters,
            period="month",
            start=current.replace(day=1),
            end=_month_end(current),
        ),
    }


def percentile(values: Sequence[int], pct: float) -> float | None:
    """Линейная интерполяция между соседними рангами. Пустой набор — None."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def build_dashboard(filters: DashboardFilters, *, now: datetime | None = None) -> DashboardData:
    """Считает дашборд несколькими GROUP BY и одной ограниченной выборкой p95."""
    current = now or timezone.now()
    start_dt, end_dt = bounds(filters)
    qs = _filtered(filters, start_dt, end_dt)
    bucket_starts = _iter_buckets(start_dt, end_dt, filters.period)
    by_profile = _grouped(qs, filters.period, "profile_id")
    by_model = _grouped(qs, filters.period, "model_id")
    sample, approximate = _p95_sample(qs)
    profile_labels = _profile_labels(set(by_profile))
    model_labels = _model_labels(set(by_model))
    no_profile = str(gettext("(no profile)"))
    no_model = str(gettext("(no model)"))
    profile_labels.setdefault(None, no_profile)
    model_labels.setdefault(None, no_model)

    profile_buckets = _buckets_by_key(by_profile)
    model_buckets = _buckets_by_key(by_model)
    overall = _sum_buckets(profile_buckets, bucket_starts)
    latency_by_bucket, tokens_by_bucket, latency_by_profile, tokens_by_profile = _sample_maps(
        sample, filters.period, by_profile=True
    )
    _, _, latency_by_model, tokens_by_model = _sample_maps(
        sample, filters.period, by_profile=False
    )
    all_latency = [latency for row in sample for latency in (int(row[1]),)]
    all_tokens = [int(row[2]) + int(row[3]) for row in sample]

    points: list[BucketPoint] = []
    for start in bucket_starts:
        agg = overall[start]
        points.append(
            _bucket_point(
                start,
                agg,
                filters,
                p95_latency=percentile(latency_by_bucket.get(start, []), 95),
                p95_tokens=percentile(tokens_by_bucket.get(start, []), 95),
            )
        )

    profile_rows, profiles_truncated = _group_rows(
        profile_buckets,
        profile_labels,
        latency_by_profile,
        tokens_by_profile,
    )
    model_rows, models_truncated = _group_rows(
        model_buckets,
        model_labels,
        latency_by_model,
        tokens_by_model,
    )
    cost_profile, req_profile, err_profile, other_profile = _metric_series(
        bucket_starts, profile_buckets, profile_labels
    )
    cost_model, req_model, err_model, other_model = _metric_series(
        bucket_starts, model_buckets, model_labels
    )
    total = _Agg()
    for agg in overall.values():
        total.add(agg)
    previous = _previous_totals(filters)
    return DashboardData(
        filters=filters,
        request_count=total.request_count,
        error_count=total.error_count,
        error_rate=_rate(total.error_count, total.request_count),
        cost_usd=total.cost,
        avg_latency_ms=_avg(total.sum_latency, total.request_count),
        p95_latency_ms=percentile(all_latency, 95),
        total_tokens=total.sum_tokens,
        avg_tokens=_avg(total.sum_tokens, total.request_count),
        p95_tokens=percentile(all_tokens, 95),
        p95_approximate=approximate,
        p95_sample_size=len(sample),
        buckets=tuple(points),
        by_profile=profile_rows,
        by_model=model_rows,
        profiles_truncated=profiles_truncated,
        models_truncated=models_truncated,
        top_profiles=profile_rows[:TOP_N],
        top_models=model_rows[:TOP_N],
        profile_cost_series=cost_profile,
        profile_request_series=req_profile,
        profile_error_series=err_profile,
        model_cost_series=cost_model,
        model_request_series=req_model,
        model_error_series=err_model,
        budgets=_budgets(filters.profile_id, now=current),
        has_other=other_profile or other_model,
        previous=previous,
    )


def model_choices(filters: DashboardFilters) -> list[tuple[int, str]]:
    """Модели, которые уже есть в окне (и явно выбранная, даже если пусто)."""
    start_dt, end_dt = bounds(filters)
    qs = RequestLog.objects.filter(
        created_at__gte=start_dt,
        created_at__lt=end_dt,
        model_id__isnull=False,
    )
    if filters.profile_id is not None:
        qs = qs.filter(profile_id=filters.profile_id)
    ids = {int(pk) for pk in qs.values_list("model_id", flat=True).distinct() if pk is not None}
    if filters.model_id is not None:
        ids.add(filters.model_id)
    if not ids:
        return []
    rows = OpenRouterModel.objects.filter(pk__in=ids).order_by("name", "model_id")
    return [(row.pk, row.name or row.model_id) for row in rows]


def chart_sections(data: DashboardData) -> tuple[ChartSection, ...]:
    """Спеки Chart.js: линии по времени и столбцы avg/p95 по группам."""
    labels = tuple(point.label for point in data.buckets)
    over_time = ChartSection(
        title=str(gettext("Over time")),
        charts=(
            _line_block(
                "over-cost",
                str(gettext("Cost (USD)")),
                "usd",
                labels,
                (
                    ChartDataset(
                        str(gettext("Cost (USD)")),
                        tuple(float(point.cost_usd) for point in data.buckets),
                        _PALETTE[0],
                    ),
                ),
            ),
            _line_block(
                "over-requests",
                str(gettext("Requests")),
                "count",
                labels,
                (
                    ChartDataset(
                        str(gettext("Requests")),
                        tuple(float(point.request_count) for point in data.buckets),
                        _PALETTE[1],
                    ),
                ),
            ),
            _line_block(
                "over-errors",
                str(gettext("Error rate")),
                "percent",
                labels,
                (
                    ChartDataset(
                        str(gettext("Error rate")),
                        tuple(point.error_rate for point in data.buckets),
                        _PALETTE[4],
                    ),
                ),
            ),
            _line_block(
                "over-latency",
                str(gettext("Latency (ms)")),
                "ms",
                labels,
                _avg_p95(
                    tuple(point.avg_latency_ms for point in data.buckets),
                    tuple(point.p95_latency_ms for point in data.buckets),
                ),
            ),
            _line_block(
                "over-tokens",
                str(gettext("Tokens")),
                "tokens",
                labels,
                _avg_p95(
                    tuple(point.avg_tokens for point in data.buckets),
                    tuple(point.p95_tokens for point in data.buckets),
                ),
            ),
        ),
    )
    by_profile = _group_section(
        "profile",
        str(gettext("By profile")),
        labels,
        data.profile_cost_series,
        data.profile_request_series,
        data.profile_error_series,
        data.by_profile,
    )
    by_model = _group_section(
        "model",
        str(gettext("By model")),
        labels,
        data.model_cost_series,
        data.model_request_series,
        data.model_error_series,
        data.by_model,
    )
    return (over_time, by_profile, by_model)


def chart_payload(sections: Sequence[ChartSection]) -> dict[str, object]:
    """JSON для json_script. Пустые графики остаются текстом в шаблоне."""
    payload: dict[str, object] = {}
    for section in sections:
        for chart in section.charts:
            if chart.empty:
                continue
            payload[chart.id] = {
                "kind": chart.kind,
                "unit": chart.unit,
                "labels": list(chart.labels),
                "datasets": [
                    {"label": item.label, "data": list(item.data), "color": item.color}
                    for item in chart.datasets
                ],
            }
    return payload


def format_usd(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.000001"))
    return f"${format(quantized, 'f')}"


def format_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}%"


def format_ms(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value)} ms"


def format_tokens(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value):,}"


def present(data: DashboardData) -> dict[str, object]:
    """Строки для шаблона. Деньги остаются Decimal только внутри расчёта."""
    sections = chart_sections(data) if data.request_count else ()
    return {
        "cost": format_usd(data.cost_usd),
        "requests": f"{data.request_count:,}",
        "error_rate": format_rate(data.error_rate),
        "avg_latency": format_ms(data.avg_latency_ms),
        "p95_latency": format_ms(data.p95_latency_ms),
        "total_tokens": f"{data.total_tokens:,}",
        "avg_tokens": format_tokens(data.avg_tokens),
        "p95_tokens": format_tokens(data.p95_tokens),
        "empty": data.request_count == 0,
        "p95_approximate": data.p95_approximate,
        "p95_sample_size": data.p95_sample_size,
        "has_other": data.has_other,
        "sections": sections,
        "chart_data": chart_payload(sections),
        "deltas": _deltas(data),
        "prior_period": format_prior_period(data.previous.start, data.previous.end),
        "top_profiles": [_group_dict(row) for row in data.top_profiles],
        "top_models": [_group_dict(row) for row in data.top_models],
        "by_profile": [_group_dict(row) for row in data.by_profile],
        "by_model": [_group_dict(row) for row in data.by_model],
        "profiles_truncated": data.profiles_truncated,
        "models_truncated": data.models_truncated,
        "budgets": [_budget_dict(row) for row in data.budgets],
    }


def _deltas(data: DashboardData) -> dict[str, dict[str, str]]:
    previous = data.previous
    return {
        "cost": _delta_money(data.cost_usd, previous.cost_usd),
        "requests": _delta_count(data.request_count, previous.request_count),
        "error_rate": _delta_rate(data.error_rate, previous.error_rate),
        "latency": _delta_latency(data.p95_latency_ms, previous.p95_latency_ms),
    }


def _delta_money(current: Decimal, previous: Decimal) -> dict[str, str]:
    absolute = current - previous
    if absolute == 0:
        return {"text": format_usd(_ZERO), "relative": "0.0%", "tone": "flat"}
    relative = ""
    if previous != 0:
        change = (absolute / previous) * Decimal(100)
        relative = f"{change:+.1f}%"
    tone: DeltaTone = "bad" if absolute > 0 else "good"
    return {"text": _signed_money(absolute), "relative": relative, "tone": tone}


def _signed_money(value: Decimal) -> str:
    if value > 0:
        return "+" + format_usd(value)
    if value < 0:
        return "-" + format_usd(-value)
    return format_usd(value)


def _delta_count(current: int, previous: int) -> dict[str, str]:
    absolute = current - previous
    if absolute == 0:
        return {"text": "0", "relative": "0.0%", "tone": "flat"}
    relative = ""
    if previous:
        relative = f"{absolute * 100 / previous:+.1f}%"
    return {"text": f"{absolute:+,}", "relative": relative, "tone": "neutral"}


def _delta_rate(current: float | None, previous: float | None) -> dict[str, str]:
    if current is None or previous is None:
        missing_prior = previous is None and current is not None
        note = str(gettext("No earlier data")) if missing_prior else "—"
        return {"text": note, "relative": "", "tone": "none"}
    absolute = current - previous
    unit = str(gettext("pp"))
    if abs(absolute) < 0.05:
        return {"text": f"0.0 {unit}", "relative": "", "tone": "flat"}
    tone: DeltaTone = "bad" if absolute > 0 else "good"
    return {"text": f"{absolute:+.1f} {unit}", "relative": "", "tone": tone}


def _delta_latency(current: float | None, previous: float | None) -> dict[str, str]:
    if current is None or previous is None:
        missing_prior = previous is None and current is not None
        note = str(gettext("No earlier data")) if missing_prior else "—"
        return {"text": note, "relative": "", "tone": "none"}
    absolute = current - previous
    if abs(absolute) < 0.5:
        return {"text": "0 ms", "relative": "0.0%", "tone": "flat"}
    relative = ""
    if previous:
        relative = f"{absolute * 100 / previous:+.1f}%"
    tone: DeltaTone = "bad" if absolute > 0 else "good"
    return {"text": f"{round(absolute):+d} ms", "relative": relative, "tone": tone}


def format_prior_period(start: date, end: date) -> str:
    if start == end:
        return start.isoformat()
    return f"{start.isoformat()} - {end.isoformat()}"


def bounds(filters: DashboardFilters) -> tuple[datetime, datetime]:
    """Полуинтервал [start 00:00, end+1day 00:00) в текущей таймзоне."""
    return _midnight(filters.start), _midnight(filters.end + timedelta(days=1))


def previous_dates(filters: DashboardFilters) -> tuple[date, date]:
    """Календарное окно той же длины, заканчивающееся в день перед filters.start."""
    span = (filters.end - filters.start).days + 1
    end = filters.start - timedelta(days=1)
    start = end - timedelta(days=span - 1)
    return start, end


def _previous_totals(filters: DashboardFilters) -> PreviousTotals:
    """Итоги прошлого окна: один агрегат и ограниченная выборка latency для p95."""
    start, end = previous_dates(filters)
    start_dt, end_dt = _midnight(start), _midnight(end + timedelta(days=1))
    qs = _filtered(filters, start_dt, end_dt)
    row = qs.aggregate(
        request_count=Count("id"),
        error_count=Count("id", filter=NON_2XX),
        total_cost=Coalesce(Sum("cost_usd"), Value(_ZERO), output_field=_MONEY),
    )
    request_count = int(row["request_count"] or 0)
    error_count = int(row["error_count"] or 0)
    latencies = [
        int(value or 0)
        for value in qs.order_by("-created_at").values_list("latency_ms", flat=True)[:P95_ROW_CAP]
    ]
    return PreviousTotals(
        start=start,
        end=end,
        request_count=request_count,
        error_count=error_count,
        error_rate=_rate(error_count, request_count),
        cost_usd=_as_decimal(row["total_cost"]),
        p95_latency_ms=percentile(latencies, 95),
    )


def _filtered(
    filters: DashboardFilters, start_dt: datetime, end_dt: datetime
) -> QuerySet[RequestLog]:
    qs = RequestLog.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
    if filters.profile_id is not None:
        qs = qs.filter(profile_id=filters.profile_id)
    if filters.model_id is not None:
        qs = qs.filter(model_id=filters.model_id)
    return qs


def _grouped(
    qs: QuerySet[RequestLog],
    period: PeriodName,
    group_field: str,
) -> dict[int | None, dict[datetime, _Agg]]:
    """GROUP BY бакет + profile_id или model_id. Ordering сброшен, чтобы не раздувать группы."""
    tz = timezone.get_current_timezone()
    trunc = (
        TruncHour("created_at", tzinfo=tz)
        if period == "day"
        else TruncDay("created_at", tzinfo=tz)
    )
    rows = (
        qs.annotate(_bucket=trunc)
        .values("_bucket", group_field)
        .annotate(
            request_count=Count("id"),
            error_count=Count("id", filter=NON_2XX),
            total_cost=Coalesce(Sum("cost_usd"), Value(_ZERO), output_field=_MONEY),
            sum_latency=Coalesce(Sum("latency_ms"), Value(0), output_field=_INT),
            sum_prompt=Coalesce(Sum("prompt_tokens"), Value(0), output_field=_INT),
            sum_completion=Coalesce(Sum("completion_tokens"), Value(0), output_field=_INT),
        )
        .order_by()
    )
    grouped: dict[int | None, dict[datetime, _Agg]] = defaultdict(dict)
    for row in rows:
        raw_key = row[group_field]
        key = int(raw_key) if raw_key is not None else None
        bucket = row["_bucket"]
        if not isinstance(bucket, datetime):
            continue
        grouped[key][bucket_key(bucket, period)] = _agg_from_row(row)
    return grouped


def _p95_sample(
    qs: QuerySet[RequestLog],
) -> tuple[list[tuple[datetime, int, int, int, int | None, int | None]], bool]:
    """Самые свежие строки окна, не больше P95_ROW_CAP. Лишняя строка — признак приближения."""
    rows = list(
        qs.order_by("-created_at").values_list(
            "created_at",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "profile_id",
            "model_id",
        )[: P95_ROW_CAP + 1]
    )
    approximate = len(rows) > P95_ROW_CAP
    if approximate:
        rows = rows[:P95_ROW_CAP]
    typed: list[tuple[datetime, int, int, int, int | None, int | None]] = []
    for created_at, latency, prompt, completion, profile_id, model_id in rows:
        if not isinstance(created_at, datetime):
            continue
        typed.append(
            (
                created_at,
                int(latency or 0),
                int(prompt or 0),
                int(completion or 0),
                int(profile_id) if profile_id is not None else None,
                int(model_id) if model_id is not None else None,
            )
        )
    return typed, approximate


def _sample_maps(
    sample: Sequence[tuple[datetime, int, int, int, int | None, int | None]],
    period: PeriodName,
    *,
    by_profile: bool,
) -> tuple[
    dict[datetime, list[int]],
    dict[datetime, list[int]],
    dict[int | None, list[int]],
    dict[int | None, list[int]],
]:
    by_bucket_latency: dict[datetime, list[int]] = defaultdict(list)
    by_bucket_tokens: dict[datetime, list[int]] = defaultdict(list)
    by_group_latency: dict[int | None, list[int]] = defaultdict(list)
    by_group_tokens: dict[int | None, list[int]] = defaultdict(list)
    for created_at, latency, prompt, completion, profile_id, model_id in sample:
        tokens = prompt + completion
        key = bucket_key(created_at, period)
        by_bucket_latency[key].append(latency)
        by_bucket_tokens[key].append(tokens)
        group_id = profile_id if by_profile else model_id
        by_group_latency[group_id].append(latency)
        by_group_tokens[group_id].append(tokens)
    return by_bucket_latency, by_bucket_tokens, by_group_latency, by_group_tokens


def _budgets(profile_id: int | None, *, now: datetime) -> tuple[BudgetRow, ...]:
    """Календарные сутки и месяц. Модельный фильтр дашборда сюда не входит."""
    profiles = UsageProfile.objects.all()
    if profile_id is not None:
        profiles = profiles.filter(pk=profile_id)
    profile_list = list(profiles.order_by("name"))
    if not profile_list:
        return ()
    day_start = _period_start(now, "day")
    month_start = _period_start(now, "month")
    is_today = Q(created_at__gte=day_start)
    aggregated = (
        RequestLog.objects.filter(
            profile_id__in=[profile.pk for profile in profile_list],
            created_at__gte=month_start,
        )
        .values("profile_id")
        .annotate(
            day_count=Count("id", filter=is_today & _COUNTED_REQUEST),
            month_count=Count("id", filter=_COUNTED_REQUEST),
            day_cost=Coalesce(
                Sum("cost_usd", filter=is_today),
                Value(_ZERO),
                output_field=_MONEY,
            ),
            month_cost=Coalesce(Sum("cost_usd"), Value(_ZERO), output_field=_MONEY),
        )
        .order_by()
    )
    by_id: dict[int, Any] = {}
    for aggregated_row in aggregated:
        profile_pk = aggregated_row["profile_id"]
        if profile_pk is not None:
            by_id[int(profile_pk)] = aggregated_row
    result: list[BudgetRow] = []
    for profile in profile_list:
        row = by_id.get(profile.pk, {})
        day_requests = int(row.get("day_count") or 0)
        month_requests = int(row.get("month_count") or 0)
        day_cost = _as_decimal(row.get("day_cost"))
        month_cost = _as_decimal(row.get("month_cost"))
        result.append(
            BudgetRow(
                name=profile.name,
                day_requests=day_requests,
                day_request_limit=profile.max_requests_per_day,
                day_request_pct=_percent(day_requests, profile.max_requests_per_day),
                month_requests=month_requests,
                month_request_limit=profile.max_requests_per_month,
                month_request_pct=_percent(month_requests, profile.max_requests_per_month),
                day_cost=day_cost,
                day_budget=profile.budget_usd_per_day,
                day_cost_pct=_percent(day_cost, profile.budget_usd_per_day),
                month_cost=month_cost,
                month_budget=profile.budget_usd_per_month,
                month_cost_pct=_percent(month_cost, profile.budget_usd_per_month),
            )
        )
    return tuple(result)


def bucket_key(value: datetime, period: PeriodName) -> datetime:
    """Начало часа или локальных суток. Совпадает с Trunc* в текущей таймзоне."""
    current = value
    if settings.USE_TZ:
        tz = timezone.get_current_timezone()
        if timezone.is_naive(current):
            current = timezone.make_aware(current, UTC)
        current = timezone.localtime(current, tz)
    if period == "day":
        return current.replace(minute=0, second=0, microsecond=0)
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def _iter_buckets(start_dt: datetime, end_dt: datetime, period: PeriodName) -> list[datetime]:
    cursor = bucket_key(start_dt, period)
    step = timedelta(hours=1) if period == "day" else timedelta(days=1)
    buckets: list[datetime] = []
    # Окно уже зажато parse_filters, здесь только защита от вечного цикла.
    limit = 24 * _MAX_HOURLY_DAYS + 2 if period == "day" else _MAX_DAILY_DAYS + 2
    while cursor < end_dt and len(buckets) < limit:
        buckets.append(cursor)
        cursor += step
    return buckets


def _bucket_point(
    start: datetime,
    agg: _Agg,
    filters: DashboardFilters,
    *,
    p95_latency: float | None,
    p95_tokens: float | None,
) -> BucketPoint:
    return BucketPoint(
        start=start,
        label=_bucket_label(start, filters),
        request_count=agg.request_count,
        error_count=agg.error_count,
        error_rate=_rate(agg.error_count, agg.request_count),
        cost_usd=agg.cost,
        avg_latency_ms=_avg(agg.sum_latency, agg.request_count),
        p95_latency_ms=p95_latency,
        total_tokens=agg.sum_tokens,
        avg_tokens=_avg(agg.sum_tokens, agg.request_count),
        p95_tokens=p95_tokens,
    )


def _bucket_label(start: datetime, filters: DashboardFilters) -> str:
    if filters.period == "day":
        if filters.start != filters.end:
            return start.strftime("%m-%d %H:%M")
        return start.strftime("%H:%M")
    return start.strftime("%Y-%m-%d")


def _group_rows(
    grouped: dict[int | None, dict[datetime, _Agg]],
    labels: dict[int | None, str],
    latency: dict[int | None, list[int]],
    tokens: dict[int | None, list[int]],
) -> tuple[tuple[GroupRow, ...], bool]:
    rows: list[GroupRow] = []
    for key, buckets in grouped.items():
        total = _Agg()
        for agg in buckets.values():
            total.add(agg)
        label = labels.get(key) or str(gettext("(no profile)"))
        rows.append(
            GroupRow(
                label=label,
                request_count=total.request_count,
                error_count=total.error_count,
                error_rate=_rate(total.error_count, total.request_count),
                cost_usd=total.cost,
                avg_latency_ms=_avg(total.sum_latency, total.request_count),
                p95_latency_ms=percentile(latency.get(key, []), 95),
                total_tokens=total.sum_tokens,
                avg_tokens=_avg(total.sum_tokens, total.request_count),
                p95_tokens=percentile(tokens.get(key, []), 95),
            )
        )
    rows.sort(key=lambda row: (-row.cost_usd, row.label.casefold()))
    truncated = len(rows) > TABLE_ROW_CAP
    return tuple(rows[:TABLE_ROW_CAP]), truncated


def _metric_series(
    bucket_starts: Sequence[datetime],
    grouped: dict[int | None, dict[datetime, _Agg]],
    labels: dict[int | None, str],
) -> tuple[tuple[NamedSeries, ...], tuple[NamedSeries, ...], tuple[NamedSeries, ...], bool]:
    ranked: list[tuple[Decimal, int | None, dict[datetime, _Agg]]] = []
    for key, buckets in grouped.items():
        cost = sum((agg.cost for agg in buckets.values()), _ZERO)
        ranked.append((cost, key, buckets))
    ranked.sort(key=lambda item: (-item[0], labels.get(item[1], "").casefold()))
    has_other = len(ranked) > MAX_SERIES
    chosen = ranked[: MAX_SERIES - 1] if has_other else ranked
    series_aggs: list[tuple[str, dict[datetime, _Agg]]] = [
        (labels.get(key) or str(gettext("(no profile)")), buckets) for _, key, buckets in chosen
    ]
    if has_other:
        other: dict[datetime, _Agg] = {}
        for _, _, buckets in ranked[MAX_SERIES - 1 :]:
            for start, agg in buckets.items():
                slot = other.get(start)
                if slot is None:
                    other[start] = agg.copy()
                else:
                    slot.add(agg)
        series_aggs.append((str(gettext("Other")), other))
    return (
        _named(bucket_starts, series_aggs, "cost"),
        _named(bucket_starts, series_aggs, "requests"),
        _named(bucket_starts, series_aggs, "error_rate"),
        has_other,
    )


def _named(
    bucket_starts: Sequence[datetime],
    series_aggs: Sequence[tuple[str, dict[datetime, _Agg]]],
    metric: MetricName,
) -> tuple[NamedSeries, ...]:
    named: list[NamedSeries] = []
    for label, buckets in series_aggs:
        values = tuple(_metric_value(buckets.get(start), metric) for start in bucket_starts)
        named.append(NamedSeries(label=label, values=values))
    return tuple(named)


def _metric_value(agg: _Agg | None, metric: MetricName) -> float | None:
    if agg is None or agg.request_count == 0:
        if metric == "error_rate":
            return None
        return 0.0
    if metric == "cost":
        return float(agg.cost)
    if metric == "requests":
        return float(agg.request_count)
    return agg.error_count * 100.0 / agg.request_count


def _group_section(
    prefix: str,
    title: str,
    labels: Sequence[str],
    cost: Sequence[NamedSeries],
    requests: Sequence[NamedSeries],
    errors: Sequence[NamedSeries],
    rows: Sequence[GroupRow],
) -> ChartSection:
    top = rows[:MAX_SERIES]
    names = tuple(row.label for row in top)
    other = bool(cost) and cost[-1].label == str(gettext("Other"))
    return ChartSection(
        title=title,
        charts=(
            _line_block(
                f"{prefix}-cost",
                str(gettext("Cost (USD)")),
                "usd",
                labels,
                _colored(cost, other=other),
            ),
            _line_block(
                f"{prefix}-requests",
                str(gettext("Requests")),
                "count",
                labels,
                _colored(requests, other=other),
            ),
            _line_block(
                f"{prefix}-errors",
                str(gettext("Error rate")),
                "percent",
                labels,
                _colored(errors, other=other),
            ),
            _bar_block(
                f"{prefix}-latency",
                str(gettext("Latency (ms)")),
                "ms",
                names,
                _avg_p95(
                    tuple(row.avg_latency_ms for row in top),
                    tuple(row.p95_latency_ms for row in top),
                ),
            ),
            _bar_block(
                f"{prefix}-tokens",
                str(gettext("Tokens")),
                "tokens",
                names,
                _avg_p95(
                    tuple(row.avg_tokens for row in top),
                    tuple(row.p95_tokens for row in top),
                ),
            ),
        ),
    )


def _line_block(
    chart_id: str,
    title: str,
    unit: ChartUnit,
    labels: Sequence[str],
    datasets: Sequence[ChartDataset],
) -> ChartBlock:
    return ChartBlock(chart_id, title, "line", unit, tuple(labels), tuple(datasets))


def _bar_block(
    chart_id: str,
    title: str,
    unit: ChartUnit,
    labels: Sequence[str],
    datasets: Sequence[ChartDataset],
) -> ChartBlock:
    return ChartBlock(chart_id, title, "bar", unit, tuple(labels), tuple(datasets))


def _avg_p95(
    average: Sequence[float | None],
    p95: Sequence[float | None],
) -> tuple[ChartDataset, ...]:
    return (
        ChartDataset(str(gettext("Average")), tuple(average), _AVG_COLOR),
        ChartDataset(str(gettext("p95")), tuple(p95), _P95_COLOR),
    )


def _colored(series: Sequence[NamedSeries], *, other: bool) -> tuple[ChartDataset, ...]:
    last = len(series) - 1
    painted: list[ChartDataset] = []
    for index, item in enumerate(series):
        if other and index == last:
            color = _OTHER_COLOR
        else:
            color = _PALETTE[index % len(_PALETTE)]
        painted.append(ChartDataset(item.label, item.values, color))
    return tuple(painted)


def _group_dict(row: GroupRow) -> dict[str, object]:
    return {
        "label": row.label,
        "requests": f"{row.request_count:,}",
        "error_rate": format_rate(row.error_rate),
        "cost": format_usd(row.cost_usd),
        "avg_latency": format_ms(row.avg_latency_ms),
        "p95_latency": format_ms(row.p95_latency_ms),
        "avg_tokens": format_tokens(row.avg_tokens),
        "p95_tokens": format_tokens(row.p95_tokens),
        "total_tokens": f"{row.total_tokens:,}",
    }


def _budget_dict(row: BudgetRow) -> dict[str, object]:
    return {
        "name": row.name,
        "day_requests": f"{row.day_requests:,}",
        "day_request_limit": _format_limit(row.day_request_limit),
        "day_request_pct": format_rate(row.day_request_pct)
        if row.day_request_limit is not None
        else "—",
        "day_request_over": row.day_request_pct is not None and row.day_request_pct >= 100,
        "month_requests": f"{row.month_requests:,}",
        "month_request_limit": _format_limit(row.month_request_limit),
        "month_request_pct": (
            format_rate(row.month_request_pct) if row.month_request_limit is not None else "—"
        ),
        "month_request_over": row.month_request_pct is not None and row.month_request_pct >= 100,
        "day_cost": format_usd(row.day_cost),
        "day_budget": format_usd(row.day_budget)
        if row.day_budget is not None
        else str(gettext("unlimited")),
        "day_cost_pct": format_rate(row.day_cost_pct) if row.day_budget is not None else "—",
        "day_cost_over": row.day_cost_pct is not None and row.day_cost_pct >= 100,
        "month_cost": format_usd(row.month_cost),
        "month_budget": (
            format_usd(row.month_budget)
            if row.month_budget is not None
            else str(gettext("unlimited"))
        ),
        "month_cost_pct": format_rate(row.month_cost_pct) if row.month_budget is not None else "—",
        "month_cost_over": row.month_cost_pct is not None and row.month_cost_pct >= 100,
    }


def _format_limit(value: int | None) -> str:
    if value is None:
        return str(gettext("unlimited"))
    return f"{value:,}"


def _profile_labels(keys: set[int | None]) -> dict[int | None, str]:
    ids = [key for key in keys if key is not None]
    if not ids:
        return {}
    return {
        int(pk): name
        for pk, name in UsageProfile.objects.filter(pk__in=ids).values_list("pk", "name")
    }


def _model_labels(keys: set[int | None]) -> dict[int | None, str]:
    ids = [key for key in keys if key is not None]
    if not ids:
        return {}
    labels: dict[int | None, str] = {}
    for pk, name, model_id in OpenRouterModel.objects.filter(pk__in=ids).values_list(
        "pk", "name", "model_id"
    ):
        labels[int(pk)] = name or model_id
    return labels


def _buckets_by_key(
    grouped: dict[int | None, dict[datetime, _Agg]],
) -> dict[int | None, dict[datetime, _Agg]]:
    return grouped


def _sum_buckets(
    grouped: dict[int | None, dict[datetime, _Agg]],
    bucket_starts: Sequence[datetime],
) -> dict[datetime, _Agg]:
    overall = {start: _Agg() for start in bucket_starts}
    for buckets in grouped.values():
        for start, agg in buckets.items():
            slot = overall.get(start)
            if slot is None:
                overall[start] = agg.copy()
            else:
                slot.add(agg)
    return overall


def _agg_from_row(row: Mapping[str, Any]) -> _Agg:
    return _Agg(
        request_count=int(row["request_count"] or 0),
        error_count=int(row["error_count"] or 0),
        cost=_as_decimal(row["total_cost"]),
        sum_latency=int(row["sum_latency"] or 0),
        sum_tokens=int(row["sum_prompt"] or 0) + int(row["sum_completion"] or 0),
    )


def _avg(total: int, count: int) -> float | None:
    if count <= 0:
        return None
    return total / count


def _rate(errors: int, count: int) -> float | None:
    if count <= 0:
        return None
    return errors * 100.0 / count


def _percent(used: Decimal | int, limit: Decimal | int | None) -> float | None:
    if limit is None:
        return None
    limit_dec = Decimal(str(limit))
    used_dec = used if isinstance(used, Decimal) else Decimal(used)
    if limit_dec <= 0:
        return 100.0 if used_dec > 0 else 0.0
    return float((used_dec / limit_dec) * Decimal(100))


def _midnight(day: date) -> datetime:
    naive = datetime.combine(day, time.min)
    if settings.USE_TZ:
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def _period_start(now: datetime, period: PeriodName) -> datetime:
    """Начало календарных суток или месяца для now. Совпадает с models._period_start."""
    local = timezone.localtime(now) if timezone.is_aware(now) else now
    if period == "day":
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if timezone.is_aware(now) and timezone.is_naive(start):
        return timezone.make_aware(start, timezone.get_current_timezone())
    return start


def _month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_pk(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _query(
    filters: DashboardFilters,
    *,
    period: str,
    start: date,
    end: date,
) -> str:
    params: dict[str, str] = {
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    if filters.profile_id is not None:
        params["profile"] = str(filters.profile_id)
    if filters.model_id is not None:
        params["model"] = str(filters.model_id)
    return urlencode(params)
