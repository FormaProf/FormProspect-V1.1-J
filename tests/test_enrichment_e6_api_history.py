from __future__ import annotations

import requests

from modules.entreprise_api import EntrepriseApiClient


SIREN = "301096772"
CURRENT_SIRET = "30109677200027"
HISTORICAL_SIRET = "30109677200019"


def _primary_payload():
    """Réponse typique d'une résolution directe par SIREN : siège actuel seulement."""
    return {
        "results": [
            {
                "siren": SIREN,
                "nom_raison_sociale": "DECAM",
                "nom_complet": "DECAM",
                "nombre_etablissements": 2,
                "nombre_etablissements_ouverts": 1,
                "siege": {
                    "siret": CURRENT_SIRET,
                    "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                    "code_postal": "75012",
                    "libelle_commune": "PARIS",
                    "est_siege": True,
                    "etat_administratif": "A",
                },
                # La recherche directe par SIREN ne garantit pas l'historique.
                "matching_etablissements": [],
            }
        ]
    }


def _name_payload():
    """Recherche textuelle : elle expose les deux établissements DECAM."""
    return {
        "results": [
            {
                # Homonyme volontaire : il ne doit jamais contaminer DECAM.
                "siren": "999999999",
                "nom_raison_sociale": "DECAM",
                "nom_complet": "DECAM",
                "siege": {
                    "siret": "99999999900011",
                    "adresse": "1 RUE TEST 13001 MARSEILLE",
                    "code_postal": "13001",
                    "libelle_commune": "MARSEILLE",
                    "est_siege": True,
                },
                "matching_etablissements": [],
            },
            {
                "siren": SIREN,
                "nom_raison_sociale": "DECAM",
                "nom_complet": "DECAM",
                "nombre_etablissements": 2,
                "nombre_etablissements_ouverts": 1,
                "siege": {
                    "siret": CURRENT_SIRET,
                    "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                    "code_postal": "75012",
                    "libelle_commune": "PARIS",
                    "est_siege": True,
                    "etat_administratif": "A",
                },
                "matching_etablissements": [
                    {
                        "siret": CURRENT_SIRET,
                        "adresse": "56 RUE DU FAUBOURG SAINT-ANTOINE 75012 PARIS",
                        "code_postal": "75012",
                        "libelle_commune": "PARIS",
                        "est_siege": True,
                        "etat_administratif": "A",
                    },
                    {
                        "siret": HISTORICAL_SIRET,
                        "adresse": "9 RUE MARJOLIN 92300 LEVALLOIS-PERRET",
                        "code_postal": "92300",
                        "libelle_commune": "LEVALLOIS-PERRET",
                        "est_siege": False,
                        "ancien_siege": True,
                        "etat_administratif": "F",
                        "date_fermeture": "2024-10-01",
                    },
                ],
            },
        ]
    }


class _Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_resolve_expands_decam_with_historical_establishment(monkeypatch):
    """resolve() doit compléter le siège actuel avec les établissements historiques."""
    client = EntrepriseApiClient()
    calls = []

    def fake_get(*args, **kwargs):
        params = dict(kwargs.get("params") or {})
        calls.append(params)
        query = str(params.get("q") or "")

        if query == SIREN:
            return _Response(_primary_payload())
        if query == "DECAM":
            return _Response(_name_payload())
        raise AssertionError(f"Requête inattendue : {params}")

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client, "_throttle", lambda: None)

    result = client.resolve(
        {
            "entreprise": "DECAM",
            "siren": SIREN,
            "siret": CURRENT_SIRET,
        }
    )

    assert result["resolved"] is True
    assert result["siren"] == SIREN
    assert result["siret_siege"] == CURRENT_SIRET

    by_siret = {item["siret"]: item for item in result["locations"]}
    assert set(by_siret) == {CURRENT_SIRET, HISTORICAL_SIRET}
    assert by_siret[CURRENT_SIRET]["code_postal"] == "75012"
    assert by_siret[HISTORICAL_SIRET]["adresse"].startswith("9 RUE MARJOLIN")
    assert by_siret[HISTORICAL_SIRET]["code_postal"] == "92300"
    assert by_siret[HISTORICAL_SIRET]["ville"] == "LEVALLOIS-PERRET"

    assert len(calls) == 2
    assert calls[0]["q"] == SIREN
    assert calls[1]["q"] == "DECAM"
    assert calls[1]["limite_matching_etablissements"] == 100

    # Le résultat enrichi doit être mis en cache par SIREN.
    cached = client.resolve(
        {
            "entreprise": "DECAM",
            "siren": SIREN,
            "siret": CURRENT_SIRET,
        }
    )
    assert cached["from_cache"] is True
    assert len(calls) == 2
    assert {item["siret"] for item in cached["locations"]} == {
        CURRENT_SIRET,
        HISTORICAL_SIRET,
    }


def test_history_expansion_filters_same_name_companies_by_exact_siren(monkeypatch):
    """Une recherche par nom peut contenir des homonymes : seul le SIREN exact est fusionné."""
    client = EntrepriseApiClient()

    def fake_get(*args, **kwargs):
        query = str((kwargs.get("params") or {}).get("q") or "")
        if query == SIREN:
            return _Response(_primary_payload())
        return _Response(_name_payload())

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client, "_throttle", lambda: None)

    result = client.resolve(
        {
            "entreprise": "DECAM",
            "siren": SIREN,
            "siret": CURRENT_SIRET,
        }
    )

    locations = result["locations"]
    assert any(item["siret"] == HISTORICAL_SIRET for item in locations)
    assert all(not item["adresse"].startswith("1 RUE TEST") for item in locations)
    assert all(not item["siret"].startswith("999999999") for item in locations)


def test_history_lookup_failure_keeps_primary_identity(monkeypatch):
    """Une panne de la seconde requête ne doit pas faire perdre l'identité actuelle résolue."""
    client = EntrepriseApiClient()
    calls = []

    def fake_get(*args, **kwargs):
        params = dict(kwargs.get("params") or {})
        calls.append(params)
        if str(params.get("q") or "") == SIREN:
            return _Response(_primary_payload())
        raise requests.Timeout("history lookup timeout")

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client, "_throttle", lambda: None)

    result = client.resolve(
        {
            "entreprise": "DECAM",
            "siren": SIREN,
            "siret": CURRENT_SIRET,
        }
    )

    assert len(calls) == 2
    assert result["resolved"] is True
    assert result["siren"] == SIREN
    assert result["siret_siege"] == CURRENT_SIRET
    assert any(item["siret"] == CURRENT_SIRET for item in result["locations"])
    assert result["error"] == ""
