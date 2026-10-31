# Changelog

## 0.7.0 — 2026-10-31

OpenTelemetry tracing, request-log grouping, a staff usage dashboard, and an optional Pydantic AI model ship together. There is no 0.6.0 release. Upgrade from 0.5.1 with `manage.py migrate` (`0011_requestlog_grouping`, then `0012_requestlog_model_created_idx`).

### OpenTelemetry and log grouping

- Extra `django-openrouter[otel]` (`opentelemetry-api` only). The SDK and exporter stay in the host project. If the package is missing, calls do not import it.
- Spans stay off until `OPENROUTER["OTEL"]` is true. A parent span covers `chat()`, `achat()`, `stream()`, `astream()`, `transcribe()`, `atranscribe()`, `generate_image()` and `agenerate_image()`. Each HTTP attempt, including retries and fallbacks, is a child span and nests under an active Django or Celery span.
- Attributes follow the GenAI conventions (`gen_ai.system=openrouter`, operation, request and response model, token counts, finish reasons) plus `openrouter.cost_usd`, profile, fallback index, retry index, status, latency, username, `session_id` and `trace_id`. Streams record time to first token and keep the parent span open until the generator finishes. `BudgetExceeded`, `RateLimitExceeded`, timeouts and an interrupted stream (`499`) are span errors.
- Prompt and completion text is omitted unless `OPENROUTER["OTEL_CAPTURE_CONTENT"]` is true. `OTEL_CONTENT_REDACTOR` is a dotted path `fn(text, *, kind) -> str`. API keys and `Authorization` headers are never span attributes.
- `RequestLog` gains nullable indexed `trace_id` and `session_id`, and nullable JSON `metadata` (migration `0011_requestlog_grouping`). One call shares a `trace_id` across retries and fallbacks: the OpenTelemetry trace id when a span is recording, otherwise a generated id. `session_id=` and `metadata=` on a chat call are sent to OpenRouter and stored on the log. `trace_id=` and `trace=` (extra span attributes) stay local. `bound_session()` works like `bound_username()`. File and ClickHouse rows include the three fields (`metadata` is a JSON string). The admin log filters and searches by session or trace; a row links to the other calls in that session or trace.

### Usage dashboard

- **Usage dashboard** is on the OpenRouter admin index and in the request-log summary. Default path: `/admin/django_openrouter/requestlog/dashboard/`. The route is `RequestLogAdmin.get_urls` wrapped in `admin_view`, so a custom `AdminSite` that registers `RequestLog` serves the same page. Access matches the log: superuser or `django_openrouter.view_usage_logs`.
- Day view buckets by hour (at most 7 days). Month view buckets by day (at most 366 days). Filter by date range, profile and model.
- Charts use vendored Chart.js 4.4.6 (MIT, no CDN, no inline script). Series data is embedded with `json_script`. Cost, request count, error rate, average and p95 latency, and average and p95 tokens are shown overall and grouped by profile and by model. Headline cards compare the window with the previous window of the same length. Non-2xx statuses count as errors, including 402, 429, 499, 5xx and in-flight reservations (status 0).
- Totals sit next to each profile’s current daily and monthly request and USD limits. p95 is computed in Python from at most 20,000 of the newest rows. Migration `0012_requestlog_model_created_idx` adds a `(model, created_at)` index and depends on `0011`. It does not change `trace_id`, `session_id` or `metadata`.

### Pydantic AI

- Extra `django-openrouter[pydantic-ai]` (`pydantic-ai>=2.64`). `django_openrouter` does not import it. `OpenRouterProfileModel` raises `ImportError` with the install hint when the extra is missing.
- `OpenRouterProfileModel("chat")` is a Pydantic AI `Model`. It sends chat-completions payloads through `AsyncOpenRouterClient`, so the profile chain, fallback on `402` / `408` / `429` / `5xx`, budget reservations, rate limits, retries, timeouts, the kill switch, the request log and `bound_username` stay in this library.
- Text, multiple tool calls and tool-result round trips, structured output (`output_type`, including `NativeOutput` / `PromptedOutput`), `Agent.run` / `run_sync` / `run_stream`. Agent `temperature` and `max_tokens` are capped by the profile. `thinking` is forwarded as OpenRouter `reasoning`. Image inputs are sent as `image_url` parts.
- `BudgetExceeded` and `RateLimitExceeded` are raised to the agent caller and do not fall through to a model outside the profile chain. Token counts and cost are copied onto Pydantic AI `RequestUsage` / `RunUsage.cost`.
- `Agent.run(conversation_id=...)` is stored as `session_id` and sent on the chat body, unless `bound_session()` is already active — that session and its metadata win. The adapter does not set `trace_id`, so an active OpenTelemetry span (including `Agent(instrument=True)`) becomes the log trace id.

