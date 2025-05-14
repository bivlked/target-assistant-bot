import pytest
import time
from utils.ratelimiter import TokenBucket, UserRateLimiter, RateLimitException

# Tests for TokenBucket


def test_token_bucket_initialization():
    bucket = TokenBucket(tokens_per_second=10, max_tokens=100)
    assert bucket.current_tokens == 100
    assert bucket.max_tokens == 100
    assert bucket.tokens_per_second == 10


def test_token_bucket_initialization_invalid_params():
    with pytest.raises(ValueError):
        TokenBucket(tokens_per_second=0, max_tokens=100)
    with pytest.raises(ValueError):
        TokenBucket(tokens_per_second=10, max_tokens=0)


def test_token_bucket_consume_sufficient_tokens():
    bucket = TokenBucket(tokens_per_second=1, max_tokens=10)
    assert bucket.consume(5) is True
    assert bucket.current_tokens == pytest.approx(5, abs=1e-2)
    assert bucket.consume(5) is True
    assert bucket.current_tokens == pytest.approx(0, abs=1e-2)


def test_token_bucket_consume_insufficient_tokens():
    bucket = TokenBucket(tokens_per_second=1, max_tokens=5)
    assert bucket.consume(3) is True
    assert bucket.current_tokens == pytest.approx(2, abs=1e-2)
    assert bucket.consume(3) is False  # Not enough tokens
    assert bucket.current_tokens == pytest.approx(2, abs=1e-2)  # Tokens not consumed


def test_token_bucket_consume_invalid_value():
    bucket = TokenBucket(tokens_per_second=1, max_tokens=5)
    with pytest.raises(ValueError):
        bucket.consume(0)
    with pytest.raises(ValueError):
        bucket.consume(-1)


def test_token_bucket_refill():
    tokens_per_sec = 10
    max_tok = 20
    bucket = TokenBucket(tokens_per_second=tokens_per_sec, max_tokens=max_tok)
    bucket.consume(max_tok)  # Empty the bucket
    assert bucket.current_tokens == pytest.approx(0, abs=1e-2)

    time.sleep(0.5)  # Wait for 0.5 seconds
    bucket._refill()  # Manually trigger refill for testing, consume also calls it
    # Expected tokens: 0.5 * 10 = 5
    assert bucket.current_tokens == pytest.approx(
        5, abs=0.1
    )  # Adjusted abs for sleep variability

    time.sleep(2)  # Wait for 2 more seconds (total 2.5s for ~25 tokens, capped at 20)
    bucket._refill()
    assert bucket.current_tokens == max_tok  # Should be capped at max_tokens


def test_token_bucket_get_retry_after():
    bucket = TokenBucket(tokens_per_second=10, max_tokens=20)
    assert bucket.get_retry_after(5) == 0  # Can consume immediately

    bucket.consume(15)  # current_tokens = 5
    assert bucket.current_tokens == 5

    # Need 10 tokens, have 5, need 5 more. Rate 10/s. retry_after = 5/10 = 0.5s
    assert bucket.get_retry_after(10) == pytest.approx(0.5, abs=0.1)

    # Requesting more than max_tokens
    assert bucket.get_retry_after(25) is None

    bucket.consume(5)  # Empty bucket
    # Need 1 token, have 0. retry_after = 1/10 = 0.1s
    assert bucket.get_retry_after(1) == pytest.approx(0.1, abs=0.05)


# Tests for UserRateLimiter


def test_user_rate_limiter_creates_bucket():
    limiter = UserRateLimiter(default_tokens_per_second=1, default_max_tokens=10)
    user_id = "test_user_1"
    assert user_id not in limiter._user_buckets
    limiter._get_or_create_bucket(user_id)  # Access private for test visibility
    assert user_id in limiter._user_buckets
    assert isinstance(limiter._user_buckets[user_id], TokenBucket)


def test_user_rate_limiter_check_limit_allows_and_consumes():
    limiter = UserRateLimiter(default_tokens_per_second=1, default_max_tokens=2)
    user_id = "user_a"
    limiter.check_limit(user_id)  # Consume 1
    limiter.check_limit(user_id)  # Consume 1
    # Next one should fail
    with pytest.raises(RateLimitException) as exc_info:
        limiter.check_limit(user_id)
    assert "Rate limit exceeded" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds is not None
    assert exc_info.value.retry_after_seconds > 0


def test_user_rate_limiter_isolates_users():
    limiter = UserRateLimiter(default_tokens_per_second=1, default_max_tokens=1)
    user_a = "user_a"
    user_b = "user_b"

    limiter.check_limit(user_a)  # user_a consumes their token
    with pytest.raises(RateLimitException):  # user_a should be limited
        limiter.check_limit(user_a)

    limiter.check_limit(user_b)  # user_b should still have their token
    # No exception for user_b, means they are isolated


def test_user_rate_limiter_exception_message_and_retry_after():
    limiter = UserRateLimiter(default_tokens_per_second=1, default_max_tokens=1)
    user_id = "test_user"
    limiter.check_limit(user_id)  # Consume the only token

    with pytest.raises(RateLimitException) as exc_info:
        limiter.check_limit(user_id)

    assert "Rate limit exceeded" in str(exc_info.value)
    assert "Please try again in" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds == pytest.approx(1.0, abs=0.1)


def test_user_rate_limiter_impossible_request():
    limiter = UserRateLimiter(default_tokens_per_second=1, default_max_tokens=5)
    user_id = "test_user"
    with pytest.raises(RateLimitException) as exc_info:
        limiter.check_limit(user_id, tokens_to_consume=10)  # More than max_tokens
    assert "Requested tokens exceed maximum bucket capacity" in str(exc_info.value)
    assert exc_info.value.retry_after_seconds is None
