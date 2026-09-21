from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


PAGE = source("ui/pages/dashboard_page.py")
THEME = source("ui/dashboard_premium_theme.py")
CHARTS = source("ui/widgets/dashboard_charts.py")
MAIN = source("ui/windows/main_window.py")


def test_dashboard_v2_sources_are_valid_python():
    for code in (PAGE, THEME, CHARTS, MAIN):
        ast.parse(code)


def test_dashboard_uses_one_structural_layout_for_all_three_themes():
    assert "THEME_CLASSIC" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert "THEME_UI_DARK" in THEME
    build = PAGE.split("def _build_ui(self):", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    assert "THEME_CLASSIC" not in build
    assert "THEME_UI_LIGHT" not in build
    assert "THEME_UI_DARK" not in build
    assert "if self._theme_mode" not in build


def test_quote_stays_above_kpis_and_command_center():
    build = PAGE.split("def _build_ui(self):", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    quote = build.index("root.addWidget(self._build_quote_card())")
    kpis = build.index("kpi_grid = QGridLayout()")
    command = build.index("command_grid = QGridLayout()")
    assert quote < kpis < command


def test_dashboard_v2_is_compact_and_keeps_core_metrics():
    assert "setMinimumHeight(96)" in PAGE
    for key in (
        '"prospects"',
        '"telephones"',
        '"emails"',
        '"sites"',
        '"average_prospect_score"',
        '"annual_revenue"',
    ):
        assert key in PAGE
    assert "_build_pipeline_card()" in PAGE
    assert "_build_actions_card()" in PAGE
    assert "_build_enrichment_card()" in PAGE
    assert "_build_scoring_card()" in PAGE
    assert "_build_recent_activity_card()" in PAGE


def test_dashboard_theme_switch_is_in_place_without_reload_contract():
    assert "def _apply_visual_theme(self):" in PAGE
    assert "dashboard_stylesheet(self._theme_mode)" in PAGE
    assert "apply_theme(self._theme_mode)" in PAGE
    sync = MAIN.split(
        "def _sync_commercial_project_theme_pages(self):",
        1,
    )[1].split("\n    def ", 1)[0]
    assert '"dashboard_page"' in sync
    assert "_apply_visual_theme" in sync
    assert "deleteLater" not in sync


def test_dashboard_charts_are_theme_aware():
    assert "dashboard_palette" in CHARTS
    assert CHARTS.count("def apply_theme") >= 2
    assert 'self._palette["track"]' in CHARTS
    assert 'self._palette["primary"]' in CHARTS
    assert 'self._palette["text"]' in CHARTS


def test_dashboard_does_not_add_new_data_loads_to_build_or_theme_switch():
    build = PAGE.split("def _build_ui(self):", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    theme = PAGE.split("def _apply_visual_theme(self):", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    forbidden = (
        "get_dashboard_data(",
        "list_cloud_sales(",
        "CloudRuntime.api(",
        "ActivityService.list_events(",
    )
    for token in forbidden:
        assert token not in build
        assert token not in theme


def test_dashboard_new_pipeline_stage_uses_brand_blue():
    assert 'color = "#338CE4" if is_new else PIPELINE_COLORS.get' in PAGE
    assert 'style="color:#338CE4;font-size:12px;">■</span>' in PAGE
    assert 'display_name.replace("🟢", "")' in PAGE


def test_dashboard_empty_health_row_is_compact_but_restores_for_active_project():
    assert "def _set_health_compact(self, compact: bool) -> None:" in PAGE
    assert "self.quality_donut.setMinimumHeight(78)" in PAGE
    assert "self.quality_donut.setMaximumHeight(90)" in PAGE
    assert "self._set_health_compact(True)" in PAGE
    assert "self._set_health_compact(False)" in PAGE
    assert "self.contact_empty.setFixedHeight(38)" in PAGE
