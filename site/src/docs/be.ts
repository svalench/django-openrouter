import type { DocsContent } from './types'

export const be: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter для Django — мадэлі, профілі, бюджэты і логі запытаў праз адмінку',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Пошук па дакументацыі…',
    searchEmpty: 'Нічога не знойдзена. Паспрабуйце іншы запыт.',
    onThisPage: 'На гэтай старонцы',
    copied: 'Скапіравана',
    copy: 'Капіраваць',
    editGithub: 'GitHub',
    prev: 'Назад',
    next: 'Далей',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Пачаць за 3 хвіліны',
    heroGithub: 'Рэпазіторый',
    builtWith: 'Дакументацыя па праекце',
    license: 'Ліцэнзія MIT',
  },
  ui: {
    theme: 'Пераключыць тэму',
    language: 'Мова',
    openMenu: 'Адкрыць меню',
    closeMenu: 'Закрыць меню',
  },
  sections: [
    {
      id: 'intro',
      group: 'Пачатак працы',
      title: 'Уводзіны',
      lead: 'Паўторна выкарыстоўваемая Django-праграма, якая ператварае OpenRouter у кіраваны рэсурс: мадэлі, профілі выкарыстання, бюджэты і логі запытаў жывуць у базе і наладжаюцца праз адмінку — без паўторнага дэплою.',
      blocks: [
        {
          type: 'p',
          text: 'Код прадукту — пераклады, чат, рэзюмэ — звяртаецца да OpenRouter праз гэтую бібліятэку, а не праз жорстка прапісаныя ключы і ID мадэляў у `settings.py`. Аператар выбірае актыўныя мадэлі, задае дзённыя і месячныя ліміты і глядзіць выдаткі проста ў адмінцы.',
        },
        { type: 'h3', text: 'Чаму не settings.py?' },
        {
          type: 'p',
          text: 'Радок накшталт `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` у наладах азначае дэплой пры кожнай змене мадэлі, бюджэту ці аварыйным выключэнні. `django-openrouter` трымае гэтую runtime-палітыку ў базе, кэшуе яе і правярае ліміты перад кожным запытам.',
        },
        {
          type: 'list',
          items: [
            '**Каталог мадэляў у базе.** `sync_models` цягне каталог OpenRouter (`GET /api/v1/models` + `/endpoints`) з цэнамі, затрымкай p50 TTFT, прапускной здольнасцю і колькасцю параметраў.',
            '**Профілі выкарыстання.** Стабільны slug (`chat`, `translation`) → упарадкаваны ланцуг мадэляў, `max_tokens`, `temperature`, ліміты і бюджэты.',
            '**Ліміты перад запытам.** Дзённыя/месячныя ліміты запытаў і бюджэты ў USD правяраюцца перад HTTP-выклікам. Вычарпанне — гэта выключэнне, а не ціхі fallback.',
            '**Стрымінг (SSE).** `stream()` / `astream()` аддаюць адказ кавалкамі; уключаецца адным чэкбоксам у наладах.',
            '**Кожны выклік лагуецца.** Кожная спроба пішацца ў БД, JSONL-файл ці ClickHouse (падключальныя бэкенды) — разам з імем карыстальніка, які выклікаў.',
            '**Бяспечныя ключы.** API-ключ у адмінцы шыфруецца (Fernet, ад `SECRET_KEY`) і толькі для запісу: пасля захавання яго можна толькі замяніць або ачысціць.',
            '**Аварыйны выключальнік і паралелізм.** Чэкбокс `enabled` імгненна спыняе ўсе выклікі, а `max_parallel_requests` абмяжоўвае паралельныя HTTP-запыты на працэс.',
          ],
        },
        { type: 'h3', text: 'Магчымасці' },
        {
          type: 'table',
          head: ['Магчымасць', 'Статус'],
          rows: [
            ['Сінхронны і асінхронны кліенты', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Аднарадковыя фасады', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Ланцугі fallback мадэляў', 'Пры 402 / 429 / 5xx, у зададзеным парадку'],
            ['Паўторы пры памылках транспарту', 'Наладжвальны `max_retries`'],
            ['Стрымінг (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, па змаўчанні выключаны'],
            ['Бэкенды логаў', 'База (па змаўчанні), ротацыйны JSONL-файл, ClickHouse'],
            ['Ліміт паралелізму', '`max_parallel_requests`, па змаўчанні 10'],
            ['Адмінка на вашай мове', 'Каталогі перакладаў для дзясяткаў locale у пакеце'],
            ['Падказкі тыпаў', 'Пакет пастаўляецца з `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Сумяшчальнасць',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 і 6.0. Залежнасці: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Пачатак працы',
      title: 'Хуткі старт',
      lead: 'Ад усталёўкі да першага адказу мадэлі — чатыры крокі.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Усталюйце пакет',
              text: 'Адна каманда з PyPI: `pip install django-openrouter`.',
            },
            {
              title: 'Падключыце праграму і middleware',
              text: 'Дадайце `django_openrouter` у `INSTALLED_APPS` і `django_openrouter.middleware.CurrentUserMiddleware` у `MIDDLEWARE`, затым выканайце `python manage.py migrate`.',
            },
            {
              title: 'Наладзьце ў адмінцы',
              text: 'Адкрыйце **OpenRouter → OpenRouter settings**: устаўце API-ключ (ён будзе зашыфраваны) або пакіньце поле пустым і задайце `OPENROUTER_API_KEY` у асяроддзі.',
            },
            {
              title: 'Сінхранізуйце каталог і стварыце профіль',
              text: 'Выканайце `python manage.py sync_models`, затым стварыце **Usage profile** са slug `chat`, дадайце мадэлі ў парадку прыярытэту і пры жаданні зрабіце яго профілем па змаўчанні.',
            },
          ],
        },
        { type: 'h3', text: '1. Усталёўка' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Падключэнне і міграцыі' },
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
          text: '`CurrentUserMiddleware` ставіцца **пасля** `AuthenticationMiddleware` і запісвае імя карыстальніка ў лог запытаў. Без яго кожны радок пазначаецца як `anonymous`.',
        },
        { type: 'h3', text: '3. Наладка ў Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Адкрыйце **OpenRouter → OpenRouter settings**. Устаўце API-ключ — ён шыфруецца і больш не паказваецца — або пакіньце поле пустым і задайце `OPENROUTER_API_KEY` у асяроддзі.',
            'Выканайце `python manage.py sync_models`, каб падцягнуць каталог мадэляў (`GET /api/v1/models`).',
            'Стварыце **Usage profile** (slug `translation`, `chat`, …) і дадайце адну ці некалькі мадэляў у парадку прыярытэту (першая спрабуецца першай), плюс ліміты і бюджэты.',
            'Прызначце профіль **default profile**, калі хочаце выклікаць `chat(messages=...)` без імя.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Скрыншоты',
          text: 'Усе чатыры раздзелы адмінкі — налады, каталог, профілі і лог — пакрытыя скрыншотамі ў раздзеле «Адмінка».',
        },
        { type: 'h3', text: '4. Першы выклік' },
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
          title: 'Праверка без захаванага ключа',
          text: 'Каталог можна сінхранізаваць аднаразовым ключом: `python manage.py sync_models --api-key sk-or-...` — ён не захаваецца ў базе.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Даведнікі',
      title: 'Канфігурацыя',
      lead: 'Парадак пошуку API-ключа, слоўнік settings.OPENROUTER і як працуе кэш runtime-канфігурацыі.',
      blocks: [
        { type: 'h3', text: 'Адкуль бярэцца API-ключ' },
        {
          type: 'p',
          text: 'Калі поле ключа ў адмінцы пустое, бібліятэка шукае ключ у такім парадку:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (налада верхняга ўзроўню)',
            'зменная асяроддзя `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Ключ, захаваны ў адмінцы, заўсёды перамагае ўсе тры варыянты вышэй. Ён захоўваецца зашыфраваным (Fernet, ад `SECRET_KEY`) і пасля захавання нечытэльны.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Ключ', 'Па змаўчанні', 'Апісанне'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Колькі секунд трымаць runtime-канфігурацыю ў кэшы Django'],
            ['`CACHE_ALIAS`', '`"default"`', 'Аліяс кэша (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Колькі секунд адмінка не перасінхранізоўвае каталог мадэляў'],
            ['`API_KEY`', 'не зададзены', 'Рэзервовы ключ, калі поле ў адмінцы пустое'],
            ['`HTTP_REFERER`', 'не зададзены', 'Загаловак `HTTP-Referer` (атрыбуцыя праграмы ў OpenRouter)'],
            ['`X_TITLE`', 'не зададзены', 'Загаловак `X-Title`'],
            ['`LOG_BACKENDS`', 'толькі БД', 'Куды пішуцца логі запытаў — гл. раздзел «Бэкенды логаў»'],
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
          text: 'Стандартнага `LocMemCache` дастаткова. Redis ці Memcached — па жаданні: дастаткова паказаць на іх праз `CACHE_ALIAS`.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Налады жывуць у адмінцы, не ў settings.py',
          text: 'Таймаўт, колькасць паўтораў, аварыйны выключальнік, стрымінг (`streaming_enabled`) і ліміт паралельных запытаў (`max_parallel_requests`) знаходзяцца ў **OpenRouter settings** адмінкі — падрабязнасці са скрыншотам у раздзеле «Адмінка».',
        },
        { type: 'h3', text: 'Як працуе кэш' },
        {
          type: 'p',
          text: 'Кліент не чытае базу наўпрост, а кэшаваны здымак `RuntimeConfig`: налады, актыўныя профілі і іх fallback-мадэлі. Сігналы `post_save` / `post_delete` на ўсіх мадэлях праграмы імгненна інвалідуюць кэш — праўкі ў адмінцы дзейнічаюць без перазапуску, а `CACHE_TIMEOUT` — толькі страхоўка.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache і некалькі працэсаў',
          text: 'Пры `LocMemCache` кожны працэс трымае ўласную копію кэша: інвалідацыя адбываецца толькі ў тым працэсе, дзе вы захавалі ў адмінцы. Для шматпрацэсных дэплояў выкарыстоўвайце Redis/Memcached праз `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Даведнікі',
      title: 'Выкарыстанне',
      lead: 'Фасады chat() / achat() / stream() / astream(), класы кліентаў, перавызначэнні на выклік і структура выніку.',
      blocks: [
        { type: 'h3', text: 'Фасад chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # profile slug; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Сінхронны кліент' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Асінхронны выклік' },
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
          text: 'Асінхронны кліент паўтарае сінхронны: аперацыі ORM ідуць праз `sync_to_async`, HTTP — праз `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Стрымінг (SSE)' },
        {
          type: 'p',
          text: 'Стрымінг па змаўчанні выключаны. Уключыце **Streaming enabled** у **OpenRouter settings**, тады `stream()` і `astream()` аддаюць адказ кавалкамі `ChatChunk`:',
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
          text: '`chat(..., stream=True)` выкарыстоўвае той жа SSE-транспарт і вяртае поўны `ChatResult`. Калі стрымінг уключаны ў наладах, звычайны `chat()` таксама ідзе праз SSE; `stream=False` прымусова дае звычайны JSON-адказ. Выклік пры выключаным стрымінгу кідае `ConfigurationError` да любога HTTP-запыту.',
        },
        {
          type: 'table',
          head: ['Поле ChatChunk', 'Тып', 'Апісанне'],
          rows: [
            ['`delta`', '`str`', 'Тэкст бягучага кавалка'],
            ['`content`', '`str`', 'Тэкст, назапашаны дагэтуль'],
            ['`model_used`', '`str`', 'Мадэль, якая генеруе адказ'],
            ['`done`', '`bool`', '`True` на апошнім кавалку'],
            ['`result`', '`ChatResult | None`', 'Поўны вынік на апошнім кавалку'],
            ['`raw`', '`dict`', 'Сырая SSE-падзея'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback і стрымінг',
          text: 'Пераход да наступнай мадэлі магчымы толькі да адпраўкі першага кавалка. Калі мадэль пачала стрыміць і ўпала пасярэдзіне, памылка вяртаецца выклікальніку: частка адказу ўжо пайшла кліенту.',
        },
        { type: 'h3', text: 'Перавызначэнні на выклік' },
        {
          type: 'p',
          text: 'Любыя `**overrides` перадаюцца ў цела запыту. `max_tokens` і `temperature` перакрываюць значэнні профілю, а `model` часова ставіць указаную мадэль першай у ланцугу:',
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
        { type: 'h3', text: 'Паралелізм' },
        {
          type: 'p',
          text: 'Поле **Max parallel requests** у наладах (па змаўчанні `10`, `0` = без ліміту) абмяжоўвае колькасць паралельных HTTP-запытаў да OpenRouter у бягучым працэсе — і для `chat()`, і для `stream()`, сінхронна і асінхронна.',
        },
        { type: 'h3', text: 'Вынік: ChatResult' },
        {
          type: 'table',
          head: ['Поле', 'Тып', 'Апісанне'],
          rows: [
            ['`content`', '`str`', 'Тэкст адказу (тэкставыя часткі злепленыя пры шматчастковым змесце)'],
            ['`prompt_tokens`', '`int`', 'Токены промпту з `usage`'],
            ['`completion_tokens`', '`int`', 'Токены completion з `usage`'],
            ['`cost_usd`', '`Decimal`', 'Кошт: з цэн каталога, інакш `usage.cost` з API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Кошт з каталога — для звярання з білінгам'],
            ['`model_used`', '`str`', 'Мадэль, якая рэальна адказала'],
            ['`latency_ms`', '`int`', 'Затрымка паспяховай спробы'],
            ['`raw`', '`dict`', 'Сыры JSON-адказ ад OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Даведнікі',
      title: 'Каталог мадэляў',
      lead: 'Як sync_models напаўняе каталог і што захоўвае OpenRouterModel.',
      blocks: [
        { type: 'h3', text: 'Каманда sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # one-off key, never stored` },
        {
          type: 'p',
          text: 'Каманда робіць upsert каталога (`GET /api/v1/models`) і ўзбагачае яго метрыкамі `/endpoints` — затрымка p50 і прапускная здольнасць. Нічога не выдаляе: мадэлі, якія зніклі з OpenRouter, атрымліваюць `is_active=False`. Профілі, якія спасылаюцца на такую мадэль, не ламаюцца — выклікі пачынаюць падаць з `ModelDisabled`, пакуль вы не пераключыце профіль.',
        },
        { type: 'h3', text: 'Палі мадэлі' },
        {
          type: 'table',
          head: ['Поле', 'Апісанне'],
          rows: [
            ['`model_id`', 'Ідэнтыфікатар OpenRouter, напрыклад `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Чалавекачытэльная назва'],
            ['`context_length`', 'Памер кантэксту ў токенах'],
            ['`pricing`', 'JSON з цэнамі за токен: `prompt`, `completion`, апцыянальна `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Цэны за токен як decimal — для сартавання і фільтраў у адмінцы'],
            ['`latency_ms`', 'p50 TTFT найлепшага эндпоінта, у мілісекундах'],
            ['`throughput`', 'p50 прапускная здольнасць найлепшага эндпоінта, токены/с'],
            ['`parameter_count`', 'Прыблізная колькасць вагаў (70B → 70000000000), для сартавання'],
            ['`parameter_label`', 'Памер з адзінкай: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Спіс падтрыманых параметраў'],
            ['`modality`', 'Мадальнасць, напрыклад `text->text`'],
            ['`is_active`', 'Ці можна выбраць мадэль у профілях'],
            ['`last_synced_at`', 'Калі сінхранізацыя апошні раз бачыла гэтую мадэль'],
            ['`is_free` (уласнасць)', '`True`, калі цэны `prompt`/`completion`/`request` роўныя нулю'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Толькі бясплатныя мадэлі',
          text: 'Сцяг профілю `only_free_models` дазваляе толькі мадэлі з нулявой цаной у каталогу — зручна для дэвавых стэндаў і дэма. Дзейнічае і для асноўнай мадэлі, і для кожнага fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Даведнікі',
      title: 'Ліміты, бюджэты і fallback',
      lead: 'Што правяраецца перад запытам, што адбываецца пры памылках OpenRouter і калі ўключаецца fallback.',
      blocks: [
        { type: 'h3', text: 'Ліміты профілю' },
        {
          type: 'p',
          text: 'Выдаткі лічацца з `RequestLog` за бягучы каляндарны дзень і месяц (у актыўным `TIME_ZONE`). Пустое (`null`) поле ліміту азначае «без ліміту».',
        },
        {
          type: 'table',
          head: ['Поле профілю', 'Што абмяжоўвае', 'Выключэнне'],
          rows: [
            ['`max_requests_per_day`', 'Колькасць запытаў за дзень', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Колькасць запытаў за месяц', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Сума `cost_usd` за дзень', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Сума `cost_usd` за месяц', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'Праверка ідзе ў транзакцыі: радок профілю блакуецца `select_for_update`, агрэгаты лічацца пад гэтым локам — паралельныя запыты не могуць праскочыць ліміт.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Лімітам патрэбны DatabaseBackend',
          text: 'Агрэгаты лічацца з табліцы `RequestLog`, таму `DatabaseBackend` мусіць застацца ў `LOG_BACKENDS` (гэта стандарт). Калі яго прыбраць, `check_limits()` не бачыць выдаткаў і ліміты перастаюць працаваць.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Без ціхіх абходных шляхоў',
          text: 'Вычарпанне ліміту ці бюджэту — гэта выключэнне (`BudgetExceeded` / `RateLimitExceeded`) да HTTP-выкліку. Бібліятэка **не** пераключаецца на іншую мадэль, каб прапіхнуць запыт.',
        },
        { type: 'h3', text: 'Ланцуг fallback' },
        {
          type: 'p',
          text: 'Fallback-мадэлі ўключаюцца толькі калі сам OpenRouter вяртае `402`, `429` ці `5xx`. Парадак задае поле `order` у адмінцы; дублікаты ў ланцугу адкідаюцца. Мадэлі, забароненыя правіламі профілю (неактыўныя ці платныя пры `only_free_models`), прапускаюцца.',
        },
        {
          type: 'list',
          items: [
            '**Памылкі транспарту і 5xx** — паўтараюцца да `max_retries` разоў на той жа мадэлі, потым fallback.',
            '**402 / 429** — адразу пераход да наступнай мадэлі ў ланцугу.',
            '**Іншыя 4xx** (напрыклад 400) — кідаюцца адразу, без fallback: запыт, хутчэй за ўсё, няправільны для ўсіх мадэляў.',
            '**Кожная спроба** — у тым ліку няўдалая — пішацца ў лог.',
          ],
        },
        { type: 'h3', text: 'Глабальны аварыйны выключальнік' },
        {
          type: 'p',
          text: 'Чэкбокс `enabled` у **OpenRouter settings** спыняе ўсё імгненна: любы `chat()` кідае `OpenRouterDisabled` яшчэ да праверкі лімітаў. Зручна пры інцыдэнтах і планавых работах.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Даведнікі',
      title: 'Бэкенды логаў',
      lead: 'Кожны HTTP-выклік пішацца ва ўсе бэкенды з OPENROUTER["LOG_BACKENDS"]: база праекта, JSONL-файл, ClickHouse — або ваш уласны клас.',
      blocks: [
        {
          type: 'p',
          text: 'Кожны элемент спісу — гэта або кропкавы шлях да класа (стандартныя налады), або dict з ключом `BACKEND` і параметрамі. Калі `LOG_BACKENDS` не зададзены, логі пішуцца толькі ў базу праекта (`RequestLog`).',
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
        { type: 'h3', text: 'DatabaseBackend (па змаўчанні)' },
        {
          type: 'p',
          text: 'Піша радкі ў мадэль `RequestLog`. Дзённыя/месячныя ліміты і бюджэты агрэгуюцца з гэтай табліцы — пакіньце гэты бэкенд уключаным, калі карыстаецеся лімітамі: без яго `check_limits()` не бачыць выдаткаў.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines у файл з ротацыяй па памеры (`RotatingFileHandler`): адзін радок = адзін JSON-аб’ект з палямі `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Устаўляе `FORMAT JSONEachRow` праз HTTP-інтэрфейс ClickHouse. Без дадатковых залежнасцей — выкарыстоўваецца той жа `httpx`. Імёны базы і табліцы правяраюцца як ідэнтыфікатары, каб прадухіліць ін’екцыю. Табліцу стварыце так:',
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
          text: 'Кожны наладжаны бэкенд атрымлівае кожны запіс, а збой бэкенда (поўны дыск, недасягальны ClickHouse) ніколі не ламае `chat()` — памылка пішацца ў логер `django_openrouter`.',
        },
        { type: 'h3', text: 'Хто зрабіў запыт' },
        {
          type: 'p',
          text: 'Кожны запіс нясе імя карыстальніка Django, які зрабіў выклік. Яго дае `django_openrouter.middleware.CurrentUserMiddleware` (пасля `AuthenticationMiddleware`). Выклікі без карыстальніка або па-за HTTP-запытам лагуюцца як `anonymous`. У Celery і management-камандах задайце імя ўручную:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Уласны бэкенд' },
        {
          type: 'p',
          text: 'Успадкуйце `django_openrouter.log_backends.LogBackend`, рэалізуйце `write()` (і пры жаданні `awrite()`) і дадайце кропкавы шлях класа ў `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Даведнікі',
      title: 'Адмінка',
      lead: 'Уся runtime-палітыка жыве ў чатырох раздзелах Django admin: налады, каталог мадэляў, профілі выкарыстання і логі запытаў.',
      blocks: [
        {
          type: 'table',
          head: ['Раздзел', 'Што робіць'],
          rows: [
            ['**OpenRouter settings**', 'Аварыйны выключальнік, зашыфраваны API-ключ, стрымінг, таймаўты'],
            ['**OpenRouter models**', 'Каталог з OpenRouter: цана, затрымка, прапускная здольнасць'],
            ['**Usage profiles**', 'Ланцуг мадэляў, ліміты, бюджэты, статыстыка выдаткаў'],
            ['**Request logs**', 'Токены, кошт і затрымка кожнага выкліку (толькі чытанне)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Сінглтон: спіс перанакіроўвае на адзіны радок, і яго нельга выдаліць. Тут сабраныя ўсе глабальныя налады інтэграцыі:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — глабальны аварыйны выключальнік. Выключаны → кожны `chat()` / `stream()` кідае `OpenRouterDisabled`.',
            '**API key** — толькі для запісу, шыфруецца Fernet ад `SECRET_KEY`. Пустое поле захоўвае бягучы ключ; новае значэнне замяняе яго; чэкбокс **Clear stored API key** чысціць ключ з базы — тады выкарыстоўваецца `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`.',
            '**Base URL** — корань API OpenRouter (`https://openrouter.ai/api/v1`).',
            '**Default profile** — профіль, які выкарыстоўваецца, калі `chat(messages=...)` выклікаецца без імя.',
            '**Request timeout** / **Max retries** — HTTP-таймаўт і колькасць паўтораў пры памылках транспарту/5xx перад пераходам да наступнай мадэлі ў ланцугу.',
            '**Streaming enabled** — дазваляе SSE праз `stream()` / `astream()` і `chat(stream=True)`. Па змаўчанні выключана.',
            '**Max parallel requests** — ліміт паралельных HTTP-выклікаў у гэтым працэсе (`0` = без ліміту).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings: уключана, статус ключа, base url, профіль па змаўчанні, таймаўт, паўторы, стрымінг, ліміт паралелізму',
          caption: 'OpenRouter settings: аварыйны выключальнік, API-ключ толькі для запісу, профіль па змаўчанні, таймаўты, стрымінг і ліміт паралелізму.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'Каталог з `GET /api/v1/models` плюс метрыкі `/endpoints` (затрымка і прапускная здольнасць). Радкі нельга дадаваць ці выдаляць уручную, картка мадэлі — толькі для чытання.',
        },
        {
          type: 'list',
          items: [
            '**Калонкі:** назва, `latency_ms` (p50 TTFT), прапускная здольнасць (токены/с), цэны prompt/completion за 1M токенаў, памер вагаў (`70B` / `8x7B`), `is_active`. Сартаванне клікам, пустыя значэнні заўсёды ў канцы.',
            '**Фільтры:** актыўнасць, мадальнасць, цана (бясплатныя / < $1 / $1–10 / ≥ $10 за 1M), хуткасць (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (дзеянне) — upsert каталога; зніклыя мадэлі атрымліваюць `is_active=False`.',
            '**Assign to usage profile…** (дзеянне) — дапісвае выбраныя мадэлі ў канец ланцуга профілю; дублікаты, неактыўныя і платныя мадэлі (пры `only_free_models`) прапускаюцца са справаздачай.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Пры першым адкрыцці спіс абнаўляецца з API, потым 10 хвілін аддаецца з базы (`CATALOG_CACHE_TIMEOUT`). Тая ж сінхранізацыя з кансолі: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — каталог мадэляў OpenRouter: назва, затрымка, прапускная здольнасць, цана за 1M, памер вагаў, актыўнасць; фільтры справа',
          caption: 'Каталог мадэляў: сартаванне па цане/затрымцы, фільтры цаны і хуткасці, дзеянні сінхранізацыі і прызначэння ў профіль.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Профіль — гэта slug, які перадае ваш код (`chat`, `translation`, …), плюс упарадкаваны спіс мадэляў: першая спрабуецца першай, астатнія — fallback пры `402` / `429` / `5xx`. Вычарпаныя ліміты кідаюць выключэнне замест ціхай змены мадэлі.',
        },
        {
          type: 'list',
          items: [
            '**Спіс профіляў:** назва, асноўная мадэль, актыўнасць, толькі-бясплатныя, дзённыя ліміты запытаў/бюджэту і агрэгаты з лога — колькасць запытаў, сярэдняя і сумарная затрымка, сярэдні і сумарны кошт (адзін GROUP BY на старонку).',
            '**Форма:** `max_tokens`, `temperature` (0–2), дзённыя/месячныя ліміты запытаў і USD (пустае = без ліміту), **only free models**, **is active**.',
            '**Models (priority order) inline:** аўтадапаўненне па каталогу — цана і затрымка ў подпісе, тыя ж фільтры цаны/хуткасці, што ў каталогу. Парадак пералічваецца пры захаванні, а першая мадэль ланцуга сінхранізуецца ў поле `model`.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — спіс профіляў выкарыстання з агрэгатамі запытаў, затрымкі і кошту',
          caption: 'Профілі выкарыстання: ланцуг мадэляў, ліміты і агрэгаты выдаткаў проста ў спісе.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Лог толькі для чытання. Кожная HTTP-спроба (у тым ліку fallback і памылкі) становіцца радком, калі ўключаны `DatabaseBackend` (па змаўчанні). Дзённыя і месячныя ліміты агрэгуюцца з гэтай табліцы.',
        },
        {
          type: 'list',
          items: [
            '**Калонкі:** час, імя карыстальніка, профіль, мадэль, HTTP-статус, токены prompt/completion, кошт, затрымка.',
            '**Зводка над табліцай:** колькасць запытаў і сума USD для бягучага фільтра. Фільтры: профіль, статус, дата; пошук па тэксце памылкі і імені карыстальніка.',
            '**Username** дае `CurrentUserMiddleware`; без яго радкі пазначаюцца `anonymous`. У Celery і management-камандах — `bound_username("worker")` (гл. «Бэкенды логаў»).',
            '**Правы:** асобны дазвол `view_usage_logs` дазваляе даць падтрымцы доступ да выдаткаў без доступу да налад.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — лог запытаў: час, карыстальнік, профіль, мадэль, статус, токены, кошт, затрымка; зводка зверху',
          caption: 'Логі запытаў: кожная спроба з токенамі, коштам і затрымкай, са зводкай фільтра над табліцай.',
        },
        { type: 'h3', text: 'Ахова API-ключа' },
        {
          type: 'list',
          items: [
            '**Шыфраванне.** Поле `api_key` — гэта `EncryptedTextField`: Fernet, ключ ад `SECRET_KEY`.',
            '**Толькі для запісу.** Пасля захавання значэнне нельга паглядзець — толькі замяніць або ачысціць.',
            '**Альтэрнатыва без базы.** Ключ можа жыць толькі ў асяроддзі (`OPENROUTER_API_KEY`), а поле ў адмінцы застаецца пустым.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Ротацыя SECRET_KEY',
          text: 'Ключ Fernet выводзіцца з `SECRET_KEY`. Змена `SECRET_KEY` робіць API-ключы ў базе нечытэльнымі — іх трэба ўвесці зноў.',
        },
        { type: 'h3', text: 'Праверкі' },
        {
          type: 'list',
          items: [
            '`temperature` — толькі ў межах 0…2.',
            'Асноўная і fallback-мадэлі мусяць быць актыўнымі.',
            'Пры `only_free_models` усе мадэлі ў профілі мусяць быць бясплатнымі.',
            'Пара `(profile, model)` у ланцугу fallback унікальная.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Даведка',
      title: 'API Reference',
      lead: 'Публічныя імпарты з django_openrouter: фасады, кліенты, вынік і выключэнні.',
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
          text: '`profile_name=None` выкарыстоўвае профіль па змаўчанні з налад. Выклік без `messages` — гэта `TypeError`. Калі профіль не знойдзены або неактыўны — `ConfigurationError`.',
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
        { type: 'h3', text: 'Выключэнні' },
        {
          type: 'table',
          head: ['Выключэнне', 'Калі'],
          rows: [
            ['`OpenRouterError`', 'Базавы клас усіх выключэнняў бібліятэкі'],
            ['`ConfigurationError`', 'Няма ключа, профілю ці профілю па змаўчанні; стрымінг выключаны'],
            ['`OpenRouterDisabled`', 'Аварыйны выключальнік: `enabled=False` у наладах'],
            ['`ModelDisabled`', 'Профіль/мадэль неактыўныя або парушаюць `only_free_models`'],
            ['`RateLimitExceeded`', 'Вычарпаны дзённы/месячны ліміт запытаў'],
            ['`BudgetExceeded`', 'Вычарпаны дзённы/месячны бюджэт'],
            ['`OpenRouterAPIError`', 'Памылка API пасля паўтораў і fallback; нясе `status_code`'],
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
          text: 'Бяспечна выклікаць і ўнутры, і па-за `transaction.atomic()` — абгортка ствараецца аўтаматычна. Лок бярэцца на радку профілю, не на логах, таму растучая табліца `RequestLog` не раздзімае блакіроўкі.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Даведка',
      title: 'FAQ',
      lead: 'Частыя пытанні і пасткі.',
      blocks: [
        { type: 'h3', text: 'Змены ў адмінцы не прымяняюцца' },
        {
          type: 'p',
          text: 'Хутчэй за ўсё вы запускаеце некалькі працэсаў з `LocMemCache`: інвалідацыя кэша адбылася толькі ў тым працэсе, дзе вы націснулі «Save». Пераключыцеся на Redis/Memcached і задайце аліяс у `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '“No usage profile specified and default_profile is not set”' },
        {
          type: 'p',
          text: 'Вы выклікалі `chat()` без імя профілю і профіль па змаўчанні не зададзены. Альбо перадайце slug першым аргументам, альбо выберыце **default profile** у **OpenRouter settings**.',
        },
        { type: 'h3', text: '“Usage profile X is not found or inactive”' },
        {
          type: 'p',
          text: 'Няма профілю з такім slug, або яго чэкбокс `is_active` выключаны. У runtime-канфігурацыю трапляюць толькі актыўныя профілі.',
        },
        { type: 'h3', text: 'Ці падтрымліваецца стрымінг?' },
        {
          type: 'p',
          text: 'Так. Уключыце **Streaming enabled** у **OpenRouter settings** і карыстайцеся `stream()` / `astream()` або `chat(stream=True)`. Пры ўключаным стрымінгу звычайны `chat()` таксама ідзе праз SSE; `stream=False` прымусова дае JSON-адказ.',
        },
        { type: 'h3', text: 'Ліміты не спрацоўваюць' },
        {
          type: 'p',
          text: 'Праверце, што `django_openrouter.log_backends.DatabaseBackend` ёсць у `OPENROUTER["LOG_BACKENDS"]` (па змаўчанні ёсць): ліміты і бюджэты агрэгуюцца з табліцы `RequestLog`, і без гэтага бэкенда праверкі не бачаць выдаткаў.',
        },
        { type: 'h3', text: 'Як зрабіць адмінку на сваёй мове?' },
        {
          type: 'p',
          text: 'Усе подпісы адмінкі абгорнутыя ў `gettext_lazy`, а каталогі перакладаў для дзясяткаў locale пастаўляюцца ў пакеце (`locale/<locale_django>/LC_MESSAGES/django.po`). Хост-праект вырашае, якія мовы актыўныя: наладзьце `LANGUAGE_CODE` / `LANGUAGES` і падключыце `LocaleMiddleware`. Пасля праўкі `.po` скампілюйце каталогі — `python manage.py compilemessages -l be`. Увага: англійская ў пакеце — гэта `en_GB` / `en-gb`; базавага каталога `en` няма.',
        },
        { type: 'h3', text: 'Як палічыць выдаткі ўручную?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Ці можна карыстацца без адмінкі?' },
        {
          type: 'p',
          text: 'Не — у гэтым і сэнс бібліятэкі: палітыка (мадэлі, ліміты, бюджэты) жыве ў базе і кіруецца аператарам. Ключ, аднак, можа жыць толькі ў асяроддзі.',
        },
      ],
    },
  ],
}
