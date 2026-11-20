"""Rate limiting for token operations to prevent brute-force attacks."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple


class TokenRateLimiter:
    """
    Rate limiter specifically for token operations.
    Prevents brute-force token guessing and abuse.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
        lockout_seconds: int = 300,
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_attempts: Maximum failed attempts within window
            window_seconds: Time window for counting attempts
            lockout_seconds: Lockout duration after exceeding max attempts
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        
        # Track attempts: client_ip -> [(timestamp, success)]
        self._attempts: Dict[str, list[Tuple[datetime, bool]]] = defaultdict(list)
        
        # Track lockouts: client_ip -> lockout_until
        self._lockouts: Dict[str, datetime] = {}

    def record_attempt(self, client_ip: str, success: bool) -> None:
        """Record a token validation attempt."""
        now = datetime.now()
        
        # Clean old attempts (outside window)
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._attempts[client_ip] = [
            (ts, s) for ts, s in self._attempts[client_ip]
            if ts > cutoff
        ]
        
        # Record new attempt
        self._attempts[client_ip].append((now, success))
        
        # Check if should lockout
        if not success:
            failed_count = sum(1 for _, s in self._attempts[client_ip] if not s)
            if failed_count >= self.max_attempts:
                self._lockouts[client_ip] = now + timedelta(seconds=self.lockout_seconds)

    def is_locked_out(self, client_ip: str) -> bool:
        """Check if client is currently locked out."""
        if client_ip not in self._lockouts:
            return False
        
        lockout_until = self._lockouts[client_ip]
        if datetime.now() < lockout_until:
            return True
        
        # Lockout expired
        del self._lockouts[client_ip]
        self._attempts[client_ip] = []
        return False

    def get_lockout_remaining(self, client_ip: str) -> int:
        """Get remaining lockout time in seconds."""
        if client_ip not in self._lockouts:
            return 0
        
        lockout_until = self._lockouts[client_ip]
        remaining = (lockout_until - datetime.now()).total_seconds()
        return max(0, int(remaining))

    def get_attempts_remaining(self, client_ip: str) -> int:
        """Get number of attempts remaining before lockout."""
        if self.is_locked_out(client_ip):
            return 0
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Count recent failed attempts
        failed_count = sum(
            1 for ts, success in self._attempts.get(client_ip, [])
            if not success and ts > cutoff
        )
        
        return max(0, self.max_attempts - failed_count)


# Global rate limiter instance
token_rate_limiter = TokenRateLimiter(
    max_attempts=5,  # 5 failed attempts
    window_seconds=60,  # within 60 seconds
    lockout_seconds=300,  # results in 5 minute lockout
)

