from types import SimpleNamespace

import pandas as pd

from services.prospect_excel_update_service import ProspectExcelUpdateService


class FakeCloudClient:
    def __init__(self, prospects):
        self.prospects = list(prospects)
        self.calls = []
        self.update_calls = []

    def list_prospects(self, **params):
        self.calls.append(dict(params))
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))
        items = self.prospects[offset:offset + limit]
        return SimpleNamespace(
            items=items,
            total=len(self.prospects),
            limit=limit,
            offset=offset,
        )

    def update_prospect(self, prospect_id, payload):
        self.update_calls.append((prospect_id, payload))
        raise AssertionError("La prévisualisation Cloud ne doit jamais écrire.")


def _xlsx(tmp_path, rows):
    path = tmp_path / "enrichissement.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def test_cloud_preview_matches_only_exact_siret_and_never_updates(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Téléphone": "01 30 74 16 32",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient([
        {
            "id": "p1",
            "siret": "31035888200028",
            "siren": "310358882",
            "entreprise": "ENTREPRISE NADOT",
            "telephone": "01 34 51 26 77",
            "email": "",
            "site_web": "",
        }
    ])

    stats = ProspectExcelUpdateService().comparer_avec_cloud(
        path, client, "project-1", page_size=50
    )

    assert stats["lecture_seule"] is True
    assert stats["mode_base"] == "cloud_ro"
    assert stats["cle_correspondance"] == "siret_exact"
    assert stats["creation_prospects"] is False
    assert stats["suppression_donnees"] is False
    assert stats["mise_a_jour_cloud"] is False
    assert stats["correspondances_siret"] == 1
    assert stats["introuvables"] == 0
    assert client.update_calls == []

    differences = stats["apercu"][0]["differences"]
    phone = next(item for item in differences if item["champ_source"] == "telephone")
    email = next(item for item in differences if item["champ_source"] == "email")
    assert phone["action"] == "fusionner"
    assert phone["valeur_actuelle"] == "01 34 51 26 77"
    assert phone["valeurs_excel"] == ["01 30 74 16 32"]
    assert email["action"] == "completer"


def test_cloud_preview_does_not_fallback_to_siren(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "SIREN": "310358882",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient([
        {
            "id": "other-establishment",
            "siret": "31035888200010",
            "siren": "310358882",
            "entreprise": "ENTREPRISE NADOT",
            "email": "",
        }
    ])

    stats = ProspectExcelUpdateService().comparer_avec_cloud(path, client, "project-1")

    assert stats["correspondances_siret"] == 0
    assert stats["introuvables"] == 1
    assert stats["apercu"] == []


def test_cloud_preview_paginates_project_prospects(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "30109677200027",
        "Téléphone": "01 47 37 56 00",
    }])
    prospects = [
        {"id": "a", "siret": "11111111111111", "entreprise": "A", "telephone": ""},
        {"id": "b", "siret": "22222222222222", "entreprise": "B", "telephone": ""},
        {"id": "decam", "siret": "30109677200027", "entreprise": "DECAM", "telephone": ""},
    ]
    client = FakeCloudClient(prospects)

    stats = ProspectExcelUpdateService().comparer_avec_cloud(
        path, client, "project-42", page_size=2
    )

    assert stats["correspondances_siret"] == 1
    assert stats["pages_cloud_lues"] == 2
    assert stats["prospects_cloud_lus"] == 3
    assert [call["offset"] for call in client.calls] == [0, 2]
    assert all(call["project_id"] == "project-42" for call in client.calls)


def test_cloud_preview_marks_duplicate_exact_siret_as_ambiguous(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient([
        {"id": "p1", "siret": "31035888200028", "entreprise": "NADOT 1", "email": ""},
        {"id": "p2", "siret": "31035888200028", "entreprise": "NADOT 2", "email": ""},
    ])

    stats = ProspectExcelUpdateService().comparer_avec_cloud(path, client, "project-1")

    assert stats["correspondances_siret"] == 0
    assert stats["ambigus_siret"] == 1
    assert stats["apercu"] == []


def test_cloud_preview_requires_project_and_never_uses_import_endpoint(tmp_path):
    path = _xlsx(tmp_path, [{"SIRET": "31035888200028"}])
    client = FakeCloudClient([])

    service = ProspectExcelUpdateService()
    try:
        service.comparer_avec_cloud(path, client, "")
    except ValueError as exc:
        assert "project_id" in str(exc)
    else:
        raise AssertionError("Un project_id vide doit être refusé.")

    assert not hasattr(service, "import_project_prospects")
    assert client.update_calls == []
