from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Max, QuerySet, Sum
from django.db.models.expressions import OrderBy
from django.db.models.functions import Coalesce
from django.forms import BaseInlineFormSet, ModelForm, PasswordInput
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_openrouter.exceptions import ConfigurationError, OpenRouterError
from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    ProfileUsageTotals,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
    usage_totals_by_profile,
)
from django_openrouter.parameter_size import display_parameter_label
from django_openrouter.sync import ensure_catalog_fresh, sync_openrouter_models

_MILLION = Decimal("1000000")
_NULL_LAST_FIELDS = frozenset(
    {"latency_ms", "throughput", "prompt_price", "completion_price", "parameter_count"}
)
_CHEAP_PROMPT = Decimal("0.000001")  # < $1 / 1M
_MID_PROMPT = Decimal("0.00001")  # < $10 / 1M
_FAST_MS = 400.0
_SLOW_MS = 1200.0


def format_model_choice_label(obj: OpenRouterModel) -> str:
    """Подпись в autocomplete: имя, размер, цена за 1M, latency, throughput."""
    price = (
        f"{_format_per_million(obj.prompt_price)} / {_format_per_million(obj.completion_price)}"
    )
    latency = f"{obj.latency_ms:.0f} ms" if obj.latency_ms is not None else "—"
    throughput = f"{obj.throughput:.0f} tok/s" if obj.throughput is not None else "—"
    name = obj.name or obj.model_id
    size = (
        display_parameter_label(
            stored_label=obj.parameter_label,
            model_id=obj.model_id,
            name=obj.name,
        )
        or "—"
    )
    return f"{name} · {size} · {price} · {latency} · {throughput}"


def apply_price_filter(qs: QuerySet[OpenRouterModel], value: str) -> QuerySet[OpenRouterModel]:
    """Фильтр каталога по prompt-цене за 1M токенов."""
    if value == "free":
        return qs.filter(prompt_price=0)
    if value == "cheap":
        return qs.filter(prompt_price__gt=0, prompt_price__lt=_CHEAP_PROMPT)
    if value == "mid":
        return qs.filter(prompt_price__gte=_CHEAP_PROMPT, prompt_price__lt=_MID_PROMPT)
    if value == "expensive":
        return qs.filter(prompt_price__gte=_MID_PROMPT)
    return qs


def apply_speed_filter(qs: QuerySet[OpenRouterModel], value: str) -> QuerySet[OpenRouterModel]:
    """Фильтр каталога по p50 latency (меньше = быстрее)."""
    if value == "fast":
        return qs.filter(latency_ms__lt=_FAST_MS)
    if value == "medium":
        return qs.filter(latency_ms__gte=_FAST_MS, latency_ms__lt=_SLOW_MS)
    if value == "slow":
        return qs.filter(latency_ms__gte=_SLOW_MS)
    if value == "unknown":
        return qs.filter(latency_ms__isnull=True)
    return qs


class PriceBucketFilter(SimpleListFilter):
    title = _("Price")
    parameter_name = "price"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> list[tuple[str, str]]:
        return [
            ("free", str(_("Free"))),
            ("cheap", str(_("Cheap (< $1 / 1M)"))),
            ("mid", str(_("Mid ($1-$10 / 1M)"))),
            ("expensive", str(_("Expensive (>= $10 / 1M)"))),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[OpenRouterModel]
    ) -> QuerySet[OpenRouterModel]:
        return apply_price_filter(queryset, self.value() or "")


class SpeedBucketFilter(SimpleListFilter):
    title = _("Speed")
    parameter_name = "speed"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> list[tuple[str, str]]:
        return [
            ("fast", str(_("Fast (< 400 ms)"))),
            ("medium", str(_("Medium (400-1200 ms)"))),
            ("slow", str(_("Slow (>= 1200 ms)"))),
            ("unknown", str(_("Unknown latency"))),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[OpenRouterModel]
    ) -> QuerySet[OpenRouterModel]:
        return apply_speed_filter(queryset, self.value() or "")


class OpenRouterAutocompleteJsonView(AutocompleteJsonView):
    """Autocomplete каталога: цена/скорость в подписи и те же GET-фильтры, что в changelist."""

    def serialize_result(self, obj: object, to_field_name: str) -> dict[str, str]:
        text = format_model_choice_label(obj) if isinstance(obj, OpenRouterModel) else str(obj)
        return {"id": str(getattr(obj, to_field_name)), "text": text}

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        if getattr(self.model_admin, "model", None) is OpenRouterModel:
            qs = apply_price_filter(qs, str(self.request.GET.get("price") or ""))
            qs = apply_speed_filter(qs, str(self.request.GET.get("speed") or ""))
        return qs


