from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
DIALOG = (ROOT / "ui/dialogs/prospect_dialog.py").read_text(encoding="utf-8")
TABLE = (ROOT / "ui/widgets/crm/prospects_table.py").read_text(encoding="utf-8")
KANBAN = (ROOT / "ui/widgets/crm/kanban_column.py").read_text(encoding="utf-8")
FILTERS = (ROOT / "ui/widgets/crm/filters_bar.py").read_text(encoding="utf-8")
CORE = (ROOT / "core/crm.py").read_text(encoding="utf-8")
DASHBOARD = (ROOT / "ui/pages/dashboard_page.py").read_text(encoding="utf-8")

def test_modified_sources_parse():
    for source in (DIALOG, TABLE, KANBAN, FILTERS):
        ast.parse(source)

def test_nouveau_is_blue_on_visible_surfaces():
    assert "#338CE4" in DASHBOARD
    assert '"nouveau": ("NOUVEAU", "#EAF4FF", "#0B5FC6", "#338CE4")' in DIALOG
    assert '("NOUVEAU", "#0B2742", "#8FD6FF", "#338CE4")' in DIALOG
    assert '"🟢 Nouveau": ("Nouveau", "#EAF4FF", "#0B5FC6", "#338CE4")' in TABLE
    assert 'return "#338CE4"' in KANBAN
    assert 'couleur = "#338CE4"' in KANBAN
    assert 'QColor("#338CE4")' in FILTERS

def test_pipeline_business_value_is_preserved():
    assert 'PIPELINE_DEFAULT = "🟢 Nouveau"' in CORE
    assert 'self.pipeline_input.addItem(QIcon(marker), "Nouveau", canonical)' in DIALOG
    assert "self.pipeline_input.currentData()" in DIALOG
    assert 'combo.addItem(QIcon(marker), "Nouveau", texte)' in FILTERS
