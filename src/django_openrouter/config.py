"""Runtime-конфигурация с кэшированием через Django cache framework."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings as django_settings
from django.core.cache import caches
from django.core.cache.backends.base import BaseCache
from django.db.models import Prefetch

from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    UsageProfile,
    UsageProfileFallback,
)

CACHE_KEY = "django_openrouter:runtime_config:v1"
CATALOG_CACHE_KEY = "django_openrouter:admin_catalog:v1"
_DEFAULT_CACHE_TIMEOUT = 60
_DEFAULT_CATALOG_CACHE_TIMEOUT = 600
_DEFAULT_CACHE_ALIAS = "default"
_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def openrouter_setting(key: str, default: Any = None) -> Any:
    """Читает ключ из settings.OPENROUTER, иначе возвращает default."""
    options = django_settings.OPENROUTER if hasattr(django_settings, "OPENROUTER") else None
    if not isinstance(options, dict):
        return default
    if key not in options:
        return default
    return options[key]


def resolve_api_key(stored: str = "") -> str:
    """
    Порядок: ключ из БД → OPENROUTER['API_KEY'] → OPENROUTER_API_KEY → env.
    """
    if stored:
        return stored
    from_dict = openrouter_setting("API_KEY", "") or ""
    if from_dict:
        return str(from_dict)
    top_level = getattr(django_settings, "OPENROUTER_API_KEY", "") or ""
    if top_level:
        return str(top_level)
    return os.environ.get("OPENROUTER_API_KEY", "") or ""


@dataclass
class ModelSnapshot:
    """Слепок каталожной модели для клиента (без ORM)."""

    pk: int
    model_id: str
    name: str
    pricing: dict[str, Any]
    is_active: bool
    is_free: bool


@dataclass
class ProfileSnapshot:
    """Слепок активного профиля использования."""

    pk: int
    name: str
    model: ModelSnapshot
    fallback_models: list[ModelSnapshot]
    max_tokens: int | None
    temperature: float | None
    max_requests_per_day: int | None
    max_requests_per_month: int | None
    budget_usd_per_day: Any
    budget_usd_per_month: Any
    only_free_models: bool
    is_active: bool


@dataclass
class RuntimeConfig:
    """Кэшируемый снимок настроек + активных профилей."""

    enabled: bool
    api_key: str
    base_url: str
    request_timeout: int
    max_retries: int
    streaming_enabled: bool
    max_parallel_requests: int
    http_referer: str
    x_title: str
    default_profile_name: str | None
    profiles: dict[str, ProfileSnapshot] = field(default_factory=dict)


def _cache_alias() -> str:
    alias = openrouter_setting("CACHE_ALIAS", _DEFAULT_CACHE_ALIAS) or _DEFAULT_CACHE_ALIAS
    return str(alias)


def _cache() -> BaseCache:
    """Возвращает кэш-бэкенд alias из OPENROUTER['CACHE_ALIAS']."""
    try:
        return caches[_cache_alias()]
    except Exception:
        return caches["default"]


def catalog_cache_timeout() -> int:
    """TTL живого каталога админки, секунды (дефолт 10 мин)."""
    return int(
        openrouter_setting("CATALOG_CACHE_TIMEOUT", _DEFAULT_CATALOG_CACHE_TIMEOUT)
        or _DEFAULT_CATALOG_CACHE_TIMEOUT
    )


def is_catalog_fresh() -> bool:
    """True, если каталог админки ещё в 10-минутном кэше."""
    return _cache().get(CATALOG_CACHE_KEY) is not None


def mark_catalog_fresh() -> None:
    """Помечает каталог свежим после успешного синка."""
    _cache().set(CATALOG_CACHE_KEY, True, catalog_cache_timeout())


def invalidate_catalog_cache() -> None:
    """Сбрасывает кэш каталога админки (ручной синк / команда)."""
    _cache().delete(CATALOG_CACHE_KEY)


def invalidate_runtime_config() -> None:
    """Сбрасывает кэш конфигурации (вызывается из сигналов)."""
    _cache().delete(CACHE_KEY)


def get_runtime_config(*, force_reload: bool = False) -> RuntimeConfig:
    """Возвращает runtime-конфиг из кэша либо собирает его из БД."""
    cache = _cache()
    if not force_reload:
        cached = cache.get(CACHE_KEY)
        if isinstance(cached, RuntimeConfig):
            return cached
    cfg = load_runtime_config()
    timeout = int(
        openrouter_setting("CACHE_TIMEOUT", _DEFAULT_CACHE_TIMEOUT) or _DEFAULT_CACHE_TIMEOUT
    )
    cache.set(CACHE_KEY, cfg, timeout)
    return cfg


def load_runtime_config() -> RuntimeConfig:
    """Читает OpenRouterSettings и активные профили напрямую из БД."""
    settings_obj = OpenRouterSettings.load()
    fallback_qs = UsageProfileFallback.objects.select_related("model").order_by("order", "id")
    profiles_qs = (
        UsageProfile.objects.filter(is_active=True)
        .select_related("model")
        .prefetch_related(Prefetch("fallback_links", queryset=fallback_qs))
    )
    profiles: dict[str, ProfileSnapshot] = {}
    for profile in profiles_qs:
        if not profile.ordered_models():
            continue
        profiles[profile.name] = _profile_snapshot(profile)

    default_name: str | None = None
    if settings_obj.default_profile_id:
        default_profile = settings_obj.default_profile
        if (
            default_profile is not None
            and default_profile.is_active
            and default_profile.ordered_models()
        ):
            default_name = default_profile.name
            if default_name not in profiles:
                profiles[default_name] = _profile_snapshot(default_profile)

    http_referer = str(openrouter_setting("HTTP_REFERER", "") or "")
    x_title = str(openrouter_setting("X_TITLE", "") or "")
    return RuntimeConfig(
        enabled=bool(settings_obj.enabled),
        api_key=resolve_api_key(settings_obj.api_key),
        base_url=(settings_obj.base_url or _DEFAULT_BASE_URL).rstrip("/"),
        request_timeout=int(settings_obj.request_timeout),
        max_retries=int(settings_obj.max_retries),
        streaming_enabled=bool(settings_obj.streaming_enabled),
        max_parallel_requests=int(settings_obj.max_parallel_requests),
        http_referer=http_referer,
        x_title=x_title,
        default_profile_name=default_name,
        profiles=profiles,
    )


def snapshot_from_model(model: OpenRouterModel) -> ModelSnapshot:
    return ModelSnapshot(
        pk=model.pk,
        model_id=model.model_id,
        name=model.name,
        pricing=dict(model.pricing or {}),
        is_active=bool(model.is_active),
        is_free=bool(model.is_free),
    )


def _profile_snapshot(profile: UsageProfile) -> ProfileSnapshot:
    chain = profile.ordered_models()
    primary = chain[0]
    fallbacks = [snapshot_from_model(item) for item in chain[1:]]
    return ProfileSnapshot(
        pk=profile.pk,
        name=profile.name,
        model=snapshot_from_model(primary),
        fallback_models=fallbacks,
        max_tokens=profile.max_tokens,
        temperature=profile.temperature,
        max_requests_per_day=profile.max_requests_per_day,
        max_requests_per_month=profile.max_requests_per_month,
        budget_usd_per_day=profile.budget_usd_per_day,
        budget_usd_per_month=profile.budget_usd_per_month,
        only_free_models=bool(profile.only_free_models),
        is_active=bool(profile.is_active),
    )
