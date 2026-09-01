import asyncio
import sqlite3

from services.enrichment_service import EnrichmentService
from services.scoring_service import ScoringService


def _result(source, *, phone="", site="", score=90):
    return {
        "source": source,
        "source_detail": "",
        "nom": "ACME",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": [phone] if phone else [],
        "faxes": [],
        "site_web": site,
        "email": "",
        "texte": "ACME",
        "match_score": score,
        "match_reasons": [],
        "confidence": "validated",
        "technical_errors": [],
    }


class _Api:
    def __init__(self):
        self.requests = 0

    def stats(self):
        return {
            "api_requests": self.requests,
            "api_cache_hits": 0,
            "api_failures": 0,
            "api_cache_size": 0,
        }

    def resolve(self, _identity):
        self.requests += 1
        return {"resolved": False}


class _PagesJaunes:
    def __init__(self, result, calls):
        self.result = result
        self.calls = calls

    async def rechercher_nom(self, _identity):
        self.calls["pages_jaunes"] += 1
        return self.result

    async def fermer(self):
        return None


class _GoogleMaps:
    def __init__(self, result, calls):
        self.result = result
        self.calls = calls

    async def rechercher(self, _identity):
        self.calls["google"] += 1
        return self.result

    async def fermer(self):
        return None


class _SyncSource:
    def __init__(self, result, calls, key):
        self.result = result
        self.calls = calls
        self.key = key

    def rechercher(self, _identity):
        self.calls[self.key] += 1
        return self.result


class _EmailFinder:
    def __init__(self, calls):
        self.calls = calls

    @staticmethod
    def _is_technical(_email):
        return False

    def chercher(self, _site):
        self.calls["email"] += 1
        return ""


class _SocialFinder:
    def __init__(self, calls):
        self.calls = calls

    def chercher(self, _site):
        self.calls["social"] += 1
        return {}


def _create_database(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE prospects (
            id INTEGER PRIMARY KEY,
            entreprise TEXT,
            siret TEXT,
            siren TEXT,
            adresse TEXT,
            code_postal TEXT,
            ville TEXT,
            code_naf TEXT,
            noms_recherche TEXT,
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
            id, entreprise, siret, siren, adresse, code_postal,
            ville, code_naf, noms_recherche
        ) VALUES (1, 'ACME', '12345678900012', '123456789', '', '', '', '', '[]')
        """
    )
    conn.commit()
    conn.close()


def _build_service(calls):
    service = EnrichmentService.__new__(EnrichmentService)
    service.entreprise_api = _Api()
    service.pages_jaunes = _PagesJaunes(
        _result(
            "pages_jaunes",
            phone="01 00 00 00 00",
            site="https://direct-acme.example",
        ),
        calls,
    )
    service.google = _GoogleMaps(
        _result(
            "google_maps",
            phone="02 00 00 00 00",
            site="https://maps-acme.example",
        ),
        calls,
    )
    service.annuaire_118000 = _SyncSource(
        _result(
            "118000",
            phone="03 00 00 00 00",
            site="https://annuaire-acme.example",
        ),
        calls,
        "118000",
    )
    service.web_fallback = _SyncSource(
        _result(
            "web_fallback",
            phone="04 00 00 00 00",
            site="https://web-acme.example",
        ),
        calls,
        "web",
    )
    service.email_finder = _EmailFinder(calls)
    service.social_finder = _SocialFinder(calls)
    return service


def _run_strategy(tmp_path, monkeypatch, strategy):
    db = tmp_path / f"{strategy}.db"
    _create_database(db)
    monkeypatch.setattr(
        ScoringService,
        "score_prospect_with_connection",
        staticmethod(lambda _conn, _prospect_id: None),
    )
    calls = {
        "pages_jaunes": 0,
        "google": 0,
        "118000": 0,
        "web": 0,
        "email": 0,
        "social": 0,
    }
    result = asyncio.run(
        _build_service(calls)._enrichir_async(str(db), strategy=strategy)
    )
    return calls, result


def test_rapid_stops_optional_sources_after_direct_reliable_contact(tmp_path, monkeypatch):
    calls, result = _run_strategy(tmp_path, monkeypatch, "rapid")
    assert result["enrichment_method"] == "rapid"
    assert result["enrichis"] == 1
    assert calls == {
        "pages_jaunes": 1,
        "google": 0,
        "118000": 0,
        "web": 0,
        "email": 1,
        "social": 1,
    }


def test_standard_preserves_full_e6_source_path_and_two_site_analysis(tmp_path, monkeypatch):
    calls, result = _run_strategy(tmp_path, monkeypatch, "standard")
    assert result["enrichment_method"] == "standard"
    assert result["enrichis"] == 1
    assert calls == {
        "pages_jaunes": 1,
        "google": 1,
        "118000": 1,
        "web": 1,
        "email": 2,
        "social": 2,
    }


def test_deep_preserves_full_sources_and_analyzes_four_sites(tmp_path, monkeypatch):
    calls, result = _run_strategy(tmp_path, monkeypatch, "deep")
    assert result["enrichment_method"] == "deep"
    assert result["enrichis"] == 1
    assert calls == {
        "pages_jaunes": 1,
        "google": 1,
        "118000": 1,
        "web": 1,
        "email": 4,
        "social": 4,
    }
