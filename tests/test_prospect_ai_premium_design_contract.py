from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
DIALOG = (ROOT / "ui" / "dialogs" / "prospect_dialog.py").read_text(
    encoding="utf-8"
)
THEME = (ROOT / "ui" / "ai_premium_theme.py").read_text(
    encoding="utf-8"
)

ASSISTANT = (ROOT / "ui" / "pages" / "ai_assistant_page.py").read_text(
    encoding="utf-8"
)


def test_ai_premium_sources_are_valid_python():
    ast.parse(DIALOG)
    ast.parse(THEME)
    ast.parse(ASSISTANT)


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


def test_ai_assistant_uses_command_center_design_system():
    assert "AI COMMAND CENTER" in ASSISTANT
    assert 'setObjectName("AIAssistantRoot")' in ASSISTANT
    assert 'setObjectName("AiRadarCard")' in ASSISTANT
    assert 'setObjectName("AiConsole")' in ASSISTANT
    assert 'setObjectName("AiToolsShell")' in ASSISTANT
    assert 'setObjectName("AiOutputCard")' in ASSISTANT
    assert 'setProperty("aiFeedCard", True)' in ASSISTANT


def test_ai_assistant_theme_switch_is_visual_only():
    assert "assistant_page_palette" in ASSISTANT
    assert "assistant_page_stylesheet" in ASSISTANT
    visual_block = ASSISTANT.split("def _apply_visual_theme(self) -> None:", 1)[1].split(
        "def showEvent", 1
    )[0]
    assert "CloudRuntime" not in visual_block
    assert "self.service" not in visual_block
    assert "_load_prospects" not in visual_block
    assert "_load_insights" not in visual_block
    assert "_load_history" not in visual_block


def test_ai_assistant_business_actions_are_preserved():
    for token in (
        "self.open_prospect_copilot",
        "self.open_automatic_qualification",
        "self.prepare_call",
        "self.explain_score",
        "self.recommend_action",
        "self.generate_call_script",
        "self.generate_email",
        "self.generate_objections",
        "self.generate_follow_up_plan",
        "self.open_commercial_memory",
        "self.add_commercial_memory",
        "self.show_knowledge_overview",
    ):
        assert token in ASSISTANT


def test_ai_assistant_theme_module_exposes_page_palette_and_qss():
    assert "def assistant_page_palette(" in THEME
    assert "def assistant_page_stylesheet(" in THEME
    assert 'QWidget#AIAssistantRoot' in THEME
    assert 'QTableWidget#AiProspectTable' in THEME
    assert 'QTextEdit#AiOutput' in THEME
