from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class QualificationResult:
    total: int
    coordinates: int
    decision_maker: int
    activity: int
    digital: int
    history: int
    confidence: int
    maturity: str
    urgency: str
    potential: str
    recommended_action: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    missing: tuple[str, ...]


class QualificationService:
    """Qualification commerciale locale, explicable et sans API externe."""

    @staticmethod
    def _present(value: Any) -> bool:
        return value is not None and str(value).strip() not in {"", "nan", "None"}

    @staticmethod
    def _parse_date(value: Any):
        raw = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def calculate(cls, prospect: dict, memories: list[dict] | None = None) -> QualificationResult:
        memories = memories or []
        phone = cls._present(prospect.get("telephone"))
        email = cls._present(prospect.get("email"))
        siret = cls._present(prospect.get("siret"))
        address = cls._present(prospect.get("adresse")) or cls._present(prospect.get("ville"))
        leader = any(cls._present(prospect.get(k)) for k in ("dirigeant", "nom_dirigeant", "contact", "commercial_assigne"))
        naf = cls._present(prospect.get("code_naf"))
        activity = cls._present(prospect.get("activite")) or naf
        site = cls._present(prospect.get("site_web"))
        linkedin = cls._present(prospect.get("linkedin"))
        socials = any(cls._present(prospect.get(k)) for k in ("facebook", "instagram", "youtube"))

        coordinates = (8 if phone else 0) + (8 if email else 0) + (2 if siret else 0) + (2 if address else 0)
        decision_maker = 20 if leader else (8 if phone or email else 0)
        activity_score = (12 if activity else 0) + (5 if naf else 0) + (3 if siret else 0)
        digital = (7 if site else 0) + (5 if linkedin else 0) + (3 if socials else 0)

        types = {str(m.get("memory_type") or "") for m in memories}
        history = min(25, len(memories) * 3)
        if "Besoin" in types: history += 5
        if "Difficulté" in types: history += 4
        if "Décision" in types: history += 4
        if "Prochaine étape" in types: history += 4
        history = min(25, history)

        total = min(100, coordinates + decision_maker + activity_score + digital + history)
        completeness_signals = [phone,email,siret,address,leader,activity,site,linkedin]
        confidence = round((sum(completeness_signals)/len(completeness_signals))*75 + min(len(memories),5)*5)
        confidence = min(100, confidence)

        strengths=[]; weaknesses=[]; missing=[]
        for label, present in (("Téléphone",phone),("E-mail",email),("SIRET",siret),("Adresse / ville",address),("Décideur",leader),("Activité",activity),("Site internet",site),("LinkedIn",linkedin)):
            (strengths if present else missing).append(label)
        if memories: strengths.append(f"Historique commercial disponible ({len(memories)} élément(s))")
        else: weaknesses.append("Aucun historique commercial")
        if not leader: weaknesses.append("Décideur non identifié")
        if not phone: weaknesses.append("Pas de téléphone disponible")
        if not activity: weaknesses.append("Activité insuffisamment qualifiée")

        if total >= 80:
            maturity, potential = "🟢 Très forte opportunité", "★★★★★"
        elif total >= 65:
            maturity, potential = "🟢 Opportunité forte", "★★★★☆"
        elif total >= 45:
            maturity, potential = "🟡 À qualifier davantage", "★★★☆☆"
        elif total >= 25:
            maturity, potential = "🟠 Priorité faible", "★★☆☆☆"
        else:
            maturity, potential = "🔴 Données insuffisantes", "★☆☆☆☆"

        action_date = cls._parse_date(prospect.get("date_prochaine_action"))
        today = date.today()
        if action_date and action_date <= today:
            urgency = "🔥 Urgent"
        elif total >= 80 and phone:
            urgency = "🔥 Urgent"
        elif total >= 65 and (phone or email):
            urgency = "⚡ Important — sous 48 h"
        elif total >= 45:
            urgency = "📅 Planifiable cette semaine"
        else:
            urgency = "💤 À surveiller / enrichir"

        if total >= 65 and phone:
            recommended = "📞 Appeler aujourd'hui et viser un rendez-vous de découverte de 20 minutes."
        elif email and total >= 45:
            recommended = "📧 Envoyer un e-mail personnalisé puis programmer une relance téléphonique sous 2 à 3 jours."
        elif phone:
            recommended = "📞 Appeler pour identifier le décideur et qualifier le besoin."
        else:
            recommended = "🔍 Enrichir la fiche avant toute action commerciale."

        return QualificationResult(total, coordinates, decision_maker, activity_score, digital, history, confidence, maturity, urgency, potential, recommended, tuple(strengths), tuple(weaknesses), tuple(missing))
