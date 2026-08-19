from __future__ import annotations

import re

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from services.cloud_api_client import CloudAPIError


class CloudTrainerDialog(QDialog):
    """Création et modification d'une fiche formateur Cloud."""

    def __init__(self, api, parent=None, trainer: dict | None = None):
        super().__init__(parent)
        self.api = api
        self.trainer = dict(trainer or {})
        self.saved_trainer: dict | None = None
        self.setWindowTitle(
            "Modifier le formateur" if self.trainer else "Ajouter un formateur"
        )
        self.resize(760, 820)
        self._build_ui()
        self._populate()

    @staticmethod
    def _line(placeholder: str = "") -> QLineEdit:
        field = QLineEdit()
        field.setMinimumHeight(34)
        field.setPlaceholderText(placeholder)
        return field

    @staticmethod
    def _date_editor() -> QDateEdit:
        editor = QDateEdit(QDate.currentDate())
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd/MM/yyyy")
        editor.setMinimumHeight(34)
        calendar = editor.calendarWidget()
        if calendar is not None:
            calendar.setNavigationBarVisible(True)
            calendar.setMinimumWidth(300)
            calendar.setStyleSheet(
                "QCalendarWidget QWidget#qt_calendar_navigationbar{"
                "background:#F8FAFC;border-bottom:1px solid #D9E2EC;}"
                "QCalendarWidget QToolButton{color:#10233C;background:transparent;"
                "border:none;font-weight:800;padding:5px 8px;}"
                "QCalendarWidget QToolButton#qt_calendar_monthbutton{min-width:95px;}"
                "QCalendarWidget QToolButton#qt_calendar_yearbutton{min-width:55px;}"
                "QCalendarWidget QSpinBox,QCalendarWidget QMenu{"
                "color:#10233C;background:#FFFFFF;}"
                "QCalendarWidget QAbstractItemView:enabled{color:#10233C;"
                "background:#FFFFFF;selection-background-color:#338CE4;"
                "selection-color:#FFFFFF;}"
            )
        return editor

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel(
            "Modifier la fiche formateur"
            if self.trainer
            else "Ajouter un formateur à l'annuaire Cloud"
        )
        title.setStyleSheet(f"color:{TEXT}; font-size:23px; font-weight:900;")
        subtitle = QLabel(
            "Ces informations seront réutilisées dans les sessions, les documents "
            "administratifs et le suivi Qualiopi."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title)
        root.addWidget(subtitle)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        self.first_name = self._line("Prénom")
        self.last_name = self._line("Nom")
        self.email = self._line("Adresse e-mail professionnelle")
        self.phone = self._line("Téléphone")
        self.professional_status = QComboBox()
        self.professional_status.setMinimumHeight(34)
        self.professional_status.addItem("Sous-traitant", "subcontractor")
        self.professional_status.addItem("Indépendant", "independent")
        self.professional_status.addItem("Salarié", "employee")
        self.siret = self._line("14 chiffres")
        self.availability_url = self._line(
            "Lien Google Sheets / Google Calendar / agenda en ligne"
        )
        self.specialties = QTextEdit()
        self.specialties.setMinimumHeight(58)
        self.specialties.setPlaceholderText("Ex. Excel, bureautique, pilotage d'activité")
        self.diplomas = QTextEdit()
        self.diplomas.setMinimumHeight(58)
        self.diplomas.setPlaceholderText("Ex. Titre professionnel FPA")
        self.certifications = QTextEdit()
        self.certifications.setMinimumHeight(58)
        self.certifications.setPlaceholderText("Ex. TOSA Excel Expert — 920/1000")
        self.nda = self._line("Numéro de déclaration d'activité éventuel")
        self.rc_reference = self._line("Référence de l'assurance RC Pro")

        rc_row = QHBoxLayout()
        self.rc_has_expiry = QCheckBox("Échéance")
        self.rc_expiry = self._date_editor()
        self.rc_expiry.setEnabled(False)
        self.rc_has_expiry.toggled.connect(self.rc_expiry.setEnabled)
        rc_row.addWidget(self.rc_has_expiry)
        rc_row.addWidget(self.rc_expiry, 1)

        urssaf_row = QHBoxLayout()
        self.urssaf_has_expiry = QCheckBox("Attestation disponible jusqu'au")
        self.urssaf_expiry = self._date_editor()
        self.urssaf_expiry.setEnabled(False)
        self.urssaf_has_expiry.toggled.connect(self.urssaf_expiry.setEnabled)
        urssaf_row.addWidget(self.urssaf_has_expiry)
        urssaf_row.addWidget(self.urssaf_expiry, 1)

        self.contract_present = QCheckBox("Contrat de prestation présent")
        self.notes = QTextEdit()
        self.notes.setMinimumHeight(64)
        self.notes.setPlaceholderText("Notes internes administratives")

        form.addRow("Prénom *", self.first_name)
        form.addRow("Nom *", self.last_name)
        form.addRow("E-mail", self.email)
        form.addRow("Téléphone", self.phone)
        form.addRow("Statut professionnel", self.professional_status)
        form.addRow("SIRET", self.siret)
        form.addRow("Lien disponibilités", self.availability_url)
        form.addRow("Spécialités", self.specialties)
        form.addRow("Diplômes", self.diplomas)
        form.addRow("Certifications", self.certifications)
        form.addRow("NDA", self.nda)
        form.addRow("RC professionnelle", self.rc_reference)
        form.addRow("Validité RC Pro", rc_row)
        form.addRow("Vigilance URSSAF", urssaf_row)
        form.addRow("Contrat", self.contract_present)
        form.addRow("Notes internes", self.notes)
        root.addWidget(card, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(
            "Enregistrer les modifications" if self.trainer else "Créer le formateur"
        )
        self.save_button.setStyleSheet(PRIMARY_BUTTON)
        self.save_button.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(self.save_button)
        root.addLayout(actions)

    @staticmethod
    def _set_iso_date(
        check: QCheckBox,
        editor: QDateEdit,
        value: object,
    ) -> None:
        text = str(value or "").strip()
        date = QDate.fromString(text[:10], "yyyy-MM-dd")
        if date.isValid():
            check.setChecked(True)
            editor.setDate(date)

    def _populate(self) -> None:
        if not self.trainer:
            return
        self.first_name.setText(str(self.trainer.get("first_name") or ""))
        self.last_name.setText(str(self.trainer.get("last_name") or ""))
        self.email.setText(str(self.trainer.get("email") or ""))
        self.phone.setText(str(self.trainer.get("phone") or ""))
        status = self.professional_status.findData(
            str(self.trainer.get("professional_status") or "subcontractor")
        )
        if status >= 0:
            self.professional_status.setCurrentIndex(status)
        self.siret.setText(str(self.trainer.get("siret") or ""))
        self.availability_url.setText(
            str(self.trainer.get("availability_url") or "")
        )
        self.specialties.setPlainText(str(self.trainer.get("specialties") or ""))
        self.diplomas.setPlainText(str(self.trainer.get("diplomas") or ""))
        self.certifications.setPlainText(
            str(self.trainer.get("certifications") or "")
        )
        self.nda.setText(
            str(self.trainer.get("activity_declaration_number") or "")
        )
        self.rc_reference.setText(
            str(self.trainer.get("rc_pro_reference") or "")
        )
        self._set_iso_date(
            self.rc_has_expiry,
            self.rc_expiry,
            self.trainer.get("rc_pro_expires_on"),
        )
        self._set_iso_date(
            self.urssaf_has_expiry,
            self.urssaf_expiry,
            self.trainer.get("urssaf_expires_on"),
        )
        self.contract_present.setChecked(
            bool(self.trainer.get("contract_present"))
        )
        self.notes.setPlainText(str(self.trainer.get("notes") or ""))

    def _save(self) -> None:
        first_name = self.first_name.text().strip()
        last_name = self.last_name.text().strip()
        if not first_name or not last_name:
            QMessageBox.warning(
                self,
                "Fiche incomplète",
                "Le prénom et le nom du formateur sont obligatoires.",
            )
            return

        siret = re.sub(r"\s+", "", self.siret.text())
        if siret and (len(siret) != 14 or not siret.isdigit()):
            QMessageBox.warning(
                self,
                "SIRET invalide",
                "Le SIRET doit contenir exactement 14 chiffres.",
            )
            return

        availability_url = self.availability_url.text().strip()
        if availability_url and not availability_url.lower().startswith(
            ("http://", "https://")
        ):
            QMessageBox.warning(
                self,
                "Lien de disponibilités invalide",
                "Le lien doit commencer par http:// ou https://.",
            )
            return

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "professional_status": str(
                self.professional_status.currentData() or "subcontractor"
            ),
            "siret": siret,
            "availability_url": availability_url,
            "specialties": self.specialties.toPlainText().strip(),
            "diplomas": self.diplomas.toPlainText().strip(),
            "certifications": self.certifications.toPlainText().strip(),
            "activity_declaration_number": self.nda.text().strip(),
            "rc_pro_reference": self.rc_reference.text().strip(),
            "rc_pro_expires_on": (
                self.rc_expiry.date().toString("yyyy-MM-dd")
                if self.rc_has_expiry.isChecked()
                else None
            ),
            "urssaf_expires_on": (
                self.urssaf_expiry.date().toString("yyyy-MM-dd")
                if self.urssaf_has_expiry.isChecked()
                else None
            ),
            "contract_present": self.contract_present.isChecked(),
            "notes": self.notes.toPlainText().strip(),
        }

        self.save_button.setEnabled(False)
        try:
            if self.trainer:
                self.saved_trainer = self.api.update_cloud_trainer(
                    str(self.trainer.get("id") or ""),
                    payload,
                )
            else:
                self.saved_trainer = self.api.create_cloud_trainer(payload)
        except CloudAPIError as exc:
            self.save_button.setEnabled(True)
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Formateur enregistré",
            "La fiche formateur a été enregistrée dans l'annuaire Cloud.",
        )
        self.accept()
