from __future__ import annotations

import shutil
import sqlite3
from core.sqlite_utils import connect_database
from datetime import datetime
from pathlib import Path
from typing import Any


class TrainingCaseService:
    """RC2.1.2 — dossiers formation et demandes internes de devis."""

    QUOTE_STATUSES = (
        "Brouillon", "À traiter", "En préparation", "Devis disponible",
        "Envoyé au client", "Signé", "Refusé", "Expiré",
    )

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
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
                CREATE TABLE IF NOT EXISTS quote_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    requested_by TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'À traiter',
                    quote_file_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_quote_requests_status
                    ON quote_requests(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_quote_requests_session
                    ON quote_requests(session_id);
                """
            )

    def list_cases(self, search: str = "") -> list[dict[str, Any]]:
        sql = """
            SELECT s.id AS session_id, c.id AS client_id, c.company_name, c.contact_name,
                   c.commercial_name, c.folder_path, t.reference, t.name AS training_name,
                   s.start_date, s.end_date, s.modality, s.duration_hours, s.price_cents,
                   s.participant_count, s.trainer_name, s.funder, s.status AS session_status,
                   COALESCE(w.current_step, 'Client créé') AS current_step,
                   COALESCE(w.progress_percent, 10) AS progress_percent,
                   COALESCE((SELECT qr.status FROM quote_requests qr WHERE qr.session_id=s.id
                             ORDER BY qr.id DESC LIMIT 1), 'Non demandée') AS quote_status,
                   COALESCE((SELECT qr.quote_file_path FROM quote_requests qr WHERE qr.session_id=s.id
                             ORDER BY qr.id DESC LIMIT 1), '') AS quote_file_path,
                   (SELECT qr.id FROM quote_requests qr WHERE qr.session_id=s.id
                             ORDER BY qr.id DESC LIMIT 1) AS quote_request_id
            FROM training_sessions s
            JOIN clients c ON c.id=s.client_id
            JOIN trainings t ON t.id=s.training_id
            LEFT JOIN client_workflows w ON w.session_id=s.id
        """
        params: list[Any] = []
        if search.strip():
            token = f"%{search.strip()}%"
            sql += " WHERE c.company_name LIKE ? OR t.name LIKE ? OR c.commercial_name LIKE ? "
            params.extend([token, token, token])
        sql += " ORDER BY s.start_date DESC, s.id DESC"
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def get_case(self, session_id: int) -> dict[str, Any] | None:
        rows = [r for r in self.list_cases() if int(r["session_id"]) == int(session_id)]
        return rows[0] if rows else None

    def create_quote_request(self, session_id: int, requested_by: str, note: str = "") -> int:
        case = self.get_case(session_id)
        if not case:
            raise ValueError("Le dossier formation est introuvable.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO quote_requests(client_id, session_id, requested_by, note, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'À traiter', ?, ?)""",
                (case["client_id"], session_id, requested_by.strip(), note.strip(), now, now),
            )
            conn.execute(
                """UPDATE client_workflows SET current_step='Demande de devis', progress_percent=20,
                   updated_at=? WHERE session_id=?""", (now, session_id),
            )
            return int(cur.lastrowid)

    def list_quote_requests(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT qr.*, c.company_name, t.name AS training_name, s.start_date, s.end_date,
                          s.price_cents, s.participant_count, c.folder_path
                   FROM quote_requests qr
                   JOIN clients c ON c.id=qr.client_id
                   JOIN training_sessions s ON s.id=qr.session_id
                   JOIN trainings t ON t.id=s.training_id
                   ORDER BY CASE qr.status WHEN 'À traiter' THEN 0 WHEN 'En préparation' THEN 1 ELSE 2 END,
                            qr.created_at DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def update_quote_status(self, request_id: int, status: str) -> None:
        if status not in self.QUOTE_STATUSES:
            raise ValueError("Statut de devis invalide.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            row = conn.execute("SELECT session_id FROM quote_requests WHERE id=?", (request_id,)).fetchone()
            if not row:
                raise ValueError("La demande de devis est introuvable.")
            conn.execute("UPDATE quote_requests SET status=?, updated_at=? WHERE id=?", (status, now, request_id))
            step_map = {
                "À traiter": ("Demande de devis", 20), "En préparation": ("Devis en préparation", 25),
                "Devis disponible": ("Devis disponible", 30), "Envoyé au client": ("Devis envoyé", 35),
                "Signé": ("Devis signé", 45), "Refusé": ("Devis refusé", 20), "Expiré": ("Devis expiré", 20),
            }
            if status in step_map:
                step, progress = step_map[status]
                conn.execute("UPDATE client_workflows SET current_step=?, progress_percent=?, updated_at=? WHERE session_id=?",
                             (step, progress, now, int(row["session_id"])))

    def import_quote_pdf(self, request_id: int, source_path: str | Path) -> Path:
        source = Path(source_path)
        if not source.exists() or source.suffix.lower() != ".pdf":
            raise ValueError("Sélectionnez un fichier PDF valide.")
        with self._connect() as conn:
            row = conn.execute(
                """SELECT qr.session_id, c.company_name, c.folder_path FROM quote_requests qr
                   JOIN clients c ON c.id=qr.client_id WHERE qr.id=?""", (request_id,)
            ).fetchone()
            if not row:
                raise ValueError("La demande de devis est introuvable.")
            target_dir = Path(row["folder_path"]) / "01 - Devis"
            target_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_company = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in row["company_name"]).strip()
            target = target_dir / f"Devis_{safe_company}_{stamp}.pdf"
            shutil.copy2(source, target)
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute("UPDATE quote_requests SET quote_file_path=?, status='Devis disponible', updated_at=? WHERE id=?",
                         (str(target), now, request_id))
            conn.execute("UPDATE client_workflows SET current_step='Devis disponible', progress_percent=30, updated_at=? WHERE session_id=?",
                         (now, int(row["session_id"])))
        return target

    def get_quote_file(self, request_id: int) -> Path:
        with self._connect() as conn:
            row = conn.execute("SELECT quote_file_path FROM quote_requests WHERE id=?", (request_id,)).fetchone()
        if not row or not row["quote_file_path"]:
            raise ValueError("Aucun devis PDF n'est disponible pour cette demande.")
        path = Path(row["quote_file_path"])
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("Le fichier du devis est introuvable. Demandez à l'administrateur de le réimporter.")
        return path

    def delete_training_case(self, session_id: int) -> None:
        """Supprime un dossier formation sans supprimer la fiche client partagée."""
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM training_sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                raise ValueError("Le dossier formation est introuvable.")
            # Suppression explicite pour rester compatible avec d'anciennes bases
            # qui n'auraient pas activé toutes les cascades de clés étrangères.
            conn.execute("DELETE FROM quote_requests WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM client_workflows WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM training_sessions WHERE id=?", (session_id,))
