from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from datetime import date, datetime, timedelta


class AgendaService:
    """Accès aux prochaines actions commerciales du projet actif."""

    SUPPORTED_FORMATS = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    )

    @classmethod
    def parse_date(cls, value) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        for fmt in cls.SUPPORTED_FORMATS:
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def to_storage(value: date) -> str:
        return value.isoformat()

    def list_actions(self, database_path, start_date: date, end_date: date) -> list[dict]:
        conn = connect_database(database_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT id, entreprise, ville, telephone, email, pipeline, priorite,
                       prochaine_action, date_prochaine_action, commercial_assigne,
                       score_prospect, score_grade
                FROM prospects
                WHERE COALESCE(TRIM(date_prochaine_action), '') != ''
                  AND COALESCE(TRIM(prochaine_action), '') NOT IN ('', 'Aucune')
                ORDER BY id ASC
                """
            ).fetchall()
        finally:
            conn.close()

        results = []
        for row in rows:
            action_date = self.parse_date(row["date_prochaine_action"])
            if action_date is None or not (start_date <= action_date <= end_date):
                continue
            item = dict(row)
            item["action_date"] = action_date
            results.append(item)

        results.sort(
            key=lambda item: (
                item["action_date"],
                -int(item.get("score_prospect") or 0),
                str(item.get("entreprise") or "").lower(),
            )
        )
        return results

    def list_for_day(self, database_path, selected_date: date) -> list[dict]:
        return self.list_actions(database_path, selected_date, selected_date)

    def get_month_counts(self, database_path, year: int, month: int) -> dict[date, int]:
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        start = date(year, month, 1)
        end = next_month - timedelta(days=1)
        counts: dict[date, int] = {}
        for item in self.list_actions(database_path, start, end):
            action_date = item["action_date"]
            counts[action_date] = counts.get(action_date, 0) + 1
        return counts

    def get_summary(self, database_path, reference_date: date | None = None) -> dict:
        reference = reference_date or date.today()
        horizon = reference + timedelta(days=7)
        conn = connect_database(database_path)
        try:
            rows = conn.execute(
                """
                SELECT date_prochaine_action, prochaine_action
                FROM prospects
                WHERE COALESCE(TRIM(date_prochaine_action), '') != ''
                  AND COALESCE(TRIM(prochaine_action), '') NOT IN ('', 'Aucune')
                """
            ).fetchall()
        finally:
            conn.close()

        today = overdue = upcoming = total = 0
        for raw_date, _action in rows:
            parsed = self.parse_date(raw_date)
            if parsed is None:
                continue
            total += 1
            if parsed < reference:
                overdue += 1
            elif parsed == reference:
                today += 1
            elif parsed <= horizon:
                upcoming += 1
        return {"today": today, "overdue": overdue, "upcoming": upcoming, "total": total}

    def complete_action(self, database_path, prospect_id: int) -> bool:
        conn = connect_database(database_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE prospects
                SET prochaine_action = 'Aucune', date_prochaine_action = ''
                WHERE id = ?
                """,
                (int(prospect_id),),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def reschedule_action(self, database_path, prospect_id: int, new_date: date) -> bool:
        conn = connect_database(database_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE prospects
                SET date_prochaine_action = ?
                WHERE id = ?
                """,
                (self.to_storage(new_date), int(prospect_id)),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
