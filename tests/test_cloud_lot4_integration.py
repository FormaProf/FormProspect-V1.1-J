from __future__ import annotations

from dataclasses import dataclass

import pytest

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
    assert rows[0][7] == "🔵 RDV programmé"
    assert rows[0][8] == "⭐⭐⭐⭐"
