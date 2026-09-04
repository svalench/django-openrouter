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


@receiver(post_save, sender=UsageProfile)
def ensure_primary_in_chain(
    sender: type[object], instance: UsageProfile, raw: bool = False, **kwargs: object
) -> None:
    """create(model=...) без инлайнов — primary попадает в through-таблицу."""
    if raw or not instance.pk or not instance.model_id:
        return
    if instance.fallback_links.filter(model_id=instance.model_id).exists():
        return
    UsageProfileFallback.objects.create(profile=instance, model_id=instance.model_id, order=0)


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
