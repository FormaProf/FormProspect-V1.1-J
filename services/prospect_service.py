
from __future__ import annotations

from core.datasource_resolver import DataSourceResolver
from core.application_state import ApplicationState
from services.cloud_runtime import CloudRuntime
from services.prospect_data_provider import (
    CloudProspectDataProvider,
    LocalProspectDataProvider,
    ProspectDataProvider,
)
from services.scoring_service import ScoringService


class ProspectService:
    """
    Service métier du CRM prospects.

    La sélection de la source de données dépend du projet actif via
    DataSourceResolver. Le provider est conservé en mémoire afin de réutiliser
    les caches Cloud entre les compteurs, les filtres et la liste des prospects.
    """

    def __init__(
        self,
        database_path=None,
        *,
        resolver: DataSourceResolver | None = None,
        cloud_api_client=None,
    ):
        self.database_path = database_path
        self.resolver = resolver or DataSourceResolver()
        self.cloud_api_client = cloud_api_client
        self._last_total = 0

        self._provider_cache: ProspectDataProvider | None = None
        self._provider_cache_key = None

    @property
    def is_cloud(self) -> bool:
        """Cloud si un projet déployé est ouvert, ou si aucun projet local
        n'est ouvert mais qu'une session Cloud est active."""
        if ApplicationState.has_project():
            return self.resolver.is_cloud()
        return CloudRuntime.is_active()

    def get_repository(self, database_path=None):
        """
        Compatibilité avec les anciens appels directs au repository.

        Cette méthode ne doit être utilisée que pour le mode local.
        """

        provider = LocalProspectDataProvider(
            self._database_path(database_path)
        )
        return provider.repository

    def _database_path(self, database_path=None):
        db = database_path or self.database_path
        if db:
            return db

        if not ApplicationState.has_project():
            raise ValueError(
                "Aucun projet local actif : la base SQLite n'est pas disponible."
            )

        context = self.resolver.resolve()
        return context.project.database

    @staticmethod
    def _cloud_project_key(project):
        return str(
            getattr(project, "id", None)
            or getattr(project, "project_id", None)
            or getattr(project, "name", None)
            or id(project)
        )

    def _provider(self, database_path=None) -> ProspectDataProvider:
        # Un projet local ouvert reste LOCAL même avec une session Cloud.
        # Sans projet local, un commercial connecté travaille sur son CRM Cloud.
        cloud_project_id = None

        if ApplicationState.has_project():
            context = self.resolver.resolve()

            if not context.is_cloud:
                database = self._database_path(database_path)
                cache_key = ("local", str(database))

                if (
                    self._provider_cache is None
                    or self._provider_cache_key != cache_key
                    or not isinstance(
                        self._provider_cache,
                        LocalProspectDataProvider,
                    )
                ):
                    self._provider_cache = LocalProspectDataProvider(
                        database
                    )
                    self._provider_cache_key = cache_key

                return self._provider_cache

            cloud_project_id = context.project_id
            cache_key = (
                "cloud",
                str(context.project_id or self._cloud_project_key(context.project)),
                id(self.cloud_api_client)
                if self.cloud_api_client is not None
                else "runtime",
            )

        elif CloudRuntime.is_active():
            cache_key = (
                "cloud",
                "organization-session",
                id(self.cloud_api_client)
                if self.cloud_api_client is not None
                else "runtime",
            )

        else:
            raise RuntimeError(
                "Aucune source de données Form@Prospect n'est disponible."
            )

        if (
            self._provider_cache is None
            or self._provider_cache_key != cache_key
            or not isinstance(
                self._provider_cache,
                CloudProspectDataProvider,
            )
        ):
            self._provider_cache = CloudProspectDataProvider(
                self.cloud_api_client,
                project_id=cloud_project_id,
            )
            self._provider_cache_key = cache_key

        return self._provider_cache

    def invalider_caches(
        self,
        *,
        statistiques=True,
        filtres=True,
    ) -> None:
        """
        Invalide les données mises en mémoire sans recréer tout le service.

        Cette méthode est appelée lors d'un rafraîchissement manuel ou après
        une modification de fiche susceptible de changer les compteurs/filtres.
        """

        provider = self._provider()

        if statistiques and hasattr(
            provider,
            "_stats_cache",
        ):
            provider._stats_cache = None

        if filtres:
            if hasattr(
                provider,
                "_filter_options_cache",
            ):
                provider._filter_options_cache = None

            if hasattr(
                provider,
                "_owner_names_loaded",
            ):
                provider._owner_names_loaded = False

            if hasattr(
                provider,
                "_owner_name_by_id",
            ):
                provider._owner_name_by_id.clear()

            if hasattr(
                provider,
                "_owner_id_by_label",
            ):
                provider._owner_id_by_label.clear()

    def _remember_total(
        self,
        provider: ProspectDataProvider,
    ) -> None:
        self._last_total = getattr(
            provider,
            "last_total",
            self._last_total,
        )

    def compter_prospects(self, database_path=None):
        return self._provider(
            database_path
        ).count_all()

    def compter_telephones(self, database_path=None):
        return self._provider(
            database_path
        ).count_with_phone()

    def compter_emails(self, database_path=None):
        return self._provider(
            database_path
        ).count_with_email()

    def compter_sites(self, database_path=None):
        return self._provider(
            database_path
        ).count_with_website()

    def compter_prospects_filtres(
        self,
        database_path=None,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
    ):
        return self._provider(
            database_path
        ).count_filtered(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
        )

    def recuperer_prospects(
        self,
        database_path=None,
        limite=100,
    ):
        provider = self._provider(database_path)
        result = provider.get_all(limite)
        self._remember_total(provider)
        return result

    def rechercher_prospects(
        self,
        database_path,
        recherche,
        limite=100,
    ):
        provider = self._provider(database_path)
        result = provider.search(
            recherche,
            limite,
        )
        self._remember_total(provider)
        return result

    def rechercher_prospects_filtres(
        self,
        database_path=None,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
        limite=100,
        offset=0,
    ):
        provider = self._provider(database_path)
        result = provider.search_filtered(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
            limite=limite,
            offset=offset,
        )
        self._remember_total(provider)
        return result

    def recuperer_options_filtres(
        self,
        database_path=None,
    ):
        return self._provider(
            database_path
        ).get_filter_options()

    def recuperer_prospect_par_id(
        self,
        database_path,
        prospect_id,
    ):
        return self._provider(
            database_path
        ).get_by_id(prospect_id)

    def mettre_a_jour_pipeline(
        self,
        database_path,
        prospect_id,
        pipeline,
    ):
        if not pipeline or not str(pipeline).strip():
            raise ValueError(
                "Le pipeline ne peut pas être vide."
            )

        return self._provider(
            database_path
        ).update_pipeline(
            prospect_id,
            str(pipeline).strip(),
        )

    def mettre_a_jour_contact(
        self,
        database_path,
        prospect_id,
        telephone,
        site_web,
        email,
        facebook,
        linkedin,
        instagram,
        youtube,
        pipeline,
        priorite,
        prochaine_action,
        date_prochaine_action,
        commercial_assigne,
    ):
        return self._provider(
            database_path
        ).update_contact_infos(
            prospect_id,
            telephone,
            site_web,
            email,
            facebook,
            linkedin,
            instagram,
            youtube,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
        )

    def recalculer_scores(
        self,
        database_path=None,
        progress_callback=None,
    ):
        if self.resolver.is_cloud():
            raise RuntimeError(
                "Le scoring Cloud sera activé dans un lot dédié."
            )

        return ScoringService.score_all(
            self._database_path(database_path),
            progress_callback=progress_callback,
        )
