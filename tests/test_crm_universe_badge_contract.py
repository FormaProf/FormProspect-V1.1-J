from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
PROSPECTS = (ROOT / "ui/pages/prospects_page.py").read_text(encoding="utf-8")
PROJECTS = (ROOT / "ui/pages/commercial_projects_page.py").read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")

def test_crm_universe_sources_parse():
    for source in (PROSPECTS, PROJECTS, MAIN):
        ast.parse(source)

def test_crm_badge_is_dynamic_not_hardcoded_ai():
    assert 'QLabel("●  AI CRM  •  LIVE")' not in PROSPECTS
    assert 'QLabel("●  CRM  •  LIVE")' in PROSPECTS
    assert "def set_crm_universe(" in PROSPECTS
    assert 'prefix = f"{normalized.upper()} CRM"' in PROSPECTS

def test_project_page_caches_universe_from_already_loaded_parents():
    assert "def cache_universe_context(self, parents)" in PROJECTS
    assert "def universe_name_for_project(self, project_id: str)" in PROJECTS
    start = PROJECTS.index("def cache_universe_context(self, parents)")
    end = PROJECTS.index("def rafraichir(self):", start)
    block = PROJECTS[start:end]
    assert "self.service." not in block
    assert "CloudRuntime" not in block

def test_universe_cache_is_refreshed_from_existing_parent_payload():
    refresh_start = PROJECTS.index("def rafraichir(self):")
    refresh = PROJECTS[refresh_start:]
    assert "self.cache_universe_context(parents)" in refresh

def test_main_window_propagates_universe_before_opening_crm():
    assert "self.commercial_projects_page.cache_universe_context(parents)" in MAIN
    assert "universe_name_for_project(project_id)" in MAIN
    assert "prospects_page.set_crm_universe(universe_name)" in MAIN
