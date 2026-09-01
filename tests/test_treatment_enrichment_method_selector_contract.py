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


def test_page_imports_catalog_runtime_and_selector():
    assert "EnrichmentMethodCatalog" in SOURCE
    assert "EnrichmentMethodRuntime" in SOURCE
    assert "QComboBox" in SOURCE


def test_selector_exposes_descriptions_and_change_handler():
    assert "self.enrichment_method_combo" in SOURCE
    assert "self.enrichment_method_description" in SOURCE
    assert _method("_on_enrichment_method_changed")


def test_refresh_still_applies_method_gate():
    assert _calls(_method("rafraichir"), "_apply_enrichment_method_gate")


def test_excel_never_routes_to_web_engine():
    segment = ast.get_source_segment(SOURCE, _method("demarrer_enrichissement"))
    assert "profile.uses_excel" in segment
    assert "Méthode Excel" in segment


def test_selected_web_method_is_activated_before_worker_start():
    segment = ast.get_source_segment(SOURCE, _method("demarrer_enrichissement"))
    assert "EnrichmentMethodRuntime.activate(profile.key)" in segment
    assert segment.index("EnrichmentMethodRuntime.activate(profile.key)") < segment.index(
        "EnrichmentWorker("
    )


def test_worker_constructor_contract_remains_unchanged():
    segment = ast.get_source_segment(SOURCE, _method("demarrer_enrichissement"))
    assert "EnrichmentWorker(\n            str(project.database),\n            limite,\n            mode=mode," in segment
    assert "strategy=" not in segment[segment.index("EnrichmentWorker("):]


def test_activity_records_selected_method():
    segment = ast.get_source_segment(SOURCE, _method("demarrer_enrichissement"))
    assert '"enrichment_method": profile.key' in segment
    assert "profile.label" in segment


def test_selector_is_locked_while_enrichment_runs():
    segment = ast.get_source_segment(SOURCE, _method("_set_enrichment_running"))
    assert "self.enrichment_method_combo.setEnabled(not running)" in segment
