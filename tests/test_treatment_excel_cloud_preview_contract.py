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
    calls = []
    for node in ast.walk(method):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            calls.append(node.func.attr)
    return calls


def test_cloud_preview_uses_cloud_runtime_and_read_only_comparison():
    source = PAGE_PATH.read_text(encoding="utf-8")
    calls = _called_attributes(_method("analyser_mise_a_jour_excel"))

    assert "from services.cloud_runtime import CloudRuntime" in source
    assert "comparer_avec_cloud" in calls
    assert "comparer_avec_sqlite" in calls
    assert "update_prospect" not in calls
    assert "appliquer_mise_a_jour_sqlite" not in calls


def test_cloud_project_enables_analysis_but_never_apply_button():
    source = PAGE_PATH.read_text(encoding="utf-8")

    assert 'self.excel_update_badge.set_state("idle", "Cloud prêt")' in source
    assert "bool(self.fichier_excel_mise_a_jour)" in source
    assert "self.bouton_appliquer_mise_a_jour.setEnabled(False)" in source
    assert "L'écriture Cloud reste désactivée dans ce lot." in source


def test_cloud_preview_uses_resolved_project_id():
    source = PAGE_PATH.read_text(encoding="utf-8")

    assert 'project_id = str(context.project_id or "").strip()' in source
    assert "CloudRuntime.api()" in source
    assert "project_id," in source


def test_apply_method_still_refuses_cloud_writes():
    source = PAGE_PATH.read_text(encoding="utf-8")
    method = _method("appliquer_mise_a_jour_excel")
    segment = ast.get_source_segment(source, method) or ""

    assert "if context.is_cloud" in segment
    assert "Aucune modification n'a été effectuée" in segment
    assert "appliquer_mise_a_jour_sqlite" in segment
    assert "update_prospect" not in segment
