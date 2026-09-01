import pandas as pd

from services.prospect_excel_update_service import ProspectExcelUpdateService


def test_analyse_excel_reconnait_les_identifiants_et_reste_en_lecture_seule(tmp_path):
    xlsx = tmp_path / "prospects.xlsx"

    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "SIREN": "",
                "Entreprise": "ENTREPRISE NADOT",
                "Téléphone": "01 34 51 26 77",
                "E-mail": "contact@example.fr",
                "Site Internet": "https://example.fr",
            },
            {
                "SIRET": "ABC",
                "SIREN": "301096772",
                "Entreprise": "DECAM",
                "Téléphone": "",
                "E-mail": "",
                "Site Internet": "",
            },
            {
                "SIRET": "",
                "SIREN": "",
                "Entreprise": "SANS IDENTIFIANT",
                "Téléphone": "01 00 00 00 00",
                "E-mail": "",
                "Site Internet": "",
            },
            {
                "SIRET": "12345678900012",
                "SIREN": "987654321",
                "Entreprise": "INCOHERENT",
                "Téléphone": "",
                "E-mail": "",
                "Site Internet": "",
            },
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().analyser_fichier(xlsx)

    assert result["lecture_seule"] is True
    assert result["lignes_excel"] == 4
    assert result["lignes_exploitables"] == 3
    assert result["lignes_sans_identifiant"] == 1
    assert result["siret_valides"] == 2
    assert result["siret_invalides"] == 1
    assert result["siren_valides"] == 2
    assert result["siren_invalides"] == 0
    assert result["siren_deduits_du_siret"] == 1
    assert result["incoherences_identifiants"] == 1

    assert result["colonnes_reconnues"]["siret"] == ["SIRET"]
    assert result["colonnes_reconnues"]["siren"] == ["SIREN"]
    assert result["colonnes_reconnues"]["telephone"] == ["Téléphone"]
    assert result["colonnes_reconnues"]["email"] == ["E-mail"]
    assert result["colonnes_reconnues"]["site_web"] == ["Site Internet"]


def test_analyse_excel_accepte_plusieurs_telephones_et_exclut_le_fax(tmp_path):
    xlsx = tmp_path / "contacts.xlsx"

    pd.DataFrame(
        [
            {
                "SIRET": "31035888200028",
                "Téléphone": "01 34 51 26 77",
                "Téléphone 2": "01 30 74 16 32",
                "Portable": "06 11 22 33 44",
                "Fax": "01 99 99 99 99",
                "LinkedIn URL": "https://linkedin.com/company/example",
            }
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().analyser_fichier(xlsx)

    assert result["colonnes_reconnues"]["telephone"] == [
        "Téléphone",
        "Téléphone 2",
    ]
    assert result["colonnes_reconnues"]["mobile"] == ["Portable"]
    assert result["colonnes_reconnues"]["linkedin"] == ["LinkedIn URL"]
    assert result["colonnes_exclues"]["fax"] == ["Fax"]
    assert "Fax" not in result["colonnes_reconnues"].get("telephone", [])
    assert result["valeurs_detectees"]["telephone"] == 2
    assert result["valeurs_detectees"]["mobile"] == 1


def test_analyse_excel_normalise_les_siret_et_siren_formates(tmp_path):
    xlsx = tmp_path / "identifiants.xlsx"

    pd.DataFrame(
        [
            {
                "Numéro SIRET": "310 358 882 00028",
                "Numéro SIREN": "310 358 882",
            },
            {
                "Numéro SIRET": "30109677200027.0",
                "Numéro SIREN": "",
            },
        ]
    ).to_excel(xlsx, index=False)

    result = ProspectExcelUpdateService().analyser_fichier(xlsx)

    assert result["lignes_exploitables"] == 2
    assert result["siret_valides"] == 2
    assert result["siret_invalides"] == 0
    assert result["siren_valides"] == 1
    assert result["siren_deduits_du_siret"] == 1
    assert result["incoherences_identifiants"] == 0


def test_analyse_excel_refuse_un_format_non_excel(tmp_path):
    fichier = tmp_path / "prospects.csv"
    fichier.write_text("SIRET\n31035888200028\n", encoding="utf-8")

    service = ProspectExcelUpdateService()

    try:
        service.analyser_fichier(fichier)
    except ValueError as exc:
        assert ".xlsx" in str(exc)
    else:
        raise AssertionError("Le fichier CSV aurait dû être refusé.")
