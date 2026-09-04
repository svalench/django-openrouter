from __future__ import annotations

import asyncio
import threading
import time

from django_openrouter.concurrency import ParallelismLimiter, get_limiter


def test_sync_slot_respects_limit() -> None:
    limiter = ParallelismLimiter()
    current = 0
    max_seen = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal current, max_seen
        with limiter.slot(2):
            with lock:
                current += 1
                max_seen = max(max_seen, current)
            time.sleep(0.05)
            with lock:
                current -= 1

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert max_seen <= 2
    assert max_seen >= 2
    assert limiter.in_flight == 0


def test_zero_limit_is_unlimited() -> None:
    limiter = ParallelismLimiter()
    with limiter.slot(0):
        with limiter.slot(0):
            assert limiter.in_flight == 2
    assert limiter.in_flight == 0


def test_reset_clears_in_flight() -> None:
    limiter = ParallelismLimiter()
    limiter._acquire(0)
    assert limiter.in_flight == 1
    limiter.reset()
    assert limiter.in_flight == 0


def test_async_slot_respects_limit() -> None:
    async def main() -> None:
        limiter = ParallelismLimiter()
        current = 0
        max_seen = 0
        lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal current, max_seen
            async with limiter.aslot(2):
                async with lock:
                    current += 1
                    max_seen = max(max_seen, current)
                await asyncio.sleep(0.05)
                async with lock:
                    current -= 1

        await asyncio.gather(*[worker() for _ in range(6)])
        assert max_seen <= 2
        assert max_seen >= 2
        assert limiter.in_flight == 0

    asyncio.run(main())


def test_get_limiter_is_singleton() -> None:
    assert get_limiter() is get_limiter()
