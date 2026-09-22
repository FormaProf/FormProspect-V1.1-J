from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "ui" / "pages" / "activity_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui" / "activity_premium_theme.py").read_text(encoding="utf-8")


def test_activity_premium_sources_are_valid_python():
    ast.parse(PAGE)
    ast.parse(THEME)


def test_activity_page_uses_command_center_structure():
    assert "ACTIVITY COMMAND CENTER" in PAGE
    assert 'setObjectName("ActivityPageRoot")' in PAGE
    assert 'setObjectName("ActivityHero")' in PAGE
    assert 'setObjectName("ActivityFeed")' in PAGE
    assert 'setObjectName("ActivityFilterCombo")' in PAGE
    assert 'setObjectName("ActivityCountBadge")' in PAGE
    assert 'setObjectName("ActivityEventCard")' in PAGE


def test_activity_page_theme_switch_is_visual_only():
    assert "activity_page_palette" in PAGE
    assert "activity_page_stylesheet" in PAGE
    visual_block = PAGE.split("def _apply_visual_theme(self) -> None:", 1)[1].split(
        "def showEvent", 1
    )[0]
    assert "ActivityService" not in visual_block
    assert "DataSourceResolver" not in visual_block
    assert "rafraichir(" not in visual_block


def test_activity_business_loading_contract_is_preserved():
    assert "self.datasource_resolver.resolve()" in PAGE
    assert "if context.is_cloud:" in PAGE
    assert "ActivityService.list_events(" in PAGE
    assert "project=project" in PAGE
    assert "limit=500" in PAGE
    assert "self.filter_combo.currentData()" in PAGE
    assert 'event.get("category") == selected' in PAGE


def test_cloud_workspace_does_not_read_local_activity_service():
    cloud_block = PAGE.split("if context.is_cloud:", 1)[1].split(
        "project = active_project or ApplicationState.get_project()", 1
    )[0]
    assert "ActivityService.list_events" not in cloud_block
    assert "self.events = []" in cloud_block


def test_activity_kpis_keep_existing_semantics():
    assert 'commercial_categories = {"general", "enrichment", "import"}' in PAGE
    assert 'system_categories = {"project", "backup", "restore"}' in PAGE
    for key in ("today", "week", "commercial", "system"):
        assert f'self.kpi_values["{key}"]' in PAGE


def test_activity_event_semantics_are_preserved():
    for category in (
        '"project": "Projet"',
        '"import": "Import"',
        '"enrichment": "Enrichissement"',
        '"backup": "Sauvegarde"',
        '"restore": "Restauration"',
        '"general": "Général"',
    ):
        assert category in PAGE
    for level in ('"success"', '"warning"', '"error"', '"info"'):
        assert level in PAGE


def test_activity_theme_module_exposes_page_palette_and_qss():
    assert "def activity_page_palette(" in THEME
    assert "def activity_page_stylesheet(" in THEME
    assert "QWidget#ActivityPageRoot" in THEME
    assert "QFrame#ActivityHero" in THEME
    assert "QFrame#ActivityEventCard" in THEME
