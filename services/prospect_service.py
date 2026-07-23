from __future__ import annotations

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
from services.scoring_service import ScoringService


class ProspectService:
    """CRM service with Cloud-first behaviour and a local SQLite fallback."""

    def __init__(self, database_path=None):
        self.database_path = database_path
        self._last_total = 0

    @property
    def is_cloud(self) -> bool:
        return CloudRuntime.is_active()

    def get_repository(self, database_path=None):
        db = database_path or self.database_path
        if not db:
            raise ValueError("Aucune base de données sélectionnée.")
        return ProspectRepository(db)

    @staticmethod
    def _row(item: dict, *, detailed: bool = False):
        base = (
            item.get("id"), item.get("company_name", ""), item.get("city", ""),
            item.get("postal_code", ""), item.get("phone", ""), item.get("website", ""),
            item.get("email", ""), pipeline_to_ui(item.get("pipeline_stage", "nouveau")),
            priority_to_ui(item.get("priority", "normal")), item.get("next_action", "") or "Aucune",
            display_datetime(item.get("next_action_at")), item.get("owner_user_id", ""),
            0, "★☆☆☆☆", "Score Cloud à venir",
        )
        if not detailed:
            return base
        # Legacy ProspectDialog expects the historic 30-column tuple.
        return (
            item.get("id"), item.get("company_name", ""), item.get("siret", ""), item.get("siren", ""),
            item.get("address", ""), item.get("postal_code", ""), item.get("city", ""),
            item.get("naf_code", ""), item.get("phone", ""), item.get("website", ""),
            item.get("email", ""), "", "", "", "",
            item.get("status", "active"), display_datetime(item.get("created_at")),
            pipeline_to_ui(item.get("pipeline_stage", "nouveau")), priority_to_ui(item.get("priority", "normal")),
            item.get("next_action", "") or "Aucune", display_datetime(item.get("next_action_at")),
            item.get("owner_user_id", ""), 0, "★☆☆☆☆", "Score Cloud à venir", "[]", "",
        )

    def _cloud_list(self, *, recherche="", pipeline="", priorite="", ville="", limite=100, offset=0):
        page = CloudRuntime.api().list_prospects(
            search=recherche,
            pipeline_stage=pipeline_to_api(pipeline) if pipeline else None,
            priority=priority_to_api(priorite) if priorite else None,
            city=ville,
            limit=limite,
            offset=offset,
        )
        self._last_total = page.total
        return [self._row(item) for item in page.items]

    def compter_prospects(self, database_path=None):
        if self.is_cloud:
            return CloudRuntime.api().list_prospects(limit=1, offset=0).total
        return self.get_repository(database_path).count_all()

    def compter_telephones(self, database_path=None):
        if self.is_cloud:
            return sum(1 for row in self._cloud_list(limite=500) if row[4])
        return self.get_repository(database_path).count_with_phone()

    def compter_emails(self, database_path=None):
        if self.is_cloud:
            return sum(1 for row in self._cloud_list(limite=500) if row[6])
        return self.get_repository(database_path).count_with_email()

    def compter_sites(self, database_path=None):
        if self.is_cloud:
            return sum(1 for row in self._cloud_list(limite=500) if row[5])
        return self.get_repository(database_path).count_with_website()

    def compter_prospects_filtres(self, database_path=None, recherche="", pipeline="", priorite="", commercial="", ville=""):
        if self.is_cloud:
            page = CloudRuntime.api().list_prospects(
                search=recherche,
                pipeline_stage=pipeline_to_api(pipeline) if pipeline else None,
                priority=priority_to_api(priorite) if priorite else None,
                city=ville,
                owner_user_id=commercial or None,
                limit=1,
                offset=0,
            )
            return page.total
        return self.get_repository(database_path).count_filtered(
            recherche=recherche, pipeline=pipeline, priorite=priorite, commercial=commercial, ville=ville,
        )

    def recuperer_prospects(self, database_path=None, limite=100):
        if self.is_cloud:
            return self._cloud_list(limite=limite)
        return self.get_repository(database_path).get_all(limite)

    def rechercher_prospects(self, database_path, recherche, limite=100):
        if self.is_cloud:
            return self._cloud_list(recherche=recherche, limite=limite)
        return self.get_repository(database_path).search(recherche, limite)

    def rechercher_prospects_filtres(self, database_path=None, recherche="", pipeline="", priorite="", commercial="", ville="", limite=100, offset=0):
        if self.is_cloud:
            page = CloudRuntime.api().list_prospects(
                search=recherche,
                pipeline_stage=pipeline_to_api(pipeline) if pipeline else None,
                priority=priority_to_api(priorite) if priorite else None,
                city=ville,
                owner_user_id=commercial or None,
                limit=limite,
                offset=offset,
            )
            self._last_total = page.total
            return [self._row(item) for item in page.items]
        return self.get_repository(database_path).search_filtered(
            recherche=recherche, pipeline=pipeline, priorite=priorite, commercial=commercial,
            ville=ville, limite=limite, offset=offset,
        )

    def recuperer_options_filtres(self, database_path=None):
        if self.is_cloud:
            rows = self._cloud_list(limite=500)
            return {
                "pipelines": sorted({row[7] for row in rows if row[7]}),
                "priorites": sorted({row[8] for row in rows if row[8]}),
                "commerciaux": sorted({str(row[11]) for row in rows if row[11]}),
                "villes": sorted({row[2] for row in rows if row[2]}),
            }
        return self.get_repository(database_path).get_filter_options()

    def recuperer_prospect_par_id(self, database_path, prospect_id):
        if self.is_cloud:
            return self._row(CloudRuntime.api().get_prospect(str(prospect_id)), detailed=True)
        return self.get_repository(database_path).get_by_id(prospect_id)

    def mettre_a_jour_pipeline(self, database_path, prospect_id, pipeline):
        if not pipeline or not str(pipeline).strip():
            raise ValueError("Le pipeline ne peut pas être vide.")
        if self.is_cloud:
            CloudRuntime.api().change_stage(str(prospect_id), pipeline_to_api(pipeline))
            return True
        return self.get_repository(database_path).update_pipeline(prospect_id, str(pipeline).strip())

    def mettre_a_jour_contact(self, database_path, prospect_id, telephone, site_web, email, facebook, linkedin,
                              instagram, youtube, pipeline, priorite, prochaine_action, date_prochaine_action,
                              commercial_assigne):
        if self.is_cloud:
            current = CloudRuntime.api().get_prospect(str(prospect_id))
            payload = {
                "phone": telephone,
                "website": site_web,
                "email": email,
                "priority": priority_to_api(priorite),
                "next_action": "" if prochaine_action == "Aucune" else prochaine_action,
                "next_action_at": parse_datetime(date_prochaine_action),
            }
            if commercial_assigne and commercial_assigne != str(current.get("owner_user_id", "")):
                payload["owner_user_id"] = commercial_assigne
            CloudRuntime.api().update_prospect(str(prospect_id), payload)
            if pipeline_to_api(pipeline) != current.get("pipeline_stage"):
                CloudRuntime.api().change_stage(str(prospect_id), pipeline_to_api(pipeline))
            return True
        return self.get_repository(database_path).update_contact_infos(
            prospect_id, telephone, site_web, email, facebook, linkedin, instagram, youtube,
            pipeline, priorite, prochaine_action, date_prochaine_action, commercial_assigne,
        )

    def recalculer_scores(self, database_path=None, progress_callback=None):
        if self.is_cloud:
            raise RuntimeError("Le scoring Cloud sera activé dans un lot dédié.")
        return ScoringService.score_all(database_path, progress_callback=progress_callback)
