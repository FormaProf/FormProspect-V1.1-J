from __future__ import annotations

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from modules.company_matcher import (
    confidence,
    identity_locations,
    identity_names,
    score_candidate,
)


class Annuaire118000Finder:
    """Recherche directe dans l'annuaire public 118000.

    Cette source ne remplace pas PagesJaunes / Google Maps / WebFallback :
    elle les complète avec des coordonnées publiques trouvées sur les
    implantations actuelles ou historiques déjà validées par l'API Entreprises.
    """

    SEARCH_URL = "https://www.118000.fr/search"
    TIMEOUT = 8
    MAX_QUERIES = 4

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
        self.last_errors: list[str] = []

    @staticmethod
    def _empty(errors=None):
        return {
            "source": "118000",
            "source_detail": "",
            "nom": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "email": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": list(errors or []),
        }

    @staticmethod
    def _normalize_phone(value: str) -> str:
        digits = re.sub(r"\D", "", str(value or ""))
        if digits.startswith("33") and len(digits) == 11:
            digits = "0" + digits[2:]
        if len(digits) == 10 and digits.startswith("0") and digits[1] in "123456789":
            return " ".join(digits[index:index + 2] for index in range(0, 10, 2))
        return ""

    @staticmethod
    def _query_plan(identity: dict) -> list[tuple[str, str]]:
        names = identity_names(identity)
        locations = identity_locations(identity)
        if not names:
            return []

        queries: list[tuple[str, str]] = []
        seen = set()

        # Priorité au nom principal, puis aux alias distinctifs.
        for name in names:
            for location in locations:
                cp = str(location.get("code_postal") or "").strip()
                city = str(location.get("ville") or "").strip()
                label = " ".join(value for value in (cp, city) if value).strip()
                if not label:
                    continue

                key = (name.strip().lower(), label.lower())
                if key in seen:
                    continue
                seen.add(key)
                queries.append((name.strip(), label))
                if len(queries) >= Annuaire118000Finder.MAX_QUERIES:
                    return queries

        return queries

    def _candidate_from_card(self, card, identity: dict, page_url: str) -> dict:
        raw_info = str(card.get("data-info") or "").strip()
        if not raw_info:
            info_node = card.select_one("[data-info]")
            raw_info = str(info_node.get("data-info") or "").strip() if info_node else ""

        data = {}
        if raw_info:
            try:
                parsed = json.loads(raw_info)
                if isinstance(parsed, dict):
                    data = parsed
            except Exception:
                data = {}

        card_text = card.get_text(" ", strip=True)
        name = str(data.get("name") or "").strip()
        address = str(data.get("address") or "").strip()
        cp = str(data.get("cp") or "").strip()
        city = str(data.get("city") or "").strip()

        phones = []
        faxes = []

        # 118000 expose généralement les lignes dans tel/mainLine. Certaines
        # fiches peuvent aussi exposer un fax dans un champ dédié : on le
        # qualifie séparément afin qu'il ne soit jamais enregistré comme
        # téléphone commercial.
        for raw in (
            data.get("tel"),
            data.get("mainLine"),
            data.get("phone"),
            data.get("telephone"),
        ):
            number = self._normalize_phone(raw)
            if number and number not in phones:
                phones.append(number)

        for raw in (
            data.get("fax"),
            data.get("faxLine"),
            data.get("mainFax"),
            data.get("faxNumber"),
        ):
            number = self._normalize_phone(raw)
            if number and number not in faxes:
                faxes.append(number)

        # Détection explicite des mentions "fax" visibles dans la carte.
        for match in re.findall(
            r"(?i)\bfax\b\s*[:\-]?\s*"
            r"((?:\+33|0)\s*[1-9](?:[\s.\-]*\d{2}){4})",
            card_text,
        ):
            number = self._normalize_phone(match)
            if number and number not in faxes:
                faxes.append(number)

        # Secours si le JSON change mais que le numéro reste visible.
        if not phones:
            for match in re.findall(
                r"(?:(?:\+33|0)\s*[1-9](?:[\s.\-]*\d{2}){4})",
                card_text,
            ):
                number = self._normalize_phone(match)
                if number and number not in phones:
                    phones.append(number)

        fax_keys = {re.sub(r"\D", "", number) for number in faxes}
        phones = [
            number
            for number in phones
            if re.sub(r"\D", "", number) not in fax_keys
        ]

        detail_url = str(data.get("urlDetail") or "").strip()
        if detail_url:
            detail_url = urljoin(page_url, detail_url)

        candidate = {
            "source": "118000",
            "source_detail": detail_url,
            "nom": name,
            "adresse": address,
            "code_postal": cp,
            "ville": city,
            "telephones": phones,
            "faxes": faxes,
            "site_web": "",
            "email": "",
            "texte": " ".join(
                value
                for value in (
                    card_text,
                    raw_info,
                )
                if value
            ),
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": [],
        }
        score, reasons = score_candidate(identity, candidate)
        candidate["match_score"] = score
        candidate["match_reasons"] = reasons
        candidate["confidence"] = confidence(score)
        return candidate

    def _search_once(self, identity: dict, who: str, label: str) -> list[dict]:
        response = requests.get(
            self.SEARCH_URL,
            params={"who": who, "label": label},
            headers=self.headers,
            timeout=self.TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text or "", "lxml")
        candidates = []

        # Le site place son JSON public dans data-info, sur la carte ou un enfant.
        nodes = soup.select(".card")
        if not nodes:
            nodes = soup.select("[data-info]")

        seen = set()
        for node in nodes:
            candidate = self._candidate_from_card(node, identity, response.url)
            detail = candidate.get("source_detail") or ""
            signature = (
                detail,
                candidate.get("nom"),
                candidate.get("adresse"),
                candidate.get("code_postal"),
                tuple(candidate.get("telephones") or []),
            )
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(candidate)

        return candidates

    def rechercher(self, identity: dict) -> dict:
        self.last_errors = []
        validated = []

        for who, label in self._query_plan(identity):
            try:
                candidates = self._search_once(identity, who, label)
            except Exception as exc:
                self.last_errors.append(
                    f"118000 {who} / {label}: {type(exc).__name__}: {exc}"
                )
                continue

            for candidate in candidates:
                if candidate.get("confidence") == "validated":
                    validated.append(candidate)

        if not validated:
            return self._empty(self.last_errors)

        validated.sort(
            key=lambda result: int(result.get("match_score") or 0),
            reverse=True,
        )

        phones = []
        faxes = []
        seen_phones = set()
        seen_faxes = set()
        details = []
        for candidate in validated:
            for raw in candidate.get("faxes") or []:
                number = self._normalize_phone(raw)
                key = re.sub(r"\D", "", number)
                if key and key not in seen_faxes:
                    seen_faxes.add(key)
                    faxes.append(number)

            for raw in candidate.get("telephones") or []:
                number = self._normalize_phone(raw)
                key = re.sub(r"\D", "", number)
                if key and key not in seen_phones and key not in seen_faxes:
                    seen_phones.add(key)
                    phones.append(number)

            detail = str(candidate.get("source_detail") or "").strip()
            if detail and detail not in details:
                details.append(detail)

        best = dict(validated[0])
        best["source"] = "118000"
        best["source_detail"] = " + ".join(details)
        best["telephones"] = phones
        best["faxes"] = faxes
        best["site_web"] = ""
        best["email"] = ""
        best["technical_errors"] = list(self.last_errors)
        return best
