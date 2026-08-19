from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.application_state import ApplicationState
from core.project import Project
from core.workspace_state import (
    CloudProject,
    WorkspaceContext,
    WorkspaceState,
)
from services.project_manager import (
    ProjectConfigurationError,
    ProjectManager,
)


class DataSourceResolutionError(RuntimeError):
    """Erreur lors de la détermination de la source de données active."""


class DataSourceMode(str, Enum):
    """Sources de données prises en charge par l'application desktop."""

    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(frozen=True)
class DataSourceContext:
    """
    Contexte immuable décrivant la source de données active.

    En mode local, ``project`` contient un objet Project possédant un dossier
    Windows et une base SQLite.

    En mode Cloud, ``project`` contient un objet CloudProject léger, sans
    dossier Windows et sans base SQLite.
    """

    mode: DataSourceMode
    project: Project | CloudProject
    project_id: str | None = None
    organization_id: str | None = None
    deployment_status: str = ProjectManager.CLOUD_STATUS_LOCAL

    @property
    def is_local(self) -> bool:
        return self.mode is DataSourceMode.LOCAL

    @property
    def is_cloud(self) -> bool:
        return self.mode is DataSourceMode.CLOUD

    @property
    def local_project(self) -> Project | None:
        if self.is_local and isinstance(self.project, Project):
            return self.project

        return None

    @property
    def cloud_project(self) -> CloudProject | None:
        if self.is_cloud and isinstance(self.project, CloudProject):
            return self.project

        return None

    @property
    def name(self) -> str:
        return self.project.name


