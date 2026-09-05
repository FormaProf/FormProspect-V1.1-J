from __future__ import annotations

import ast
from pathlib import Path


PAGE = (
    Path(__file__).parents[1]
    / "ui"
    / "pages"
    / "prospects_page.py"
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


def test_manual_prospect_button_exists_in_toolbar():
    assert "bouton_ajouter_prospect" in SOURCE
    assert "+ Ajouter un prospect" in SOURCE
    assert (
        "toolbar_layout.addWidget("
        "self.bouton_ajouter_prospect)"
        in SOURCE
    )


def test_commercial_uses_individual_manual_permission():
    segment = _source(
        "_peut_creer_prospect_manuellement"
    )

    assert 'role == "Commercial"' in segment
    assert (
        "can_create_prospect_manually"
        in segment
    )


def test_existing_backend_roles_keep_creation_access():
    segment = _source(
        "_peut_creer_prospect_manuellement"
    )

    for role in (
        "Administrateur",
        "Manager",
        "Assistant administratif",
        "Dirigeant hors France",
    ):
        assert role in segment


def test_trainer_has_no_manual_creation_access():
    segment = _source(
        "_peut_creer_prospect_manuellement"
    )

    assert '"Formateur"' not in segment


def test_button_clickability_follows_manual_creation_permission():
    assert (
        "self.bouton_ajouter_prospect.setEnabled("
        in SOURCE
    )
    assert "can_create_manually" in SOURCE
    assert (
        "self.bouton_ajouter_prospect.clicked.connect("
        in SOURCE
    )
    assert (
        "self.ajouter_prospect_manuellement"
        in SOURCE
    )
