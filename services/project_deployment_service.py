from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.project import Project
from repositories.prospect_repository import ProspectRepository
from services.cloud_api_client import CloudAPIError, CloudAPIClient
from services.cloud_runtime import CloudRuntime
from services.project_import_service import (
    ProjectImportResult,
    ProjectImportService,
)
from services.project_manager import (
    ProjectConfigurationError,
    ProjectManager,
)
from services.system import ActivityService


class ProjectDeploymentError(RuntimeError):
    """Erreur métier rencontrée pendant le déploiement d'un projet."""


class ProjectAlreadyDeployedError(ProjectDeploymentError):
    """Le projet local possède déjà une identité Cloud."""


class InvalidCloudProjectResponseError(ProjectDeploymentError):
    """La réponse reçue du Cloud ne permet pas d'identifier le projet."""


class ProjectImportAfterDeploymentError(ProjectDeploymentError):
    """
    Le projet a été créé dans le Cloud, mais l'import a échoué.

    L'identifiant Cloud est conservé afin d'éviter la création
    accidentelle d'un second projet lors d'une nouvelle tentative.
    """

    def __init__(
        self,
        message: str,
        *,
        project_id: str,
    ):
        super().__init__(message)
        self.project_id = project_id


@dataclass(frozen=True)
class ProjectDeploymentResult:
    """Informations du projet créé dans Form@Prospect Cloud."""

    project_id: str
    organization_id: str
    deployment_status: str
    deployed_at: str
    last_sync_at: str
    cloud_project: dict[str, Any]


@dataclass(frozen=True)
class ProjectDeploymentSummary:
    """
    Résultat global de la création et de l'import d'un projet.

    Attributes:
        project_id:
            Identifiant UUID du projet créé dans le Cloud.

        deployment_result:
            Informations relatives à la création du projet Cloud.

        import_result:
            Statistiques de l'import des prospects locaux.
    """

    project_id: str
    deployment_result: ProjectDeploymentResult
    import_result: ProjectImportResult


