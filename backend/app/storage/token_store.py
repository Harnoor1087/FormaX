import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TokenStore:
    """
    Manages API tokens with database persistence.
    Supports token generation, revocation, expiration, and audit trail.
    """

    def __init__(self, database_path: Optional[str] = None):
        self.database_path = Path(database_path or settings.DATABASE_PATH)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS api_tokens (
                    token_id TEXT PRIMARY KEY,
                    token_value TEXT NOT NULL UNIQUE,
                    token_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('operator', 'reviewer')),
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    metadata_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS token_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id TEXT NOT NULL REFERENCES api_tokens(token_id) ON DELETE CASCADE,
                    endpoint TEXT NOT NULL,
                    client_ip TEXT,
                    used_at TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_tokens_active
                    ON api_tokens(is_active, expires_at);
                    
                CREATE INDEX IF NOT EXISTS idx_token_value
                    ON api_tokens(token_value) WHERE is_active = 1;
                    
                CREATE INDEX IF NOT EXISTS idx_token_usage_token
                    ON token_usage_log(token_id, used_at DESC);
                """
            )

    def generate_token(
        self,
        token_name: str,
        role: str,
        created_by: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a new API token with the specified parameters."""
        if role not in ("operator", "reviewer"):
            raise ValueError(f"Invalid role: {role}. Must be 'operator' or 'reviewer'.")

        token_id = str(uuid.uuid4())
        token_value = f"ftx_{secrets.token_urlsafe(32)}"
        created_at = _utc_now()
        expires_at = None

        if expires_in_days:
            expiry = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            expires_at = expiry.isoformat()

        with self._connect() as connection:
            connection.execute(
                """INSERT INTO api_tokens
                   (token_id, token_value, token_name, role, created_by, created_at, expires_at, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    token_id,
                    token_value,
                    token_name,
                    role,
                    created_by,
                    created_at,
                    expires_at,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

        return {
            "token_id": token_id,
            "token_value": token_value,
            "token_name": token_name,
            "role": role,
            "created_at": created_at,
            "expires_at": expires_at,
        }

    def validate_token(self, token_value: str) -> Optional[Dict[str, Any]]:
        """Validate a token and return its details if valid."""
        with self._connect() as connection:
            row = connection.execute(
                """SELECT token_id, token_name, role, created_at, expires_at, last_used_at, metadata_json
                   FROM api_tokens
                   WHERE token_value = ? AND is_active = 1""",
                (token_value,),
            ).fetchone()

            if row is None:
                return None

            # Check expiration
            if row["expires_at"]:
                try:
                    expires = datetime.fromisoformat(row["expires_at"])
                    if datetime.now(timezone.utc) > expires:
                        # Auto-revoke expired token
                        self.revoke_token(row["token_id"])
                        return None
                except (ValueError, TypeError):
                    # Invalid expiration date - log and continue
                    return None

            return {
                "token_id": row["token_id"],
                "token_name": row["token_name"],
                "role": row["role"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "last_used_at": row["last_used_at"],
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            }

    def record_token_usage(
        self,
        token_id: str,
        endpoint: str,
        client_ip: Optional[str] = None,
    ) -> None:
        """Record token usage for audit purposes."""
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO token_usage_log (token_id, endpoint, client_ip, used_at)
                   VALUES (?, ?, ?, ?)""",
                (token_id, endpoint, client_ip, now),
            )
            connection.execute(
                "UPDATE api_tokens SET last_used_at = ? WHERE token_id = ?",
                (now, token_id),
            )

    def list_tokens(
        self,
        include_inactive: bool = False,
        role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all tokens with optional filtering."""
        query = "SELECT * FROM api_tokens WHERE 1=1"
        params = []

        if not include_inactive:
            query += " AND is_active = 1"

        if role:
            query += " AND role = ?"
            params.append(role)

        query += " ORDER BY created_at DESC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return [
            {
                "token_id": row["token_id"],
                "token_name": row["token_name"],
                "role": row["role"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "last_used_at": row["last_used_at"],
                "is_active": bool(row["is_active"]),
                "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            }
            for row in rows
        ]

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get token details by ID (without exposing token_value)."""
        with self._connect() as connection:
            row = connection.execute(
                """SELECT token_id, token_name, role, created_by, created_at, expires_at, 
                          last_used_at, is_active, metadata_json
                   FROM api_tokens WHERE token_id = ?""",
                (token_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "token_id": row["token_id"],
            "token_name": row["token_name"],
            "role": row["role"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "last_used_at": row["last_used_at"],
            "is_active": bool(row["is_active"]),
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        }

    def revoke_token(self, token_id: str) -> bool:
        """Revoke (deactivate) a token."""
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE api_tokens SET is_active = 0 WHERE token_id = ?",
                (token_id,),
            )
        return cursor.rowcount > 0

    def get_token_usage_stats(self, token_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get usage statistics for a specific token."""
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT endpoint, client_ip, used_at
                   FROM token_usage_log
                   WHERE token_id = ?
                   ORDER BY used_at DESC
                   LIMIT ?""",
                (token_id, limit),
            ).fetchall()

        return [
            {
                "endpoint": row["endpoint"],
                "client_ip": row["client_ip"],
                "used_at": row["used_at"],
            }
            for row in rows
        ]


token_store = TokenStore()

