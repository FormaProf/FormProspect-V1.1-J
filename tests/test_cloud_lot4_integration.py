from __future__ import annotations

from dataclasses import dataclass

import pytest
from PySide6.QtWidgets import QApplication

from core.crm import PIPELINE
from ui.widgets.crm.prospects_table import ProspectsTableWidget
from ui.widgets.crm.filters_bar import CRMFiltersBar
from services.cloud_api_client import CloudAPIClient, CloudAPIError, PageResult
from services.cloud_crm_mapping import pipeline_to_api, pipeline_to_ui, priority_to_api, priority_to_ui
from services.cloud_runtime import CloudRuntime
from services.prospect_service import ProspectService


@dataclass
class _Session:
    access_token: str = "token"
    organization_id: str = "org-1"


class _Auth:
    session = _Session()
    current_user = object()


class _Response:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _HTTP:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def test_cloud_api_client_sends_token_and_organization_header():
    client = CloudAPIClient(_Auth(), "https://example.test/api/v1")
    client.http = _HTTP(_Response(payload=[]))
    client.get_json("/prospects")
    _, url, kwargs = client.http.calls[0]
    assert url == "https://example.test/api/v1/prospects"
    assert kwargs["headers"]["Authorization"] == "Bearer token"
    assert kwargs["headers"]["X-Organization-ID"] == "org-1"


def test_cloud_api_client_reads_pagination_headers():
    client = CloudAPIClient(_Auth(), "https://example.test/api/v1")
    client.http = _HTTP(_Response(payload=[{"id": "p1"}], headers={"X-Total-Count": "9", "X-Limit": "1", "X-Offset": "2"}))
    page = client.list_prospects(limit=1, offset=2)
    assert page.total == 9
    assert page.limit == 1
    assert page.offset == 2


def test_cloud_api_client_exposes_backend_error_message():
    client = CloudAPIClient(_Auth(), "https://example.test/api/v1")
    client.http = _HTTP(_Response(status_code=403, payload={"detail": "Modification interdite."}))
    with pytest.raises(CloudAPIError, match="Modification interdite"):
        client.get_json("/prospects/p1")


def test_desktop_pipeline_and_priority_mapping():
    assert pipeline_to_api("🟣 Proposition envoyée") == "proposition_envoyee"
    assert pipeline_to_ui("gagne") == "🟢 Client"
    assert pipeline_to_api("🔥 Lead chaud") == "lead_chaud"
    assert pipeline_to_ui("lead_chaud") == "🔥 Lead chaud"
    assert pipeline_to_ui("a_contacter") == "🟡 À contacter"
    assert pipeline_to_ui("contacte") == "🔵 Contacté"
    assert pipeline_to_ui("rdv_planifie") == "📅 RDV planifié"
    assert priority_to_api("⭐⭐⭐⭐⭐") == "urgente"
    assert priority_to_ui("haute") == "⭐⭐⭐⭐"


def test_cloud_prospect_service_adapts_api_payload_to_existing_table(monkeypatch):
    class API:
        def list_prospects(self, **kwargs):
            return PageResult(items=[{
                "id": "p1", "company_name": "Dupont", "city": "Lille", "postal_code": "59000",
                "phone": "0102030405", "website": "https://example.test", "email": "a@example.test",
                "pipeline_stage": "rdv_planifie", "priority": "haute", "next_action": "Rappeler",
                "next_action_at": "2026-07-24T09:00:00", "owner_user_id": "u1",
            }], total=1, limit=100, offset=0)

    monkeypatch.setattr(CloudRuntime, "is_active", classmethod(lambda cls: True))
    monkeypatch.setattr(CloudRuntime, "api", classmethod(lambda cls: API()))
    rows = ProspectService().rechercher_prospects_filtres(None)
    assert rows[0][0] == "p1"
    assert rows[0][7] == "📅 RDV planifié"
    assert rows[0][8] == "⭐⭐⭐⭐"


def test_desktop_pipeline_exposes_full_business_stages():
    expected = [
        "🟢 Nouveau",
        "🟡 À contacter",
        "🔥 Lead chaud",
        "🔵 Contacté",
        "📅 RDV planifié",
        "🟣 Proposition envoyée",
        "🟠 Négociation",
        "🟢 Client",
        "🔴 Perdu",
    ]
    assert PIPELINE == expected
    assert list(ProspectsTableWidget.PIPELINE_ORDER) == expected


def test_crm_table_displays_prospect_source():
    app = QApplication.instance() or QApplication([])
    table = ProspectsTableWidget()
    row = (
        "prospect-1", "Entreprise BTP", "Lille", "59000",
        "0102030405", "https://example.test", "contact@example.test",
        "🔥 Lead chaud", "", "Aucune", "", "Florian",
        75, "★★★★☆", "Bon potentiel", "0612345678",
        "BTP Florian NUMA IDF-1",
    )
    table.afficher_lignes([row])
    assert table.columnCount() == 16
    assert table.horizontalHeaderItem(15).text() == "Source"
    assert table.item(0, 15).text() == "BTP Florian NUMA IDF-1"


def test_crm_filters_bar_exposes_project_selector_without_mixing_business_filters():
    app = QApplication.instance() or QApplication([])
    filters = CRMFiltersBar()

    filters.charger_options({
        "pipelines": [],
        "priorites": [],
        "commerciaux": [],
        "villes": [],
        "projects": [
            {"id": "project-1", "name": "Projet Alpha"},
            {"id": "project-2", "name": "Projet Beta"},
        ],
    })

    assert filters.project_filtre.count() == 3
    assert filters.project_filtre.itemText(0) == "Projet : Tous"
    assert filters.project_filtre.itemData(0) == ""
    assert filters.project_filtre.itemText(1) == "Projet Alpha"
    assert filters.project_filtre.itemData(1) == "project-1"

    filters.project_filtre.setCurrentIndex(2)
    assert filters.project_id_selectionne() == "project-2"
    assert "project_id" not in filters.criteres()


def test_crm_project_selector_emits_change_and_resets_to_all():
    app = QApplication.instance() or QApplication([])
    filters = CRMFiltersBar()
    filters.charger_options({
        "pipelines": [],
        "priorites": [],
        "commerciaux": [],
        "villes": [],
        "projects": [
            {"id": "project-1", "name": "Projet Alpha"},
            {"id": "project-2", "name": "Projet Beta"},
        ],
    })

    emissions = []
    filters.filters_changed.connect(lambda: emissions.append("changed"))

    filters.project_filtre.setCurrentIndex(1)
    assert emissions == ["changed"]
    assert filters.project_id_selectionne() == "project-1"

    filters.effacer_filtres()
    assert filters.project_id_selectionne() == ""
    assert filters.project_filtre.currentIndex() == 0


def test_crm_project_selector_can_be_initialized_silently():
    app = QApplication.instance() or QApplication([])
    filters = CRMFiltersBar()
    filters.charger_options({
        "pipelines": [],
        "priorites": [],
        "commerciaux": [],
        "villes": [],
        "projects": [
            {"id": "project-1", "name": "Projet Alpha"},
            {"id": "project-2", "name": "Projet Beta"},
        ],
    })

    emissions = []
    filters.filters_changed.connect(lambda: emissions.append("changed"))

    filters.selectionner_project_id("project-2")

    assert filters.project_id_selectionne() == "project-2"
    assert emissions == []
