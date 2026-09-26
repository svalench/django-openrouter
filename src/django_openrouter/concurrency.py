"""Процесс-локальный лимит параллельных HTTP-запросов к OpenRouter."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager


class ParallelismLimiter:
    """
    Счётчик in-flight вызовов. Лимит передаётся на каждый acquire (0 = без ограничения).

    Счётчик общий для потоков и event loop'ов процесса. Синхронные ожидающие
    спят на threading.Condition, асинхронные — на asyncio.Future своего loop;
    release будит и тех, и других, без busy-wait.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._in_flight = 0
        self._async_waiters: deque[tuple[asyncio.AbstractEventLoop, asyncio.Future[None]]] = (
            deque()
        )

    @property
    def in_flight(self) -> int:
        with self._condition:
            return self._in_flight

    def reset(self) -> None:
        """Обнуляет счётчик. Нужен тестам, чтобы слот не «завис» после падения."""
        with self._condition:
            self._in_flight = 0
            self._wake_all_locked()

    @contextmanager
    def slot(self, limit: int) -> Iterator[None]:
        self._acquire(int(limit))
        try:
            yield
        finally:
            self._release()

    @asynccontextmanager
    async def aslot(self, limit: int) -> AsyncIterator[None]:
        await self._acquire_async(int(limit))
        try:
            yield
        finally:
            self._release()

    def _acquire(self, limit: int) -> None:
        with self._condition:
            while limit > 0 and self._in_flight >= limit:
                self._condition.wait()
            self._in_flight += 1

    async def _acquire_async(self, limit: int) -> None:
        loop = asyncio.get_running_loop()
        while True:
            with self._condition:
                if limit <= 0 or self._in_flight < limit:
                    self._in_flight += 1
                    return
                waiter: asyncio.Future[None] = loop.create_future()
                self._async_waiters.append((loop, waiter))
            try:
                await waiter
            finally:
                with self._condition:
                    if (loop, waiter) in self._async_waiters:
                        self._async_waiters.remove((loop, waiter))

    def _release(self) -> None:
        with self._condition:
            if self._in_flight > 0:
                self._in_flight -= 1
            self._wake_all_locked()

    def _wake_all_locked(self) -> None:
        # Будим всех: лимиты у вызовов могут отличаться, кто пройдёт — решит цикл acquire.
        self._condition.notify_all()
        while self._async_waiters:
            loop, waiter = self._async_waiters.popleft()
            if not loop.is_closed():
                loop.call_soon_threadsafe(_resolve, waiter)


def _resolve(waiter: asyncio.Future[None]) -> None:
    if not waiter.done():
        waiter.set_result(None)


_LIMITER = ParallelismLimiter()


def get_limiter() -> ParallelismLimiter:
    return _LIMITER
