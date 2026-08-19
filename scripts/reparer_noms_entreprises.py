from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from services.import_service import ImportService


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    excel_path, _ = QFileDialog.getOpenFileName(
        None,
        "Sélectionner le fichier Excel d'origine",
        "",
        "Fichiers Excel (*.xlsx *.xls)",
    )
    if not excel_path:
        return

    db_path, _ = QFileDialog.getOpenFileName(
        None,
        "Sélectionner la base SQLite du projet à réparer",
        "",
        "Base SQLite (*.db *.sqlite *.sqlite3);;Tous les fichiers (*)",
    )
    if not db_path:
        return

    answer = QMessageBox.question(
        None,
        "Confirmer la réparation",
        "Cette opération ne crée aucun prospect.\n\n"
        "Elle complète uniquement le champ Entreprise des prospects déjà présents "
        "et vides, en les retrouvant par SIRET (ou SIREN).\n\n"
        "Continuer ?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if answer != QMessageBox.Yes:
        return

    try:
        result = ImportService().reparer_noms_entreprises_depuis_excel(
            excel_path,
            db_path,
        )
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Réparation impossible",
            str(exc),
        )
        return

    QMessageBox.information(
        None,
        "Réparation terminée",
        "\n".join(
            [
                f"Lignes Excel analysées : {result['lignes_excel']}",
                f"Prospects réparés : {result['repares']}",
                f"Déjà renseignés : {result['deja_renseignes']}",
                f"Sans SIRET/SIREN : {result['sans_identifiant']}",
                f"Sans nom exploitable : {result['sans_nom_exploitable']}",
                f"Non retrouvés dans le projet : {result['introuvables']}",
            ]
        ),
    )


if __name__ == "__main__":
    main()
