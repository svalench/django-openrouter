# Библиотека: исправления по ревью

## Progress
- [x] 1. Резервирование лимита/бюджета (pending RequestLog, status 102) — гонка TOCTOU
- [x] 2. Стоимость: приоритет usage.cost, pricing.request, usage.include
- [x] 3. 200 + error в теле / битый JSON → 502 с fallback
- [x] 4. Прерванный стрим логируется (499)
- [x] 5. request_count считает только 200 (+живые резервы)
- [x] 6. MultiFernet + SECRET_KEY_FALLBACKS, ротация, warning при сбое
- [x] 7. Лимитер без busy-wait (future на loop)
- [x] 8. Общие httpx-клиенты (http_clients.py)
- [x] 9. Один агрегат день+месяц (usage_summary), одна блокировка
- [x] 10. BACKGROUND-запись для лог-бэкендов
- [x] 11. Retry: backoff + Retry-After, 408/425/429
- [x] 12. Дедупликация sync/async (_SSEState, единый _attempt_*)
- [x] 13. extra async пустой, предупреждение о неподдерживаемых overrides
- [x] Фичи: tool_calls/finish_reason/reasoning, сигнал request_logged, prune_request_logs
- [x] pytest (90% cov) / ruff / mypy / makemigrations --check / README

DONE
