from dataclasses import dataclass
from pathlib import Path

from ui.pages.commercial_account_page import (
    _preserve_cloud_session_identity,
)


@dataclass(frozen=True)
class FakeUser:
    role: str = "Commercial"
    cloud_user_id: str = ""
    organization_id: str = ""
    organization_name: str = ""
    permissions: tuple[str, ...] = ()
    can_create_prospect_manually: bool = False


def test_cloud_identity_survives_local_profile_reload():
    local_user = FakeUser(
        role="Formateur",
        can_create_prospect_manually=False,
    )
    cloud_user = FakeUser(
        role="Commercial",
        cloud_user_id="cloud-user-1",
        organization_id="org-1",
        organization_name="NM FORMATION",
        permissions=("prospect.read",),
        can_create_prospect_manually=True,
    )

    merged = _preserve_cloud_session_identity(
        local_user,
        cloud_user,
    )

    assert merged.role == "Commercial"
    assert merged.cloud_user_id == "cloud-user-1"
    assert merged.organization_id == "org-1"
    assert merged.organization_name == "NM FORMATION"
    assert merged.permissions == ("prospect.read",)
    assert merged.can_create_prospect_manually is True


def test_local_identity_is_unchanged_without_cloud_session():
    local_user = FakeUser(
        role="Commercial",
        can_create_prospect_manually=False,
    )

    merged = _preserve_cloud_session_identity(
        local_user,
        FakeUser(),
    )

    assert merged is local_user


def test_commercial_account_refresh_uses_cloud_identity_guard():
    source = Path(
        "ui/pages/commercial_account_page.py"
    ).read_text(encoding="utf-8")

    start = source.index("    def rafraichir(self):")
    end = source.index(
        "    def _refresh_commercial_organization",
        start,
    )
    segment = source[start:end]

    assert "_preserve_cloud_session_identity(" in segment
