from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

PAGE = (ROOT / "ui/pages/training_cases_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui/training_cases_premium_theme.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def _method_block(source: str, signature: str) -> str:
    return source.split(signature, 1)[1].split("\n    def ", 1)[0]


def test_training_cases_premium_sources_parse():
    for source in (PAGE, THEME, MAIN):
        ast.parse(source)


def test_training_cases_uses_one_structure_for_all_themes():
    build = _method_block(PAGE, "def _build_ui(self) -> None:")
    assert "training_cases_palette(self._theme_mode)" in PAGE
    assert "def _apply_visual_theme(self) -> None:" in PAGE
    assert "self._build_cloud_content()" in build
    assert "self._build_local_content()" in build
    assert "if self._theme_mode" not in build


def test_finance_dashboard_is_a_real_command_center():
    build = _method_block(PAGE, "def _build_ui(self) -> None:")
    cockpit = _method_block(PAGE, "def _build_finance_cockpit(self) -> QWidget:")
    refresh = _method_block(PAGE, "def _refresh_kpis(self) -> None:")

    assert "self.finance_cockpit = self._build_finance_cockpit()" in build
    assert 'QLabel("POSITION FINANCIÈRE")' in cockpit
    assert 'QLabel("ACTIONS IMMÉDIATES")' in cockpit
    assert 'QLabel("FLUX FINANCIER")' in cockpit
    assert '"pending", "Demandées"' in cockpit
    assert '"preparing", "Préparation"' in cockpit
    assert '"available", "Disponibles"' in cockpit
    assert '"closed", "Clôturées"' in cockpit
    assert "active_value_cents" in refresh
    assert 'self.cloud_tabs.addTab(docs_page, "Documents disponibles")' in PAGE
    assert 'self.cloud_tabs.addTab(requests_page, "Demandes de documents")' in PAGE


def test_finance_page_has_compact_empty_states_instead_of_blank_tables():
    assert "self.cloud_empty_state" in PAGE
    assert "self.cloud_request_empty_state" in PAGE
    assert "self.case_empty_state" in PAGE
    assert "self.quote_empty_state" in PAGE
    assert "self.cloud_table.setVisible(has_documents)" in PAGE
    assert "self.cloud_request_table.setVisible(has_requests)" in PAGE


def test_theme_switch_only_restyles_existing_training_cases_page():
    block = _method_block(MAIN, "def _sync_commercial_project_theme_pages(self):")
    assert '"training_cases_page"' in block
    assert "_apply_visual_theme" in block
    assert "TrainingCasesPage(" not in block
    assert "deleteLater" not in block


def test_training_cases_theme_supports_light_and_dark_without_network_logic():
    assert "THEME_UI_DARK" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert '"page": "#07101A"' in THEME
    assert '"page": "#F4F8FC"' in THEME
    assert '"primary": "#338CE4"' in THEME
    assert "CloudRuntime" not in THEME
    assert "api." not in THEME


def test_finance_kpis_reuse_loaded_data_without_new_api_calls():
    block = _method_block(PAGE, "def _refresh_kpis(self) -> None:")
    assert "self.cloud_documents" in block
    assert "self.cloud_quote_requests" in block
    assert "self.case_rows" in block
    assert "self.quote_rows" in block
    assert "CloudRuntime" not in block
    assert ".api()" not in block


def test_finance_cockpit_uses_loaded_data_only():
    block = _method_block(PAGE, "def _refresh_kpis(self) -> None:")
    assert "price_cents" in block
    assert "self.cloud_documents" in block
    assert "self.cloud_quote_requests" in block
    assert "CloudRuntime" not in block
    assert ".api()" not in block


def test_finance_theme_has_cockpit_specific_surfaces():
    assert 'QFrame[financeHeroCard="true"]' in THEME
    assert 'QFrame[financeActionCard="true"]' in THEME
    assert 'QFrame[financeFlowCard="true"]' in THEME
    assert 'QLabel[financeHeroValue="true"]' in THEME


def test_finance_cloud_workspace_uses_premium_segmented_navigation():
    cloud = _method_block(PAGE, "def _build_cloud_content(self) -> QWidget:")
    assert 'workspace_nav.setProperty("financeWorkspaceNav", True)' in cloud
    assert 'setProperty("financeWorkspaceButton", True)' in cloud
    assert "self.cloud_tabs.tabBar().hide()" in cloud
    assert "self.cloud_tabs.currentChanged.connect(self._sync_cloud_workspace_navigation)" in cloud
    assert 'self.cloud_tabs.addTab(docs_page, "Documents disponibles")' in cloud
    assert 'self.cloud_tabs.addTab(requests_page, "Demandes de documents")' in cloud


def test_finance_cloud_workspaces_have_premium_headers_and_toolbars():
    docs = _method_block(PAGE, "def _build_cloud_documents_tab(self) -> QWidget:")
    requests = _method_block(PAGE, "def _build_cloud_requests_tab(self) -> QWidget:")

    for block in (docs, requests):
        assert 'setProperty("financeWorkspaceHeader", True)' in block
        assert 'setProperty("financeWorkspaceIcon", True)' in block
        assert 'setProperty("financeToolbar", True)' in block
        assert 'setProperty("financeToolbarLabel", True)' in block
        assert 'setProperty("financeToolbarDivider", True)' in block
        assert 'setProperty("financeCompactEmpty", True)' in block

    assert "setMinimumHeight(104)" in docs
    assert "setMaximumHeight(122)" in docs
    assert "setMinimumHeight(104)" in requests
    assert "setMaximumHeight(122)" in requests


def test_finance_theme_styles_premium_workspace_components():
    assert 'QFrame[financeWorkspaceNav="true"]' in THEME
    assert 'QPushButton[financeWorkspaceButton="true"]:checked' in THEME
    assert 'QFrame[financeWorkspaceHeader="true"]' in THEME
    assert 'QLabel[financeWorkspaceIcon="true"]' in THEME
    assert 'QFrame[financeToolbar="true"]' in THEME
    assert 'QLabel[financeToolbarLabel="true"]' in THEME
    assert 'QFrame[financeToolbarDivider="true"]' in THEME


def test_finance_cloud_workspace_scrolls_instead_of_compressing_content():
    cloud = _method_block(PAGE, "def _build_cloud_content(self) -> QWidget:")
    assert "QScrollArea" in PAGE
    assert 'self.cloud_workspace_scroll.setObjectName("FinanceWorkspaceScroll")' in cloud
    assert "self.cloud_workspace_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in cloud
    assert "self.cloud_tabs.setMinimumHeight(590)" in cloud
    assert "setMaximumHeight(430)" not in cloud
    assert "layout.addWidget(self.cloud_workspace_scroll, 1)" in cloud


def test_finance_cloud_toolbars_keep_rows_separated():
    docs = _method_block(PAGE, "def _build_cloud_documents_tab(self) -> QWidget:")
    requests = _method_block(PAGE, "def _build_cloud_requests_tab(self) -> QWidget:")
    for block in (docs, requests):
        assert "search_row = QHBoxLayout()" in block
        assert "filter_row = QHBoxLayout()" in block
        assert "filters.setMinimumHeight(170)" in block
        assert "setMinimumHeight(220)" in block
    assert 'QScrollArea#FinanceWorkspaceScroll QScrollBar:vertical' in THEME
