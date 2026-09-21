from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def source(path):
    return (ROOT / path).read_text(encoding="utf-8")

PAGE = source("ui/pages/prospects_page.py")
FILTERS = source("ui/widgets/crm/filters_bar.py")
TABLE = source("ui/widgets/crm/prospects_table.py")
KANBAN = source("ui/widgets/crm/kanban_view.py")
COLUMN = source("ui/widgets/crm/kanban_column.py")
CARD = source("ui/widgets/crm/kanban_card.py")
THEME = source("ui/crm_premium_theme.py")

def test_crm_premium_sources_parse():
    for code in (PAGE, FILTERS, TABLE, KANBAN, COLUMN, CARD, THEME):
        ast.parse(code)

def test_crm_uses_global_three_theme_system():
    assert "THEME_CLASSIC" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert "THEME_UI_DARK" in THEME
    assert "get_theme_preference" in THEME

def test_classic_theme_remains_supported():
    assert "CRM_THEME_CLASSIC" in PAGE
    assert "if classic:" in PAGE
    assert "theme == CRM_THEME_CLASSIC" in FILTERS
    assert "theme == CRM_THEME_CLASSIC" in TABLE
    assert "self._current_theme == CRM_THEME_CLASSIC" in KANBAN
    assert "self._current_theme == CRM_THEME_CLASSIC" in COLUMN
    assert "theme == CRM_THEME_CLASSIC" in CARD

def test_premium_crm_theme_is_applied_to_all_main_surfaces():
    assert "self.hero_mode_chip" in PAGE
    assert "self.filters_bar.apply_theme(theme)" in PAGE
    assert "self.table.apply_theme(theme)" in PAGE
    assert "self.kanban.apply_theme(theme)" in PAGE
    assert "def showEvent" in PAGE

def test_filters_and_table_are_theme_aware():
    assert "def apply_theme" in FILTERS
    assert "def set_theme_mode" in TABLE
    assert "crm_palette(self.theme_mode)" in TABLE
    assert "row_selected" in TABLE

def test_kanban_components_receive_theme_natively():
    assert "column.apply_theme(self._current_theme)" in KANBAN
    assert "def apply_theme" in COLUMN
    assert "card.apply_theme(self._current_theme)" in COLUMN
    assert "def apply_theme" in CARD
    assert "Source : {source}" in CARD

def test_kanban_drag_drop_contract_is_preserved():
    assert "pipeline_change_requested = Signal(object, str)" in KANBAN
    assert "column.card_dropped.connect(self._handle_card_dropped)" in KANBAN
    assert "self.pipeline_change_requested.emit(prospect_id, pipeline_name)" in KANBAN
    assert "AUTO_SCROLL_MARGIN = 90" in KANBAN
    assert "card_dropped = Signal(object, str)" in COLUMN
    assert "MIME_TYPE = \"application/x-formaprospect-kanban-card\"" in CARD

def test_crm_business_contracts_are_preserved():
    assert "ProspectDialog(" in PAGE
    assert "EnrichmentWorker(" in PAGE
    assert "changer_pipeline_prospect" in PAGE
    assert "_project_scope_id" in PAGE
    assert ".rechercher_prospects_filtres(" in PAGE


def test_crm_premium_polish_uses_compact_command_bar():
    assert "self.command_pagination_frame" in PAGE
    assert "self.pagination_card.setVisible(not premium)" in PAGE
    assert "self.command_pagination_frame.setVisible(premium)" in PAGE
    assert "button.setFixedHeight(36)" in PAGE


def test_kanban_filter_status_is_truthful():
    assert "filters_active=self.filters_bar.filtres_actifs()" in PAGE
    assert "def afficher_lignes(self, prospects, *, filters_active=False)" in KANBAN
    assert 'filter_suffix = "  •  filtres actifs" if filters_active else ""' in KANBAN


def test_kanban_polish_compacts_cards_and_scrollbars():
    assert "_compact_commercial_name" in CARD
    assert "Commercial  •  {self._commercial_display}" in CARD
    assert "setToolTip(self._commercial_raw)" in CARD
    assert "height:5px" in KANBAN
    assert "width:5px" in COLUMN
    assert "_pipeline_accent" in COLUMN
