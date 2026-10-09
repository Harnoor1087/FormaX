import time
from app.security.rate_limiter import SlidingWindowRateLimiter

def test_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=10, enabled=True)
    client_id = "test_client_1"

    for _ in range(5):
        allowed, retry_after = limiter.is_allowed(client_id)
        assert allowed is True
        assert retry_after == 0

def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=5, enabled=True)
    client_id = "test_client_2"

    for _ in range(3):
        allowed, _ = limiter.is_allowed(client_id)
        assert allowed is True

    # 4th request must be blocked
    allowed, retry_after = limiter.is_allowed(client_id)
    assert allowed is False
    assert retry_after > 0

def test_rate_limiter_sliding_window_expiry():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=1, enabled=True)
    client_id = "test_client_3"

    assert limiter.is_allowed(client_id)[0] is True
    assert limiter.is_allowed(client_id)[0] is True
    assert limiter.is_allowed(client_id)[0] is False

    # Wait for window to expire
    time.sleep(1.1)
    assert limiter.is_allowed(client_id)[0] is True
