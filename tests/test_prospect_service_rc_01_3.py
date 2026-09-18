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


    def test_cloud_session_without_project_uses_organization_provider(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )
        provider = FakeProvider()

        with patch(
            "services.prospect_service.ApplicationState.has_project",
            return_value=False,
        ), patch(
            "services.prospect_service.CloudRuntime.is_active",
            return_value=True,
        ), patch(
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
            project_id=None,
        )
        local_provider.assert_not_called()


    def test_cloud_crm_project_scope_switches_provider_cache(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )
        provider_one = FakeProvider()
        provider_two = FakeProvider()
        provider_all = FakeProvider()

        with patch(
            "services.prospect_service.ApplicationState.has_project",
            return_value=False,
        ), patch(
            "services.prospect_service.CloudRuntime.is_active",
            return_value=True,
        ), patch(
            "services.prospect_service.CloudProspectDataProvider",
            side_effect=[
                provider_one,
                provider_two,
                provider_all,
            ],
        ) as cloud_provider:
            service.recuperer_prospects(
                limite=50,
                project_id="project-1",
            )
            service.recuperer_prospects(
                limite=50,
                project_id="project-2",
            )
            service.recuperer_prospects(
                limite=50,
                project_id=None,
            )

        self.assertEqual(
            [call.kwargs["project_id"] for call in cloud_provider.call_args_list],
            ["project-1", "project-2", None],
        )

    def test_cloud_crm_all_projects_overrides_active_cloud_project(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )
        provider = FakeProvider()

        with patch(
            "services.prospect_service.CloudProspectDataProvider",
            return_value=provider,
        ) as cloud_provider:
            service.recuperer_prospects(
                limite=50,
                project_id=None,
            )

        cloud_provider.assert_called_once_with(
            "api",
            project_id=None,
        )


    def test_cloud_crm_project_scope_is_used_by_list_counts_and_options(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )

        class ScopedFakeCloudProvider(FakeProvider):
            calls = []

            def __init__(self, api_client=None, *, project_id=None):
                super().__init__()
                self.__class__.calls.append((api_client, project_id))

        with patch(
            "services.prospect_service.ApplicationState.has_project",
            return_value=False,
        ), patch(
            "services.prospect_service.CloudRuntime.is_active",
            return_value=True,
        ), patch(
            "services.prospect_service.CloudProspectDataProvider",
            new=ScopedFakeCloudProvider,
        ):
            self.assertEqual(
                service.compter_prospects(
                    project_id="project-1"
                ),
                7,
            )
            self.assertEqual(
                service.compter_prospects_filtres(
                    recherche="ACME",
                    project_id="project-1",
                ),
                2,
            )
            self.assertEqual(
                service.rechercher_prospects_filtres(
                    recherche="ACME",
                    limite=25,
                    project_id="project-1",
                ),
                [("filtre",)],
            )
            self.assertEqual(
                service.recuperer_options_filtres(
                    project_id="project-1"
                ),
                {"pipeline": ["Nouveau"]},
            )

        self.assertEqual(
            ScopedFakeCloudProvider.calls,
            [("api", "project-1")],
        )


    def test_cloud_crm_project_scope_is_used_by_cache_invalidation(self):
        service = ProspectService(
            resolver=FakeResolver(cloud=True),
            cloud_api_client="api",
        )

        class ScopedFakeCloudProvider(FakeProvider):
            calls = []

            def __init__(self, api_client=None, *, project_id=None):
                super().__init__()
                self._stats_cache = {"cached": True}
                self._filter_options_cache = {"cached": True}
                self.__class__.calls.append((api_client, project_id))

        with patch(
            "services.prospect_service.ApplicationState.has_project",
            return_value=False,
        ), patch(
            "services.prospect_service.CloudRuntime.is_active",
            return_value=True,
        ), patch(
            "services.prospect_service.CloudProspectDataProvider",
            new=ScopedFakeCloudProvider,
        ):
            service.invalider_caches(
                statistiques=True,
                filtres=True,
                project_id="project-1",
            )

        self.assertEqual(
            ScopedFakeCloudProvider.calls,
            [("api", "project-1")],
        )
        self.assertIsNone(service._provider_cache._stats_cache)
        self.assertIsNone(
            service._provider_cache._filter_options_cache
        )

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
