import type { DocsContent } from './types'

export const fr: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter pour Django — modèles, profils, budgets et journaux gérés depuis l’admin',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'Rechercher dans la doc…',
    searchEmpty: 'Aucun résultat. Essayez une autre recherche.',
    onThisPage: 'Sur cette page',
    copied: 'Copié',
    copy: 'Copier',
    editGithub: 'GitHub',
    prev: 'Précédent',
    next: 'Suivant',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: 'Démarrez en 3 minutes',
    heroGithub: 'Dépôt',
    builtWith: 'Documentation de',
    license: 'Licence MIT',
  },
  ui: {
    theme: 'Changer de thème',
    language: 'Langue',
    openMenu: 'Ouvrir le menu',
    closeMenu: 'Fermer le menu',
  },
  sections: [
    {
      id: 'intro',
      group: 'Démarrage',
      title: 'Introduction',
      lead: 'Une application Django réutilisable qui fait d’OpenRouter une ressource administrée : modèles, profils d’usage, budgets et journaux de requêtes vivent en base et se configurent depuis l’admin — sans redéploiement.',
      blocks: [
        {
          type: 'p',
          text: 'Votre code produit — traduction, chat, résumés — dialogue avec OpenRouter via cette bibliothèque plutôt qu’avec des clés et des identifiants de modèles codés en dur dans `settings.py`. Un opérateur choisit les modèles actifs, fixe des limites quotidiennes et mensuelles et suit les dépenses directement dans l’admin.',
        },
        { type: 'h3', text: 'Pourquoi pas settings.py ?' },
        {
          type: 'p',
          text: 'Une ligne comme `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` dans les settings impose un déploiement pour chaque changement de modèle, ajustement de budget ou coupure d’urgence. `django-openrouter` conserve cette politique d’exécution en base de données, la met en cache et vérifie les limites avant chaque requête.',
        },
        {
          type: 'list',
          items: [
            '**Catalogue de modèles en base.** `sync_models` récupère le catalogue OpenRouter (`GET /api/v1/models` + `/endpoints`) avec prix, latence (p50 TTFT), throughput et taille des poids.',
            '**Profils d’usage.** Un slug stable (`chat`, `translation`) → une chaîne ordonnée de modèles, `max_tokens`, `temperature`, limites et budgets.',
            '**Limites avant la requête.** Les limites quotidiennes/mensuelles de requêtes et les budgets en USD sont vérifiés avant l’appel HTTP. L’épuisement est une exception, pas un fallback silencieux.',
            '**Streaming (SSE).** `stream()` / `astream()` délivrent la réponse par morceaux ; activé d’une simple case à cocher dans les réglages.',
            '**Chaque appel est journalisé.** Chaque tentative est écrite en base, dans un fichier JSONL ou dans ClickHouse (backends enfichables) — avec le username de l’utilisateur appelant.',
            '**Clés en sécurité.** La clé API de l’admin est chiffrée (Fernet, dérivée de `SECRET_KEY`) et en écriture seule : après l’enregistrement, elle ne peut être que remplacée ou effacée.',
            '**Kill switch et parallélisme.** La case `enabled` arrête tous les appels instantanément, et `max_parallel_requests` plafonne les requêtes HTTP simultanées par processus.',
          ],
        },
        { type: 'h3', text: 'Fonctionnalités' },
        {
          type: 'table',
          head: ['Fonctionnalité', 'Statut'],
          rows: [
            ['Clients sync et async', '`OpenRouterClient`, `AsyncOpenRouterClient`'],
            ['Façades en une ligne', '`chat()`, `achat()`, `stream()`, `astream()`'],
            ['Chaînes de fallback de modèles', 'Sur 402 / 429 / 5xx, dans l’ordre configuré'],
            ['Réessais des erreurs de transport', 'Configurable via `max_retries`'],
            ['Streaming (SSE)', '`stream()` / `astream()` / `chat(stream=True)`, désactivé par défaut'],
            ['Backends de logs', 'Base de données (défaut), fichier JSONL avec rotation, ClickHouse'],
            ['Plafond de parallélisme', '`max_parallel_requests`, 10 par défaut'],
            ['Admin dans votre langue', 'Catalogues de traduction pour des dizaines de locales inclus'],
            ['Typage', 'Le paquet embarque `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Compatibilité',
          text: 'Python 3.11–3.13, Django 4.2, 5.0, 5.1, 5.2 et 6.0. Dépendances : `django>=4.2`, `httpx>=0.27`, `cryptography>=42`.',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'Démarrage',
      title: 'Démarrage rapide',
      lead: 'De l’installation à la première réponse du modèle — quatre étapes.',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'Installez le paquet',
              text: 'Une seule commande depuis PyPI : `pip install django-openrouter`.',
            },
            {
              title: 'Branchez l’app et le middleware',
              text: 'Ajoutez `django_openrouter` à `INSTALLED_APPS` et `django_openrouter.middleware.CurrentUserMiddleware` à `MIDDLEWARE`, puis lancez `python manage.py migrate`.',
            },
            {
              title: 'Configurez dans l’admin',
              text: 'Ouvrez **OpenRouter → OpenRouter settings** : collez votre clé API (elle sera chiffrée) ou laissez le champ vide et définissez `OPENROUTER_API_KEY` dans l’environnement.',
            },
            {
              title: 'Synchronisez le catalogue et créez un profil',
              text: 'Lancez `python manage.py sync_models`, puis créez un **Usage profile** avec le slug `chat`, ajoutez des modèles par ordre de priorité et faites-en éventuellement le profil par défaut.',
            },
          ],
        },
        { type: 'h3', text: '1. Installation' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. Branchement et migrations' },
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
          text: '`CurrentUserMiddleware` se place **après** `AuthenticationMiddleware` et enregistre le username de l’utilisateur appelant dans le journal des requêtes. Sans lui, toutes les lignes sont marquées `anonymous`.',
        },
        { type: 'h3', text: '3. Configuration dans Django admin' },
        {
          type: 'list',
          ordered: true,
          items: [
            'Ouvrez **OpenRouter → OpenRouter settings**. Collez votre clé API — elle est chiffrée et n’est plus jamais affichée — ou laissez le champ vide et définissez `OPENROUTER_API_KEY` dans l’environnement.',
            'Lancez `python manage.py sync_models` pour récupérer le catalogue des modèles (`GET /api/v1/models`).',
            'Créez un **Usage profile** (slug `translation`, `chat`, …) et ajoutez un ou plusieurs modèles par ordre de priorité (le premier est essayé en premier), plus les limites et budgets.',
            'Définissez le profil comme **default profile** si vous voulez appeler `chat(messages=...)` sans nom.',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Captures d’écran',
          text: 'Les quatre sections de l’admin — réglages, catalogue, profils et journal — sont détaillées avec captures d’écran dans la section « Admin ».',
        },
        { type: 'h3', text: '4. Premier appel' },
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
          title: 'Test sans clé enregistrée',
          text: 'Le catalogue peut être synchronisé avec une clé à usage unique : `python manage.py sync_models --api-key sk-or-...` — elle ne sera pas enregistrée en base.',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'Guides',
      title: 'Configuration',
      lead: 'Ordre de résolution de la clé API, le dictionnaire settings.OPENROUTER et le fonctionnement du cache de configuration runtime.',
      blocks: [
        { type: 'h3', text: 'D’où vient la clé API' },
        {
          type: 'p',
          text: 'Si le champ de la clé dans l’admin est vide, la bibliothèque cherche la clé dans cet ordre :',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY` (setting de premier niveau)',
            'la variable d’environnement `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'Une clé enregistrée dans l’admin prime toujours sur les trois options ci-dessus. Elle est stockée chiffrée (Fernet, dérivée de `SECRET_KEY`) et illisible après enregistrement.',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['Clé', 'Défaut', 'Description'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'Durée en secondes de conservation de la config runtime dans le cache Django'],
            ['`CACHE_ALIAS`', '`"default"`', 'Alias de cache (`django.core.cache`)'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', 'Durée en secondes pendant laquelle l’admin ne resynchronise pas le catalogue'],
            ['`API_KEY`', 'non défini', 'Clé de secours si le champ de l’admin est vide'],
            ['`HTTP_REFERER`', 'non défini', 'En-tête `HTTP-Referer` (attribution de l’app dans OpenRouter)'],
            ['`X_TITLE`', 'non défini', 'En-tête `X-Title`'],
            ['`LOG_BACKENDS`', 'BD seule', 'Où écrire les journaux de requêtes — voir la section « Backends de logs »'],
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
          text: 'Le `LocMemCache` de base suffit. Redis ou Memcached sont optionnels — pointez simplement `CACHE_ALIAS` vers eux.',
        },
        {
          type: 'callout',
          kind: 'info',
          title: 'Les réglages vivent dans l’admin, pas dans settings.py',
          text: 'Timeout, nombre de réessais, kill switch, streaming (`streaming_enabled`) et plafond de requêtes parallèles (`max_parallel_requests`) vivent dans **OpenRouter settings** de l’admin — détails avec capture dans la section « Admin ».',
        },
        { type: 'h3', text: 'Comment fonctionne le cache' },
        {
          type: 'p',
          text: 'Le client ne lit pas la base directement mais un instantané `RuntimeConfig` mis en cache : réglages, profils actifs et leurs modèles de fallback. Les signaux `post_save` / `post_delete` de tous les modèles de l’app invalident le cache instantanément — les modifications de l’admin s’appliquent sans redémarrage, et `CACHE_TIMEOUT` n’est qu’un filet de sécurité.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache et multi-processus',
          text: 'Avec `LocMemCache`, chaque processus garde sa propre copie du cache : l’invalidation n’a lieu que dans le processus où vous avez enregistré dans l’admin. Pour un déploiement multi-processus, utilisez Redis/Memcached via `CACHE_ALIAS`.',
        },
      ],
    },
    {
      id: 'usage',
      group: 'Guides',
      title: 'Utilisation',
      lead: 'Les façades chat() / achat() / stream() / astream(), les classes clientes, les surcharges par appel et la structure du résultat.',
      blocks: [
        { type: 'h3', text: 'La façade chat()' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # slug du profil ; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: 'Client synchrone' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: 'Appel asynchrone' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# ou via la classe
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: 'Le client asynchrone reflète le synchrone : les opérations ORM passent par `sync_to_async`, le HTTP par `httpx.AsyncClient`.',
        },
        { type: 'h3', text: 'Streaming (SSE)' },
        {
          type: 'p',
          text: 'Le streaming est désactivé par défaut. Activez **Streaming enabled** dans **OpenRouter settings**, puis `stream()` et `astream()` délivrent la réponse en morceaux `ChatChunk` :',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# morceau final : done=True, chunk.result contient le ChatResult complet

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` utilise le même transport SSE et renvoie le `ChatResult` complet. Si le streaming est activé dans les réglages, un `chat()` simple passe aussi par SSE ; `stream=False` force une réponse JSON classique. Appeler avec le streaming désactivé lève `ConfigurationError` avant toute requête HTTP.',
        },
        {
          type: 'table',
          head: ['Champ de ChatChunk', 'Type', 'Description'],
          rows: [
            ['`delta`', '`str`', 'Texte du morceau courant'],
            ['`content`', '`str`', 'Texte accumulé jusqu’ici'],
            ['`model_used`', '`str`', 'Le modèle qui produit la réponse'],
            ['`done`', '`bool`', '`True` sur le morceau final'],
            ['`result`', '`ChatResult | None`', 'Résultat complet sur le morceau final'],
            ['`raw`', '`dict`', 'L’événement SSE brut'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Fallback et streaming',
          text: 'Le fallback vers le modèle suivant n’est possible qu’avant l’émission du premier morceau. Si un modèle commence à streamer puis échoue en cours de route, l’erreur est renvoyée à l’appelant : une partie de la réponse a déjà été envoyée au client.',
        },
        { type: 'h3', text: 'Surcharges par appel' },
        {
          type: 'p',
          text: 'Tous les `**overrides` sont transmis au corps de la requête. `max_tokens` et `temperature` remplacent les valeurs du profil, et `model` place temporairement le modèle indiqué en tête de chaîne :',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # doit exister dans le catalogue
    response_format={"type": "json_object"},  # tout paramètre OpenRouter
)`,
        },
        { type: 'h3', text: 'Parallélisme' },
        {
          type: 'p',
          text: 'Le champ **Max parallel requests** des réglages (défaut `10`, `0` = illimité) plafonne le nombre de requêtes HTTP simultanées vers OpenRouter dans le processus courant — pour `chat()` comme pour `stream()`, en sync comme en async.',
        },
        { type: 'h3', text: 'Résultat : ChatResult' },
        {
          type: 'table',
          head: ['Champ', 'Type', 'Description'],
          rows: [
            ['`content`', '`str`', 'Texte de la réponse (parties texte concaténées pour le contenu multipart)'],
            ['`prompt_tokens`', '`int`', 'Tokens du prompt selon `usage`'],
            ['`completion_tokens`', '`int`', 'Tokens de la réponse selon `usage`'],
            ['`cost_usd`', '`Decimal`', 'Coût : d’après les prix du catalogue, sinon `usage.cost` de l’API'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'Coût selon le catalogue — pour rapprochement avec la facturation'],
            ['`model_used`', '`str`', 'Le modèle qui a réellement répondu'],
            ['`latency_ms`', '`int`', 'Latence de la tentative réussie'],
            ['`raw`', '`dict`', 'Réponse JSON brute d’OpenRouter'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: 'Guides',
      title: 'Catalogue de modèles',
      lead: 'Comment sync_models remplit le catalogue et ce que stocke OpenRouterModel.',
      blocks: [
        { type: 'h3', text: 'La commande sync_models' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # clé à usage unique, jamais enregistrée` },
        {
          type: 'p',
          text: 'La commande fait un upsert du catalogue (`GET /api/v1/models`) et l’enrichit des métriques `/endpoints` — latence p50 et throughput. Elle ne supprime rien : les modèles disparus d’OpenRouter reçoivent `is_active=False`. Les profils qui référencent un tel modèle ne cassent pas — les appels échouent simplement avec `ModelDisabled` jusqu’à ce que vous changiez le profil.',
        },
        { type: 'h3', text: 'Champs du modèle' },
        {
          type: 'table',
          head: ['Champ', 'Description'],
          rows: [
            ['`model_id`', 'Identifiant OpenRouter, ex. `anthropic/claude-3.5-sonnet`'],
            ['`name`', 'Nom lisible'],
            ['`context_length`', 'Taille du contexte en tokens'],
            ['`pricing`', 'JSON des prix par token : `prompt`, `completion`, optionnel `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'Prix par token en décimal — pour trier et filtrer dans l’admin'],
            ['`latency_ms`', 'p50 TTFT du meilleur endpoint, en millisecondes'],
            ['`throughput`', 'p50 throughput du meilleur endpoint, tokens/s'],
            ['`parameter_count`', 'Nombre approximatif de poids (70B → 70000000000), pour le tri'],
            ['`parameter_label`', 'Taille affichée avec unité : `70B`, `340M`, `8x7B`'],
            ['`supported_parameters`', 'Liste des paramètres supportés'],
            ['`modality`', 'Modalité, ex. `text->text`'],
            ['`is_active`', 'Si le modèle peut être choisi dans les profils'],
            ['`last_synced_at`', 'Quand la synchronisation l’a vu pour la dernière fois'],
            ['`is_free` (property)', '`True` si les prix `prompt`/`completion`/`request` sont nuls'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'Modèles gratuits uniquement',
          text: 'Le flag de profil `only_free_models` n’autorise que les modèles à prix nul du catalogue — pratique pour les environnements de dev et les démos. Vérifié pour le modèle principal comme pour chaque fallback.',
        },
      ],
    },
    {
      id: 'limits',
      group: 'Guides',
      title: 'Limites, budgets et fallback',
      lead: 'Ce qui est vérifié avant la requête, ce qui se passe en cas d’erreur OpenRouter et quand le fallback se déclenche.',
      blocks: [
        { type: 'h3', text: 'Limites du profil' },
        {
          type: 'p',
          text: 'La consommation est calculée depuis `RequestLog` pour le jour et le mois calendaires courants (dans le `TIME_ZONE` actif). Un champ de limite vide (`null`) signifie « illimité ».',
        },
        {
          type: 'table',
          head: ['Champ du profil', 'Ce qu’il plafonne', 'Exception'],
          rows: [
            ['`max_requests_per_day`', 'Nombre de requêtes par jour', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', 'Nombre de requêtes par mois', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', 'Somme des `cost_usd` par jour', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', 'Somme des `cost_usd` par mois', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: 'La vérification s’exécute dans une transaction : la ligne du profil est verrouillée avec `select_for_update` et les agrégats sont calculés sous ce verrou — les requêtes concurrentes ne peuvent pas dépasser la limite en course.',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'Les limites exigent DatabaseBackend',
          text: 'Les agrégats sont calculés sur la table `RequestLog`, donc `DatabaseBackend` doit rester dans `LOG_BACKENDS` (c’est le défaut). Si vous le retirez, `check_limits()` ne voit aucune dépense et les limites cessent de fonctionner.',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Pas de contournement silencieux',
          text: 'L’épuisement d’une limite ou d’un budget est une exception (`BudgetExceeded` / `RateLimitExceeded`) levée avant l’appel HTTP. La bibliothèque ne bascule **pas** vers un autre modèle pour faire passer la requête.',
        },
        { type: 'h3', text: 'Chaîne de fallback' },
        {
          type: 'p',
          text: 'Les modèles de fallback n’interviennent que lorsque OpenRouter lui-même renvoie `402`, `429` ou `5xx`. L’ordre est défini par le champ `order` dans l’admin ; les doublons de la chaîne sont écartés. Les modèles interdits par les règles du profil (inactifs, ou payants avec `only_free_models`) sont ignorés.',
        },
        {
          type: 'list',
          items: [
            '**Erreurs de transport et 5xx** — réessayées jusqu’à `max_retries` fois sur le même modèle, puis fallback.',
            '**402 / 429** — passage immédiat au modèle suivant de la chaîne.',
            '**Autres 4xx** (ex. 400) — levées immédiatement, sans fallback : la requête est probablement invalide pour tous les modèles.',
            '**Chaque tentative** — y compris les échecs — est écrite dans le journal.',
          ],
        },
        { type: 'h3', text: 'Kill switch global' },
        {
          type: 'p',
          text: 'La case `enabled` de **OpenRouter settings** arrête tout instantanément : tout appel à `chat()` lève `OpenRouterDisabled` avant même la vérification des limites. Pratique pour les incidents et les arrêts planifiés.',
        },
      ],
    },
    {
      id: 'logging',
      group: 'Guides',
      title: 'Backends de logs',
      lead: 'Chaque appel HTTP est écrit dans tous les backends listés dans OPENROUTER["LOG_BACKENDS"] : la base du projet, un fichier JSONL, ClickHouse — ou votre propre classe.',
      blocks: [
        {
          type: 'p',
          text: 'Chaque entrée de la liste est soit un dotted path vers une classe (réglages par défaut), soit un dictionnaire avec la clé `BACKEND` et des paramètres. Si `LOG_BACKENDS` n’est pas défini, les logs ne sont écrits que dans la base du projet (`RequestLog`).',
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
        { type: 'h3', text: 'DatabaseBackend (par défaut)' },
        {
          type: 'p',
          text: 'Écrit des lignes dans le modèle `RequestLog`. Les limites et budgets quotidiens/mensuels s’agrègent depuis cette table — gardez ce backend activé si vous utilisez les limites : sans lui, `check_limits()` ne voit aucune dépense.',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'JSON Lines vers un fichier avec rotation par taille (`RotatingFileHandler`) : une ligne = un objet JSON avec les champs `created_at`, `profile`, `model`, `status_code`, `error_message`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `username`.',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'Insère du `FORMAT JSONEachRow` via l’interface HTTP de ClickHouse. Aucune dépendance supplémentaire — le même `httpx` est utilisé. Les noms de base et de table sont validés comme identifiants pour éviter toute injection. Créez la table ainsi :',
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
          text: 'Tous les backends configurés reçoivent chaque enregistrement, et une défaillance de backend (disque plein, ClickHouse injoignable) ne casse jamais `chat()` — l’erreur est consignée dans le logger `django_openrouter`.',
        },
        { type: 'h3', text: 'Qui a fait la requête' },
        {
          type: 'p',
          text: 'Chaque enregistrement porte le username de l’utilisateur Django à l’origine de l’appel. Il est fourni par `django_openrouter.middleware.CurrentUserMiddleware` (après `AuthenticationMiddleware`). Les appels sans utilisateur ou hors requête HTTP sont journalisés comme `anonymous`. Dans Celery et les commandes de gestion, définissez le nom manuellement :',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'Backend personnalisé' },
        {
          type: 'p',
          text: 'Héritez de `django_openrouter.log_backends.LogBackend`, implémentez `write()` (et optionnellement `awrite()`) et ajoutez le dotted path de la classe à `LOG_BACKENDS`.',
        },
      ],
    },
    {
      id: 'admin',
      group: 'Guides',
      title: 'L’admin',
      lead: 'Toute la politique runtime vit dans quatre sections du Django admin : réglages, catalogue de modèles, profils d’usage et journal des requêtes.',
      blocks: [
        {
          type: 'table',
          head: ['Section', 'Rôle'],
          rows: [
            ['**OpenRouter settings**', 'Kill switch, clé API chiffrée, streaming, timeouts'],
            ['**OpenRouter models**', 'Le catalogue d’OpenRouter : prix, latence, throughput'],
            ['**Usage profiles**', 'Chaîne de modèles, limites, budgets, statistiques de dépense'],
            ['**Request logs**', 'Tokens, coût et latence de chaque appel (lecture seule)'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'Un singleton : la liste redirige vers l’unique ligne, impossible à supprimer. Tous les réglages globaux de l’intégration sont réunis ici :',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — le kill switch global. Désactivé → chaque `chat()` / `stream()` lève `OpenRouterDisabled`.',
            '**API key** — écriture seule, chiffrée avec Fernet dérivée de `SECRET_KEY`. Un champ vide conserve la clé actuelle ; une nouvelle valeur la remplace ; la case **Clear stored API key** efface la clé de la base — `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]` est alors utilisée.',
            '**Base URL** — la racine de l’API OpenRouter (`https://openrouter.ai/api/v1`).',
            '**Default profile** — le profil utilisé quand `chat(messages=...)` est appelé sans nom.',
            '**Request timeout** / **Max retries** — timeout HTTP et nombre de réessais sur erreurs de transport/5xx avant de passer au modèle suivant de la chaîne.',
            '**Streaming enabled** — autorise le SSE via `stream()` / `astream()` et `chat(stream=True)`. Désactivé par défaut.',
            '**Max parallel requests** — plafond d’appels HTTP simultanés dans ce processus (`0` = illimité).',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings : enabled, statut de la clé, base url, default profile, timeout, réessais, streaming, plafond de parallélisme',
          caption: 'OpenRouter settings : kill switch, clé API en écriture seule, profil par défaut, timeouts, streaming et plafond de parallélisme.',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: 'Le catalogue de `GET /api/v1/models` plus les métriques `/endpoints` (latence et throughput). Les lignes ne peuvent être ni ajoutées ni supprimées à la main, et la fiche modèle est en lecture seule.',
        },
        {
          type: 'list',
          items: [
            '**Colonnes :** nom, `latency_ms` (p50 TTFT), throughput (tokens/s), prix prompt/completion par 1M de tokens, taille des poids (`70B` / `8x7B`), `is_active`. Tri au clic sur la colonne — les valeurs vides toujours en fin.',
            '**Filtres :** activité, modalité, prix (free / < $1 / $1–10 / ≥ $10 par 1M), vitesse (< 400 ms / 400–1200 / ≥ 1200).',
            '**Sync catalog with OpenRouter** (action) — upsert du catalogue ; les modèles disparus reçoivent `is_active=False`.',
            '**Assign to usage profile…** (action) — ajoute les modèles sélectionnés en fin de chaîne d’un profil ; doublons, inactifs et payants (avec `only_free_models`) ignorés avec un rapport.',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: 'À la première ouverture, la liste est rafraîchie depuis l’API puis servie depuis la base pendant 10 minutes (`CATALOG_CACHE_TIMEOUT`). La même synchronisation en console : `python manage.py sync_models`.',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — catalogue de modèles OpenRouter : nom, latence, throughput, prix par 1M, taille des poids, activité ; filtres à droite',
          caption: 'Catalogue de modèles : tri par prix/latence, filtres par prix et vitesse, actions sync et assign to profile.',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'Un profil, c’est le slug que passe votre code (`chat`, `translation`, …) plus une liste ordonnée de modèles : le premier est essayé en premier, les autres font fallback sur `402` / `429` / `5xx`. Les limites épuisées lèvent une exception au lieu de changer de modèle en silence.',
        },
        {
          type: 'list',
          items: [
            '**Liste des profils :** nom, modèle principal, activité, only-free, limites quotidiennes de requêtes/budget et agrégats du journal — nombre de requêtes, latence moyenne et totale, coût moyen et total (un GROUP BY par page).',
            '**Formulaire :** `max_tokens`, `temperature` (0–2), limites quotidiennes/mensuelles de requêtes et d’USD (vide = illimité), **only free models**, **is active**.',
            '**Inline Models (priority order) :** autocomplétion sur le catalogue — le libellé affiche prix et latence, et les mêmes filtres prix/vitesse que le catalogue s’appliquent. L’ordre est renormalisé à l’enregistrement, et le premier modèle de la chaîne est synchronisé vers le champ `model`.',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — liste des profils d’usage avec agrégats de requêtes, latence et coût',
          caption: 'Profils d’usage : chaîne de modèles, limites et agrégats de dépense directement dans la liste.',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: 'Un journal en lecture seule. Chaque tentative HTTP (fallbacks et erreurs inclus) devient une ligne quand `DatabaseBackend` est activé (par défaut). Les limites quotidiennes et mensuelles s’agrègent depuis cette table.',
        },
        {
          type: 'list',
          items: [
            '**Colonnes :** heure, username, profil, modèle, statut HTTP, tokens prompt/completion, coût, latence.',
            '**Résumé au-dessus du tableau :** nombre de requêtes et total USD pour le filtre courant. Filtres : profil, statut, date ; recherche sur le texte d’erreur et le username.',
            '**Username** fourni par `CurrentUserMiddleware` ; sans lui les lignes sont marquées `anonymous`. Dans Celery et les commandes de gestion — `bound_username("worker")` (voir « Backends de logs »).',
            '**Permissions :** la permission dédiée `view_usage_logs` permet de donner au support l’accès aux dépenses sans accès aux réglages.',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — journal des requêtes : heure, username, profil, modèle, statut, tokens, coût, latence ; résumé en haut',
          caption: 'Journal des requêtes : chaque tentative avec tokens, coût et latence, résumé du filtre au-dessus du tableau.',
        },
        { type: 'h3', text: 'Protection de la clé API' },
        {
          type: 'list',
          items: [
            '**Chiffrement.** Le champ `api_key` est un `EncryptedTextField` : Fernet, clé dérivée de `SECRET_KEY`.',
            '**Écriture seule.** Après enregistrement, la valeur ne peut être consultée — seulement remplacée ou effacée.',
            '**Alternative sans base.** La clé peut vivre uniquement dans l’environnement (`OPENROUTER_API_KEY`), le champ de l’admin restant vide.',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'Rotation de SECRET_KEY',
          text: 'La clé Fernet est dérivée de `SECRET_KEY`. Changer `SECRET_KEY` rend les clés API stockées en base illisibles — il faudra les saisir à nouveau.',
        },
        { type: 'h3', text: 'Validations' },
        {
          type: 'list',
          items: [
            '`temperature` — uniquement dans l’intervalle 0…2.',
            'Les modèles principal et de fallback doivent être actifs.',
            'Avec `only_free_models`, tous les modèles du profil doivent être gratuits.',
            'Le couple `(profile, model)` de la chaîne de fallback est unique.',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'Référence',
      title: 'Référence API',
      lead: 'Imports publics de django_openrouter : façades, clients, résultat et exceptions.',
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
          text: '`profile_name=None` utilise le profil par défaut des réglages. Appeler sans `messages` est un `TypeError`. Si le profil est introuvable ou inactif — `ConfigurationError`.',
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
    delta: str                      # texte du morceau courant
    content: str                    # texte accumulé de la réponse
    model_used: str = ""
    done: bool = False              # True sur le morceau final
    result: ChatResult | None = None  # résultat complet sur le morceau final
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: 'Exceptions' },
        {
          type: 'table',
          head: ['Exception', 'Quand'],
          rows: [
            ['`OpenRouterError`', 'Classe de base de toutes les exceptions de la bibliothèque'],
            ['`ConfigurationError`', 'Pas de clé, de profil ou de profil par défaut ; streaming désactivé'],
            ['`OpenRouterDisabled`', 'Kill switch : `enabled=False` dans les réglages'],
            ['`ModelDisabled`', 'Profil/modèle inactif ou violation de `only_free_models`'],
            ['`RateLimitExceeded`', 'Limite quotidienne/mensuelle de requêtes épuisée'],
            ['`BudgetExceeded`', 'Budget quotidien/mensuel épuisé'],
            ['`OpenRouterAPIError`', 'Erreur API après réessais et fallback ; porte `status_code`'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'gestion des erreurs',
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
          code: `stats = profile.get_usage("day")    # ou "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # début de la période (datetime)`,
        },
        {
          type: 'p',
          text: 'Sûr à appeler aussi bien dans `transaction.atomic()` qu’en dehors — le wrapper est créé automatiquement. Le verrou porte sur la ligne du profil, pas sur les logs, donc la croissance de la table `RequestLog` ne fait pas exploser les verrous.',
        },
      ],
    },
    {
      id: 'faq',
      group: 'Référence',
      title: 'FAQ',
      lead: 'Questions fréquentes et pièges courants.',
      blocks: [
        { type: 'h3', text: 'Les changements de l’admin ne s’appliquent pas' },
        {
          type: 'p',
          text: 'Vous exécutez probablement plusieurs processus avec `LocMemCache` : l’invalidation du cache n’a eu lieu que dans le processus où vous avez cliqué sur « Enregistrer ». Passez à Redis/Memcached et définissez l’alias dans `OPENROUTER["CACHE_ALIAS"]`.',
        },
        { type: 'h3', text: '« No usage profile specified and default_profile is not set »' },
        {
          type: 'p',
          text: 'Vous avez appelé `chat()` sans nom de profil et aucun profil par défaut n’est défini. Passez le slug en premier argument ou choisissez un **default profile** dans **OpenRouter settings**.',
        },
        { type: 'h3', text: '« Usage profile X is not found or inactive »' },
        {
          type: 'p',
          text: 'Aucun profil avec ce slug, ou sa case `is_active` est décochée. Seuls les profils actifs entrent dans la configuration runtime.',
        },
        { type: 'h3', text: 'Le streaming est-il supporté ?' },
        {
          type: 'p',
          text: 'Oui. Activez **Streaming enabled** dans **OpenRouter settings** et utilisez `stream()` / `astream()` ou `chat(stream=True)`. Avec le streaming activé, un `chat()` simple passe aussi par SSE ; `stream=False` force une réponse JSON.',
        },
        { type: 'h3', text: 'Les limites ne se déclenchent pas' },
        {
          type: 'p',
          text: 'Vérifiez que `django_openrouter.log_backends.DatabaseBackend` figure dans `OPENROUTER["LOG_BACKENDS"]` (c’est le cas par défaut) : les limites et budgets s’agrègent depuis la table `RequestLog`, et sans ce backend la dépense est invisible pour les vérifications.',
        },
        { type: 'h3', text: 'Comment avoir l’admin dans ma langue ?' },
        {
          type: 'p',
          text: 'Tous les libellés de l’admin sont enveloppés dans `gettext_lazy`, et les catalogues de traduction pour des dizaines de locales sont livrés dans le paquet (`locale/<locale_django>/LC_MESSAGES/django.po`). Le projet hôte décide des langues actives : configurez `LANGUAGE_CODE` / `LANGUAGES` et branchez `LocaleMiddleware`. Après modification des `.po`, compilez les catalogues — `python manage.py compilemessages -l fr`. Attention : l’anglais du paquet est `en_GB` / `en-gb` ; il n’existe pas de catalogue de base `en`.',
        },
        { type: 'h3', text: 'Comment calculer la dépense à la main ?' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: 'Peut-on s’en servir sans l’admin ?' },
        {
          type: 'p',
          text: 'Non — c’est la raison d’être de la bibliothèque : la politique (modèles, limites, budgets) vit en base et est gérée par un opérateur. La clé, elle, peut vivre uniquement dans l’environnement.',
        },
      ],
    },
  ],
}
