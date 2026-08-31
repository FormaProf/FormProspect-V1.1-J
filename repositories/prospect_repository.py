from __future__ import annotations

from collections.abc import Iterator

from repositories.base_repository import BaseRepository
from services.deployment.deployment_batch import DeploymentBatch


class ProspectRepository(BaseRepository):
    SELECT_LIST = """
        SELECT
            id,
            entreprise,
            ville,
            code_postal,
            telephone,
            site_web,
            email,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
            score_prospect,
            score_grade,
            score_label,
            mobile
        FROM prospects
    """

    DEPLOYMENT_SELECT = """
        SELECT
            id,
            entreprise,
            siret,
            siren,
            adresse,
            code_postal,
            ville,
            code_naf,
            telephone,
            site_web,
            email,
            facebook,
            linkedin,
            instagram,
            twitter,
            youtube,
            social_other_urls,
            statut_enrichissement,
            date_collecte,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
            score_prospect,
            score_grade,
            score_label,
            score_details,
            date_score
        FROM prospects
    """

    DEPLOYMENT_BATCH_SELECT = """
        SELECT
            id,
            entreprise,
            siret,
            siren,
            adresse,
            code_postal,
            ville,
            code_naf,
            telephone,
            site_web,
            email,
            facebook,
            linkedin,
            instagram,
            twitter,
            youtube,
            social_other_urls,
            statut_enrichissement,
            date_collecte,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
            score_prospect,
            score_grade,
            score_label,
            score_details,
            date_score,
            mobile
        FROM prospects
    """

    SEARCH_FIELDS = [
        "entreprise",
        "ville",
        "code_postal",
        "telephone",
        "mobile",
        "site_web",
        "email",
        "statut_enrichissement",
        "pipeline",
        "priorite",
        "prochaine_action",
        "date_prochaine_action",
        "commercial_assigne",
        "score_grade",
        "score_label",
    ]

    FILTER_FIELDS = {
        "pipeline": "pipeline",
        "priorite": "priorite",
        "commercial": "commercial_assigne",
        "ville": "ville",
    }

    @staticmethod
    def _ensure_social_deployment_columns(conn):
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(prospects)")
        columns = {row[1] for row in cur.fetchall()}
        for column in ("twitter", "social_other_urls", "mobile"):
            if column not in columns:
                cur.execute(
                    f"ALTER TABLE prospects ADD COLUMN {column} TEXT DEFAULT ''"
                )
        conn.commit()

    def count_all(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM prospects")
            return cur.fetchone()[0]
        finally:
            conn.close()

    def count_with_phone(self):
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM prospects "
                "WHERE (telephone IS NOT NULL AND TRIM(telephone) != '') "
                "   OR (mobile IS NOT NULL AND TRIM(mobile) != '')"
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    def count_with_email(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM prospects "
                "WHERE email IS NOT NULL AND email != ''"
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    def count_with_website(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM prospects "
                "WHERE site_web IS NOT NULL AND site_web != ''"
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    def _build_where_clause(
        self,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
    ):
        clauses = []
        params = []

        recherche = (recherche or "").strip()
        if recherche:
            terme = f"%{recherche}%"
            search_clause = " OR ".join(
                [f"{field} LIKE ?" for field in self.SEARCH_FIELDS]
            )
            clauses.append(f"({search_clause})")
            params.extend([terme] * len(self.SEARCH_FIELDS))

        filters = {
            "pipeline": pipeline,
            "priorite": priorite,
            "commercial": commercial,
            "ville": ville,
        }

        for key, value in filters.items():
            value = (value or "").strip()
            if value:
                field = self.FILTER_FIELDS[key]
                clauses.append(f"{field} = ?")
                params.append(value)

        if not clauses:
            return "", params

        return " WHERE " + " AND ".join(clauses), params

    def count_filtered(
        self,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
    ):
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            where_clause, params = self._build_where_clause(
                recherche=recherche,
                pipeline=pipeline,
                priorite=priorite,
                commercial=commercial,
                ville=ville,
            )
            cur.execute(
                f"SELECT COUNT(*) FROM prospects{where_clause}",
                params,
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    def get_all(self, limit=100):
        return self.search_filtered(limite=limit)

    def search(self, recherche, limit=100):
        return self.search_filtered(recherche=recherche, limite=limit)

    def search_filtered(
        self,
        recherche="",
        pipeline="",
        priorite="",
        commercial="",
        ville="",
        limite=100,
        offset=0,
    ):
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            where_clause, params = self._build_where_clause(
                recherche=recherche,
                pipeline=pipeline,
                priorite=priorite,
                commercial=commercial,
                ville=ville,
            )
            params.extend([limite, offset])
            cur.execute(
                f"""
                {self.SELECT_LIST}
                {where_clause}
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            return cur.fetchall()
        finally:
            conn.close()

    def iterate_deployment_batches(
        self,
        *,
        batch_size: int = 500,
        start_offset: int = 0,
    ) -> Iterator[DeploymentBatch]:
        """
        Lit les prospects destinés au déploiement par lots.

        Une seule connexion est conservée pendant l'itération. La méthode ne
        charge jamais l'intégralité de la table en mémoire.
        """
        if batch_size <= 0:
            raise ValueError("batch_size doit être strictement positif.")
        if start_offset < 0:
            raise ValueError("start_offset ne peut pas être négatif.")

        total_items = int(self.count_all())
        if start_offset >= total_items:
            return

        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            offset = start_offset
            batch_number = (start_offset // batch_size) + 1

            while offset < total_items:
                cur.execute(
                    f"""
                    {self.DEPLOYMENT_BATCH_SELECT}
                    ORDER BY id ASC
                    LIMIT ? OFFSET ?
                    """,
                    (batch_size, offset),
                )
                rows = tuple(cur.fetchall())
                if not rows:
                    break

                yield DeploymentBatch(
                    number=batch_number,
                    offset=offset,
                    items=rows,
                    total_items=total_items,
                    batch_size=batch_size,
                )

                offset += len(rows)
                batch_number += 1
        finally:
            conn.close()

    def get_distinct_values(self, column_name, limit=500):
        allowed_columns = {
            "pipeline",
            "priorite",
            "commercial_assigne",
            "ville",
        }

        if column_name not in allowed_columns:
            raise ValueError(
                f"Colonne non autorisée pour les filtres : {column_name}"
            )

        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT DISTINCT {column_name}
                FROM prospects
                WHERE {column_name} IS NOT NULL
                  AND TRIM({column_name}) != ''
                ORDER BY {column_name} ASC
                LIMIT ?
                """,
                (limit,),
            )
            return [
                ligne[0]
                for ligne in cur.fetchall()
                if ligne and ligne[0]
            ]
        finally:
            conn.close()

    def get_filter_options(self):
        return {
            "pipeline": self.get_distinct_values("pipeline"),
            "priorite": self.get_distinct_values("priorite"),
            "commercial": self.get_distinct_values(
                "commercial_assigne"
            ),
            "ville": self.get_distinct_values("ville"),
        }

    def get_by_id(self, prospect_id):
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            cur.execute(
                f"""
                {self.DEPLOYMENT_SELECT}
                WHERE id = ?
                """,
                (prospect_id,),
            )
            return cur.fetchone()
        finally:
            conn.close()

    def update_pipeline(self, prospect_id, pipeline):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE prospects
                SET pipeline = ?
                WHERE id = ?
                """,
                (pipeline, prospect_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_mobile(self, prospect_id):
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(mobile, '') FROM prospects WHERE id = ?",
                (prospect_id,),
            )
            row = cur.fetchone()
            return str(row[0] or "") if row else ""
        finally:
            conn.close()

    def update_contact_infos(
        self,
        prospect_id,
        telephone,
        mobile,
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
        conn = self.get_connection()
        try:
            self._ensure_social_deployment_columns(conn)
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE prospects
                SET
                    telephone = ?,
                    mobile = ?,
                    site_web = ?,
                    email = ?,
                    facebook = ?,
                    linkedin = ?,
                    instagram = ?,
                    youtube = ?,
                    pipeline = ?,
                    priorite = ?,
                    prochaine_action = ?,
                    date_prochaine_action = ?,
                    commercial_assigne = ?
                WHERE id = ?
                """,
                (
                    telephone,
                    mobile,
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
                    prospect_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


