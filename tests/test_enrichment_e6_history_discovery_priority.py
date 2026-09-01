from __future__ import annotations

import requests

from modules.web_fallback import WebFallbackFinder


SOCIETE_URL = "https://www.societe.com/societe/decam-301096772.html"
BATICO_URL = "https://www.batico.fr/artisans-hauts-de-seine/m04.html"
SEO_URL = "https://prix-poele-a-granules.fr/ile-de-france/paris/paris-12e-arrondissement-75012/artisans/decam-27021"


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


def _empty_candidate(source_detail=""):
    return {
        "source": "web_fallback",
        "source_detail": source_detail,
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
        "technical_errors": [],
    }


def _societe_text():
    return (
        "DECAM - 92300 Ancien établissement du 16 août 1974 au 01 octobre 2024 "
        "SIRET 30109677200019 Activité Réparation d'appareils électroménagers "
        "Adresse 9 RUE MARJOLIN, 92300 LEVALLOIS-PERRET Dossier d'urbanisme "
        "Observations RNE transfert De : 9 R MARJOLIN 92300 LEVALLOIS PERRET "
        "A : 56 rue du Faubourg Saint Antoine 75012 Paris"
    )


def test_query_plan_reserves_identity_history_discovery_axis_when_history_unknown():
    finder = WebFallbackFinder()

    queries = finder._query_plan(_identity())

    assert len(queries) <= finder.MAX_QUERIES
    assert any(
        "DECAM" in query.upper()
        and "TELEPHONE" not in query.upper().replace("É", "E")
        and "30109677200027" not in query
        and ("75012" in query or "301096772" in query)
        for query in queries
    )


def test_rechercher_can_discover_history_from_separate_identity_query(monkeypatch):
    finder = WebFallbackFinder()
    seen_queries = []

    def fake_search(query):
        seen_queries.append(query)
        normalized = query.upper().replace("É", "E")

        if "MARJOLIN" in normalized and "92300" in query:
            finder._remember_search_metadata(
                BATICO_URL,
                title="Thermique, Chauffage, Climatisation du Hauts de Seine",
                snippet=(
                    "Decam (S.A.R.L.) 9 r Marjolin, 92300 LEVALLOIS PERRET / "
                    "Téléphone : 01 47 37 56 00"
                ),
            )
            return [BATICO_URL]

        if (
            "DECAM" in normalized
            and "TELEPHONE" not in normalized
            and "30109677200027" not in query
        ):
            finder._remember_search_metadata(
                SOCIETE_URL,
                title="Société DECAM à PARIS (75012) - 301096772",
                snippet="DECAM à PARIS - SIREN 301096772",
            )
            return [SOCIETE_URL]

        return []

    def fake_fetch(url, identity, search_metadata=None):
        if url == SOCIETE_URL:
            candidate = _empty_candidate("societe.com")
            candidate.update(
                nom="DECAM",
                texte=_societe_text(),
                match_score=180,
                match_reasons=["SIREN exact", "nom très proche"],
                confidence="validated",
            )
            return candidate

        if url == BATICO_URL:
            return finder._candidate_from_search_metadata(
                search_metadata,
                identity,
            )

        return _empty_candidate()

    monkeypatch.setattr(finder, "_search_urls", fake_search)
    monkeypatch.setattr(finder, "_fetch_candidate", fake_fetch)

    result = finder.rechercher(_identity())

    assert any(
        "DECAM" in q.upper()
        and "TELEPHONE" not in q.upper().replace("É", "E")
        and "30109677200027" not in q
        for q in seen_queries
    )
    assert any("MARJOLIN" in q.upper() and "92300" in q for q in seen_queries)
    assert result["telephones"] == ["01 47 37 56 00"]
    assert result["site_web"] == ""


def test_unrelated_seo_domain_is_not_promoted_as_company_official_site(monkeypatch):
    html = """
    <html>
      <head><title>DECAM - Installateur de poêle à granulés Paris 12e (75012)</title></head>
      <body>
        <h1>DECAM</h1>
        <p>DECAM à Paris 75012. Retrouvez les coordonnées de cet artisan.</p>
      </body>
    </html>
    """

    class Response:
        text = html
        url = SEO_URL
        headers = {"Content-Type": "text/html; charset=utf-8"}

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        "modules.web_fallback.requests.get",
        lambda *args, **kwargs: Response(),
    )

    finder = WebFallbackFinder()
    candidate = finder._fetch_candidate(
        SEO_URL,
        _identity(),
        search_metadata={
            "url": SEO_URL,
            "title": "DECAM - Installateur de poêle à granulés Paris 12e (75012)",
            "snippet": "DECAM à Paris 75012. Retrouvez les coordonnées de cet artisan.",
        },
    )

    assert candidate["confidence"] == "validated"
    assert candidate["site_web"] == ""


def test_company_named_domain_can_still_be_promoted_as_official_site(monkeypatch):
    official_url = "https://decam.fr/contact"
    html = """
    <html>
      <head><title>DECAM</title></head>
      <body><h1>DECAM</h1><p>Entreprise DECAM à Paris 75012.</p></body>
    </html>
    """

    class Response:
        text = html
        url = official_url
        headers = {"Content-Type": "text/html; charset=utf-8"}

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        "modules.web_fallback.requests.get",
        lambda *args, **kwargs: Response(),
    )

    finder = WebFallbackFinder()
    candidate = finder._fetch_candidate(
        official_url,
        _identity(),
        search_metadata={
            "url": official_url,
            "title": "DECAM",
            "snippet": "DECAM entreprise à Paris 75012",
        },
    )

    assert candidate["confidence"] == "validated"
    assert candidate["site_web"] == "https://decam.fr/"
