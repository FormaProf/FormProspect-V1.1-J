from pathlib import Path

import pandas as pd

from modules.social_finder import SocialFinder
from services.import_service import ImportService


def test_nd_placeholders_are_not_search_aliases():
    service = ImportService()
    df = pd.DataFrame([
        {
            "denominationUniteLegale": "SOCIETE EXEMPLE",
            "denominationUsuelleEtablissement": "[ND]",
            "enseigne1Etablissement": "N/D",
            "sigleUniteLegale": "N/A",
            "nomUniteLegale": "[ND]",
            "prenom1UniteLegale": "[ND]",
        }
    ])
    cols = service._normaliser_colonnes(df)
    names = service._noms_recherche(df.iloc[0], cols)
    assert names == []


def test_real_aliases_survive_placeholder_filter():
    service = ImportService()
    df = pd.DataFrame([
        {
            "denominationUniteLegale": "COMPAGNIE IMMOBILIERE PERRISSEL ET ASSOCIES",
            "enseigne1Etablissement": "AGENCE ETOILE CIPA",
            "sigleUniteLegale": "CIPA",
            "nomUniteLegale": "[ND]",
            "prenom1UniteLegale": "[ND]",
        }
    ])
    cols = service._normaliser_colonnes(df)
    names = service._noms_recherche(df.iloc[0], cols)
    assert names == ["AGENCE ETOILE CIPA", "CIPA"]


def test_generic_social_roots_are_rejected():
    assert SocialFinder._is_generic_social_url("https://www.facebook.com/", "facebook")
    assert SocialFinder._is_generic_social_url("https://instagram.com/", "instagram")
    assert SocialFinder._is_generic_social_url("https://www.linkedin.com/", "linkedin")
    assert SocialFinder._is_generic_social_url("https://x.com/intent/tweet?x=1", "twitter")


def test_real_social_profiles_are_kept():
    assert not SocialFinder._is_generic_social_url(
        "https://www.facebook.com/motralec", "facebook"
    )
    assert not SocialFinder._is_generic_social_url(
        "https://www.instagram.com/terca.fr/", "instagram"
    )
    assert not SocialFinder._is_generic_social_url(
        "https://www.linkedin.com/company/terca", "linkedin"
    )
    assert not SocialFinder._is_generic_social_url(
        "https://x.com/entreprise", "twitter"
    )


def test_linkedin_generic_routes_are_rejected():
    assert SocialFinder._is_generic_social_url(
        "https://www.linkedin.com/feed/", "linkedin"
    )
    assert SocialFinder._is_generic_social_url(
        "https://www.linkedin.com/login", "linkedin"
    )


def test_youtube_channel_is_kept_but_video_not_counted_as_company_profile():
    assert not SocialFinder._is_generic_social_url(
        "https://www.youtube.com/@entreprise", "youtube"
    )
    assert not SocialFinder._is_generic_social_url(
        "https://www.youtube.com/channel/UC123456", "youtube"
    )
    assert SocialFinder._is_generic_social_url(
        "https://www.youtube.com/watch?v=abc", "youtube"
    )
