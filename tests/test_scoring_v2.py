import json
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from core.database import init_database
from services.scoring_service import ScoringService


class ScoringV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "project.db"
        init_database(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _insert_prospect(self, **overrides):
        data = {
            "entreprise": "BTP Exemple",
            "siret": "12345678900012",
            "siren": "123456789",
            "adresse": "1 rue du Test",
            "code_postal": "59000",
            "ville": "Lille",
            "code_naf": "43.99A",
            "telephone": "0612345678",
            "site_web": "https://exemple.fr",
            "email": "contact@exemple.fr",
            "facebook": "",
            "linkedin": "https://linkedin.com/company/exemple",
            "instagram": "",
            "youtube": "",
            "statut_enrichissement": "Enrichi",
            "date_collecte": date.today().isoformat(),
            "pipeline": "🟠 Négociation",
            "priorite": "⭐⭐⭐⭐⭐",
            "prochaine_action": "Relancer",
            "date_prochaine_action": (date.today() + timedelta(days=1)).isoformat(),
            "commercial_assigne": "Nacim",
        }
        data.update(overrides)
        conn = sqlite3.connect(self.db)
        columns = ",".join(data)
        placeholders = ",".join("?" for _ in data)
        cur = conn.execute(f"INSERT INTO prospects ({columns}) VALUES ({placeholders})", tuple(data.values()))
        prospect_id = cur.lastrowid
        conn.commit()
        conn.close()
        return prospect_id

    def test_migration_adds_v2_schema_without_losing_existing_data(self):
        prospect_id = self._insert_prospect()
        init_database(self.db)
        conn = sqlite3.connect(self.db)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(prospects)")}
        self.assertTrue({"score_completude", "score_conversion", "score_risque", "score_version"}.issubset(columns))
        self.assertEqual(conn.execute("SELECT entreprise FROM prospects WHERE id=?", (prospect_id,)).fetchone()[0], "BTP Exemple")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=19").fetchone()[0], 1)
        conn.close()

    def test_hot_prospect_receives_high_explainable_score(self):
        prospect_id = self._insert_prospect()
        conn = sqlite3.connect(self.db)
        for i in range(4):
            conn.execute("INSERT INTO activities(prospect_id,date_creation,type_action,description) VALUES (?,?,?,?)", (prospect_id, date.today().isoformat(), "Appel", f"Contact {i}"))
        conn.execute("INSERT INTO notes(prospect_id,date_creation,contenu) VALUES (?,?,?)", (prospect_id, date.today().isoformat(), "Budget confirmé"))
        conn.commit(); conn.close()

        result = ScoringService.score_prospect(self.db, prospect_id)
        self.assertGreaterEqual(result.score, 70)
        self.assertGreater(result.conversion, 60)
        self.assertLess(result.risk, 50)
        self.assertIn(result.label, {"Chaud", "Très chaud"})
        self.assertTrue(any("Engagement commercial" in reason for reason in result.reasons))

    def test_cold_incomplete_prospect_stays_low(self):
        prospect_id = self._insert_prospect(
            siret="", siren="", adresse="", code_postal="", code_naf="",
            telephone="", site_web="", email="", linkedin="",
            statut_enrichissement="", pipeline="🟢 Nouveau", priorite="⭐",
            prochaine_action="Aucune", date_prochaine_action="", commercial_assigne="",
        )
        result = ScoringService.score_prospect(self.db, prospect_id)
        self.assertLess(result.score, 30)
        self.assertGreaterEqual(result.risk, 70)
        self.assertEqual(result.label, "Données insuffisantes")

    def test_history_is_created_only_when_score_changes(self):
        prospect_id = self._insert_prospect()
        first = ScoringService.score_prospect(self.db, prospect_id)
        ScoringService.score_prospect(self.db, prospect_id)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM prospect_score_history WHERE prospect_id=?", (prospect_id,)).fetchone()[0], 1)
        conn.execute("UPDATE prospects SET pipeline='🟢 Client' WHERE id=?", (prospect_id,))
        conn.commit(); conn.close()
        second = ScoringService.score_prospect(self.db, prospect_id)
        self.assertGreater(second.score, first.score)
        self.assertEqual(second.conversion, 100)
        self.assertEqual(second.risk, 0)
        self.assertEqual(len(ScoringService.get_history(self.db, prospect_id)), 2)

    def test_score_all_updates_distribution_and_version(self):
        self._insert_prospect()
        self._insert_prospect(entreprise="Prospect froid", telephone="", email="", site_web="", pipeline="🟢 Nouveau")
        report = ScoringService.score_all(self.db)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["version"], "v2")
        self.assertEqual(sum(report["distribution"].values()), 2)
        conn = sqlite3.connect(self.db)
        versions = {row[0] for row in conn.execute("SELECT score_version FROM prospects")}
        conn.close()
        self.assertEqual(versions, {"v2"})


if __name__ == "__main__":
    unittest.main()
