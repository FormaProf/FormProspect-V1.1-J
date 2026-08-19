from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from core.project import Project


class WorkspaceStateError(RuntimeError):
    """Erreur liée à l’espace de travail actif."""


class WorkspaceMode(str, Enum):
    """Types d’espaces de travail pris en charge."""

    LOCAL = "local"
    CLOUD = "cloud"


@dataclass(frozen=True)
class CloudProject:
    """
    Représentation légère d’un projet Cloud.

    Cet objet ne correspond pas à un dossier Windows et ne possède donc
    ni chemin local, ni fichier project.json, ni base SQLite.
    """

    id: str
    name: str
    organization_id: str | None = None
    assigned_to: str | None = None
    status: str | None = None
    prospect_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CloudProject":
        """
        Construit un CloudProject depuis la réponse de l’API.

        Accepte aussi bien une clé ``id`` qu’une clé ``project_id``.
        """

        project_id = cls._clean_identifier(
            data.get("id") or data.get("project_id")
        )

        if not project_id:
            raise WorkspaceStateError(
                "Le projet Cloud ne contient aucun identifiant valide."
            )

        name = str(
            data.get("name")
            or data.get("project_name")
            or "Projet Cloud"
        ).strip()

        if not name:
            name = "Projet Cloud"

        organization_id = cls._clean_identifier(
            data.get("organization_id")
        )

        assigned_to = cls._clean_identifier(
            data.get("assigned_to")
            or data.get("assigned_user_id")
        )

        status_value = data.get("status")
        status = (
            str(status_value).strip()
            if status_value is not None
            else None
        )

        prospect_count = cls._clean_optional_integer(
            data.get("prospect_count")
            or data.get("prospects_count")
            or data.get("total_prospects")
        )

        return cls(
            id=project_id,
            name=name,
            organization_id=organization_id,
            assigned_to=assigned_to,
            status=status,
            prospect_count=prospect_count,
            metadata=dict(data),
        )

    @property
    def project_id(self) -> str:
        """Alias explicite utilisé par les services Cloud."""

        return self.id

    @staticmethod
    def _clean_identifier(value: Any) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _clean_optional_integer(value: Any) -> int | None:
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class WorkspaceContext:
    """Description immuable de l’espace de travail actuellement ouvert."""

    mode: WorkspaceMode
    local_project: Project | None = None
    cloud_project: CloudProject | None = None

    @property
    def is_local(self) -> bool:
        return self.mode is WorkspaceMode.LOCAL

    @property
    def is_cloud(self) -> bool:
        return self.mode is WorkspaceMode.CLOUD

    @property
    def name(self) -> str:
        if self.is_local and self.local_project is not None:
            return self.local_project.name

        if self.is_cloud and self.cloud_project is not None:
            return self.cloud_project.name

        return "Aucun projet"

    @property
    def project_id(self) -> str | None:
        if self.cloud_project is None:
            return None

        return self.cloud_project.project_id

    @property
    def organization_id(self) -> str | None:
        if self.cloud_project is None:
            return None

        return self.cloud_project.organization_id


class WorkspaceState:
    """
    État global de l’espace de travail actif.

    Il peut représenter :

    - un projet local ouvert depuis un dossier Windows ;
    - un projet Cloud ouvert depuis la liste des projets accessibles.

    Cette classe ne réalise aucun appel réseau et aucun accès SQLite.
    """

    _current: WorkspaceContext | None = None

    @classmethod
    def set_local_project(cls, project: Project) -> WorkspaceContext:
        """Active un projet local existant."""

        if not isinstance(project, Project):
            raise WorkspaceStateError(
                "Le projet local fourni n’est pas un projet Form@Prospect valide."
            )

        context = WorkspaceContext(
            mode=WorkspaceMode.LOCAL,
            local_project=project,
            cloud_project=None,
        )

        cls._current = context
        return context

    @classmethod
    def set_cloud_project(
        cls,
        project: CloudProject | Mapping[str, Any],
    ) -> WorkspaceContext:
        """Active un projet Cloud issu de l’API."""

        cloud_project = (
            project
            if isinstance(project, CloudProject)
            else CloudProject.from_mapping(project)
        )

        context = WorkspaceContext(
            mode=WorkspaceMode.CLOUD,
            local_project=None,
            cloud_project=cloud_project,
        )

        cls._current = context
        return context

    @classmethod
    def current(cls) -> WorkspaceContext | None:
        """Retourne l’espace de travail actif, ou None."""

        return cls._current

    @classmethod
    def require_current(cls) -> WorkspaceContext:
        """Retourne l’espace actif ou lève une erreur explicite."""

        if cls._current is None:
            raise WorkspaceStateError(
                "Aucun espace de travail Form@Prospect n’est actuellement ouvert."
            )

        return cls._current

    @classmethod
    def clear(cls) -> None:
        """Ferme l’espace de travail actif."""

        cls._current = None

    @classmethod
    def has_workspace(cls) -> bool:
        return cls._current is not None

    @classmethod
    def has_local_project(cls) -> bool:
        return cls._current is not None and cls._current.is_local

    @classmethod
    def has_cloud_project(cls) -> bool:
        return cls._current is not None and cls._current.is_cloud

    @classmethod
    def is_local(cls) -> bool:
        return cls.has_local_project()

    @classmethod
    def is_cloud(cls) -> bool:
        return cls.has_cloud_project()

    @classmethod
    def get_local_project(cls) -> Project | None:
        if cls._current is None:
            return None

        return cls._current.local_project

    @classmethod
    def get_cloud_project(cls) -> CloudProject | None:
        if cls._current is None:
            return None

        return cls._current.cloud_project

    @classmethod
    def get_project_id(cls) -> str | None:
        cloud_project = cls.get_cloud_project()

        if cloud_project is None:
            return None

        return cloud_project.project_id

    @classmethod
    def get_organization_id(cls) -> str | None:
        cloud_project = cls.get_cloud_project()

        if cloud_project is None:
            return None

        return cloud_project.organization_id

    @classmethod
    def get_name(cls) -> str:
        if cls._current is None:
            return "Aucun projet"

        return cls._current.name