from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .formaprof_knowledge import FormAProfKnowledge
from .qualification_service import QualificationService


@dataclass(frozen=True)
class ProspectRecommendation:
    prospect_id: int
    entreprise: str
    score: int
    grade: str
    label: str
    pipeline: str
    telephone: str
    email: str
    prochaine_action: str
    date_prochaine_action: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AssistantInsight:
    title: str
    message: str
    level: str = "info"


class AssistantService:
    """Copilote commercial local et explicable.

    Cette première version ne transmet aucune donnée à un service externe. Elle
    analyse la base SQLite du projet, exploite le scoring existant et génère des
    recommandations, scripts d'appel et e-mails personnalisables.
    """

    HISTORY_LIMIT = 100

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self._ensure_history_table()

    def _connect(self):
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_history_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    prospect_id INTEGER,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS commercial_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prospect_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual'
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_commercial_memory_prospect
                ON commercial_memory(prospect_id, created_at DESC)
                """
            )
            conn.commit()

    @staticmethod
    def _text(value) -> str:
        return str(value or "").strip()

    @staticmethod
    def _parse_date(value: str):
        value = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def dashboard_summary(self) -> dict:
        today = date.today()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN COALESCE(TRIM(telephone), '') != '' THEN 1 ELSE 0 END) AS phones,
                    SUM(CASE WHEN COALESCE(TRIM(email), '') != '' THEN 1 ELSE 0 END) AS emails,
                    SUM(CASE WHEN COALESCE(TRIM(site_web), '') != '' THEN 1 ELSE 0 END) AS sites,
                    SUM(CASE WHEN COALESCE(score_prospect, 0) >= 65 THEN 1 ELSE 0 END) AS priorities,
                    SUM(CASE WHEN COALESCE(TRIM(statut_enrichissement), '') = 'Enrichi' THEN 1 ELSE 0 END) AS enriched,
                    AVG(COALESCE(score_prospect, 0)) AS average_score
                FROM prospects
                """
            ).fetchone()
            action_rows = conn.execute(
                """
                SELECT date_prochaine_action
                FROM prospects
                WHERE COALESCE(TRIM(date_prochaine_action), '') != ''
                """
            ).fetchall()

        due_today = 0
        overdue = 0
        for item in action_rows:
            parsed = self._parse_date(item[0])
            if parsed == today:
                due_today += 1
            elif parsed and parsed < today:
                overdue += 1

        total = int(row["total"] or 0)
        contact_fields = int(row["phones"] or 0) + int(row["emails"] or 0) + int(row["sites"] or 0)
        quality = round(contact_fields / (total * 3) * 100) if total else 0
        return {
            "total": total,
            "phones": int(row["phones"] or 0),
            "emails": int(row["emails"] or 0),
            "sites": int(row["sites"] or 0),
            "priorities": int(row["priorities"] or 0),
            "enriched": int(row["enriched"] or 0),
            "average_score": round(float(row["average_score"] or 0), 1),
            "quality": quality,
            "due_today": due_today,
            "overdue": overdue,
        }

    def insights(self) -> list[AssistantInsight]:
        data = self.dashboard_summary()
        insights: list[AssistantInsight] = []
        if data["overdue"]:
            insights.append(AssistantInsight(
                "Relances en retard",
                f"{data['overdue']} prospect(s) ont une action dépassée. Traitez-les en priorité.",
                "warning",
            ))
        if data["due_today"]:
            insights.append(AssistantInsight(
                "Actions du jour",
                f"{data['due_today']} action(s) commerciale(s) sont prévues aujourd'hui.",
                "info",
            ))
        if data["priorities"]:
            insights.append(AssistantInsight(
                "Prospects prioritaires",
                f"{data['priorities']} prospect(s) ont un score supérieur ou égal à 65/100.",
                "success",
            ))
        missing_phones = max(0, data["total"] - data["phones"])
        missing_emails = max(0, data["total"] - data["emails"])
        if missing_phones or missing_emails:
            insights.append(AssistantInsight(
                "Qualité de la base",
                f"Il manque encore {missing_phones} téléphone(s) et {missing_emails} e-mail(s).",
                "info",
            ))
        if not insights:
            insights.append(AssistantInsight(
                "Base prête",
                "Aucune alerte prioritaire. Vous pouvez poursuivre la prospection.",
                "success",
            ))
        return insights

    def top_prospects(self, limit: int = 25) -> list[ProspectRecommendation]:
        safe_limit = max(1, min(int(limit), 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, entreprise, COALESCE(score_prospect, 0) AS score_prospect,
                       COALESCE(score_grade, '★☆☆☆☆') AS score_grade,
                       COALESCE(score_label, 'Données insuffisantes') AS score_label,
                       COALESCE(pipeline, '🟢 Nouveau') AS pipeline,
                       COALESCE(telephone, '') AS telephone,
                       COALESCE(email, '') AS email,
                       COALESCE(prochaine_action, 'Aucune') AS prochaine_action,
                       COALESCE(date_prochaine_action, '') AS date_prochaine_action,
                       COALESCE(site_web, '') AS site_web,
                       COALESCE(linkedin, '') AS linkedin
                FROM prospects
                ORDER BY score_prospect DESC,
                         CASE WHEN COALESCE(TRIM(telephone), '') != '' THEN 0 ELSE 1 END,
                         CASE WHEN COALESCE(TRIM(email), '') != '' THEN 0 ELSE 1 END,
                         id ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        results = []
        for row in rows:
            reasons = []
            if self._text(row["telephone"]):
                reasons.append("Téléphone disponible")
            if self._text(row["email"]):
                reasons.append("E-mail disponible")
            if self._text(row["site_web"]):
                reasons.append("Site internet identifié")
            if self._text(row["linkedin"]):
                reasons.append("Présence LinkedIn")
            if not reasons:
                reasons.append("Enrichissement complémentaire recommandé")
            results.append(ProspectRecommendation(
                prospect_id=int(row["id"]),
                entreprise=self._text(row["entreprise"]) or "Entreprise sans nom",
                score=int(row["score_prospect"] or 0),
                grade=self._text(row["score_grade"]) or "★☆☆☆☆",
                label=self._text(row["score_label"]) or "Données insuffisantes",
                pipeline=self._text(row["pipeline"]) or "🟢 Nouveau",
                telephone=self._text(row["telephone"]),
                email=self._text(row["email"]),
                prochaine_action=self._text(row["prochaine_action"]) or "Aucune",
                date_prochaine_action=self._text(row["date_prochaine_action"]),
                reasons=tuple(reasons),
            ))
        return results

    def search_prospects(
        self,
        query: str,
        limit: int = 100,
    ) -> list[ProspectRecommendation]:
        clean_query = self._text(query).lower()
        if not clean_query:
            return self.top_prospects(limit)

        safe_limit = max(1, min(int(limit), 500))
        fields = (
            "entreprise",
            "siret",
            "ville",
            "telephone",
            "email",
            "code_naf",
        )
        tokens = [token for token in clean_query.split() if token]
        conditions = []
        parameters = []
        for token in tokens:
            conditions.append(
                "(" + " OR ".join(
                    f"LOWER(COALESCE({field}, '')) LIKE ?"
                    for field in fields
                ) + ")"
            )
            parameters.extend([f"%{token}%"] * len(fields))
        parameters.append(safe_limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, entreprise, COALESCE(score_prospect, 0) AS score_prospect,
                       COALESCE(score_grade, '★☆☆☆☆') AS score_grade,
                       COALESCE(score_label, 'Données insuffisantes') AS score_label,
                       COALESCE(pipeline, '🟢 Nouveau') AS pipeline,
                       COALESCE(telephone, '') AS telephone,
                       COALESCE(email, '') AS email,
                       COALESCE(prochaine_action, 'Aucune') AS prochaine_action,
                       COALESCE(date_prochaine_action, '') AS date_prochaine_action,
                       COALESCE(site_web, '') AS site_web,
                       COALESCE(linkedin, '') AS linkedin
                FROM prospects
                WHERE {' AND '.join(conditions)}
                ORDER BY
                    CASE
                        WHEN LOWER(COALESCE(entreprise, '')) = ? THEN 0
                        WHEN LOWER(COALESCE(entreprise, '')) LIKE ? THEN 1
                        ELSE 2
                    END,
                    score_prospect DESC,
                    entreprise COLLATE NOCASE ASC,
                    id ASC
                LIMIT ?
                """,
                parameters[:-1]
                + [clean_query, f"{clean_query}%", parameters[-1]],
            ).fetchall()

        results = []
        for row in rows:
            reasons = []
            if self._text(row["telephone"]):
                reasons.append("Téléphone disponible")
            if self._text(row["email"]):
                reasons.append("E-mail disponible")
            if self._text(row["site_web"]):
                reasons.append("Site internet identifié")
            if self._text(row["linkedin"]):
                reasons.append("Présence LinkedIn")
            if not reasons:
                reasons.append("Enrichissement complémentaire recommandé")
            results.append(ProspectRecommendation(
                prospect_id=int(row["id"]),
                entreprise=self._text(row["entreprise"]) or "Entreprise sans nom",
                score=int(row["score_prospect"] or 0),
                grade=self._text(row["score_grade"]) or "★☆☆☆☆",
                label=self._text(row["score_label"]) or "Données insuffisantes",
                pipeline=self._text(row["pipeline"]) or "🟢 Nouveau",
                telephone=self._text(row["telephone"]),
                email=self._text(row["email"]),
                prochaine_action=self._text(row["prochaine_action"]) or "Aucune",
                date_prochaine_action=self._text(row["date_prochaine_action"]),
                reasons=tuple(reasons),
            ))
        return results

    def get_prospect(self, prospect_id: int) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM prospects WHERE id = ?", (int(prospect_id),)).fetchone()
        if row is None:
            raise ValueError("Prospect introuvable.")
        return dict(row)

    def explain_score(self, prospect_id: int) -> str:
        prospect = self.get_prospect(prospect_id)
        name = self._text(prospect.get("entreprise")) or "Ce prospect"
        score = int(prospect.get("score_prospect") or 0)
        grade = self._text(prospect.get("score_grade")) or "★☆☆☆☆"
        lines = [f"{name} obtient {score}/100 ({grade}).", ""]
        positive = []
        missing = []
        checks = (
            ("telephone", "Téléphone"), ("email", "E-mail"), ("site_web", "Site web"),
            ("linkedin", "LinkedIn"), ("siret", "SIRET"), ("code_naf", "Code NAF"),
        )
        for key, label in checks:
            (positive if self._text(prospect.get(key)) else missing).append(label)
        if positive:
            lines.append("Points forts : " + ", ".join(positive) + ".")
        if missing:
            lines.append("À compléter : " + ", ".join(missing) + ".")
        if score >= 65:
            lines.append("Recommandation : contact prioritaire avec une approche directe et personnalisée.")
        elif score >= 45:
            lines.append("Recommandation : qualifier le besoin avant une proposition commerciale.")
        else:
            lines.append("Recommandation : enrichir les données avant de lancer la prospection.")
        content = "\n".join(lines)
        self.save_history("score", prospect_id, f"Explication du score — {name}", content)
        return content

    def next_action(self, prospect_id: int) -> str:
        p = self.get_prospect(prospect_id)
        name = self._text(p.get("entreprise")) or "ce prospect"
        score = int(p.get("score_prospect") or 0)
        phone = self._text(p.get("telephone"))
        email = self._text(p.get("email"))
        pipeline = self._text(p.get("pipeline"))
        if score >= 65 and phone:
            content = f"Appelez {name} en priorité. Préparez une accroche courte centrée sur le gain de temps et le pilotage commercial."
        elif email:
            content = f"Envoyez un e-mail personnalisé à {name}, puis programmez une relance téléphonique sous 2 à 3 jours."
        elif phone:
            content = f"Appelez {name} pour qualifier le décideur, le besoin et l'échéance du projet."
        else:
            content = f"Enrichissez les coordonnées de {name} avant toute action commerciale."
        if "Client" in pipeline:
            content = f"Planifiez un suivi de satisfaction et identifiez une opportunité de vente complémentaire pour {name}."
        self.save_history("action", prospect_id, f"Prochaine action — {name}", content)
        return content




    MEMORY_TYPES = (
        "Besoin",
        "Outil actuel",
        "Difficulté",
        "Objection",
        "Décision",
        "Prochaine étape",
        "Contexte",
        "Autre",
    )

    def add_commercial_memory(
        self,
        prospect_id: int,
        content: str,
        memory_type: str = "Contexte",
        source: str = "manual",
    ) -> int:
        self.get_prospect(prospect_id)
        clean_content = self._text(content)
        clean_type = self._text(memory_type) or "Contexte"
        clean_source = self._text(source) or "manual"
        if not clean_content:
            raise ValueError("La mémoire commerciale ne peut pas être vide.")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO commercial_memory(
                    prospect_id, created_at, memory_type, content, source
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(prospect_id),
                    datetime.now().isoformat(timespec="seconds"),
                    clean_type,
                    clean_content,
                    clean_source,
                ),
            )
            conn.commit()
            memory_id = int(cursor.lastrowid)
        return memory_id

    def commercial_memories(self, prospect_id: int, limit: int = 100) -> list[dict]:
        self.get_prospect(prospect_id)
        safe_limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, prospect_id, created_at, memory_type, content, source
                FROM commercial_memory
                WHERE prospect_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (int(prospect_id), safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_commercial_memory(self, memory_id: int, prospect_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM commercial_memory
                WHERE id = ? AND prospect_id = ?
                """,
                (int(memory_id), int(prospect_id)),
            )
            conn.commit()
        return cursor.rowcount > 0

    def commercial_memory_report(self, prospect_id: int) -> str:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "Entreprise sans nom"
        memories = self.commercial_memories(prospect_id, 200)

        with self._connect() as conn:
            history_rows = conn.execute(
                """
                SELECT created_at, action_type, title, content
                FROM ai_history
                WHERE prospect_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 20
                """,
                (int(prospect_id),),
            ).fetchall()

        if not memories and not history_rows:
            content = (
                f"MÉMOIRE COMMERCIALE — {company}\n"
                f"{'=' * 58}\n\n"
                "Aucune information commerciale n'a encore été mémorisée pour ce prospect.\n\n"
                "Ajoutez après chaque échange :\n"
                "• les outils actuellement utilisés ;\n"
                "• les difficultés exprimées ;\n"
                "• les besoins prioritaires ;\n"
                "• les objections ;\n"
                "• la décision et la prochaine étape."
            )
            self.save_history(
                "commercial_memory_report",
                prospect_id,
                f"Mémoire commerciale — {company}",
                content,
            )
            return content

        grouped: dict[str, list[dict]] = {}
        for item in memories:
            grouped.setdefault(item["memory_type"], []).append(item)

        lines = [
            f"MÉMOIRE COMMERCIALE — {company}",
            "=" * 58,
            "",
            "SYNTHÈSE INTELLIGENTE",
            f"• {len(memories)} information(s) commerciale(s) enregistrée(s).",
            f"• {len(history_rows)} génération(s) IA récente(s) liée(s) au prospect.",
        ]

        priority_order = [
            "Besoin",
            "Difficulté",
            "Outil actuel",
            "Objection",
            "Décision",
            "Prochaine étape",
            "Contexte",
            "Autre",
        ]
        for memory_type in priority_order:
            items = grouped.get(memory_type, [])
            if not items:
                continue
            latest = items[0]
            lines.append(
                f"• Dernier élément « {memory_type} » : {latest['content']}"
            )

        lines.extend(["", "HISTORIQUE COMMERCIAL"])
        for item in memories:
            date_text = item["created_at"].replace("T", " ")
            lines.extend([
                f"[{date_text}] {item['memory_type']}",
                item["content"],
                "",
            ])

        if history_rows:
            lines.extend(["ACTIVITÉ IA RÉCENTE"])
            for row in history_rows:
                date_text = row["created_at"].replace("T", " ")
                lines.append(f"• {date_text} — {row['title']}")

        lines.extend([
            "",
            "RECOMMANDATION POUR LE PROCHAIN CONTACT",
            "Relisez les besoins, difficultés, objections et décisions avant l'appel. "
            "Commencez l'échange en rappelant un élément concret déjà évoqué afin que "
            "le prospect sente que son contexte est compris et suivi.",
        ])

        content = "\n".join(lines)
        self.save_history(
            "commercial_memory_report",
            prospect_id,
            f"Mémoire commerciale — {company}",
            content,
        )
        return content

    def automatic_qualification(self, prospect_id: int) -> dict:
        prospect = self.get_prospect(prospect_id)
        memories = self.commercial_memories(prospect_id, 200)
        result = QualificationService.calculate(prospect, memories)
        return {
            "total": result.total,
            "coordinates": result.coordinates,
            "decision_maker": result.decision_maker,
            "activity": result.activity,
            "digital": result.digital,
            "history": result.history,
            "confidence": result.confidence,
            "maturity": result.maturity,
            "urgency": result.urgency,
            "potential": result.potential,
            "recommended_action": result.recommended_action,
            "strengths": list(result.strengths),
            "weaknesses": list(result.weaknesses),
            "missing": list(result.missing),
        }

    def automatic_qualification_report(self, prospect_id: int) -> str:
        prospect = self.get_prospect(prospect_id)
        company = self._text(prospect.get("entreprise")) or "Entreprise sans nom"
        q = self.automatic_qualification(prospect_id)
        strengths = "\n".join(f"✓ {x}" for x in q["strengths"]) or "• Aucun point fort identifié"
        weaknesses = "\n".join(f"• {x}" for x in q["weaknesses"]) or "• Aucun point faible majeur"
        missing = "\n".join(f"• {x}" for x in q["missing"]) or "• Aucune information essentielle manquante"
        content = (
            f"QUALIFICATION AUTOMATIQUE — {company}\n"
            f"{'=' * 58}\n\n"
            f"SCORE GLOBAL : {q['total']}/100\n"
            f"MATURITÉ : {q['maturity']}\n"
            f"POTENTIEL : {q['potential']}\n"
            f"URGENCE : {q['urgency']}\n"
            f"CONFIANCE IA : {q['confidence']} %\n\n"
            "DÉTAIL DU SCORE\n"
            f"• Coordonnées : {q['coordinates']}/20\n"
            f"• Décideur : {q['decision_maker']}/20\n"
            f"• Activité : {q['activity']}/20\n"
            f"• Présence digitale : {q['digital']}/15\n"
            f"• Historique commercial : {q['history']}/25\n\n"
            "POINTS FORTS\n" + strengths + "\n\n"
            "POINTS FAIBLES\n" + weaknesses + "\n\n"
            "INFORMATIONS À COMPLÉTER\n" + missing + "\n\n"
            "ACTION RECOMMANDÉE\n" + q['recommended_action'] + "\n\n"
            "LECTURE DU DIAGNOSTIC\n"
            "Le score est explicable et repose uniquement sur les données de la fiche, "
            "la mémoire commerciale et les échéances enregistrées. Il n'utilise aucune donnée externe."
        )
        self.save_history("automatic_qualification", prospect_id, f"Qualification automatique — {company}", content)
        return content

    def prospect_copilot(self, prospect_id: int) -> dict:
        """Construit le tableau de bord IA d'un prospect sélectionné."""
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "Entreprise sans nom"
        city = self._text(p.get("ville"))
        activity = self._text(p.get("activite")) or self._text(p.get("code_naf")) or "BTP"
        score = int(p.get("score_prospect") or 0)
        pipeline = self._text(p.get("pipeline")) or "🟢 Nouveau"
        phone = self._text(p.get("telephone"))
        email = self._text(p.get("email"))
        website = self._text(p.get("site_web"))
        linkedin = self._text(p.get("linkedin"))
        siret = self._text(p.get("siret"))
        dirigeant = (
            self._text(p.get("dirigeant"))
            or self._text(p.get("nom_dirigeant"))
            or self._text(p.get("contact"))
        )

        completeness_fields = [phone, email, website, linkedin, siret, dirigeant, city, activity]
        completeness = round(sum(bool(v) for v in completeness_fields) / len(completeness_fields) * 100)

        if score >= 75 and phone:
            priority = "Très haute"
            objective = "Obtenir un rendez-vous de découverte de 20 minutes"
            action = "Appeler aujourd'hui avec l'argument formation + outil sur mesure"
            probability = "Forte"
        elif score >= 55 and (phone or email):
            priority = "Haute"
            objective = "Qualifier le besoin et identifier le décideur"
            action = "Appeler ou envoyer un e-mail personnalisé puis relancer sous 3 jours"
            probability = "Moyenne à forte"
        elif phone or email:
            priority = "Moyenne"
            objective = "Comprendre l'organisation actuelle"
            action = "Lancer une première prise de contact puis enrichir les données"
            probability = "Moyenne"
        else:
            priority = "À enrichir"
            objective = "Compléter les coordonnées avant prospection"
            action = "Rechercher un téléphone, un e-mail ou le dirigeant"
            probability = "Faible à ce stade"

        missing = []
        for label, value in (
            ("téléphone", phone),
            ("e-mail", email),
            ("site internet", website),
            ("LinkedIn", linkedin),
            ("SIRET", siret),
            ("dirigeant / contact", dirigeant),
            ("ville", city),
        ):
            if not value:
                missing.append(label)

        reasons = []
        if score >= 65:
            reasons.append("score commercial élevé")
        if phone:
            reasons.append("téléphone disponible")
        if email:
            reasons.append("e-mail disponible")
        if activity and activity != "BTP":
            reasons.append(f"activité identifiée : {activity}")
        if city:
            reasons.append(f"implantation connue : {city}")
        if not reasons:
            reasons.append("informations encore insuffisantes")

        arguments = [
            "Formation pratique adaptée au fonctionnement de l'entreprise",
            "Analyse concrète des besoins et des méthodes actuelles",
            "Création d'un outil de pilotage personnalisé",
            "Prise en charge possible selon l'éligibilité et l'accord du financeur",
            "Accompagnement qualité pendant douze mois",
        ]

        summary = (
            f"{company} est une entreprise du secteur {activity}"
            + (f" située à {city}" if city else "")
            + f". Son score commercial est de {score}/100 et elle se trouve dans le pipeline « {pipeline} »."
        )

        return {
            "prospect_id": int(prospect_id),
            "company": company,
            "summary": summary,
            "score": score,
            "pipeline": pipeline,
            "priority": priority,
            "probability": probability,
            "objective": objective,
            "recommended_action": action,
            "completeness": completeness,
            "missing": missing,
            "reasons": reasons,
            "arguments": arguments,
        }

    def prospect_copilot_report(self, prospect_id: int) -> str:
        data = self.prospect_copilot(prospect_id)
        missing_text = "\n".join(f"• {item}" for item in data["missing"]) or "• Aucune donnée essentielle manquante"
        reasons_text = "\n".join(f"• {item}" for item in data["reasons"])
        arguments_text = "\n".join(f"• {item}" for item in data["arguments"])
        content = (
            f"COPILOTE PROSPECT — {data['company']}\n"
            f"{'=' * 58}\n\n"
            "RÉSUMÉ\n"
            f"{data['summary']}\n\n"
            "PRIORITÉ COMMERCIALE\n"
            f"{data['priority']}\n\n"
            "PROBABILITÉ ESTIMÉE D'INTÉRÊT\n"
            f"{data['probability']}\n\n"
            "OBJECTIF CONSEILLÉ\n"
            f"{data['objective']}\n\n"
            "PROCHAINE ACTION\n"
            f"{data['recommended_action']}\n\n"
            "QUALITÉ DES INFORMATIONS\n"
            f"{data['completeness']} % de complétude\n\n"
            "POURQUOI CE PROSPECT ?\n"
            f"{reasons_text}\n\n"
            "INFORMATIONS À COMPLÉTER\n"
            f"{missing_text}\n\n"
            "ARGUMENTS FORM@PROF À METTRE EN AVANT\n"
            f"{arguments_text}\n\n"
            "RAPPEL\n"
            "L'objectif n'est pas de vendre immédiatement, mais d'obtenir un échange de découverte "
            "et de vérifier si la formation et l'outil de pilotage sur mesure répondent à un besoin réel."
        )
        self.save_history(
            "prospect_copilot",
            prospect_id,
            f"Copilote prospect — {data['company']}",
            content,
        )
        return content

    def call_preparation(self, prospect_id: int) -> str:
        """Prépare un appel complet à partir du prospect et du Knowledge Engine."""
        p = self.get_prospect(prospect_id)
        engine = FormAProfKnowledge.engine()

        company = self._text(p.get("entreprise")) or "Entreprise sans nom"
        city = self._text(p.get("ville"))
        activity = self._text(p.get("activite")) or self._text(p.get("code_naf")) or "BTP"
        score = int(p.get("score_prospect") or 0)
        grade = self._text(p.get("score_grade")) or "★☆☆☆☆"
        pipeline = self._text(p.get("pipeline")) or "🟢 Nouveau"
        phone = self._text(p.get("telephone"))
        email = self._text(p.get("email"))
        site = self._text(p.get("site_web"))
        linkedin = self._text(p.get("linkedin"))
        siret = self._text(p.get("siret"))
        dirigeant = (
            self._text(p.get("dirigeant"))
            or self._text(p.get("nom_dirigeant"))
            or self._text(p.get("contact"))
        )

        fields = {
            "Téléphone": phone,
            "E-mail": email,
            "Site internet": site,
            "LinkedIn": linkedin,
            "SIRET": siret,
            "Dirigeant / contact": dirigeant,
            "Activité": activity if activity != "BTP" else "",
            "Ville": city,
        }
        present = sum(1 for value in fields.values() if value)
        readiness = round((present / len(fields)) * 70 + min(max(score, 0), 100) * 0.30)
        readiness = max(0, min(readiness, 100))
        if readiness >= 80:
            readiness_label = "🟢 Prêt à appeler"
        elif readiness >= 55:
            readiness_label = "🟠 Appel possible — quelques informations manquent"
        else:
            readiness_label = "🔴 Enrichissement recommandé avant l'appel"

        missing = [label for label, value in fields.items() if not value]
        missing_text = "\n".join(f"• {item}" for item in missing) if missing else "• Aucune information essentielle manquante"

        questions = engine.qualification_questions()
        selected_questions = questions[:6]
        questions_text = "\n".join(f"☐ {question}" for question in selected_questions)

        objections = engine.objections()
        likely_ids = ["already_excel", "already_erp", "no_time", "send_email"]
        selected_objections = [item for item in objections if item.get("id") in likely_ids]
        objection_lines = []
        for index, item in enumerate(selected_objections, start=1):
            objection_lines.extend([
                f"{index}. « {item.get('prospect_says', '')} »",
                f"   Réponse : {item.get('response', '')}",
                f"   Rebond : {item.get('follow_up_question', '')}",
                "",
            ])
        objections_text = "\n".join(objection_lines).rstrip()

        funding_wording = engine.funding().get("mandatory_wording", FormAProfKnowledge.FUNDING_WORDING)
        intro_context = f" à {city}" if city else ""
        decision_maker = f" auprès de {dirigeant}" if dirigeant else ""

        content = (
            f"PRÉPARATION D'APPEL — {company}\n"
            f"{'=' * 58}\n\n"
            "1. FICHE EXPRESS DU PROSPECT\n"
            f"Entreprise : {company}\n"
            f"Activité : {activity}\n"
            f"Localisation : {city or 'Non renseignée'}\n"
            f"Contact : {dirigeant or 'Non renseigné'}\n"
            f"Téléphone : {phone or 'Non renseigné'}\n"
            f"E-mail : {email or 'Non renseigné'}\n"
            f"Pipeline : {pipeline}\n"
            f"Score commercial : {score}/100 — {grade}\n\n"
            "2. SCORE DE PRÉPARATION\n"
            f"{readiness_label} — {readiness} %\n\n"
            "Informations à compléter :\n"
            f"{missing_text}\n\n"
            "3. OBJECTIF DE L'APPEL\n"
            "• Comprendre l'organisation actuelle de l'entreprise.\n"
            "• Identifier les difficultés de suivi et de pilotage.\n"
            "• Présenter la formation pratique et la création de l'outil sur mesure.\n"
            "• Obtenir un rendez-vous de découverte d'environ vingt minutes.\n\n"
            "4. ACCROCHE CONSEILLÉE\n"
            f"Bonjour Monsieur/Madame, je suis [Prénom] de Form@Prof – Up Your Skills. "
            f"Je me permets de vous contacter au sujet de {company}{intro_context}. "
            f"Nous accompagnons les entreprises du secteur {activity} dans l'organisation "
            "et le pilotage de leur activité grâce à une formation pratique, suivie de la "
            "création d'un outil de pilotage entièrement adapté à leur fonctionnement.\n\n"
            "5. QUESTION D'OUVERTURE\n"
            "Aujourd'hui, comment suivez-vous vos devis, vos chantiers, vos règlements "
            "et la rentabilité de votre activité ?\n\n"
            "6. QUESTIONS DE DÉCOUVERTE\n"
            f"{questions_text}\n\n"
            "7. PROPOSITION DE VALEUR FORM@PROF\n"
            "Nous commençons par analyser le fonctionnement de l'entreprise pendant une "
            "formation concrète et directement adaptée à ses besoins. À l'issue de cette "
            "formation, nous créons avec l'entreprise un outil de pilotage sur mesure pour "
            "centraliser les informations, réduire les doubles saisies et faciliter les décisions.\n\n"
            "8. QUALIOPI ET FINANCEMENT\n"
            f"{funding_wording}\n\n"
            "9. ACCOMPAGNEMENT QUALITÉ\n"
            f"{FormAProfKnowledge.QUALITY_SUPPORT}\n\n"
            "10. OBJECTIONS PROBABLES ET RÉPONSES\n"
            f"{objections_text}\n\n"
            "11. CONCLUSION CONSEILLÉE\n"
            "L'objectif de mon appel n'est pas de vous vendre quelque chose immédiatement. "
            "Je souhaite simplement comprendre votre fonctionnement et vérifier si notre "
            "accompagnement peut réellement vous faire gagner du temps et améliorer votre "
            f"pilotage{decision_maker}. Seriez-vous disponible pour un échange d'une vingtaine "
            "de minutes cette semaine ?\n\n"
            "12. CONSIGNE AU COMMERCIAL\n"
            "Écoutez davantage que vous ne parlez. Notez les outils utilisés, les irritants, "
            "les personnes impliquées, l'urgence et la prochaine action convenue."
        )
        self.save_history(
            "call_preparation",
            prospect_id,
            f"Préparation d'appel — {company}",
            content,
        )
        return content

    def call_script(self, prospect_id: int) -> str:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "votre entreprise"
        city = self._text(p.get("ville"))
        activity = self._text(p.get("activite")) or self._text(p.get("code_naf"))
        context = f" située à {city}" if city else ""
        activity_line = f" dans votre activité ({activity})" if activity else " dans le BTP"
        questions = "\n".join(f"• {q}" for q in FormAProfKnowledge.QUALIFICATION_QUESTIONS[:4])
        benefits = "\n".join(f"• {b.capitalize()}." for b in FormAProfKnowledge.BUSINESS_BENEFITS)
        content = (
            f"SCRIPT D'APPEL FORM@PROF — {company}\n\n"
            "1. ACCROCHE\n"
            "Bonjour Monsieur/Madame, je suis [Prénom] de Form@Prof – Up Your Skills. "
            f"Je me permets de vous contacter au sujet de {company}{context}. "
            f"Nous accompagnons les entreprises{activity_line} dans l'organisation et le pilotage de leur activité.\n\n"
            "2. OUVERTURE DU BESOIN\n"
            "Beaucoup de dirigeants du BTP utilisent plusieurs fichiers, un logiciel métier qui ne couvre pas tout, "
            "ou encore un suivi assez manuel. Cela peut rendre difficile le suivi des chantiers, des devis, des règlements "
            "et de la rentabilité.\n\n"
            "Aujourd'hui, comment pilotez-vous votre activité ?\n\n"
            "[Écouter la réponse et rebondir sur les difficultés évoquées]\n\n"
            "3. PRÉSENTATION DE L'ACCOMPAGNEMENT\n"
            "Notre approche repose sur une formation pratique et directement adaptée au fonctionnement de votre entreprise. "
            "Pendant la formation, nous analysons vos méthodes, vos contraintes et vos besoins. À l'issue de cette formation, "
            "nous créons avec vous un outil de pilotage personnalisé, conçu pour votre façon de travailler.\n\n"
            "Cet outil peut notamment permettre de :\n"
            f"{benefits}\n\n"
            "4. QUALIOPI ET FINANCEMENT\n"
            f"{FormAProfKnowledge.FUNDING_WORDING}\n\n"
            "5. ACCOMPAGNEMENT QUALITÉ\n"
            f"{FormAProfKnowledge.QUALITY_SUPPORT}\n\n"
            "6. QUESTIONS DE QUALIFICATION\n"
            f"{questions}\n\n"
            "7. PRISE DE RENDEZ-VOUS\n"
            "L'objectif de mon appel n'est pas de vous vendre quelque chose immédiatement, mais de comprendre votre fonctionnement "
            "et de vérifier si cet accompagnement peut réellement vous faire gagner du temps et améliorer votre visibilité. "
            "Seriez-vous disponible pour un échange d'une vingtaine de minutes cette semaine ?"
        )
        self.save_history("call_script", prospect_id, f"Script d'appel Form@Prof — {company}", content)
        return content

    def email_draft(self, prospect_id: int) -> tuple[str, str]:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "votre entreprise"
        subject = f"Pilotage de l'activité de {company} — formation et outil sur mesure"
        body = (
            "Bonjour,\n\n"
            f"Je me permets de vous contacter au sujet de {company}. {FormAProfKnowledge.BRAND} accompagne les entreprises "
            "du BTP dans l'organisation et le pilotage de leur activité.\n\n"
            "Notre accompagnement prend la forme d'une formation pratique adaptée au fonctionnement de l'entreprise. "
            "Pendant cette formation, nous analysons les besoins puis créons, à son issue, un outil de pilotage personnalisé "
            "pour centraliser notamment les devis, chantiers, règlements, relances, chiffre d'affaires et indicateurs de rentabilité.\n\n"
            f"{FormAProfKnowledge.FUNDING_WORDING}\n\n"
            f"{FormAProfKnowledge.QUALITY_SUPPORT}\n\n"
            "Je vous propose un échange d'une vingtaine de minutes afin de comprendre votre organisation actuelle et de vérifier "
            "si cet accompagnement pourrait vous apporter un gain de temps concret.\n\n"
            "Quel créneau vous conviendrait le mieux ?\n\n"
            "Bien cordialement,\n[Signature Form@Prof]"
        )
        content = f"Objet : {subject}\n\n{body}"
        self.save_history("email", prospect_id, f"E-mail Form@Prof — {company}", content)
        return subject, body

    def objection_guide(self, prospect_id: int) -> str:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "ce prospect"
        lines = [f"RÉPONSES AUX OBJECTIONS — {company}", ""]
        labels = {
            "excel": "J'utilise déjà Excel",
            "erp": "J'ai déjà un ERP / logiciel métier",
            "temps": "Je n'ai pas le temps",
            "prix": "Cela va coûter trop cher",
            "pas_besoin": "Je n'en ai pas besoin",
        }
        for key, label in labels.items():
            lines.extend([f"OBJECTION : {label}", f"RÉPONSE : {FormAProfKnowledge.OBJECTIONS[key]}", ""])
        lines.append("Rappel : ne jamais garantir une prise en charge. Toujours préciser qu'elle dépend de l'éligibilité et de l'accord du financeur.")
        content = "\n".join(lines)
        self.save_history("objections", prospect_id, f"Objections — {company}", content)
        return content

    def follow_up_plan(self, prospect_id: int) -> str:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "ce prospect"
        content = (
            f"PLAN DE RELANCE — {company}\n\n"
            "J0 — Appel de qualification : comprendre les outils actuels, les irritants et le niveau de décision.\n"
            "J0 — Envoyer un e-mail récapitulatif présentant la formation, l'outil de pilotage sur mesure, Qualiopi et l'accompagnement qualité annuel.\n"
            "J+3 — Relance téléphonique courte centrée sur le besoin exprimé lors du premier échange.\n"
            "J+7 — Partager un exemple concret de bénéfice : suivi des chantiers, rentabilité, devis ou règlements.\n"
            "J+14 — Dernière relance utile en proposant un rendez-vous de 20 minutes, sans pression commerciale.\n\n"
            "À chaque étape : personnaliser le message, consigner la réponse dans le CRM et programmer la prochaine action."
        )
        self.save_history("follow_up", prospect_id, f"Plan de relance — {company}", content)
        return content

    def knowledge_overview(self) -> str:
        content = FormAProfKnowledge.engine().overview()
        self.save_history("knowledge", None, "Base de connaissances Form@Prof", content)
        return content

    def save_history(self, action_type: str, prospect_id: int | None, title: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ai_history(created_at, action_type, prospect_id, title, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (datetime.now().isoformat(timespec="seconds"), action_type, prospect_id, title, content),
            )
            conn.commit()

    def history(self, limit: int = 30) -> list[dict]:
        safe_limit = max(1, min(int(limit), self.HISTORY_LIMIT))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, action_type, prospect_id, title, content
                FROM ai_history ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]
