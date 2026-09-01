from copy import deepcopy
from types import SimpleNamespace

import pandas as pd

from services.prospect_excel_update_service import ProspectExcelUpdateService


class FakeCloudClient:
    def __init__(self, prospects, *, detail_overrides=None, fail_update_ids=None):
        self.prospects = {str(p["id"]): deepcopy(p) for p in prospects}
        self.detail_overrides = {
            str(key): deepcopy(value)
            for key, value in (detail_overrides or {}).items()
        }
        self.fail_update_ids = {str(value) for value in (fail_update_ids or set())}
        self.list_calls = []
        self.get_calls = []
        self.update_calls = []

    def list_prospects(self, **params):
        self.list_calls.append(dict(params))
        items_all = [deepcopy(value) for value in self.prospects.values()]
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))
        return SimpleNamespace(
            items=items_all[offset:offset + limit],
            total=len(items_all),
            limit=limit,
            offset=offset,
        )

    def get_prospect(self, prospect_id):
        prospect_id = str(prospect_id)
        self.get_calls.append(prospect_id)
        if prospect_id in self.detail_overrides:
            return deepcopy(self.detail_overrides[prospect_id])
        return deepcopy(self.prospects[prospect_id])

    def update_prospect(self, prospect_id, payload):
        prospect_id = str(prospect_id)
        self.update_calls.append((prospect_id, deepcopy(payload)))
        if prospect_id in self.fail_update_ids:
            raise RuntimeError(f"échec simulé {prospect_id}")
        self.prospects[prospect_id].update(payload)
        return deepcopy(self.prospects[prospect_id])


def _xlsx(tmp_path, rows):
    path = tmp_path / "enrichissement_cloud.xlsx"
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def test_cloud_apply_merges_contacts_without_deleting_old_values(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Téléphone": "01 30 74 16 32",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient([{
        "id": "p1",
        "siret": "31035888200028",
        "siren": "310358882",
        "entreprise": "ENTREPRISE NADOT",
        "telephone": "01 34 51 26 77",
        "email": "",
    }])

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["transaction_atomique"] is False
    assert result["rollback_global"] is False
    assert result["creation_prospects"] is False
    assert result["suppression_donnees"] is False
    assert result["prospects_mis_a_jour"] == 1
    assert result["prospects_en_echec"] == 0
    assert result["informations_ajoutees"] == 2

    assert len(client.update_calls) == 1
    prospect_id, payload = client.update_calls[0]
    assert prospect_id == "p1"
    assert payload["telephone"] == "01 34 51 26 77 ; 01 30 74 16 32"
    assert payload["email"] == "contact@nadot.fr"
    assert "id" not in payload
    assert "siret" not in payload
    assert "siren" not in payload


def test_cloud_apply_continues_after_one_prospect_fails(tmp_path):
    path = _xlsx(tmp_path, [
        {"SIRET": "31035888200028", "Email": "a@example.fr"},
        {"SIRET": "30109677200027", "Email": "b@example.fr"},
    ])
    client = FakeCloudClient(
        [
            {"id": "p1", "siret": "31035888200028", "entreprise": "A", "email": ""},
            {"id": "p2", "siret": "30109677200027", "entreprise": "B", "email": ""},
        ],
        fail_update_ids={"p1"},
    )

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["prospects_mis_a_jour"] == 1
    assert result["prospects_en_echec"] == 1
    assert result["mise_a_jour_partielle"] is True
    assert result["tentatives_mise_a_jour"] == 2
    assert len(result["echecs"]) == 1
    assert result["echecs"][0]["prospect_id"] == "p1"
    assert client.prospects["p2"]["email"] == "b@example.fr"


def test_cloud_apply_refuses_write_if_siret_changed_after_preview(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient(
        [{"id": "p1", "siret": "31035888200028", "entreprise": "NADOT", "email": ""}],
        detail_overrides={
            "p1": {"id": "p1", "siret": "31035888200010", "entreprise": "NADOT", "email": ""}
        },
    )

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["prospects_mis_a_jour"] == 0
    assert result["prospects_en_echec"] == 1
    assert client.update_calls == []
    assert "SIRET" in result["echecs"][0]["erreur"]


def test_cloud_apply_groups_duplicate_excel_rows_into_one_patch(tmp_path):
    path = _xlsx(tmp_path, [
        {"SIRET": "31035888200028", "Téléphone": "01 30 74 16 32"},
        {"SIRET": "31035888200028", "Téléphone": "09 62 12 27 94"},
    ])
    client = FakeCloudClient([{
        "id": "p1",
        "siret": "31035888200028",
        "entreprise": "NADOT",
        "telephone": "01 34 51 26 77",
    }])

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["correspondances_siret"] == 2
    assert result["prospects_mis_a_jour"] == 1
    assert len(client.update_calls) == 1
    payload = client.update_calls[0][1]
    assert payload["telephone"] == (
        "01 34 51 26 77 ; 01 30 74 16 32 ; 09 62 12 27 94"
    )


def test_cloud_apply_rechecks_scalar_and_never_overwrites_latest_value(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Adresse": "10 rue Nouvelle",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient(
        [{
            "id": "p1",
            "siret": "31035888200028",
            "entreprise": "NADOT",
            "adresse": "",
            "email": "",
        }],
        detail_overrides={
            "p1": {
                "id": "p1",
                "siret": "31035888200028",
                "entreprise": "NADOT",
                "adresse": "20 rue Déjà renseignée",
                "email": "",
            }
        },
    )

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["prospects_mis_a_jour"] == 1
    payload = client.update_calls[0][1]
    assert payload == {"email": "contact@nadot.fr"}
    assert "adresse" not in payload


def test_cloud_apply_never_creates_missing_siret(tmp_path):
    path = _xlsx(tmp_path, [{
        "SIRET": "31035888200028",
        "Email": "contact@nadot.fr",
    }])
    client = FakeCloudClient([])

    result = ProspectExcelUpdateService().appliquer_mise_a_jour_cloud(
        path, client, "project-1"
    )

    assert result["introuvables"] == 1
    assert result["prospects_mis_a_jour"] == 0
    assert result["prospects_en_echec"] == 0
    assert client.get_calls == []
    assert client.update_calls == []
