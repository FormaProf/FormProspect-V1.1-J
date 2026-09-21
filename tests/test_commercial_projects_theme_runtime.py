from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ui.windows.main_window import MainWindow


class ThemeAwarePage:
    def __init__(self):
        self.applied = 0
        self.deleted = 0

    def _apply_visual_theme(self):
        self.applied += 1

    def deleteLater(self):
        self.deleted += 1


def test_runtime_sync_updates_project_pages_in_place():
    admin = ThemeAwarePage()
    commercial = ThemeAwarePage()
    window = SimpleNamespace(
        admin_commercial_projects_page=admin,
        commercial_projects_page=commercial,
    )

    MainWindow._sync_commercial_project_theme_pages(window)

    assert window.admin_commercial_projects_page is admin
    assert window.commercial_projects_page is commercial
    assert admin.applied == 1
    assert commercial.applied == 1
    assert admin.deleted == 0
    assert commercial.deleted == 0


def test_runtime_sync_does_not_rebuild_widgets():
    source = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "windows"
        / "main_window.py"
    ).read_text(encoding="utf-8")

    block = source.split(
        "def _sync_commercial_project_theme_pages(self):",
        1,
    )[1].split("\n    def ", 1)[0]

    assert "AdminCommercialProjectsPage(" not in block
    assert "CommercialProjectsPage(" not in block
    assert "_apply_visual_theme" in block
    assert "deleteLater" not in block


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
