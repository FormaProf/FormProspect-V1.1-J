from pathlib import Path
import ast


SERVICE = Path(__file__).parents[1] / "services" / "enrichment_service.py"
SOURCE = SERVICE.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _method(name):
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Méthode absente : {name}")


def test_service_imports_method_runtime_without_changing_source_modules():
    assert "EnrichmentMethodCatalog" in SOURCE
    assert "EnrichmentMethodRuntime" in SOURCE
    assert "from modules.annuaire_118000 import Annuaire118000Finder" in SOURCE
    assert "from modules.web_fallback import WebFallbackFinder" in SOURCE


def test_public_enrichir_accepts_optional_strategy_and_forwards_it():
    node = _method("enrichir")
    assert any(arg.arg == "strategy" for arg in node.args.args)
    segment = ast.get_source_segment(SOURCE, node)
    assert "strategy=strategy" in segment


def test_async_engine_uses_runtime_when_worker_does_not_pass_strategy():
    segment = ast.get_source_segment(SOURCE, _method("_enrichir_async"))
    assert "EnrichmentMethodRuntime.active_profile()" in segment
    assert "EnrichmentMethodCatalog.get(strategy)" in segment


def test_google_118000_and_web_are_strategy_gated():
    segment = ast.get_source_segment(SOURCE, _method("_enrichir_async"))
    assert "strategy_profile.should_run_google" in segment
    assert "strategy_profile.should_run_118000" in segment
    assert "strategy_profile.should_run_web" in segment


def test_site_analysis_depth_comes_from_profile():
    segment = ast.get_source_segment(SOURCE, _method("_enrichir_async"))
    assert "limit=strategy_profile.site_analysis_limit" in segment


def test_skipped_sources_are_empty_not_fake_valid_results():
    segment = ast.get_source_segment(SOURCE, _method("_empty_source_result"))
    assert '"confidence": "rejected"' in segment
    assert '"technical_errors": []' in segment


def test_e6_phone_quality_rule_still_excludes_explicit_faxes_without_corroboration_requirement():
    segment = ast.get_source_segment(SOURCE, _method("_select_contact_numbers"))
    assert "fax_keys" in segment
    assert "key in fax_keys" in segment
    assert "corroboration" in ast.get_docstring(_method("_select_contact_numbers"))


def test_e6_reliable_site_filter_remains_present():
    segment = ast.get_source_segment(SOURCE, _method("_site_is_reliable"))
    for blocked in ("118000.fr", "pagesjaunes.fr", "facebook.com", "linkedin.com"):
        assert blocked in segment
