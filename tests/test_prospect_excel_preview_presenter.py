import pytest

from services.prospect_excel_preview_presenter import build_excel_update_preview_text


def _stats():
    return {
        "fichier": "C:/temp/prospects_enrichis.xlsx",
        "lignes_excel": 197,
        "correspondances_siret": 186,
        "introuvables": 7,
        "sans_siret": 2,
        "siret_invalides": 1,
        "ambigus_siret": 1,
        "ignores_incoherents": 0,
        "lignes_sans_changement": 60,
        "champs_vides_a_completer": 51,
        "valeurs_a_fusionner": 31,
        "conflits_a_verifier": 4,
        "modifications_potentielles": {
            "telephone": 24,
            "mobile": 7,
            "email": 18,
            "site_web": 9,
            "facebook": 2,
            "adresse": 3,
        },
        "apercu": [
            {
                "ligne_excel": 14,
                "entreprise": "ENTREPRISE NADOT",
                "siret": "31035888200028",
                "differences": [
                    {
                        "champ_source": "telephone",
                        "action": "fusionner",
                        "valeurs_excel": ["01 30 74 16 32", "09 62 12 27 94"],
                    },
                    {
                        "champ_source": "email",
                        "action": "completer",
                        "valeurs_excel": ["contact@nadot.fr"],
                    },
                ],
            }
        ],
    }


def test_preview_mentions_siret_exact_and_absolute_safety_guards():
    text = build_excel_update_preview_text(_stats())

    assert "SIRET exact uniquement" in text
    assert "Création automatique de prospects : NON" in text
    assert "Suppression de données existantes : NON" in text
    assert "Aucune modification n'a été effectuée." in text


def test_preview_displays_correspondence_and_detected_value_counts():
    text = build_excel_update_preview_text(_stats())

    assert "Prospects retrouvés par SIRET : 186" in text
    assert "SIRET introuvables : 7" in text
    assert "Téléphones : 24" in text
    assert "Mobiles : 7" in text
    assert "Emails : 18" in text
    assert "Sites web : 9" in text
    assert "Facebook : 2" in text
    assert "Adresses : 3" in text


def test_preview_shows_additive_actions_for_each_prospect():
    text = build_excel_update_preview_text(_stats())

    assert "ENTREPRISE NADOT — SIRET 31035888200028 — ligne Excel 14" in text
    assert "Téléphones (à fusionner) : 01 30 74 16 32 ; 09 62 12 27 94" in text
    assert "Emails (à compléter) : contact@nadot.fr" in text


def test_preview_can_hide_details_without_losing_summary():
    text = build_excel_update_preview_text(_stats(), detail_limit=0)

    assert "Prospects retrouvés par SIRET : 186" in text
    assert "DÉTAIL DE L'APERÇU" not in text
    assert "ENTREPRISE NADOT" not in text


def test_preview_rejects_negative_detail_limit():
    with pytest.raises(ValueError):
        build_excel_update_preview_text(_stats(), detail_limit=-1)
