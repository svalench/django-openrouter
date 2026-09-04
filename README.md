# django-openrouter

Reusable Django application for managing [OpenRouter](https://openrouter.ai) models, usage profiles, budgets and request logs from Django admin.

Your product code (translation, chat, summarization, …) talks to OpenRouter through this library instead of hardcoded `settings.py` keys and model ids. An operator picks active models, sets daily/monthly limits, and inspects spend in admin.

## Why not `settings.py`?

Hardcoding `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` means a deploy to change models, budgets or a kill switch. `django-openrouter` stores that runtime policy in the database, caches it, and enforces limits before every request.

API keys stored in admin are encrypted in the database (Fernet, key derived from `SECRET_KEY`) and are write-only: after save the value cannot be viewed, only replaced or cleared. Keys can still come from the environment (`OPENROUTER_API_KEY`) if you prefer not to keep them in the database.

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
MIDDLEWARE = [
    ...,
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_openrouter.middleware.CurrentUserMiddleware",
    ...,
]
```

```bash
python manage.py migrate
```

### 3. Configure in Django admin

1. Open **OpenRouter → OpenRouter settings**. Paste an API key (it is encrypted and cannot be viewed after save) *or* leave it empty and set `OPENROUTER_API_KEY` in the environment.
2. Run `python manage.py sync_models` to pull the model catalog (`GET /api/v1/models`).
3. Create a **Usage profile** (slug `translation`, `chat`, …), add one or more models in priority order (first is tried first), plus limits and budgets.
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

Streaming is off by default. Turn on **Streaming enabled** in OpenRouter settings, then iterate chunks:

```python
from django_openrouter import stream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)
```

`chat(..., stream=True)` uses the same SSE transport and returns a complete `ChatResult`. With streaming enabled, `chat()` (without `stream=False`) also talks SSE. `stream=False` forces a regular JSON response.

Async: `astream("chat", messages=...)` / `AsyncOpenRouterClient("chat").stream(...)`.

**Max parallel requests** (default 10, `0` = unlimited) caps concurrent HTTP calls to OpenRouter in the current process — both `chat()` and `stream()`, sync and async.

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
| `CATALOG_CACHE_TIMEOUT` | `600` | Seconds to skip re-fetching the admin model catalog |
| `API_KEY` | unset | Fallback API key if the admin field is empty |
| `HTTP_REFERER` | unset | Sent as `HTTP-Referer` (OpenRouter app attribution) |
| `X_TITLE` | unset | Sent as `X-Title` |
| `LOG_BACKENDS` | DB only | Where request logs are written; see below |

Also accepted, in this order, when the admin API key is empty:

1. `settings.OPENROUTER["API_KEY"]`
2. `settings.OPENROUTER_API_KEY`
3. Environment variable `OPENROUTER_API_KEY`

Example:

```python
OPENROUTER = {
    "CACHE_TIMEOUT": 60,
    "CATALOG_CACHE_TIMEOUT": 600,
    "CACHE_ALIAS": "default",
    "HTTP_REFERER": "https://my-app.example",
    "X_TITLE": "My App",
}
```

The default cache backend (`LocMemCache`) is enough. Redis/Memcached are optional.

The **OpenRouter models** changelist pulls `GET /api/v1/models` (and per-model `/endpoints` for latency/throughput) on first view, then serves the database for 10 minutes (`CATALOG_CACHE_TIMEOUT`). Columns: name, response time (`latency_ms`), load (`throughput` tok/s), price per 1M tokens. Click a column to sort (nulls last). Sidebar filters: price buckets and speed (latency). The same price/speed info appears in the usage-profile model autocomplete; filter dropdowns on the profile form pass `price` / `speed` query params to that autocomplete.

## Request logging backends

Every HTTP call (including failed attempts and fallbacks) is logged through the backends listed in `OPENROUTER["LOG_BACKENDS"]`. An entry is either a dotted path (defaults apply) or a dict with a `BACKEND` key plus options:

```python
OPENROUTER = {
    "LOG_BACKENDS": [
        # 1. Project database (default): writes RequestLog rows.
        "django_openrouter.log_backends.DatabaseBackend",
        # 2. JSON Lines file with size-based rotation.
        {
            "BACKEND": "django_openrouter.log_backends.FileBackend",
            "PATH": "/var/log/myapp/openrouter-requests.jsonl",
            "MAX_BYTES": 10 * 1024 * 1024,  # rotate at 10 MB
            "BACKUP_COUNT": 5,
        },
        # 3. ClickHouse over its HTTP interface (uses httpx, no extra deps).
        {
            "BACKEND": "django_openrouter.log_backends.ClickHouseBackend",
            "URL": "http://localhost:8123",
            "DATABASE": "analytics",
            "TABLE": "openrouter_request_log",
            "USERNAME": "logger",
            "PASSWORD": "secret",
        },
    ],
}
```

All configured backends receive every record. Logging is **best-effort**: a failing backend (full disk, unreachable ClickHouse) never breaks `chat()` — the error is logged to the `django_openrouter` logger.

Backend-specific notes:

- **DatabaseBackend** writes to the `RequestLog` model. Daily/monthly request limits and budgets are aggregated from that table, so keep this backend enabled if you use limits; without it `check_limits()` sees no usage.
- **FileBackend** uses `logging.handlers.RotatingFileHandler`; the line format is one JSON object per request with `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.
- **ClickHouseBackend** inserts `FORMAT JSONEachRow` per request. Create a table like:

```sql
CREATE TABLE analytics.openrouter_request_log
(
    created_at DateTime,
    profile String,
    model String,
    status_code UInt16,
    error_message String,
    prompt_tokens UInt32,
    completion_tokens UInt32,
    cost_usd Decimal(20, 10),
    latency_ms UInt32,
    username String
)
ENGINE = MergeTree
ORDER BY (created_at, profile);
```

Each log row stores the Django username that triggered the call. Add `django_openrouter.middleware.CurrentUserMiddleware` **after** `AuthenticationMiddleware`. Unauthenticated (or non-HTTP) calls are logged as `anonymous`. In Celery / management commands:

```python
from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])
```

You can also point `LOG_BACKENDS` at your own subclass of `django_openrouter.log_backends.LogBackend` (implement `write()`, optionally `awrite()`).

## Limits

Usage is aggregated from `RequestLog` for the current calendar day and month (`UsageProfile.get_usage("day"|"month")`). Null limit fields mean “unlimited”.

## Internationalization

Admin labels (filters, help texts, verbose names) are wrapped in `gettext_lazy`.
Catalogs live in `src/django_openrouter/locale/<django_locale>/LC_MESSAGES/django.po`.

The host project decides which languages are active. Example:

```python
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", _("Русский")),
    ("uk", _("Українська")),
    ("pl", _("Polski")),
    ("be", _("Беларуская")),
    ("en-gb", _("English")),
    ("de", _("Deutsch")),
    ("fr", _("Français")),
    ("es", _("Español")),
    ("zh-hans", _("简体中文")),
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # after SessionMiddleware
    ...
]
```

Django language codes (`zh-hans`) map to gettext dirs (`zh_Hans`). English in this
package is `en_GB` / `en-gb` — there is no base `en` catalog.

Compile after editing `.po` files:

```bash
msgfmt -o src/django_openrouter/locale/ru/LC_MESSAGES/django.mo \
        src/django_openrouter/locale/ru/LC_MESSAGES/django.po
```

Or from a Django project that has this app on `INSTALLED_APPS`:

```bash
python manage.py compilemessages -l ru
```

`.mo` files are not generated automatically; without them admin stays in English
even if `LANGUAGE_CODE` is set.

## License

MIT
