import type { DocsContent } from './types'

export const ru: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter для Django — модели, профили, бюджеты и логи через админку',
    version: '0.7.0',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Поиск по документации…',
    searchEmpty: 'Ничего не найдено. Попробуйте другой запрос.',
    onThisPage: 'На этой странице',
    copied: 'Скопировано',
    copy: 'Копировать',
    editGithub: 'GitHub',
    prev: 'Назад',
    next: 'Вперёд',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Начать за 3 минуты',
    heroGithub: 'Репозиторий',
    builtWith: 'Документация по проекту',
    license: 'Лицензия MIT',
  },
  ui: {
    theme: 'Переключить тему',
    language: 'Язык',
    openMenu: 'Открыть меню',
    closeMenu: 'Закрыть меню',
  },
  sections: [
    {
      id: 'intro',
      group: 'Начало работы',
      title: 'Введение',
      lead: 'Переиспользуемое Django-приложение, которое превращает OpenRouter в управляемый ресурс: модели, профили использования, бюджеты и журнал запросов живут в базе и настраиваются через админку — без редеплоев.',
      blocks: [
        {
          type: 'p',
          text: 'Ваш продуктовый код — переводы, чат, суммаризация — обращается к OpenRouter через эту библиотеку, а не через захардкоженные в `settings.py` ключи и идентификаторы моделей. Оператор выбирает активные модели, задаёт дневные и месячные лимиты и смотрит расход прямо в админке.',
        },
        { type: 'h3', text: 'Почему не settings.py?' },
        {
          type: 'p',
          text: 'Строка `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` в настройках означает деплой ради каждой смены модели, бюджета или аварийного отключения. `django-openrouter` хранит эту runtime-политику в базе данных, кэширует её и проверяет лимиты перед каждым запросом.',
        },
        {
          type: 'list',
          items: [
            '**Каталог моделей в базе.** `sync_models` подтягивает каталог OpenRouter (`GET /api/v1/models` + `/endpoints`) с ценами, латентностью (p50 TTFT), throughput и размером весов.',
            '**Профили использования.** Стабильный slug (`chat`, `translation`) → упорядоченная цепочка моделей, `max_tokens`, `temperature`, лимиты и бюджеты.',
            '**Лимиты до запроса.** Дневные/месячные лимиты запросов и бюджеты в USD проверяются до HTTP-вызова. Исчерпание — это исключение, а не молчаливый fallback.',
            '**Стриминг (SSE).** `stream()` / `astream()` отдают ответ по чанкам; включается одним чекбоксом в настройках.',
            '**Журнал каждого вызова.** Каждая попытка пишется в БД, JSONL-файл или ClickHouse (плагинные бэкенды) — вместе с username вызвавшего пользователя.',
            '**Безопасные ключи.** API-ключ из админки зашифрован (Fernet, ключ из `SECRET_KEY`) и write-only: после сохранения его можно только заменить или очистить.',
            '**Kill switch и параллелизм.** Чекбокс `enabled` мгновенно останавливает все вызовы, а `max_parallel_requests` ограничивает одновременные HTTP-запросы в процессе.',
          ],
        },
        { type: 'h3', text: 'Возможности' },
        {
          type: 'table',
          head: ['Возможность', 'Статус'],
          rows: [
            ['Синхронный и асинхронный клиенты', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Фасады-однострочники', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Fallback-цепочки моделей', 'При 402 / 429 / 5xx, в заданном порядке'],
            ['Ретраи транспортных ошибок', 'Настраивается `max_retries`'],
            ['Стриминг (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, по умолчанию выключен'],
            ['Бэкенды логов', 'БД (по умолчанию), JSONL-файл с ротацией, ClickHouse'],
            ['Лимит параллелизма', '`max_parallel_requests`, по умолчанию 10'],
            ['Админка на вашем языке', 'Каталоги переводов для десятков локалей в комплекте'],
            ['Типизация', 'Пакет помечен `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Совместимость',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 и 6.0. Зависимости: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Начало работы',
      title: 'Быстрый старт',
      lead: 'От установки до первого ответа модели — четыре шага.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Установите пакет',
              text: 'Ставится из PyPI одной командой: `pip install django-openrouter`.',
            },
            {
              title: 'Подключите приложение и middleware',
              text: 'Добавьте `django_openrouter` в `INSTALLED_APPS` и `django_openrouter.middleware.CurrentUserMiddleware` в `MIDDLEWARE`, затем выполните `python manage.py migrate`.',
            },
            {
              title: 'Настройте в админке',
              text: 'Откройте **OpenRouter → OpenRouter settings**: вставьте API-ключ (он будет зашифрован) или оставьте поле пустым и задайте `OPENROUTER_API_KEY` в окружении.',
            },
            {
              title: 'Синхронизируйте каталог и создайте профиль',
              text: 'Выполните `python manage.py sync_models`, затем создайте **Usage profile** со slug `chat`, добавьте модели в порядке приоритета и при желании сделайте профиль дефолтным.',
            },
          ],
        },
        { type: 'h3', text: '1. Установка' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Подключение и миграции' },
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
          text: '`CurrentUserMiddleware` ставится **после** `AuthenticationMiddleware` и записывает username вызвавшего пользователя в журнал запросов. Без него все строки будут помечены как `anonymous`. Для `StreamingHttpResponse` username держится и во время отдачи тела, поэтому `stream()` внутри потоковой вьюхи логируется под нужным пользователем.',
        },
        { type: 'h3', text: '3. Настройка в Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Откройте **OpenRouter → OpenRouter settings**. Вставьте API-ключ — он зашифрован и не отображается после сохранения — либо оставьте поле пустым и задайте `OPENROUTER_API_KEY` в окружении.',
            'Запустите `python manage.py sync_models`, чтобы подтянуть каталог моделей (`GET /api/v1/models`).',
            'Создайте **Usage profile** (slug `translation`, `chat`, …) и добавьте одну или несколько моделей в порядке приоритета (первая пробуется первой), плюс лимиты и бюджеты.',
            'Установите профиль как **default profile**, если хотите вызывать `chat(messages=...)` без имени.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Скриншоты',
          text: 'Все четыре раздела админки — настройки, каталог, профили и журнал — со скриншотами разобраны в разделе «Админка».',
        },
        { type: 'h3', text: '4. Первый вызов' },
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
          title: 'Проверка без ключа',
          text: 'Каталог можно синхронизировать с разовым ключом: `python manage.py sync_models --api-key sk-or-...` — он не сохранится в базе.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Руководство',
      title: 'Конфигурация',
      lead: 'Порядок разрешения API-ключа, словарь settings.OPENROUTER и как устроен кэш runtime-конфигурации.',
      blocks: [
        { type: 'h3', text: 'Откуда берётся API-ключ' },
        {
          type: 'p',
          text: 'Если поле ключа в админке пустое, библиотека ищет ключ в следующем порядке:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (настройка верхнего уровня)',
            'переменная окружения `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Ключ, сохранённый в админке, всегда имеет приоритет над всеми тремя вариантами выше. Он хранится зашифрованным (Fernet, ключ выводится из `SECRET_KEY`) и недоступен для чтения после сохранения.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Ключ', 'По умолчанию', 'Описание'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Сколько секунд держать runtime-конфиг в кэше Django'],
            ['`CACHE_ALIAS`', '`"default"`', 'Алиас кэша (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Сколько секунд админка не пересинхронизирует каталог моделей'],
            ['`API_KEY`', 'не задан', 'Запасной ключ, если поле в админке пустое'],
            ['`HTTP_REFERER`', 'не задан', 'Заголовок `HTTP-Referer` (атрибуция приложения в OpenRouter)'],
            ['`X_TITLE`', 'не задан', 'Заголовок `X-Title`'],
            ['`LOG_BACKENDS`', 'только БД', 'Куда писать логи запросов — см. раздел «Бэкенды логов»'],
            ["`OTEL`", "`false`", "Спаны. Выключено, даже если opentelemetry-api установлен"],
            ["`OTEL_CAPTURE_CONTENT`", "`false`", "Писать на спан отредактированные промпт и ответ"],
            ["`OTEL_CONTENT_REDACTOR`", "не задан", "Dotted path fn(text, *, kind) -> str"],
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
          text: 'Стандартного `LocMemCache` достаточно. Redis или Memcached — опционально, просто укажите нужный `CACHE_ALIAS`.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Настройки в админке, а не в settings.py',
          text: 'Таймаут, число ретраев, kill switch, стриминг (`streaming_enabled`) и лимит параллельных запросов (`max_parallel_requests`) живут в разделе **OpenRouter settings** админки — подробности со скриншотом в разделе «Админка».',
        },
        { type: 'h3', text: 'Как работает кэш' },
        {
          type: 'p',
          text: 'Клиент читает не базу напрямую, а снимок `RuntimeConfig` из кэша Django: настройки, активные профили и их fallback-модели. Сигналы `post_save` / `post_delete` на всех моделях приложения мгновенно инвалидируют кэш — правки в админке применяются без рестарта, а `CACHE_TIMEOUT` служит лишь страховкой.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache и несколько процессов',
          text: 'С `LocMemCache` каждый процесс держит свою копию кэша: инвалидация сработает только в процессе, где сохраняли в админке. Для multi-process деплоя используйте Redis/Memcached через `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Руководство',
      title: 'Использование',
      lead: 'Фасады chat() / achat() / stream() / astream(), классы клиентов, переопределения на вызов и структура результата.',
      blocks: [
        { type: 'h3', text: 'Фасад chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # slug профиля; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Синхронный клиент' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Асинхронный вызов' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# или классом
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: 'Асинхронный клиент полностью повторяет интерфейс синхронного: ORM-операции уходят в `sync_to_async`, HTTP — через `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Стриминг (SSE)' },
        {
          type: 'p',
          text: 'Стриминг выключен по умолчанию. Включите **Streaming enabled** в **OpenRouter settings**, после чего `stream()` и `astream()` будут отдавать ответ чанками `ChatChunk`:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# финальный чанк: done=True, chunk.result — полный ChatResult

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` использует тот же SSE-транспорт и возвращает полный `ChatResult`. Обычный `chat()` всегда идёт обычным JSON-запросом, даже при включённом стриминге. Вызов при выключенном стриминге бросает `ConfigurationError` ещё до HTTP-запроса.',
        },
        {
          type: 'table',
          head: ['Поле ChatChunk', 'Тип', 'Описание'],
          rows: [
            ['`delta`', '`str`', 'Текст текущего чанка'],
            ['`content`', '`str`', 'Накопленный текст с начала ответа'],
            ['`model_used`', '`str`', 'Модель, отдающая ответ'],
            ['`done`', '`bool`', '`True` у финального чанка'],
            ['`result`', '`ChatResult | None`', 'Полный результат у финального чанка'],
            ['`raw`', '`dict`', 'Сырое SSE-событие'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback и стриминг',
          text: 'Fallback на следующую модель возможен, только если ни один чанк ещё не отдан. Если модель начала стримить и упала посередине — ошибка пробрасывается вызывающему коду: часть ответа уже ушла клиенту.',
        },
        { type: 'h3', text: 'Переопределения на вызов' },
        {
          type: 'p',
          text: 'Любые `**overrides` пробрасываются в тело запроса. `max_tokens` и `temperature` перекрывают значения профиля, `model` временно ставит указанную модель первой в цепочке:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # должен быть в цепочке моделей этого профиля
    response_format={"type": "json_object"},  # любой параметр OpenRouter
)`,
        },
        { type: 'h3', text: 'Параллелизм' },
        {
          type: 'p',
          text: 'Поле **Max parallel requests** в настройках (по умолчанию `10`, `0` = без ограничений) ограничивает число одновременных HTTP-запросов к OpenRouter в текущем процессе — и для `chat()`, и для `stream()`, синхронных и асинхронных.',
        },
        { type: 'h3', text: 'Результат: ChatResult' },
        {
          type: 'table',
          head: ['Поле', 'Тип', 'Описание'],
          rows: [
            ['`content`', '`str`', 'Текст ответа (склейка text-частей для multipart-контента)'],
            ['`prompt_tokens`', '`int`', 'Токены промпта из `usage`'],
            ['`completion_tokens`', '`int`', 'Токены ответа из `usage`'],
            ['`cost_usd`', '`Decimal`', 'Стоимость: `usage.cost` от API, если есть; иначе оценка по каталогу'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Стоимость по каталогу — для сверки с биллингом'],
            ['`model_used`', '`str`', 'Модель, реально вернувшая ответ'],
            ['`latency_ms`', '`int`', 'Латентность успешной попытки'],
            ['`raw`', '`dict`', 'Сырой JSON ответа OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'pydantic-ai',
      group: 'Руководство',
      title: 'Pydantic AI',
      lead: 'Необязательный адаптер: агент Pydantic AI ходит в OpenRouter через профиль использования. Цепочка моделей, бюджеты, лимиты, kill switch и журнал запросов остаются в django-openrouter.',
      blocks: [
        {
          type: 'p',
          text: 'Дополнительная зависимость: `pip install "django-openrouter[pydantic-ai]"` (Pydantic AI 2.64+). Импорт `django_openrouter` не тянет Pydantic AI. Класс — `django_openrouter.integrations.pydantic_ai.OpenRouterProfileModel`. Без extra этот импорт поднимает `ImportError` и подсказывает команду установки.',
        },
        {
          type: 'p',
          text: 'Это `Model` Pydantic AI, а не `Provider`. Провайдер отдал бы только HTTP-клиент, и Pydantic AI сам позвал бы OpenRouter — мимо цепочки профиля, резерва бюджета, лимитов, kill switch, журнала и `bound_username`. `OpenRouterProfileModel` собирает chat-completions и вызывает `AsyncOpenRouterClient`. `Agent.run` и `Agent.run_sync` оба идут в эти async-методы.',
        },
        { type: 'h3', text: 'Агент' },
        {
          type: 'code',
          lang: 'python',
          code: `from pydantic_ai import Agent

from django_openrouter.integrations.pydantic_ai import OpenRouterProfileModel

agent = Agent(OpenRouterProfileModel("chat"))
result = agent.run_sync("Hello")
print(result.output, result.usage.cost, result.response.model_name)`,
        },
        {
          type: 'p',
          text: '`profile` — слаг профиля. `None` берёт чат-профиль по умолчанию. Возможности Pydantic AI передаются как `model_profile=`: здесь `profile` — это слаг Django. Идентификатор модели агента остаётся `openrouter:<slug>`. `result.response.model_name` — id из каталога, который реально ответил, уже после fallback. В `result.usage` токены и `cost` в USD (`usage.cost` из API, если он есть, иначе оценка по каталогу).',
        },
        {
          type: 'p',
          text: '`temperature` и `max_tokens` агента ограничиваются профилем. Более низкая temperature сохраняется. Если агент их не передал, остаются значения профиля. `thinking` уходит как OpenRouter `reasoning` (`False` → `{"enabled": false}`, `"high"` → `{"enabled": true, "effort": "high"}`). `timeout` — это idle `request_timeout` одного вызова. Картинки на входе (`ImageUrl`, image `BinaryContent`) становятся частями `image_url`. Картинки в ответе модели остаются в `ChatResult.images` и не превращаются в image-части Pydantic AI.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Стриминг',
          text: '`agent.run_stream` и `run_stream_sync` требуют включённого Streaming в настройках OpenRouter. Текстовые дельты приходят по мере SSE. Reasoning и tool calls дописываются из финального чанка.',
        },
        {
          type: 'p',
          text: '`BudgetExceeded` и `RateLimitExceeded` доходят до вызывающего кода. Они поднимаются до HTTP и не переключают вызов на другую модель. HTTP-fallback остаётся внутри цепочки профиля (`402`, `408`, `429`, `5xx`).',
        },
        {
          type: 'p',
          text: '`Agent.run(conversation_id=...)` попадает в журнал как `session_id` и уходит в тело chat, если `bound_session()` ещё не включён. Сессия и metadata из этого блока важнее и тоже уходят в запрос. Адаптер не передаёт `trace_id`. Активный спан OpenTelemetry — Django, Celery или `Agent(instrument=True)` — становится `trace_id` в журнале. Без трейсинга у каждого вызова модели свой id, общий для retry и fallback этого вызова.',
        },
        { type: 'h3', text: 'Django view' },
        {
          type: 'code',
          lang: 'python',
          title: 'views.py',
          code: `from django.http import JsonResponse
from django.views.decorators.http import require_POST
from pydantic_ai import Agent

from django_openrouter.exceptions import BudgetExceeded, RateLimitExceeded
from django_openrouter.integrations.pydantic_ai import OpenRouterProfileModel

agent = Agent(OpenRouterProfileModel("chat"))

@require_POST
def ask(request):
    try:
        result = agent.run_sync(request.POST["q"])
    except (BudgetExceeded, RateLimitExceeded) as exc:
        return JsonResponse({"error": str(exc)}, status=429)
    return JsonResponse(
        {
            "answer": result.output,
            "model": result.response.model_name,
            "cost_usd": str(result.usage.cost),
        }
    )`,
        },
        { type: 'h3', text: 'Задача Celery' },
        {
          type: 'p',
          text: 'Вне запроса имя в журнале задаёт `bound_username`. Для HTTP это уже делает `CurrentUserMiddleware`.',
        },
        {
          type: 'code',
          lang: 'python',
          title: 'tasks.py',
          code: `from celery import shared_task
from pydantic_ai import Agent

from django_openrouter.current_user import bound_username
from django_openrouter.integrations.pydantic_ai import OpenRouterProfileModel

agent = Agent(OpenRouterProfileModel("chat"))

@shared_task
def summarize(username: str, text: str) -> str:
    with bound_username(username):
        result = agent.run_sync(f"Summarize:\\n{text}")
    return result.output`,
        },
      ],
    },
    {
      id: 'transcription',
      group: 'Руководство',
      title: 'Речь в текст',
      lead: 'transcribe() / atranscribe() отправляют аудио браузера или сервера на OpenRouter POST /api/v1/audio/transcriptions. Профили, бюджеты и журнал запросов — те же, что у чата.',
      blocks: [
        {
          type: 'p',
          text: 'Модели транскрипции нет в обычном чат-каталоге. `sync_models` дополнительно запрашивает `GET /api/v1/models?output_modalities=transcription` и сохраняет их с modality `audio->transcription` и `output_modalities: ["transcription"]`. Синк чата в остальном прежний: модель, исчезнувшая из обоих списков, деактивируется, а модель только для транскрипции не выключается из-за того, что её нет в чат-каталоге.',
        },
        { type: 'h3', text: 'Профиль транскрипции' },
        {
          type: 'p',
          text: 'В **Профилях использования** поставьте **Тип** = **Transcription**, выберите только модели транскрипции (автокомплит фильтруется по полю типа) и при необходимости язык, лимит размера и длительность. В **Настройках OpenRouter** укажите этот профиль как **Default transcription profile**, если `transcribe()` должен работать без слага. Ключ, base URL и kill switch остаются на той же строке настроек. Отдельного singleton для STT нет: бюджеты и логи уже живут на профилях, и в приложении можно развести диктовку и расшифровку встреч.',
        },
        {
          type: 'table',
          head: ['Поле профиля', 'Зачем'],
          rows: [
            ['`kind`', '`chat` (по умолчанию) или `transcription`'],
            ['`language`', 'Подсказка ISO-639-1 (`en`, `ru`). Пусто = автоопределение. Для чата игнорируется'],
            ['`max_audio_bytes`', 'Лимит загрузки. Пусто = 25 МиБ'],
            ['`max_audio_seconds`', 'Худшая длина в секундах для резерва бюджета duration-моделей (Whisper: context length 0, цена `prompt` — за секунду)'],
            ['`max_requests_*` / `budget_usd_*`', 'Те же дневные и месячные лимиты, что у чата. Резерв сходится к `usage.cost`'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Бюджет duration-модели требует max_audio_seconds',
          text: 'Профиль транскрипции с бюджетом в USD и duration-моделью бросает `ConfigurationError`, пока не задан `max_audio_seconds`. Токенные STT-модели (ненулевой context length) резервируют `context_length ×` максимальную цену за токен — та же идея, что у чата.',
        },
        { type: 'h3', text: 'Вызов transcribe()' },
        {
          type: 'code',
          lang: 'python',
          title: 'views.py',
          code: `from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django_openrouter import transcribe
from django_openrouter.exceptions import (
    AudioTooLarge,
    BudgetExceeded,
    ConfigurationError,
    OpenRouterDisabled,
    UnsupportedAudioFormat,
)

@require_POST
def dictate(request):
    blob = request.FILES["audio"]
    try:
        result = transcribe(
            blob,
            filename=blob.name,
            content_type=blob.content_type,
            profile="dictation",  # или None → дефолтный профиль транскрипции
            language="ru",
        )
    except OpenRouterDisabled:
        return JsonResponse({"error": "disabled"}, status=503)
    except (UnsupportedAudioFormat, AudioTooLarge, ConfigurationError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except BudgetExceeded:
        return JsonResponse({"error": "budget"}, status=429)
    return JsonResponse(
        {
            "text": result.text,
            "model": result.model_used,
            "cost_usd": str(result.cost_usd),
            "seconds": None if result.duration_seconds is None else str(result.duration_seconds),
        }
    )`,
        },
        {
          type: 'p',
          text: 'В библиотеке нет зависимости от ffmpeg. Передавайте контейнер, который принимает OpenRouter: webm, ogg, mp3, wav, m4a, flac или aac. Блоб `MediaRecorder` (`audio/webm;codecs=opus`) подходит. Чтобы перекодировать заранее, задайте `OPENROUTER["AUDIO_PREPARE"]` — dotted path функции `(data, *, filename, content_type) -> (bytes, filename, content_type)`.',
        },
        {
          type: 'code',
          lang: 'javascript',
          title: 'browser',
          code: `const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
const chunks = [];
recorder.ondataavailable = (event) => {
  if (event.data.size) chunks.push(event.data);
};
recorder.onstop = async () => {
  const blob = new Blob(chunks, { type: recorder.mimeType });
  const body = new FormData();
  body.append("audio", blob, "dictation.webm");
  const response = await fetch("/dictate/", {
    method: "POST",
    body,
    headers: { "X-CSRFToken": csrfToken },
  });
  const payload = await response.json();
  console.log(payload.text);
};
recorder.start();`,
        },
        {
          type: 'p',
          text: '`atranscribe()` и методы `OpenRouterClient.transcribe` / `AsyncOpenRouterClient.transcribe` — тот же вызов. `model=` может только переставить модель, которая уже есть в профиле. `prompt=` уходит в JSON; OpenRouter сейчас игнорирует prompt верхнего уровня в multipart, поэтому это подсказка, а не гарантия смещения словаря. `TranscriptionResult` содержит `text`, счётчики токенов, `duration_seconds`, `cost_usd`, `catalog_cost_usd`, `model_used`, `latency_ms` и `raw`.',
        },
      ],
    },
    {
      id: 'models',
      group: 'Руководство',
      title: 'Каталог моделей',
      lead: 'Как sync_models наполняет каталог и что хранит OpenRouterModel.',
      blocks: [
        { type: 'h3', text: 'Команда sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # разовый ключ, не сохраняется` },
        {
          type: 'p',
          text: 'Команда делает upsert чат-каталога (`GET /api/v1/models`) и каталога транскрипции (`GET /api/v1/models?output_modalities=transcription`), затем обогащает оба метриками `/endpoints` — p50-латентностью и throughput. Ничего не удаляет: модели, исчезнувшие из обоих списков, получают `is_active=False`. Профили, ссылающиеся на такую модель, не ломаются — вызов просто начнёт падать с `ModelDisabled`, пока вы не переключите профиль.',
        },
        { type: 'h3', text: 'Поля модели' },
        {
          type: 'table',
          head: ['Поле', 'Описание'],
          rows: [
            ['`model_id`', 'Идентификатор OpenRouter, напр. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Человекочитаемое имя'],
            ['`context_length`', 'Размер контекста в токенах'],
            ['`pricing`', 'JSON цен за токен: `prompt`, `completion`, опционально `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Цены за токен в десятичном виде — для сортировки и фильтров в админке'],
            ['`latency_ms`', 'p50 TTFT лучшего эндпоинта, в миллисекундах'],
            ['`throughput`', 'p50 throughput лучшего эндпоинта, ток/с'],
            ['`parameter_count`', 'Примерное число весов (70B → 70000000000), для сортировки'],
            ['`parameter_label`', 'Отображаемый размер с единицей: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Список поддерживаемых параметров'],
            ['`modality`', 'Модальность, напр. `text->text` или `audio->transcription`'],
            ['`output_modalities`', 'Список из каталога, напр. `["text"]` или `["transcription"]`'],
            ['`is_active`', 'Можно ли выбирать модель в профилях'],
            ['`last_synced_at`', 'Когда модель последний раз видела синхронизация'],
            ['`is_free` (property)', '`True`, если цены `prompt`/`completion`/`request` равны нулю'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Только бесплатные модели',
          text: 'Флаг профиля `only_free_models` разрешает только модели с нулевой ценой в каталоге — удобно для dev-стендов и демо. Проверяется и для основной модели, и для каждой fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Руководство',
      title: 'Лимиты, бюджеты и fallback',
      lead: 'Что проверяется до запроса, что происходит при ошибках OpenRouter и когда срабатывает fallback.',
      blocks: [
        { type: 'h3', text: 'Лимиты профиля' },
        {
          type: 'p',
          text: 'Расход считается из `RequestLog` за текущие календарные день и месяц (в активном `TIME_ZONE`). Пустое (`null`) поле лимита означает «без ограничений».',
        },
        {
          type: 'table',
          head: ['Поле профиля', 'Что ограничивает', 'Исключение'],
          rows: [
            ['`max_requests_per_day`', 'Число запросов за день', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Число запросов за месяц', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Сумму `cost_usd` за день', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Сумму `cost_usd` за месяц', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'Перед каждой HTTP-попыткой транзакция блокирует строку профиля и резервирует один запрос и стоимость худшего случая: полный контекст модели по максимальной потокенной цене (`prompt`, `completion`, `input_cache_read`, `input_cache_write`, `internal_reasoning`), плюс `request` / `web_search` и `image` × число частей `image_url`. Успешный вызов сверяет резерв с фактическим usage; неудачные, прерванные и отменённые вызовы (статус `499`) сохраняют резерв до сверки с биллингом. Для бюджета модели нужны корректные цены, context length и текстовый выход (`text+image->text` подходит); прочие ненулевые цены, например `audio`, отклоняются. Повторы, упавшие с HTTP-ошибкой, не расходуют лимит запросов.',
        },
        {
          type: 'p',
          text: 'Резервы, оставшиеся после убитого воркера, освобождаются из cron (статус `499`, стоимость `0`); резервы ответов без `usage` не трогаются:',
        },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py release_stale_reservations --minutes 60 [--dry-run]` },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Лимиты требуют DatabaseBackend',
          text: 'Агрегаты считаются по таблице `RequestLog`. Если у профиля есть лимиты, но `DatabaseBackend` убран из `LOG_BACKENDS`, вызов завершится `ConfigurationError`.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Без молчаливых обходов',
          text: 'Исчерпание лимита или бюджета — это исключение (`BudgetExceeded` / `RateLimitExceeded`) до HTTP-вызова. Библиотека **не** переключается на другую модель, чтобы «дожать» запрос.',
        },
        { type: 'h3', text: 'Цепочка fallback' },
        {
          type: 'p',
          text: 'Fallback-модели задействуются только когда сам OpenRouter вернул `402`, `429` или `5xx`. Порядок задаётся полем `order` в админке; дубликаты в цепочке отбрасываются. Модели, запрещённые правилами профиля (выключена, не бесплатная при `only_free_models`), пропускаются.',
        },
        {
          type: 'list',
          items: [
            '**Транспортные ошибки и 5xx** — ретраятся до `max_retries` раз на той же модели, затем fallback.',
            '**429 / 408** — повтор на той же модели (с учётом `Retry-After`), затем следующая модель цепочки.',
            '**402** (закончились кредиты аккаунта) — дальше пробуются только бесплатные модели цепочки.',
            '**Прочие 4xx** (например, 400) — ошибка пробрасывается сразу, без fallback: запрос, скорее всего, невалиден для всех моделей.',
            '**Каждая попытка** — включая неуспешные — пишется в журнал.',
          ],
        },
        { type: 'h3', text: 'Глобальный kill switch' },
        {
          type: 'p',
          text: 'Чекбокс `enabled` в **OpenRouter settings** мгновенно останавливает всё: любой вызов `chat()` падает с `OpenRouterDisabled` ещё до проверки лимитов. Удобно для инцидентов и плановых остановок.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Руководство',
      title: 'Бэкенды логов',
      lead: 'Каждый HTTP-вызов пишется во все бэкенды из OPENROUTER["LOG_BACKENDS"]: в базу проекта, JSONL-файл, ClickHouse — или в ваш собственный класс.',
      blocks: [
        {
          type: 'p',
          text: 'Каждая запись в списке — либо dotted path к классу (настройки по умолчанию), либо словарь с ключом `BACKEND` и параметрами. Если `LOG_BACKENDS` не задан, логи пишутся только в базу проекта (`RequestLog`).',
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
        { type: 'h3', text: 'DatabaseBackend (по умолчанию)' },
        {
          type: 'p',
          text: 'Пишет строки в `RequestLog`, включая предварительные резервы. Для профилей с лимитами этот бэкенд обязателен; иначе возникает `ConfigurationError`.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines в файл с ротацией по объёму (`RotatingFileHandler`): одна строка = один JSON-объект с полями `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`, `trace_id`, `session_id`, `metadata`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Вставляет `FORMAT JSONEachRow` через HTTP-интерфейс ClickHouse. Дополнительных зависимостей нет — используется тот же `httpx`. Имена базы и таблицы валидируются как идентификаторы, чтобы исключить инъекции. Таблица создаётся так:',
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
    username String,
    trace_id String,
    session_id String,
    metadata String
)
ENGINE = MergeTree
ORDER BY (created_at, profile);`,
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Best-effort',
          text: 'Все настроенные бэкенды получают каждую запись, а сбой бэкенда (переполненный диск, недоступный ClickHouse) никогда не роняет `chat()` — ошибка пишется в логгер `django_openrouter`.',
        },
        { type: 'h3', text: 'Кто сделал запрос' },
        {
          type: 'p',
          text: 'В каждую запись попадает username пользователя Django, сделавшего вызов. Его подставляет `django_openrouter.middleware.CurrentUserMiddleware` (после `AuthenticationMiddleware`). Вызовы без пользователя или вне HTTP-запроса логируются как `anonymous`. В Celery и management-командах задайте имя вручную:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Свой бэкенд' },
        {
          type: 'p',
          text: 'Отнаследуйтесь от `django_openrouter.log_backends.LogBackend`, реализуйте `write()` (и опционально `awrite()`) и добавьте dotted path класса в `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'tracing',
      group: "Руководство",
      title: "Трейсинг и группы логов",
      lead: "Необязательные спаны OpenTelemetry и поля trace_id, session_id, metadata в журнале запросов.",
      blocks: [
        {
          type: "p",
          text: "pip install django-openrouter[otel] ставит только opentelemetry-api. SDK и экспортёр остаются в проекте-хосте. Если пакета нет, вызовы его не импортируют. Спаны выключены, пока OPENROUTER['OTEL'] не равен true.",
        },
        {
          type: "h3",
          text: "Спаны",
        },
        {
          type: "p",
          text: "chat, achat, stream, astream, transcribe, atranscribe, generate_image и agenerate_image открывают один родительский спан. generate_image не добавляет вложенный спан chat. Каждая HTTP-попытка, включая retry и fallback, — дочерний спан. Активный спан Django или Celery остаётся родителем. Стрим пишет время до первого токена и держит родительский спан до конца генератора.",
        },
        {
          type: "p",
          text: "Атрибуты: gen_ai.system=openrouter, gen_ai.operation.name, модели запроса и ответа, токены и finish reason, плюс openrouter.cost_usd, profile, индекс fallback, индекс retry, код статуса, латентность, username, session_id и trace_id. BudgetExceeded, RateLimitExceeded, таймауты и прерванный стрим (499) — ошибки спана. Текст промпта и ответа не пишется, пока не включён OTEL_CAPTURE_CONTENT. Редактор — dotted path (text, *, kind) -> str. Ключ API и заголовок Authorization в атрибуты не попадают.",
        },
        {
          type: "h3",
          text: "Группировка",
        },
        {
          type: "p",
          text: "У RequestLog nullable индексы trace_id и session_id и nullable JSON metadata. Retry и fallback одного вызова делят trace_id: это id трейса OpenTelemetry, если спан пишется, иначе сгенерированный id. trace_id= задаёт id в логе и в атрибуте спана и не подменяет id контекста спана. session_id= и metadata= у chat по-прежнему уходят в OpenRouter. trace= — дополнительные атрибуты спана, в запрос не входят. Транскрипция сохраняет поля и не кладёт их в JSON аудио.",
        },
        {
          type: "code",
          lang: "python",
          title: "bound_session",
          code: "from django_openrouter import chat\nfrom django_openrouter.current_user import bound_session\n\nwith bound_session(\"ticket-42\", metadata={\"feature\": \"support\"}):\n    chat(\"chat\", messages=[{\"role\": \"user\", \"content\": \"Hi\"}])\n\nchat(\n    \"chat\",\n    messages=[{\"role\": \"user\", \"content\": \"Hi\"}],\n    session_id=\"other\",\n    metadata={\"feature\": \"billing\"},\n    trace={\"feature.flag\": \"beta\"},\n)",
        },
        {
          type: "p",
          text: "Аргументы вызова перекрывают bound_session только для этого вызова. Ключи metadata вызова заменяют ключи блока. В админке журнал фильтруется и ищется по session_id и trace_id. У строки есть ссылки all calls in this session и all calls in this trace. Metadata на странице записи только для чтения.",
        },
        {
          type: "h3",
          text: "Logfire, Langfuse, Jaeger, Tempo",
        },
        {
          type: "code",
          lang: "python",
          title: "OTLP",
          code: "pip install \"django-openrouter[otel]\" opentelemetry-sdk opentelemetry-exporter-otlp\n\n# Logfire: logfire.configure() sets the TracerProvider.\n# Langfuse via OTLP:\n#   OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel\n#   OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64 public:secret>\n# Jaeger or Grafana Tempo (OTLP/HTTP):\n#   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318\n\nfrom opentelemetry import trace\nfrom opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter\nfrom opentelemetry.sdk.trace import TracerProvider\nfrom opentelemetry.sdk.trace.export import BatchSpanProcessor\n\nprovider = TracerProvider()\nprovider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))\ntrace.set_tracer_provider(provider)",
        },
      ],
    },
    {
      id: 'admin',
      group: 'Руководство',
      title: 'Админка',
      lead: 'Вся runtime-политика живёт в Django admin: настройки, каталог моделей, профили использования, журнал запросов и панель расхода.',
      blocks: [
        {
          type: 'table',
          head: ['Раздел', 'Что делает'],
          rows: [
            ['**OpenRouter settings**', 'Kill switch, зашифрованный API-ключ, стриминг, таймауты'],
            ['**OpenRouter models**', 'Каталог из OpenRouter: цена, латентность, throughput'],
            ['**Usage profiles**', 'Цепочка моделей, лимиты, бюджеты, статистика расхода'],
            ['**Request logs**', 'Токены, стоимость и латентность каждого вызова (read-only)'],
            ['**Usage dashboard**', 'Расход, доля ошибок, латентность и токены рядом с бюджетами профилей'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Singleton: список записей перенаправляет на единственную строку, а удалить её нельзя. Здесь собраны глобальные настройки интеграции:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — глобальный kill switch. Выкл → каждый `chat()` / `stream()` падает с `OpenRouterDisabled`.',
            '**API key** — write-only, зашифрован Fernet из `SECRET_KEY`. Пустое поле сохраняет текущий ключ; новое значение заменяет его; чекбокс **Clear stored API key** стирает ключ из базы — тогда используется `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`.',
            '**Base URL** — корень OpenRouter API (`https://openrouter.ai/api/v1`).',
            '**Default profile** — профиль, используемый, когда `chat(messages=...)` вызван без имени.',
            '**Request timeout** / **Max retries** — HTTP-таймаут и число ретраев на транспорт/5xx перед переходом к следующей модели цепочки.',
            '**Streaming enabled** — разрешает SSE через `stream()` / `astream()` и `chat(stream=True)`. По умолчанию выключен.',
            '**Max parallel requests** — потолок одновременных HTTP-вызовов в этом процессе (`0` = без ограничений).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings: enabled, статус ключа, base url, default profile, таймаут, ретраи, стриминг, лимит параллелизма',
          caption: 'OpenRouter settings: kill switch, write-only API-ключ, дефолтный профиль, таймауты, стриминг и лимит параллелизма.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'Каталог из `GET /api/v1/models` плюс метрики `/endpoints` (латентность и throughput). Строки нельзя добавить или удалить руками, карточка модели — read-only.',
        },
        {
          type: 'list',
          items: [
            '**Колонки:** имя, `latency_ms` (p50 TTFT), throughput (ток/с), цены prompt/completion за 1M токенов, размер весов (`70B` / `8x7B`), `is_active`. Сортировка кликом по колонке — пустые значения всегда в конце.',
            '**Фильтры:** активность, модальность, цена (free / < $1 / $1–10 / ≥ $10 за 1M), скорость (< 400 мс / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (действие) — upsert каталога; исчезнувшие модели получают `is_active=False`.',
            '**Assign to usage profile…** (действие) — добавляет выбранные модели в конец цепочки профиля; дубликаты, неактивные и платные модели при `only_free_models` пропускаются с отчётом.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'При первом открытии список обновляется из API, затем 10 минут отдаётся из базы (`CATALOG_CACHE_TIMEOUT`). Тот же синк из консоли: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — каталог моделей OpenRouter: имя, latency, throughput, цена за 1M, размер весов, активность; фильтры справа',
          caption: 'Каталог моделей: сортировка по цене/латентности, фильтры по цене и скорости, действия sync и assign to profile.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Профиль — это slug, который передаёт ваш код (`chat`, `translation`, …), плюс упорядоченный список моделей: первая пробуется первой, остальные — fallback при `402` / `429` / `5xx`. Исчерпанные лимиты выбрасывают исключение, а не молчаливо переключают модель.',
        },
        {
          type: 'list',
          items: [
            '**Список профилей:** имя, основная модель, активность, only-free, дневные лимиты запросов/бюджета и агрегаты из журнала — число запросов, средняя и суммарная латентность, средняя и суммарная стоимость (один GROUP BY на страницу).',
            '**Форма:** `max_tokens`, `temperature` (0–2), дневные/месячные лимиты запросов и USD (пусто = без лимита), **only free models**, **is active**.',
            '**Инлайн Models (priority order):** автокомплит по каталогу — в подписи видны цена и латентность, действуют те же фильтры цены/скорости, что и в каталоге. Порядок нормализуется при сохранении, а первая модель цепочки синхронизируется в поле `model`.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — список профилей использования с агрегатами запросов, латентности и стоимости',
          caption: 'Профили использования: цепочка моделей, лимиты и агрегаты расхода прямо в списке.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Read-only журнал. Каждая HTTP-попытка (включая fallback и ошибки) становится строкой, когда включён `DatabaseBackend` (по умолчанию). Дневные и месячные лимиты агрегируются из этой таблицы.',
        },
        {
          type: 'list',
          items: [
            '**Колонки:** время, username, профиль, модель, HTTP-статус, токены prompt/completion, стоимость, латентность.',
            '**Сводка над таблицей:** число запросов и сумма USD по текущему фильтру. Фильтры: профиль, статус, дата, session id, trace id; поиск по тексту ошибки, username, session id и trace id.',
            '**Сессия и трейс:** у строки ссылки all calls in this session и all calls in this trace. Metadata на странице записи только для чтения.',
            '**Username** подставляет `CurrentUserMiddleware`; без него строки помечаются `anonymous`. В Celery и management-командах — `bound_username("worker")` (см. «Бэкенды логов»).',
            '**Права:** отдельное право `view_usage_logs` позволяет дать саппорту доступ к расходу без доступа к настройкам.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — журнал запросов: время, username, профиль, модель, статус, токены, стоимость, латентность; сводка сверху',
          caption: 'Журнал запросов: каждая попытка с токенами, стоимостью и латентностью, сводка по фильтру над таблицей.',
        },
        { type: 'h3', text: 'Панель расхода' },
        {
          type: 'p',
          text: 'Сотрудник с правом `view_usage_logs` (и суперпользователь) открывает **Usage dashboard** с индекса OpenRouter или из сводки журнала. Страница регистрируется в `RequestLogAdmin.get_urls` и оборачивается в `admin_view`, поэтому свой `AdminSite`, на котором зарегистрирован `RequestLog`, отдаёт ту же страницу. В стандартной админке путь — `/admin/django_openrouter/requestlog/dashboard/`.',
        },
        {
          type: 'list',
          items: [
            '**Окно.** День группирует по часам (не больше 7 дней). Месяц — по дням (не больше 366 дней). Пресеты переключают на сегодня или текущий месяц. Фильтры сужают выборку по профилю и модели.',
            '**Графики.** Вендорный Chart.js (MIT, без сборки, без CDN и без inline-скрипта). Данные передаются через `json_script`: стоимость, запросы, доля ошибок, средняя и p95 латентность и токены — всего и по профилю и модели. Цвет серии стабилен. Графики следуют светлой и тёмной теме админки. Карточки сверху сравнивают окно с предыдущим периодом той же длины.',
            '**Ошибки.** Всё вне HTTP 200–299, включая 402, 429, 499, 5xx и незакрытый резерв (статус 0), пока его не сверят.',
            '**Бюджеты и топ расхода.** У каждого профиля — текущие календарные сутки и месяц против лимитов запросов и USD, с процентом использования. Счётчик запросов совпадает с правилами лимита (HTTP-ошибки кроме 499 не считаются); стоимость включает каждую строку. Фильтр по модели эти цифры не меняет. p95 считается в Python не больше чем по 20 000 самым свежим строкам.',
          ],
        },
        {
          type: 'image',
          src: 'admin-dashboard.png',
          alt: 'Django admin — панель расхода: фильтры, стоимость, запросы, доля ошибок, латентность, токены и бюджеты профилей',
          caption: 'Панель расхода: траты, ошибки и латентность за выбранный день или месяц рядом с дневным и месячным бюджетом профиля.',
        },
        {
          type: 'image',
          src: 'admin-dashboard-dark.png',
          alt: 'Django admin — панель расхода в тёмной теме: фильтры, стоимость, запросы, доля ошибок, латентность, токены и бюджеты профилей',
          caption: 'Тёмная тема: те же графики следуют переключателю темы Django admin.',
        },
        { type: 'h3', text: 'Защита API-ключа' },
        {
          type: 'list',
          items: [
            '**Шифрование.** Поле `api_key` — `EncryptedTextField`: Fernet, ключ выводится из `SECRET_KEY`.',
            '**Write-only.** После сохранения значение нельзя посмотреть — только заменить или очистить.',
            '**Альтернатива без базы.** Ключ может жить только в окружении (`OPENROUTER_API_KEY`), поле в админке остаётся пустым.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Ротация SECRET_KEY',
          text: 'Ключ Fernet выводится из `SECRET_KEY`. При смене `SECRET_KEY` сохранённые в базе API-ключи станут нечитаемыми — их нужно будет ввести заново.',
        },
        { type: 'h3', text: 'Валидации' },
        {
          type: 'list',
          items: [
            '`temperature` — только в диапазоне 0…2.',
            'Основная и fallback-модели обязаны быть активными.',
            'При `only_free_models` все модели профиля должны быть бесплатными.',
            'Пара `(profile, model)` в fallback-цепочке уникальна.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Справочник',
      title: 'API Reference',
      lead: 'Публичный импорт из django_openrouter: фасады, клиенты, результат и исключения.',
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
) -> AsyncIterator[ChatChunk]: ...

def transcribe(
    audio: bytes | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
) -> TranscriptionResult: ...

async def atranscribe(
    audio: bytes | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    language: str | None = None,
    prompt: str | None = None,
) -> TranscriptionResult: ...`,
        },
        {
          type: 'p',
          text: '`profile_name=None` использует дефолтный профиль из настроек. Вызов без `messages` — `TypeError`. Если профиль не найден или неактивен — `ConfigurationError`.',
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
    delta: str                      # текст текущего чанка
    content: str                    # накопленный текст ответа
    model_used: str = ""
    done: bool = False              # True у финального чанка
    result: ChatResult | None = None  # полный результат у финального чанка
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: 'Исключения' },
        {
          type: 'table',
          head: ['Исключение', 'Когда'],
          rows: [
            ['`OpenRouterError`', 'Базовый класс всех исключений библиотеки'],
            ['`ConfigurationError`', 'Нет ключа, профиля или дефолтного профиля; стриминг выключен'],
            ['`OpenRouterDisabled`', 'Kill switch: `enabled=False` в настройках'],
            ['`ModelDisabled`', 'Профиль/модель выключены или нарушен `only_free_models`'],
            ['`RateLimitExceeded`', 'Исчерпан лимит запросов за день/месяц'],
            ['`BudgetExceeded`', 'Исчерпан бюджет за день/месяц'],
            ['`OpenRouterAPIError`', 'Ошибка API после ретраев и fallback; несёт `status_code`'],
            ['`UnsupportedAudioFormat`', 'Аудио транскрипции не webm/ogg/mp3/wav/m4a/flac/aac'],
            ['`AudioTooLarge`', 'Аудио больше лимита профиля (по умолчанию 25 МиБ)'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'обработка ошибок',
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
          code: `stats = profile.get_usage("day")    # или "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # начало периода (datetime)`,
        },
        {
          type: 'p',
          text: 'Безопасно вызывать и внутри `transaction.atomic()`, и снаружи — обёртка создаётся автоматически. Блокировка вешается на строку профиля, а не на логи, поэтому рост таблицы `RequestLog` не взрывает блокировки.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Справочник',
      title: 'FAQ',
      lead: 'Частые вопросы и подводные камни.',
      blocks: [
        { type: 'h3', text: 'Изменения в админке не применяются' },
        {
          type: 'p',
          text: 'Скорее всего, у вас несколько процессов и `LocMemCache`: инвалидация кэша сработала только в процессе, где вы нажали «Сохранить». Переключитесь на Redis/Memcached и укажите алиас в `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '«No usage profile specified and default_profile is not set»' },
        {
          type: 'p',
          text: 'Вы вызвали `chat()` без имени профиля, а дефолтный профиль не задан. Либо передайте slug первым аргументом, либо выберите **default profile** в **OpenRouter settings**.',
        },
        { type: 'h3', text: '«Usage profile X is not found or inactive»' },
        {
          type: 'p',
          text: 'Профиля с таким slug нет или снят чекбокс `is_active`. В runtime-конфиг попадают только активные профили.',
        },
        { type: 'h3', text: 'Поддерживается ли стриминг?' },
        {
          type: 'p',
          text: 'Да. Включите **Streaming enabled** в **OpenRouter settings** и используйте `stream()` / `astream()` или `chat(stream=True)`. Обычный `chat()` без `stream=True` всегда возвращает обычный JSON-ответ.',
        },
        { type: 'h3', text: 'Лимиты не срабатывают' },
        {
          type: 'p',
          text: 'Проверьте, что `django_openrouter.log_backends.DatabaseBackend` есть в `OPENROUTER["LOG_BACKENDS"]` (по умолчанию он включён). Без этого бэкенда профиль с лимитами выдаёт `ConfigurationError`.',
        },
        { type: 'h3', text: 'Как перевести админку на мой язык?' },
        {
          type: 'p',
          text: 'Все подписи админки обёрнуты в `gettext_lazy`, а каталоги переводов для десятков локалей лежат прямо в пакете (`locale/<локаль_django>/LC_MESSAGES/django.po`). Хост-проект решает, какие языки активны: настройте `LANGUAGE_CODE` / `LANGUAGES` и подключите `LocaleMiddleware`. После правки `.po` скомпилируйте каталоги — `python manage.py compilemessages -l ru`. Учтите: английский в пакете — это `en_GB` / `en-gb`, базового каталога `en` нет.',
        },
        { type: 'h3', text: 'Как посчитать расход вручную?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Можно ли без админки?' },
        {
          type: 'p',
          text: 'Нет — в этом и смысл библиотеки: политика (модели, лимиты, бюджеты) живёт в базе и управляется оператором. Ключ при этом можно держать только в окружении.',
        },
      ],
    },
  ],
}
