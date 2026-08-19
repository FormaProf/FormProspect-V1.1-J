from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.application_state import ApplicationState
from services.backup_service import BackupService
from services.system.activity_service import ActivityService


@dataclass(frozen=True)
class RecoveryPoint:
    path: Path
    reason: str


class RecoveryManager:
    """Point d'entrée unique pour protéger un projet avant une action sensible."""

    BEFORE_IMPORT = "AVANT_IMPORT"
    BEFORE_ENRICHMENT = "AVANT_ENRICHISSEMENT"
    BEFORE_RESTORE = "AVANT_RESTAURATION"
    BEFORE_DELETE = "AVANT_SUPPRESSION"

    def __init__(self, backup_service: BackupService | None = None):
        self.backup_service = backup_service or BackupService()

    def create_checkpoint(self, reason: str, *, project=None) -> RecoveryPoint:
        project = project or ApplicationState.get_project()
        if project is None:
            raise ValueError("Aucun projet actif à protéger.")

        try:
            path = self.backup_service.create_automatic_backup(project, reason)
        except Exception as exc:
            ActivityService.record(
                "Échec du point de restauration",
                f"{reason} : {exc}",
                category="backup",
                level="error",
                metadata={"reason": reason},
                project=project,
            )
            raise

        ActivityService.record(
            "Point de restauration créé",
            f"{reason.replace('_', ' ').title()} — {path.name}",
            category="backup",
            level="success",
            metadata={"reason": reason, "path": str(path)},
            project=project,
        )
        return RecoveryPoint(path=path, reason=reason)

    def before_import(self, *, project=None) -> RecoveryPoint:
        return self.create_checkpoint(self.BEFORE_IMPORT, project=project)

    def before_enrichment(self, *, project=None) -> RecoveryPoint:
        return self.create_checkpoint(self.BEFORE_ENRICHMENT, project=project)

    def before_restore(self, *, project=None) -> RecoveryPoint:
        return self.create_checkpoint(self.BEFORE_RESTORE, project=project)
