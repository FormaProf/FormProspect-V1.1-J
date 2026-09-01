from __future__ import annotations

import threading
import time

from modules.web_fallback import WebFallbackFinder


def _identity():
    return {
        "entreprise": "DECAM",
        "siret": "30109677200027",
        "siren": "301096772",
        "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE",
        "code_postal": "75012",
        "ville": "PARIS",
        "noms_recherche": ["DECAM"],
        "localisations_recherche": [
            {
                "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE",
                "code_postal": "75012",
                "ville": "PARIS",
            }
        ],
    }


def _validated(url: str):
    return {
        "source": "web_fallback",
        "source_detail": "example.test",
        "nom": "DECAM",
        "adresse": "",
        "code_postal": "75012",
        "ville": "PARIS",
        "telephones": ["01 47 37 56 00"],
        "faxes": [],
        "site_web": "",
        "email": "",
        "texte": "DECAM 75012 PARIS Téléphone 01 47 37 56 00",
        "match_score": 200,
        "match_reasons": ["SIRET exact"],
        "confidence": "validated",
        "technical_errors": [],
    }


def test_search_queries_are_serialized_to_avoid_search_engine_throttling(monkeypatch):
    """Les requêtes moteur doivent rester séquentielles; les pages peuvent être lues en parallèle."""
    finder = WebFallbackFinder()
    lock = threading.Lock()
    active = 0
    max_active = 0
    concurrent_detected = False
    seen_queries = []

    def fake_search(query):
        nonlocal active, max_active, concurrent_detected
        with lock:
            active += 1
            max_active = max(max_active, active)
            if active > 1:
                concurrent_detected = True
            seen_queries.append(query)

        # Laisse assez de temps à une éventuelle seconde requête parallèle
        # pour entrer. Un moteur anti-bot peut alors renvoyer une page vide.
        time.sleep(0.06)

        with lock:
            blocked = concurrent_detected
            active -= 1

        if blocked:
            return []

        url = f"https://example.test/{len(seen_queries)}"
        finder._remember_search_metadata(
            url,
            title="DECAM",
            snippet="DECAM 75012 PARIS SIRET 30109677200027 Téléphone 01 47 37 56 00",
        )
        return [url]

    monkeypatch.setattr(finder, "_search_urls", fake_search)
    monkeypatch.setattr(
        finder,
        "_fetch_candidate",
        lambda url, identity, search_metadata=None: _validated(url),
    )

    result = finder.rechercher(_identity())

    assert len(seen_queries) >= 2
    assert max_active == 1
    assert result["confidence"] == "validated"
    assert result["telephones"] == ["01 47 37 56 00"]
