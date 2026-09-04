"""Синхронизация каталога моделей с GET /api/v1/models."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from django_openrouter.config import (
    get_runtime_config,
    invalidate_catalog_cache,
    is_catalog_fresh,
    mark_catalog_fresh,
    resolve_api_key,
)
from django_openrouter.exceptions import ConfigurationError
from django_openrouter.models import OpenRouterModel, OpenRouterSettings
from django_openrouter.parameter_size import parse_parameter_size

_ENDPOINTS_CONCURRENCY = 16
_ENDPOINTS_BUDGET_SEC = 15.0
_ENDPOINTS_REQUEST_TIMEOUT = 5.0
_API_V1_SUFFIX = "/api/v1"


@dataclass(frozen=True)
class SyncSummary:
    created: int
    updated: int
    deactivated: int
    total_remote: int


def _optional_price(value: object) -> Decimal | None:
    """Decimal из pricing; None если ключа нет или значение битое."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _defaults_from_remote(item: dict[str, Any]) -> dict[str, Any]:
    architecture = item.get("architecture") or {}
    modality = architecture.get("modality") or item.get("modality") or ""
    pricing = item.get("pricing") or {}
    pricing_dict = pricing if isinstance(pricing, dict) else {}
    size = parse_parameter_size(item.get("id"), item.get("name"), item.get("description"))
    return {
        "name": item.get("name") or item.get("id") or "",
        "context_length": item.get("context_length"),
        "pricing": pricing_dict,
        "prompt_price": _optional_price(pricing_dict.get("prompt")),
        "completion_price": _optional_price(pricing_dict.get("completion")),
        "supported_parameters": item.get("supported_parameters") or [],
        "modality": str(modality),
        "parameter_count": size.count if size is not None else None,
        "parameter_label": size.label if size is not None else "",
        "last_synced_at": timezone.now(),
    }


def _p50(value: object) -> float | None:
    raw: object
    if isinstance(value, dict):
        raw = value.get("p50")
    else:
        raw = value
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _latency_ms(p50: float | None) -> float | None:
    """p50 < 10 считаем секундами (как в примерах OpenRouter)."""
    if p50 is None:
        return None
    if p50 < 10:
        return p50 * 1000.0
    return p50


