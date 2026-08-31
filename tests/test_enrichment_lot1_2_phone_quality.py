from services.enrichment_service import EnrichmentService


def test_keeps_all_legitimate_numbers_from_best_validated_source():
    valid = [
        {
            "source": "pages_jaunes",
            "match_score": 200,
            "telephones": [
                "01 48 09 20 65",
                "01 48 09 17 40",
                "01 48 09 26 26",
                "06 12 34 56 78",
                "09 70 10 20 30",
            ],
            "faxes": [],
        }
    ]

    phones, source = EnrichmentService._select_contact_numbers(valid)

    assert source == "pages_jaunes"
    assert phones == [
        "06 12 34 56 78",
        "01 48 09 17 40",
        "01 48 09 20 65",
        "01 48 09 26 26",
        "09 70 10 20 30",
    ]


def test_explicit_fax_is_removed_even_if_also_listed_as_phone():
    valid = [
        {
            "source": "pages_jaunes",
            "match_score": 200,
            "telephones": ["01 39 19 22 26", "01 39 19 22 00"],
            "faxes": ["01 39 19 22 00"],
        }
    ]

    phones, _ = EnrichmentService._select_contact_numbers(valid)

    assert phones == ["01 39 19 22 26"]


def test_fax_identified_by_another_valid_source_is_also_excluded():
    valid = [
        {
            "source": "pages_jaunes",
            "match_score": 200,
            "telephones": ["01 39 19 22 26", "01 39 19 22 00"],
            "faxes": [],
        },
        {
            "source": "google_maps",
            "match_score": 120,
            "telephones": [],
            "faxes": ["01 39 19 22 00"],
        },
    ]

    phones, source = EnrichmentService._select_contact_numbers(valid)

    assert source == "pages_jaunes"
    assert phones == ["01 39 19 22 26"]


def test_best_source_can_keep_more_than_four_numbers():
    valid = [
        {
            "source": "pages_jaunes",
            "match_score": 200,
            "telephones": [
                "01 40 00 00 01",
                "01 40 00 00 02",
                "01 40 00 00 03",
                "01 40 00 00 04",
                "01 40 00 00 05",
            ],
            "faxes": [],
        }
    ]

    phones, _ = EnrichmentService._select_contact_numbers(valid)

    assert len(phones) == 5
