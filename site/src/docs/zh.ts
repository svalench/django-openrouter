import type { DocsContent } from './types'

export const zh: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: '面向 Django 的 OpenRouter — 通过管理后台管理模型、用量配置、预算和请求日志',
    version: '0.7.0',
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
          text: '`CurrentUserMiddleware` 必须放在 `AuthenticationMiddleware` **之后**，并把调用用户的用户名写入请求日志。没有它，每一行都会标记为 `anonymous`。 对于 `StreamingHttpResponse`，在输出响应体期间用户名仍保持绑定，因此流式视图中的 `stream()` 会记录到正确的用户。',
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
            ["`OTEL`", "`false`", "开启 span。即使安装了 opentelemetry-api 也默认关闭"],
            ["`OTEL_CAPTURE_CONTENT`", "`false`", "把脱敏后的提示和回复写到 span"],
            ["`OTEL_CONTENT_REDACTOR`", "未设置", "点分路径 fn(text, *, kind) -> str"],
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
          text: '`chat(..., stream=True)` 使用相同的 SSE 传输并返回完整的 `ChatResult`。普通 `chat()` 即使启用了流式输出也始终使用普通 JSON 响应。流式输出关闭时调用会在任何 HTTP 请求前抛出 `ConfigurationError`。',
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
      id: 'pydantic-ai',
      group: '指南',
      title: 'Pydantic AI',
      lead: '可选适配器：Pydantic AI 代理通过使用配置档调用 OpenRouter。模型链、预算、速率限制、总开关和请求日志仍留在 django-openrouter。',
      blocks: [
        {
          type: 'p',
          text: '安装可选依赖：`pip install "django-openrouter[pydantic-ai]"`（Pydantic AI 2.64+）。导入 `django_openrouter` 不会导入 Pydantic AI。类是 `django_openrouter.integrations.pydantic_ai.OpenRouterProfileModel`。没有该 extra 时，这个导入会抛出 `ImportError` 并给出安装命令。',
        },
        {
          type: 'p',
          text: '这是 Pydantic AI 的 `Model`，不是 `Provider`。Provider 只会交出 HTTP 客户端，Pydantic AI 会自己调用 OpenRouter，从而绕过配置档模型链、预算预留、速率限制、总开关、请求日志和 `bound_username`。`OpenRouterProfileModel` 组装 chat completions 请求并调用 `AsyncOpenRouterClient`。`Agent.run` 和 `Agent.run_sync` 都走这些异步方法。',
        },
        { type: 'h3', text: '代理' },
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
          text: '`profile` 是使用配置档的 slug。`None` 使用默认聊天配置档。Pydantic AI 的能力配置传给 `model_profile=`，因为这里的 `profile` 是 Django 的 slug。代理的模型 id 仍是 `openrouter:<slug>`。`result.response.model_name` 是回退后实际作答的目录 id。`result.usage` 含 token 数和美元 `cost`（有 API 的 `usage.cost` 时用它，否则用目录估算）。',
        },
        {
          type: 'p',
          text: '代理的 `temperature` 和 `max_tokens` 受配置档上限约束。更低的 temperature 会保留。未传的值沿用配置档默认值。`thinking` 会作为 OpenRouter 的 `reasoning` 送出（`False` 变成 `{"enabled": false}`，`"high"` 变成 `{"enabled": true, "effort": "high"}`）。`timeout` 是这一次调用的空闲 `request_timeout`。输入图片（`ImageUrl`、图片 `BinaryContent`）成为 `image_url` 片段。模型返回的图片仍在 `ChatResult.images`，不会转成 Pydantic AI 的图片片段。',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: '流式',
          text: '`agent.run_stream` 和 `run_stream_sync` 需要在 OpenRouter 设置里打开 Streaming。文本增量随 SSE 到达。Reasoning 和 tool calls 从最后一个分片补上。',
        },
        {
          type: 'p',
          text: '`BudgetExceeded` 和 `RateLimitExceeded` 会抛给调用方。它们在 HTTP 之前发生，不会悄悄换到另一个模型。HTTP 回退只发生在配置档的模型链内（`402`、`408`、`429`、`5xx`）。',
        },
        {
          type: 'p',
          text: '`Agent.run(conversation_id=...)` 在没有 `bound_session()` 时写入请求日志的 `session_id`，并放进 chat 请求体。块里的 session 和 metadata 优先，同样会转发到请求。适配器不传 `trace_id`。当前的 OpenTelemetry span（Django、Celery 或 `Agent(instrument=True)`）成为日志里的 `trace_id`。未开追踪时，每次模型调用有自己的 id，该调用的重试和回退共用它。',
        },
        { type: 'h3', text: 'Django 视图' },
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
        { type: 'h3', text: 'Celery 任务' },
        {
          type: 'p',
          text: '请求之外用 `bound_username` 绑定日志里的用户名。HTTP 里 `CurrentUserMiddleware` 已经这样做。',
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
      group: '指南',
      title: '语音转文字',
      lead: 'transcribe() / atranscribe() 把浏览器或服务器上的音频发到 OpenRouter POST /api/v1/audio/transcriptions。配置档、预算和请求日志与聊天是同一套机制。',
      blocks: [
        {
          type: 'p',
          text: '转写模型不在默认的聊天目录里。`sync_models` 还会请求 `GET /api/v1/models?output_modalities=transcription`，并以 modality `audio->transcription` 和 `output_modalities: ["transcription"]` 保存。聊天同步除此之外不变：从两份目录里都消失的模型会被停用，只做转写的模型不会仅仅因为不在聊天列表里就被停用。',
        },
        { type: 'h3', text: '配置转写配置档' },
        {
          type: 'p',
          text: '在**使用配置档**里把 **Kind** 设为 **Transcription**，只选择转写模型（自动完成会按类型字段过滤），并按需设置语言、上传大小和时长上限。如果希望 `transcribe()` 不传 slug 也能工作，在 **OpenRouter settings** 里把该配置档选为 **Default transcription profile**。API 密钥、base URL 和总开关仍在同一行设置上。没有单独的 STT 单例：预算和日志本来就在配置档上，应用可以把听写和会议转写分开。',
        },
        {
          type: 'table',
          head: ['配置档字段', '作用'],
          rows: [
            ['`kind`', '`chat`（默认）或 `transcription`'],
            ['`language`', 'ISO-639-1 提示（`en`、`ru`）。留空表示自动检测。聊天时忽略'],
            ['`max_audio_bytes`', '上传上限。留空为 25 MiB'],
            ['`max_audio_seconds`', '按时长计价的模型预留的最坏秒数（Whisper 的 context length 为 0，`prompt` 价格按秒计）'],
            ['`max_requests_*` / `budget_usd_*`', '与聊天相同的按日、按月限额。预留会按 `usage.cost` 结算'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: '按时长计费的预算需要 max_audio_seconds',
          text: '带美元预算的转写配置档如果使用按时长计价的模型，在设置 `max_audio_seconds` 之前会抛出 `ConfigurationError`。按 token 计价的 STT 模型（context length 不为 0）会预留 `context_length ×` 最高的单 token 价格，思路与聊天相同。',
        },
        { type: 'h3', text: '调用 transcribe()' },
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
            profile="dictation",  # 或 None → 默认转写配置档
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
          text: '本库不依赖 ffmpeg。请发送 OpenRouter 接受的容器：webm、ogg、mp3、wav、m4a、flac 或 aac。浏览器 `MediaRecorder` 的 blob（`audio/webm;codecs=opus`）即可。若要先转码，把 `OPENROUTER["AUDIO_PREPARE"]` 设为 dotted path。该可调用对象接收 `(data, *, filename, content_type)`，必须返回 `(bytes, filename, content_type)`。',
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
          text: '`atranscribe()` 以及 `OpenRouterClient.transcribe` / `AsyncOpenRouterClient.transcribe` 是同一次调用。`model=` 只能重排该配置档里已有的模型。`prompt=` 会放进 JSON 正文；OpenRouter 目前会忽略 multipart API 顶层的 prompt，因此把它当作可选提示，而不是保证生效的词表偏向。`TranscriptionResult` 包含 `text`、token 计数、`duration_seconds`、`cost_usd`、`catalog_cost_usd`、`model_used`、`latency_ms` 和 `raw`。',
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
          text: '该命令会 upsert 聊天目录（`GET /api/v1/models`）和转写目录（`GET /api/v1/models?output_modalities=transcription`），再用 `/endpoints` 指标丰富两者 — p50 延迟和吞吐量。它从不删除任何东西：从两份列表中都消失的模型会设为 `is_active=False`。引用该模型的配置不会损坏 — 调用会开始以 `ModelDisabled` 失败，直到你切换配置。',
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
            ['`modality`', '模态，例如 `text->text` 或 `audio->transcription`'],
            ['`output_modalities`', '目录中的列表，例如 `["text"]` 或 `["transcription"]`'],
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
          text: '每次 HTTP 尝试前，事务会锁定配置行并预留一次请求和最坏情况费用：完整上下文窗口 × 最高的按 token 价格（`prompt`、`completion`、`input_cache_read`、`input_cache_write`、`internal_reasoning`），再加上 `request` / `web_search` 以及 `image` × `image_url` 部分的数量。成功的调用按实际 usage 结算预留；失败、中断或取消的调用（`499`）在核对账单前保留预留。设置预算的模型需要有效价格、context length 和文本输出（`text+image->text` 也可以）；`audio` 等其他非零价格会被拒绝。因 HTTP 错误失败的重试不计入请求限额。',
        },
        {
          type: 'p',
          text: '被终止的 worker 遗留的预留通过 cron 释放（状态 `499`，费用 `0`）；没有 `usage` 的响应的预留会保留：',
        },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py release_stale_reservations --minutes 60 [--dry-run]` },
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
            '**429 / 408** — 在同一模型上重试（遵循 `Retry-After`），然后切到链中的下一个模型。',
            '**402**（账户余额用尽）— 只继续尝试链中剩余的免费模型。',
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
          text: '按大小滚动的 JSON Lines 文件（`RotatingFileHandler`）：一行 = 一个 JSON 对象，字段为 `created_at`、`profile`、`model`、`status_code`、`error_message`、`prompt_tokens`、`completion_tokens`、`cost_usd`、`latency_ms`、`username`、`trace_id`、`session_id`、`metadata`。',
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
      id: 'tracing',
      group: "指南",
      title: "追踪与日志分组",
      lead: "可选的 OpenTelemetry span，以及每条请求日志上的 trace_id、session_id 和 metadata。",
      blocks: [
        {
          type: "p",
          text: "pip install django-openrouter[otel] 只安装 opentelemetry-api。SDK 和导出器由宿主项目选择。未安装时不会 import。在 OPENROUTER['OTEL'] 为 true 之前不会创建 span。",
        },
        {
          type: "h3",
          text: "Spans",
        },
        {
          type: "p",
          text: "chat、stream、transcribe、generate_image 及其异步版本各有一个父 span。generate_image 不会再套一层 chat span。每次 HTTP 尝试（含重试和 fallback）是子 span。流式调用记录首 token 时间，并保持父 span 直到生成器结束。BudgetExceeded、RateLimitExceeded、超时和被中断的流（499）记为错误。",
        },
        {
          type: "h3",
          text: "trace_id / session_id",
        },
        {
          type: "p",
          text: "RequestLog 增加可空且有索引的 trace_id、session_id，以及可空 JSON metadata。同一次调用的重试共享 trace_id：有 span 时用 OpenTelemetry 的 trace id，否则生成一个。chat 的 session_id 和 metadata 仍会发给 OpenRouter。trace= 只作为 span 属性。转写会保存这些字段，但不会放进音频 JSON。管理后台可按 session_id 和 trace_id 过滤和搜索，并链接到同一会话或同一 trace 的全部调用。metadata 只读。",
        },
        {
          type: "code",
          lang: "python",
          title: "bound_session",
          code: "from django_openrouter import chat\nfrom django_openrouter.current_user import bound_session\n\nwith bound_session(\"ticket-42\", metadata={\"feature\": \"support\"}):\n    chat(\"chat\", messages=[{\"role\": \"user\", \"content\": \"Hi\"}])\n\nchat(\n    \"chat\",\n    messages=[{\"role\": \"user\", \"content\": \"Hi\"}],\n    session_id=\"other\",\n    metadata={\"feature\": \"billing\"},\n    trace={\"feature.flag\": \"beta\"},\n)",
        },
        {
          type: "p",
          text: '调用参数只在这一次覆盖 `bound_session`。调用里的 `metadata` 键会替换块里的同名键。只有 `OTEL_CAPTURE_CONTENT` 为 true 时，提示和回复正文才会写到 span。',
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
      group: '指南',
      title: '管理后台',
      lead: '全部运行时策略集中在 Django 管理后台：设置、模型目录、用量配置、请求日志和用量仪表盘。',
      blocks: [
        {
          type: 'table',
          head: ['分区', '作用'],
          rows: [
            ['**OpenRouter settings**', '紧急开关、加密 API 密钥、流式输出、超时'],
            ['**OpenRouter models**', '来自 OpenRouter 的目录：价格、延迟、吞吐量'],
            ['**Usage profiles**', '模型链、限额、预算、花费统计'],
            ['**Request logs**', '每次调用的 token、费用和延迟（只读）'],
            ['**Usage dashboard**', '花费、错误率、延迟和 token，并对照配置的预算'],
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
        { type: 'h3', text: '用量仪表盘' },
        {
          type: 'p',
          text: '拥有 `view_usage_logs` 的员工（以及超级用户）可以从 OpenRouter 索引或日志摘要打开 **Usage dashboard**。该视图挂在 `RequestLogAdmin.get_urls` 上，并用 `admin_view` 包装，因此注册了 `RequestLog` 的自定义 `AdminSite` 会提供同一页面。默认管理站点的路径是 `/admin/django_openrouter/requestlog/dashboard/`。',
        },
        {
          type: 'list',
          items: [
            '**窗口。** 按天查看时按小时分桶（最多 7 天）。按月查看时按天分桶（最多 366 天）。可按配置和模型过滤。',
            '**图表。** 随包提供的 Chart.js（MIT，无构建、无 CDN、无内联脚本）。数据通过 `json_script` 传入：费用、请求数、错误率、平均/p95 延迟和 token，可按总体、配置和模型查看。同一序列颜色固定，并跟随管理后台的浅色和深色主题。指标卡与等长的上一时段对比。200–299 以外都算错误，包括 402、429、499、5xx 和状态 0。',
            '**预算。** 用当前日历日和月对照请求上限与美元上限，并显示已用百分比。p95 在 Python 中按窗口内最多 20,000 条最新记录计算。',
          ],
        },
        {
          type: 'image',
          src: 'admin-dashboard.png',
          alt: 'Django 管理后台用量仪表盘：筛选、费用、请求数、错误率、延迟、token 和配置预算',
          caption: '用量仪表盘：所选日期或月份的花费、错误和延迟，以及每个配置的预算。',
        },
        {
          type: 'image',
          src: 'admin-dashboard-dark.png',
          alt: 'Django 管理后台用量仪表盘（深色主题）：筛选、费用、请求数、错误率、延迟、token 和配置预算',
          caption: '深色主题：同一组图表跟随 Django 管理后台的主题开关。',
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
            ['`UnsupportedAudioFormat`', '转写音频不是 webm/ogg/mp3/wav/m4a/flac/aac'],
            ['`AudioTooLarge`', '转写音频超过配置档上限（默认 25 MiB）'],
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
          text: '支持。在 **OpenRouter settings** 中启用 **Streaming enabled**，并使用 `stream()` / `astream()` 或 `chat(stream=True)`。不带 `stream=True` 的普通 `chat()` 始终返回普通 JSON 响应。',
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
