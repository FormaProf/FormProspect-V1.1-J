from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.application_state import ApplicationState
from core.datasource_resolver import (
    DataSourceMode,
    DataSourceResolutionError,
    DataSourceResolver,
)
from core.project import Project
from services.project_manager import ProjectManager


class DataSourceResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_project = ApplicationState.get_project()
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.project_manager = ProjectManager()
        self.resolver = DataSourceResolver(self.project_manager)

    def tearDown(self) -> None:
        ApplicationState.current_project = self.previous_project
        self.temp_directory.cleanup()

    def create_project(
        self,
        *,
        deployment_status: str = ProjectManager.CLOUD_STATUS_LOCAL,
        project_id: str | None = None,
        organization_id: str | None = None,
    ) -> Project:
        folder = self.root / "Projet test"
        folder.mkdir(parents=True, exist_ok=True)

        configuration = {
            "nom": "Projet test",
            "version": "1.0.0",
            "created_at": "2026-01-01T00:00:00",
            "cloud": {
                "project_id": project_id,
                "organization_id": organization_id,
                "deployment_status": deployment_status,
                "deployed_at": None,
                "last_sync_at": None,
            },
        }

        (folder / "project.json").write_text(
            json.dumps(configuration),
            encoding="utf-8",
        )

        return Project(folder)

    def test_no_active_project_raises_explicit_error(self) -> None:
        ApplicationState.current_project = None

        with self.assertRaises(DataSourceResolutionError):
            self.resolver.resolve()

    def test_local_project_resolves_to_local_mode(self) -> None:
        project = self.create_project()
        ApplicationState.set_project(project)

        context = self.resolver.resolve()

        self.assertEqual(context.mode, DataSourceMode.LOCAL)
        self.assertTrue(context.is_local)
        self.assertFalse(context.is_cloud)

    def test_deployed_project_with_id_resolves_to_cloud_mode(self) -> None:
        project = self.create_project(
            deployment_status=ProjectManager.CLOUD_STATUS_DEPLOYED,
            project_id="cloud-project-123",
            organization_id="organization-456",
        )
        ApplicationState.set_project(project)

        context = self.resolver.resolve()

        self.assertEqual(context.mode, DataSourceMode.CLOUD)
        self.assertTrue(context.is_cloud)
        self.assertEqual(context.project_id, "cloud-project-123")
        self.assertEqual(context.organization_id, "organization-456")

    def test_deployed_project_without_cloud_id_is_rejected(self) -> None:
        project = self.create_project(
            deployment_status=ProjectManager.CLOUD_STATUS_DEPLOYED,
        )
        ApplicationState.set_project(project)

        with self.assertRaises(DataSourceResolutionError):
            self.resolver.resolve()

    def test_unknown_deployment_status_is_rejected(self) -> None:
        project = self.create_project(
            deployment_status="unknown-status",
            project_id="cloud-project-123",
        )
        ApplicationState.set_project(project)

        with self.assertRaises(DataSourceResolutionError):
            self.resolver.resolve()


if __name__ == "__main__":
    unittest.main()
