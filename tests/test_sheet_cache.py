import pytest
from unittest.mock import MagicMock
import time

from utils.cache import sheet_cache_instance, TTL_SECONDS, cached_sheet_method


class DummyCachedReader:
    def __init__(self):
        self.api_calls = 0

    @cached_sheet_method(lambda: "global_data")
    def get_global_data(self, user_id: int) -> str:
        self.api_calls += 1
        return f"Global data for {user_id}"

    @cached_sheet_method(lambda date_str: date_str)
    def get_daily_data(self, user_id: int, date_str: str) -> str:
        self.api_calls += 1
        return f"Data for {user_id} on {date_str}"

    # Simulate a write operation that should invalidate cache
    def update_data(self, user_id: int, _data: str):
        sheet_cache_instance._invalidate_for_user(user_id)


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """Ensure cache is empty before each test run."""
    # Access internal store for full clear, as invalidate needs user_id
    sheet_cache_instance._store.clear()  # pylint: disable=protected-access
    yield


def test_cache_serves_from_cache_on_second_call():
    reader = DummyCachedReader()
    user_id = 1

    # First call - should hit API
    reader.get_global_data(user_id)
    assert reader.api_calls == 1

    # Second call - should be cached
    reader.get_global_data(user_id)
    assert reader.api_calls == 1, "Second call should be cached"


def test_cache_invalidates_on_write():
    reader = DummyCachedReader()
    user_id = 1

    reader.get_global_data(user_id)  # Populate cache
    assert reader.api_calls == 1

    reader.update_data(user_id, "new data")  # Invalidate

    reader.get_global_data(user_id)  # Should hit API again
    assert reader.api_calls == 2, "Cache should be invalidated after write"


def test_cache_respects_ttl():
    reader = DummyCachedReader()
    user_id = 1

    reader.get_global_data(user_id)
    assert reader.api_calls == 1

    # Manipulate timestamp of the cached entry to simulate expiry
    cache_key = (user_id, "get_global_data:global_data")
    _value, _ts = sheet_cache_instance._store[
        cache_key
    ]  # pylint: disable=protected-access
    sheet_cache_instance._store[cache_key] = (
        _value,
        time.time() - TTL_SECONDS - 1,
    )  # pylint: disable=protected-access

    reader.get_global_data(user_id)
    assert reader.api_calls == 2, "Cache should expire after TTL"


def test_cache_keys_are_distinct_for_different_methods_and_args():
    reader = DummyCachedReader()
    user_id = 1

    reader.get_global_data(user_id)  # call 1
    reader.get_daily_data(user_id, "2024-01-01")  # call 2
    reader.get_daily_data(user_id, "2024-01-02")  # call 3
    assert reader.api_calls == 3

    # Repeat calls - should be cached
    reader.get_global_data(user_id)
    reader.get_daily_data(user_id, "2024-01-01")
    reader.get_daily_data(user_id, "2024-01-02")
    assert reader.api_calls == 3, "All subsequent calls should be cached"


def test_cache_isolates_users():
    reader = DummyCachedReader()
    user1, user2 = 1, 2

    reader.get_global_data(user1)  # user1, call 1
    reader.get_global_data(user2)  # user2, call 1
    assert reader.api_calls == 2

    reader.get_global_data(user1)  # user1, cached
    reader.get_global_data(user2)  # user2, cached
    assert reader.api_calls == 2

    reader.update_data(user1, "new data for user1")  # Invalidate user1 only

    reader.get_global_data(user1)  # user1, call 2 (API hit)
    assert reader.api_calls == 3
    reader.get_global_data(user2)  # user2, still cached
    assert reader.api_calls == 3, "Invalidating user1 should not affect user2"
