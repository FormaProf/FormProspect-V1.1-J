from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime


PRIMARY = "#338CE4"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#DCE5EF"
BACKGROUND = "#F8FAFC"
CLIENT_STAGE = "gagne"


class CloudClientOnboardingDialog(QDialog):
    """Complete the legal client record before the CRM conversion is committed."""

    def __init__(self, prospect_id: str, parent=None):
        super().__init__(parent)
        self.prospect_id = str(prospect_id)
        self.api = CloudRuntime.api()
        self.prospect: dict = {}
        self.result_data: dict | None = None

        self.setWindowTitle("Finaliser la fiche client")
        self.resize(820, 760)
        self.setMinimumSize(720, 620)
        self._build_ui()
        self._load_prospect()

    @staticmethod
    def _field(placeholder: str = "") -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(40)
        field.setStyleSheet(
            f"QLineEdit{{background:white;color:{TEXT};border:1px solid {BORDER};"
            "border-radius:9px;padding:0 11px;font-size:13px;}"
            f"QLineEdit:focus{{border:2px solid {PRIMARY};}}"
        )
        return field

    @staticmethod
    def _section(title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame{{background:white;border:1px solid {BORDER};border-radius:14px;}}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setStyleSheet(f"font-size:17px;font-weight:900;color:{TEXT};border:none;")
        description = QLabel(subtitle)
        description.setWordWrap(True)
        description.setStyleSheet(f"font-size:12px;color:{MUTED};border:none;")
        layout.addWidget(heading)
        layout.addWidget(description)
        return frame, layout

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("QFrame{background:white;border:none;border-bottom:1px solid #E2E8F0;}")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(28, 22, 28, 18)
        self.title_label = QLabel("Finaliser la transformation en client")
        self.title_label.setStyleSheet(f"font-size:25px;font-weight:900;color:{TEXT};")
        self.subtitle_label = QLabel(
            "Le prospect ne passera au statut Client qu'après validation de toutes "
            "les informations nécessaires aux conventions, factures et dossiers de formation."
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(f"color:{MUTED};font-size:13px;")
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setStyleSheet(f"background:{BACKGROUND};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 22, 28, 22)
        content_layout.setSpacing(16)

        legal_frame, legal_layout = self._section(
            "1. Informations légales de l'entreprise",
            "Ces données seront reprises automatiquement dans les documents administratifs.",
        )
        legal_form = QFormLayout()
        legal_form.setSpacing(11)
        legal_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.company = self._field("Raison sociale")
        self.siret = self._field("14 chiffres")
        self.siret.setMaxLength(14)
        self.siren = self._field("9 chiffres — facultatif")
        self.siren.setMaxLength(9)
        self.address = self._field("Numéro et voie")
        self.postal_code = self._field("Code postal")
        self.city = self._field("Ville")
        self.country = self._field("Pays")
        for label, field in (
            ("Entreprise *", self.company),
            ("SIRET *", self.siret),
            ("SIREN", self.siren),
            ("Adresse *", self.address),
            ("Code postal *", self.postal_code),
            ("Ville *", self.city),
            ("Pays", self.country),
        ):
            legal_form.addRow(label, field)
        legal_layout.addLayout(legal_form)
        content_layout.addWidget(legal_frame)

        representative_frame, representative_layout = self._section(
            "2. Dirigeant ou représentant légal",
            "Le nom et la fonction renseignés ici alimenteront notamment la convention de formation.",
        )
        representative_form = QFormLayout()
        representative_form.setSpacing(11)
        representative_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.first_name = self._field("Prénom")
        self.last_name = self._field("Nom")
        self.job_title = self._field("Ex. Gérant, Présidente, Dirigeant")
        self.email = self._field("adresse@entreprise.fr")
        self.phone = self._field("Téléphone principal")
        self.mobile = self._field("Mobile — facultatif")
        for label, field in (
            ("Prénom *", self.first_name),
            ("Nom *", self.last_name),
            ("Fonction *", self.job_title),
            ("E-mail *", self.email),
            ("Téléphone", self.phone),
            ("Mobile", self.mobile),
        ):
            representative_form.addRow(label, field)
        representative_layout.addLayout(representative_form)
        content_layout.addWidget(representative_frame)


        social_frame, social_layout = self._section(
            "3. Réseaux sociaux et présence en ligne",
            "Ces informations peuvent provenir de l'enrichissement et restent attachées au client.",
        )
        social_form = QFormLayout()
        social_form.setSpacing(11)
        social_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.website = self._field("https://www.entreprise.fr")
        self.linkedin = self._field("https://linkedin.com/company/...")
        self.facebook = self._field("https://facebook.com/...")
        self.instagram = self._field("https://instagram.com/...")
        self.twitter = self._field("https://x.com/...")
        self.youtube = self._field("https://youtube.com/@...")
        self.social_other_urls = QTextEdit()
        self.social_other_urls.setPlaceholderText(
            "Autres URL sociales, une par ligne"
        )
        self.social_other_urls.setFixedHeight(72)

        for label, field in (
            ("Site web", self.website),
            ("LinkedIn", self.linkedin),
            ("Facebook", self.facebook),
            ("Instagram", self.instagram),
            ("X / Twitter", self.twitter),
            ("YouTube", self.youtube),
        ):
            social_form.addRow(label, field)
        social_form.addRow("Autres réseaux", self.social_other_urls)
        social_layout.addLayout(social_form)
        content_layout.addWidget(social_frame)

        info = QLabel(
            "✓ Après validation, le client apparaîtra dans Ventes & commissions et dans la préparation des documents."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#ECFDF3;border:1px solid #ABEFC6;border-radius:10px;"
            "padding:12px;color:#067647;font-weight:700;"
        )
        content_layout.addWidget(info)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QFrame()
        footer.setStyleSheet("QFrame{background:white;border:none;border-top:1px solid #E2E8F0;}")
        actions = QHBoxLayout(footer)
        actions.setContentsMargins(28, 16, 28, 16)
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setMinimumHeight(42)
        cancel.setStyleSheet(
            f"QPushButton{{background:white;color:{TEXT};border:1px solid {BORDER};"
            "border-radius:9px;padding:0 18px;font-weight:800;}"
        )
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Valider la fiche et créer le client")
        self.save_button.setMinimumHeight(42)
        self.save_button.setStyleSheet(
            f"QPushButton{{background:{PRIMARY};color:white;border:none;border-radius:9px;"
            "padding:0 20px;font-weight:900;}QPushButton:hover{background:#256DB4;}"
        )
        self.save_button.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(self.save_button)
        root.addWidget(footer)

    def _load_prospect(self) -> None:
        try:
            self.prospect = self.api.get_prospect(self.prospect_id)
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Fiche client", str(exc))
            self.save_button.setEnabled(False)
            return

        if str(self.prospect.get("pipeline_stage") or "").strip() == CLIENT_STAGE:
            self.setWindowTitle("Modifier la fiche client")
            self.title_label.setText("Modifier la fiche client")
            self.subtitle_label.setText(
                "Mettez à jour les informations légales et le représentant. "
                "Les prochains documents utiliseront automatiquement ces données."
            )
            self.save_button.setText("Enregistrer la fiche client")

        contact_first = str(self.prospect.get("contact_first_name") or "").strip()
        contact_last = str(self.prospect.get("contact_last_name") or "").strip()
        contact_name = str(self.prospect.get("contact_name") or "").strip()
        if not (contact_first or contact_last) and contact_name:
            parts = contact_name.split(maxsplit=1)
            contact_first = parts[0]
            contact_last = parts[1] if len(parts) > 1 else ""

        self.company.setText(str(self.prospect.get("company_name") or ""))
        self.siret.setText(str(self.prospect.get("siret") or ""))
        self.siren.setText(str(self.prospect.get("siren") or ""))
        self.address.setText(str(self.prospect.get("address") or ""))
        self.postal_code.setText(str(self.prospect.get("postal_code") or ""))
        self.city.setText(str(self.prospect.get("city") or ""))
        self.country.setText(str(self.prospect.get("country") or "France"))
        self.first_name.setText(contact_first)
        self.last_name.setText(contact_last)
        self.job_title.setText(str(self.prospect.get("job_title") or ""))
        self.email.setText(str(self.prospect.get("email") or ""))
        self.phone.setText(str(self.prospect.get("phone") or ""))
        self.mobile.setText(str(self.prospect.get("mobile") or ""))
        self.website.setText(str(self.prospect.get("website") or ""))
        self.linkedin.setText(str(self.prospect.get("linkedin") or ""))
        self.facebook.setText(str(self.prospect.get("facebook") or ""))
        self.instagram.setText(str(self.prospect.get("instagram") or ""))
        self.twitter.setText(str(self.prospect.get("twitter") or ""))
        self.youtube.setText(str(self.prospect.get("youtube") or ""))
        self.social_other_urls.setPlainText(
            str(self.prospect.get("social_other_urls") or "")
        )

    def _required_values(self) -> list[tuple[str, QLineEdit]]:
        return [
            ("l'entreprise", self.company),
            ("le SIRET", self.siret),
            ("l'adresse", self.address),
            ("le code postal", self.postal_code),
            ("la ville", self.city),
            ("le prénom du dirigeant", self.first_name),
            ("le nom du dirigeant", self.last_name),
            ("la fonction du dirigeant", self.job_title),
            ("l'adresse e-mail", self.email),
        ]

    def _validate(self) -> bool:
        missing = [label for label, field in self._required_values() if not field.text().strip()]
        if not self.phone.text().strip() and not self.mobile.text().strip():
            missing.append("un téléphone ou un mobile")
        if missing:
            QMessageBox.warning(
                self,
                "Fiche client incomplète",
                "Renseignez : " + ", ".join(missing) + ".",
            )
            return False
        siret = re.sub(r"\D", "", self.siret.text())
        if len(siret) != 14:
            QMessageBox.warning(self, "SIRET", "Le SIRET doit contenir exactement 14 chiffres.")
            return False
        siren = re.sub(r"\D", "", self.siren.text())
        if siren and len(siren) != 9:
            QMessageBox.warning(self, "SIREN", "Le SIREN doit contenir exactement 9 chiffres.")
            return False
        if "@" not in self.email.text().strip():
            QMessageBox.warning(self, "E-mail", "L'adresse e-mail n'est pas valide.")
            return False
        return True

    def _save(self) -> None:
        if not self._validate():
            return
        first_name = self.first_name.text().strip()
        last_name = self.last_name.text().strip()
        payload = {
            "company_name": self.company.text().strip(),
            "siret": re.sub(r"\D", "", self.siret.text()),
            "siren": re.sub(r"\D", "", self.siren.text()),
            "address": self.address.text().strip(),
            "postal_code": self.postal_code.text().strip(),
            "city": self.city.text().strip(),
            "country": self.country.text().strip() or "France",
            "contact_first_name": first_name,
            "contact_last_name": last_name,
            "contact_name": f"{first_name} {last_name}".strip(),
            "job_title": self.job_title.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "mobile": self.mobile.text().strip(),
            "website": self.website.text().strip(),
            "linkedin": self.linkedin.text().strip(),
            "facebook": self.facebook.text().strip(),
            "instagram": self.instagram.text().strip(),
            "twitter": self.twitter.text().strip(),
            "youtube": self.youtube.text().strip(),
            "social_other_urls": self.social_other_urls.toPlainText().strip(),
            "next_action": "Préparer les documents de formation",
        }
        self.save_button.setEnabled(False)
        try:
            current_stage = str(
                self.prospect.get("pipeline_stage") or ""
            ).strip()

            self.result_data = self.api.update_prospect(
                self.prospect_id,
                payload,
            )

            if current_stage != CLIENT_STAGE:
                self.api.change_stage(
                    self.prospect_id,
                    CLIENT_STAGE,
                    note=(
                        "Qualification en client après validation "
                        "de la fiche client complète."
                    ),
                )
                self.result_data = self.api.get_prospect(
                    self.prospect_id
                )

        except CloudAPIError as exc:
            self.save_button.setEnabled(True)
            QMessageBox.critical(
                self,
                "Transformation impossible",
                str(exc),
            )
            return

        self.accept()
