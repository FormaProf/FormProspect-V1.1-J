from __future__ import annotations

from datetime import date, datetime, timedelta

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

from core.session import SessionState
from core.theme_settings import get_theme_preference
from ui.commissions_premium_theme import (
    commissions_page_stylesheet,
    commissions_palette,
    commissions_table_stylesheet,
)
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.dialogs.new_sale_dialog import NewSaleDialog
from ui.dialogs.commission_invoices_dialog import CommissionInvoicesDialog
from ui.dialogs.partner_commission_statements_dialog import PartnerCommissionStatementsDialog
from services.commission_invoice_pdf import save_invoice_pdf


MONTHS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


class PremiumFinanceCard(QFrame):
    """Carte KPI compacte pour le cockpit ventes & commissions."""

    def __init__(
        self,
        label: str,
        value: str,
        accent_key: str,
        helper: str = "",
    ):
        super().__init__()
        self.setObjectName("SalesKpiCard")
        self.setMinimumHeight(88)
        self.accent_key = str(accent_key or "primary")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 11)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(7)

        self.dot = QLabel()
        self.dot.setFixedSize(9, 9)

        self.label = QLabel(label)
        self.label.setObjectName("SalesKpiLabel")

        top.addWidget(self.dot)
        top.addWidget(self.label)
        top.addStretch()

        self.value = QLabel(value)
        self.value.setObjectName("SalesKpiValue")

        self.helper = QLabel(helper)
        self.helper.setObjectName("SalesKpiHelper")

        layout.addLayout(top)
        layout.addWidget(self.value)
        if helper:
            layout.addWidget(self.helper)

    def set_value(self, value: str):
        self.value.setText(str(value))

    def apply_palette(self, palette: dict[str, str]) -> None:
        accent = palette.get(self.accent_key, palette["primary"])
        self.dot.setStyleSheet(
            f"background:{accent}; border:none; border-radius:4px;"
        )


