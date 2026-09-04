"""Синхронный и асинхронный клиенты OpenRouter (Chat Completions)."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from asgiref.sync import sync_to_async

from django_openrouter.config import (
    ProfileSnapshot,
    RuntimeConfig,
    get_runtime_config,
)
from django_openrouter.exceptions import (
    ConfigurationError,
    ModelDisabled,
    OpenRouterAPIError,
    OpenRouterDisabled,
)
from django_openrouter.models import OpenRouterModel, RequestLog, UsageProfile
from django_openrouter.rules import assert_model_allowed, check_limits

ChatMessage = Mapping[str, Any]
ChatMessages = Sequence[ChatMessage]

_FALLBACK_STATUSES = frozenset({402, 429})


@dataclass(frozen=True)
class ChatResult:
    """Результат chat-completions вызова."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    catalog_cost_usd: Decimal | None
    model_used: str
    latency_ms: int
    raw: dict[str, Any] = field(default_factory=dict)


def compute_cost(
    prompt_tokens: int,
    completion_tokens: int,
    pricing: Mapping[str, Any] | None,
    usage_cost: object | None = None,
) -> tuple[Decimal, Decimal | None]:
    """
    Считает стоимость по токенам usage и pricing каталога.

    Возвращает (cost_usd для лога, catalog_cost для сверки).
    Если OpenRouter прислал usage.cost — он используется как fallback,
    когда в каталоге нет цены.
    """
    catalog_cost: Decimal | None = None
    if pricing:
        prompt_price = Decimal(str(pricing.get("prompt") or 0))
        completion_price = Decimal(str(pricing.get("completion") or 0))
        catalog_cost = prompt_price * prompt_tokens + completion_price * completion_tokens
    api_cost = Decimal(str(usage_cost)) if usage_cost is not None else None
    if catalog_cost is not None:
        return catalog_cost, catalog_cost
    return api_cost or Decimal("0"), catalog_cost


def _headers(cfg: RuntimeConfig) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    if cfg.http_referer:
        headers["HTTP-Referer"] = cfg.http_referer
    if cfg.x_title:
        headers["X-Title"] = cfg.x_title
    return headers


def _build_payload(
    profile: UsageProfile,
    model_id: str,
    messages: ChatMessages,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model_id, "messages": list(messages)}
    max_tokens = overrides["max_tokens"] if "max_tokens" in overrides else profile.max_tokens
    temperature = overrides["temperature"] if "temperature" in overrides else profile.temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    for key, value in overrides.items():
        if key in {"stream", "max_tokens", "temperature", "model"}:
            continue
        payload[key] = value
    return payload


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") or {}
    content = message.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return str(content)


def _resolve_profile(cfg: RuntimeConfig, profile_name: str | None) -> ProfileSnapshot:
    name = profile_name or cfg.default_profile_name
    if not name:
        raise ConfigurationError("No usage profile specified and default_profile is not set.")
    snapshot = cfg.profiles.get(name)
    if snapshot is None:
        raise ConfigurationError(f"Usage profile {name!r} is not found or inactive.")
    return snapshot


def _model_chain(
    profile: UsageProfile,
    overrides: dict[str, Any],
) -> list[OpenRouterModel]:
    chain: list[OpenRouterModel] = [profile.model]
    seen: set[int] = {profile.model.pk}
    for model in profile.ordered_fallback_models():
        if model.pk not in seen:
            chain.append(model)
            seen.add(model.pk)
    override_id = overrides.get("model")
    if override_id:
        try:
            overridden = OpenRouterModel.objects.get(model_id=override_id)
        except OpenRouterModel.DoesNotExist as exc:
            raise ConfigurationError(f"Unknown model {override_id!r}.") from exc
        chain = [overridden] + [item for item in chain if item.pk != overridden.pk]
    return chain


def _allowed_models(profile: UsageProfile, chain: list[OpenRouterModel]) -> list[OpenRouterModel]:
    allowed: list[OpenRouterModel] = []
    for model in chain:
        try:
            assert_model_allowed(profile, model)
        except ModelDisabled:
            continue
        allowed.append(model)
    if not chain:
        raise ConfigurationError(f"Profile {profile.name!r} has no models configured.")
    if not allowed:
        raise ModelDisabled(f"No allowed models left for profile {profile.name!r}.")
    return allowed


def _should_fallback(status_code: int) -> bool:
    return status_code in _FALLBACK_STATUSES or status_code >= 500


