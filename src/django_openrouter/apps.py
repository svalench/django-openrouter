from __future__ import annotations

from django.apps import AppConfig


class DjangoOpenRouterConfig(AppConfig):
    """Конфиг приложения django_openrouter."""

    name = "django_openrouter"
    label = "django_openrouter"
    verbose_name = "OpenRouter"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.contrib import admin
        from django.http import HttpRequest, HttpResponseBase

        from django_openrouter import signals as _signals  # noqa: F401
        from django_openrouter.admin import OpenRouterAutocompleteJsonView

        def autocomplete_view(request: HttpRequest) -> HttpResponseBase:
            return OpenRouterAutocompleteJsonView.as_view(admin_site=admin.site)(request)

        admin.site.autocomplete_view = autocomplete_view  # type: ignore[method-assign,assignment]
