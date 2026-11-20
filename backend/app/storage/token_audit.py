"""Token audit logging for security monitoring."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from ..config import settings


class TokenAuditLogger:
    """Audit logger specifically for token operations."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize token audit logger."""
        self.log_file = Path(log_file or settings.AUDIT_LOG_PATH)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup Python logger
        self.logger = logging.getLogger("token_audit")
        self.logger.setLevel(logging.INFO)
        
        # File handler for audit trail
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Write audit event to log file."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **details,
        }
        self.logger.info(json.dumps(event, ensure_ascii=False))

    def log_token_created(
        self,
        token_id: str,
        token_name: str,
        role: str,
        created_by: Optional[str],
        expires_at: Optional[str],
    ) -> None:
        """Log token creation event."""
        self._log_event("token_created", {
            "token_id": token_id,
            "token_name": token_name,
            "role": role,
            "created_by": created_by,
            "expires_at": expires_at,
        })

    def log_token_revoked(
        self,
        token_id: str,
        token_name: str,
        revoked_by: Optional[str] = None,
    ) -> None:
        """Log token revocation event."""
        self._log_event("token_revoked", {
            "token_id": token_id,
            "token_name": token_name,
            "revoked_by": revoked_by,
        })

    def log_token_validation_failed(
        self,
        client_ip: str,
        reason: str,
    ) -> None:
        """Log failed token validation attempt."""
        self._log_event("token_validation_failed", {
            "client_ip": client_ip,
            "reason": reason,
        })

    def log_token_expired_auto_revoked(
        self,
        token_id: str,
        token_name: str,
    ) -> None:
        """Log automatic revocation of expired token."""
        self._log_event("token_expired_auto_revoked", {
            "token_id": token_id,
            "token_name": token_name,
        })

    def log_rate_limit_exceeded(
        self,
        client_ip: str,
        lockout_seconds: int,
    ) -> None:
        """Log rate limit violation."""
        self._log_event("rate_limit_exceeded", {
            "client_ip": client_ip,
            "lockout_seconds": lockout_seconds,
        })


# Global audit logger instance
token_audit_logger = TokenAuditLogger()

