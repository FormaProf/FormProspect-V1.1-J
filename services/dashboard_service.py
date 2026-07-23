from repositories.dashboard_repository import DashboardRepository


class DashboardService:
    """Prépare toutes les données du centre de commandement."""

    QUALITY_FIELDS = ("telephone", "email", "site_web", "linkedin")

    def __init__(self, database_path=None):
        self.database_path = database_path

    def get_repository(self, database_path=None):
        db = database_path or self.database_path
        if not db:
            raise ValueError("Aucune base de données sélectionnée.")
        return DashboardRepository(db)

    @staticmethod
    def _percentage(value, total):
        if not total:
            return 0
        return round((value / total) * 100)

    def get_dashboard_data(self, database_path):
        repo = self.get_repository(database_path)
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
            round(sum(item["percentage"] for item in quality.values()) / len(quality))
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
                "average_prospect_score": repo.average_prospect_score(),
            },
            "pipeline": {name: count for name, count in repo.count_by_pipeline()},
            "scoring": {name: count for name, count in repo.count_by_score_grade()},
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
                "remaining": remaining,
                "errors": enrichment_errors,
                "percentage": self._percentage(enriched, total),
            },
            "activity": {
                "actions_today": repo.count_actions_today(),
                "actions_next_7_days": repo.count_actions_next_7_days(),
                "actions_overdue": repo.count_actions_overdue(),
                "high_priority": repo.count_high_priority(),
                "missing_phone": max(0, total - counts["telephone"]),
                "missing_email": max(0, total - counts["email"]),
            },
        }
