from repositories.base_repository import BaseRepository


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
            score_label
        FROM prospects
    """

    SEARCH_FIELDS = [
        "entreprise",
        "ville",
        "code_postal",
        "telephone",
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

    def count_all(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prospects")
        total = cur.fetchone()[0]
        conn.close()
        return total

    def count_with_phone(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prospects WHERE telephone IS NOT NULL AND telephone != ''")
        total = cur.fetchone()[0]
        conn.close()
        return total

    def count_with_email(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prospects WHERE email IS NOT NULL AND email != ''")
        total = cur.fetchone()[0]
        conn.close()
        return total

    def count_with_website(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prospects WHERE site_web IS NOT NULL AND site_web != ''")
        total = cur.fetchone()[0]
        conn.close()
        return total

    def _build_where_clause(self, recherche="", pipeline="", priorite="", commercial="", ville=""):
        clauses = []
        params = []

        recherche = (recherche or "").strip()
        if recherche:
            terme = f"%{recherche}%"
            search_clause = " OR ".join([f"{field} LIKE ?" for field in self.SEARCH_FIELDS])
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

    def count_filtered(self, recherche="", pipeline="", priorite="", commercial="", ville=""):
        conn = self.get_connection()
        cur = conn.cursor()

        where_clause, params = self._build_where_clause(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
        )

        cur.execute(f"SELECT COUNT(*) FROM prospects{where_clause}", params)
        total = cur.fetchone()[0]
        conn.close()
        return total

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
        cur = conn.cursor()

        where_clause, params = self._build_where_clause(
            recherche=recherche,
            pipeline=pipeline,
            priorite=priorite,
            commercial=commercial,
            ville=ville,
        )

        params.extend([limite, offset])
        cur.execute(f"""
            {self.SELECT_LIST}
            {where_clause}
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        """, params)

        lignes = cur.fetchall()
        conn.close()
        return lignes

    def get_distinct_values(self, column_name, limit=500):
        allowed_columns = {
            "pipeline",
            "priorite",
            "commercial_assigne",
            "ville",
        }

        if column_name not in allowed_columns:
            raise ValueError(f"Colonne non autorisée pour les filtres : {column_name}")

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute(f"""
            SELECT DISTINCT {column_name}
            FROM prospects
            WHERE {column_name} IS NOT NULL
              AND TRIM({column_name}) != ''
            ORDER BY {column_name} ASC
            LIMIT ?
        """, (limit,))

        valeurs = [ligne[0] for ligne in cur.fetchall() if ligne and ligne[0]]
        conn.close()
        return valeurs

    def get_filter_options(self):
        return {
            "pipeline": self.get_distinct_values("pipeline"),
            "priorite": self.get_distinct_values("priorite"),
            "commercial": self.get_distinct_values("commercial_assigne"),
            "ville": self.get_distinct_values("ville"),
        }

    def get_by_id(self, prospect_id):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
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
                youtube,
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
            WHERE id = ?
        """, (prospect_id,))

        prospect = cur.fetchone()
        conn.close()
        return prospect


    def update_pipeline(self, prospect_id, pipeline):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE prospects
            SET pipeline = ?
            WHERE id = ?
        """, (pipeline, prospect_id))

        conn.commit()
        updated = cur.rowcount
        conn.close()
        return updated > 0

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
        commercial_assigne
    ):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE prospects
            SET
                telephone = ?,
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
        """, (
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
            prospect_id
        ))

        conn.commit()
        conn.close()
