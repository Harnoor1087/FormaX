import json
import os
import time
from datetime import datetime, timezone
from collections import deque
from threading import Lock
from typing import List, Dict, Any, Optional
from ..config import settings

class SecurityAuditLogger:
    """
    Audit Log & Access-Controlled Storage Layer (Synopsis Section 4 & 5).
    Maintains forensic traceability without logging credentials or raw secrets.
    """

    def __init__(self, log_file: Optional[str] = None, max_memory_entries: int = 200):
        self.log_file = log_file or settings.AUDIT_LOG_FILE
        self.max_memory_entries = max_memory_entries
        self._memory_ring = deque(maxlen=max_memory_entries)
        self._lock = Lock()
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        try:
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass

    def log_event(
        self,
        request_id: str,
        client_ip: str,
        decision: str,
        risk_score: float,
        detected_signals: List[str],
        reason_code: str,
        output_types: List[str],
        source_length: int,
        sensitive_flags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Records a structured security event.
        Guarantees that no raw secret tokens or API keys are stored.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "client_ip": client_ip,
            "decision": decision,
            "risk_score": round(risk_score, 2),
            "detected_signals": detected_signals,
            "sensitive_flags": sensitive_flags or [],
            "reason_code": reason_code,
            "output_types": output_types,
            "source_length": source_length,
        }

        with self._lock:
            # 1. Append to in-memory circular ring buffer
            self._memory_ring.append(event)

            # 2. Persist to disk (JSONL format)
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception:
                # Disk write errors should not crash the request pipeline
                pass

        return event

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent audit events for authorized operator review."""
        with self._lock:
            entries = list(self._memory_ring)
        return entries[-limit:]

    def clear(self):
        """Clears audit logs (for test isolation)."""
        with self._lock:
            self._memory_ring.clear()
            if os.path.exists(self.log_file):
                try:
                    os.remove(self.log_file)
                except Exception:
                    pass

audit_logger = SecurityAuditLogger()