## 0.5.1 — 2026-10-22

Fix chat calls failing when OpenRouter compresses the response body.

- `chat()`, `achat()`, `generate_image()` and `agenerate_image()` read the body with `iter_bytes()` / `aiter_bytes()` so a wall-clock deadline can close that response. Those iterators already remove `Content-Encoding`. Rebuilding an `httpx.Response` with the original header made `.json()` decompress the bytes again (`Error -3 while decompressing data: incorrect header check` for gzip, and the brotli equivalent for `br`). The decoded bytes are parsed directly.
- `stream()` / `astream()` already consumed the decoded SSE text and were not inflated twice. Regression tests cover gzip, brotli and `identity` for chat, async chat, both streaming APIs and image generation.
- Depend on `httpx[brotli]` so `br` is advertised and decoded. httpx only offers that encoding when the brotli package is installed.

## 0.5.0 — 2026-10-22

Wall-clock deadlines for chat calls, and first-class image output. Compatible with the 0.4.0 call signatures.

- `request_timeout` stays the idle timeout between bytes. It no longer has to be raised globally for one streaming profile: set `UsageProfile.request_timeout` (blank = the global value) or pass `request_timeout=` on that call. Other profiles keep the global idle timeout.
- `total_timeout` on OpenRouter settings and on a usage profile, or `total_timeout=` / `deadline_s=` on a call, is a wall-clock deadline for that chat or stream. A per-call value overrides the profile, which overrides the global setting. Blank means no overall deadline, as in 0.4.0.
- When the deadline fires, only that request's response is closed. The shared httpx client stays open for other calls in the process. `stream()` / `astream()` end with a final chunk whose `result.incomplete` is true and whose content, images and usage are whatever had already arrived. `chat()` / `achat()` raise `OpenRouterTimeout`; `partial` on the exception is that same result, or `None` when nothing arrived. The attempt is logged as status `499` with the partial token counts. It is not retried and does not fall through to the next model.
- `ChatResult.images` is a list of `GeneratedImage` (`data`, `mime`, `url`). Data URLs are decoded into `data` and `mime`. `http`/`https` URLs are downloaded without the OpenRouter API key; a failed or oversized download leaves `data` empty and keeps `url`. Text in `content` is unchanged.
- `generate_image(prompt, model=..., profile=...)` and `agenerate_image()` send `modalities=["image", "text"]` unless the caller sets `modalities`. Usage and cost are reported the same way as `chat()`.
- `reasoning={"enabled": false}` (and any other `reasoning` object) is forwarded on the chat request.

## 0.4.0 — 2026-10-18

Speech-to-text via OpenRouter `POST /api/v1/audio/transcriptions`.

- Sync transcription models from `GET /api/v1/models?output_modalities=transcription` and mark them on `modality` / `output_modalities`. Chat catalog sync still upserts `GET /api/v1/models` and does not deactivate a model that exists only in the transcription catalog.
- Usage profiles gain `kind=chat|transcription`. Transcription profiles only accept transcription models, can set an ISO-639-1 `language`, `max_audio_bytes` (blank = 25 MiB) and `max_audio_seconds` (worst-case duration for budget reservations on duration-priced models). Request limits and USD budgets are the same fields as chat.
- `OpenRouterSettings.default_transcription_profile` is the profile `transcribe()` uses when no slug is passed. The global kill switch, API key and base URL are unchanged.
- `transcribe()` / `atranscribe()` (and the same methods on the sync and async clients) send JSON `input_audio`, log the call on the existing request log, and reserve budget before the HTTP call. No ffmpeg dependency. Callers send webm, ogg, mp3, wav, m4a, flac or aac, or set `OPENROUTER["AUDIO_PREPARE"]` to a callable that returns `(bytes, filename, content_type)`.
- New exceptions: `UnsupportedAudioFormat`, `AudioTooLarge`. Disabled integration and a missing API key still raise `OpenRouterDisabled` and `ConfigurationError`.

## 0.3.2 — 2026-10-18

Security and reliability update. Users should upgrade, especially installations
that grant Django admin access to non-superuser staff. Use Django 5.2.18+ or
the latest patched release of a supported Django series in production; legacy
Django compatibility tests are not a security support guarantee.

- Enforce Django permissions for settings creation, catalog actions and usage
  profile assignments. Read-only catalog access no longer refreshes remote data.
- Keep model routing within the configured usage profile; reject the upstream
  `models` override so policy and budget checks apply to every fallback attempt.
- Keep catalog enrichment requests on the configured API origin and encode model paths.
- Isolate file logging destinations to prevent duplicate records and writes to
  previously configured log files.
- Add regression coverage for permissions, routing and sync/async file logging.
