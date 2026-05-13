"""
SQLite persistence for Automated Farmer.
Stores player scripts and level-completion progress.
"""

import sqlite3
import os
from datetime import datetime, timezone

_DB_PATH     = os.path.join(os.path.dirname(__file__), "game_data.db")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't already exist."""
    with open(_SCHEMA_PATH) as f:
        schema = f.read()
    with _connect() as conn:
        conn.executescript(schema)


def save_script(username: str, level_id: int, code: str) -> None:
    """Persist the code the player just submitted."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO scripts (username, level_id, code) VALUES (?, ?, ?)",
            (username, level_id, code),
        )


def record_attempt(username: str, level_id: int) -> None:
    """Increment the attempt counter for this user/level pair."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO progress (username, level_id, attempts)
            VALUES (?, ?, 1)
            ON CONFLICT (username, level_id) DO UPDATE SET attempts = attempts + 1
            """,
            (username, level_id),
        )


def record_completion(username: str, level_id: int, elapsed: float) -> None:
    """Mark the level complete and update best time if this run was faster."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO progress (username, level_id, attempts, completed, best_time, completed_at)
            VALUES (?, ?, 0, 1, ?, ?)
            ON CONFLICT (username, level_id) DO UPDATE SET
                completed    = 1,
                best_time    = CASE
                                   WHEN best_time IS NULL OR ? < best_time THEN ?
                                   ELSE best_time
                               END,
                completed_at = COALESCE(completed_at, ?)
            """,
            (username, level_id, elapsed, now, elapsed, elapsed, now),
        )


def get_last_script(username: str, level_id: int) -> str | None:
    """Return the most recently saved script for this user/level, or None."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT code FROM scripts
            WHERE username = ? AND level_id = ?
            ORDER BY saved_at DESC
            LIMIT 1
            """,
            (username, level_id),
        ).fetchone()
    return row[0] if row else None


def get_progress(username: str) -> list[dict]:
    """Return all progress rows for a user (used for analytics / display)."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT level_id, attempts, completed, best_time, completed_at
            FROM progress
            WHERE username = ?
            ORDER BY level_id
            """,
            (username,),
        ).fetchall()
    return [
        {
            "level_id":     r[0],
            "attempts":     r[1],
            "completed":    bool(r[2]),
            "best_time":    r[3],
            "completed_at": r[4],
        }
        for r in rows
    ]