def _write_log(
    *,
    profile: UsageProfile,
    model: OpenRouterModel | None,
    status_code: int,
    error_message: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: Decimal = Decimal("0"),
    latency_ms: int = 0,
) -> None:
    RequestLog.objects.create(
        profile=profile,
        model=model,
        status_code=status_code,
        error_message=error_message,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


def _result_from_payload(
    payload: dict[str, Any],
    model: OpenRouterModel,
    latency_ms: int,
) -> ChatResult:
    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    usage_cost = usage.get("cost")
    cost_usd, catalog_cost = compute_cost(
        prompt_tokens,
        completion_tokens,
        model.pricing,
        usage_cost,
    )
    return ChatResult(
        content=_extract_content(payload),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        catalog_cost_usd=catalog_cost,
        model_used=str(payload.get("model") or model.model_id),
        latency_ms=latency_ms,
        raw=payload,
    )


def _prepare(
    profile_name: str | None,
    overrides: dict[str, Any],
) -> tuple[RuntimeConfig, UsageProfile]:
    if overrides.get("stream"):
        raise NotImplementedError("Streaming is not implemented in django-openrouter MVP.")
    cfg = get_runtime_config()
    if not cfg.enabled:
        raise OpenRouterDisabled("OpenRouter is disabled in admin settings.")
    if not cfg.api_key:
        raise ConfigurationError("OpenRouter API key is not configured.")
    snapshot = _resolve_profile(cfg, profile_name)
    profile = UsageProfile.objects.select_related("model").get(pk=snapshot.pk)
    check_limits(profile)
    return cfg, profile


class OpenRouterClient:
    """Синхронный клиент. Конфигурация берётся из runtime cache, не из БД напрямую."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        cfg, profile = _prepare(self.profile_name, overrides)
        chain = _allowed_models(profile, _model_chain(profile, overrides))
        url = f"{cfg.base_url}/chat/completions"
        last_error: Exception | None = None
        with httpx.Client(timeout=cfg.request_timeout) as http:
            for model in chain:
                payload = _build_payload(profile, model.model_id, messages, overrides)
                result, last_error = _attempt_model_sync(http, url, cfg, profile, model, payload)
                if result is not None:
                    return result
        if last_error is not None:
            raise last_error
        raise OpenRouterAPIError("All models failed without a specific error.")


def _attempt_model_sync(
    http: httpx.Client,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> tuple[ChatResult | None, Exception | None]:
    last_error: Exception | None = None
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            response = http.post(url, json=payload, headers=_headers(cfg))
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _write_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if attempt >= int(cfg.max_retries):
                return None, last_error
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 200:
            payload_json = response.json()
            result = _result_from_payload(payload_json, model, latency_ms)
            _write_log(
                profile=profile,
                model=model,
                status_code=200,
                error_message=None,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
            )
            return result, None
        error_text = response.text[:2000]
        _write_log(
            profile=profile,
            model=model,
            status_code=response.status_code,
            error_message=error_text,
            latency_ms=latency_ms,
        )
        last_error = OpenRouterAPIError(
            f"OpenRouter returned HTTP {response.status_code}: {error_text}",
            status_code=response.status_code,
        )
        if response.status_code >= 500 and attempt < int(cfg.max_retries):
            continue
        if _should_fallback(response.status_code):
            return None, last_error
        raise last_error
    return None, last_error


class AsyncOpenRouterClient:
    """Асинхронный клиент с тем же интерфейсом, что и OpenRouterClient."""

    def __init__(self, profile_name: str | None = None) -> None:
        self.profile_name = profile_name

    async def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult:
        cfg, profile = await sync_to_async(_prepare, thread_sensitive=True)(
            self.profile_name, overrides
        )
        chain = await sync_to_async(_allowed_models, thread_sensitive=True)(
            profile, await sync_to_async(_model_chain, thread_sensitive=True)(profile, overrides)
        )
        url = f"{cfg.base_url}/chat/completions"
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=cfg.request_timeout) as http:
            for model in chain:
                payload = _build_payload(profile, model.model_id, messages, overrides)
                result, last_error = await _attempt_model_async(
                    http, url, cfg, profile, model, payload
                )
                if result is not None:
                    return result
        if last_error is not None:
            raise last_error
        raise OpenRouterAPIError("All models failed without a specific error.")


async def _awrite_log(
    *,
    profile: UsageProfile,
    model: OpenRouterModel | None,
    status_code: int,
    error_message: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: Decimal = Decimal("0"),
    latency_ms: int = 0,
) -> None:
    await RequestLog.objects.acreate(
        profile=profile,
        model=model,
        status_code=status_code,
        error_message=error_message,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


async def _attempt_model_async(
    http: httpx.AsyncClient,
    url: str,
    cfg: RuntimeConfig,
    profile: UsageProfile,
    model: OpenRouterModel,
    payload: dict[str, Any],
) -> tuple[ChatResult | None, Exception | None]:
    last_error: Exception | None = None
    for attempt in range(int(cfg.max_retries) + 1):
        started = time.perf_counter()
        try:
            response = await http.post(url, json=payload, headers=_headers(cfg))
        except httpx.RequestError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            await _awrite_log(
                profile=profile,
                model=model,
                status_code=0,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            last_error = OpenRouterAPIError(str(exc), status_code=None)
            if attempt >= int(cfg.max_retries):
                return None, last_error
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code == 200:
            payload_json = response.json()
            result = _result_from_payload(payload_json, model, latency_ms)
            await _awrite_log(
                profile=profile,
                model=model,
                status_code=200,
                error_message=None,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
            )
            return result, None
        error_text = response.text[:2000]
        await _awrite_log(
            profile=profile,
            model=model,
            status_code=response.status_code,
            error_message=error_text,
            latency_ms=latency_ms,
        )
        last_error = OpenRouterAPIError(
            f"OpenRouter returned HTTP {response.status_code}: {error_text}",
            status_code=response.status_code,
        )
        if response.status_code >= 500 and attempt < int(cfg.max_retries):
            continue
        if _should_fallback(response.status_code):
            return None, last_error
        raise last_error
    return None, last_error


def chat(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> ChatResult:
    """Фасад: chat("translation", messages=[...])."""
    if messages is None:
        raise TypeError("chat() missing required argument: 'messages'")
    return OpenRouterClient(profile_name).chat(messages, **overrides)


async def achat(
    profile_name: str | None = None,
    messages: ChatMessages | None = None,
    **overrides: Any,
) -> ChatResult:
    """Асинхронный фасад, зеркало chat()."""
    if messages is None:
        raise TypeError("achat() missing required argument: 'messages'")
    return await AsyncOpenRouterClient(profile_name).chat(messages, **overrides)
