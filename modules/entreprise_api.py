from __future__ import annotations

import re
import threading
import time
from typing import Any

import requests


class EntrepriseApiClient:
    """Résout un SIREN/SIRET via l'API Recherche d'entreprises.

    Lot 2.3 : cette source ne fournit pas directement les téléphones/emails.
    Elle sert à compléter l'identité avec le siège, les autres établissements,
    les enseignes et le sigle avant d'interroger PagesJaunes / Google Maps.

    L'API est ouverte mais limitée en débit. On conserve donc un cache mémoire
    par SIREN et on espace légèrement les appels réseau réels.
    """

    SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
    MIN_REQUEST_INTERVAL = 0.18  # < 7 req/s, avec une petite marge.
    TIMEOUT = 5

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "FormProspect-Enrichment/2.3 (+https://forma-prof.fr)",
            }
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._last_request_at = 0.0
        self.network_requests = 0
        self.cache_hits = 0
        self.failures = 0

    @staticmethod
    def _digits(value: Any) -> str:
        return re.sub(r"\D", "", str(value or ""))

    @staticmethod
    def _clean_text(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.upper() in {"[ND]", "ND", "N/D", "N/A", "NA", "NEANT", "NÉANT"}:
            return ""
        return text

    @classmethod
    def _append_unique(cls, target: list[str], *values: Any) -> None:
        seen = {re.sub(r"\W+", "", x.lower()) for x in target if x}
        for raw in values:
            value = cls._clean_text(raw)
            if not value:
                continue
            key = re.sub(r"\W+", "", value.lower())
            if key and key not in seen:
                seen.add(key)
                target.append(value)

    @classmethod
    def _location_from_etablissement(cls, etab: dict[str, Any]) -> dict[str, str] | None:
        if not isinstance(etab, dict):
            return None
        adresse = cls._clean_text(etab.get("adresse") or etab.get("geo_adresse"))
        cp = cls._clean_text(etab.get("code_postal"))
        ville = cls._clean_text(
            etab.get("libelle_commune")
            or etab.get("commune")
            or etab.get("libelle_commune_etranger")
        )
        siret = cls._digits(etab.get("siret"))
        if not any((adresse, cp, ville, siret)):
            return None
        return {
            "adresse": adresse,
            "code_postal": cp,
            "ville": ville,
            "siret": siret if len(siret) == 14 else "",
            "est_siege": bool(etab.get("est_siege")),
        }

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self.MIN_REQUEST_INTERVAL - (now - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def _empty(self, *, error: str = "", from_cache: bool = False) -> dict[str, Any]:
        return {
            "resolved": False,
            "siren": "",
            "siret_siege": "",
            "names": [],
            "locations": [],
            "error": error,
            "from_cache": from_cache,
        }

    def _parse_result(self, result: dict[str, Any], expected_siren: str) -> dict[str, Any]:
        if not isinstance(result, dict):
            return self._empty()

        siren = self._digits(result.get("siren"))
        if expected_siren and siren != expected_siren:
            return self._empty()

        names: list[str] = []
        self._append_unique(
            names,
            result.get("nom_raison_sociale"),
            result.get("nom_complet"),
            result.get("sigle"),
        )

        locations: list[dict[str, str]] = []
        seen_locations = set()

        def consume_etab(etab: dict[str, Any]) -> None:
            if not isinstance(etab, dict):
                return
            self._append_unique(
                names,
                etab.get("nom_commercial"),
                *(etab.get("liste_enseignes") or []),
            )
            location = self._location_from_etablissement(etab)
            if not location:
                return
            key = (
                location.get("siret", ""),
                location.get("adresse", "").lower(),
                location.get("code_postal", ""),
                location.get("ville", "").lower(),
            )
            if key not in seen_locations:
                seen_locations.add(key)
                locations.append(location)

        siege = result.get("siege") or {}
        consume_etab(siege)
        for etab in result.get("matching_etablissements") or []:
            consume_etab(etab)

        siret_siege = self._digits((siege or {}).get("siret"))
        return {
            "resolved": bool(siren),
            "siren": siren,
            "siret_siege": siret_siege if len(siret_siege) == 14 else "",
            "names": names,
            "locations": locations,
            "error": "",
            "from_cache": False,
        }

    def resolve(self, identity: dict[str, Any]) -> dict[str, Any]:
        siren = self._digits(identity.get("siren"))
        siret = self._digits(identity.get("siret"))
        if len(siren) != 9 and len(siret) == 14:
            siren = siret[:9]
        if len(siren) != 9:
            return self._empty()

        if siren in self._cache:
            self.cache_hits += 1
            cached = dict(self._cache[siren])
            cached["from_cache"] = True
            return cached

        self._throttle()
        try:
            response = self.session.get(
                self.SEARCH_URL,
                params={
                    "q": siren,
                    "minimal": "true",
                    "include": "siege,matching_etablissements",
                    "limite_matching_etablissements": 100,
                    "per_page": 1,
                },
                timeout=self.TIMEOUT,
            )
            self.network_requests += 1

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = min(2.0, max(0.2, float(retry_after)))
                except Exception:
                    delay = 0.5
                time.sleep(delay)
                response = self.session.get(
                    self.SEARCH_URL,
                    params={
                        "q": siren,
                        "minimal": "true",
                        "include": "siege,matching_etablissements",
                        "limite_matching_etablissements": 100,
                        "per_page": 1,
                    },
                    timeout=self.TIMEOUT,
                )
                self.network_requests += 1

            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            exact = next(
                (
                    item
                    for item in results
                    if self._digits((item or {}).get("siren")) == siren
                ),
                None,
            )
            parsed = self._parse_result(exact or {}, siren)
            self._cache[siren] = dict(parsed)
            return parsed
        except Exception as exc:
            self.failures += 1
            result = self._empty(error=f"{type(exc).__name__}: {exc}")
            # On ne mémorise pas durablement un échec réseau : un autre SIRET
            # du même SIREN pourra retenter l'appel plus tard dans la session.
            return result

    def stats(self) -> dict[str, int]:
        return {
            "api_requests": int(self.network_requests),
            "api_cache_hits": int(self.cache_hits),
            "api_failures": int(self.failures),
            "api_cache_size": len(self._cache),
        }
