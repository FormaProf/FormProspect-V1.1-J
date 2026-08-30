from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QMessageBox, QVBoxLayout,
)

from core.premium_theme import MUTED, TEXT


class CloudUserDialog(QDialog):
    ROLES = (
        ("Commercial", "Commercial"),
        ("Manager", "Manager"),
        ("Dirigeant hors France", "Dirigeant hors France"),
        ("Administrateur", "Administrateur"),
        ("Formateur", "Formateur"),
        ("Assistant administratif", "Assistant administratif"),
    )

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.created_user = None
        self.setWindowTitle("Ajouter un utilisateur")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("Ajouter un utilisateur Cloud")
        title.setStyleSheet(f"color:{TEXT};font-size:22px;font-weight:900;")
        root.addWidget(title)

        info = QLabel(
            "Le compte sera créé dans votre organisation Form@Prospect. "
            "L'utilisateur recevra automatiquement un e-mail sécurisé lui "
            "permettant d'activer son accès et de définir son mot de passe."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED};font-size:12px;")
        root.addWidget(info)

        form = QFormLayout()
        form.setSpacing(11)

        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("Prénom")
        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Nom")
        self.email = QLineEdit()
        self.email.setPlaceholderText("exemple@entreprise.fr")

        self.role = QComboBox()
        for label, value in self.ROLES:
            self.role.addItem(label, value)

        form.addRow("Prénom", self.first_name)
        form.addRow("Nom", self.last_name)
        form.addRow("E-mail *", self.email)
        form.addRow("Rôle *", self.role)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Créer et envoyer l'invitation")
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self):
        email = self.email.text().strip().lower()
        first_name = self.first_name.text().strip()
        last_name = self.last_name.text().strip()
        role = str(self.role.currentData() or "Commercial")

        if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            QMessageBox.warning(
                self, "Adresse e-mail", "Saisissez une adresse e-mail valide."
            )
            return

        try:
            self.created_user = self.auth_service.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Création impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Invitation envoyée",
            f"Le compte {email} a été créé.\n\n"
            "Un e-mail d'invitation sécurisé a été envoyé afin que "
            "l'utilisateur puisse activer son compte et définir son mot de passe.",
        )
        self.accept()
