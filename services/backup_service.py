from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from core.constants import APP_NAME, VERSION
from core.project import Project


class BackupService:
    """Service de sauvegarde et restauration des projets Form@Prospect.

    Une sauvegarde `.fpbackup` est une archive ZIP contenant les fichiers utiles
    du projet. Le dossier `backups` est volontairement exclu afin d'éviter les
    sauvegardes récursives et les fichiers trop volumineux.
    """

    BACKUP_EXTENSION = ".fpbackup"
    METADATA_FILENAME = "backup_metadata.json"
    REQUIRED_FILES = {"project.json", "project.db"}
    PROJECT_DIRECTORIES = ("imports", "exports", "logs", "cache")
    EXCLUDED_DIRECTORIES = {"backups", "__pycache__", ".git"}
    AUTOMATIC_PREFIX = "AUTO"
    DEFAULT_AUTOMATIC_RETENTION = 20

    def create_backup(self, project: Project, destination_path=None) -> Path:
        """Crée une sauvegarde complète du projet et retourne son chemin."""
        self.validate_project(project)

        destination = Path(destination_path) if destination_path else self.default_backup_path(project)
        destination = self._ensure_backup_extension(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        temp_destination = destination.with_suffix(destination.suffix + ".tmp")
        if temp_destination.exists():
            temp_destination.unlink()

        try:
            with zipfile.ZipFile(temp_destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                self._write_metadata(archive, project)
                self._write_project_files(archive, project)

            if not self._validate_archive_content(temp_destination):
                raise ValueError("La sauvegarde créée est invalide.")

            if destination.exists():
                destination.unlink()

            temp_destination.rename(destination)
            self._write_log(project, f"Sauvegarde créée : {destination}")
            return destination

        except Exception:
            if temp_destination.exists():
                temp_destination.unlink()
            raise

    def create_automatic_backup(
        self,
        project: Project,
        reason: str,
        *,
        retention: int | None = None,
    ) -> Path:
        """Crée un point de restauration automatique nommé selon son motif.

        Exemple : ``AUTO_2026-07-15_14-30-00_AVANT_IMPORT.fpbackup``.
        Les sauvegardes manuelles ne sont jamais supprimées par la rétention.
        """
        self.validate_project(project)
        safe_reason = self._safe_filename(reason).upper() or "POINT_RESTAURATION"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destination = project.backups / (
            f"{self.AUTOMATIC_PREFIX}_{timestamp}_{safe_reason}{self.BACKUP_EXTENSION}"
        )
        backup_path = self.create_backup(project, destination)
        self.cleanup_automatic_backups(
            project,
            keep=self.DEFAULT_AUTOMATIC_RETENTION if retention is None else retention,
        )
        return backup_path

    def list_backups(self, project: Project) -> list[dict]:
        """Retourne les sauvegardes du projet, de la plus récente à la plus ancienne."""
        self.validate_project(project)
        results = []
        for path in project.backups.glob(f"*{self.BACKUP_EXTENSION}"):
            try:
                stat = path.stat()
            except OSError:
                continue
            results.append({
                "path": path,
                "name": path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
                "automatic": path.name.startswith(f"{self.AUTOMATIC_PREFIX}_"),
            })
        results.sort(key=lambda item: item["modified_at"], reverse=True)
        return results

    def cleanup_automatic_backups(self, project: Project, keep: int = 20) -> int:
        """Conserve les ``keep`` sauvegardes automatiques les plus récentes."""
        keep = max(1, int(keep))
        automatic = [item for item in self.list_backups(project) if item["automatic"]]
        deleted = 0
        for item in automatic[keep:]:
            try:
                item["path"].unlink()
                deleted += 1
            except OSError:
                continue
        if deleted:
            self._write_log(project, f"{deleted} ancienne(s) sauvegarde(s) automatique(s) supprimée(s).")
        return deleted

    def restore_backup(self, backup_file, destination_folder) -> Path:
        """Restaure une sauvegarde dans un nouveau dossier et retourne ce dossier."""
        backup_path = Path(backup_file)
        destination_parent = Path(destination_folder)

        if not self.validate_backup(backup_path):
            raise ValueError("Sauvegarde invalide ou corrompue.")

        destination_parent.mkdir(parents=True, exist_ok=True)
        project_name = self._project_name_from_backup(backup_path)
        restore_folder = self._unique_restore_folder(destination_parent, project_name)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                with zipfile.ZipFile(backup_path, "r") as archive:
                    archive.extractall(temp_path)

                self._validate_extracted_backup(temp_path)
                shutil.move(str(temp_path), str(restore_folder))

            except Exception:
                if restore_folder.exists():
                    shutil.rmtree(restore_folder, ignore_errors=True)
                raise

        project = Project(restore_folder)
        self._ensure_project_directories(project)
        self._write_log(project, f"Projet restauré depuis : {backup_path}")
        return restore_folder

    def validate_backup(self, backup_file) -> bool:
        """Vérifie qu'un fichier `.fpbackup` contient les fichiers indispensables."""
        backup_path = Path(backup_file)

        if not backup_path.exists() or not backup_path.is_file():
            return False

        if backup_path.suffix.lower() != self.BACKUP_EXTENSION:
            return False

        return self._validate_archive_content(backup_path)

    def _validate_archive_content(self, backup_path: Path) -> bool:
        try:
            with zipfile.ZipFile(backup_path, "r") as archive:
                names = set(archive.namelist())
                return self.REQUIRED_FILES.issubset(names)
        except zipfile.BadZipFile:
            return False

    def validate_project(self, project: Project) -> None:
        """Vérifie qu'un projet est sauvegardable."""
        if project is None:
            raise ValueError("Aucun projet actif.")

        if not project.folder.exists():
            raise FileNotFoundError("Le dossier du projet est introuvable.")

        if not project.config.exists():
            raise FileNotFoundError("project.json introuvable.")

        if not project.database.exists():
            raise FileNotFoundError("project.db introuvable.")

        self._ensure_project_directories(project)

    def default_backup_path(self, project: Project) -> Path:
        """Retourne le chemin de sauvegarde par défaut du projet actif."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = self._safe_filename(project.name)
        backups_folder = project.folder / "backups"
        return backups_folder / f"{safe_name}_{timestamp}{self.BACKUP_EXTENSION}"

    def _write_metadata(self, archive: zipfile.ZipFile, project: Project) -> None:
        metadata = {
            "app": APP_NAME,
            "app_version": VERSION,
            "backup_version": "1.0",
            "project_name": project.name,
            "created_at": datetime.now().isoformat(),
        }
        archive.writestr(
            self.METADATA_FILENAME,
            json.dumps(metadata, indent=4, ensure_ascii=False),
        )

    def _write_project_files(self, archive: zipfile.ZipFile, project: Project) -> None:
        for path in project.folder.rglob("*"):
            if path.is_dir():
                continue

            relative = path.relative_to(project.folder)
            parts = set(relative.parts)

            if parts.intersection(self.EXCLUDED_DIRECTORIES):
                continue

            archive.write(path, relative.as_posix())

    def _project_name_from_backup(self, backup_path: Path) -> str:
        try:
            with zipfile.ZipFile(backup_path, "r") as archive:
                with archive.open("project.json") as file:
                    config = json.load(file)
                    name = str(config.get("nom") or "Projet restaure").strip()
                    if name:
                        return name
        except Exception:
            pass

        return backup_path.stem

    def _validate_extracted_backup(self, folder: Path) -> None:
        for filename in self.REQUIRED_FILES:
            if not (folder / filename).exists():
                raise ValueError(f"Sauvegarde invalide : {filename} introuvable.")

    def _unique_restore_folder(self, parent: Path, project_name: str) -> Path:
        safe_name = self._safe_folder_name(project_name)
        candidate = parent / safe_name

        if not candidate.exists():
            return candidate

        restored_candidate = parent / f"{safe_name} restauré"
        if not restored_candidate.exists():
            return restored_candidate

        counter = 2
        while True:
            candidate = parent / f"{safe_name} restauré {counter}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _ensure_project_directories(self, project: Project) -> None:
        for directory in self.PROJECT_DIRECTORIES:
            (project.folder / directory).mkdir(exist_ok=True)
        (project.folder / "backups").mkdir(exist_ok=True)

    def _write_log(self, project: Project, message: str) -> None:
        try:
            project.logs.mkdir(exist_ok=True)
            log_file = project.logs / "backups.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as file:
                file.write(f"[{timestamp}] {message}\n")
        except Exception:
            # La journalisation ne doit jamais bloquer une sauvegarde valide.
            pass

    def _ensure_backup_extension(self, path: Path) -> Path:
        if path.suffix.lower() != self.BACKUP_EXTENSION:
            return path.with_suffix(self.BACKUP_EXTENSION)
        return path

    def _safe_filename(self, value: str) -> str:
        value = value.strip() or "projet"
        value = re.sub(r"[^\w\-. ]+", "_", value, flags=re.UNICODE)
        return value.replace(" ", "_")

    def _safe_folder_name(self, value: str) -> str:
        value = value.strip() or "Projet restaure"
        return re.sub(r"[<>:\"/\\|?*]+", "_", value)
