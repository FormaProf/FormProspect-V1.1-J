import ast
from pathlib import Path

from services.prospect_excel_preview_presenter import build_excel_update_result_text


PAGE_PATH = Path("ui/pages/treatment_page.py")


def _method(name):
    tree = ast.parse(PAGE_PATH.read_text(encoding="utf-8"))
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TreatmentPage"
    )
    return next(
        node for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_cloud_apply_is_wired_to_dedicated_service_method():
    source = PAGE_PATH.read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, _method("appliquer_mise_a_jour_excel")) or ""

    assert "appliquer_mise_a_jour_cloud" in segment
    assert "CloudRuntime.api()" in segment
    assert 'project_id = str(context.project_id or "").strip()' in segment
    assert "rollback global" in segment
    assert "Aucun prospect ne sera créé" in segment
    assert "aucune ancienne donnée ne sera supprimée" in segment


def test_cloud_apply_does_not_create_local_recovery_point():
    source = PAGE_PATH.read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, _method("appliquer_mise_a_jour_excel")) or ""
    cloud_segment = segment.split("if context.is_cloud:", 1)[1].split(
        "project = context.project or ApplicationState.get_project()", 1
    )[0]

    assert "_create_recovery_point" not in cloud_segment
    assert "appliquer_mise_a_jour_sqlite" not in cloud_segment


def test_cloud_project_can_enable_apply_after_actionable_preview():
    source = PAGE_PATH.read_text(encoding="utf-8")

    assert 'self.excel_update_preview_stats.get("mode_base") == "cloud_ro"' in source
    assert "self._excel_update_has_actions(self.excel_update_preview_stats)" in source
    assert "Les écritures Cloud sont additives" in source


def test_cloud_result_presenter_explicitly_states_no_global_rollback():
    text = build_excel_update_result_text({
        "fichier": "enrichi.xlsx",
        "mode_base": "cloud_rw_individual",
        "transaction_atomique": False,
        "correspondances_siret": 2,
        "prospects_mis_a_jour": 1,
        "prospects_en_echec": 1,
        "informations_ajoutees": 3,
        "echecs": [{
            "entreprise": "NADOT",
            "siret": "31035888200028",
            "erreur": "échec réseau",
        }],
    })

    assert "rollback global : NON" in text
    assert "Prospects en échec : 1" in text
    assert "NADOT — SIRET 31035888200028 : échec réseau" in text
    assert "Aucune ancienne donnée n'a été supprimée." in text
