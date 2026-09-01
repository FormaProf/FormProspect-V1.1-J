import ast
from pathlib import Path


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


def test_preview_context_guard_checks_cloud_project_id_and_local_database():
    source = PAGE_PATH.read_text(encoding="utf-8")
    segment = ast.get_source_segment(
        source, _method("_excel_update_preview_matches_context")
    ) or ""

    assert 'stats.get("project_id")' in segment
    assert "context.project_id" in segment
    assert 'stats.get("base_sqlite")' in segment
    assert "project.database" in segment
    assert 'stats.get("mode_base") == "cloud_ro"' in segment
    assert 'stats.get("mode_base") != "sqlite_ro"' in segment


def test_apply_refuses_stale_preview_before_local_or_cloud_write():
    source = PAGE_PATH.read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, _method("appliquer_mise_a_jour_excel")) or ""

    guard_pos = segment.index("_excel_update_preview_matches_context")
    cloud_write_pos = segment.index("appliquer_mise_a_jour_cloud")
    local_write_pos = segment.index("appliquer_mise_a_jour_sqlite")

    assert guard_pos < cloud_write_pos
    assert guard_pos < local_write_pos
    assert "Le projet actif a changé depuis l'analyse Excel" in segment
    assert "Analyse obsolète" in segment


def test_refresh_only_enables_apply_for_preview_belonging_to_active_context():
    source = PAGE_PATH.read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, _method("rafraichir")) or ""

    assert segment.count("_excel_update_preview_matches_context") >= 2
    assert "_excel_update_has_actions" in segment
