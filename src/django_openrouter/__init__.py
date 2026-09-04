"""django-openrouter — reusable Django app for OpenRouter models, budgets and usage logs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0b1"
default_app_config = "django_openrouter.apps.DjangoOpenRouterConfig"

if TYPE_CHECKING:
    from django_openrouter.client import (
        AsyncOpenRouterClient as AsyncOpenRouterClient,
    )
    from django_openrouter.client import (
        ChatResult as ChatResult,
    )
    from django_openrouter.client import (
        OpenRouterClient as OpenRouterClient,
    )
    from django_openrouter.client import (
        achat as achat,
    )
    from django_openrouter.client import (
        chat as chat,
    )

__all__ = [
    "AsyncOpenRouterClient",
    "ChatResult",
    "OpenRouterClient",
    "__version__",
    "achat",
    "chat",
]


def __getattr__(name: str) -> Any:
    # Ленивый импорт, чтобы версия пакета читалась без django.setup().
    if name in {"AsyncOpenRouterClient", "ChatResult", "OpenRouterClient", "achat", "chat"}:
        from django_openrouter import client as client_module

        mapping = {
            "AsyncOpenRouterClient": client_module.AsyncOpenRouterClient,
            "ChatResult": client_module.ChatResult,
            "OpenRouterClient": client_module.OpenRouterClient,
            "achat": client_module.achat,
            "chat": client_module.chat,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
