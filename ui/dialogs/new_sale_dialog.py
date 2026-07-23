from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QMessageBox, QTextEdit, QVBoxLayout,
)

from core.session import SessionState
from services.commission_service import CommissionService


class NewSaleDialog(QDialog):
    def __init__(self, service: CommissionService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Enregistrer une vente")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.prospect_combo = QComboBox()
        for prospect in self.service.list_prospects():
            details = " — ".join(x for x in (prospect.get("ville"), prospect.get("telephone")) if x)
            label = prospect["entreprise"] + (f" ({details})" if details else "")
            self.prospect_combo.addItem(label, prospect["id"])

        self.offer_combo = QComboBox()
        for offer in self.service.list_offers():
            self.offer_combo.addItem(
                f"{offer['name']} — {offer['price_cents']/100:,.2f} € — {offer['commission_rate']:g} %".replace(",", " "),
                offer,
            )

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(QDate.currentDate())
        self.date_edit.setToolTip("La date de signature ne peut pas être postérieure à aujourd'hui.")

        self.preview = QLabel()
        self.preview.setStyleSheet(
            "background:#EEF6FF; border:1px solid #BFDBFE; border-radius:10px; "
            "padding:12px; color:#123B63; font-size:14px; font-weight:700;"
        )
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Note facultative sur le contrat signé…")
        self.notes.setFixedHeight(80)

        form.addRow("Client / prospect", self.prospect_combo)
        form.addRow("Offre vendue", self.offer_combo)
        form.addRow("Date de signature", self.date_edit)
        form.addRow("Calcul automatique", self.preview)
        form.addRow("Notes", self.notes)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Enregistrer la vente")
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.offer_combo.currentIndexChanged.connect(self._update_preview)
        self._update_preview()

    def _update_preview(self) -> None:
        offer = self.offer_combo.currentData()
        if not offer:
            self.preview.setText("Aucune offre disponible")
            return
        commission = round(offer["price_cents"] * float(offer["commission_rate"]) / 100)
        self.preview.setText(
            f"Prix : {offer['price_cents']/100:,.2f} €   •   "
            f"Commission : {offer['commission_rate']:g} %   •   "
            f"Montant gagné : {commission/100:,.2f} €"
        .replace(",", " "))

    def _save(self) -> None:
        user = SessionState.user()
        if user is None:
            QMessageBox.warning(self, "Session", "Aucun utilisateur connecté.")
            return
        if self.prospect_combo.currentData() is None:
            QMessageBox.warning(self, "Prospect", "Sélectionnez un prospect.")
            return
        offer = self.offer_combo.currentData()
        if not offer:
            QMessageBox.warning(self, "Offre", "Sélectionnez une offre.")
            return
        qdate = self.date_edit.date()
        signed_at = date(qdate.year(), qdate.month(), qdate.day())
        if signed_at > date.today():
            QMessageBox.warning(
                self,
                "Date de signature",
                "La date de signature ne peut pas être postérieure à la date du jour.",
            )
            return
        try:
            self.service.create_sale(
                prospect_id=int(self.prospect_combo.currentData()),
                offer_id=int(offer["id"]),
                commercial_user_id=user.id,
                commercial_name=user.display_name,
                signed_at=signed_at,
                notes=self.notes.toPlainText(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", str(exc))
            return
        QMessageBox.information(self, "Vente enregistrée", "La vente et la commission ont été enregistrées.")
        self.accept()
