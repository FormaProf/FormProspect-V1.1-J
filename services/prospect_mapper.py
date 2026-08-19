from __future__ import annotations
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any


class ProspectMapper:
    """Transforme les champs SQLite locaux enrichis vers ProspectCreate Cloud."""

    DEPLOYMENT_COLUMNS = (
        "id", "entreprise", "siret", "siren", "adresse", "code_postal",
        "ville", "code_naf", "telephone", "site_web", "email", "facebook",
        "linkedin", "instagram", "twitter", "youtube", "social_other_urls",
        "statut_enrichissement", "date_collecte", "pipeline", "priorite",
        "prochaine_action", "date_prochaine_action", "commercial_assigne",
        "score_prospect", "score_grade", "score_label", "score_details",
        "date_score",
    )

    @classmethod
    def from_sqlite(cls, row: Any) -> dict[str, Any]:
        s = cls._to_mapping(row)
        phone, mobile = cls._phones(s.get("telephone"))

        payload = {
            "company_name": cls._text(s.get("entreprise")),
            "siret": cls._digits(s.get("siret"), 14),
            "siren": cls._digits(s.get("siren"), 9),
            "address": cls._text(s.get("adresse")),
            "postal_code": cls._text(s.get("code_postal")),
            "city": cls._text(s.get("ville")),
            "naf_code": cls._naf(s.get("code_naf")),
            "phone": phone,
            "mobile": mobile,
            "website": cls._url(s.get("site_web")),
            "email": cls._text(s.get("email")),
            "facebook": cls._url(s.get("facebook")),
            "linkedin": cls._url(s.get("linkedin")),
            "instagram": cls._url(s.get("instagram")),
            "twitter": cls._url(s.get("twitter")),
            "youtube": cls._url(s.get("youtube")),
            "social_other_urls": cls._other_urls(s.get("social_other_urls")),
            "pipeline_stage": cls._pipeline(s.get("pipeline")),
            "priority": cls._priority(s.get("priorite")),
            "next_action": cls._next_action(s.get("prochaine_action")),
            "next_action_at": cls._dt(s.get("date_prochaine_action")),
            "enrichment_status": cls._enrichment_status(
                s.get("statut_enrichissement")
            ),
            "enriched_at": cls._dt(s.get("date_collecte")),
            "origin": "project_import",
        }
        if not payload["company_name"]:
            payload["company_name"] = (
                cls._text(s.get("siret"))
                or cls._text(s.get("siren"))
                or "Prospect importé"
            )
        return {
            key: value for key, value in payload.items()
            if value not in (None, "")
        }

    @classmethod
    def from_batch(cls, rows: Sequence[Any]) -> list[dict[str, Any]]:
        return [cls.from_sqlite(row) for row in rows]

    @classmethod
    def _to_mapping(cls, row):
        if isinstance(row, Mapping):
            return dict(row)
        keys = getattr(row, "keys", None)
        if callable(keys):
            return {str(key): row[key] for key in keys()}
        if isinstance(row, Sequence) and not isinstance(
            row, (str, bytes, bytearray)
        ):
            if len(row) != len(cls.DEPLOYMENT_COLUMNS):
                raise ValueError(
                    f"{len(row)} valeur(s) reçue(s), "
                    f"{len(cls.DEPLOYMENT_COLUMNS)} attendue(s)."
                )
            return dict(zip(cls.DEPLOYMENT_COLUMNS, row, strict=True))
        raise TypeError(f"Type non pris en charge : {type(row).__name__}.")

    @staticmethod
    def _text(value):
        if value is None:
            return ""
        value = str(value).strip()
        return "" if value.lower() in {"nan", "none", "null"} else value

    @classmethod
    def _digits(cls, value, length):
        value = "".join(c for c in cls._text(value) if c.isdigit())
        return value if len(value) == length else ""

    @classmethod
    def _phones(cls, value) -> tuple[str, str]:
        """Extrait jusqu'à deux numéros distincts sans fusionner les lignes.

        Les cellules locales peuvent contenir plusieurs numéros séparés par
        des retours à la ligne, '/', ';', '|' ou ','. Chaque bloc est analysé
        séparément afin qu'un couple de numéros ne soit jamais interprété
        comme un seul numéro trop long.
        """
        value = cls._text(value)
        if not value:
            return "", ""

        # Sépare d'abord les numéros multiples. Important : ne pas utiliser
        # ``\\s`` dans le motif principal car il inclut les retours à la ligne.
        chunks = [
            part.strip()
            for part in re.split(r"[\r\n;/|,]+", value)
            if part.strip()
        ]

        valid: list[str] = []

        for chunk in chunks:
            # Peut aussi récupérer un numéro au milieu d'un petit libellé.
            candidates = re.findall(
                r"\+?\d(?:[ \t().-]*\d){5,14}",
                chunk,
            )

            if not candidates:
                candidates = [chunk]

            for candidate in candidates:
                candidate = re.sub(r"[ \t]+", " ", candidate).strip(" .,-")
                digits = re.sub(r"\D", "", candidate)

                if not (6 <= len(digits) <= 15):
                    continue
                if len(candidate) > 50:
                    continue
                if not re.fullmatch(r"[0-9+().\-\s]+", candidate):
                    continue

                # Déduplication sur les chiffres.
                if any(
                    re.sub(r"\D", "", existing) == digits
                    for existing in valid
                ):
                    continue

                valid.append(candidate)

                if len(valid) == 2:
                    return valid[0], valid[1]

        return (
            valid[0] if len(valid) >= 1 else "",
            valid[1] if len(valid) >= 2 else "",
        )

    @classmethod
    def _url(cls, value):
        value = cls._text(value)
        if value and "://" not in value:
            value = "https://" + value
        return value

    @classmethod
    def _other_urls(cls, value):
        urls = []
        for raw in re.split(r"[\r\n;]+", cls._text(value)):
            url = cls._url(raw)
            if url and url not in urls:
                urls.append(url)
        return "\n".join(urls)

    @classmethod
    def _naf(cls, value):
        value = cls._text(value).upper().replace(" ", "")
        if len(value) == 5 and "." not in value and value[:4].isdigit():
            return f"{value[:2]}.{value[2:]}"
        return value

    @classmethod
    def _pipeline(cls, value):
        value = cls._text(value).lower()
        for icon in ("🟢", "🟡", "🔵", "🟣", "🟠", "🔴"):
            value = value.replace(icon, "")
        value = value.strip()
        return {
            "nouveau": "nouveau",
            "qualification": "a_contacter",
            "à contacter": "a_contacter",
            "a contacter": "a_contacter",
            "contacté": "contacte",
            "contacte": "contacte",
            "rdv programmé": "rdv_planifie",
            "rdv programme": "rdv_planifie",
            "rdv planifié": "rdv_planifie",
            "rdv planifie": "rdv_planifie",
            "proposition envoyée": "proposition_envoyee",
            "proposition envoyee": "proposition_envoyee",
            "négociation": "negociation",
            "negociation": "negociation",
            "client": "gagne",
            "gagné": "gagne",
            "gagne": "gagne",
            "perdu": "perdu",
        }.get(value, "nouveau")

    @classmethod
    def _priority(cls, value):
        value = cls._text(value).lower()
        if "urgent" in value or value.count("⭐") >= 4:
            return "urgente"
        if "haut" in value or value.count("⭐") == 3:
            return "haute"
        if "bas" in value or value.count("⭐") == 1:
            return "basse"
        return "normal"

    @classmethod
    def _next_action(cls, value):
        value = cls._text(value)
        return "" if value.lower() in {"aucune", "none"} else value

    @classmethod
    def _enrichment_status(cls, value):
        value = cls._text(value).lower()

        if "erreur" in value or value == "error":
            return "error"

        if "aucun résultat fiable" in value or "aucun resultat fiable" in value:
            return "no_reliable_result"

        if "enrich" in value:
            return "enriched"

        return "pending"

    @classmethod
    def _dt(cls, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time()).isoformat()
        value = cls._text(value)
        if not value:
            return None
        try:
            if len(value) == 10:
                d = date.fromisoformat(value)
                return datetime.combine(d, datetime.min.time()).isoformat()
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).isoformat()
        except ValueError:
            return None
