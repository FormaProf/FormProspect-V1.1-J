from repositories.base_repository import BaseRepository


class DashboardRepository(BaseRepository):
    """Accès aux statistiques utilisées par le Dashboard 2.0."""

    _CONTACT_COLUMNS = {
        "telephone",
        "email",
        "site_web",
        "facebook",
        "linkedin",
        "instagram",
        "youtube",
    }

    def _fetch_one_value(self, query, params=None):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params or [])
            row = cur.fetchone()
            return (row[0] if row else 0) or 0
        finally:
            conn.close()

    def count_all_prospects(self):
        return self._fetch_one_value("SELECT COUNT(*) FROM prospects")

    def count_not_empty(self, column_name):
        if column_name not in self._CONTACT_COLUMNS:
            raise ValueError(f"Colonne non autorisée pour le dashboard : {column_name}")
        return self._fetch_one_value(
            f"""
            SELECT COUNT(*)
            FROM prospects
            WHERE {column_name} IS NOT NULL
              AND TRIM({column_name}) != ''
            """
        )

    def count_empty(self, column_name):
        if column_name not in self._CONTACT_COLUMNS:
            raise ValueError(f"Colonne non autorisée pour le dashboard : {column_name}")
        return self._fetch_one_value(
            f"""
            SELECT COUNT(*)
            FROM prospects
            WHERE {column_name} IS NULL
               OR TRIM({column_name}) = ''
            """
        )

    def count_enriched(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE COALESCE(TRIM(statut_enrichissement), '') = 'Enrichi'
            """
        )

    def count_enrichment_errors(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE COALESCE(TRIM(statut_enrichissement), '') = 'Erreur enrichissement'
            """
        )

    def count_no_reliable_result(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE COALESCE(TRIM(statut_enrichissement), '') = 'Aucun résultat fiable'
            """
        )

    def count_by_pipeline(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COALESCE(NULLIF(TRIM(pipeline), ''), 'Non défini') AS pipeline_name,
                    COUNT(*) AS total
                FROM prospects
                GROUP BY pipeline_name
                ORDER BY total DESC
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    def count_actions_today(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE date_prochaine_action IS NOT NULL
              AND TRIM(date_prochaine_action) != ''
              AND date(date_prochaine_action) = date('now', 'localtime')
            """
        )

    def count_actions_next_7_days(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE date_prochaine_action IS NOT NULL
              AND TRIM(date_prochaine_action) != ''
              AND date(date_prochaine_action) > date('now', 'localtime')
              AND date(date_prochaine_action) <= date('now', 'localtime', '+7 day')
            """
        )

    def count_actions_overdue(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE date_prochaine_action IS NOT NULL
              AND TRIM(date_prochaine_action) != ''
              AND date(date_prochaine_action) < date('now', 'localtime')
            """
        )

    def count_high_priority(self):
        return self._fetch_one_value(
            """
            SELECT COUNT(*)
            FROM prospects
            WHERE priorite IS NOT NULL
              AND TRIM(priorite) != ''
              AND (
                    priorite LIKE '%⭐⭐⭐⭐⭐%'
                 OR priorite LIKE '%⭐⭐⭐⭐%'
                 OR priorite LIKE '%⭐⭐⭐%'
              )
            """
        )


    def count_by_score_grade(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT COALESCE(NULLIF(TRIM(score_grade), ''), 'Non calculé'), COUNT(*)
                FROM prospects
                GROUP BY COALESCE(NULLIF(TRIM(score_grade), ''), 'Non calculé')
            """)
            return cur.fetchall()
        finally:
            conn.close()

    def average_prospect_score(self):
        return round(float(self._fetch_one_value(
            "SELECT COALESCE(AVG(score_prospect), 0) FROM prospects"
        )))