class CommissionsPage(QWidget):
    """Pilotage Cloud des ventes, encaissements et commissions."""

    def __init__(self):
        super().__init__()
        self.setObjectName("CommissionsPage")
        self.sales_rows: list[dict] = []
        self._resolved_theme = get_theme_preference()
        self._palette = commissions_palette(self._resolved_theme)
        self._status_tone = "muted"
        self._build_ui()
        self._apply_visual_theme()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 22)
        root.setSpacing(12)

        # -------------------------
        # Header / période / actions
        # -------------------------
        header_card = QFrame()
        header_card.setObjectName("SalesHeader")

        header_root = QVBoxLayout(header_card)
        header_root.setContentsMargins(20, 16, 18, 14)
        header_root.setSpacing(12)

        header_top = QHBoxLayout()
        header_top.setSpacing(14)

        titles = QVBoxLayout()
        titles.setSpacing(2)

        eyebrow = QLabel("VENTES  •  PILOTAGE FINANCIER")
        eyebrow.setObjectName("SalesEyebrow")

        title = QLabel("Ventes & commissions")
        title.setObjectName("SalesTitle")

        self.subtitle = QLabel(
            "Suivi sécurisé des contrats, encaissements et commissions dans le Cloud."
        )
        self.subtitle.setObjectName("SalesSubtitle")
        self.subtitle.setWordWrap(True)

        titles.addWidget(eyebrow)
        titles.addWidget(title)
        titles.addWidget(self.subtitle)

        header_top.addLayout(titles, 1)

        current = date.today()

        period_panel = QFrame()
        period_panel.setObjectName("SalesPeriodPanel")
        period_layout = QHBoxLayout(period_panel)
        period_layout.setContentsMargins(12, 8, 10, 8)
        period_layout.setSpacing(8)

        period_label = QLabel("PÉRIODE")
        period_label.setObjectName("SalesPeriodLabel")

        self.month_combo = QComboBox()
        self.month_combo.setObjectName("SalesPeriodCombo")
        self.month_combo.addItems(MONTHS)
        self.month_combo.setCurrentIndex(current.month - 1)
        self.month_combo.setFixedHeight(36)
        self.month_combo.setMinimumWidth(112)

        self.year_combo = QComboBox()
        self.year_combo.setObjectName("SalesPeriodCombo")
        self.year_combo.addItems(
            [str(year) for year in range(current.year - 3, current.year + 21)]
        )
        self.year_combo.setCurrentText(str(current.year))
        self.year_combo.setFixedHeight(36)
        self.year_combo.setMinimumWidth(78)

        self.cloud_badge = QLabel("")
        self.cloud_badge.setObjectName("SalesCloudBadge")
        self.cloud_badge.setAlignment(Qt.AlignCenter)

        period_layout.addWidget(period_label)
        period_layout.addWidget(self.month_combo)
        period_layout.addWidget(self.year_combo)

        header_top.addWidget(self.cloud_badge, 0, Qt.AlignTop)
        header_top.addWidget(period_panel, 0, Qt.AlignTop)

        header_root.addLayout(header_top)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.refresh_button = QPushButton("Actualiser")
        self.refresh_button.setObjectName("SalesSecondaryButton")
        self.refresh_button.setFixedHeight(38)
        self.refresh_button.clicked.connect(self.rafraichir)

        self.history_button = QPushButton("Historique factures")
        self.history_button.setObjectName("SalesSecondaryButton")
        self.history_button.setFixedHeight(38)
        self.history_button.clicked.connect(self._open_invoice_history)
        self.history_button.setVisible(
            SessionState.has_role("Commercial", "Administrateur")
        )

        self.partner_history_button = QPushButton("Relevés partenaire")
        self.partner_history_button.setObjectName("SalesSecondaryButton")
        self.partner_history_button.setFixedHeight(38)
        self.partner_history_button.setVisible(
            SessionState.has_role("Administrateur", "Dirigeant hors France")
        )
        self.partner_history_button.clicked.connect(
            self._open_partner_statement_history
        )

        self.invoice_button = QPushButton("Générer ma facture")
        self.invoice_button.setObjectName("SalesSecondaryButton")
        self.invoice_button.setFixedHeight(38)
        self.invoice_button.setVisible(SessionState.has_role("Commercial"))
        self.invoice_button.clicked.connect(self._generate_invoice)

        self.add_button = QPushButton("＋ Enregistrer une vente")
        self.add_button.setObjectName("SalesPrimaryButton")
        self.add_button.setFixedHeight(38)
        self.add_button.clicked.connect(self._new_sale)

        actions.addWidget(self.refresh_button)
        actions.addWidget(self.history_button)
        actions.addWidget(self.partner_history_button)
        actions.addWidget(self.invoice_button)
        actions.addStretch()
        actions.addWidget(self.add_button)

        header_root.addLayout(actions)
        root.addWidget(header_card)

        # -------------------------
        # KPI financiers compacts
        # -------------------------
        cards = QGridLayout()
        cards.setHorizontalSpacing(9)
        cards.setVerticalSpacing(9)

        self.contracts_card = PremiumFinanceCard(
            "Contrats signés", "0", "primary", "Ventes enregistrées"
        )
        self.signed_revenue_card = PremiumFinanceCard(
            "CA signé", "0,00 €", "finance", "Valeur contractuelle"
        )
        self.collected_revenue_card = PremiumFinanceCard(
            "CA encaissé", "0,00 €", "success", "Règlements reçus"
        )
        self.pending_card = PremiumFinanceCard(
            "Commissions en attente", "0,00 €", "warning", "En validation"
        )
        self.due_card = PremiumFinanceCard(
            "Commissions à verser", "0,00 €", "violet", "Validées et dues"
        )
        self.paid_card = PremiumFinanceCard(
            "Commissions versées", "0,00 €", "success", "Paiements finalisés"
        )

        self.metric_cards = [
            self.contracts_card,
            self.signed_revenue_card,
            self.collected_revenue_card,
            self.pending_card,
            self.due_card,
            self.paid_card,
        ]

        for index, card in enumerate(self.metric_cards):
            cards.setColumnStretch(index, 1)
            cards.addWidget(card, 0, index)

        root.addLayout(cards)

        # -------------------------
        # Flux financier / ventes
        # -------------------------
        table_frame = QFrame()
        table_frame.setObjectName("SalesTableCard")

        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(14, 13, 14, 13)
        table_layout.setSpacing(10)

        table_header = QHBoxLayout()
        table_titles = QVBoxLayout()
        table_titles.setSpacing(2)

        table_eyebrow = QLabel("FLUX FINANCIER DU MOIS")
        table_eyebrow.setObjectName("SalesSectionEyebrow")

        table_title = QLabel("Détail des ventes")
        table_title.setObjectName("SalesTableTitle")

        table_helper = QLabel(
            "Contrats, encaissements et commissions de la période sélectionnée."
        )
        table_helper.setObjectName("SalesTableHelper")

        table_titles.addWidget(table_eyebrow)
        table_titles.addWidget(table_title)
        table_titles.addWidget(table_helper)

        self.period_summary = QLabel("0 vente")
        self.period_summary.setObjectName("SalesPeriodSummary")
        self.period_summary.setAlignment(Qt.AlignCenter)
        self.period_summary.setMinimumWidth(104)
        self.period_summary.setFixedHeight(28)

        table_header.addLayout(table_titles)
        table_header.addStretch()
        table_header.addWidget(self.period_summary, 0, Qt.AlignTop)
        table_layout.addLayout(table_header)

        self.show_commercial_column = (
            SessionState.has_role("Administrateur")
            or SessionState.has_role("Manager")
            or SessionState.has_role("Dirigeant hors France")
        )

        if self.show_commercial_column:
            self.table_headers = [
                "Date", "Client", "Formation", "Commercial",
                "Montant", "Taux", "Commission", "Paiement", "Statut",
            ]
        else:
            self.table_headers = [
                "Date", "Client", "Formation",
                "Montant", "Taux", "Commission", "Paiement", "Statut",
            ]

        self.table = QTableWidget(0, len(self.table_headers))
        self.table.setHorizontalHeaderLabels(self.table_headers)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 230)
        self.table.setColumnWidth(2, 180)

        if self.show_commercial_column:
            self.table.horizontalHeader().setSectionResizeMode(
                3, QHeaderView.Fixed
            )
            self.table.setColumnWidth(3, 150)

        self.table.setMinimumHeight(285)
        self.table.itemSelectionChanged.connect(self._update_action_buttons)

        self.rate_col = self.table_headers.index("Taux")
        self.status_col = self.table_headers.index("Statut")
        self.amount_col = self.table_headers.index("Montant")
        self.commission_col = self.table_headers.index("Commission")
        self.payment_col = self.table_headers.index("Paiement")

        self.table.horizontalHeader().setSectionResizeMode(
            self.rate_col, QHeaderView.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.payment_col, QHeaderView.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            self.status_col, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(self.rate_col, 92)
        self.table.setColumnWidth(self.payment_col, 180)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("SalesEmptyState")
        self.empty_state.setMinimumHeight(210)

        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(7)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_icon = QLabel("◎")
        empty_icon.setObjectName("SalesEmptyIcon")
        empty_icon.setFixedSize(38, 38)
        empty_icon.setAlignment(Qt.AlignCenter)

        empty_title = QLabel("Aucune vente sur cette période")
        empty_title.setObjectName("SalesEmptyTitle")
        empty_title.setAlignment(Qt.AlignCenter)

        empty_helper = QLabel(
            "Les nouvelles ventes apparaîtront ici dès leur enregistrement."
        )
        empty_helper.setObjectName("SalesEmptyHelper")
        empty_helper.setAlignment(Qt.AlignCenter)
        empty_helper.setWordWrap(True)

        empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_helper)

        table_layout.addWidget(self.table)
        table_layout.addWidget(self.empty_state)
        root.addWidget(table_frame, 1)

        # -------------------------
        # Information / actions administration
        # -------------------------
        footer_card = QFrame()
        footer_card.setObjectName("SalesFooter")

        action_bar = QHBoxLayout(footer_card)
        action_bar.setContentsMargins(13, 9, 13, 9)
        action_bar.setSpacing(8)

        self.status_label = QLabel("")
        self.status_label.setObjectName("SalesStatusText")
        self.status_label.setWordWrap(True)
        action_bar.addWidget(self.status_label, 1)

        self.client_paid_button = QPushButton("Valider l'encaissement")
        self.client_paid_button.setObjectName("SalesSecondaryButton")
        self.client_paid_button.setFixedHeight(36)
        self.client_paid_button.clicked.connect(self._mark_client_paid)

        self.commission_paid_button = QPushButton("Commission versée")
        self.commission_paid_button.setObjectName("SalesSecondaryButton")
        self.commission_paid_button.setFixedHeight(36)
        self.commission_paid_button.clicked.connect(self._mark_commission_paid)

        self.cancel_button = QPushButton("Annuler la vente")
        self.cancel_button.setObjectName("SalesDangerButton")
        self.cancel_button.setFixedHeight(36)
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
        self._update_table_empty_state()
        self._update_action_buttons()

    def _apply_visual_theme(self) -> None:
        self._resolved_theme = get_theme_preference()
        self._palette = commissions_palette(self._resolved_theme)

        self.setStyleSheet(commissions_page_stylesheet(self._palette))
        self.table.setStyleSheet(commissions_table_stylesheet(self._palette))

        for card in self.metric_cards:
            card.apply_palette(self._palette)

        self._refresh_cloud_badge()
        self._set_status_text(self.status_label.text(), self._status_tone)
        self._restyle_table_badges()

    def _refresh_cloud_badge(self) -> None:
        active = CloudRuntime.is_active()
        if active:
            bg = self._palette["success_bg"]
            fg = self._palette["success_text"]
            border = self._palette["success_border"]
            text = "●  CLOUD · CONNECTÉ"
        else:
            bg = self._palette["neutral_bg"]
            fg = self._palette["neutral_text"]
            border = self._palette["neutral_border"]
            text = "○  CLOUD · HORS LIGNE"

        self.cloud_badge.setText(text)
        self.cloud_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            "border-radius:10px; padding:5px 10px; "
            "font-size:9px; font-weight:900;"
        )

    def _set_status_text(self, text: str, tone: str = "muted") -> None:
        self._status_tone = str(tone or "muted")
        self.status_label.setText(str(text or ""))

        if self._status_tone == "danger":
            color = self._palette["danger_text"]
        elif self._status_tone == "info":
            color = self._palette["primary_text"]
        else:
            color = self._palette["muted"]

        self.status_label.setStyleSheet(
            f"color:{color}; background:transparent; border:none; font-size:10px;"
        )

    def _update_table_empty_state(self) -> None:
        has_rows = bool(self.sales_rows)
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        count = len(self.sales_rows)
        self.period_summary.setText(
            f"{count} vente" if count == 1 else f"{count} ventes"
        )

    def _restyle_table_badges(self) -> None:
        for row_index, sale in enumerate(self.sales_rows):
            if row_index >= self.table.rowCount():
                break

            rate_widget = self.table.cellWidget(row_index, self.rate_col)
            if isinstance(rate_widget, QLabel):
                rate_widget.setStyleSheet(self._rate_badge_style())

            payment_widget = self.table.cellWidget(row_index, self.payment_col)
            if isinstance(payment_widget, QLabel):
                payment_widget.setStyleSheet(
                    self._payment_badge_style(payment_widget.text())
                )

            status_widget = self.table.cellWidget(row_index, self.status_col)
            if isinstance(status_widget, QLabel):
                status_widget.setStyleSheet(
                    self._status_badge_style(
                        sale.get("display_status") or status_widget.text()
                    )
                )

    @staticmethod
    def _parse_iso_date(value) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(text[:10])
            except ValueError:
                return None

    @classmethod
    def _payment_display(cls, sale: dict) -> tuple[str, str]:
        status = str(sale.get("payment_status") or "pending").lower()
        paid_on = cls._parse_iso_date(sale.get("client_paid_at"))

        if status == "paid":
            if paid_on:
                text = f"Payé · {paid_on.strftime('%d/%m/%Y')}"
                return text, f"Paiement client encaissé le {paid_on.strftime('%d/%m/%Y')}."
            return "Payé", "Paiement client encaissé."

        if status == "refunded":
            return "Remboursé", "Le règlement client a été remboursé."

        signed_on = cls._parse_iso_date(sale.get("signed_at"))
        if signed_on is None:
            return "En attente", "Paiement client en attente de confirmation par l’administration."

        due_on = signed_on + timedelta(days=10)
        if date.today() > due_on:
            return (
                f"En retard · {due_on.strftime('%d/%m')}",
                f"Paiement en retard. Échéance contractuelle : {due_on.strftime('%d/%m/%Y')}. "
                "Le commercial peut relancer le client ; seul l’administration peut confirmer l’encaissement.",
            )
        return (
            f"En attente · {due_on.strftime('%d/%m')}",
            f"Paiement attendu au plus tard le {due_on.strftime('%d/%m/%Y')}. "
            "Seul l’administration peut confirmer l’encaissement.",
        )

    def _payment_badge_style(self, payment_text: str) -> str:
        text = str(payment_text or "").lower()
        if "payé" in text:
            bg = self._palette["success_bg"]
            fg = self._palette["success_text"]
            border = self._palette["success_border"]
        elif "retard" in text or "rembours" in text:
            bg = self._palette["danger_bg"]
            fg = self._palette["danger_text"]
            border = self._palette["danger_border"]
        else:
            bg = self._palette["warning_bg"]
            fg = self._palette["warning_text"]
            border = self._palette["warning_border"]

        return (
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            "border-radius:10px; padding:4px 10px; "
            "font-size:10px; font-weight:900;"
        )

    def _status_badge_style(self, status_text: str) -> str:
        text = str(status_text or "").lower()

        if "versée" in text or "payée" in text:
            bg = self._palette["success_bg"]
            fg = self._palette["success_text"]
            border = self._palette["success_border"]
        elif "annul" in text:
            bg = self._palette["danger_bg"]
            fg = self._palette["danger_text"]
            border = self._palette["danger_border"]
        elif "factur" in text:
            bg = self._palette["warning_bg"]
            fg = self._palette["warning_text"]
            border = self._palette["warning_border"]
        elif "validation automatique" in text or "à verser" in text:
            bg = self._palette["info_bg"]
            fg = self._palette["info_text"]
            border = self._palette["info_border"]
        else:
            bg = self._palette["neutral_bg"]
            fg = self._palette["neutral_text"]
            border = self._palette["neutral_border"]

        return (
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            "border-radius:10px; padding:4px 12px; "
            "font-size:11px; font-weight:900;"
        )

    def _rate_badge_style(self) -> str:
        return (
            f"background:{self._palette['violet_bg']}; "
            f"color:{self._palette['violet_text']}; "
            f"border:1px solid {self._palette['violet_border']}; "
            "border-radius:10px; padding:4px 12px; "
            "font-size:12px; font-weight:900;"
        )

    @staticmethod
    def _is_admin() -> bool:
        return SessionState.has_role("Administrateur")

    @staticmethod
    def _may_create() -> bool:
        return SessionState.has_role("Administrateur", "Manager", "Dirigeant hors France", "Commercial")

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
        self._update_table_empty_state()
        self._update_action_buttons()

    def rafraichir(self, *_args) -> None:
        self._refresh_cloud_badge()
        self.add_button.setEnabled(self._may_create() and CloudRuntime.is_active())

        if not CloudRuntime.is_active():
            self._reset()
            self.subtitle.setText(
                "Connectez-vous à Form@Prospect Cloud pour consulter les ventes."
            )
            self._set_status_text("Aucune session Cloud active.", "muted")
            return

        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        self._set_status_text("Chargement des ventes Cloud…", "info")

        try:
            api = CloudRuntime.api()
            summary = api.get_cloud_sales_summary(year=year, month=month)
            self.sales_rows = api.list_cloud_sales(year=year, month=month)
        except (CloudAPIError, RuntimeError) as exc:
            self._reset()
            self.subtitle.setText("Ventes & commissions Cloud")
            self._set_status_text(f"⛔ {exc}", "danger")
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
        elif user and user.role == "Dirigeant hors France":
            self.subtitle.setText(
                f"Vue du call center partenaire — {MONTHS[month - 1]} {year}"
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
                sale.get("offer_reference") or sale.get("offer_name") or "",
            ]

            if self.show_commercial_column:
                values.append(sale.get("commercial_name") or "")

            values.extend(
                [
                    self._format_euro(int(sale.get("price_cents") or 0)),
                    self._format_rate(sale.get("commission_rate")),
                    self._format_euro(int(sale.get("commission_cents") or 0)),
                    self._payment_display(sale)[0],
                    sale.get("display_status") or "",
                ]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                # Toutes les valeurs du tableau sont centrées pour conserver
                # une lecture homogène, y compris Client / Formation / montants.
                item.setTextAlignment(Qt.AlignCenter)
                if column == 1:
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

                elif column == self.payment_col:
                    payment_text, payment_tooltip = self._payment_display(sale)
                    badge = QLabel(payment_text)
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setToolTip(payment_tooltip)
                    badge.setMinimumWidth(155)
                    badge.setFixedHeight(36)
                    badge.setStyleSheet(self._payment_badge_style(payment_text))
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

        self._update_table_empty_state()
        self._set_status_text(
            "J+15 démarre à la signature de la convention. La commission n’est validée "
            "automatiquement que si le paiement client a été encaissé. Si J+15 tombe le mois "
            "suivant, elle est reportée sur la facture du mois suivant.",
            "muted",
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
            "Le commercial verra immédiatement le paiement comme encaissé. "
            "La commission restera en attente jusqu’à J+15 si cette date n’est pas encore atteinte.",
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
