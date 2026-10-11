"""Persistent SQLite storage for PotWise's saved pots."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from database.db import DEFAULT_DATABASE_PATH, connection


@contextmanager
def _connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    with connection(database_path) as db_connection:
        db_connection.execute(
            """
            CREATE TABLE IF NOT EXISTS my_pots (
                plant_id TEXT PRIMARY KEY,
                plant_name TEXT NOT NULL,
                scientific_name TEXT,
                pot_volume_litres REAL
            )
            """
        )
        db_connection.commit()
        yield db_connection


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
    """Compatibility wrapper for the previous assistant storage API."""

    from core.chat_history import get_or_create_conversation as _get_or_create

    return _get_or_create(plant_id, database_path=database_path)


def save_conversation_message(
    conversation_id: str,
    role: str,
    message_text: str,
    input_method: str,
    *,
    database_path: str | Path | None = None,
) -> None:
    """Compatibility wrapper for the previous assistant storage API."""

    from core.chat_history import save_message

    save_message(
        conversation_id,
        role,
        message_text,
        input_method=input_method,
        database_path=database_path,
    )


def load_conversation_messages(
    conversation_id: str, *, database_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Compatibility wrapper returning the previous message field names."""

    from core.chat_history import get_conversation_messages

    return [
        {
            "message_id": message["id"],
            "conversation_id": message["conversation_id"],
            "timestamp": message["created_at"],
            "role": message["role"],
            "message_text": message["content"],
            "input_method": message["input_method"],
        }
        for message in get_conversation_messages(
            conversation_id,
            database_path=database_path,
        )
    ]
