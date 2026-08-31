from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import patch

from services.prospect_service import ProspectService


@dataclass(frozen=True)
class FakeProject:
    database: str = "project.db"


@dataclass(frozen=True)
class FakeContext:
    is_cloud: bool
    project: FakeProject = FakeProject()
    project_id: str | None = None


class FakeResolver:
    def __init__(self, cloud: bool):
        self.cloud = cloud

    def resolve(self):
        return FakeContext(
            is_cloud=self.cloud,
            project_id="cloud-project" if self.cloud else None,
        )

    def is_cloud(self):
        return self.cloud


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.last_total = 12

    def count_all(self):
        self.calls.append(("count_all",))
        return 7

    def count_with_phone(self):
        return 5

    def count_with_email(self):
        return 4

    def count_with_website(self):
        return 3

    def count_filtered(self, **kwargs):
        self.calls.append(("count_filtered", kwargs))
        return 2

    def get_all(self, limite=100):
        self.calls.append(("get_all", limite))
        return [("prospect",)]

    def search(self, recherche, limite=100):
        self.calls.append(("search", recherche, limite))
        return [("resultat",)]

    def search_filtered(self, **kwargs):
        self.calls.append(("search_filtered", kwargs))
        return [("filtre",)]

    def get_filter_options(self):
        return {"pipeline": ["Nouveau"]}

    def get_by_id(self, prospect_id):
        return (prospect_id,)

    def update_pipeline(self, prospect_id, pipeline):
        self.calls.append(("update_pipeline", prospect_id, pipeline))
        return True

    def update_contact_infos(self, *args):
        self.calls.append(("update_contact_infos", args))
        return True


class ProspectServiceTests(unittest.TestCase):
    def setUp(self):
        self._has_project_patcher = patch(
            "services.prospect_service.ApplicationState.has_project",
            return_value=True,
        )
        self._has_project_patcher.start()
        self.addCleanup(self._has_project_patcher.stop)

    def test_local_project_uses_local_provider(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=False)
        )
        provider = FakeProvider()

        with patch(
            "services.prospect_service.LocalProspectDataProvider",
            return_value=provider,
        ) as local_provider, patch(
            "services.prospect_service.CloudProspectDataProvider"
        ) as cloud_provider:
            self.assertEqual(service.compter_prospects("local.db"), 7)

        local_provider.assert_called_once_with("local.db")
        cloud_provider.assert_not_called()

    def test_cloud_project_uses_cloud_provider(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )
        provider = FakeProvider()

        with patch(
            "services.prospect_service.CloudProspectDataProvider",
            return_value=provider,
        ) as cloud_provider, patch(
            "services.prospect_service.LocalProspectDataProvider"
        ) as local_provider:
            result = service.recuperer_prospects(limite=50)

        self.assertEqual(result, [("prospect",)])
        self.assertEqual(service._last_total, 12)
        cloud_provider.assert_called_once_with(
            "api",
            project_id="cloud-project",
        )
        local_provider.assert_not_called()

    def test_pipeline_validation_is_preserved(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=False)
        )

        with self.assertRaises(ValueError):
            service.mettre_a_jour_pipeline(
                "local.db",
                1,
                "   ",
            )

    def test_service_delegates_filtered_search(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=False)
        )
        provider = FakeProvider()

        with patch(
            "services.prospect_service.LocalProspectDataProvider",
            return_value=provider,
        ):
            result = service.rechercher_prospects_filtres(
                "local.db",
                recherche="ACME",
                pipeline="À contacter",
                limite=25,
                offset=5,
            )

        self.assertEqual(result, [("filtre",)])
        self.assertEqual(
            provider.calls[-1],
            (
                "search_filtered",
                {
                    "recherche": "ACME",
                    "pipeline": "À contacter",
                    "priorite": "",
                    "commercial": "",
                    "ville": "",
                    "limite": 25,
                    "offset": 5,
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
