import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.sqlite_utils import connect_database
from services.client_onboarding_service import ClientOnboardingService


class ClientOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "project.db"
        with connect_database(self.db) as conn:
            conn.execute("""CREATE TABLE prospects (
                id INTEGER PRIMARY KEY, entreprise TEXT, siret TEXT, siren TEXT, adresse TEXT,
                code_postal TEXT, ville TEXT, telephone TEXT, email TEXT, commercial_assigne TEXT,
                pipeline TEXT, prochaine_action TEXT, date_prochaine_action TEXT)""")
            conn.execute("""INSERT INTO prospects VALUES
                (1,'ACME BTP','12345678900011','','1 rue Test','59000','Lille','0600000000',
                 'contact@acme.fr','Nacim','🟢 Nouveau','','')""")
        self.service = ClientOnboardingService(self.db, self.root)
        self.training_id = self.service.document_service.save_training(
            reference="BTP-14H", name="Pilotage BTP", duration_hours=14,
            price_cents=170000, modality="À distance")

    def tearDown(self): self.tmp.cleanup()

    def test_transform_creates_client_session_workflow_and_folders(self):
        result = self.service.transform(
            prospect_id=1, company_name="ACME BTP", siret="12345678900011",
            training_id=self.training_id, start_date="2026-09-01", end_date="2026-09-02")
        self.assertTrue(result.client_folder.exists())
        self.assertTrue((result.client_folder / "01 - Devis").exists())
        with connect_database(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM training_sessions").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT pipeline FROM prospects WHERE id=1").fetchone()[0], "🟢 Client")

    def test_end_date_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.transform(prospect_id=1, company_name="ACME", training_id=self.training_id,
                                   start_date="2026-09-02", end_date="2026-09-01")

    def test_existing_client_can_receive_another_session(self):
        kwargs=dict(prospect_id=1, company_name="ACME", training_id=self.training_id,
                    start_date="2026-09-01", end_date="2026-09-02")
        self.service.transform(**kwargs); self.service.transform(**kwargs)
        with connect_database(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM training_sessions").fetchone()[0], 2)

if __name__ == '__main__': unittest.main()
