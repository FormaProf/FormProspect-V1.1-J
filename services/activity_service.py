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

    Le service peut fonctionner de deux façons :

    1. Mode explicite :
       le contexte appelant connaît déjà la source des données et transmet
       ``is_cloud_mode``. C'est notamment le cas de ProspectDialog lorsqu'un
       prospect Cloud est ouvert depuis la vue globale Administrateur sans
       projet actif.

    2. Mode historique :
       si aucun mode explicite n'est fourni, DataSourceResolver détermine
       la source à partir du projet actuellement ouvert.

    CloudRuntime sert uniquement à fournir le client API lorsqu'une source
    Cloud a été explicitement déterminée.
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
        self.is_cloud_mode = is_cloud_mode

    def _is_cloud_project(self) -> bool:
        """
        Indique si les activités doivent utiliser la source Cloud.

        Lorsqu'un mode explicite a été transmis par l'appelant, celui-ci est
        prioritaire. Cela permet notamment d'ouvrir un prospect Cloud depuis
        la vue globale Administrateur même lorsqu'aucun projet n'est ouvert.

        En l'absence de mode explicite, le fonctionnement historique fondé
        sur DataSourceResolver est conservé.
        """

        if self.is_cloud_mode is not None:
            return self.is_cloud_mode

        return self.resolver.resolve().is_cloud

    def _cloud_api(self):
        """
        Retourne le client API utilisable pour une source Cloud.

        Un client peut être injecté pendant les tests. Dans l'application,
        CloudRuntime fournit le client correspondant à la session active.
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
        Retourne l'historique des activités depuis la source appropriée.
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
        Ajoute une activité dans la source appropriée.
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
