from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "ui" / "windows" / "main_window.py"
RESPONSIVE = ROOT / "ui" / "responsive_layout.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_responsive_module_is_syntax_valid_and_business_neutral():
    source = _source(RESPONSIVE)
    ast.parse(source)
    assert "class ResponsivePageHost(QScrollArea)" in source
    assert "class ResponsiveManager(QObject)" in source
    assert "class ResponsiveStackedWidget(QStackedWidget)" in source
    assert "CloudRuntime" not in source
    assert "CloudAPI" not in source
    assert "rafraichir(" not in source
    assert "refresh_data(" not in source


def test_main_window_keeps_one_stacked_workspace_for_all_tabs():
    source = _source(MAIN)
    ast.parse(source)
    assert "self.pages = ResponsiveStackedWidget()" in source
    assert "self.page_host = ResponsivePageHost(self.pages)" in source
    assert "layout.addWidget(self.page_host, 1)" in source
    assert "self.responsive_manager = ResponsiveManager(" in source
    # Campaigns / sequences remain ordinary pages inside the same responsive stack.
    assert "self.pages.addWidget(page)" in source
    assert "self.campaigns_page = CampaignsPage()" in source
    assert "self.sequences_page = SequencesPage()" in source


def test_responsive_host_does_not_wrap_or_reparent_individual_pages():
    source = _source(RESPONSIVE)
    # Only the QStackedWidget itself is installed in the global scroll host.
    assert "self.setWidget(self.stack)" in source
    assert "page.setParent" not in source
    assert "setWidget(page)" not in source
    assert "takeAt(" not in source
    assert "setLayout(" not in source


def test_scroll_fallback_is_enabled_in_both_directions():
    source = _source(RESPONSIVE)
    assert "setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in source
    assert "setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in source
    assert "required.height() > viewport.height()" in source
    assert "required.width() > viewport.width()" in source


def test_responsive_density_restores_desktop_values_exactly():
    source = _source(RESPONSIVE)
    assert "layout.setContentsMargins(left, top, right, bottom)" in source
    assert "layout.setSpacing(original_spacing)" in source
    assert "DESKTOP = \"desktop\"" in source
    assert "LAPTOP = \"laptop\"" in source
    assert "COMPACT = \"compact\"" in source


def test_initial_window_is_capped_to_real_available_geometry():
    main_source = _source(MAIN)
    responsive_source = _source(RESPONSIVE)
    assert "fit_window_to_available_geometry(self, WINDOW_WIDTH, WINDOW_HEIGHT)" in main_source
    assert "availableGeometry()" in responsive_source


def test_page_themes_are_not_rewritten_by_the_responsive_layer():
    source = _source(RESPONSIVE)
    # The only stylesheet is scoped to the host itself; there are no broad
    # QWidget/QFrame rules capable of overriding premium page themes.
    assert 'QScrollArea#ResponsivePageHost' in source
    assert 'QWidget {' not in source
    assert 'QFrame {' not in source
    assert 'QLabel {' not in source
    assert 'QPushButton {' not in source
    assert '.setFixedWidth(' not in source
