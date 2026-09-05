import type { DocsContent } from './types'

export const es: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter para Django — modelos, perfiles, presupuestos y registros gestionados desde el admin',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Buscar en la documentación…',
    searchEmpty: 'Sin resultados. Prueba con otra búsqueda.',
    onThisPage: 'En esta página',
    copied: 'Copiado',
    copy: 'Copiar',
    editGithub: 'GitHub',
    prev: 'Anterior',
    next: 'Siguiente',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Empieza en 3 minutos',
    heroGithub: 'Repositorio',
    builtWith: 'Documentación de',
    license: 'Licencia MIT',
  },
  ui: {
    theme: 'Cambiar tema',
    language: 'Idioma',
    openMenu: 'Abrir menú',
    closeMenu: 'Cerrar menú',
  },
  sections: [
    {
      id: 'intro',
      group: 'Primeros pasos',
      title: 'Introducción',
      lead: 'Una aplicación reutilizable de Django que convierte OpenRouter en un recurso gestionado: modelos, perfiles de uso, presupuestos y registros de peticiones viven en la base de datos y se configuran desde el admin — sin redespliegues.',
      blocks: [
        {
          type: 'p',
          text: 'Tu código de producto — traducción, chat, resúmenes — habla con OpenRouter a través de esta librería en lugar de claves e ids de modelo fijos en `settings.py`. Un operador elige los modelos activos, define límites diarios y mensuales y revisa el gasto directamente en el admin.',
        },
        { type: 'h3', text: '¿Por qué no settings.py?' },
        {
          type: 'p',
          text: 'Una línea como `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` en los settings implica un despliegue por cada cambio de modelo, ajuste de presupuesto o apagado de emergencia. `django-openrouter` guarda esa política de runtime en la base de datos, la cachea y comprueba los límites antes de cada petición.',
        },
        {
          type: 'list',
          items: [
            '**Catálogo de modelos en la base de datos.** `sync_models` descarga el catálogo de OpenRouter (`GET /api/v1/models` + `/endpoints`) con precios, latencia (p50 TTFT), throughput y tamaño de pesos.',
            '**Perfiles de uso.** Un slug estable (`chat`, `translation`) → una cadena ordenada de modelos, `max_tokens`, `temperature`, límites y presupuestos.',
            '**Límites antes de la petición.** Los límites diarios/mensuales de peticiones y los presupuestos en USD se comprueban antes de la llamada HTTP. El agotamiento es una excepción, no un fallback silencioso.',
            '**Streaming (SSE).** `stream()` / `astream()` entregan la respuesta en chunks; se activa con una sola casilla en los settings.',
            '**Cada llamada queda registrada.** Cada intento se escribe en la BD, un archivo JSONL o ClickHouse (backends enchufables) — junto con el username del usuario que la hizo.',
            '**Claves seguras.** La API key del admin se guarda cifrada (Fernet, derivada de `SECRET_KEY`) y es write-only: tras guardarla solo puede reemplazarse o borrarse.',
            '**Kill switch y paralelismo.** La casilla `enabled` detiene todas las llamadas al instante, y `max_parallel_requests` limita las peticiones HTTP simultáneas por proceso.',
          ],
        },
        { type: 'h3', text: 'Características' },
        {
          type: 'table',
          head: ['Característica', 'Estado'],
          rows: [
            ['Clientes síncrono y asíncrono', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Fachadas de una línea', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Cadenas de fallback de modelos', 'Ante 402 / 429 / 5xx, en el orden configurado'],
            ['Reintentos de errores de transporte', 'Configurable con `max_retries`'],
            ['Streaming (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, desactivado por defecto'],
            ['Backends de logs', 'Base de datos (por defecto), archivo JSONL con rotación, ClickHouse'],
            ['Límite de paralelismo', '`max_parallel_requests`, 10 por defecto'],
            ['Admin en tu idioma', 'Catálogos de traducción para decenas de locales incluidos'],
            ['Tipado', 'El paquete incluye `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Compatibilidad',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 y 6.0. Dependencias: `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Primeros pasos',
      title: 'Inicio rápido',
      lead: 'De la instalación a la primera respuesta del modelo — cuatro pasos.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Instala el paquete',
              text: 'Un solo comando desde PyPI: `pip install django-openrouter`.',
            },
            {
              title: 'Conecta la app y el middleware',
              text: 'Añade `django_openrouter` a `INSTALLED_APPS` y `django_openrouter.middleware.CurrentUserMiddleware` a `MIDDLEWARE`, luego ejecuta `python manage.py migrate`.',
            },
            {
              title: 'Configura en el admin',
              text: 'Abre **OpenRouter → OpenRouter settings**: pega tu API key (se cifrará) o deja el campo vacío y define `OPENROUTER_API_KEY` en el entorno.',
            },
            {
              title: 'Sincroniza el catálogo y crea un perfil',
              text: 'Ejecuta `python manage.py sync_models`, luego crea un **Usage profile** con el slug `chat`, añade modelos en orden de prioridad y, si quieres, márcalo como perfil por defecto.',
            },
          ],
        },
        { type: 'h3', text: '1. Instalación' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Conexión y migraciones' },
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
          text: '`CurrentUserMiddleware` va **después** de `AuthenticationMiddleware` y registra el username del usuario que hace la llamada en el log de peticiones. Sin él, todas las filas quedan marcadas como `anonymous`.',
        },
        { type: 'h3', text: '3. Configuración en Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Abre **OpenRouter → OpenRouter settings**. Pega tu API key — se cifra y no vuelve a mostrarse — o deja el campo vacío y define `OPENROUTER_API_KEY` en el entorno.',
            'Ejecuta `python manage.py sync_models` para descargar el catálogo de modelos (`GET /api/v1/models`).',
            'Crea un **Usage profile** (slug `translation`, `chat`, …) y añade uno o varios modelos en orden de prioridad (el primero se prueba primero), además de límites y presupuestos.',
            'Marca el perfil como **default profile** si quieres llamar a `chat(messages=...)` sin nombre.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Capturas de pantalla',
          text: 'Las cuatro secciones del admin — settings, catálogo, perfiles y log — están descritas con capturas en la sección «Admin».',
        },
        { type: 'h3', text: '4. Primera llamada' },
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
          title: 'Prueba sin guardar la clave',
          text: 'El catálogo puede sincronizarse con una clave de un solo uso: `python manage.py sync_models --api-key sk-or-...` — no se guardará en la base de datos.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Guías',
      title: 'Configuración',
      lead: 'Orden de resolución de la API key, el diccionario settings.OPENROUTER y cómo funciona la caché de la configuración de runtime.',
      blocks: [
        { type: 'h3', text: 'De dónde sale la API key' },
        {
          type: 'p',
          text: 'Si el campo de la clave en el admin está vacío, la librería busca la clave en este orden:',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (setting de primer nivel)',
            'la variable de entorno `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Una clave guardada en el admin siempre tiene prioridad sobre las tres opciones anteriores. Se almacena cifrada (Fernet, derivada de `SECRET_KEY`) y no puede leerse tras guardarla.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Clave', 'Por defecto', 'Descripción'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Cuántos segundos se conserva la config de runtime en la caché de Django'],
            ['`CACHE_ALIAS`', '`"default"`', 'Alias de caché (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Cuántos segundos el admin evita resincronizar el catálogo de modelos'],
            ['`API_KEY`', 'sin definir', 'Clave de respaldo si el campo del admin está vacío'],
            ['`HTTP_REFERER`', 'sin definir', 'Cabecera `HTTP-Referer` (atribución de la app en OpenRouter)'],
            ['`X_TITLE`', 'sin definir', 'Cabecera `X-Title`'],
            ['`LOG_BACKENDS`', 'solo BD', 'Dónde se escriben los logs de peticiones — ver la sección «Backends de logs»'],
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
          text: 'El `LocMemCache` de serie es suficiente. Redis o Memcached son opcionales: basta con apuntar `CACHE_ALIAS` hacia ellos.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Los ajustes viven en el admin, no en settings.py',
          text: 'El timeout, el número de reintentos, el kill switch, el streaming (`streaming_enabled`) y el límite de peticiones paralelas (`max_parallel_requests`) viven en **OpenRouter settings** del admin — detalles con captura en la sección «Admin».',
        },
        { type: 'h3', text: 'Cómo funciona la caché' },
        {
          type: 'p',
          text: 'El cliente no lee la base de datos directamente, sino una instantánea `RuntimeConfig` cacheada: settings, perfiles activos y sus modelos de fallback. Las señales `post_save` / `post_delete` de todos los modelos de la app invalidan la caché al instante — los cambios en el admin se aplican sin reiniciar, y `CACHE_TIMEOUT` es solo una red de seguridad.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache y múltiples procesos',
          text: 'Con `LocMemCache` cada proceso mantiene su propia copia de la caché: la invalidación solo ocurre en el proceso donde guardaste en el admin. Para despliegues multi-proceso usa Redis/Memcached vía `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Guías',
      title: 'Uso',
      lead: 'Las fachadas chat() / achat() / stream() / astream(), las clases de cliente, los overrides por llamada y la estructura del resultado.',
      blocks: [
        { type: 'h3', text: 'La fachada chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # slug del perfil; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Cliente síncrono' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Llamada asíncrona' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# o con la clase
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: 'El cliente asíncrono replica el síncrono: las operaciones ORM pasan por `sync_to_async` y el HTTP por `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Streaming (SSE)' },
        {
          type: 'p',
          text: 'El streaming está desactivado por defecto. Activa **Streaming enabled** en **OpenRouter settings** y `stream()` / `astream()` entregarán la respuesta en chunks `ChatChunk`:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# chunk final: done=True, chunk.result contiene el ChatResult completo

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` usa el mismo transporte SSE y devuelve el `ChatResult` completo. Si el streaming está activado en los settings, un `chat()` normal también va por SSE; `stream=False` fuerza una respuesta JSON normal. Llamar con el streaming desactivado lanza `ConfigurationError` antes de cualquier petición HTTP.',
        },
        {
          type: 'table',
          head: ['Campo de ChatChunk', 'Tipo', 'Descripción'],
          rows: [
            ['`delta`', '`str`', 'Texto del chunk actual'],
            ['`content`', '`str`', 'Texto acumulado hasta el momento'],
            ['`model_used`', '`str`', 'El modelo que produce la respuesta'],
            ['`done`', '`bool`', '`True` en el chunk final'],
            ['`result`', '`ChatResult | None`', 'Resultado completo en el chunk final'],
            ['`raw`', '`dict`', 'El evento SSE en bruto'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback y streaming',
          text: 'El fallback al siguiente modelo solo es posible antes de emitir el primer chunk. Si un modelo empieza a streamear y falla a mitad, el error se propaga al llamador: parte de la respuesta ya se ha enviado al cliente.',
        },
        { type: 'h3', text: 'Overrides por llamada' },
        {
          type: 'p',
          text: 'Cualquier `**overrides` se reenvía al cuerpo de la petición. `max_tokens` y `temperature` sobrescriben los valores del perfil, y `model` coloca temporalmente el modelo indicado al frente de la cadena:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # debe existir en el catálogo
    response_format={"type": "json_object"},  # cualquier parámetro de OpenRouter
)`,
        },
        { type: 'h3', text: 'Paralelismo' },
        {
          type: 'p',
          text: 'El campo **Max parallel requests** de los settings (por defecto `10`, `0` = sin límite) limita el número de peticiones HTTP simultáneas a OpenRouter en el proceso actual — tanto para `chat()` como para `stream()`, síncronas y asíncronas.',
        },
        { type: 'h3', text: 'Resultado: ChatResult' },
        {
          type: 'table',
          head: ['Campo', 'Tipo', 'Descripción'],
          rows: [
            ['`content`', '`str`', 'Texto de la respuesta (partes de texto unidas para contenido multipart)'],
            ['`prompt_tokens`', '`int`', 'Tokens del prompt según `usage`'],
            ['`completion_tokens`', '`int`', 'Tokens de la respuesta según `usage`'],
            ['`cost_usd`', '`Decimal`', 'Coste: según precios del catálogo, si no `usage.cost` de la API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Coste según el catálogo — para conciliar con la facturación'],
            ['`model_used`', '`str`', 'El modelo que realmente respondió'],
            ['`latency_ms`', '`int`', 'Latencia del intento con éxito'],
            ['`raw`', '`dict`', 'Respuesta JSON en bruto de OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Guías',
      title: 'Catálogo de modelos',
      lead: 'Cómo sync_models llena el catálogo y qué guarda OpenRouterModel.',
      blocks: [
        { type: 'h3', text: 'El comando sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # clave de un solo uso, no se guarda` },
        {
          type: 'p',
          text: 'El comando hace upsert del catálogo (`GET /api/v1/models`) y lo enriquece con métricas de `/endpoints` — latencia p50 y throughput. Nunca borra nada: los modelos que desaparecen de OpenRouter reciben `is_active=False`. Los perfiles que referencian ese modelo no se rompen: las llamadas simplemente empiezan a fallar con `ModelDisabled` hasta que cambies el perfil.',
        },
        { type: 'h3', text: 'Campos del modelo' },
        {
          type: 'table',
          head: ['Campo', 'Descripción'],
          rows: [
            ['`model_id`', 'Identificador de OpenRouter, p. ej. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Nombre legible'],
            ['`context_length`', 'Tamaño del contexto en tokens'],
            ['`pricing`', 'JSON con precios por token: `prompt`, `completion`, opcional `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Precios por token en decimal — para ordenar y filtrar en el admin'],
            ['`latency_ms`', 'p50 TTFT del mejor endpoint, en milisegundos'],
            ['`throughput`', 'p50 throughput del mejor endpoint, tokens/s'],
            ['`parameter_count`', 'Número aproximado de pesos (70B → 70000000000), para ordenar'],
            ['`parameter_label`', 'Tamaño para mostrar con unidad: `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Lista de parámetros soportados'],
            ['`modality`', 'Modalidad, p. ej. `text->text`'],
            ['`is_active`', 'Si el modelo puede elegirse en los perfiles'],
            ['`last_synced_at`', 'Cuándo lo vio la sincronización por última vez'],
            ['`is_free` (property)', '`True` si los precios `prompt`/`completion`/`request` son cero'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Solo modelos gratuitos',
          text: 'El flag de perfil `only_free_models` permite solo modelos con precio cero en el catálogo — útil para entornos de desarrollo y demos. Se aplica tanto al modelo principal como a cada fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Guías',
      title: 'Límites, presupuestos y fallback',
      lead: 'Qué se comprueba antes de la petición, qué ocurre ante errores de OpenRouter y cuándo entra el fallback.',
      blocks: [
        { type: 'h3', text: 'Límites del perfil' },
        {
          type: 'p',
          text: 'El gasto se calcula desde `RequestLog` para el día y el mes naturales actuales (en el `TIME_ZONE` activo). Un campo de límite vacío (`null`) significa «sin límite».',
        },
        {
          type: 'table',
          head: ['Campo del perfil', 'Qué limita', 'Excepción'],
          rows: [
            ['`max_requests_per_day`', 'Número de peticiones al día', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Número de peticiones al mes', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Suma de `cost_usd` al día', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Suma de `cost_usd` al mes', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'La comprobación se ejecuta en una transacción: la fila del perfil se bloquea con `select_for_update` y los agregados se calculan bajo ese bloqueo — las peticiones concurrentes no pueden superar el límite en carrera.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Los límites requieren DatabaseBackend',
          text: 'Los agregados se calculan sobre la tabla `RequestLog`, así que `DatabaseBackend` debe permanecer en `LOG_BACKENDS` (es el valor por defecto). Si lo quitas, `check_limits()` no ve el gasto y los límites dejan de funcionar.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Sin rodeos silenciosos',
          text: 'Agotar un límite o un presupuesto es una excepción (`BudgetExceeded` / `RateLimitExceeded`) lanzada antes de la llamada HTTP. La librería **no** cambia a otro modelo para colar la petición.',
        },
        { type: 'h3', text: 'Cadena de fallback' },
        {
          type: 'p',
          text: 'Los modelos de fallback solo entran cuando el propio OpenRouter devuelve `402`, `429` o `5xx`. El orden lo define el campo `order` en el admin; los duplicados de la cadena se descartan. Los modelos prohibidos por las reglas del perfil (inactivos, o de pago con `only_free_models`) se omiten.',
        },
        {
          type: 'list',
          items: [
            '**Errores de transporte y 5xx** — se reintentan hasta `max_retries` veces en el mismo modelo, luego fallback.',
            '**402 / 429** — se pasa directamente al siguiente modelo de la cadena.',
            '**Otros 4xx** (p. ej. 400) — se lanzan de inmediato, sin fallback: la petición probablemente es inválida para todos los modelos.',
            '**Cada intento** — incluidos los fallidos — se escribe en el log.',
          ],
        },
        { type: 'h3', text: 'Kill switch global' },
        {
          type: 'p',
          text: 'La casilla `enabled` de **OpenRouter settings** lo detiene todo al instante: cualquier llamada a `chat()` lanza `OpenRouterDisabled` antes incluso de comprobar los límites. Útil para incidentes y paradas planificadas.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Guías',
      title: 'Backends de logs',
      lead: 'Cada llamada HTTP se escribe en todos los backends de OPENROUTER["LOG_BACKENDS"]: la base de datos del proyecto, un archivo JSONL, ClickHouse — o tu propia clase.',
      blocks: [
        {
          type: 'p',
          text: 'Cada entrada de la lista es un dotted path a una clase (configuración por defecto) o un diccionario con la clave `BACKEND` y parámetros. Si `LOG_BACKENDS` no está definido, los logs se escriben solo en la base de datos del proyecto (`RequestLog`).',
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
        { type: 'h3', text: 'DatabaseBackend (por defecto)' },
        {
          type: 'p',
          text: 'Escribe filas en el modelo `RequestLog`. Los límites y presupuestos diarios/mensuales se agregan desde esta tabla — mantén este backend activado si usas límites: sin él, `check_limits()` no ve el gasto.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines a un archivo con rotación por tamaño (`RotatingFileHandler`): una línea = un objeto JSON con los campos `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Inserta `FORMAT JSONEachRow` a través de la interfaz HTTP de ClickHouse. Sin dependencias extra — usa el mismo `httpx`. Los nombres de base de datos y tabla se validan como identificadores para evitar inyecciones. La tabla se crea así:',
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
          text: 'Todos los backends configurados reciben cada registro, y un fallo de backend (disco lleno, ClickHouse inalcanzable) nunca rompe `chat()` — el error se registra en el logger `django_openrouter`.',
        },
        { type: 'h3', text: 'Quién hizo la petición' },
        {
          type: 'p',
          text: 'Cada registro lleva el username del usuario de Django que hizo la llamada. Lo aporta `django_openrouter.middleware.CurrentUserMiddleware` (después de `AuthenticationMiddleware`). Las llamadas sin usuario o fuera de una petición HTTP se registran como `anonymous`. En Celery y management commands define el nombre manualmente:',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Backend personalizado' },
        {
          type: 'p',
          text: 'Hereda de `django_openrouter.log_backends.LogBackend`, implementa `write()` (y opcionalmente `awrite()`) y añade el dotted path de la clase a `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Guías',
      title: 'El admin',
      lead: 'Toda la política de runtime vive en cuatro secciones del Django admin: settings, catálogo de modelos, perfiles de uso y log de peticiones.',
      blocks: [
        {
          type: 'table',
          head: ['Sección', 'Qué hace'],
          rows: [
            ['**OpenRouter settings**', 'Kill switch, API key cifrada, streaming, timeouts'],
            ['**OpenRouter models**', 'El catálogo de OpenRouter: precio, latencia, throughput'],
            ['**Usage profiles**', 'Cadena de modelos, límites, presupuestos, estadísticas de gasto'],
            ['**Request logs**', 'Tokens, coste y latencia de cada llamada (solo lectura)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Un singleton: la lista redirige a la única fila y no puede borrarse. Aquí se reúnen todos los ajustes globales de la integración:',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — el kill switch global. Desactivado → cada `chat()` / `stream()` lanza `OpenRouterDisabled`.',
            '**API key** — write-only, cifrada con Fernet derivada de `SECRET_KEY`. Un campo vacío conserva la clave actual; un valor nuevo la reemplaza; la casilla **Clear stored API key** borra la clave de la base de datos — entonces se usa `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`.',
            '**Base URL** — la raíz de la API de OpenRouter (`https://openrouter.ai/api/v1`).',
            '**Default profile** — el perfil usado cuando `chat(messages=...)` se llama sin nombre.',
            '**Request timeout** / **Max retries** — timeout HTTP y número de reintentos ante errores de transporte/5xx antes de pasar al siguiente modelo de la cadena.',
            '**Streaming enabled** — permite SSE vía `stream()` / `astream()` y `chat(stream=True)`. Desactivado por defecto.',
            '**Max parallel requests** — tope de llamadas HTTP simultáneas en este proceso (`0` = sin límite).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings: enabled, estado de la clave, base url, default profile, timeout, reintentos, streaming, límite de paralelismo',
          caption: 'OpenRouter settings: kill switch, API key write-only, perfil por defecto, timeouts, streaming y límite de paralelismo.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'El catálogo de `GET /api/v1/models` más las métricas de `/endpoints` (latencia y throughput). Las filas no pueden añadirse ni borrarse a mano, y la ficha del modelo es de solo lectura.',
        },
        {
          type: 'list',
          items: [
            '**Columnas:** nombre, `latency_ms` (p50 TTFT), throughput (tokens/s), precios prompt/completion por 1M de tokens, tamaño de pesos (`70B` / `8x7B`), `is_active`. Ordenación con clic en la columna — los valores vacíos siempre al final.',
            '**Filtros:** actividad, modalidad, precio (free / < $1 / $1–10 / ≥ $10 por 1M), velocidad (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (acción) — upsert del catálogo; los modelos desaparecidos reciben `is_active=False`.',
            '**Assign to usage profile…** (acción) — añade los modelos seleccionados al final de la cadena de un perfil; duplicados, inactivos y de pago (con `only_free_models`) se omiten con un informe.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Al abrir la lista por primera vez se actualiza desde la API y luego se sirve desde la base de datos durante 10 minutos (`CATALOG_CACHE_TIMEOUT`). La misma sincronización desde la consola: `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — catálogo de modelos de OpenRouter: nombre, latency, throughput, precio por 1M, tamaño de pesos, actividad; filtros a la derecha',
          caption: 'Catálogo de modelos: ordenación por precio/latencia, filtros por precio y velocidad, acciones de sync y assign to profile.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Un perfil es el slug que pasa tu código (`chat`, `translation`, …) más una lista ordenada de modelos: el primero se prueba primero, el resto hace fallback ante `402` / `429` / `5xx`. Los límites agotados lanzan una excepción en lugar de cambiar de modelo en silencio.',
        },
        {
          type: 'list',
          items: [
            '**Lista de perfiles:** nombre, modelo principal, actividad, only-free, límites diarios de peticiones/presupuesto y agregados del log — número de peticiones, latencia media y total, coste medio y total (un GROUP BY por página).',
            '**Formulario:** `max_tokens`, `temperature` (0–2), límites diarios/mensuales de peticiones y USD (vacío = sin límite), **only free models**, **is active**.',
            '**Inline Models (priority order):** autocompletado sobre el catálogo — la etiqueta muestra precio y latencia, y aplican los mismos filtros de precio/velocidad que en el catálogo. El orden se renormaliza al guardar, y el primer modelo de la cadena se sincroniza con el campo `model`.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — lista de perfiles de uso con agregados de peticiones, latencia y coste',
          caption: 'Perfiles de uso: cadena de modelos, límites y agregados de gasto directamente en la lista.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Un log de solo lectura. Cada intento HTTP (incluidos fallbacks y errores) se convierte en una fila cuando `DatabaseBackend` está activado (por defecto). Los límites diarios y mensuales se agregan desde esta tabla.',
        },
        {
          type: 'list',
          items: [
            '**Columnas:** hora, username, perfil, modelo, estado HTTP, tokens prompt/completion, coste, latencia.',
            '**Resumen sobre la tabla:** número de peticiones y total en USD del filtro actual. Filtros: perfil, estado, fecha; búsqueda por texto de error y username.',
            '**Username** lo aporta `CurrentUserMiddleware`; sin él las filas quedan como `anonymous`. En Celery y management commands — `bound_username("worker")` (ver «Backends de logs»).',
            '**Permisos:** el permiso independiente `view_usage_logs` permite dar a soporte acceso al gasto sin acceso a los settings.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — log de peticiones: hora, username, perfil, modelo, estado, tokens, coste, latencia; resumen arriba',
          caption: 'Log de peticiones: cada intento con tokens, coste y latencia, con el resumen del filtro sobre la tabla.',
        },
        { type: 'h3', text: 'Protección de la API key' },
        {
          type: 'list',
          items: [
            '**Cifrado.** El campo `api_key` es un `EncryptedTextField`: Fernet, clave derivada de `SECRET_KEY`.',
            '**Write-only.** Tras guardarla, el valor no puede verse — solo reemplazarse o borrarse.',
            '**Alternativa sin base de datos.** La clave puede vivir solo en el entorno (`OPENROUTER_API_KEY`), dejando el campo del admin vacío.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Rotación de SECRET_KEY',
          text: 'La clave Fernet se deriva de `SECRET_KEY`. Al cambiar `SECRET_KEY`, las API keys guardadas en la base de datos se vuelven ilegibles — habrá que introducirlas de nuevo.',
        },
        { type: 'h3', text: 'Validaciones' },
        {
          type: 'list',
          items: [
            '`temperature` — solo en el rango 0…2.',
            'Los modelos principal y de fallback deben estar activos.',
            'Con `only_free_models`, todos los modelos del perfil deben ser gratuitos.',
            'El par `(profile, model)` de la cadena de fallback es único.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Referencia',
      title: 'Referencia de la API',
      lead: 'Imports públicos de django_openrouter: fachadas, clientes, el resultado y las excepciones.',
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
          text: '`profile_name=None` usa el perfil por defecto de los settings. Llamar sin `messages` es un `TypeError`. Si el perfil no existe o está inactivo — `ConfigurationError`.',
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
    delta: str                      # texto del chunk actual
    content: str                    # texto acumulado de la respuesta
    model_used: str = ""
    done: bool = False              # True en el chunk final
    result: ChatResult | None = None  # resultado completo en el chunk final
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: 'Excepciones' },
        {
          type: 'table',
          head: ['Excepción', 'Cuándo'],
          rows: [
            ['`OpenRouterError`', 'Clase base de todas las excepciones de la librería'],
            ['`ConfigurationError`', 'Sin clave, perfil o perfil por defecto; streaming desactivado'],
            ['`OpenRouterDisabled`', 'Kill switch: `enabled=False` en los settings'],
            ['`ModelDisabled`', 'Perfil/modelo inactivo o violación de `only_free_models`'],
            ['`RateLimitExceeded`', 'Límite diario/mensual de peticiones agotado'],
            ['`BudgetExceeded`', 'Presupuesto diario/mensual agotado'],
            ['`OpenRouterAPIError`', 'Error de la API tras reintentos y fallback; lleva `status_code`'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'manejo de errores',
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
          code: `stats = profile.get_usage("day")    # o "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # inicio del periodo (datetime)`,
        },
        {
          type: 'p',
          text: 'Seguro de llamar tanto dentro como fuera de `transaction.atomic()` — el wrapper se crea automáticamente. El bloqueo se toma sobre la fila del perfil, no sobre los logs, así que el crecimiento de la tabla `RequestLog` no dispara los bloqueos.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Referencia',
      title: 'FAQ',
      lead: 'Preguntas frecuentes y trampas comunes.',
      blocks: [
        { type: 'h3', text: 'Los cambios del admin no se aplican' },
        {
          type: 'p',
          text: 'Lo más probable es que ejecutes varios procesos con `LocMemCache`: la invalidación de caché solo ocurrió en el proceso donde pulsaste «Guardar». Cambia a Redis/Memcached y define el alias en `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '«No usage profile specified and default_profile is not set»' },
        {
          type: 'p',
          text: 'Llamaste a `chat()` sin nombre de perfil y no hay perfil por defecto. Pasa el slug como primer argumento o elige un **default profile** en **OpenRouter settings**.',
        },
        { type: 'h3', text: '«Usage profile X is not found or inactive»' },
        {
          type: 'p',
          text: 'No existe un perfil con ese slug o su casilla `is_active` está desmarcada. Solo los perfiles activos llegan a la configuración de runtime.',
        },
        { type: 'h3', text: '¿Hay soporte de streaming?' },
        {
          type: 'p',
          text: 'Sí. Activa **Streaming enabled** en **OpenRouter settings** y usa `stream()` / `astream()` o `chat(stream=True)`. Con el streaming activado, un `chat()` normal también va por SSE; `stream=False` fuerza una respuesta JSON.',
        },
        { type: 'h3', text: 'Los límites no saltan' },
        {
          type: 'p',
          text: 'Comprueba que `django_openrouter.log_backends.DatabaseBackend` esté en `OPENROUTER["LOG_BACKENDS"]` (lo está por defecto): los límites y presupuestos se agregan desde la tabla `RequestLog`, y sin este backend el gasto es invisible para las comprobaciones.',
        },
        { type: 'h3', text: '¿Cómo pongo el admin en mi idioma?' },
        {
          type: 'p',
          text: 'Todas las etiquetas del admin están envueltas en `gettext_lazy`, y los catálogos de traducción para decenas de locales se incluyen en el paquete (`locale/<locale_de_django>/LC_MESSAGES/django.po`). El proyecto anfitrión decide qué idiomas están activos: configura `LANGUAGE_CODE` / `LANGUAGES` y conecta `LocaleMiddleware`. Tras editar los `.po`, compila los catálogos — `python manage.py compilemessages -l es`. Ojo: el inglés del paquete es `en_GB` / `en-gb`; no existe un catálogo base `en`.',
        },
        { type: 'h3', text: '¿Cómo calculo el gasto a mano?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: '¿Puedo usarlo sin el admin?' },
        {
          type: 'p',
          text: 'No — esa es la idea de la librería: la política (modelos, límites, presupuestos) vive en la base de datos y la gestiona un operador. La clave, eso sí, puede vivir solo en el entorno.',
        },
      ],
    },
  ],
}
