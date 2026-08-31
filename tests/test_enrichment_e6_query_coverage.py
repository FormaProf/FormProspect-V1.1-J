from modules.web_fallback import WebFallbackFinder


def test_rechercher_uses_all_priority_queries_before_fetch_limit(monkeypatch):
    """Les recherches actuelle, SIRET et historique doivent toutes être exécutées."""

    finder = WebFallbackFinder()

    queries = [
        "DECAM 75012 PARIS",
        "30109677200027",
        "DECAM 92300 LEVALLOIS-PERRET",
    ]

    search_results = {
        queries[0]: [
            "https://current.example/result-1",
            "https://current.example/result-2",
            "https://current.example/result-3",
            "https://current.example/result-4",
        ],
        queries[1]: [
            "https://siret.example/result-1",
            "https://siret.example/result-2",
        ],
        queries[2]: [
            "https://history.example/result-1",
            "https://history.example/result-2",
        ],
    }

    search_calls = []
    fetched_urls = []

    monkeypatch.setattr(
        finder,
        "_query_plan",
        lambda identity: list(queries),
    )

    def fake_search_urls(query):
        search_calls.append(query)
        return list(search_results[query])

    def fake_fetch_candidate(url, identity):
        fetched_urls.append(url)
        return {
            "source": "web_fallback",
            "source_detail": url,
            "nom": "DECAM",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "email": "",
            "texte": "",
            "match_score": 200,
            "match_reasons": ["SIRET exact"],
            "confidence": "validated",
            "technical_errors": [],
        }

    monkeypatch.setattr(finder, "_search_urls", fake_search_urls)
    monkeypatch.setattr(finder, "_fetch_candidate", fake_fetch_candidate)
    monkeypatch.setattr(
        finder,
        "_merge_valid",
        lambda candidates: {
            "source": "web_fallback",
            "technical_errors": [],
        },
    )

    result = finder.rechercher({"entreprise": "DECAM"})

    assert set(search_calls) == set(queries)
    assert len(search_calls) == len(queries)

    # MAX_FETCHES reste strictement respecté.
    assert len(fetched_urls) == finder.MAX_FETCHES

    # Malgré la limite globale de quatre pages, chaque axe prioritaire
    # doit obtenir au moins une place dans les pages réellement ouvertes.
    assert search_results[queries[0]][0] in fetched_urls
    assert search_results[queries[1]][0] in fetched_urls
    assert search_results[queries[2]][0] in fetched_urls

    assert result["technical_errors"] == []


def test_rechercher_deduplicates_urls_across_priority_queries(monkeypatch):
    """Une même page trouvée par plusieurs requêtes ne doit être ouverte qu'une fois."""

    finder = WebFallbackFinder()

    queries = [
        "DECAM 75012 PARIS",
        "30109677200027",
        "DECAM 92300 LEVALLOIS-PERRET",
    ]

    shared = "https://shared.example/decam"
    search_results = {
        queries[0]: [
            shared,
            "https://current.example/decam",
        ],
        queries[1]: [
            shared,
            "https://siret.example/decam",
        ],
        queries[2]: [
            shared,
            "https://history.example/decam",
        ],
    }

    fetched_urls = []

    monkeypatch.setattr(
        finder,
        "_query_plan",
        lambda identity: list(queries),
    )
    monkeypatch.setattr(
        finder,
        "_search_urls",
        lambda query: list(search_results[query]),
    )

    def fake_fetch_candidate(url, identity):
        fetched_urls.append(url)
        return {
            "source": "web_fallback",
            "source_detail": url,
            "nom": "DECAM",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "email": "",
            "texte": "",
            "match_score": 200,
            "match_reasons": ["SIRET exact"],
            "confidence": "validated",
            "technical_errors": [],
        }

    monkeypatch.setattr(finder, "_fetch_candidate", fake_fetch_candidate)
    monkeypatch.setattr(
        finder,
        "_merge_valid",
        lambda candidates: {
            "source": "web_fallback",
            "technical_errors": [],
        },
    )

    finder.rechercher({"entreprise": "DECAM"})

    assert len(fetched_urls) == len(set(fetched_urls))
    assert shared in fetched_urls
    assert "https://siret.example/decam" in fetched_urls
    assert "https://history.example/decam" in fetched_urls
