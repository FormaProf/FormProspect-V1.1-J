from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.premium_theme import BORDER, MUTED, PAGE_BG, PRIMARY, PRIMARY_DARK, TEXT


class PortfolioTransferDialog(QDialog):
    """Prévisualise et déclenche un transfert serveur de portefeuille commercial."""

    def __init__(
        self,
        auth_service,
        membership_id: str,
        source_name: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.auth_service = auth_service
        self.membership_id = str(membership_id or "").strip()
        self.source_name = str(source_name or "").strip() or "Commercial"
        self.preview: dict = {}
        self.transfer_result: dict | None = None

        self.setWindowTitle("Transférer le portefeuille commercial")
        self.setModal(True)
        self.resize(720, 650)
        self.setMinimumSize(680, 600)
        self.setStyleSheet(self._style())

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        root.addWidget(self._build_header())
        root.addWidget(self._build_summary())
        root.addWidget(self._build_target())
        root.addStretch(1)
        root.addLayout(self._build_actions())

        self._load()

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("TransferHero")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 17, 20, 17)
        layout.setSpacing(5)

        eyebrow = QLabel("FORM@PROSPECT  ·  OFFBOARDING COMMERCIAL")
        eyebrow.setObjectName("TransferEyebrow")

        title = QLabel("Transférer un portefeuille")
        title.setObjectName("TransferTitle")

        self.source_label = QLabel(
            f"Source : {self.source_name}  ·  Compte désactivé requis"
        )
        self.source_label.setObjectName("TransferSource")

        subtitle = QLabel(
            "Les fiches prospects et les relances encore ouvertes sont reprises "
            "par le nouveau commercial. Les ventes, commissions et historiques "
            "restent attribués à leur auteur d’origine."
        )
        subtitle.setObjectName("TransferSubtitle")
        subtitle.setWordWrap(True)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(self.source_label)
        layout.addSpacing(3)
        layout.addWidget(subtitle)
        return frame

    def _build_summary(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SummaryCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("Aperçu avant transfert")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.metrics: dict[str, QLabel] = {}
        cards = [
            ("prospects_total", "Prospects", "0"),
            ("clients_current", "Clients actuels", "0"),
            ("prospects_archived", "Archivés", "0"),
            ("planned_activities", "Relances à reprendre", "0"),
            ("overdue_activities", "Dont en retard", "0"),
            ("historical_sales_count", "Ventes conservées", "0"),
            ("historical_commission_cents", "Commissions conservées", "0,00 €"),
        ]

        for index, (key, label, initial) in enumerate(cards):
            card = QFrame()
            card.setObjectName("MetricCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(3)

            label_widget = QLabel(label)
            label_widget.setObjectName("MetricLabel")
            value_widget = QLabel(initial)
            value_widget.setObjectName("MetricValue")
            value_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            card_layout.addWidget(label_widget)
            card_layout.addWidget(value_widget)

            row, column = divmod(index, 3)
            if index == len(cards) - 1:
                grid.addWidget(card, row, 0, 1, 3)
            else:
                grid.addWidget(card, row, column)
            self.metrics[key] = value_widget

        layout.addLayout(grid)

        self.status_message = QLabel("Chargement du portefeuille…")
        self.status_message.setObjectName("StatusMessage")
        self.status_message.setWordWrap(True)
        layout.addWidget(self.status_message)
        return frame

    def _build_target(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("TargetCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(8)

        title = QLabel("Nouveau propriétaire du portefeuille")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Seuls les comptes Commercial actifs de la même organisation sont proposés."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.target_combo = QComboBox()
        self.target_combo.setObjectName("TargetCombo")
        self.target_combo.currentIndexChanged.connect(self._update_transfer_state)
        layout.addWidget(self.target_combo)
        return frame

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        cancel = QPushButton("Annuler")
        cancel.setObjectName("GhostButton")
        cancel.clicked.connect(self.reject)

        self.transfer_button = QPushButton("Transférer le portefeuille")
        self.transfer_button.setObjectName("TransferPrimaryButton")
        self.transfer_button.setEnabled(False)
        self.transfer_button.clicked.connect(self._confirm_and_transfer)

        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(self.transfer_button)
        return row

    @staticmethod
    def _format_money(cents) -> str:
        try:
            value = int(cents or 0) / 100
        except (TypeError, ValueError):
            value = 0.0
        return f"{value:,.2f} €".replace(",", " ").replace(".", ",")

    def _load(self) -> None:
        if not self.membership_id:
            self._set_error("Identifiant du commercial source manquant.")
            return

        try:
            preview = self.auth_service.portfolio_transfer_preview(
                self.membership_id
            )
            users = self.auth_service.list_users()
        except Exception as exc:
            self._set_error(str(exc))
            return

        self.preview = preview
        self.source_name = str(
            preview.get("source_name") or self.source_name
        ).strip() or self.source_name
        self.source_label.setText(
            f"Source : {self.source_name}  ·  "
            + ("Compte actif" if preview.get("source_active") else "Compte inactif")
        )

        for key in (
            "prospects_total",
            "clients_current",
            "prospects_archived",
            "planned_activities",
            "overdue_activities",
            "historical_sales_count",
        ):
            self.metrics[key].setText(str(int(preview.get(key) or 0)))

        self.metrics["historical_commission_cents"].setText(
            self._format_money(preview.get("historical_commission_cents"))
        )

        source_user_id = str(preview.get("source_user_id") or "").strip()
        eligible = [
            user
            for user in users
            if bool(user.get("active"))
            and str(user.get("role") or "").strip() == "Commercial"
            and str(user.get("user_id") or "").strip()
            and str(user.get("user_id") or "").strip() != source_user_id
        ]
        eligible.sort(
            key=lambda user: (
                str(user.get("last_name") or "").lower(),
                str(user.get("first_name") or "").lower(),
                str(user.get("email") or "").lower(),
            )
        )

        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("Sélectionnez un commercial…", "")
        for user in eligible:
            full_name = (
                f"{user.get('first_name') or ''} {user.get('last_name') or ''}"
            ).strip()
            label = full_name or str(user.get("email") or "Commercial")
            email = str(user.get("email") or "").strip()
            if email and email.lower() not in label.lower():
                label = f"{label}  ·  {email}"
            self.target_combo.addItem(label, str(user.get("user_id") or "").strip())
        self.target_combo.blockSignals(False)

        if not preview.get("can_transfer"):
            reason = str(preview.get("blocked_reason") or "").strip()
            self.status_message.setText(
                reason or "Ce portefeuille ne peut pas être transféré."
            )
            self.status_message.setProperty("state", "error")
        elif not eligible:
            self.status_message.setText(
                "Aucun autre Commercial actif n’est actuellement disponible "
                "pour recevoir ce portefeuille."
            )
            self.status_message.setProperty("state", "warning")
        else:
            self.status_message.setText(
                "Le transfert ne recrée aucune fiche : le propriétaire des prospects "
                "existants est simplement réattribué."
            )
            self.status_message.setProperty("state", "ok")

        self.status_message.style().unpolish(self.status_message)
        self.status_message.style().polish(self.status_message)
        self._update_transfer_state()

    def _set_error(self, message: str) -> None:
        self.preview = {}
        self.status_message.setText(message or "Impossible de charger le portefeuille.")
        self.status_message.setProperty("state", "error")
        self.status_message.style().unpolish(self.status_message)
        self.status_message.style().polish(self.status_message)
        self.target_combo.clear()
        self.target_combo.addItem("Aucun destinataire disponible", "")
        self.transfer_button.setEnabled(False)

    def _update_transfer_state(self, *_args) -> None:
        target_user_id = str(self.target_combo.currentData() or "").strip()
        can_transfer = bool(self.preview.get("can_transfer"))
        self.transfer_button.setEnabled(bool(target_user_id and can_transfer))

    def _confirm_and_transfer(self) -> None:
        target_user_id = str(self.target_combo.currentData() or "").strip()
        target_name = self.target_combo.currentText().strip()

        if not target_user_id:
            QMessageBox.information(
                self,
                "Transfert de portefeuille",
                "Sélectionnez le commercial qui doit reprendre le portefeuille.",
            )
            return

        prospects = int(self.preview.get("prospects_total") or 0)
        activities = int(self.preview.get("planned_activities") or 0)
        sales = int(self.preview.get("historical_sales_count") or 0)

        answer = QMessageBox.question(
            self,
            "Confirmer le transfert",
            (
                f"Transférer le portefeuille de {self.source_name} vers {target_name} ?\n\n"
                f"• {prospects} prospect(s) changeront de propriétaire\n"
                f"• {activities} activité(s) planifiée(s) seront réattribuée(s)\n"
                f"• {sales} vente(s) historique(s) resteront attribuée(s) "
                f"à {self.source_name}\n\n"
                "Cette opération est enregistrée dans le journal d’audit."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.transfer_button.setEnabled(False)
        try:
            result = self.auth_service.transfer_portfolio(
                self.membership_id,
                target_user_id,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Transfert impossible",
                str(exc),
            )
            self._update_transfer_state()
            return

        self.transfer_result = result
        QMessageBox.information(
            self,
            "Portefeuille transféré",
            (
                f"{int(result.get('prospects_transferred') or 0)} prospect(s) et "
                f"{int(result.get('activities_transferred') or 0)} activité(s) "
                "planifiée(s) ont été transférés.\n\n"
                "Les ventes, commissions et historiques passés n’ont pas été réattribués."
            ),
        )
        self.accept()

    @staticmethod
    def _style() -> str:
        return f"""
            QDialog {{
                background: {PAGE_BG};
            }}

            QFrame#TransferHero {{
                background: #0B2A4F;
                border: 1px solid #163D69;
                border-radius: 18px;
            }}

            QLabel#TransferEyebrow {{
                color: #5FC0FF;
                font-size: 9px;
                font-weight: 900;
            }}

            QLabel#TransferTitle {{
                color: white;
                font-size: 23px;
                font-weight: 900;
            }}

            QLabel#TransferSource {{
                color: #BFE1FF;
                font-size: 10px;
                font-weight: 800;
            }}

            QLabel#TransferSubtitle {{
                color: #D5E7F8;
                font-size: 10px;
            }}

            QFrame#SummaryCard,
            QFrame#TargetCard {{
                background: white;
                border: 1px solid #DDE6F0;
                border-radius: 14px;
            }}

            QLabel#SectionTitle {{
                color: {TEXT};
                font-size: 14px;
                font-weight: 900;
            }}

            QFrame#MetricCard {{
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }}

            QLabel#MetricLabel {{
                color: #64748B;
                font-size: 9px;
                font-weight: 700;
            }}

            QLabel#MetricValue {{
                color: {TEXT};
                font-size: 19px;
                font-weight: 900;
            }}

            QLabel#Hint {{
                color: {MUTED};
                font-size: 9px;
            }}

            QLabel#StatusMessage {{
                padding: 9px 11px;
                border-radius: 9px;
                font-size: 9px;
                font-weight: 700;
                background: #EFF6FF;
                color: #1D4ED8;
                border: 1px solid #BFDBFE;
            }}

            QLabel#StatusMessage[state="ok"] {{
                background: #ECFDF5;
                color: #047857;
                border-color: #A7F3D0;
            }}

            QLabel#StatusMessage[state="warning"] {{
                background: #FFFBEB;
                color: #B45309;
                border-color: #FDE68A;
            }}

            QLabel#StatusMessage[state="error"] {{
                background: #FEF2F2;
                color: #B91C1C;
                border-color: #FECACA;
            }}

            QComboBox#TargetCombo {{
                min-height: 40px;
                padding: 0 34px 0 12px;
                background: #F8FAFC;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                font-size: 10px;
                font-weight: 700;
            }}

            QComboBox#TargetCombo:focus {{
                background: white;
                border: 1px solid {PRIMARY};
            }}

            QPushButton#TransferPrimaryButton {{
                min-height: 40px;
                padding: 0 18px;
                background: {PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 900;
            }}

            QPushButton#TransferPrimaryButton:hover {{
                background: {PRIMARY_DARK};
            }}

            QPushButton#TransferPrimaryButton:disabled {{
                background: #CBD5E1;
                color: #F8FAFC;
            }}

            QPushButton#GhostButton {{
                min-height: 40px;
                padding: 0 16px;
                background: white;
                color: #475569;
                border: 1px solid {BORDER};
                border-radius: 10px;
                font-size: 10px;
                font-weight: 800;
            }}

            QPushButton#GhostButton:hover {{
                color: {PRIMARY};
                border-color: {PRIMARY};
            }}
        """
