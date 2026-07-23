from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentStats:
    trainings: int
    templates: int
    active_templates: int
    documents: int


class DocumentService:
    """Fondations du moteur documentaire RC2.0.1.

    Cette version gère le catalogue de formations, les modèles de documents,
    la numérotation et les paramètres. La génération DOCX/PDF sera branchée
    sur ces tables dans RC2.0.3.
    """

    DOCUMENT_TYPES = ("Devis", "Convention", "Programme", "Convocation", "Facture", "Attestation")
    MODALITIES = ("À distance", "Présentiel", "Mixte")

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trainings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    name TEXT NOT NULL,
                    duration_hours REAL NOT NULL DEFAULT 0 CHECK(duration_hours >= 0),
                    price_cents INTEGER NOT NULL DEFAULT 0 CHECK(price_cents >= 0),
                    modality TEXT NOT NULL DEFAULT 'À distance',
                    certification TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    objectives TEXT NOT NULL DEFAULT '',
                    prerequisites TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS document_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    training_id INTEGER,
                    source_path TEXT NOT NULL DEFAULT '',
                    output_format TEXT NOT NULL DEFAULT 'DOCX',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(name, document_type),
                    FOREIGN KEY(training_id) REFERENCES trainings(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS document_sequences (
                    document_type TEXT PRIMARY KEY,
                    prefix TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    current_value INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS document_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prospect_id INTEGER NOT NULL UNIQUE,
                    company_name TEXT NOT NULL,
                    siret TEXT NOT NULL DEFAULT '',
                    address TEXT NOT NULL DEFAULT '',
                    postal_code TEXT NOT NULL DEFAULT '',
                    city TEXT NOT NULL DEFAULT '',
                    contact_name TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    commercial_name TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Actif',
                    folder_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    training_id INTEGER NOT NULL,
                    trainer_name TEXT NOT NULL DEFAULT '',
                    commercial_name TEXT NOT NULL DEFAULT '',
                    funder TEXT NOT NULL DEFAULT 'Entreprise',
                    funder_details TEXT NOT NULL DEFAULT '',
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    daily_schedule TEXT NOT NULL DEFAULT '',
                    modality TEXT NOT NULL,
                    duration_hours REAL NOT NULL,
                    price_cents INTEGER NOT NULL,
                    participant_count INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'Préparation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                    FOREIGN KEY(training_id) REFERENCES trainings(id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS client_workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    current_step TEXT NOT NULL DEFAULT 'Client créé',
                    progress_percent INTEGER NOT NULL DEFAULT 10,
                    updated_at TEXT NOT NULL,
                    UNIQUE(client_id, session_id),
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_training_sessions_client
                    ON training_sessions(client_id, start_date);
                CREATE INDEX IF NOT EXISTS idx_client_workflows_step
                    ON client_workflows(current_step);

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_number TEXT NOT NULL UNIQUE,
                    document_type TEXT NOT NULL,
                    prospect_id INTEGER,
                    training_id INTEGER,
                    template_id INTEGER,
                    file_path TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Brouillon',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(prospect_id) REFERENCES prospects(id) ON DELETE SET NULL,
                    FOREIGN KEY(training_id) REFERENCES trainings(id) ON DELETE SET NULL,
                    FOREIGN KEY(template_id) REFERENCES document_templates(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_document_templates_type
                    ON document_templates(document_type, active);
                CREATE INDEX IF NOT EXISTS idx_documents_type_date
                    ON documents(document_type, created_at DESC);
                """
            )
            # Migration RC2.0.2a : enrichissement du catalogue de formations.
            existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(trainings)").fetchall()}
            for column, ddl in {
                "category": "TEXT NOT NULL DEFAULT ''",
                "target_audience": "TEXT NOT NULL DEFAULT ''",
                "teaching_methods": "TEXT NOT NULL DEFAULT ''",
                "evaluation_methods": "TEXT NOT NULL DEFAULT ''",
                "max_participants": "INTEGER NOT NULL DEFAULT 8",
            }.items():
                if column not in existing_columns:
                    conn.execute(f"ALTER TABLE trainings ADD COLUMN {column} {ddl}")

            for document_type, prefix in {
                "Devis": "DEV", "Convention": "CONV", "Programme": "PROG",
                "Convocation": "CONVOC", "Facture": "FACT", "Attestation": "ATT",
            }.items():
                conn.execute(
                    """INSERT OR IGNORE INTO document_sequences(document_type, prefix, year, current_value)
                       VALUES (?, ?, CAST(strftime('%Y','now') AS INTEGER), 0)""",
                    (document_type, prefix),
                )
            defaults = {
                "documents_root": "",
                "organization_name": "NM FORMATION",
                "brand_color": "#338CE4",
            }
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO document_settings(setting_key, setting_value, updated_at) VALUES (?, ?, ?)",
                    (key, value, now),
                )

    def ensure_official_templates(self) -> None:
        """Installe les modèles Word officiels fournis avec Form@Prospect.

        Les chemins sont recalculés à chaque ouverture afin que les projets restent
        portables, même lorsque Form@Prospect est déplacé sur un autre ordinateur.
        """
        templates_dir = Path(__file__).resolve().parent.parent / "assets" / "document_templates"
        official = {
            "Convention": ("Convention Form@Prof officielle", templates_dir / "Convention_FormProf_Officielle.docx"),
            "Programme": ("Programme Form@Prof officiel", templates_dir / "Programme_FormProf_Officiel.docx"),
            "Convocation": ("Convocation Form@Prof officielle", templates_dir / "Convocation_FormProf_Officielle.docx"),
        }
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            for document_type, (name, path) in official.items():
                if not path.is_file():
                    continue
                row = conn.execute(
                    "SELECT id FROM document_templates WHERE name=? AND document_type=?",
                    (name, document_type),
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE document_templates SET source_path=?, output_format='DOCX + PDF', active=1, updated_at=? WHERE id=?",
                        (str(path), now, int(row[0])),
                    )
                else:
                    conn.execute(
                        """INSERT INTO document_templates(name, document_type, training_id, source_path, output_format, active, created_at, updated_at)
                           VALUES (?, ?, NULL, ?, 'DOCX + PDF', 1, ?, ?)""",
                        (name, document_type, str(path), now, now),
                    )

    def ensure_default_training(self) -> int:
        """Ajoute la formation Pilotage BTP uniquement si le catalogue est vide."""
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM trainings ORDER BY id LIMIT 1").fetchone()
        if row:
            return int(row[0])
        return self.save_training(
            reference="BTP-PILOTAGE", name="Pilotage d'activité BTP",
            duration_hours=14.0, price_cents=150000, modality="À distance",
            description="Création d'un outil de pilotage d'activité sous Excel / Google Sheets.",
            objectives="Structurer le suivi des clients, chantiers et du chiffre d'affaires ; automatiser les calculs ; créer des tableaux croisés dynamiques et graphiques.",
            prerequisites="Savoir utiliser un ordinateur. Débutant Excel / Google Sheets accepté.",
            category="Bureautique / BTP",
            target_audience="Artisans du bâtiment, dirigeants de TPE/PME, conducteurs de travaux et assistants administratifs.",
            teaching_methods="Démonstrations, exercices pratiques, cas métier, atelier guidé et construction progressive d'un outil personnalisé.",
            evaluation_methods="Test de positionnement, exercices pratiques, mise en situation et évaluation finale du fichier réalisé.",
            max_participants=8, active=True,
        )

    def stats(self) -> DocumentStats:
        with self._connect() as conn:
            trainings = conn.execute("SELECT COUNT(*) FROM trainings").fetchone()[0]
            templates = conn.execute("SELECT COUNT(*) FROM document_templates").fetchone()[0]
            active_templates = conn.execute("SELECT COUNT(*) FROM document_templates WHERE active = 1").fetchone()[0]
            documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return DocumentStats(int(trainings), int(templates), int(active_templates), int(documents))

    def list_trainings(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM trainings"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY active DESC, name COLLATE NOCASE"
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query).fetchall()]

    def get_training(self, training_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM trainings WHERE id = ?", (int(training_id),)).fetchone()
        return dict(row) if row else None

    def save_training(self, *, training_id: int | None = None, reference: str, name: str,
                      duration_hours: float, price_cents: int, modality: str,
                      certification: str = "", description: str = "", objectives: str = "",
                      prerequisites: str = "", active: bool = True, category: str = "",
                      target_audience: str = "", teaching_methods: str = "",
                      evaluation_methods: str = "", max_participants: int = 8) -> int:
        reference = reference.strip().upper()
        name = name.strip()
        if not reference:
            raise ValueError("La référence de la formation est obligatoire.")
        if not name:
            raise ValueError("Le nom de la formation est obligatoire.")
        if duration_hours <= 0:
            raise ValueError("La durée doit être supérieure à zéro.")
        if price_cents < 0:
            raise ValueError("Le prix ne peut pas être négatif.")
        if modality not in self.MODALITIES:
            raise ValueError("La modalité sélectionnée est invalide.")
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self._connect() as conn:
                if training_id is None:
                    cur = conn.execute(
                        """INSERT INTO trainings(reference, name, duration_hours, price_cents, modality,
                           certification, description, objectives, prerequisites, active, created_at, updated_at,
                           category, target_audience, teaching_methods, evaluation_methods, max_participants)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (reference, name, float(duration_hours), int(price_cents), modality,
                         certification.strip(), description.strip(), objectives.strip(), prerequisites.strip(),
                         1 if active else 0, now, now, category.strip(), target_audience.strip(),
                         teaching_methods.strip(), evaluation_methods.strip(), max(1, int(max_participants))),
                    )
                    return int(cur.lastrowid)
                conn.execute(
                    """UPDATE trainings SET reference=?, name=?, duration_hours=?, price_cents=?, modality=?,
                       certification=?, description=?, objectives=?, prerequisites=?, active=?, updated_at=?,
                       category=?, target_audience=?, teaching_methods=?, evaluation_methods=?, max_participants=?
                       WHERE id=?""",
                    (reference, name, float(duration_hours), int(price_cents), modality,
                     certification.strip(), description.strip(), objectives.strip(), prerequisites.strip(),
                     1 if active else 0, now, category.strip(), target_audience.strip(),
                     teaching_methods.strip(), evaluation_methods.strip(), max(1, int(max_participants)), int(training_id)),
                )
                return int(training_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Cette référence de formation existe déjà.") from exc

    def set_training_active(self, training_id: int, active: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE trainings SET active=?, updated_at=? WHERE id=?",
                         (1 if active else 0, datetime.now().isoformat(timespec="seconds"), int(training_id)))

    def duplicate_training(self, training_id: int) -> int:
        source = self.get_training(training_id)
        if not source:
            raise ValueError("Formation introuvable.")
        base_reference = f"{source['reference']}-COPIE"
        reference = base_reference
        index = 2
        existing = {row['reference'].upper() for row in self.list_trainings()}
        while reference.upper() in existing:
            reference = f"{base_reference}-{index}"
            index += 1
        return self.save_training(
            reference=reference, name=f"{source['name']} (copie)",
            duration_hours=source['duration_hours'], price_cents=source['price_cents'],
            modality=source['modality'], certification=source.get('certification',''),
            description=source.get('description',''), objectives=source.get('objectives',''),
            prerequisites=source.get('prerequisites',''), active=False,
            category=source.get('category',''), target_audience=source.get('target_audience',''),
            teaching_methods=source.get('teaching_methods',''), evaluation_methods=source.get('evaluation_methods',''),
            max_participants=source.get('max_participants',8),
        )

    def delete_training(self, training_id: int) -> None:
        with self._connect() as conn:
            used = conn.execute("SELECT COUNT(*) FROM training_sessions WHERE training_id=?", (int(training_id),)).fetchone()[0]
            if used:
                raise ValueError("Cette formation est déjà utilisée dans une session. Désactivez-la plutôt que de la supprimer.")
            conn.execute("DELETE FROM trainings WHERE id=?", (int(training_id),))

    def list_templates(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT t.*, f.name AS training_name FROM document_templates t
                   LEFT JOIN trainings f ON f.id=t.training_id
                   ORDER BY t.active DESC, t.document_type, t.name COLLATE NOCASE"""
            ).fetchall()
        return [dict(row) for row in rows]

    def save_template(self, *, template_id: int | None = None, name: str, document_type: str,
                      source_path: str, output_format: str = "DOCX", training_id: int | None = None,
                      active: bool = True) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Le nom du modèle est obligatoire.")
        if document_type not in self.DOCUMENT_TYPES:
            raise ValueError("Le type de document est invalide.")
        source_path = source_path.strip()
        if source_path and not Path(source_path).exists():
            raise ValueError("Le fichier modèle sélectionné est introuvable.")
        output_format = output_format.upper()
        if output_format not in {"DOCX", "PDF", "DOCX + PDF"}:
            raise ValueError("Le format de sortie est invalide.")
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self._connect() as conn:
                if template_id is None:
                    cur = conn.execute(
                        """INSERT INTO document_templates(name, document_type, training_id, source_path,
                           output_format, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, document_type, training_id, source_path, output_format, 1 if active else 0, now, now),
                    )
                    return int(cur.lastrowid)
                conn.execute(
                    """UPDATE document_templates SET name=?, document_type=?, training_id=?, source_path=?,
                       output_format=?, active=?, updated_at=? WHERE id=?""",
                    (name, document_type, training_id, source_path, output_format,
                     1 if active else 0, now, int(template_id)),
                )
                return int(template_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Un modèle portant ce nom existe déjà pour ce type de document.") from exc

    def set_template_active(self, template_id: int, active: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE document_templates SET active=?, updated_at=? WHERE id=?",
                         (1 if active else 0, datetime.now().isoformat(timespec="seconds"), int(template_id)))

    def next_number(self, document_type: str, year: int | None = None) -> str:
        if document_type not in self.DOCUMENT_TYPES:
            raise ValueError("Le type de document est invalide.")
        year = int(year or datetime.now().year)
        with self._connect() as conn:
            row = conn.execute("SELECT prefix, year, current_value FROM document_sequences WHERE document_type=?",
                               (document_type,)).fetchone()
            if row is None:
                raise ValueError("La séquence documentaire est introuvable.")
            current = 0 if int(row["year"]) != year else int(row["current_value"])
            current += 1
            conn.execute("UPDATE document_sequences SET year=?, current_value=? WHERE document_type=?",
                         (year, current, document_type))
            return f"{row['prefix']}-{year}-{current:06d}"


    def list_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT d.*, c.company_name
                   FROM documents d
                   LEFT JOIN prospects p ON p.id=d.prospect_id
                   LEFT JOIN clients c ON c.prospect_id=p.id
                   ORDER BY d.created_at DESC, d.id DESC"""
            ).fetchall()
        return [dict(row) for row in rows]
