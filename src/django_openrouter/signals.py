"""Инвалидация кэша runtime-конфига при изменениях в админке."""

from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from django_openrouter.config import invalidate_runtime_config
from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    UsageProfile,
    UsageProfileFallback,
)


@receiver(post_save, sender=OpenRouterSettings)
@receiver(post_delete, sender=OpenRouterSettings)
@receiver(post_save, sender=OpenRouterModel)
@receiver(post_delete, sender=OpenRouterModel)
@receiver(post_save, sender=UsageProfile)
@receiver(post_delete, sender=UsageProfile)
@receiver(post_save, sender=UsageProfileFallback)
@receiver(post_delete, sender=UsageProfileFallback)
def invalidate_openrouter_cache(sender: type[object], **kwargs: object) -> None:
    invalidate_runtime_config()
