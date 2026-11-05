"""Durable storage of analyses (jobs + results) in SQLite.

On Render, ``GEOIA_DB_PATH`` must point to a persistent disk mount
(e.g. ``/var/data/geoia.sqlite3``); the container filesystem is ephemeral.
PDF reports are rendered on demand from the stored JSON, so no binary files
need to be kept.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    planet TEXT NOT NULL,
    request_key TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_analyses_key ON analyses(request_key, status, created_at);
"""


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or get_settings().db_path
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL") if self.path != ":memory:" else None
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def ping(self) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1").fetchone() == (1,)

    def save(self, analysis_id: str, planet: str, request_key: str, status: str, result: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO analyses(id, planet, request_key, status, created_at, updated_at, result_json) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
                "updated_at=excluded.updated_at, result_json=excluded.result_json",
                (analysis_id, planet, request_key, status, result.get("created_at") or now, now,
                 json.dumps(result, default=str)))
            self._conn.commit()

    def get(self, analysis_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT result_json FROM analyses WHERE id=?", (analysis_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def find_recent(self, request_key: str, ttl_s: int) -> dict | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ttl_s)).isoformat()
        with self._lock:
            row = self._conn.execute(
                "SELECT result_json FROM analyses WHERE request_key=? AND status='completed' AND updated_at>=? "
                "ORDER BY updated_at DESC LIMIT 1", (request_key, cutoff)).fetchone()
        return json.loads(row[0]) if row else None

    def mark_interrupted(self) -> int:
        """Jobs left 'processing' by a previous process cannot resume."""
        with self._lock:
            rows = self._conn.execute("SELECT id, result_json FROM analyses WHERE status='processing'").fetchall()
            for rid, js in rows:
                doc = json.loads(js)
                doc["status"] = "failed"
                doc.setdefault("problems", []).append({"section": "job", "reason": "provider_error",
                                                       "message": "interrupted by a server restart; resubmit",
                                                       "source_id": None})
                self._conn.execute("UPDATE analyses SET status='failed', result_json=? WHERE id=?",
                                   (json.dumps(doc, default=str), rid))
            self._conn.commit()
        return len(rows)


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def set_store(store: Store | None) -> None:
    global _store
    _store = store
