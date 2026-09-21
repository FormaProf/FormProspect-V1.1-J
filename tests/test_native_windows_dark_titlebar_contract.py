from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

MAIN = (ROOT / "ui" / "windows" / "main_window.py").read_text(encoding="utf-8")
NATIVE = (ROOT / "ui" / "native_window_theme.py").read_text(encoding="utf-8")


def test_native_titlebar_sources_are_valid_python():
    ast.parse(MAIN)
    ast.parse(NATIVE)


def test_windows_dark_titlebar_uses_supported_dwm_attributes():
    assert "_DWMWA_USE_IMMERSIVE_DARK_MODE = 20" in NATIVE
    assert "_DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19" in NATIVE
    assert "DwmSetWindowAttribute" in NATIVE
    assert "SetWindowPos" in NATIVE
    assert "_SWP_FRAMECHANGED" in NATIVE


def test_titlebar_follows_only_ui_dark_and_resets_for_other_themes():
    assert "normalize_theme_mode(mode) == THEME_UI_DARK" in NATIVE
    assert "ctypes.c_int(1 if dark else 0)" in NATIVE


def test_mainwindow_applies_native_theme_after_hwnd_exists():
    assert "def _apply_native_window_theme(self):" in MAIN
    assert "def showEvent(self, event):" in MAIN
    show_block = MAIN.split("def showEvent(self, event):", 1)[1].split(
        "def resizeEvent(self, event):", 1
    )[0]
    assert "QTimer.singleShot(0, self._apply_native_window_theme)" in show_block
    assert "QTimer.singleShot(120, self._apply_native_window_theme)" in show_block


def test_appearance_change_reapplies_native_titlebar_immediately():
    block = MAIN.split("def ouvrir_apparence(self):", 1)[1].split(
        "def _refresh_connected_profile(self):", 1
    )[0]
    assert "self._apply_native_window_theme()" in block
    assert "QTimer.singleShot(120, self._apply_native_window_theme)" in block
