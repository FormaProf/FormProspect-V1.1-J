"""SQLite helpers for deterministic connection cleanup on every platform.

The standard ``sqlite3.Connection`` context manager commits or rolls back a
transaction, but it does not close the database handle. On Windows this can
leave temporary ``project.db`` files locked until garbage collection runs.
``ClosingConnection`` keeps normal sqlite3 behaviour while guaranteeing that
``with connect_database(...)`` releases the file handle immediately.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class ClosingConnection(sqlite3.Connection):
    """Connection whose context manager also closes the native file handle."""

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool | None:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect_database(database: str | Path, *args: Any, **kwargs: Any) -> sqlite3.Connection:
    """Open a SQLite connection with deterministic context-manager cleanup."""

    kwargs.setdefault("factory", ClosingConnection)
    return sqlite3.connect(str(database), *args, **kwargs)
