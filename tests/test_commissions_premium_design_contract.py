from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

PAGE = (ROOT / "ui/pages/commissions_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui/commissions_premium_theme.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def _method_block(source: str, signature: str) -> str:
    start = source.index(signature)
    next_method = source.find("\n    def ", start + len(signature))
    if next_method < 0:
        return source[start:]
    return source[start:next_method]


def test_commissions_sources_parse():
    for source in (PAGE, THEME, MAIN):
        ast.parse(source)


def test_commissions_layout_is_dense_and_theme_independent():
    build = _method_block(PAGE, "def _build_ui(self) -> None:")
    assert 'header_card.setObjectName("SalesHeader")' in build
    assert 'cards.addWidget(card, 0, index)' in build
    assert 'table_frame.setObjectName("SalesTableCard")' in build
    assert 'footer_card.setObjectName("SalesFooter")' in build
    assert "THEME_UI_DARK" not in build
    assert "THEME_UI_LIGHT" not in build


def test_commissions_theme_switch_is_in_place_without_cloud_reload():
    apply_block = _method_block(PAGE, "def _apply_visual_theme(self) -> None:")
    assert "get_theme_preference()" in apply_block
    assert "commissions_page_stylesheet" in apply_block
    assert "commissions_table_stylesheet" in apply_block
    assert "_restyle_table_badges()" in apply_block
    assert "rafraichir(" not in apply_block
    assert "CloudRuntime.api()" not in apply_block
    assert "get_cloud_sales_summary" not in apply_block
    assert "list_cloud_sales" not in apply_block


def test_commissions_has_compact_empty_state_and_one_row_kpis():
    assert 'self.empty_state.setObjectName("SalesEmptyState")' in PAGE
    assert "self.table.setVisible(has_rows)" in PAGE
    assert "self.empty_state.setVisible(not has_rows)" in PAGE
    assert 'self.period_summary.setText(' in PAGE
    assert 'f"{count} vente"' in PAGE
    assert 'f"{count} ventes"' in PAGE


def test_commissions_dark_palette_keeps_brand_blue_and_semantic_badges():
    assert '"page": "#07101A"' in THEME
    assert '"card": "#0D1826"' in THEME
    assert '"primary": "#338CE4"' in THEME
    assert '"success_bg": "#102D27"' in THEME
    assert '"warning_bg": "#332A16"' in THEME
    assert '"danger_bg": "#351923"' in THEME
    assert '"violet_bg": "#24203F"' in THEME


def test_commissions_is_part_of_global_in_place_theme_sync():
    sync = _method_block(
        MAIN,
        "def _sync_commercial_project_theme_pages(self):",
    )
    assert '"dashboard_page"' in sync
    assert '"agenda_page"' in sync
    assert '"commissions_page"' in sync
    assert 'apply_theme = getattr(page, "_apply_visual_theme", None)' in sync


def test_commissions_business_cloud_calls_are_unchanged_in_refresh():
    refresh = _method_block(PAGE, "def rafraichir(self, *_args) -> None:")
    assert "api.get_cloud_sales_summary(year=year, month=month)" in refresh
    assert "api.list_cloud_sales(year=year, month=month)" in refresh
    assert "self._update_table_empty_state()" in refresh
