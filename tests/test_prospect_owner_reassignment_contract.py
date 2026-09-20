from pathlib import Path

DIALOG = Path("ui/dialogs/prospect_dialog.py").read_text(encoding="utf-8")
PROVIDER = Path("services/prospect_data_provider.py").read_text(encoding="utf-8")


def test_admin_cloud_uses_controlled_owner_selector():
    assert "SessionState.has_role(\"Administrateur\")" in DIALOG
    assert 'self.commercial_selector.addItem("Non affecté", None)' in DIALOG
    assert "list_users(active_only=True)" in DIALOG
    assert 'self._field_block("Commercial assigné", self.commercial_field)' in DIALOG


def test_non_admin_cloud_owner_is_not_freely_editable():
    assert "self.commercial_input.setReadOnly(True)" in DIALOG
    assert "if self._is_cloud_mode and not self._can_assign_owner:" in DIALOG


def test_cloud_provider_can_explicitly_unassign_owner():
    assert 'value.casefold() in {"non affecté", "non assigné"}' in PROVIDER
    assert 'payload["owner_user_id"] = None' in PROVIDER
    assert "current_owner_id" in PROVIDER


def test_cloud_does_not_duplicate_owner_change_in_activity_feed():
    assert "not self._is_cloud_mode" in DIALOG
    assert "nouveau_commercial != self.ancien_commercial" in DIALOG
