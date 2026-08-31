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
        "date_score", "mobile",
    )

    @classmethod
    def from_sqlite(cls, row: Any) -> dict[str, Any]:
        s = cls._to_mapping(row)
        phone, mobile = cls._phones(
            " / ".join(
                value for value in (
                    cls._text(s.get("telephone")),
                    cls._text(s.get("mobile")),
                )
                if value
            )
        )

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
            "email": cls._email(s.get("email")),
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
    def _email(cls, value):
        """Retourne un e-mail exploitable par le Cloud, sinon une valeur vide.

        La donnée locale d'origine n'est jamais modifiée : seul le payload de
        synchronisation est assaini afin qu'une adresse issue de
        l'enrichissement ne bloque pas un lot complet.
        """
        value = cls._text(value)
        if not value:
            return ""

        # Le champ CRM représente une seule adresse. Si une source contient
        # plusieurs valeurs, on retient la première adresse syntaxiquement
        # plausible et on laisse la donnée locale intacte.
        candidates = [
            part.strip()
            for part in re.split(r"[\r\n;,/|]+", value)
            if part.strip()
        ]
        pattern = re.compile(
            r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
            r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
            re.IGNORECASE,
        )
        for candidate in candidates:
            if len(candidate) <= 320 and pattern.fullmatch(candidate):
                return candidate
        return ""

    @classmethod
    def _phones(cls, value) -> tuple[str, str]:
        """Classe tous les numéros locaux en Téléphone et Mobile.

        Règle métier Form@Prospect :
        - 06 / 07 => ``mobile`` ;
        - autres numéros français valides => ``phone`` ;
        - aucun nombre arbitraire n'est supprimé : tous les numéros valides
          sont conservés, dédupliqués et séparés par `` / ``.

        Les anciens projets utilisant des retours à la ligne, ``;``, ``|``
        ou ``,`` restent compatibles. Les numéros +33 sont normalisés en
        format national avant classement.
        """
        value = cls._text(value)
        if not value:
            return "", ""

        chunks = [
            part.strip()
            for part in re.split(r"[\r\n;/|,]+", value)
            if part.strip()
        ]

        phones: list[str] = []
        mobiles: list[str] = []
        seen: set[str] = set()

        def normalize(candidate: str) -> str:
            raw = str(candidate or "").strip()
            digits = re.sub(r"\D", "", raw)

            # +33 X XX XX XX XX / 0033 X XX XX XX XX -> 0X XX XX XX XX
            if raw.startswith("+33") and len(digits) == 11 and digits.startswith("33"):
                digits = "0" + digits[2:]
            elif raw.startswith("0033") and len(digits) == 13 and digits.startswith("0033"):
                digits = "0" + digits[4:]

            if len(digits) != 10 or not digits.startswith("0"):
                return ""
            if digits[1] == "0":
                return ""

            return " ".join(digits[i:i + 2] for i in range(0, 10, 2))

        for chunk in chunks:
            # Les sources d'enrichissement fournissent normalement un numéro
            # par bloc. Ce motif permet aussi les petits libellés tels que
            # "Tél : 04 90 00 00 00" sans absorber une longue chaîne de
            # chiffres sans séparateur métier.
            candidates = re.findall(
                r"(?<!\d)(?:\+33\s?|0033\s?|0)[1-9](?:[ .\-]?\d{2}){4}(?!\d)",
                chunk,
            )
            if not candidates:
                candidates = [chunk]

            for candidate in candidates:
                normalized = normalize(candidate)
                if not normalized:
                    continue
                key = re.sub(r"\D", "", normalized)
                if key in seen:
                    continue
                seen.add(key)

                if key.startswith(("06", "07")):
                    mobiles.append(normalized)
                else:
                    phones.append(normalized)

        return " / ".join(phones), " / ".join(mobiles)

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
