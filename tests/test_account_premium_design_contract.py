from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = (ROOT / "ui" / "pages" / "account_page.py").read_text(encoding="utf-8")
COMMERCIAL = (
    ROOT / "ui" / "pages" / "commercial_account_page.py"
).read_text(encoding="utf-8")
THEME = (ROOT / "ui" / "account_premium_theme.py").read_text(encoding="utf-8")


def test_account_premium_sources_are_valid_python():
    for source in (ACCOUNT, COMMERCIAL, THEME):
        ast.parse(source)


def test_account_page_has_command_center_hero_and_status():
    assert 'setObjectName("AccountHero")' in COMMERCIAL
    assert "ACCOUNT CENTER  •  IDENTITÉ & SÉCURITÉ" in COMMERCIAL
    assert 'setObjectName("AccountActiveBadge")' in COMMERCIAL
    assert 'setObjectName("AccountHeroMeta")' in COMMERCIAL


def test_account_page_has_compact_live_summary_cards_without_new_reads():
    assert 'setProperty("accountMetricCard", True)' in COMMERCIAL
    assert '"Identité"' in COMMERCIAL
    assert '"Accès"' in COMMERCIAL
    assert '"Licence"' in COMMERCIAL

    # Le redesign réutilise les données déjà chargées par rafraichir().
    assert COMMERCIAL.count('api.get_json("/identity/commercial-organization")') == 1
    assert COMMERCIAL.count("license_info()") == 1


def test_profile_business_actions_are_preserved():
    assert "self._upload_photo" in COMMERCIAL
    assert "self._remove_photo" in COMMERCIAL
    assert "self._edit_identity" in COMMERCIAL
    assert "self._change_password" in COMMERCIAL
    assert "_preserve_cloud_session_identity(" in COMMERCIAL


def test_existing_account_sections_and_scroll_contract_are_preserved():
    assert 'setObjectName("AccountScrollArea")' in COMMERCIAL
    assert "setWidgetResizable(True)" in COMMERCIAL
    assert "setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)" in COMMERCIAL
    assert "self.profile_card.setMinimumHeight(365)" in COMMERCIAL
    assert "root.addWidget(self.organization_card)" in COMMERCIAL
    assert "root.addWidget(self._build_security_card())" in COMMERCIAL
    assert "root.addWidget(self._build_license_card())" in COMMERCIAL


def test_appearance_bar_is_promoted_to_a_real_workspace_control():
    assert 'setObjectName("AppearanceBar")' in ACCOUNT
    assert "Apparence de Form@Prospect" in ACCOUNT
    assert 'setObjectName("AppearanceValue")' in ACCOUNT
    assert 'setObjectName("AppearanceButton")' in ACCOUNT
    assert "self.appearance_requested" in ACCOUNT


def test_theme_contract_contains_premium_surfaces_and_dense_controls():
    assert "QFrame#AccountHero" in THEME
    assert 'QFrame[accountMetricCard="true"]' in THEME
    assert "QFrame#AccountCard" in THEME
    assert "QFrame#AvatarPanel" in THEME
    assert "QFrame#FeaturePanel" in THEME
    assert "QFrame#AppearanceBar" in THEME
