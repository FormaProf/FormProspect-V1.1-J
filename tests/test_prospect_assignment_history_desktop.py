from pathlib import Path

from services.cloud_api_client import CloudAPIClient
from ui.dialogs.prospect_dialog import ProspectDialog


def test_api_lists_prospect_assignment_history(monkeypatch):
    client = CloudAPIClient(
        auth_service=object(),
        base_url="https://example.test",
    )
    calls = []
    expected = [{"event_type": "owner_changed"}]

    def fake_get_json(path, *, params=None):
        calls.append((path, params))
        return expected

    monkeypatch.setattr(client, "get_json", fake_get_json)

    assert client.list_prospect_assignment_history("prospect-1") == expected
    assert calls == [
        ("/prospects/prospect-1/assignment-history", None)
    ]


def test_assignment_history_line_formats_manual_transfer():
    text = ProspectDialog._assignment_history_line(
        {
            "source": "manual",
            "old_owner_name": "Samy Ancien",
            "new_owner_name": "Nass Nouveau",
            "old_project_name": "BTP Samy",
            "new_project_name": "BTP Nass",
            "actor_name": "Nacim Admin",
            "occurred_at": "2026-09-20T16:42:00+02:00",
        }
    )

    assert "20/09/2026 16:42" in text
    assert "Samy Ancien → Nass Nouveau" in text
    assert "Réaffectation manuelle" in text
    assert "BTP Samy → BTP Nass" in text
    assert "Effectué par : Nacim Admin" in text


def test_assignment_history_line_formats_landing_transfer():
    text = ProspectDialog._assignment_history_line(
        {
            "source": "landing",
            "old_owner_name": "",
            "new_owner_name": "Nass Nouveau",
            "new_project_name": "test 7",
            "actor_name": "",
            "occurred_at": "2026-09-20T16:43:00+02:00",
        }
    )

    assert "Non affecté → Nass Nouveau" in text
    assert "Landing Page" in text
    assert "Projet : test 7" in text


def test_cloud_history_is_loaded_in_prospect_dialog():
    source = Path("ui/dialogs/prospect_dialog.py").read_text(encoding="utf-8")
    assert "list_prospect_assignment_history" in source
    assert "for event in assignment_history:" in source
