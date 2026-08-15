import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID
from weakref import WeakValueDictionary

_market_locks: WeakValueDictionary[tuple[int, UUID], asyncio.Lock] = (
    WeakValueDictionary()
)


@asynccontextmanager
async def local_market_lock(market_id: UUID) -> AsyncIterator[None]:
    """Serialize SQLite trades where ``SELECT FOR UPDATE`` is unavailable.

    PostgreSQL remains protected by its database row lock. This process-local fallback
    makes the supported SQLite development/test mode deterministic as well.
    """

    loop = asyncio.get_running_loop()
    key = (id(loop), market_id)
    lock = _market_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _market_locks[key] = lock
    async with lock:
        yield
