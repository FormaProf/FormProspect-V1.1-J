import asyncio
import sqlite3
from pathlib import Path

from modules.company_matcher import confidence, score_candidate
from services.enrichment_service import EnrichmentService


class FakeFinder:
    def __init__(self, by_id=None, by_name=None, google=None):
        self.by_id = by_id
        self.by_name = by_name
        self.google = google

    async def ouvrir(self):
        return None

    async def fermer(self):
        return None

    async def rechercher_identifiant(self, identity):
        return self.by_id or rejected("pages_jaunes")

    async def rechercher_nom(self, identity):
        return self.by_name or rejected("pages_jaunes")

    async def rechercher(self, identity):
        return self.google or rejected("google_maps")


class FakeApi:
    def resolve(self, identity):
        return {
            "resolved": False, "siren": "", "siret_siege": "",
            "names": [], "locations": [], "error": "", "from_cache": False,
        }

    def stats(self):
        return {
            "api_requests": 0, "api_cache_hits": 0, "api_failures": 0,
            "api_cache_size": 0,
        }


class FakeWeb:
    def rechercher(self, identity):
        return rejected("web_fallback")


class FakeEmailFinder:
    def __init__(self, value=""):
        self.value = value

    def chercher(self, site):
        return self.value


class FakeSocialFinder:
    def chercher(self, site):
        return {
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "twitter": "",
            "youtube": "",
            "other_urls": [],
        }


def rejected(source):
    return {
        "source": source,
        "nom": "",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": [],
        "site_web": "",
        "texte": "",
        "match_score": 0,
        "match_reasons": [],
        "confidence": "rejected",
        "technical_errors": [],
    }


def validated(source="pages_jaunes", phones=None, site=""):
    return {
        "source": source,
        "nom": "Entreprise test",
        "adresse": "1 rue Test 59000 Lille",
        "code_postal": "59000",
        "ville": "Lille",
        "telephones": phones or [],
        "site_web": site,
        "texte": "SIRET 12345678900011",
        "match_score": 200,
        "match_reasons": ["SIRET exact"],
        "confidence": "validated",
        "technical_errors": [],
    }


def create_db(path: Path, status="Importé"):
    con = sqlite3.connect(path)
    con.execute(
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
    con.execute(
        """
        INSERT INTO prospects (
            id, entreprise, siret, siren, adresse, code_postal, ville,
            code_naf, statut_enrichissement
        ) VALUES (1, 'Entreprise test', '12345678900011', '123456789',
                  '1 rue Test', '59000', 'Lille', '4399A', ?)
        """,
        (status,),
    )
    con.commit()
    con.close()


def test_exact_siret_overrides_name_and_location_mismatch():
    identity = {
        "entreprise": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "siret": "05480416600129",
        "siren": "054804166",
        "code_postal": "75010",
        "ville": "PARIS",
        "adresse": "4 boulevard Saint-Martin",
    }
    candidate = {
        "nom": "Agence Etoile Cipa",
        "code_postal": "13001",
        "ville": "Marseille",
        "adresse": "Adresse commerciale différente",
        "texte": "Informations légales - SIRET 054 804 166 00129",
    }
    score, reasons = score_candidate(identity, candidate)
    assert score == 200
    assert reasons == ["SIRET exact"]
    assert confidence(score) == "validated"


def test_valid_identity_without_useful_data_is_not_marked_enriched(tmp_path, monkeypatch):
    db = tmp_path / "project.db"
    create_db(db)
    service = EnrichmentService()
    service.entreprise_api = FakeApi()
    service.web_fallback = FakeWeb()
    service.pages_jaunes = FakeFinder(by_name=validated())
    service.google = FakeFinder(google=validated(source="google_maps"))
    service.email_finder = FakeEmailFinder()
    service.social_finder = FakeSocialFinder()

    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(service._enrichir_async(db, limite=1))
    con = sqlite3.connect(db)
    status = con.execute(
        "SELECT statut_enrichissement FROM prospects WHERE id=1"
    ).fetchone()[0]
    con.close()

    assert status == service.NO_RELIABLE_RESULT_STATUS
    assert result["traites"] == 1
    assert result["enrichis"] == 0
    assert result["sans_resultat"] == 1
    assert result["erreurs"] == 0


def test_useful_phone_marks_prospect_enriched(tmp_path, monkeypatch):
    db = tmp_path / "project.db"
    create_db(db)
    service = EnrichmentService()
    service.entreprise_api = FakeApi()
    service.web_fallback = FakeWeb()
    service.pages_jaunes = FakeFinder(
        by_name=validated(phones=["01 40 37 05 05"])
    )
    service.google = FakeFinder(google=rejected("google_maps"))
    service.email_finder = FakeEmailFinder()
    service.social_finder = FakeSocialFinder()

    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(service._enrichir_async(db, limite=1))
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT statut_enrichissement, telephone FROM prospects WHERE id=1"
    ).fetchone()
    con.close()

    assert row[0] == service.ENRICHED_STATUS
    assert row[1] == "01 40 37 05 05"
    assert result["traites"] == 1
    assert result["enrichis"] == 1
    assert result["sans_resultat"] == 0
    assert result["telephones"] == 1


def test_reset_no_result_makes_prospect_retryable(tmp_path):
    db = tmp_path / "project.db"
    create_db(db, status=EnrichmentService.NO_RELIABLE_RESULT_STATUS)
    service = EnrichmentService()

    assert service.compter_sans_resultat(db) == 1
    assert service.compter_a_enrichir(db) == 0
    assert service.reinitialiser_sans_resultat(db) == 1
    assert service.compter_sans_resultat(db) == 0
    assert service.compter_a_enrichir(db) == 1
