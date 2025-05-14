from __future__ import annotations

"""Simple in-memory LRU cache for Google Sheets read operations.

The cache key includes user_id and the logical method name. Any write
operation **must** call :pyfunc:`invalidate` to keep data consistent in
case the user (or bot) modifies the spreadsheet.

For safety we also set a TTL (time-to-live) – even if invalidate was not
called, entries older than ``TTL_SECONDS`` are silently ignored.
"""

from functools import lru_cache
from typing import Callable, TypeVar, Any, Dict, Tuple
import time

T = TypeVar("T")

TTL_SECONDS = 3600  # 1 hour


class SheetCache:
    def __init__(self) -> None:
        self._store: Dict[Tuple[int, str], Tuple[Any, float]] = {}

    def _get_from_store(self, cache_key: Tuple[int, str]) -> Any | None:
        val_ts = self._store.get(cache_key)
        if val_ts:
            value, ts = val_ts
            if time.time() - ts < TTL_SECONDS:
                return value
        return None

    def _put_in_store(self, cache_key: Tuple[int, str], value: Any) -> None:
        self._store[cache_key] = (value, time.time())

    def _invalidate_for_user(self, user_id: int) -> None:
        """Drops all cache entries for a given user."""
        keys_to_delete = [k for k in self._store if k[0] == user_id]
        for k in keys_to_delete:
            self._store.pop(k, None)


# ---------------------------------------------------------------------------
# Public helper – singleton style
# ---------------------------------------------------------------------------


# Using a global store to be shared across instances of SheetsManager
# This is simpler than passing SheetCache instance around.
_global_sheet_store: Dict[Tuple[int, str], Tuple[Any, float]] | None = None


# Global singleton instance
sheet_cache_instance = SheetCache()


# Public decorator and invalidate function that use the singleton
def cached_sheet_method(key_fn: Callable[..., str]):
    """Decorator for read methods that should be cached.
    ``key_fn`` generates a unique part of the cache key based on method arguments.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(
            self_decorated_method: Any, user_id: int, *args: Any, **kwargs: Any
        ) -> T:
            cache_key = (user_id, f"{func.__name__}:{key_fn(*args, **kwargs)}")
            cached_value = sheet_cache_instance._get_from_store(cache_key)
            if cached_value is not None:
                return cached_value

            value = func(self_decorated_method, user_id, *args, **kwargs)
            sheet_cache_instance._put_in_store(cache_key, value)
            return value

        return wrapper

    return decorator


def invalidate_sheet_cache(user_id: int) -> None:
    """Public function to invalidate cache for a user."""
    sheet_cache_instance._invalidate_for_user(user_id)
