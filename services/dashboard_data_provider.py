from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any

from repositories.dashboard_repository import DashboardRepository
from services.cloud_crm_mapping import pipeline_to_ui, priority_to_ui
from services.cloud_runtime import CloudRuntime


class DashboardDataProvider(ABC):
    """
    Contrat commun des sources de données du Dashboard.

    Chaque provider doit produire exactement la même structure,
    que les données proviennent de SQLite ou de Form@Prospect Cloud.
    """

    @abstractmethod
    def get_dashboard_data(self) -> dict[str, Any]:
        raise NotImplementedError


class LocalDashboardDataProvider(DashboardDataProvider):
    """Provider du Dashboard pour les projets locaux SQLite."""

    QUALITY_FIELDS = (
        "telephone",
        "email",
        "site_web",
        "linkedin",
    )

    def __init__(self, database_path) -> None:
        if not database_path:
            raise ValueError("Aucune base de données locale sélectionnée.")

        self.repository = DashboardRepository(database_path)

    @staticmethod
    def _percentage(value: int, total: int) -> int:
        if not total:
            return 0

        return round((value / total) * 100)

    def get_dashboard_data(self) -> dict[str, Any]:
        repo = self.repository
        total = repo.count_all_prospects()

        counts = {
            "telephone": repo.count_not_empty("telephone"),
            "email": repo.count_not_empty("email"),
            "site_web": repo.count_not_empty("site_web"),
            "facebook": repo.count_not_empty("facebook"),
            "linkedin": repo.count_not_empty("linkedin"),
            "instagram": repo.count_not_empty("instagram"),
        }

        quality = {
            key: {
                "value": counts[key],
                "missing": max(0, total - counts[key]),
                "percentage": self._percentage(counts[key], total),
            }
            for key in self.QUALITY_FIELDS
        }

        quality_score = (
            round(
                sum(
                    item["percentage"]
                    for item in quality.values()
                )
                / len(quality)
            )
            if quality
            else 0
        )

        enriched = repo.count_enriched()
        enrichment_errors = repo.count_enrichment_errors()
        remaining = max(0, total - enriched)

        return {
            "kpi": {
                "prospects": total,
                "telephones": counts["telephone"],
                "emails": counts["email"],
                "sites": counts["site_web"],
                "quality_score": quality_score,
                "average_prospect_score": (
                    repo.average_prospect_score()
                ),
            },
            "pipeline": {
                name: count
                for name, count in repo.count_by_pipeline()
            },
            "scoring": {
                name: count
                for name, count in repo.count_by_score_grade()
            },
            "quality": quality,
            "contact_distribution": [
                ("Téléphones", counts["telephone"]),
                ("Emails", counts["email"]),
                ("Sites", counts["site_web"]),
                ("LinkedIn", counts["linkedin"]),
                ("Facebook", counts["facebook"]),
                ("Instagram", counts["instagram"]),
            ],
            "enrichment": {
                "enriched": enriched,
                "no_reliable_result": no_reliable_result,
                "treated": treated,
                "remaining": remaining,
                "errors": enrichment_errors,
                "percentage": self._percentage(
                    treated,
                    total,
                ),
            },
            "activity": {
                "actions_today": repo.count_actions_today(),
                "actions_next_7_days": (
                    repo.count_actions_next_7_days()
                ),
                "actions_overdue": (
                    repo.count_actions_overdue()
                ),
                "high_priority": (
                    repo.count_high_priority()
                ),
                "missing_phone": max(
                    0,
                    total - counts["telephone"],
                ),
                "missing_email": max(
                    0,
                    total - counts["email"],
                ),
            },
        }


