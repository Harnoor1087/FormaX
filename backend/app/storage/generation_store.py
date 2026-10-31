import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem, OutputValidation
from ..config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GenerationStore:
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
                CREATE TABLE IF NOT EXISTS generations (
                    id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    generation_mode TEXT NOT NULL DEFAULT 'template'
                );
                CREATE TABLE IF NOT EXISTS generation_outputs (
                    id TEXT PRIMARY KEY,
                    generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
                    output_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_points_json TEXT NOT NULL,
                    body TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    generation_mode TEXT,
                    review_status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    export_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS generation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
                    output_id TEXT REFERENCES generation_outputs(id) ON DELETE SET NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS video_jobs (
                    id TEXT PRIMARY KEY,
                    output_id TEXT NOT NULL REFERENCES generation_outputs(id) ON DELETE CASCADE,
                    output_updated_at TEXT NOT NULL,
                    operation_name TEXT,
                    status TEXT NOT NULL CHECK (
                        status IN ('starting', 'processing', 'downloading', 'completed', 'failed', 'stale')
                    ),
                    file_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_generations_created_at
                    ON generations(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_generation_outputs_generation
                    ON generation_outputs(generation_id);
                CREATE INDEX IF NOT EXISTS idx_video_jobs_output
                    ON video_jobs(output_id, created_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_video_jobs_active_output
                    ON video_jobs(output_id)
                    WHERE status IN ('starting', 'processing', 'downloading', 'completed');
                """
            )
            generation_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(generations)")
            }
            if "generation_mode" not in generation_columns:
                connection.execute(
                    "ALTER TABLE generations ADD COLUMN generation_mode TEXT NOT NULL DEFAULT 'template'"
                )
            output_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(generation_outputs)")
            }
            if "generation_mode" not in output_columns:
                connection.execute(
                    "ALTER TABLE generation_outputs ADD COLUMN generation_mode TEXT"
                )
            connection.execute(
                """UPDATE video_jobs SET status = 'failed',
                   error = 'The server restarted before video generation was submitted.',
                   updated_at = ? WHERE status = 'starting'""",
                (_utc_now(),),
            )
            connection.execute(
                """UPDATE video_jobs SET status = 'processing', updated_at = ?
                   WHERE status = 'downloading'""",
                (_utc_now(),),
            )

    @staticmethod
    def _decode_output(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "output_id": row["id"],
            "generation_id": row["generation_id"],
            "output_type": row["output_type"],
            "title": row["title"],
            "summary": row["summary"],
            "key_points": json.loads(row["key_points_json"]),
            "body": row["body"],
            "generation_mode": row["generation_mode"],
            "validation": json.loads(row["validation_json"]),
            "review_status": row["review_status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "approved_at": row["approved_at"],
            "export_count": row["export_count"],
        }

    def create_generation(
        self,
        request_id: str,
        context: StructuredContext,
        validation: OutputValidation,
        outputs: Sequence[GenerateOutputItem],
        generation_mode: str = "template",
    ) -> tuple[str, List[GenerateOutputItem]]:
        generation_id = str(uuid.uuid4())
        created_at = _utc_now()
        saved_outputs: List[GenerateOutputItem] = []

        with self._connect() as connection:
            connection.execute(
                """INSERT INTO generations
                   (id, request_id, created_at, source_text, context_json, validation_json, generation_mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    generation_id,
                    request_id,
                    created_at,
                    context.source_text,
                    context.model_dump_json(),
                    validation.model_dump_json(),
                    generation_mode,
                ),
            )
            for output in outputs:
                output_id = str(uuid.uuid4())
                item = output.model_copy(update={"output_id": output_id, "review_status": "draft"})
                connection.execute(
                    """INSERT INTO generation_outputs
                       (id, generation_id, output_type, title, summary, key_points_json, body,
                        validation_json, generation_mode, review_status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
                    (
                        output_id,
                        generation_id,
                        item.output_type,
                        item.title,
                        item.summary,
                        json.dumps(item.key_points, ensure_ascii=False),
                        item.body,
                        item.validation.model_dump_json() if item.validation else "{}",
                        item.generation_mode or generation_mode,
                        created_at,
                        created_at,
                    ),
                )
                saved_outputs.append(item)
            connection.execute(
                "INSERT INTO generation_events (generation_id, action, created_at) VALUES (?, ?, ?)",
                (generation_id, "generated", created_at),
            )

        return generation_id, saved_outputs

    def list_generations(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT g.id, g.request_id, g.created_at, g.validation_json, g.generation_mode,
                          COUNT(o.id) AS output_count,
                          SUM(CASE WHEN o.review_status = 'approved' THEN 1 ELSE 0 END) AS approved_count
                   FROM generations g
                   LEFT JOIN generation_outputs o ON o.generation_id = g.id
                   GROUP BY g.id
                   ORDER BY g.created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [
            {
                "generation_id": row["id"],
                "request_id": row["request_id"],
                "created_at": row["created_at"],
                "validation": json.loads(row["validation_json"]),
                "generation_mode": row["generation_mode"],
                "output_count": row["output_count"],
                "approved_count": row["approved_count"] or 0,
            }
            for row in rows
        ]

    def get_generation(self, generation_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            generation = connection.execute(
                "SELECT * FROM generations WHERE id = ?", (generation_id,)
            ).fetchone()
            if generation is None:
                return None
            output_rows = connection.execute(
                "SELECT * FROM generation_outputs WHERE generation_id = ? ORDER BY created_at, id",
                (generation_id,),
            ).fetchall()
            event_rows = connection.execute(
                """SELECT output_id, action, created_at FROM generation_events
                   WHERE generation_id = ? ORDER BY id""",
                (generation_id,),
            ).fetchall()
        return {
            "generation_id": generation["id"],
            "request_id": generation["request_id"],
            "created_at": generation["created_at"],
            "source_text": generation["source_text"],
            "context": json.loads(generation["context_json"]),
            "validation": json.loads(generation["validation_json"]),
            "generation_mode": generation["generation_mode"],
            "outputs": [self._decode_output(row) for row in output_rows],
            "events": [
                {"output_id": row["output_id"], "action": row["action"], "created_at": row["created_at"]}
                for row in event_rows
            ],
        }

    def get_output(self, output_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_outputs WHERE id = ?", (output_id,)
            ).fetchone()
        return self._decode_output(row) if row else None

    def update_output(
        self,
        output_id: str,
        output: GenerateOutputItem,
        validation: OutputValidation,
    ) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT generation_id FROM generation_outputs WHERE id = ?", (output_id,)
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """UPDATE generation_outputs
                   SET title = ?, summary = ?, key_points_json = ?, body = ?,
                       validation_json = ?, review_status = 'draft', approved_at = NULL,
                       updated_at = ?
                   WHERE id = ?""",
                (
                    output.title,
                    output.summary,
                    json.dumps(output.key_points, ensure_ascii=False),
                    output.body,
                    validation.model_dump_json(),
                    now,
                    output_id,
                ),
            )
            connection.execute(
                """UPDATE video_jobs SET status = 'stale',
                   error = 'The approved video brief changed; approve it again before rendering.',
                   updated_at = ?
                   WHERE output_id = ? AND status IN ('starting', 'processing', 'downloading', 'completed')""",
                (now, output_id),
            )
            connection.execute(
                """INSERT INTO generation_events
                   (generation_id, output_id, action, created_at) VALUES (?, ?, 'edited', ?)""",
                (row["generation_id"], output_id, now),
            )
        return self.get_output(output_id)

    def approve_output(self, output_id: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT generation_id FROM generation_outputs WHERE id = ?", (output_id,)
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """UPDATE generation_outputs
                   SET review_status = 'approved', approved_at = ?, updated_at = ?
                   WHERE id = ?""",
                (now, now, output_id),
            )
            connection.execute(
                """INSERT INTO generation_events
                   (generation_id, output_id, action, created_at) VALUES (?, ?, 'approved', ?)""",
                (row["generation_id"], output_id, now),
            )
        return self.get_output(output_id)

    def record_export(self, output_id: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT generation_id FROM generation_outputs WHERE id = ? AND review_status = 'approved'",
                (output_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """UPDATE generation_outputs
                   SET export_count = export_count + 1, updated_at = ? WHERE id = ?""",
                (now, output_id),
            )
            connection.execute(
                """INSERT INTO generation_events
                   (generation_id, output_id, action, created_at) VALUES (?, ?, 'exported', ?)""",
                (row["generation_id"], output_id, now),
            )
        return self.get_output(output_id)

    @staticmethod
    def _decode_video_job(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "video_job_id": row["id"],
            "output_id": row["output_id"],
            "output_updated_at": row["output_updated_at"],
            "operation_name": row["operation_name"],
            "status": row["status"],
            "file_path": row["file_path"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_video_job(self, output_id: str, output_updated_at: str) -> Dict[str, Any]:
        video_job_id = str(uuid.uuid4())
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO video_jobs
                   (id, output_id, output_updated_at, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'starting', ?, ?)""",
                (video_job_id, output_id, output_updated_at, now, now),
            )
            row = connection.execute(
                "SELECT * FROM video_jobs WHERE id = ?", (video_job_id,)
            ).fetchone()
        return self._decode_video_job(row)

    def get_video_job(self, video_job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM video_jobs WHERE id = ?", (video_job_id,)
            ).fetchone()
        return self._decode_video_job(row) if row else None

    def get_video_job_for_output(self, output_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM video_jobs WHERE output_id = ?
                   ORDER BY created_at DESC, id DESC LIMIT 1""",
                (output_id,),
            ).fetchone()
        return self._decode_video_job(row) if row else None

    def submit_video_job(self, video_job_id: str, operation_name: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """UPDATE video_jobs SET status = 'processing', operation_name = ?,
                   updated_at = ? WHERE id = ? AND status = 'starting'""",
                (operation_name, now, video_job_id),
            )
        return self.get_video_job(video_job_id)

    def fail_video_job(self, video_job_id: str, error: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """UPDATE video_jobs SET status = 'failed', error = ?, updated_at = ?
                   WHERE id = ? AND status IN ('starting', 'processing', 'downloading')""",
                (error, now, video_job_id),
            )
        return self.get_video_job(video_job_id)

    def claim_video_download(self, video_job_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE video_jobs SET status = 'downloading', updated_at = ?
                   WHERE id = ? AND status = 'processing'""",
                (_utc_now(), video_job_id),
            )
        return cursor.rowcount == 1

    def complete_video_job(self, video_job_id: str, file_path: str) -> Optional[Dict[str, Any]]:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT output_id FROM video_jobs
                   WHERE id = ? AND status = 'downloading'""",
                (video_job_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """UPDATE video_jobs SET status = 'completed', file_path = ?, error = NULL,
                   updated_at = ? WHERE id = ?""",
                (file_path, now, video_job_id),
            )
            output = connection.execute(
                "SELECT generation_id FROM generation_outputs WHERE id = ?",
                (row["output_id"],),
            ).fetchone()
            if output is not None:
                connection.execute(
                    """INSERT INTO generation_events
                       (generation_id, output_id, action, created_at)
                       VALUES (?, ?, 'video_generated', ?)""",
                    (output["generation_id"], row["output_id"], now),
                )
        return self.get_video_job(video_job_id)

    def record_video_event(self, output_id: str, action: str) -> None:
        now = _utc_now()
        with self._connect() as connection:
            output = connection.execute(
                "SELECT generation_id FROM generation_outputs WHERE id = ?",
                (output_id,),
            ).fetchone()
            if output is not None:
                connection.execute(
                    """INSERT INTO generation_events
                       (generation_id, output_id, action, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (output["generation_id"], output_id, action, now),
                )


generation_store = GenerationStore()
