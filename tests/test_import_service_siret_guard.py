import pandas as pd

from core.database import connect_database, init_database
from services.import_service import ImportService


def _excel(path, rows):
    pd.DataFrame(rows).to_excel(path, index=False)


def test_import_local_refuse_siret_invalide_et_doublon_fichier(tmp_path):
    db = tmp_path / "prospects.db"
    xlsx = tmp_path / "prospects.xlsx"

    _excel(
        xlsx,
        [
            {"Entreprise": "Entreprise A", "SIRET": "12345678900011"},
            {"Entreprise": "Doublon A", "SIRET": "12345678900011"},
            {"Entreprise": "Sans SIRET", "SIRET": ""},
            {"Entreprise": "SIRET invalide", "SIRET": "123456789"},
        ],
    )

    total = ImportService().importer_excel_vers_sqlite(xlsx, db)

    assert total == 1

    conn = connect_database(db)
    try:
        rows = conn.execute(
            "SELECT entreprise, siret FROM prospects ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    assert [tuple(row) for row in rows] == [
        ("Entreprise A", "12345678900011")
    ]


def test_import_local_ignore_siret_existant_sans_modifier(tmp_path):
    db = tmp_path / "prospects.db"
    xlsx = tmp_path / "prospects.xlsx"

    init_database(db)

    conn = connect_database(db)
    try:
        conn.execute(
            """
            INSERT INTO prospects (
                entreprise, siret, telephone, commercial_assigne
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "Entreprise originale",
                "12345678900012",
                "0600000000",
                "Commercial A",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    _excel(
        xlsx,
        [
            {
                "Entreprise": "Nom modifié",
                "SIRET": "12345678900012",
                "Téléphone": "0799999999",
            },
            {
                "Entreprise": "Nouvelle entreprise",
                "SIRET": "12345678900013",
            },
        ],
    )

    total = ImportService().importer_excel_vers_sqlite(xlsx, db)

    assert total == 1

    conn = connect_database(db)
    try:
        existing = conn.execute(
            """
            SELECT entreprise, telephone, commercial_assigne
            FROM prospects
            WHERE siret = ?
            """,
            ("12345678900012",),
        ).fetchone()

        count = conn.execute(
            "SELECT COUNT(*) FROM prospects"
        ).fetchone()[0]
    finally:
        conn.close()

    assert tuple(existing) == (
        "Entreprise originale",
        "0600000000",
        "Commercial A",
    )
    assert count == 2


def test_import_local_normalise_siret_formate(tmp_path):
    db = tmp_path / "prospects.db"
    xlsx = tmp_path / "prospects.xlsx"

    _excel(
        xlsx,
        [
            {
                "Entreprise": "Entreprise formatée",
                "SIRET": "123 456 789 000 14",
            }
        ],
    )

    total = ImportService().importer_excel_vers_sqlite(xlsx, db)

    assert total == 1

    conn = connect_database(db)
    try:
        siret = conn.execute(
            "SELECT siret FROM prospects"
        ).fetchone()[0]
    finally:
        conn.close()

    assert siret == "12345678900014"
