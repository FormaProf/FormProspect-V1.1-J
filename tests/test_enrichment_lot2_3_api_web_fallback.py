import json
import sqlite3

from core.database import init_database
from modules.entreprise_api import EntrepriseApiClient
from modules.web_fallback import WebFallbackFinder
from services.enrichment_service import EnrichmentService


class _NoApi:
    def resolve(self, identity):
        return {
            "resolved": False,
            "siren": "",
            "siret_siege": "",
            "names": [],
            "locations": [],
            "error": "",
            "from_cache": False,
        }

    def stats(self):
        return {
            "api_requests": 0,
            "api_cache_hits": 0,
            "api_failures": 0,
            "api_cache_size": 0,
        }


class _ApiClimat22(_NoApi):
    def resolve(self, identity):
        return {
            "resolved": True,
            "siren": "068800226",
            "siret_siege": "06880022600034",
            "names": ["SOCIETE CLIMAT 22", "CLIMAT 22"],
            "locations": [
                {
                    "adresse": "41 IMPASSE DES ROSELIERES",
                    "code_postal": "13400",
                    "ville": "AUBAGNE",
                    "siret": "06880022600034",
                    "est_siege": True,
                }
            ],
            "error": "",
            "from_cache": False,
        }

    def stats(self):
        return {
            "api_requests": 1,
            "api_cache_hits": 0,
            "api_failures": 0,
            "api_cache_size": 1,
        }


class _EmptySource:
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
            "email": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": [],
        }


class _ClimatPages(_EmptySource):
    async def rechercher_nom(self, identity):
        # Le siège national doit avoir été injecté par l'API avant PagesJaunes.
        assert any(
            item.get("code_postal") == "13400" and item.get("ville") == "AUBAGNE"
            for item in identity.get("localisations_recherche", [])
        )
        assert "CLIMAT 22" in identity.get("noms_recherche", [])
        return {
            "source": "pages_jaunes",
            "nom": "Climat 22",
            "adresse": "41 impasse des Roselières 13400 Aubagne",
            "code_postal": "13400",
            "ville": "Aubagne",
            "telephones": ["04 91 79 05 91"],
            "faxes": [],
            "site_web": "https://www.climat22.com/",
            "email": "",
            "texte": "SIREN 068800226 Climat 22 41 impasse des Roselières 13400 Aubagne",
            "match_score": 200,
            "match_reasons": ["SIREN exact"],
            "confidence": "validated",
            "technical_errors": [],
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


class _WebDous:
    def rechercher(self, identity):
        assert identity["siret"] == "30006734500029"
        return {
            "source": "web_fallback",
            "source_detail": "cylex-locale.fr + allbiz.fr",
            "nom": "Dous Mebrouk",
            "adresse": "10 rue du Fer à Cheval 95200 Sarcelles",
            "code_postal": "95200",
            "ville": "Sarcelles",
            # Le fax est volontairement aussi présent dans telephones : le
            # service doit l'exclure grâce au champ faxes.
            "telephones": ["01 39 90 15 80", "01 39 90 93 17"],
            "faxes": ["01 39 90 93 17"],
            "site_web": "",
            "email": "",
            "texte": "Dous Mebrouk SIRET 30006734500029 95200 Sarcelles",
            "match_score": 200,
            "match_reasons": ["SIRET exact"],
            "confidence": "validated",
            "technical_errors": [],
        }


def _make_db(tmp_path, row):
    path = tmp_path / "project.db"
    init_database(path)
    conn = sqlite3.connect(path)
    EnrichmentService._ensure_social_columns(conn)
    conn.execute(
        """
        INSERT INTO prospects (
            entreprise, siret, siren, adresse, code_postal, ville, code_naf,
            telephone, mobile, site_web, email, noms_recherche,
            statut_enrichissement, date_collecte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', '', ?, 'Importé', '')
        """,
        (
            row["entreprise"], row["siret"], row["siren"], row["adresse"],
            row["code_postal"], row["ville"], row.get("code_naf", ""),
            json.dumps(row.get("noms_recherche", [])),
        ),
    )
    conn.commit()
    conn.close()
    return path


def test_api_parser_extracts_siege_aliases_and_locations(monkeypatch):
    client = EntrepriseApiClient()

    class _Response:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "siren": "068800226",
                        "nom_raison_sociale": "SOCIETE CLIMAT 22",
                        "nom_complet": "SOCIETE CLIMAT 22",
                        "sigle": None,
                        "siege": {
                            "siret": "06880022600034",
                            "adresse": "41 IMPASSE DES ROSELIERES 13400 AUBAGNE",
                            "code_postal": "13400",
                            "libelle_commune": "AUBAGNE",
                            "nom_commercial": "CLIMAT 22",
                            "liste_enseignes": ["CLIMAT 22"],
                            "est_siege": True,
                        },
                        "matching_etablissements": [
                            {
                                "siret": "06880022600026",
                                "adresse": "80 AVENUE DU GENERAL DE GAULLE 91170 VIRY-CHATILLON",
                                "code_postal": "91170",
                                "libelle_commune": "VIRY-CHATILLON",
                                "liste_enseignes": [],
                                "est_siege": False,
                            }
                        ],
                    }
                ]
            }

    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return _Response()

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client, "_throttle", lambda: None)

    identity = {"siren": "068800226", "siret": "06880022600026"}
    first = client.resolve(identity)
    second = client.resolve(identity)

    assert first["resolved"] is True
    assert first["siret_siege"] == "06880022600034"
    assert "CLIMAT 22" in first["names"]
    assert any(x["code_postal"] == "13400" for x in first["locations"])
    assert any(x["code_postal"] == "91170" for x in first["locations"])
    assert len(calls) == 1
    assert second["from_cache"] is True
    assert client.stats()["api_cache_hits"] == 1


