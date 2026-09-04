from __future__ import annotations

from django.apps import AppConfig


class DjangoOpenRouterConfig(AppConfig):
    """Конфиг приложения django_openrouter."""

    name = "django_openrouter"
    label = "django_openrouter"
    verbose_name = "OpenRouter"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django_openrouter import signals as _signals  # noqa: F401
