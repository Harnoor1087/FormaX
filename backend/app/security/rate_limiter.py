import time
from collections import defaultdict
from threading import Lock
from typing import Tuple, Dict, List
from fastapi import Request, HTTPException, status
from ..config import settings

class SlidingWindowRateLimiter:
    """
    Sliding window in-memory rate limiter protecting against denial-of-service
    and unbounded consumption (OWASP LLM04 / Denial of Wallet).
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60, enabled: bool = True):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Determines whether client_id can make a request.
        Returns:
            Tuple of (is_allowed: bool, retry_after_seconds: int)
        """
        if not self.enabled:
            return True, 0

        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Purge timestamps outside the sliding window
            timestamps = [t for t in self._requests[client_id] if t > window_start]
            self._requests[client_id] = timestamps

            if len(timestamps) >= self.max_requests:
                earliest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - earliest)))
                return False, retry_after

            self._requests[client_id].append(now)
            return True, 0

    def reset(self):
        """Resets rate limiting state (useful for test suites)."""
        with self._lock:
            self._requests.clear()

# Global default instance
rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    enabled=settings.RATE_LIMIT_ENABLED,
)

def rate_limit_dependency(request: Request):
    """
    FastAPI dependency that enforces rate limiting per client IP.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    client_ip = request.client.host if request.client else "unknown_client"
    allowed, retry_after = rate_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Too many requests. Please retry in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
