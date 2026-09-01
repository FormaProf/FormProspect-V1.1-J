from __future__ import annotations

from modules.web_fallback import WebFallbackFinder


SOCIETE_URL = "https://www.societe.com/societe/decam-301096772.html"
BATICO_URL = "https://www.batico.fr/artisans-hauts-de-seine/m04.html"


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
                "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                "code_postal": "75012",
                "ville": "PARIS",
            }
        ],
    }


def _societe_text():
    return (
        "DECAM - 75012. SIRET 30109677200027. "
        "Adresse 56 RUE DU FAUBOURG SAINT-ANTOINE, 75012 PARIS. "
        "DECAM - 92300 Ancien établissement du 16 août 1974 au 01 octobre 2024 "
        "SIRET 30109677200019 Activité Réparation d'appareils électroménagers. "
        "Adresse 9 RUE MARJOLIN, 92300 LEVALLOIS-PERRET."
    )


def _empty_candidate(source_detail=""):
    return {
        "source": "web_fallback",
        "source_detail": source_detail,
        "nom": "DECAM",
        "adresse": "",
        "code_postal": "75012",
        "ville": "PARIS",
        "telephones": [],
        "faxes": [],
        "site_web": "",
        "email": "",
        "texte": "",
        "match_score": 93,
        "match_reasons": ["nom très proche", "code postal exact", "ville exacte"],
        "confidence": "validated",
        "technical_errors": [],
    }


def test_societe_text_extracts_decam_historical_establishment():
    finder = WebFallbackFinder()

    locations = finder._historical_locations_from_text(
        _societe_text(),
        _identity(),
    )

    assert locations == [
        {
            "adresse": "9 RUE MARJOLIN",
            "code_postal": "92300",
            "ville": "LEVALLOIS-PERRET",
            "siret": "30109677200019",
        }
    ]


def test_historical_location_is_appended_without_duplicate_current_address():
    finder = WebFallbackFinder()

    enriched = finder._identity_with_historical_locations(
        _identity(),
        [
            {
                "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE",
                "code_postal": "75012",
                "ville": "PARIS",
                "siret": "30109677200027",
            },
            {
                "adresse": "9 RUE MARJOLIN",
                "code_postal": "92300",
                "ville": "LEVALLOIS-PERRET",
                "siret": "30109677200019",
            },
        ],
    )

    locations = enriched["localisations_recherche"]
    assert len(locations) == 2
    assert locations[-1]["adresse"] == "9 RUE MARJOLIN"
    assert locations[-1]["code_postal"] == "92300"
    assert locations[-1]["ville"] == "LEVALLOIS-PERRET"


def test_rechercher_runs_second_pass_on_discovered_history(monkeypatch):
    """DECAM doit pouvoir découvrir Marjolin via Societe.com puis chercher son téléphone."""
    finder = WebFallbackFinder()
    seen_queries = []

    def fake_search_urls(query):
        seen_queries.append(query)
        upper = query.upper()
        if "MARJOLIN" in upper and "92300" in upper:
            finder._remember_search_metadata(
                BATICO_URL,
                title="Thermique, Chauffage, Climatisation du Hauts de Seine",
                snippet=(
                    "Decam (S.A.R.L.) 9 r Marjolin, 92300 LEVALLOIS PERRET / "
                    "Téléphone : 01 47 37 56 00"
                ),
            )
            return [BATICO_URL]

        finder._remember_search_metadata(
            SOCIETE_URL,
            title="Société DECAM à PARIS (75012) - 301096772",
            snippet="DECAM 75012 PARIS SIREN 301096772",
        )
        return [SOCIETE_URL]

    def fake_fetch(url, identity, search_metadata=None):
        if url == SOCIETE_URL:
            candidate = _empty_candidate("societe.com")
            candidate["match_score"] = 200
            candidate["match_reasons"] = ["SIREN exact"]
            candidate["texte"] = _societe_text()
            return candidate

        assert url == BATICO_URL
        return finder._candidate_from_search_metadata(
            search_metadata,
            identity,
        )

    monkeypatch.setattr(finder, "_search_urls", fake_search_urls)
    monkeypatch.setattr(finder, "_fetch_candidate", fake_fetch)

    result = finder.rechercher(_identity())

    assert any("MARJOLIN" in query.upper() for query in seen_queries)
    assert result["confidence"] == "validated"
    assert result["telephones"] == ["01 47 37 56 00"]
    assert result["site_web"] == ""
