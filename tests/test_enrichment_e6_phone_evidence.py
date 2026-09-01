from services.enrichment_service import EnrichmentService


def _result(source, phones=None, faxes=None, score=100):
    return {
        "source": source,
        "source_detail": "",
        "nom": "ENTREPRISE TEST",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "telephones": list(phones or []),
        "faxes": list(faxes or []),
        "site_web": "",
        "email": "",
        "texte": "",
        "match_score": score,
        "match_reasons": ["test"],
        "confidence": "validated",
        "technical_errors": [],
    }


def test_118000_unique_supplement_is_kept_when_primary_phone_exists():
    numbers, sources = EnrichmentService._select_contact_numbers(
        [
            _result(
                "pages_jaunes",
                phones=["01 47 37 56 00"],
                score=200,
            ),
            _result(
                "118000",
                phones=["01 47 37 56 00", "01 47 39 10 49"],
                score=115,
            ),
        ]
    )

    assert set(numbers) == {"01 47 37 56 00", "01 47 39 10 49"}
    assert "pages_jaunes" in sources
    assert "118000" in sources


def test_118000_unique_supplement_is_kept_when_siren_phone_already_exists():
    numbers, sources = EnrichmentService._select_contact_numbers(
        [
            _result(
                "118000",
                phones=["06 12 34 56 78"],
                score=115,
            ),
        ],
        trusted_existing=["01 47 37 56 00"],
    )

    assert numbers == ["06 12 34 56 78"]
    assert sources == "118000"


def test_118000_remains_usable_when_it_is_the_only_phone_source():
    numbers, sources = EnrichmentService._select_contact_numbers(
        [
            _result(
                "118000",
                phones=["01 47 39 10 49", "01 47 37 56 00"],
                score=115,
            ),
        ]
    )

    assert set(numbers) == {"01 47 39 10 49", "01 47 37 56 00"}
    assert sources == "118000"


def test_explicit_fax_is_always_excluded_even_if_also_listed_as_phone():
    numbers, _ = EnrichmentService._select_contact_numbers(
        [
            _result(
                "pages_jaunes",
                phones=["01 47 37 56 00"],
                score=200,
            ),
            _result(
                "directory",
                phones=["01 47 39 10 49"],
                faxes=["01 47 39 10 49"],
                score=180,
            ),
        ]
    )

    assert numbers == ["01 47 37 56 00"]


def test_distinct_valid_sources_can_all_contribute_numbers():
    numbers, sources = EnrichmentService._select_contact_numbers(
        [
            _result(
                "pages_jaunes",
                phones=["01 47 37 56 00"],
                score=200,
            ),
            _result(
                "google_maps",
                phones=["01 47 37 48 32"],
                score=190,
            ),
            _result(
                "118000",
                phones=["09 62 12 27 94"],
                score=115,
            ),
        ]
    )

    assert set(numbers) == {
        "01 47 37 56 00",
        "01 47 37 48 32",
        "09 62 12 27 94",
    }
    assert "pages_jaunes" in sources
    assert "google_maps" in sources
    assert "118000" in sources
