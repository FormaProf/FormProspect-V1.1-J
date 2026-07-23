from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox
)

from services.project_manager import ProjectManager
from core.database import init_database


class NewProjectDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nouveau projet")
        self.setFixedSize(420, 260)

        self.project_manager = ProjectManager()

        layout = QVBoxLayout()

        self.nom_input = QLineEdit()
        self.nom_input.setPlaceholderText("Nom du projet")

        self.emplacement_input = QLineEdit()
        self.emplacement_input.setPlaceholderText("Emplacement du projet")

        bouton_parcourir = QPushButton("Parcourir")
        bouton_parcourir.clicked.connect(self.choisir_emplacement)

        bouton_creer = QPushButton("Créer le projet")
        bouton_creer.clicked.connect(self.creer_projet)

        layout.addWidget(QLabel("Nom du projet"))
        layout.addWidget(self.nom_input)
        layout.addWidget(QLabel("Emplacement"))
        layout.addWidget(self.emplacement_input)
        layout.addWidget(bouton_parcourir)
        layout.addWidget(bouton_creer)

        self.setLayout(layout)

    def choisir_emplacement(self):
        dossier = QFileDialog.getExistingDirectory(self, "Choisir un emplacement")
        if dossier:
            self.emplacement_input.setText(dossier)

    def creer_projet(self):
        nom = self.nom_input.text().strip()
        emplacement = self.emplacement_input.text().strip()

        if not nom or not emplacement:
            QMessageBox.warning(self, "Attention", "Merci de renseigner le nom et l'emplacement.")
            return

        projet = self.project_manager.create_project(nom, emplacement)
        init_database(projet.database)

        QMessageBox.information(self, "Succès", "Projet créé avec succès.")
        self.accept()