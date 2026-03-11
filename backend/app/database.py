"""SQLite job persistence layer — records job lifecycle, analytics, and email status."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any


_DB_PATH: str = "jobs.db"
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str | None = None) -> None:
    """Create the jobs table if it does not exist."""
    global _DB_PATH
    if db_path is not None:
        _DB_PATH = db_path
    with _lock, sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'pending',
                filename TEXT,
                to_email TEXT,
                subject TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                rows_processed INTEGER,
                analytics_json TEXT,
                llm_summary TEXT,
                llm_provider_used TEXT,
                llm_latency_ms REAL,
                email_status TEXT,
                email_id TEXT,
                error TEXT,
                chart_paths TEXT
            )
        """)
        conn.commit()


def create_job(
    job_id: str,
    filename: str,
    to_email: str,
    subject: str,
) -> dict[str, Any]:
    """Insert a new pending job record."""
    now = _now_iso()
    record = {
        "id": job_id,
        "status": "pending",
        "filename": filename,
        "to_email": to_email,
        "subject": subject,
        "created_at": now,
        "updated_at": now,
    }
    with _lock, sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO jobs (id, status, filename, to_email, subject, created_at, updated_at)
               VALUES (:id, :status, :filename, :to_email, :subject, :created_at, :updated_at)""",
            record,
        )
        conn.commit()
    return record


def update_job(job_id: str, **fields: Any) -> None:
    """Update arbitrary fields on a job record."""
    fields["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with _lock, sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE id = ?",  # noqa: S608 — keys are hardcoded
            values,
        )
        conn.commit()


def get_job(job_id: str) -> dict[str, Any] | None:
    """Fetch a single job by ID. Returns None if not found."""
    with _lock, sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    # Deserialize JSON fields
    if result.get("analytics_json"):
        result["analytics"] = json.loads(result["analytics_json"])
    else:
        result["analytics"] = None
    if result.get("chart_paths"):
        result["chart_paths"] = json.loads(result["chart_paths"])
    return result
