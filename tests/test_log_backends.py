from __future__ import annotations

import json
from logging.handlers import RotatingFileHandler
from pathlib import Path

import httpx
import pytest
import respx
from asgiref.sync import async_to_sync
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_openrouter import achat, chat
from django_openrouter.log_backends import (
    DatabaseBackend,
    FileBackend,
    get_log_backends,
    invalidate_log_backends,
)
from django_openrouter.models import OpenRouterSettings, RequestLog, UsageProfile
from tests.conftest import completion_payload

pytestmark = pytest.mark.django_db

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
CLICKHOUSE_URL = "http://clickhouse.example:8123"
MESSAGES = [{"role": "user", "content": "Hi"}]
FILE_BACKEND = "django_openrouter.log_backends.FileBackend"
CLICKHOUSE_BACKEND = "django_openrouter.log_backends.ClickHouseBackend"


@pytest.fixture(autouse=True)
def _reset_log_backends():
    invalidate_log_backends()
    yield
    invalidate_log_backends()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_default_backend_is_database() -> None:
    backends = get_log_backends(force_reload=True)
    assert len(backends) == 1
    assert isinstance(backends[0], DatabaseBackend)


@respx.mock
def test_chat_logs_to_file(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    log_file = tmp_path / "openrouter.jsonl"
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(prompt_tokens=10, completion_tokens=5)
        )
    )
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": FILE_BACKEND, "PATH": str(log_file)}]}
    ):
        result = chat("chat", messages=MESSAGES)
    assert result.content == "Hello"
    assert RequestLog.objects.count() == 0  # DB backend не настроен
    rows = read_jsonl(log_file)
    assert len(rows) == 1
    row = rows[0]
    assert row["profile"] == "chat"
    assert row["model"] == "anthropic/claude-3.5-sonnet"
    assert row["status_code"] == 200
    assert row["prompt_tokens"] == 10
    assert row["completion_tokens"] == 5
    assert row["latency_ms"] >= 0
    assert row["username"] == "anonymous"
    assert row["created_at"]


@respx.mock
def test_chat_logs_to_database_and_file(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    log_file = tmp_path / "openrouter.jsonl"
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload())
    )
    with override_settings(
        OPENROUTER={
            "LOG_BACKENDS": [
                "django_openrouter.log_backends.DatabaseBackend",
                {"BACKEND": FILE_BACKEND, "PATH": str(log_file)},
            ]
        }
    ):
        chat("chat", messages=MESSAGES)
    assert RequestLog.objects.count() == 1
    assert len(read_jsonl(log_file)) == 1


def test_file_backend_rotation_settings(tmp_path: Path) -> None:
    log_file = tmp_path / "openrouter.jsonl"
    with override_settings(
        OPENROUTER={
            "LOG_BACKENDS": [
                {
                    "BACKEND": FILE_BACKEND,
                    "PATH": str(log_file),
                    "MAX_BYTES": 1024,
                    "BACKUP_COUNT": 3,
                }
            ]
        }
    ):
        backends = get_log_backends(force_reload=True)
    backend = backends[0]
    assert isinstance(backend, FileBackend)
    assert isinstance(backend._handler, RotatingFileHandler)
    assert backend._handler.maxBytes == 1024
    assert backend._handler.backupCount == 3


@respx.mock
def test_chat_logs_to_clickhouse(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200, json=completion_payload(prompt_tokens=7, completion_tokens=3)
        )
    )
    route = respx_mock.post(f"{CLICKHOUSE_URL}/").mock(return_value=httpx.Response(200))
    with override_settings(
        OPENROUTER={
            "LOG_BACKENDS": [
                {
                    "BACKEND": CLICKHOUSE_BACKEND,
                    "URL": CLICKHOUSE_URL,
                    "DATABASE": "analytics",
                    "TABLE": "openrouter_request_log",
                    "USERNAME": "logger",
                    "PASSWORD": "secret",
                }
            ]
        }
    ):
        chat("chat", messages=MESSAGES)
    assert RequestLog.objects.count() == 0
    request = route.calls.last.request
    assert "INSERT INTO analytics.openrouter_request_log FORMAT JSONEachRow" in str(
        request.url.params["query"]
    )
    assert request.headers["Authorization"].startswith("Basic ")
    row = json.loads(request.content.decode("utf-8"))
    assert row["profile"] == "chat"
    assert row["model"] == "anthropic/claude-3.5-sonnet"
    assert row["status_code"] == 200
    assert row["prompt_tokens"] == 7
    assert row["completion_tokens"] == 3
    assert row["username"] == "anonymous"


