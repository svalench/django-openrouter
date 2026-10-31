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

## 2026-09-27 — проверка библиотеки
- pytest: все тесты зелёные, покрытие 90%
- ruff check / mypy / makemigrations --check: ок
- ruff format применён к 11 файлам
DONE

## 2026-09-27 — ревью логики
- найдено: зависшие резервы (CancelledError/BaseException), username теряется в StreamingHttpResponse, бюджет недоступен для multimodal/cache-pricing моделей, провальные попытки списывают worst-case
- ожидается решение пользователя по исправлениям

## 2026-09-27 — исправления по ревью
- резервы закрываются при CancelledError/любом сбое (499), команда release_stale_reservations
- username сохраняется в StreamingHttpResponse
- бюджет для multimodal/cache/web_search, учёт картинок
- 402 → только бесплатные модели; неудачные HTTP-попытки не съедают лимит запросов; chat() без stream=True всегда JSON
- pytest 215 ok, ruff, mypy, makemigrations ok; README обновлён
DONE

## 2026-10-18 — speech-to-text 0.4.0
- профили kind=transcription + default_transcription_profile, без отдельного singleton
- sync каталога transcription, transcribe/atranscribe, миграция 0009
- pytest 265 ok, coverage 87.34%, ruff, mypy
- python -m build + twine check --strict: django_openrouter-0.4.0 sdist и wheel PASSED
- PostgreSQL-джоба локально не запускалась: pg_isready нет
DONE

## 2026-10-18 — docs parity STT
- be/de/es/fr/ja/pl/zh: полный раздел transcription как в en.ts (профиль, поля, view, MediaRecorder, AUDIO_PREPARE, исключения, каталог, сигнатуры)
- README: «Added in 0.4.0»; отдельной changelog-страницы на сайте нет, meta.version уже 0.4.0
- site: npm ci && npm run build (tsc -b && vite build) ок
- код библиотеки и версия не менялись
DONE

## 2026-10-31 — usage dashboard
- staff-only страница RequestLogAdmin.get_urls + admin_view, ссылка на индексе любой AdminSite
- агрегаты ORM TruncHour/TruncDay, p95 в Python с потолком 20000, индекс (model, created_at)
- графики inline SVG, фильтры день/месяц + профиль/модель, бюджеты и топ расхода
- pytest полный, coverage 87.56%, ruff, mypy
DONE

## 2026-10-31 — dashboard visuals
- KPI: cost, requests, error rate, p95 latency, дельта к предыдущему окну той же длины
- Chart.js 4.4.6 MIT в static, данные через json_script, цвета серий стабильны, light/dark через CSS variables админки
- pytest 324 passed, coverage 87.32%, ruff, mypy
DONE

## 2026-10-31 — merge master 0.6.0
- индекс дашборда переименован в 0012, зависит от 0011_requestlog_grouping
- trace_id, session_id, metadata с master сохранены
- pytest coverage 86.27%, ruff, mypy, makemigrations --check
DONE

## 2026-10-31 — 0.6.0 OTEL и группы логов
- extra `otel` = только opentelemetry-api; спаны выключены, пока OPENROUTER['OTEL'] не true
- родительский спан на chat/stream/transcribe/generate_image, дочерний на HTTP-попытку
- RequestLog.trace_id, session_id (индексы), metadata JSON, миграция 0011
- bound_session, session_id/metadata/trace_id/trace; File и ClickHouse; админка
- причина падения полного прогона: async for + ранний return не сбрасывает ContextVar (`aclose` в другом Context). Перед yield наружу контекст снимается
- pytest 332 passed, coverage 85.09%, ruff, mypy; site npm run build
DONE

## 2026-10-22 — 0.5.1 content-encoding
- причина: iter_bytes уже снимает Content-Encoding, _rehydrate собирал httpx.Response с тем же заголовком, .json() распаковывал второй раз (zlib -3)
- фикс: json.loads по раскодированным байтам, _rehydrate удалён
- тесты: gzip/br/identity для chat, achat, stream, astream, generate_image, agenerate_image
- pytest 307 passed, coverage 86.06%, ruff, mypy — Python 3.12.3, Django 6.1.2
DONE

## 2026-10-31 — pydantic-ai adapter
- точка интеграции: OpenRouterProfileModel (свой Model), не Provider и не pydantic_ai OpenRouterModel — иначе обходятся цепочка, резерв, kill switch, журнал, bound_username
- extra django-openrouter[pydantic-ai], импорт только из integrations.pydantic_ai
- tests/test_pydantic_ai.py: 26 passed; полный pytest coverage 86.65% (>=85); ruff check/format; mypy src/django_openrouter
- site: npm ci && npm run build (tsc -b && vite build) ок, раздел pydantic-ai во всех 9 локалях
- версия пакета остаётся 0.5.1, CHANGELOG Unreleased
DONE

## 2026-10-31 — 0.7.0 merge master
- master c3dd4d3: OTel 0011 и dashboard 0012; версия 0.7.0, отдельного релиза 0.6.0 нет
- extras otel и pydantic-ai; OpenRouterProfileModel прокидывает conversation_id как session_id, bound_session важнее, trace_id не задаёт — берётся активный спан
- pytest 378 passed, coverage 86.70%, ruff check, mypy, makemigrations --check, site build, twine check --strict
- PyPI: push тега v*.*.* (publish.yml), не GitHub Release
DONE