def _best_stats(endpoints: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    """Минимальная latency p50; throughput с того же endpoint."""
    scored: list[tuple[float | None, float | None]] = []
    for endpoint in endpoints:
        lat = _p50(endpoint.get("latency_last_30m"))
        thr = _p50(endpoint.get("throughput_last_30m"))
        scored.append((lat, thr))
    with_lat = [row for row in scored if row[0] is not None]
    if with_lat:
        lat, thr = min(with_lat, key=lambda row: row[0] or 0.0)
        return _latency_ms(lat), thr
    with_thr = [row for row in scored if row[1] is not None]
    if with_thr:
        _lat, thr = max(with_thr, key=lambda row: row[1] or 0.0)
        return None, thr
    return None, None


def _parse_endpoints(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    endpoints: object
    if isinstance(data, dict):
        endpoints = data.get("endpoints")
    elif isinstance(data, list):
        endpoints = data
    else:
        endpoints = payload.get("endpoints")
    if not isinstance(endpoints, list):
        return []
    return [item for item in endpoints if isinstance(item, dict)]


def _endpoints_url(base_url: str, item: dict[str, Any], model_id: str) -> str:
    """URL статистики провайдеров: links.details или /models/{id}/endpoints."""
    links = item.get("links") if isinstance(item.get("links"), dict) else {}
    details = links.get("details") if isinstance(links, dict) else None
    if isinstance(details, str) and details.startswith("http"):
        return details
    if isinstance(details, str) and details.startswith("/"):
        origin = base_url
        if origin.endswith(_API_V1_SUFFIX):
            origin = origin[: -len(_API_V1_SUFFIX)]
        return origin.rstrip("/") + details
    return f"{base_url}/models/{model_id}/endpoints"


def _fetch_endpoint_stats(
    http: httpx.Client,
    url: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[float | None, float | None]:
    try:
        response = http.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None, None
    return _best_stats(_parse_endpoints(payload))


def _enrich_endpoint_stats(
    *,
    headers: dict[str, str],
    base_url: str,
    items: list[dict[str, Any]],
    request_timeout: float,
) -> None:
    """Параллельно тянет /endpoints; пишем в БД только из главного потока."""
    jobs: list[tuple[str, str]] = []
    for item in items:
        model_id = str(item.get("id") or "")
        if not model_id:
            continue
        jobs.append((model_id, _endpoints_url(base_url, item, model_id)))
    if not jobs:
        return

    deadline = time.monotonic() + _ENDPOINTS_BUDGET_SEC
    results: dict[str, tuple[float | None, float | None]] = {}
    per_timeout = min(_ENDPOINTS_REQUEST_TIMEOUT, request_timeout)

    def _job(model_id: str, url: str) -> tuple[str, tuple[float | None, float | None]]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return model_id, (None, None)
        timeout = min(per_timeout, remaining)
        with httpx.Client(timeout=timeout) as client:
            return model_id, _fetch_endpoint_stats(client, url, headers, timeout)

    with ThreadPoolExecutor(max_workers=_ENDPOINTS_CONCURRENCY) as pool:
        futures = [pool.submit(_job, model_id, url) for model_id, url in jobs]
        for future in as_completed(futures):
            if time.monotonic() > deadline:
                break
            try:
                model_id, stats = future.result()
            except Exception:
                continue
            results[model_id] = stats

    for model_id, (latency_ms, throughput) in results.items():
        if latency_ms is None and throughput is None:
            continue
        OpenRouterModel.objects.filter(model_id=model_id).update(
            latency_ms=latency_ms,
            throughput=throughput,
        )


def _resolve_sync_key(api_key: str | None, stored: str) -> str:
    key = api_key or resolve_api_key(stored)
    if not key:
        key = get_runtime_config().api_key
    if not key:
        raise ConfigurationError(_("OpenRouter API key is not configured."))
    return key


def sync_openrouter_models(
    *,
    api_key: str | None = None,
    timeout: float | None = None,
    enrich_stats: bool = False,
) -> SyncSummary:
    """
    Upsert каталога. Существующие строки не удаляются.
    Исчезнувшие модели помечаются is_active=False.
    is_active у присутствующих в API не перезаписывается (решение админа).
    """
    settings_obj = OpenRouterSettings.load()
    key = _resolve_sync_key(api_key, settings_obj.api_key)

    base_url = (settings_obj.base_url or "https://openrouter.ai/api/v1").rstrip("/")
    request_timeout = float(timeout if timeout is not None else settings_obj.request_timeout)
    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {key}"}
    with httpx.Client(timeout=request_timeout) as http:
        response = http.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()

        remote = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(remote, list):
            raise ConfigurationError(_("Unexpected OpenRouter /models response."))

        created = 0
        updated = 0
        seen_ids: set[str] = set()
        catalog_items: list[dict[str, Any]] = []
        with transaction.atomic():
            for item in remote:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                model_id = str(item["id"])
                seen_ids.add(model_id)
                catalog_items.append(item)
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
        if enrich_stats:
            _enrich_endpoint_stats(
                headers=headers,
                base_url=base_url,
                items=catalog_items,
                request_timeout=request_timeout,
            )

    if enrich_stats:
        mark_catalog_fresh()
    else:
        invalidate_catalog_cache()
    return SyncSummary(
        created=created,
        updated=updated,
        deactivated=deactivated,
        total_remote=len(seen_ids),
    )


def ensure_catalog_fresh() -> SyncSummary | None:
    """Синк каталога + stats, если 10-минутный кэш пуст."""
    if is_catalog_fresh():
        return None
    return sync_openrouter_models(enrich_stats=True)
