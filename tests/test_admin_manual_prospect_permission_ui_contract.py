from __future__ import annotations

import ast
from pathlib import Path


PAGE = (
    Path(__file__).parents[1]
    / "ui"
    / "pages"
    / "admin_account_page.py"
)

SOURCE = PAGE.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def _method(name: str) -> ast.FunctionDef:
    for node in ast.walk(TREE):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == name
        ):
            return node

    raise AssertionError(
        f"Methode absente : {name}"
    )


def _source(name: str) -> str:
    node = _method(name)
    return ast.get_source_segment(
        SOURCE,
        node,
    ) or ""


def test_admin_page_exposes_manual_prospect_permission_button():
    assert (
        "manual_prospect_permission_button"
        in SOURCE
    )
    assert (
        "_toggle_manual_prospect_permission"
        in SOURCE
    )


def test_manual_permission_is_kept_in_hidden_row_metadata():
    assert "Qt.UserRole" in SOURCE

    selected = _source(
        "_selected_user_details"
    )

    assert (
        "can_create_prospect_manually"
        in selected
    )
    assert "data(Qt.UserRole)" in selected


def test_manual_permission_button_is_restricted_to_commercials():
    segment = _source(
        "_update_manual_prospect_permission_button"
    )

    assert (
        'details["role"] == "Commercial"'
        in segment
    )
    assert "setEnabled(enabled)" in segment
    assert "setVisible(False)" in segment


def test_manual_permission_action_uses_cloud_admin_service():
    segment = _source(
        "_toggle_manual_prospect_permission"
    )

    assert (
        "set_manual_prospect_creation_permission"
        in segment
    )
    assert (
        "new_allowed = not currently_allowed"
        in segment
    )
    assert "self.rafraichir()" in segment
