from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from core.session import SessionState
from ui.widgets.sidebar import Sidebar


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def build_sidebar(monkeypatch, role):
    user = SimpleNamespace(role=role, display_name="Test User", photo_path=None)
    monkeypatch.setattr(SessionState, "user", staticmethod(lambda: user))
    return Sidebar()


def test_commercial_projects_entry_is_available_to_commercial_and_manager(qapp, monkeypatch):
    commercial = build_sidebar(monkeypatch, "Commercial")

    assert "commercial_projects" in commercial.buttons_by_key
    assert not commercial.buttons_by_key["commercial_projects"].isHidden()
    assert "Mes projets commerciaux" in commercial.buttons_by_key["commercial_projects"].text()

    manager = build_sidebar(monkeypatch, "Manager")
    assert not manager.buttons_by_key["commercial_projects"].isHidden()
    assert "Projets de mon équipe" in manager.buttons_by_key["commercial_projects"].text()

    for role in ("Administrateur", "Formateur"):
        sidebar = build_sidebar(monkeypatch, role)
        assert sidebar.buttons_by_key["commercial_projects"].isHidden()


def test_admin_commercial_projects_entry_is_reserved_to_admin(qapp, monkeypatch):
    admin = build_sidebar(monkeypatch, "Administrateur")

    assert "admin_commercial_projects" in admin.buttons_by_key
    assert not admin.buttons_by_key["admin_commercial_projects"].isHidden()

    for role in ("Manager", "Commercial", "Formateur"):
        sidebar = build_sidebar(monkeypatch, role)
        assert sidebar.buttons_by_key["admin_commercial_projects"].isHidden()
