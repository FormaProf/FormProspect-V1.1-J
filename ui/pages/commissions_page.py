from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.session import SessionState
from services.commission_service import CommissionService
from ui.components.metric_card import MetricCard
from ui.dialogs.new_sale_dialog import NewSaleDialog


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class CommissionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.service: CommissionService | None = None
        self.sales_rows: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(35, 28, 35, 28)
        root.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Ventes & commissions")
        title.setStyleSheet("font-size:30px; font-weight:900; color:#111827;")
        self.subtitle = QLabel("Suivi automatique des contrats signés")
        self.subtitle.setStyleSheet("color:#6B7280; font-size:14px;")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTHS)
        self.year_combo = QComboBox()
        current = date.today()
        self.year_combo.addItems([str(year) for year in range(current.year - 3, current.year + 2)])
        self.year_combo.setCurrentText(str(current.year))
        self.month_combo.setCurrentIndex(current.month - 1)
        self.month_combo.currentIndexChanged.connect(self.rafraichir)
        self.year_combo.currentIndexChanged.connect(self.rafraichir)
        header.addWidget(self.month_combo)
        header.addWidget(self.year_combo)

        self.add_button = QPushButton("＋ Enregistrer une vente")
        self.add_button.setFixedHeight(42)
        self.add_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 18px;font-weight:800;} QPushButton:hover{background:#256DB4;}"
        )
        self.add_button.clicked.connect(self._new_sale)
        header.addWidget(self.add_button)
        root.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.revenue_card = MetricCard("CA signé", "0,00 €", "💰")
        self.commission_card = MetricCard("Mes commissions", "0,00 €", "💵")
        self.contracts_card = MetricCard("Contrats signés", "0", "📄")
        cards.addWidget(self.revenue_card)
        cards.addWidget(self.commission_card)
        cards.addWidget(self.contracts_card)
        root.addLayout(cards)

        table_frame = QFrame()
        table_frame.setStyleSheet("QFrame{background:white;border:1px solid #E5E7EB;border-radius:14px;}")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(14, 14, 14, 14)
        table_title = QLabel("Détail des ventes")
        table_title.setStyleSheet("font-size:17px;font-weight:800;color:#111827;border:none;")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Client", "Offre", "Commercial", "Montant",
            "Taux", "Commission", "Statut",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table_layout.addWidget(self.table)
        root.addWidget(table_frame, 1)

        self.cancel_button = QPushButton("Annuler la vente sélectionnée")
        self.cancel_button.clicked.connect(self._cancel_selected)
        self.cancel_button.setVisible(SessionState.has_role("Administrateur", "Manager"))
        root.addWidget(self.cancel_button, 0, Qt.AlignRight)

    def _scope_user_id(self) -> int | None:
        user = SessionState.user()
        if user is None:
            return -1
        return user.id if user.role == "Commercial" else None

    def _format_euro(self, cents: int) -> str:
        return f"{cents / 100:,.2f} €".replace(",", " ")

    def rafraichir(self) -> None:
        if not ApplicationState.has_project():
            self.subtitle.setText("Ouvrez un projet pour consulter les ventes.")
            self.table.setRowCount(0)
            self.revenue_card.set_value("0,00 €")
            self.commission_card.set_value("0,00 €")
            self.contracts_card.set_value("0")
            return
        self.service = CommissionService(ApplicationState.get_project().database)
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        user_id = self._scope_user_id()
        summary = self.service.monthly_summary(year=year, month=month, commercial_user_id=user_id)
        self.sales_rows = self.service.list_sales(year=year, month=month, commercial_user_id=user_id)

        user = SessionState.user()
        if user and user.role == "Commercial":
            self.subtitle.setText(f"Résultats de {user.display_name} — {MONTHS[month-1]} {year}")
        else:
            self.subtitle.setText(f"Vue équipe — {MONTHS[month-1]} {year}")
        self.revenue_card.set_value(self._format_euro(summary["revenue_cents"]))
        self.commission_card.set_value(self._format_euro(summary["commission_cents"]))
        self.contracts_card.set_value(str(summary["contracts"]))

        self.table.setRowCount(len(self.sales_rows))
        for row_index, sale in enumerate(self.sales_rows):
            values = [
                sale["signed_at"], sale["prospect_name"], sale["offer_name"],
                sale["commercial_name"], self._format_euro(sale["price_cents"]),
                f"{sale['commission_rate']:g} %", self._format_euro(sale["commission_cents"]),
                sale["status"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (4, 5, 6):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, column, item)

    def _new_sale(self) -> None:
        if not ApplicationState.has_project():
            QMessageBox.warning(self, "Projet", "Ouvrez d'abord un projet.")
            return
        self.service = CommissionService(ApplicationState.get_project().database)
        if not self.service.list_prospects():
            QMessageBox.warning(self, "Prospects", "Ajoutez ou importez au moins un prospect avant d'enregistrer une vente.")
            return
        dialog = NewSaleDialog(self.service, self)
        if dialog.exec():
            self.rafraichir()

    def _cancel_selected(self) -> None:
        if not self.service or not SessionState.has_role("Administrateur", "Manager"):
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Sélection", "Sélectionnez une vente.")
            return
        sale = self.sales_rows[row]
        if sale["status"] == "Annulée":
            return
        answer = QMessageBox.question(
            self, "Annuler la vente",
            "Cette vente ne sera plus comptée dans le chiffre d'affaires ni les commissions. Continuer ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.service.cancel_sale(int(sale["id"]))
            self.rafraichir()
