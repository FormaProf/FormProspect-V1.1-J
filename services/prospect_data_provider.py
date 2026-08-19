from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from repositories.prospect_repository import ProspectRepository
from services.cloud_crm_mapping import (
    display_datetime,
    pipeline_to_api,
    pipeline_to_ui,
    priority_to_api,
    priority_to_ui,
    parse_datetime,
)
from services.cloud_runtime import CloudRuntime
from core.session import SessionState


class ProspectDataProvider(ABC):
    """Contrat commun des sources de données utilisées par ProspectService."""

    @abstractmethod
    def count_all(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_with_phone(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_with_email(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_with_website(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_filtered(
        self,
        *,
        recherche: str = "",
        pipeline: str = "",
        priorite: str = "",
        commercial: str = "",
        ville: str = "",
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_all(self, limite: int = 100):
        raise NotImplementedError

    @abstractmethod
    def search(self, recherche: str, limite: int = 100):
        raise NotImplementedError

    @abstractmethod
    def search_filtered(
        self,
        *,
        recherche: str = "",
        pipeline: str = "",
        priorite: str = "",
        commercial: str = "",
        ville: str = "",
        limite: int = 100,
        offset: int = 0,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_filter_options(self) -> dict[str, list[Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, prospect_id):
        raise NotImplementedError

    @abstractmethod
    def update_pipeline(self, prospect_id, pipeline: str):
        raise NotImplementedError

    @abstractmethod
    def update_contact_infos(
        self,
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
        raise NotImplementedError


class LocalProspectDataProvider(ProspectDataProvider):
    """Adaptateur du repository SQLite historique."""

    def __init__(self, database_path) -> None:
        if not database_path:
            raise ValueError("Aucune base de données sélectionnée.")
        self.repository = ProspectRepository(database_path)

    def count_all(self) -> int:
        return self.repository.count_all()

    def count_with_phone(self) -> int:
        return self.repository.count_with_phone()

    def count_with_email(self) -> int:
        return self.repository.count_with_email()

    def count_with_website(self) -> int:
        return self.repository.count_with_website()

    def count_filtered(
        self,
        *,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
    ) -> int:
        return self.repository.count_filtered(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
        )

    def get_all(self, limite=100):
        return self.repository.get_all(limite)

    def search(self, recherche, limite=100):
        return self.repository.search(recherche, limite)

    def search_filtered(
        self,
        *,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
        limite=100,
        offset=0,
    ):
        return self.repository.search_filtered(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
            limite=limite,
            offset=offset,
        )

    def get_filter_options(self) -> dict[str, list[Any]]:
        return self.repository.get_filter_options()

    def get_by_id(self, prospect_id):
        return self.repository.get_by_id(prospect_id)

    def update_pipeline(self, prospect_id, pipeline):
        return self.repository.update_pipeline(prospect_id, pipeline)

    def update_contact_infos(
        self,
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
        return self.repository.update_contact_infos(
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


class CloudProspectDataProvider(ProspectDataProvider):
    """Adaptateur du client HTTP Form@Prospect Cloud."""

    def __init__(
        self,
        api_client=None,
        *,
        project_id: str | None = None,
    ) -> None:
        self.api_client = api_client or CloudRuntime.api()
        self.project_id = str(project_id or "").strip() or None
        self.last_total = 0

        # Correspondance UUID Cloud -> nom lisible du commercial.
        self._owner_names_loaded = False
        self._owner_name_by_id: dict[str, str] = {}
        self._owner_id_by_label: dict[str, str] = {}

        # Les options sont chargées une seule fois par instance du provider.
        self._filter_options_cache: dict[str, list[Any]] | None = None

    @staticmethod
    def _object_value(item: Any, *names: str):
        """Lit une valeur dans un dictionnaire ou un objet métier."""

        if item is None:
            return None

        for name in names:
            if isinstance(item, dict):
                value = item.get(name)
            else:
                value = getattr(item, name, None)

            if value not in (None, ""):
                return value

        return None

    @classmethod
    def _user_identity(cls, item: Any) -> tuple[str, str, str]:
        """
        Retourne (user_id, display_name, email) pour les différentes formes
        de réponses possibles de l'API utilisateurs/membres.
        """

        nested_user = cls._object_value(item, "user", "profile")
        source = nested_user or item

        user_id = cls._object_value(
            item,
            "user_id",
            "cloud_user_id",
            "id",
        ) or cls._object_value(
            source,
            "user_id",
            "cloud_user_id",
            "id",
        )

        display_name = cls._object_value(
            item,
            "display_name",
            "full_name",
            "name",
        ) or cls._object_value(
            source,
            "display_name",
            "full_name",
            "name",
        )

        email = cls._object_value(
            item,
            "email",
        ) or cls._object_value(
            source,
            "email",
        )

        return (
            str(user_id or "").strip(),
            str(display_name or "").strip(),
            str(email or "").strip(),
        )

    def _register_owner(
        self,
        user_id: Any,
        display_name: Any = "",
        email: Any = "",
    ) -> None:
        user_id_text = str(user_id or "").strip()

        if not user_id_text:
            return

        display_text = str(display_name or "").strip()
        email_text = str(email or "").strip()

        label = display_text or email_text or user_id_text

        # Si deux membres ont le même nom, l'email rend le libellé unique.
        existing_id = self._owner_id_by_label.get(label)
        if existing_id and existing_id != user_id_text and email_text:
            label = f"{label} ({email_text})"

        self._owner_name_by_id[user_id_text] = label
        self._owner_id_by_label[label] = user_id_text

    @staticmethod
    def _response_items(response: Any) -> list[Any]:
        if response is None:
            return []

        if isinstance(response, dict):
            items = (
                response.get("items")
                or response.get("users")
                or response.get("members")
                or []
            )
            return list(items)

        items = getattr(response, "items", None)
        if items is not None and not callable(items):
            return list(items)

        if isinstance(response, (list, tuple, set)):
            return list(response)

        return []

    def _register_current_user(self) -> None:
        """Ajoute l'utilisateur connecté au cache des commerciaux."""

        current_user = SessionState.user()

        if current_user is None:
            return

        current_id = (
            getattr(current_user, "cloud_user_id", None)
            or getattr(current_user, "user_id", None)
            or getattr(current_user, "id", None)
        )
        current_name = (
            getattr(current_user, "display_name", None)
            or getattr(current_user, "full_name", None)
            or getattr(current_user, "name", None)
        )
        current_email = getattr(
            current_user,
            "email",
            None,
        )

        self._register_owner(
            current_id,
            current_name,
            current_email,
        )

    def _cache_filter_options(
        self,
        payload: dict,
    ) -> dict[str, list[Any]]:
        """
        Convertit la réponse Cloud vers les libellés attendus par
        l'interface historique et enregistre les commerciaux.
        """

        self._register_current_user()

        owners = payload.get("owners") or []

        for item in owners:
            user_id, display_name, email = self._user_identity(item)
            self._register_owner(
                user_id,
                display_name,
                email,
            )

        pipelines = sorted(
            {
                pipeline_to_ui(str(value))
                for value in payload.get("pipelines", [])
                if str(value or "").strip()
            }
        )
        priorities = sorted(
            {
                priority_to_ui(str(value))
                for value in payload.get("priorities", [])
                if str(value or "").strip()
            }
        )
        cities = sorted(
            {
                str(value).strip()
                for value in payload.get("cities", [])
                if str(value or "").strip()
            }
        )
        commercials = sorted(
            {
                self._owner_name_by_id.get(
                    str(item.get("id", "")).strip(),
                    (
                        str(item.get("display_name", "")).strip()
                        or str(item.get("email", "")).strip()
                        or str(item.get("id", "")).strip()
                    ),
                )
                for item in owners
                if str(item.get("id", "")).strip()
            }
        )

        self._filter_options_cache = {
            "pipelines": pipelines,
            "priorites": priorities,
            "commerciaux": commercials,
            "villes": cities,
        }
        self._owner_names_loaded = True

        return self._filter_options_cache

    def _load_filter_options(
        self,
    ) -> dict[str, list[Any]]:
        if self._filter_options_cache is not None:
            return self._filter_options_cache

        payload = (
            self.api_client.get_prospect_filter_options(
                project_id=self.project_id
            )
        )

        return self._cache_filter_options(payload)

    def _load_owner_names(self) -> None:
        if self._owner_names_loaded:
            return

        self._register_current_user()

        # Le nouvel endpoint fournit directement les commerciaux visibles.
        try:
            self._load_filter_options()
            return
        except Exception:
            pass

        # Compatibilité de secours si le backend n'est pas encore à jour.
        try:
            try:
                response = self.api_client.list_users(
                    active_only=True,
                )
            except TypeError:
                response = self.api_client.list_users()

            for item in self._response_items(response):
                user_id, display_name, email = self._user_identity(item)
                self._register_owner(
                    user_id,
                    display_name,
                    email,
                )

        except Exception:
            pass

        self._owner_names_loaded = True

    def _owner_display_name(self, owner_user_id: Any) -> str:
        owner_id = str(owner_user_id or "").strip()

        if not owner_id:
            return "Non assigné"

        self._load_owner_names()
        return self._owner_name_by_id.get(owner_id, owner_id)

    def _owner_id(self, owner_value: Any) -> str:
        """
        Transforme un nom affiché en UUID avant un filtre ou une mise à jour.
        Une valeur déjà sous forme d'UUID est conservée.
        """

        value = str(owner_value or "").strip()

        if not value:
            return ""

        self._load_owner_names()
        return self._owner_id_by_label.get(value, value)

    def _row(self, item: dict, *, detailed: bool = False):
        owner_display_name = self._owner_display_name(
            item.get("owner_user_id")
        )

        base = (
            item.get("id"),
            item.get("company_name", ""),
            item.get("city", ""),
            item.get("postal_code", ""),
            item.get("phone", ""),
            item.get("website", ""),
            item.get("email", ""),
            pipeline_to_ui(item.get("pipeline_stage", "nouveau")),
            priority_to_ui(item.get("priority", "normal")),
            item.get("next_action", "") or "Aucune",
            display_datetime(item.get("next_action_at")),
            owner_display_name,
            0,
            "★☆☆☆☆",
            "Score Cloud à venir",
            item.get("mobile", ""),
        )

        if not detailed:
            return base

        return (
            item.get("id"),
            item.get("company_name", ""),
            item.get("siret", ""),
            item.get("siren", ""),
            item.get("address", ""),
            item.get("postal_code", ""),
            item.get("city", ""),
            item.get("naf_code", ""),
            item.get("phone", ""),
            item.get("website", ""),
            item.get("email", ""),
            item.get("facebook", ""),
            item.get("linkedin", ""),
            item.get("instagram", ""),
            item.get("youtube", ""),
            item.get("twitter", ""),
            item.get("social_other_urls", ""),
            item.get("status", "active"),
            display_datetime(item.get("created_at")),
            pipeline_to_ui(item.get("pipeline_stage", "nouveau")),
            priority_to_ui(item.get("priority", "normal")),
            item.get("next_action", "") or "Aucune",
            display_datetime(item.get("next_action_at")),
            owner_display_name,
            0,
            "★☆☆☆☆",
            "Score Cloud à venir",
            "[]",
            "",
        )

    def _list(
        self,
        *,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
        limite=100,
        offset=0,
    ):
        page = self.api_client.list_prospects(
            search=recherche,
            pipeline_stage=pipeline_to_api(pipeline) if pipeline else None,
            priority=priority_to_api(priorite) if priorite else None,
            city=ville,
            owner_user_id=self._owner_id(commercial) or None,
            project_id=self.project_id,
            limit=limite,
            offset=offset,
        )
        self.last_total = page.total
        return [self._row(item) for item in page.items]

    def count_all(self) -> int:
        return self.api_client.list_prospects(
            project_id=self.project_id,
            limit=1,
            offset=0,
        ).total

    def count_with_phone(self) -> int:
        return sum(1 for row in self._list(limite=500) if row[4])

    def count_with_email(self) -> int:
        return sum(1 for row in self._list(limite=500) if row[6])

    def count_with_website(self) -> int:
        return sum(1 for row in self._list(limite=500) if row[5])

    def count_filtered(
        self,
        *,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
    ) -> int:
        page = self.api_client.list_prospects(
            search=recherche,
            pipeline_stage=pipeline_to_api(pipeline) if pipeline else None,
            priority=priority_to_api(priorite) if priorite else None,
            city=ville,
            owner_user_id=self._owner_id(commercial) or None,
            project_id=self.project_id,
            limit=1,
            offset=0,
        )
        return page.total

    def get_all(self, limite=100):
        return self._list(limite=limite)

    def search(self, recherche, limite=100):
        return self._list(recherche=recherche, limite=limite)

    def search_filtered(
        self,
        *,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
        limite=100,
        offset=0,
    ):
        return self._list(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
            limite=limite,
            offset=offset,
        )

    def get_filter_options(self) -> dict[str, list[Any]]:
        """
        Utilise l'endpoint SQL distinct du backend.

        En cas d'ancien backend ou d'indisponibilité temporaire, la méthode
        historique reste disponible comme solution de secours.
        """

        try:
            cached = self._load_filter_options()
            return {
                key: list(values)
                for key, values in cached.items()
            }
        except Exception:
            rows = self._list(limite=500)
            return {
                "pipelines": sorted(
                    {row[7] for row in rows if row[7]}
                ),
                "priorites": sorted(
                    {row[8] for row in rows if row[8]}
                ),
                "commerciaux": sorted(
                    {
                        str(row[11])
                        for row in rows
                        if row[11]
                    }
                ),
                "villes": sorted(
                    {row[2] for row in rows if row[2]}
                ),
            }

    def get_by_id(self, prospect_id):
        return self._row(
            self.api_client.get_prospect(str(prospect_id)),
            detailed=True,
        )

    def update_pipeline(self, prospect_id, pipeline):
        self.api_client.change_stage(
            str(prospect_id),
            pipeline_to_api(pipeline),
        )
        return True

    def update_contact_infos(
        self,
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
        current = self.api_client.get_prospect(str(prospect_id))
        payload = {
            "phone": telephone,
            "website": site_web,
            "email": email,
            "facebook": facebook,
            "linkedin": linkedin,
            "instagram": instagram,
            "youtube": youtube,
            "priority": priority_to_api(priorite),
            "next_action": (
                "" if prochaine_action == "Aucune" else prochaine_action
            ),
            "next_action_at": parse_datetime(date_prochaine_action),
        }

        owner_user_id = self._owner_id(commercial_assigne)

        if (
            owner_user_id
            and owner_user_id
            != str(current.get("owner_user_id", ""))
        ):
            payload["owner_user_id"] = owner_user_id

        self.api_client.update_prospect(str(prospect_id), payload)

        if pipeline_to_api(pipeline) != current.get("pipeline_stage"):
            self.api_client.change_stage(
                str(prospect_id),
                pipeline_to_api(pipeline),
            )

        return True
