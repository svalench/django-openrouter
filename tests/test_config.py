from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import override_settings

from django_openrouter.config import (
    CACHE_KEY,
    CATALOG_CACHE_KEY,
    catalog_cache_timeout,
    get_runtime_config,
    invalidate_catalog_cache,
    invalidate_runtime_config,
    mark_catalog_fresh,
    resolve_api_key,
)
from django_openrouter.models import OpenRouterSettings, UsageProfile

pytestmark = pytest.mark.django_db


def test_runtime_config_cached(or_settings: OpenRouterSettings, profile: UsageProfile) -> None:
    cache.clear()
    first = get_runtime_config()
    or_settings.base_url = "https://changed.example/api/v1"
    # без save сигнал не сработает — в кэше старое значение
    OpenRouterSettings.objects.filter(pk=or_settings.pk).update(
        base_url="https://changed.example/api/v1"
    )
    cached = get_runtime_config()
    assert cached.base_url == first.base_url
    assert cached.profiles["chat"].name == "chat"
    assert cached.streaming_enabled is False
    assert cached.max_parallel_requests == 10


def test_signal_invalidates_cache(or_settings: OpenRouterSettings) -> None:
    cfg = get_runtime_config()
    assert cfg.enabled is True
    assert cfg.streaming_enabled is False
    or_settings.enabled = False
    or_settings.streaming_enabled = True
    or_settings.max_parallel_requests = 4
    or_settings.save()
    reloaded = get_runtime_config()
    assert reloaded.enabled is False
    assert reloaded.streaming_enabled is True
    assert reloaded.max_parallel_requests == 4


def test_invalidate_helper(or_settings: OpenRouterSettings) -> None:
    get_runtime_config()
    assert cache.get(CACHE_KEY) is not None
    invalidate_runtime_config()
    assert cache.get(CACHE_KEY) is None


def test_catalog_cache_roundtrip() -> None:
    cache.clear()
    assert catalog_cache_timeout() == 600
    mark_catalog_fresh()
    assert cache.get(CATALOG_CACHE_KEY) is True
    invalidate_catalog_cache()
    assert cache.get(CATALOG_CACHE_KEY) is None


def test_api_key_from_env(
    or_settings: OpenRouterSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    or_settings.api_key = ""
    or_settings.save()
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    assert resolve_api_key("") == "from-env"
    cfg = get_runtime_config(force_reload=True)
    assert cfg.api_key == "from-env"


@override_settings(OPENROUTER_API_KEY="from-django-setting")
def test_api_key_from_django_setting(or_settings: OpenRouterSettings) -> None:
    or_settings.api_key = ""
    or_settings.save()
    assert resolve_api_key("") == "from-django-setting"


@override_settings(
    OPENROUTER={"CACHE_TIMEOUT": 60, "CACHE_ALIAS": "default", "API_KEY": "from-dict"}
)
def test_api_key_from_openrouter_dict(or_settings: OpenRouterSettings) -> None:
    or_settings.api_key = ""
    or_settings.save()
    assert resolve_api_key("") == "from-dict"


def test_db_api_key_wins(or_settings: OpenRouterSettings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "from-env")
    assert resolve_api_key("sk-db") == "sk-db"


def test_snapshot_chain_excludes_primary_from_fallbacks(
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
    fallback_model,
) -> None:
    from django_openrouter.models import UsageProfileFallback

    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    cfg = get_runtime_config(force_reload=True)
    snapshot = cfg.profiles["chat"]
    assert snapshot.model.model_id == "anthropic/claude-3.5-sonnet"
    assert [item.model_id for item in snapshot.fallback_models] == [fallback_model.model_id]


def test_inactive_profile_not_in_config(
    or_settings: OpenRouterSettings, profile: UsageProfile
) -> None:
    profile.is_active = False
    profile.save()
    cfg = get_runtime_config(force_reload=True)
    assert "chat" not in cfg.profiles
    assert cfg.default_profile_name is None


@override_settings(OPENROUTER={"CACHE_TIMEOUT": 30, "CACHE_ALIAS": "does-not-exist"})
def test_missing_cache_alias_falls_back(or_settings: OpenRouterSettings) -> None:
    from django_openrouter.config import get_runtime_config

    cfg = get_runtime_config(force_reload=True)
    assert cfg.enabled is True
    assert cfg.streaming_enabled is False
    assert cfg.max_parallel_requests == 10


@override_settings(OPENROUTER="not-a-dict")
def test_openrouter_setting_non_mapping() -> None:
    from django_openrouter.config import openrouter_setting

    assert openrouter_setting("CACHE_TIMEOUT", 60) == 60
