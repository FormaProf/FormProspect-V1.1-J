from __future__ import annotations

import json
import os
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .assistant_service import (
    AssistantInsight,
    AssistantService,
    ProspectRecommendation,
)


class CloudAssistantService(AssistantService):
    """Assistant commercial pour une session Form@Prospect Cloud.

    Les recommandations sont calculées localement à partir des prospects que
    l'utilisateur connecté a déjà le droit de consulter. Aucune donnée n'est
    transmise à un service d'IA externe.
    """

    def __init__(self, api, *, state_path: str | Path | None = None):
        # Ne pas appeler AssistantService.__init__ : il attend une base SQLite.
        self.api = api
        self._prospects: list[dict[str, Any]] | None = None
        self._prospects_by_id: dict[str, dict[str, Any]] = {}
        self._state_path = Path(state_path) if state_path else self._default_state_path()
        self._state = self._load_state()

    @staticmethod
    def _default_state_path() -> Path:
        base = Path(os.getenv("APPDATA") or (Path.home() / ".formaprospect"))
        return base / "Form@Prospect" / "assistant_ia_cloud.json"

    def _load_state(self) -> dict[str, Any]:
        try:
            if self._state_path.is_file():
                payload = json.loads(self._state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    payload.setdefault("history", [])
                    payload.setdefault("memories", {})
                    payload.setdefault("next_memory_id", 1)
                    return payload
        except (OSError, ValueError, TypeError):
            pass
        return {"history": [], "memories": {}, "next_memory_id": 1}

    def _save_state(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._state_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self._state_path)
        except OSError:
            # L'assistant reste utilisable même si le poste interdit l'écriture.
            pass

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _grade(score: int) -> str:
        stars = max(1, min(5, (int(score) + 19) // 20))
        return "★" * stars + "☆" * (5 - stars)

    @classmethod
    def _score(cls, prospect: dict[str, Any]) -> int:
        phone = cls._text(prospect.get("phone") or prospect.get("mobile"))
        email = cls._text(prospect.get("email"))
        website = cls._text(prospect.get("website"))
        siret = cls._text(prospect.get("siret"))
        naf = cls._text(prospect.get("naf_code"))
        activity = cls._text(prospect.get("activity"))
        city = cls._text(prospect.get("city"))
        contact = cls._text(prospect.get("contact_name"))
        next_action = cls._text(prospect.get("next_action"))
        priority = cls._text(prospect.get("priority")).lower()
        pipeline = cls._text(prospect.get("pipeline_stage")).lower()

        score = 0
        score += 20 if phone else 0
        score += 15 if email else 0
        score += 8 if website else 0
        score += 10 if siret else 0
        score += 5 if naf else 0
        score += 7 if activity else 0
        score += 5 if city else 0
        score += 8 if contact else 0
        score += 5 if next_action else 0
        score += {"urgente": 17, "haute": 12, "normal": 5, "basse": 0}.get(priority, 4)

        if any(word in pipeline for word in ("qualif", "rdv", "rendez", "proposition", "devis")):
            score += 10
        elif any(word in pipeline for word in ("client", "gagne", "gagné")):
            score += 8
        elif any(word in pipeline for word in ("perdu", "refus")):
            score -= 15

        return max(0, min(100, score))

    @classmethod
    def _label(cls, score: int) -> str:
        if score >= 80:
            return "Très forte opportunité"
        if score >= 65:
            return "Opportunité forte"
        if score >= 45:
            return "À qualifier"
        if score >= 25:
            return "Priorité faible"
        return "Données à enrichir"

    def refresh(self) -> None:
        self._prospects = None
        self._prospects_by_id = {}

    def _load_all_prospects(self) -> list[dict[str, Any]]:
        if self._prospects is not None:
            return self._prospects

        rows: list[dict[str, Any]] = []
        offset = 0
        page_size = 100
        while True:
            page = self.api.list_prospects(limit=page_size, offset=offset)
            items = list(getattr(page, "items", []) or [])
            rows.extend(item for item in items if isinstance(item, dict))
            total = int(getattr(page, "total", len(rows)) or len(rows))
            offset += len(items)
            if not items or offset >= total or len(rows) >= 5000:
                break

        self._prospects = rows
        self._prospects_by_id = {
            str(item.get("id")): item
            for item in rows
            if item.get("id")
        }
        return rows

    def _mapped_prospect(self, prospect: dict[str, Any]) -> dict[str, Any]:
        score = self._score(prospect)
        contact_name = self._text(prospect.get("contact_name"))
        if not contact_name:
            contact_name = " ".join(
                part
                for part in (
                    self._text(prospect.get("contact_first_name")),
                    self._text(prospect.get("contact_last_name")),
                )
                if part
            )
        next_action_at = self._parse_datetime(prospect.get("next_action_at"))
        return {
            **prospect,
            "id": str(prospect.get("id") or ""),
            "entreprise": self._text(prospect.get("company_name")) or "Entreprise sans nom",
            "telephone": self._text(prospect.get("mobile") or prospect.get("phone")),
            "email": self._text(prospect.get("email")),
            "site_web": self._text(prospect.get("website")),
            "siret": self._text(prospect.get("siret")),
            "code_naf": self._text(prospect.get("naf_code")),
            "activite": self._text(prospect.get("activity")),
            "adresse": self._text(prospect.get("address")),
            "ville": self._text(prospect.get("city")),
            "pipeline": self._text(prospect.get("pipeline_stage")) or "Nouveau",
            "priorite": self._text(prospect.get("priority")) or "normal",
            "prochaine_action": self._text(prospect.get("next_action")) or "Aucune",
            "date_prochaine_action": next_action_at.date().isoformat() if next_action_at else "",
            "contact": contact_name,
            "dirigeant": contact_name,
            "nom_dirigeant": contact_name,
            "score_prospect": score,
            "score_grade": self._grade(score),
            "score_label": self._label(score),
            "linkedin": "",
            "facebook": "",
            "instagram": "",
            "youtube": "",
        }

    def dashboard_summary(self) -> dict[str, Any]:
        rows = self._load_all_prospects()
        total = len(rows)
        phones = sum(bool(self._text(row.get("phone") or row.get("mobile"))) for row in rows)
        emails = sum(bool(self._text(row.get("email"))) for row in rows)
        sites = sum(bool(self._text(row.get("website"))) for row in rows)
        priorities = sum(self._score(row) >= 65 for row in rows)

        today = date.today()
        due_today = 0
        overdue = 0
        for row in rows:
            next_at = self._parse_datetime(row.get("next_action_at"))
            if not next_at:
                continue
            next_date = next_at.date()
            if next_date == today:
                due_today += 1
            elif next_date < today:
                overdue += 1

        quality = round((phones + emails + sites) / (total * 3) * 100) if total else 0
        average = round(sum(self._score(row) for row in rows) / total, 1) if total else 0.0
        return {
            "total": total,
            "phones": phones,
            "emails": emails,
            "sites": sites,
            "priorities": priorities,
            "enriched": sum(bool(self._text(row.get("siret"))) for row in rows),
            "average_score": average,
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
                f"{data['overdue']} prospect(s) ont une action dépassée.",
                "warning",
            ))
        if data["due_today"]:
            insights.append(AssistantInsight(
                "Actions du jour",
                f"{data['due_today']} action(s) sont prévues aujourd'hui.",
                "info",
            ))
        if data["priorities"]:
            insights.append(AssistantInsight(
                "Prospects prioritaires",
                f"{data['priorities']} prospect(s) disposent d'un niveau de qualification élevé.",
                "success",
            ))
        missing_phones = max(0, data["total"] - data["phones"])
        missing_emails = max(0, data["total"] - data["emails"])
        if missing_phones or missing_emails:
            insights.append(AssistantInsight(
                "Qualité de la base",
                f"Il manque {missing_phones} téléphone(s) et {missing_emails} e-mail(s).",
                "info",
            ))
        if not insights:
            insights.append(AssistantInsight(
                "Base prête",
                "Aucune alerte prioritaire pour les prospects visibles.",
                "success",
            ))
        return insights

    @staticmethod
    def _normalize_search(value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        ).casefold().strip()

    def _recommendation_from_row(
        self,
        row: dict[str, Any],
    ) -> ProspectRecommendation:
        score = self._score(row)
        phone = self._text(row.get("mobile") or row.get("phone"))
        email = self._text(row.get("email"))
        reasons = []
        if phone:
            reasons.append("Téléphone disponible")
        if email:
            reasons.append("E-mail disponible")
        if self._text(row.get("website")):
            reasons.append("Site internet identifié")
        if self._text(row.get("siret")):
            reasons.append("SIRET renseigné")
        if not reasons:
            reasons.append("Enrichissement complémentaire recommandé")
        next_at = self._parse_datetime(row.get("next_action_at"))
        return ProspectRecommendation(
            prospect_id=str(row.get("id") or ""),  # type: ignore[arg-type]
            entreprise=self._text(row.get("company_name")) or "Entreprise sans nom",
            score=score,
            grade=self._grade(score),
            label=self._label(score),
            pipeline=self._text(row.get("pipeline_stage")) or "Nouveau",
            telephone=phone,
            email=email,
            prochaine_action=self._text(row.get("next_action")) or "Aucune",
            date_prochaine_action=next_at.date().isoformat() if next_at else "",
            reasons=tuple(reasons),
        )

    def search_prospects(
        self,
        query: str,
        limit: int = 100,
    ) -> list[ProspectRecommendation]:
        clean_query = self._normalize_search(query)
        if not clean_query:
            return self.top_prospects(limit)

        tokens = [token for token in clean_query.split() if token]
        safe_limit = max(1, min(int(limit), 500))
        matches: list[tuple[tuple[int, int, int, int, int], dict[str, Any]]] = []

        for row in self._load_all_prospects():
            company = self._normalize_search(row.get("company_name"))
            searchable = self._normalize_search(
                " ".join(
                    str(value or "")
                    for value in (
                        row.get("company_name"),
                        row.get("siret"),
                        row.get("city"),
                        row.get("phone"),
                        row.get("mobile"),
                        row.get("email"),
                        row.get("naf_code"),
                        row.get("activity"),
                        row.get("contact_name"),
                        row.get("contact_first_name"),
                        row.get("contact_last_name"),
                    )
                )
            )
            if not all(token in searchable for token in tokens):
                continue

            exact_company = int(company == clean_query)
            starts_company = int(company.startswith(clean_query))
            has_phone = int(bool(self._text(row.get("phone") or row.get("mobile"))))
            has_email = int(bool(self._text(row.get("email"))))
            matches.append((
                (
                    exact_company,
                    starts_company,
                    self._score(row),
                    has_phone,
                    has_email,
                ),
                row,
            ))

        matches.sort(key=lambda item: item[0], reverse=True)
        return [
            self._recommendation_from_row(row)
            for _, row in matches[:safe_limit]
        ]

    def top_prospects(self, limit: int = 25) -> list[ProspectRecommendation]:
        safe_limit = max(1, min(int(limit), 100))
        rows = sorted(
            self._load_all_prospects(),
            key=lambda item: (
                self._score(item),
                bool(self._text(item.get("phone") or item.get("mobile"))),
                bool(self._text(item.get("email"))),
            ),
            reverse=True,
        )[:safe_limit]

        return [self._recommendation_from_row(row) for row in rows]

    def get_prospect(self, prospect_id) -> dict[str, Any]:
        key = str(prospect_id)
        self._load_all_prospects()
        prospect = self._prospects_by_id.get(key)
        if prospect is None:
            payload = self.api.get_prospect(key)
            if not isinstance(payload, dict):
                raise ValueError("Prospect introuvable.")
            prospect = payload
            self._prospects_by_id[key] = prospect
        return self._mapped_prospect(prospect)

    def add_commercial_memory(
        self,
        prospect_id,
        content: str,
        memory_type: str = "Contexte",
        source: str = "manual",
    ) -> int:
        self.get_prospect(prospect_id)
        clean_content = self._text(content)
        if not clean_content:
            raise ValueError("La mémoire commerciale ne peut pas être vide.")
        memory_id = int(self._state.get("next_memory_id", 1))
        self._state["next_memory_id"] = memory_id + 1
        key = str(prospect_id)
        memories = self._state.setdefault("memories", {}).setdefault(key, [])
        memories.insert(0, {
            "id": memory_id,
            "prospect_id": key,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "memory_type": self._text(memory_type) or "Contexte",
            "content": clean_content,
            "source": self._text(source) or "manual",
        })
        memories[:] = memories[:500]
        self._save_state()
        return memory_id

    def commercial_memories(self, prospect_id, limit: int = 100) -> list[dict[str, Any]]:
        self.get_prospect(prospect_id)
        safe_limit = max(1, min(int(limit), 500))
        memories = self._state.setdefault("memories", {}).get(str(prospect_id), [])
        return [dict(item) for item in memories[:safe_limit] if isinstance(item, dict)]

    def delete_commercial_memory(self, memory_id: int, prospect_id) -> bool:
        memories = self._state.setdefault("memories", {}).get(str(prospect_id), [])
        before = len(memories)
        memories[:] = [item for item in memories if int(item.get("id", -1)) != int(memory_id)]
        changed = len(memories) != before
        if changed:
            self._save_state()
        return changed

    def commercial_memory_report(self, prospect_id) -> str:
        prospect = self.get_prospect(prospect_id)
        company = self._text(prospect.get("entreprise")) or "Entreprise sans nom"
        memories = self.commercial_memories(prospect_id, 200)
        related_history = [
            item for item in self.history(100)
            if str(item.get("prospect_id") or "") == str(prospect_id)
        ][:20]
        if not memories and not related_history:
            content = (
                f"MÉMOIRE COMMERCIALE — {company}\n"
                f"{'=' * 58}\n\n"
                "Aucune information n'a encore été mémorisée sur ce poste.\n\n"
                "Ajoutez après chaque échange les besoins, difficultés, objections, "
                "décisions et prochaines étapes."
            )
        else:
            lines = [
                f"MÉMOIRE COMMERCIALE — {company}",
                "=" * 58,
                "",
                f"{len(memories)} information(s) locale(s) enregistrée(s).",
                "",
            ]
            for item in memories:
                lines.extend([
                    f"[{str(item.get('created_at', '')).replace('T', ' ')}] {item.get('memory_type', 'Contexte')}",
                    str(item.get("content") or ""),
                    "",
                ])
            if related_history:
                lines.append("ACTIVITÉ IA RÉCENTE")
                lines.extend(
                    f"• {str(item.get('created_at', '')).replace('T', ' ')} — {item.get('title', '')}"
                    for item in related_history
                )
            content = "\n".join(lines)
        self.save_history("commercial_memory_report", prospect_id, f"Mémoire commerciale — {company}", content)
        return content

    def prospect_copilot(self, prospect_id) -> dict[str, Any]:
        p = self.get_prospect(prospect_id)
        company = self._text(p.get("entreprise")) or "Entreprise sans nom"
        city = self._text(p.get("ville"))
        activity = self._text(p.get("activite")) or self._text(p.get("code_naf")) or "activité non précisée"
        score = int(p.get("score_prospect") or 0)
        pipeline = self._text(p.get("pipeline")) or "Nouveau"
        phone = self._text(p.get("telephone"))
        email = self._text(p.get("email"))
        website = self._text(p.get("site_web"))
        siret = self._text(p.get("siret"))
        dirigeant = self._text(p.get("dirigeant"))

        completeness_fields = [phone, email, website, siret, dirigeant, city, activity]
        completeness = round(sum(bool(value) for value in completeness_fields) / len(completeness_fields) * 100)
        if score >= 75 and phone:
            priority, objective, action, probability = (
                "Très haute",
                "Obtenir un rendez-vous de découverte de 20 minutes",
                "Appeler aujourd'hui avec une accroche personnalisée",
                "Forte",
            )
        elif score >= 55 and (phone or email):
            priority, objective, action, probability = (
                "Haute",
                "Qualifier le besoin et identifier le décideur",
                "Appeler ou envoyer un e-mail puis relancer sous trois jours",
                "Moyenne à forte",
            )
        elif phone or email:
            priority, objective, action, probability = (
                "Moyenne",
                "Comprendre l'organisation actuelle",
                "Lancer une première prise de contact",
                "Moyenne",
            )
        else:
            priority, objective, action, probability = (
                "À enrichir",
                "Compléter les coordonnées",
                "Rechercher un téléphone, un e-mail ou le dirigeant",
                "Faible à ce stade",
            )

        missing = [
            label for label, value in (
                ("téléphone", phone),
                ("e-mail", email),
                ("site internet", website),
                ("SIRET", siret),
                ("dirigeant / contact", dirigeant),
                ("ville", city),
            ) if not value
        ]
        reasons = []
        if score >= 65:
            reasons.append("niveau de qualification élevé")
        if phone:
            reasons.append("téléphone disponible")
        if email:
            reasons.append("e-mail disponible")
        if city:
            reasons.append(f"implantation connue : {city}")
        if not reasons:
            reasons.append("informations encore insuffisantes")

        return {
            "prospect_id": str(prospect_id),
            "company": company,
            "summary": (
                f"{company} exerce une activité liée à {activity}"
                + (f" à {city}" if city else "")
                + f". Son score interne est de {score}/100 et son pipeline est « {pipeline} »."
            ),
            "score": score,
            "pipeline": pipeline,
            "priority": priority,
            "probability": probability,
            "objective": objective,
            "recommended_action": action,
            "completeness": completeness,
            "missing": missing,
            "reasons": reasons,
            "arguments": [
                "Formation pratique adaptée au fonctionnement de l'entreprise",
                "Analyse concrète des besoins et des méthodes actuelles",
                "Création d'un outil opérationnel personnalisé",
                "Accompagnement au financement selon l'éligibilité et l'accord du financeur",
                "Suivi qualité après la formation",
            ],
        }

    def save_history(self, action_type: str, prospect_id, title: str, content: str) -> None:
        history = self._state.setdefault("history", [])
        next_id = max((int(item.get("id", 0)) for item in history if isinstance(item, dict)), default=0) + 1
        history.insert(0, {
            "id": next_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "action_type": str(action_type or ""),
            "prospect_id": str(prospect_id) if prospect_id is not None else None,
            "title": str(title or ""),
            "content": str(content or ""),
        })
        history[:] = history[: self.HISTORY_LIMIT]
        self._save_state()

    def history(self, limit: int = 30) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), self.HISTORY_LIMIT))
        history = self._state.setdefault("history", [])
        return [dict(item) for item in history[:safe_limit] if isinstance(item, dict)]
