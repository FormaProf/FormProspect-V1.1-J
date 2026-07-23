from __future__ import annotations

import json
import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.database import init_database


@dataclass(frozen=True)
class ProspectScore:
    score: int
    grade: str
    label: str
    reasons: tuple[str, ...]
    completeness: int = 0
    potential: int = 0
    engagement: int = 0
    urgency: int = 0
    conversion: int = 0
    risk: int = 100

    @property
    def details_json(self) -> str:
        return json.dumps(list(self.reasons), ensure_ascii=False)


class ScoringService:
    """Moteur de scoring commercial V2, explicable et entièrement local."""

    VERSION = "v2"
    CONTACT_FIELDS = ("telephone", "email", "site_web")
    PROFILE_FIELDS = (
        "entreprise", "siret", "siren", "adresse", "code_postal", "ville",
        "code_naf", "telephone", "site_web", "email", "linkedin", "facebook",
        "instagram",
    )
    SCORE_COLUMNS = (
        "id", "entreprise", "telephone", "email", "site_web", "linkedin",
        "facebook", "instagram", "siret", "siren", "code_naf", "adresse",
        "ville", "code_postal", "statut_enrichissement", "pipeline", "priorite",
        "prochaine_action", "date_prochaine_action", "commercial_assigne",
    )

    PIPELINE_POINTS = {
        "🟢 Nouveau": 5,
        "🟡 Qualification": 20,
        "🔵 RDV programmé": 45,
        "🟣 Proposition envoyée": 65,
        "🟠 Négociation": 85,
        "🟢 Client": 100,
        "🔴 Perdu": 0,
    }

    @staticmethod
    def _present(value) -> bool:
        return value is not None and str(value).strip() not in {"", "nan", "None"}

    @staticmethod
    def _clamp(value: float) -> int:
        return min(100, max(0, int(round(value))))

    @staticmethod
    def _parse_date(value) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None

    @classmethod
    def calculate(cls, prospect: dict, activity_count: int = 0, note_count: int = 0) -> ProspectScore:
        reasons: list[str] = []

        present_count = sum(cls._present(prospect.get(field)) for field in cls.PROFILE_FIELDS)
        completeness = cls._clamp((present_count / len(cls.PROFILE_FIELDS)) * 100)

        potential = 10
        if cls._present(prospect.get("siret")) or cls._present(prospect.get("siren")):
            potential += 25
        if cls._present(prospect.get("code_naf")):
            potential += 20
        if cls._present(prospect.get("site_web")):
            potential += 20
        if cls._present(prospect.get("linkedin")):
            potential += 15
        if str(prospect.get("statut_enrichissement") or "").strip() == "Enrichi":
            potential += 10
        potential = cls._clamp(potential)

        pipeline = str(prospect.get("pipeline") or "🟢 Nouveau").strip()
        pipeline_score = cls.PIPELINE_POINTS.get(pipeline, 5)
        engagement = cls._clamp(
            pipeline_score * 0.55
            + min(activity_count, 8) * 5
            + min(note_count, 5) * 4
            + (10 if cls._present(prospect.get("commercial_assigne")) else 0)
        )

        priority_text = str(prospect.get("priorite") or "")
        priority_score = min(priority_text.count("⭐") * 20, 100)
        action_date = cls._parse_date(prospect.get("date_prochaine_action"))
        date_score = 0
        if action_date:
            delta = (action_date - date.today()).days
            if delta < 0:
                date_score = 100
            elif delta <= 2:
                date_score = 90
            elif delta <= 7:
                date_score = 65
            elif delta <= 30:
                date_score = 35
        action_score = 25 if cls._present(prospect.get("prochaine_action")) and str(prospect.get("prochaine_action")) != "Aucune" else 0
        urgency = cls._clamp(priority_score * 0.45 + date_score * 0.40 + action_score)

        contactability = sum(cls._present(prospect.get(f)) for f in cls.CONTACT_FIELDS) / len(cls.CONTACT_FIELDS) * 100
        conversion = cls._clamp(
            contactability * 0.20 + potential * 0.20 + engagement * 0.35
            + urgency * 0.10 + pipeline_score * 0.15
        )
        if pipeline == "🟢 Client":
            conversion = 100
        elif pipeline == "🔴 Perdu":
            conversion = 0

        risk = 100
        risk -= contactability * 0.35
        risk -= completeness * 0.20
        risk -= engagement * 0.25
        risk -= potential * 0.10
        if action_date:
            risk -= 10
        if pipeline == "🔴 Perdu":
            risk = 100
        elif pipeline == "🟢 Client":
            risk = 0
        risk = cls._clamp(risk)

        score = cls._clamp(
            completeness * 0.15 + potential * 0.20 + engagement * 0.25
            + urgency * 0.15 + conversion * 0.25 - risk * 0.10
        )

        if score >= 85:
            grade, label = "★★★★★", "Très chaud"
        elif score >= 70:
            grade, label = "★★★★☆", "Chaud"
        elif score >= 50:
            grade, label = "★★★☆☆", "À travailler"
        elif score >= 30:
            grade, label = "★★☆☆☆", "Froid"
        else:
            grade, label = "★☆☆☆☆", "Données insuffisantes"

        reasons.extend([
            f"Complétude : {completeness}/100",
            f"Potentiel entreprise : {potential}/100",
            f"Engagement commercial : {engagement}/100 ({activity_count} activité(s), {note_count} note(s))",
            f"Urgence : {urgency}/100",
            f"Probabilité de conversion : {conversion}/100",
            f"Risque commercial : {risk}/100",
            f"Pipeline analysé : {pipeline}",
        ])
        return ProspectScore(score, grade, label, tuple(reasons), completeness, potential, engagement, urgency, conversion, risk)

    @classmethod
    def _row_to_dict(cls, row) -> dict:
        return dict(zip(cls.SCORE_COLUMNS, row))

    @classmethod
    def score_prospect_with_connection(cls, conn: sqlite3.Connection, prospect_id: int) -> ProspectScore:
        cur = conn.cursor()
        cur.execute(f"SELECT {', '.join(cls.SCORE_COLUMNS)} FROM prospects WHERE id = ?", (prospect_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Prospect {prospect_id} introuvable.")

        cur.execute("SELECT COUNT(*) FROM activities WHERE prospect_id = ?", (prospect_id,))
        activity_count = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM notes WHERE prospect_id = ?", (prospect_id,))
        note_count = int(cur.fetchone()[0])
        result = cls.calculate(cls._row_to_dict(row), activity_count, note_count)
        now = datetime.now().isoformat(timespec="seconds")

        cur.execute(
            """
            UPDATE prospects SET
                score_prospect=?, score_grade=?, score_label=?, score_details=?, date_score=?,
                score_completude=?, score_potentiel=?, score_engagement=?, score_urgence=?,
                score_conversion=?, score_risque=?, score_version=?
            WHERE id=?
            """,
            (result.score, result.grade, result.label, result.details_json, now,
             result.completeness, result.potential, result.engagement, result.urgency,
             result.conversion, result.risk, cls.VERSION, prospect_id),
        )

        cur.execute(
            "SELECT score_global, score_completude, score_potentiel, score_engagement, score_urgence, score_conversion, score_risque "
            "FROM prospect_score_history WHERE prospect_id=? ORDER BY id DESC LIMIT 1",
            (prospect_id,),
        )
        previous = cur.fetchone()
        snapshot = (result.score, result.completeness, result.potential, result.engagement, result.urgency, result.conversion, result.risk)
        if previous != snapshot:
            cur.execute(
                """
                INSERT INTO prospect_score_history(
                    prospect_id, score_global, score_completude, score_potentiel,
                    score_engagement, score_urgence, score_conversion, score_risque,
                    grade, label, details_json, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (prospect_id, *snapshot, result.grade, result.label, result.details_json, now),
            )
        return result

    @classmethod
    def score_prospect(cls, database_path: str | Path, prospect_id: int) -> ProspectScore:
        init_database(database_path)
        conn = connect_database(database_path)
        try:
            result = cls.score_prospect_with_connection(conn, prospect_id)
            conn.commit()
            return result
        finally:
            conn.close()

    @classmethod
    def get_history(cls, database_path: str | Path, prospect_id: int, limit: int = 20) -> list[dict]:
        init_database(database_path)
        conn = connect_database(database_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM prospect_score_history WHERE prospect_id=? ORDER BY id DESC LIMIT ?",
                (prospect_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @classmethod
    def score_all(cls, database_path, progress_callback=None) -> dict:
        init_database(database_path)
        conn = connect_database(database_path)
        try:
            ids = [row[0] for row in conn.execute("SELECT id FROM prospects ORDER BY id ASC").fetchall()]
            distribution = {"★★★★★": 0, "★★★★☆": 0, "★★★☆☆": 0, "★★☆☆☆": 0, "★☆☆☆☆": 0}
            for index, prospect_id in enumerate(ids, start=1):
                score = cls.score_prospect_with_connection(conn, prospect_id)
                distribution[score.grade] += 1
                if progress_callback:
                    progress_callback(index, len(ids), score)
            conn.commit()
            return {"total": len(ids), "distribution": distribution, "version": cls.VERSION}
        finally:
            conn.close()
