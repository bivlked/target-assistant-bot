"""User subscription management for Target Assistant Bot."""

from __future__ import annotations

import structlog
from typing import Set

logger = structlog.get_logger(__name__)

# In-memory storage for subscribed users
# In production, this should be replaced with persistent storage (Redis, database, etc.)
_subscribed_users: Set[int] = set()


def subscribe_user(user_id: int) -> None:
    """Subscribe a user to the bot.

    Args:
        user_id: Telegram user ID
    """
    _subscribed_users.add(user_id)
    logger.info(f"User {user_id} subscribed")


def unsubscribe_user(user_id: int) -> None:
    """Unsubscribe a user from the bot.

    Args:
        user_id: Telegram user ID
    """
    _subscribed_users.discard(user_id)
    logger.info(f"User {user_id} unsubscribed")


async def is_subscribed(user_id: int) -> bool:
    """Check if a user is subscribed to the bot.

    Args:
        user_id: Telegram user ID

    Returns:
        True if user is subscribed, False otherwise
    """
    return user_id in _subscribed_users


def get_subscribed_users() -> Set[int]:
    """Get all subscribed users.

    Returns:
        Set of subscribed user IDs
    """
    return _subscribed_users.copy()


def get_subscription_count() -> int:
    """Get total number of subscribed users.

    Returns:
        Number of subscribed users
    """
    return len(_subscribed_users)
