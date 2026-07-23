from __future__ import annotations

import sqlite3
from pathlib import Path

from core.sqlite_utils import connect_database


def test_managed_connection_is_closed_after_context(tmp_path: Path) -> None:
    database = tmp_path / "project.db"

    with connect_database(database) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO sample DEFAULT VALUES")

    try:
        connection.execute("SELECT 1")
    except sqlite3.ProgrammingError as exc:
        assert "closed" in str(exc).lower()
    else:
        raise AssertionError("La connexion SQLite aurait dû être fermée à la sortie du contexte.")

    renamed = tmp_path / "project-renamed.db"
    database.rename(renamed)
    renamed.unlink()
    assert not renamed.exists()
