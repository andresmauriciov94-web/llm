"""Persistencia del historial de conversacion (patron Repository).

Aisla toda la logica de acceso a datos detras de una interfaz simple. El resto
del sistema guarda y lee mensajes sin conocer SQLite; migrar a Postgres/Redis
seria reimplementar esta clase, sin tocar el pipeline ni la API.

La base es SQLite (un archivo), suficiente para un solo nodo y, sobre todo,
consultable con SQL para la analitica del historico.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT NOT NULL,
    role              TEXT NOT NULL,
    content           TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    latency_ms        INTEGER,
    retrieved_ids     TEXT,
    model             TEXT,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            # Migracion suave: agrega columnas de tokens si la BD es antigua.
            existing = {r["name"] for r in conn.execute("PRAGMA table_info(messages)")}
            for col in ("prompt_tokens", "completion_tokens"):
                if col not in existing:
                    conn.execute(
                        f"ALTER TABLE messages ADD COLUMN {col} INTEGER DEFAULT 0"
                    )

    # -- escritura ---------------------------------------------------------
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        latency_ms: int | None = None,
        retrieved_ids: list[str] | None = None,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO messages
                   (session_id, role, content, created_at, latency_ms,
                    retrieved_ids, model, prompt_tokens, completion_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    role,
                    content,
                    _now(),
                    latency_ms,
                    json.dumps(retrieved_ids or []),
                    model,
                    prompt_tokens,
                    completion_tokens,
                ),
            )
            return int(cursor.lastrowid)

    # -- lectura -----------------------------------------------------------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        data = dict(row)
        data["retrieved_ids"] = json.loads(data.get("retrieved_ids") or "[]")
        return data

    def get_last_messages(self, session_id: str, n: int) -> list[dict]:
        """Ultimos N mensajes de la sesion, en orden cronologico (viejo -> nuevo)."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE session_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (session_id, n),
            ).fetchall()
        return [self._row_to_dict(r) for r in reversed(rows)]

    def get_session(self, session_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_sessions(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT session_id FROM messages ORDER BY session_id"
            ).fetchall()
        return [r["session_id"] for r in rows]

    def all_messages(self) -> list[dict]:
        """Todo el historico (para la analitica)."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM messages ORDER BY id ASC").fetchall()
        return [self._row_to_dict(r) for r in rows]