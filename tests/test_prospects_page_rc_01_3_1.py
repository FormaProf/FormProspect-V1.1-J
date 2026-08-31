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


if __name__ == "__main__":
    unittest.main()
