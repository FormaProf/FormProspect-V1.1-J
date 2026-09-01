import ast
from pathlib import Path


PAGE_PATH = Path("ui/pages/treatment_page.py")


def _class_node():
    tree = ast.parse(PAGE_PATH.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TreatmentPage"
    )


def _method(name):
    cls = _class_node()
    return next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _called_attributes(method):
    result = []
    for node in ast.walk(method):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            result.append(node.func.attr)
    return result


def test_treatment_page_exposes_separate_excel_update_preview_actions():
    cls = _class_node()
    method_names = {
        node.name for node in cls.body if isinstance(node, ast.FunctionDef)
    }

    assert "choisir_excel_mise_a_jour" in method_names
    assert "analyser_mise_a_jour_excel" in method_names


def test_excel_preview_analysis_uses_read_only_comparison_not_legacy_import():
    calls = _called_attributes(_method("analyser_mise_a_jour_excel"))

    assert "comparer_avec_sqlite" in calls
    assert "importer_excel_vers_sqlite" not in calls
    assert "update_prospect" not in calls


def test_legacy_excel_import_method_is_still_present_and_separate():
    calls = _called_attributes(_method("importer_dans_sqlite"))

    assert "importer_excel_vers_sqlite" in calls
