"""django-openrouter — reusable Django app for OpenRouter models, budgets and usage logs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.6.0"
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
        GeneratedImage as GeneratedImage,
    )
    from django_openrouter.client import (
        OpenRouterClient as OpenRouterClient,
    )
    from django_openrouter.client import (
        achat as achat,
    )
    from django_openrouter.client import (
        agenerate_image as agenerate_image,
    )
    from django_openrouter.client import (
        astream as astream,
    )
    from django_openrouter.client import (
        chat as chat,
    )
    from django_openrouter.client import (
        generate_image as generate_image,
    )
    from django_openrouter.client import (
        stream as stream,
    )
    from django_openrouter.exceptions import (
        OpenRouterTimeout as OpenRouterTimeout,
    )
    from django_openrouter.transcription import (
        TranscriptionResult as TranscriptionResult,
    )
    from django_openrouter.transcription import (
        atranscribe as atranscribe,
    )
    from django_openrouter.transcription import (
        transcribe as transcribe,
    )

__all__ = [
    "AsyncOpenRouterClient",
    "ChatChunk",
    "ChatResult",
    "GeneratedImage",
    "OpenRouterClient",
    "OpenRouterTimeout",
    "TranscriptionResult",
    "__version__",
    "achat",
    "agenerate_image",
    "astream",
    "atranscribe",
    "chat",
    "generate_image",
    "stream",
    "transcribe",
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
            "GeneratedImage": client_module.GeneratedImage,
            "OpenRouterClient": client_module.OpenRouterClient,
            "OpenRouterTimeout": None,
            "achat": client_module.achat,
            "agenerate_image": client_module.agenerate_image,
            "astream": client_module.astream,
            "chat": client_module.chat,
            "generate_image": client_module.generate_image,
            "stream": client_module.stream,
        }
        if name == "OpenRouterTimeout":
            from django_openrouter.exceptions import OpenRouterTimeout

            return OpenRouterTimeout
        if name in mapping and mapping[name] is not None:
            return mapping[name]
        from django_openrouter import transcription as transcription_module

        transcription_mapping = {
            "TranscriptionResult": transcription_module.TranscriptionResult,
            "atranscribe": transcription_module.atranscribe,
            "transcribe": transcription_module.transcribe,
        }
        return transcription_mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
