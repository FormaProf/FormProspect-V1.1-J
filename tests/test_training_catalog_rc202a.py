import tempfile
import unittest
from pathlib import Path
from core.sqlite_utils import connect_database
from services.document_service import DocumentService

class TrainingCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'project.db'
        import sqlite3
        with connect_database(self.db) as conn:
            conn.execute('CREATE TABLE prospects(id INTEGER PRIMARY KEY)')
        self.service = DocumentService(self.db)

    def tearDown(self): self.tmp.cleanup()

    def test_seed_training_available(self):
        self.service.ensure_default_training()
        rows = self.service.list_trainings(active_only=True)
        self.assertTrue(any(r['reference'] == 'BTP-PILOTAGE' for r in rows))

    def test_duplicate_is_inactive(self):
        self.service.ensure_default_training()
        source = self.service.list_trainings()[0]
        new_id = self.service.duplicate_training(source['id'])
        copy = self.service.get_training(new_id)
        self.assertEqual(copy['active'], 0)
        self.assertIn('(copie)', copy['name'])

    def test_extended_fields_saved(self):
        tid = self.service.save_training(reference='TEST-1', name='Test', duration_hours=7, price_cents=90000, modality='Présentiel', category='Test', target_audience='Dirigeants', teaching_methods='Atelier', evaluation_methods='QCM', max_participants=12)
        row = self.service.get_training(tid)
        self.assertEqual(row['max_participants'], 12)
        self.assertEqual(row['category'], 'Test')

if __name__ == '__main__': unittest.main()
