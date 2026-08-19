from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QProgressBar, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.premium_theme import (
    BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON, TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime


MONTHS = [
    "Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
    "Juil", "Août", "Sep", "Oct", "Nov", "Déc",
]


class AdminStatisticsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.kpi_labels = {}
        self.month_bars = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    @staticmethod
    def _euro(cents):
        return (
            f"{int(cents or 0) / 100:,.2f} €"
            .replace(",", " ")
            .replace(".", ",")
        )

    @staticmethod
    def _percent(value):
        try:
            return f"{float(value or 0):.1f} %".replace(".", ",")
        except (TypeError, ValueError):
            return "0,0 %"

    def _panel(self):
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame{{background:{CARD};border:1px solid {BORDER};"
            "border-radius:12px;}}"
        )
        return frame

    def _title(self, text):
        label = QLabel(text)
        label.setStyleSheet(
            f"font-size:17px;font-weight:900;color:{TEXT};"
        )
        return label

    def _metric_card(self, title, icon):
        frame = self._panel()
        frame.setMinimumHeight(110)
        box = QVBoxLayout(frame)
        box.setContentsMargins(14, 12, 14, 12)
        top = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet(
            f"color:{MUTED};font-size:11px;font-weight:800;"
        )
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(
            "font-size:16px;background:#EEF6FF;border-radius:8px;padding:4px;"
        )
        top.addWidget(label)
        top.addStretch()
        top.addWidget(icon_label)
        value = QLabel("—")
        value.setStyleSheet(
            f"color:{NAVY};font-size:22px;font-weight:900;"
        )
        box.addLayout(top)
        box.addStretch()
        box.addWidget(value)
        return frame, value

    def _style_table(self, table):
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(260)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        table.setStyleSheet(
            f"QTableWidget{{background:white;color:{TEXT};"
            f"border:1px solid {BORDER};gridline-color:{BORDER};"
            "alternate-background-color:#F8FAFC;}}"
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background:{PAGE_BG};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 24, 30, 34)
        layout.setSpacing(18)

        header = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel("Statistiques administrateur")
        title.setStyleSheet(
            f"font-size:30px;font-weight:900;color:{TEXT};"
        )
        subtitle = QLabel(
            "Pilotage global de la performance commerciale."
        )
        subtitle.setStyleSheet(f"color:{MUTED};font-size:13px;")
        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text)
        header.addStretch()

        self.year = QComboBox()
        current = datetime.now().year
        for value in range(current - 4, current + 2):
            self.year.addItem(str(value), value)
        self.year.setCurrentText(str(current))
        self.year.currentIndexChanged.connect(self.rafraichir)

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(PRIMARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)
        header.addWidget(QLabel("Année :"))
        header.addWidget(self.year)
        header.addWidget(refresh)
        layout.addLayout(header)

        note = QLabel(
            "CA, ventes, encaissements, commissions et RDV : année sélectionnée. "
            "Prospects, clients et conversion prospect → client : portefeuille CRM actuel."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            f"background:white;border:1px solid {BORDER};border-radius:10px;"
            f"padding:10px 12px;color:{MUTED};"
        )
        layout.addWidget(note)

        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            ("signed_revenue_cents", "CA signé", "€"),
            ("sales_count", "Ventes", "✓"),
            ("collected_revenue_cents", "Encaissé", "€"),
            ("generated_commission_cents", "Commissions générées", "%"),
            ("average_basket_cents", "Panier moyen", "🛒"),
            ("prospects_assigned", "Prospects attribués", "👥"),
            ("clients_count", "Clients", "🤝"),
            ("appointments_obtained", "RDV obtenus", "📅"),
            ("prospect_to_client_rate", "Prospect → client", "↗"),
            ("client_to_sale_rate", "Client → vente", "🎯"),
            ("paid_commission_cents", "Commissions versées", "✓"),
        ]
        for i, (key, title_text, icon) in enumerate(cards):
            card, value = self._metric_card(title_text, icon)
            self.kpi_labels[key] = value
            grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(grid)

        layout.addWidget(self._title("Top commerciaux"))
        self.top_commercials_grid = QGridLayout()
        self.top_commercials_grid.setSpacing(12)
        self.top_commercial_cards = []
        for rank in range(3):
            card = self._panel()
            card.setMinimumHeight(118)
            card_box = QVBoxLayout(card)
            card_box.setContentsMargins(15, 13, 15, 13)
            rank_label = QLabel(f"TOP {rank + 1}")
            rank_label.setStyleSheet(
                f"color:{MUTED};font-size:10px;font-weight:900;"
            )
            name_label = QLabel("—")
            name_label.setStyleSheet(
                f"color:{TEXT};font-size:16px;font-weight:900;"
            )
            ca_label = QLabel("0,00 €")
            ca_label.setStyleSheet(
                f"color:{NAVY};font-size:20px;font-weight:900;"
            )
            detail_label = QLabel("0 vente • 0 RDV")
            detail_label.setStyleSheet(
                f"color:{MUTED};font-size:11px;"
            )
            card_box.addWidget(rank_label)
            card_box.addWidget(name_label)
            card_box.addWidget(ca_label)
            card_box.addWidget(detail_label)
            self.top_commercial_cards.append(
                (name_label, ca_label, detail_label)
            )
            self.top_commercials_grid.addWidget(card, 0, rank)
        layout.addLayout(self.top_commercials_grid)

        layout.addWidget(self._title("Performance par commercial"))
        self.commercials = QTableWidget(0, 11)
        self.commercials.setHorizontalHeaderLabels([
            "Commercial", "Prospects", "Clients", "RDV", "Ventes",
            "CA", "Encaissé", "Commissions", "Panier moyen",
            "Prospect → client", "Client → vente",
        ])
        self._style_table(self.commercials)
        layout.addWidget(self.commercials)

        lower = QGridLayout()
        lower.setSpacing(14)

        trainings_panel = self._panel()
        trainings_box = QVBoxLayout(trainings_panel)
        trainings_box.addWidget(self._title("Top formations"))
        self.trainings = QTableWidget(0, 4)
        self.trainings.setHorizontalHeaderLabels(
            ["Formation", "Ventes", "CA", "Encaissé"]
        )
        self._style_table(self.trainings)
        trainings_box.addWidget(self.trainings)
        lower.addWidget(trainings_panel, 0, 0)

        monthly_panel = self._panel()
        monthly_box = QVBoxLayout(monthly_panel)
        monthly_box.addWidget(
            self._title("Évolution mensuelle du CA")
        )
        for month in MONTHS:
            row = QHBoxLayout()
            label = QLabel(month)
            label.setFixedWidth(36)
            label.setStyleSheet(
                f"color:{MUTED};font-weight:700;"
            )
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            bar.setStyleSheet(
                "QProgressBar{border:none;background:#E8EDF4;"
                "border-radius:6px;}"
                "QProgressBar::chunk{background:#338CE4;"
                "border-radius:6px;}"
            )
            amount = QLabel("0 €")
            amount.setFixedWidth(105)
            amount.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount.setStyleSheet(f"color:{TEXT};font-size:11px;")
            row.addWidget(label)
            row.addWidget(bar, 1)
            row.addWidget(amount)
            monthly_box.addLayout(row)
            self.month_bars.append((bar, amount))
        self.monthly_table = QTableWidget(0, 5)
        self.monthly_table.setHorizontalHeaderLabels(
            ["Mois", "Ventes", "CA signé", "Encaissé", "Commissions"]
        )
        self._style_table(self.monthly_table)
        self.monthly_table.setMinimumHeight(250)
        monthly_box.addWidget(self.monthly_table)

        lower.addWidget(monthly_panel, 0, 1)
        lower.setColumnStretch(0, 3)
        lower.setColumnStretch(1, 2)
        layout.addLayout(lower)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED};")
        layout.addWidget(self.status)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def rafraichir(self):
        if not SessionState.has_role("Administrateur"):
            self.status.setText(
                "Cette section est réservée à l'administrateur."
            )
            return
        if not CloudRuntime.is_active():
            self.status.setText(
                "Connectez-vous au Cloud pour afficher les statistiques."
            )
            return

        year = int(self.year.currentData() or datetime.now().year)
        try:
            self.data = CloudRuntime.api().get_admin_statistics(
                year=year
            )
        except CloudAPIError as exc:
            self.status.setText(f"⛔ {exc}")
            return
        except Exception as exc:
            self.status.setText(f"⛔ {exc}")
            return

        totals = self.data.get("totals") or {}
        money = {
            "signed_revenue_cents",
            "collected_revenue_cents",
            "generated_commission_cents",
            "average_basket_cents",
            "paid_commission_cents",
        }
        percents = {
            "prospect_to_client_rate",
            "client_to_sale_rate",
        }
        for key, label in self.kpi_labels.items():
            raw = totals.get(key, 0)
            if key in money:
                label.setText(self._euro(raw))
            elif key in percents:
                label.setText(self._percent(raw))
            else:
                label.setText(str(int(raw or 0)))

        commercial_rows = self.data.get("commercials") or []
        self._fill_top_commercials(commercial_rows)
        self._fill_commercials(commercial_rows)
        self._fill_trainings(
            self.data.get("trainings") or []
        )
        self._fill_monthly(
            self.data.get("monthly") or []
        )
        self.status.setText(
            f"Actualisé — {year} — "
            f"{len(self.data.get('commercials') or [])} commercial(aux)."
        )

    def _fill_top_commercials(self, rows):
        for index, widgets in enumerate(self.top_commercial_cards):
            name_label, ca_label, detail_label = widgets
            if index >= len(rows):
                name_label.setText("—")
                ca_label.setText("0,00 €")
                detail_label.setText("0 vente • 0 RDV")
                continue

            row = rows[index]
            name_label.setText(
                str(row.get("commercial_name") or "Commercial")
            )
            ca_label.setText(
                self._euro(row.get("signed_revenue_cents") or 0)
            )
            ventes = int(row.get("sales_count") or 0)
            rdv = int(row.get("appointments_obtained") or 0)
            detail_label.setText(
                f"{ventes} vente(s) • {rdv} RDV"
            )

    def _fill_commercials(self, rows):
        self.commercials.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row.get("commercial_name") or "Commercial",
                int(row.get("prospects_assigned") or 0),
                int(row.get("clients_count") or 0),
                int(row.get("appointments_obtained") or 0),
                int(row.get("sales_count") or 0),
                self._euro(row.get("signed_revenue_cents") or 0),
                self._euro(
                    row.get("collected_revenue_cents") or 0
                ),
                self._euro(
                    row.get("generated_commission_cents") or 0
                ),
                self._euro(
                    row.get("average_basket_cents") or 0
                ),
                self._percent(
                    row.get("prospect_to_client_rate") or 0
                ),
                self._percent(
                    row.get("client_to_sale_rate") or 0
                ),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.commercials.setItem(r, c, item)

    def _fill_trainings(self, rows):
        self.trainings.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row.get("name")
                or row.get("reference")
                or "Formation",
                int(row.get("sales_count") or 0),
                self._euro(
                    row.get("signed_revenue_cents") or 0
                ),
                self._euro(
                    row.get("collected_revenue_cents") or 0
                ),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.trainings.setItem(r, c, item)

    def _fill_monthly(self, rows):
        rows_by_month = {
            int(row.get("month") or 0): row
            for row in rows
        }
        values = {
            month: int(
                (rows_by_month.get(month) or {}).get(
                    "signed_revenue_cents"
                ) or 0
            )
            for month in range(1, 13)
        }
        maximum = max(values.values(), default=0)

        self.monthly_table.setRowCount(12)

        for month, (bar, amount) in enumerate(
            self.month_bars, start=1
        ):
            row = rows_by_month.get(month) or {}
            cents = values.get(month, 0)
            bar.setValue(
                int((cents / maximum) * 1000)
                if maximum else 0
            )
            amount.setText(self._euro(cents))

            values_row = [
                MONTHS[month - 1],
                int(row.get("sales_count") or 0),
                self._euro(
                    row.get("signed_revenue_cents") or 0
                ),
                self._euro(
                    row.get("collected_revenue_cents") or 0
                ),
                self._euro(
                    row.get("generated_commission_cents") or 0
                ),
            ]
            for column, value in enumerate(values_row):
                item = QTableWidgetItem(str(value))
                if column > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.monthly_table.setItem(
                    month - 1,
                    column,
                    item,
                )
