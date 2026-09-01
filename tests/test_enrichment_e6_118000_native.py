import asyncio
import importlib
import sqlite3

import pytest

from services.enrichment_service import EnrichmentService


def _rejected(source):
    return {
        "source": source,
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


def _validated(source, *, phones=None, score=180):
    return {
        "source": source,
        "source_detail": "",
        "nom": "DECAM",
        "adresse": "9 RUE MARJOLIN",
        "code_postal": "92300",
        "ville": "LEVALLOIS-PERRET",
        "telephones": list(phones or []),
        "faxes": [],
        "site_web": "",
        "email": "",
        "texte": "DECAM 9 RUE MARJOLIN 92300 LEVALLOIS-PERRET",
        "match_score": score,
        "match_reasons": ["nom très proche", "code postal exact", "ville exacte"],
        "confidence": "validated",
        "technical_errors": [],
    }


def _create_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE prospects (
            id INTEGER PRIMARY KEY,
            entreprise TEXT DEFAULT '',
            siret TEXT DEFAULT '',
            siren TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            code_postal TEXT DEFAULT '',
            ville TEXT DEFAULT '',
            code_naf TEXT DEFAULT '',
            noms_recherche TEXT DEFAULT '[]',
            telephone TEXT DEFAULT '',
            mobile TEXT DEFAULT '',
            site_web TEXT DEFAULT '',
            email TEXT DEFAULT '',
            facebook TEXT DEFAULT '',
            linkedin TEXT DEFAULT '',
            instagram TEXT DEFAULT '',
            twitter TEXT DEFAULT '',
            youtube TEXT DEFAULT '',
            social_other_urls TEXT DEFAULT '',
            statut_enrichissement TEXT DEFAULT '',
            date_collecte TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO prospects (
            id, entreprise, siret, siren, adresse, code_postal, ville,
            code_naf, noms_recherche, statut_enrichissement
        )
        VALUES (1, 'DECAM', '30109677200027', '301096772',
                '56 RUE DU FAUBOURG SAINT-ANTOINE', '75012', 'PARIS',
                '43.22B', '["DECAM"]', '')
        """
    )
    conn.commit()
    conn.close()


class FakeApi:
    def stats(self):
        return {
            "api_requests": 0,
            "api_cache_hits": 0,
            "api_failures": 0,
            "api_cache_size": 0,
        }

    def resolve(self, identity):
        return {
            "resolved": True,
            "siren": "301096772",
            "siret_siege": "30109677200027",
            "names": ["DECAM"],
            "locations": [
                {
                    "siret": "30109677200027",
                    "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                    "code_postal": "75012",
                    "ville": "PARIS",
                    "est_siege": True,
                },
                {
                    "siret": "30109677200019",
                    "adresse": "9 RUE MARJOLIN 92300 LEVALLOIS-PERRET",
                    "code_postal": "92300",
                    "ville": "LEVALLOIS-PERRET",
                    "est_siege": False,
                },
            ],
            "error": "",
            "from_cache": False,
        }


class FakePages:
    def __init__(self, result):
        self.result = result

    async def rechercher_nom(self, identity):
        return dict(self.result)

    async def fermer(self):
        return None


class FakeGoogle:
    async def rechercher(self, identity):
        return _rejected("google_maps")

    async def fermer(self):
        return None


class FakeWeb:
    def rechercher(self, identity):
        return _rejected("web_fallback")


class Recording118000:
    def __init__(self, result=None, exc=None):
        self.result = result or _rejected("118000")
        self.exc = exc
        self.calls = []

    def rechercher(self, identity):
        self.calls.append(dict(identity))
        if self.exc:
            raise self.exc
        return dict(self.result)


class FakeEmail:
    @staticmethod
    def _is_technical(email):
        return False

    def chercher(self, site_web):
        return ""


class FakeSocial:
    def chercher(self, site_web):
        return {
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "twitter": "",
            "youtube": "",
            "other_urls": [],
        }


def _configure(service, source118, pages):
    service.entreprise_api = FakeApi()
    service.pages_jaunes = FakePages(pages)
    service.google = FakeGoogle()
    service.web_fallback = FakeWeb()
    service.annuaire_118000 = source118
    service.email_finder = FakeEmail()
    service.social_finder = FakeSocial()


def test_118000_completes_existing_pagesjaunes_phone(tmp_path, monkeypatch):
    db = tmp_path / "annuaire118000.db"
    _create_db(db)

    source118 = Recording118000(
        _validated(
            "118000",
            phones=["01 47 39 10 49", "01 47 37 56 00"],
            score=115,
        )
    )
    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        score=200,
    )

    service = EnrichmentService()
    _configure(service, source118, pages)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(source118.calls) == 1

    conn = sqlite3.connect(db)
    telephone = conn.execute(
        "SELECT telephone FROM prospects WHERE id = 1"
    ).fetchone()[0]
    conn.close()

    assert set(telephone.split(" / ")) == {
        "01 47 37 56 00",
        "01 47 39 10 49",
    }
    assert result["enrichis"] == 1


def test_118000_receives_api_historical_locations(tmp_path, monkeypatch):
    db = tmp_path / "history118000.db"
    _create_db(db)

    source118 = Recording118000(_rejected("118000"))
    service = EnrichmentService()
    _configure(service, source118, _rejected("pages_jaunes"))
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(source118.calls) == 1
    locations = source118.calls[0]["localisations_recherche"]
    assert any(
        item.get("code_postal") == "92300"
        and "MARJOLIN" in str(item.get("adresse") or "").upper()
        for item in locations
    )


def test_118000_failure_does_not_discard_valid_pagesjaunes_result(tmp_path, monkeypatch):
    db = tmp_path / "failure118000.db"
    _create_db(db)

    source118 = Recording118000(exc=RuntimeError("temporary 118000 failure"))
    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        score=200,
    )

    service = EnrichmentService()
    _configure(service, source118, pages)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(source118.calls) == 1

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT telephone, statut_enrichissement FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert row == ("01 47 37 56 00", service.ENRICHED_STATUS)
    assert result["erreurs"] == 0


def test_native_118000_parser_extracts_both_decam_cards(monkeypatch):
    try:
        module = importlib.import_module("modules.annuaire_118000")
    except ModuleNotFoundError:
        pytest.fail("modules.annuaire_118000 n'existe pas encore")

    html = """
    <html><body>
      <div class="card">
        <div data-info='{"comCode":"C0061241166","address":"9 RUE MARJOLIN",
        "mainLine":"0147391049","tel":"0147391049",
        "urlDetail":"https://www.118000.fr/e_C0061241166","name":"Decam",
        "cp":"92300","city":"LEVALLOIS PERRET"}'></div>
        Decam 9 RUE MARJOLIN 92300 Levallois Perret 01 47 39 10 49
      </div>
      <div class="card">
        <div data-info='{"comCode":"C0097720982","address":"",
        "mainLine":"0147375600","tel":"0147375600",
        "urlDetail":"https://www.118000.fr/e_C0097720982","name":"Decam",
        "cp":"92300","city":"LEVALLOIS PERRET"}'></div>
        Decam 92300 Levallois Perret 01 47 37 56 00
      </div>
    </body></html>
    """

    class Response:
        status_code = 200
        text = html
        url = "https://www.118000.fr/search?who=DECAM&label=92300+LEVALLOIS-PERRET"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        "modules.annuaire_118000.requests.get",
        lambda *args, **kwargs: Response(),
    )

    finder = module.Annuaire118000Finder()
    identity = {
        "entreprise": "DECAM",
        "siret": "30109677200027",
        "siren": "301096772",
        "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
        "code_postal": "75012",
        "ville": "PARIS",
        "noms_recherche": ["DECAM"],
        "localisations_recherche": [
            {
                "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                "code_postal": "75012",
                "ville": "PARIS",
            },
            {
                "adresse": "9 RUE MARJOLIN 92300 LEVALLOIS-PERRET",
                "code_postal": "92300",
                "ville": "LEVALLOIS-PERRET",
            },
        ],
    }

    result = finder.rechercher(identity)

    assert result["confidence"] == "validated"
    assert set(result["telephones"]) == {
        "01 47 39 10 49",
        "01 47 37 56 00",
    }
    assert "118000.fr/e_C0061241166" in result["source_detail"]
