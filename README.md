# django-openrouter

[![PyPI](https://img.shields.io/pypi/v/django-openrouter.svg)](https://pypi.org/project/django-openrouter/)
[![Python](https://img.shields.io/pypi/pyversions/django-openrouter.svg)](https://pypi.org/project/django-openrouter/)
[![CI](https://github.com/svalench/django-openrouter/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/svalench/django-openrouter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/svalench/django-openrouter/blob/master/LICENSE)

Reusable Django application for managing [OpenRouter](https://openrouter.ai) models, usage profiles, budgets and request logs from Django admin.

Your product code (translation, chat, summarization, …) talks to OpenRouter through this library instead of hardcoded `settings.py` keys and model ids. An operator picks active models, sets daily/monthly limits, and inspects spend in admin.

**Documentation:** https://svalench.github.io/django-openrouter/

Requires Python 3.11+ and Django 4.2+ (subject to Django's Python compatibility).
This is a third-party integration, not an official OpenRouter SDK.

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

### 4. Call from your Django application

After configuring the `chat` profile, run this in a view, task, or
`python manage.py shell`:

```python
from django_openrouter import chat

result = chat("chat", messages=[{"role": "user", "content": "Hello"}])
print(result.content)
print(result.model_used, result.cost_usd, result.latency_ms)
```

This makes a real API request and may incur provider charges. To try the
integration without an API key or provider calls, run the mocked tests in
[Contributing](https://github.com/svalench/django-openrouter/blob/master/CONTRIBUTING.md).
See [Usage](#usage) for async clients, streaming, and fallback behavior.

Screenshots: [`docs/img/`](https://github.com/svalench/django-openrouter/tree/master/docs/img).

## Admin pages

Four models under **OpenRouter**. Runtime policy lives here, not in `settings.py`.

| Page | What it does |
| --- | --- |
| [OpenRouter settings](#openrouter-settings) | Kill switch, encrypted API key, streaming, timeouts |
| [OpenRouter models](#openrouter-models) | Catalog from OpenRouter: price, latency, throughput |
| [Usage profiles](#usage-profiles) | Ordered model chain, limits, budgets, spend stats |
| [Request logs](#request-logs) | Per-call tokens, cost, latency (read-only) |

### OpenRouter settings

Singleton: the changelist redirects to the only row. The row cannot be deleted.

![OpenRouter settings](https://raw.githubusercontent.com/svalench/django-openrouter/master/docs/img/settings.png)

- **Enabled** — global kill switch. Off → every `chat()` / `stream()` fails.
- **API key** — write-only, Fernet-encrypted from `SECRET_KEY`. After save the value cannot be viewed. Blank keeps the stored key; a new value replaces it. **Clear stored API key** wipes the DB key so the process falls back to `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`.
- **Base URL** — OpenRouter API root (`https://openrouter.ai/api/v1`).
- **Default profile** — used when `chat(messages=...)` omits a profile name.
- **Request timeout** / **Max retries** — HTTP timeout and retries on transport / 5xx before the next model in the chain.
- **Streaming enabled** — allows SSE via `stream()` / `astream()` and `chat(stream=True)`. Off by default.
- **Max parallel requests** — cap on concurrent HTTP calls in this process (`0` = unlimited).

### OpenRouter models

Catalog from `GET /api/v1/models` (plus `/endpoints` for latency/throughput). Rows cannot be added or deleted by hand; the detail page is read-only.

![OpenRouter models](https://raw.githubusercontent.com/svalench/django-openrouter/master/docs/img/models.png)

Columns: name, `latency_ms` (p50 TTFT), throughput (tok/s), prompt/completion price per 1M tokens, parameter size (`70B` / `8x7B`), `is_active`. Click a column to sort (nulls last).

Filters: active, modality, price (free / cheap &lt; $1 / mid $1–10 / expensive), speed (&lt; 400 ms / 400–1200 / ≥ 1200).

Actions:

- **Sync catalog with OpenRouter** — upsert; models missing remotely get `is_active=False`.
- **Assign to usage profile…** — append selected models to a profile chain (skips duplicates, inactive, and paid models when the profile has `only_free_models`).

The changelist refreshes from the API on first view, then serves the database for 10 minutes (`CATALOG_CACHE_TIMEOUT`). Same sync: `python manage.py sync_models`.

### Usage profiles

A profile is the slug your code passes (`chat`, `translation`, …) plus an ordered model list (first is tried first; later rows are fallback on `402` / `429` / `5xx`). Exhausted limits/budgets raise; they do not silently fall back.

![Usage profiles](https://raw.githubusercontent.com/svalench/django-openrouter/master/docs/img/profiles.png)

Changelist: name, primary model, active, only-free, daily request/budget caps, and aggregates from logs (request count, avg/total latency, avg/total cost).

On the form: `max_tokens`, `temperature` (0–2), daily/monthly request and USD limits (blank = unlimited), **only free models**, **is active**. Inline **Models (priority order)** uses catalog autocomplete (price + latency in the label; same price/speed query filters as the catalog). Saving syncs the first chain item into `model`.

### Request logs

Read-only. Every HTTP attempt (including fallbacks and errors) is a row when `DatabaseBackend` is enabled (the default). Daily/monthly limits are aggregated from this table.

![Request logs](https://raw.githubusercontent.com/svalench/django-openrouter/master/docs/img/logs.png)

Columns: time, username, profile, model, HTTP status, prompt/completion tokens, cost, latency. Above the table: request count and USD total for the current filter. Filters: profile, status, date.

Username comes from `django_openrouter.middleware.CurrentUserMiddleware` (after `AuthenticationMiddleware`). Without it, rows show `anonymous`. In Celery / management commands use `bound_username("worker")`.

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

`model=` can reorder only models already configured in that profile; it cannot introduce a model outside the profile chain.

Profiles with limits atomically reserve a request slot before each HTTP attempt. For budgets, the reservation uses the model's full context window at the higher of its catalog prompt/completion token prices, plus any per-request price; on successful completion the row is reconciled to reported usage. This deliberately rejects calls when the remaining budget cannot cover that worst case, even if the likely response would be cheap. A budgeted model needs valid catalog prices and a context length, and currently must be text-to-text with no image charge. Failed or interrupted calls retain their reservation because their final charge may be unknown; inspect the request log and provider billing before manually correcting these rows. Provider-side limits remain advisable because catalog pricing or provider charges can change independently of this package.

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

Catalog refresh, price/speed columns and profile autocomplete filters are described under [Admin pages](#admin-pages).

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

- **DatabaseBackend** writes to the `RequestLog` model. Daily/monthly request limits and budgets are aggregated from that table. Profiles with limits raise `ConfigurationError` if this backend is not configured.
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

## Contributing

See [CONTRIBUTING.md](https://github.com/svalench/django-openrouter/blob/master/CONTRIBUTING.md)
for a local test setup, lint/type checks, and distribution validation.
Bug reports should include a minimal reproduction and version information,
never real API keys or private request data.
