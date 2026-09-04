# django-openrouter

Reusable Django application for managing [OpenRouter](https://openrouter.ai) models, usage profiles, budgets and request logs from Django admin.

Your product code (translation, chat, summarization, …) talks to OpenRouter through this library instead of hardcoded `settings.py` keys and model ids. An operator picks active models, sets daily/monthly limits, and inspects spend in admin.

## Why not `settings.py`?

Hardcoding `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` means a deploy to change models, budgets or a kill switch. `django-openrouter` stores that runtime policy in the database, caches it, and enforces limits before every request.

API keys can still come from the environment (`OPENROUTER_API_KEY`) if you prefer not to keep them in the database.

## Quickstart

### 1. Install

```bash
pip install django-openrouter
```

### 2. Enable the app and migrate

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "django_openrouter",
]
```

```bash
python manage.py migrate
```

### 3. Configure in Django admin

1. Open **OpenRouter → OpenRouter settings**. Paste an API key *or* leave it empty and set `OPENROUTER_API_KEY` in the environment.
2. Run `python manage.py sync_models` to pull the model catalog (`GET /api/v1/models`).
3. Create a **Usage profile** (slug `translation`, `chat`, …), pick a model, optional fallbacks, limits and budgets.
4. Set that profile as **default profile** if you want `chat(messages=...)` without a name.

## Usage

```python
from django_openrouter import chat

result = chat(
    "translation",
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)
print(result.content)
print(result.model_used, result.cost_usd, result.latency_ms)
```

Sync client:

```python
from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])
```

Async:

```python
from django_openrouter import achat

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])
```

If a profile’s limit or budget is exhausted, `chat()` raises `BudgetExceeded` or `RateLimitExceeded` and **does not** silently fall back. Fallback models are only used when OpenRouter returns `402`, `429` or `5xx`.

Streaming (`stream=True`) raises `NotImplementedError` in this MVP.

## Management command

```bash
python manage.py sync_models
python manage.py sync_models --api-key sk-or-...
```

Upserts the catalog, never deletes rows, and sets `is_active=False` on models that disappeared from OpenRouter.

## `settings.OPENROUTER`

| Key | Default | Description |
| --- | --- | --- |
| `CACHE_TIMEOUT` | `60` | Seconds to keep runtime config in Django’s cache |
| `CACHE_ALIAS` | `"default"` | Cache alias (`django.core.cache`) |
| `API_KEY` | unset | Fallback API key if the admin field is empty |
| `HTTP_REFERER` | unset | Sent as `HTTP-Referer` (OpenRouter app attribution) |
| `X_TITLE` | unset | Sent as `X-Title` |

Also accepted, in this order, when the admin API key is empty:

1. `settings.OPENROUTER["API_KEY"]`
2. `settings.OPENROUTER_API_KEY`
3. Environment variable `OPENROUTER_API_KEY`

Example:

```python
OPENROUTER = {
    "CACHE_TIMEOUT": 60,
    "CACHE_ALIAS": "default",
    "HTTP_REFERER": "https://my-app.example",
    "X_TITLE": "My App",
}
```

The default cache backend (`LocMemCache`) is enough. Redis/Memcached are optional.

## Limits

Usage is aggregated from `RequestLog` for the current calendar day and month (`UsageProfile.get_usage("day"|"month")`). Null limit fields mean “unlimited”.

## License

MIT
