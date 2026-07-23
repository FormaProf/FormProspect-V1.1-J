from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from core.application_state import ApplicationState


class ActivityService:
    """Historique persistant des actions importantes d'un projet.

    Les événements sont enregistrés en JSON Lines pour permettre une lecture
    fiable et évolutive, ainsi que dans un fichier texte lisible pour le support.
    """

    _lock = threading.RLock()
    FILE_NAME = "activity.jsonl"
    TEXT_FILE_NAME = "activity.log"
    MAX_READ_EVENTS = 2000

    @classmethod
    def _resolve_logs_folder(cls, project=None) -> Path | None:
        project = project or ApplicationState.get_project()
        if project is None:
            return None
        logs = Path(project.logs)
        logs.mkdir(parents=True, exist_ok=True)
        return logs

    @classmethod
    def record(
        cls,
        title: str,
        message: str = "",
        *,
        category: str = "general",
        level: str = "info",
        metadata: dict[str, Any] | None = None,
        project=None,
    ) -> bool:
        logs = cls._resolve_logs_folder(project)
        if logs is None:
            return False

        event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "level": str(level).lower(),
            "category": str(category).lower(),
            "title": str(title).strip(),
            "message": str(message).strip(),
            "metadata": metadata or {},
        }

        with cls._lock:
            with (logs / cls.FILE_NAME).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

            text = (
                f"{event['timestamp']} | {event['level'].upper()} | "
                f"{event['category']} | {event['title']}"
            )
            if event["message"]:
                text += f" | {event['message']}"
            with (logs / cls.TEXT_FILE_NAME).open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        return True

    @classmethod
    def list_events(cls, *, project=None, limit: int = 300) -> list[dict[str, Any]]:
        logs = cls._resolve_logs_folder(project)
        if logs is None:
            return []

        path = logs / cls.FILE_NAME
        if not path.exists():
            return []

        safe_limit = max(1, min(int(limit), cls.MAX_READ_EVENTS))
        events: list[dict[str, Any]] = []
        with cls._lock:
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []

        for line in lines[-safe_limit:]:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(event, dict):
                events.append(event)
        events.reverse()
        return events

    @classmethod
    def clear(cls, *, project=None) -> None:
        logs = cls._resolve_logs_folder(project)
        if logs is None:
            return
        with cls._lock:
            for name in (cls.FILE_NAME, cls.TEXT_FILE_NAME):
                path = logs / name
                if path.exists():
                    path.unlink()
