from pathlib import Path


class Project:
    """Représente l'arborescence d'un projet local Form@Prospect."""

    def __init__(self, dossier):
        self.folder = Path(dossier)
        self.name = self.folder.name

        self.database = self.folder / "project.db"
        self.config = self.folder / "project.json"

        self.logs = self.folder / "logs"
        self.exports = self.folder / "exports"
        self.cache = self.folder / "cache"
        self.imports = self.folder / "imports"
        self.backups = self.folder / "backups"

    def exists(self) -> bool:
        """Indique si le dossier du projet existe."""
        return self.folder.exists()

    def has_configuration(self) -> bool:
        """Indique si le projet possède un fichier project.json."""
        return self.config.is_file()