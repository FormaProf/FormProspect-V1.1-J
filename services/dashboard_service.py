from __future__ import annotations

from core.datasource_resolver import DataSourceResolver
from services.dashboard_data_provider import (
    CloudDashboardDataProvider,
    DashboardDataProvider,
    LocalDashboardDataProvider,
)


class DashboardService:
    """
    Service métier du Dashboard Form@Prospect.

    La source de données est sélectionnée automatiquement selon
    l'espace de travail actif :

    - projet local : base SQLite ;
    - projet Cloud : API Form@Prospect Cloud.
    """

    def __init__(
        self,
        database_path=None,
        *,
        resolver: DataSourceResolver | None = None,
        cloud_api_client=None,
    ) -> None:
        self.database_path = database_path
        self.resolver = resolver or DataSourceResolver()
        self.cloud_api_client = cloud_api_client

    @property
    def is_cloud(self) -> bool:
        """Indique si le workspace actif utilise les données Cloud."""

        return self.resolver.is_cloud()

    def _database_path(self, database_path=None):
        """
        Résout le chemin de la base SQLite du projet local actif.

        Cette méthode ne doit être appelée que pour un projet local.
        """

        db = database_path or self.database_path

        if db:
            return db

        context = self.resolver.resolve()
        project = context.project

        database = getattr(project, "database", None)

        if not database:
            raise ValueError(
                "Le projet local actif ne possède aucune base "
                "de données SQLite valide."
            )

        return database

    def _provider(
        self,
        database_path=None,
    ) -> DashboardDataProvider:
        """
        Retourne le provider adapté à la source de données active.
        """

        context = self.resolver.resolve()

        if context.is_cloud:
            return CloudDashboardDataProvider(
                api_client=self.cloud_api_client,
                project_id=context.project_id,
            )

        return LocalDashboardDataProvider(
            self._database_path(database_path)
        )

    def get_repository(self, database_path=None):
        """
        Compatibilité temporaire avec les anciens appels directs
        au DashboardRepository.

        Cette méthode est disponible uniquement en mode local.
        """

        provider = self._provider(database_path)

        if not isinstance(
            provider,
            LocalDashboardDataProvider,
        ):
            raise RuntimeError(
                "DashboardRepository n'est pas disponible "
                "pour un projet Cloud."
            )

        return provider.repository

    def get_dashboard_data(
        self,
        database_path=None,
    ) -> dict:
        """
        Retourne toutes les données nécessaires à l'affichage
        du Dashboard, quelle que soit leur provenance.
        """

        provider = self._provider(database_path)
        return provider.get_dashboard_data()