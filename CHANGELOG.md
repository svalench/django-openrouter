# Changelog

## Unreleased

Staff usage dashboard on the request log.

- Open **Usage dashboard** from the OpenRouter admin index or from the request-log summary. The page is a `RequestLogAdmin.get_urls` route wrapped in `admin_view`, so it stays on whichever admin site registers `RequestLog`. Access matches the log itself: staff who are superusers or have `view_usage_logs`.
- Day view buckets by hour (at most 7 days). Month view buckets by day (at most 366 days). Filter by date range, profile and model.
- Charts are inline SVG (no build step, no inline script): cost (USD), request count, error rate, average and p95 latency, average and p95 tokens, overall and grouped by profile and by model. Non-2xx statuses count as errors, including 402, 429, 499, 5xx and in-flight reservations (status 0).
- Totals sit next to each profile’s current daily and monthly request and USD limits, with percent used. Request counts follow the same rules as limit enforcement. The most expensive profiles and models in the selected range are listed separately.
- Aggregation stays in the Django ORM (`TruncHour` / `TruncDay`). p95 is computed in Python from at most 20,000 of the newest rows in the window. A `(model, created_at)` index covers the model filter. `trace_id`, `session_id` and `metadata` are untouched.

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
