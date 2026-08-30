from __future__ import annotations

from services.cloud_auth_service import CloudAuthError, CloudAuthService


class FakeAPI:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []
        self.next_get = {}
        self.next_post = {}

    def get_json(self, path, **kwargs):
        self.get_calls.append((path, kwargs))
        return self.next_get

    def post_json(self, path, payload, *, expected=(200, 201)):
        self.post_calls.append((path, payload, expected))
        return self.next_post


def _service():
    service = object.__new__(CloudAuthService)
    service.current_user = object()
    service.api = FakeAPI()
    return service


def test_portfolio_transfer_preview_uses_admin_membership_endpoint():
    service = _service()
    service.api.next_get = {
        "source_membership_id": "membership-1",
        "source_user_id": "user-1",
        "source_name": "Commercial Test",
        "source_active": False,
        "prospects_total": 12,
        "prospects_active": 10,
        "prospects_archived": 2,
        "clients_current": 3,
        "planned_activities": 4,
        "overdue_activities": 1,
        "historical_sales_count": 2,
        "historical_commission_cents": 34000,
        "can_transfer": True,
        "blocked_reason": "",
    }

    payload = service.portfolio_transfer_preview(" membership-1 ")

    assert payload["prospects_total"] == 12
    assert service.api.get_calls == [
        ("/admin/users/membership-1/portfolio-transfer-preview", {})
    ]


def test_transfer_portfolio_posts_target_user_id_and_expects_200():
    service = _service()
    service.api.next_post = {
        "source_membership_id": "membership-1",
        "source_user_id": "source-user",
        "source_name": "Source",
        "target_user_id": "target-user",
        "target_name": "Target",
        "prospects_transferred": 12,
        "activities_transferred": 4,
        "audit_action": "user.portfolio_transferred",
    }

    payload = service.transfer_portfolio("membership-1", " target-user ")

    assert payload["prospects_transferred"] == 12
    assert service.api.post_calls == [
        (
            "/admin/users/membership-1/portfolio-transfer",
            {"target_user_id": "target-user"},
            (200,),
        )
    ]


def test_transfer_portfolio_rejects_empty_target_before_api_call():
    service = _service()

    try:
        service.transfer_portfolio("membership-1", " ")
    except ValueError as exc:
        assert "destinataire" in str(exc).lower()
    else:
        raise AssertionError("Une destination vide devait être refusée.")

    assert service.api.post_calls == []


def test_portfolio_transfer_requires_cloud_session():
    service = _service()
    service.current_user = None

    try:
        service.portfolio_transfer_preview("membership-1")
    except CloudAuthError as exc:
        assert "session" in str(exc).lower()
    else:
        raise AssertionError("Une session Cloud devait être exigée.")
