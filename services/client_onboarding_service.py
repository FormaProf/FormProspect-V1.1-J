from __future__ import annotations

import re
import sqlite3
from core.sqlite_utils import connect_database
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from services.document_service import DocumentService


@dataclass(frozen=True)
class ClientOnboardingResult:
    client_id: int
    session_id: int
    workflow_id: int
    client_folder: Path


class ClientOnboardingService:
    """Transforme un prospect en client et prépare sa session de formation."""

    FUNDERS = ("Entreprise", "FAFCEA", "OPCO", "CPF", "Autre")
    WORKFLOW_STEPS = (
        "Client créé", "Devis à préparer", "Convention à préparer",
        "Formation à planifier", "Formation réalisée", "Facture à envoyer", "Dossier clôturé",
    )

    def __init__(self, database_path: str | Path, project_folder: str | Path | None = None):
        self.database_path = Path(database_path)
        self.project_folder = Path(project_folder) if project_folder else self.database_path.parent
        self.document_service = DocumentService(self.database_path)
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
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

                CREATE INDEX IF NOT EXISTS idx_training_sessions_client ON training_sessions(client_id, start_date);
                CREATE INDEX IF NOT EXISTS idx_client_workflows_step ON client_workflows(current_step);
                """
            )

    def prospect_as_dict(self, prospect_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT id, entreprise, siret, siren, adresse, code_postal, ville, telephone,
                          email, commercial_assigne, pipeline
                   FROM prospects WHERE id = ?""",
                (int(prospect_id),),
            ).fetchone()
        if row is None:
            raise ValueError("Le prospect sélectionné est introuvable.")
        return dict(row)

    def list_trainings(self) -> list[dict[str, Any]]:
        return self.document_service.list_trainings(active_only=True)

    @staticmethod
    def _safe_folder_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r'[<>:"/\\|?*]+', " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip(" .")
        return normalized[:100] or "CLIENT"

    def _documents_root(self) -> Path:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT setting_value FROM document_settings WHERE setting_key='documents_root'"
            ).fetchone()
        configured = str(row[0]).strip() if row else ""
        return Path(configured) if configured else self.project_folder / "Clients"

    def _create_client_folders(self, company_name: str) -> Path:
        root = self._documents_root()
        client_folder = root / self._safe_folder_name(company_name)
        for name in (
            "01 - Devis", "02 - Conventions", "03 - Programmes", "04 - Convocations",
            "05 - Factures", "06 - Emargements", "07 - Attestations", "08 - Satisfaction", "09 - Divers",
        ):
            (client_folder / name).mkdir(parents=True, exist_ok=True)
        return client_folder

    def transform(self, *, prospect_id: int, company_name: str, siret: str = "", address: str = "",
                  postal_code: str = "", city: str = "", contact_name: str = "", phone: str = "",
                  email: str = "", training_id: int, trainer_name: str = "", commercial_name: str = "",
                  funder: str = "Entreprise", funder_details: str = "", start_date: str,
                  end_date: str, daily_schedule: str = "9h-12h / 13h-17h", modality: str | None = None,
                  duration_hours: float | None = None, price_cents: int | None = None,
                  participant_count: int = 1) -> ClientOnboardingResult:
        company_name = company_name.strip()
        if not company_name:
            raise ValueError("Le nom de l’entreprise est obligatoire.")
        training = self.document_service.get_training(int(training_id))
        if training is None or not int(training.get("active", 0)):
            raise ValueError("La formation sélectionnée est introuvable ou inactive.")
        if funder not in self.FUNDERS:
            raise ValueError("Le financeur sélectionné est invalide.")
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise ValueError("Les dates de formation sont invalides.") from exc
        if end < start:
            raise ValueError("La date de fin ne peut pas précéder la date de début.")
        if participant_count < 1:
            raise ValueError("Le nombre de participants doit être au moins égal à 1.")

        duration = float(training["duration_hours"] if duration_hours is None else duration_hours)
        price = int(training["price_cents"] if price_cents is None else price_cents)
        chosen_modality = (modality or training["modality"]).strip()
        if duration <= 0 or price < 0:
            raise ValueError("La durée ou le prix de la session est invalide.")

        self.prospect_as_dict(prospect_id)
        client_folder = self._create_client_folders(company_name)
        now = datetime.now().isoformat(timespec="seconds")

        with self._connect() as conn:
            existing = conn.execute("SELECT id FROM clients WHERE prospect_id=?", (int(prospect_id),)).fetchone()
            if existing:
                client_id = int(existing["id"])
                conn.execute(
                    """UPDATE clients SET company_name=?, siret=?, address=?, postal_code=?, city=?,
                       contact_name=?, phone=?, email=?, commercial_name=?, folder_path=?, updated_at=? WHERE id=?""",
                    (company_name, siret.strip(), address.strip(), postal_code.strip(), city.strip(),
                     contact_name.strip(), phone.strip(), email.strip(), commercial_name.strip(),
                     str(client_folder), now, client_id),
                )
            else:
                cur = conn.execute(
                    """INSERT INTO clients(prospect_id, company_name, siret, address, postal_code, city,
                       contact_name, phone, email, commercial_name, folder_path, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (int(prospect_id), company_name, siret.strip(), address.strip(), postal_code.strip(), city.strip(),
                     contact_name.strip(), phone.strip(), email.strip(), commercial_name.strip(),
                     str(client_folder), now, now),
                )
                client_id = int(cur.lastrowid)

            cur = conn.execute(
                """INSERT INTO training_sessions(client_id, training_id, trainer_name, commercial_name,
                   funder, funder_details, start_date, end_date, daily_schedule, modality, duration_hours,
                   price_cents, participant_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (client_id, int(training_id), trainer_name.strip(), commercial_name.strip(), funder,
                 funder_details.strip(), start.isoformat(), end.isoformat(), daily_schedule.strip(),
                 chosen_modality, duration, price, int(participant_count), now, now),
            )
            session_id = int(cur.lastrowid)
            cur = conn.execute(
                """INSERT INTO client_workflows(client_id, session_id, current_step, progress_percent, updated_at)
                   VALUES (?, ?, 'Client créé', 10, ?)""",
                (client_id, session_id, now),
            )
            workflow_id = int(cur.lastrowid)
            conn.execute(
                """UPDATE prospects SET pipeline='🟢 Client', prochaine_action='Préparer le devis',
                   date_prochaine_action=? WHERE id=?""",
                (date.today().isoformat(), int(prospect_id)),
            )

        return ClientOnboardingResult(client_id, session_id, workflow_id, client_folder)
