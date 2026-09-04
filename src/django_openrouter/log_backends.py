"""Плагинные бэкенды логирования запросов.

Список бэкендов задаётся в settings.OPENROUTER['LOG_BACKENDS']. Каждая запись —
либо dotted path к классу (с настройками по умолчанию), либо dict с ключом
'BACKEND' и параметрами:

    OPENROUTER = {
        "LOG_BACKENDS": [
            "django_openrouter.log_backends.DatabaseBackend",
            {
                "BACKEND": "django_openrouter.log_backends.FileBackend",
                "PATH": "/var/log/myapp/openrouter.jsonl",
                "MAX_BYTES": 10 * 1024 * 1024,
                "BACKUP_COUNT": 5,
            },
            {
                "BACKEND": "django_openrouter.log_backends.ClickHouseBackend",
                "URL": "http://localhost:8123",
                "DATABASE": "analytics",
                "TABLE": "openrouter_request_log",
                "USERNAME": "logger",
                "PASSWORD": "secret",
            },
        ],
    }

Если LOG_BACKENDS не задан, пишется только в БД проекта (RequestLog).
Запись в каждый бэкенд выполняется best-effort: ошибка бэкенда не роняет
chat()-запрос, а логируется в logger 'django_openrouter'.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import httpx
from asgiref.sync import sync_to_async
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import receiver
from django.test.signals import setting_changed
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from django_openrouter.config import openrouter_setting
from django_openrouter.current_user import current_username
from django_openrouter.models import RequestLog

if TYPE_CHECKING:
    from django_openrouter.models import OpenRouterModel, UsageProfile

logger = logging.getLogger("django_openrouter")

_DEFAULT_FILE_PATH = "openrouter-requests.jsonl"
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5
_DEFAULT_CLICKHOUSE_TABLE = "django_openrouter_request_log"
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class LogRecord:
    """Сырые данные одного HTTP-вызова, раздаются всем бэкендам."""

    profile: UsageProfile | None  # ORM-объект, нужен только DatabaseBackend
    model: OpenRouterModel | None
    profile_name: str
    model_id: str
    status_code: int
    error_message: str | None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    latency_ms: int
    username: str
    created_at: datetime


def record_to_dict(record: LogRecord) -> dict[str, Any]:
    """Плоское JSON-сериализуемое представление записи (файл, ClickHouse)."""
    return {
        "created_at": record.created_at.isoformat(),
        "profile": record.profile_name,
        "model": record.model_id,
        "status_code": record.status_code,
        "error_message": record.error_message or "",
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
        "cost_usd": str(record.cost_usd),
        "latency_ms": record.latency_ms,
        "username": record.username,
    }


class LogBackend:
    """Базовый класс бэкенда. Потомки переопределяют write() и/или awrite()."""

    def __init__(self, **config: Any) -> None:
        self.config = {str(key).upper(): value for key, value in config.items()}

    def write(self, record: LogRecord) -> None:
        raise NotImplementedError

    async def awrite(self, record: LogRecord) -> None:
        await sync_to_async(self.write, thread_sensitive=True)(record)


class DatabaseBackend(LogBackend):
    """Пишет в RequestLog — таблицу логов по умолчанию.

    Дневные/месячные лимиты и бюджеты (check_limits) считаются именно по ней:
    если убрать этот бэкенд из LOG_BACKENDS, контроль лимитов перестанет работать.
    """

    def write(self, record: LogRecord) -> None:
        RequestLog.objects.create(
            profile=record.profile,
            model=record.model,
            status_code=record.status_code,
            error_message=record.error_message,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            cost_usd=record.cost_usd,
            latency_ms=record.latency_ms,
            username=record.username,
        )

    async def awrite(self, record: LogRecord) -> None:
        await RequestLog.objects.acreate(
            profile=record.profile,
            model=record.model,
            status_code=record.status_code,
            error_message=record.error_message,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            cost_usd=record.cost_usd,
            latency_ms=record.latency_ms,
            username=record.username,
        )


class FileBackend(LogBackend):
    """JSON Lines в файл с ротацией по объёму (logging.handlers.RotatingFileHandler)."""

    _handlers: dict[tuple[str, int, int], logging.Handler] = {}

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        self.path = str(self.config.get("PATH") or _DEFAULT_FILE_PATH)
        self.max_bytes = int(self.config.get("MAX_BYTES") or _DEFAULT_MAX_BYTES)
        self.backup_count = int(self.config.get("BACKUP_COUNT") or _DEFAULT_BACKUP_COUNT)
        self._logger = logging.getLogger("django_openrouter.request_log")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        key = (self.path, self.max_bytes, self.backup_count)
        if key not in self._handlers:
            from logging.handlers import RotatingFileHandler

            handler = RotatingFileHandler(
                self.path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._handlers[key] = handler
        self._handler = self._handlers[key]
        if self._handler not in self._logger.handlers:
            self._logger.addHandler(self._handler)

    def write(self, record: LogRecord) -> None:
        self._logger.info(json.dumps(record_to_dict(record), ensure_ascii=False))

    async def awrite(self, record: LogRecord) -> None:
        await asyncio.to_thread(self.write, record)


class ClickHouseBackend(LogBackend):
    """INSERT через HTTP-интерфейс ClickHouse, формат JSONEachRow.

    Дополнительных зависимостей не требует: используется уже входящий в
    пакет httpx. Имена database/table проверяются, чтобы не допустить
    инъекции в строку INSERT.
    """

    def __init__(self, **config: Any) -> None:
        super().__init__(**config)
        url = str(self.config.get("URL") or "").rstrip("/")
        if not url:
            raise ImproperlyConfigured(
                _(
                    "ClickHouseBackend requires 'URL' in the LOG_BACKENDS entry "
                    "(e.g. http://localhost:8123)."
                )
            )
        self.url = url
        self.database = str(self.config.get("DATABASE") or "default")
        self.table = str(self.config.get("TABLE") or _DEFAULT_CLICKHOUSE_TABLE)
        for label, identifier in (("DATABASE", self.database), ("TABLE", self.table)):
            if not _IDENTIFIER_RE.fullmatch(identifier):
                raise ImproperlyConfigured(
                    _("ClickHouseBackend: invalid %(label)s identifier %(identifier)r.")
                    % {"label": label, "identifier": identifier}
                )
        username = self.config.get("USERNAME")
        password = self.config.get("PASSWORD")
        self._auth_kwargs: dict[str, Any] = {}
        if username or password:
            self._auth_kwargs["auth"] = httpx.BasicAuth(str(username or ""), str(password or ""))
        self.timeout = float(self.config.get("TIMEOUT") or 10)

    @property
    def _query(self) -> str:
        return f"INSERT INTO {self.database}.{self.table} FORMAT JSONEachRow"

    def write(self, record: LogRecord) -> None:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.url}/",
                params={"query": self._query},
                content=json.dumps(record_to_dict(record), ensure_ascii=False),
                **self._auth_kwargs,
            )
            response.raise_for_status()

    async def awrite(self, record: LogRecord) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/",
                params={"query": self._query},
                content=json.dumps(record_to_dict(record), ensure_ascii=False),
                **self._auth_kwargs,
            )
            response.raise_for_status()


def _build_backend(spec: str | dict[str, Any]) -> LogBackend:
    if isinstance(spec, str):
        path, options = spec, {}
    elif isinstance(spec, dict):
        raw_path = spec.get("BACKEND") or spec.get("backend")
        if not raw_path:
            raise ImproperlyConfigured(_("LOG_BACKENDS entry dict requires a 'BACKEND' key."))
        path = str(raw_path)
        options = {key: value for key, value in spec.items() if str(key).upper() != "BACKEND"}
    else:
        raise ImproperlyConfigured(
            _("LOG_BACKENDS entries must be strings or dicts, got %(type)s.")
            % {"type": type(spec).__name__}
        )
    try:
        backend_cls: type[LogBackend] = import_string(path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            _("Cannot import log backend %(path)r: %(error)s") % {"path": path, "error": exc}
        ) from exc
    if not issubclass(backend_cls, LogBackend):
        raise ImproperlyConfigured(_("%(path)r is not a LogBackend subclass.") % {"path": path})
    return backend_cls(**options)


_backend_registry: list[LogBackend] | None = None


def get_log_backends(*, force_reload: bool = False) -> list[LogBackend]:
    """Резолвит LOG_BACKENDS из settings (с кэшем на процесс)."""
    global _backend_registry
    if _backend_registry is not None and not force_reload:
        return _backend_registry
    specs = openrouter_setting("LOG_BACKENDS")
    if specs is None:
        specs = ["django_openrouter.log_backends.DatabaseBackend"]
    if not isinstance(specs, (list, tuple)):
        raise ImproperlyConfigured(_("OPENROUTER['LOG_BACKENDS'] must be a list."))
    _backend_registry = [_build_backend(spec) for spec in specs]
    return _backend_registry


def invalidate_log_backends() -> None:
    global _backend_registry
    _backend_registry = None


@receiver(setting_changed)
def _reset_on_setting_changed(*, setting: str, **kwargs: Any) -> None:
    if setting == "OPENROUTER" or setting.startswith("OPENROUTER_"):
        invalidate_log_backends()


def dispatch_log(record: LogRecord) -> None:
    """Синхронно пишет запись во все настроенные бэкенды (best-effort)."""
    for backend in get_log_backends():
        try:
            backend.write(record)
        except Exception:
            logger.exception("OpenRouter log backend %s failed.", type(backend).__name__)


async def adispatch_log(record: LogRecord) -> None:
    """Асинхронный вариант dispatch_log."""
    for backend in get_log_backends():
        try:
            await backend.awrite(record)
        except Exception:
            logger.exception("OpenRouter log backend %s failed.", type(backend).__name__)


def make_record(
    *,
    profile: UsageProfile | None,
    model: OpenRouterModel | None,
    status_code: int,
    error_message: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: Decimal = Decimal("0"),
    latency_ms: int = 0,
    username: str | None = None,
) -> LogRecord:
    """Собирает LogRecord из аргументов клиента (created_at ставится здесь)."""
    return LogRecord(
        profile=profile,
        model=model,
        profile_name=profile.name if profile is not None else "",
        model_id=model.model_id if model is not None else "",
        status_code=status_code,
        error_message=error_message,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        username=username or current_username(),
        created_at=timezone.now(),
    )
