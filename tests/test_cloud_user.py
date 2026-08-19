from datetime import datetime

import pytest

from models.cloud_user import CloudUser, CloudUserDataError


def valid_payload() -> dict:
    return {
        "id": "user-1",
        "membership_id": "membership-1",
        "first_name": "Ahmed",
        "last_name": "Benali",
        "email": "ahmed@example.com",
        "phone": "",
        "role": "commercial",
        "status": "active",
        "is_active": True,
        "manager_user_id": None,
        "can_create_prospect_manually": False,
        "last_login_at": "2026-07-26T20:15:00+00:00",
    }


def test_cloud_user_from_payload() -> None:
    user = CloudUser.from_payload(valid_payload())

    assert user.full_name == "Ahmed Benali"
    assert user.display_name == "Ahmed Benali (Commercial)"
    assert user.is_commercial is True
    assert user.is_assignable_to_project is True
    assert isinstance(user.last_login_at, datetime)


def test_full_name_falls_back_to_email() -> None:
    payload = valid_payload()
    payload["first_name"] = ""
    payload["last_name"] = ""

    user = CloudUser.from_payload(payload)

    assert user.full_name == "ahmed@example.com"


def test_missing_required_field_is_rejected() -> None:
    payload = valid_payload()
    payload["email"] = ""

    with pytest.raises(CloudUserDataError):
        CloudUser.from_payload(payload)


def test_inactive_commercial_is_not_assignable() -> None:
    payload = valid_payload()
    payload["is_active"] = False

    user = CloudUser.from_payload(payload)

    assert user.is_assignable_to_project is False
