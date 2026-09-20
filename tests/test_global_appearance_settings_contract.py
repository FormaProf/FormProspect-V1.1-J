from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

THEME_SETTINGS = (ROOT / "core" / "theme_settings.py").read_text(encoding="utf-8")
DIALOG = (ROOT / "ui" / "dialogs" / "appearance_dialog.py").read_text(encoding="utf-8")
PROSPECT = (ROOT / "ui" / "dialogs" / "prospect_dialog.py").read_text(encoding="utf-8")
ACCOUNT = (ROOT / "ui" / "pages" / "account_page.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui" / "windows" / "main_window.py").read_text(encoding="utf-8")


def test_global_theme_sources_are_valid_python():
    for source in (THEME_SETTINGS, DIALOG, PROSPECT, ACCOUNT, MAIN):
        ast.parse(source)


def test_three_product_themes_exist():
    assert 'THEME_CLASSIC = "classic"' in THEME_SETTINGS
    assert 'THEME_UI_LIGHT = "ui_light"' in THEME_SETTINGS
    assert 'THEME_UI_DARK = "ui_dark"' in THEME_SETTINGS


def test_classic_is_safe_default_and_legacy_values_migrate():
    assert 'settings.value("appearance/theme", THEME_CLASSIC)' in THEME_SETTINGS
    assert '"light": THEME_UI_LIGHT' in THEME_SETTINGS
    assert '"dark": THEME_UI_DARK' in THEME_SETTINGS
    assert '"system": THEME_CLASSIC' in THEME_SETTINGS


def test_theme_picker_is_global_not_inside_prospect_dialog():
    assert "AppearanceDialog" in MAIN
    assert 'QAction("Apparence"' in MAIN
    assert "appearance_requested" in ACCOUNT
    assert "theme_selector" not in PROSPECT
    assert "QSettings" not in PROSPECT


def test_prospect_reads_global_theme_and_preserves_business_contracts():
    assert "get_theme_preference()" in PROSPECT
    assert "THEME_CLASSIC" in PROSPECT
    assert "THEME_UI_LIGHT" in PROSPECT
    assert "THEME_UI_DARK" in PROSPECT
    save_block = PROSPECT.split("def enregistrer(self):", 1)[1]
    assert "self.commercial_selector.currentData()" in save_block
    assert "list_prospect_assignment_history" in PROSPECT


def test_appearance_dialog_has_exactly_three_choices():
    assert "THEME_CLASSIC" in DIALOG
    assert "THEME_UI_LIGHT" in DIALOG
    assert "THEME_UI_DARK" in DIALOG
    assert "CLASSIQUE" in DIALOG
    assert "UI CLAIR" in DIALOG
    assert "UI SOMBRE" in DIALOG
