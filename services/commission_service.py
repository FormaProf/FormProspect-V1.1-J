from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Offer:
    id: int
    name: str
    price_cents: int
    commission_rate: float
    active: bool


class CommissionService:
    """Gestion du catalogue, des ventes et des commissions.

    Les montants sont stockés en centimes afin d'éviter les erreurs d'arrondi.
    Le prix et le taux sont copiés dans la vente au moment de la signature :
    une modification future du catalogue ne change donc pas l'historique.
    """

    DEFAULT_OFFERS = (
        ("Formation Classic BTP", 170_000, 15.0, "Autoentrepreneur sans salarié"),
        ("Formation Pro BTP", 250_000, 20.0, "TPE de 1 à 2 salariés"),
        ("Formation Pro+ BTP", 350_000, 25.0, "TPE/PME de 3 à 5 salariés"),
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
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    description TEXT NOT NULL DEFAULT '',
                    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                    commission_rate REAL NOT NULL CHECK(commission_rate >= 0),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prospect_id INTEGER NOT NULL,
                    offer_id INTEGER NOT NULL,
                    commercial_user_id INTEGER NOT NULL,
                    commercial_name TEXT NOT NULL,
                    signed_at TEXT NOT NULL,
                    price_cents INTEGER NOT NULL,
                    commission_rate REAL NOT NULL,
                    commission_cents INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Signée',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    cancelled_at TEXT,
                    FOREIGN KEY(prospect_id) REFERENCES prospects(id),
                    FOREIGN KEY(offer_id) REFERENCES offers(id)
                );

                CREATE INDEX IF NOT EXISTS idx_sales_commercial_date
                    ON sales(commercial_user_id, signed_at);
                CREATE INDEX IF NOT EXISTS idx_sales_status_date
                    ON sales(status, signed_at);
                CREATE INDEX IF NOT EXISTS idx_sales_prospect
                    ON sales(prospect_id);
                """
            )
            now = datetime.now().isoformat(timespec="seconds")
            for name, price_cents, rate, description in self.DEFAULT_OFFERS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO offers(
                        name, description, price_cents, commission_rate,
                        active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (name, description, price_cents, rate, now, now),
                )

    def list_offers(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM offers"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY price_cents, name COLLATE NOCASE"
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def list_prospects(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, COALESCE(NULLIF(TRIM(entreprise), ''), 'Prospect #' || id) AS entreprise,
                       ville, email, telephone
                FROM prospects
                ORDER BY entreprise COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_sale(
        self,
        *,
        prospect_id: int,
        offer_id: int,
        commercial_user_id: int,
        commercial_name: str,
        signed_at: str | date,
        notes: str = "",
    ) -> int:
        signed_text = signed_at.isoformat() if isinstance(signed_at, date) else str(signed_at).strip()
        try:
            signed_date = date.fromisoformat(signed_text)
        except ValueError as exc:
            raise ValueError("La date de signature est invalide.") from exc

        if signed_date > date.today():
            raise ValueError("La date de signature ne peut pas être postérieure à la date du jour.")

        with self._connect() as conn:
            prospect = conn.execute("SELECT id FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
            if prospect is None:
                raise ValueError("Le prospect sélectionné est introuvable.")

            offer = conn.execute(
                "SELECT * FROM offers WHERE id = ? AND active = 1", (offer_id,)
            ).fetchone()
            if offer is None:
                raise ValueError("L'offre sélectionnée est introuvable ou inactive.")

            price_cents = int(offer["price_cents"])
            rate = float(offer["commission_rate"])
            commission_cents = round(price_cents * rate / 100.0)
            now = datetime.now().isoformat(timespec="seconds")

            cursor = conn.execute(
                """
                INSERT INTO sales(
                    prospect_id, offer_id, commercial_user_id, commercial_name,
                    signed_at, price_cents, commission_rate, commission_cents,
                    status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Signée', ?, ?)
                """,
                (
                    int(prospect_id), int(offer_id), int(commercial_user_id),
                    commercial_name.strip() or f"Utilisateur {commercial_user_id}",
                    signed_text, price_cents, rate, commission_cents,
                    notes.strip(), now,
                ),
            )
            conn.execute(
                "UPDATE prospects SET pipeline = '🟢 Client' WHERE id = ?",
                (int(prospect_id),),
            )
            conn.execute(
                """
                INSERT INTO activities(prospect_id, date_creation, type_action, description)
                VALUES (?, ?, 'Vente', ?)
                """,
                (
                    int(prospect_id), now,
                    f"Contrat signé : {offer['name']} — {price_cents / 100:.2f} € — commission {commission_cents / 100:.2f} €",
                ),
            )
            return int(cursor.lastrowid)

    def cancel_sale(self, sale_id: int) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT status FROM sales WHERE id = ?", (sale_id,)).fetchone()
            if row is None:
                raise ValueError("Vente introuvable.")
            if row["status"] == "Annulée":
                return
            conn.execute(
                "UPDATE sales SET status = 'Annulée', cancelled_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), sale_id),
            )

    def monthly_summary(
        self,
        *,
        year: int,
        month: int,
        commercial_user_id: int | None = None,
    ) -> dict[str, int]:
        start = date(year, month, 1)
        end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        where = "status = 'Signée' AND signed_at >= ? AND signed_at < ?"
        params: list[Any] = [start.isoformat(), end.isoformat()]
        if commercial_user_id is not None:
            where += " AND commercial_user_id = ?"
            params.append(int(commercial_user_id))
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS contracts,
                       COALESCE(SUM(price_cents), 0) AS revenue_cents,
                       COALESCE(SUM(commission_cents), 0) AS commission_cents
                FROM sales WHERE {where}
                """,
                tuple(params),
            ).fetchone()
        return {
            "contracts": int(row["contracts"]),
            "revenue_cents": int(row["revenue_cents"]),
            "commission_cents": int(row["commission_cents"]),
        }

    def list_sales(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        commercial_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions = ["1 = 1"]
        params: list[Any] = []
        if year is not None and month is not None:
            start = date(year, month, 1)
            end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
            conditions.extend(["s.signed_at >= ?", "s.signed_at < ?"])
            params.extend([start.isoformat(), end.isoformat()])
        if commercial_user_id is not None:
            conditions.append("s.commercial_user_id = ?")
            params.append(int(commercial_user_id))

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT s.id, s.signed_at, s.commercial_user_id, s.commercial_name,
                       s.price_cents, s.commission_rate, s.commission_cents,
                       s.status, s.notes, o.name AS offer_name,
                       COALESCE(NULLIF(TRIM(p.entreprise), ''), 'Prospect #' || p.id) AS prospect_name
                FROM sales s
                JOIN offers o ON o.id = s.offer_id
                JOIN prospects p ON p.id = s.prospect_id
                WHERE {' AND '.join(conditions)}
                ORDER BY s.signed_at DESC, s.id DESC
                """,
                tuple(params),
            ).fetchall()
        return [dict(row) for row in rows]
