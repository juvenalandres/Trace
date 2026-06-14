import asyncio
import hashlib
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable

from trace_app.auth import get_current_user


class TTLCache:
    """Thread-safe in-memory LRU cache with TTL."""

    def __init__(self, maxsize: int = 256, ttl: int = 60):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            expires, value = self._cache[key]
            if time.monotonic() < expires:
                self._cache.move_to_end(key)
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = (time.monotonic() + self._ttl, value)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count removed."""
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._cache[k]
        return len(keys_to_delete)

    def clear(self) -> None:
        self._cache.clear()


# Global cache instance: 256 entries, 60 second TTL
_stats_cache = TTLCache(maxsize=256, ttl=60)


def get_stats_cache() -> TTLCache:
    return _stats_cache


def invalidate_user_stats(user_id: int) -> None:
    """Invalidate all cached stats for a user. Call after activity create/update/delete."""
    _stats_cache.invalidate_prefix(f"{user_id}:")
