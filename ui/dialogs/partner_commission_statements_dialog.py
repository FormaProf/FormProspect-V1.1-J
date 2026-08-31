from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.premium_theme import BORDER, MUTED, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.partner_commission_statement_pdf import save_partner_statement_pdf

MONTHS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
          "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


class PartnerInvoiceUploadDialog(QDialog):
    def __init__(self, api, statement: dict, parent=None):
        super().__init__(parent)
        self.api = api
        self.statement = statement
        self.file_path = Path()
        self.setWindowTitle("Déposer la facture du partenaire")
        self.setModal(True)
        self.setMinimumWidth(580)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        title = QLabel("Déposer la facture officielle")
        title.setStyleSheet(f"font-size:21px;font-weight:900;color:{TEXT};")
        root.addWidget(title)

        info = QLabel(
            "Le relevé Form@Prospect sert de base de contrôle. "
            "La facture officielle reste émise par votre société."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED};")
        root.addWidget(info)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:#FFFFFF;border:1px solid {BORDER};border-radius:14px;}}"
        )
        form = QFormLayout(card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self.number = QLineEdit()
        self.number.setPlaceholderText("Ex. J2D-2026-008")

        self.issued_at = QDateEdit()
        self.issued_at.setCalendarPopup(True)
        self.issued_at.setDisplayFormat("dd/MM/yyyy")
        self.issued_at.setDate(QDate.currentDate())

        file_row = QHBoxLayout()
        self.file_label = QLabel("Aucun PDF sélectionné")
        self.file_label.setWordWrap(True)
        choose = QPushButton("Choisir un PDF")
        choose.setStyleSheet(SECONDARY_BUTTON)
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(choose)

        form.addRow("N° de facture", self.number)
        form.addRow("Date de facture", self.issued_at)
        form.addRow("Fichier PDF", file_row)
        root.addWidget(card)

        security = QLabel(
            "Le PDF est contrôlé côté serveur. Une facture déjà déposée ne peut "
            "pas être remplacée silencieusement."
        )
        security.setWordWrap(True)
        security.setStyleSheet(f"color:{MUTED};font-size:10px;")
        root.addWidget(security)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        send = QPushButton("Déposer la facture")
        send.setStyleSheet(PRIMARY_BUTTON)
        send.clicked.connect(self._upload)
        actions.addWidget(cancel)
        actions.addWidget(send)
        root.addLayout(actions)

    def _choose_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choisir la facture du partenaire", "", "Documents PDF (*.pdf)"
        )
        if filename:
            self.file_path = Path(filename)
            self.file_label.setText(self.file_path.name)

    def _upload(self):
        number = self.number.text().strip()
        if not number:
            QMessageBox.warning(self, "Numéro manquant", "Saisissez le numéro de facture.")
            return
        if not self.file_path.is_file():
            QMessageBox.warning(self, "Facture manquante", "Sélectionnez le PDF de la facture.")
            return
        if self.file_path.suffix.lower() != ".pdf":
            QMessageBox.warning(self, "Format interdit", "Seuls les fichiers PDF sont autorisés.")
            return

        qdate = self.issued_at.date()
        issued_at = date(qdate.year(), qdate.month(), qdate.day()).isoformat()
        statement_number = (
            self.statement.get("statement_number")
            or self.statement.get("invoice_number")
            or "ce relevé"
        )
        if QMessageBox.question(
            self,
            "Confirmer le dépôt",
            f"Déposer la facture {number} pour le relevé {statement_number} ?\n\n"
            "Après dépôt, la facture ne pourra pas être remplacée silencieusement.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        try:
            self.api.upload_partner_commission_invoice(
                str(self.statement.get("id") or ""),
                invoice_number=number,
                invoice_issued_at=issued_at,
                file_path=self.file_path,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Dépôt impossible", str(exc))
            return

        QMessageBox.information(
            self, "Facture reçue",
            "La facture du partenaire a été enregistrée dans le stockage Cloud sécurisé."
        )
        self.accept()


class PartnerCommissionStatementsDialog(QDialog):
    def __init__(self, api, parent=None, *, selected_year=None, selected_month=None):
        super().__init__(parent)
        self.api = api
        self.rows: list[dict] = []
        self.is_admin = SessionState.has_role("Administrateur")
        self.is_foreign_director = SessionState.has_role("Dirigeant hors France")
        self.admin_partners: list[dict] = []

        today = date.today()
        self.initial_year = int(selected_year or today.year)
        self.initial_month = int(selected_month or today.month)

        self.setWindowTitle("Relevés & factures partenaires")
        self.resize(1220, 700)
        self._build_ui()
        if self.is_admin:
            self._load_admin_partners()
        self.rafraichir()

    @staticmethod
    def _euro(cents) -> str:
        return f"{int(cents or 0)/100:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _date_fr(value) -> str:
        text = str(value or "")
        if len(text) >= 10 and text[4] == "-":
            return f"{text[8:10]}/{text[5:7]}/{text[:4]}"
        return text or "—"

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 22)
        root.setSpacing(12)

        title = QLabel(
            "Mes relevés de commissions"
            if self.is_foreign_director
            else "Relevés de commissions partenaires"
        )
        title.setStyleSheet(f"font-size:25px;font-weight:900;color:{TEXT};")
        root.addWidget(title)

        subtitle = QLabel(
            "Form@Prospect fige les commissions dans un relevé. Le partenaire "
            "dépose ensuite sa propre facture officielle avant paiement."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(subtitle)

        filters = QHBoxLayout()
        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTHS)
        self.month_combo.setCurrentIndex(max(0, min(11, self.initial_month - 1)))

        self.year_combo = QComboBox()
        current_year = date.today().year
        years = list(range(current_year - 3, current_year + 6))
        if self.initial_year not in years:
            years.append(self.initial_year)
            years.sort()
        self.year_combo.addItems([str(y) for y in years])
        self.year_combo.setCurrentText(str(self.initial_year))

        filters.addWidget(QLabel("Période :"))
        filters.addWidget(self.month_combo)
        filters.addWidget(self.year_combo)

        self.partner_label = QLabel("Partenaire :")
        self.partner_combo = QComboBox()
        self.partner_combo.setMinimumWidth(250)
        self.partner_label.setVisible(self.is_admin)
        self.partner_combo.setVisible(self.is_admin)
        filters.addWidget(self.partner_label)
        filters.addWidget(self.partner_combo)
        filters.addStretch()

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)
        filters.addWidget(refresh)

        self.create_button = QPushButton("Créer le relevé")
        self.create_button.setStyleSheet(PRIMARY_BUTTON)
        self.create_button.setVisible(self.is_admin)
        self.create_button.clicked.connect(self._create_statement)
        filters.addWidget(self.create_button)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Relevé", "Période", "Partenaire", "Émission",
            "Commissions", "Montant", "Facture partenaire", "Statut",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet(
            f"QTableWidget{{background:white;color:{TEXT};border:1px solid {BORDER};"
            f"gridline-color:{BORDER};}}"
        )
        self.table.itemSelectionChanged.connect(self._update_actions)
        root.addWidget(self.table, 1)

        bar = QHBoxLayout()
        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED};")
        bar.addWidget(self.status, 1)

        self.statement_pdf = QPushButton("Télécharger le relevé")
        self.statement_pdf.setStyleSheet(SECONDARY_BUTTON)
        self.statement_pdf.clicked.connect(self._download_statement)

        self.upload_invoice = QPushButton("Déposer ma facture")
        self.upload_invoice.setStyleSheet(PRIMARY_BUTTON)
        self.upload_invoice.setVisible(self.is_foreign_director)
        self.upload_invoice.clicked.connect(self._upload_invoice)

        self.view_invoice = QPushButton("Télécharger la facture")
        self.view_invoice.setStyleSheet(SECONDARY_BUTTON)
        self.view_invoice.clicked.connect(self._download_partner_invoice)

        self.mark_paid = QPushButton("Marquer payé")
        self.mark_paid.setStyleSheet(PRIMARY_BUTTON)
        self.mark_paid.setVisible(self.is_admin)
        self.mark_paid.clicked.connect(self._mark_paid)

        close = QPushButton("Fermer")
        close.setStyleSheet(SECONDARY_BUTTON)
        close.clicked.connect(self.accept)

        for widget in (self.statement_pdf, self.upload_invoice, self.view_invoice, self.mark_paid, close):
            bar.addWidget(widget)
        root.addLayout(bar)
        self._update_actions()

    def _selected(self, warn=True):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            if warn:
                QMessageBox.information(self, "Sélection", "Sélectionnez un relevé.")
            return None
        return self.rows[row]

    # 0033B: Administration creates partner statements
    def _load_admin_partners(self):
        if not self.is_admin:
            return

        try:
            partners = self.api.list_admin_commercial_partners()
        except CloudAPIError as exc:
            self.admin_partners = []
            self.partner_combo.clear()
            self.partner_combo.addItem("Partenaires indisponibles", None)
            self.create_button.setEnabled(False)
            self.status.setText(f"⛔ {exc}")
            return

        self.admin_partners = sorted(
            [row for row in partners if bool(row.get("active"))],
            key=lambda row: str(row.get("legal_name") or "").casefold(),
        )
        self.partner_combo.clear()

        for partner in self.admin_partners:
            partner_id = str(partner.get("id") or "").strip()
            legal_name = str(partner.get("legal_name") or "").strip() or "Partenaire"
            if partner_id:
                self.partner_combo.addItem(legal_name, partner_id)

        if self.partner_combo.count() == 0:
            self.partner_combo.addItem("Aucun partenaire actif", None)
            self.create_button.setEnabled(False)
        else:
            self.create_button.setEnabled(True)

    def rafraichir(self):
        year = int(self.year_combo.currentText())
        try:
            self.rows = self.api.list_partner_commission_invoices(year=year)
        except CloudAPIError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.status.setText(f"⛔ {exc}")
            self._update_actions()
            return

        self.table.setRowCount(len(self.rows))
        for r, statement in enumerate(self.rows):
            month = int(statement.get("period_month") or 0)
            year_value = int(statement.get("period_year") or 0)
            period = f"{MONTHS[month-1]} {year_value}" if 1 <= month <= 12 else str(year_value)
            partner_invoice = (
                statement.get("partner_invoice_number")
                if statement.get("has_partner_invoice")
                else "En attente"
            )
            values = [
                statement.get("statement_number") or statement.get("invoice_number") or "",
                period,
                statement.get("seller_name") or "",
                self._date_fr(statement.get("issued_at")),
                str(len(statement.get("lines") or [])),
                self._euro(statement.get("total_cents")),
                partner_invoice or "",
                statement.get("display_status") or statement.get("status") or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c != 2:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
            self.table.setRowHeight(r, 44)

        self.status.setText(f"{len(self.rows)} relevé(s) partenaire(s).")
        self._update_actions()

    def _update_actions(self):
        statement = self._selected(warn=False)
        self.statement_pdf.setEnabled(statement is not None)
        self.view_invoice.setEnabled(bool(statement and statement.get("has_partner_invoice")))
        self.upload_invoice.setEnabled(bool(statement and statement.get("can_upload_invoice")))
        self.mark_paid.setEnabled(bool(statement and statement.get("can_mark_paid")))

    def _create_statement(self):
        if not self.is_admin:
            return

        partner_id = self.partner_combo.currentData()
        partner_name = self.partner_combo.currentText().strip()
        if not partner_id:
            QMessageBox.warning(
                self,
                "Partenaire requis",
                "Sélectionnez un partenaire commercial actif avant de créer le relevé.",
            )
            return

        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        period = f"{MONTHS[month-1]} {year}"

        if QMessageBox.question(
            self,
            "Créer le relevé",
            f"Créer le relevé de commissions de {partner_name} pour {period} ?\n\n"
            "Seules les commissions réellement dues à ce partenaire et non déjà incluses "
            "dans un autre relevé seront ajoutées.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        try:
            statement = self.api.create_partner_commission_statement(
                commercial_partner_id=str(partner_id),
                year=year,
                month=month,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Relevé impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Relevé créé",
            f"Le relevé {statement.get('statement_number') or statement.get('invoice_number')} "
            f"a été créé pour {self._euro(statement.get('total_cents'))}.\n\n"
            "Le dirigeant du partenaire pourra maintenant consulter ce relevé et "
            "déposer la facture officielle de son entreprise.",
        )
        self.rafraichir()

    def _download_statement(self):
        statement = self._selected()
        if not statement:
            return
        default = f"{statement.get('statement_number') or statement.get('invoice_number') or 'releve-commissions'}.pdf"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le relevé de commissions",
            str(Path.home() / "Downloads" / default), "Document PDF (*.pdf)"
        )
        if not destination:
            return
        try:
            saved = save_partner_statement_pdf(statement, destination)
        except Exception as exc:
            QMessageBox.critical(self, "PDF impossible", str(exc))
            return
        if QMessageBox.question(
            self, "Relevé enregistré",
            f"Le relevé a été enregistré ici :\n{saved}\n\nL'ouvrir maintenant ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        ) == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(saved)))

    def _upload_invoice(self):
        statement = self._selected()
        if not statement or not statement.get("can_upload_invoice"):
            return
        if PartnerInvoiceUploadDialog(self.api, statement, self).exec():
            self.rafraichir()

    def _download_partner_invoice(self):
        statement = self._selected()
        if not statement or not statement.get("has_partner_invoice"):
            return
        default = str(
            statement.get("partner_invoice_original_filename")
            or statement.get("partner_invoice_number")
            or "facture-partenaire.pdf"
        )
        if not default.lower().endswith(".pdf"):
            default += ".pdf"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Télécharger la facture du partenaire",
            str(Path.home() / "Downloads" / default), "Document PDF (*.pdf)"
        )
        if not destination:
            return
        try:
            saved = self.api.download_partner_commission_invoice(
                str(statement.get("id") or ""), destination
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Téléchargement impossible", str(exc))
            return
        if QMessageBox.question(
            self, "Facture téléchargée",
            f"La facture a été enregistrée ici :\n{saved}\n\nL'ouvrir maintenant ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        ) == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(saved)))

    def _mark_paid(self):
        statement = self._selected()
        if not statement or not statement.get("can_mark_paid"):
            return
        number = statement.get("partner_invoice_number") or "facture partenaire"
        total = self._euro(statement.get("total_cents"))
        if QMessageBox.question(
            self, "Confirmer le paiement",
            f"Confirmez-vous le paiement de {total} pour {number} ?\n\n"
            "Toutes les commissions de ce relevé seront marquées comme payées.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        reference, accepted = QInputDialog.getText(
            self, "Référence de paiement", "Référence du virement (facultatif) :"
        )
        if not accepted:
            return
        try:
            self.api.mark_partner_commission_invoice_paid(
                str(statement.get("id") or ""), reference=reference
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Paiement impossible", str(exc))
            return
        QMessageBox.information(
            self, "Paiement enregistré",
            "Le relevé partenaire et ses commissions ont été marqués comme payés."
        )
        self.rafraichir()
