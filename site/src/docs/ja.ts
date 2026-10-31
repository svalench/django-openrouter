import type { DocsContent } from './types'

export const ja: DocsContent = {
  meta: {
    name: 'django-openrouter',
    tagline: 'OpenRouter for Django — モデル・プロファイル・予算・ログを管理画面から運用',
    version: '0.7.0',
    github: 'https://github.com/svalench/django-openrouter',
    pypi: 'https://pypi.org/project/django-openrouter/',
  },
  nav: {
    searchPlaceholder: 'ドキュメントを検索…',
    searchEmpty: '見つかりませんでした。別のキーワードをお試しください。',
    onThisPage: 'このページの内容',
    copied: 'コピーしました',
    copy: 'コピー',
    editGithub: 'GitHub',
    prev: '前へ',
    next: '次へ',
    heroBadge: 'MIT · Python ≥ 3.11 · Django ≥ 4.2',
    heroCta: '3分ではじめる',
    heroGithub: 'リポジトリ',
    builtWith: 'ドキュメント：',
    license: 'MIT ライセンス',
  },
  ui: {
    theme: 'テーマを切り替え',
    language: '言語',
    openMenu: 'メニューを開く',
    closeMenu: 'メニューを閉じる',
  },
  sections: [
    {
      id: 'intro',
      group: 'はじめに',
      title: 'イントロダクション',
      lead: 'OpenRouter を管理対象リソースに変える再利用可能な Django アプリ。モデル・利用プロファイル・予算・リクエストログはデータベースに保存され、管理画面から設定できます。再デプロイは不要です。',
      blocks: [
        {
          type: 'p',
          text: '翻訳・チャット・要約などのプロダクトコードは、`settings.py` にハードコードされたキーやモデル ID ではなく、このライブラリ経由で OpenRouter と通信します。運用者はアクティブなモデルの選択、日次・月次の上限設定、利用額の確認を管理画面で行えます。',
        },
        { type: 'h3', text: 'なぜ settings.py ではダメなのか' },
        {
          type: 'p',
          text: 'settings に `OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"` と書くやり方では、モデル変更・予算調整・緊急停止のたびにデプロイが必要になります。`django-openrouter` はこのランタイムポリシーをデータベースに保存し、キャッシュし、リクエストのたびに上限をチェックします。',
        },
        {
          type: 'list',
          items: [
            '**モデルカタログを DB に。** `sync_models` が OpenRouter のカタログ（`GET /api/v1/models` + `/endpoints`）を価格・レイテンシ（p50 TTFT）・スループット・重みサイズとともに取り込みます。',
            '**利用プロファイル。** 安定した slug（`chat`、`translation`）→ 順序付きモデルチェーン、`max_tokens`、`temperature`、上限、予算。',
            '**リクエスト前の上限チェック。** 日次・月次のリクエスト上限と USD 予算を HTTP 呼び出しの前に検査。超過は例外であり、サイレントなフォールバックではありません。',
            '**ストリーミング（SSE）。** `stream()` / `astream()` がレスポンスをチャンクで返します。設定のチェックボックス 1 つで有効化。',
            '**すべての呼び出しを記録。** 各試行は DB・JSONL ファイル・ClickHouse（プラガブルなバックエンド）へ、呼び出したユーザーの username とともに書き込まれます。',
            '**安全なキー管理。** 管理画面の API キーは暗号化（Fernet、`SECRET_KEY` から導出）かつ write-only。保存後は置き換えか消去のみ可能です。',
            '**キルスイッチと並列性。** `enabled` チェックボックスですべての呼び出しを即時停止。`max_parallel_requests` でプロセスあたりの同時 HTTP リクエスト数を制限。',
          ],
        },
        { type: 'h3', text: '機能一覧' },
        {
          type: 'table',
          head: ['機能', '状態'],
          rows: [
            ['同期・非同期クライアント', '`OpenRouterClient`、`AsyncOpenRouterClient`'],
            ['ワンライナーファサード', '`chat()`、`achat()`、`stream()`、`astream()`'],
            ['モデルのフォールバックチェーン', '402 / 429 / 5xx 時に設定順で'],
            ['トランスポートエラーのリトライ', '`max_retries` で設定可能'],
            ['ストリーミング（SSE）', '`stream()` / `astream()` / `chat(stream=True)`。デフォルトはオフ'],
            ['ログバックエンド', 'DB（デフォルト）、ローテーション付き JSONL ファイル、ClickHouse'],
            ['並列数の上限', '`max_parallel_requests`、デフォルト 10'],
            ['管理画面の多言語対応', '数十ロケールの翻訳カタログを同梱'],
            ['型ヒント', 'パッケージに `py.typed` を同梱'],
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          title: '互換性',
          text: 'Python 3.11–3.13、Django 4.2 / 5.0 / 5.1 / 5.2 / 6.0。依存関係：`django>=4.2`、`httpx>=0.27`、`cryptography>=42`。',
        },
      ],
    },
    {
      id: 'quickstart',
      group: 'はじめに',
      title: 'クイックスタート',
      lead: 'インストールから最初のモデル応答まで、4 ステップ。',
      blocks: [
        {
          type: 'steps',
          items: [
            {
              title: 'パッケージをインストール',
              text: 'PyPI から 1 コマンド：`pip install django-openrouter`。',
            },
            {
              title: 'アプリとミドルウェアを接続',
              text: '`INSTALLED_APPS` に `django_openrouter`、`MIDDLEWARE` に `django_openrouter.middleware.CurrentUserMiddleware` を追加し、`python manage.py migrate` を実行。',
            },
            {
              title: '管理画面で設定',
              text: '**OpenRouter → OpenRouter settings** を開き、API キーを貼り付け（暗号化されます）るか、空欄のまま環境変数 `OPENROUTER_API_KEY` を設定します。',
            },
            {
              title: 'カタログ同期とプロファイル作成',
              text: '`python manage.py sync_models` を実行し、slug `chat` の **Usage profile** を作成。モデルを優先順に追加し、必要ならデフォルトプロファイルに設定します。',
            },
          ],
        },
        { type: 'h3', text: '1. インストール' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `pip install django-openrouter` },
        { type: 'h3', text: '2. 接続とマイグレーション' },
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
          text: '`CurrentUserMiddleware` は `AuthenticationMiddleware` の**後**に置き、呼び出したユーザーの username をリクエストログに記録します。これがないと、すべての行が `anonymous` になります。 `StreamingHttpResponse` ではボディ送信中も username が保持されるため、ストリーミングビュー内の `stream()` も正しいユーザーで記録されます。',
        },
        { type: 'h3', text: '3. Django admin での設定' },
        {
          type: 'list',
          ordered: true,
          items: [
            '**OpenRouter → OpenRouter settings** を開く。API キーを貼り付ける（暗号化され、以後表示されません）か、空欄のまま環境変数 `OPENROUTER_API_KEY` を設定。',
            '`python manage.py sync_models` を実行してモデルカタログ（`GET /api/v1/models`）を取り込む。',
            '**Usage profile** を作成（slug は `translation`、`chat` など）し、モデルを優先順（先頭から試行）に 1 つ以上追加。上限と予算も設定。',
            '名前なしで `chat(messages=...)` を呼びたい場合は、そのプロファイルを **default profile** に設定。',
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: 'スクリーンショット',
          text: '管理画面の 4 セクション（設定・カタログ・プロファイル・ログ）は、スクリーンショット付きで「管理画面」セクションにまとめています。',
        },
        { type: 'h3', text: '4. 最初の呼び出し' },
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
          title: 'キーを保存せずに確認',
          text: '使い捨てキーでカタログを同期できます：`python manage.py sync_models --api-key sk-or-...` — データベースには保存されません。',
        },
      ],
    },
    {
      id: 'configuration',
      group: 'ガイド',
      title: '設定',
      lead: 'API キーの解決順序、settings.OPENROUTER 辞書、ランタイム設定キャッシュの仕組み。',
      blocks: [
        { type: 'h3', text: 'API キーの出どころ' },
        {
          type: 'p',
          text: '管理画面のキー欄が空の場合、ライブラリは次の順序でキーを探します：',
        },
        {
          type: 'list',
          ordered: true,
          items: [
            '`settings.OPENROUTER["API_KEY"]`',
            '`settings.OPENROUTER_API_KEY`（トップレベル設定）',
            '環境変数 `OPENROUTER_API_KEY`',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: '管理画面に保存されたキーは、上記 3 つすべてより常に優先されます。暗号化（Fernet、`SECRET_KEY` から導出）されて保存され、保存後は読み取れません。',
        },
        { type: 'h3', text: 'settings.OPENROUTER' },
        {
          type: 'table',
          head: ['キー', 'デフォルト', '説明'],
          rows: [
            ['`CACHE_TIMEOUT`', '`60`', 'ランタイム設定を Django キャッシュに保持する秒数'],
            ['`CACHE_ALIAS`', '`"default"`', 'キャッシュエイリアス（`django.core.cache`）'],
            ['`CATALOG_CACHE_TIMEOUT`', '`600`', '管理画面がモデルカタログの再同期をスキップする秒数'],
            ['`API_KEY`', '未設定', '管理画面の欄が空の場合のフォールバックキー'],
            ['`HTTP_REFERER`', '未設定', '`HTTP-Referer` ヘッダー（OpenRouter でのアプリ帰属）'],
            ['`X_TITLE`', '未設定', '`X-Title` ヘッダー'],
            ['`LOG_BACKENDS`', 'DB のみ', 'リクエストログの書き込み先 — 「ログバックエンド」セクション参照'],
            ["`OTEL`", "`false`", "スパン。opentelemetry-api があっても既定ではオフ"],
            ["`OTEL_CAPTURE_CONTENT`", "`false`", "マスクしたプロンプトと応答をスパンに書く"],
            ["`OTEL_CONTENT_REDACTOR`", "未設定", "ドットパス fn(text, *, kind) -> str"],
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
          text: '標準の `LocMemCache` で十分です。Redis や Memcached は任意 — `CACHE_ALIAS` を向けるだけです。',
        },
        {
          type: 'callout',
          kind: 'info',
          title: '設定は settings.py ではなく管理画面に',
          text: 'タイムアウト、リトライ回数、キルスイッチ、ストリーミング（`streaming_enabled`）、並列リクエスト上限（`max_parallel_requests`）は管理画面の **OpenRouter settings** にあります。スクリーンショット付きの詳細は「管理画面」セクションへ。',
        },
        { type: 'h3', text: 'キャッシュの仕組み' },
        {
          type: 'p',
          text: 'クライアントは DB を直接読まず、キャッシュされた `RuntimeConfig` スナップショット（設定・アクティブなプロファイル・フォールバックモデル）を読みます。アプリ内全モデルの `post_save` / `post_delete` シグナルがキャッシュを即時無効化するため、管理画面の変更は再起動なしで反映され、`CACHE_TIMEOUT` は保険にすぎません。',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'LocMemCache とマルチプロセス',
          text: '`LocMemCache` ではプロセスごとにキャッシュのコピーを持つため、無効化は管理画面で保存したプロセス内でしか起きません。マルチプロセス環境では `CACHE_ALIAS` で Redis/Memcached を使ってください。',
        },
      ],
    },
    {
      id: 'usage',
      group: 'ガイド',
      title: '使い方',
      lead: 'chat() / achat() / stream() / astream() ファサード、クライアントクラス、呼び出しごとのオーバーライド、結果の構造。',
      blocks: [
        { type: 'h3', text: 'chat() ファサード' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import chat

result = chat(
    "translation",  # プロファイルの slug。None → デフォルトプロファイル
    messages=[{"role": "user", "content": "Translate to French: hello"}],
)`,
        },
        { type: 'h3', text: '同期クライアント' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import OpenRouterClient

client = OpenRouterClient("chat")
result = client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        { type: 'h3', text: '非同期呼び出し' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import achat, AsyncOpenRouterClient

result = await achat("chat", messages=[{"role": "user", "content": "Hello"}])

# クラス経由でも
client = AsyncOpenRouterClient("chat")
result = await client.chat(messages=[{"role": "user", "content": "Hello"}])`,
        },
        {
          type: 'p',
          text: '非同期クライアントは同期版と同じインターフェースです。ORM 操作は `sync_to_async` 経由、HTTP は `httpx.AsyncClient` 経由で行われます。',
        },
        { type: 'h3', text: 'ストリーミング（SSE）' },
        {
          type: 'p',
          text: 'ストリーミングはデフォルトでオフです。**OpenRouter settings** の **Streaming enabled** を有効にすると、`stream()` と `astream()` がレスポンスを `ChatChunk` のチャンクで返します：',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter import stream, astream

for chunk in stream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)

# 最終チャンク: done=True、chunk.result に完全な ChatResult

async for chunk in astream("chat", messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta, end="", flush=True)`,
        },
        {
          type: 'p',
          text: '`chat(..., stream=True)` は同じ SSE トランスポートを使い、完全な `ChatResult` を返します。通常の `chat()` はストリーミングが有効でも常に通常の JSON レスポンスを使います。ストリーミング無効時の呼び出しは、HTTP リクエスト前に `ConfigurationError` を送出します。',
        },
        {
          type: 'table',
          head: ['ChatChunk のフィールド', '型', '説明'],
          rows: [
            ['`delta`', '`str`', '現在のチャンクのテキスト'],
            ['`content`', '`str`', 'ここまでに蓄積されたテキスト'],
            ['`model_used`', '`str`', '応答を生成しているモデル'],
            ['`done`', '`bool`', '最終チャンクで `True`'],
            ['`result`', '`ChatResult | None`', '最終チャンクの完全な結果'],
            ['`raw`', '`dict`', '生の SSE イベント'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'フォールバックとストリーミング',
          text: '次のモデルへのフォールバックが可能なのは、最初のチャンクが送出される前だけです。モデルがストリーミングを開始した後に途中で失敗した場合、エラーは呼び出し元に投げられます。応答の一部はすでにクライアントへ送られているためです。',
        },
        { type: 'h3', text: '呼び出しごとのオーバーライド' },
        {
          type: 'p',
          text: '任意の `**overrides` はリクエストボディにそのまま渡されます。`max_tokens` と `temperature` はプロファイルの値を上書きし、`model` は指定モデルを一時的にチェーンの先頭に置きます：',
        },
        {
          type: 'code',
          lang: 'python',
          code: `result = chat(
    "chat",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.2,
    max_tokens=512,
    model="openai/gpt-4o-mini",        # カタログに存在する必要あり
    response_format={"type": "json_object"},  # OpenRouter の任意パラメータ
)`,
        },
        { type: 'h3', text: '並列性' },
        {
          type: 'p',
          text: '設定の **Max parallel requests** フィールド（デフォルト `10`、`0` = 無制限）は、現在のプロセス内での OpenRouter への同時 HTTP リクエスト数を制限します。`chat()` と `stream()` の両方、同期・非同期の両方に適用されます。',
        },
        { type: 'h3', text: '結果：ChatResult' },
        {
          type: 'table',
          head: ['フィールド', '型', '説明'],
          rows: [
            ['`content`', '`str`', '応答テキスト（マルチパートの場合は text 部分を連結）'],
            ['`prompt_tokens`', '`int`', '`usage` のプロンプトトークン数'],
            ['`completion_tokens`', '`int`', '`usage` の応答トークン数'],
            ['`cost_usd`', '`Decimal`', 'コスト：カタログ価格から、なければ API の `usage.cost`'],
            ['`catalog_cost_usd`', '`Decimal | None`', 'カタログ基準のコスト — 請求との照合用'],
            ['`model_used`', '`str`', '実際に応答したモデル'],
            ['`latency_ms`', '`int`', '成功した試行のレイテンシ'],
            ['`raw`', '`dict`', 'OpenRouter の生 JSON レスポンス'],
          ],
        },
      ],
    },
    {
      id: 'pydantic-ai',
      group: 'ガイド',
      title: 'Pydantic AI',
      lead: '任意のアダプタです。Pydantic AI のエージェントは利用プロファイル経由で OpenRouter を呼びます。モデル列、予算、レート制限、キルスイッチ、リクエストログは django-openrouter 側に残ります。',
      blocks: [
        {
          type: 'p',
          text: '追加依存を入れます: `pip install "django-openrouter[pydantic-ai]"`（Pydantic AI 2.64+）。`django_openrouter` の import は Pydantic AI を読み込みません。クラスは `django_openrouter.integrations.pydantic_ai.OpenRouterProfileModel` です。extra が無いとその import は `ImportError` になり、インストールコマンドを示します。',
        },
        {
          type: 'p',
          text: 'これは Pydantic AI の `Model` であり、`Provider` ではありません。Provider は HTTP クライアントを渡すだけで、Pydantic AI 自身が OpenRouter を呼び、プロファイルの列、予算の予約、レート制限、キルスイッチ、ログ、`bound_username` を通りません。`OpenRouterProfileModel` は chat completions のペイロードを組み立て、`AsyncOpenRouterClient` を呼びます。`Agent.run` と `Agent.run_sync` はどちらもその async メソッドを使います。',
        },
        { type: 'h3', text: 'エージェント' },
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
          text: '`profile` は利用プロファイルのスラッグです。`None` は既定のチャットプロファイルです。Pydantic AI の能力は `model_profile=` に渡します。ここでの `profile` は Django のスラッグだからです。エージェントのモデル id は `openrouter:<slug>` のままです。`result.response.model_name` はフォールバック後に実際に答えたカタログ id です。`result.usage` にはトークン数と USD の `cost` が入ります（API の `usage.cost` があればそれ、なければカタログ見積もり）。',
        },
        {
          type: 'p',
          text: 'エージェントの `temperature` と `max_tokens` はプロファイルが上限です。より低い temperature はそのまま残ります。省略した値はプロファイルの既定です。`thinking` は OpenRouter の `reasoning` として送られます（`False` は `{"enabled": false}`、`"high"` は `{"enabled": true, "effort": "high"}`）。`timeout` はその呼び出しのアイドル `request_timeout` です。入力画像（`ImageUrl`、画像の `BinaryContent`）は `image_url` パートになります。モデルが返した画像は `ChatResult.images` に残り、Pydantic AI の画像パートには変換しません。',
        },
        {
          type: 'callout',
          kind: 'warning',
          title: 'ストリーミング',
          text: '`agent.run_stream` と `run_stream_sync` には OpenRouter 設定で Streaming を有効にする必要があります。テキストの差分は SSE に合わせて届きます。Reasoning と tool calls は最終チャンクから付きます。',
        },
        {
          type: 'p',
          text: '`BudgetExceeded` と `RateLimitExceeded` は呼び出し元まで届きます。HTTP の前に発生し、別モデルへ黙って移りません。HTTP のフォールバックはプロファイルの列の中だけです（`402`、`408`、`429`、`5xx`）。',
        },
        {
          type: 'p',
          text: '`Agent.run(conversation_id=...)` は、`bound_session()` が無いときリクエストログの `session_id` になり、chat の本文にも送られます。ブロック側の session と metadata が優先され、同じくリクエストに載ります。アダプタは `trace_id` を渡しません。有効な OpenTelemetry スパン（Django、Celery、`Agent(instrument=True)`）がログの `trace_id` になります。トレースがオフなら、モデル呼び出しごとに id が付き、その呼び出しのリトライとフォールバックで共有されます。',
        },
        { type: 'h3', text: 'Django ビュー' },
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
        { type: 'h3', text: 'Celery タスク' },
        {
          type: 'p',
          text: 'リクエストの外では `bound_username` がログのユーザー名を縛ります。HTTP では `CurrentUserMiddleware` がすでにそれをします。',
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
      group: 'ガイド',
      title: '音声文字起こし',
      lead: 'transcribe() / atranscribe() はブラウザまたはサーバーの音声を OpenRouter POST /api/v1/audio/transcriptions に送ります。プロファイル、予算、リクエストログはチャットと同じ仕組みです。',
      blocks: [
        {
          type: 'p',
          text: '文字起こしモデルは通常のチャット用カタログに含まれません。`sync_models` は `GET /api/v1/models?output_modalities=transcription` も取得し、modality `audio->transcription` と `output_modalities: ["transcription"]` で保存します。チャットの同期はそれ以外変わりません。両方のカタログから消えたモデルは無効化され、文字起こし専用モデルはチャット一覧に無いという理由だけでは無効化されません。',
        },
        { type: 'h3', text: '文字起こしプロファイルを設定する' },
        {
          type: 'p',
          text: '**利用プロファイル**で **Kind** を **Transcription** にし、文字起こしモデルだけを選びます（オートコンプリートは種別フィールドで絞り込みます）。必要なら言語、アップロードサイズ、長さの上限も設定します。スラッグなしで `transcribe()` を動かすなら、**OpenRouter settings** でそのプロファイルを **Default transcription profile** にします。API キー、base URL、キルスイッチは同じ設定行のままです。STT 専用のシングルトンはありません。予算とログはすでにプロファイルにあり、アプリ側でディクテーションと会議の文字起こしを分けられます。',
        },
        {
          type: 'table',
          head: ['プロファイルのフィールド', '役割'],
          rows: [
            ['`kind`', '`chat`（既定）または `transcription`'],
            ['`language`', 'ISO-639-1 のヒント（`en`、`ru`）。空なら自動検出。チャットでは無視'],
            ['`max_audio_bytes`', 'アップロード上限。空なら 25 MiB'],
            ['`max_audio_seconds`', '秒課金モデル向けに予約する最悪ケースの秒数（Whisper は context length が 0 で、`prompt` の価格は秒あたり）'],
            ['`max_requests_*` / `budget_usd_*`', 'チャットと同じ日次・月次の上限。予約は `usage.cost` に照合される'],
          ],
        },
        {
          type: 'callout',
          kind: 'warning',
          title: '秒課金の予算には max_audio_seconds が必要',
          text: 'USD 予算のある文字起こしプロファイルで秒課金モデルを使うと、`max_audio_seconds` を設定するまで `ConfigurationError` になります。トークン課金の STT モデル（context length が 0 でないもの）は、チャットと同じ考え方で `context_length ×` 最も高いトークン単価を予約します。',
        },
        { type: 'h3', text: 'transcribe() を呼ぶ' },
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
            profile="dictation",  # または None → 既定の文字起こしプロファイル
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
          text: 'ライブラリは ffmpeg に依存しません。OpenRouter が受け付けるコンテナを送ってください。webm、ogg、mp3、wav、m4a、flac、aac です。ブラウザの `MediaRecorder` blob（`audio/webm;codecs=opus`）で問題ありません。先に変換するなら `OPENROUTER["AUDIO_PREPARE"]` に dotted path を指定します。呼び出し可能オブジェクトは `(data, *, filename, content_type)` を受け取り、`(bytes, filename, content_type)` を返します。',
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
          text: '`atranscribe()` と `OpenRouterClient.transcribe` / `AsyncOpenRouterClient.transcribe` は同じ呼び出しです。`model=` で並べ替えられるのは、そのプロファイルに既にあるモデルだけです。`prompt=` は JSON ボディに載ります。OpenRouter は現在、multipart API のトップレベル prompt を無視するため、語彙を必ず偏らせるものではなく任意のヒント文として扱ってください。`TranscriptionResult` には `text`、トークン数、`duration_seconds`、`cost_usd`、`catalog_cost_usd`、`model_used`、`latency_ms`、`raw` が入ります。',
        },
      ],
    },
    {
      id: 'models',
      group: 'ガイド',
      title: 'モデルカタログ',
      lead: 'sync_models がカタログをどう埋めるか、OpenRouterModel が何を保持するか。',
      blocks: [
        { type: 'h3', text: 'sync_models コマンド' },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py sync_models
python manage.py sync_models --api-key sk-or-...  # 使い捨てキー。保存されません` },
        {
          type: 'p',
          text: 'このコマンドはチャット用カタログ（`GET /api/v1/models`）と文字起こし用カタログ（`GET /api/v1/models?output_modalities=transcription`）を upsert し、両方を `/endpoints` のメトリクス（p50 レイテンシとスループット）で補強します。削除は一切行いません。両方の一覧から消えたモデルには `is_active=False` が付きます。そのモデルを参照するプロファイルは壊れません — プロファイルを切り替えるまで、呼び出しが `ModelDisabled` で失敗するだけです。',
        },
        { type: 'h3', text: 'モデルのフィールド' },
        {
          type: 'table',
          head: ['フィールド', '説明'],
          rows: [
            ['`model_id`', 'OpenRouter の識別子。例：`anthropic/claude-3.5-sonnet`'],
            ['`name`', '人間が読める名前'],
            ['`context_length`', 'コンテキストサイズ（トークン）'],
            ['`pricing`', 'トークン単価の JSON：`prompt`、`completion`、任意で `request`/`image`'],
            ['`prompt_price` / `completion_price`', 'トークン単価（10 進数）— 管理画面でのソート・フィルタ用'],
            ['`latency_ms`', '最良エンドポイントの p50 TTFT（ミリ秒）'],
            ['`throughput`', '最良エンドポイントの p50 スループット（トークン/秒）'],
            ['`parameter_count`', 'おおよその重み数（70B → 70000000000）。ソート用'],
            ['`parameter_label`', '単位付きの表示サイズ：`70B`、`340M`、`8x7B`'],
            ['`supported_parameters`', 'サポートされるパラメータの一覧'],
            ['`modality`', 'モダリティ。例：`text->text` または `audio->transcription`'],
            ['`output_modalities`', 'カタログのリスト。例：`["text"]` または `["transcription"]`'],
            ['`is_active`', 'プロファイルで選択可能か'],
            ['`last_synced_at`', '同期が最後にこのモデルを確認した日時'],
            ['`is_free`（property）', '`prompt`/`completion`/`request` の価格がすべてゼロなら `True`'],
          ],
        },
        {
          type: 'callout',
          kind: 'tip',
          title: '無料モデルのみ',
          text: 'プロファイルのフラグ `only_free_models` は、カタログで価格ゼロのモデルのみを許可します。dev 環境やデモに便利です。プライマリモデルとすべてのフォールバックの両方に適用されます。',
        },
      ],
    },
    {
      id: 'limits',
      group: 'ガイド',
      title: '上限・予算・フォールバック',
      lead: 'リクエスト前に何がチェックされるか、OpenRouter のエラー時に何が起きるか、フォールバックがいつ発動するか。',
      blocks: [
        { type: 'h3', text: 'プロファイルの上限' },
        {
          type: 'p',
          text: '消費量は `RequestLog` から、現在の暦日・暦月（アクティブな `TIME_ZONE`）で計算されます。上限フィールドが空（`null`）なら「無制限」です。',
        },
        {
          type: 'table',
          head: ['プロファイルのフィールド', '制限対象', '例外'],
          rows: [
            ['`max_requests_per_day`', '1 日のリクエスト数', '`RateLimitExceeded`'],
            ['`max_requests_per_month`', '1 か月のリクエスト数', '`RateLimitExceeded`'],
            ['`budget_usd_per_day`', '1 日の `cost_usd` 合計', '`BudgetExceeded`'],
            ['`budget_usd_per_month`', '1 か月の `cost_usd` 合計', '`BudgetExceeded`'],
          ],
        },
        {
          type: 'p',
          text: '各 HTTP 試行の前に、トランザクションがプロファイル行をロックし、1 リクエストと最悪ケースのコストを予約します。最悪ケースは、コンテキスト全体 × 最も高いトークン単価（`prompt`、`completion`、`input_cache_read`、`input_cache_write`、`internal_reasoning`）に、`request` / `web_search` と `image` × `image_url` パーツ数を加えたものです。成功した呼び出しは実際の usage で精算され、失敗・中断・キャンセルされた呼び出し（`499`）は課金確認まで予約を保持します。予算付きモデルには有効な価格、context length、テキスト出力（`text+image->text` も可）が必要で、`audio` など他の非ゼロ価格は拒否されます。HTTP エラーで失敗したリトライはリクエスト上限に数えられません。',
        },
        {
          type: 'p',
          text: '停止したワーカーが残した予約は cron で解放されます（ステータス `499`、コスト `0`）。`usage` なしのレスポンスの予約は残ります：',
        },
        { type: 'code', lang: 'bash', title: 'terminal', code: `python manage.py release_stale_reservations --minutes 60 [--dry-run]` },
        {
          type: 'callout',
          kind: 'warning',
          title: '上限には DatabaseBackend が必要',
          text: '集計は `RequestLog` テーブルから計算されるため、`DatabaseBackend` は `LOG_BACKENDS` に残す必要があります（デフォルトで有効）。外すと `check_limits()` が消費を認識できず、上限が機能しなくなります。',
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'サイレントな迂回はなし',
          text: '上限・予算の超過は HTTP 呼び出しの前に例外（`BudgetExceeded` / `RateLimitExceeded`）として発生します。ライブラリが別モデルへ切り替えてリクエストを「ねじ込む」ことは**ありません**。',
        },
        { type: 'h3', text: 'フォールバックチェーン' },
        {
          type: 'p',
          text: 'フォールバックモデルが使われるのは、OpenRouter 自体が `402`、`429`、`5xx` を返した場合のみです。順序は管理画面の `order` フィールドで設定し、チェーン内の重複は除外されます。プロファイルのルールで禁止されたモデル（非アクティブ、`only_free_models` での有料モデル）はスキップされます。',
        },
        {
          type: 'list',
          items: [
            '**トランスポートエラーと 5xx** — 同じモデルで `max_retries` 回までリトライし、その後フォールバック。',
            '**429 / 408** — 同じモデルでリトライ（`Retry-After` を尊重）し、その後チェーンの次のモデルへ。',
            '**402**（アカウントのクレジット切れ）— チェーン内の残りの無料モデルのみを試行。',
            '**その他の 4xx**（例：400）— フォールバックなしで即座に送出。リクエスト自体が全モデルで無効な可能性が高いため。',
            '**すべての試行** — 失敗も含め — がログに書き込まれます。',
          ],
        },
        { type: 'h3', text: 'グローバルキルスイッチ' },
        {
          type: 'p',
          text: '**OpenRouter settings** の `enabled` チェックボックスですべてが即時停止します。どの `chat()` 呼び出しも、上限チェックの前に `OpenRouterDisabled` を送出します。インシデントや計画停止に便利です。',
        },
      ],
    },
    {
      id: 'logging',
      group: 'ガイド',
      title: 'ログバックエンド',
      lead: 'すべての HTTP 呼び出しは OPENROUTER["LOG_BACKENDS"] に列挙された全バックエンド（プロジェクトの DB、JSONL ファイル、ClickHouse、または自作クラス）へ書き込まれます。',
      blocks: [
        {
          type: 'p',
          text: 'リストの各エントリは、クラスへの dotted path（デフォルト設定）か、`BACKEND` キーとパラメータを持つ辞書です。`LOG_BACKENDS` が未設定の場合、ログはプロジェクトのデータベース（`RequestLog`）にのみ書き込まれます。',
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
        { type: 'h3', text: 'DatabaseBackend（デフォルト）' },
        {
          type: 'p',
          text: '`RequestLog` モデルに行を書き込みます。日次・月次の上限と予算はこのテーブルから集計されます。上限を使うならこのバックエンドを有効のままにしてください。ないと `check_limits()` が消費を認識できません。',
        },
        { type: 'h3', text: 'FileBackend' },
        {
          type: 'p',
          text: 'サイズベースのローテーション付き（`RotatingFileHandler`）で JSON Lines をファイルへ出力。1 行 = 1 JSON オブジェクトで、フィールドは `created_at`、`profile`、`model`、`status_code`、`error_message`、`prompt_tokens`、`completion_tokens`、`cost_usd`、`latency_ms`、`username`、`trace_id`、`session_id`、`metadata` です。',
        },
        { type: 'h3', text: 'ClickHouseBackend' },
        {
          type: 'p',
          text: 'ClickHouse の HTTP インターフェース経由で `FORMAT JSONEachRow` を挿入します。追加の依存関係は不要 — 同じ `httpx` を使用。インジェクション防止のため、データベース名とテーブル名は識別子として検証されます。テーブルの作成：',
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
          title: 'ベストエフォート',
          text: '設定されたすべてのバックエンドがすべてのレコードを受け取り、バックエンドの障害（ディスク満杯、ClickHouse 到達不能など）が `chat()` を壊すことはありません。エラーは `django_openrouter` ロガーに記録されます。',
        },
        { type: 'h3', text: '誰がリクエストしたか' },
        {
          type: 'p',
          text: '各レコードには、呼び出しを行った Django ユーザーの username が入ります。これは `django_openrouter.middleware.CurrentUserMiddleware`（`AuthenticationMiddleware` の後）が供給します。ユーザーのいない呼び出しや HTTP リクエスト外の呼び出しは `anonymous` として記録されます。Celery や management コマンドでは手動で名前を設定します：',
        },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.current_user import bound_username

with bound_username("worker"):
    chat("chat", messages=[...])`,
        },
        { type: 'h3', text: 'カスタムバックエンド' },
        {
          type: 'p',
          text: '`django_openrouter.log_backends.LogBackend` を継承し、`write()`（任意で `awrite()`）を実装して、クラスの dotted path を `LOG_BACKENDS` に追加します。',
        },
      ],
    },
    {
      id: 'tracing',
      group: "ガイド",
      title: "トレースとログのグループ",
      lead: "任意の OpenTelemetry スパンと、各リクエストログの trace_id、session_id、metadata。",
      blocks: [
        {
          type: "p",
          text: "pip install django-openrouter[otel] は opentelemetry-api だけを入れます。SDK とエクスポーターはホスト側です。未インストールなら import しません。OPENROUTER['OTEL'] が true になるまでスパンはオフです。",
        },
        {
          type: "h3",
          text: "Spans",
        },
        {
          type: "p",
          text: "chat、stream、transcribe、generate_image と非同期版は親スパンを一つ開きます。generate_image はネストした chat スパンを足しません。リトライとフォールバックを含む各 HTTP 試行が子スパンです。ストリームは最初のトークンまでの時間を記録し、ジェネレータが終わるまで親を開いたままにします。BudgetExceeded、RateLimitExceeded、タイムアウト、中断したストリーム (499) はエラーです。",
        },
        {
          type: "h3",
          text: "trace_id / session_id",
        },
        {
          type: "p",
          text: "RequestLog に nullable でインデックス付きの trace_id と session_id、nullable の JSON metadata があります。一つの呼び出しのリトライは同じ trace_id を共有します。スパンがあるときは OpenTelemetry のトレース id、なければ生成した id です。chat の session_id と metadata はこれまで通り OpenRouter に送られます。trace= はローカルなスパン属性です。文字起こしはフィールドを保存し、音声 JSON には入れません。管理画面では session_id と trace_id で絞り込みと検索ができ、同じセッションまたはトレースの呼び出しへのリンクがあります。metadata は読み取り専用です。",
        },
        {
          type: "code",
          lang: "python",
          title: "bound_session",
          code: "from django_openrouter import chat\nfrom django_openrouter.current_user import bound_session\n\nwith bound_session(\"ticket-42\", metadata={\"feature\": \"support\"}):\n    chat(\"chat\", messages=[{\"role\": \"user\", \"content\": \"Hi\"}])\n\nchat(\n    \"chat\",\n    messages=[{\"role\": \"user\", \"content\": \"Hi\"}],\n    session_id=\"other\",\n    metadata={\"feature\": \"billing\"},\n    trace={\"feature.flag\": \"beta\"},\n)",
        },
        {
          type: "p",
          text: '呼び出し引数はその呼び出しだけ `bound_session` を上書きします。呼び出しの `metadata` のキーはブロックのキーを置き換えます。プロンプトと応答の本文は `OTEL_CAPTURE_CONTENT` が true のときだけスパンに載ります。',
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
      group: 'ガイド',
      title: '管理画面',
      lead: 'ランタイムポリシーは Django admin にあります：設定、モデルカタログ、利用プロファイル、リクエストログ、利用ダッシュボード。',
      blocks: [
        {
          type: 'table',
          head: ['セクション', '役割'],
          rows: [
            ['**OpenRouter settings**', 'キルスイッチ、暗号化 API キー、ストリーミング、タイムアウト'],
            ['**OpenRouter models**', 'OpenRouter のカタログ：価格・レイテンシ・スループット'],
            ['**Usage profiles**', 'モデルチェーン、上限、予算、消費統計'],
            ['**Request logs**', '各呼び出しのトークン・コスト・レイテンシ（読み取り専用）'],
            ['**Usage dashboard**', 'コスト、エラー率、レイテンシ、トークンをプロファイル予算と並べて表示'],
          ],
        },
        { type: 'h3', text: 'OpenRouter settings' },
        {
          type: 'p',
          text: 'シングルトン：一覧は唯一の行へリダイレクトされ、削除はできません。統合のグローバル設定がすべてここに集まっています：',
        },
        {
          type: 'list',
          items: [
            '**Enabled** — グローバルキルスイッチ。オフ → すべての `chat()` / `stream()` が `OpenRouterDisabled` を送出。',
            '**API key** — write-only。`SECRET_KEY` から導出された Fernet で暗号化。空欄は現在のキーを保持、新しい値は置き換え、**Clear stored API key** チェックボックスは DB からキーを消去 — その場合は `OPENROUTER_API_KEY` / `settings.OPENROUTER["API_KEY"]` が使われます。',
            '**Base URL** — OpenRouter API のルート（`https://openrouter.ai/api/v1`）。',
            '**Default profile** — 名前なしで `chat(messages=...)` が呼ばれたときに使われるプロファイル。',
            '**Request timeout** / **Max retries** — HTTP タイムアウトと、チェーンの次モデルへ移る前のトランスポート/5xx リトライ回数。',
            '**Streaming enabled** — `stream()` / `astream()` と `chat(stream=True)` による SSE を許可。デフォルトはオフ。',
            '**Max parallel requests** — このプロセス内の同時 HTTP 呼び出しの上限（`0` = 無制限）。',
          ],
        },
        {
          type: 'image',
          src: 'admin-settings.png',
          alt: 'Django admin — OpenRouter settings：enabled、キーの状態、base url、default profile、タイムアウト、リトライ、ストリーミング、並列上限',
          caption: 'OpenRouter settings：キルスイッチ、write-only の API キー、デフォルトプロファイル、タイムアウト、ストリーミング、並列上限。',
        },
        { type: 'h3', text: 'OpenRouter models' },
        {
          type: 'p',
          text: '`GET /api/v1/models` のカタログに `/endpoints` のメトリクス（レイテンシとスループット）を加えたもの。手動での行の追加・削除は不可、モデルの詳細画面は読み取り専用です。',
        },
        {
          type: 'list',
          items: [
            '**列：** 名前、`latency_ms`（p50 TTFT）、スループット（トークン/秒）、100 万トークンあたりの prompt/completion 価格、重みサイズ（`70B` / `8x7B`）、`is_active`。列クリックでソート — 空値は常に末尾。',
            '**フィルター：** アクティブ状態、モダリティ、価格（free / < $1 / $1–10 / ≥ $10 per 1M）、速度（< 400 ms / 400–1200 / ≥ 1200）。',
            '**Sync catalog with OpenRouter**（アクション）— カタログを upsert。消えたモデルには `is_active=False`。',
            '**Assign to usage profile…**（アクション）— 選択モデルをプロファイルのチェーン末尾に追加。重複・非アクティブ・`only_free_models` 下の有料モデルはレポート付きでスキップ。',
          ],
        },
        {
          type: 'callout',
          kind: 'info',
          text: '初回オープン時に一覧は API から更新され、その後 10 分間は DB から返されます（`CATALOG_CACHE_TIMEOUT`）。コンソールからの同等の同期：`python manage.py sync_models`。',
        },
        {
          type: 'image',
          src: 'admin-models.png',
          alt: 'Django admin — OpenRouter モデルカタログ：名前、レイテンシ、スループット、100 万トークン価格、重みサイズ、アクティブ状態。右側にフィルター',
          caption: 'モデルカタログ：価格/レイテンシでソート、価格・速度でフィルター、sync と assign to profile のアクション。',
        },
        { type: 'h3', text: 'Usage profiles' },
        {
          type: 'p',
          text: 'プロファイルとは、コードが渡す slug（`chat`、`translation` など）と順序付きモデルリストのこと。先頭が最初に試行され、残りは `402` / `429` / `5xx` でフォールバックします。上限超過は例外を投げ、サイレントにモデルを切り替えることはありません。',
        },
        {
          type: 'list',
          items: [
            '**プロファイル一覧：** 名前、プライマリモデル、アクティブ状態、only-free、日次リクエスト/予算上限、ログからの集計 — リクエスト数、平均/合計レイテンシ、平均/合計コスト（1 ページ 1 GROUP BY）。',
            '**フォーム：** `max_tokens`、`temperature`（0–2）、日次/月次のリクエスト・USD 上限（空 = 無制限）、**only free models**、**is active**。',
            '**インライン Models (priority order)：** カタログへのオートコンプリート — ラベルに価格とレイテンシが表示され、カタログと同じ価格/速度フィルターが効きます。保存時に順序は正規化され、チェーン先頭のモデルが `model` フィールドへ同期されます。',
          ],
        },
        {
          type: 'image',
          src: 'admin-profiles.png',
          alt: 'Django admin — 利用プロファイル一覧：リクエスト数・レイテンシ・コストの集計付き',
          caption: '利用プロファイル：モデルチェーン、上限、消費集計を一覧で直接確認。',
        },
        { type: 'h3', text: 'Request logs' },
        {
          type: 'p',
          text: '読み取り専用のログ。`DatabaseBackend` が有効な場合（デフォルト）、すべての HTTP 試行（フォールバックやエラーを含む）が 1 行になります。日次・月次の上限はこのテーブルから集計されます。',
        },
        {
          type: 'list',
          items: [
            '**列：** 時刻、username、プロファイル、モデル、HTTP ステータス、prompt/completion トークン、コスト、レイテンシ。',
            '**テーブル上部のサマリー：** 現在のフィルターでのリクエスト数と USD 合計。フィルター：プロファイル、ステータス、日付。エラーテキストと username で検索可能。',
            '**Username** は `CurrentUserMiddleware` が供給。ない場合は `anonymous`。Celery や management コマンドでは `bound_username("worker")`（「ログバックエンド」参照）。',
            '**権限：** 独立した `view_usage_logs` 権限により、設定へのアクセスを与えずにサポート担当へ消費情報へのアクセスを許可できます。',
          ],
        },
        {
          type: 'image',
          src: 'admin-logs.png',
          alt: 'Django admin — リクエストログ：時刻、username、プロファイル、モデル、ステータス、トークン、コスト、レイテンシ。上部にサマリー',
          caption: 'リクエストログ：すべての試行をトークン・コスト・レイテンシ付きで記録。フィルターのサマリーがテーブル上部に表示。',
        },
        { type: 'h3', text: '利用ダッシュボード' },
        {
          type: 'p',
          text: '`view_usage_logs` を持つスタッフ（とスーパーユーザー）は、OpenRouter のインデックスかログリサマリーから **Usage dashboard** を開きます。ビューは `RequestLogAdmin.get_urls` に登録され `admin_view` で包まれるため、`RequestLog` を登録した独自の `AdminSite` でも同じページになります。既定の admin のパスは `/admin/django_openrouter/requestlog/dashboard/` です。',
        },
        {
          type: 'list',
          items: [
            '**期間。** 日は時間バケット（最大 7 日）。月は日バケット（最大 366 日）。プロファイルとモデルで絞り込めます。',
            '**チャート。** 同梱の Chart.js（MIT、ビルドなし、CDN なし、インラインスクリプトなし）。データは `json_script` で渡します。コスト、件数、エラー率、平均/p95 レイテンシとトークンを、全体およびプロファイル別・モデル別に表示します。系列の色は固定で、管理画面のライト/ダークテーマに追従します。主要カードは同じ長さの直前期間と比較します。200–299 以外（402、429、499、5xx、ステータス 0 を含む）がエラーです。',
            '**予算。** カレンダー上の当日と当月を、リクエスト上限と USD 上限および使用率と並べます。p95 は直近最大 20,000 行から Python で計算します。',
          ],
        },
        {
          type: 'image',
          src: 'admin-dashboard.png',
          alt: 'Django admin の利用ダッシュボード：フィルタ、コスト、件数、エラー率、レイテンシ、トークン、プロファイル予算',
          caption: '利用ダッシュボード：選んだ日または月の支出・エラー・レイテンシと、プロファイルの予算。',
        },
        {
          type: 'image',
          src: 'admin-dashboard-dark.png',
          alt: 'Django admin の利用ダッシュボード（ダークテーマ）：フィルタ、コスト、件数、エラー率、レイテンシ、トークン、プロファイル予算',
          caption: 'ダークテーマ：同じグラフが Django admin のテーマ切り替えに従います。',
        },
        { type: 'h3', text: 'API キーの保護' },
        {
          type: 'list',
          items: [
            '**暗号化。** `api_key` フィールドは `EncryptedTextField`：Fernet、キーは `SECRET_KEY` から導出。',
            '**Write-only。** 保存後、値は閲覧不可 — 置き換えか消去のみ。',
            '**DB を使わない代替案。** キーを環境変数（`OPENROUTER_API_KEY`）だけに置き、管理画面の欄は空のままにできます。',
          ],
        },
        {
          type: 'callout',
          kind: 'danger',
          title: 'SECRET_KEY のローテーション',
          text: 'Fernet キーは `SECRET_KEY` から導出されます。`SECRET_KEY` を変更すると、DB に保存された API キーは読み取り不能になり、再入力が必要になります。',
        },
        { type: 'h3', text: 'バリデーション' },
        {
          type: 'list',
          items: [
            '`temperature` — 0…2 の範囲のみ。',
            'プライマリおよびフォールバックモデルはアクティブ必須。',
            '`only_free_models` では、プロファイルの全モデルが無料必須。',
            'フォールバックチェーン内の `(profile, model)` の組は一意。',
          ],
        },
      ],
    },
    {
      id: 'api',
      group: 'リファレンス',
      title: 'API リファレンス',
      lead: 'django_openrouter の公開インポート：ファサード、クライアント、結果、例外。',
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
          text: '`profile_name=None` は設定のデフォルトプロファイルを使います。`messages` なしの呼び出しは `TypeError`。プロファイルが見つからない・非アクティブの場合は `ConfigurationError`。',
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
    delta: str                      # 現在のチャンクのテキスト
    content: str                    # 蓄積された応答テキスト
    model_used: str = ""
    done: bool = False              # 最終チャンクで True
    result: ChatResult | None = None  # 最終チャンクの完全な結果
    raw: dict[str, Any] = field(default_factory=dict)`,
        },
        { type: 'h3', text: '例外' },
        {
          type: 'table',
          head: ['例外', '発生条件'],
          rows: [
            ['`OpenRouterError`', 'ライブラリの全例外の基底クラス'],
            ['`ConfigurationError`', 'キー・プロファイル・デフォルトプロファイルなし。ストリーミング無効'],
            ['`OpenRouterDisabled`', 'キルスイッチ：設定で `enabled=False`'],
            ['`ModelDisabled`', 'プロファイル/モデルが非アクティブ、または `only_free_models` 違反'],
            ['`RateLimitExceeded`', '日次/月次リクエスト上限の超過'],
            ['`BudgetExceeded`', '日次/月次予算の超過'],
            ['`OpenRouterAPIError`', 'リトライとフォールバック後の API エラー。`status_code` を保持'],
            ['`UnsupportedAudioFormat`', '文字起こし音声が webm/ogg/mp3/wav/m4a/flac/aac ではない'],
            ['`AudioTooLarge`', '文字起こし音声がプロファイルの上限を超えている（既定 25 MiB）'],
          ],
        },
        {
          type: 'code',
          lang: 'python',
          title: 'エラーハンドリング',
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
          code: `stats = profile.get_usage("day")    # または "month"
stats.request_count  # int
stats.total_cost     # Decimal
stats.since          # 期間の開始（datetime）`,
        },
        {
          type: 'p',
          text: '`transaction.atomic()` の内外どちらからでも安全に呼べます — ラッパーは自動作成されます。ロックはログではなくプロファイル行にかかるため、`RequestLog` テーブルの増大でロックが爆発することはありません。',
        },
      ],
    },
    {
      id: 'faq',
      group: 'リファレンス',
      title: 'FAQ',
      lead: 'よくある質問と落とし穴。',
      blocks: [
        { type: 'h3', text: '管理画面の変更が反映されない' },
        {
          type: 'p',
          text: 'おそらく複数プロセスで `LocMemCache` を使っています。キャッシュの無効化は「保存」を押したプロセス内でしか起きません。Redis/Memcached に切り替え、`OPENROUTER["CACHE_ALIAS"]` にエイリアスを設定してください。',
        },
        { type: 'h3', text: '「No usage profile specified and default_profile is not set」' },
        {
          type: 'p',
          text: 'プロファイル名なしで `chat()` を呼び、デフォルトプロファイルも未設定です。slug を第 1 引数に渡すか、**OpenRouter settings** で **default profile** を選んでください。',
        },
        { type: 'h3', text: '「Usage profile X is not found or inactive」' },
        {
          type: 'p',
          text: 'その slug のプロファイルが存在しないか、`is_active` チェックが外れています。ランタイム設定に入るのはアクティブなプロファイルだけです。',
        },
        { type: 'h3', text: 'ストリーミングはサポートされている？' },
        {
          type: 'p',
          text: 'はい。**OpenRouter settings** で **Streaming enabled** を有効にし、`stream()` / `astream()` または `chat(stream=True)` を使います。`stream=True` なしの通常の `chat()` は常に JSON レスポンスを返します。',
        },
        { type: 'h3', text: '上限が発動しない' },
        {
          type: 'p',
          text: '`django_openrouter.log_backends.DatabaseBackend` が `OPENROUTER["LOG_BACKENDS"]` に含まれているか確認してください（デフォルトでは含まれています）。上限と予算は `RequestLog` テーブルから集計されるため、このバックエンドがないと消費がチェックから見えません。',
        },
        { type: 'h3', text: '管理画面を自分の言語にするには？' },
        {
          type: 'p',
          text: '管理画面のすべてのラベルは `gettext_lazy` でラップされ、数十ロケールの翻訳カタログがパッケージに同梱されています（`locale/<Django ロケール>/LC_MESSAGES/django.po`）。有効な言語はホストプロジェクトが決めます：`LANGUAGE_CODE` / `LANGUAGES` を設定し、`LocaleMiddleware` を接続。`.po` 編集後はカタログをコンパイル — `python manage.py compilemessages -l ja`。注意：パッケージの英語は `en_GB` / `en-gb` で、基底の `en` カタログはありません。',
        },
        { type: 'h3', text: '消費額を手動で集計するには？' },
        {
          type: 'code',
          lang: 'python',
          code: `from django_openrouter.models import RequestLog

RequestLog.objects.filter(profile__name="chat").values_list(
    "cost_usd", "prompt_tokens", "completion_tokens",
)`,
        },
        { type: 'h3', text: '管理画面なしで使える？' },
        {
          type: 'p',
          text: 'いいえ — それがこのライブラリの思想です。ポリシー（モデル・上限・予算）は DB に置き、運用者が管理します。キーだけは環境変数に置くことができます。',
        },
      ],
    },
  ],
}
