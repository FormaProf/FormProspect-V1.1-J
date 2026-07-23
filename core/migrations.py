from __future__ import annotations

import sqlite3
from datetime import datetime

TARGET_SCHEMA_VERSION = 19


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return column in {row[1] for row in cur.fetchall()}


def _add_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_migrations(conn: sqlite3.Connection) -> int:
    """Applique les migrations idempotentes de la RC1.9.

    La migration ne supprime et ne renomme aucune colonne existante. Elle peut
    donc être rejouée sur une base RC1.8.1 ou RC1.9 sans perte de données.
    """
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )

    migration_name = "RC1.9 - scoring commercial V2"
    cur.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (TARGET_SCHEMA_VERSION,))
    already_applied = cur.fetchone() is not None

    scoring_v2_columns = {
        "score_completude": "INTEGER NOT NULL DEFAULT 0",
        "score_potentiel": "INTEGER NOT NULL DEFAULT 0",
        "score_engagement": "INTEGER NOT NULL DEFAULT 0",
        "score_urgence": "INTEGER NOT NULL DEFAULT 0",
        "score_conversion": "INTEGER NOT NULL DEFAULT 0",
        "score_risque": "INTEGER NOT NULL DEFAULT 100",
        "score_version": "TEXT NOT NULL DEFAULT 'v1'",
    }
    for name, definition in scoring_v2_columns.items():
        _add_column(cur, "prospects", name, definition)

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS prospect_score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER NOT NULL,
            score_global INTEGER NOT NULL,
            score_completude INTEGER NOT NULL,
            score_potentiel INTEGER NOT NULL,
            score_engagement INTEGER NOT NULL,
            score_urgence INTEGER NOT NULL,
            score_conversion INTEGER NOT NULL,
            score_risque INTEGER NOT NULL,
            grade TEXT NOT NULL,
            label TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '[]',
            calculated_at TEXT NOT NULL,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_score_history_prospect_date
        ON prospect_score_history(prospect_id, calculated_at DESC);
        """
    )

    if not already_applied:
        cur.execute(
            "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
            (TARGET_SCHEMA_VERSION, migration_name, datetime.now().isoformat(timespec="seconds")),
        )

    conn.commit()
    return TARGET_SCHEMA_VERSION
