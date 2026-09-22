from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
AGENDA = (ROOT / "ui/pages/agenda_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui/agenda_premium_theme.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def _method_block(source: str, signature: str) -> str:
    return source.split(signature, 1)[1].split("\n    def ", 1)[0]


def test_agenda_premium_sources_parse():
    for source in (AGENDA, THEME, MAIN):
        ast.parse(source)


def test_agenda_uses_one_structure_for_all_three_themes():
    build = _method_block(AGENDA, "def _build_ui(self):")
    assert "get_theme_preference" not in build
    assert "THEME_CLASSIC" not in build
    assert "THEME_UI_LIGHT" not in build
    assert "THEME_UI_DARK" not in build
    assert 'setObjectName("AgendaHeader")' in build
    assert 'setObjectName("AgendaPanel")' in build
    assert 'setObjectName("AgendaEmptyState")' in build


def test_agenda_theme_switch_is_in_place_and_never_loads_cloud_data():
    block = _method_block(AGENDA, "def _apply_visual_theme(self):")
    assert "agenda_palette(get_theme_preference())" in block
    assert "agenda_page_stylesheet" in block
    assert "agenda_calendar_stylesheet" in block
    assert "agenda_table_stylesheet" in block
    assert "_render_calendar_marks()" in block
    assert "_build_ui(" not in block
    assert "rafraichir(" not in block
    assert "ensure_loaded(" not in block
    assert "CloudRuntime" not in block
    assert "AgendaService" not in block


def test_calendar_retheme_uses_cached_marks_only():
    init = _method_block(AGENDA, "def __init__(self):")
    render = _method_block(AGENDA, "def _render_calendar_marks(self)")
    refresh = _method_block(AGENDA, "def refresh_calendar_marks(self, *_args)")
    assert "self._calendar_counts: dict[date, int] = {}" in init
    assert "self._calendar_counts.items()" in render
    assert "get_month_counts" not in render
    assert "CloudRuntime" not in render
    assert "self._calendar_counts = counts" in refresh


def test_agenda_keeps_lazy_background_cloud_loading_contract():
    init = _method_block(AGENDA, "def __init__(self):")
    assert "self.rafraichir()" not in init
    assert "self._cache_ttl_seconds = 300.0" in init
    assert "threading.Thread(" in AGENDA
    assert "cloud_refresh_ready = Signal()" in AGENDA
    assert "self._load_cloud_actions()" in AGENDA


def test_agenda_empty_day_is_compact_and_action_buttons_follow_data_state():
    load = _method_block(AGENDA, "def load_selected_day(self)")
    assert "self.table.setVisible(action_count > 0)" in load
    assert "self.empty_state.setVisible(action_count == 0)" in load
    assert "button.setEnabled(action_count > 0)" in load


def test_agenda_uses_semantic_action_mark_colors():
    render = _method_block(AGENDA, "def _render_calendar_marks(self)")
    assert 'palette["danger_soft"]' in render
    assert 'palette["primary"]' in render
    assert 'palette["primary_soft"]' in render


def test_main_window_rethemes_existing_agenda_without_rebuild():
    block = _method_block(MAIN, "def _sync_commercial_project_theme_pages(self):")
    assert '"agenda_page"' in block
    assert "_apply_visual_theme" in block
    assert "AgendaPage(" not in block
    assert "deleteLater" not in block


def test_agenda_theme_defines_classic_light_and_dark_palettes():
    assert "THEME_UI_DARK" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert 'return {' in THEME
    assert '"primary": "#338CE4"' in THEME


def test_agenda_dark_mode_styles_calendar_internal_surfaces():
    apply_block = _method_block(AGENDA, "def _apply_visual_theme(self):")
    calendar_block = _method_block(
        AGENDA,
        "def _apply_calendar_palette(self, palette: dict[str, str])",
    )
    assert "self._apply_calendar_palette(palette)" in apply_block
    assert "QPalette.Base" in calendar_block
    assert "QPalette.AlternateBase" in calendar_block
    assert "setHeaderTextFormat" in calendar_block
    assert "setWeekdayTextFormat" in calendar_block
    assert 'palette["calendar_header_bg"]' in calendar_block
    assert 'palette["calendar_weekend"]' in calendar_block


def test_agenda_dark_palette_is_neutral_and_keeps_formaprospect_blue():
    assert '"page": "#07101A"' in THEME
    assert '"card": "#0D1826"' in THEME
    assert '"primary": "#338CE4"' in THEME
    assert '"calendar_header_bg": "#0B1725"' in THEME
