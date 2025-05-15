"""Rate limiting utilities using the Token Bucket algorithm.

This module provides:

- `RateLimitException`: Custom exception raised when a rate limit is exceeded.
- `TokenBucket`: Core implementation of the token bucket algorithm, managing
  token replenishment and consumption for a single resource.
- `UserRateLimiter`: Manages multiple `TokenBucket` instances, typically one per user,
  to enforce user-specific rate limits for operations like LLM calls.

The `UserRateLimiter` is intended to be instantiated once per limited resource type
(e.g., one for LLM calls) and then used by calling its `check_limit` method,
passing the user identifier.
"""

import time
from typing import Dict, Any


class RateLimitException(Exception):
    """Exception raised when an operation exceeds the defined rate limit."""

    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TokenBucket:
    """Implements the Token Bucket algorithm for a single rate-limited resource.

    Attributes:
        tokens_per_second: The rate at which tokens are added to the bucket.
        max_tokens: The maximum capacity of the bucket.
        current_tokens: The current number of available tokens.
        last_update_time: The timestamp of the last token refill.
    """

    def __init__(self, tokens_per_second: float, max_tokens: float):
        """Initializes a TokenBucket.

        Args:
            tokens_per_second: Rate of token replenishment.
            max_tokens: Maximum token capacity.
        """
        if not (tokens_per_second > 0 and max_tokens > 0):
            raise ValueError("Tokens per second and max tokens must be positive.")
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.current_tokens = max_tokens  # Start full
        self.last_update_time = time.monotonic()  # More precise than time.time()

    def _refill(self) -> None:
        """(Internal) Refills tokens based on time elapsed since last update."""
        now = time.monotonic()
        elapsed_time = now - self.last_update_time
        tokens_to_add = elapsed_time * self.tokens_per_second
        self.current_tokens = min(self.max_tokens, self.current_tokens + tokens_to_add)
        self.last_update_time = now

    def consume(self, tokens_to_consume: int = 1) -> bool:
        """Attempts to consume a number of tokens.

        Args:
            tokens_to_consume: The number of tokens to attempt to consume (must be > 0).

        Returns:
            True if tokens were consumed successfully, False otherwise.
        """
        if tokens_to_consume <= 0:
            raise ValueError("Tokens to consume must be positive.")

        self._refill()
        if self.current_tokens >= tokens_to_consume:
            self.current_tokens -= tokens_to_consume
            return True
        return False

    def get_retry_after(self, tokens_to_consume: int = 1) -> float | None:
        """Calculates how long to wait before tokens_to_consume can be met.

        Args:
            tokens_to_consume: The number of tokens desired.

        Returns:
            Time in seconds to wait, or 0 if consumable immediately,
            or None if the request exceeds max_tokens.
        """
        if tokens_to_consume > self.max_tokens:
            return None  # Impossible to satisfy
        self._refill()
        if self.current_tokens >= tokens_to_consume:
            return 0  # Can consume immediately

        required_additional_tokens = tokens_to_consume - self.current_tokens
        return required_additional_tokens / self.tokens_per_second


class UserRateLimiter:
    """Manages a collection of TokenBuckets, typically one per user ID.

    This allows enforcing rate limits on a per-user basis for shared resources.
    """

    def __init__(self, default_tokens_per_second: float, default_max_tokens: float):
        """Initializes the UserRateLimiter with default bucket parameters.

        Args:
            default_tokens_per_second: Default token refill rate for new user buckets.
            default_max_tokens: Default maximum token capacity for new user buckets.
        """
        self.default_tokens_per_second = default_tokens_per_second
        self.default_max_tokens = default_max_tokens
        self._user_buckets: Dict[Any, TokenBucket] = {}

    def _get_or_create_bucket(self, user_id: Any) -> TokenBucket:
        """(Internal) Retrieves an existing TokenBucket for a user or creates a new one."""
        if user_id not in self._user_buckets:
            self._user_buckets[user_id] = TokenBucket(
                self.default_tokens_per_second, self.default_max_tokens
            )
        return self._user_buckets[user_id]

    def check_limit(self, user_id: Any, tokens_to_consume: int = 1) -> None:
        """Checks if the specified user can consume the given number of tokens.

        Args:
            user_id: The identifier of the user (e.g., Telegram user ID).
            tokens_to_consume: The number of tokens to attempt to consume.

        Raises:
            RateLimitException: If the user's bucket does not have enough tokens.
        """
        bucket = self._get_or_create_bucket(user_id)
        if not bucket.consume(tokens_to_consume):
            retry_after = bucket.get_retry_after(tokens_to_consume)
            msg = "Rate limit exceeded."
            if retry_after is not None and retry_after > 0:
                msg += f" Please try again in {retry_after:.2f} seconds."
            elif retry_after is None:
                msg += " Requested tokens exceed maximum bucket capacity."
            raise RateLimitException(message=msg, retry_after_seconds=retry_after)
