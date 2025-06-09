"""Tests for utils/subscription.py user subscription management."""

import pytest
from unittest.mock import patch

from utils.subscription import (
    subscribe_user,
    unsubscribe_user,
    is_subscribed,
    get_subscribed_users,
    get_subscription_count,
    _subscribed_users,
)


@pytest.fixture(autouse=True)
def clear_subscriptions():
    """Clear subscription state before each test."""
    _subscribed_users.clear()
    yield
    _subscribed_users.clear()


def test_subscribe_user():
    """Test user subscription functionality."""
    user_id = 12345

    # Initially user should not be subscribed
    assert user_id not in _subscribed_users
    assert get_subscription_count() == 0

    # Subscribe user
    subscribe_user(user_id)

    # User should now be subscribed
    assert user_id in _subscribed_users
    assert get_subscription_count() == 1

    # Subscribing the same user again should not duplicate
    subscribe_user(user_id)
    assert get_subscription_count() == 1


def test_unsubscribe_user():
    """Test user unsubscription functionality."""
    user_id = 54321

    # Subscribe user first
    subscribe_user(user_id)
    assert user_id in _subscribed_users
    assert get_subscription_count() == 1

    # Unsubscribe user
    unsubscribe_user(user_id)

    # User should no longer be subscribed
    assert user_id not in _subscribed_users
    assert get_subscription_count() == 0

    # Unsubscribing non-existent user should not raise error
    unsubscribe_user(99999)  # Non-existent user
    assert get_subscription_count() == 0


@pytest.mark.asyncio
async def test_is_subscribed():
    """Test subscription status checking."""
    user_id_1 = 11111
    user_id_2 = 22222

    # Initially no users are subscribed
    assert await is_subscribed(user_id_1) is False
    assert await is_subscribed(user_id_2) is False

    # Subscribe only user_id_1
    subscribe_user(user_id_1)

    # Check subscription status
    assert await is_subscribed(user_id_1) is True
    assert await is_subscribed(user_id_2) is False

    # Subscribe user_id_2
    subscribe_user(user_id_2)

    # Both should be subscribed now
    assert await is_subscribed(user_id_1) is True
    assert await is_subscribed(user_id_2) is True

    # Unsubscribe user_id_1
    unsubscribe_user(user_id_1)

    # Only user_id_2 should be subscribed
    assert await is_subscribed(user_id_1) is False
    assert await is_subscribed(user_id_2) is True


def test_get_subscribed_users():
    """Test getting all subscribed users."""
    user_ids = [100, 200, 300]

    # Initially no users
    subscribed = get_subscribed_users()
    assert subscribed == set()
    assert len(subscribed) == 0

    # Subscribe users
    for user_id in user_ids:
        subscribe_user(user_id)

    # Get subscribed users
    subscribed = get_subscribed_users()
    assert subscribed == set(user_ids)
    assert len(subscribed) == 3

    # Returned set should be a copy (modifying it should not affect internal state)
    subscribed.add(999)
    assert 999 not in _subscribed_users
    assert get_subscription_count() == 3


def test_get_subscription_count():
    """Test getting subscription count."""
    # Initially zero
    assert get_subscription_count() == 0

    # Add users and check count
    subscribe_user(1)
    assert get_subscription_count() == 1

    subscribe_user(2)
    assert get_subscription_count() == 2

    subscribe_user(3)
    assert get_subscription_count() == 3

    # Remove user and check count
    unsubscribe_user(2)
    assert get_subscription_count() == 2

    unsubscribe_user(1)
    unsubscribe_user(3)
    assert get_subscription_count() == 0


def test_subscription_logging():
    """Test that subscription actions are logged."""
    user_id = 77777

    # Test subscribe logging
    with patch("utils.subscription.logger.info") as mock_log:
        subscribe_user(user_id)
        mock_log.assert_called_once_with("User subscribed", user_id=user_id)

    # Test unsubscribe logging
    with patch("utils.subscription.logger.info") as mock_log:
        unsubscribe_user(user_id)
        mock_log.assert_called_once_with("User unsubscribed", user_id=user_id)


def test_multiple_users_workflow():
    """Test complete workflow with multiple users."""
    users = [1001, 1002, 1003, 1004, 1005]

    # Subscribe all users
    for user_id in users:
        subscribe_user(user_id)

    assert get_subscription_count() == 5
    subscribed = get_subscribed_users()
    assert subscribed == set(users)

    # Check all are subscribed
    for user_id in users:
        assert user_id in _subscribed_users

    # Unsubscribe some users
    unsubscribe_user(1002)
    unsubscribe_user(1004)

    assert get_subscription_count() == 3
    expected_remaining = {1001, 1003, 1005}
    assert get_subscribed_users() == expected_remaining

    # Check individual subscription status
    assert 1001 in _subscribed_users
    assert 1002 not in _subscribed_users
    assert 1003 in _subscribed_users
    assert 1004 not in _subscribed_users
    assert 1005 in _subscribed_users


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases and boundary conditions."""
    # Test with zero user ID
    subscribe_user(0)
    assert await is_subscribed(0) is True
    assert get_subscription_count() == 1

    # Test with negative user ID
    subscribe_user(-1)
    assert await is_subscribed(-1) is True
    assert get_subscription_count() == 2

    # Test with large user ID
    large_id = 999999999
    subscribe_user(large_id)
    assert await is_subscribed(large_id) is True
    assert get_subscription_count() == 3

    # Clean up
    unsubscribe_user(0)
    unsubscribe_user(-1)
    unsubscribe_user(large_id)
    assert get_subscription_count() == 0