class OpenRouterSettingsForm(ModelForm):
    """API-ключ write-only: после сохранения его нельзя увидеть в админке."""

    api_key = forms.CharField(
        label=_("API key"),
        required=False,
        strip=True,
        widget=PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password"},
        ),
    )
    clear_api_key = forms.BooleanField(
        label=_("Clear stored API key"),
        required=False,
    )

    class Meta:
        model = OpenRouterSettings
        fields = (
            "api_key",
            "base_url",
            "default_profile",
            "request_timeout",
            "max_retries",
            "streaming_enabled",
            "max_parallel_requests",
            "enabled",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Никогда не подставляем расшифрованный ключ в виджет.
        self.initial["api_key"] = ""
        self.fields["api_key"].initial = ""
        stored = bool(self.instance.pk and self.instance.api_key)
        if stored:
            self.fields["api_key"].help_text = _(
                "A key is stored encrypted. Leave blank to keep it, or enter a new "
                "key to replace it. The stored value cannot be viewed."
            )
        else:
            self.fields["api_key"].help_text = _(
                "Entered once, stored encrypted, and cannot be viewed again. "
                "Leave empty to use OPENROUTER_API_KEY / settings.OPENROUTER['API_KEY']."
            )
        if not stored:
            self.fields["clear_api_key"].disabled = True

    def save(self, commit: bool = True) -> OpenRouterSettings:
        instance: OpenRouterSettings = super().save(commit=False)
        raw_key = self.cleaned_data.get("api_key") or ""
        if raw_key:
            instance.api_key = raw_key
        elif self.cleaned_data.get("clear_api_key"):
            instance.api_key = ""
        elif instance.pk:
            instance.api_key = OpenRouterSettings.objects.get(pk=instance.pk).api_key
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(OpenRouterSettings)
class OpenRouterSettingsAdmin(admin.ModelAdmin):
    form = OpenRouterSettingsForm
    readonly_fields = ("api_key_status",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "enabled",
                    "api_key_status",
                    "api_key",
                    "clear_api_key",
                    "base_url",
                    "default_profile",
                    "request_timeout",
                    "max_retries",
                    "streaming_enabled",
                    "max_parallel_requests",
                )
            },
        ),
    )

    @admin.display(description=_("API key status"))
    def api_key_status(self, obj: OpenRouterSettings | None) -> str:
        if obj is not None and obj.pk and obj.api_key:
            return str(_("Stored (encrypted, not visible)"))
        return str(_("Not set"))

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        obj = OpenRouterSettings.load()
        return redirect(
            reverse("admin:django_openrouter_openroutersettings_change", args=[obj.pk])
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not OpenRouterSettings.objects.exists()

    def has_delete_permission(
        self, request: HttpRequest, obj: OpenRouterSettings | None = None
    ) -> bool:
        return False


class UsageProfileFallbackForm(ModelForm):
    class Meta:
        model = UsageProfileFallback
        fields = ("model", "order")

    def clean(self) -> dict[str, object]:
        cleaned = super().clean() or {}
        model = cleaned.get("model")
        if model is not None and not model.is_active:
            self.add_error("model", _("Fallback model must be active."))
        return cleaned


class UsageProfileFallbackInlineFormSet(BaseInlineFormSet):
    def clean(self) -> None:
        super().clean()
        only_free = bool(self.instance.only_free_models)
        kept: list[tuple[int, int, ModelForm]] = []
        seen: set[int] = set()
        for index, form in enumerate(self.forms):
            if form.errors:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            model = form.cleaned_data.get("model")
            if model is None:
                continue
            if not model.is_active:
                raise ValidationError(_("Models in the chain must be active."))
            if only_free and not model.is_free:
                raise ValidationError(_("only_free_models allows only free models."))
            if model.pk in seen:
                raise ValidationError(_("Each model may appear only once."))
            seen.add(model.pk)
            order_val = form.cleaned_data.get("order")
            order_num = int(order_val) if order_val is not None else index
            kept.append((order_num, index, form))
        kept.sort(key=lambda item: (item[0], item[1]))
        for new_order, (_old, _index, form) in enumerate(kept):
            form.cleaned_data["order"] = new_order
            form.instance.order = new_order


class UsageProfileFallbackInline(admin.TabularInline):
    model = UsageProfileFallback
    form = UsageProfileFallbackForm
    formset = UsageProfileFallbackInlineFormSet
    extra = 1
    min_num = 0
    validate_min = False
    ordering = ("order",)
    autocomplete_fields = ("model",)
    verbose_name = _("Model")
    verbose_name_plural = _("Models (priority order)")
    fields = ("order", "model")

    def formfield_for_foreignkey(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        if db_field.name == "model":
            kwargs["queryset"] = OpenRouterModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class UsageProfileForm(ModelForm):
    class Meta:
        model = UsageProfile
        fields = (
            "name",
            "max_tokens",
            "temperature",
            "max_requests_per_day",
            "max_requests_per_month",
            "budget_usd_per_day",
            "budget_usd_per_month",
            "only_free_models",
            "is_active",
        )


class AssignToProfileForm(forms.Form):
    """Промежуточная форма экшена «присвоить выбранные модели профилю»."""

    profile = forms.ModelChoiceField(
        queryset=UsageProfile.objects.all(),
        label=_("Usage profile"),
    )


class UsageProfileChangeList(ChangeList):
    """После пагинации — один GROUP BY логов только по PK текущей страницы."""

    def get_results(self, request: HttpRequest) -> None:
        super().get_results(request)
        ids = [obj.pk for obj in self.result_list]
        stats = usage_totals_by_profile(ids)
        for obj in self.result_list:
            obj.__dict__["_usage_totals"] = stats.get(obj.pk)


def _totals_of(obj: UsageProfile) -> ProfileUsageTotals | None:
    stored = obj.__dict__.get("_usage_totals")
    if isinstance(stored, ProfileUsageTotals):
        return stored
    return None


def _format_duration_ms(ms: float) -> str:
    total = round(ms)
    if total < 1000:
        return f"{total} ms"
    seconds = total / 1000.0
    if seconds < 60:
        text = f"{seconds:.1f}".rstrip("0").rstrip(".")
        return f"{text} s"
    minutes, sec = divmod(round(seconds), 60)
    return f"{minutes}m {sec:02d}s"


def _format_usd(amount: Decimal) -> str:
    text = format(amount, "f").rstrip("0").rstrip(".")
    if not text:
        text = "0"
    return f"${text}"


@admin.register(UsageProfile)
class UsageProfileAdmin(admin.ModelAdmin):
    form = UsageProfileForm
    inlines = (UsageProfileFallbackInline,)
    empty_value_display = "—"
    list_display = (
        "name",
        "model",
        "is_active",
        "only_free_models",
        "max_requests_per_day",
        "budget_usd_per_day",
        "request_count_display",
        "avg_latency_display",
        "total_latency_display",
        "avg_cost_display",
        "total_cost_display",
    )
    list_filter = ("is_active", "only_free_models")
    search_fields = ("name",)

    class Media:
        js = ("django_openrouter/js/model_choice_filters.js",)
        css = {"all": ("django_openrouter/css/model_choice_filters.css",)}

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> type[ChangeList]:
        return UsageProfileChangeList

    def save_related(
        self,
        request: HttpRequest,
        form: ModelForm,
        formsets: Any,
        change: bool,
    ) -> None:
        super().save_related(request, form, formsets, change)
        form.instance.sync_primary_from_chain()

    @admin.display(description=_("Requests"))
    def request_count_display(self, obj: UsageProfile) -> str:
        totals = _totals_of(obj)
        if totals is None:
            return str(self.get_empty_value_display())
        return str(totals.request_count)

    @admin.display(description=_("Avg latency"))
    def avg_latency_display(self, obj: UsageProfile) -> str:
        totals = _totals_of(obj)
        if totals is None:
            return str(self.get_empty_value_display())
        return _format_duration_ms(totals.avg_latency_ms)

    @admin.display(description=_("Total time"))
    def total_latency_display(self, obj: UsageProfile) -> str:
        totals = _totals_of(obj)
        if totals is None:
            return str(self.get_empty_value_display())
        return _format_duration_ms(float(totals.total_latency_ms))

    @admin.display(description=_("Avg cost"))
    def avg_cost_display(self, obj: UsageProfile) -> str:
        totals = _totals_of(obj)
        if totals is None:
            return str(self.get_empty_value_display())
        return _format_usd(totals.avg_cost_usd)

    @admin.display(description=_("Total cost"))
    def total_cost_display(self, obj: UsageProfile) -> str:
        totals = _totals_of(obj)
        if totals is None:
            return str(self.get_empty_value_display())
        return _format_usd(totals.total_cost_usd)


class OpenRouterModelChangeList(ChangeList):
    """Сортировка latency/throughput/цены с NULL в конце."""

    def get_ordering(self, request: HttpRequest, queryset: QuerySet[OpenRouterModel]) -> list[Any]:
        ordering = super().get_ordering(request, queryset)
        rewritten: list[Any] = []
        for item in ordering:
            if isinstance(item, OrderBy):
                rewritten.append(item)
                continue
            if not isinstance(item, str):
                rewritten.append(item)
                continue
            descending = item.startswith("-")
            field_name = item[1:] if descending else item
            if field_name in _NULL_LAST_FIELDS:
                expr = F(field_name)
                rewritten.append(
                    expr.desc(nulls_last=True) if descending else expr.asc(nulls_last=True)
                )
            else:
                rewritten.append(item)
        return rewritten


@admin.register(OpenRouterModel)
class OpenRouterModelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "latency_ms",
        "throughput",
        "price_display",
        "parameter_size_display",
        "is_active",
    )
    list_display_links = ("name",)
    list_filter = ("is_active", "modality", PriceBucketFilter, SpeedBucketFilter)
    search_fields = ("model_id", "name")
    actions = ("sync_with_openrouter", "assign_to_profile")
    readonly_fields = (
        "last_synced_at",
        "prompt_price",
        "completion_price",
        "latency_ms",
        "throughput",
        "parameter_count",
        "parameter_label",
    )
    empty_value_display = "—"
    ordering = ("name",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: OpenRouterModel | None = None
    ) -> bool:
        # Changelist/actions (sync) — да; карточка модели — только просмотр.
        return obj is None

    def has_delete_permission(
        self, request: HttpRequest, obj: OpenRouterModel | None = None
    ) -> bool:
        return False

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> type[ChangeList]:
        return OpenRouterModelChangeList

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        if request.method == "GET":
            try:
                ensure_catalog_fresh()
            except (ConfigurationError, OpenRouterError, OSError, httpx.HTTPError) as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description=_("Price"), ordering="prompt_price")
    def price_display(self, obj: OpenRouterModel) -> str:
        """Цена prompt/completion за 1M токенов."""
        prompt = _format_per_million(obj.prompt_price)
        completion = _format_per_million(obj.completion_price)
        return f"{prompt} / {completion}"

    @admin.display(description=_("Params"), ordering="parameter_count")
    def parameter_size_display(self, obj: OpenRouterModel) -> str:
        """Размер весов: 70B / 340M / 8×7B, не число API-параметров."""
        label = display_parameter_label(
            stored_label=obj.parameter_label,
            model_id=obj.model_id,
            name=obj.name,
        )
        if label is None:
            return str(self.get_empty_value_display())
        return label

    @admin.action(description=_("Sync catalog with OpenRouter"))
    def sync_with_openrouter(
        self,
        request: HttpRequest,
        queryset: QuerySet[OpenRouterModel],
    ) -> None:
        try:
            summary = sync_openrouter_models(enrich_stats=True)
        except (ConfigurationError, OpenRouterError, OSError, httpx.HTTPError) as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        self.message_user(
            request,
            _(
                "Sync complete: %(created)s created, %(updated)s updated, "
                "%(deactivated)s deactivated (%(total)s remote)."
            )
            % {
                "created": summary.created,
                "updated": summary.updated,
                "deactivated": summary.deactivated,
                "total": summary.total_remote,
            },
        )

    @admin.action(description=_("Assign to usage profile…"))
    def assign_to_profile(
        self,
        request: HttpRequest,
        queryset: QuerySet[OpenRouterModel],
    ) -> HttpResponse | None:
        """Присваивает выбранные модели цепочке профиля (в конец, order = max+1)."""
        if request.method == "POST" and "apply" in request.POST:
            form = AssignToProfileForm(request.POST)
            if form.is_valid():
                profile = form.cleaned_data["profile"]
                added, skipped = self._attach_to_profile(profile, queryset)
                if added:
                    profile.sync_primary_from_chain()
                self._report_assign(request, profile, added, skipped)
                return redirect("admin:django_openrouter_openroutermodel_changelist")
        else:
            form = AssignToProfileForm()
        context = {
            **self.admin_site.each_context(request),
            "title": _("Assign models to usage profile"),
            "models": queryset,
            "form": form,
        }
        return render(
            request,
            "admin/django_openrouter/openroutermodel/assign_to_profile.html",
            context,
        )

    def _attach_to_profile(
        self,
        profile: UsageProfile,
        queryset: QuerySet[OpenRouterModel],
    ) -> tuple[list[OpenRouterModel], dict[str, list[OpenRouterModel]]]:
        """Добавляет модели в цепочку профиля; вернуть (добавленные, {причина: пропущенные})."""
        links = profile.fallback_links
        existing = set(links.values_list("model_id", flat=True))
        next_order = int(links.aggregate(max_order=Max("order"))["max_order"] or 0)
        added: list[OpenRouterModel] = []
        skipped: dict[str, list[OpenRouterModel]] = {
            "duplicates": [],
            "inactive": [],
            "not_free": [],
        }
        for model in queryset.order_by("model_id"):
            if model.pk in existing:
                skipped["duplicates"].append(model)
                continue
            if not model.is_active:
                skipped["inactive"].append(model)
                continue
            if profile.only_free_models and not model.is_free:
                skipped["not_free"].append(model)
                continue
            next_order += 1
            UsageProfileFallback.objects.create(
                profile=profile,
                model=model,
                order=next_order,
            )
            existing.add(model.pk)
            added.append(model)
        return added, skipped

    def _report_assign(
        self,
        request: HttpRequest,
        profile: UsageProfile,
        added: list[OpenRouterModel],
        skipped: dict[str, list[OpenRouterModel]],
    ) -> None:
        reasons = [
            (_("%(count)s already in the chain"), "duplicates"),
            (_("%(count)s inactive"), "inactive"),
            (_("%(count)s not free (only_free_models)"), "not_free"),
        ]
        skipped_parts = [
            template % {"count": len(skipped[key])} for template, key in reasons if skipped[key]
        ]
        if added:
            text = _("Added %(count)s model(s) to profile “%(profile)s”.") % {
                "count": len(added),
                "profile": profile.name,
            }
            level = messages.SUCCESS
        else:
            text = _("No models were added to profile “%(profile)s”.") % {"profile": profile.name}
            level = messages.WARNING
        if skipped_parts:
            text += " " + _("Skipped: %(reasons)s.") % {"reasons": ", ".join(skipped_parts)}
            if level == messages.SUCCESS:
                level = messages.WARNING
        self.message_user(request, text, level=level)


