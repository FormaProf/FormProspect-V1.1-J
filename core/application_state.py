from __future__ import annotations

from core.project import Project
from core.workspace_state import CloudProject, WorkspaceState


class ApplicationState:
    """
    Couche de compatibilité avec l'ancien fonctionnement de Form@Prospect.

    Les anciennes pages utilisent encore ApplicationState pour accéder au
    projet local actif. Le nouvel état de référence est désormais
    WorkspaceState, qui prend en charge les projets locaux et Cloud.
    """

    current_project: Project | None = None

    @classmethod
    def set_project(cls, project: Project) -> None:
        """
        Active un projet local.

        Cette méthode conserve le comportement historique tout en enregistrant
        également le projet dans WorkspaceState.
        """

        if not isinstance(project, Project):
            raise TypeError(
                "Le projet fourni n'est pas un projet Form@Prospect valide."
            )

        cls.current_project = project
        WorkspaceState.set_local_project(project)

    @classmethod
    def set_cloud_project(cls, project: CloudProject | dict) -> None:
        """
        Active un projet Cloud.

        Aucun dossier Windows ni aucune base SQLite locale ne sont nécessaires.
        """

        cls.current_project = None
        WorkspaceState.set_cloud_project(project)

    @classmethod
    def get_project(cls) -> Project | None:
        """
        Retourne uniquement le projet local actif.

        Pour un projet Cloud, cette méthode retourne None afin de ne pas faire
        croire aux anciens composants qu'une base SQLite locale existe.
        """

        workspace_project = WorkspaceState.get_local_project()

        if workspace_project is not None:
            cls.current_project = workspace_project

        return cls.current_project

    @classmethod
    def get_cloud_project(cls) -> CloudProject | None:
        """Retourne le projet Cloud actif, s'il existe."""

        return WorkspaceState.get_cloud_project()

    @classmethod
    def get_workspace(cls):
        """Retourne le contexte Local ou Cloud actuellement actif."""

        return WorkspaceState.current()

    @classmethod
    def has_project(cls) -> bool:
        """
        Indique qu'un espace de travail est actif.

        Cette méthode retourne désormais True pour un projet local comme pour
        un projet Cloud. Cela permet aux pages migrées de ne plus bloquer les
        utilisateurs Cloud avec le message « Aucun projet actif ».
        """

        return WorkspaceState.has_workspace()

    @classmethod
    def has_local_project(cls) -> bool:
        return WorkspaceState.has_local_project()

    @classmethod
    def has_cloud_project(cls) -> bool:
        return WorkspaceState.has_cloud_project()

    @classmethod
    def is_local(cls) -> bool:
        return WorkspaceState.is_local()

    @classmethod
    def is_cloud(cls) -> bool:
        return WorkspaceState.is_cloud()

    @classmethod
    def get_project_id(cls) -> str | None:
        """Retourne l'identifiant UUID du projet Cloud actif."""

        return WorkspaceState.get_project_id()

    @classmethod
    def get_organization_id(cls) -> str | None:
        return WorkspaceState.get_organization_id()

    @classmethod
    def get_project_name(cls) -> str:
        return WorkspaceState.get_name()

    @classmethod
    def clear_project(cls) -> None:
        """Ferme le projet local ou Cloud actuellement actif."""

        cls.current_project = None
        WorkspaceState.clear()