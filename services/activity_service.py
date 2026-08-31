from __future__ import annotations

from datetime import datetime

from core.datasource_resolver import DataSourceResolver
from repositories.activity_repository import ActivityRepository
from services.cloud_crm_mapping import (
    ACTION_TYPE_TO_API,
    display_datetime,
)
from services.cloud_runtime import CloudRuntime


class ActivityService:
    """
    Service métier chargé de l'historique des activités d'un prospect.

    La source des données dépend du projet actif et est déterminée par
    DataSourceResolver.

    CloudRuntime ne sert qu'à fournir le client API lorsque le projet
    actif est réellement déployé dans le Cloud.
    """

    def __init__(
        self,
        *,
        resolver: DataSourceResolver | None = None,
        cloud_api_client=None,
        is_cloud_mode: bool | None = None,
    ) -> None:
        self.resolver = resolver or DataSourceResolver()
        self.cloud_api_client = cloud_api_client
        # Le CRM Cloud global n'implique pas qu'un projet Cloud précis soit
        # ouvert. Le mode peut donc être injecté explicitement par l'écran.
        self._is_cloud_mode_override = (
            None if is_cloud_mode is None else bool(is_cloud_mode)
        )

    def _is_cloud_project(self) -> bool:
        """
        Indique si le projet actif utilise la source Cloud.
        """

        if self._is_cloud_mode_override is not None:
            return self._is_cloud_mode_override

        return self.resolver.resolve().is_cloud

    def _cloud_api(self):
        """
        Retourne le client API associé à la session Cloud active.
        """

        return self.cloud_api_client or CloudRuntime.api()

    @staticmethod
    def _local_repository(database_path) -> ActivityRepository:
        if not database_path:
            raise ValueError(
                "Aucune base de données locale n'est sélectionnée."
            )

        return ActivityRepository(database_path)

    def get_activities(self, database_path, prospect_id):
        """
        Retourne l'historique des activités depuis la source du projet actif.
        """

        if self._is_cloud_project():
            items = self._cloud_api().list_activities(str(prospect_id))

            return [
                (
                    item.get("id"),
                    display_datetime(item.get("created_at")),
                    item.get("activity_type", "note"),
                    item.get("description")
                    or item.get("subject", ""),
                )
                for item in items
            ]

        repository = self._local_repository(database_path)
        return repository.get_activities(prospect_id)

    def add_activity(
        self,
        database_path,
        prospect_id,
        type_action,
        description,
    ):
        """
        Ajoute une activité dans la source du projet actif.
        """

        type_action_normalise = str(type_action or "Activité").strip()
        description_normalisee = str(description or "").strip()

        if self._is_cloud_project():
            activity_type = ACTION_TYPE_TO_API.get(
                type_action_normalise,
                "note",
            )

            status = (
                "completed"
                if activity_type == "note"
                else "planned"
            )

            return self._cloud_api().create_activity(
                str(prospect_id),
                {
                    "activity_type": activity_type,
                    "subject": type_action_normalise[:200],
                    "description": description_normalisee,
                    "status": status,
                    "priority": "normal",
                    "scheduled_at": None,
                },
            )

        repository = self._local_repository(database_path)

        return repository.add_activity(
            prospect_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            type_action_normalise,
            description_normalisee,
        )