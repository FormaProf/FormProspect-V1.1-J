import asyncio
import json
import sqlite3

from core.database import init_database
from modules.company_matcher import confidence, identity_locations, identity_names, score_candidate
from modules.google_maps import GoogleMapsFinder
from modules.pages_jaunes import PagesJaunesFinder
from services.enrichment_service import EnrichmentService


class _EmptyFinder:
    async def ouvrir(self):
        return None

    async def fermer(self):
        return None

    async def rechercher_nom(self, identity):
        return self._empty("pages_jaunes")

    async def rechercher(self, identity):
        return self._empty("google_maps")

    @staticmethod
    def _empty(source):
        return {
            "source": source,
            "nom": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": [],
        }


class _NoApi:
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


class _NoEmail:
    def chercher(self, site):
        return ""


class _NoSocial:
    def chercher(self, site):
        return {
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "twitter": "",
            "youtube": "",
            "other_urls": [],
        }


def _make_db(tmp_path):
    path = tmp_path / "project.db"
    init_database(path)
    conn = sqlite3.connect(path)
    EnrichmentService._ensure_social_columns(conn)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO prospects (
            entreprise, siret, siren, adresse, code_postal, ville, code_naf,
            telephone, mobile, site_web, email, noms_recherche,
            statut_enrichissement, date_collecte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
        """,
        (
            "C T O", "30631273700050", "306312737", "28 ROUTE DE CHATOU",
            "78420", "CARRIERES-SUR-SEINE", "43.22B", "01 39 14 57 56",
            "06 11 22 33 44", "https://www.cto-chauffage.fr/", "cto@wanadoo.fr",
            json.dumps(["CONSTRUCTION TRADITIONNELLES DE L'OUEST"]), "Enrichi",
        ),
    )
    cur.execute(
        """
        INSERT INTO prospects (
            entreprise, siret, siren, adresse, code_postal, ville, code_naf,
            telephone, mobile, site_web, email, noms_recherche,
            statut_enrichissement, date_collecte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', '', '', 'Importé', '')
        """,
        (
            "C T O", "30631273700043", "306312737", "16 RUE GABRIEL PERI",
            "78420", "CARRIERES-SUR-SEINE", "43.99C",
        ),
    )
    conn.commit()
    conn.close()
    return path


def _target_identity(service, conn):
    groups = service._charger_contexte_siren(conn)
    row = conn.execute(
        """
        SELECT id, entreprise, siret, siren, adresse, code_postal, ville,
               code_naf, noms_recherche
        FROM prospects WHERE siret = '30631273700043'
        """
    ).fetchone()
    identity = {
        "entreprise": row[1],
        "siret": row[2],
        "siren": row[3],
        "adresse": row[4],
        "code_postal": row[5],
        "ville": row[6],
        "code_naf": row[7],
        "noms_recherche": service._parse_names_payload(row[8]),
    }
    return row[0], service._identity_avec_contexte_siren(identity, row[0], groups), groups


def test_cto_context_mutualizes_aliases_locations_and_compact_acronym(tmp_path):
    path = _make_db(tmp_path)
    service = EnrichmentService()
    conn = sqlite3.connect(path)
    prospect_id, identity, _ = _target_identity(service, conn)
    conn.close()

    names = identity_names(identity)
    assert "CONSTRUCTION TRADITIONNELLES DE L'OUEST" in names
    assert "CTO" in names

    locations = identity_locations(identity)
    assert any(item["adresse"] == "16 RUE GABRIEL PERI" for item in locations)
    assert any(item["adresse"] == "28 ROUTE DE CHATOU" for item in locations)


def test_search_plans_use_siren_sibling_data_without_searching_identifiers(tmp_path):
    path = _make_db(tmp_path)
    service = EnrichmentService()
    conn = sqlite3.connect(path)
    _, identity, _ = _target_identity(service, conn)
    conn.close()

    pj_plan = PagesJaunesFinder._name_search_plan(identity)
    pj_text = " | ".join(f"{name} {location}" for name, location in pj_plan)
    assert "CONSTRUCTION TRADITIONNELLES DE L'OUEST" in pj_text
    assert "CTO" in pj_text
    assert "30631273700043" not in pj_text
    assert "306312737" not in pj_text

    maps_queries = GoogleMapsFinder._search_queries(identity)
    maps_text = " | ".join(maps_queries)
    assert "CONSTRUCTION TRADITIONNELLES DE L'OUEST" in maps_text
    assert "CTO" in maps_text
    assert "30631273700043" not in maps_text
    assert "306312737" not in maps_text


def test_matcher_accepts_public_profile_at_sibling_location(tmp_path):
    path = _make_db(tmp_path)
    service = EnrichmentService()
    conn = sqlite3.connect(path)
    _, identity, _ = _target_identity(service, conn)
    conn.close()

    candidate = {
        "nom": "Cto",
        "adresse": "28 route de Chatou 78420 Carrières-sur-Seine",
        "code_postal": "78420",
        "ville": "Carrières-sur-Seine",
        "texte": "Cto 28 route de Chatou 78420 Carrières-sur-Seine",
    }
    score, reasons = score_candidate(identity, candidate)
    assert confidence(score) == "validated"
    assert score >= 65
    assert any("alias" in reason for reason in reasons)


def test_siren_contacts_are_reused_as_fallback(tmp_path):
    path = _make_db(tmp_path)
    service = EnrichmentService()
    conn = sqlite3.connect(path)
    prospect_id, identity, groups = _target_identity(service, conn)
    bundle = service._contacts_du_siren(identity, prospect_id, groups)
    conn.close()

    assert "01 39 14 57 56" in bundle["phones"]
    assert "06 11 22 33 44" in bundle["mobiles"]
    assert bundle["site_web"] == "https://www.cto-chauffage.fr/"
    assert bundle["email"] == "cto@wanadoo.fr"


def test_enrichment_can_fallback_to_existing_siren_sibling_contacts(tmp_path):
    path = _make_db(tmp_path)
    service = EnrichmentService()
    service.entreprise_api = _NoApi()
    service.pages_jaunes = _EmptyFinder()
    service.google = _EmptyFinder()
    service.email_finder = _NoEmail()
    service.social_finder = _NoSocial()

    result = service.enrichir(path, limite=1)
    assert result["enrichis"] == 1
    assert result["sans_resultat"] == 0

    conn = sqlite3.connect(path)
    row = conn.execute(
        """
        SELECT telephone, mobile, site_web, email, statut_enrichissement
        FROM prospects WHERE siret = '30631273700043'
        """
    ).fetchone()
    conn.close()

    assert row[0] == "01 39 14 57 56"
    assert row[1] == "06 11 22 33 44"
    assert row[2] == "https://www.cto-chauffage.fr/"
    assert row[3] == "cto@wanadoo.fr"
    assert row[4] == "Enrichi"
