from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMERCIAL = (ROOT / "ui/pages/commercial_projects_page.py").read_text(encoding="utf-8")
ADMIN = (ROOT / "ui/pages/admin_commercial_projects_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui/commercial_projects_theme.py").read_text(encoding="utf-8")
AGENDA = (ROOT / "ui/pages/agenda_page.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")
DASHBOARD = (ROOT / "ui/pages/dashboard_page.py").read_text(encoding="utf-8")


def _method_block(source: str, signature: str) -> str:
    return source.split(signature, 1)[1].split("\n    def ", 1)[0]


def test_project_pages_use_one_structural_layout_for_all_themes():
    assert "self._classic_mode = False" in COMMERCIAL
    assert "self._build_premium_ui()" in _method_block(COMMERCIAL, "def __init__(")
    assert "self._classic_mode = False" in ADMIN
    assert 'if mode == THEME_CLASSIC:\n        return ""' not in THEME
    assert "return True" in _method_block(THEME, "def premium_projects_enabled(")


def test_theme_switch_updates_existing_project_pages_without_rebuild():
    block = _method_block(MAIN, "def _sync_commercial_project_theme_pages(self):")
    assert "_apply_visual_theme" in block
    assert "AdminCommercialProjectsPage(" not in block
    assert "CommercialProjectsPage(" not in block
    assert "deleteLater" not in block


def test_commercial_landing_action_is_prominent():
    assert "🚀  Ma Landing Page" in COMMERCIAL
    assert "QPushButton#ProjectLandingAction" in THEME
    assert "min-height:38px" in THEME


def test_agenda_is_lazy_cached_and_cloud_refresh_is_backgrounded():
    init = _method_block(AGENDA, "def __init__(self):")
    assert "self.rafraichir()" not in init
    assert "self._cache_ttl_seconds = 300.0" in init
    assert "def ensure_loaded(" in AGENDA
    assert "threading.Thread(" in AGENDA
    assert "cloud_refresh_ready = Signal()" in AGENDA
    assert "self._load_cloud_actions()" in AGENDA


def test_agenda_navigation_displays_page_before_refresh():
    block = _method_block(MAIN, "def ouvrir_agenda(self):")
    assert block.index("setCurrentWidget") < block.index("ensure_loaded")


def test_dashboard_keeps_dense_layout_and_weekly_quote_near_top():
    build = _method_block(DASHBOARD, "def _build_ui(self):")
    quote_pos = build.index("root.addWidget(self._build_quote_card())")
    insights_pos = build.index("insight_grid = QGridLayout()")
    assert quote_pos < insights_pos
