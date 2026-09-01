from __future__ import annotations

from modules.web_fallback import WebFallbackFinder


BATICO_URL = "https://www.batico.fr/artisans-hauts-de-seine/m04.html"


def _decam_identity():
    return {
        "entreprise": "DECAM",
        "siret": "30109677200027",
        "siren": "301096772",
        "adresse": "56 RUE DU FAUBOURG SAINT ANTOINE",
        "code_postal": "75012",
        "ville": "PARIS",
        "noms_recherche": ["DECAM", "D.E.C.A.M."],
        "localisations_recherche": [
            {
                "adresse": "56 RUE DU FAUBOURG SAINT ANTOINE",
                "code_postal": "75012",
                "ville": "PARIS",
            },
            {
                "adresse": "9 RUE MARJOLIN",
                "code_postal": "92300",
                "ville": "LEVALLOIS-PERRET",
            },
        ],
    }


def _batico_metadata():
    return {
        "url": BATICO_URL,
        "title": "Thermique, Chauffage, Climatisation du Hauts de Seine",
        "snippet": (
            "Decam (S.A.R.L.) 9 r Marjolin, 92300 LEVALLOIS PERRET / "
            "Téléphone : 01 47 37 56 00"
        ),
    }


def test_query_plan_uses_historical_street_address():
    """Une ancienne adresse précise doit guider la 3e requête, pas seulement la ville."""
    finder = WebFallbackFinder()

    queries = finder._query_plan(_decam_identity())

    assert len(queries) <= finder.MAX_QUERIES
    assert any(
        "9 RUE MARJOLIN" in query.upper()
        and "92300" in query
        and "LEVALLOIS" in query.upper()
        for query in queries
    )


def test_generic_search_title_can_use_exact_company_name_from_snippet():
    """Un annuaire peut avoir un titre générique : le bloc DECAM du snippet doit suffire."""
    finder = WebFallbackFinder()

    candidate = finder._candidate_from_search_metadata(
        _batico_metadata(),
        _decam_identity(),
    )

    assert candidate["confidence"] == "validated"
    assert candidate["match_score"] >= 85
    assert candidate["telephones"] == ["01 47 37 56 00"]
    assert candidate["site_web"] == ""
    assert any(
        reason in candidate["match_reasons"]
        for reason in ("nom très proche", "enseigne/alias très proche")
    )
    assert any(
        reason in candidate["match_reasons"]
        for reason in ("code postal exact", "code postal présent")
    )


def test_multi_company_directory_page_extracts_only_decam_contact(monkeypatch):
    """Une page listant plusieurs artisans ne doit pas mélanger leurs téléphones."""
    html = """
    <html>
      <head><title>Thermique, Chauffage, Climatisation du Hauts de Seine</title></head>
      <body>
        Daikin Klima Installateur qualifié
        15 r Vieux Pont, 92000 NANTERRE / Téléphone : 01 46 69 29 00

        Decam (S.A.R.L.)
        9 r Marjolin, 92300 LEVALLOIS PERRET / Téléphone : 01 47 37 56 00

        Dao-Tholozan
        97 Bis r Colombes, 92400 COURBEVOIE / Téléphone : 01 43 33 14 33
      </body>
    </html>
    """

    class Response:
        text = html
        url = BATICO_URL
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
        BATICO_URL,
        _decam_identity(),
        search_metadata=_batico_metadata(),
    )

    assert candidate["confidence"] == "validated"
    assert candidate["telephones"] == ["01 47 37 56 00"]
    assert "01 46 69 29 00" not in candidate["telephones"]
    assert "01 43 33 14 33" not in candidate["telephones"]
    assert candidate["site_web"] == ""


def test_batico_listing_is_never_promoted_to_official_site():
    """La page catalogue Batico est une source de contact, pas le site de DECAM."""
    assert WebFallbackFinder._is_official_candidate_url(BATICO_URL) is False
