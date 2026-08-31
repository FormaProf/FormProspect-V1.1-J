import json
import sqlite3
from pathlib import Path

import pandas as pd

from modules.company_matcher import confidence, score_candidate
from modules.pages_jaunes import PagesJaunesFinder
from services.import_service import ImportService


def test_alias_can_validate_public_trade_name_without_siret_in_page():
    identity = {
        "entreprise": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "noms_recherche": ["CIPA"],
        "siret": "05480416600129",
        "siren": "054804166",
        "adresse": "4 boulevard Saint-Martin",
        "code_postal": "75010",
        "ville": "PARIS",
    }
    candidate = {
        "nom": "Agence Etoile Cipa",
        "adresse": "4 boulevard Saint-Martin 75010 Paris",
        "code_postal": "75010",
        "ville": "",
        "texte": "Agence Etoile Cipa 4 boulevard Saint-Martin 75010 Paris",
    }

    score, reasons = score_candidate(identity, candidate)

    assert score >= 65
    assert confidence(score) == "validated"
    assert any("enseigne/alias" in reason for reason in reasons)


def test_pages_jaunes_tries_alias_before_legal_name_and_never_ids():
    identity = {
        "entreprise": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
        "noms_recherche": ["CIPA"],
        "siret": "05480416600129",
        "siren": "054804166",
        "adresse": "4 boulevard Saint-Martin",
        "code_postal": "75010",
        "ville": "PARIS",
    }

    plan = PagesJaunesFinder._name_search_plan(identity)

    assert plan[0] == ("CIPA", "75010 PARIS")
    assert (identity["entreprise"], "75010 PARIS") in plan
    flattened = " ".join(" ".join(item) for item in plan)
    assert identity["siret"] not in flattened
    assert identity["siren"] not in flattened


def test_backfill_search_names_updates_existing_siret_without_inserting(tmp_path: Path):
    db = tmp_path / "project.db"
    con = sqlite3.connect(db)
    con.execute(
        """
        CREATE TABLE prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entreprise TEXT,
            siret TEXT,
            siren TEXT,
            adresse TEXT,
            code_postal TEXT,
            ville TEXT,
            code_naf TEXT,
            telephone TEXT,
            site_web TEXT,
            email TEXT,
            facebook TEXT,
            linkedin TEXT,
            instagram TEXT,
            youtube TEXT,
            statut_enrichissement TEXT,
            date_collecte TEXT
        )
        """
    )
    con.execute(
        "INSERT INTO prospects(entreprise,siret,siren) VALUES (?,?,?)",
        ("COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES", "05480416600129", "054804166"),
    )
    con.commit()
    con.close()

    xlsx = tmp_path / "source.xlsx"
    pd.DataFrame([
        {
            "siret": "05480416600129",
            "siren": "054804166",
            "denominationUniteLegale": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
            "sigleUniteLegale": "CIPA",
            "enseigne1Etablissement": "AGENCE ETOILE CIPA",
        }
    ]).to_excel(xlsx, index=False)

    stats = ImportService().mettre_a_jour_noms_recherche_depuis_excel(xlsx, db)

    con = sqlite3.connect(db)
    count = con.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    raw = con.execute("SELECT noms_recherche FROM prospects").fetchone()[0]
    con.close()

    names = json.loads(raw)
    assert count == 1
    assert stats["mis_a_jour"] == 1
    assert names == ["AGENCE ETOILE CIPA", "CIPA"]
