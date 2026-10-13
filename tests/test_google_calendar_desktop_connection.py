from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.cloud_api_client import CloudAPIClient


class _FakeAuth:
    session = SimpleNamespace(
        access_token="token",
        organization_id="organization",
    )


def test_google_calendar_cloud_api_client_contract():
    client = CloudAPIClient(_FakeAuth(), "https://api.example.test")
    calls = []

    def fake_get(path, *, params=None):
        calls.append(("GET", path, params))
        return {"configured": True, "connected": True}

    def fake_post(path, payload, *, expected=(200, 201)):
        calls.append(("POST", path, dict(payload), tuple(expected)))
        if path.endswith("connect-url"):
            return {"authorization_url": "https://accounts.google.test/oauth"}
        if path.endswith("sync-planned-actions"):
            return {
                "created": 2,
                "updated": 1,
                "deleted": 0,
                "skipped": 0,
                "errors": 0,
                "total": 3,
            }
        return {"connected": False}

    client.get_json = fake_get
    client.post_json = fake_post

    assert client.get_google_calendar_status()["connected"] is True
    assert (
        client.get_google_calendar_connect_url()
        == "https://accounts.google.test/oauth"
    )
    assert client.disconnect_google_calendar() == {"connected": False}
    assert client.sync_google_calendar_planned_actions()["created"] == 2

    assert calls == [
        ("GET", "/google-calendar/status", None),
        ("POST", "/google-calendar/connect-url", {}, (200,)),
        ("POST", "/google-calendar/disconnect", {}, (200,)),
        ("POST", "/google-calendar/sync-planned-actions", {}, (200,)),
    ]


def test_account_page_exposes_google_calendar_connection_without_polling():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ui/pages/account_page.py").read_text(encoding="utf-8")

    assert "Google Agenda" in source
    assert "Connecter Google Agenda" in source
    assert "get_google_calendar_status" in source
    assert "get_google_calendar_connect_url" in source
    assert "disconnect_google_calendar" in source
    assert "sync_google_calendar_planned_actions" in source
    assert "QDesktopServices.openUrl" in source
    assert "Actualiser" in source
    assert "Synchroniser" in source

    # Connection status is refreshed only when the account page is refreshed
    # or the user explicitly asks for it: no background Cloud polling.
    assert "QTimer" not in source
