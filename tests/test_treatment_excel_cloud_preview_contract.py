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


def test_cloud_project_enables_analysis_and_actionable_apply_button():
    source = PAGE_PATH.read_text(encoding="utf-8")

    assert 'self.excel_update_badge.set_state("idle", "Cloud prêt")' in source
    assert "bool(self.fichier_excel_mise_a_jour)" in source
    assert 'self.excel_update_preview_stats.get("mode_base") == "cloud_ro"' in source
    assert "self._excel_update_has_actions(self.excel_update_preview_stats)" in source
    assert "Les écritures Cloud sont additives" in source


def test_cloud_preview_uses_resolved_project_id():
    source = PAGE_PATH.read_text(encoding="utf-8")

    assert 'project_id = str(context.project_id or "").strip()' in source
    assert "CloudRuntime.api()" in source
    assert "project_id," in source


def test_apply_method_routes_cloud_to_dedicated_additive_service():
    source = PAGE_PATH.read_text(encoding="utf-8")
    method = _method("appliquer_mise_a_jour_excel")
    segment = ast.get_source_segment(source, method) or ""

    assert "if context.is_cloud" in segment
    assert "appliquer_mise_a_jour_cloud" in segment
    assert "CloudRuntime.api()" in segment
    assert "rollback global" in segment
    assert "appliquer_mise_a_jour_sqlite" in segment
