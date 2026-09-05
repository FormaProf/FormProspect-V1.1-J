from __future__ import annotations

from core.database import init_database
from repositories.prospect_repository import ProspectRepository
from services.cloud_api_client import CloudAPIClient
from services.prospect_data_provider import (
    CloudProspectDataProvider,
)
from services.prospect_service import ProspectService


def test_cloud_api_create_prospect_uses_post_endpoint():
    client = object.__new__(CloudAPIClient)

    captured = {}

    def fake_post(path, payload, *, expected=(200, 201)):
        captured["path"] = path
        captured["payload"] = payload
        captured["expected"] = expected
        return {
            "id": "prospect-1",
            **payload,
        }

    client.post_json = fake_post

    result = client.create_prospect(
        {
            "company_name": "Entreprise Cloud",
            "siret": "12345678900012",
        }
    )

    assert captured == {
        "path": "/prospects",
        "payload": {
            "company_name": "Entreprise Cloud",
            "siret": "12345678900012",
        },
        "expected": (201,),
    }
    assert result["id"] == "prospect-1"


def test_cloud_provider_injects_active_project_id():
    class FakeAPI:
        def __init__(self):
            self.payload = None

        def create_prospect(self, payload):
            self.payload = dict(payload)
            return {
                "id": "prospect-1",
                **payload,
            }

    api = FakeAPI()

    provider = CloudProspectDataProvider(
        api_client=api,
        project_id="project-123",
    )

    result = provider.create_prospect(
        {
            "company_name": "Entreprise projet",
            "siret": "12345678900013",
        }
    )

    assert api.payload["project_id"] == "project-123"
    assert result["project_id"] == "project-123"


def test_local_repository_creates_and_rejects_duplicate_siret(
    tmp_path,
):
    database_path = tmp_path / "prospects.db"

    init_database(database_path)

    repository = ProspectRepository(
        database_path
    )

    first_id = repository.create_prospect(
        {
            "company_name": "Entreprise locale",
            "siret": "12345678900014",
            "city": "Lille",
            "email": "contact@example.test",
        }
    )

    assert int(first_id) > 0

    row = repository.get_by_id(first_id)

    assert row is not None

    try:
        repository.create_prospect(
            {
                "company_name": "Doublon local",
                "siret": "12345678900014",
            }
        )
    except ValueError as exc:
        assert "SIRET" in str(exc)
    else:
        raise AssertionError(
            "Le doublon SIRET local aurait du etre refuse."
        )


def test_prospect_service_normalizes_siret_before_provider():
    class FakeProvider:
        def __init__(self):
            self.payload = None
            self._filter_options_cache = {
                "dummy": ["value"]
            }

        def create_prospect(self, payload):
            self.payload = dict(payload)
            return {"id": "created"}

    provider = FakeProvider()

    service = ProspectService()
    service._provider = (
        lambda database_path=None: provider
    )

    result = service.creer_prospect(
        data={
            "company_name": "  Entreprise Test  ",
            "siret": "123 456 789 000 15",
        }
    )

    assert result == {"id": "created"}
    assert (
        provider.payload["company_name"]
        == "Entreprise Test"
    )
    assert (
        provider.payload["siret"]
        == "12345678900015"
    )
    assert (
        provider.payload["siren"]
        == "123456789"
    )
    assert provider._filter_options_cache is None


def test_prospect_service_rejects_invalid_siret_before_provider():
    service = ProspectService()

    try:
        service.creer_prospect(
            data={
                "company_name": "Entreprise invalide",
                "siret": "123",
            }
        )
    except ValueError as exc:
        assert "14 chiffres" in str(exc)
    else:
        raise AssertionError(
            "Un SIRET invalide aurait du etre refuse."
        )
