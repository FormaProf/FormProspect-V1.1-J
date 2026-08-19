from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.premium_theme import BORDER, CARD, MUTED, PAGE_BG, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from services.training_case_service import TrainingCaseService
from ui.dialogs.cloud_quote_request_dialog import CloudQuoteRequestDialog
from ui.dialogs.generate_documents_dialog import CloudAdministrativeUploadDialog
from ui.dialogs.quote_request_dialog import QuoteRequestDialog


class TrainingCasesPage(QWidget):
    """Devis, factures et demandes de documents Cloud, avec conservation du mode local."""

    COMMERCIAL_DOCUMENT_TYPES = {"Devis", "Facture"}

    def __init__(self):
        super().__init__()
        self.service: TrainingCaseService | None = None
        self.case_rows: list[dict] = []
        self.quote_rows: list[dict] = []

        self.cloud_prospects: list[dict] = []
        self.cloud_trainings: list[dict] = []
        self.cloud_documents: list[dict] = []
        self.cloud_visible_documents: list[dict] = []
        self.cloud_quote_requests: list[dict] = []
        self.cloud_visible_quote_requests: list[dict] = []
        self.cloud_prospect_names: dict[str, str] = {}
        self.cloud_training_names: dict[str, str] = {}

        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("CommercialDocumentCard")
        card.setStyleSheet(
            "QFrame#CommercialDocumentCard{"
            "background:#FFFFFF;"
            "border:1px solid #E4EBF4;"
            "border-radius:18px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        return card

    @staticmethod
    def _input_style() -> str:
        return (
            "QLineEdit,QComboBox{"
            "background:#FFFFFF;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 11px;min-height:38px;"
            "font-size:11px;font-weight:700;"
            "}"
            "QLineEdit:focus,QComboBox:focus{border:2px solid #338CE4;}"
            "QComboBox::drop-down{border:none;border-left:1px solid #E6EDF5;"
            "width:28px;background:#F8FBFF;}"
        )

    @staticmethod
    def _table_style(table: QTableWidget) -> None:
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.horizontalHeader().setMinimumHeight(40)
        table.setStyleSheet(
            "QTableWidget{"
            "background:#FFFFFF;color:#172033;"
            "border:1px solid #E4EBF4;border-radius:12px;"
            "selection-background-color:#EAF4FF;"
            "selection-color:#0B1220;font-size:10px;"
            "}"
            "QTableWidget::item{"
            "background:#FFFFFF;border-bottom:1px solid #EEF3F8;"
            "padding:7px 8px;"
            "}"
            "QTableWidget::item:selected{background:#EAF4FF;color:#0B1220;}"
            "QHeaderView::section{"
            "background:#0B2A52;color:#FFFFFF;border:none;"
            "border-right:1px solid #173C68;padding:9px 8px;"
            "font-size:10px;font-weight:900;"
            "}"
        )

    @staticmethod
    def _type_badge_style(document_type: str) -> str:
        if str(document_type).lower() == "facture":
            return (
                "background:#ECFDF5;color:#047857;border:1px solid #A7F3D0;"
                "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
            )
        return (
            "background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE;"
            "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        )

    @staticmethod
    def _status_badge_style(status: str) -> str:
        value = str(status or "").lower()
        if any(word in value for word in ("disponible", "available")):
            return "background:#ECFDF5;color:#047857;border:1px solid #A7F3D0;border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        if any(word in value for word in ("préparation", "preparing")):
            return "background:#FFF7ED;color:#C2410C;border:1px solid #FED7AA;border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        if any(word in value for word in ("refus", "rejected", "erreur", "failed")):
            return "background:#FEF2F2;color:#B42318;border:1px solid #FECACA;border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        if any(word in value for word in ("annul", "cancelled", "archiv", "remplac")):
            return "background:#F8FAFC;color:#64748B;border:1px solid #E2E8F0;border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        return "background:#F5F3FF;color:#6D28D9;border:1px solid #DDD6FE;border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"

    @staticmethod
    def _format_price(cents) -> str:
        try:
            value = int(cents or 0) / 100
        except (TypeError, ValueError):
            value = 0
        return f"{value:,.2f} €".replace(",", " ").replace(".00", "")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(14)

        header_card = QFrame()
        header_card.setObjectName("CommercialDocsHeader")
        header_card.setStyleSheet(
            "QFrame#CommercialDocsHeader{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #FFFFFF, stop:0.72 #F8FBFF, stop:1 #EAF4FF);"
            "border:1px solid #E4EBF4;border-radius:20px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        header = QHBoxLayout(header_card)
        header.setContentsMargins(22, 18, 22, 18)
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        eyebrow = QLabel("COMMERCIAL  •  DOCUMENTS FINANCIERS")
        eyebrow.setStyleSheet(
            "color:#338CE4;font-size:10px;font-weight:900;letter-spacing:1.1px;"
        )

        self.title = QLabel("Devis & factures")
        self.title.setStyleSheet(
            "font-size:28px;font-weight:900;color:#0B1220;"
        )

        self.subtitle = QLabel(
            "Consultez les documents commerciaux et transmettez vos demandes de devis ou de facture."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color:#6B7A90;font-size:11px;")

        title_box.addWidget(eyebrow)
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box, 1)

        self.header_refresh = QPushButton("Actualiser")
        self.header_refresh.setMinimumHeight(40)
        self.header_refresh.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 15px;font-size:11px;font-weight:850;}"
            "QPushButton:hover{background:#F8FBFF;color:#338CE4;border-color:#AFCFF0;}"
        )
        self.header_refresh.clicked.connect(self.rafraichir)
        header.addWidget(self.header_refresh)

        root.addWidget(header_card)

        self.cloud_content = self._build_cloud_content()
        root.addWidget(self.cloud_content, 1)
        self.cloud_content.setVisible(False)

        self.local_content = self._build_local_content()
        root.addWidget(self.local_content, 1)
        self.local_content.setVisible(False)

        self.info_state = QLabel("")
        self.info_state.setAlignment(Qt.AlignCenter)
        self.info_state.setWordWrap(True)
        self.info_state.setMinimumHeight(140)
        self.info_state.setStyleSheet(
            "background:#FFFFFF;color:#64748B;border:1px dashed #D7E2EE;"
            "border-radius:16px;padding:18px;"
        )
        root.addWidget(self.info_state, 1)
        self.info_state.setVisible(False)

    # ------------------------------------------------------------------
    # Cloud
    # ------------------------------------------------------------------
    def _build_cloud_content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        info = QFrame()
        info.setObjectName("CommercialDocsInfo")
        info.setStyleSheet(
            "QFrame#CommercialDocsInfo{background:#F4F9FF;border:1px solid #DDEBFA;"
            "border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(10)

        info_icon = QLabel("i")
        info_icon.setFixedSize(28, 28)
        info_icon.setAlignment(Qt.AlignCenter)
        info_icon.setStyleSheet(
            "background:#338CE4;color:white;border-radius:14px;"
            "font-size:12px;font-weight:900;"
        )

        info_text = QLabel(
            "Demandez un devis ou une facture depuis cet espace. "
            "Une fois le document déposé dans le Cloud privé, vous pouvez le télécharger ici."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color:#64748B;font-size:10px;")

        info_layout.addWidget(info_icon, 0, Qt.AlignTop)
        info_layout.addWidget(info_text, 1)
        layout.addWidget(info)

        self.cloud_tabs = QTabWidget()
        self.cloud_tabs.setDocumentMode(True)
        self.cloud_tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #E4EBF4;border-radius:16px;"
            "background:#FFFFFF;top:-1px;}"
            "QTabBar::tab{background:transparent;color:#64748B;border:none;"
            "padding:10px 18px;margin-right:4px;font-size:11px;font-weight:800;}"
            "QTabBar::tab:selected{background:#0B2A52;color:#FFFFFF;"
            "border-radius:10px;}"
            "QTabBar::tab:hover:!selected{color:#338CE4;background:#F4F9FF;"
            "border-radius:10px;}"
        )
        self.cloud_tabs.addTab(self._build_cloud_documents_tab(), "Devis & factures")
        self.cloud_tabs.addTab(self._build_cloud_requests_tab(), "Demandes de documents")
        layout.addWidget(self.cloud_tabs, 1)
        return page

    def _build_cloud_documents_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:#FFFFFF;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        eyebrow = QLabel("BIBLIOTHÈQUE COMMERCIALE")
        eyebrow.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        title = QLabel("Documents disponibles")
        title.setStyleSheet("color:#0B1220;font-size:16px;font-weight:900;")
        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        top.addLayout(title_box)
        top.addStretch()

        self.cloud_count_badge = QLabel("0 document")
        self.cloud_count_badge.setAlignment(Qt.AlignCenter)
        self.cloud_count_badge.setMinimumWidth(92)
        self.cloud_count_badge.setFixedHeight(28)
        self.cloud_count_badge.setStyleSheet(
            "background:#EAF4FF;color:#0B5EA8;border:1px solid #BFDDFC;"
            "border-radius:9px;padding:0 10px;font-size:10px;font-weight:900;"
        )
        top.addWidget(self.cloud_count_badge)
        layout.addLayout(top)

        filters = QFrame()
        filters.setObjectName("CommercialDocsFilters")
        filters.setStyleSheet(
            "QFrame#CommercialDocsFilters{background:#F8FBFF;"
            "border:1px solid #E4EBF4;border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(14, 12, 14, 12)
        filters_layout.setSpacing(8)

        filters_title = QLabel("FILTRES")
        filters_title.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        filters_layout.addWidget(filters_title)

        tools = QHBoxLayout()
        tools.setSpacing(9)

        self.cloud_search = QLineEdit()
        self.cloud_search.setPlaceholderText(
            "Rechercher un client, un numéro, une formation ou un fichier…"
        )
        self.cloud_search.setStyleSheet(self._input_style())
        self.cloud_search.textChanged.connect(self._apply_cloud_filters)
        tools.addWidget(self.cloud_search, 1)

        self.cloud_type_combo = QComboBox()
        self.cloud_type_combo.addItem("Tous les documents", "")
        self.cloud_type_combo.addItem("Devis", "Devis")
        self.cloud_type_combo.addItem("Factures", "Facture")
        self.cloud_type_combo.setMinimumWidth(150)
        self.cloud_type_combo.setStyleSheet(self._input_style())
        self.cloud_type_combo.currentIndexChanged.connect(self._apply_cloud_filters)
        tools.addWidget(self.cloud_type_combo)

        self.cloud_prospect_combo = QComboBox()
        self.cloud_prospect_combo.setMinimumWidth(210)
        self.cloud_prospect_combo.setMaximumWidth(300)
        self.cloud_prospect_combo.setStyleSheet(self._input_style())
        self.cloud_prospect_combo.currentIndexChanged.connect(self._load_cloud_documents)
        tools.addWidget(self.cloud_prospect_combo)

        self.cloud_history_check = QCheckBox("Historique")
        self.cloud_history_check.setStyleSheet(
            "QCheckBox{color:#53657C;font-size:10px;font-weight:750;spacing:6px;}"
            "QCheckBox::indicator{width:15px;height:15px;}"
        )
        self.cloud_history_check.toggled.connect(self._load_cloud_documents)
        tools.addWidget(self.cloud_history_check)

        self.cloud_download_button = QPushButton("Télécharger")
        self.cloud_download_button.setMinimumHeight(38)
        self.cloud_download_button.setEnabled(False)
        self.cloud_download_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:9px;"
            "padding:0 14px;font-size:11px;font-weight:900;}"
            "QPushButton:hover{background:#247BD0;}"
            "QPushButton:disabled{background:#DCE6F0;color:#94A3B8;}"
        )
        self.cloud_download_button.clicked.connect(self._download_cloud_document)
        tools.addWidget(self.cloud_download_button)

        self.cloud_upload_button = QPushButton("Déposer un devis / une facture")
        self.cloud_upload_button.setMinimumHeight(38)
        self.cloud_upload_button.setStyleSheet(PRIMARY_BUTTON)
        self.cloud_upload_button.clicked.connect(self._upload_cloud_document)
        tools.addWidget(self.cloud_upload_button)

        filters_layout.addLayout(tools)
        layout.addWidget(filters)

        status_row = QHBoxLayout()
        self.cloud_status = QLabel("")
        self.cloud_status.setWordWrap(True)
        self.cloud_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
        )
        status_row.addWidget(self.cloud_status)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.cloud_table = QTableWidget(0, 8)
        self.cloud_table.setHorizontalHeaderLabels(
            ["Type", "Numéro", "Client", "Formation", "Fichier", "Statut", "Version", "Créé le"]
        )
        self._table_style(self.cloud_table)
        header = self.cloud_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)


        # Proportions premium — onglet Devis factures.
        # Type et Statut gardent assez de largeur pour afficher les badges complets.
        cloud_header = self.cloud_table.horizontalHeader()
        cloud_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        cloud_header.setSectionResizeMode(0, QHeaderView.Fixed)      # Type
        cloud_header.setSectionResizeMode(1, QHeaderView.Fixed)      # Numéro
        cloud_header.setSectionResizeMode(2, QHeaderView.Fixed)      # Client
        cloud_header.setSectionResizeMode(3, QHeaderView.Stretch)    # Formation
        cloud_header.setSectionResizeMode(4, QHeaderView.Stretch)    # Fichier
        cloud_header.setSectionResizeMode(5, QHeaderView.Fixed)      # Statut
        cloud_header.setSectionResizeMode(6, QHeaderView.Fixed)      # Version
        cloud_header.setSectionResizeMode(7, QHeaderView.Fixed)      # Créé le

        self.cloud_table.setColumnWidth(0, 96)
        self.cloud_table.setColumnWidth(1, 82)
        self.cloud_table.setColumnWidth(2, 150)
        self.cloud_table.setColumnWidth(5, 145)
        self.cloud_table.setColumnWidth(6, 78)
        self.cloud_table.setColumnWidth(7, 122)

        self.cloud_table.itemDoubleClicked.connect(
            lambda _item: self._download_cloud_document()
        )
        self.cloud_table.itemSelectionChanged.connect(
            lambda: self.cloud_download_button.setEnabled(
                self.cloud_table.currentRow() >= 0
            )
        )
        layout.addWidget(self.cloud_table, 1)
        return page

    def _build_cloud_requests_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:#FFFFFF;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        eyebrow = QLabel("SUIVI DES DEMANDES")
        eyebrow.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        title = QLabel("Demandes de documents")
        title.setStyleSheet("color:#0B1220;font-size:16px;font-weight:900;")
        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        top.addLayout(title_box)
        top.addStretch()

        self.cloud_request_count_badge = QLabel("0 demande")
        self.cloud_request_count_badge.setAlignment(Qt.AlignCenter)
        self.cloud_request_count_badge.setMinimumWidth(92)
        self.cloud_request_count_badge.setFixedHeight(28)
        self.cloud_request_count_badge.setStyleSheet(
            "background:#F5F3FF;color:#6D28D9;border:1px solid #DDD6FE;"
            "border-radius:9px;padding:0 10px;font-size:10px;font-weight:900;"
        )
        top.addWidget(self.cloud_request_count_badge)
        layout.addLayout(top)

        filters = QFrame()
        filters.setObjectName("CommercialRequestsFilters")
        filters.setStyleSheet(
            "QFrame#CommercialRequestsFilters{background:#F8FBFF;"
            "border:1px solid #E4EBF4;border-radius:14px;}"
        )
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(14, 12, 14, 12)
        filters_layout.setSpacing(8)

        tools = QHBoxLayout()
        tools.setSpacing(9)

        self.cloud_request_search = QLineEdit()
        self.cloud_request_search.setPlaceholderText(
            "Rechercher un client, une formation, un demandeur ou une note…"
        )
        self.cloud_request_search.setStyleSheet(self._input_style())
        self.cloud_request_search.textChanged.connect(self._apply_cloud_quote_filters)
        tools.addWidget(self.cloud_request_search, 1)

        self.cloud_request_type_combo = QComboBox()
        self.cloud_request_type_combo.addItem("Tous les types", "")
        self.cloud_request_type_combo.addItem("Devis", "Devis")
        self.cloud_request_type_combo.addItem("Factures", "Facture")
        self.cloud_request_type_combo.setStyleSheet(self._input_style())
        self.cloud_request_type_combo.currentIndexChanged.connect(self._apply_cloud_quote_filters)
        tools.addWidget(self.cloud_request_type_combo)

        self.cloud_request_status_combo = QComboBox()
        self.cloud_request_status_combo.addItem("Tous les statuts", "")
        self.cloud_request_status_combo.addItem("À traiter", "pending")
        self.cloud_request_status_combo.addItem("En préparation", "preparing")
        self.cloud_request_status_combo.addItem("Document disponible", "available")
        self.cloud_request_status_combo.addItem("Refusée", "rejected")
        self.cloud_request_status_combo.addItem("Annulée", "cancelled")
        self.cloud_request_status_combo.setStyleSheet(self._input_style())
        self.cloud_request_status_combo.currentIndexChanged.connect(self._apply_cloud_quote_filters)
        tools.addWidget(self.cloud_request_status_combo)

        filters_layout.addLayout(tools)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.cloud_request_create_button = QPushButton("Demander un devis / une facture")
        self.cloud_request_create_button.setStyleSheet(PRIMARY_BUTTON)
        self.cloud_request_create_button.clicked.connect(self._create_cloud_quote_request)
        actions.addWidget(self.cloud_request_create_button)

        actions.addStretch()

        self.cloud_request_prepare_button = QPushButton("Mettre en préparation")
        self.cloud_request_prepare_button.setStyleSheet(SECONDARY_BUTTON)
        self.cloud_request_prepare_button.clicked.connect(
            lambda: self._update_cloud_quote_status("preparing")
        )
        actions.addWidget(self.cloud_request_prepare_button)

        self.cloud_request_upload_button = QPushButton("Déposer le document")
        self.cloud_request_upload_button.setStyleSheet(PRIMARY_BUTTON)
        self.cloud_request_upload_button.clicked.connect(self._upload_requested_quote)
        actions.addWidget(self.cloud_request_upload_button)

        self.cloud_request_reject_button = QPushButton("Refuser")
        self.cloud_request_reject_button.setStyleSheet(SECONDARY_BUTTON)
        self.cloud_request_reject_button.clicked.connect(
            lambda: self._update_cloud_quote_status("rejected")
        )
        actions.addWidget(self.cloud_request_reject_button)

        self.cloud_request_cancel_button = QPushButton("Annuler la demande")
        self.cloud_request_cancel_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#64748B;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:0 14px;min-height:36px;font-size:10px;font-weight:850;}"
            "QPushButton:hover{background:#FFF7F7;color:#B42318;border-color:#F3C7C7;}"
            "QPushButton:disabled{background:#F8FAFC;color:#B6C0CC;border-color:#E7EDF4;}"
        )
        self.cloud_request_cancel_button.setEnabled(False)
        self.cloud_request_cancel_button.clicked.connect(
            lambda: self._update_cloud_quote_status("cancelled")
        )
        actions.addWidget(self.cloud_request_cancel_button)

        filters_layout.addLayout(actions)
        layout.addWidget(filters)

        self.cloud_request_status = QLabel("")
        self.cloud_request_status.setWordWrap(True)
        self.cloud_request_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
        )
        layout.addWidget(self.cloud_request_status)

        self.cloud_request_table = QTableWidget(0, 10)
        self.cloud_request_table.setHorizontalHeaderLabels(
            [
                "Type",
                "Client",
                "Formation",
                "Prix",
                "Demandeur",
                "Commercial",
                "Note",
                "Statut",
                "Document",
                "Créée le",
            ]
        )

        # Pour un commercial, la colonne "Commercial" est redondante :
        # elle reste visible pour l'administrateur / manager.
        role = self._current_role()
        self._hide_request_commercial_column = role == "commercial"
        self.cloud_request_table.setColumnHidden(
            5, self._hide_request_commercial_column
        )
        self._table_style(self.cloud_request_table)
        request_header = self.cloud_request_table.horizontalHeader()
        request_header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Répartition premium : le type et le statut doivent rester parfaitement lisibles.
        request_header.setSectionResizeMode(0, QHeaderView.Fixed)      # Type
        request_header.setSectionResizeMode(1, QHeaderView.Fixed)      # Client
        request_header.setSectionResizeMode(2, QHeaderView.Stretch)    # Formation
        request_header.setSectionResizeMode(6, QHeaderView.Stretch)    # Note
        request_header.setSectionResizeMode(7, QHeaderView.Fixed)      # Statut

        self.cloud_request_table.setColumnWidth(0, 96)
        self.cloud_request_table.setColumnWidth(1, 150)
        self.cloud_request_table.setColumnWidth(3, 82)
        self.cloud_request_table.setColumnWidth(4, 110)
        self.cloud_request_table.setColumnWidth(7, 160)
        self.cloud_request_table.setColumnWidth(8, 100)
        self.cloud_request_table.setColumnWidth(9, 120)
        self.cloud_request_table.itemDoubleClicked.connect(
            lambda _item: self._download_requested_quote()
        )
        self.cloud_request_table.itemSelectionChanged.connect(
            self._refresh_request_action_state
        )
        layout.addWidget(self.cloud_request_table, 1)
        return page

    def _refresh_request_action_state(self) -> None:
        """Adapte les actions au rôle, à la sélection et au statut courant."""
        if not hasattr(self, "cloud_request_table"):
            return

        row = self.cloud_request_table.currentRow()
        request = None

        if row >= 0:
            first_item = self.cloud_request_table.item(row, 0)
            request_id = str(first_item.data(Qt.UserRole) or "") if first_item else ""
            request = next(
                (
                    item
                    for item in self.cloud_quote_requests
                    if str(item.get("id") or "") == request_id
                ),
                None,
            )

        status = str((request or {}).get("status") or "").strip().lower()
        has_selection = request is not None

        # Un commercial peut annuler une demande tant qu'elle n'est pas finalisée.
        cancellable = has_selection and status in {"pending", "preparing"}
        if hasattr(self, "cloud_request_cancel_button"):
            self.cloud_request_cancel_button.setEnabled(cancellable)

        # Actions administratives uniquement lorsqu'elles ont du sens.
        role = self._current_role()
        is_admin_side = role in {"administrateur", "admin", "manager"}

        if hasattr(self, "cloud_request_prepare_button"):
            self.cloud_request_prepare_button.setVisible(is_admin_side)
            self.cloud_request_prepare_button.setEnabled(
                is_admin_side and has_selection and status == "pending"
            )

        if hasattr(self, "cloud_request_upload_button"):
            self.cloud_request_upload_button.setVisible(is_admin_side)
            self.cloud_request_upload_button.setEnabled(
                is_admin_side and has_selection and status in {"pending", "preparing"}
            )

        if hasattr(self, "cloud_request_reject_button"):
            self.cloud_request_reject_button.setVisible(is_admin_side)
            self.cloud_request_reject_button.setEnabled(
                is_admin_side and has_selection and status in {"pending", "preparing"}
            )

    def _project(self):
        try:
            return ApplicationState.get_project() if ApplicationState.has_project() else None
        except Exception:
            return None

    def _is_cloud(self) -> bool:
        project = self._project()
        if project is not None:
            try:
                return DataSourceResolver().resolve(project).is_cloud
            except Exception:
                pass
        return CloudRuntime.is_active()

    @staticmethod
    def _current_role() -> str:
        user = SessionState.user()
        return str(getattr(user, "role", "") or "").strip().lower()

    @staticmethod
    def _has_permission(permission: str) -> bool:
        user = SessionState.user()
        return permission in tuple(getattr(user, "permissions", ()) or ())

    def _can_admin_upload(self) -> bool:
        return self._current_role() in {"admin", "administrateur"} or self._has_permission(
            "document:upload"
        )

    def _can_create_quote_request(self) -> bool:
        return self._current_role() in {
            "admin",
            "administrateur",
            "manager",
            "commercial",
        } or self._has_permission("quote_request:create")

    def _can_manage_quote_requests(self) -> bool:
        return self._current_role() in {"admin", "administrateur"} or self._has_permission(
            "quote_request:manage"
        )

    def _load_cloud_mode(self) -> None:
        self.info_state.setVisible(False)
        self.local_content.setVisible(False)
        self.cloud_content.setVisible(True)
        self.subtitle.setText(
            "Consultez les devis et factures, et suivez les demandes de documents transmises à l'administrateur."
        )
        can_manage = self._can_manage_quote_requests()
        self.cloud_upload_button.setVisible(self._can_admin_upload())
        self.cloud_request_create_button.setVisible(self._can_create_quote_request())
        self.cloud_request_prepare_button.setVisible(can_manage)
        self.cloud_request_upload_button.setVisible(can_manage and self._can_admin_upload())
        self.cloud_request_reject_button.setVisible(can_manage)
        self.cloud_request_cancel_button.setVisible(not can_manage)

        api = CloudRuntime.api()
        selected_prospect_id = self.cloud_prospect_combo.currentData()
        try:
            visible = api.list_prospects(include_archived=False, limit=500).items
            self.cloud_prospects = [
                item for item in visible
                if str(item.get("pipeline_stage") or "") == "gagne"
            ]
            self.cloud_trainings = api.list_document_trainings(include_inactive=True)
        except CloudAPIError as exc:
            self.cloud_status.setText(f"⛔ {exc}")
            self.cloud_status.setStyleSheet("color:#B42318;")
            self.cloud_request_status.setText(f"⛔ {exc}")
            self.cloud_request_status.setStyleSheet("color:#B42318;")
            self.cloud_table.setRowCount(0)
            self.cloud_request_table.setRowCount(0)
            return

        self.cloud_prospect_names = {
            str(item.get("id") or ""): str(item.get("company_name") or "Client sans nom")
            for item in self.cloud_prospects
        }
        self.cloud_training_names = {
            str(item.get("id") or ""): str(item.get("name") or item.get("reference") or "Formation")
            for item in self.cloud_trainings
        }

        self.cloud_prospect_combo.blockSignals(True)
        self.cloud_prospect_combo.clear()
        self.cloud_prospect_combo.addItem("Tous les clients visibles", None)
        restore_index = 0
        for index, prospect in enumerate(self.cloud_prospects, start=1):
            prospect_id = str(prospect.get("id") or "")
            self.cloud_prospect_combo.addItem(
                str(prospect.get("company_name") or "Client sans nom"),
                prospect_id,
            )
            if selected_prospect_id and str(selected_prospect_id) == prospect_id:
                restore_index = index
        self.cloud_prospect_combo.setCurrentIndex(restore_index)
        self.cloud_prospect_combo.blockSignals(False)
        self._load_cloud_documents()
        self._load_cloud_quote_requests()

    def _load_cloud_documents(self, *_args) -> None:
        if not self._is_cloud() or not CloudRuntime.is_active():
            return
        prospect_id = self.cloud_prospect_combo.currentData()
        try:
            documents = CloudRuntime.api().list_cloud_documents(
                prospect_id=str(prospect_id) if prospect_id else None,
                include_history=self.cloud_history_check.isChecked(),
                include_archived=False,
                limit=500,
            )
        except CloudAPIError as exc:
            self.cloud_documents = []
            self.cloud_visible_documents = []
            self.cloud_table.setRowCount(0)
            self.cloud_status.setText(f"⛔ {exc}")
            self.cloud_status.setStyleSheet("color:#B42318;")
            return

        self.cloud_documents = [
            item for item in documents
            if str(item.get("document_type") or "") in self.COMMERCIAL_DOCUMENT_TYPES
        ]
        self._apply_cloud_filters()

    def _apply_cloud_filters(self, *_args) -> None:
        selected_type = str(self.cloud_type_combo.currentData() or "")
        query = self.cloud_search.text().strip().lower()
        visible: list[dict] = []

        for document in self.cloud_documents:
            document_type = str(document.get("document_type") or "")
            if selected_type and document_type != selected_type:
                continue
            prospect_name = self.cloud_prospect_names.get(
                str(document.get("prospect_id") or ""), "Client visible"
            )
            training_name = self.cloud_training_names.get(
                str(document.get("training_id") or ""), "—"
            )
            searchable = " ".join(
                [
                    document_type,
                    str(document.get("document_number") or ""),
                    prospect_name,
                    training_name,
                    str(document.get("original_filename") or ""),
                ]
            ).lower()
            if query and query not in searchable:
                continue
            visible.append(document)

        self.cloud_visible_documents = visible
        self.cloud_table.setRowCount(len(visible))
        for row_index, document in enumerate(visible):
            prospect_name = self.cloud_prospect_names.get(
                str(document.get("prospect_id") or ""), "Client visible"
            )
            training_name = self.cloud_training_names.get(
                str(document.get("training_id") or ""), "—"
            )
            created = str(document.get("created_at") or "").replace("T", " ")[:16]
            status_value = str(document.get("status") or "available")
            status_label = {
                "available": "Disponible",
                "superseded": "Remplacé",
                "archived": "Archivé",
                "failed": "Erreur",
            }.get(status_value, status_value)
            values = [
                document.get("document_type") or "—",
                document.get("document_number") or "—",
                prospect_name,
                training_name,
                document.get("original_filename") or "—",
                status_label,
                document.get("version") or 1,
                created or "—",
            ]
            self.cloud_table.setRowHeight(row_index, 44)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(Qt.UserRole, str(document.get("id") or ""))
                    self.cloud_table.setItem(row_index, column, item)
                    badge = QLabel(str(value))
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setFixedHeight(26)
                    badge.setStyleSheet(self._type_badge_style(str(value)))
                    self.cloud_table.setCellWidget(row_index, column, badge)
                    continue

                if column == 5:
                    self.cloud_table.setItem(row_index, column, item)
                    badge = QLabel(str(value))
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setFixedHeight(26)
                    badge.setStyleSheet(self._status_badge_style(str(value)))
                    self.cloud_table.setCellWidget(row_index, column, badge)
                    continue

                if column in (1, 6, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 2:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif column == 4:
                    item.setToolTip(str(value))

                self.cloud_table.setItem(row_index, column, item)

        if hasattr(self, "cloud_count_badge"):
            count = len(visible)
            self.cloud_count_badge.setText(
                f"{count} document" if count == 1 else f"{count} documents"
            )

        self.cloud_download_button.setEnabled(False)
        self.cloud_status.setText(
            f"{len(visible)} affiché(s) sur {len(self.cloud_documents)} disponible(s)  •  "
            "Double-cliquez pour télécharger"
        )
        self.cloud_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
        )

    def _load_cloud_quote_requests(self, *_args) -> None:
        if not self._is_cloud() or not CloudRuntime.is_active():
            return
        try:
            self.cloud_quote_requests = CloudRuntime.api().list_cloud_quote_requests()
        except CloudAPIError as exc:
            self.cloud_quote_requests = []
            self.cloud_visible_quote_requests = []
            self.cloud_request_table.setRowCount(0)
            self.cloud_request_status.setText(f"⛔ {exc}")
            self.cloud_request_status.setStyleSheet("color:#B42318;")
            return
        self._apply_cloud_quote_filters()

    def _apply_cloud_quote_filters(self, *_args) -> None:
        selected_type = str(self.cloud_request_type_combo.currentData() or "")
        selected_status = str(self.cloud_request_status_combo.currentData() or "")
        query = self.cloud_request_search.text().strip().lower()
        visible: list[dict] = []
        for request in self.cloud_quote_requests:
            if selected_type and str(request.get("document_type") or "Devis") != selected_type:
                continue
            if selected_status and str(request.get("status") or "") != selected_status:
                continue
            searchable = " ".join(
                [
                    str(request.get("document_type") or "Devis"),
                    str(request.get("client_name") or ""),
                    str(request.get("training_reference") or ""),
                    str(request.get("training_name") or ""),
                    str(request.get("requester_name") or ""),
                    str(request.get("commercial_name") or ""),
                    str(request.get("note") or ""),
                    str(request.get("display_status") or ""),
                ]
            ).lower()
            if query and query not in searchable:
                continue
            visible.append(request)

        self.cloud_visible_quote_requests = visible
        self.cloud_request_table.setRowCount(len(visible))
        for row_index, request in enumerate(visible):
            created = str(request.get("created_at") or "").replace("T", " ")[:16]
            values = [
                request.get("document_type") or "Devis",
                request.get("client_name") or "—",
                request.get("training_name") or "—",
                self._format_price(request.get("price_cents")),
                request.get("requester_name") or "—",
                request.get("commercial_name") or "—",
                request.get("note") or "—",
                request.get("display_status") or request.get("status") or "—",
                request.get("document_number") or ("Disponible" if request.get("document_id") else "—"),
                created or "—",
            ]
            self.cloud_request_table.setRowHeight(row_index, 44)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(Qt.UserRole, str(request.get("id") or ""))
                    self.cloud_request_table.setItem(row_index, column, item)
                    badge = QLabel(str(value))
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setFixedHeight(26)
                    badge.setStyleSheet(self._type_badge_style(str(value)))
                    self.cloud_request_table.setCellWidget(row_index, column, badge)
                    continue

                if column == 7:
                    self.cloud_request_table.setItem(row_index, column, item)
                    badge = QLabel(str(value))
                    badge.setAlignment(Qt.AlignCenter)
                    badge.setFixedHeight(26)
                    badge.setStyleSheet(self._status_badge_style(str(value)))
                    self.cloud_request_table.setCellWidget(row_index, column, badge)
                    continue

                if column in (3, 9):
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                if column in (2, 6, 8):
                    item.setToolTip(str(value))

                self.cloud_request_table.setItem(row_index, column, item)

        if hasattr(self, "cloud_request_count_badge"):
            count = len(visible)
            self.cloud_request_count_badge.setText(
                f"{count} demande" if count == 1 else f"{count} demandes"
            )

        self.cloud_request_status.setText(
            f"{len(visible)} affichée(s) sur {len(self.cloud_quote_requests)} demande(s)"
        )
        self.cloud_request_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
        )
        self.cloud_request_table.clearSelection()
        self._refresh_request_action_state()

    def _selected_cloud_document(self) -> dict | None:
        row = self.cloud_table.currentRow()
        if row < 0 or row >= len(self.cloud_visible_documents):
            QMessageBox.information(self, "Document", "Sélectionnez d'abord un devis ou une facture.")
            return None
        return self.cloud_visible_documents[row]

    def _selected_cloud_quote_request(self) -> dict | None:
        row = self.cloud_request_table.currentRow()
        if row < 0 or row >= len(self.cloud_visible_quote_requests):
            QMessageBox.information(self, "Demande", "Sélectionnez d'abord une demande de document.")
            return None
        return self.cloud_visible_quote_requests[row]

    def _download_document_by_id(self, document_id: str, filename: str) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Télécharger le document",
            filename or "document",
            "Tous les fichiers (*.*)",
        )
        if not destination:
            return
        try:
            saved = CloudRuntime.api().download_cloud_document(document_id, destination)
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Téléchargement impossible", str(exc))
            return
        answer = QMessageBox.question(
            self,
            "Document téléchargé",
            f"Le document a été enregistré ici :\n{saved}\n\nL'ouvrir maintenant ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(saved)))

    def _download_cloud_document(self, *_args) -> None:
        document = self._selected_cloud_document()
        if document:
            self._download_document_by_id(
                str(document.get("id") or ""),
                str(document.get("original_filename") or "document"),
            )

    def _download_requested_quote(self, *_args) -> None:
        request = self._selected_cloud_quote_request()
        if not request:
            return
        document_id = str(request.get("document_id") or "")
        if not document_id:
            QMessageBox.information(
                self,
                "Document indisponible",
                "L'administrateur n'a pas encore déposé le document pour cette demande.",
            )
            return
        document_type = str(request.get("document_type") or "Devis")
        base_name = "facture" if document_type == "Facture" else "devis"
        filename = f"{request.get('document_number') or base_name}_{request.get('client_name') or 'client'}.pdf"
        self._download_document_by_id(document_id, filename)

    def _upload_cloud_document(self) -> None:
        if not self._can_admin_upload():
            return
        prospect_id = self.cloud_prospect_combo.currentData()
        dialog = CloudAdministrativeUploadDialog(
            CloudRuntime.api(),
            self,
            initial_prospect_id=str(prospect_id) if prospect_id else None,
            allowed_document_types=("Devis", "Facture"),
            initial_document_type=str(self.cloud_type_combo.currentData() or "") or "Devis",
        )
        if dialog.exec():
            self._load_cloud_documents()

    def _apply_quote_request_dialog_premium(self, dialog) -> None:
        """Modernise visuellement la demande de devis/facture sans toucher à sa logique."""
        dialog.resize(800, 650)
        dialog.setMinimumSize(740, 590)
        dialog.setStyleSheet(
            "QDialog{background:#F5F8FC;}"
            "QLabel{background:transparent;border:none;color:#53657C;}"
            "QComboBox,QLineEdit{"
            "background:#FFFFFF;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 11px;min-height:40px;"
            "font-size:11px;font-weight:700;"
            "}"
            "QComboBox:focus,QLineEdit:focus{border:2px solid #338CE4;}"
            "QComboBox::drop-down{"
            "border:none;border-left:1px solid #E6EDF5;width:30px;background:#F8FBFF;"
            "}"
            "QTextEdit{"
            "background:#FFFFFF;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:12px;padding:10px;font-size:11px;"
            "selection-background-color:#D9ECFF;"
            "}"
            "QTextEdit:focus{border:2px solid #338CE4;}"
            "QFrame{border-radius:16px;}"
        )

        # Cartes existantes du dialogue : blanches et beaucoup plus aérées.
        for frame in dialog.findChildren(QFrame):
            if frame is dialog:
                continue
            frame.setStyleSheet(
                "QFrame{background:#FFFFFF;border:1px solid #E4EBF4;"
                "border-radius:16px;}"
                "QLabel{background:transparent;border:none;}"
            )

        # Titres / textes selon leur contenu actuel.
        for label in dialog.findChildren(QLabel):
            content = label.text().strip()

            if content.startswith("Nouvelle demande"):
                label.setStyleSheet(
                    "color:#0B1220;font-size:25px;font-weight:900;"
                    "background:transparent;border:none;"
                )
            elif "Sélectionnez le type de document" in content:
                label.setStyleSheet(
                    "color:#6B7A90;font-size:11px;"
                    "background:transparent;border:none;"
                )
            elif content.startswith("DOCUMENT DEMANDÉ"):
                label.setStyleSheet(
                    "background:#F4F9FF;color:#0B2A52;"
                    "border:1px solid #CFE3F7;border-radius:14px;"
                    "padding:14px 16px;font-size:11px;font-weight:800;"
                )
            else:
                label.setStyleSheet(
                    "color:#53657C;font-size:10px;font-weight:750;"
                    "background:transparent;border:none;"
                )

        for edit in dialog.findChildren(QTextEdit):
            edit.setMinimumHeight(120)

        # Boutons : secondaire pour Annuler, bleu premium pour l'envoi.
        for button in dialog.findChildren(QPushButton):
            caption = button.text().strip().lower()
            button.setMinimumHeight(40)

            if "envoyer" in caption:
                button.setMinimumWidth(176)
                button.setMinimumHeight(46)
                button.setCursor(Qt.PointingHandCursor)
                button.setStyleSheet(
                    "QPushButton{"
                    "background:#338CE4;color:#FFFFFF;border:1px solid #338CE4;"
                    "border-radius:12px;padding:0 22px;font-size:11px;font-weight:900;"
                    "}"
                    "QPushButton:hover{background:#287FD4;border-color:#287FD4;}"
                    "QPushButton:pressed{background:#1E6DBA;border-color:#1E6DBA;"
                    "padding-top:1px;}"
                    "QPushButton:disabled{background:#DCE6F0;color:#94A3B8;"
                    "border-color:#DCE6F0;}"
                )
            elif "annuler" in caption:
                button.setMinimumWidth(118)
                button.setMinimumHeight(46)
                button.setCursor(Qt.PointingHandCursor)
                button.setStyleSheet(
                    "QPushButton{"
                    "background:#FFFFFF;color:#334155;"
                    "border:1px solid #CBD8E6;border-radius:12px;"
                    "padding:0 20px;font-size:11px;font-weight:850;"
                    "}"
                    "QPushButton:hover{background:#F4F9FF;color:#247BD0;"
                    "border-color:#8DBCEB;}"
                    "QPushButton:pressed{background:#EAF4FE;"
                    "border-color:#6FAAE4;padding-top:1px;}"
                )

    def _create_cloud_quote_request(self) -> None:
        current_prospect = self.cloud_prospect_combo.currentData()
        dialog = CloudQuoteRequestDialog(
            CloudRuntime.api(),
            self.cloud_prospects,
            self.cloud_trainings,
            self,
            initial_prospect_id=str(current_prospect) if current_prospect else None,
            initial_document_type=str(self.cloud_request_type_combo.currentData() or "") or "Devis",
        )
        self._apply_quote_request_dialog_premium(dialog)
        if dialog.exec():
            self.cloud_tabs.setCurrentIndex(1)
            self._load_cloud_quote_requests()

    def _update_cloud_quote_status(self, request_status: str) -> None:
        request = self._selected_cloud_quote_request()
        if not request:
            return
        labels = {
            "preparing": "mettre cette demande en préparation",
            "rejected": "refuser cette demande",
            "cancelled": "annuler cette demande",
        }
        if QMessageBox.question(
            self,
            "Confirmer",
            f"Voulez-vous {labels.get(request_status, 'modifier cette demande')} ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            CloudRuntime.api().update_cloud_quote_request_status(
                str(request.get("id") or ""),
                request_status=request_status,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))
            return
        self._load_cloud_quote_requests()

    def _upload_requested_quote(self) -> None:
        request = self._selected_cloud_quote_request()
        if not request:
            return
        if str(request.get("status") or "") in {"rejected", "cancelled", "available"}:
            QMessageBox.information(
                self,
                "Demande clôturée",
                "Cette demande ne peut plus recevoir un nouveau document depuis ce bouton.",
            )
            return
        document_type = str(request.get("document_type") or "Devis")
        dialog = CloudAdministrativeUploadDialog(
            CloudRuntime.api(),
            self,
            initial_prospect_id=str(request.get("prospect_id") or ""),
            allowed_document_types=(document_type,),
            initial_document_type=document_type,
        )
        if not dialog.exec():
            return
        document = dialog.uploaded_document or {}
        document_id = str(document.get("id") or "")
        if not document_id:
            QMessageBox.critical(
                self,
                "Association impossible",
                "Le document a été déposé mais son identifiant Cloud n'a pas été retourné.",
            )
            return
        try:
            CloudRuntime.api().attach_cloud_quote_document(
                str(request.get("id") or ""),
                document_id=document_id,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Association impossible", str(exc))
            return
        self._load_cloud_quote_requests()
        self._load_cloud_documents()
        QMessageBox.information(
            self,
            f"{document_type} disponible",
            f"Le {document_type.lower()} est maintenant disponible pour le commercial concerné.",
        )

    # ------------------------------------------------------------------
    # Local historical workflow
    # ------------------------------------------------------------------
    def _build_local_content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._cases_tab(), "Dossiers et devis")
        self.tabs.addTab(self._quotes_tab(), "Demandes de devis")
        return page

    def _cases_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher un client, une formation ou un commercial…")
        self.search.textChanged.connect(self._load_cases)

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)

        self.download_btn = QPushButton("Télécharger le devis")
        self.download_btn.setStyleSheet(SECONDARY_BUTTON)
        self.download_btn.clicked.connect(self._download_case_quote)

        self.delete_case_btn = QPushButton("Supprimer le dossier")
        self.delete_case_btn.setStyleSheet(SECONDARY_BUTTON)
        self.delete_case_btn.clicked.connect(self._delete_case)
        self.delete_case_btn.setVisible(SessionState.has_role("Administrateur"))

        self.request_btn = QPushButton("Demander un devis")
        self.request_btn.setStyleSheet(PRIMARY_BUTTON)
        self.request_btn.clicked.connect(self._request_quote)

        tools.addWidget(self.search, 1)
        tools.addWidget(refresh)
        tools.addWidget(self.download_btn)
        tools.addWidget(self.delete_case_btn)
        tools.addWidget(self.request_btn)
        layout.addLayout(tools)

        self.case_table = QTableWidget(0, 9)
        self.case_table.setHorizontalHeaderLabels(
            [
                "Client",
                "Formation",
                "Dates",
                "Modalité",
                "Participants",
                "Commercial",
                "Financeur",
                "Étape",
                "Devis",
            ]
        )
        self.case_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.case_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.case_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.case_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.case_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.case_table.itemDoubleClicked.connect(lambda _item: self._download_case_quote())
        layout.addWidget(self.case_table, 1)
        return page

    def _quotes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)

        tools = QHBoxLayout()
        tools.addStretch()
        self.status_combo = QComboBox()
        self.status_combo.addItems(TrainingCaseService.QUOTE_STATUSES)

        self.download_quote_btn = QPushButton("Télécharger le PDF")
        self.download_quote_btn.setStyleSheet(SECONDARY_BUTTON)
        self.download_quote_btn.clicked.connect(self._download_selected_quote)

        self.status_btn = QPushButton("Mettre à jour le statut")
        self.status_btn.setStyleSheet(SECONDARY_BUTTON)
        self.status_btn.clicked.connect(self._update_status)

        self.import_btn = QPushButton("Importer le devis PDF")
        self.import_btn.setStyleSheet(PRIMARY_BUTTON)
        self.import_btn.clicked.connect(self._import_quote)

        is_admin = SessionState.has_role("Administrateur")
        self.status_combo.setVisible(is_admin)
        self.status_btn.setVisible(is_admin)
        self.import_btn.setVisible(is_admin)

        tools.addWidget(self.download_quote_btn)
        tools.addWidget(self.status_combo)
        tools.addWidget(self.status_btn)
        tools.addWidget(self.import_btn)
        layout.addLayout(tools)

        self.quote_table = QTableWidget(0, 8)
        self.quote_table.setHorizontalHeaderLabels(
            ["Client", "Formation", "Dates", "Demandeur", "Note", "Statut", "PDF", "Créée le"]
        )
        self.quote_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.quote_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.quote_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.quote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.quote_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.quote_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.quote_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.quote_table.itemDoubleClicked.connect(lambda _item: self._download_selected_quote())
        layout.addWidget(self.quote_table, 1)
        return page

    def _ensure_service(self) -> bool:
        if not ApplicationState.has_project():
            return False
        project = ApplicationState.get_project()
        db = getattr(project, "database", None) or getattr(project, "database_path", None)
        if db is None:
            QMessageBox.critical(
                self,
                "Projet incompatible",
                "Impossible de localiser la base de données du projet ouvert.",
            )
            return False
        db = Path(db)
        if not self.service or Path(self.service.database_path) != db:
            self.service = TrainingCaseService(db)
        return True

    def rafraichir(self) -> None:
        if self._is_cloud():
            if not CloudRuntime.is_active():
                self.cloud_content.setVisible(False)
                self.local_content.setVisible(False)
                self.info_state.setText(
                    "La session Form@Prospect Cloud n'est pas active. Reconnectez-vous pour accéder aux devis et factures."
                )
                self.info_state.setVisible(True)
                return
            self._load_cloud_mode()
            return

        self.cloud_content.setVisible(False)
        self.info_state.setVisible(False)
        self.local_content.setVisible(True)
        self.subtitle.setText(
            "Gestion locale des dossiers de formation et des demandes de devis."
        )
        if not self._ensure_service():
            self.local_content.setVisible(False)
            self.info_state.setText("Ouvrez un projet local pour accéder aux devis.")
            self.info_state.setVisible(True)
            return
        self._load_cases()
        self._load_quotes()

    def _load_cases(self, *_args) -> None:
        if self._is_cloud() or not self._ensure_service():
            return
        self.case_rows = self.service.list_cases(self.search.text() if hasattr(self, "search") else "")
        self.case_table.setRowCount(len(self.case_rows))
        for row_index, row in enumerate(self.case_rows):
            values = [
                row["company_name"],
                row["training_name"],
                f"{row['start_date']} → {row['end_date']}",
                row["modality"],
                str(row["participant_count"]),
                row["commercial_name"],
                row["funder"],
                f"{row['current_step']} ({row['progress_percent']} %)",
                row["quote_status"],
            ]
            for column, value in enumerate(values):
                self.case_table.setItem(row_index, column, QTableWidgetItem(str(value or "—")))

    def _load_quotes(self) -> None:
        if self._is_cloud() or not self._ensure_service():
            return
        self.quote_rows = self.service.list_quote_requests()
        self.quote_table.setRowCount(len(self.quote_rows))
        for row_index, row in enumerate(self.quote_rows):
            values = [
                row["company_name"],
                row["training_name"],
                f"{row['start_date']} → {row['end_date']}",
                row["requested_by"],
                row["note"],
                row["status"],
                "Disponible" if row["quote_file_path"] else "—",
                row["created_at"].replace("T", " "),
            ]
            for column, value in enumerate(values):
                self.quote_table.setItem(row_index, column, QTableWidgetItem(str(value or "—")))

    def _selected_case(self) -> dict | None:
        row = self.case_table.currentRow()
        return self.case_rows[row] if 0 <= row < len(self.case_rows) else None

    def _selected_quote(self) -> dict | None:
        row = self.quote_table.currentRow()
        return self.quote_rows[row] if 0 <= row < len(self.quote_rows) else None

    def _save_quote_copy(self, source: Path) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Télécharger le devis",
            source.name,
            "Documents PDF (*.pdf)",
        )
        if not target:
            return
        target_path = Path(target)
        if target_path.suffix.lower() != ".pdf":
            target_path = target_path.with_suffix(".pdf")
        try:
            if source.resolve() != target_path.resolve():
                shutil.copy2(source, target_path)
        except Exception as exc:
            QMessageBox.critical(self, "Téléchargement impossible", str(exc))
            return
        QMessageBox.information(self, "Devis téléchargé", f"Le devis a été enregistré dans :\n{target_path}")

    def _download_case_quote(self) -> None:
        case = self._selected_case()
        if not case:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez un dossier formation.")
            return
        request_id = case.get("quote_request_id")
        if not request_id or not case.get("quote_file_path"):
            QMessageBox.information(
                self,
                "Devis indisponible",
                "Aucun devis PDF n'a encore été importé pour ce dossier.",
            )
            return
        try:
            source = self.service.get_quote_file(int(request_id))
        except Exception as exc:
            QMessageBox.critical(self, "Devis indisponible", str(exc))
            return
        self._save_quote_copy(source)

    def _download_selected_quote(self) -> None:
        quote = self._selected_quote()
        if not quote:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez une demande de devis.")
            return
        try:
            source = self.service.get_quote_file(int(quote["id"]))
        except Exception as exc:
            QMessageBox.critical(self, "Devis indisponible", str(exc))
            return
        self._save_quote_copy(source)

    def _request_quote(self) -> None:
        case = self._selected_case()
        if not case:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez un dossier formation.")
            return
        dialog = QuoteRequestDialog(case, self)
        if dialog.exec():
            user = SessionState.user()
            requested_by = user.display_name if user else case.get("commercial_name", "")
            try:
                self.service.create_quote_request(
                    case["session_id"],
                    requested_by,
                    dialog.note.toPlainText(),
                )
            except Exception as exc:
                QMessageBox.critical(self, "Demande impossible", str(exc))
                return
            self.rafraichir()
            self.tabs.setCurrentIndex(1)
            QMessageBox.information(
                self,
                "Demande envoyée",
                "La demande de devis a été transmise à l'administrateur.",
            )

    def _update_status(self) -> None:
        if not SessionState.has_role("Administrateur"):
            return
        row = self._selected_quote()
        if not row:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez une demande.")
            return
        try:
            self.service.update_quote_status(row["id"], self.status_combo.currentText())
        except Exception as exc:
            QMessageBox.critical(self, "Mise à jour impossible", str(exc))
            return
        self.rafraichir()

    def _import_quote(self) -> None:
        if not SessionState.has_role("Administrateur"):
            return
        row = self._selected_quote()
        if not row:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez une demande.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importer le devis", "", "Documents PDF (*.pdf)")
        if not path:
            return
        try:
            target = self.service.import_quote_pdf(row["id"], path)
        except Exception as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return
        self.rafraichir()
        QMessageBox.information(self, "Devis disponible", f"Le devis a été archivé dans :\n{target}")

    def _delete_case(self) -> None:
        if not SessionState.has_role("Administrateur"):
            return
        case = self._selected_case()
        if not case:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez le dossier à supprimer.")
            return
        answer = QMessageBox.question(
            self,
            "Supprimer le dossier formation",
            f"Supprimer définitivement ce dossier ?\n\n"
            f"Client : {case['company_name']}\n"
            f"Formation : {case['training_name']}\n"
            f"Dates : {case['start_date']} → {case['end_date']}\n\n"
            "La fiche client ne sera pas supprimée. Les demandes de devis liées à ce dossier seront supprimées.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.service.delete_training_case(int(case["session_id"]))
        except Exception as exc:
            QMessageBox.critical(self, "Suppression impossible", str(exc))
            return
        self.rafraichir()
        QMessageBox.information(self, "Dossier supprimé", "Le dossier formation a bien été supprimé.")
