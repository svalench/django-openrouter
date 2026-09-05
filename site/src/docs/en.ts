import type { DocsContent } from './types'

export const en: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter for Django — models, profiles, budgets and request logs managed via the admin',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Search the documentation…',
    searchEmpty: 'Nothing found. Try a different query.',
    onThisPage: 'On this page',
    copied: 'Copied',
    copy: 'Copy',
    editGithub: 'GitHub',
    prev: 'Previous',
    next: 'Next',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Get started in 3 minutes',
    heroGithub: 'Repository',
    builtWith: 'Documentation for',
    license: 'MIT License',
  },
  ui: {
    theme: 'Toggle theme',
    language: 'Language',
    openMenu: 'Open menu',
    closeMenu: 'Close menu',
  },
  sections: [
    {
      id: 'intro',
      group: 'Getting started',
      title: 'Introduction',
      lead: 'A reusable Django app that turns OpenRouter into a managed resource: models, usage profiles, budgets and request logs live in the database and are configured via the admin — no redeploys.',
      blocks: [
        {
          type: 'p',
          text: 'Your product code — translations, chat, summarization — talks to OpenRouter through this library instead of hardcoded keys and model IDs in `settings.py`. An operator picks the active models, sets daily and monthly limits and watches the spend right in the admin.',
        },
        { type: 'h3', text: 'Why not settings.py?' },
        {
          type: 'p',
          text: 'A line like `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` in your settings means a deploy for every model change, budget tweak or emergency shutoff. `django-openrouter` keeps that runtime policy in the database, caches it, and checks limits before every request.',
        },
        {
          type: 'list',
          items: [
            '**Model catalog in the database.** `sync_models` pulls the OpenRouter catalog (`GET /api/v1/models` + `/endpoints`) with prices, p50 TTFT latency, throughput and parameter counts.',
            '**Usage profiles.** A stable slug (`chat`, `translation`) → an ordered model chain, `max_tokens`, `temperature`, limits and budgets.',
            '**Limits before the request.** Daily/monthly request limits and USD budgets are checked before the HTTP call. Exhaustion is an exception, not a silent fallback.',
            '**Streaming (SSE).** `stream()` / `astream()` deliver the response in chunks; enabled with a single checkbox in the settings.',
            '**Every call is logged.** Each attempt is written to the DB, a JSONL file or ClickHouse (pluggable backends) — together with the calling user’s username.',
            '**Safe keys.** The admin API key is encrypted (Fernet, derived from `SECRET_KEY`) and write-only: after saving it can only be replaced or cleared.',
            '**Kill switch & parallelism.** The `enabled` checkbox stops all calls instantly, and `max_parallel_requests` caps concurrent HTTP requests per process.',
          ],
        },
        { type: 'h3', text: 'Features' },
        {
          type: 'table',
          head: ['Feature', 'Status'],
          rows: [
            ['Sync & async clients', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['One-line facades', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Model fallback chains', 'On 402 / 429 / 5xx, in the configured order'],
            ['Transport error retries', 'Configurable `max_retries`'],
            ['Streaming (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, off by default'],
            ['Log backends', 'Database (default), rotating JSONL file, ClickHouse'],
            ['Parallelism cap', '`max_parallel_requests`, default 10'],
            ['Admin in your language', 'Translation catalogs for dozens of locales included'],
            ['Type hints', 'Package ships `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Compatibility',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 and 6.0. Dependencies: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Getting started',
      title: 'Quickstart',
      lead: 'From installation to the first model response — four steps.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Install the package',
              text: 'One command from PyPI: `pip install django-openrouter`.',
            },
            {
              title: 'Wire up the app and middleware',
              text: 'Add `django_openrouter` to `INSTALLED_APPS` and `django_openrouter.middleware.CurrentUserMiddleware` to `MIDDLEWARE`, then run `python manage.py migrate`.',
            },
            {
              title: 'Configure in the admin',
              text: 'Open **OpenRouter → OpenRouter settings**: paste your API key (it will be encrypted) or leave the field empty and set `OPENROUTER_API_KEY` in the environment.',
            },
            {
              title: 'Sync the catalog and create a profile',
              text: 'Run `python manage.py sync_models`, then create a **Usage profile** with the slug `chat`, add models in priority order and optionally make it the default profile.',
            },
          ],
        },
        { type: 'h3', text: '1. Installation' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Wiring and migrations' },
        {
          type: 'code',
          lang: 'python',
          title: 'settings.py',
          code: `INSTALLED_APPS = [
    ...,
    "django_openrouter",
]

MIDDLEWARE = [
    ...,
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_openrouter.middleware.CurrentUserMiddleware",
    ...,
]`,
        },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py migrate` },
        {
          type: 'p',
          text: '`CurrentUserMiddleware` goes **after** `AuthenticationMiddleware` and records the calling user’s username in the request log. Without it every row is stamped `anonymous`.',
        },
        { type: 'h3', text: '3. Configure in Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Open **OpenRouter → OpenRouter settings**. Paste your API key — it is encrypted and never displayed again — or leave the field empty and set `OPENROUTER_API_KEY` in the environment.',
            'Run `python manage.py sync_models` to pull the model catalog (`GET /api/v1/models`).',
            'Create a **Usage profile** (slug `translation`, `chat`, …) and add one or more models in priority order (the first is tried first), plus limits and budgets.',
            'Set the profile as the **default profile** if you want to call `chat(messages=...)` without a name.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Screenshots',
          text: 'All four admin sections — settings, catalog, profiles and the log — are covered with screenshots in the “Admin” section.',
        },
        { type: 'h3', text: '4. First call' },
        {
          type: 'code',
          lang: 'python',
          title: 'views.py',
          code: `from django_openrouter import chat

result = chat(
    "translation",
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)
print(result.content)
print(result.model_used, result.cost_usd, result.latency_ms)`,
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Check without a stored key',
          text: 'The catalog can be synced with a one-off key: `python manage.py sync_models --api-key sk-or-...` — it won’t be saved to the database.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Guides',
      title: 'Configuration',
      lead: 'API key resolution order, the settings.OPENROUTER dictionary and how the runtime config cache works.',
      blocks: [
        { type: 'h3', text: 'Where the API key comes from' },
        {
          type: 'p',
          text: 'If the admin key field is empty, the library looks for a key in this order:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (top-level setting)',
            'the `OPENROUTER_API_KEY` environment variable',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'A key saved in the admin always wins over all three options above. It is stored encrypted (Fernet, derived from `SECRET_KEY`) and is unreadable after saving.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Key', 'Default', 'Description'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'How many seconds to keep the runtime config in the Django cache'],
            ['`CACHE_ALIAS`', '`"default"`', 'Cache alias (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'How many seconds the admin skips re-syncing the model catalog'],
            ['`API_KEY`', 'unset', 'Fallback key if the admin field is empty'],
            ['`HTTP_REFERER`', 'unset', 'The `HTTP-Referer` header (app attribution in OpenRouter)'],
            ['`X_TITLE`', 'unset', 'The `X-Title` header'],
            ['`LOG_BACKENDS`', 'DB only', 'Where request logs are written — see the “Log backends” section'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'settings.py',
          code: `OPENROUTER = {
    "CACHE_TIMEOUT": 60,
    "CATALOG_CACHE_TIMEOUT": 600,
    "CACHE_ALIAS": "default",
    "HTTP_REFERER": "https://my-app.example",
    "X_TITLE": "My App",
}`,
        },
        {
          type: 'p',
          text: 'The stock `LocMemCache` is enough. Redis or Memcached is optional — just point `CACHE_ALIAS` at it.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Settings live in the admin, not in settings.py',
          text: 'Timeout, retry count, the kill switch, streaming (`streaming_enabled`) and the parallel request cap (`max_parallel_requests`) live in the admin’s **OpenRouter settings** — details with a screenshot in the “Admin” section.',
        },
        { type: 'h3', text: 'How the cache works' },
        {
          type: 'p',
          text: 'The client doesn’t read the database directly but a cached `RuntimeConfig` snapshot: settings, active profiles and their fallback models. `post_save` / `post_delete` signals on all app models invalidate the cache instantly — admin edits apply without a restart, and `CACHE_TIMEOUT` is just a safety net.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache and multiple processes',
          text: 'With `LocMemCache` each process keeps its own cache copy: invalidation only happens in the process where you saved in the admin. For multi-process deployments use Redis/Memcached via `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Guides',
      title: 'Usage',
      lead: 'The chat() / achat() / stream() / astream() facades, client classes, per-call overrides and the result structure.',
      blocks: [
        { type: 'h3', text: 'The chat() facade' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # profile slug; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Sync client' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Async call' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# or the class
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: 'The async client mirrors the sync one: ORM operations go through `sync_to_async`, HTTP through `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Streaming (SSE)' },
        {
          type: 'p',
          text: 'Streaming is off by default. Enable **Streaming enabled** in **OpenRouter settings**, then `stream()` and `astream()` deliver the response as `ChatChunk` chunks:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# final chunk: done=True, chunk.result holds the full ChatResult

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` uses the same SSE transport and returns the full `ChatResult`. If streaming is enabled in the settings, a plain `chat()` call also goes over SSE; `stream=False` forces a regular JSON response. Calling with streaming disabled raises `ConfigurationError` before any HTTP request.',
        },
        {
          type: 'table',
          head: ['ChatChunk field', 'Type', 'Description'],
          rows: [
            ['`delta`', '`str`', 'Text of the current chunk'],
            ['`content`', '`str`', 'Text accumulated so far'],
            ['`model_used`', '`str`', 'The model producing the answer'],
            ['`done`', '`bool`', '`True` on the final chunk'],
            ['`result`', '`ChatResult | None`', 'Full result on the final chunk'],
            ['`raw`', '`dict`', 'The raw SSE event'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback and streaming',
          text: 'Falling back to the next model is only possible before the first chunk is emitted. If a model starts streaming and fails mid-way, the error is raised to the caller: part of the answer has already been sent to the client.',
        },
        { type: 'h3', text: 'Per-call overrides' },
        {
          type: 'p',
          text: 'Any `**overrides` are forwarded into the request body. `max_tokens` and `temperature` override the profile values, and `model` temporarily puts the given model first in the chain:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # must exist in the catalog
    response_format={"type": "json_object"},  # any OpenRouter parameter
)`,
        },
        { type: 'h3', text: 'Parallelism' },
        {
          type: 'p',
          text: 'The **Max parallel requests** field in the settings (default `10`, `0` = unlimited) caps the number of concurrent HTTP requests to OpenRouter in the current process — for both `chat()` and `stream()`, sync and async.',
        },
        { type: 'h3', text: 'Result: ChatResult' },
        {
          type: 'table',
          head: ['Field', 'Type', 'Description'],
          rows: [
            ['`content`', '`str`', 'Response text (text parts joined for multipart content)'],
            ['`prompt_tokens`', '`int`', 'Prompt tokens from `usage`'],
            ['`completion_tokens`', '`int`', 'Completion tokens from `usage`'],
            ['`cost_usd`', '`Decimal`', 'Cost: from catalog prices, otherwise `usage.cost` from the API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Catalog cost — for reconciling with billing'],
            ['`model_used`', '`str`', 'The model that actually answered'],
            ['`latency_ms`', '`int`', 'Latency of the successful attempt'],
            ['`raw`', '`dict`', 'Raw JSON response from OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Guides',
      title: 'Model catalog',
      lead: 'How sync_models populates the catalog and what OpenRouterModel stores.',
      blocks: [
        { type: 'h3', text: 'The sync_models command' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # one-off key, never stored` },
        {
          type: 'p',
          text: 'The command upserts the catalog (`GET /api/v1/models`) and enriches it with `/endpoints` metrics — p50 latency and throughput. It never deletes anything: models that disappear from OpenRouter get `is_active=False`. Profiles referencing such a model don’t break — calls simply start failing with `ModelDisabled` until you switch the profile.',
        },
        { type: 'h3', text: 'Model fields' },
        {
          type: 'table',
          head: ['Field', 'Description'],
          rows: [
            ['`model_id`', 'OpenRouter identifier, e.g. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Human-readable name'],
            ['`context_length`', 'Context size in tokens'],
            ['`pricing`', 'JSON with per-token prices: `prompt`, `completion`, optional `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Per-token prices as decimals — for sorting and filtering in the admin'],
            ['`latency_ms`', 'p50 TTFT of the best endpoint, in milliseconds'],
            ['`throughput`', 'p50 throughput of the best endpoint, tokens/s'],
            ['`parameter_count`', 'Approximate weight count (70B → 70000000000), for sorting'],
            ['`parameter_label`', 'Display size with a unit: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'List of supported parameters'],
            ['`modality`', 'Modality, e.g. `text->text`'],
            ['`is_active`', 'Whether the model can be picked in profiles'],
            ['`last_synced_at`', 'When the sync last saw this model'],
            ['`is_free` (property)', '`True` if `prompt`/`completion`/`request` prices are all zero'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Free models only',
          text: 'The profile flag `only_free_models` allows only models with zero price in the catalog — handy for dev stands and demos. It is enforced for both the primary model and every fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Guides',
      title: 'Limits, budgets and fallback',
      lead: 'What is checked before the request, what happens on OpenRouter errors and when fallback kicks in.',
      blocks: [
        { type: 'h3', text: 'Profile limits' },
        {
          type: 'p',
          text: 'Spend is calculated from `RequestLog` for the current calendar day and month (in the active `TIME_ZONE`). An empty (`null`) limit field means “unlimited”.',
        },
        {
          type: 'table',
          head: ['Profile field', 'What it caps', 'Exception'],
          rows: [
            ['`max_requests_per_day`', 'Number of requests per day', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Number of requests per month', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Sum of `cost_usd` per day', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Sum of `cost_usd` per month', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'The check runs in a transaction: the profile row is locked with `select_for_update` and aggregates are computed under that lock — concurrent requests can’t race past a limit.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Limits require DatabaseBackend',
          text: 'Aggregates are computed from the `RequestLog` table, so `DatabaseBackend` must stay in `LOG_BACKENDS` (it is the default). If you remove it, `check_limits()` sees no spend and limits stop working.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'No silent workarounds',
          text: 'Exhausting a limit or a budget is an exception (`BudgetExceeded` / `RateLimitExceeded`) raised before the HTTP call. The library does **not** switch to another model to squeeze the request through.',
        },
        { type: 'h3', text: 'Fallback chain' },
        {
          type: 'p',
          text: 'Fallback models are only engaged when OpenRouter itself returns `402`, `429` or `5xx`. The order is set by the `order` field in the admin; duplicates in the chain are dropped. Models disallowed by profile rules (inactive, or non-free with `only_free_models`) are skipped.',
        },
        {
          type: 'list',
          items: [
            '**Transport errors and 5xx** — retried up to `max_retries` times on the same model, then fallback.',
            '**402 / 429** — immediately move to the next model in the chain.',
            '**Other 4xx** (e.g. 400) — raised immediately, no fallback: the request is likely invalid for all models.',
            '**Every attempt** — including failed ones — is written to the log.',
          ],
        },
        { type: 'h3', text: 'Global kill switch' },
        {
          type: 'p',
          text: 'The `enabled` checkbox in **OpenRouter settings** stops everything instantly: any `chat()` call raises `OpenRouterDisabled` before limits are even checked. Handy for incidents and planned maintenance.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Guides',
      title: 'Log backends',
      lead: 'Every HTTP call is written to all backends listed in OPENROUTER["LOG_BACKENDS"]: the project database, a JSONL file, ClickHouse — or your own class.',
      blocks: [
        {
          type: 'p',
          text: 'Each entry in the list is either a dotted path to a class (default settings) or a dict with a `BACKEND` key plus parameters. If `LOG_BACKENDS` is unset, logs are written only to the project database (`RequestLog`).',
        },
        {
          type: 'code',
          lang: 'python',
          title: 'settings.py',
          code: `OPENROUTER = {
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
}`,
        },
        { type: 'h3', text: 'DatabaseBackend (default)' },
        {
          type: 'p',
          text: 'Writes rows to the `RequestLog` model. Daily/monthly limits and budgets aggregate from this table — keep this backend enabled if you use limits: without it `check_limits()` sees no spend.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines to a file with size-based rotation (`RotatingFileHandler`): one line = one JSON object with `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username` fields.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Inserts `FORMAT JSONEachRow` over the ClickHouse HTTP interface. No extra dependencies — the same `httpx` is used. Database and table names are validated as identifiers to prevent injection. Create the table like this:',
        },
        {
          type: 'code',
          lang: 'bash',
          title: 'clickhouse',
          code: `CREATE TABLE analytics.openrouter_request_log
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
ORDER BY (created_at, profile);`,
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Best-effort',
          text: 'Every configured backend receives every record, and a backend failure (full disk, unreachable ClickHouse) never breaks `chat()` — the error is logged to the `django_openrouter` logger.',
        },
        { type: 'h3', text: 'Who made the request' },
        {
          type: 'p',
          text: 'Every record carries the username of the Django user who made the call. It is supplied by `django_openrouter.middleware.CurrentUserMiddleware` (after `AuthenticationMiddleware`). Calls without a user or outside an HTTP request are logged as `anonymous`. In Celery and management commands set the name manually:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Custom backend' },
        {
          type: 'p',
          text: 'Subclass `django_openrouter.log_backends.LogBackend`, implement `write()` (and optionally `awrite()`), and add the class’s dotted path to `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Guides',
      title: 'The admin',
      lead: 'All runtime policy lives in four Django admin sections: settings, the model catalog, usage profiles and request logs.',
      blocks: [
        {
          type: 'table',
          head: ['Section', 'What it does'],
          rows: [
            ['**OpenRouter settings**', 'Kill switch, encrypted API key, streaming, timeouts'],
            ['**OpenRouter models**', 'The catalog from OpenRouter: price, latency, throughput'],
            ['**Usage profiles**', 'Model chain, limits, budgets, spend statistics'],
            ['**Request logs**', 'Tokens, cost and latency of every call (read-only)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'A singleton: the changelist redirects to the single row, and it cannot be deleted. All global integration settings are collected here:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — the global kill switch. Off → every `chat()` / `stream()` raises `OpenRouterDisabled`.',
            '**API key** — write-only, encrypted with Fernet derived from `SECRET_KEY`. An empty field keeps the current key; a new value replaces it; the **Clear stored API key** checkbox wipes the key from the database — then `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]` is used.',
            '**Base URL** — the OpenRouter API root (`https://openrouter.ai/api/v1`).',
            '**Default profile** — the profile used when `chat(messages=...)` is called without a name.',
            '**Request timeout** / **Max retries** — HTTP timeout and retry count on transport/5xx errors before moving to the next model in the chain.',
            '**Streaming enabled** — allows SSE via `stream()` / `astream()` and `chat(stream=True)`. Off by default.',
            '**Max parallel requests** — cap on concurrent HTTP calls in this process (`0` = unlimited).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings: enabled, key status, base url, default profile, timeout, retries, streaming, parallelism cap',
          caption: 'OpenRouter settings: kill switch, write-only API key, default profile, timeouts, streaming and the parallelism cap.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'The catalog from `GET /api/v1/models` plus `/endpoints` metrics (latency and throughput). Rows can’t be added or deleted by hand, and the model card is read-only.',
        },
        {
          type: 'list',
          items: [
            '**Columns:** name, `latency_ms` (p50 TTFT), throughput (tokens/s), prompt/completion prices per 1M tokens, weight size (`70B` / `8x7B`), `is_active`. Click-to-sort with empty values always last.',
            '**Filters:** activity, modality, price (free / < $1 / $1–10 / ≥ $10 per 1M), speed (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (action) — upserts the catalog; disappeared models get `is_active=False`.',
            '**Assign to usage profile…** (action) — appends the selected models to the end of a profile’s chain; duplicates, inactive and non-free models (with `only_free_models`) are skipped with a report.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'On first open the list is refreshed from the API, then served from the database for 10 minutes (`CATALOG_CACHE_TIMEOUT`). The same sync from the console: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — OpenRouter model catalog: name, latency, throughput, price per 1M, weight size, activity; filters on the right',
          caption: 'Model catalog: sort by price/latency, filter by price and speed, sync and assign-to-profile actions.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'A profile is the slug your code passes (`chat`, `translation`, …) plus an ordered list of models: the first is tried first, the rest fall back on `402` / `429` / `5xx`. Exhausted limits raise an exception instead of silently switching models.',
        },
        {
          type: 'list',
          items: [
            '**Profile list:** name, primary model, activity, only-free, daily request/budget limits and aggregates from the log — request count, average and total latency, average and total cost (one GROUP BY per page).',
            '**Form:** `max_tokens`, `temperature` (0–2), daily/monthly request and USD limits (empty = unlimited), **only free models**, **is active**.',
            '**Models (priority order) inline:** autocomplete over the catalog — price and latency are shown in the label, and the same price/speed filters as in the catalog apply. Order is renormalized on save, and the first model in the chain is synced to the `model` field.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — usage profile list with request, latency and cost aggregates',
          caption: 'Usage profiles: model chain, limits and spend aggregates right in the list.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'A read-only log. Every HTTP attempt (including fallbacks and errors) becomes a row when `DatabaseBackend` is enabled (the default). Daily and monthly limits aggregate from this table.',
        },
        {
          type: 'list',
          items: [
            '**Columns:** time, username, profile, model, HTTP status, prompt/completion tokens, cost, latency.',
            '**Summary above the table:** request count and total USD for the current filter. Filters: profile, status, date; search over the error text and username.',
            '**Username** is supplied by `CurrentUserMiddleware`; without it rows are stamped `anonymous`. In Celery and management commands — `bound_username("worker")` (see “Log backends”).',
            '**Permissions:** the separate `view_usage_logs` permission lets you give support staff access to spend without access to settings.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — request log: time, username, profile, model, status, tokens, cost, latency; summary on top',
          caption: 'Request logs: every attempt with tokens, cost and latency, with a filter summary above the table.',
        },
        { type: 'h3', text: 'API key protection' },
        {
          type: 'list',
          items: [
            '**Encryption.** The `api_key` field is an `EncryptedTextField`: Fernet, key derived from `SECRET_KEY`.',
            '**Write-only.** After saving, the value cannot be viewed — only replaced or cleared.',
            '**Database-free alternative.** The key can live only in the environment (`OPENROUTER_API_KEY`), leaving the admin field empty.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Rotating SECRET_KEY',
          text: 'The Fernet key is derived from `SECRET_KEY`. Changing `SECRET_KEY` makes API keys stored in the database unreadable — they will have to be entered again.',
        },
        { type: 'h3', text: 'Validations' },
        {
          type: 'list',
          items: [
            '`temperature` — only within 0…2.',
            'Primary and fallback models must be active.',
            'With `only_free_models`, all models in the profile must be free.',
            'The `(profile, model)` pair in the fallback chain is unique.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Reference',
      title: 'API Reference',
      lead: 'Public imports from django_openrouter: facades, clients, the result and exceptions.',
      blocks: [
        { type: 'h3', text: 'chat() / achat()' },
        {
          type: 'code',
          lang: 'python',
          title: 'django_openrouter',
          code: `def chat(
    profile_name: str | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    **overrides: Any,
) -> ChatResult: ...

async def achat(
    profile_name: str | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    **overrides: Any,
) -> ChatResult: ...

def stream(
    profile_name: str | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    **overrides: Any,
) -> Iterator[ChatChunk]: ...

async def astream(
    profile_name: str | None = None,
    messages: Sequence[Mapping[str, Any]] | None = None,
    **overrides: Any,
) -> AsyncIterator[ChatChunk]: ...`,
        },
        {
          type: 'p',
          text: '`profile_name=None` uses the default profile from the settings. Calling without `messages` is a `TypeError`. If the profile is not found or inactive — `ConfigurationError`.',
        },
        { type: 'h3', text: 'OpenRouterClient / AsyncOpenRouterClient' },
        {
          type: 'code',
          lang: 'python',
          code: `class OpenRouterClient:
    def __init__(self, profile_name: str | None = None) -> None: ...
    def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult: ...
    def stream(self, messages: ChatMessages, **overrides: Any) -> Iterator[ChatChunk]: ...

class AsyncOpenRouterClient:
    def __init__(self, profile_name: str | None = None) -> None: ...
    async def chat(self, messages: ChatMessages, **overrides: Any) -> ChatResult: ...
    def stream(self, messages: ChatMessages, **overrides: Any) -> AsyncIterator[ChatChunk]: ...`,
        },
        { type: 'h3', text: 'ChatResult' },
        {
          type: 'code',
          lang: 'python',
          code: `@dataclass(frozen=True)
class ChatResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    catalog_cost_usd: Decimal | None
    model_used: str
    latency_ms: int
    raw: dict[str, Any]`,
        },
        { type: 'h3', text: 'ChatChunk' },
        {
          type: 'code',
          lang: 'python',
          code: `@dataclass(frozen=True)
class ChatChunk:
    delta: str                      # text of the current chunk
    content: str                    # accumulated response text
    model_used: str = ""
    done: bool = False              # True on the final chunk
    result: ChatResult | None = None  # full result on the final chunk
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: 'Exceptions' },
        {
          type: 'table',
          head: ['Exception', 'When'],
          rows: [
            ['`OpenRouterError`', 'Base class of all library exceptions'],
            ['`ConfigurationError`', 'No key, profile or default profile; streaming is disabled'],
            ['`OpenRouterDisabled`', 'Kill switch: `enabled=False` in the settings'],
            ['`ModelDisabled`', 'Profile/model is inactive or violates `only_free_models`'],
            ['`RateLimitExceeded`', 'Daily/monthly request limit exhausted'],
            ['`BudgetExceeded`', 'Daily/monthly budget exhausted'],
            ['`OpenRouterAPIError`', 'API error after retries and fallback; carries `status_code`'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'error handling',
          code: `from django_openrouter import chat
from django_openrouter.exceptions import (
    BudgetExceeded,
    OpenRouterAPIError,
    RateLimitExceeded,
)

try:
    result = chat("chat", messages=messages)
except (BudgetExceeded, RateLimitExceeded):
    show_quota_page()
except OpenRouterAPIError as exc:
    log.warning("openrouter failed: %s (status=%s)", exc, exc.status_code)`,
        },
        { type: 'h3', text: 'UsageProfile.get_usage()' },
        {
          type: 'code',
          lang: 'python',
          code: `stats = profile.get_usage("day")    # or "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # period start (datetime)`,
        },
        {
          type: 'p',
          text: 'Safe to call both inside and outside `transaction.atomic()` — the wrapper is created automatically. The lock is taken on the profile row, not on the logs, so a growing `RequestLog` table doesn’t blow up locking.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Reference',
      title: 'FAQ',
      lead: 'Frequent questions and pitfalls.',
      blocks: [
        { type: 'h3', text: 'Admin changes don’t apply' },
        {
          type: 'p',
          text: 'Most likely you run multiple processes with `LocMemCache`: cache invalidation only happened in the process where you clicked “Save”. Switch to Redis/Memcached and set the alias in `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '“No usage profile specified and default_profile is not set”' },
        {
          type: 'p',
          text: 'You called `chat()` without a profile name and no default profile is set. Either pass the slug as the first argument or pick a **default profile** in **OpenRouter settings**.',
        },
        { type: 'h3', text: '“Usage profile X is not found or inactive”' },
        {
          type: 'p',
          text: 'There is no profile with that slug, or its `is_active` checkbox is off. Only active profiles make it into the runtime config.',
        },
        { type: 'h3', text: 'Is streaming supported?' },
        {
          type: 'p',
          text: 'Yes. Enable **Streaming enabled** in **OpenRouter settings** and use `stream()` / `astream()` or `chat(stream=True)`. With streaming enabled, a plain `chat()` also goes over SSE; `stream=False` forces a JSON response.',
        },
        { type: 'h3', text: 'Limits don’t trigger' },
        {
          type: 'p',
          text: 'Check that `django_openrouter.log_backends.DatabaseBackend` is in `OPENROUTER["LOG_BACKENDS"]` (it is by default): limits and budgets aggregate from the `RequestLog` table, and without this backend spend is invisible to the checks.',
        },
        { type: 'h3', text: 'How do I get the admin in my language?' },
        {
          type: 'p',
          text: 'All admin labels are wrapped in `gettext_lazy`, and translation catalogs for dozens of locales ship in the package (`locale/<django_locale>/LC_MESSAGES/django.po`). The host project decides which languages are active: configure `LANGUAGE_CODE` / `LANGUAGES` and wire up `LocaleMiddleware`. After editing `.po` files, compile the catalogs — `python manage.py compilemessages -l ru`. Note: English in the package is `en_GB` / `en-gb`; there is no base `en` catalog.',
        },
        { type: 'h3', text: 'How do I compute spend manually?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Can I use it without the admin?' },
        {
          type: 'p',
          text: 'No — that’s the point of the library: policy (models, limits, budgets) lives in the database and is managed by an operator. The key, however, can live only in the environment.',
        },
      ],
    },
  ],
}
