import pytest

from services.enrichment_method_service import EnrichmentMethodCatalog


def test_catalog_has_exactly_four_expected_methods():
    assert [p.key for p in EnrichmentMethodCatalog.profiles()] == [
        "rapid", "standard", "deep", "excel"
    ]


def test_standard_is_default_and_engine_ready():
    assert EnrichmentMethodCatalog.DEFAULT == "standard"
    profile = EnrichmentMethodCatalog.get(None)
    assert profile.key == "standard"
    assert profile.engine_ready is True
    assert profile.uses_excel is False


def test_excel_routes_to_excel_module_not_web_engine():
    profile = EnrichmentMethodCatalog.get("excel")
    assert profile.uses_excel is True
    assert profile.engine_ready is False


@pytest.mark.parametrize("key", ["rapid", "deep"])
def test_future_web_profiles_are_declared_but_locked(key):
    profile = EnrichmentMethodCatalog.get(key)
    assert profile.engine_ready is False
    assert profile.uses_excel is False


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError):
        EnrichmentMethodCatalog.get("turbo")
