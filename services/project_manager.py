from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.application_state import ApplicationState
from core.database import init_database
from core.project import Project
from services.system import ActivityService


class ProjectConfigurationError(RuntimeError):
    """Erreur liée au fichier project.json d'un projet."""


class ProjectManager:
    """Gère le cycle de vie et la configuration des projets locaux."""

    PROJECT_VERSION = "1.0.0"

    CLOUD_STATUS_LOCAL = "local"
    CLOUD_STATUS_DEPLOYED = "deployed"

    def create_project(self, nom_projet, emplacement):
        dossier = Path(emplacement) / nom_projet
        dossier.mkdir(parents=True, exist_ok=True)

        projet = Project(dossier)

        configuration = self._build_default_configuration(nom_projet)
        self.save_configuration(projet, configuration)

        self.ensure_project_structure(projet)
        init_database(projet.database)

        ApplicationState.set_project(projet)

        ActivityService.record(
            "Projet créé",
            f"Le projet {projet.name} a été créé et initialisé.",
            category="project",
            level="success",
            project=projet,
        )

        return projet

    def open_project(self, dossier):
        projet = Project(dossier)

        if not projet.exists():
            raise FileNotFoundError("Le projet n'existe pas.")

        if not projet.has_configuration():
            raise FileNotFoundError("project.json introuvable.")

        configuration = self.read_configuration(projet)

        # Rend les anciens projets compatibles avec la RC-03C.
        normalized_configuration = self.normalize_configuration(
            projet,
            configuration,
        )

        if normalized_configuration != configuration:
            self.save_configuration(projet, normalized_configuration)

        self.ensure_project_structure(projet)
        init_database(projet.database)

        ApplicationState.set_project(projet)

        ActivityService.record(
            "Projet ouvert",
            f"Le projet {projet.name} est maintenant actif.",
            category="project",
            level="info",
            project=projet,
        )

        return projet

    def ensure_project_structure(self, projet):
        projet.logs.mkdir(parents=True, exist_ok=True)
        projet.exports.mkdir(parents=True, exist_ok=True)
        projet.cache.mkdir(parents=True, exist_ok=True)
        projet.imports.mkdir(parents=True, exist_ok=True)

        # Compatibilité avec les anciennes classes Project.
        backups = getattr(projet, "backups", projet.folder / "backups")
        backups.mkdir(parents=True, exist_ok=True)

    def read_configuration(self, projet: Project) -> dict[str, Any]:
        """Lit et valide le fichier project.json."""

        if not projet.config.is_file():
            raise ProjectConfigurationError(
                f"Le fichier de configuration est introuvable : "
                f"{projet.config}"
            )

        try:
            with projet.config.open("r", encoding="utf-8") as handle:
                configuration = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ProjectConfigurationError(
                "Le fichier project.json contient un JSON invalide."
            ) from exc
        except OSError as exc:
            raise ProjectConfigurationError(
                "Impossible de lire le fichier project.json."
            ) from exc

        if not isinstance(configuration, dict):
            raise ProjectConfigurationError(
                "Le contenu de project.json doit être un objet JSON."
            )

        return configuration

    def save_configuration(
        self,
        projet: Project,
        configuration: dict[str, Any],
    ) -> None:
        """Enregistre la configuration du projet de manière sécurisée."""

        if not isinstance(configuration, dict):
            raise ProjectConfigurationError(
                "La configuration du projet doit être un dictionnaire."
            )

        projet.folder.mkdir(parents=True, exist_ok=True)

        temporary_file = projet.config.with_suffix(".json.tmp")

        try:
            with temporary_file.open("w", encoding="utf-8") as handle:
                json.dump(
                    configuration,
                    handle,
                    indent=4,
                    ensure_ascii=False,
                )

            temporary_file.replace(projet.config)

        except OSError as exc:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass

            raise ProjectConfigurationError(
                "Impossible d'enregistrer le fichier project.json."
            ) from exc

    def normalize_configuration(
        self,
        projet: Project,
        configuration: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Complète une ancienne configuration sans supprimer ses données.

        Cette méthode rend les projets créés avant la RC-03C compatibles
        avec les nouvelles métadonnées Cloud.
        """

        normalized = dict(configuration)

        normalized.setdefault("nom", projet.name)
        normalized.setdefault("version", self.PROJECT_VERSION)
        normalized.setdefault("created_at", datetime.now().isoformat())

        cloud = normalized.get("cloud")

        if not isinstance(cloud, dict):
            cloud = {}

        normalized["cloud"] = {
            "project_id": cloud.get("project_id"),
            "organization_id": cloud.get("organization_id"),
            "deployment_status": cloud.get(
                "deployment_status",
                self.CLOUD_STATUS_LOCAL,
            ),
            "deployed_at": cloud.get("deployed_at"),
            "last_sync_at": cloud.get("last_sync_at"),
        }

        return normalized

    def get_cloud_configuration(
        self,
        projet: Project,
    ) -> dict[str, Any]:
        """Retourne les métadonnées Cloud normalisées du projet."""

        configuration = self.read_configuration(projet)
        normalized = self.normalize_configuration(
            projet,
            configuration,
        )

        return dict(normalized["cloud"])

    def update_cloud_configuration(
        self,
        projet: Project,
        *,
        project_id: str | None = None,
        organization_id: str | None = None,
        deployment_status: str | None = None,
        deployed_at: str | None = None,
        last_sync_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Met à jour les métadonnées Cloud du projet.

        Les valeurs non fournies conservent leur valeur actuelle.
        """

        configuration = self.read_configuration(projet)
        configuration = self.normalize_configuration(
            projet,
            configuration,
        )

        cloud = dict(configuration["cloud"])

        if project_id is not None:
            cloud["project_id"] = project_id

        if organization_id is not None:
            cloud["organization_id"] = organization_id

        if deployment_status is not None:
            cloud["deployment_status"] = deployment_status

        if deployed_at is not None:
            cloud["deployed_at"] = deployed_at

        if last_sync_at is not None:
            cloud["last_sync_at"] = last_sync_at

        configuration["cloud"] = cloud
        self.save_configuration(projet, configuration)

        return dict(cloud)

    def is_deployed(self, projet: Project) -> bool:
        """Indique si le projet possède un identifiant Cloud."""

        cloud = self.get_cloud_configuration(projet)

        return bool(
            cloud.get("project_id")
            and cloud.get("deployment_status")
            == self.CLOUD_STATUS_DEPLOYED
        )

    def _build_default_configuration(
        self,
        nom_projet: str,
    ) -> dict[str, Any]:
        """Construit la configuration initiale d'un nouveau projet."""

        return {
            "nom": nom_projet,
            "version": self.PROJECT_VERSION,
            "created_at": datetime.now().isoformat(),
            "cloud": {
                "project_id": None,
                "organization_id": None,
                "deployment_status": self.CLOUD_STATUS_LOCAL,
                "deployed_at": None,
                "last_sync_at": None,
            },
        }