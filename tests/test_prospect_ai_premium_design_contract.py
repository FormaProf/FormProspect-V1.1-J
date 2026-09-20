from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
DIALOG = (ROOT / "ui" / "dialogs" / "prospect_dialog.py").read_text(
    encoding="utf-8"
)
THEME = (ROOT / "ui" / "ai_premium_theme.py").read_text(
    encoding="utf-8"
)


def test_ai_premium_sources_are_valid_python():
    ast.parse(DIALOG)
    ast.parse(THEME)


def test_prospect_dialog_uses_ai_premium_design_system():
    assert "from ui.ai_premium_theme import (" in DIALOG
    assert "AIPremiumCard" in DIALOG
    assert "AI SALES COMMAND CENTER" in DIALOG
    assert "AI PREMIUM EXPERIENCE" in DIALOG


def test_premium_cards_have_real_hover_animation():
    assert "class AIPremiumCard" in THEME
    assert "QGraphicsDropShadowEffect" in THEME
    assert "QPropertyAnimation" in THEME
    assert "def enterEvent" in THEME
    assert "def leaveEvent" in THEME
    assert 'setProperty("hovered", hovered)' in THEME


def test_owner_uuid_hotfix_is_preserved():
    save_block = DIALOG.split("def enregistrer(self):", 1)[1]
    assert "self.commercial_selector.currentData()" in save_block


def test_cloud_history_and_save_contracts_are_preserved():
    assert "list_prospect_assignment_history" in DIALOG
    assert "self.prospect_service.mettre_a_jour_contact(" in DIALOG
    assert "CloudRuntime.api().update_prospect(" in DIALOG
