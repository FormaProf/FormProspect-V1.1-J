import pytest

from services.enrichment_method_service import (
    EnrichmentMethodCatalog,
    EnrichmentMethodRuntime,
)


def test_catalog_has_exactly_four_expected_methods():
    assert [p.key for p in EnrichmentMethodCatalog.profiles()] == [
        "rapid", "standard", "deep", "excel"
    ]


def test_standard_is_default_and_keeps_e6_profile():
    profile = EnrichmentMethodCatalog.get(None)
    assert EnrichmentMethodCatalog.DEFAULT == "standard"
    assert profile.key == "standard"
    assert profile.engine_ready is True
    assert profile.uses_excel is False
    assert profile.should_run_google(has_useful=True) is True
    assert profile.should_run_118000(has_phone=True) is True
    assert profile.should_run_web(has_useful=True) is True
    assert profile.site_analysis_limit == 2


def test_rapid_is_engine_ready_and_skips_optional_sources_when_possible():
    profile = EnrichmentMethodCatalog.get("rapid")
    assert profile.engine_ready is True
    assert profile.should_run_google(has_useful=True) is False
    assert profile.should_run_google(has_useful=False) is True
    assert profile.should_run_118000(has_phone=True) is False
    assert profile.should_run_118000(has_phone=False) is True
    assert profile.should_run_web(has_useful=True) is False
    assert profile.should_run_web(has_useful=False) is True
    assert profile.site_analysis_limit == 1


def test_deep_is_engine_ready_and_keeps_all_sources_with_four_sites():
    profile = EnrichmentMethodCatalog.get("deep")
    assert profile.engine_ready is True
    assert profile.should_run_google(has_useful=True) is True
    assert profile.should_run_118000(has_phone=True) is True
    assert profile.should_run_web(has_useful=True) is True
    assert profile.site_analysis_limit == 4


def test_excel_routes_to_excel_module_not_web_engine():
    profile = EnrichmentMethodCatalog.get("excel")
    assert profile.uses_excel is True
    assert profile.engine_ready is False
    assert profile.site_analysis_limit == 0


def test_runtime_defaults_to_standard_and_can_activate_web_profile():
    EnrichmentMethodRuntime.reset()
    assert EnrichmentMethodRuntime.active_key() == "standard"
    profile = EnrichmentMethodRuntime.activate("rapid")
    assert profile.key == "rapid"
    assert EnrichmentMethodRuntime.active_profile().key == "rapid"
    EnrichmentMethodRuntime.reset()


def test_runtime_rejects_excel_activation():
    EnrichmentMethodRuntime.reset()
    with pytest.raises(ValueError):
        EnrichmentMethodRuntime.activate("excel")
    assert EnrichmentMethodRuntime.active_key() == "standard"


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError):
        EnrichmentMethodCatalog.get("turbo")
