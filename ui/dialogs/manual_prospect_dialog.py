from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.session import SessionState
from services.cloud_runtime import CloudRuntime


class ManualProspectDialog(QDialog):
    """Cr?ation manuelle d'un prospect Local ou Cloud."""

    def __init__(
        self,
        prospect_service,
        database_path=None,
        *,
        is_cloud_mode=False,
        parent=None,
    ):
        super().__init__(parent)

        self.prospect_service = prospect_service
        self.database_path = database_path
        self.is_cloud_mode = bool(is_cloud_mode)

        self.setWindowTitle("Ajouter un prospect")
        self.setModal(True)
        self.resize(720, 720)

        self._build_ui()
        self._load_owner_choices()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 20)
        root.setSpacing(16)

        title = QLabel("Ajouter un prospect")
        title.setStyleSheet(
            "font-size:22px; font-weight:900; "
            "color:#0B1220; border:none;"
        )

        subtitle = QLabel(
            "Cr?ez une nouvelle fiche prospect. "
            "Le SIRET est obligatoire et doit ?tre unique."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size:12px; color:#64748B; border:none;"
        )

        root.addWidget(title)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(4, 4, 12, 4)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.company_name = self._line(
            "Ex. BAA Plomberie"
        )
        self.siret = self._line(
            "14 chiffres"
        )
        self.contact_first_name = self._line("Pr?nom")
        self.contact_last_name = self._line("Nom")
        self.job_title = self._line(
            "Ex. G?rant, Dirigeant..."
        )
        self.phone = self._line("T?l?phone fixe")
        self.mobile = self._line("06 / 07")
        self.email = self._line("contact@entreprise.fr")
        self.website = self._line("https://...")
        self.address = self._line("Adresse")
        self.postal_code = self._line("Code postal")
        self.city = self._line("Ville")
        self.naf_code = self._line("Ex. 43.99A")

        self.notes = QTextEdit()
        self.notes.setPlaceholderText(
            "Informations utiles sur le prospect..."
        )
        self.notes.setMinimumHeight(90)

        self.owner_combo = QComboBox()
        self.owner_combo.setVisible(False)
        self.owner_label = QLabel("Commercial")
        self.owner_label.setVisible(False)

        form.addRow("Entreprise *", self.company_name)
        form.addRow("SIRET *", self.siret)
        form.addRow("Pr?nom du contact", self.contact_first_name)
        form.addRow("Nom du contact", self.contact_last_name)
        form.addRow("Fonction", self.job_title)
        form.addRow("T?l?phone", self.phone)
        form.addRow("Mobile", self.mobile)
        form.addRow("E-mail", self.email)
        form.addRow("Site Internet", self.website)
        form.addRow("Adresse", self.address)
        form.addRow("Code postal", self.postal_code)
        form.addRow("Ville", self.city)
        form.addRow("Code NAF", self.naf_code)
        form.addRow(self.owner_label, self.owner_combo)
        form.addRow("Notes", self.notes)

        body.setStyleSheet("""
            QLineEdit, QComboBox, QTextEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:8px 10px;
                font-size:12px;
            }

            QLineEdit, QComboBox {
                min-height:38px;
            }

            QLineEdit:focus,
            QComboBox:focus,
            QTextEdit:focus {
                border:2px solid #338CE4;
            }

            QLabel {
                color:#53657C;
                font-size:11px;
                font-weight:800;
                border:none;
            }
        """)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()

        cancel_button = QPushButton("Annuler")
        self.create_button = QPushButton("Ajouter le prospect")

        cancel_button.setFixedHeight(42)
        self.create_button.setFixedHeight(42)

        cancel_button.setStyleSheet("""
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 18px;
                font-weight:800;
            }
            QPushButton:hover {
                background:#F8FBFF;
            }
        """)

        self.create_button.setStyleSheet("""
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 20px;
                font-weight:900;
            }
            QPushButton:hover {
                background:#247CD4;
            }
            QPushButton:disabled {
                background:#AFCDEA;
            }
        """)

        cancel_button.clicked.connect(self.reject)
        self.create_button.clicked.connect(
            self._create_prospect
        )

        actions.addWidget(cancel_button)
        actions.addWidget(self.create_button)

        root.addLayout(actions)

    @staticmethod
    def _line(placeholder):
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        return field

    def _load_owner_choices(self):
        user = SessionState.user()

        if user is None:
            return

        role = str(
            getattr(user, "role", "") or ""
        ).strip()

        if not self.is_cloud_mode or role != "Administrateur":
            return

        try:
            users = CloudRuntime.api().list_users(
                active_only=True
            )
        except Exception:
            return

        self.owner_combo.clear()
        self.owner_combo.addItem(
            "Moi-m?me (Administrateur)",
            None,
        )

        for candidate in users:
            if not getattr(candidate, "is_commercial", False):
                continue

            self.owner_combo.addItem(
                str(candidate.display_name),
                str(candidate.id),
            )

        self.owner_label.setVisible(True)
        self.owner_combo.setVisible(True)

    @staticmethod
    def _normalize_siret(value):
        return "".join(
            char
            for char in str(value or "")
            if char.isdigit()
        )

    def _payload(self):
        siret = self._normalize_siret(
            self.siret.text()
        )

        if not self.company_name.text().strip():
            raise ValueError(
                "Le nom de l'entreprise est obligatoire."
            )

        if len(siret) != 14:
            raise ValueError(
                "Le SIRET doit contenir exactement 14 chiffres."
            )

        payload = {
            "company_name": self.company_name.text().strip(),
            "siret": siret,
            "contact_first_name": (
                self.contact_first_name.text().strip()
            ),
            "contact_last_name": (
                self.contact_last_name.text().strip()
            ),
            "job_title": self.job_title.text().strip(),
            "phone": self.phone.text().strip(),
            "mobile": self.mobile.text().strip(),
            "email": self.email.text().strip(),
            "website": self.website.text().strip(),
            "address": self.address.text().strip(),
            "postal_code": self.postal_code.text().strip(),
            "city": self.city.text().strip(),
            "naf_code": self.naf_code.text().strip(),
            "notes": self.notes.toPlainText().strip(),
            "source": "Saisie manuelle",
        }

        owner_id = self.owner_combo.currentData()

        if (
            self.owner_combo.isVisible()
            and owner_id
        ):
            payload["owner_user_id"] = owner_id

        return payload

    def _create_prospect(self):
        try:
            payload = self._payload()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Informations ? v?rifier",
                str(exc),
            )
            return

        self.create_button.setEnabled(False)

        try:
            self.prospect_service.creer_prospect(
                self.database_path,
                data=payload,
            )

        except Exception as exc:
            status_code = getattr(
                exc,
                "status_code",
                None,
            )

            if status_code == 409:
                message = (
                    "Ce SIRET est d?j? pr?sent dans "
                    "Form@Prospect.\n\n"
                    "Aucun doublon n'a ?t? cr??."
                )
            elif status_code == 403:
                message = (
                    "Votre compte n'est pas autoris? "
                    "? cr?er ou affecter ce prospect."
                )
            elif status_code == 422:
                message = (
                    "Certaines informations sont invalides.\n\n"
                    f"{exc}"
                )
            elif (
                isinstance(exc, ValueError)
                and "SIRET" in str(exc)
            ):
                message = str(exc)
            else:
                message = (
                    "Le prospect n'a pas pu ?tre cr??.\n\n"
                    f"{exc}"
                )

            QMessageBox.warning(
                self,
                "Cr?ation impossible",
                message,
            )

            self.create_button.setEnabled(True)
            return

        self.accept()
