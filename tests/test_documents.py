import tempfile
import unittest
from pathlib import Path

from core.database import init_database
from services.document_service import DocumentService


class DocumentServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "project.db"
        init_database(self.db)
        self.service = DocumentService(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_and_default_sequences(self):
        stats = self.service.stats()
        self.assertEqual(stats.trainings, 0)
        self.assertEqual(stats.templates, 0)
        self.assertEqual(self.service.next_number("Devis", 2026), "DEV-2026-000001")
        self.assertEqual(self.service.next_number("Devis", 2026), "DEV-2026-000002")
        self.assertEqual(self.service.next_number("Devis", 2027), "DEV-2027-000001")

    def test_training_crud(self):
        training_id = self.service.save_training(reference="BTP-PILOT", name="Pilotage d'activité BTP",
            duration_hours=14, price_cents=150000, modality="À distance")
        row = self.service.get_training(training_id)
        self.assertEqual(row["reference"], "BTP-PILOT")
        self.assertEqual(row["price_cents"], 150000)
        self.service.set_training_active(training_id, False)
        self.assertEqual(self.service.list_trainings()[0]["active"], 0)

    def test_template_linked_to_training(self):
        training_id = self.service.save_training(reference="EXCEL-1", name="Excel Débutant",
            duration_hours=30, price_cents=146500, modality="Mixte")
        template_id = self.service.save_template(name="Convention Excel", document_type="Convention",
            source_path="", output_format="DOCX + PDF", training_id=training_id)
        rows = self.service.list_templates()
        self.assertEqual(rows[0]["id"], template_id)
        self.assertEqual(rows[0]["training_name"], "Excel Débutant")

    def test_duplicate_reference_rejected(self):
        payload = dict(reference="CYBER", name="Cybersécurité", duration_hours=14, price_cents=115000, modality="À distance")
        self.service.save_training(**payload)
        with self.assertRaises(ValueError):
            self.service.save_training(**payload)


if __name__ == "__main__":
    unittest.main()
