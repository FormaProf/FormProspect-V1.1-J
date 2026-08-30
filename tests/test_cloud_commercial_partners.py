from __future__ import annotations

from types import SimpleNamespace

from services.auth_service import AuthService
from services.cloud_auth_service import CloudAuthService


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_foreign_director_role_maps_to_cloud_value(tmp_path):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    assert service._cloud_role_value("Dirigeant hors France") == "foreign_director"
    assert service._cloud_role_value("foreign_director") == "foreign_director"


def test_partner_crud_and_team_use_admin_cloud_endpoints(tmp_path):
    service = CloudAuthService(AuthService(tmp_path / "accounts.db"))
    service.current_user = SimpleNamespace(id="cloud-admin")
    captured = []

    service.api.get_json = lambda path: ([{"id": "p1"}] if path == "/admin/partners" else [])
    service.api.post_json = lambda path, payload, expected=(200,): captured.append(("POST", path, payload, expected)) or {"id": "p1", **payload}
    service.api.patch_json = lambda path, payload: captured.append(("PATCH", path, payload, None)) or {"id": "p1", **payload}
    service.api.request = lambda method, path, json, expected=(200,): captured.append((method, path, json, expected)) or FakeResponse({"id": "p1", "director_user_id": json["director_user_id"], "commercial_user_ids": json["commercial_user_ids"]})

    assert service.list_commercial_partners() == [{"id": "p1"}]
    service.create_commercial_partner({"legal_name": "Vince Call Center", "country": "Cameroun"})
    service.update_commercial_partner("p1", {"city": "Douala"})
    result = service.set_commercial_partner_team(
        "p1",
        director_user_id="vince",
        commercial_user_ids=["setter-1", "setter-2"],
    )

    assert result["commercial_user_ids"] == ["setter-1", "setter-2"]
    assert captured[0][0:2] == ("POST", "/admin/partners")
    assert captured[1][0:2] == ("PATCH", "/admin/partners/p1")
    assert captured[2][0:2] == ("PUT", "/admin/partners/p1/team")
