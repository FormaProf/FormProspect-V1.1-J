from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS = (ROOT / "ui/pages/documents_page.py").read_text(encoding="utf-8")
THEME = (ROOT / "ui/documents_premium_theme.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def _method_block(source: str, signature: str) -> str:
    return source.split(signature, 1)[1].split("\n    def ", 1)[0]


def test_documents_premium_sources_parse():
    for source in (DOCUMENTS, THEME, MAIN):
        ast.parse(source)


def test_documents_keep_one_structure_for_all_themes():
    build = _method_block(DOCUMENTS, "def _build_ui(self):")
    assert "DocumentsHeader" in build
    assert "self.cloud_content = self._build_cloud_content()" in build
    assert "self.tabs = QTabWidget()" in build
    assert "if self._theme_mode" not in build


def test_documents_cloud_workspace_has_command_center_and_library():
    cloud = _method_block(DOCUMENTS, "def _build_cloud_content(self)")
    assert "DocumentsCommandCard" in cloud
    assert "CENTRE DOCUMENTAIRE" in cloud
    assert "Créer & déposer" in cloud
    assert "DocumentsLibraryCard" in cloud
    assert "BIBLIOTHÈQUE CLOUD" in cloud
    assert "DocumentsLibraryEmpty" in cloud
    assert "Votre bibliothèque est prête" in cloud


def test_documents_cloud_empty_state_replaces_empty_table():
    load = _method_block(DOCUMENTS, "def _load_cloud_documents(self, *_args)")
    assert "has_documents = count > 0" in load
    assert "self.cloud_table.setVisible(has_documents)" in load
    assert "self.cloud_empty_state.setVisible(not has_documents)" in load
    assert "self.cloud_actions_bar.setVisible(has_documents)" in load


def test_documents_cloud_command_center_has_four_metrics():
    cloud = _method_block(DOCUMENTS, "def _build_cloud_content(self)")
    for key in ("documents", "generated", "uploaded", "signed"):
        assert f'("{key}",' in cloud


def test_documents_theme_switch_is_in_place_without_refresh_or_cloud_calls():
    block = _method_block(DOCUMENTS, "def _apply_visual_theme(self):")
    assert "get_theme_preference()" in block
    assert "documents_page_stylesheet" in block
    assert "documents_table_stylesheet" in block
    assert "self.rafraichir()" not in block
    assert "CloudRuntime" not in block
    assert "_load_cloud_documents" not in block


def test_documents_light_mode_is_not_a_dark_slab():
    assert '"card": "#FFFFFF"' in THEME
    assert '"table_header": "#F1F5F9"' in THEME
    assert '"header_a": "#0B223A"' in THEME
    assert '"header_text": "#FFFFFF"' in THEME


def test_documents_dark_palette_stays_native_and_keeps_brand_blue():
    assert '"page": "#07101A"' in THEME
    assert '"card": "#0D1826"' in THEME
    assert '"primary": "#338CE4"' in THEME


def test_main_window_rethemes_documents_without_rebuild():
    sync = _method_block(
        MAIN,
        "def _sync_commercial_project_theme_pages(self):",
    )
    assert '"documents_page"' in sync
    assert "DocumentsPage(" not in sync
    assert "deleteLater" not in sync
