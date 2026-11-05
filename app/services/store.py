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
    result_json TEXT NOT NULL,
    request_json TEXT
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
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(analyses)")}
        if "request_json" not in cols:  # databases created before job resumption existed
            self._conn.execute("ALTER TABLE analyses ADD COLUMN request_json TEXT")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def ping(self) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1").fetchone() == (1,)

    def save(self, analysis_id: str, planet: str, request_key: str, status: str, result: dict,
             request: dict | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO analyses(id, planet, request_key, status, created_at, updated_at, result_json, "
                "request_json) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
                "updated_at=excluded.updated_at, result_json=excluded.result_json, "
                "request_json=COALESCE(excluded.request_json, analyses.request_json)",
                (analysis_id, planet, request_key, status, result.get("created_at") or now, now,
                 json.dumps(result, default=str), json.dumps(request) if request is not None else None))
            self._conn.commit()

    def processing_jobs(self) -> list[dict]:
        """Jobs left 'processing' (e.g. by a restart), with their stored request."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, planet, request_key, created_at, request_json FROM analyses "
                "WHERE status='processing' ORDER BY created_at").fetchall()
        return [{"id": r[0], "planet": r[1], "request_key": r[2], "created_at": r[3],
                 "request": json.loads(r[4]) if r[4] else None} for r in rows]

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

    def mark_failed(self, ids: list[str], message: str) -> int:
        with self._lock:
            rows = [r for r in self._conn.execute("SELECT id, result_json FROM analyses WHERE status='processing'")
                    if r[0] in set(ids)]
            for rid, js in rows:
                doc = json.loads(js)
                doc["status"] = "failed"
                doc.setdefault("problems", []).append({"section": "job", "reason": "provider_error",
                                                       "message": message, "source_id": None})
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
