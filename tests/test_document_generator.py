import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.sqlite_utils import connect_database
from services.client_onboarding_service import ClientOnboardingService
from services.document_generator_service import DocumentGeneratorService


class DocumentGeneratorTests(unittest.TestCase):
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
                 'contact@acme.fr','Nacim','Nouveau','','')""")
        onboarding = ClientOnboardingService(self.db, self.root)
        training_id = onboarding.document_service.save_training(
            reference="BTP-14H", name="Pilotage BTP", duration_hours=14,
            price_cents=170000, modality="À distance", objectives="Structurer le suivi d’activité")
        result = onboarding.transform(prospect_id=1, company_name="ACME BTP", siret="12345678900011",
                                      address="1 rue Test", postal_code="59000", city="Lille",
                                      contact_name="Mme Test", email="contact@acme.fr", training_id=training_id,
                                      trainer_name="Mélanie", start_date="2026-09-01", end_date="2026-09-02")
        self.session_id = result.session_id
        self.service = DocumentGeneratorService(self.db, self.root)

    def tearDown(self): self.tmp.cleanup()

    def test_variables_are_built_from_session(self):
        session = self.service.get_session_context(self.session_id)
        values = self.service.build_variables(session, "DEV-2026-000001")
        self.assertEqual(values["CLIENT_NOM"], "ACME BTP")
        self.assertEqual(values["FORMATION_PRIX"], "1 700 €")
        self.assertEqual(values["DATE_DEBUT"], "01/09/2026")

    def test_generate_four_docx_and_history(self):
        results = self.service.generate(session_id=self.session_id,
                                        document_types=["Devis", "Convention", "Programme", "Convocation"],
                                        generate_pdf=False)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(item.docx_path.exists() for item in results))
        with connect_database(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 4)
            step = conn.execute("SELECT current_step FROM client_workflows WHERE session_id=?", (self.session_id,)).fetchone()[0]
            self.assertEqual(step, "Documents générés")

    def test_invalid_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.generate(session_id=self.session_id, document_types=["Inconnu"], generate_pdf=False)

    def test_preflight_reports_templates_and_optional_warnings(self):
        check = self.service.preflight(self.session_id, ["Devis", "Convention"])
        self.assertTrue(check.can_generate)
        self.assertEqual(check.templates["Devis"], "Modèle interne Form@Prof")
        self.assertTrue(any("aucun modèle DOCX" in warning for warning in check.warnings))

    def test_preflight_blocks_invalid_dates(self):
        with connect_database(self.db) as conn:
            conn.execute("UPDATE training_sessions SET start_date='2026-09-03', end_date='2026-09-01' WHERE id=?", (self.session_id,))
        check = self.service.preflight(self.session_id, ["Devis"])
        self.assertFalse(check.can_generate)
        self.assertTrue(any("date de fin" in error for error in check.errors))
        with self.assertRaises(ValueError):
            self.service.generate(session_id=self.session_id, document_types=["Devis"], generate_pdf=False)

    def test_broken_template_falls_back_to_internal_model(self):
        template_id = self.service.document_service.save_template(
            name="Devis cassé", document_type="Devis", source_path="", training_id=None
        )
        with connect_database(self.db) as conn:
            conn.execute("UPDATE document_templates SET source_path=? WHERE id=?", (str(self.root / "missing.docx"), template_id))
        results = self.service.generate(session_id=self.session_id, document_types=["Devis"], generate_pdf=False)
        self.assertEqual(results[0].template_name, "Modèle interne Form@Prof")
        self.assertIn("modèle interne", results[0].warning.lower())
        self.assertGreater(results[0].docx_path.stat().st_size, 0)


if __name__ == "__main__": unittest.main()
