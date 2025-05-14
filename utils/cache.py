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


class _CacheEntry(Dict[str, Any]):
    __slots__ = ("value", "ts")


# ---------------------------------------------------------------------------
# Public helper – singleton style
# ---------------------------------------------------------------------------


# Using a global store to be shared across instances of SheetsManager
# This is simpler than passing SheetCache instance around.
_global_sheet_store: Dict[Tuple[int, str], Tuple[Any, float]] | None = None


class SheetCache:  # pylint: disable=too-few-public-methods
    def __init__(self):
        global _global_sheet_store
        if _global_sheet_store is None:
            _global_sheet_store = {}
        self._store = _global_sheet_store

    def cached(self, key_fn: Callable[..., str]):  # noqa: D401
        """Decorator for read methods of SheetsManager.

        ``key_fn`` receives the same args/kwargs as the wrapped method and
        returns additional part of the key (e.g. date).
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(self, user_id: int, *args: Any, **kwargs: Any) -> T:  # type: ignore[override]
                cache_key = (user_id, f"{func.__name__}:{key_fn(*args, **kwargs)}")
                val_ts = self._store.get(cache_key)
                if val_ts:
                    value, ts = val_ts
                    if time.time() - ts < TTL_SECONDS:
                        return value  # type: ignore[return-value]
                value = func(self, user_id, *args, **kwargs)
                self._store[cache_key] = (value, time.time())
                return value

            return wrapper

        return decorator

    def invalidate(self, user_id: int) -> None:
        """Drop all cache entries of given user."""
        keys_to_delete = [k for k in self._store if k[0] == user_id]
        for k in keys_to_delete:
            self._store.pop(k, None)


sheet_cache = SheetCache()
