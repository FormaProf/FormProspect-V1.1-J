from __future__ import annotations

import requests

from modules.web_fallback import WebFallbackFinder


ALLBIZ_URL = "https://www.allbiz.fr/la-cornue-decam-sav-01-47-37-48-32"


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


def _decam_search_metadata():
    return {
        "url": ALLBIZ_URL,
        "title": "La Cornue Decam SAV | Levallois-Perret",
        "snippet": (
            "DECAM - 9 rue Marjolin 92300 Levallois-Perret. "
            "SIRET 30109677200027. Téléphone : 01 47 37 48 32, "
            "01 47 37 56 00. Email : decam.lacornue@wanadoo.fr"
        ),
    }


def _empty_candidate():
    return {
        "source": "web_fallback",
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
        "technical_errors": [],
    }


def test_search_urls_keeps_title_and_snippet_metadata(monkeypatch):
    """DuckDuckGo ne doit plus jeter l'extrait avant d'ouvrir la page."""

    html = f"""
    <html><body>
      <div class="result">
        <a class="result__a" href="{ALLBIZ_URL}">
          La Cornue Decam SAV | Levallois-Perret
        </a>
        <a class="result__snippet">
          DECAM - 9 rue Marjolin 92300 Levallois-Perret.
          SIRET 30109677200027. Téléphone : 01 47 37 48 32.
        </a>
      </div>
    </body></html>
    """

    class Response:
        text = html

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        "modules.web_fallback.requests.get",
        lambda *args, **kwargs: Response(),
    )

    finder = WebFallbackFinder()
    urls = finder._search_urls("30109677200027")

    assert urls == [ALLBIZ_URL]
    metadata = finder._search_metadata[ALLBIZ_URL]
    assert "La Cornue Decam SAV" in metadata["title"]
    assert "30109677200027" in metadata["snippet"]
    assert "01 47 37 48 32" in metadata["snippet"]


def test_search_metadata_recovers_decam_contacts_with_exact_siret():
    """Un extrait portant le SIRET exact peut fournir téléphone/email sans ouvrir l'annuaire."""

    finder = WebFallbackFinder()
    candidate = finder._candidate_from_search_metadata(
        _decam_search_metadata(),
        _decam_identity(),
    )

    assert candidate["confidence"] == "validated"
    assert candidate["match_score"] == 200
    assert "SIRET exact" in candidate["match_reasons"]
    assert candidate["telephones"] == [
        "01 47 37 48 32",
        "01 47 37 56 00",
    ]
    assert candidate["email"] == "decam.lacornue@wanadoo.fr"

    # Allbiz est une source/annuaire, pas le site officiel de DECAM.
    assert candidate["site_web"] == ""
    assert candidate["source_detail"] == "allbiz.fr"


def test_fetch_403_falls_back_to_validated_search_metadata(monkeypatch):
    """Un HTTP 403 ne doit plus faire perdre un extrait de recherche déjà fiable."""

    def forbidden(*args, **kwargs):
        response = requests.Response()
        response.status_code = 403
        response.url = ALLBIZ_URL
        raise requests.HTTPError(
            f"403 Client Error: Forbidden for url: {ALLBIZ_URL}",
            response=response,
        )

    monkeypatch.setattr("modules.web_fallback.requests.get", forbidden)

    finder = WebFallbackFinder()
    candidate = finder._fetch_candidate(
        ALLBIZ_URL,
        _decam_identity(),
        search_metadata=_decam_search_metadata(),
    )

    assert candidate["confidence"] == "validated"
    assert candidate["telephones"] == [
        "01 47 37 48 32",
        "01 47 37 56 00",
    ]
    assert candidate["email"] == "decam.lacornue@wanadoo.fr"
    assert candidate["site_web"] == ""
    assert any("403" in error for error in candidate["technical_errors"])


def test_rechercher_passes_search_metadata_to_page_fetch(monkeypatch):
    """Le flux complet doit transmettre l'extrait DuckDuckGo au lecteur de page."""

    finder = WebFallbackFinder()
    metadata = _decam_search_metadata()

    monkeypatch.setattr(
        finder,
        "_query_plan",
        lambda identity: ["30109677200027"],
    )

    def fake_search_urls(query):
        finder._search_metadata = {ALLBIZ_URL: dict(metadata)}
        return [ALLBIZ_URL]

    received_metadata = []

    def fake_fetch_candidate(url, identity, search_metadata=None):
        received_metadata.append(search_metadata)
        if not search_metadata:
            return _empty_candidate()
        return {
            "source": "web_fallback",
            "source_detail": "allbiz.fr",
            "nom": "La Cornue Decam SAV | Levallois-Perret",
            "adresse": "",
            "code_postal": "92300",
            "ville": "",
            "telephones": ["01 47 37 48 32"],
            "faxes": [],
            "site_web": "",
            "email": "decam.lacornue@wanadoo.fr",
            "texte": metadata["snippet"],
            "match_score": 200,
            "match_reasons": ["SIRET exact"],
            "confidence": "validated",
            "technical_errors": [],
        }

    monkeypatch.setattr(finder, "_search_urls", fake_search_urls)
    monkeypatch.setattr(finder, "_fetch_candidate", fake_fetch_candidate)

    result = finder.rechercher(_decam_identity())

    assert received_metadata == [metadata]
    assert result["confidence"] == "validated"
    assert result["telephones"] == ["01 47 37 48 32"]
    assert result["email"] == "decam.lacornue@wanadoo.fr"


def test_directory_profile_urls_are_not_promoted_to_official_site():
    """Une fiche SEO/annuaire identifiée par SIRET reste une source, jamais le site officiel."""

    assert (
        WebFallbackFinder._is_official_candidate_url(
            "https://fernandesclimatisation.com/entreprise/301096772-decam-paris"
        )
        is False
    )
    assert (
        WebFallbackFinder._is_official_candidate_url(
            "https://www.monartisan.info/decam-30109677200027"
        )
        is False
    )
    assert (
        WebFallbackFinder._is_official_candidate_url(
            "https://decam.biz/"
        )
        is True
    )


def test_search_metadata_without_strong_identity_is_not_validated():
    """Un téléphone visible dans un extrait ne suffit jamais sans preuve d'identité forte."""

    finder = WebFallbackFinder()
    metadata = {
        "url": "https://directory.example/decam-services",
        "title": "DECAM SERVICES",
        "snippet": (
            "DECAM SERVICES - Marseille. Téléphone : 01 99 99 99 99. "
            "Email : contact@autre-societe.example"
        ),
    }

    candidate = finder._candidate_from_search_metadata(
        metadata,
        _decam_identity(),
    )

    assert candidate["confidence"] != "validated"
    assert "SIRET exact" not in candidate["match_reasons"]
