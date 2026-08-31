from __future__ import annotations

from datetime import datetime

from core.datasource_resolver import DataSourceResolver
from repositories.note_repository import NoteRepository
from services.cloud_crm_mapping import display_datetime
from services.cloud_runtime import CloudRuntime


class NoteService:
    """
    Service métier chargé des notes liées aux prospects.

    La source des données est déterminée par DataSourceResolver à partir
    du projet actuellement ouvert.

    CloudRuntime sert uniquement à fournir le client API lorsqu'un projet
    est réellement configuré en mode Cloud.
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
        # Un écran CRM Cloud global peut être utilisé sans projet/workspace
        # actuellement ouvert. Dans ce cas le contexte de l'écran est plus
        # fiable que DataSourceResolver, qui exige un projet actif.
        self._is_cloud_mode_override = (
            None if is_cloud_mode is None else bool(is_cloud_mode)
        )

    def _is_cloud_project(self) -> bool:
        """
        Indique si le projet actif utilise la source de données Cloud.

        La présence d'une session Cloud ne décide jamais de la source
        de données.
        """

        if self._is_cloud_mode_override is not None:
            return self._is_cloud_mode_override

        return self.resolver.resolve().is_cloud

    def _cloud_api(self):
        """
        Retourne le client API utilisable pour un projet Cloud.

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
        Retourne les notes du prospect depuis la source du projet actif.
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
        Ajoute une note dans la source du projet actif.
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