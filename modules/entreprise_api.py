from __future__ import annotations

import re
import threading
import time
from typing import Any

import requests


class EntrepriseApiClient:
    """Résout un SIREN/SIRET via l'API Recherche d'entreprises.

    Cette source ne fournit pas directement les téléphones/emails. Elle sert à
    consolider l'identité avant les recherches de coordonnées : raison sociale,
    enseignes, siège actuel et, lorsque l'API le permet, établissements anciens
    ou secondaires appartenant à la même unité légale.

    L'API est ouverte mais limitée en débit. Un cache mémoire par SIREN évite de
    répéter les deux requêtes d'identité pour plusieurs établissements d'une
    même société.
    """

    SEARCH_URL = "https://recherche-entreprises.api.gouv.fr/search"
    MIN_REQUEST_INTERVAL = 0.18  # < 7 req/s, avec une petite marge.
    TIMEOUT = 5
    HISTORY_MATCH_LIMIT = 100
    HISTORY_RESULT_LIMIT = 25

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
    def _location_from_etablissement(
        cls,
        etab: dict[str, Any],
    ) -> dict[str, Any] | None:
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

        locations: list[dict[str, Any]] = []
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
                str(location.get("adresse", "")).lower(),
                location.get("code_postal", ""),
                str(location.get("ville", "")).lower(),
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

    @classmethod
    def _merge_parsed(
        cls,
        primary: dict[str, Any],
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        """Fusionne deux résolutions déjà filtrées sur le même SIREN."""
        merged = {
            "resolved": bool(primary.get("resolved") or extra.get("resolved")),
            "siren": str(primary.get("siren") or extra.get("siren") or ""),
            "siret_siege": str(
                primary.get("siret_siege") or extra.get("siret_siege") or ""
            ),
            "names": list(primary.get("names") or []),
            "locations": [dict(item) for item in primary.get("locations") or []],
            "error": "",
            "from_cache": False,
        }

        cls._append_unique(merged["names"], *(extra.get("names") or []))

        seen_sirets = {
            cls._digits(item.get("siret"))
            for item in merged["locations"]
            if cls._digits(item.get("siret"))
        }
        seen_locations = {
            (
                str(item.get("adresse") or "").strip().lower(),
                str(item.get("code_postal") or "").strip(),
                str(item.get("ville") or "").strip().lower(),
            )
            for item in merged["locations"]
        }

        for raw in extra.get("locations") or []:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            item_siret = cls._digits(item.get("siret"))
            location_key = (
                str(item.get("adresse") or "").strip().lower(),
                str(item.get("code_postal") or "").strip(),
                str(item.get("ville") or "").strip().lower(),
            )
            if item_siret and item_siret in seen_sirets:
                continue
            if any(location_key) and location_key in seen_locations:
                continue
            if item_siret:
                seen_sirets.add(item_siret)
            if any(location_key):
                seen_locations.add(location_key)
            merged["locations"].append(item)

        return merged

    @staticmethod
    def _needs_history_expansion(
        raw_result: dict[str, Any],
        parsed: dict[str, Any],
    ) -> bool:
        """Détermine si une recherche textuelle peut apporter des établissements.

        Une recherche directe par SIREN peut ne retourner que le siège courant.
        On déclenche alors une seconde recherche par nom. Si la première réponse
        contient déjà des ``matching_etablissements``, on évite l'appel réseau
        supplémentaire afin de conserver les performances et la compatibilité.
        """
        matching = raw_result.get("matching_etablissements") or []

        try:
            declared_count = int(raw_result.get("nombre_etablissements") or 0)
        except Exception:
            declared_count = 0

        known_count = len(parsed.get("locations") or [])

        # Le compteur déclaré par l'API est l'indicateur le plus fiable : même
        # si la réponse directe contient un matching_etablissements partiel, on
        # complète lorsque le nombre d'implantations connues reste inférieur.
        if declared_count > 1:
            return declared_count > known_count

        # Compatibilité avec les réponses/tests plus anciens qui n'exposent pas
        # nombre_etablissements : si des établissements sont déjà présents, on
        # considère la première résolution suffisante et on évite un second appel.
        if matching:
            return False

        return False

    def _request_results(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Exécute une requête API avec throttle et un retry court sur HTTP 429."""
        self._throttle()
        response = self.session.get(
            self.SEARCH_URL,
            params=params,
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
            self._throttle()
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=self.TIMEOUT,
            )
            self.network_requests += 1

        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        return [item for item in results if isinstance(item, dict)]

    def _history_query_name(
        self,
        identity: dict[str, Any],
        parsed: dict[str, Any],
    ) -> str:
        candidates = [
            identity.get("entreprise"),
            *(parsed.get("names") or []),
        ]
        for value in candidates:
            text = self._clean_text(value)
            if text:
                return text
        return ""

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
            cached["names"] = list(cached.get("names") or [])
            cached["locations"] = [dict(x) for x in cached.get("locations") or []]
            cached["from_cache"] = True
            return cached

        primary_params = {
            "q": siren,
            "minimal": "true",
            "include": "siege,matching_etablissements",
            "limite_matching_etablissements": self.HISTORY_MATCH_LIMIT,
            "per_page": 1,
        }

        try:
            results = self._request_results(primary_params)
            exact = next(
                (
                    item
                    for item in results
                    if self._digits((item or {}).get("siren")) == siren
                ),
                None,
            )
            if not exact:
                parsed = self._empty()
                self._cache[siren] = dict(parsed)
                return parsed

            parsed = self._parse_result(exact, siren)
        except Exception as exc:
            self.failures += 1
            # On ne mémorise pas durablement un échec réseau : un autre SIRET
            # du même SIREN pourra retenter l'appel plus tard dans la session.
            return self._empty(error=f"{type(exc).__name__}: {exc}")

        # La recherche directe par SIREN peut ne présenter que le siège. Lorsque
        # l'API annonce davantage d'établissements, une recherche textuelle par
        # nom permet de récupérer matching_etablissements, y compris fermés.
        if self._needs_history_expansion(exact, parsed):
            history_name = self._history_query_name(identity, parsed)
            if history_name:
                history_params = {
                    "q": history_name,
                    "page": 1,
                    "per_page": self.HISTORY_RESULT_LIMIT,
                    "limite_matching_etablissements": self.HISTORY_MATCH_LIMIT,
                }
                try:
                    history_results = self._request_results(history_params)
                    history_exact = next(
                        (
                            item
                            for item in history_results
                            if self._digits((item or {}).get("siren")) == siren
                        ),
                        None,
                    )
                    if history_exact:
                        history_parsed = self._parse_result(history_exact, siren)
                        parsed = self._merge_parsed(parsed, history_parsed)
                except Exception:
                    # Cette seconde passe est un enrichissement optionnel. Une
                    # panne ne doit jamais annuler l'identité actuelle déjà
                    # résolue ni marquer le résultat principal comme en erreur.
                    pass

        cached = dict(parsed)
        cached["names"] = list(parsed.get("names") or [])
        cached["locations"] = [dict(x) for x in parsed.get("locations") or []]
        cached["from_cache"] = False
        self._cache[siren] = cached

        result = dict(cached)
        result["names"] = list(cached.get("names") or [])
        result["locations"] = [dict(x) for x in cached.get("locations") or []]
        return result

    def stats(self) -> dict[str, int]:
        return {
            "api_requests": int(self.network_requests),
            "api_cache_hits": int(self.cache_hits),
            "api_failures": int(self.failures),
            "api_cache_size": len(self._cache),
        }
