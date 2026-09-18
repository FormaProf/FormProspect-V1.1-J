from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import patch

from ui.pages.prospects_page import ProspectsPage


@dataclass(frozen=True)
class FakeProject:
    name: str = "Projet Test"
    database: str = "projet.db"


@dataclass(frozen=True)
class FakeContext:
    is_cloud: bool
    project: FakeProject = FakeProject()


class FakeResolver:
    def __init__(self, is_cloud: bool):
        self.context = FakeContext(is_cloud=is_cloud)

    def resolve(self):
        return self.context


class ProspectsPageDataSourceTests(unittest.TestCase):
    def setUp(self):
        self._has_project_patcher = patch(
            "ui.pages.prospects_page.ApplicationState.has_project",
            return_value=True,
        )
        self._has_project_patcher.start()
        self.addCleanup(self._has_project_patcher.stop)

    def _page_without_qt_init(self, is_cloud: bool):
        class PageHarness:
            _data_context = ProspectsPage._data_context
            _database_path = ProspectsPage._database_path
            _is_cloud = ProspectsPage._is_cloud
            _source_name = ProspectsPage._source_name
            _project_scope_id = ProspectsPage._project_scope_id

        page = PageHarness()
        page.datasource_resolver = FakeResolver(is_cloud)
        return page

    def test_local_project_returns_sqlite_path(self):
        page = self._page_without_qt_init(False)
        self.assertEqual(page._database_path(), "projet.db")
        self.assertFalse(page._is_cloud())

    def test_cloud_project_returns_no_sqlite_path(self):
        page = self._page_without_qt_init(True)
        self.assertIsNone(page._database_path())
        self.assertTrue(page._is_cloud())

    def test_cloud_source_name_falls_back_to_formaprospect_cloud(self):
        page = self._page_without_qt_init(True)

        with patch(
            "ui.pages.prospects_page.SessionState.user",
            return_value=None,
        ):
            self.assertEqual(page._source_name(), "Form@Prospect Cloud")

    def test_cloud_crm_project_scope_uses_context_then_selector(self):
        page = self._page_without_qt_init(True)
        page.datasource_resolver.context = type(
            'Context',
            (),
            {
                'is_cloud': True,
                'project_id': 'cloud-project',
                'project': FakeProject(),
            },
        )()

        class Filters:
            selected = ''

            def project_id_selectionne(self):
                return self.selected

        page.filters_bar = Filters()
        page._project_filter_initialized = False

        self.assertEqual(
            page._project_scope_id(),
            'cloud-project',
        )

        page._project_filter_initialized = True
        page.filters_bar.selected = 'project-2'
        self.assertEqual(
            page._project_scope_id(),
            'project-2',
        )

        page.filters_bar.selected = ''
        self.assertIsNone(page._project_scope_id())

    def test_load_uses_selected_cloud_project_for_all_crm_queries(self):
        calls = []

        class Filters:
            def criteres(self):
                return {"recherche": "ACME"}

            def project_id_selectionne(self):
                return "project-2"

            def charger_options(self, *args, **kwargs):
                pass

        class Service:
            def recuperer_options_filtres(self, database_path=None, *, project_id=None):
                calls.append(("options", project_id))
                return {"projects": []}

            def compter_prospects(self, database_path=None, *, project_id=None):
                calls.append(("total", project_id))
                return 1

            def compter_prospects_filtres(self, database_path=None, *, project_id=None, **kwargs):
                calls.append(("filtered", project_id))
                return 1

            def rechercher_prospects_filtres(self, database_path=None, *, project_id=None, **kwargs):
                calls.append(("prospects", project_id))
                return []

        class Widget:
            def setText(self, *parts):
                pass

            def setEnabled(self, *args):
                pass

        class PageHarness:
            DISPLAY_LIMIT = 100
            _lancer_chargement = ProspectsPage._lancer_chargement
            _project_scope_id = ProspectsPage._project_scope_id

            def _database_path(self):
                return None

            def _source_name(self):
                return "Cloud"

            def _filters_active(self, criteres):
                return True

            def calculer_total_pages(self, total):
                return 1

            def mettre_a_jour_infos(self, *args):
                pass

            def mettre_a_jour_pagination_ui(self):
                pass

            def afficher_donnees_vue_active(self):
                pass

            def _start_worker(self, fn, *, on_result, on_error, on_finished):
                payload = fn()
                on_result(payload)
                on_finished()

        page = PageHarness()
        page.filters_bar = Filters()
        page.prospect_service = Service()
        page._project_filter_initialized = True
        page.page_courante = 1
        page._load_generation = 0
        page.label_info = Widget()
        page.label_affichage = Widget()
        page.bouton_rafraichir = Widget()

        page._lancer_chargement(
            reset_page=False,
            reload_options=True,
        )

        self.assertEqual(
            calls,
            [
                ("options", "project-2"),
                ("total", "project-2"),
                ("filtered", "project-2"),
                ("prospects", "project-2"),
            ],
        )

    def test_force_refresh_invalidates_selected_cloud_project_scope(self):
        calls = []

        class Service:
            def invalider_caches(
                self,
                *,
                statistiques=True,
                filtres=True,
                project_id=None,
            ):
                calls.append(project_id)

        class PageHarness:
            charger_prospects = ProspectsPage.charger_prospects
            _project_scope_id = ProspectsPage._project_scope_id

            def _has_data_source(self):
                return True

            def _lancer_chargement(self, *, reset_page, reload_options):
                self.load_args = (reset_page, reload_options)

        class Filters:
            def project_id_selectionne(self):
                return "project-2"

        page = PageHarness()
        page.prospect_service = Service()
        page.filters_bar = Filters()
        page._project_filter_initialized = True
        page._filter_options_loaded = True
        page.page_courante = 3

        page.charger_prospects(force_refresh=True)

        self.assertEqual(calls, ["project-2"])
        self.assertFalse(page._filter_options_loaded)
        self.assertEqual(page.page_courante, 1)
        self.assertEqual(page.load_args, (False, True))

    def test_initial_cloud_project_is_selected_after_options_load(self):
        selections = []

        class Filters:
            def criteres(self):
                return {}

            def charger_options(self, *args, **kwargs):
                pass

            def selectionner_project_id(self, project_id):
                selections.append(project_id)

        class Service:
            def recuperer_options_filtres(
                self,
                database_path=None,
                *,
                project_id=None,
            ):
                return {
                    "projects": [
                        {"id": "cloud-project", "name": "Projet Cloud"},
                    ],
                }

            def compter_prospects(
                self,
                database_path=None,
                *,
                project_id=None,
            ):
                return 0

            def rechercher_prospects_filtres(
                self,
                database_path=None,
                *,
                project_id=None,
                **kwargs,
            ):
                return []

        class Widget:
            def setText(self, *parts):
                pass

            def setEnabled(self, *args):
                pass

        class PageHarness:
            DISPLAY_LIMIT = 100
            _lancer_chargement = ProspectsPage._lancer_chargement

            def _database_path(self):
                return None

            def _project_scope_id(self):
                return "cloud-project"

            def _source_name(self):
                return "Cloud"

            def _filters_active(self, criteres):
                return False

            def calculer_total_pages(self, total):
                return 1

            def mettre_a_jour_infos(self, *args):
                pass

            def mettre_a_jour_pagination_ui(self):
                pass

            def afficher_donnees_vue_active(self):
                pass

            def _start_worker(
                self,
                fn,
                *,
                on_result,
                on_error,
                on_finished,
            ):
                payload = fn()
                on_result(payload)
                on_finished()

        page = PageHarness()
        page.filters_bar = Filters()
        page.prospect_service = Service()
        page._project_filter_initialized = False
        page._filter_options_loaded = False
        page.page_courante = 1
        page._load_generation = 0
        page.label_info = Widget()
        page.label_affichage = Widget()
        page.bouton_rafraichir = Widget()

        page._lancer_chargement(
            reset_page=False,
            reload_options=True,
        )

        self.assertEqual(selections, ["cloud-project"])
        self.assertTrue(page._project_filter_initialized)

    def test_apply_filters_reloads_options_when_project_scope_changes(self):
        class PageHarness:
            appliquer_filtres = ProspectsPage.appliquer_filtres

            def _has_data_source(self):
                return True

            def _project_scope_id(self):
                return self.project_id

            def _lancer_chargement(
                self,
                *,
                reset_page,
                reload_options,
            ):
                self.load_args = (
                    reset_page,
                    reload_options,
                )

        page = PageHarness()
        page.project_id = "project-2"
        page._filter_options_loaded = True
        page._filter_options_project_id = "project-1"

        page.appliquer_filtres(reset_page=True)

        self.assertEqual(
            page.load_args,
            (True, True),
        )

        page._filter_options_project_id = "project-2"
        page.appliquer_filtres(reset_page=True)

        self.assertEqual(
            page.load_args,
            (True, False),
        )


if __name__ == "__main__":
    unittest.main()
