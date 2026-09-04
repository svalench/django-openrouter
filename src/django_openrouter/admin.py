from __future__ import annotations

from decimal import Decimal

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.forms import BaseInlineFormSet, ModelForm, PasswordInput
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_openrouter.exceptions import ConfigurationError, OpenRouterError
from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)
from django_openrouter.sync import sync_openrouter_models


class OpenRouterSettingsForm(ModelForm):
    class Meta:
        model = OpenRouterSettings
        fields = (
            "api_key",
            "base_url",
            "default_profile",
            "request_timeout",
            "max_retries",
            "enabled",
        )
        widgets = {
            "api_key": PasswordInput(render_value=False),
        }

    def save(self, commit: bool = True) -> OpenRouterSettings:
        instance: OpenRouterSettings = super().save(commit=False)
        raw_key = self.cleaned_data.get("api_key") or ""
        if not raw_key and instance.pk:
            instance.api_key = OpenRouterSettings.objects.get(pk=instance.pk).api_key
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(OpenRouterSettings)
class OpenRouterSettingsAdmin(admin.ModelAdmin):
    form = OpenRouterSettingsForm
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "enabled",
                    "api_key",
                    "base_url",
                    "default_profile",
                    "request_timeout",
                    "max_retries",
                )
            },
        ),
    )

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
        for form in self.forms:
            if form.errors:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            model = form.cleaned_data.get("model")
            if model is None:
                continue
            if not model.is_active:
                raise ValidationError(_("Fallback models must be active."))
            if only_free and not model.is_free:
                raise ValidationError(_("only_free_models allows only free fallback models."))


class UsageProfileFallbackInline(admin.TabularInline):
    model = UsageProfileFallback
    form = UsageProfileFallbackForm
    formset = UsageProfileFallbackInlineFormSet
    extra = 1
    ordering = ("order",)
    autocomplete_fields = ("model",)


class UsageProfileForm(ModelForm):
    class Meta:
        model = UsageProfile
        fields = (
            "name",
            "model",
            "max_tokens",
            "temperature",
            "max_requests_per_day",
            "max_requests_per_month",
            "budget_usd_per_day",
            "budget_usd_per_month",
            "only_free_models",
            "is_active",
        )

    def clean(self) -> dict[str, object]:
        cleaned = super().clean() or {}
        model = cleaned.get("model")
        only_free = bool(cleaned.get("only_free_models"))
        if model is not None and not model.is_active:
            self.add_error("model", _("Primary model must be active."))
        if only_free and model is not None and not model.is_free:
            self.add_error("model", _("only_free_models requires a free primary model."))
        return cleaned


@admin.register(UsageProfile)
class UsageProfileAdmin(admin.ModelAdmin):
    form = UsageProfileForm
    inlines = (UsageProfileFallbackInline,)
    list_display = (
        "name",
        "model",
        "is_active",
        "only_free_models",
        "max_requests_per_day",
        "budget_usd_per_day",
    )
    list_filter = ("is_active", "only_free_models")
    search_fields = ("name",)
    autocomplete_fields = ("model",)


@admin.register(OpenRouterModel)
class OpenRouterModelAdmin(admin.ModelAdmin):
    list_display = ("model_id", "name", "modality", "is_active", "last_synced_at")
    list_filter = ("is_active", "modality")
    search_fields = ("model_id", "name")
    actions = ("sync_with_openrouter",)
    readonly_fields = ("last_synced_at",)

    @admin.action(description=_("Sync catalog with OpenRouter"))
    def sync_with_openrouter(
        self,
        request: HttpRequest,
        queryset: QuerySet[OpenRouterModel],
    ) -> None:
        try:
            summary = sync_openrouter_models()
        except (ConfigurationError, OpenRouterError, OSError) as exc:
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


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    change_list_template = "admin/django_openrouter/requestlog/change_list.html"
    list_display = (
        "created_at",
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
    search_fields = ("error_message",)
    ordering = ("-created_at",)
    readonly_fields = (
        "profile",
        "model",
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
