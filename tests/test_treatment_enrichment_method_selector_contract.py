from pathlib import Path
import ast


PAGE = Path(__file__).parents[1] / "ui" / "pages" / "treatment_page.py"
SOURCE = PAGE.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _method(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Méthode absente : {name}")


def _calls(node, attr):
    for item in ast.walk(node):
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            if item.func.attr == attr:
                return True
    return False


def test_page_imports_method_catalog_and_qcombobox():
    assert "EnrichmentMethodCatalog" in SOURCE
    assert "QComboBox" in SOURCE


def test_selector_exposes_profile_descriptions_and_change_handler():
    assert "self.enrichment_method_combo" in SOURCE
    assert "self.enrichment_method_description" in SOURCE
    assert _method("_on_enrichment_method_changed")


def test_refresh_applies_method_gate():
    node = _method("rafraichir")
    assert _calls(node, "_apply_enrichment_method_gate")


def test_engine_launch_is_guarded_by_selected_profile():
    node = _method("demarrer_enrichissement")
    segment = ast.get_source_segment(SOURCE, node)
    assert "profile.uses_excel" in segment
    assert "profile.engine_ready" in segment


def test_lot_does_not_change_worker_constructor_contract():
    node = _method("demarrer_enrichissement")
    segment = ast.get_source_segment(SOURCE, node)
    assert "EnrichmentWorker(\n            str(project.database),\n            limite,\n            mode=mode," in segment
    assert "strategy=" not in segment
    assert "profile=" not in segment


def test_selector_is_locked_while_enrichment_runs():
    node = _method("_set_enrichment_running")
    segment = ast.get_source_segment(SOURCE, node)
    assert "self.enrichment_method_combo.setEnabled(not running)" in segment