class ProjectDeploymentService:
    """
    Déploie un projet local vers Form@Prospect Cloud.

    Ce service orchestre :

    1. la validation du projet local ;
    2. la création du projet dans le Cloud ;
    3. l'enregistrement de son identité dans project.json ;
    4. l'import des prospects SQLite par lots ;
    5. la mise à jour de la date de dernière synchronisation ;
    6. l'enregistrement de l'activité locale.
    """

    def __init__(
        self,
        project_manager: ProjectManager | None = None,
    ):
        self.project_manager = project_manager or ProjectManager()

    def deploy(
        self,
        project: Project,
        *,
        description: str = "",
        assigned_to: str | None = None,
        batch_size: int = ProjectImportService.DEFAULT_BATCH_SIZE,
    ) -> ProjectDeploymentSummary:
        """
        Crée le projet Cloud puis importe ses prospects locaux.

        Args:
            project:
                Projet local à déployer.

            description:
                Description facultative envoyée au Cloud.

            assigned_to:
                Identifiant facultatif du commercial auquel affecter
                immédiatement le projet.

            batch_size:
                Nombre maximal de prospects envoyés dans chaque lot.

        Returns:
            ProjectDeploymentSummary:
                Résultat global de la création et de l'import.

        Raises:
            ProjectAlreadyDeployedError:
                Si le projet possède déjà une identité Cloud.

            ProjectImportAfterDeploymentError:
                Si le projet Cloud a été créé, mais que l'import
                des prospects a échoué.

            ProjectDeploymentError:
                Si le projet est invalide ou si sa création échoue.

            CloudAPIError:
                Si le backend Cloud refuse la création du projet.
        """

        self._validate_local_project(project)

        if self.project_manager.is_deployed(project):
            cloud = self.project_manager.get_cloud_configuration(project)
            project_id = str(cloud.get("project_id") or "").strip()

            raise ProjectAlreadyDeployedError(
                "Ce projet est déjà déployé dans Form@Prospect Cloud"
                + (
                    f" avec l'identifiant {project_id}."
                    if project_id
                    else "."
                )
            )

        payload = self._build_payload(
            project,
            description=description,
            assigned_to=assigned_to,
        )

        api = self._get_cloud_api()

        cloud_project = self._create_cloud_project(
            api,
            payload,
        )

        project_id, organization_id = self._validate_cloud_response(
            cloud_project
        )

        deployment_time = datetime.now().isoformat()

        cloud_configuration = self._save_cloud_identity(
            project,
            project_id=project_id,
            organization_id=organization_id,
            deployment_time=deployment_time,
        )

        deployment_result = ProjectDeploymentResult(
            project_id=project_id,
            organization_id=organization_id,
            deployment_status=str(
                cloud_configuration["deployment_status"]
            ),
            deployed_at=str(cloud_configuration["deployed_at"]),
            last_sync_at=str(cloud_configuration["last_sync_at"]),
            cloud_project=cloud_project,
        )

        try:
            import_result = self._import_local_prospects(
                project,
                project_id=project_id,
                api=api,
                batch_size=batch_size,
            )

        except Exception as exc:
            self._record_import_failure_activity(
                project,
                project_id=project_id,
                error=exc,
            )

            raise ProjectImportAfterDeploymentError(
                (
                    "Le projet a bien été créé dans Form@Prospect Cloud, "
                    "mais l'import des prospects locaux a échoué. "
                    f"Identifiant Cloud du projet : {project_id}"
                ),
                project_id=project_id,
            ) from exc

        cloud_configuration = self._update_last_sync(
            project,
            project_id=project_id,
            organization_id=organization_id,
            deployed_at=deployment_result.deployed_at,
        )

        deployment_result = ProjectDeploymentResult(
            project_id=project_id,
            organization_id=organization_id,
            deployment_status=str(
                cloud_configuration["deployment_status"]
            ),
            deployed_at=str(cloud_configuration["deployed_at"]),
            last_sync_at=str(cloud_configuration["last_sync_at"]),
            cloud_project=cloud_project,
        )

        self._record_deployment_activity(
            project,
            project_id=project_id,
            import_result=import_result,
        )

        return ProjectDeploymentSummary(
            project_id=project_id,
            deployment_result=deployment_result,
            import_result=import_result,
        )

    def synchronize(
        self,
        project: Project,
        *,
        batch_size: int = ProjectImportService.DEFAULT_BATCH_SIZE,
    ) -> ProjectDeploymentSummary:
        """
        Synchronise les prospects locaux avec un projet Cloud déjà créé.

        Aucun nouveau projet Cloud n'est créé. La méthode réutilise
        l'identifiant enregistré dans project.json.
        """

        self._validate_local_project(project)

        cloud_configuration = (
            self.project_manager.get_cloud_configuration(project)
        )

        project_id = str(
            cloud_configuration.get("project_id") or ""
        ).strip()

        organization_id = str(
            cloud_configuration.get("organization_id") or ""
        ).strip()

        deployed_at = str(
            cloud_configuration.get("deployed_at") or ""
        ).strip()

        if not project_id:
            raise ProjectDeploymentError(
                "L'identifiant du projet Cloud est introuvable "
                "dans project.json."
            )

        if not organization_id:
            raise ProjectDeploymentError(
                "L'identifiant de l'organisation Cloud est introuvable "
                "dans project.json."
            )

        api = self._get_cloud_api()

        try:
            cloud_project = api.get_project(project_id)

            import_result = self._import_local_prospects(
                project,
                project_id=project_id,
                api=api,
                batch_size=batch_size,
            )

        except CloudAPIError:
            raise

        except Exception as exc:
            self._record_import_failure_activity(
                project,
                project_id=project_id,
                error=exc,
            )

            raise ProjectDeploymentError(
                "La synchronisation des prospects vers le Cloud "
                f"a échoué : {type(exc).__name__} : {exc}"
            ) from exc

        cloud_configuration = self._update_last_sync(
            project,
            project_id=project_id,
            organization_id=organization_id,
            deployed_at=deployed_at or datetime.now().isoformat(),
        )

        deployment_result = ProjectDeploymentResult(
            project_id=project_id,
            organization_id=organization_id,
            deployment_status=str(
                cloud_configuration["deployment_status"]
            ),
            deployed_at=str(
                cloud_configuration["deployed_at"]
            ),
            last_sync_at=str(
                cloud_configuration["last_sync_at"]
            ),
            cloud_project=cloud_project,
        )

        self._record_deployment_activity(
            project,
            project_id=project_id,
            import_result=import_result,
        )

        return ProjectDeploymentSummary(
            project_id=project_id,
            deployment_result=deployment_result,
            import_result=import_result,
        )

    def get_deployment_status(
        self,
        project: Project,
    ) -> dict[str, Any]:
        """Retourne l'état Cloud actuellement enregistré localement."""

        self._validate_local_project(project)

        return self.project_manager.get_cloud_configuration(project)

    def is_deployed(
        self,
        project: Project,
    ) -> bool:
        """Indique si le projet local est déjà rattaché au Cloud."""

        self._validate_local_project(project)

        return self.project_manager.is_deployed(project)

    @staticmethod
    def _validate_local_project(project: Project) -> None:
        """Vérifie que le projet local peut être déployé."""

        if project is None:
            raise ProjectDeploymentError(
                "Aucun projet local n'a été fourni."
            )

        if not isinstance(project, Project):
            raise ProjectDeploymentError(
                "Le projet fourni n'est pas un projet Form@Prospect valide."
            )

        if not project.exists():
            raise ProjectDeploymentError(
                "Le dossier du projet local est introuvable."
            )

        if not project.has_configuration():
            raise ProjectDeploymentError(
                "Le fichier project.json du projet est introuvable."
            )

        if not project.database.is_file():
            raise ProjectDeploymentError(
                "La base de données project.db du projet est introuvable."
            )

        if not str(project.name).strip():
            raise ProjectDeploymentError(
                "Le projet local ne possède pas de nom valide."
            )

    @staticmethod
    def _build_payload(
        project: Project,
        *,
        description: str,
        assigned_to: str | None,
    ) -> dict[str, Any]:
        """Construit les données acceptées par POST /projects."""

        normalized_assigned_to = (
            str(assigned_to).strip()
            if assigned_to is not None
            else None
        )

        if not normalized_assigned_to:
            normalized_assigned_to = None

        return {
            "name": str(project.name).strip(),
            "description": str(description or "").strip(),
            "status": "preparation",
            "assigned_to": normalized_assigned_to,
        }

    @staticmethod
    def _get_cloud_api() -> CloudAPIClient:
        """Retourne le client API de la session Cloud active."""

        try:
            return CloudRuntime.api()

        except RuntimeError as exc:
            raise ProjectDeploymentError(
                "Aucune session Form@Prospect Cloud active."
            ) from exc

        except Exception as exc:
            raise ProjectDeploymentError(
                "Le client Form@Prospect Cloud n'a pas pu être initialisé."
            ) from exc

    @staticmethod
    def _create_cloud_project(
        api: CloudAPIClient,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Crée le projet dans le Cloud."""

        try:
            return api.create_project(payload)

        except CloudAPIError:
            raise

        except Exception as exc:
            raise ProjectDeploymentError(
                "Une erreur inattendue est survenue pendant la création "
                "du projet dans le Cloud."
            ) from exc

    def _save_cloud_identity(
        self,
        project: Project,
        *,
        project_id: str,
        organization_id: str,
        deployment_time: str,
    ) -> dict[str, Any]:
        """
        Enregistre immédiatement l'identité Cloud dans project.json.

        Cette écriture est réalisée avant l'import afin de ne pas perdre
        l'identifiant du projet si l'import échoue ensuite.
        """

        try:
            return self.project_manager.update_cloud_configuration(
                project,
                project_id=project_id,
                organization_id=organization_id,
                deployment_status=(
                    self.project_manager.CLOUD_STATUS_DEPLOYED
                ),
                deployed_at=deployment_time,
                last_sync_at=deployment_time,
            )

        except ProjectConfigurationError as exc:
            raise ProjectDeploymentError(
                "Le projet a été créé dans le Cloud, mais son fichier "
                "project.json n'a pas pu être mis à jour. "
                f"Identifiant Cloud du projet : {project_id}"
            ) from exc

    @staticmethod
    def _import_local_prospects(
        project: Project,
        *,
        project_id: str,
        api: CloudAPIClient,
        batch_size: int,
    ) -> ProjectImportResult:
        """Construit les dépendances puis importe les prospects locaux."""

        repository = ProspectRepository(
            str(project.database)
        )

        import_service = ProjectImportService(
            repository=repository,
            api=api,
        )

        return import_service.import_project(
            project_id,
            batch_size=batch_size,
        )

    def _update_last_sync(
        self,
        project: Project,
        *,
        project_id: str,
        organization_id: str,
        deployed_at: str,
    ) -> dict[str, Any]:
        """Actualise la date de synchronisation après l'import."""

        last_sync_at = datetime.now().isoformat()

        try:
            return self.project_manager.update_cloud_configuration(
                project,
                project_id=project_id,
                organization_id=organization_id,
                deployment_status=(
                    self.project_manager.CLOUD_STATUS_DEPLOYED
                ),
                deployed_at=deployed_at,
                last_sync_at=last_sync_at,
            )

        except ProjectConfigurationError as exc:
            raise ProjectDeploymentError(
                "Les prospects ont été importés, mais la date de dernière "
                "synchronisation n'a pas pu être enregistrée dans "
                "project.json. "
                f"Identifiant Cloud du projet : {project_id}"
            ) from exc

    @staticmethod
    def _validate_cloud_response(
        cloud_project: object,
    ) -> tuple[str, str]:
        """Extrait et valide les identifiants retournés par le Cloud."""

        if not isinstance(cloud_project, dict):
            raise InvalidCloudProjectResponseError(
                "Form@Prospect Cloud a retourné une réponse invalide."
            )

        project_id = str(
            cloud_project.get("id") or ""
        ).strip()

        organization_id = str(
            cloud_project.get("organization_id") or ""
        ).strip()

        if not project_id:
            raise InvalidCloudProjectResponseError(
                "La réponse du Cloud ne contient pas l'identifiant "
                "du projet créé."
            )

        if not organization_id:
            raise InvalidCloudProjectResponseError(
                "La réponse du Cloud ne contient pas l'identifiant "
                "de l'organisation."
            )

        return project_id, organization_id

    @staticmethod
    def _record_deployment_activity(
        project: Project,
        *,
        project_id: str,
        import_result: ProjectImportResult,
    ) -> None:
        """Enregistre le déploiement complet dans l'activité locale."""

        try:
            ActivityService.record(
                "Projet déployé dans le Cloud",
                (
                    f"Le projet {project.name} a été créé dans "
                    "Form@Prospect Cloud. "
                    f"Identifiant : {project_id}. "
                    f"{import_result.imported_prospects} prospect(s) "
                    "importé(s), "
                    f"{import_result.failed_prospects} échec(s), "
                    f"{import_result.processed_batches} lot(s) traité(s)."
                ),
                category="cloud",
                level=(
                    "success"
                    if import_result.failed_prospects == 0
                    else "warning"
                ),
                project=project,
            )

        except Exception:
            pass

    @staticmethod
    def _record_import_failure_activity(
        project: Project,
        *,
        project_id: str,
        error: Exception,
    ) -> None:
        """Enregistre un échec d'import sans masquer l'erreur initiale."""

        try:
            ActivityService.record(
                "Import Cloud interrompu",
                (
                    f"Le projet {project.name} a été créé dans le Cloud "
                    f"avec l'identifiant {project_id}, mais l'import "
                    "des prospects a échoué. "
                    f"Erreur : {error}"
                ),
                category="cloud",
                level="error",
                project=project,
            )

        except Exception:
            pass