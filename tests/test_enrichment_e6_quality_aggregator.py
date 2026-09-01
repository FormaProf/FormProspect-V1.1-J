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
        "adresse": "9 RUE MARJOLIN",
        "code_postal": "92300",
        "ville": "LEVALLOIS-PERRET",
        "telephones": list(phones or []),
        "faxes": [],
        "site_web": site,
        "email": email,
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
        ) VALUES (
            1, 'DECAM', '30109677200027', '301096772',
            '56 RUE DU FAUBOURG SAINT-ANTOINE', '75012', 'PARIS',
            '43.22B', '["DECAM"]', ''
        )
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


class RecordingGoogle:
    def __init__(self, result=None, exc=None):
        self.result = result or _rejected("google_maps")
        self.exc = exc
        self.calls = []

    async def rechercher(self, identity):
        self.calls.append(dict(identity))
        if self.exc:
            raise self.exc
        return dict(self.result)

    async def fermer(self):
        return None


class Fake118000:
    def rechercher(self, identity):
        return _rejected("118000")


class FakeWeb:
    def __init__(self, result=None):
        self.result = result or _rejected("web_fallback")

    def rechercher(self, identity):
        return dict(self.result)


class RecordingEmail:
    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.calls = []

    @staticmethod
    def _is_technical(email):
        email = str(email or "").lower()
        return email.startswith("noreply@") or email.startswith("no-reply@")

    def chercher(self, site_web):
        self.calls.append(site_web)
        return self.answers.get(site_web, "")


class RecordingSocial:
    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.calls = []

    def chercher(self, site_web):
        self.calls.append(site_web)
        result = {
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "twitter": "",
            "youtube": "",
            "other_urls": [],
        }
        result.update(self.answers.get(site_web, {}))
        return result


def _configure(service, *, pages, google, web=None, email=None, social=None):
    service.entreprise_api = FakeApi()
    service.pages_jaunes = FakePages(pages)
    service.google = google
    service.annuaire_118000 = Fake118000()
    service.web_fallback = web or FakeWeb()
    service.email_finder = email or RecordingEmail()
    service.social_finder = social or RecordingSocial()


def test_google_maps_is_complementary_even_when_pagesjaunes_is_already_complete(tmp_path, monkeypatch):
    db = tmp_path / "google_complement.db"
    _create_db(db)

    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        site="https://decam.example/",
        score=200,
    )
    google = RecordingGoogle(
        _validated(
            "google_maps",
            phones=["01 47 37 48 32"],
            site="https://decam.example/",
            score=190,
        )
    )

    service = EnrichmentService()
    _configure(service, pages=pages, google=google)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    asyncio.run(service._enrichir_async(db, mode="selected", prospect_ids=[1]))

    assert len(google.calls) == 1
    conn = sqlite3.connect(db)
    telephone = conn.execute(
        "SELECT telephone FROM prospects WHERE id = 1"
    ).fetchone()[0]
    conn.close()
    assert set(telephone.split(" / ")) == {
        "01 47 37 56 00",
        "01 47 37 48 32",
    }


def test_all_validated_sites_are_scanned_for_email_and_social_profiles(tmp_path, monkeypatch):
    db = tmp_path / "multi_site.db"
    _create_db(db)

    site_primary = "https://decam-primary.example/"
    site_secondary = "https://decam-secondary.example/"
    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        site=site_primary,
        score=200,
    )
    google = RecordingGoogle(
        _validated(
            "google_maps",
            site=site_secondary,
            score=190,
        )
    )
    email = RecordingEmail({site_secondary: "contact@decam-secondary.example"})
    social = RecordingSocial(
        {
            site_secondary: {
                "linkedin": "https://www.linkedin.com/company/decam-example"
            }
        }
    )

    service = EnrichmentService()
    _configure(
        service,
        pages=pages,
        google=google,
        email=email,
        social=social,
    )
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    asyncio.run(service._enrichir_async(db, mode="selected", prospect_ids=[1]))

    assert email.calls == [site_primary, site_secondary]
    assert social.calls == [site_primary, site_secondary]

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT site_web, email, linkedin FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert row == (
        site_primary,
        "contact@decam-secondary.example",
        "https://www.linkedin.com/company/decam-example",
    )


def test_technical_source_email_is_never_saved(tmp_path, monkeypatch):
    db = tmp_path / "technical_email.db"
    _create_db(db)

    pages = _validated(
        "pages_jaunes",
        phones=["01 47 37 56 00"],
        email="noreply@tracking.example",
        score=200,
    )
    google = RecordingGoogle(_rejected("google_maps"))

    service = EnrichmentService()
    _configure(service, pages=pages, google=google)
    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    asyncio.run(service._enrichir_async(db, mode="selected", prospect_ids=[1]))

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT telephone, email, statut_enrichissement FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()

    assert row == (
        "01 47 37 56 00",
        "",
        service.ENRICHED_STATUS,
    )