class CloudDashboardDataProvider(DashboardDataProvider):
    """
    Provider du Dashboard pour un projet Form@Prospect Cloud.

    Les calculs sont effectués à partir des prospects visibles par
    l'utilisateur connecté. Les règles d'accès restent donc appliquées
    par le backend Cloud.
    """

    QUALITY_FIELDS = (
        "telephone",
        "email",
        "site_web",
        "linkedin",
    )

    PAGE_SIZE = 500

    def __init__(
        self,
        api_client=None,
        project_id: str | None = None,
    ) -> None:
        self.api_client = api_client or CloudRuntime.api()
        self.project_id = (
            str(project_id).strip()
            if project_id
            else None
        )

    @staticmethod
    def _percentage(value: int, total: int) -> int:
        if not total:
            return 0

        return round((value / total) * 100)

    @staticmethod
    def _has_value(value: Any) -> bool:
        if value is None:
            return False

        return bool(str(value).strip())

    @staticmethod
    def _first_value(
        item: dict[str, Any],
        *keys: str,
    ) -> Any:
        """
        Retourne la première valeur non vide trouvée parmi plusieurs
        noms possibles d'un même champ local/Cloud.
        """

        for key in keys:
            value = item.get(key)

            if value is not None and str(value).strip():
                return value

        return ""

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(
                value,
                datetime.min.time(),
            )

        text = str(value).strip()

        if not text:
            return None

        normalized = text.replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(normalized)

            if parsed.tzinfo is not None:
                parsed = parsed.astimezone().replace(
                    tzinfo=None
                )

            return parsed

        except ValueError:
            pass

        formats = (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M",
        )

        for date_format in formats:
            try:
                return datetime.strptime(
                    text,
                    date_format,
                )
            except ValueError:
                continue

        return None

    @staticmethod
    def _score_value(item: dict[str, Any]) -> float:
        value = CloudDashboardDataProvider._first_value(
            item,
            "score_prospect",
            "prospect_score",
            "score",
        )

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _score_grade(item: dict[str, Any]) -> str:
        grade = CloudDashboardDataProvider._first_value(
            item,
            "score_grade",
            "scoreGrade",
        )

        if grade:
            return str(grade).strip()

        score = CloudDashboardDataProvider._score_value(item)

        if score <= 0:
            return "Non calculé"

        if score >= 80:
            return "★★★★★"

        if score >= 60:
            return "★★★★☆"

        if score >= 40:
            return "★★★☆☆"

        if score >= 20:
            return "★★☆☆☆"

        return "★☆☆☆☆"

    @staticmethod
    def _is_high_priority(item: dict[str, Any]) -> bool:
        raw_priority = CloudDashboardDataProvider._first_value(
            item,
            "priority",
            "priorite",
        )

        api_priority = str(raw_priority).strip().lower()

        if api_priority in {
            "high",
            "urgent",
            "very_high",
            "haute",
            "élevée",
            "elevee",
        }:
            return True

        ui_priority = priority_to_ui(
            api_priority or "normal"
        )

        return (
            "⭐⭐⭐⭐⭐" in ui_priority
            or "⭐⭐⭐⭐" in ui_priority
            or "⭐⭐⭐" in ui_priority
        )

    @staticmethod
    def _enrichment_status(item: dict[str, Any]) -> str:
        return str(
            CloudDashboardDataProvider._first_value(
                item,
                "enrichment_status",
                "statut_enrichissement",
                "enrichmentStatus",
            )
        ).strip().lower()

    def _request_page(
        self,
        *,
        limit: int,
        offset: int,
    ):
        params = {
            "limit": limit,
            "offset": offset,
        }

        if self.project_id:
            params["project_id"] = self.project_id

        return self.api_client.list_prospects(**params)

    def _load_all_prospects(self) -> list[dict[str, Any]]:
        """
        Charge toutes les pages accessibles à l'utilisateur connecté.

        Le backend reste responsable de filtrer les prospects selon
        l'organisation, le projet et les droits du commercial.
        """

        prospects: list[dict[str, Any]] = []
        offset = 0
        total: int | None = None

        while total is None or offset < total:
            page = self._request_page(
                limit=self.PAGE_SIZE,
                offset=offset,
            )

            items = page.items or []

            if total is None:
                total = page.total

            prospects.extend(items)

            if not items:
                break

            offset += len(items)

            if len(items) < self.PAGE_SIZE:
                break

        return prospects

    def get_dashboard_data(self) -> dict[str, Any]:
        prospects = self._load_all_prospects()
        total = len(prospects)

        contact_keys = {
            "telephone": (
                "phone",
                "telephone",
            ),
            "email": (
                "email",
            ),
            "site_web": (
                "website",
                "site_web",
            ),
            "linkedin": (
                "linkedin",
                "linkedin_url",
            ),
            "facebook": (
                "facebook",
                "facebook_url",
            ),
            "instagram": (
                "instagram",
                "instagram_url",
            ),
        }

        counts: dict[str, int] = {}

        for target_key, source_keys in contact_keys.items():
            counts[target_key] = sum(
                1
                for item in prospects
                if self._has_value(
                    self._first_value(
                        item,
                        *source_keys,
                    )
                )
            )

        quality = {
            key: {
                "value": counts[key],
                "missing": max(
                    0,
                    total - counts[key],
                ),
                "percentage": self._percentage(
                    counts[key],
                    total,
                ),
            }
            for key in self.QUALITY_FIELDS
        }

        quality_score = (
            round(
                sum(
                    item["percentage"]
                    for item in quality.values()
                )
                / len(quality)
            )
            if quality
            else 0
        )

        pipeline: dict[str, int] = {}

        for item in prospects:
            raw_stage = self._first_value(
                item,
                "pipeline_stage",
                "pipeline",
            )

            stage = pipeline_to_ui(
                str(raw_stage or "nouveau")
            )

            pipeline[stage] = pipeline.get(stage, 0) + 1

        scoring: dict[str, int] = {}

        score_values: list[float] = []

        for item in prospects:
            grade = self._score_grade(item)

            scoring[grade] = scoring.get(grade, 0) + 1

            score = self._score_value(item)

            if score > 0:
                score_values.append(score)

        average_score = (
            round(sum(score_values) / len(score_values))
            if score_values
            else 0
        )

        today = datetime.now().date()
        next_week = today + timedelta(days=7)

        actions_today = 0
        actions_next_7_days = 0
        actions_overdue = 0
        high_priority = 0

        for item in prospects:
            action_at = self._parse_datetime(
                self._first_value(
                    item,
                    "next_action_at",
                    "date_prochaine_action",
                )
            )

            if action_at is not None:
                action_date = action_at.date()

                if action_date == today:
                    actions_today += 1

                elif today < action_date <= next_week:
                    actions_next_7_days += 1

                elif action_date < today:
                    actions_overdue += 1

            if self._is_high_priority(item):
                high_priority += 1

        enriched = 0
        no_reliable_result = 0
        enrichment_errors = 0

        for item in prospects:
            status = self._enrichment_status(item)

            if status in {
                "enrichi",
                "enriched",
                "completed",
                "complete",
            }:
                enriched += 1

            elif status in {
                "aucun résultat fiable",
                "aucun resultat fiable",
                "no_reliable_result",
            }:
                no_reliable_result += 1

            elif status in {
                "erreur enrichissement",
                "error",
                "failed",
                "failure",
            }:
                enrichment_errors += 1

        treated = enriched + no_reliable_result + enrichment_errors
        remaining = max(0, total - treated)

        return {
            "kpi": {
                "prospects": total,
                "telephones": counts["telephone"],
                "emails": counts["email"],
                "sites": counts["site_web"],
                "quality_score": quality_score,
                "average_prospect_score": average_score,
            },
            "pipeline": pipeline,
            "scoring": scoring,
            "quality": quality,
            "contact_distribution": [
                ("Téléphones", counts["telephone"]),
                ("Emails", counts["email"]),
                ("Sites", counts["site_web"]),
                ("LinkedIn", counts["linkedin"]),
                ("Facebook", counts["facebook"]),
                ("Instagram", counts["instagram"]),
            ],
            "enrichment": {
                "enriched": enriched,
                "no_reliable_result": no_reliable_result,
                "treated": treated,
                "remaining": remaining,
                "errors": enrichment_errors,
                "percentage": self._percentage(
                    treated,
                    total,
                ),
            },
            "activity": {
                "actions_today": actions_today,
                "actions_next_7_days": (
                    actions_next_7_days
                ),
                "actions_overdue": actions_overdue,
                "high_priority": high_priority,
                "missing_phone": max(
                    0,
                    total - counts["telephone"],
                ),
                "missing_email": max(
                    0,
                    total - counts["email"],
                ),
            },
        }