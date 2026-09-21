from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

MAIN = (ROOT / "ui" / "windows" / "main_window.py").read_text(encoding="utf-8")
NATIVE = (ROOT / "ui" / "native_window_theme.py").read_text(encoding="utf-8")


def test_window_chrome_sources_parse():
    ast.parse(MAIN)
    ast.parse(NATIVE)


def test_mainwindow_applies_qt_and_native_chrome_from_same_theme():
    block = MAIN.split("def _apply_native_window_theme(self):", 1)[1].split(
        "def showEvent(self, event):", 1
    )[0]
    assert "mode = get_theme_preference()" in block
    assert "apply_qt_window_chrome(self, mode)" in block
    assert "apply_native_window_theme(self, mode)" in block


def test_qt_chrome_styles_menubar_menus_and_statusbar():
    assert "def apply_qt_window_chrome(window, mode: str) -> None:" in NATIVE
    assert "window.menuBar()" in NATIVE
    assert "window.statusBar()" in NATIVE
    assert "QMenuBar::item:selected" in NATIVE
    assert "QMenu::item:selected" in NATIVE
    assert "QStatusBar" in NATIVE


def test_dark_chrome_matches_ai_command_center_palette():
    assert 'menu_bg = "#06111F"' in NATIVE
    assert 'popup_bg = "#0B1A2B"' in NATIVE
    assert 'menu_selected = "#12365B"' in NATIVE
    assert 'status_bg = "#06111F"' in NATIVE


def test_classic_theme_clears_added_chrome_styles():
    assert 'menu_bar.setStyleSheet("")' in NATIVE
    assert 'status_bar.setStyleSheet("")' in NATIVE


def test_theme_change_and_showevent_reuse_same_chrome_entrypoint():
    appearance = MAIN.split("def ouvrir_apparence(self):", 1)[1].split(
        "def _refresh_connected_profile(self):", 1
    )[0]
    show = MAIN.split("def showEvent(self, event):", 1)[1].split(
        "def resizeEvent(self, event):", 1
    )[0]
    assert "self._apply_native_window_theme()" in appearance
    assert "QTimer.singleShot(0, self._apply_native_window_theme)" in show