def _format_per_million(price: Decimal | None) -> str:
    if price is None:
        return "—"
    per_million = price * _MILLION
    text = format(per_million, "f").rstrip("0").rstrip(".")
    return f"${text}"


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    change_list_template = "admin/django_openrouter/requestlog/change_list.html"
    list_display = (
        "created_at",
        "username",
        "profile",
        "model",
        "status_code",
        "prompt_tokens",
        "completion_tokens",
        "cost_usd",
        "latency_ms",
    )
    list_filter = ("profile", "status_code", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("error_message", "username")
    ordering = ("-created_at",)
    readonly_fields = (
        "profile",
        "model",
        "username",
        "status_code",
        "error_message",
        "prompt_tokens",
        "completion_tokens",
        "cost_usd",
        "latency_ms",
        "created_at",
    )

    def has_view_permission(self, request: HttpRequest, obj: RequestLog | None = None) -> bool:
        user = request.user
        if not user.is_staff:
            return False
        return bool(user.is_superuser or user.has_perm("django_openrouter.view_usage_logs"))

    def has_module_permission(self, request: HttpRequest) -> bool:
        return self.has_view_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: RequestLog | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: RequestLog | None = None) -> bool:
        return False

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        if not self.has_view_permission(request):
            raise PermissionDenied
        extra_context = extra_context or {}
        response = super().changelist_view(request, extra_context=extra_context)
        if not hasattr(response, "context_data") or response.context_data is None:
            return response
        cl = response.context_data.get("cl")
        if cl is None:
            return response
        summary = cl.queryset.aggregate(
            request_count=Count("id"),
            total_cost=Coalesce(Sum("cost_usd"), Decimal("0.00")),
        )
        response.context_data["summary"] = summary
        return response
