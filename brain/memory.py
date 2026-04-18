"""SQLite-backed memory for the agent.

Two simple layers:

* ``remember(key, value)`` / ``recall(key)`` — key-value facts ("user's name",
  "last battery voltage", "preferred dance routine").
* ``log_episode(summary, tags)`` / ``recent_episodes(n)`` — episodic log of
  what the robot did. Useful for the agent to plan coherently over time
  ("last time you walked you said the floor was slippery — still true?").

Persistence is per-database-file; default lives in ``~/.phonewalker/memory.db``
but tests use an in-memory `":memory:"` database.

Deliberately not a vector store. For a 4-servo robot with a handful of
recurring concepts, key-value + episode log is enough. If we ever hit real
recall limits we bolt on sqlite-vss or chroma behind the same interface.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DB = Path.home() / ".phonewalker" / "memory.db"


@dataclass
class Episode:
    id: int
    ts_ms: int
    summary: str
    tags: list[str]


class Memory:
    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_ms INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_episodes_ts ON episodes(ts_ms DESC);
                """
            )

    # ------------------------------------------------------------ facts

    def remember(self, key: str, value: Any) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO facts(key, value, updated_ms) VALUES(?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
                "updated_ms=excluded.updated_ms",
                (key, json.dumps(value), _now_ms()),
            )

    def recall(self, key: str) -> Any | None:
        row = self._conn.execute(
            "SELECT value FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row["value"]) if row is not None else None

    def forget(self, key: str) -> bool:
        with self._conn:
            cur = self._conn.execute("DELETE FROM facts WHERE key = ?", (key,))
            return cur.rowcount > 0

    def all_facts(self) -> dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value FROM facts ORDER BY key"
        ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ---------------------------------------------------------- episodes

    def log_episode(self, summary: str, tags: Iterable[str] | None = None) -> int:
        tags_list = list(tags or [])
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO episodes(ts_ms, summary, tags) VALUES(?, ?, ?)",
                (_now_ms(), summary, json.dumps(tags_list)),
            )
            return int(cur.lastrowid)

    def recent_episodes(self, n: int = 10) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT id, ts_ms, summary, tags FROM episodes "
            "ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            Episode(
                id=r["id"],
                ts_ms=r["ts_ms"],
                summary=r["summary"],
                tags=json.loads(r["tags"]),
            )
            for r in rows
        ]

    def search_episodes(self, query: str, n: int = 10) -> list[Episode]:
        """Naive substring search — sufficient for small histories."""
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = self._conn.execute(
            "SELECT id, ts_ms, summary, tags FROM episodes "
            "WHERE summary LIKE ? ESCAPE '\\' ORDER BY id DESC LIMIT ?",
            (f"%{escaped}%", n),
        ).fetchall()
        return [
            Episode(r["id"], r["ts_ms"], r["summary"], json.loads(r["tags"]))
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()


def _now_ms() -> int:
    return int(time.time() * 1000)