class DataSourceResolver:
    """
    Détermine la source de données active de Form@Prospect.

    Le resolver prend désormais en charge :

    - les projets locaux ouverts depuis un dossier Windows ;
    - les projets Cloud sélectionnés depuis l'espace de travail connecté.

    WorkspaceState constitue la source de vérité principale.

    La lecture de ApplicationState.current_project est uniquement conservée
    comme mécanisme de compatibilité avec d'anciens composants qui auraient
    affecté directement le projet local sans appeler set_project().
    """

    def __init__(
        self,
        project_manager: ProjectManager | None = None,
    ) -> None:
        self.project_manager = project_manager or ProjectManager()

    def current_workspace(self) -> WorkspaceContext:
        """Retourne l'espace de travail actif."""

        workspace = WorkspaceState.current()

        if workspace is not None:
            return workspace

        # Compatibilité avec d'anciens appels qui auraient modifié directement
        # ApplicationState.current_project sans passer par set_project().
        legacy_project = ApplicationState.current_project

        if isinstance(legacy_project, Project):
            return WorkspaceState.set_local_project(legacy_project)

        raise DataSourceResolutionError(
            "Aucun espace de travail Form@Prospect n'est actuellement ouvert."
        )

    def current_project(self) -> Project | CloudProject:
        """
        Retourne le projet actif, qu'il soit local ou Cloud.

        Cette méthode ne garantit donc plus que le résultat possède les
        attributs ``database`` ou ``folder``.
        """

        workspace = self.current_workspace()

        if workspace.is_local:
            if workspace.local_project is None:
                raise DataSourceResolutionError(
                    "L'espace local actif ne contient aucun projet valide."
                )

            return workspace.local_project

        if workspace.is_cloud:
            if workspace.cloud_project is None:
                raise DataSourceResolutionError(
                    "L'espace Cloud actif ne contient aucun projet valide."
                )

            return workspace.cloud_project

        raise DataSourceResolutionError(
            "Le type de l'espace de travail actif n'est pas reconnu."
        )

    def resolve(
        self,
        project: Project | CloudProject | None = None,
    ) -> DataSourceContext:
        """
        Construit le contexte de données actif.

        Lorsque ``project`` n'est pas fourni, le WorkspaceState actif est
        utilisé.

        Un CloudProject est toujours traité en mode Cloud.

        Un Project local continue d'utiliser son fichier project.json pour
        déterminer s'il doit accéder à SQLite ou à sa version déployée dans le
        Cloud.
        """

        selected_project = project or self.current_project()

        if isinstance(selected_project, CloudProject):
            return self._resolve_cloud_project(selected_project)

        if isinstance(selected_project, Project):
            return self._resolve_local_project(selected_project)

        raise DataSourceResolutionError(
            "Le projet actif n'est pas un projet Form@Prospect valide."
        )

    def _resolve_cloud_project(
        self,
        project: CloudProject,
    ) -> DataSourceContext:
        """Construit le contexte d'un projet sélectionné depuis le Cloud."""

        project_id = self._clean_optional_identifier(project.project_id)

        if not project_id:
            raise DataSourceResolutionError(
                "Le projet Cloud actif ne possède aucun identifiant valide."
            )

        return DataSourceContext(
            mode=DataSourceMode.CLOUD,
            project=project,
            project_id=project_id,
            organization_id=self._clean_optional_identifier(
                project.organization_id
            ),
            deployment_status=ProjectManager.CLOUD_STATUS_DEPLOYED,
        )

    def _resolve_local_project(
        self,
        project: Project,
    ) -> DataSourceContext:
        """
        Construit le contexte d'un projet provenant d'un dossier Windows.

        Un projet local peut rester en mode SQLite ou utiliser le Cloud lorsque
        son project.json indique qu'il a été déployé.
        """

        self._validate_local_project(project)

        try:
            cloud = self.project_manager.get_cloud_configuration(project)
        except ProjectConfigurationError as exc:
            raise DataSourceResolutionError(
                "Impossible de déterminer la source de données : "
                "le fichier project.json est invalide."
            ) from exc

        deployment_status = str(
            cloud.get("deployment_status")
            or self.project_manager.CLOUD_STATUS_LOCAL
        ).strip().lower()

        project_id = self._clean_optional_identifier(
            cloud.get("project_id")
        )
        organization_id = self._clean_optional_identifier(
            cloud.get("organization_id")
        )

        if deployment_status == self.project_manager.CLOUD_STATUS_LOCAL:
            return DataSourceContext(
                mode=DataSourceMode.LOCAL,
                project=project,
                project_id=project_id,
                organization_id=organization_id,
                deployment_status=deployment_status,
            )

        if deployment_status == self.project_manager.CLOUD_STATUS_DEPLOYED:
            if not project_id:
                raise DataSourceResolutionError(
                    "Le projet est marqué comme déployé, mais aucun "
                    "identifiant Cloud n'est enregistré."
                )

            return DataSourceContext(
                mode=DataSourceMode.CLOUD,
                project=project,
                project_id=project_id,
                organization_id=organization_id,
                deployment_status=deployment_status,
            )

        raise DataSourceResolutionError(
            "Statut de déploiement Cloud non reconnu : "
            f"{deployment_status!r}."
        )

    def is_local(
        self,
        project: Project | CloudProject | None = None,
    ) -> bool:
        return self.resolve(project).is_local

    def is_cloud(
        self,
        project: Project | CloudProject | None = None,
    ) -> bool:
        return self.resolve(project).is_cloud

    def project_id(
        self,
        project: Project | CloudProject | None = None,
    ) -> str | None:
        return self.resolve(project).project_id

    def organization_id(
        self,
        project: Project | CloudProject | None = None,
    ) -> str | None:
        return self.resolve(project).organization_id

    def deployment_status(
        self,
        project: Project | CloudProject | None = None,
    ) -> str:
        return self.resolve(project).deployment_status

    @staticmethod
    def _validate_local_project(project: Project) -> None:
        if not isinstance(project, Project):
            raise DataSourceResolutionError(
                "Le projet fourni n'est pas un projet local Form@Prospect valide."
            )

        if not project.exists():
            raise DataSourceResolutionError(
                "Le dossier du projet actif est introuvable."
            )

        if not project.has_configuration():
            raise DataSourceResolutionError(
                "Le fichier project.json du projet actif est introuvable."
            )

    @staticmethod
    def _clean_optional_identifier(value: object) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None