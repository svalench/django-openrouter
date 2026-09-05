import type { DocsContent } from './types'

export const de: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter für Django — Modelle, Profile, Budgets und Logs über das Admin-Panel verwaltet',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Dokumentation durchsuchen…',
    searchEmpty: 'Nichts gefunden. Versuchen Sie einen anderen Begriff.',
    onThisPage: 'Auf dieser Seite',
    copied: 'Kopiert',
    copy: 'Kopieren',
    editGithub: 'GitHub',
    prev: 'Zurück',
    next: 'Weiter',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'In 3 Minuten starten',
    heroGithub: 'Repository',
    builtWith: 'Dokumentation zu',
    license: 'MIT-Lizenz',
  },
  ui: {
    theme: 'Theme wechseln',
    language: 'Sprache',
    openMenu: 'Menü öffnen',
    closeMenu: 'Menü schließen',
  },
  sections: [
    {
      id: 'intro',
      group: 'Erste Schritte',
      title: 'Einführung',
      lead: 'Eine wiederverwendbare Django-App, die OpenRouter in eine verwaltete Ressource verwandelt: Modelle, Nutzungsprofile, Budgets und Request-Logs liegen in der Datenbank und werden über das Admin-Panel konfiguriert — ohne Redeployment.',
      blocks: [
        {
          type: 'p',
          text: 'Ihr Produktcode — Übersetzung, Chat, Zusammenfassungen — spricht über diese Bibliothek mit OpenRouter statt über hartkodierte Schlüssel und Modell-IDs in `settings.py`. Ein Operator wählt aktive Modelle, setzt tägliche und monatliche Limits und prüft die Kosten direkt im Admin.',
        },
        { type: 'h3', text: 'Warum nicht settings.py?' },
        {
          type: 'p',
          text: 'Eine Zeile wie `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` in den Settings bedeutet ein Deployment für jeden Modellwechsel, jede Budgetanpassung oder Notabschaltung. `django-openrouter` hält diese Runtime-Policy in der Datenbank, cached sie und prüft Limits vor jeder Anfrage.',
        },
        {
          type: 'list',
          items: [
            '**Modellkatalog in der Datenbank.** `sync_models` lädt den OpenRouter-Katalog (`GET /api/v1/models` + `/endpoints`) mit Preisen, Latenz (p50 TTFT), Throughput und Gewichtsgröße.',
            '**Nutzungsprofile.** Ein stabiler Slug (`chat`, `translation`) → geordnete Modellkette, `max_tokens`, `temperature`, Limits und Budgets.',
            '**Limits vor der Anfrage.** Tägliche/monatliche Request-Limits und USD-Budgets werden vor dem HTTP-Aufruf geprüft. Erschöpfung ist eine Exception, kein stiller Fallback.',
            '**Streaming (SSE).** `stream()` / `astream()` liefern die Antwort in Chunks; per Checkbox in den Settings aktivierbar.',
            '**Jeder Aufruf wird protokolliert.** Jeder Versuch wird in die DB, eine JSONL-Datei oder ClickHouse geschrieben (steckbare Backends) — zusammen mit dem Username des aufrufenden Nutzers.',
            '**Sichere Schlüssel.** Der Admin-API-Key ist verschlüsselt (Fernet, aus `SECRET_KEY` abgeleitet) und write-only: Nach dem Speichern kann er nur ersetzt oder gelöscht werden.',
            '**Kill-Switch und Parallelität.** Die Checkbox `enabled` stoppt alle Aufrufe sofort, und `max_parallel_requests` begrenzt gleichzeitige HTTP-Anfragen pro Prozess.',
          ],
        },
        { type: 'h3', text: 'Funktionen' },
        {
          type: 'table',
          head: ['Funktion', 'Status'],
          rows: [
            ['Sync- und Async-Clients', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Einzeiler-Fassaden', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Modell-Fallback-Ketten', 'Bei 402 / 429 / 5xx, in konfigurierter Reihenfolge'],
            ['Retries bei Transportfehlern', 'Konfigurierbar über `max_retries`'],
            ['Streaming (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, standardmäßig aus'],
            ['Log-Backends', 'Datenbank (Standard), rotierende JSONL-Datei, ClickHouse'],
            ['Parallelitäts-Limit', '`max_parallel_requests`, Standard 10'],
            ['Admin in Ihrer Sprache', 'Übersetzungskataloge für Dutzende Locales im Lieferumfang'],
            ['Typisierung', 'Paket enthält `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Kompatibilität',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 und 6.0. Abhängigkeiten: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Erste Schritte',
      title: 'Schnellstart',
      lead: 'Von der Installation bis zur ersten Modellantwort — vier Schritte.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Paket installieren',
              text: 'Ein Befehl von PyPI: `pip install django-openrouter`.',
            },
            {
              title: 'App und Middleware einbinden',
              text: 'Fügen Sie `django_openrouter` zu `INSTALLED_APPS` und `django_openrouter.middleware.CurrentUserMiddleware` zu `MIDDLEWARE` hinzu, dann `python manage.py migrate` ausführen.',
            },
            {
              title: 'Im Admin konfigurieren',
              text: 'Öffnen Sie **OpenRouter → OpenRouter settings**: Fügen Sie Ihren API-Key ein (er wird verschlüsselt) oder lassen Sie das Feld leer und setzen `OPENROUTER_API_KEY` in der Umgebung.',
            },
            {
              title: 'Katalog synchronisieren und Profil anlegen',
              text: 'Führen Sie `python manage.py sync_models` aus, erstellen Sie dann ein **Usage profile** mit dem Slug `chat`, fügen Sie Modelle in Prioritätsreihenfolge hinzu und machen Sie es optional zum Default-Profil.',
            },
          ],
        },
        { type: 'h3', text: '1. Installation' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Einbindung und Migrationen' },
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
          text: '`CurrentUserMiddleware` kommt **nach** `AuthenticationMiddleware` und schreibt den Username des aufrufenden Nutzers in das Request-Log. Ohne ihn werden alle Zeilen als `anonymous` markiert.',
        },
        { type: 'h3', text: '3. Konfiguration im Django-Admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Öffnen Sie **OpenRouter → OpenRouter settings**. Fügen Sie Ihren API-Key ein — er wird verschlüsselt und nie wieder angezeigt — oder lassen Sie das Feld leer und setzen `OPENROUTER_API_KEY` in der Umgebung.',
            'Führen Sie `python manage.py sync_models` aus, um den Modellkatalog zu laden (`GET /api/v1/models`).',
            'Erstellen Sie ein **Usage profile** (Slug `translation`, `chat`, …) und fügen Sie ein oder mehrere Modelle in Prioritätsreihenfolge hinzu (das erste wird zuerst versucht), plus Limits und Budgets.',
            'Setzen Sie das Profil als **default profile**, wenn Sie `chat(messages=...)` ohne Namen aufrufen möchten.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Screenshots',
          text: 'Alle vier Admin-Bereiche — Settings, Katalog, Profile und Log — sind mit Screenshots im Abschnitt „Admin“ beschrieben.',
        },
        { type: 'h3', text: '4. Erster Aufruf' },
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
          title: 'Test ohne gespeicherten Schlüssel',
          text: 'Der Katalog lässt sich mit einem Einmal-Schlüssel synchronisieren: `python manage.py sync_models --api-key sk-or-...` — er wird nicht in der Datenbank gespeichert.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Anleitungen',
      title: 'Konfiguration',
      lead: 'Auflösungsreihenfolge des API-Keys, das Dictionary settings.OPENROUTER und wie der Runtime-Config-Cache funktioniert.',
      blocks: [
        { type: 'h3', text: 'Woher der API-Key kommt' },
        {
          type: 'p',
          text: 'Wenn das Schlüsselfeld im Admin leer ist, sucht die Bibliothek in dieser Reihenfolge nach einem Schlüssel:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (Top-Level-Setting)',
            'die Umgebungsvariable `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Ein im Admin gespeicherter Schlüssel hat immer Vorrang vor allen drei Optionen oben. Er wird verschlüsselt gespeichert (Fernet, aus `SECRET_KEY` abgeleitet) und ist nach dem Speichern nicht mehr lesbar.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Schlüssel', 'Standard', 'Beschreibung'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Wie viele Sekunden die Runtime-Config im Django-Cache gehalten wird'],
            ['`CACHE_ALIAS`', '`"default"`', 'Cache-Alias (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Wie viele Sekunden der Admin die Katalog-Synchronisation überspringt'],
            ['`API_KEY`', 'nicht gesetzt', 'Fallback-Schlüssel, wenn das Admin-Feld leer ist'],
            ['`HTTP_REFERER`', 'nicht gesetzt', 'Der Header `HTTP-Referer` (App-Attribution in OpenRouter)'],
            ['`X_TITLE`', 'nicht gesetzt', 'Der Header `X-Title`'],
            ['`LOG_BACKENDS`', 'nur DB', 'Wohin Request-Logs geschrieben werden — siehe Abschnitt „Log-Backends“'],
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
          text: 'Der Standard-`LocMemCache` reicht aus. Redis oder Memcached sind optional — zeigen Sie einfach mit `CACHE_ALIAS` darauf.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Settings leben im Admin, nicht in settings.py',
          text: 'Timeout, Retry-Anzahl, Kill-Switch, Streaming (`streaming_enabled`) und das Parallel-Request-Limit (`max_parallel_requests`) leben in den **OpenRouter settings** des Admins — Details mit Screenshot im Abschnitt „Admin“.',
        },
        { type: 'h3', text: 'Wie der Cache funktioniert' },
        {
          type: 'p',
          text: 'Der Client liest nicht direkt die Datenbank, sondern einen gecachten `RuntimeConfig`-Snapshot: Settings, aktive Profile und ihre Fallback-Modelle. `post_save`-/`post_delete`-Signale auf allen App-Modellen invalidieren den Cache sofort — Admin-Änderungen greifen ohne Neustart, und `CACHE_TIMEOUT` ist nur ein Sicherheitsnetz.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache und mehrere Prozesse',
          text: 'Mit `LocMemCache` hält jeder Prozess eine eigene Cache-Kopie: Die Invalidierung passiert nur in dem Prozess, in dem Sie im Admin gespeichert haben. Für Multi-Prozess-Deployments nutzen Sie Redis/Memcached über `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Anleitungen',
      title: 'Verwendung',
      lead: 'Die Fassaden chat() / achat() / stream() / astream(), die Client-Klassen, Overrides pro Aufruf und die Ergebnisstruktur.',
      blocks: [
        { type: 'h3', text: 'Die Fassade chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # Profil-Slug; None → Default-Profil
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Sync-Client' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Async-Aufruf' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# oder über die Klasse
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: 'Der Async-Client spiegelt den Sync-Client: ORM-Operationen laufen über `sync_to_async`, HTTP über `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Streaming (SSE)' },
        {
          type: 'p',
          text: 'Streaming ist standardmäßig aus. Aktivieren Sie **Streaming enabled** in den **OpenRouter settings**, dann liefern `stream()` und `astream()` die Antwort als `ChatChunk`-Chunks:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# letzter Chunk: done=True, chunk.result enthält das vollständige ChatResult

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` nutzt denselben SSE-Transport und gibt das vollständige `ChatResult` zurück. Ist Streaming in den Settings aktiviert, läuft auch ein einfaches `chat()` über SSE; `stream=False` erzwingt eine normale JSON-Antwort. Ein Aufruf bei deaktiviertem Streaming wirft `ConfigurationError`, noch bevor eine HTTP-Anfrage entsteht.',
        },
        {
          type: 'table',
          head: ['ChatChunk-Feld', 'Typ', 'Beschreibung'],
          rows: [
            ['`delta`', '`str`', 'Text des aktuellen Chunks'],
            ['`content`', '`str`', 'Bisher akkumulierter Text'],
            ['`model_used`', '`str`', 'Das Modell, das die Antwort erzeugt'],
            ['`done`', '`bool`', '`True` beim letzten Chunk'],
            ['`result`', '`ChatResult | None`', 'Vollständiges Ergebnis beim letzten Chunk'],
            ['`raw`', '`dict`', 'Das rohe SSE-Event'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback und Streaming',
          text: 'Ein Fallback auf das nächste Modell ist nur möglich, bevor der erste Chunk ausgegeben wurde. Beginnt ein Modell zu streamen und scheitert mittendrin, wird der Fehler an den Aufrufer weitergereicht: Ein Teil der Antwort ist bereits zum Client unterwegs.',
        },
        { type: 'h3', text: 'Overrides pro Aufruf' },
        {
          type: 'p',
          text: 'Alle `**overrides` werden in den Request-Body durchgereicht. `max_tokens` und `temperature` überschreiben die Profilwerte, und `model` setzt das angegebene Modell temporär an die Spitze der Kette:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # muss im Katalog existieren
    response_format={"type": "json_object"},  # jeder OpenRouter-Parameter
)`,
        },
        { type: 'h3', text: 'Parallelität' },
        {
          type: 'p',
          text: 'Das Feld **Max parallel requests** in den Settings (Standard `10`, `0` = unbegrenzt) begrenzt die Zahl gleichzeitiger HTTP-Anfragen an OpenRouter im aktuellen Prozess — für `chat()` wie für `stream()`, sync wie async.',
        },
        { type: 'h3', text: 'Ergebnis: ChatResult' },
        {
          type: 'table',
          head: ['Feld', 'Typ', 'Beschreibung'],
          rows: [
            ['`content`', '`str`', 'Antworttext (Textteile bei Multipart-Content zusammengefügt)'],
            ['`prompt_tokens`', '`int`', 'Prompt-Tokens aus `usage`'],
            ['`completion_tokens`', '`int`', 'Completion-Tokens aus `usage`'],
            ['`cost_usd`', '`Decimal`', 'Kosten: nach Katalogpreisen, sonst `usage.cost` der API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Katalogkosten — zum Abgleich mit der Abrechnung'],
            ['`model_used`', '`str`', 'Das Modell, das tatsächlich geantwortet hat'],
            ['`latency_ms`', '`int`', 'Latenz des erfolgreichen Versuchs'],
            ['`raw`', '`dict`', 'Rohe JSON-Antwort von OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Anleitungen',
      title: 'Modellkatalog',
      lead: 'Wie sync_models den Katalog füllt und was OpenRouterModel speichert.',
      blocks: [
        { type: 'h3', text: 'Der Befehl sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # Einmal-Schlüssel, wird nicht gespeichert` },
        {
          type: 'p',
          text: 'Der Befehl macht einen Upsert des Katalogs (`GET /api/v1/models`) und reichert ihn mit `/endpoints`-Metriken an — p50-Latenz und Throughput. Er löscht nichts: Modelle, die aus OpenRouter verschwinden, bekommen `is_active=False`. Profile, die auf so ein Modell verweisen, brechen nicht — Aufrufe schlagen einfach mit `ModelDisabled` fehl, bis Sie das Profil umstellen.',
        },
        { type: 'h3', text: 'Modellfelder' },
        {
          type: 'table',
          head: ['Feld', 'Beschreibung'],
          rows: [
            ['`model_id`', 'OpenRouter-Kennung, z. B. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Lesbarer Name'],
            ['`context_length`', 'Kontextgröße in Tokens'],
            ['`pricing`', 'JSON mit Preisen pro Token: `prompt`, `completion`, optional `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Preise pro Token als Dezimalwerte — zum Sortieren und Filtern im Admin'],
            ['`latency_ms`', 'p50-TTFT des besten Endpunkts, in Millisekunden'],
            ['`throughput`', 'p50-Throughput des besten Endpunkts, Tokens/s'],
            ['`parameter_count`', 'Ungefähre Gewichtszahl (70B → 70000000000), zum Sortieren'],
            ['`parameter_label`', 'Anzeigegröße mit Einheit: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Liste unterstützter Parameter'],
            ['`modality`', 'Modalität, z. B. `text->text`'],
            ['`is_active`', 'Ob das Modell in Profilen gewählt werden kann'],
            ['`last_synced_at`', 'Wann der Sync das Modell zuletzt gesehen hat'],
            ['`is_free` (Property)', '`True`, wenn die Preise `prompt`/`completion`/`request` null sind'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Nur kostenlose Modelle',
          text: 'Das Profil-Flag `only_free_models` erlaubt nur Modelle mit Nullpreis im Katalog — praktisch für Dev-Umgebungen und Demos. Gilt für das Primärmodell und jeden Fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Anleitungen',
      title: 'Limits, Budgets und Fallback',
      lead: 'Was vor der Anfrage geprüft wird, was bei OpenRouter-Fehlern passiert und wann der Fallback greift.',
      blocks: [
        { type: 'h3', text: 'Profil-Limits' },
        {
          type: 'p',
          text: 'Der Verbrauch wird aus `RequestLog` für den aktuellen Kalendertag und -monat berechnet (in der aktiven `TIME_ZONE`). Ein leeres (`null`) Limit-Feld bedeutet „unbegrenzt“.',
        },
        {
          type: 'table',
          head: ['Profilfeld', 'Was es begrenzt', 'Exception'],
          rows: [
            ['`max_requests_per_day`', 'Anzahl Requests pro Tag', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Anzahl Requests pro Monat', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Summe der `cost_usd` pro Tag', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Summe der `cost_usd` pro Monat', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'Die Prüfung läuft in einer Transaktion: Die Profilzeile wird mit `select_for_update` gesperrt und Aggregate werden unter dieser Sperre berechnet — konkurrierende Requests können ein Limit nicht im Wettlauf überholen.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Limits brauchen DatabaseBackend',
          text: 'Aggregate werden aus der Tabelle `RequestLog` berechnet, daher muss `DatabaseBackend` in `LOG_BACKENDS` bleiben (das ist der Standard). Entfernen Sie ihn, sieht `check_limits()` keinen Verbrauch und Limits funktionieren nicht mehr.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Keine stillen Umwege',
          text: 'Ein erschöpftes Limit oder Budget ist eine Exception (`BudgetExceeded` / `RateLimitExceeded`) vor dem HTTP-Aufruf. Die Bibliothek wechselt **nicht** zu einem anderen Modell, um den Request noch durchzudrücken.',
        },
        { type: 'h3', text: 'Fallback-Kette' },
        {
          type: 'p',
          text: 'Fallback-Modelle greifen nur, wenn OpenRouter selbst `402`, `429` oder `5xx` zurückgibt. Die Reihenfolge steuert das Feld `order` im Admin; Duplikate in der Kette werden verworfen. Von den Profilregeln verbotene Modelle (inaktiv oder kostenpflichtig bei `only_free_models`) werden übersprungen.',
        },
        {
          type: 'list',
          items: [
            '**Transportfehler und 5xx** — bis zu `max_retries`-Mal auf demselben Modell wiederholt, dann Fallback.',
            '**402 / 429** — sofort weiter zum nächsten Modell der Kette.',
            '**Andere 4xx** (z. B. 400) — sofort geworfen, ohne Fallback: Der Request ist vermutlich für alle Modelle ungültig.',
            '**Jeder Versuch** — auch fehlgeschlagene — wird ins Log geschrieben.',
          ],
        },
        { type: 'h3', text: 'Globaler Kill-Switch' },
        {
          type: 'p',
          text: 'Die Checkbox `enabled` in den **OpenRouter settings** stoppt sofort alles: Jeder `chat()`-Aufruf wirft `OpenRouterDisabled`, noch bevor Limits geprüft werden. Praktisch für Incidents und geplante Wartung.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Anleitungen',
      title: 'Log-Backends',
      lead: 'Jeder HTTP-Aufruf wird in alle Backends aus OPENROUTER["LOG_BACKENDS"] geschrieben: Projektdatenbank, JSONL-Datei, ClickHouse — oder Ihre eigene Klasse.',
      blocks: [
        {
          type: 'p',
          text: 'Jeder Eintrag der Liste ist entweder ein Dotted Path zu einer Klasse (Standardeinstellungen) oder ein Dict mit dem Schlüssel `BACKEND` plus Parametern. Ist `LOG_BACKENDS` nicht gesetzt, werden Logs nur in die Projektdatenbank (`RequestLog`) geschrieben.',
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
        { type: 'h3', text: 'DatabaseBackend (Standard)' },
        {
          type: 'p',
          text: 'Schreibt Zeilen in das Modell `RequestLog`. Tägliche/monatliche Limits und Budgets aggregieren aus dieser Tabelle — lassen Sie dieses Backend aktiv, wenn Sie Limits nutzen: Ohne es sieht `check_limits()` keinen Verbrauch.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines in eine Datei mit größenbasierter Rotation (`RotatingFileHandler`): eine Zeile = ein JSON-Objekt mit den Feldern `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Fügt `FORMAT JSONEachRow` über das HTTP-Interface von ClickHouse ein. Keine zusätzlichen Abhängigkeiten — es wird dasselbe `httpx` verwendet. Datenbank- und Tabellennamen werden als Bezeichner validiert, um Injection zu verhindern. Die Tabelle wird so angelegt:',
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
          title: 'Best-Effort',
          text: 'Alle konfigurierten Backends erhalten jeden Datensatz, und ein Backend-Fehler (volle Platte, unerreichbares ClickHouse) bricht niemals `chat()` — der Fehler landet im Logger `django_openrouter`.',
        },
        { type: 'h3', text: 'Wer hat den Request gemacht' },
        {
          type: 'p',
          text: 'Jeder Datensatz trägt den Username des Django-Nutzers, der den Aufruf gemacht hat. Geliefert wird er von `django_openrouter.middleware.CurrentUserMiddleware` (nach `AuthenticationMiddleware`). Aufrufe ohne Nutzer oder außerhalb eines HTTP-Requests werden als `anonymous` geloggt. In Celery und Management-Commands setzen Sie den Namen manuell:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Eigenes Backend' },
        {
          type: 'p',
          text: 'Erben Sie von `django_openrouter.log_backends.LogBackend`, implementieren Sie `write()` (und optional `awrite()`) und tragen Sie den Dotted Path der Klasse in `LOG_BACKENDS` ein.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Anleitungen',
      title: 'Das Admin-Panel',
      lead: 'Die gesamte Runtime-Policy lebt in vier Bereichen des Django-Admin: Settings, Modellkatalog, Nutzungsprofile und Request-Logs.',
      blocks: [
        {
          type: 'table',
          head: ['Bereich', 'Aufgabe'],
          rows: [
            ['**OpenRouter settings**', 'Kill-Switch, verschlüsselter API-Key, Streaming, Timeouts'],
            ['**OpenRouter models**', 'Der Katalog von OpenRouter: Preis, Latenz, Throughput'],
            ['**Usage profiles**', 'Modellkette, Limits, Budgets, Verbrauchsstatistik'],
            ['**Request logs**', 'Tokens, Kosten und Latenz jedes Aufrufs (read-only)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Ein Singleton: Die Liste leitet auf die einzige Zeile weiter, und sie kann nicht gelöscht werden. Hier sind alle globalen Einstellungen der Integration versammelt:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — der globale Kill-Switch. Aus → jeder `chat()`-/`stream()`-Aufruf wirft `OpenRouterDisabled`.',
            '**API key** — write-only, mit Fernet aus `SECRET_KEY` verschlüsselt. Ein leeres Feld behält den aktuellen Schlüssel; ein neuer Wert ersetzt ihn; die Checkbox **Clear stored API key** löscht den Schlüssel aus der Datenbank — dann wird `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]` verwendet.',
            '**Base URL** — die Wurzel der OpenRouter-API (`https://openrouter.ai/api/v1`).',
            '**Default profile** — das Profil, das verwendet wird, wenn `chat(messages=...)` ohne Namen aufgerufen wird.',
            '**Request timeout** / **Max retries** — HTTP-Timeout und Retry-Anzahl bei Transport-/5xx-Fehlern, bevor das nächste Modell der Kette drankommt.',
            '**Streaming enabled** — erlaubt SSE über `stream()` / `astream()` und `chat(stream=True)`. Standardmäßig aus.',
            '**Max parallel requests** — Obergrenze gleichzeitiger HTTP-Aufrufe in diesem Prozess (`0` = unbegrenzt).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django-Admin — OpenRouter settings: enabled, Schlüsselstatus, base url, default profile, Timeout, Retries, Streaming, Parallelitäts-Limit',
          caption: 'OpenRouter settings: Kill-Switch, write-only API-Key, Default-Profil, Timeouts, Streaming und Parallelitäts-Limit.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'Der Katalog aus `GET /api/v1/models` plus `/endpoints`-Metriken (Latenz und Throughput). Zeilen können nicht von Hand hinzugefügt oder gelöscht werden, und die Modellkarte ist read-only.',
        },
        {
          type: 'list',
          items: [
            '**Spalten:** Name, `latency_ms` (p50 TTFT), Throughput (Tokens/s), Prompt-/Completion-Preise pro 1M Tokens, Gewichtsgröße (`70B` / `8x7B`), `is_active`. Sortieren per Klick auf die Spalte — leere Werte immer am Ende.',
            '**Filter:** Aktivität, Modalität, Preis (free / < $1 / $1–10 / ≥ $10 pro 1M), Geschwindigkeit (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (Aktion) — Upsert des Katalogs; verschwundene Modelle bekommen `is_active=False`.',
            '**Assign to usage profile…** (Aktion) — hängt die ausgewählten Modelle ans Ende der Kette eines Profils; Duplikate, inaktive und kostenpflichtige Modelle (bei `only_free_models`) werden mit Bericht übersprungen.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Beim ersten Öffnen wird die Liste aus der API aktualisiert und danach 10 Minuten aus der Datenbank geliefert (`CATALOG_CACHE_TIMEOUT`). Derselbe Sync aus der Konsole: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django-Admin — OpenRouter-Modellkatalog: Name, Latenz, Throughput, Preis pro 1M, Gewichtsgröße, Aktivität; Filter rechts',
          caption: 'Modellkatalog: Sortieren nach Preis/Latenz, Filtern nach Preis und Geschwindigkeit, Aktionen sync und assign to profile.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Ein Profil ist der Slug, den Ihr Code übergibt (`chat`, `translation`, …), plus eine geordnete Modellliste: Das erste wird zuerst versucht, der Rest fällt bei `402` / `429` / `5xx` zurück. Erschöpfte Limits werfen eine Exception, statt still das Modell zu wechseln.',
        },
        {
          type: 'list',
          items: [
            '**Profilliste:** Name, Primärmodell, Aktivität, only-free, tägliche Request-/Budget-Limits und Aggregate aus dem Log — Request-Anzahl, mittlere und gesamte Latenz, mittlere und gesamte Kosten (ein GROUP BY pro Seite).',
            '**Formular:** `max_tokens`, `temperature` (0–2), tägliche/monatliche Request- und USD-Limits (leer = unbegrenzt), **only free models**, **is active**.',
            '**Inline Models (priority order):** Autocomplete über den Katalog — Label zeigen Preis und Latenz, und es gelten dieselben Preis-/Geschwindigkeitsfilter wie im Katalog. Die Reihenfolge wird beim Speichern normalisiert, und das erste Modell der Kette wird in das Feld `model` synchronisiert.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django-Admin — Profilliste mit Aggregaten zu Requests, Latenz und Kosten',
          caption: 'Nutzungsprofile: Modellkette, Limits und Verbrauchsaggregate direkt in der Liste.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Ein Read-only-Log. Jeder HTTP-Versuch (inklusive Fallbacks und Fehler) wird zu einer Zeile, wenn `DatabaseBackend` aktiv ist (Standard). Tägliche und monatliche Limits aggregieren aus dieser Tabelle.',
        },
        {
          type: 'list',
          items: [
            '**Spalten:** Zeit, Username, Profil, Modell, HTTP-Status, Prompt-/Completion-Tokens, Kosten, Latenz.',
            '**Zusammenfassung über der Tabelle:** Request-Anzahl und Gesamt-USD für den aktuellen Filter. Filter: Profil, Status, Datum; Suche über Fehlertext und Username.',
            '**Username** liefert `CurrentUserMiddleware`; ohne ihn werden Zeilen als `anonymous` markiert. In Celery und Management-Commands — `bound_username("worker")` (siehe „Log-Backends“).',
            '**Berechtigungen:** Die separate Berechtigung `view_usage_logs` erlaubt Support-Zugang zu den Kosten ohne Zugang zu den Settings.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django-Admin — Request-Log: Zeit, Username, Profil, Modell, Status, Tokens, Kosten, Latenz; Zusammenfassung oben',
          caption: 'Request-Logs: jeder Versuch mit Tokens, Kosten und Latenz, Filter-Zusammenfassung über der Tabelle.',
        },
        { type: 'h3', text: 'Schutz des API-Keys' },
        {
          type: 'list',
          items: [
            '**Verschlüsselung.** Das Feld `api_key` ist ein `EncryptedTextField`: Fernet, Schlüssel aus `SECRET_KEY` abgeleitet.',
            '**Write-only.** Nach dem Speichern kann der Wert nicht eingesehen werden — nur ersetzt oder gelöscht.',
            '**Alternative ohne Datenbank.** Der Schlüssel kann ausschließlich in der Umgebung leben (`OPENROUTER_API_KEY`), das Admin-Feld bleibt leer.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Rotation von SECRET_KEY',
          text: 'Der Fernet-Schlüssel wird aus `SECRET_KEY` abgeleitet. Ändern Sie `SECRET_KEY`, werden in der Datenbank gespeicherte API-Keys unlesbar — sie müssen neu eingegeben werden.',
        },
        { type: 'h3', text: 'Validierungen' },
        {
          type: 'list',
          items: [
            '`temperature` — nur im Bereich 0…2.',
            'Primär- und Fallback-Modelle müssen aktiv sein.',
            'Bei `only_free_models` müssen alle Modelle des Profils kostenlos sein.',
            'Das Paar `(profile, model)` in der Fallback-Kette ist eindeutig.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Referenz',
      title: 'API-Referenz',
      lead: 'Öffentliche Imports aus django_openrouter: Fassaden, Clients, Ergebnis und Exceptions.',
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
          text: '`profile_name=None` verwendet das Default-Profil aus den Settings. Ein Aufruf ohne `messages` ist ein `TypeError`. Wird das Profil nicht gefunden oder ist inaktiv — `ConfigurationError`.',
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
    delta: str                      # Text des aktuellen Chunks
    content: str                    # akkumulierter Antworttext
    model_used: str = ""
    done: bool = False              # True beim letzten Chunk
    result: ChatResult | None = None  # vollständiges Ergebnis beim letzten Chunk
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: 'Exceptions' },
        {
          type: 'table',
          head: ['Exception', 'Wann'],
          rows: [
            ['`OpenRouterError`', 'Basisklasse aller Exceptions der Bibliothek'],
            ['`ConfigurationError`', 'Kein Schlüssel, Profil oder Default-Profil; Streaming deaktiviert'],
            ['`OpenRouterDisabled`', 'Kill-Switch: `enabled=False` in den Settings'],
            ['`ModelDisabled`', 'Profil/Modell inaktiv oder Verstoß gegen `only_free_models`'],
            ['`RateLimitExceeded`', 'Tägliches/monatliches Request-Limit erschöpft'],
            ['`BudgetExceeded`', 'Tägliches/monatliches Budget erschöpft'],
            ['`OpenRouterAPIError`', 'API-Fehler nach Retries und Fallback; trägt `status_code`'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'Fehlerbehandlung',
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
          code: `stats = profile.get_usage("day")    # oder "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # Beginn des Zeitraums (datetime)`,
        },
        {
          type: 'p',
          text: 'Sicher aufrufbar sowohl innerhalb als auch außerhalb von `transaction.atomic()` — der Wrapper wird automatisch erstellt. Die Sperre liegt auf der Profilzeile, nicht auf den Logs, daher explodieren die Sperren nicht, wenn die Tabelle `RequestLog` wächst.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Referenz',
      title: 'FAQ',
      lead: 'Häufige Fragen und Stolpersteine.',
      blocks: [
        { type: 'h3', text: 'Admin-Änderungen greifen nicht' },
        {
          type: 'p',
          text: 'Höchstwahrscheinlich laufen mehrere Prozesse mit `LocMemCache`: Die Cache-Invalidierung ist nur in dem Prozess passiert, in dem Sie „Speichern“ geklickt haben. Wechseln Sie zu Redis/Memcached und setzen Sie den Alias in `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '„No usage profile specified and default_profile is not set“' },
        {
          type: 'p',
          text: 'Sie haben `chat()` ohne Profilnamen aufgerufen und kein Default-Profil ist gesetzt. Übergeben Sie entweder den Slug als erstes Argument oder wählen Sie ein **default profile** in den **OpenRouter settings**.',
        },
        { type: 'h3', text: '„Usage profile X is not found or inactive“' },
        {
          type: 'p',
          text: 'Es gibt kein Profil mit diesem Slug, oder seine Checkbox `is_active` ist abgewählt. Nur aktive Profile landen in der Runtime-Config.',
        },
        { type: 'h3', text: 'Wird Streaming unterstützt?' },
        {
          type: 'p',
          text: 'Ja. Aktivieren Sie **Streaming enabled** in den **OpenRouter settings** und nutzen Sie `stream()` / `astream()` oder `chat(stream=True)`. Bei aktiviertem Streaming läuft auch ein einfaches `chat()` über SSE; `stream=False` erzwingt eine JSON-Antwort.',
        },
        { type: 'h3', text: 'Limits greifen nicht' },
        {
          type: 'p',
          text: 'Prüfen Sie, dass `django_openrouter.log_backends.DatabaseBackend` in `OPENROUTER["LOG_BACKENDS"]` steht (standardmäßig der Fall): Limits und Budgets aggregieren aus der Tabelle `RequestLog`, und ohne dieses Backend ist der Verbrauch für die Prüfungen unsichtbar.',
        },
        { type: 'h3', text: 'Wie bekomme ich den Admin in meiner Sprache?' },
        {
          type: 'p',
          text: 'Alle Admin-Labels sind in `gettext_lazy` gehüllt, und Übersetzungskataloge für Dutzende Locales liegen im Paket (`locale/<django_locale>/LC_MESSAGES/django.po`). Das Host-Projekt entscheidet, welche Sprachen aktiv sind: Konfigurieren Sie `LANGUAGE_CODE` / `LANGUAGES` und binden Sie `LocaleMiddleware` ein. Nach dem Bearbeiten der `.po`-Dateien kompilieren Sie die Kataloge — `python manage.py compilemessages -l de`. Hinweis: Englisch im Paket ist `en_GB` / `en-gb`; einen Basis-Katalog `en` gibt es nicht.',
        },
        { type: 'h3', text: 'Wie rechne ich den Verbrauch manuell aus?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Geht es auch ohne Admin?' },
        {
          type: 'p',
          text: 'Nein — genau darum geht es bei der Bibliothek: Die Policy (Modelle, Limits, Budgets) lebt in der Datenbank und wird von einem Operator verwaltet. Der Schlüssel kann jedoch ausschließlich in der Umgebung leben.',
        },
      ],
    },
  ],
}
