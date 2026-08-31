import asyncio
import sqlite3

import pytest
from PySide6.QtWidgets import QApplication, QAbstractItemView

from services.enrichment_service import EnrichmentService
from ui.widgets.crm.prospects_table import ProspectsTableWidget


def rejected(source):
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
    conn.executemany(
        """
        INSERT INTO prospects (
            id, entreprise, siret, siren, telephone, mobile, site_web, email,
            facebook, statut_enrichissement
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A traiter", "11111111100011", "111111111", "", "", "", "", "", ""),
            (
                2,
                "Déjà enrichi",
                "22222222200022",
                "222222222",
                "01 00 00 00 02",
                "",
                "https://old.example",
                "old@example.test",
                "https://facebook.example/old",
                EnrichmentService.ENRICHED_STATUS,
            ),
            (
                3,
                "Sans résultat",
                "33333333300033",
                "333333333",
                "",
                "",
                "",
                "",
                "",
                EnrichmentService.NO_RELIABLE_RESULT_STATUS,
            ),
            (
                4,
                "Erreur",
                "44444444400044",
                "444444444",
                "",
                "",
                "",
                "",
                "",
                EnrichmentService.ERROR_STATUS,
            ),
            (5, "", "55555555500055", "555555555", "", "", "", "", "", ""),
        ],
    )
    conn.commit()
    return conn


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
            "resolved": False,
            "siren": "",
            "siret_siege": "",
            "names": [],
            "locations": [],
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
        self.result = result or rejected("google_maps")

    async def rechercher(self, identity):
        return dict(self.result)

    async def fermer(self):
        return None


class FakeWeb:
    def __init__(self, result=None):
        self.result = result or rejected("web_fallback")

    def rechercher(self, identity):
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


def _validated_phone(phone):
    return {
        "source": "pages_jaunes",
        "source_detail": "",
        "nom": "Déjà enrichi",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": [phone],
        "faxes": [],
        "site_web": "",
        "email": "",
        "texte": "",
        "match_score": 200,
        "match_reasons": ["SIRET exact"],
        "confidence": "validated",
        "technical_errors": [],
    }


def _configure_service(service, pages_result):
    service.entreprise_api = FakeApi()
    service.pages_jaunes = FakePages(pages_result)
    service.google = FakeGoogle()
    service.web_fallback = FakeWeb()
    service.email_finder = FakeEmail()
    service.social_finder = FakeSocial()


def test_enrichment_targets_pending_selected_and_all(tmp_path):
    db = tmp_path / "targets.db"
    conn = _create_db(db)
    service = EnrichmentService()

    pending = service._charger_prospects(
        conn,
        mode="pending",
    )
    selected = service._charger_prospects(
        conn,
        mode="selected",
        prospect_ids=[2, 3],
    )
    all_rows = service._charger_prospects(
        conn,
        mode="all",
    )
    conn.close()

    assert [row[0] for row in pending] == [1, 4]
    assert [row[0] for row in selected] == [2, 3]
    assert [row[0] for row in all_rows] == [1, 2, 3, 4]


def test_enrichment_target_counts_follow_mode(tmp_path):
    db = tmp_path / "counts.db"
    conn = _create_db(db)
    conn.close()

    service = EnrichmentService()

    assert service.compter_cible(db, mode="pending") == 2
    assert service.compter_cible(
        db,
        mode="selected",
        prospect_ids=[2, 3],
    ) == 2
    assert service.compter_cible(db, mode="all") == 4


def test_invalid_enrichment_mode_is_rejected(tmp_path):
    db = tmp_path / "invalid.db"
    conn = _create_db(db)
    service = EnrichmentService()

    with pytest.raises(ValueError):
        service._charger_prospects(conn, mode="unknown")

    conn.close()


def test_selected_reenrichment_replaces_old_enrichment_contacts(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "replace.db"
    conn = _create_db(db)
    conn.close()

    service = EnrichmentService()
    _configure_service(service, _validated_phone("01 47 37 48 32"))

    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(
            db,
            mode="selected",
            prospect_ids=[2],
        )
    )

    conn = sqlite3.connect(db)
    row = conn.execute(
        """
        SELECT telephone, mobile, site_web, email, facebook, statut_enrichissement
        FROM prospects
        WHERE id = 2
        """
    ).fetchone()
    conn.close()

    assert row == (
        "01 47 37 48 32",
        "",
        "",
        "",
        "",
        service.ENRICHED_STATUS,
    )
    assert result["traites"] == 1
    assert result["enrichis"] == 1


def test_selected_reenrichment_clears_stale_contacts_when_no_reliable_result(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "no_result.db"
    conn = _create_db(db)
    conn.close()

    service = EnrichmentService()
    _configure_service(service, rejected("pages_jaunes"))

    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    result = asyncio.run(
        service._enrichir_async(
            db,
            mode="selected",
            prospect_ids=[2],
        )
    )

    conn = sqlite3.connect(db)
    row = conn.execute(
        """
        SELECT telephone, mobile, site_web, email, facebook, statut_enrichissement
        FROM prospects
        WHERE id = 2
        """
    ).fetchone()
    conn.close()

    assert row == (
        "",
        "",
        "",
        "",
        "",
        service.NO_RELIABLE_RESULT_STATUS,
    )
    assert result["traites"] == 1
    assert result["sans_resultat"] == 1


def test_pending_enrichment_keeps_existing_fields_when_new_source_is_empty(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "pending_preserve.db"
    conn = _create_db(db)
    conn.execute(
        """
        UPDATE prospects
        SET statut_enrichissement = ?
        WHERE id IN (1, 4)
        """,
        (EnrichmentService.ENRICHED_STATUS,),
    )
    conn.execute(
        """
        UPDATE prospects
        SET statut_enrichissement = '',
            telephone = '01 00 00 00 99',
            site_web = 'https://manual.example',
            email = 'manual@example.test'
        WHERE id = 2
        """
    )
    conn.commit()
    conn.close()

    service = EnrichmentService()
    _configure_service(service, _validated_phone("01 47 37 48 32"))

    monkeypatch.setattr(
        "services.enrichment_service.ScoringService.score_prospect_with_connection",
        lambda *args, **kwargs: None,
    )

    asyncio.run(
        service._enrichir_async(
            db,
            mode="pending",
        )
    )

    conn = sqlite3.connect(db)
    row = conn.execute(
        """
        SELECT telephone, site_web, email
        FROM prospects
        WHERE id = 2
        """
    ).fetchone()
    conn.close()

    assert row == (
        "01 47 37 48 32",
        "https://manual.example",
        "manual@example.test",
    )


def test_prospects_table_allows_multiple_row_selection():
    app = QApplication.instance() or QApplication([])
    table = ProspectsTableWidget()

    assert table.selectionBehavior() == QAbstractItemView.SelectRows
    assert table.selectionMode() == QAbstractItemView.ExtendedSelection
    assert hasattr(table, "selected_prospect_ids")
