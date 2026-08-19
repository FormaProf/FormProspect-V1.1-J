from __future__ import annotations

import sqlite3
import uuid as uuid_module
from datetime import datetime, timezone
from typing import Callable

TARGET_SCHEMA_VERSION = 20

MIGRATION_19 = 19
MIGRATION_20 = 20

SYNC_STATE_LOCAL_ONLY = "LOCAL_ONLY"
SYNC_STATE_SYNCED = "SYNCED"
SYNC_STATE_DIRTY = "DIRTY"
SYNC_STATE_DELETED = "DELETED"
VALID_SYNC_STATES = {
    SYNC_STATE_LOCAL_ONLY,
    SYNC_STATE_SYNCED,
    SYNC_STATE_DIRTY,
    SYNC_STATE_DELETED,
}


def _utc_now() -> str:
    """Retourne un horodatage UTC ISO 8601 stable pour SQLite et l'API Cloud."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return column in {row[1] for row in cur.fetchall()}


def _add_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _ensure_migration_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _is_migration_recorded(cur: sqlite3.Cursor, version: int) -> bool:
    cur.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ?",
        (version,),
    )
    return cur.fetchone() is not None


def _record_migration(
    cur: sqlite3.Cursor,
    version: int,
    name: str,
) -> None:
    cur.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(version, name, applied_at)
        VALUES (?, ?, ?)
        """,
        (version, name, _utc_now()),
    )


def _migration_v19_scoring_v2(cur: sqlite3.Cursor) -> None:
    """Conserve et rejoue de manière sûre la migration historique RC1.9."""
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

    cur.execute(
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
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_score_history_prospect_date
        ON prospect_score_history(prospect_id, calculated_at DESC)
        """
    )


def _backfill_prospect_sync_metadata(cur: sqlite3.Cursor) -> None:
    """Complète les métadonnées manquantes sans modifier les valeurs existantes."""
    now = _utc_now()

    cur.execute(
        """
        UPDATE prospects
        SET created_at = ?
        WHERE created_at IS NULL OR TRIM(created_at) = ''
        """,
        (now,),
    )
    cur.execute(
        """
        UPDATE prospects
        SET updated_at = created_at
        WHERE updated_at IS NULL OR TRIM(updated_at) = ''
        """
    )
    cur.execute(
        """
        UPDATE prospects
        SET sync_state = ?
        WHERE sync_state IS NULL
           OR TRIM(sync_state) = ''
           OR UPPER(TRIM(sync_state)) NOT IN (?, ?, ?, ?)
        """,
        (
            SYNC_STATE_LOCAL_ONLY,
            SYNC_STATE_LOCAL_ONLY,
            SYNC_STATE_SYNCED,
            SYNC_STATE_DIRTY,
            SYNC_STATE_DELETED,
        ),
    )
    cur.execute(
        """
        UPDATE prospects
        SET sync_state = UPPER(TRIM(sync_state))
        WHERE sync_state IS NOT NULL
        """
    )

    cur.execute(
        """
        SELECT id
        FROM prospects
        WHERE uuid IS NULL OR TRIM(uuid) = ''
        ORDER BY id
        """
    )
    missing_ids = [row[0] for row in cur.fetchall()]

    for prospect_id in missing_ids:
        cur.execute(
            "UPDATE prospects SET uuid = ? WHERE id = ?",
            (str(uuid_module.uuid4()), prospect_id),
        )


def _assert_unique_prospect_uuids(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        SELECT uuid, COUNT(*)
        FROM prospects
        WHERE uuid IS NOT NULL AND TRIM(uuid) != ''
        GROUP BY uuid
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    )
    duplicate = cur.fetchone()
    if duplicate is not None:
        raise sqlite3.IntegrityError(
            "Migration v20 impossible : plusieurs prospects possèdent le même UUID."
        )


def _migration_v20_sync_foundation(cur: sqlite3.Cursor) -> None:
    """Ajoute le socle local requis par la future synchronisation Cloud."""
    sync_columns = {
        "uuid": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "sync_state": f"TEXT NOT NULL DEFAULT '{SYNC_STATE_LOCAL_ONLY}'",
        "last_synced_at": "TEXT",
    }

    for name, definition in sync_columns.items():
        _add_column(cur, "prospects", name, definition)

    _backfill_prospect_sync_metadata(cur)
    _assert_unique_prospect_uuids(cur)

    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_prospects_uuid ON prospects(uuid)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_prospects_sync_state ON prospects(sync_state)"
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_prospects_sync_pending
        ON prospects(sync_state, updated_at)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_prospects_last_synced_at
        ON prospects(last_synced_at)
        """
    )


MigrationFunction = Callable[[sqlite3.Cursor], None]

MIGRATIONS: tuple[tuple[int, str, MigrationFunction], ...] = (
    (
        MIGRATION_19,
        "RC1.9 - scoring commercial V2",
        _migration_v19_scoring_v2,
    ),
    (
        MIGRATION_20,
        "RC-01.5-B.5.1-A - synchronization foundation",
        _migration_v20_sync_foundation,
    ),
)


def run_migrations(conn: sqlite3.Connection) -> int:
    """Applique toutes les migrations desktop jusqu'à la version cible.

    Chaque migration est idempotente : sa structure est vérifiée même si son
    numéro est déjà enregistré. Cette stratégie répare les bases partiellement
    migrées sans supprimer ni renommer les données existantes.
    """
    cur = conn.cursor()

    if not _table_exists(cur, "prospects"):
        raise sqlite3.OperationalError(
            "La table prospects doit être créée avant l'exécution des migrations."
        )

    savepoint_name = "formaprospect_schema_migrations"
    cur.execute(f"SAVEPOINT {savepoint_name}")

    try:
        _ensure_migration_table(cur)

        for version, name, migration in MIGRATIONS:
            if version > TARGET_SCHEMA_VERSION:
                continue

            migration(cur)

            if not _is_migration_recorded(cur, version):
                _record_migration(cur, version, name)

        cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        conn.commit()
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        conn.rollback()
        raise

    return TARGET_SCHEMA_VERSION
