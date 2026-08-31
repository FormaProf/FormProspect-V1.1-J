from core.migrations import run_migrations
import sqlite3
from core.sqlite_utils import connect_database
import os


class Database:
    def __init__(self, database_path):
        self.database_path = database_path

    def create_database(self):
        init_database(self.database_path)


def colonne_existe(cur, table, colonne):
    cur.execute(f"PRAGMA table_info({table})")
    colonnes = [row[1] for row in cur.fetchall()]
    return colonne in colonnes


def init_database(database_path):
    os.makedirs(os.path.dirname(str(database_path)), exist_ok=True)

    conn = connect_database(database_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prospects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entreprise TEXT,
        siret TEXT,
        siren TEXT,
        adresse TEXT,
        code_postal TEXT,
        ville TEXT,
        code_naf TEXT,
        telephone TEXT,
        site_web TEXT,
        email TEXT,
        facebook TEXT,
        linkedin TEXT,
        instagram TEXT,
        youtube TEXT,
        statut_enrichissement TEXT,
        date_collecte TEXT
    )
    """)

    if not colonne_existe(cur, "prospects", "pipeline"):
        cur.execute("ALTER TABLE prospects ADD COLUMN pipeline TEXT DEFAULT '🟢 Nouveau'")
        cur.execute("""
            UPDATE prospects
            SET pipeline = statut_enrichissement
            WHERE statut_enrichissement IN (
                '🟢 Nouveau',
                '🟡 Qualification',
                '🔵 RDV programmé',
                '🟣 Proposition envoyée',
                '🟠 Négociation',
                '🟢 Client',
                '🔴 Perdu'
            )
        """)

    if not colonne_existe(cur, "prospects", "priorite"):
        cur.execute("ALTER TABLE prospects ADD COLUMN priorite TEXT DEFAULT '⭐⭐⭐'")

    if not colonne_existe(cur, "prospects", "prochaine_action"):
        cur.execute("ALTER TABLE prospects ADD COLUMN prochaine_action TEXT DEFAULT 'Aucune'")

    if not colonne_existe(cur, "prospects", "date_prochaine_action"):
        cur.execute("ALTER TABLE prospects ADD COLUMN date_prochaine_action TEXT DEFAULT ''")

    if not colonne_existe(cur, "prospects", "commercial_assigne"):
        cur.execute("ALTER TABLE prospects ADD COLUMN commercial_assigne TEXT DEFAULT ''")

    # Lot 2 : noms alternatifs destinés uniquement à la recherche publique
    # (enseigne, dénomination usuelle, sigle, nom d'usage). Le nom principal
    # reste stocké dans ``entreprise`` afin de ne pas modifier le CRM.
    if not colonne_existe(cur, "prospects", "noms_recherche"):
        cur.execute("ALTER TABLE prospects ADD COLUMN noms_recherche TEXT DEFAULT ''")

    scoring_columns = {
        "score_prospect": "INTEGER DEFAULT 0",
        "score_grade": "TEXT DEFAULT '★☆☆☆☆'",
        "score_label": "TEXT DEFAULT 'Données insuffisantes'",
        "score_details": "TEXT DEFAULT '[]'",
        "date_score": "TEXT DEFAULT ''",
    }
    for column_name, definition in scoring_columns.items():
        if not colonne_existe(cur, "prospects", column_name):
            cur.execute(f"ALTER TABLE prospects ADD COLUMN {column_name} {definition}")

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_prospects_date_action
        ON prospects(date_prochaine_action)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id INTEGER NOT NULL,
        date_creation TEXT,
        contenu TEXT,
        FOREIGN KEY(prospect_id) REFERENCES prospects(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id INTEGER NOT NULL,
        date_creation TEXT,
        type_action TEXT,
        description TEXT,
        FOREIGN KEY(prospect_id) REFERENCES prospects(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        action_type TEXT NOT NULL,
        prospect_id INTEGER,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    )
    """)


    cur.executescript("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        template_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Brouillon',
        min_score INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS campaign_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        prospect_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        personalized_subject TEXT NOT NULL,
        personalized_body TEXT NOT NULL,
        recommended_channel TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Prêt',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(campaign_id, prospect_id),
        FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign
    ON campaign_recipients(campaign_id, status);
    """)


    cur.executescript("""
    CREATE TABLE IF NOT EXISTS sequences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Brouillon',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sequence_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sequence_id INTEGER NOT NULL,
        step_order INTEGER NOT NULL,
        day_offset INTEGER NOT NULL DEFAULT 0,
        step_type TEXT NOT NULL,
        title TEXT NOT NULL,
        instructions TEXT NOT NULL DEFAULT '',
        FOREIGN KEY(sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS sequence_enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sequence_id INTEGER NOT NULL,
        prospect_id INTEGER NOT NULL,
        current_step INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'Active',
        started_at TEXT NOT NULL,
        next_action_at TEXT,
        completed_at TEXT,
        UNIQUE(sequence_id, prospect_id),
        FOREIGN KEY(sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS sequence_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER NOT NULL,
        step_id INTEGER,
        event_type TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(enrollment_id) REFERENCES sequence_enrollments(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_sequence_enrollments_due
    ON sequence_enrollments(status, next_action_at);
    """)

    run_migrations(conn)
    conn.commit()
    conn.close()
