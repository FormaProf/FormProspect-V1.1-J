from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from core.premium_theme import BORDER, MUTED, NAVY, PRIMARY, TEXT
from services.cloud_api_client import CloudAPIError


class NewSaleDialog(QDialog):
    """Enregistrement sécurisé d'une vente dans Form@Prospect Cloud."""

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.prospects: list[dict] = []
        self.trainings: list[dict] = []

        self.setWindowTitle("Enregistrer une vente")
        self.resize(960, 800)
        self.setMinimumSize(840, 700)
        self.setStyleSheet("background:#F5F8FC;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("NewSaleHeader")
        header.setStyleSheet("""
            QFrame#NewSaleHeader {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:0.72 #F7FBFF,
                    stop:1 #EAF4FF
                );
                border:none;
                border-bottom:1px solid #E4EBF4;
            }
        """)

        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(26, 22, 26, 20)
        header_layout.setSpacing(4)

        eyebrow = QLabel("VENTE  •  ENREGISTREMENT COMMERCIAL")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        title = QLabel("Convention signée · créer la vente")
        title.setStyleSheet(
            "font-size:28px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        subtitle = QLabel(
            "Enregistrez la vente uniquement lorsque la convention de formation est signée. "
            "La commission est alors créée au statut « En attente » et son délai J+15 démarre."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size:12px; color:#6B7A90; background:transparent; border:none;"
        )

        header_layout.addWidget(eyebrow)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QWidget()
        body.setStyleSheet("background:#F5F8FC;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 22, 26, 22)
        body_layout.setSpacing(16)

        contract_card = QFrame()
        contract_card.setObjectName("ContractCard")
        contract_card.setMinimumHeight(300)
        contract_card.setStyleSheet("""
            QFrame#ContractCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        contract_layout = QVBoxLayout(contract_card)
        contract_layout.setContentsMargins(20, 18, 20, 20)
        contract_layout.setSpacing(12)

        section_label = QLabel("CONVENTION DE FORMATION SIGNÉE")
        section_label.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        section_help = QLabel(
            "Les informations tarifaires sont récupérées automatiquement et ne peuvent pas être modifiées. "
            "La date ci-dessous doit être la date de signature de la convention."
        )
        section_help.setWordWrap(True)
        section_help.setStyleSheet(
            "font-size:11px; color:#7A899C; background:transparent; border:none;"
        )

        contract_layout.addWidget(section_label)
        contract_layout.addWidget(section_help)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.prospect_combo = QComboBox()
        self.training_combo = QComboBox()
        self.prospect_combo.setToolTip("Sélectionnez le client concerné par la vente.")
        self.training_combo.setToolTip("Sélectionnez la formation vendue.")

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMaximumDate(QDate.currentDate())

        self._style_input(self.prospect_combo)
        self._style_input(self.training_combo)
        self._style_date(self.date_edit)

        grid.addWidget(self._field_block("Client", self.prospect_combo), 0, 0, 1, 2)
        grid.addWidget(self._field_block("Formation vendue", self.training_combo), 1, 0, 1, 2)
        grid.addWidget(self._field_block("Date de signature de la convention", self.date_edit), 2, 0, 1, 2)

        contract_layout.addLayout(grid)
        body_layout.addWidget(contract_card)

        calc_card = QFrame()
        calc_card.setObjectName("CalcCard")
        calc_card.setStyleSheet("""
            QFrame#CalcCard {
                background:#F8FBFF;
                border:1px solid #CFE3F8;
                border-radius:18px;
            }
        """)
        calc_layout = QVBoxLayout(calc_card)
        calc_layout.setContentsMargins(20, 18, 20, 18)
        calc_layout.setSpacing(8)

        calc_label = QLabel("CALCUL AUTOMATIQUE")
        calc_label.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        self.preview = QLabel("Chargement du catalogue…")
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet(
            "font-size:15px; font-weight:900; color:#0B2A52; "
            "background:transparent; border:none;"
        )

        calc_hint = QLabel(
            "La commission reste en attente jusqu’à J+15 et ne peut être validée que si le paiement client est encaissé."
        )
        calc_hint.setWordWrap(True)
        calc_hint.setStyleSheet(
            "font-size:10px; color:#6B7A90; background:transparent; border:none;"
        )

        calc_layout.addWidget(calc_label)
        calc_layout.addWidget(self.preview)
        calc_layout.addWidget(calc_hint)
        body_layout.addWidget(calc_card)

        notes_card = QFrame()
        notes_card.setObjectName("NotesCard")
        notes_card.setStyleSheet("""
            QFrame#NotesCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(20, 18, 20, 20)
        notes_layout.setSpacing(8)

        notes_label = QLabel("NOTE INTERNE")
        notes_label.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        notes_help = QLabel(
            "Ajoutez, si nécessaire, une information utile concernant le contrat signé."
        )
        notes_help.setWordWrap(True)
        notes_help.setStyleSheet(
            "font-size:11px; color:#7A899C; background:transparent; border:none;"
        )

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Note facultative sur le contrat signé…")
        self.notes.setMinimumHeight(100)
        self.notes.setStyleSheet("""
            QTextEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:11px;
                padding:10px;
                font-size:12px;
            }
            QTextEdit:focus {
                border:2px solid #338CE4;
            }
        """)

        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(notes_help)
        notes_layout.addWidget(self.notes)
        body_layout.addWidget(notes_card)

        body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background:#F5F8FC;
                border:none;
            }
            QScrollBar:vertical {
                background:transparent;
                width:10px;
                margin:4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background:#CBD5E1;
                min-height:38px;
                border-radius:5px;
            }
            QScrollBar::handle:vertical:hover {
                background:#94A3B8;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0;
            }
        """)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("SaleFooter")
        footer.setStyleSheet("""
            QFrame#SaleFooter {
                background:#FFFFFF;
                border:none;
                border-top:1px solid #E4EBF4;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(22, 14, 22, 14)
        footer_layout.setSpacing(10)

        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(42)
        cancel_button.setStyleSheet(self._secondary_button_style())
        cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Enregistrer la vente")
        self.save_button.setFixedHeight(42)
        self.save_button.setStyleSheet(self._primary_button_style())
        self.save_button.clicked.connect(self._save)

        footer_layout.addStretch()
        footer_layout.addWidget(cancel_button)
        footer_layout.addWidget(self.save_button)
        root.addWidget(footer)

        self.prospect_combo.currentIndexChanged.connect(self._update_preview)
        self.training_combo.currentIndexChanged.connect(self._update_preview)
        self._load_data()

    @staticmethod
    def _field_block(label_text, field):
        block = QWidget()
        block.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet(
            "font-size:11px; font-weight:800; color:#53657C; "
            "background:transparent; border:none;"
        )
        layout.addWidget(label)
        layout.addWidget(field)
        return block

    @staticmethod
    def _style_input(widget):
        widget.setFixedHeight(48)
        widget.setStyleSheet("""
            QComboBox {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 34px 0 12px;
                font-size:12px;
                font-weight:700;
            }
            QComboBox:focus {
                border:2px solid #338CE4;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                border:none;
                border-left:1px solid #E6EDF5;
                width:30px;
                background:#F8FBFF;
                border-top-right-radius:9px;
                border-bottom-right-radius:9px;
            }
            QComboBox QAbstractItemView {
                background:#FFFFFF;
                color:#172033;
                selection-background-color:#EAF4FF;
                selection-color:#0B1220;
                border:1px solid #DCE5EF;
                outline:0;
                padding:5px;
            }
        """)

    @staticmethod
    def _style_date(widget):
        widget.setFixedHeight(48)
        widget.setStyleSheet("""
            QDateEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 38px 0 12px;
                font-size:12px;
                font-weight:700;
            }
            QDateEdit:focus {
                border:2px solid #338CE4;
            }
            QDateEdit::drop-down {
                width:34px;
                border:none;
                border-left:1px solid #E6EDF5;
                background:#F8FBFF;
                border-top-right-radius:9px;
                border-bottom-right-radius:9px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background:#0B2A52;
            }
            QCalendarWidget QToolButton {
                color:#FFFFFF;
                background:transparent;
                border:none;
                font-weight:900;
                padding:7px;
            }
            QCalendarWidget QToolButton:hover {
                background:#123966;
                border-radius:8px;
            }
            QCalendarWidget QSpinBox {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:7px;
                padding:4px 6px;
                font-weight:800;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background:#FFFFFF;
                color:#334155;
                selection-background-color:#338CE4;
                selection-color:#FFFFFF;
                outline:0;
                font-size:12px;
            }
        """)

    @staticmethod
    def _primary_button_style():
        return """
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 18px;
                font-size:12px;
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
                padding:0 16px;
                font-size:12px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """

    @staticmethod
    def _format_euro(cents: int) -> str:
        return f"{int(cents) / 100:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _format_rate(value) -> str:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        return f"{number:g} %"

    def _load_data(self) -> None:
        page = self.api.list_prospects(
            pipeline_stage="gagne",
            limit=500,
            offset=0,
            sort_by="company_name",
            sort_direction="asc",
        )
        self.prospects = list(page.items)
        self.trainings = self.api.list_document_trainings(
            include_inactive=False
        )

        for prospect in self.prospects:
            company = str(prospect.get("company_name") or "Prospect").strip()
            contact = str(prospect.get("contact_name") or "").strip()
            city = str(prospect.get("city") or "").strip()
            details = " — ".join(part for part in (contact, city) if part)
            label = company + (f" ({details})" if details else "")
            self.prospect_combo.addItem(label, prospect)

        for training in self.trainings:
            label = (
                f"{training.get('reference') or ''} — "
                f"{training.get('name') or ''} — "
                f"{self._format_euro(int(training.get('price_cents') or 0))}"
            )
            self.training_combo.addItem(label, training)

        has_data = bool(self.prospects and self.trainings)
        self.save_button.setEnabled(has_data)

        if not self.prospects:
            self.preview.setText(
                "Aucun client disponible. Transformez d’abord un prospect en client depuis le CRM."
            )
        elif not self.trainings:
            self.preview.setText(
                "Aucune formation active. L'administrateur doit compléter le catalogue."
            )
        else:
            self._update_preview()

    def _update_preview(self) -> None:
        prospect = self.prospect_combo.currentData()
        training = self.training_combo.currentData()

        if not isinstance(prospect, dict) or not isinstance(training, dict):
            self.preview.setText("Sélectionnez un client et une formation.")
            self.save_button.setEnabled(False)
            return

        prospect_id = str(prospect.get("id") or "").strip()
        training_id = str(training.get("id") or "").strip()
        if not prospect_id or not training_id:
            self.preview.setText("Données de vente incomplètes.")
            self.save_button.setEnabled(False)
            return

        self.preview.setText("Calcul de la commission Cloud…")
        self.save_button.setEnabled(False)

        try:
            result = self.api.preview_cloud_sale_commission(
                {
                    "prospect_id": prospect_id,
                    "training_id": training_id,
                }
            )
        except CloudAPIError as exc:
            self.preview.setText(f"Aperçu indisponible : {exc}")
            self.save_button.setEnabled(False)
            return

        price_cents = int(result.get("price_cents") or 0)
        try:
            rate = float(result.get("commission_rate") or 0)
        except (TypeError, ValueError):
            rate = 0.0
        commission_cents = int(result.get("commission_cents") or 0)

        if rate <= 0:
            self.preview.setText(
                f"Prix : {self._format_euro(price_cents)}  •  "
                "Taux non configuré — vente impossible"
            )
            self.save_button.setEnabled(False)
            return

        beneficiary_type = str(
            result.get("commission_beneficiary_type") or "commercial"
        )
        beneficiary_name = str(
            result.get("commission_beneficiary_name") or ""
        ).strip()

        if beneficiary_type == "commercial_partner":
            commission_label = "Commission partenaire"
            beneficiary_suffix = (
                f"   •   Bénéficiaire : {beneficiary_name}"
                if beneficiary_name
                else ""
            )
        else:
            commission_label = "Commission"
            beneficiary_suffix = ""

        self.preview.setText(
            f"Prix signé : {self._format_euro(price_cents)}   •   "
            f"{commission_label} : {self._format_rate(rate)}   •   "
            f"Montant potentiel : {self._format_euro(commission_cents)}"
            f"{beneficiary_suffix}"
        )
        self.save_button.setEnabled(bool(self.prospects and self.trainings))

    def _save(self) -> None:
        prospect = self.prospect_combo.currentData()
        training = self.training_combo.currentData()

        if not isinstance(prospect, dict):
            QMessageBox.warning(self, "Prospect", "Sélectionnez un prospect.")
            return

        if not isinstance(training, dict):
            QMessageBox.warning(self, "Formation", "Sélectionnez une formation.")
            return

        qdate = self.date_edit.date()
        signed_at = date(qdate.year(), qdate.month(), qdate.day())

        if signed_at > date.today():
            QMessageBox.warning(
                self,
                "Date de signature",
                "La date de signature ne peut pas être postérieure à aujourd'hui.",
            )
            return

        try:
            self.api.create_cloud_sale(
                {
                    "prospect_id": str(prospect.get("id") or ""),
                    "training_id": str(training.get("id") or ""),
                    "signed_at": signed_at.isoformat(),
                    "notes": self.notes.toPlainText().strip(),
                }
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Vente non enregistrée", str(exc))
            return

        QMessageBox.information(
            self,
            "Vente enregistrée",
            "La vente a été enregistrée dans le Cloud à la date de signature de la convention. "
            "La commission est créée « En attente » pour 15 jours et ne sera validée que si le paiement client est encaissé.",
        )
        self.accept()
