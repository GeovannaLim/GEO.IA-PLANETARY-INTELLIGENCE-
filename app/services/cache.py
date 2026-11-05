"""Small async-aware TTL cache for provider metadata (catalogues, capabilities,
product searches). Results of analyses are cached separately in the store."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable


class TTLCache:
    def __init__(self, maxsize: int = 512):
        self._data: dict[Any, tuple[float, Any]] = {}
        self._locks: dict[Any, asyncio.Lock] = {}
        self.maxsize = maxsize

    def get(self, key: Any) -> Any:
        hit = self._data.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: Any, value: Any, ttl_s: float) -> None:
        if len(self._data) >= self.maxsize:
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)
        self._data[key] = (time.monotonic() + ttl_s, value)

    async def get_or_set(self, key: Any, ttl_s: float, factory: Callable[[], Awaitable[Any]]) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            value = self.get(key)
            if value is None:
                value = await factory()  # exceptions are not cached
                self.set(key, value, ttl_s)
            return value

    def clear(self) -> None:
        self._data.clear()


metadata_cache = TTLCache()
