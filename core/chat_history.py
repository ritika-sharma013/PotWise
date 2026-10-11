"""Persistent local conversation history for PlantWise Assistant chats."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from database.db import DEFAULT_DATABASE_PATH, connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connection(database_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    with connection(database_path) as db_connection:
        _ensure_schema(db_connection)
        yield db_connection


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _create_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            plant_id TEXT,
            plant_name TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            input_method TEXT NOT NULL DEFAULT 'text',
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """
    )


def _migrate_legacy_schema(connection: sqlite3.Connection) -> None:
    legacy_messages = "conversation_messages"
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("ALTER TABLE conversations RENAME TO legacy_conversations")
    if _columns(connection, legacy_messages):
        connection.execute(
            "ALTER TABLE conversation_messages RENAME TO legacy_conversation_messages"
        )
    _create_tables(connection)

    legacy_rows = connection.execute(
        """
        SELECT conversation_id, plant_id, created_at
        FROM legacy_conversations
        """
    ).fetchall()
    for row in legacy_rows:
        created_at = str(row["created_at"])
        plant_id = row["plant_id"]
        plant_name = plant_id or "PlantWise Chat"
        title = f"🌱 {plant_name}"
        connection.execute(
            """
            INSERT OR IGNORE INTO conversations
                (id, title, plant_id, plant_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row["conversation_id"], title, plant_id, plant_name, created_at, created_at),
        )

    if _columns(connection, "legacy_conversation_messages"):
        message_rows = connection.execute(
            """
            SELECT conversation_id, role, message_text, timestamp, input_method
            FROM legacy_conversation_messages
            ORDER BY message_id
            """
        ).fetchall()
        for row in message_rows:
            connection.execute(
                """
                INSERT INTO messages
                    (conversation_id, role, content, created_at, input_method)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["conversation_id"],
                    row["role"],
                    row["message_text"],
                    row["timestamp"],
                    row["input_method"],
                ),
            )
    connection.execute("DROP TABLE IF EXISTS legacy_conversation_messages")
    connection.execute("DROP TABLE legacy_conversations")
    connection.execute("PRAGMA foreign_keys = ON")


def _ensure_schema(connection: sqlite3.Connection) -> None:
    conversation_columns = _columns(connection, "conversations")
    if conversation_columns and "id" not in conversation_columns:
        _migrate_legacy_schema(connection)
    else:
        _create_tables(connection)
    connection.commit()


def init_db(*, database_path: str | Path | None = None) -> None:
    """Create or migrate the local chat-history tables."""

    with _connection(database_path):
        pass


def create_conversation(
    plant_id: str | None = None,
    plant_name: str | None = None,
    *,
    title: str | None = None,
    database_path: str | Path | None = None,
) -> str:
    """Create a new conversation, even when the plant matches an older chat."""

    conversation_id = uuid4().hex
    now = _now()
    display_name = plant_name or "New Plant Chat"
    conversation_title = title or f"🌱 {display_name}"
    with _connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO conversations
                (id, title, plant_id, plant_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, conversation_title, plant_id, plant_name, now, now),
        )
        connection.commit()
    return conversation_id


def get_or_create_conversation(
    plant_id: str,
    *,
    database_path: str | Path | None = None,
) -> str:
    """Compatibility helper retaining the old one-conversation-per-plant API."""

    with _connection(database_path) as connection:
        row = connection.execute(
            "SELECT id FROM conversations WHERE plant_id = ? ORDER BY created_at LIMIT 1",
            (plant_id,),
        ).fetchone()
        if row is not None:
            return str(row["id"])
    return create_conversation(plant_id, plant_id, database_path=database_path)


def update_conversation(
    conversation_id: str,
    *,
    plant_id: str | None = None,
    plant_name: str | None = None,
    title: str | None = None,
    database_path: str | Path | None = None,
) -> None:
    """Update metadata and activity time for a conversation."""

    with _connection(database_path) as connection:
        current = connection.execute(
            "SELECT title, plant_id, plant_name FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if current is None:
            return
        next_name = plant_name if plant_name is not None else current["plant_name"]
        next_id = plant_id if plant_id is not None else current["plant_id"]
        next_title = title or current["title"]
        if title is None and plant_name:
            next_title = f"🌱 {plant_name}"
        connection.execute(
            """
            UPDATE conversations
            SET title = ?, plant_id = ?, plant_name = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_title, next_id, next_name, _now(), conversation_id),
        )
        connection.commit()


def rename_conversation(
    conversation_id: str,
    new_title: str,
    *,
    database_path: str | Path | None = None,
) -> bool:
    """Rename a conversation and update its activity timestamp."""

    title = new_title.strip()
    if not title:
        return False
    with _connection(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, _now(), conversation_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    input_method: str = "text",
    database_path: str | Path | None = None,
) -> None:
    """Save a message and update its conversation's activity timestamp."""

    with _connection(database_path) as connection:
        created_at = _now()
        connection.execute(
            """
            INSERT INTO messages
                (conversation_id, role, content, created_at, input_method)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, created_at, input_method),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (created_at, conversation_id),
        )
        connection.commit()


def get_conversation_messages(
    conversation_id: str,
    *,
    database_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, conversation_id, role, content, created_at, input_method
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id
            """,
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(
    conversation_id: str,
    *,
    database_path: str | Path | None = None,
) -> dict[str, Any] | None:
    with _connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, title, plant_id, plant_name, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_recent_conversations(
    *, database_path: str | Path | None = None
) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, plant_id, plant_name, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_conversation(
    conversation_id: str,
    *,
    database_path: str | Path | None = None,
) -> None:
    with _connection(database_path) as connection:
        connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        connection.commit()
