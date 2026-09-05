import type { DocsContent } from './types'

export const zh: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: '面向 Django 的 OpenRouter — 通过管理后台管理模型、用量配置、预算和请求日志',
    version: '0.1.2',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: '搜索文档…',
    searchEmpty: '没有找到结果。请换一个关键词试试。',
    onThisPage: '本页目录',
    copied: '已复制',
    copy: '复制',
    editGithub: 'GitHub',
    prev: '上一页',
    next: '下一页',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: '3 分钟快速开始',
    heroGithub: '仓库',
    builtWith: '文档项目',
    license: 'MIT 许可证',
  },
  ui: {
    theme: '切换主题',
    language: '语言',
    openMenu: '打开菜单',
    closeMenu: '关闭菜单',
  },
  sections: [
    {
      id: 'intro',
      group: '入门',
      title: '简介',
      lead: '可复用的 Django 应用，把 OpenRouter 变成可管理的资源：模型、用量配置、预算和请求日志存放在数据库中，通过管理后台配置 — 无需重新部署。',
      blocks: [
        {
          type: 'p',
          text: '产品代码 — 翻译、聊天、摘要 — 通过本库访问 OpenRouter，而不是把密钥和模型 ID 写死在 `settings.py` 里。运维人员在管理后台选择启用的模型、设置每日/每月限额，并直接查看花费。',
        },
        { type: 'h3', text: '为什么不用 settings.py？' },
        {
          type: 'p',
          text: '在配置里写一行 `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"`，每次换模型、改预算或紧急关停都要重新部署。`django-openrouter` 把运行时策略放在数据库中、加以缓存，并在每次请求前检查限额。',
        },
        {
          type: 'list',
          items: [
            '**数据库中的模型目录。** `sync_models` 拉取 OpenRouter 目录（`GET /api/v1/models` + `/endpoints`），包含价格、p50 TTFT 延迟、吞吐量和参数规模。',
            '**用量配置。** 稳定的 slug（`chat`、`translation`）→ 有序模型链、`max_tokens`、`temperature`、限额和预算。',
            '**请求前检查限额。** 每日/每月请求次数和美元预算在发起 HTTP 调用前校验。超限会抛异常，而不是静默换模型。',
            '**流式输出（SSE）。** `stream()` / `astream()` 按块返回响应；管理后台一个复选框即可开启。',
            '**每次调用都记日志。** 每次尝试写入数据库、JSONL 文件或 ClickHouse（可插拔后端）— 并带上发起用户的用户名。',
            '**安全的密钥。** 管理后台的 API 密钥加密存储（Fernet，由 `SECRET_KEY` 派生），且只写不读：保存后只能替换或清除。',
            '**紧急开关与并发。** `enabled` 复选框可立即停止全部调用，`max_parallel_requests` 限制每个进程的并发 HTTP 请求。',
          ],
        },
        { type: 'h3', text: '功能' },
        {
          type: 'table',
          head: ['功能', '状态'],
          rows: [
            ['同步与异步客户端', '`OpenRouterClient`、`AsyncOpenRouterClient`'],
            ['单行门面函数', '`chat()`、`achat()`、`stream()`、`astream()`'],
            ['模型回退链', '在 402 / 429 / 5xx 时按配置顺序切换'],
            ['传输错误重试', '可配置的 `max_retries`'],
            ['流式输出（SSE）', '`stream()` / `astream()` / `chat(stream=True)`，默认关闭'],
            ['日志后端', '数据库（默认）、滚动 JSONL 文件、ClickHouse'],
            ['并发上限', '`max_parallel_requests`，默认 10'],
            ['管理后台本地化', '内置数十种语言的翻译目录'],
            ['类型提示', '包内附带 `py.typed`'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: '兼容性',
          text: 'Python 3.11–3.13，Django 4.2、5.0、5.1、5.2 和 6.0。依赖：`django>=4.2`、`httpx>=0.27`、`cryptography>=42`。',
        },
      ],
    },
    {
      id: 'quickstart',
      group: '入门',
      title: '快速开始',
      lead: '从安装到第一次模型回复 — 四个步骤。',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: '安装包',
              text: '一条 PyPI 命令：`pip install django-openrouter`。',
            },
            {
              title: '接入应用和中间件',
              text: '把 `django_openrouter` 加入 `INSTALLED_APPS`，把 `django_openrouter.middleware.CurrentUserMiddleware` 加入 `MIDDLEWARE`，然后运行 `python manage.py migrate`。',
            },
            {
              title: '在管理后台配置',
              text: '打开 **OpenRouter → OpenRouter settings**：粘贴 API 密钥（会被加密），或留空并在环境变量中设置 `OPENROUTER_API_KEY`。',
            },
            {
              title: '同步目录并创建配置',
              text: '运行 `python manage.py sync_models`，然后创建一个 slug 为 `chat` 的 **Usage profile**，按优先级添加模型，可选设为默认配置。',
            },
          ],
        },
        { type: 'h3', text: '1. 安装' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. 接入与迁移' },
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
          text: '`CurrentUserMiddleware` 必须放在 `AuthenticationMiddleware` **之后**，并把调用用户的用户名写入请求日志。没有它，每一行都会标记为 `anonymous`。',
        },
        { type: 'h3', text: '3. 在 Django 管理后台配置' },
        {
          type: 'list',
          ordered: true,
          items: [
            '打开 **OpenRouter → OpenRouter settings**。粘贴 API 密钥 — 它会被加密且不会再次显示 — 或留空并在环境变量中设置 `OPENROUTER_API_KEY`。',
            '运行 `python manage.py sync_models` 拉取模型目录（`GET /api/v1/models`）。',
            '创建 **Usage profile**（slug 为 `translation`、`chat` 等），按优先级添加一个或多个模型（第一个先尝试），并设置限额和预算。',
            '若希望调用 `chat(messages=...)` 时不传名称，把该配置设为 **default profile**。',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: '截图',
          text: '管理后台四个分区 — 设置、目录、配置和日志 — 都在「管理后台」一节配有截图。',
        },
        { type: 'h3', text: '4. 第一次调用' },
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
          title: '不把密钥存进数据库也能检查',
          text: '目录可以用一次性密钥同步：`python manage.py sync_models --api-key sk-or-...` — 不会写入数据库。',
        },
      ],
    },
    {
      id: 'configuration',
      group: '指南',
      title: '配置',
      lead: 'API 密钥解析顺序、settings.OPENROUTER 字典，以及运行时配置缓存的工作方式。',
      blocks: [
        { type: 'h3', text: 'API 密钥从哪里来' },
        {
          type: 'p',
          text: '如果管理后台的密钥字段为空，库会按以下顺序查找密钥：',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY`（顶层设置）',
            '`OPENROUTER_API_KEY` 环境变量',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: '保存在管理后台的密钥始终优先于以上三项。它加密存储（Fernet，由 `SECRET_KEY` 派生），保存后不可读。',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['键', '默认值', '说明'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', '运行时配置在 Django 缓存中保留的秒数'],
            ['`CACHE_ALIAS`', '`"default"`', '缓存别名（`django.core.cache`）'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', '管理后台跳过重新同步模型目录的秒数'],
            ['`API_KEY`', '未设置', '管理后台字段为空时的回退密钥'],
            ['`HTTP_REFERER`', '未设置', '`HTTP-Referer` 头（OpenRouter 中的应用归属）'],
            ['`X_TITLE`', '未设置', '`X-Title` 头'],
            ['`LOG_BACKENDS`', '仅数据库', '请求日志写入位置 — 见「日志后端」一节'],
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
          text: '自带的 `LocMemCache` 就够用。Redis 或 Memcached 是可选的 — 把 `CACHE_ALIAS` 指向即可。',
        },
        {
          type: 'callout',
          kind: 'info',
          title: '设置在管理后台，不在 settings.py',
          text: '超时、重试次数、紧急开关、流式输出（`streaming_enabled`）和并行请求上限（`max_parallel_requests`）都在管理后台的 **OpenRouter settings** — 带截图的细节见「管理后台」一节。',
        },
        { type: 'h3', text: '缓存如何工作' },
        {
          type: 'p',
          text: '客户端不直接读数据库，而是读取缓存的 `RuntimeConfig` 快照：设置、启用的配置及其回退模型。所有应用模型上的 `post_save` / `post_delete` 信号会立即失效缓存 — 管理后台的修改无需重启即可生效，`CACHE_TIMEOUT` 只是安全网。',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache 与多进程',
          text: '使用 `LocMemCache` 时每个进程各自一份缓存：失效只发生在你于管理后台保存的那个进程。多进程部署请通过 `CACHE_ALIAS` 使用 Redis/Memcached。',
        },
      ],
    },
    {
      id: 'usage',
      group: '指南',
      title: '用法',
      lead: 'chat() / achat() / stream() / astream() 门面、客户端类、单次调用覆盖，以及结果结构。',
      blocks: [
        { type: 'h3', text: 'chat() 门面' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # profile slug; None → default profile
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: '同步客户端' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: '异步调用' },
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
          text: '异步客户端镜像同步客户端：ORM 操作走 `sync_to_async`，HTTP 走 `httpx.AsyncClient`。',
        },
        { type: 'h3', text: '流式输出（SSE）' },
        {
          type: 'p',
          text: '流式输出默认关闭。在 **OpenRouter settings** 中启用 **Streaming enabled**，然后 `stream()` 和 `astream()` 以 `ChatChunk` 块交付响应：',
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
          text: '`chat(..., stream=True)` 使用相同的 SSE 传输并返回完整的 `ChatResult`。若设置中已启用流式输出，普通 `chat()` 也会走 SSE；`stream=False` 强制普通 JSON 响应。在流式关闭时调用会在任何 HTTP 请求之前抛出 `ConfigurationError`。',
        },
        {
          type: 'table',
          head: ['ChatChunk 字段', '类型', '说明'],
          rows: [
            ['`delta`', '`str`', '当前块的文本'],
            ['`content`', '`str`', '到目前为止累积的文本'],
            ['`model_used`', '`str`', '正在生成回答的模型'],
            ['`done`', '`bool`', '最后一块为 `True`'],
            ['`result`', '`ChatResult | None`', '最后一块上的完整结果'],
            ['`raw`', '`dict`', '原始 SSE 事件'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: '回退与流式输出',
          text: '回退到下一个模型只可能发生在发出第一块之前。如果某个模型开始流式输出后中途失败，错误会抛给调用方：部分答案已经发给客户端。',
        },
        { type: 'h3', text: '单次调用覆盖' },
        {
          type: 'p',
          text: '任意 `**overrides` 会转发进请求体。`max_tokens` 和 `temperature` 覆盖配置中的值，而 `model` 会临时把指定模型放到链的最前面：',
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
        { type: 'h3', text: '并发' },
        {
          type: 'p',
          text: '设置中的 **Max parallel requests** 字段（默认 `10`，`0` = 不限制）限制当前进程向 OpenRouter 发出的并发 HTTP 请求数 — 同时适用于 `chat()` 和 `stream()`，同步与异步。',
        },
        { type: 'h3', text: '结果：ChatResult' },
        {
          type: 'table',
          head: ['字段', '类型', '说明'],
          rows: [
            ['`content`', '`str`', '响应文本（多部分内容的文本段已拼接）'],
            ['`prompt_tokens`', '`int`', '来自 `usage` 的 prompt token 数'],
            ['`completion_tokens`', '`int`', '来自 `usage` 的 completion token 数'],
            ['`cost_usd`', '`Decimal`', '费用：来自目录价格，否则来自 API 的 `usage.cost`'],
            ['`catalog_cost_usd`', '`Decimal | None`', '目录费用 — 用于与账单对账'],
            ['`model_used`', '`str`', '实际作答的模型'],
            ['`latency_ms`', '`int`', '成功尝试的延迟'],
            ['`raw`', '`dict`', 'OpenRouter 的原始 JSON 响应'],
          ],
        },
      ],
    },
    {
      id: 'models',
      group: '指南',
      title: '模型目录',
      lead: 'sync_models 如何填充目录，以及 OpenRouterModel 存储哪些字段。',
      blocks: [
        { type: 'h3', text: 'sync_models 命令' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # one-off key, never stored` },
        {
          type: 'p',
          text: '该命令 upsert 目录（`GET /api/v1/models`），并用 `/endpoints` 指标丰富它 — p50 延迟和吞吐量。它从不删除任何东西：从 OpenRouter 消失的模型会设为 `is_active=False`。引用该模型的配置不会损坏 — 调用会开始以 `ModelDisabled` 失败，直到你切换配置。',
        },
        { type: 'h3', text: '模型字段' },
        {
          type: 'table',
          head: ['字段', '说明'],
          rows: [
            ['`model_id`', 'OpenRouter 标识符，例如 `anthropic/claude-3.5-sonnet`'],
            ['`name`', '人类可读名称'],
            ['`context_length`', '上下文长度（token）'],
            ['`pricing`', '每 token 价格 JSON：`prompt`、`completion`，可选 `request`/`image`'],
            ['`prompt_price` / `completion_price`', '十进制每 token 价格 — 用于管理后台排序和筛选'],
            ['`latency_ms`', '最佳端点的 p50 TTFT，毫秒'],
            ['`throughput`', '最佳端点的 p50 吞吐量，token/s'],
            ['`parameter_count`', '近似参数量（70B → 70000000000），用于排序'],
            ['`parameter_label`', '带单位的显示规模：`70B`、`340M`、`8x7B`'],
            ['`supported_parameters`', '支持的参数列表'],
            ['`modality`', '模态，例如 `text->text`'],
            ['`is_active`', '模型能否在配置中选用'],
            ['`last_synced_at`', '同步上次看到该模型的时间'],
            ['`is_free`（属性）', '若 `prompt`/`completion`/`request` 价格均为零则为 `True`'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: '仅免费模型',
          text: '配置标志 `only_free_models` 只允许目录中价格为零的模型 — 适合开发环境和演示。它对主模型和每一个回退模型都生效。',
        },
      ],
    },
    {
      id: 'limits',
      group: '指南',
      title: '限额、预算与回退',
      lead: '请求前检查什么、OpenRouter 出错时会发生什么，以及何时启用回退。',
      blocks: [
        { type: 'h3', text: '配置限额' },
        {
          type: 'p',
          text: '花费按当前日历日和月（活动 `TIME_ZONE`）从 `RequestLog` 汇总。空（`null`）限额字段表示「不限制」。',
        },
        {
          type: 'table',
          head: ['配置字段', '限制内容', '异常'],
          rows: [
            ['`max_requests_per_day`', '每日请求数', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', '每月请求数', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', '每日 `cost_usd` 合计', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', '每月 `cost_usd` 合计', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: '检查在事务中运行：配置行用 `select_for_update` 锁定，聚合在该锁下计算 — 并发请求无法抢跑越过限额。',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: '限额需要 DatabaseBackend',
          text: '聚合来自 `RequestLog` 表，因此 `DatabaseBackend` 必须保留在 `LOG_BACKENDS` 中（这是默认值）。若移除它，`check_limits()` 看不到花费，限额就会失效。',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: '没有静默绕过',
          text: '用尽限额或预算会在 HTTP 调用前抛出异常（`BudgetExceeded` / `RateLimitExceeded`）。库**不会**换到另一个模型把请求硬塞过去。',
        },
        { type: 'h3', text: '回退链' },
        {
          type: 'p',
          text: '只有当 OpenRouter 自身返回 `402`、`429` 或 `5xx` 时才会启用回退模型。顺序由管理后台的 `order` 字段决定；链中的重复项会被去掉。被配置规则禁止的模型（未启用，或在 `only_free_models` 下非免费）会被跳过。',
        },
        {
          type: 'list',
          items: [
            '**传输错误和 5xx** — 在同一模型上最多重试 `max_retries` 次，然后回退。',
            '**402 / 429** — 立即切到链中的下一个模型。',
            '**其他 4xx**（例如 400）— 立即抛出，不回退：该请求很可能对所有模型都无效。',
            '**每次尝试** — 包括失败的 — 都会写入日志。',
          ],
        },
        { type: 'h3', text: '全局紧急开关' },
        {
          type: 'p',
          text: '**OpenRouter settings** 中的 `enabled` 复选框会立即停止一切：任何 `chat()` 调用在检查限额之前就会抛出 `OpenRouterDisabled`。适合事故处理和计划维护。',
        },
      ],
    },
    {
      id: 'logging',
      group: '指南',
      title: '日志后端',
      lead: '每次 HTTP 调用都会写入 OPENROUTER["LOG_BACKENDS"] 中列出的全部后端：项目数据库、JSONL 文件、ClickHouse — 或你自己的类。',
      blocks: [
        {
          type: 'p',
          text: '列表中的每一项要么是类的点分路径（默认设置），要么是带 `BACKEND` 键和参数的字典。若未设置 `LOG_BACKENDS`，日志只写入项目数据库（`RequestLog`）。',
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
        { type: 'h3', text: 'DatabaseBackend（默认）' },
        {
          type: 'p',
          text: '向 `RequestLog` 模型写入行。每日/每月限额和预算从此表聚合 — 如果使用限额，请保持此后端启用：没有它，`check_limits()` 看不到花费。',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: '按大小滚动的 JSON Lines 文件（`RotatingFileHandler`）：一行 = 一个 JSON 对象，字段为 `created_at`、`profile`、`model`、`status_code`、`error_message`、`prompt_tokens`、`completion_tokens`、`cost_usd`、`latency_ms`、`username`。',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: '通过 ClickHouse HTTP 接口插入 `FORMAT JSONEachRow`。无需额外依赖 — 使用同一个 `httpx`。数据库和表名按标识符校验以防止注入。可以这样建表：',
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
          title: '尽力而为',
          text: '每个已配置后端都会收到每条记录，后端失败（磁盘满、ClickHouse 不可达）永远不会中断 `chat()` — 错误会记到 `django_openrouter` 日志器。',
        },
        { type: 'h3', text: '谁发起了请求' },
        {
          type: 'p',
          text: '每条记录都带有发起调用的 Django 用户的用户名。它由 `django_openrouter.middleware.CurrentUserMiddleware` 提供（在 `AuthenticationMiddleware` 之后）。没有用户或在 HTTP 请求之外的调用记为 `anonymous`。在 Celery 和管理命令中请手动设置名称：',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: '自定义后端' },
        {
          type: 'p',
          text: '继承 `django_openrouter.log_backends.LogBackend`，实现 `write()`（以及可选的 `awrite()`），并把类的点分路径加入 `LOG_BACKENDS`。',
        },
      ],
    },
    {
      id: 'admin',
      group: '指南',
      title: '管理后台',
      lead: '全部运行时策略集中在 Django 管理后台的四个分区：设置、模型目录、用量配置和请求日志。',
      blocks: [
        {
          type: 'table',
          head: ['分区', '作用'],
          rows: [
            ['**OpenRouter settings**', '紧急开关、加密 API 密钥、流式输出、超时'],
            ['**OpenRouter models**', '来自 OpenRouter 的目录：价格、延迟、吞吐量'],
            ['**Usage profiles**', '模型链、限额、预算、花费统计'],
            ['**Request logs**', '每次调用的 token、费用和延迟（只读）'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: '单例：列表页会重定向到唯一一行，且无法删除。所有全局集成设置都集中在这里：',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — 全局紧急开关。关闭 → 每次 `chat()` / `stream()` 抛出 `OpenRouterDisabled`。',
            '**API key** — 只写，用由 `SECRET_KEY` 派生的 Fernet 加密。空字段保留当前密钥；新值替换它；**Clear stored API key** 复选框从数据库清除密钥 — 随后使用 `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]`。',
            '**Base URL** — OpenRouter API 根地址（`https://openrouter.ai/api/v1`）。',
            '**Default profile** — 调用 `chat(messages=...)` 且不传名称时使用的配置。',
            '**Request timeout** / **Max retries** — HTTP 超时，以及在切到链中下一个模型之前对传输/5xx 错误的重试次数。',
            '**Streaming enabled** — 允许通过 `stream()` / `astream()` 和 `chat(stream=True)` 使用 SSE。默认关闭。',
            '**Max parallel requests** — 本进程并发 HTTP 调用上限（`0` = 不限制）。',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django 管理后台 — OpenRouter settings：启用、密钥状态、base url、默认配置、超时、重试、流式输出、并发上限',
          caption: 'OpenRouter settings：紧急开关、只写 API 密钥、默认配置、超时、流式输出和并发上限。',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: '来自 `GET /api/v1/models` 的目录，加上 `/endpoints` 指标（延迟和吞吐量）。行不能手工添加或删除，模型卡片只读。',
        },
        {
          type: 'list',
          items: [
            '**列：** 名称、`latency_ms`（p50 TTFT）、吞吐量（token/s）、每 100 万 token 的 prompt/completion 价格、参数规模（`70B` / `8x7B`）、`is_active`。点击排序，空值始终排在最后。',
            '**筛选：** 启用状态、模态、价格（免费 / < $1 / $1–10 / ≥ $10 每 100 万）、速度（< 400 ms / 400–1200 / ≥ 1200）。',
            '**Sync catalog with OpenRouter**（操作）— upsert 目录；消失的模型设为 `is_active=False`。',
            '**Assign to usage profile…**（操作）— 把选中的模型追加到配置链末尾；重复、未启用和非免费模型（在 `only_free_models` 下）会跳过并给出报告。',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: '首次打开时列表会从 API 刷新，随后 10 分钟内从数据库提供（`CATALOG_CACHE_TIMEOUT`）。控制台同样的同步：`python manage.py sync_models`。',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django 管理后台 — OpenRouter 模型目录：名称、延迟、吞吐量、每 100 万价格、参数规模、启用状态；右侧为筛选器',
          caption: '模型目录：按价格/延迟排序，按价格和速度筛选，同步以及分配到配置的操作。',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: '配置就是代码传入的 slug（`chat`、`translation` 等）加上有序模型列表：第一个先尝试，其余在 `402` / `429` / `5xx` 时回退。限额用尽会抛异常，而不是静默换模型。',
        },
        {
          type: 'list',
          items: [
            '**配置列表：** 名称、主模型、启用状态、仅免费、每日请求/预算限额，以及来自日志的聚合 — 请求数、平均和总延迟、平均和总费用（每页一次 GROUP BY）。',
            '**表单：** `max_tokens`、`temperature`（0–2）、每日/每月请求和美元限额（空 = 不限制）、**only free models**、**is active**。',
            '**Models (priority order) 内联：** 目录自动完成 — 标签中显示价格和延迟，并应用与目录相同的价格/速度筛选。保存时重排顺序，链中的第一个模型同步到 `model` 字段。',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django 管理后台 — 用量配置列表，含请求、延迟和费用聚合',
          caption: '用量配置：模型链、限额和花费聚合就在列表中。',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: '只读日志。每次 HTTP 尝试（包括回退和错误）在启用 `DatabaseBackend`（默认）时成为一行。每日和每月限额从此表聚合。',
        },
        {
          type: 'list',
          items: [
            '**列：** 时间、用户名、配置、模型、HTTP 状态、prompt/completion token、费用、延迟。',
            '**表上方汇总：** 当前筛选下的请求数和美元合计。筛选：配置、状态、日期；按错误文本和用户名搜索。',
            '**Username** 由 `CurrentUserMiddleware` 提供；没有它时行标记为 `anonymous`。在 Celery 和管理命令中 — `bound_username("worker")`（见「日志后端」）。',
            '**权限：** 单独的 `view_usage_logs` 权限可以让支持人员查看花费，而无需访问设置。',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django 管理后台 — 请求日志：时间、用户名、配置、模型、状态、token、费用、延迟；顶部为汇总',
          caption: '请求日志：每次尝试含 token、费用和延迟，表上方有筛选汇总。',
        },
        { type: 'h3', text: 'API 密钥保护' },
        {
          type: 'list',
          items: [
            '**加密。** `api_key` 字段是 `EncryptedTextField`：Fernet，密钥由 `SECRET_KEY` 派生。',
            '**只写。** 保存后无法查看该值 — 只能替换或清除。',
            '**不入库的替代方案。** 密钥可以只放在环境变量（`OPENROUTER_API_KEY`）中，管理后台字段留空。',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: '轮换 SECRET_KEY',
          text: 'Fernet 密钥由 `SECRET_KEY` 派生。更改 `SECRET_KEY` 会使数据库中存储的 API 密钥无法读取 — 必须重新输入。',
        },
        { type: 'h3', text: '校验' },
        {
          type: 'list',
          items: [
            '`temperature` — 仅在 0…2 范围内。',
            '主模型和回退模型必须处于启用状态。',
            '开启 `only_free_models` 时，配置中的所有模型必须免费。',
            '回退链中的 `(profile, model)` 对唯一。',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: '参考',
      title: 'API 参考',
      lead: '从 django_openrouter 公开导入：门面、客户端、结果和异常。',
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
          text: '`profile_name=None` 使用设置中的默认配置。不传 `messages` 调用是 `TypeError`。若配置未找到或未启用 — `ConfigurationError`。',
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
        { type: 'h3', text: '异常' },
        {
          type: 'table',
          head: ['异常', '何时'],
          rows: [
            ['`OpenRouterError`', '库中所有异常的基类'],
            ['`ConfigurationError`', '没有密钥、配置或默认配置；流式输出已关闭'],
            ['`OpenRouterDisabled`', '紧急开关：设置中 `enabled=False`'],
            ['`ModelDisabled`', '配置/模型未启用或违反 `only_free_models`'],
            ['`RateLimitExceeded`', '每日/每月请求限额已用尽'],
            ['`BudgetExceeded`', '每日/每月预算已用尽'],
            ['`OpenRouterAPIError`', '重试和回退后的 API 错误；带有 `status_code`'],
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
          text: '在 `transaction.atomic()` 内外都可以安全调用 — 包装会自动创建。锁加在配置行上，而不是日志上，因此增长的 `RequestLog` 表不会把锁放大。',
        },
      ],
    },
    {
      id: 'faq',
      group: '参考',
      title: '常见问题',
      lead: '常见问题和陷阱。',
      blocks: [
        { type: 'h3', text: '管理后台的修改没有生效' },
        {
          type: 'p',
          text: '很可能你在用 `LocMemCache` 跑多个进程：缓存失效只发生在你点击「Save」的那个进程。改用 Redis/Memcached，并在 `OPENROUTER["CACHE_ALIAS"]` 中设置别名。',
        },
        { type: 'h3', text: '“No usage profile specified and default_profile is not set”' },
        {
          type: 'p',
          text: '你调用了 `chat()` 却没有传配置名称，也没有设置默认配置。要么把 slug 作为第一个参数传入，要么在 **OpenRouter settings** 中选择 **default profile**。',
        },
        { type: 'h3', text: '“Usage profile X is not found or inactive”' },
        {
          type: 'p',
          text: '没有该 slug 的配置，或其 `is_active` 复选框已关闭。只有启用的配置会进入运行时配置。',
        },
        { type: 'h3', text: '支持流式输出吗？' },
        {
          type: 'p',
          text: '支持。在 **OpenRouter settings** 中启用 **Streaming enabled**，并使用 `stream()` / `astream()` 或 `chat(stream=True)`。启用流式后，普通 `chat()` 也会走 SSE；`stream=False` 强制 JSON 响应。',
        },
        { type: 'h3', text: '限额没有触发' },
        {
          type: 'p',
          text: '检查 `django_openrouter.log_backends.DatabaseBackend` 是否在 `OPENROUTER["LOG_BACKENDS"]` 中（默认就在）：限额和预算从 `RequestLog` 表聚合，没有此后端时检查看不到花费。',
        },
        { type: 'h3', text: '如何让管理后台显示我的语言？' },
        {
          type: 'p',
          text: '所有管理后台标签都包在 `gettext_lazy` 中，包内附带数十种语言的翻译目录（`locale/<django_locale>/LC_MESSAGES/django.po`）。由宿主项目决定启用哪些语言：配置 `LANGUAGE_CODE` / `LANGUAGES` 并接入 `LocaleMiddleware`。编辑 `.po` 后编译目录 — `python manage.py compilemessages -l zh_Hans`。注意：包中的英语是 `en_GB` / `en-gb`；没有基础的 `en` 目录。',
        },
        { type: 'h3', text: '如何手动统计花费？' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: '可以不用管理后台吗？' },
        {
          type: 'p',
          text: '不行 — 这正是本库的意义：策略（模型、限额、预算）存放在数据库中，由运维人员管理。不过密钥可以只放在环境变量中。',
        },
      ],
    },
  ],
}
