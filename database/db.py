"""Shared SQLite connection and path for PotWise local persistence."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "potwise.sqlite3"


@contextmanager
def connection(
    database_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Open the shared database, creating its parent directory if needed."""

    path = Path(database_path) if database_path is not None else DEFAULT_DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db_connection = sqlite3.connect(path)
    db_connection.row_factory = sqlite3.Row
    try:
        db_connection.execute("PRAGMA foreign_keys = ON")
        yield db_connection
    finally:
        db_connection.close()


def save_pot(*args, **kwargs):
    from core.pots import save_pot as _save_pot

    return _save_pot(*args, **kwargs)


def list_saved_pots(*args, **kwargs):
    from core.pots import list_saved_pots as _list_saved_pots

    return _list_saved_pots(*args, **kwargs)


def delete_pot(*args, **kwargs):
    from core.pots import delete_pot as _delete_pot

    return _delete_pot(*args, **kwargs)


__all__ = [
    "DEFAULT_DATABASE_PATH",
    "connection",
    "delete_pot",
    "list_saved_pots",
    "save_pot",
]
