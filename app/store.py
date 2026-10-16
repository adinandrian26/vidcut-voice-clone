"""Penyimpanan job di SQLite (antrean sederhana, tanpa Redis)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    stage_detail TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    warning TEXT NOT NULL DEFAULT '',
    params TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


class JobStore:
    """Thread-safe. Status: queued, downloading, separating, cloning,
    done, failed."""

    def __init__(self, db_path: Path) -> None:
        self._db = str(db_path)
        self._lock = threading.Lock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db) as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self._db, timeout=10.0)
        # WAL + busy timeout: dua proses (api & worker di docker-compose)
        # boleh membaca/menulis DB yang sama tanpa "database is locked".
        try:
            c.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("PRAGMA busy_timeout=10000")
        except sqlite3.OperationalError:
            pass
        return c

    def create(self, params: dict[str, Any]) -> str:
        jid = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO jobs (id, status, params, created_at, updated_at)"
                " VALUES (?, 'queued', ?, ?, ?)",
                (jid, json.dumps(params), now, now),
            )
        return jid

    def update(self, jid: str, status: Optional[str] = None,
               progress: Optional[int] = None,
               stage_detail: Optional[str] = None,
               error: Optional[str] = None,
               warning: Optional[str] = None) -> None:
        sets, vals = ["updated_at = ?"], [time.time()]
        if status is not None:
            sets.append("status = ?")
            vals.append(status)
        if progress is not None:
            sets.append("progress = ?")
            vals.append(max(0, min(100, progress)))
        if stage_detail is not None:
            sets.append("stage_detail = ?")
            vals.append(stage_detail)
        if error is not None:
            sets.append("error = ?")
            vals.append(error)
        if warning is not None:
            sets.append("warning = ?")
            vals.append(warning)
        vals.append(jid)
        with self._lock, self._conn() as c:
            c.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", vals)

    def get(self, jid: str) -> Optional[dict[str, Any]]:
        with self._lock, self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["params"] = json.loads(d["params"] or "{}")
        return d

    def next_queued(self) -> Optional[dict[str, Any]]:
        """Ambil satu job queued dan tandai downloading secara atomik.

        Aman untuk banyak worker sekaligus (thread maupun proses terpisah,
        mis. replika api+worker di docker-compose): klaim memakai
        BEGIN IMMEDIATE + UPDATE bersyarat, jadi hanya satu worker
        yang memenangkan tiap job.
        """
        with self._lock, self._conn() as c:
            c.row_factory = sqlite3.Row
            try:
                c.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                return None
            row = c.execute(
                "SELECT * FROM jobs WHERE status = 'queued'"
                " ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            cur = c.execute(
                "UPDATE jobs SET status = 'downloading', updated_at = ?"
                " WHERE id = ? AND status = 'queued'",
                (time.time(), row["id"]))
            if cur.rowcount == 0:
                return None  # kalah lomba dengan worker lain
            return dict(row)

    def delete(self, jid: str) -> bool:
        with self._lock, self._conn() as c:
            cur = c.execute("DELETE FROM jobs WHERE id = ?", (jid,))
            return cur.rowcount > 0

    def old_jobs(self, older_than_seconds: float) -> list[str]:
        cutoff = time.time() - older_than_seconds
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT id FROM jobs WHERE created_at < ?", (cutoff,)).fetchall()
        return [r[0] for r in rows]
