import sqlite3
from core.sqlite_utils import connect_database
import pandas as pd

from core.database import init_database


class ExportService:
    def exporter_prospects_excel(self, database_path, fichier_sortie):
        init_database(database_path)
        conn = connect_database(database_path)

        # Compatibilité avec les anciens projets locaux : la colonne Mobile
        # est ajoutée sans perte de données si elle n'existe pas encore.
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(prospects)").fetchall()
        }
        if "mobile" not in columns:
            conn.execute("ALTER TABLE prospects ADD COLUMN mobile TEXT")
            conn.commit()

        df = pd.read_sql_query("""
            SELECT
                entreprise,
                siret,
                siren,
                adresse,
                code_postal,
                ville,
                code_naf,
                telephone,
                mobile,
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
                commercial_assigne
            FROM prospects
        """, conn)

        conn.close()

        df.to_excel(fichier_sortie, index=False)

        return len(df)


    def exporter_lignes_prospects_excel(
        self,
        prospects,
        fichier_sortie,
    ):
        """Exporte les lignes CRM déjà filtrées, sans dépendre de la pagination UI."""

        columns = [
            "Entreprise",
            "Ville",
            "Code postal",
            "Téléphone",
            "Mobile",
            "Site web",
            "Email",
            "Pipeline",
            "Priorité",
            "Prochaine action",
            "Date prochaine action",
            "Commercial assigné",
            "Source",
        ]

        rows = []

        for prospect in prospects:
            if isinstance(prospect, dict):
                rows.append(
                    {
                        "Entreprise": (
                            prospect.get("company_name")
                            or prospect.get("entreprise")
                            or ""
                        ),
                        "Ville": (
                            prospect.get("city")
                            or prospect.get("ville")
                            or ""
                        ),
                        "Code postal": (
                            prospect.get("postal_code")
                            or prospect.get("code_postal")
                            or ""
                        ),
                        "Téléphone": (
                            prospect.get("phone")
                            or prospect.get("telephone")
                            or ""
                        ),
                        "Mobile": prospect.get("mobile") or "",
                        "Site web": (
                            prospect.get("website")
                            or prospect.get("site_web")
                            or ""
                        ),
                        "Email": prospect.get("email") or "",
                        "Pipeline": (
                            prospect.get("pipeline")
                            or prospect.get("pipeline_stage")
                            or ""
                        ),
                        "Priorité": (
                            prospect.get("priority")
                            or prospect.get("priorite")
                            or ""
                        ),
                        "Prochaine action": (
                            prospect.get("next_action")
                            or prospect.get("prochaine_action")
                            or ""
                        ),
                        "Date prochaine action": (
                            prospect.get("next_action_at")
                            or prospect.get("date_prochaine_action")
                            or ""
                        ),
                        "Commercial assigné": (
                            prospect.get("owner_display_name")
                            or prospect.get("commercial_assigne")
                            or ""
                        ),
                        "Source": prospect.get("source") or "",
                    }
                )
                continue

            values = list(prospect)

            def value_at(index):
                if index >= len(values):
                    return ""
                value = values[index]
                return "" if value is None else value

            rows.append(
                {
                    "Entreprise": value_at(1),
                    "Ville": value_at(2),
                    "Code postal": value_at(3),
                    "Téléphone": value_at(4),
                    "Mobile": value_at(15),
                    "Site web": value_at(5),
                    "Email": value_at(6),
                    "Pipeline": value_at(7),
                    "Priorité": value_at(8),
                    "Prochaine action": value_at(9),
                    "Date prochaine action": value_at(10),
                    "Commercial assigné": value_at(11),
                    "Source": value_at(16),
                }
            )

        df = pd.DataFrame(rows, columns=columns)
        df.to_excel(fichier_sortie, index=False)

        return len(df)