def test_web_query_plan_keeps_siret_for_generic_web_search():
    identity = {
        "entreprise": "DOUS MEBROUK",
        "siret": "30006734500029",
        "siren": "300067345",
        "adresse": "10 RUE DU FER A CHEVAL",
        "code_postal": "95200",
        "ville": "SARCELLES",
        "noms_recherche": [],
        "localisations_recherche": [],
    }
    plan = WebFallbackFinder._query_plan(identity)
    assert any("DOUS MEBROUK" in query for query in plan)
    assert "30006734500029" in plan
    assert len(plan) <= WebFallbackFinder.MAX_QUERIES


def test_lot23_uses_api_siege_before_pagesjaunes(tmp_path):
    path = _make_db(
        tmp_path,
        {
            "entreprise": "SOCIETE CLIMAT 22",
            "siret": "06880022600026",
            "siren": "068800226",
            "adresse": "80 AVENUE DU GENERAL DE GAULLE",
            "code_postal": "91170",
            "ville": "VIRY-CHATILLON",
        },
    )
    service = EnrichmentService()
    service.entreprise_api = _ApiClimat22()
    service.pages_jaunes = _ClimatPages()
    service.google = _EmptySource()
    service.web_fallback = _WebDous()  # ne doit pas être appelé
    service.email_finder = _NoEmail()
    service.social_finder = _NoSocial()

    result = service.enrichir(path, limite=1)
    assert result["enrichis"] == 1
    assert result["source_pages_jaunes"] == 1
    assert result["source_web"] == 0
    assert result["api_siren_resolved"] == 1

    conn = sqlite3.connect(path)
    row = conn.execute(
        "SELECT telephone, site_web, statut_enrichissement FROM prospects"
    ).fetchone()
    conn.close()
    assert row[0] == "04 91 79 05 91"
    assert row[1] == "https://www.climat22.com/"
    assert row[2] == "Enrichi"


def test_lot23_web_fallback_enriches_and_excludes_fax(tmp_path):
    path = _make_db(
        tmp_path,
        {
            "entreprise": "DOUS MEBROUK",
            "siret": "30006734500029",
            "siren": "300067345",
            "adresse": "10 RUE DU FER A CHEVAL",
            "code_postal": "95200",
            "ville": "SARCELLES",
        },
    )
    service = EnrichmentService()
    service.entreprise_api = _NoApi()
    service.pages_jaunes = _EmptySource()
    service.google = _EmptySource()
    service.web_fallback = _WebDous()
    service.email_finder = _NoEmail()
    service.social_finder = _NoSocial()

    result = service.enrichir(path, limite=1)
    assert result["enrichis"] == 1
    assert result["source_web"] == 1
    assert result["source_pages_jaunes"] == 0
    assert result["source_google_maps"] == 0

    conn = sqlite3.connect(path)
    row = conn.execute(
        "SELECT telephone, mobile, statut_enrichissement FROM prospects"
    ).fetchone()
    conn.close()
    assert row[0] == "01 39 90 15 80"
    assert "01 39 90 93 17" not in (row[0] or "")
    assert row[2] == "Enrichi"
