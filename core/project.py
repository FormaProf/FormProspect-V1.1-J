from pathlib import Path


class Project:
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

    def exists(self):
        return self.folder.exists()