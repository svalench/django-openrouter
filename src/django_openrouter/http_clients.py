"""Переиспользуемые httpx-клиенты: пул соединений вместо TLS-handshake на каждый вызов."""

from __future__ import annotations

import asyncio
import atexit
import threading
import weakref

import httpx

_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)

_lock = threading.Lock()
_sync_client: httpx.Client | None = None
# AsyncClient привязан к event loop, поэтому по клиенту на loop.
_async_clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient] = (
    weakref.WeakKeyDictionary()
)


def get_sync_client() -> httpx.Client:
    """Потокобезопасный общий клиент процесса. Таймаут передаётся на каждый запрос."""
    global _sync_client
    with _lock:
        if _sync_client is None or _sync_client.is_closed:
            _sync_client = httpx.Client(limits=_LIMITS)
        return _sync_client


def get_async_client() -> httpx.AsyncClient:
    """Общий клиент текущего event loop."""
    loop = asyncio.get_running_loop()
    with _lock:
        client = _async_clients.get(loop)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(limits=_LIMITS)
            _async_clients[loop] = client
        return client


def close_clients() -> None:
    """Закрывает синхронный клиент и забывает асинхронные (их закрывает GC вместе с loop)."""
    global _sync_client
    with _lock:
        if _sync_client is not None:
            _sync_client.close()
            _sync_client = None
        _async_clients.clear()


atexit.register(close_clients)
