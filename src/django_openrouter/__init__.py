"""django-openrouter — reusable Django app for OpenRouter models, budgets and usage logs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.5"
default_app_config = "django_openrouter.apps.DjangoOpenRouterConfig"

if TYPE_CHECKING:
    from django_openrouter.client import (
        AsyncOpenRouterClient as AsyncOpenRouterClient,
    )
    from django_openrouter.client import (
        ChatChunk as ChatChunk,
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
        astream as astream,
    )
    from django_openrouter.client import (
        chat as chat,
    )
    from django_openrouter.client import (
        stream as stream,
    )

__all__ = [
    "AsyncOpenRouterClient",
    "ChatChunk",
    "ChatResult",
    "OpenRouterClient",
    "__version__",
    "achat",
    "astream",
    "chat",
    "stream",
]

_EXPORTS = frozenset(__all__) - {"__version__"}


def __getattr__(name: str) -> Any:
    # Ленивый импорт, чтобы версия пакета читалась без django.setup().
    if name in _EXPORTS:
        from django_openrouter import client as client_module

        mapping = {
            "AsyncOpenRouterClient": client_module.AsyncOpenRouterClient,
            "ChatChunk": client_module.ChatChunk,
            "ChatResult": client_module.ChatResult,
            "OpenRouterClient": client_module.OpenRouterClient,
            "achat": client_module.achat,
            "astream": client_module.astream,
            "chat": client_module.chat,
            "stream": client_module.stream,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
