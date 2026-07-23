from pathlib import Path
import json
from datetime import datetime

from core.project import Project
from core.application_state import ApplicationState
from core.database import init_database
from services.system import ActivityService


class ProjectManager:
    def create_project(self, nom_projet, emplacement):
        dossier = Path(emplacement) / nom_projet
        dossier.mkdir(parents=True, exist_ok=True)

        configuration = {
            "nom": nom_projet,
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
        }
        with open(dossier / "project.json", "w", encoding="utf-8") as handle:
            json.dump(configuration, handle, indent=4, ensure_ascii=False)

        projet = Project(dossier)
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
        if not projet.config.exists():
            raise FileNotFoundError("project.json introuvable.")

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
