import asyncio

from modules.pages_jaunes import PagesJaunesFinder


def identity():
    return {
        "entreprise": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "siret": "05480416600129",
        "siren": "054804166",
        "adresse": "4 boulevard Saint-Martin",
        "code_postal": "75010",
        "ville": "PARIS",
    }


def rejected():
    return {
        "source": "pages_jaunes",
        "nom": "",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": [],
        "faxes": [],
        "site_web": "",
        "texte": "",
        "match_score": 0,
        "match_reasons": [],
        "confidence": "rejected",
        "technical_errors": [],
    }


def test_pages_jaunes_plan_uses_company_name_and_location_not_legal_ids():
    plan = PagesJaunesFinder._name_search_plan(identity())

    assert plan[0] == (
        "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "75010 PARIS",
    )
    assert plan[1] == (
        "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "4 boulevard Saint-Martin 75010 PARIS",
    )
    flattened = " ".join(" ".join(item) for item in plan)
    assert "05480416600129" not in flattened
    assert "054804166" not in flattened


def test_pages_jaunes_name_search_never_sends_siret_or_siren(monkeypatch):
    finder = PagesJaunesFinder()
    calls = []

    async def fake_open():
        return None

    async def fake_search_once(search_identity, quoiqui, location=""):
        calls.append((quoiqui, location))
        return rejected()

    monkeypatch.setattr(finder, "ouvrir", fake_open)
    monkeypatch.setattr(finder, "_search_once", fake_search_once)

    asyncio.run(finder.rechercher_nom(identity()))

    assert calls
    assert all(quoiqui == identity()["entreprise"] for quoiqui, _ in calls)
    assert all(identity()["siret"] not in quoiqui for quoiqui, _ in calls)
    assert all(identity()["siren"] not in quoiqui for quoiqui, _ in calls)


def test_legacy_identifier_method_delegates_to_name_search(monkeypatch):
    finder = PagesJaunesFinder()
    marker = {"ok": True}

    async def fake_name(search_identity):
        assert search_identity == identity()
        return marker

    monkeypatch.setattr(finder, "rechercher_nom", fake_name)
    assert asyncio.run(finder.rechercher_identifiant(identity())) is marker
