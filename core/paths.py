import sys
from pathlib import Path


def app_root() -> Path:
    """Retourne le dossier racine utilisable en développement et après packaging PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str) -> str:
    """Retourne un chemin absolu vers une ressource embarquée."""
    return str(app_root() / relative_path)


def read_version(default: str = "1.0.0") -> str:
    """Lit la version officielle depuis le fichier VERSION."""
    version_file = app_root() / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
        return version or default
    except Exception:
        return default


def user_data_dir() -> Path:
    """Dossier persistant de l'application, indépendant du dossier d'installation."""
    import os

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    folder = base / "Form@Prospect"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
