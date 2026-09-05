import type { DocsContent } from './types'

export const pl: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter dla Django — modele, profile, budżety i logi żądań zarządzane z panelu admina',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Szukaj w dokumentacji…',
    searchEmpty: 'Nic nie znaleziono. Spróbuj innego zapytania.',
    onThisPage: 'Na tej stronie',
    copied: 'Skopiowano',
    copy: 'Kopiuj',
    editGithub: 'GitHub',
    prev: 'Wstecz',
    next: 'Dalej',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Zacznij w 3 minuty',
    heroGithub: 'Repozytorium',
    builtWith: 'Dokumentacja projektu',
    license: 'Licencja MIT',
  },
  ui: {
    theme: 'Przełącz motyw',
    language: 'Język',
    openMenu: 'Otwórz menu',
    closeMenu: 'Zamknij menu',
  },
  sections: [
    {
      id: 'intro',
      group: 'Pierwsze kroki',
      title: 'Wprowadzenie',
      lead: 'Wielokrotnego użytku aplikacja Django, która zamienia OpenRouter w zasób zarządzany: modele, profile użycia, budżety i logi żądań żyją w bazie i konfiguruje się je w adminie — bez redeployu.',
      blocks: [
        {
          type: 'p',
          text: 'Kod produktu — tłumaczenia, czat, streszczenia — rozmawia z OpenRouterem przez tę bibliotekę, zamiast trzymać klucze i ID modeli na sztywno w `settings.py`. Operator wybiera aktywne modele, ustawia limity dzienne i miesięczne i ogląda wydatki wprost w adminie.',
        },
        { type: 'h3', text: 'Dlaczego nie settings.py?' },
        {
          type: 'p',
          text: 'Linia `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` w ustawieniach oznacza deploy przy każdej zmianie modelu, budżetu albo awaryjnym wyłączeniu. `django-openrouter` trzyma tę politykę runtime w bazie, cache’uje ją i sprawdza limity przed każdym żądaniem.',
        },
        {
          type: 'list',
          items: [
            '**Katalog modeli w bazie.** `sync_models` pobiera katalog OpenRouter (`GET /api/v1/models` + `/endpoints`) z cenami, opóźnieniem p50 TTFT, przepustowością i liczbą parametrów.',
            '**Profile użycia.** Stabilny slug (`chat`, `translation`) → uporządkowany łańcuch modeli, `max_tokens`, `temperature`, limity i budżety.',
            '**Limity przed żądaniem.** Dzienne/miesięczne limity żądań i budżety USD są sprawdzane przed wywołaniem HTTP. Wyczerpanie to wyjątek, nie cichy fallback.',
            '**Streaming (SSE).** `stream()` / `astream()` oddają odpowiedź w kawałkach; włącza się jednym checkboxem w ustawieniach.',
            '**Każde wywołanie jest logowane.** Każda próba trafia do bazy, pliku JSONL albo ClickHouse (podłączane backendy) — razem z nazwą użytkownika, który wywołał.',
            '**Bezpieczne klucze.** Klucz API w adminie jest szyfrowany (Fernet, pochodny od `SECRET_KEY`) i tylko do zapisu: po zapisie można go tylko zastąpić albo wyczyścić.',
            '**Kill switch i równoległość.** Checkbox `enabled` natychmiast zatrzymuje wszystkie wywołania, a `max_parallel_requests` ogranicza równoległe żądania HTTP na proces.',
          ],
        },
        { type: 'h3', text: 'Funkcje' },
        {
          type: 'table',
          head: ['Funkcja', 'Status'],
          rows: [
            ['Klient synchroniczny i asynchroniczny', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Fasady w jednej linii', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Łańcuchy fallback modeli', 'Przy 402 / 429 / 5xx, w skonfigurowanej kolejności'],
            ['Ponowienia błędów transportu', 'Konfigurowalne `max_retries`'],
            ['Streaming (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, domyślnie wyłączony'],
            ['Backendy logów', 'Baza (domyślnie), rotujący plik JSONL, ClickHouse'],
            ['Limit równoległości', '`max_parallel_requests`, domyślnie 10'],
            ['Admin w Twoim języku', 'Katalogi tłumaczeń dla kilkudziesięciu locale w paczce'],
            ['Podpowiedzi typów', 'Paczka zawiera `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Zgodność',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 i 6.0. Zależności: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Pierwsze kroki',
      title: 'Szybki start',
      lead: 'Od instalacji do pierwszej odpowiedzi modelu — cztery kroki.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Zainstaluj paczkę',
              text: 'Jedna komenda z PyPI: `pip install django-openrouter`.',
            },
            {
              title: 'Podłącz aplikację i middleware',
              text: 'Dodaj `django_openrouter` do `INSTALLED_APPS` oraz `django_openrouter.middleware.CurrentUserMiddleware` do `MIDDLEWARE`, potem uruchom `python manage.py migrate`.',
            },
            {
              title: 'Skonfiguruj w adminie',
              text: 'Otwórz **OpenRouter → OpenRouter settings**: wklej klucz API (zostanie zaszyfrowany) albo zostaw pole puste i ustaw `OPENROUTER_API_KEY` w środowisku.',
            },
            {
              title: 'Zsynchronizuj katalog i utwórz profil',
              text: 'Uruchom `python manage.py sync_models`, potem utwórz **Usage profile** ze slugiem `chat`, dodaj modele w kolejności priorytetu i opcjonalnie ustaw go jako profil domyślny.',
            },
          ],
        },
        { type: 'h3', text: '1. Instalacja' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Podłączenie i migracje' },
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
          text: '`CurrentUserMiddleware` idzie **po** `AuthenticationMiddleware` i zapisuje nazwę użytkownika w logu żądań. Bez niego każdy wiersz jest oznaczany jako `anonymous`.',
        },
        { type: 'h3', text: '3. Konfiguracja w Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Otwórz **OpenRouter → OpenRouter settings**. Wklej klucz API — jest szyfrowany i nigdy więcej nie jest wyświetlany — albo zostaw pole puste i ustaw `OPENROUTER_API_KEY` w środowisku.',
            'Uruchom `python manage.py sync_models`, żeby pobrać katalog modeli (`GET /api/v1/models`).',
            'Utwórz **Usage profile** (slug `translation`, `chat`, …) i dodaj jeden lub więcej modeli w kolejności priorytetu (pierwszy jest próbowany jako pierwszy), plus limity i budżety.',
            'Ustaw profil jako **default profile**, jeśli chcesz wywoływać `chat(messages=...)` bez nazwy.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Zrzuty ekranu',
          text: 'Wszystkie cztery sekcje admina — ustawienia, katalog, profile i log — są opisane ze zrzutami w sekcji „Admin”.',
        },
        { type: 'h3', text: '4. Pierwsze wywołanie' },
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
          title: 'Sprawdź bez zapisanego klucza',
          text: 'Katalog można zsynchronizować kluczem jednorazowym: `python manage.py sync_models --api-key sk-or-...` — nie zostanie zapisany w bazie.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Przewodniki',
      title: 'Konfiguracja',
      lead: 'Kolejność rozwiązywania klucza API, słownik settings.OPENROUTER i działanie cache konfiguracji runtime.',
      blocks: [
        { type: 'h3', text: 'Skąd bierze się klucz API' },
        {
          type: 'p',
          text: 'Jeśli pole klucza w adminie jest puste, biblioteka szuka klucza w tej kolejności:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (ustawienie najwyższego poziomu)',
            'zmienna środowiskowa `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Klucz zapisany w adminie zawsze wygrywa z trzema opcjami powyżej. Jest przechowywany zaszyfrowany (Fernet, pochodny od `SECRET_KEY`) i po zapisie nieczytelny.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Klucz', 'Domyślnie', 'Opis'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Ile sekund trzymać konfigurację runtime w cache Django'],
            ['`CACHE_ALIAS`', '`"default"`', 'Alias cache (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Ile sekund admin pomija ponowną synchronizację katalogu modeli'],
            ['`API_KEY`', 'nieustawione', 'Klucz zapasowy, gdy pole w adminie jest puste'],
            ['`HTTP_REFERER`', 'nieustawione', 'Nagłówek `HTTP-Referer` (atrybucja aplikacji w OpenRouter)'],
            ['`X_TITLE`', 'nieustawione', 'Nagłówek `X-Title`'],
            ['`LOG_BACKENDS`', 'tylko DB', 'Gdzie zapisywane są logi żądań — zobacz sekcję „Backendy logów”'],
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
          text: 'Wbudowany `LocMemCache` wystarczy. Redis albo Memcached są opcjonalne — wystarczy wskazać je przez `CACHE_ALIAS`.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Ustawienia żyją w adminie, nie w settings.py',
          text: 'Timeout, liczba ponowień, kill switch, streaming (`streaming_enabled`) i limit równoległych żądań (`max_parallel_requests`) są w **OpenRouter settings** w adminie — szczegóły ze zrzutem w sekcji „Admin”.',
        },
        { type: 'h3', text: 'Jak działa cache' },
        {
          type: 'p',
          text: 'Klient nie czyta bazy bezpośrednio, tylko cache’owany snapshot `RuntimeConfig`: ustawienia, aktywne profile i ich modele fallback. Sygnały `post_save` / `post_delete` na wszystkich modelach aplikacji natychmiast unieważniają cache — edycje w adminie działają bez restartu, a `CACHE_TIMEOUT` to tylko siatka bezpieczeństwa.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache i wiele procesów',
          text: 'Przy `LocMemCache` każdy proces trzyma własną kopię cache: unieważnienie następuje tylko w procesie, w którym zapisałeś w adminie. Przy wdrożeniach wieloprocesowych użyj Redis/Memcached przez `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Przewodniki',
      title: 'Użycie',
      lead: 'Fasady chat() / achat() / stream() / astream(), klasy klientów, nadpisania per wywołanie i struktura wyniku.',
      blocks: [
        { type: 'h3', text: 'Fasada chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # profile slug; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Klient synchroniczny' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Wywołanie asynchroniczne' },
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
          text: 'Klient asynchroniczny odwzorowuje synchroniczny: operacje ORM idą przez `sync_to_async`, HTTP przez `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Streaming (SSE)' },
        {
          type: 'p',
          text: 'Streaming jest domyślnie wyłączony. Włącz **Streaming enabled** w **OpenRouter settings**, wtedy `stream()` i `astream()` oddają odpowiedź jako kawałki `ChatChunk`:',
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
          text: '`chat(..., stream=True)` używa tego samego transportu SSE i zwraca pełny `ChatResult`. Jeśli streaming jest włączony w ustawieniach, zwykłe `chat()` też idzie przez SSE; `stream=False` wymusza zwykłą odpowiedź JSON. Wywołanie przy wyłączonym streamingu rzuca `ConfigurationError` przed jakimkolwiek żądaniem HTTP.',
        },
        {
          type: 'table',
          head: ['Pole ChatChunk', 'Typ', 'Opis'],
          rows: [
            ['`delta`', '`str`', 'Tekst bieżącego kawałka'],
            ['`content`', '`str`', 'Tekst zebrany dotychczas'],
            ['`model_used`', '`str`', 'Model generujący odpowiedź'],
            ['`done`', '`bool`', '`True` na ostatnim kawałku'],
            ['`result`', '`ChatResult | None`', 'Pełny wynik na ostatnim kawałku'],
            ['`raw`', '`dict`', 'Surowe zdarzenie SSE'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback i streaming',
          text: 'Przejście do następnego modelu jest możliwe tylko przed wysłaniem pierwszego kawałka. Jeśli model zacznie streamować i padnie w trakcie, błąd wraca do wywołującego: część odpowiedzi już poszła do klienta.',
        },
        { type: 'h3', text: 'Nadpisania per wywołanie' },
        {
          type: 'p',
          text: 'Dowolne `**overrides` są przekazywane do ciała żądania. `max_tokens` i `temperature` nadpisują wartości profilu, a `model` tymczasowo stawia dany model na początku łańcucha:',
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
        { type: 'h3', text: 'Równoległość' },
        {
          type: 'p',
          text: 'Pole **Max parallel requests** w ustawieniach (domyślnie `10`, `0` = bez limitu) ogranicza liczbę równoległych żądań HTTP do OpenRouter w bieżącym procesie — zarówno dla `chat()`, jak i `stream()`, sync i async.',
        },
        { type: 'h3', text: 'Wynik: ChatResult' },
        {
          type: 'table',
          head: ['Pole', 'Typ', 'Opis'],
          rows: [
            ['`content`', '`str`', 'Tekst odpowiedzi (części tekstowe połączone przy treści wieloczęściowej)'],
            ['`prompt_tokens`', '`int`', 'Tokeny promptu z `usage`'],
            ['`completion_tokens`', '`int`', 'Tokeny completion z `usage`'],
            ['`cost_usd`', '`Decimal`', 'Koszt: z cen katalogu, w przeciwnym razie `usage.cost` z API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Koszt z katalogu — do uzgodnienia z billingiem'],
            ['`model_used`', '`str`', 'Model, który faktycznie odpowiedział'],
            ['`latency_ms`', '`int`', 'Opóźnienie udanej próby'],
            ['`raw`', '`dict`', 'Surowa odpowiedź JSON z OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Przewodniki',
      title: 'Katalog modeli',
      lead: 'Jak sync_models wypełnia katalog i co przechowuje OpenRouterModel.',
      blocks: [
        { type: 'h3', text: 'Polecenie sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # one-off key, never stored` },
        {
          type: 'p',
          text: 'Polecenie upsertuje katalog (`GET /api/v1/models`) i wzbogaca go metrykami `/endpoints` — opóźnienie p50 i przepustowość. Nigdy nic nie usuwa: modele, które zniknęły z OpenRouter, dostają `is_active=False`. Profile wskazujące taki model się nie psują — wywołania zaczynają kończyć się `ModelDisabled`, dopóki nie zmienisz profilu.',
        },
        { type: 'h3', text: 'Pola modelu' },
        {
          type: 'table',
          head: ['Pole', 'Opis'],
          rows: [
            ['`model_id`', 'Identyfikator OpenRouter, np. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Nazwa czytelna dla człowieka'],
            ['`context_length`', 'Rozmiar kontekstu w tokenach'],
            ['`pricing`', 'JSON z cenami za token: `prompt`, `completion`, opcjonalnie `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Ceny za token jako decimal — do sortowania i filtrów w adminie'],
            ['`latency_ms`', 'p50 TTFT najlepszego endpointu, w milisekundach'],
            ['`throughput`', 'p50 przepustowość najlepszego endpointu, tokeny/s'],
            ['`parameter_count`', 'Przybliżona liczba wag (70B → 70000000000), do sortowania'],
            ['`parameter_label`', 'Rozmiar z jednostką: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Lista obsługiwanych parametrów'],
            ['`modality`', 'Modalność, np. `text->text`'],
            ['`is_active`', 'Czy model można wybrać w profilach'],
            ['`last_synced_at`', 'Kiedy synchronizacja ostatnio widziała ten model'],
            ['`is_free` (właściwość)', '`True`, jeśli ceny `prompt`/`completion`/`request` są zerowe'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Tylko darmowe modele',
          text: 'Flaga profilu `only_free_models` dopuszcza wyłącznie modele z zerową ceną w katalogu — przydatne na standach deweloperskich i demo. Obowiązuje zarówno dla modelu głównego, jak i każdego fallbacku.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Przewodniki',
      title: 'Limity, budżety i fallback',
      lead: 'Co jest sprawdzane przed żądaniem, co się dzieje przy błędach OpenRouter i kiedy włącza się fallback.',
      blocks: [
        { type: 'h3', text: 'Limity profilu' },
        {
          type: 'p',
          text: 'Wydatki liczone są z `RequestLog` za bieżący dzień i miesiąc kalendarzowy (w aktywnym `TIME_ZONE`). Puste (`null`) pole limitu oznacza „bez limitu”.',
        },
        {
          type: 'table',
          head: ['Pole profilu', 'Co ogranicza', 'Wyjątek'],
          rows: [
            ['`max_requests_per_day`', 'Liczba żądań dziennie', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Liczba żądań miesięcznie', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Suma `cost_usd` dziennie', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Suma `cost_usd` miesięcznie', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'Sprawdzenie działa w transakcji: wiersz profilu jest blokowany `select_for_update`, a agregaty liczone pod tym lockiem — równoległe żądania nie mogą wyścignąć limitu.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Limity wymagają DatabaseBackend',
          text: 'Agregaty liczone są z tabeli `RequestLog`, więc `DatabaseBackend` musi zostać w `LOG_BACKENDS` (to domyślne). Jeśli go usuniesz, `check_limits()` nie widzi wydatków i limity przestają działać.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Bez cichych obejść',
          text: 'Wyczerpanie limitu albo budżetu to wyjątek (`BudgetExceeded` / `RateLimitExceeded`) rzucany przed wywołaniem HTTP. Biblioteka **nie** przełącza na inny model, żeby przepchnąć żądanie.',
        },
        { type: 'h3', text: 'Łańcuch fallback' },
        {
          type: 'p',
          text: 'Modele fallback włączają się tylko, gdy sam OpenRouter zwraca `402`, `429` albo `5xx`. Kolejność ustawia pole `order` w adminie; duplikaty w łańcuchu są usuwane. Modele zabronione przez reguły profilu (nieaktywne albo płatne przy `only_free_models`) są pomijane.',
        },
        {
          type: 'list',
          items: [
            '**Błędy transportu i 5xx** — ponawiane do `max_retries` razy na tym samym modelu, potem fallback.',
            '**402 / 429** — natychmiast przejście do następnego modelu w łańcuchu.',
            '**Inne 4xx** (np. 400) — rzucane od razu, bez fallbacku: żądanie jest prawdopodobnie niepoprawne dla wszystkich modeli.',
            '**Każda próba** — w tym nieudane — trafia do logu.',
          ],
        },
        { type: 'h3', text: 'Globalny kill switch' },
        {
          type: 'p',
          text: 'Checkbox `enabled` w **OpenRouter settings** zatrzymuje wszystko natychmiast: każde `chat()` rzuca `OpenRouterDisabled` zanim limity w ogóle zostaną sprawdzone. Przydatne przy incydentach i planowanych pracach.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Przewodniki',
      title: 'Backendy logów',
      lead: 'Każde wywołanie HTTP jest zapisywane do wszystkich backendów z OPENROUTER["LOG_BACKENDS"]: baza projektu, plik JSONL, ClickHouse — albo Twoja klasa.',
      blocks: [
        {
          type: 'p',
          text: 'Każdy wpis na liście to albo ścieżka kropkowana do klasy (ustawienia domyślne), albo dict z kluczem `BACKEND` i parametrami. Jeśli `LOG_BACKENDS` nie jest ustawione, logi idą tylko do bazy projektu (`RequestLog`).',
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
        { type: 'h3', text: 'DatabaseBackend (domyślny)' },
        {
          type: 'p',
          text: 'Zapisuje wiersze do modelu `RequestLog`. Limity i budżety dzienne/miesięczne agregują z tej tabeli — zostaw ten backend włączony, jeśli używasz limitów: bez niego `check_limits()` nie widzi wydatków.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines do pliku z rotacją po rozmiarze (`RotatingFileHandler`): jedna linia = jeden obiekt JSON z polami `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Wstawia `FORMAT JSONEachRow` przez interfejs HTTP ClickHouse. Bez dodatkowych zależności — używany jest ten sam `httpx`. Nazwy bazy i tabeli są walidowane jako identyfikatory, żeby zapobiec injekcji. Tabelę utwórz tak:',
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
          text: 'Każdy skonfigurowany backend dostaje każdy rekord, a awaria backendu (pełny dysk, niedostępny ClickHouse) nigdy nie psuje `chat()` — błąd trafia do loggera `django_openrouter`.',
        },
        { type: 'h3', text: 'Kto wykonał żądanie' },
        {
          type: 'p',
          text: 'Każdy rekord niesie nazwę użytkownika Django, który wykonał wywołanie. Dostarcza ją `django_openrouter.middleware.CurrentUserMiddleware` (po `AuthenticationMiddleware`). Wywołania bez użytkownika albo poza żądaniem HTTP są logowane jako `anonymous`. W Celery i komendach management ustaw nazwę ręcznie:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Własny backend' },
        {
          type: 'p',
          text: 'Odziedzicz `django_openrouter.log_backends.LogBackend`, zaimplementuj `write()` (i opcjonalnie `awrite()`) i dodaj ścieżkę kropkowaną klasy do `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Przewodniki',
      title: 'Admin',
      lead: 'Cała polityka runtime mieszka w czterech sekcjach Django admin: ustawienia, katalog modeli, profile użycia i logi żądań.',
      blocks: [
        {
          type: 'table',
          head: ['Sekcja', 'Co robi'],
          rows: [
            ['**OpenRouter settings**', 'Kill switch, zaszyfrowany klucz API, streaming, timeouty'],
            ['**OpenRouter models**', 'Katalog z OpenRouter: cena, opóźnienie, przepustowość'],
            ['**Usage profiles**', 'Łańcuch modeli, limity, budżety, statystyki wydatków'],
            ['**Request logs**', 'Tokeny, koszt i opóźnienie każdego wywołania (tylko odczyt)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Singleton: lista przekierowuje do jedynego wiersza i nie da się go usunąć. Tutaj zebrane są wszystkie globalne ustawienia integracji:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — globalny kill switch. Wyłączony → każde `chat()` / `stream()` rzuca `OpenRouterDisabled`.',
            '**API key** — tylko do zapisu, szyfrowany Fernet pochodnym od `SECRET_KEY`. Puste pole zachowuje bieżący klucz; nowa wartość go zastępuje; checkbox **Clear stored API key** czyści klucz z bazy — wtedy używane jest `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`.',
            '**Base URL** — korzeń API OpenRouter (`https://openrouter.ai/api/v1`).',
            '**Default profile** — profil używany, gdy `chat(messages=...)` jest wywoływane bez nazwy.',
            '**Request timeout** / **Max retries** — timeout HTTP i liczba ponowień przy błędach transportu/5xx przed przejściem do następnego modelu w łańcuchu.',
            '**Streaming enabled** — pozwala na SSE przez `stream()` / `astream()` i `chat(stream=True)`. Domyślnie wyłączone.',
            '**Max parallel requests** — limit równoległych wywołań HTTP w tym procesie (`0` = bez limitu).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings: włączone, status klucza, base url, profil domyślny, timeout, ponowienia, streaming, limit równoległości',
          caption: 'OpenRouter settings: kill switch, klucz API tylko do zapisu, profil domyślny, timeouty, streaming i limit równoległości.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'Katalog z `GET /api/v1/models` plus metryki `/endpoints` (opóźnienie i przepustowość). Wierszy nie da się dodać ani usunąć ręcznie, karta modelu jest tylko do odczytu.',
        },
        {
          type: 'list',
          items: [
            '**Kolumny:** nazwa, `latency_ms` (p50 TTFT), przepustowość (tokeny/s), ceny prompt/completion za 1M tokenów, rozmiar wag (`70B` / `8x7B`), `is_active`. Sortowanie kliknięciem, puste wartości zawsze na końcu.',
            '**Filtry:** aktywność, modalność, cena (darmowe / < $1 / $1–10 / ≥ $10 za 1M), prędkość (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (akcja) — upsertuje katalog; zniknięte modele dostają `is_active=False`.',
            '**Assign to usage profile…** (akcja) — dopisuje wybrane modele na koniec łańcucha profilu; duplikaty, nieaktywne i płatne modele (przy `only_free_models`) są pomijane z raportem.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Przy pierwszym otwarciu lista jest odświeżana z API, potem przez 10 minut serwowana z bazy (`CATALOG_CACHE_TIMEOUT`). Ta sama synchronizacja z konsoli: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — katalog modeli OpenRouter: nazwa, opóźnienie, przepustowość, cena za 1M, rozmiar wag, aktywność; filtry po prawej',
          caption: 'Katalog modeli: sortowanie po cenie/opóźnieniu, filtry ceny i prędkości, akcje synchronizacji i przypisania do profilu.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Profil to slug, który przekazuje Twój kod (`chat`, `translation`, …), plus uporządkowana lista modeli: pierwszy jest próbowany jako pierwszy, reszta to fallback przy `402` / `429` / `5xx`. Wyczerpane limity rzucają wyjątek zamiast cicho zmieniać model.',
        },
        {
          type: 'list',
          items: [
            '**Lista profili:** nazwa, model główny, aktywność, tylko-darmowe, dzienne limity żądań/budżetu i agregaty z logu — liczba żądań, średnie i łączne opóźnienie, średni i łączny koszt (jeden GROUP BY na stronę).',
            '**Formularz:** `max_tokens`, `temperature` (0–2), dzienne/miesięczne limity żądań i USD (puste = bez limitu), **only free models**, **is active**.',
            '**Models (priority order) inline:** autouzupełnianie po katalogu — cena i opóźnienie w etykiecie, te same filtry ceny/prędkości co w katalogu. Kolejność jest renormalizowana przy zapisie, a pierwszy model łańcucha synchronizowany do pola `model`.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — lista profili użycia z agregatami żądań, opóźnienia i kosztu',
          caption: 'Profile użycia: łańcuch modeli, limity i agregaty wydatków wprost na liście.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Log tylko do odczytu. Każda próba HTTP (w tym fallbacki i błędy) staje się wierszem, gdy włączony jest `DatabaseBackend` (domyślnie). Limity dzienne i miesięczne agregują z tej tabeli.',
        },
        {
          type: 'list',
          items: [
            '**Kolumny:** czas, nazwa użytkownika, profil, model, status HTTP, tokeny prompt/completion, koszt, opóźnienie.',
            '**Podsumowanie nad tabelą:** liczba żądań i suma USD dla bieżącego filtra. Filtry: profil, status, data; wyszukiwanie po tekście błędu i nazwie użytkownika.',
            '**Username** dostarcza `CurrentUserMiddleware`; bez niego wiersze są `anonymous`. W Celery i komendach management — `bound_username("worker")` (zobacz „Backendy logów”).',
            '**Uprawnienia:** osobne uprawnienie `view_usage_logs` pozwala dać supportowi dostęp do wydatków bez dostępu do ustawień.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — log żądań: czas, użytkownik, profil, model, status, tokeny, koszt, opóźnienie; podsumowanie na górze',
          caption: 'Logi żądań: każda próba z tokenami, kosztem i opóźnieniem, z podsumowaniem filtra nad tabelą.',
        },
        { type: 'h3', text: 'Ochrona klucza API' },
        {
          type: 'list',
          items: [
            '**Szyfrowanie.** Pole `api_key` to `EncryptedTextField`: Fernet, klucz pochodny od `SECRET_KEY`.',
            '**Tylko do zapisu.** Po zapisie wartości nie da się zobaczyć — tylko zastąpić albo wyczyścić.',
            '**Alternatywa bez bazy.** Klucz może żyć tylko w środowisku (`OPENROUTER_API_KEY`), a pole w adminie zostaje puste.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Rotacja SECRET_KEY',
          text: 'Klucz Fernet jest pochodny od `SECRET_KEY`. Zmiana `SECRET_KEY` sprawia, że klucze API w bazie stają się nieczytelne — trzeba je wpisać ponownie.',
        },
        { type: 'h3', text: 'Walidacje' },
        {
          type: 'list',
          items: [
            '`temperature` — tylko w zakresie 0…2.',
            'Model główny i fallback muszą być aktywne.',
            'Przy `only_free_models` wszystkie modele w profilu muszą być darmowe.',
            'Para `(profile, model)` w łańcuchu fallback jest unikalna.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Dokumentacja',
      title: 'API Reference',
      lead: 'Publiczne importy z django_openrouter: fasady, klienci, wynik i wyjątki.',
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
          text: '`profile_name=None` używa profilu domyślnego z ustawień. Wywołanie bez `messages` to `TypeError`. Jeśli profil nie istnieje albo jest nieaktywny — `ConfigurationError`.',
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
        { type: 'h3', text: 'Wyjątki' },
        {
          type: 'table',
          head: ['Wyjątek', 'Kiedy'],
          rows: [
            ['`OpenRouterError`', 'Klasa bazowa wszystkich wyjątków biblioteki'],
            ['`ConfigurationError`', 'Brak klucza, profilu albo profilu domyślnego; streaming wyłączony'],
            ['`OpenRouterDisabled`', 'Kill switch: `enabled=False` w ustawieniach'],
            ['`ModelDisabled`', 'Profil/model nieaktywny albo narusza `only_free_models`'],
            ['`RateLimitExceeded`', 'Wyczerpany dzienny/miesięczny limit żądań'],
            ['`BudgetExceeded`', 'Wyczerpany dzienny/miesięczny budżet'],
            ['`OpenRouterAPIError`', 'Błąd API po ponowieniach i fallbacku; niesie `status_code`'],
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
          text: 'Bezpieczne zarówno wewnątrz, jak i poza `transaction.atomic()` — wrapper tworzy się automatycznie. Lock brany jest na wierszu profilu, nie na logach, więc rosnąca tabela `RequestLog` nie rozdmuchuje blokad.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Dokumentacja',
      title: 'FAQ',
      lead: 'Częste pytania i pułapki.',
      blocks: [
        { type: 'h3', text: 'Zmiany w adminie nie działają' },
        {
          type: 'p',
          text: 'Najpewniej odpalasz wiele procesów z `LocMemCache`: unieważnienie cache nastąpiło tylko w procesie, w którym kliknąłeś „Save”. Przełącz się na Redis/Memcached i ustaw alias w `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '“No usage profile specified and default_profile is not set”' },
        {
          type: 'p',
          text: 'Wywołałeś `chat()` bez nazwy profilu i nie ma ustawionego profilu domyślnego. Albo podaj slug jako pierwszy argument, albo wybierz **default profile** w **OpenRouter settings**.',
        },
        { type: 'h3', text: '“Usage profile X is not found or inactive”' },
        {
          type: 'p',
          text: 'Nie ma profilu z tym slugiem albo jego checkbox `is_active` jest wyłączony. Do konfiguracji runtime trafiają tylko aktywne profile.',
        },
        { type: 'h3', text: 'Czy streaming jest wspierany?' },
        {
          type: 'p',
          text: 'Tak. Włącz **Streaming enabled** w **OpenRouter settings** i używaj `stream()` / `astream()` albo `chat(stream=True)`. Przy włączonym streamingu zwykłe `chat()` też idzie przez SSE; `stream=False` wymusza odpowiedź JSON.',
        },
        { type: 'h3', text: 'Limity się nie uruchamiają' },
        {
          type: 'p',
          text: 'Sprawdź, czy `django_openrouter.log_backends.DatabaseBackend` jest w `OPENROUTER["LOG_BACKENDS"]` (domyślnie jest): limity i budżety agregują z tabeli `RequestLog`, a bez tego backendu wydatki są niewidoczne dla sprawdzeń.',
        },
        { type: 'h3', text: 'Jak mieć admina w swoim języku?' },
        {
          type: 'p',
          text: 'Wszystkie etykiety admina są owinięte w `gettext_lazy`, a katalogi tłumaczeń dla kilkudziesięciu locale są w paczce (`locale/<locale_django>/LC_MESSAGES/django.po`). Projekt hosta decyduje, które języki są aktywne: skonfiguruj `LANGUAGE_CODE` / `LANGUAGES` i podłącz `LocaleMiddleware`. Po edycji `.po` skompiluj katalogi — `python manage.py compilemessages -l pl`. Uwaga: angielski w paczce to `en_GB` / `en-gb`; nie ma bazowego katalogu `en`.',
        },
        { type: 'h3', text: 'Jak ręcznie policzyć wydatki?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Czy da się używać bez admina?' },
        {
          type: 'p',
          text: 'Nie — o to chodzi w bibliotece: polityka (modele, limity, budżety) żyje w bazie i zarządza nią operator. Klucz natomiast może żyć wyłącznie w środowisku.',
        },
      ],
    },
  ],
}
