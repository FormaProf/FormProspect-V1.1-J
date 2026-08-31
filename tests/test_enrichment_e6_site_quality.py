from modules.company_matcher import confidence, score_candidate
from modules.pages_jaunes import PagesJaunesFinder
from modules.web_fallback import WebFallbackFinder


def _decam_identity():
    return {
        "entreprise": "DECAM",
        "siret": "30109677200027",
        "siren": "301096772",
        "adresse": "56 RUE DU FAUBOURG SAINT ANTOINE",
        "code_postal": "75012",
        "ville": "PARIS",
        "noms_recherche": [
            "DECAM",
            "D.E.C.A.M.",
        ],
        "localisations_recherche": [
            {
                "adresse": "56 RUE DU FAUBOURG SAINT ANTOINE",
                "code_postal": "75012",
                "ville": "PARIS",
            },
            {
                "adresse": "9 RUE MARJOLIN",
                "code_postal": "92300",
                "ville": "LEVALLOIS-PERRET",
            },
        ],
    }


def test_decam_rejects_fernandes_climatisation_identity():
    """Un concurrent du même métier ne doit jamais être validé comme DECAM."""

    identity = _decam_identity()

    candidate = {
        "source": "web_fallback",
        "nom": "Fernandes Climatisation",
        "adresse": "",
        "code_postal": "75012",
        "ville": "Paris",
        "telephones": ["01 40 00 00 00"],
        "site_web": "https://fernandesclimatisation.com/",
        "email": "contact@fernandesclimatisation.com",
        "texte": (
            "Fernandes Climatisation "
            "climatisation chauffage dépannage "
            "75012 Paris"
        ),
    }

    score, reasons = score_candidate(
        identity,
        candidate,
    )

    assert confidence(score) == "rejected"
    assert "nom différent" in reasons
    assert score < 50


def test_pagesjaunes_does_not_accept_unlabelled_external_site():
    """Un simple lien externe n'est pas une preuve de site officiel."""

    links = [
        {
            "href": "https://fernandesclimatisation.com/",
            "text": "Fernandes Climatisation",
            "title": "",
            "aria_label": "",
        }
    ]

    result = PagesJaunesFinder._external_site(
        links
    )

    assert result == ""


def test_pagesjaunes_accepts_explicit_official_site_link():
    """Un vrai bouton Site internet peut être conservé."""

    links = [
        {
            "href": "https://decam.biz/",
            "text": "Site internet",
            "title": "",
            "aria_label": "",
        }
    ]

    result = PagesJaunesFinder._external_site(
        links
    )

    assert result == "https://decam.biz/"


def test_pagesjaunes_never_uses_le_site_de_as_company_website():
    """Un annuaire ne doit jamais devenir le site officiel du prospect."""

    links = [
        {
            "href": "https://www.le-site-de.com/decam/",
            "text": "Site internet",
            "title": "Site officiel",
            "aria_label": "Visiter le site",
        }
    ]

    result = PagesJaunesFinder._external_site(
        links
    )

    assert result == ""


def test_web_fallback_rejects_le_site_de_as_official_domain():
    """Le fallback Web peut consulter un annuaire mais pas le publier comme site."""

    assert (
        WebFallbackFinder._is_official_candidate_domain(
            "https://www.le-site-de.com/entreprise/test"
        )
        is False
    )


def test_web_fallback_keeps_real_company_domain_candidate():
    """Un domaine d'entreprise normal reste éligible à la validation d'identité."""

    assert (
        WebFallbackFinder._is_official_candidate_domain(
            "https://decam.biz/"
        )
        is True
    )