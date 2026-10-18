# Changelog

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
