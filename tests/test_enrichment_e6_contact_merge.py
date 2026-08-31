from modules.web_fallback import WebFallbackFinder


def _candidate(
    *,
    name,
    phones,
    score,
    reasons,
    source_detail,
    email="",
    site_web="",
    text="",
):
    return {
        "source": "web_fallback",
        "source_detail": source_detail,
        "nom": name,
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": list(phones),
        "faxes": [],
        "site_web": site_web,
        "email": email,
        "texte": text,
        "match_score": score,
        "match_reasons": list(reasons),
        "confidence": "validated",
        "technical_errors": [],
    }


def test_merge_valid_keeps_current_and_historical_decam_phones():
    current = _candidate(
        name="DECAM",
        phones=["01 47 37 48 32"],
        score=200,
        reasons=["SIRET exact"],
        source_detail="annuaire-current.example",
        text=(
            "DECAM SIRET 30109677200027 "
            "56 rue du Faubourg Saint-Antoine 75012 Paris"
        ),
    )

    historical = _candidate(
        name="DECAM",
        phones=["01 47 39 66 39"],
        score=89,
        reasons=[
            "nom très proche",
            "code postal exact",
            "ville présente",
        ],
        source_detail="annuaire-history.example",
        text="DECAM 9 rue Marjolin 92300 Levallois-Perret",
    )

    merged = WebFallbackFinder._merge_valid([current, historical])

    assert merged["telephones"] == [
        "01 47 37 48 32",
        "01 47 39 66 39",
    ]


def test_merge_valid_keeps_same_company_candidate_with_exact_siren():
    current = _candidate(
        name="DECAM",
        phones=["01 47 37 48 32"],
        score=200,
        reasons=["SIRET exact"],
        source_detail="annuaire-current.example",
    )

    same_company = _candidate(
        name="DECAM ANCIEN ETABLISSEMENT",
        phones=["01 47 37 56 00"],
        score=90,
        reasons=["SIREN exact"],
        source_detail="annuaire-siren.example",
        text="DECAM SIREN 301096772",
    )

    merged = WebFallbackFinder._merge_valid([current, same_company])

    assert merged["telephones"] == [
        "01 47 37 48 32",
        "01 47 37 56 00",
    ]


def test_merge_valid_rejects_weak_secondary_candidate_contacts():
    current = _candidate(
        name="DECAM",
        phones=["01 47 37 48 32"],
        score=200,
        reasons=["SIRET exact"],
        source_detail="annuaire-current.example",
        email="decam.lacornue@wanadoo.fr",
    )

    # Ce candidat a franchi le seuil "validated", mais les preuves d'identité
    # sont trop faibles pour qu'il puisse injecter ses coordonnées dans DECAM.
    weak_secondary = _candidate(
        name="DECAM SERVICES",
        phones=["01 99 99 99 99"],
        score=76,
        reasons=[
            "nom proche",
            "code postal exact",
            "ville présente",
        ],
        source_detail="weak-directory.example",
        email="contact@autre-societe.example",
        site_web="https://autre-societe.example/",
    )

    merged = WebFallbackFinder._merge_valid([current, weak_secondary])

    assert merged["telephones"] == ["01 47 37 48 32"]
    assert merged["email"] == "decam.lacornue@wanadoo.fr"
    assert merged["site_web"] == ""
    assert "weak-directory.example" not in merged["source_detail"]
