from __future__ import annotations

from datetime import datetime

from core.datasource_resolver import DataSourceResolver
from repositories.note_repository import NoteRepository
from services.cloud_crm_mapping import display_datetime
from services.cloud_runtime import CloudRuntime


class NoteService:
    """
    Service métier chargé des notes liées aux prospects.

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
        Indique si les notes doivent utiliser la source Cloud.

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
    def _local_repository(database_path) -> NoteRepository:
        if not database_path:
            raise ValueError(
                "Aucune base de données locale n'est sélectionnée."
            )

        return NoteRepository(database_path)

    def get_notes(self, database_path, prospect_id):
        """
        Retourne les notes du prospect depuis la source appropriée.
        """

        if self._is_cloud_project():
            items = self._cloud_api().list_activities(str(prospect_id))

            notes = [
                item
                for item in items
                if item.get("activity_type") == "note"
            ]

            return [
                (
                    item.get("id"),
                    display_datetime(item.get("created_at")),
                    item.get("description")
                    or item.get("subject", ""),
                )
                for item in notes
            ]

        repository = self._local_repository(database_path)
        return repository.get_notes(prospect_id)

    def add_note(self, database_path, prospect_id, contenu):
        """
        Ajoute une note dans la source appropriée.
        """

        contenu_normalise = str(contenu or "").strip()

        if not contenu_normalise:
            raise ValueError("Le contenu de la note ne peut pas être vide.")

        if self._is_cloud_project():
            return self._cloud_api().create_activity(
                str(prospect_id),
                {
                    "activity_type": "note",
                    "subject": "Note CRM",
                    "description": contenu_normalise,
                    "status": "completed",
                    "priority": "normal",
                    "scheduled_at": None,
                },
            )

        repository = self._local_repository(database_path)

        return repository.add_note(
            prospect_id,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            contenu_normalise,
        )
