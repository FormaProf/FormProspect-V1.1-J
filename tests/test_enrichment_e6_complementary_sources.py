import asyncio
import sqlite3

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


def _validated(source, *, phones=None, site="", email="", score=180):
    return {
        "source": source,
        "source_detail": "",
        "nom": "DECAM",
        "adresse": "",
        "code_postal": "75012",
        "ville": "PARIS",
        "telephones": list(phones or []),
        "faxes": [],
        "site_web": site,
        "email": email,
        "texte": "",
        "match_score": score,
        "match_reasons": ["SIREN exact"],
        "confidence": "validated",
        "technical_errors": [],
    }


def _create_db(path, *, sibling=False):
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
    if sibling:
        conn.execute(
            """
            INSERT INTO prospects (
                id, entreprise, siret, siren, adresse, code_postal, ville,
                code_naf, noms_recherche, telephone, statut_enrichissement
            )
            VALUES (2, 'DECAM', '30109677200019', '301096772',
                    '9 RUE MARJOLIN', '92300', 'LEVALLOIS-PERRET',
                    '43.22B', '["DECAM"]', '01 47 37 56 00', 'Enrichi')
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
    def __init__(self, result=None):
        self.result = result or _rejected("google_maps")

    async def rechercher(self, identity):
        return dict(self.result)

    async def fermer(self):
        return None


class RecordingWeb:
    def __init__(self, result=None, exc=None):
        self.result = result or _rejected("web_fallback")
        self.exc = exc
        self.calls = []

    def rechercher(self, identity):
        self.calls.append(dict(identity))
        if self.exc:
            raise self.exc
        return dict(self.result)




class Fake118000:
    def rechercher(self, identity):
        # Ce fichier teste uniquement la complémentarité du WebFallback.
        # La source 118000 possède ses propres tests dédiés et doit donc être
        # neutralisée ici pour que ses résultats ne modifient pas les attentes.
        return _rejected("118000")


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


def _configure(service, *, pages, web, google=None):
    service.entreprise_api = FakeApi()
    service.pages_jaunes = FakePages(pages)
    service.google = FakeGoogle(google)
    service.web_fallback = web
    service.annuaire_118000 = Fake118000()
    service.email_finder = FakeEmail()
    service.social_finder = FakeSocial()


def test_web_fallback_completes_pagesjaunes_instead_of_being_skipped(tmp_path, monkeypatch):
    db = tmp_path / "complement.db"
    _create_db(db)

    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        score=200,
    )
    web = RecordingWeb(
        _validated(
            "web_fallback",
            phones=["01 47 37 48 32"],
            email="decam.lacornue@wanadoo.fr",
            score=180,
        )
    )

    service = EnrichmentService()
    _configure(service, pages=pages, web=web)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(web.calls) == 1

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT telephone, email, statut_enrichissement FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert set(row[0].split(" / ")) == {
        "01 47 37 56 00",
        "01 47 37 48 32",
    }
    assert row[1:] == (
        "decam.lacornue@wanadoo.fr",
        service.ENRICHED_STATUS,
    )
    assert result["enrichis"] == 1
    assert result["source_pages_jaunes"] == 1
    assert result["source_web"] == 1


def test_web_fallback_runs_even_when_same_siren_already_has_a_phone(tmp_path, monkeypatch):
    db = tmp_path / "siren_complement.db"
    _create_db(db, sibling=True)

    web = RecordingWeb(
        _validated(
            "web_fallback",
            email="decam.lacornue@wanadoo.fr",
            score=180,
        )
    )

    service = EnrichmentService()
    _configure(service, pages=_rejected("pages_jaunes"), web=web)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(web.calls) == 1

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT telephone, email, statut_enrichissement FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert row == (
        "01 47 37 56 00",
        "decam.lacornue@wanadoo.fr",
        service.ENRICHED_STATUS,
    )
    assert result["enrichis"] == 1
    assert result["source_siren"] == 1
    assert result["source_web"] == 1


def test_web_fallback_failure_does_not_discard_valid_primary_source(tmp_path, monkeypatch):
    db = tmp_path / "web_failure.db"
    _create_db(db)

    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        score=200,
    )
    web = RecordingWeb(exc=RuntimeError("temporary web search failure"))

    service = EnrichmentService()
    _configure(service, pages=pages, web=web)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(db, mode="selected", prospect_ids=[1])
    )

    assert len(web.calls) == 1

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT telephone, statut_enrichissement FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert row == ("01 47 37 56 00", service.ENRICHED_STATUS)
    assert result["enrichis"] == 1
    assert result["erreurs"] == 0
    assert result["source_pages_jaunes"] == 1
    assert result["source_web"] == 0
