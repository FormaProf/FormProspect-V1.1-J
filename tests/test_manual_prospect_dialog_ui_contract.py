from pathlib import Path

from ui.dialogs.manual_prospect_dialog import ManualProspectDialog


PAGE = Path("ui/pages/prospects_page.py").read_text(encoding="utf-8")
DIALOG = Path(
    "ui/dialogs/manual_prospect_dialog.py"
).read_text(encoding="utf-8")


def test_manual_dialog_normalizes_siret():
    assert ManualProspectDialog._normalize_siret(
        "123 456 789 000 12"
    ) == "12345678900012"


def test_manual_dialog_contains_creation_fields():
    for field in (
        '"company_name"',
        '"siret"',
        '"contact_first_name"',
        '"contact_last_name"',
        '"mobile"',
        '"email"',
        '"website"',
        '"address"',
        '"postal_code"',
        '"city"',
        '"naf_code"',
        '"notes"',
    ):
        assert field in DIALOG


def test_manual_dialog_supports_admin_assignment():
    assert "list_users(" in DIALOG
    assert '"owner_user_id"' in DIALOG
    assert "is_commercial" in DIALOG


def test_manual_button_is_connected_and_enabled():
    assert "ManualProspectDialog" in PAGE
    assert (
        "self.bouton_ajouter_prospect.clicked.connect("
        in PAGE
    )
    assert "self.ajouter_prospect_manuellement" in PAGE
    assert (
        "self.bouton_ajouter_prospect.setEnabled(False)"
        not in PAGE
    )


def test_manual_creation_refreshes_prospects():
    assert "def ajouter_prospect_manuellement(self):" in PAGE
    assert "force_refresh=True" in PAGE
    assert "is_cloud_mode=self._is_cloud()" in PAGE
