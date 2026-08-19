from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.project import Project
from services.cloud_api_client import CloudAPIClient
from services.project_deployment_service import (
    ProjectDeploymentError,
    ProjectDeploymentService,
)
from services.project_import_service import ProjectImportResult


class FakeProjectManager:
    CLOUD_STATUS_DEPLOYED = "deployed"

    def __init__(self, *, deployed=False):
        self.deployed = deployed
        self.updated = []
        self.cloud = {
            "project_id": "cloud-existing" if deployed else None,
            "organization_id": "org-1" if deployed else None,
            "deployment_status": "deployed" if deployed else "local",
            "deployed_at": "2026-07-01T10:00:00" if deployed else None,
            "last_sync_at": None,
        }

    def is_deployed(self, project):
        return self.deployed

    def get_cloud_configuration(self, project):
        return dict(self.cloud)

    def update_cloud_configuration(self, project, **changes):
        self.cloud.update({k: v for k, v in changes.items() if v is not None})
        self.updated.append(dict(changes))
        return dict(self.cloud)


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "Projet test"
    folder.mkdir()
    (folder / "project.json").write_text("{}", encoding="utf-8")
    return Project(folder)


def import_result(total=7, imported=7, failed=0):
    return ProjectImportResult(
        total_batches=1 if total else 0,
        processed_batches=1 if total else 0,
        last_successful_batch=1 if total else 0,
        total_prospects=total,
        imported_prospects=imported,
        failed_prospects=failed,
    )


def test_deploy_imports_before_marking_project_deployed(project):
    manager = FakeProjectManager(deployed=False)
    service = ProjectDeploymentService(manager)
    api = Mock()
    api.create_project.return_value = {
        "id": "cloud-123",
        "organization_id": "org-1",
    }

    with patch("services.project_deployment_service.CloudRuntime.api", return_value=api), \
         patch.object(service, "_import_local_prospects", return_value=import_result()):
        result = service.deploy(project)

    assert result.import_result.imported_prospects == 7
    assert manager.cloud["deployment_status"] == "deployed"
    assert manager.cloud["project_id"] == "cloud-123"
    assert len(manager.updated) == 1


def test_failed_import_does_not_switch_local_project_to_cloud(project):
    manager = FakeProjectManager(deployed=False)
    service = ProjectDeploymentService(manager)
    api = Mock()
    api.create_project.return_value = {
        "id": "cloud-123",
        "organization_id": "org-1",
    }

    with patch("services.project_deployment_service.CloudRuntime.api", return_value=api), \
         patch.object(service, "_import_local_prospects", return_value=import_result(7, 6, 1)):
        with pytest.raises(ProjectDeploymentError):
            service.deploy(project)

    assert manager.updated == []
    assert manager.cloud["deployment_status"] == "local"


def test_synchronize_reuses_existing_cloud_project(project):
    manager = FakeProjectManager(deployed=True)
    service = ProjectDeploymentService(manager)
    api = Mock()
    api.get_project.return_value = {
        "id": "cloud-existing",
        "organization_id": "org-1",
    }

    with patch("services.project_deployment_service.CloudRuntime.api", return_value=api), \
         patch.object(service, "_import_local_prospects", return_value=import_result()):
        result = service.synchronize(project)

    api.create_project.assert_not_called()
    api.get_project.assert_called_once_with("cloud-existing")
    assert result.project_id == "cloud-existing"
    assert result.import_result.imported_prospects == 7
    assert manager.cloud["last_sync_at"]


def test_import_response_uses_current_backend_contract():
    client = object.__new__(CloudAPIClient)
    client.post_json = Mock(return_value={
        "created": 5,
        "updated": 2,
        "ignored": 1,
        "errors": 0,
        "processed": 8,
        "warnings": ["doublon ignoré"],
        "succeeded": True,
    })

    response = client.import_project_prospects("project-1", [{"company_name": "A"}])

    assert response.total_prospects == 8
    assert response.imported_prospects == 7
    assert response.failed_prospects == 0
    assert response.created == 5
    assert response.updated == 2
    assert response.ignored == 1
    assert response.warnings == ("doublon ignoré",)
