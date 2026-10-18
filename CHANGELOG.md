# Changelog

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
