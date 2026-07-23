from __future__ import annotations

from datetime import datetime

from repositories.activity_repository import ActivityRepository
from services.cloud_crm_mapping import ACTION_TYPE_TO_API, display_datetime
from services.cloud_runtime import CloudRuntime


class ActivityService:
    def get_activities(self, database_path, prospect_id):
        if CloudRuntime.is_active():
            items = CloudRuntime.api().list_activities(str(prospect_id))
            return [
                (
                    item.get("id"),
                    display_datetime(item.get("created_at")),
                    item.get("activity_type", "note"),
                    item.get("description") or item.get("subject", ""),
                )
                for item in items
            ]
        return ActivityRepository(database_path).get_activities(prospect_id)

    def add_activity(self, database_path, prospect_id, type_action, description):
        if CloudRuntime.is_active():
            activity_type = ACTION_TYPE_TO_API.get(type_action, "note")
            status = "completed" if activity_type == "note" else "planned"
            return CloudRuntime.api().create_activity(
                str(prospect_id),
                {
                    "activity_type": activity_type,
                    "subject": str(type_action or "Activité")[:200],
                    "description": str(description or ""),
                    "status": status,
                    "priority": "normal",
                    "scheduled_at": None,
                },
            )
        repo = ActivityRepository(database_path)
        repo.add_activity(
            prospect_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            type_action,
            description,
        )
