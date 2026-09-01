import sqlite3

import pandas as pd

from services.prospect_excel_update_service import ProspectExcelUpdateService


def _create_database(path, rows):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE prospects (
            id INTEGER PRIMARY KEY,
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
            youtube TEXT
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO prospects (
            id, entreprise, siret, siren, adresse, code_postal, ville, code_naf,
            telephone, site_web, email, facebook, linkedin, instagram, youtube
        ) VALUES (
            :id, :entreprise, :siret, :siren, :adresse, :code_postal, :ville, :code_naf,
            :telephone, :site_web, :email, :facebook, :linkedin, :instagram, :youtube
        )
        """,
        rows,
    )
    conn.commit()
    conn.close()


def _row(**overrides):
    base = {
        "id": 1,
        "entreprise": "ENTREPRISE NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "code_naf": "",
        "telephone": "01 34 51 26 77",
        "site_web": "",
        "email": "",
        "facebook": "",
        "linkedin": "",
        "instagram": "",
        "youtube": "",
    }
    base.update(overrides)
    return base


def test_comparaison_utilise_uniquement_le_siret_exact(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row()])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [{"SIRET": "31035888200028", "Email": "contact@nadot.fr"}]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["lecture_seule"] is True
    assert result["mode_base"] == "sqlite_ro"
    assert result["cle_correspondance"] == "siret_exact"
    assert result["creation_prospects"] is False
    assert result["suppression_donnees"] is False
    assert result["correspondances_siret"] == 1
    assert result["modifications_potentielles"]["email"] == 1


def test_comparaison_ne_fait_jamais_de_secours_par_siren(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row()])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [{"SIRET": "", "SIREN": "310358882", "Email": "contact@nadot.fr"}]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["correspondances_siret"] == 0
    assert result["sans_siret"] == 1
    assert result["lignes_comparees"] == 0
    assert result["modifications_potentielles"]["email"] == 0


def test_comparaison_ne_cree_pas_un_siret_introuvable(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row()])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [{"SIRET": "99999999900011", "Email": "nouveau@example.fr"}]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["introuvables"] == 1
    assert result["lignes_comparees"] == 0
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    conn.close()
    assert count == 1


def test_comparaison_fusionne_les_nouveaux_contacts_sans_supprimer_les_anciens(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row(telephone="01 34 51 26 77", email="ancien@nadot.fr")])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "Téléphone": "01 34 51 26 77",
                "Téléphone 2": "01 30 74 16 32",
                "Portable": "06 11 22 33 44",
                "Email": "ancien@nadot.fr ; contact@nadot.fr",
            }
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["modifications_potentielles"]["telephone"] == 1
    assert result["modifications_potentielles"]["mobile"] == 1
    assert result["modifications_potentielles"]["email"] == 1
    assert result["valeurs_a_fusionner"] == 3

    # La comparaison est réellement en lecture seule : les anciennes données
    # restent intactes tant que le futur lot d'écriture n'est pas développé.
    conn = sqlite3.connect(db)
    actual = conn.execute(
        "SELECT telephone, email FROM prospects WHERE id = 1"
    ).fetchone()
    conn.close()
    assert actual == ("01 34 51 26 77", "ancien@nadot.fr")


def test_comparaison_complete_un_champ_vide_sans_ecraser_un_champ_renseigne(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row(adresse="", ville="Paris")])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "Adresse": "12 rue Exemple",
                "Ville": "Lille",
            }
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["modifications_potentielles"]["adresse"] == 1
    assert result["champs_vides_a_completer"] == 1
    assert result["conflits_a_verifier"] == 1
    actions = {
        (d["champ_source"], d["action"])
        for d in result["apercu"][0]["differences"]
    }
    assert ("adresse", "completer") in actions
    assert ("ville", "verifier") in actions


def test_comparaison_ignore_une_ligne_siret_siren_incoherents(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row()])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "SIREN": "987654321",
                "Email": "mauvais@example.fr",
            }
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["ignores_incoherents"] == 1
    assert result["lignes_comparees"] == 0
    assert result["modifications_potentielles"]["email"] == 0


def test_comparaison_detecte_un_siret_duplique_dans_la_base(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row(id=1), _row(id=2, entreprise="DOUBLON")])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [{"SIRET": "31035888200028", "Email": "contact@nadot.fr"}]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["ambigus_siret"] == 1
    assert result["lignes_comparees"] == 0


def test_comparaison_ne_compte_pas_deux_fois_un_mobile_duplique(tmp_path):
    db = tmp_path / "prospects.db"
    _create_database(db, [_row(telephone="")])

    xlsx = tmp_path / "update.xlsx"
    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "Téléphone": "06 11 22 33 44",
                "Portable": "+33 6 11 22 33 44",
            }
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().comparer_avec_sqlite(xlsx, db)

    assert result["modifications_potentielles"]["telephone"] == 1
    assert result["modifications_potentielles"]["mobile"] == 0
    assert result["champs_vides_a_completer"] == 1
