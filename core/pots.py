"""Persistent SQLite storage for PotWise's saved pots."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "potwise.db"


@contextmanager
def _connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(database_path) if database_path is not None else DEFAULT_DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS my_pots (
                plant_id TEXT PRIMARY KEY,
                plant_name TEXT NOT NULL,
                scientific_name TEXT,
                pot_volume_litres REAL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                plant_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                message_text TEXT NOT NULL,
                input_method TEXT NOT NULL CHECK (input_method IN ('text', 'voice')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
            """
        )
        connection.commit()
        yield connection
    finally:
        connection.close()


def save_pot(
    plant_id: str,
    plant_name: str,
    scientific_name: str | None = None,
    pot_volume_litres: float | None = None,
    *,
    database_path: str | Path | None = None,
) -> bool:
    """Save one plant and its pot details, returning False for duplicates."""

    with _connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO my_pots
                (plant_id, plant_name, scientific_name, pot_volume_litres)
            VALUES (?, ?, ?, ?)
            """,
            (plant_id, plant_name, scientific_name, pot_volume_litres),
        )
        connection.commit()
        return cursor.rowcount == 1


def list_saved_pots(
    *, database_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Load all saved pots in insertion order."""

    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT plant_id, plant_name, scientific_name, pot_volume_litres
            FROM my_pots
            ORDER BY rowid
            """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_pot(plant_id: str, *, database_path: str | Path | None = None) -> bool:
    """Delete a saved pot by plant ID, returning whether a row was removed."""

    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM my_pots WHERE plant_id = ?", (plant_id,))
        connection.commit()
        return cursor.rowcount == 1


def get_or_create_conversation(
    plant_id: str, *, database_path: str | Path | None = None
) -> str:
    """Return the one anonymous assistant conversation for a saved plant."""

    with _connection(database_path) as connection:
        row = connection.execute(
            "SELECT conversation_id FROM conversations WHERE plant_id = ?",
            (plant_id,),
        ).fetchone()
        if row is not None:
            return str(row["conversation_id"])

        conversation_id = uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            INSERT INTO conversations (conversation_id, plant_id, created_at)
            VALUES (?, ?, ?)
            """,
            (conversation_id, plant_id, created_at),
        )
        connection.commit()
        return conversation_id


def save_conversation_message(
    conversation_id: str,
    role: str,
    message_text: str,
    input_method: str,
    *,
    database_path: str | Path | None = None,
) -> None:
    """Persist one user or assistant message for a conversation."""

    timestamp = datetime.now(timezone.utc).isoformat()
    with _connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO conversation_messages
                (conversation_id, timestamp, role, message_text, input_method)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, timestamp, role, message_text, input_method),
        )
        connection.commit()


def load_conversation_messages(
    conversation_id: str, *, database_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Load conversation messages in their original order."""

    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT message_id, conversation_id, timestamp, role, message_text, input_method
            FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY message_id
            """,
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]
