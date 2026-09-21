from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import core.theme_settings as theme_settings
import ui.windows.main_window as main_window_module
from core.theme_settings import THEME_UI_DARK, THEME_UI_LIGHT
from ui.windows.main_window import MainWindow


class FakePages:
    def __init__(self, page):
        self.widgets = [page]
        self.current = page

    def currentWidget(self):
        return self.current

    def indexOf(self, page):
        try:
            return self.widgets.index(page)
        except ValueError:
            return -1

    def insertWidget(self, index, page):
        self.widgets.insert(index, page)

    def removeWidget(self, page):
        if page in self.widgets:
            self.widgets.remove(page)

    def addWidget(self, page):
        self.widgets.append(page)

    def setCurrentWidget(self, page):
        self.current = page


class OldAdminPage:
    def __init__(self, *, classic):
        self._classic_mode = classic
        self.service = object()
        self.applied = 0
        self.deleted = 0

    def _apply_visual_theme(self):
        self.applied += 1

    def deleteLater(self):
        self.deleted += 1


class NewAdminPage:
    def __init__(self, *, service, auto_refresh):
        self.service = service
        self.auto_refresh = auto_refresh
        self.refresh_count = 0

    def rafraichir(self):
        self.refresh_count += 1


def test_runtime_sync_rebuilds_admin_when_crossing_classic_to_premium(monkeypatch):
    old = OldAdminPage(classic=True)
    pages = FakePages(old)
    window = SimpleNamespace(
        pages=pages,
        admin_commercial_projects_page=old,
        admin_commercial_project_service=old.service,
        commercial_projects_page=None,
    )

    monkeypatch.setattr(
        theme_settings,
        "get_theme_preference",
        lambda: THEME_UI_DARK,
    )
    monkeypatch.setattr(
        main_window_module,
        "AdminCommercialProjectsPage",
        NewAdminPage,
    )

    MainWindow._sync_commercial_project_theme_pages(window)

    new = window.admin_commercial_projects_page
    assert isinstance(new, NewAdminPage)
    assert new.service is old.service
    assert new.auto_refresh is False
    assert new.refresh_count == 1
    assert pages.current is new
    assert old.deleted == 1


def test_runtime_sync_keeps_premium_page_between_light_and_dark(monkeypatch):
    old = OldAdminPage(classic=False)
    pages = FakePages(old)
    window = SimpleNamespace(
        pages=pages,
        admin_commercial_projects_page=old,
        commercial_projects_page=None,
    )

    monkeypatch.setattr(
        theme_settings,
        "get_theme_preference",
        lambda: THEME_UI_LIGHT,
    )

    MainWindow._sync_commercial_project_theme_pages(window)

    assert window.admin_commercial_projects_page is old
    assert old.applied == 1
    assert old.deleted == 0
    assert pages.current is old


def test_main_window_calls_runtime_sync_after_appearance_change():
    source = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "windows"
        / "main_window.py"
    ).read_text(encoding="utf-8")
    block = source.split("def ouvrir_apparence(self):", 1)[1].split(
        "\n    def ",
        1,
    )[0]
    assert "MainWindow._sync_commercial_project_theme_pages(self)" in block
