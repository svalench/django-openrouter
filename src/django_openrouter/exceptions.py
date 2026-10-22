"""Исключения библиотеки django-openrouter."""

from __future__ import annotations

from typing import Any


class OpenRouterError(Exception):
    """Базовое исключение библиотеки."""


class ConfigurationError(OpenRouterError):
    """Некорректная или неполная конфигурация (ключ, профиль, URL)."""


class OpenRouterDisabled(OpenRouterError):
    """Глобальный kill switch: OpenRouterSettings.enabled = False."""


class ModelDisabled(OpenRouterError):
    """Профиль или модель выключены, либо нарушено правило only_free_models."""


class BudgetExceeded(OpenRouterError):
    """Исчерпан дневной или месячный бюджет профиля (HTTP-стоп, без fallback)."""


class RateLimitExceeded(OpenRouterError):
    """Исчерпан лимит запросов профиля за день или месяц."""


class UnsupportedAudioFormat(OpenRouterError):
    """Формат аудио не из списка, который принимает транскрипция OpenRouter."""


class AudioTooLarge(OpenRouterError):
    """Размер аудио больше лимита профиля или 25 МиБ по умолчанию."""


class OpenRouterAPIError(OpenRouterError):
    """Ошибка HTTP API OpenRouter после исчерпания retry/fallback."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenRouterTimeout(OpenRouterError):
    """Истёк общий дедлайн вызова, а не пауза между байтами.

    partial — неполный ChatResult (текст, картинки, usage), если провайдер
    успел что-то прислать. Для stream() тот же результат приходит финальным
    чанком с incomplete=True, и исключение из генератора не бросается.
    """

    def __init__(self, message: str, *, partial: Any = None) -> None:
        super().__init__(message)
        self.partial = partial
