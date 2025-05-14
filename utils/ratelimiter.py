"""Rate limiting utilities for API calls."""

import time
from typing import Dict, Any


class RateLimitException(Exception):
    """Custom exception for when rate limit is exceeded."""

    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TokenBucket:
    """Implements the Token Bucket algorithm for rate limiting."""

    def __init__(self, tokens_per_second: float, max_tokens: float):
        if not (tokens_per_second > 0 and max_tokens > 0):
            raise ValueError("Tokens per second and max tokens must be positive.")
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.current_tokens = max_tokens  # Start full
        self.last_update_time = time.monotonic()  # More precise than time.time()

    def _refill(self) -> None:
        """Refills tokens based on the time elapsed since the last update."""
        now = time.monotonic()
        elapsed_time = now - self.last_update_time
        tokens_to_add = elapsed_time * self.tokens_per_second
        self.current_tokens = min(self.max_tokens, self.current_tokens + tokens_to_add)
        self.last_update_time = now

    def consume(self, tokens_to_consume: int = 1) -> bool:
        """Attempts to consume a number of tokens.

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
        Returns None if it's impossible or immediate.
        """
        if tokens_to_consume > self.max_tokens:
            return None  # Impossible to satisfy
        self._refill()
        if self.current_tokens >= tokens_to_consume:
            return 0  # Can consume immediately

        required_additional_tokens = tokens_to_consume - self.current_tokens
        return required_additional_tokens / self.tokens_per_second


class UserRateLimiter:
    """Manages TokenBuckets for multiple users."""

    def __init__(self, default_tokens_per_second: float, default_max_tokens: float):
        self.default_tokens_per_second = default_tokens_per_second
        self.default_max_tokens = default_max_tokens
        self._user_buckets: Dict[Any, TokenBucket] = {}

    def _get_or_create_bucket(self, user_id: Any) -> TokenBucket:
        if user_id not in self._user_buckets:
            self._user_buckets[user_id] = TokenBucket(
                self.default_tokens_per_second, self.default_max_tokens
            )
        return self._user_buckets[user_id]

    def check_limit(self, user_id: Any, tokens_to_consume: int = 1) -> None:
        """Checks if the user can consume tokens. Raises RateLimitException if not."""
        bucket = self._get_or_create_bucket(user_id)
        if not bucket.consume(tokens_to_consume):
            retry_after = bucket.get_retry_after(tokens_to_consume)
            msg = "Rate limit exceeded."
            if retry_after is not None and retry_after > 0:
                msg += f" Please try again in {retry_after:.2f} seconds."
            elif retry_after is None:
                msg += " Requested tokens exceed maximum bucket capacity."
            raise RateLimitException(message=msg, retry_after_seconds=retry_after)
