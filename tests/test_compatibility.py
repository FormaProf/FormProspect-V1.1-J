import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.database import init_database


class CompatibilityTests(unittest.TestCase):
    def test_rc181_like_database_is_upgraded_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "legacy.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE prospects (id INTEGER PRIMARY KEY AUTOINCREMENT, entreprise TEXT, telephone TEXT, email TEXT, site_web TEXT, linkedin TEXT, facebook TEXT, instagram TEXT, siret TEXT, siren TEXT, code_naf TEXT, adresse TEXT, ville TEXT, code_postal TEXT, statut_enrichissement TEXT, date_collecte TEXT)")
            conn.execute("INSERT INTO prospects(entreprise, telephone) VALUES ('Ancien prospect','0600000000')")
            conn.commit(); conn.close()
            init_database(db)
            init_database(db)
            conn = sqlite3.connect(db)
            self.assertEqual(conn.execute("SELECT entreprise FROM prospects").fetchone()[0], "Ancien prospect")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=19").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM prospect_score_history").fetchone()[0], 0)
            conn.close()


if __name__ == "__main__":
    unittest.main()
