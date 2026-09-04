"""Процесс-локальный лимит параллельных HTTP-запросов к OpenRouter."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager


class ParallelismLimiter:
    """Счётчик in-flight вызовов. Лимит передаётся на каждый acquire (0 = без ограничения)."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._in_flight = 0

    @property
    def in_flight(self) -> int:
        with self._condition:
            return self._in_flight

    def reset(self) -> None:
        """Обнуляет счётчик. Нужен тестам, чтобы слот не «завис» после падения."""
        with self._condition:
            self._in_flight = 0
            self._condition.notify_all()

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
        if limit <= 0:
            with self._condition:
                self._in_flight += 1
            return
        with self._condition:
            while self._in_flight >= limit:
                self._condition.wait()
            self._in_flight += 1

    async def _acquire_async(self, limit: int) -> None:
        if limit <= 0:
            with self._condition:
                self._in_flight += 1
            return
        while True:
            with self._condition:
                if self._in_flight < limit:
                    self._in_flight += 1
                    return
            await asyncio.sleep(0.01)

    def _release(self) -> None:
        with self._condition:
            if self._in_flight > 0:
                self._in_flight -= 1
            self._condition.notify()


_LIMITER = ParallelismLimiter()


def get_limiter() -> ParallelismLimiter:
    return _LIMITER
