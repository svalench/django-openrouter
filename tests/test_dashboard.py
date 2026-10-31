from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import ModuleType

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test.utils import CaptureQueriesContext, override_settings
from django.urls import clear_url_caches, reverse
from django.utils import timezone

from django_openrouter.admin import RequestLogAdmin
from django_openrouter.dashboard import (
    DashboardFilters,
    build_dashboard,
    chart_sections,
    parse_filters,
    percentile,
    preset_links,
)
from django_openrouter.models import OpenRouterModel, RequestLog, UsageProfile

pytestmark = pytest.mark.django_db

_DAY = date(2024, 6, 15)


def _day(**kwargs: object) -> DashboardFilters:
    payload: dict[str, object] = {
        "period": "day",
        "start": _DAY,
        "end": _DAY,
        "profile_id": None,
        "model_id": None,
        "clamped": False,
    }
    payload.update(kwargs)
    return DashboardFilters(**payload)  # type: ignore[arg-type]


def _at(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2024, 6, day, hour, minute, tzinfo=UTC)


def _log(
    profile: UsageProfile | None,
    model: OpenRouterModel | None,
    *,
    status: int,
    cost: str = "0",
    latency: int = 0,
    prompt: int = 1,
    completion: int = 1,
    when: datetime | None = None,
) -> RequestLog:
    # auto_now_add перезаписывает created_at в pre_save, поэтому штамп ставится update().
    stamp = when or _at(1)
    row = RequestLog.objects.create(
        profile=profile,
        model=model,
        status_code=status,
        cost_usd=Decimal(cost),
        latency_ms=latency,
        prompt_tokens=prompt,
        completion_tokens=completion,
    )
    RequestLog.objects.filter(pk=row.pk).update(created_at=stamp)
    row.created_at = stamp
    return row


def test_percentile_interpolates() -> None:
    assert percentile([], 95) is None
    assert percentile([5], 95) == 5
    assert percentile(list(range(1, 101)), 95) == pytest.approx(95.05)


def test_parse_filters_defaults_swap_and_clamp() -> None:
    today = date(2024, 6, 15)
    filters = parse_filters({}, today=today)
    assert filters.period == "day"
    assert filters.start == today == filters.end
    assert filters.clamped is False

    month = parse_filters({"period": "month"}, today=today)
    assert month.start == date(2024, 6, 1)
    assert month.end == date(2024, 6, 30)

    swapped = parse_filters({"start": "2024-06-12", "end": "2024-06-10"}, today=today)
    assert (swapped.start, swapped.end) == (date(2024, 6, 10), date(2024, 6, 12))
    assert swapped.clamped is False

    clamped = parse_filters(
        {"period": "day", "start": "2024-01-01", "end": "2024-03-01"},
        today=today,
    )
    assert clamped.clamped is True
    assert clamped.end == date(2024, 1, 7)

    long_month = parse_filters(
        {"period": "month", "start": "2020-01-01", "end": "2024-01-01"},
        today=today,
    )
    assert long_month.clamped is True
    assert long_month.end == date(2020, 12, 31)

    junk = parse_filters(
        {"period": "year", "start": "nope", "profile": "x", "model": "0"},
        today=today,
    )
    assert junk.period == "day"
    assert junk.start == today
    assert junk.profile_id is None
    assert junk.model_id is None

    kept = parse_filters({"profile": "4", "model": "8"}, today=today)
    assert kept.profile_id == 4
    assert kept.model_id == 8


def test_preset_links_keep_profile_and_model() -> None:
    filters = _day(profile_id=5, model_id=9)
    links = preset_links(filters, today=_DAY)
    assert "period=day" in links["today"]
    assert "start=2024-06-15" in links["today"]
    assert "profile=5" in links["today"]
    assert "model=9" in links["today"]
    assert "period=month" in links["month"]
    assert "start=2024-06-01" in links["month"]
    assert "end=2024-06-30" in links["month"]


