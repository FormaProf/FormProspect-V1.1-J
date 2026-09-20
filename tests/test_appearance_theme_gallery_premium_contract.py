from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
DIALOG = (ROOT / "ui" / "dialogs" / "appearance_dialog.py").read_text(encoding="utf-8")


def test_premium_gallery_source_is_valid_python():
    ast.parse(DIALOG)


def test_gallery_has_visual_preview_cards_for_three_themes():
    assert "class ThemePreviewCard" in DIALOG
    assert "THEME_CATALOG" in DIALOG
    assert '"ORIGINAL"' in DIALOG
    assert '"PREMIUM"' in DIALOG
    assert '"AI PREMIUM"' in DIALOG
    assert "ThemeMiniPreview" in DIALOG
    assert 'THEME_CLASSIC: "CLASSIQUE"' in DIALOG
    assert 'THEME_UI_LIGHT: "UI CLAIR"' in DIALOG
    assert 'THEME_UI_DARK: "UI SOMBRE"' in DIALOG


def test_gallery_has_real_hover_motion_and_selection_states():
    assert "QGraphicsDropShadowEffect" in DIALOG
    assert "QPropertyAnimation" in DIALOG
    assert "def enterEvent" in DIALOG
    assert "def leaveEvent" in DIALOG
    assert 'setProperty("selected"' in DIALOG
    assert 'setProperty("active"' in DIALOG
    assert "✓ THÈME ACTIF" in DIALOG
    assert "✓ Sélectionné" in DIALOG


def test_active_theme_cannot_be_reapplied_and_save_contract_is_preserved():
    assert "self.save_button.setDisabled(is_current)" in DIALOG
    assert '"Thème déjà actif" if is_current else "Utiliser ce thème"' in DIALOG
    assert "set_theme_preference(self._selected_theme)" in DIALOG
    assert "self.accept()" in DIALOG
    assert "def selected_theme" in DIALOG
