from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = (ROOT / "ui" / "pages" / "account_page.py").read_text(encoding="utf-8")
COMMERCIAL = (
    ROOT / "ui" / "pages" / "commercial_account_page.py"
).read_text(encoding="utf-8")
THEME = (ROOT / "ui" / "account_premium_theme.py").read_text(encoding="utf-8")


def test_account_dual_theme_sources_are_valid_python():
    for source in (ACCOUNT, COMMERCIAL, THEME):
        ast.parse(source)


def test_account_theme_defines_exact_three_product_modes():
    assert "THEME_CLASSIC" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert "THEME_UI_DARK" in THEME
    assert "CLASSIC =" in THEME
    assert "LIGHT =" in THEME
    assert "DARK =" in THEME


def test_account_structure_is_not_rebuilt_when_theme_changes():
    start = ACCOUNT.index("    def apply_appearance_theme(self):")
    end = ACCOUNT.index("    def rafraichir(self):", start)
    account_apply = ACCOUNT[start:end]

    commercial_start = COMMERCIAL.index(
        "    def apply_appearance_theme(self) -> None:"
    )
    commercial_end = COMMERCIAL.index(
        "    def _build_hero(self) -> QFrame:",
        commercial_start,
    )
    commercial_apply = COMMERCIAL[commercial_start:commercial_end]

    forbidden = (
        "_build_profile_card(",
        "_build_security_card(",
        "_build_license_card(",
        "api.get_json(",
        "license_info(",
    )
    for token in forbidden:
        assert token not in account_apply
        assert token not in commercial_apply


def test_account_theme_switch_is_visual_only_and_refreshes_without_cloud_call():
    assert "get_theme_preference()" in ACCOUNT
    assert "account_shell_stylesheet" in ACCOUNT
    assert "self.view.apply_appearance_theme()" in ACCOUNT

    apply_block = COMMERCIAL.split(
        "def apply_appearance_theme(self) -> None:", 1
    )[1].split("def _build_hero", 1)[0]
    assert "get_theme_preference()" in apply_block or "self._style()" in apply_block
    assert "api." not in apply_block
    assert "auth_service." not in apply_block


def test_same_structure_is_used_for_classic_light_and_dark():
    assert "def account_page_palette(mode: str)" in THEME
    assert "def commercial_account_stylesheet(p: dict[str, str])" in THEME
    assert "def account_shell_stylesheet(p: dict[str, str])" in THEME
    assert "normalize_theme_mode(mode)" in THEME
