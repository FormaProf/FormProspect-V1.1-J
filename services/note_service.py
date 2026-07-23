from __future__ import annotations

from datetime import datetime

from repositories.note_repository import NoteRepository
from services.cloud_crm_mapping import display_datetime
from services.cloud_runtime import CloudRuntime


class NoteService:
    def get_notes(self, database_path, prospect_id):
        if CloudRuntime.is_active():
            items = CloudRuntime.api().list_activities(str(prospect_id))
            notes = [item for item in items if item.get("activity_type") == "note"]
            return [
                (item.get("id"), display_datetime(item.get("created_at")), item.get("description") or item.get("subject", ""))
                for item in notes
            ]
        return NoteRepository(database_path).get_notes(prospect_id)

    def add_note(self, database_path, prospect_id, contenu):
        if CloudRuntime.is_active():
            return CloudRuntime.api().create_activity(
                str(prospect_id),
                {
                    "activity_type": "note",
                    "subject": "Note CRM",
                    "description": str(contenu or ""),
                    "status": "completed",
                    "priority": "normal",
                    "scheduled_at": None,
                },
            )
        repo = NoteRepository(database_path)
        repo.add_note(prospect_id, datetime.now().strftime("%d/%m/%Y %H:%M"), contenu)
