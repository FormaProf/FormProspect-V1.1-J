from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    PAGE_BG,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.components.metric_card import MetricCard
from ui.dialogs.new_sale_dialog import NewSaleDialog
from ui.dialogs.commission_invoices_dialog import CommissionInvoicesDialog
from ui.dialogs.partner_commission_statements_dialog import PartnerCommissionStatementsDialog
from services.commission_invoice_pdf import save_invoice_pdf


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class PremiumFinanceCard(QFrame):
    """Carte KPI compacte et premium dédiée aux ventes & commissions."""

    def __init__(self, label: str, value: str, accent: str, helper: str = ""):
        super().__init__()
        self.setObjectName("PremiumFinanceCard")
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            QFrame#PremiumFinanceCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 13)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background:{accent}; border:none; border-radius:5px;"
        )

        self.label = QLabel(label)
        self.label.setStyleSheet(
            "font-size:11px; font-weight:800; color:#5E7087; "
            "background:transparent; border:none;"
        )

        top.addWidget(dot)
        top.addWidget(self.label)
        top.addStretch()

        self.value = QLabel(value)
        self.value.setStyleSheet(
            "font-size:22px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        self.helper = QLabel(helper)
        self.helper.setStyleSheet(
            "font-size:9px; color:#8A99AB; background:transparent; border:none;"
        )

        layout.addLayout(top)
        layout.addWidget(self.value)
        if helper:
            layout.addWidget(self.helper)

    def set_value(self, value: str):
        self.value.setText(str(value))


class CommissionsPage(QWidget):
    """Pilotage Cloud des ventes, encaissements et commissions."""

    def __init__(self):
        super().__init__()
        self.sales_rows: list[dict] = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 28)
        root.setSpacing(16)

        # -------------------------
        # Header premium
        # -------------------------
        header_card = QFrame()
        header_card.setObjectName("SalesHeader")
        header_card.setStyleSheet("""
            QFrame#SalesHeader {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:0.72 #F7FBFF,
                    stop:1 #EAF4FF
                );
                border:1px solid #E4EBF4;
                border-radius:20px;
            }
        """)

        header = QHBoxLayout(header_card)
        header.setContentsMargins(22, 18, 20, 18)
        header.setSpacing(14)

        titles = QVBoxLayout()
        titles.setSpacing(3)

        eyebrow = QLabel("VENTES  •  PERFORMANCE COMMERCIALE")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        title = QLabel("Ventes & commissions")
        title.setStyleSheet(
            "font-size:28px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        self.subtitle = QLabel(
            "Suivi sécurisé des contrats, encaissements et commissions dans le Cloud."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(
            "font-size:12px; color:#6B7A90; background:transparent; border:none;"
        )

        titles.addWidget(eyebrow)
        titles.addWidget(title)
        titles.addWidget(self.subtitle)

        header.addLayout(titles, 1)

        current = date.today()

        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTHS)
        self.month_combo.setCurrentIndex(current.month - 1)
        self.month_combo.setFixedHeight(40)
        self.month_combo.setMinimumWidth(108)

        self.year_combo = QComboBox()
        # Plage d'années dynamique :
        # conserve quelques années passées et permet de planifier loin dans le futur.
        self.year_combo.addItems(
            [str(year) for year in range(current.year - 3, current.year + 21)]
        )
        self.year_combo.setCurrentText(str(current.year))
        self.year_combo.setFixedHeight(40)
        self.year_combo.setMinimumWidth(78)

        combo_style = """
            QComboBox {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 10px;
                font-size:11px;
                font-weight:800;
            }
            QComboBox:focus {
                border:2px solid #338CE4;
            }
            QComboBox::drop-down {
                border:none;
                width:24px;
            }
        """
        self.month_combo.setStyleSheet(combo_style)
        self.year_combo.setStyleSheet(combo_style)

        refresh_button = QPushButton("Actualiser")
        refresh_button.setFixedHeight(40)
        refresh_button.setStyleSheet(self._secondary_button_style())
        refresh_button.clicked.connect(self.rafraichir)

        self.history_button = QPushButton("Historique factures")
        self.history_button.setFixedHeight(40)
        self.history_button.setStyleSheet(self._secondary_button_style())
        self.history_button.clicked.connect(self._open_invoice_history)
        # Historique personnel : commerciaux indépendants + administration.
        # Un Dirigeant hors France utilise le workflow partenaire séparé.
        self.history_button.setVisible(
            SessionState.has_role("Commercial", "Administrateur")
        )

        self.partner_history_button = QPushButton("Relevés partenaire")
        self.partner_history_button.setFixedHeight(40)
        self.partner_history_button.setStyleSheet(self._secondary_button_style())
        self.partner_history_button.setVisible(
            SessionState.has_role("Administrateur", "Dirigeant hors France")
        )
        self.partner_history_button.clicked.connect(self._open_partner_statement_history)

        self.invoice_button = QPushButton("Générer ma facture")
        self.invoice_button.setFixedHeight(40)
        self.invoice_button.setStyleSheet(self._primary_button_style())
        self.invoice_button.setVisible(SessionState.has_role("Commercial"))
        self.invoice_button.clicked.connect(self._generate_invoice)

        self.add_button = QPushButton("Enregistrer une vente")
        self.add_button.setFixedHeight(40)
        self.add_button.setStyleSheet(self._primary_button_style())
        self.add_button.clicked.connect(self._new_sale)

        header.addWidget(self.month_combo)
        header.addWidget(self.year_combo)
        header.addWidget(refresh_button)
        header.addWidget(self.history_button)
        header.addWidget(self.partner_history_button)
        header.addWidget(self.invoice_button)
        header.addWidget(self.add_button)

        root.addWidget(header_card)

        # -------------------------
        # KPI premium 3 x 2
        # -------------------------
        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)

        self.contracts_card = PremiumFinanceCard(
            "Contrats signés", "0", "#338CE4", "Ventes enregistrées"
        )
        self.signed_revenue_card = PremiumFinanceCard(
            "CA signé", "0,00 €", "#0B2A52", "Valeur contractuelle"
        )
        self.collected_revenue_card = PremiumFinanceCard(
            "CA encaissé", "0,00 €", "#16A34A", "Règlements clients reçus"
        )
        self.pending_card = PremiumFinanceCard(
            "Commissions en attente", "0,00 €", "#F59E0B", "En cours de validation"
        )
        self.due_card = PremiumFinanceCard(
            "Commissions à verser", "0,00 €", "#7C3AED", "Validées et dues"
        )
        self.paid_card = PremiumFinanceCard(
            "Commissions versées", "0,00 €", "#16A34A", "Paiements finalisés"
        )

        metric_cards = [
            self.contracts_card,
            self.signed_revenue_card,
            self.collected_revenue_card,
            self.pending_card,
            self.due_card,
            self.paid_card,
        ]
        for index, card in enumerate(metric_cards):
            cards.setColumnStretch(index % 3, 1)
            cards.addWidget(card, index // 3, index % 3)

        root.addLayout(cards)

        # -------------------------
        # Détail des ventes
        # -------------------------
        table_frame = QFrame()
        table_frame.setObjectName("SalesTableCard")
        table_frame.setStyleSheet("""
            QFrame#SalesTableCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)

        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 15, 16, 14)
        table_layout.setSpacing(12)

        table_header = QHBoxLayout()
        table_titles = QVBoxLayout()
        table_titles.setSpacing(2)

        table_eyebrow = QLabel("ACTIVITÉ COMMERCIALE")
        table_eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        table_title = QLabel("Détail des ventes")
        table_title.setStyleSheet(
            "font-size:18px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        table_titles.addWidget(table_eyebrow)
        table_titles.addWidget(table_title)

        self.period_summary = QLabel("")
        self.period_summary.setAlignment(Qt.AlignCenter)
        self.period_summary.setMinimumWidth(112)
        self.period_summary.setFixedHeight(28)
        self.period_summary.setStyleSheet(
            "font-size:10px; font-weight:900; color:#075985; "
            "background:#EFF8FF; border:1px solid #BAE6FD; "
            "border-radius:10px; padding:0 10px;"
        )

        table_header.addLayout(table_titles)
        table_header.addStretch()
        table_header.addWidget(self.period_summary, 0, Qt.AlignTop)
        table_layout.addLayout(table_header)

        self.show_commercial_column = (
            SessionState.has_role("Administrateur")
            or SessionState.has_role("Manager")
        )

        if self.show_commercial_column:
            self.table_headers = [
                "Date", "Client", "Formation", "Commercial",
                "Montant", "Taux", "Commission", "Statut",
            ]
        else:
            self.table_headers = [
                "Date", "Client", "Formation",
                "Montant", "Taux", "Commission", "Statut",
            ]

        self.table = QTableWidget(0, len(self.table_headers))
        self.table.setHorizontalHeaderLabels(self.table_headers)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        if self.show_commercial_column:
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setMinimumHeight(330)

        self.table.setStyleSheet("""
            QTableWidget {
                background:#FFFFFF;
                color:#1F2937;
                border:1px solid #E4EBF4;
                border-radius:14px;
                gridline-color:transparent;
                font-size:11px;
                outline:0;
            }
            QTableWidget::item {
                padding:9px 8px;
                border:none;
                border-bottom:1px solid #EEF2F6;
            }
            QTableWidget::item:selected {
                background:#EAF4FF;
                color:#0B1220;
            }
            QHeaderView {
                background:#0B2A52;
                border:none;
            }
            QHeaderView::section {
                background:#0B2A52;
                color:#FFFFFF;
                border:none;
                border-right:1px solid rgba(255,255,255,0.08);
                padding:10px 8px;
                font-size:10px;
                font-weight:900;
            }
            QScrollBar:vertical {
                background:transparent;
                width:9px;
                margin:3px 1px 3px 1px;
            }
            QScrollBar::handle:vertical {
                background:#CBD5E1;
                min-height:32px;
                border-radius:4px;
            }
            QScrollBar:horizontal {
                background:transparent;
                height:9px;
            }
            QScrollBar::handle:horizontal {
                background:#CBD5E1;
                min-width:40px;
                border-radius:4px;
            }
        """)

        self.table.itemSelectionChanged.connect(self._update_action_buttons)

        # Index dynamiques selon le rôle connecté.
        self.rate_col = self.table_headers.index("Taux")
        self.status_col = self.table_headers.index("Statut")
        self.amount_col = self.table_headers.index("Montant")
        self.commission_col = self.table_headers.index("Commission")

        self.table.horizontalHeader().setSectionResizeMode(
            self.rate_col, QHeaderView.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.status_col, QHeaderView.Fixed
        )
        self.table.setColumnWidth(self.rate_col, 100)
        self.table.setColumnWidth(self.status_col, 285)

        table_layout.addWidget(self.table)
        root.addWidget(table_frame, 1)

        # -------------------------
        # Barre d'information / actions admin
        # -------------------------
        footer_card = QFrame()
        footer_card.setObjectName("SalesFooter")
        footer_card.setStyleSheet("""
            QFrame#SalesFooter {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:14px;
            }
        """)

        action_bar = QHBoxLayout(footer_card)
        action_bar.setContentsMargins(14, 10, 14, 10)
        action_bar.setSpacing(8)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "font-size:10px; color:#6B7A90; background:transparent; border:none;"
        )
        action_bar.addWidget(self.status_label, 1)

        self.client_paid_button = QPushButton("Valider l'encaissement")
        self.client_paid_button.setFixedHeight(38)
        self.client_paid_button.setStyleSheet(self._secondary_button_style())
        self.client_paid_button.clicked.connect(self._mark_client_paid)

        self.commission_paid_button = QPushButton("Commission versée")
        self.commission_paid_button.setFixedHeight(38)
        self.commission_paid_button.setStyleSheet(self._secondary_button_style())
        self.commission_paid_button.clicked.connect(self._mark_commission_paid)

        self.cancel_button = QPushButton("Annuler la vente")
        self.cancel_button.setFixedHeight(38)
        self.cancel_button.setStyleSheet(self._danger_button_style())
        self.cancel_button.clicked.connect(self._cancel_selected)

        is_admin = self._is_admin()
        self.client_paid_button.setVisible(is_admin)
        self.commission_paid_button.setVisible(is_admin)
        self.cancel_button.setVisible(is_admin)

        action_bar.addWidget(self.client_paid_button)
        action_bar.addWidget(self.commission_paid_button)
        action_bar.addWidget(self.cancel_button)

        root.addWidget(footer_card)

        self.month_combo.currentIndexChanged.connect(self.rafraichir)
        self.year_combo.currentIndexChanged.connect(self.rafraichir)
        self._update_action_buttons()

    @staticmethod
    def _primary_button_style():
        return """
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 15px;
                font-size:11px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:pressed { background:#1D66B2; }
            QPushButton:disabled {
                background:#DCE6F0;
                color:#94A3B8;
            }
        """

    @staticmethod
    def _secondary_button_style():
        return """
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 14px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
            QPushButton:disabled {
                background:#F8FAFC;
                color:#B4BECA;
                border-color:#E8EDF3;
            }
        """

    @staticmethod
    def _danger_button_style():
        return """
            QPushButton {
                background:#FFFFFF;
                color:#B42318;
                border:1px solid #F2C8C4;
                border-radius:10px;
                padding:0 14px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#FFF5F4;
                border-color:#E8A7A1;
            }
            QPushButton:disabled {
                background:#F8FAFC;
                color:#C5CBD3;
                border-color:#E8EDF3;
            }
        """

    @staticmethod
    def _status_badge_style(status_text: str) -> str:
        text = str(status_text or "").lower()

        if "versée" in text or "payée" in text:
            bg, fg, border = "#ECFDF3", "#166534", "#BBF7D0"
        elif "annul" in text:
            bg, fg, border = "#FEF2F2", "#991B1B", "#FECACA"
        elif "factur" in text:
            bg, fg, border = "#FFF7ED", "#9A3412", "#FED7AA"
        elif "validation automatique" in text or "à verser" in text:
            bg, fg, border = "#EFF8FF", "#075985", "#BAE6FD"
        else:
            bg, fg, border = "#F8FAFC", "#475569", "#E2E8F0"

        return (
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            "border-radius:10px; padding:4px 12px; font-size:11px; font-weight:900;"
        )

    @staticmethod
    def _rate_badge_style() -> str:
        return (
            "background:#F5F3FF; color:#5B21B6; border:1px solid #C4B5FD; "
            "border-radius:10px; padding:4px 12px; font-size:12px; font-weight:900;"
        )

    @staticmethod
    def _is_admin() -> bool:
        return SessionState.has_role("Administrateur")

    @staticmethod
    def _may_create() -> bool:
        return SessionState.has_role("Administrateur", "Manager", "Commercial")

    @staticmethod
    def _format_euro(cents: int) -> str:
        return f"{int(cents) / 100:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _format_rate(value) -> str:
        try:
            return f"{float(value or 0):g} %"
        except (TypeError, ValueError):
            return "0 %"

    def _reset(self) -> None:
        self.sales_rows = []
        self.table.setRowCount(0)
        self.contracts_card.set_value("0")
        self.signed_revenue_card.set_value("0,00 €")
        self.collected_revenue_card.set_value("0,00 €")
        self.pending_card.set_value("0,00 €")
        self.due_card.set_value("0,00 €")
        self.paid_card.set_value("0,00 €")
        self.period_summary.setText("")
        self._update_action_buttons()

    def rafraichir(self, *_args) -> None:
        self.add_button.setEnabled(self._may_create() and CloudRuntime.is_active())
        if not CloudRuntime.is_active():
            self._reset()
            self.subtitle.setText(
                "Connectez-vous à Form@Prospect Cloud pour consulter les ventes."
            )
            self.status_label.setText("Aucune session Cloud active.")
            return

        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        self.status_label.setStyleSheet(f"color:{MUTED};")
        self.status_label.setText("Chargement des ventes Cloud…")

        try:
            api = CloudRuntime.api()
            summary = api.get_cloud_sales_summary(year=year, month=month)
            self.sales_rows = api.list_cloud_sales(year=year, month=month)
        except (CloudAPIError, RuntimeError) as exc:
            self._reset()
            self.subtitle.setText("Ventes & commissions Cloud")
            self.status_label.setStyleSheet("color:#B42318;")
            self.status_label.setText(f"⛔ {exc}")
            return

        user = SessionState.user()
        if user and user.role == "Commercial":
            self.subtitle.setText(
                f"Résultats de {user.display_name} — {MONTHS[month - 1]} {year}"
            )
        elif user and user.role == "Manager":
            self.subtitle.setText(
                f"Vue de votre équipe — {MONTHS[month - 1]} {year}"
            )
        else:
            self.subtitle.setText(
                f"Vue globale Form@Prof — {MONTHS[month - 1]} {year}"
            )

        self.contracts_card.set_value(str(summary["contracts_signed"]))
        self.signed_revenue_card.set_value(
            self._format_euro(summary["signed_revenue_cents"])
        )
        self.collected_revenue_card.set_value(
            self._format_euro(summary["collected_revenue_cents"])
        )
        self.pending_card.set_value(
            self._format_euro(summary["commission_pending_cents"])
        )
        self.due_card.set_value(
            self._format_euro(summary["commission_due_cents"])
        )
        self.paid_card.set_value(
            self._format_euro(summary["commission_paid_cents"])
        )

        self.table.setRowCount(len(self.sales_rows))
        for row_index, sale in enumerate(self.sales_rows):
            signed_at = str(sale.get("signed_at") or "")
            if len(signed_at) >= 10 and "-" in signed_at[:10]:
                year_part, month_part, day_part = signed_at[:10].split("-")
                signed_at = f"{day_part}/{month_part}/{year_part}"

            values = [
                signed_at,
                sale.get("prospect_name") or "",
                sale.get("offer_name") or "",
            ]

            if self.show_commercial_column:
                values.append(sale.get("commercial_name") or "")

            values.extend(
                [
                    self._format_euro(int(sale.get("price_cents") or 0)),
                    self._format_rate(sale.get("commission_rate")),
                    self._format_euro(int(sale.get("commission_cents") or 0)),
                    sale.get("display_status") or "",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column in (self.amount_col, self.commission_col):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif column in (0, self.rate_col, self.status_col):
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                # Les colonnes badge sont rendues avec un QLabel,
                # mais l'item reste présent pour conserver la sélection de ligne.
                self.table.setItem(row_index, column, item)

                if column == self.rate_col:
                    badge = QLabel(str(value))
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setMinimumWidth(76)
                    badge.setFixedHeight(34)
                    badge.setStyleSheet(self._rate_badge_style())
                    self.table.setCellWidget(row_index, column, badge)

                elif column == self.status_col:
                    full_status = str(value)
                    status_text = full_status

                    prefix = "Validation automatique le "
                    if full_status.lower().startswith(prefix.lower()):
                        status_text = "Validation auto · " + full_status[len(prefix):]

                    badge = QLabel(status_text)
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setToolTip(full_status)
                    badge.setMinimumWidth(245)
                    badge.setFixedHeight(36)
                    badge.setStyleSheet(self._status_badge_style(full_status))
                    self.table.setCellWidget(row_index, column, badge)

            self.table.setRowHeight(row_index, 50)

        self.period_summary.setText(
            f"{len(self.sales_rows)} vente(s)"
        )
        self.status_label.setText(
            "Les commissions sont validées automatiquement à J+15 après "
            "l’enregistrement de la vente. Si J+15 tombe le mois suivant, "
            "la commission est reportée sur la facture du mois suivant."
        )
        self._update_action_buttons()

    def _selected(self, *, warn: bool = True) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.sales_rows):
            if warn:
                QMessageBox.information(
                    self, "Sélection", "Sélectionnez d'abord une vente."
                )
            return None
        return self.sales_rows[row]

    def _update_action_buttons(self) -> None:
        sale = self._selected(warn=False)
        is_admin = self._is_admin()
        if not sale or not is_admin:
            self.client_paid_button.setEnabled(False)
            self.commission_paid_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            return

        active = sale.get("status") == "signed"
        payment_status = sale.get("payment_status")
        commission_status = sale.get("commission_status")
        self.client_paid_button.setEnabled(active and payment_status == "pending")
        is_partner_beneficiary = (
            str(sale.get("commission_beneficiary_type") or "") == "commercial_partner"
        )
        # Une commission due à un partenaire ne se paie jamais vente par vente :
        # relevé -> facture PDF reçue -> paiement groupé.
        self.commission_paid_button.setEnabled(
            active
            and payment_status == "paid"
            and not is_partner_beneficiary
            and commission_status in {"due", "invoiced"}
        )
        self.cancel_button.setEnabled(
            active and payment_status != "paid" and commission_status != "paid"
        )

    def _new_sale(self) -> None:
        if not CloudRuntime.is_active():
            QMessageBox.warning(
                self, "Cloud", "Connectez-vous à Form@Prospect Cloud."
            )
            return
        if not self._may_create():
            QMessageBox.warning(
                self, "Autorisation", "Votre rôle ne permet pas d'enregistrer une vente."
            )
            return
        try:
            dialog = NewSaleDialog(CloudRuntime.api(), self)
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Chargement impossible", str(exc))
            return
        if dialog.exec():
            self.rafraichir()

    def _mark_client_paid(self) -> None:
        sale = self._selected()
        if not sale:
            return
        reference, accepted = QInputDialog.getText(
            self,
            "Encaissement client",
            "Référence du paiement ou de la facture (facultatif) :",
        )
        if not accepted:
            return
        if QMessageBox.question(
            self,
            "Confirmer l'encaissement",
            "Confirmez-vous que Form@Prof a encaissé le règlement du client ?\n\n"
            "La commission passera alors au statut « à verser ».",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            CloudRuntime.api().mark_cloud_sale_client_paid(
                str(sale.get("id") or ""),
                reference=reference,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Validation impossible", str(exc))
            return
        self.rafraichir()

    def _mark_commission_paid(self) -> None:
        sale = self._selected()
        if not sale:
            return
        reference, accepted = QInputDialog.getText(
            self,
            "Commission versée",
            "Référence du virement ou du règlement (facultatif) :",
        )
        if not accepted:
            return
        if QMessageBox.question(
            self,
            "Confirmer le versement",
            f"Confirmez-vous le versement de la commission de "
            f"{self._format_euro(int(sale.get('commission_cents') or 0))} ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            CloudRuntime.api().mark_cloud_sale_commission_paid(
                str(sale.get("id") or ""),
                reference=reference,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Validation impossible", str(exc))
            return
        self.rafraichir()

    def _generate_invoice(self) -> None:
        if not SessionState.has_role("Commercial"):
            return
        if not CloudRuntime.is_active():
            QMessageBox.warning(self, "Cloud", "Connectez-vous à Form@Prospect Cloud.")
            return

        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        period = f"{MONTHS[month - 1]} {year}"

        if QMessageBox.question(
            self,
            "Générer la facture mensuelle",
            f"Créer la facture regroupant toutes les commissions validées "
            f"à J+15 pour {period} ?\n\n"
            f"Une commission déjà facturée ne pourra pas être facturée une seconde fois.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        try:
            invoice = CloudRuntime.api().create_commission_invoice(
                year=year, month=month
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Facture impossible", str(exc))
            return

        default_name = f"{invoice.get('invoice_number') or 'facture-commissions'}.pdf"
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la facture",
            str(Path.home() / "Downloads" / default_name),
            "Document PDF (*.pdf)",
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                save_invoice_pdf(invoice, path)
            except Exception as exc:
                QMessageBox.critical(self, "PDF impossible", str(exc))
            else:
                QMessageBox.information(
                    self,
                    "Facture créée",
                    f"La facture {invoice.get('invoice_number')} a été créée "
                    f"et ajoutée à votre historique.\n\n{path}",
                )
        else:
            QMessageBox.information(
                self,
                "Facture créée",
                f"La facture {invoice.get('invoice_number')} a été créée "
                "et reste disponible dans votre historique.",
            )
        self.rafraichir()

    def _open_invoice_history(self) -> None:
        if not CloudRuntime.is_active():
            QMessageBox.warning(self, "Cloud", "Connectez-vous à Form@Prospect Cloud.")
            return
        dialog = CommissionInvoicesDialog(CloudRuntime.api(), self)
        dialog.exec()
        self.rafraichir()

    def _open_partner_statement_history(self) -> None:
        if not CloudRuntime.is_active():
            QMessageBox.warning(self, "Cloud", "Connectez-vous à Form@Prospect Cloud.")
            return
        if not SessionState.has_role("Administrateur", "Dirigeant hors France"):
            return

        dialog = PartnerCommissionStatementsDialog(
            CloudRuntime.api(),
            self,
            selected_year=int(self.year_combo.currentText()),
            selected_month=self.month_combo.currentIndex() + 1,
        )
        dialog.exec()
        self.rafraichir()

    def _cancel_selected(self) -> None:
        sale = self._selected()
        if not sale:
            return
        reason, accepted = QInputDialog.getMultiLineText(
            self,
            "Annuler la vente",
            "Motif de l'annulation :",
        )
        if not accepted:
            return
        if QMessageBox.question(
            self,
            "Confirmer l'annulation",
            "Cette vente ne sera plus comptée dans le chiffre d'affaires ni "
            "dans les commissions. Continuer ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            CloudRuntime.api().cancel_cloud_sale(
                str(sale.get("id") or ""),
                reason=reason,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Annulation impossible", str(exc))
            return
        self.rafraichir()
