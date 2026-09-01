from pathlib import Path

from services.prospect_excel_preview_presenter import build_excel_update_result_text


ROOT = Path(__file__).resolve().parents[1]
TREATMENT = ROOT / "ui" / "pages" / "treatment_page.py"


def test_result_presenter_states_no_creation_no_deletion_and_transaction():
    text = build_excel_update_result_text({
        "fichier": "enrichi.xlsx",
        "correspondances_siret": 10,
        "prospects_mis_a_jour": 7,
        "informations_ajoutees": 15,
        "champs_completes": 4,
        "valeurs_fusionnees": 11,
        "conflits_ignores": 2,
        "introuvables": 1,
    })
    assert "Prospects mis à jour : 7" in text
    assert "Informations ajoutées : 15" in text
    assert "Création automatique de prospects : NON" in text
    assert "Suppression de données existantes : NON" in text
    assert "rollback en cas d'erreur : OUI" in text


def test_treatment_page_exposes_distinct_apply_button_and_confirmation():
    source = TREATMENT.read_text(encoding="utf-8")
    assert "Enrichir les prospects avec ce fichier" in source
    assert "self.appliquer_mise_a_jour_excel" in source
    assert "self.excel_update_service.appliquer_mise_a_jour_sqlite" in source
    assert "Aucun prospect ne sera créé" in source
    assert "Aucune ancienne donnée" in source
    assert "_create_recovery_point(\"excel_update\", project)" in source


def test_treatment_page_keeps_old_import_separate():
    source = TREATMENT.read_text(encoding="utf-8")
    assert "self.bouton_importer.clicked.connect(self.importer_dans_sqlite)" in source
    assert "self.import_service.importer_excel_vers_sqlite" in source
    assert "self.bouton_appliquer_mise_a_jour.clicked.connect" in source
