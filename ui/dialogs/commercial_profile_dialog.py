
from __future__ import annotations

import re

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QTextEdit, QVBoxLayout, QWidget,
)

from core.premium_theme import (
    BORDER, CARD, MUTED, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT,
)
from services.cloud_api_client import CloudAPIError


class CloudCommercialProfileDialog(QDialog):
    def __init__(self, api, parent=None, *, profile: dict | None = None):
        super().__init__(parent)
        self.api = api
        self.profile = dict(profile or {})
        self.saved_profile: dict | None = None
        self.setWindowTitle("Fiche commercial")
        self.resize(760, 790)
        self._build_ui()
        self._populate()

    @staticmethod
    def _line(placeholder: str = "") -> QLineEdit:
        editor = QLineEdit()
        editor.setMinimumHeight(34)
        editor.setPlaceholderText(placeholder)
        return editor

    @staticmethod
    def _date_editor() -> QDateEdit:
        editor = QDateEdit()
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd/MM/yyyy")
        editor.setDate(QDate.currentDate())
        editor.setMinimumHeight(34)
        return editor

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel(
            "Modifier la fiche commerciale"
            if self.profile
            else "Ajouter un commercial à l'annuaire Cloud"
        )
        title.setStyleSheet(f"color:{TEXT}; font-size:23px; font-weight:900;")
        subtitle = QLabel(
            "Renseignez les informations du setter, closer ou manager commercial. "
            "Les documents administratifs restent facultatifs selon son statut."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

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

        self.commercial_role = QComboBox()
        self.commercial_role.setMinimumHeight(34)
        self.commercial_role.addItem("Setter", "setter")
        self.commercial_role.addItem("Closer", "closer")
        self.commercial_role.addItem("Setter / Closer", "setter_closer")
        self.commercial_role.addItem("Manager commercial", "manager")
        self.commercial_role.addItem("Autre", "other")

        self.professional_status = QComboBox()
        self.professional_status.setMinimumHeight(34)
        self.professional_status.addItem("Sous-traitant", "subcontractor")
        self.professional_status.addItem("Indépendant", "independent")
        self.professional_status.addItem("Salarié", "employee")

        self.siret = self._line("14 chiffres")
        self.business_name = self._line("Nom commercial / raison sociale à afficher sur la facture")
        self.billing_address = self._line("Adresse de facturation")
        self.billing_postal_code = self._line("Code postal")
        self.billing_city = self._line("Ville")
        self.billing_country = self._line("France")
        self.billing_country.setText("France")
        self.vat_number = self._line("N° TVA intracommunautaire si applicable")
        self.vat_mention = self._line("Ex. TVA non applicable, art. 293 B du CGI")
        self.specialties = QTextEdit()
        self.specialties.setMinimumHeight(54)
        self.specialties.setPlaceholderText(
            "Ex. Prospection B2B, BTP, qualification, closing"
        )
        self.diplomas = QTextEdit()
        self.diplomas.setMinimumHeight(54)
        self.diplomas.setPlaceholderText("Diplômes ou formations commerciales")
        self.certifications = QTextEdit()
        self.certifications.setMinimumHeight(54)
        self.certifications.setPlaceholderText("Certifications éventuelles")
        self.nda = self._line("Numéro éventuel")
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

        self.contract_present = QCheckBox(
            "Contrat / convention de prestation présent"
        )
        self.notes = QTextEdit()
        self.notes.setMinimumHeight(64)
        self.notes.setPlaceholderText("Notes internes administratives")

        form.addRow("Prénom *", self.first_name)
        form.addRow("Nom *", self.last_name)
        form.addRow("E-mail", self.email)
        form.addRow("Téléphone", self.phone)
        form.addRow("Fonction commerciale", self.commercial_role)
        form.addRow("Statut professionnel", self.professional_status)
        form.addRow("SIRET", self.siret)
        form.addRow("Nom sur facture", self.business_name)
        form.addRow("Adresse facturation", self.billing_address)
        form.addRow("Code postal", self.billing_postal_code)
        form.addRow("Ville", self.billing_city)
        form.addRow("Pays", self.billing_country)
        form.addRow("N° TVA", self.vat_number)
        form.addRow("Mention TVA", self.vat_mention)
        form.addRow("Spécialités", self.specialties)
        form.addRow("Diplômes", self.diplomas)
        form.addRow("Certifications", self.certifications)
        form.addRow("NDA / n° déclaration", self.nda)
        form.addRow("RC professionnelle", self.rc_reference)
        form.addRow("Validité RC Pro", rc_row)
        form.addRow("Vigilance URSSAF", urssaf_row)
        form.addRow("Contrat", self.contract_present)
        form.addRow("Notes internes", self.notes)

        scroll_layout.addWidget(card)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)

        self.save_button = QPushButton(
            "Enregistrer les modifications"
            if self.profile
            else "Créer le commercial"
        )
        self.save_button.setStyleSheet(PRIMARY_BUTTON)
        self.save_button.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(self.save_button)
        root.addLayout(actions)

    @staticmethod
    def _set_iso_date(check, editor, value) -> None:
        text = str(value or "").strip()
        date = QDate.fromString(text[:10], "yyyy-MM-dd")
        if date.isValid():
            check.setChecked(True)
            editor.setDate(date)

    def _populate(self) -> None:
        if not self.profile:
            return
        self.first_name.setText(str(self.profile.get("first_name") or ""))
        self.last_name.setText(str(self.profile.get("last_name") or ""))
        self.email.setText(str(self.profile.get("email") or ""))
        self.phone.setText(str(self.profile.get("phone") or ""))

        role_index = self.commercial_role.findData(
            str(self.profile.get("commercial_role") or "setter_closer")
        )
        if role_index >= 0:
            self.commercial_role.setCurrentIndex(role_index)

        status_index = self.professional_status.findData(
            str(self.profile.get("professional_status") or "subcontractor")
        )
        if status_index >= 0:
            self.professional_status.setCurrentIndex(status_index)

        self.siret.setText(str(self.profile.get("siret") or ""))
        self.business_name.setText(str(self.profile.get("business_name") or ""))
        self.billing_address.setText(str(self.profile.get("billing_address") or ""))
        self.billing_postal_code.setText(str(self.profile.get("billing_postal_code") or ""))
        self.billing_city.setText(str(self.profile.get("billing_city") or ""))
        self.billing_country.setText(str(self.profile.get("billing_country") or "France"))
        self.vat_number.setText(str(self.profile.get("vat_number") or ""))
        self.vat_mention.setText(str(self.profile.get("vat_mention") or ""))
        self.specialties.setPlainText(str(self.profile.get("specialties") or ""))
        self.diplomas.setPlainText(str(self.profile.get("diplomas") or ""))
        self.certifications.setPlainText(
            str(self.profile.get("certifications") or "")
        )
        self.nda.setText(
            str(self.profile.get("activity_declaration_number") or "")
        )
        self.rc_reference.setText(
            str(self.profile.get("rc_pro_reference") or "")
        )
        self._set_iso_date(
            self.rc_has_expiry, self.rc_expiry,
            self.profile.get("rc_pro_expires_on"),
        )
        self._set_iso_date(
            self.urssaf_has_expiry, self.urssaf_expiry,
            self.profile.get("urssaf_expires_on"),
        )
        self.contract_present.setChecked(
            bool(self.profile.get("contract_present"))
        )
        self.notes.setPlainText(str(self.profile.get("notes") or ""))

    def _save(self) -> None:
        first_name = self.first_name.text().strip()
        last_name = self.last_name.text().strip()
        if not first_name or not last_name:
            QMessageBox.warning(
                self,
                "Fiche incomplète",
                "Le prénom et le nom du commercial sont obligatoires.",
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

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "commercial_role": str(
                self.commercial_role.currentData() or "setter_closer"
            ),
            "professional_status": str(
                self.professional_status.currentData() or "subcontractor"
            ),
            "siret": siret,
            "business_name": self.business_name.text().strip(),
            "billing_address": self.billing_address.text().strip(),
            "billing_postal_code": self.billing_postal_code.text().strip(),
            "billing_city": self.billing_city.text().strip(),
            "billing_country": self.billing_country.text().strip() or "France",
            "vat_number": self.vat_number.text().strip(),
            "vat_mention": self.vat_mention.text().strip(),
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
            if self.profile:
                self.saved_profile = self.api.update_cloud_commercial_profile(
                    str(self.profile.get("id") or ""), payload
                )
            else:
                self.saved_profile = self.api.create_cloud_commercial_profile(
                    payload
                )
        except CloudAPIError as exc:
            self.save_button.setEnabled(True)
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Commercial enregistré",
            "La fiche commerciale a été enregistrée dans l'annuaire Cloud.",
        )
        self.accept()
