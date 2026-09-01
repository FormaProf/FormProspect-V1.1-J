from services.enrichment_service import EnrichmentService


class EmailFinderStub:
    @staticmethod
    def _is_technical(email):
        value = str(email or "").lower()
        return value.startswith("noreply@") or value.startswith("tracking@")


def _result(source, site="", email="", score=150):
    return {
        "source": source,
        "source_detail": "",
        "nom": "ENTREPRISE TEST",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": [],
        "faxes": [],
        "site_web": site,
        "email": email,
        "texte": "",
        "match_score": score,
        "match_reasons": ["test"],
        "confidence": "validated",
        "technical_errors": [],
    }


def test_directory_profile_is_never_promoted_as_official_site():
    sites = EnrichmentService._site_candidates(
        [
            _result("directory", site="https://www.118000.fr/e_C0061241166", score=200),
            _result("google_maps", site="https://entreprise-test.fr/", score=190),
        ],
        limit=2,
    )
    assert sites == ["https://entreprise-test.fr/"]


def test_public_mailbox_is_allowed_when_source_identity_is_validated():
    assert EnrichmentService._email_is_reliable(
        "decam.lacornue@wanadoo.fr",
        EmailFinderStub(),
    )


def test_technical_or_directory_email_is_rejected():
    assert not EnrichmentService._email_is_reliable(
        "noreply@tracking.example",
        EmailFinderStub(),
    )
    assert not EnrichmentService._email_is_reliable(
        "contact@118000.fr",
        EmailFinderStub(),
    )
