from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "ui" / "pages" / "activity_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui" / "activity_premium_theme.py").read_text(encoding="utf-8")


def test_activity_dual_theme_sources_are_valid_python():
    ast.parse(PAGE)
    ast.parse(THEME)


def test_activity_reads_global_theme_without_reloading_data():
    assert "get_theme_preference()" in PAGE
    show_block = PAGE.split("def showEvent(self, event):", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert "_apply_visual_theme()" in show_block
    assert "ActivityService" not in show_block
    assert "DataSourceResolver" not in show_block
    assert "rafraichir(" not in show_block


def test_activity_keeps_one_structure_for_all_three_themes():
    palette_block = THEME.split("def activity_page_palette(", 1)[1].split(
        "def activity_page_stylesheet", 1
    )[0]
    assert "THEME_UI_DARK" in palette_block
    assert "THEME_UI_LIGHT" in palette_block
    assert "THEME_CLASSIC" in THEME
    assert "QStackedWidget" not in PAGE


def test_activity_dark_palette_is_not_white_surface_based():
    dark_block = THEME.split("DARK = {", 1)[1].split("}", 1)[0]
    assert '"bg": "#06111F"' in dark_block
    assert '"surface": "#0B1A2B"' in dark_block


def test_activity_theme_change_does_not_create_cloud_calls():
    visual_block = PAGE.split("def _apply_visual_theme(self) -> None:", 1)[1].split(
        "def showEvent", 1
    )[0]
    assert "CloudRuntime" not in visual_block
    assert "ActivityService" not in visual_block
