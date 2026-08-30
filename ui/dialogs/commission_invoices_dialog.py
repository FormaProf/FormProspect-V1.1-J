from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.premium_theme import BORDER, MUTED, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.commission_invoice_pdf import save_invoice_pdf


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class CommissionInvoicesDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.rows: list[dict] = []
        self.setWindowTitle("Historique des factures de commissions")
        self.resize(1050, 650)
        self._build_ui()
        self.rafraichir()

    @staticmethod
    def _euro(cents: int) -> str:
        return f"{int(cents or 0)/100:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _date_fr(value) -> str:
        text = str(value or "")
        if len(text) >= 10 and text[4] == "-":
            return f"{text[8:10]}/{text[5:7]}/{text[:4]}"
        return text

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 22)
        root.setSpacing(12)

        title = QLabel("Mes factures de commissions" if SessionState.has_role("Commercial")
                       else "Factures de commissions")
        title.setStyleSheet(f"font-size:24px;font-weight:900;color:{TEXT};")
        subtitle = QLabel(
            "Chaque facture conserve le détail exact des commissions incluses. "
            "Une commission ne peut être facturée qu'une seule fois."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["N° facture", "Période", "Émission", "Paiement prévu",
             "Commissions", "À payer", "Statut"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet(
            f"QTableWidget{{background:white;color:{TEXT};border:1px solid {BORDER};"
            f"gridline-color:{BORDER};}}"
        )
        root.addWidget(self.table, 1)

        bar = QHBoxLayout()
        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED};")
        bar.addWidget(self.status, 1)

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)

        download = QPushButton("Télécharger PDF")
        download.setStyleSheet(PRIMARY_BUTTON)
        download.clicked.connect(self._download)

        self.paid = QPushButton("Marquer payée")
        self.paid.setStyleSheet(SECONDARY_BUTTON)
        self.paid.setVisible(SessionState.has_role("Administrateur"))
        self.paid.clicked.connect(self._mark_paid)

        close = QPushButton("Fermer")
        close.setStyleSheet(SECONDARY_BUTTON)
        close.clicked.connect(self.accept)

        bar.addWidget(refresh)
        bar.addWidget(download)
        bar.addWidget(self.paid)
        bar.addWidget(close)
        root.addLayout(bar)

    def rafraichir(self):
        try:
            self.rows = self.api.list_commission_invoices()
        except CloudAPIError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.status.setText(f"⛔ {exc}")
            return

        self.table.setRowCount(len(self.rows))
        for r, invoice in enumerate(self.rows):
            month = int(invoice.get("period_month") or 1)
            year = int(invoice.get("period_year") or 0)
            period = f"{MONTHS[month-1]} {year}" if 1 <= month <= 12 else str(year)
            values = [
                invoice.get("invoice_number") or "",
                period,
                self._date_fr(invoice.get("issued_at")),
                self._date_fr(invoice.get("scheduled_payment_on")),
                str(len(invoice.get("lines") or [])),
                self._euro(invoice.get("total_cents") or 0),
                invoice.get("display_status") or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c in (4, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                if c == 5 and int(invoice.get("tax_calculation_version") or 1) >= 2:
                    item.setToolTip(
                        "HT : " + self._euro(invoice.get("total_ht_cents") or 0)
                        + "\nTVA : " + self._euro(invoice.get("vat_cents") or 0)
                        + "\nTTC : " + self._euro(invoice.get("total_cents") or 0)
                    )
                self.table.setItem(r, c, item)
        self.status.setText(f"{len(self.rows)} facture(s) enregistrée(s).")

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(self, "Sélection", "Sélectionnez une facture.")
            return None
        return self.rows[row]

    def _download(self):
        invoice = self._selected()
        if not invoice:
            return
        default = f"{invoice.get('invoice_number') or 'facture-commissions'}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la facture", str(Path.home() / "Downloads" / default),
            "Document PDF (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            save_invoice_pdf(invoice, path)
        except Exception as exc:
            QMessageBox.critical(self, "PDF impossible", str(exc))
            return
        QMessageBox.information(
            self, "Facture enregistrée", f"La facture a été enregistrée :\n{path}"
        )

    def _mark_paid(self):
        invoice = self._selected()
        if not invoice or invoice.get("status") == "paid":
            return
        reference, ok = QInputDialog.getText(
            self, "Virement effectué", "Référence du virement (facultatif) :"
        )
        if not ok:
            return
        if QMessageBox.question(
            self, "Confirmer le paiement",
            f"Confirmez-vous le paiement de {self._euro(invoice.get('total_cents') or 0)} "
            f"pour la facture {invoice.get('invoice_number')} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            self.api.mark_commission_invoice_paid(
                str(invoice.get("id") or ""), reference=reference
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Paiement impossible", str(exc))
            return
        self.rafraichir()
