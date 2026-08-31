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
