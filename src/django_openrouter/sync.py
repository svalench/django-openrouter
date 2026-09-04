"""Синхронизация каталога моделей с GET /api/v1/models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from django.db import transaction
from django.utils import timezone

from django_openrouter.config import get_runtime_config, resolve_api_key
from django_openrouter.exceptions import ConfigurationError
from django_openrouter.models import OpenRouterModel, OpenRouterSettings


@dataclass(frozen=True)
class SyncSummary:
    created: int
    updated: int
    deactivated: int
    total_remote: int


def _defaults_from_remote(item: dict[str, Any]) -> dict[str, Any]:
    architecture = item.get("architecture") or {}
    modality = architecture.get("modality") or item.get("modality") or ""
    return {
        "name": item.get("name") or item.get("id") or "",
        "context_length": item.get("context_length"),
        "pricing": item.get("pricing") or {},
        "supported_parameters": item.get("supported_parameters") or [],
        "modality": str(modality),
        "last_synced_at": timezone.now(),
    }


def sync_openrouter_models(
    *,
    api_key: str | None = None,
    timeout: float | None = None,
) -> SyncSummary:
    """
    Upsert каталога. Существующие строки не удаляются.
    Исчезнувшие модели помечаются is_active=False.
    is_active у присутствующих в API не перезаписывается (решение админа).
    """
    settings_obj = OpenRouterSettings.load()
    key = api_key or resolve_api_key(settings_obj.api_key)
    if not key:
        # Если кэш ещё пуст — пробуем runtime-конфиг.
        key = get_runtime_config().api_key
    if not key:
        raise ConfigurationError("OpenRouter API key is not configured.")

    base_url = (settings_obj.base_url or "https://openrouter.ai/api/v1").rstrip("/")
    request_timeout = float(timeout if timeout is not None else settings_obj.request_timeout)
    url = f"{base_url}/models"
    with httpx.Client(timeout=request_timeout) as http:
        response = http.get(url, headers={"Authorization": f"Bearer {key}"})
        response.raise_for_status()
        payload = response.json()

    remote = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(remote, list):
        raise ConfigurationError("Unexpected OpenRouter /models response.")

    created = 0
    updated = 0
    seen_ids: set[str] = set()
    with transaction.atomic():
        for item in remote:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            model_id = str(item["id"])
            seen_ids.add(model_id)
            _obj, was_created = OpenRouterModel.objects.update_or_create(
                model_id=model_id,
                defaults=_defaults_from_remote(item),
            )
            if was_created:
                created += 1
            else:
                updated += 1
        deactivated = 0
        if seen_ids:
            deactivated = (
                OpenRouterModel.objects.exclude(model_id__in=seen_ids)
                .filter(is_active=True)
                .update(is_active=False, last_synced_at=timezone.now())
            )
    return SyncSummary(
        created=created,
        updated=updated,
        deactivated=deactivated,
        total_remote=len(seen_ids),
    )