def test_hourly_cost_errors_latency_and_tokens(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    _log(
        profile,
        paid_model,
        status=200,
        cost="1.00",
        latency=10,
        prompt=2,
        completion=3,
        when=_at(1, 15),
    )
    _log(
        profile,
        paid_model,
        status=204,
        cost="0.50",
        latency=20,
        prompt=1,
        completion=1,
        when=_at(1, 45),
    )
    _log(profile, paid_model, status=402, cost="0.10", latency=30, when=_at(1, 50))
    _log(profile, paid_model, status=429, cost="0", latency=40, when=_at(1, 55))
    _log(
        profile,
        paid_model,
        status=499,
        cost="0.20",
        latency=100,
        prompt=4,
        completion=6,
        when=_at(2, 0),
    )
    _log(profile, paid_model, status=500, cost="0.05", latency=50, when=_at(2, 5))
    _log(profile, paid_model, status=0, cost="0.01", latency=5, when=_at(2, 10))
    _log(profile, paid_model, status=200, cost="9", when=_at(0, day=16))

    data = build_dashboard(_day())
    assert data.request_count == 7
    assert data.error_count == 5
    assert data.error_rate == pytest.approx(5 / 7 * 100)
    assert data.cost_usd == Decimal("1.86")
    assert data.total_tokens == 25
    assert data.avg_tokens == pytest.approx(25 / 7)
    assert len(data.buckets) == 24
    by_label = {point.label: point for point in data.buckets}
    assert by_label["01:00"].request_count == 4
    assert by_label["01:00"].error_count == 2
    assert by_label["01:00"].cost_usd == Decimal("1.60")
    assert by_label["01:00"].total_tokens == 11
    assert by_label["02:00"].request_count == 3
    assert by_label["02:00"].error_count == 3
    assert by_label["02:00"].cost_usd == Decimal("0.26")
    assert by_label["03:00"].request_count == 0
    assert by_label["03:00"].error_rate is None
    latencies = [10, 20, 30, 40, 100, 50, 5]
    assert data.p95_latency_ms == pytest.approx(percentile(latencies, 95))
    assert data.p95_approximate is False
    assert data.by_profile[0].label == "chat"
    assert data.by_profile[0].p95_latency_ms == pytest.approx(percentile(latencies, 95))


def test_daily_buckets_profile_and_model_filters(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    other_profile = UsageProfile.objects.create(name="translation", model=paid_model)
    other_model = OpenRouterModel.objects.create(model_id="openai/other", name="Other model")
    paid_model.name = "<img src=x>"
    paid_model.save(update_fields=["name"])
    _log(profile, paid_model, status=200, cost="0.110000", latency=10, when=_at(12, day=1))
    _log(profile, other_model, status=500, cost="0.990000", latency=80, when=_at(12, day=2))
    _log(other_profile, paid_model, status=200, cost="5", latency=15, when=_at(15, day=2))

    window = DashboardFilters(
        period="month",
        start=date(2024, 6, 1),
        end=date(2024, 6, 30),
        profile_id=None,
        model_id=None,
        clamped=False,
    )
    data = build_dashboard(window)
    assert data.request_count == 3
    assert len(data.buckets) == 30
    assert data.buckets[0].label == "2024-06-01"
    assert data.buckets[0].request_count == 1
    assert data.buckets[1].request_count == 2
    assert data.top_profiles[0].label == "translation"
    assert data.top_models[0].label == "<img src=x>"
    assert data.top_models[1].label == "Other model"
    assert [row.label for row in data.top_models] == ["<img src=x>", "Other model"]

    only_profile = build_dashboard(
        _day(period="month", start=date(2024, 6, 1), end=date(2024, 6, 30), profile_id=profile.pk)
    )
    assert only_profile.request_count == 2
    assert only_profile.cost_usd == Decimal("1.100000")
    assert only_profile.error_count == 1

    only_model = build_dashboard(
        _day(
            period="month",
            start=date(2024, 6, 1),
            end=date(2024, 6, 30),
            model_id=paid_model.pk,
        )
    )
    assert only_model.request_count == 2
    assert only_model.cost_usd == Decimal("5.110000")

    one_day = build_dashboard(_day(period="month", start=date(2024, 6, 1), end=date(2024, 6, 1)))
    svg = "".join(chart.svg for section in chart_sections(one_day) for chart in section.charts)
    assert "<circle" in svg
    assert "&lt;img src=x&gt;" in svg
    assert "<img src=x>" not in svg


def test_p95_uses_bounded_recent_sample(
    monkeypatch: pytest.MonkeyPatch, profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    monkeypatch.setattr("django_openrouter.dashboard.P95_ROW_CAP", 2)
    base = _at(12)
    for offset, latency in enumerate((10, 20, 30, 40)):
        _log(
            profile,
            paid_model,
            status=200,
            latency=latency,
            prompt=offset,
            completion=0,
            when=base + timedelta(minutes=offset),
        )
    data = build_dashboard(_day())
    assert data.p95_approximate is True
    assert data.p95_sample_size == 2
    assert data.p95_latency_ms == pytest.approx(percentile([30, 40], 95))
    assert data.p95_tokens == pytest.approx(percentile([2, 3], 95))
    assert data.avg_latency_ms == pytest.approx((10 + 20 + 30 + 40) / 4)
    assert data.request_count == 4


def test_extra_groups_collapse_to_other(
    monkeypatch: pytest.MonkeyPatch, paid_model: OpenRouterModel
) -> None:
    monkeypatch.setattr("django_openrouter.dashboard.MAX_SERIES", 2)
    for index in range(3):
        profile = UsageProfile.objects.create(name=f"p{index}", model=paid_model)
        _log(profile, paid_model, status=200, cost=str(index + 1), when=_at(3))
    data = build_dashboard(_day())
    labels = [series.label for series in data.profile_cost_series]
    assert labels == ["p2", "Other"]
    assert data.has_other is True
    other = data.profile_cost_series[1].values
    assert sum(value or 0 for value in other) == pytest.approx(1 + 2)


def test_budgets_follow_enforcement_rules(
    profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    profile.budget_usd_per_day = Decimal("1")
    profile.budget_usd_per_month = Decimal("10")
    profile.max_requests_per_day = 4
    profile.max_requests_per_month = 40
    profile.save()
    now = timezone.now()
    _log(profile, paid_model, status=200, cost="0.25", when=now)
    _log(profile, paid_model, status=500, cost="0.10", when=now)
    _log(profile, paid_model, status=499, cost="0.05", when=now)
    local = timezone.localtime(now)
    month_start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    _log(profile, paid_model, status=200, cost="9", when=month_start - timedelta(days=1))

    data = build_dashboard(_day(), now=now)
    day_stats, month_stats = profile.usage_summary()
    row = data.budgets[0]
    assert row.name == "chat"
    assert row.day_requests == day_stats.request_count == 2
    assert row.month_requests == month_stats.request_count == 2
    assert row.day_cost == day_stats.total_cost == Decimal("0.40")
    assert row.month_cost == month_stats.total_cost == Decimal("0.40")
    assert row.day_request_pct == pytest.approx(50)
    assert row.day_cost_pct == pytest.approx(40)
    assert row.month_request_pct == pytest.approx(5)
    assert row.month_cost_pct == pytest.approx(4)

    other = OpenRouterModel.objects.create(model_id="openai/budget", name="Budget model")
    _log(profile, other, status=200, cost="0.25", when=now)
    filtered = build_dashboard(_day(model_id=paid_model.pk), now=timezone.now())
    assert filtered.budgets[0].day_cost == profile.usage_summary()[0].total_cost
    assert filtered.budgets[0].day_cost == Decimal("0.65")


def test_empty_range_and_query_bound(profile: UsageProfile, paid_model: OpenRouterModel) -> None:
    _log(profile, paid_model, status=200, cost="0.2", when=_at(4))
    with CaptureQueriesContext(connection) as ctx:
        data = build_dashboard(_day())
    assert len(ctx.captured_queries) <= 8
    assert data.request_count == 1
    empty = build_dashboard(_day(start=date(2020, 1, 1), end=date(2020, 1, 1)))
    assert empty.request_count == 0
    assert empty.cost_usd == Decimal("0")
    assert empty.p95_latency_ms is None
    assert empty.budgets[0].name == "chat"
    assert empty.budgets[0].day_budget is None
    sections = chart_sections(empty)
    assert "No requests in this range." in sections[0].charts[2].svg
    assert "<svg" in sections[1].charts[3].svg


def test_model_created_index_declared() -> None:
    indexes = {index.name: list(index.fields) for index in RequestLog._meta.indexes}
    assert indexes["or_log_model_created"] == ["model", "created_at"]
    assert indexes["or_log_profile_created"] == ["profile", "created_at"]


def test_dashboard_urls_are_registered_before_object_path() -> None:
    site = AdminSite(name="custom_or_urls")
    model_admin = RequestLogAdmin(RequestLog, site)
    urls = model_admin.get_urls()
    assert urls[0].name == "django_openrouter_requestlog_dashboard"


def test_dashboard_access_control(client, admin_client) -> None:
    url = reverse("admin:django_openrouter_requestlog_dashboard")
    anonymous = client.get(url)
    assert anonymous.status_code == 302
    assert "/admin/login/" in anonymous["Location"]

    outsider = User.objects.create_user("outsider", password="x")
    perm = Permission.objects.get(
        codename="view_usage_logs",
        content_type__app_label="django_openrouter",
    )
    outsider.user_permissions.add(perm)
    client.force_login(outsider)
    assert client.get(url).status_code == 302

    staff = User.objects.create_user("dash-staff", password="x", is_staff=True)
    client.force_login(staff)
    assert client.get(url).status_code == 403

    staff.user_permissions.add(perm)
    client.force_login(staff)
    allowed = client.get(url)
    assert allowed.status_code == 200
    assert b"No requests in this range." in allowed.content
    assert b"No usage profiles." in allowed.content
    assert b"django_openrouter/js/dashboard.js" in allowed.content
    assert b"django_openrouter/css/dashboard.css" in allowed.content

    assert admin_client.get(url).status_code == 200


def test_dashboard_renders_filters_and_charts(
    admin_client, profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    _log(profile, paid_model, status=402, cost="0.110000", latency=12, when=_at(8))
    other = UsageProfile.objects.create(name="other", model=paid_model)
    _log(other, paid_model, status=200, cost="0.990000", latency=40, when=_at(9))
    url = reverse("admin:django_openrouter_requestlog_dashboard")
    response = admin_client.get(
        url,
        {"period": "day", "start": "2024-06-15", "end": "2024-06-15", "profile": str(profile.pk)},
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert response.context["page"]["cost"] == "$0.110000"
    assert "$0.990000" not in body
    assert "<svg" in body
    assert "chat" in body
    assert 'src="' in body and "dashboard.js" in body
    assert "or-chart" in body
    assert "dashboard.js" in body


def test_empty_logs_keep_budget_row(admin_client, profile: UsageProfile) -> None:
    profile.budget_usd_per_day = Decimal("2")
    profile.save(update_fields=["budget_usd_per_day"])
    url = reverse("admin:django_openrouter_requestlog_dashboard")
    response = admin_client.get(url, {"start": "2020-01-01", "end": "2020-01-01", "period": "day"})
    body = response.content.decode()
    assert response.status_code == 200
    assert "No requests in this range." in body
    assert "chat" in body
    assert "$2.000000" in body
    assert "unlimited" in body
    assert "or-chart" not in body


def test_changelist_and_index_link_dashboard(admin_client, client) -> None:
    dashboard = reverse("admin:django_openrouter_requestlog_dashboard")
    changelist = reverse("admin:django_openrouter_requestlog_changelist")
    index = reverse("admin:index")
    assert dashboard in admin_client.get(changelist).content.decode()
    assert "Usage dashboard" in admin_client.get(index).content.decode()
    assert dashboard in admin_client.get(index).content.decode()

    staff = User.objects.create_user("index-staff", password="x", is_staff=True)
    client.force_login(staff)
    hidden = client.get(index)
    assert hidden.status_code == 200
    assert dashboard not in hidden.content.decode()

    perm = Permission.objects.get(
        codename="view_usage_logs",
        content_type__app_label="django_openrouter",
    )
    staff.user_permissions.add(perm)
    client.force_login(staff)
    visible = client.get(index)
    assert dashboard in visible.content.decode()


def test_custom_admin_site_index_links_dashboard(rf) -> None:
    site = AdminSite(name="custom_or")
    site.register(RequestLog, RequestLogAdmin)
    module = ModuleType("custom_or_urls")
    from django.urls import path

    module.urlpatterns = [path("custom-admin/", site.urls)]  # type: ignore[attr-defined]
    sys.modules["custom_or_urls"] = module
    request = rf.get("/custom-admin/")
    request.user = User.objects.create_superuser("dashroot", "dash@example.com", "secret")
    try:
        with override_settings(ROOT_URLCONF="custom_or_urls"):
            clear_url_caches()
            app_list = site.get_app_list(request)
    finally:
        sys.modules.pop("custom_or_urls", None)
        clear_url_caches()
    models = [
        model
        for app in app_list
        if app["app_label"] == "django_openrouter"
        for model in app["models"]
    ]
    dashboard = next(model for model in models if model["object_name"] == "UsageDashboard")
    assert dashboard["view_only"] is True
    assert dashboard["admin_url"].endswith("/requestlog/dashboard/")
    assert models[-1]["object_name"] == "UsageDashboard"