@respx.mock
def test_clickhouse_failure_does_not_break_chat(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="pong"))
    )
    respx_mock.post(f"{CLICKHOUSE_URL}/").mock(return_value=httpx.Response(500, text="boom"))
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": CLICKHOUSE_BACKEND, "URL": CLICKHOUSE_URL}]}
    ):
        result = chat("chat", messages=MESSAGES)
    assert result.content == "pong"  # логирование best-effort


@respx.mock
def test_async_chat_logs_to_file(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    log_file = tmp_path / "async.jsonl"
    respx_mock.post(CHAT_URL).mock(
        return_value=httpx.Response(200, json=completion_payload(content="async-ok"))
    )
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": FILE_BACKEND, "PATH": str(log_file)}]}
    ):
        result = async_to_sync(achat)("chat", messages=MESSAGES)
    assert result.content == "async-ok"
    rows = read_jsonl(log_file)
    assert len(rows) == 1
    assert rows[0]["status_code"] == 200


@respx.mock
def test_async_chat_logs_to_clickhouse(
    respx_mock: respx.MockRouter,
    or_settings: OpenRouterSettings,
    profile: UsageProfile,
) -> None:
    respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(200, json=completion_payload()))
    route = respx_mock.post(f"{CLICKHOUSE_URL}/").mock(return_value=httpx.Response(200))
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": CLICKHOUSE_BACKEND, "URL": CLICKHOUSE_URL}]}
    ):
        async_to_sync(achat)("chat", messages=MESSAGES)
    assert len(route.calls) == 1


def test_clickhouse_requires_url() -> None:
    with override_settings(OPENROUTER={"LOG_BACKENDS": [CLICKHOUSE_BACKEND]}):
        with pytest.raises(ImproperlyConfigured, match="URL"):
            get_log_backends(force_reload=True)


def test_clickhouse_rejects_invalid_identifiers() -> None:
    with override_settings(
        OPENROUTER={
            "LOG_BACKENDS": [
                {"BACKEND": CLICKHOUSE_BACKEND, "URL": CLICKHOUSE_URL, "TABLE": "x; DROP TABLE y"}
            ]
        }
    ):
        with pytest.raises(ImproperlyConfigured, match="TABLE"):
            get_log_backends(force_reload=True)


def test_unknown_backend_path() -> None:
    with override_settings(OPENROUTER={"LOG_BACKENDS": ["no.such.Backend"]}):
        with pytest.raises(ImproperlyConfigured, match="Cannot import"):
            get_log_backends(force_reload=True)


def test_backend_must_subclass_log_backend() -> None:
    with override_settings(OPENROUTER={"LOG_BACKENDS": ["decimal.Decimal"]}):
        with pytest.raises(ImproperlyConfigured, match="not a LogBackend"):
            get_log_backends(force_reload=True)


def test_dict_entry_requires_backend_key() -> None:
    with override_settings(OPENROUTER={"LOG_BACKENDS": [{"PATH": "/tmp/x.jsonl"}]}):
        with pytest.raises(ImproperlyConfigured, match="BACKEND"):
            get_log_backends(force_reload=True)


def test_log_backends_must_be_a_list() -> None:
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": "django_openrouter.log_backends.FileBackend"}
    ):
        with pytest.raises(ImproperlyConfigured, match="must be a list"):
            get_log_backends(force_reload=True)


def test_override_settings_reloads_backends(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": FILE_BACKEND, "PATH": str(first)}]}
    ):
        assert get_log_backends()[0].config["PATH"] == str(first)
    with override_settings(
        OPENROUTER={"LOG_BACKENDS": [{"BACKEND": FILE_BACKEND, "PATH": str(second)}]}
    ):
        assert get_log_backends()[0].config["PATH"] == str(second)
