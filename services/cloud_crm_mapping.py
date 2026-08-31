from __future__ import annotations

from datetime import datetime

PIPELINE_LABEL_TO_SLUG = {
    "🟢 Nouveau": "nouveau",
    "🟡 Qualification": "contacte",
    "🔵 RDV programmé": "rdv_planifie",
    "🟣 Proposition envoyée": "proposition_envoyee",
    "🟠 Négociation": "negociation",
    "🟢 Client": "gagne",
    "🔴 Perdu": "perdu",
    "À contacter": "a_contacter",
    "Contacté": "contacte",
    "RDV planifié": "rdv_planifie",
    "Gagné": "gagne",
    "Perdu": "perdu",
}
PIPELINE_SLUG_TO_LABEL = {
    "nouveau": "🟢 Nouveau",
    "a_contacter": "🟡 Qualification",
    "contacte": "🟡 Qualification",
    "rdv_planifie": "🔵 RDV programmé",
    "proposition_envoyee": "🟣 Proposition envoyée",
    "negociation": "🟠 Négociation",
    "gagne": "🟢 Client",
    "perdu": "🔴 Perdu",
}
PRIORITY_LABEL_TO_API = {
    "⭐": "basse",
    "⭐⭐": "normal",
    "⭐⭐⭐": "normal",
    "⭐⭐⭐⭐": "haute",
    "⭐⭐⭐⭐⭐": "urgente",
}
PRIORITY_API_TO_LABEL = {
    "basse": "⭐",
    "normal": "⭐⭐⭐",
    "haute": "⭐⭐⭐⭐",
    "urgente": "⭐⭐⭐⭐⭐",
}
ACTION_TYPE_TO_API = {
    "Note": "note",
    "Pipeline": "note",
    "Priorité": "note",
    "Prochaine action": "task",
    "Date action": "task",
    "Commercial": "note",
    "Modification": "note",
    "Appel": "call",
    "Email": "email",
    "Rendez-vous": "meeting",
    "Tâche": "task",
}


def pipeline_to_api(value: str) -> str:
    return PIPELINE_LABEL_TO_SLUG.get(str(value or "").strip(), str(value or "nouveau").strip().lower())


def pipeline_to_ui(value: str) -> str:
    return PIPELINE_SLUG_TO_LABEL.get(str(value or "").strip(), str(value or "🟢 Nouveau"))


def priority_to_api(value: str) -> str:
    return PRIORITY_LABEL_TO_API.get(str(value or "").strip(), str(value or "normal").strip().lower())


def priority_to_ui(value: str) -> str:
    return PRIORITY_API_TO_LABEL.get(str(value or "").strip().lower(), "⭐⭐⭐")


def parse_datetime(value: str | None) -> str | None:
    """
    Convertit une date saisie dans Form@Prospect en datetime ISO.

    Les dates sans fuseau horaire sont considérées comme des heures locales
    du poste utilisateur.

    Exemples en France :
    - 2026-09-22 20:00 -> 2026-09-22T20:00:00+02:00
    - 2026-01-22 20:00 -> 2026-01-22T20:00:00+01:00

    Une datetime qui contient déjà un fuseau horaire est conservée telle quelle.
    """
    text = str(value or "").strip()

    if not text:
        return None

    # Formats issus de la saisie Form@Prospect.
    # Ils ne contiennent pas de timezone : on considère donc
    # qu'il s'agit de l'heure locale du poste utilisateur.
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text, fmt)

            # Ajoute automatiquement le fuseau local correspondant
            # à la date concernée (heure été / heure hiver).
            return parsed.astimezone().isoformat()

        except ValueError:
            pass

    # Accepte également les valeurs ISO déjà existantes,
    # notamment celles provenant du Cloud.
    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        # Une ISO sans timezone doit également être interprétée
        # comme une heure locale.
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()

        return parsed.isoformat()

    except ValueError:
        raise ValueError(
            "La date doit respecter le format "
            "JJ/MM/AAAA ou AAAA-MM-JJ."
        )


def display_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)
