from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CampaignStats:
    campaigns: int
    recipients: int
    ready: int
    sent: int
    opened: int
    replied: int
    appointments: int


class CampaignService:
    """Moteur local de campagnes commerciales.

    RC1.8 prépare les audiences, personnalise les messages et suit les statuts.
    Aucun e-mail n'est envoyé sans intégration explicite d'un fournisseur SMTP/API.
    """

    DEFAULT_TEMPLATES = {
        "Formation + outil sur mesure": {
            "subject": "Pilotage de {{entreprise}} — formation et outil sur mesure",
            "body": (
                "Bonjour {{contact}},\n\n"
                "Je me permets de vous contacter au sujet de {{entreprise}}. "
                "Form@Prof accompagne les entreprises du BTP dans l'organisation "
                "et le pilotage de leur activité.\n\n"
                "Notre approche associe une formation pratique adaptée à votre fonctionnement "
                "et la création d'un outil de pilotage personnalisé pour centraliser les devis, "
                "chantiers, règlements, relances et indicateurs de rentabilité.\n\n"
                "Form@Prof étant un organisme de formation certifié Qualiopi, une prise en charge "
                "totale ou partielle peut être étudiée selon votre situation, votre éligibilité "
                "et l'accord préalable du financeur.\n\n"
                "Un accompagnement qualité est également prévu pendant douze mois afin de vérifier "
                "que l'outil reste adapté et fonctionne correctement.\n\n"
                "Seriez-vous disponible pour un échange d'une vingtaine de minutes ?\n\n"
                "Bien cordialement,\n{{signature}}"
            ),
        },
        "Relance après premier contact": {
            "subject": "Suite à notre échange — {{entreprise}}",
            "body": (
                "Bonjour {{contact}},\n\n"
                "Je reviens vers vous à la suite de notre premier échange concernant le pilotage "
                "de l'activité de {{entreprise}}.\n\n"
                "L'objectif serait de comprendre votre organisation actuelle, puis de voir si une "
                "formation accompagnée de la création d'un outil sur mesure pourrait vous faire "
                "gagner du temps et améliorer votre visibilité.\n\n"
                "Quel créneau vous conviendrait pour un échange de vingt minutes ?\n\n"
                "Bien cordialement,\n{{signature}}"
            ),
        },
        "Invitation rendez-vous découverte": {
            "subject": "Échange de 20 minutes pour {{entreprise}}",
            "body": (
                "Bonjour {{contact}},\n\n"
                "Je vous propose un court rendez-vous afin d'analyser vos méthodes actuelles de suivi "
                "des devis, chantiers, règlements et marges.\n\n"
                "Cet échange est sans engagement : il permettra simplement de vérifier si notre "
                "accompagnement Form@Prof est pertinent pour {{entreprise}}.\n\n"
                "Êtes-vous disponible cette semaine ?\n\n"
                "Bien cordialement,\n{{signature}}"
            ),
        },
    }

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self._ensure_tables()

    def _connect(self):
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        with self._connect() as conn:
            conn.executescript(
                """
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
                """
            )
            conn.commit()

    @classmethod
    def template_names(cls) -> list[str]:
        return list(cls.DEFAULT_TEMPLATES)

    @classmethod
    def template(cls, name: str) -> dict:
        return dict(cls.DEFAULT_TEMPLATES.get(name) or next(iter(cls.DEFAULT_TEMPLATES.values())))

    @staticmethod
    def _text(value) -> str:
        return str(value or "").strip()

    @classmethod
    def personalize(cls, text: str, prospect: dict, signature: str = "L'équipe Form@Prof") -> str:
        contact = (
            cls._text(prospect.get("dirigeant"))
            or cls._text(prospect.get("nom_dirigeant"))
            or cls._text(prospect.get("contact"))
            or "Monsieur/Madame"
        )
        values = {
            "entreprise": cls._text(prospect.get("entreprise")) or "votre entreprise",
            "contact": contact,
            "ville": cls._text(prospect.get("ville")),
            "activite": cls._text(prospect.get("activite")) or cls._text(prospect.get("code_naf")) or "BTP",
            "signature": signature,
        }
        result = str(text or "")
        for key, value in values.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    @staticmethod
    def recommended_channel(prospect: dict) -> str:
        score = int(prospect.get("score_prospect") or 0)
        phone = bool(str(prospect.get("telephone") or "").strip())
        email = bool(str(prospect.get("email") or "").strip())
        if score >= 75 and phone:
            return "Appel prioritaire"
        if email and score >= 45:
            return "E-mail puis relance téléphonique"
        if phone:
            return "Appel de qualification"
        return "Enrichissement requis"

    def create_campaign(self, name: str, template_name: str, subject: str, body: str, min_score: int = 0) -> int:
        clean_name = self._text(name)
        if not clean_name:
            raise ValueError("Le nom de la campagne est obligatoire.")
        if not self._text(subject):
            raise ValueError("L'objet de l'e-mail est obligatoire.")
        if not self._text(body):
            raise ValueError("Le contenu de l'e-mail est obligatoire.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO campaigns(name, template_name, subject, body, status, min_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'Brouillon', ?, ?, ?)
                """,
                (clean_name, template_name, subject, body, max(0, min(int(min_score), 100)), now, now),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def campaigns(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*,
                       COUNT(r.id) AS recipient_count,
                       SUM(CASE WHEN r.status='Prêt' THEN 1 ELSE 0 END) AS ready_count,
                       SUM(CASE WHEN r.status='Envoyé' THEN 1 ELSE 0 END) AS sent_count,
                       SUM(CASE WHEN r.status='Répondu' THEN 1 ELSE 0 END) AS replied_count
                FROM campaigns c
                LEFT JOIN campaign_recipients r ON r.campaign_id=c.id
                GROUP BY c.id
                ORDER BY c.id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def campaign(self, campaign_id: int) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id=?", (int(campaign_id),)).fetchone()
        if row is None:
            raise ValueError("Campagne introuvable.")
        return dict(row)

    def build_audience(self, campaign_id: int, limit: int = 500) -> int:
        campaign = self.campaign(campaign_id)
        safe_limit = max(1, min(int(limit), 5000))
        with self._connect() as conn:
            prospects = conn.execute(
                """
                SELECT *
                FROM prospects
                WHERE COALESCE(TRIM(email), '') != ''
                  AND COALESCE(score_prospect, 0) >= ?
                  AND COALESCE(pipeline, '') NOT LIKE '%Perdu%'
                  AND COALESCE(pipeline, '') NOT LIKE '%Client%'
                ORDER BY COALESCE(score_prospect, 0) DESC, id ASC
                LIMIT ?
                """,
                (int(campaign["min_score"]), safe_limit),
            ).fetchall()
            now = datetime.now().isoformat(timespec="seconds")
            added = 0
            for row in prospects:
                prospect = dict(row)
                subject = self.personalize(campaign["subject"], prospect)
                body = self.personalize(campaign["body"], prospect)
                channel = self.recommended_channel(prospect)
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO campaign_recipients(
                        campaign_id, prospect_id, email, personalized_subject,
                        personalized_body, recommended_channel, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Prêt', ?, ?)
                    """,
                    (
                        int(campaign_id), int(prospect["id"]), self._text(prospect.get("email")),
                        subject, body, channel, now, now,
                    ),
                )
                added += cursor.rowcount
            conn.execute(
                "UPDATE campaigns SET status=?, updated_at=? WHERE id=?",
                ("Audience prête" if prospects else "Aucun destinataire", now, int(campaign_id)),
            )
            conn.commit()
        return added

    def recipients(self, campaign_id: int, limit: int = 1000) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.*, p.entreprise, p.telephone, p.score_prospect, p.pipeline
                FROM campaign_recipients r
                JOIN prospects p ON p.id=r.prospect_id
                WHERE r.campaign_id=?
                ORDER BY COALESCE(p.score_prospect,0) DESC, r.id ASC
                LIMIT ?
                """,
                (int(campaign_id), max(1, min(int(limit), 5000))),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_recipient_status(self, recipient_id: int, status: str) -> None:
        allowed = {"Prêt", "Envoyé", "Ouvert", "Cliqué", "Répondu", "Rendez-vous", "Exclu"}
        if status not in allowed:
            raise ValueError("Statut de campagne invalide.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE campaign_recipients SET status=?, updated_at=? WHERE id=?",
                (status, now, int(recipient_id)),
            )
            conn.commit()

    def stats(self) -> CampaignStats:
        with self._connect() as conn:
            campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
            row = conn.execute(
                """
                SELECT COUNT(*) AS recipients,
                       SUM(CASE WHEN status='Prêt' THEN 1 ELSE 0 END) AS ready,
                       SUM(CASE WHEN status='Envoyé' THEN 1 ELSE 0 END) AS sent,
                       SUM(CASE WHEN status='Ouvert' THEN 1 ELSE 0 END) AS opened,
                       SUM(CASE WHEN status='Répondu' THEN 1 ELSE 0 END) AS replied,
                       SUM(CASE WHEN status='Rendez-vous' THEN 1 ELSE 0 END) AS appointments
                FROM campaign_recipients
                """
            ).fetchone()
        return CampaignStats(
            campaigns=int(campaigns or 0),
            recipients=int(row["recipients"] or 0),
            ready=int(row["ready"] or 0),
            sent=int(row["sent"] or 0),
            opened=int(row["opened"] or 0),
            replied=int(row["replied"] or 0),
            appointments=int(row["appointments"] or 0),
        )
