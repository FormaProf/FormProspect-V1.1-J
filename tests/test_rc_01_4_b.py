from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from repositories.prospect_repository import ProspectRepository
from services.deployment.deployment_context import DeploymentContext
from services.deployment.readers.prospect_reader import (
    ProspectDeploymentReader,
)


class FakeRepository(ProspectRepository):
    def __init__(self, database_path):
        self.database_path = database_path

    def get_connection(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn


class RC014BTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tempdir.name) / "test.db"
        conn = sqlite3.connect(self.database_path)
        conn.execute("""
            CREATE TABLE prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entreprise TEXT,
                siret TEXT,
                siren TEXT,
                adresse TEXT,
                code_postal TEXT,
                ville TEXT,
                code_naf TEXT,
                telephone TEXT,
                site_web TEXT,
                email TEXT,
                facebook TEXT,
                linkedin TEXT,
                instagram TEXT,
                youtube TEXT,
                statut_enrichissement TEXT,
                date_collecte TEXT,
                pipeline TEXT,
                priorite TEXT,
                prochaine_action TEXT,
                date_prochaine_action TEXT,
                commercial_assigne TEXT,
                score_prospect INTEGER,
                score_grade TEXT,
                score_label TEXT,
                score_details TEXT,
                date_score TEXT
            )
        """)
        conn.executemany(
            """
            INSERT INTO prospects (
                entreprise, ville, pipeline, priorite, score_prospect
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (f"Entreprise {i}", "Lille", "Nouveau", "normal", i)
                for i in range(12)
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_repository_iterates_without_loading_all(self):
        repository = FakeRepository(self.database_path)
        batches = list(
            repository.iterate_deployment_batches(batch_size=5)
        )
        self.assertEqual([batch.count for batch in batches], [5, 5, 2])
        self.assertEqual(batches[0].offset, 0)
        self.assertEqual(batches[-1].total_items, 12)
        self.assertTrue(batches[-1].is_last)

    def test_reader_uses_repository(self):
        repository = FakeRepository(self.database_path)
        reader = ProspectDeploymentReader(repository)
        context = DeploymentContext(
            entity_type="prospect",
            project_id="project-id",
            organization_id="organization-id",
            batch_size=4,
        )
        self.assertEqual(reader.count(context), 12)
        batches = list(reader.iter_batches(context))
        self.assertEqual([batch.count for batch in batches], [4, 4, 4])

    def test_resume_offset(self):
        repository = FakeRepository(self.database_path)
        batches = list(
            repository.iterate_deployment_batches(
                batch_size=5,
                start_offset=10,
            )
        )
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].offset, 10)
        self.assertEqual(batches[0].count, 2)


if __name__ == "__main__":
    unittest.main()
