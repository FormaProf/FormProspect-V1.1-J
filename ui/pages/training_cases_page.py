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
    QScrollArea,
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
from core.theme_settings import get_theme_preference
from ui.training_cases_premium_theme import (
    danger_button_stylesheet,
    empty_state_stylesheet,
    header_stylesheet,
    input_stylesheet,
    page_stylesheet,
    primary_button_stylesheet,
    secondary_button_stylesheet,
    status_badge_stylesheet,
    table_stylesheet,
    training_cases_palette,
    type_badge_stylesheet,
)
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

        self._theme_mode = get_theme_preference()
        self._palette = training_cases_palette(self._theme_mode)

        self.setObjectName("TrainingCasesRoot")
        self._build_ui()
        self._apply_visual_theme()

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

    def _input_style(self) -> str:
        return input_stylesheet(self._palette)

    def _table_style(self, table: QTableWidget) -> None:
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.horizontalHeader().setMinimumHeight(40)
        table.setStyleSheet(table_stylesheet(self._palette))

    def _type_badge_style(self, document_type: str) -> str:
        return type_badge_stylesheet(self._palette, document_type)

    def _status_badge_style(self, status: str) -> str:
        return status_badge_stylesheet(self._palette, status)

    @staticmethod
    def _format_price(cents) -> str:
        try:
            value = int(cents or 0) / 100
        except (TypeError, ValueError):
            value = 0
        return f"{value:,.2f} €".replace(",", " ").replace(".00", "")

    def _build_kpi_card(self, label: str, caption: str, accent: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setProperty("financeCard", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(7)

        dot = QLabel("●")
        dot.setFixedWidth(12)
        dot.setAlignment(Qt.AlignCenter)
        dot.setStyleSheet(
            f"color:{accent};background:transparent;border:none;font-size:11px;"
        )

        title = QLabel(label)
        title.setProperty("financeKpiLabel", True)

        top.addWidget(dot)
        top.addWidget(title)
        top.addStretch()

        value = QLabel("0")
        value.setProperty("financeKpiValue", True)

        hint = QLabel(caption)
        hint.setProperty("financeKpiCaption", True)

        layout.addLayout(top)
        layout.addWidget(value)
        layout.addWidget(hint)
        return card, value

    def _build_cockpit_stat(self, label: str, accent: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setProperty("financeMiniStat", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(
            f"color:{accent};background:transparent;border:none;font-size:10px;"
        )
        dot.setFixedWidth(10)
        title = QLabel(label)
        title.setProperty("financeMiniStatLabel", True)
        top.addWidget(dot)
        top.addWidget(title)
        top.addStretch()

        value = QLabel("0")
        value.setProperty("financeMiniStatValue", True)
        layout.addLayout(top)
        layout.addWidget(value)
        return frame, value

    def _build_flow_stage(
        self,
        label: str,
        caption: str,
        accent: str,
    ) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setProperty("financeFlowStage", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(7)
        marker = QLabel("■")
        marker.setFixedWidth(12)
        marker.setStyleSheet(
            f"color:{accent};background:transparent;border:none;font-size:10px;"
        )
        title = QLabel(label)
        title.setProperty("financeFlowLabel", True)
        top.addWidget(marker)
        top.addWidget(title)
        top.addStretch()

        value = QLabel("0")
        value.setProperty("financeFlowValue", True)

        hint = QLabel(caption)
        hint.setProperty("financeFlowCaption", True)

        layout.addLayout(top)
        layout.addWidget(value)
        layout.addWidget(hint)
        return frame, value

    def _build_finance_cockpit(self) -> QWidget:
        cockpit = QWidget()
        cockpit.setObjectName("FinanceCockpit")
        layout = QVBoxLayout(cockpit)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        overview = QFrame()
        overview.setProperty("financeHeroCard", True)
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(18, 15, 18, 15)
        overview_layout.setSpacing(8)

        overline = QLabel("POSITION FINANCIÈRE")
        overline.setProperty("financeOverline", True)

        self.finance_value_title = QLabel("0 € en suivi")
        self.finance_value_title.setProperty("financeHeroValue", True)

        self.finance_value_caption = QLabel(
            "Montant cumulé des demandes financières actives."
        )
        self.finance_value_caption.setProperty("financeBody", True)
        self.finance_value_caption.setWordWrap(True)

        overview_layout.addWidget(overline)
        overview_layout.addWidget(self.finance_value_title)
        overview_layout.addWidget(self.finance_value_caption)

        mini_row = QHBoxLayout()
        mini_row.setSpacing(8)
        self.finance_mini_values = {}

        mini_specs = (
            ("documents", "Documents", self._palette["primary"]),
            ("quotes", "Devis", self._palette["violet"]),
            ("invoices", "Factures", self._palette["success"]),
        )
        for key, label, accent in mini_specs:
            card, value = self._build_cockpit_stat(label, accent)
            self.finance_mini_values[key] = value
            mini_row.addWidget(card, 1)

        overview_layout.addLayout(mini_row)
        top_row.addWidget(overview, 2)

        actions = QFrame()
        actions.setProperty("financeActionCard", True)
        self.finance_action_card = actions
        action_layout = QVBoxLayout(actions)
        action_layout.setContentsMargins(18, 15, 18, 15)
        action_layout.setSpacing(8)

        action_overline = QLabel("ACTIONS IMMÉDIATES")
        action_overline.setProperty("financeOverline", True)

        action_title = QLabel("Faire avancer un dossier")
        action_title.setProperty("financeSectionTitle", True)

        action_text = QLabel(
            "Créez une demande ou déposez un document sans chercher dans le tableau."
        )
        action_text.setProperty("financeBody", True)
        action_text.setWordWrap(True)

        self.quick_request_button = QPushButton("+  Demander un devis / une facture")
        self.quick_request_button.setMinimumHeight(42)
        self.quick_request_button.clicked.connect(self._create_cloud_quote_request)
        self._finance_primary_buttons.append(self.quick_request_button)

        self.quick_upload_button = QPushButton("↑  Déposer un document")
        self.quick_upload_button.setMinimumHeight(40)
        self.quick_upload_button.clicked.connect(self._upload_cloud_document)
        self._finance_secondary_buttons.append(self.quick_upload_button)

        action_layout.addWidget(action_overline)
        action_layout.addWidget(action_title)
        action_layout.addWidget(action_text)
        action_layout.addStretch()
        action_layout.addWidget(self.quick_request_button)
        action_layout.addWidget(self.quick_upload_button)
        top_row.addWidget(actions, 1)

        layout.addLayout(top_row)

        flow = QFrame()
        flow.setProperty("financeFlowCard", True)
        flow_layout = QVBoxLayout(flow)
        flow_layout.setContentsMargins(16, 12, 16, 12)
        flow_layout.setSpacing(8)

        flow_header = QHBoxLayout()
        flow_title_box = QVBoxLayout()
        flow_title_box.setSpacing(1)

        flow_overline = QLabel("FLUX FINANCIER")
        flow_overline.setProperty("financeOverline", True)
        flow_title = QLabel("Du besoin au document disponible")
        flow_title.setProperty("financeSectionTitle", True)
        flow_subtitle = QLabel(
            "Visualisez instantanément où se trouvent les demandes en cours."
        )
        flow_subtitle.setProperty("financeBody", True)

        flow_title_box.addWidget(flow_overline)
        flow_title_box.addWidget(flow_title)
        flow_title_box.addWidget(flow_subtitle)
        flow_header.addLayout(flow_title_box)
        flow_header.addStretch()
        flow_layout.addLayout(flow_header)

        stage_row = QHBoxLayout()
        stage_row.setSpacing(8)
        self.finance_flow_values = {}

        stages = (
            ("pending", "Demandées", "À prendre en charge", self._palette["warning"]),
            ("preparing", "Préparation", "Document en cours", self._palette["violet"]),
            ("available", "Disponibles", "Prêts à télécharger", self._palette["success"]),
            ("closed", "Clôturées", "Refusées ou annulées", self._palette["muted"]),
        )
        for key, label, caption, accent in stages:
            stage, value = self._build_flow_stage(label, caption, accent)
            self.finance_flow_values[key] = value
            stage_row.addWidget(stage, 1)

        flow_layout.addLayout(stage_row)
        layout.addWidget(flow)
        return cockpit

    def _refresh_kpis(self) -> None:
        if not hasattr(self, "finance_mini_values"):
            return

        if self._is_cloud():
            documents = list(self.cloud_documents or [])
            requests = list(self.cloud_quote_requests or [])

            docs = len(documents)
            quotes = sum(
                1 for item in documents
                if str(item.get("document_type") or "").lower() == "devis"
            )
            invoices = sum(
                1 for item in documents
                if str(item.get("document_type") or "").lower() == "facture"
            )

            pending = 0
            preparing = 0
            available = 0
            closed = 0
            active_value_cents = 0

            for item in requests:
                status = str(item.get("status") or "").strip().lower()
                if status == "pending":
                    pending += 1
                elif status == "preparing":
                    preparing += 1
                elif status == "available":
                    available += 1
                elif status in {"rejected", "cancelled"}:
                    closed += 1

                if status in {"pending", "preparing"}:
                    try:
                        active_value_cents += int(item.get("price_cents") or 0)
                    except (TypeError, ValueError):
                        pass

            self.finance_value_title.setText(
                f"{self._format_price(active_value_cents)} en suivi"
            )
            self.finance_value_caption.setText(
                "Montant cumulé des demandes encore à traiter ou en préparation."
            )

            self.finance_mini_values["documents"].setText(str(docs))
            self.finance_mini_values["quotes"].setText(str(quotes))
            self.finance_mini_values["invoices"].setText(str(invoices))

            flow_values = {
                "pending": pending,
                "preparing": preparing,
                "available": available,
                "closed": closed,
            }
        else:
            cases = list(self.case_rows or [])
            requests = list(self.quote_rows or [])

            docs = len(cases)
            quotes = len(requests)
            invoices = sum(1 for item in requests if item.get("quote_file_path"))

            pending = sum(
                1 for item in requests
                if str(item.get("status") or "") == "À traiter"
            )
            preparing = sum(
                1 for item in requests
                if str(item.get("status") or "") == "En préparation"
            )
            available = sum(1 for item in requests if item.get("quote_file_path"))
            closed = max(0, len(requests) - pending - preparing - available)

            self.finance_value_title.setText(f"{pending + preparing} demande(s) active(s)")
            self.finance_value_caption.setText(
                "Suivi local des demandes de devis et documents disponibles."
            )

            self.finance_mini_values["documents"].setText(str(docs))
            self.finance_mini_values["quotes"].setText(str(quotes))
            self.finance_mini_values["invoices"].setText(str(invoices))

            flow_values = {
                "pending": pending,
                "preparing": preparing,
                "available": available,
                "closed": closed,
            }

        for key, value in flow_values.items():
            widget = getattr(self, "finance_flow_values", {}).get(key)
            if widget is not None:
                widget.setText(str(value))

    def _restyle_visible_badges(self) -> None:
        if hasattr(self, "cloud_table"):
            for row in range(self.cloud_table.rowCount()):
                type_widget = self.cloud_table.cellWidget(row, 0)
                if isinstance(type_widget, QLabel):
                    type_widget.setStyleSheet(self._type_badge_style(type_widget.text()))
                status_widget = self.cloud_table.cellWidget(row, 5)
                if isinstance(status_widget, QLabel):
                    status_widget.setStyleSheet(self._status_badge_style(status_widget.text()))

        if hasattr(self, "cloud_request_table"):
            for row in range(self.cloud_request_table.rowCount()):
                type_widget = self.cloud_request_table.cellWidget(row, 0)
                if isinstance(type_widget, QLabel):
                    type_widget.setStyleSheet(self._type_badge_style(type_widget.text()))
                status_widget = self.cloud_request_table.cellWidget(row, 7)
                if isinstance(status_widget, QLabel):
                    status_widget.setStyleSheet(self._status_badge_style(status_widget.text()))

    def _apply_visual_theme(self) -> None:
        self._theme_mode = get_theme_preference()
        self._palette = training_cases_palette(self._theme_mode)
        p = self._palette

        self.setStyleSheet(page_stylesheet(p))
        self.header_card.setStyleSheet(header_stylesheet(p))

        self.header_eyebrow.setStyleSheet(
            f"color:{p['primary_text']};font-size:10px;font-weight:900;"
            "letter-spacing:1.1px;background:transparent;border:none;"
        )
        self.title.setStyleSheet(
            "font-size:28px;font-weight:950;color:#FFFFFF;"
            "background:transparent;border:none;"
        )
        self.subtitle.setStyleSheet(
            "color:#C7D6E8;font-size:11px;background:transparent;border:none;"
        )
        self.mode_chip.setStyleSheet(
            f"background:{p['primary_soft']};color:{p['primary_text']};"
            f"border:1px solid {p['border_strong']};border-radius:10px;"
            "padding:0 11px;font-size:9px;font-weight:900;"
        )
        self.header_refresh.setStyleSheet(secondary_button_stylesheet(p))
        self.info_state.setStyleSheet(empty_state_stylesheet(p))

        for frame in getattr(self, "_finance_cards", []):
            frame.setProperty("financeCard", True)
            frame.style().unpolish(frame)
            frame.style().polish(frame)

        for combo in getattr(self, "_finance_inputs", []):
            combo.setStyleSheet(self._input_style())

        for button in getattr(self, "_finance_primary_buttons", []):
            button.setStyleSheet(primary_button_stylesheet(p))

        for button in getattr(self, "_finance_secondary_buttons", []):
            button.setStyleSheet(secondary_button_stylesheet(p))

        for button in getattr(self, "_finance_danger_buttons", []):
            button.setStyleSheet(danger_button_stylesheet(p))

        if hasattr(self, "cloud_info"):
            self.cloud_info.setStyleSheet(
                f"QFrame#CommercialDocsInfo{{background:{p['surface_soft']};"
                f"border:1px solid {p['border']};border-radius:14px;}}"
            )
        if hasattr(self, "cloud_info_icon"):
            self.cloud_info_icon.setStyleSheet(
                f"background:{p['primary']};color:white;border-radius:14px;"
                "font-size:12px;font-weight:900;"
            )
        if hasattr(self, "cloud_info_text"):
            self.cloud_info_text.setStyleSheet(
                f"color:{p['muted']};font-size:10px;background:transparent;border:none;"
            )

        for tabs in (getattr(self, "cloud_tabs", None), getattr(self, "tabs", None)):
            if tabs is not None:
                tabs.setObjectName("FinanceTabs")
                tabs.style().unpolish(tabs)
                tabs.style().polish(tabs)

        for page in getattr(self, "_finance_tab_pages", []):
            page.setObjectName("FinanceWorkspacePage")
            page.setStyleSheet(
                f"QWidget#FinanceWorkspacePage{{background:{p['surface']};border:none;}}"
            )

        for frame in getattr(self, "_finance_filter_frames", []):
            frame.style().unpolish(frame)
            frame.style().polish(frame)

        for table in getattr(self, "_finance_tables", []):
            self._table_style(table)

        for empty in getattr(self, "_finance_empty_states", []):
            empty.setStyleSheet(empty_state_stylesheet(p))

        for status in (
            getattr(self, "cloud_status", None),
            getattr(self, "cloud_request_status", None),
            getattr(self, "local_status", None),
        ):
            if status is not None:
                status.setStyleSheet(
                    f"color:{p['muted']};font-size:9px;font-weight:700;"
                    "background:transparent;border:none;"
                )

        self._restyle_visible_badges()

    def _build_ui(self) -> None:
        self._finance_cards = []
        self._finance_inputs = []
        self._finance_primary_buttons = []
        self._finance_secondary_buttons = []
        self._finance_danger_buttons = []
        self._finance_filter_frames = []
        self._finance_tables = []
        self._finance_empty_states = []
        self._finance_tab_pages = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 22)
        root.setSpacing(12)

        self.header_card = QFrame()
        self.header_card.setObjectName("CommercialDocsHeader")
        header = QHBoxLayout(self.header_card)
        header.setContentsMargins(20, 16, 18, 16)
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        self.header_eyebrow = QLabel("FINANCE  •  DOCUMENTS COMMERCIAUX")
        self.title = QLabel("Devis & factures")
        self.subtitle = QLabel(
            "Pilotez les demandes, les documents disponibles et les actions à traiter."
        )
        self.subtitle.setWordWrap(True)

        title_box.addWidget(self.header_eyebrow)
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box, 1)

        right = QHBoxLayout()
        right.setSpacing(8)

        self.mode_chip = QLabel("●  FINANCE  •  ACTIF")
        self.mode_chip.setAlignment(Qt.AlignCenter)
        self.mode_chip.setFixedHeight(30)
        self.mode_chip.setMinimumWidth(120)

        self.header_refresh = QPushButton("↻  Actualiser")
        self.header_refresh.setMinimumHeight(38)
        self.header_refresh.clicked.connect(self.rafraichir)
        self._finance_secondary_buttons.append(self.header_refresh)

        right.addWidget(self.mode_chip)
        right.addWidget(self.header_refresh)
        header.addLayout(right)

        root.addWidget(self.header_card)

        self.finance_cockpit = self._build_finance_cockpit()
        root.addWidget(self.finance_cockpit)

        self.cloud_content = self._build_cloud_content()
        root.addWidget(self.cloud_content)
        self.cloud_content.setVisible(False)

        self.local_content = self._build_local_content()
        root.addWidget(self.local_content)
        self.local_content.setVisible(False)

        self.info_state = QLabel("")
        self.info_state.setAlignment(Qt.AlignCenter)
        self.info_state.setWordWrap(True)
        self.info_state.setMinimumHeight(160)
        root.addWidget(self.info_state)
        self.info_state.setVisible(False)

        root.addStretch()

    def _build_cloud_content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        workspace_nav = QFrame()
        workspace_nav.setProperty("financeWorkspaceNav", True)
        nav_layout = QHBoxLayout(workspace_nav)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        self.cloud_documents_nav = QPushButton(
            "DOCUMENTS DISPONIBLES\nBibliothèque  •  devis & factures"
        )
        self.cloud_documents_nav.setCheckable(True)
        self.cloud_documents_nav.setAutoExclusive(True)
        self.cloud_documents_nav.setChecked(True)
        self.cloud_documents_nav.setCursor(Qt.PointingHandCursor)
        self.cloud_documents_nav.setProperty("financeWorkspaceButton", True)
        self.cloud_documents_nav.setMinimumHeight(54)

        self.cloud_requests_nav = QPushButton(
            "DEMANDES DE DOCUMENTS\nWorkflow  •  suivi & traitement"
        )
        self.cloud_requests_nav.setCheckable(True)
        self.cloud_requests_nav.setAutoExclusive(True)
        self.cloud_requests_nav.setCursor(Qt.PointingHandCursor)
        self.cloud_requests_nav.setProperty("financeWorkspaceButton", True)
        self.cloud_requests_nav.setMinimumHeight(54)

        nav_layout.addWidget(self.cloud_documents_nav, 1)
        nav_layout.addWidget(self.cloud_requests_nav, 1)
        layout.addWidget(workspace_nav)

        self.cloud_tabs = QTabWidget()
        self.cloud_tabs.setDocumentMode(True)
        self.cloud_tabs.setObjectName("FinanceTabs")
        # Le contenu garde une hauteur confortable. Si l'espace disponible est
        # plus petit, le QScrollArea ci-dessous prend le relais au lieu de
        # comprimer les widgets et de provoquer des chevauchements.
        self.cloud_tabs.setMinimumHeight(590)

        docs_page = self._build_cloud_documents_tab()
        requests_page = self._build_cloud_requests_tab()
        self._finance_tab_pages.extend((docs_page, requests_page))

        self.cloud_tabs.addTab(docs_page, "Documents disponibles")
        self.cloud_tabs.addTab(requests_page, "Demandes de documents")
        self.cloud_tabs.tabBar().hide()

        self.cloud_documents_nav.clicked.connect(
            lambda: self.cloud_tabs.setCurrentIndex(0)
        )
        self.cloud_requests_nav.clicked.connect(
            lambda: self.cloud_tabs.setCurrentIndex(1)
        )
        self.cloud_tabs.currentChanged.connect(self._sync_cloud_workspace_navigation)

        self.cloud_workspace_scroll = QScrollArea()
        self.cloud_workspace_scroll.setObjectName("FinanceWorkspaceScroll")
        self.cloud_workspace_scroll.setWidgetResizable(True)
        self.cloud_workspace_scroll.setFrameShape(QFrame.NoFrame)
        self.cloud_workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cloud_workspace_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cloud_workspace_scroll.setMinimumHeight(260)
        self.cloud_workspace_scroll.setWidget(self.cloud_tabs)

        layout.addWidget(self.cloud_workspace_scroll, 1)
        return page

    def _sync_cloud_workspace_navigation(self, index: int) -> None:
        """Synchronise la navigation premium avec l'espace Cloud affiché."""
        if not hasattr(self, "cloud_documents_nav") or not hasattr(self, "cloud_requests_nav"):
            return
        if index == 1:
            self.cloud_requests_nav.setChecked(True)
        else:
            self.cloud_documents_nav.setChecked(True)

    def _build_cloud_documents_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)

        workspace_header = QFrame()
        workspace_header.setProperty("financeWorkspaceHeader", True)
        workspace_header.setMinimumHeight(68)
        header_layout = QHBoxLayout(workspace_header)
        header_layout.setContentsMargins(14, 11, 14, 11)
        header_layout.setSpacing(11)

        icon = QLabel("DOC")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setProperty("financeWorkspaceIcon", True)
        header_layout.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        eyebrow = QLabel("BIBLIOTHÈQUE FINANCIÈRE")
        eyebrow.setProperty("financeOverline", True)

        title = QLabel("Devis & factures disponibles")
        title.setProperty("financeSectionTitle", True)

        subtitle = QLabel(
            "Retrouvez les documents liés aux clients et formations visibles dans votre portefeuille."
        )
        subtitle.setProperty("financeBody", True)
        subtitle.setWordWrap(True)

        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box, 1)

        self.cloud_count_badge = QLabel("0 document")
        self.cloud_count_badge.setAlignment(Qt.AlignCenter)
        self.cloud_count_badge.setMinimumWidth(94)
        self.cloud_count_badge.setFixedHeight(30)
        self.cloud_count_badge.setProperty("financeCountBadge", True)
        header_layout.addWidget(self.cloud_count_badge)

        layout.addWidget(workspace_header)

        filters = QFrame()
        filters.setProperty("financeCard", True)
        filters.setProperty("financeToolbar", True)
        filters.setMinimumHeight(170)
        self._finance_filter_frames.append(filters)

        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(12, 9, 12, 9)
        filters_layout.setSpacing(7)

        toolbar_meta = QHBoxLayout()
        toolbar_meta.setSpacing(8)

        toolbar_label = QLabel("RECHERCHE & FILTRES")
        toolbar_label.setProperty("financeToolbarLabel", True)
        toolbar_meta.addWidget(toolbar_label)

        toolbar_hint = QLabel("Affinez la bibliothèque sans quitter votre espace de travail")
        toolbar_hint.setProperty("financeToolbarHint", True)
        toolbar_meta.addWidget(toolbar_hint)
        toolbar_meta.addStretch()

        filters_layout.addLayout(toolbar_meta)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.cloud_search = QLineEdit()
        self.cloud_search.setPlaceholderText(
            "Rechercher un client, un numéro, une formation ou un fichier…"
        )
        self.cloud_search.setClearButtonEnabled(True)
        self.cloud_search.setMinimumHeight(38)
        self.cloud_search.textChanged.connect(self._apply_cloud_filters)
        self._finance_inputs.append(self.cloud_search)
        search_row.addWidget(self.cloud_search, 1)
        filters_layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.cloud_type_combo = QComboBox()
        self.cloud_type_combo.addItem("Tous les documents", "")
        self.cloud_type_combo.addItem("Devis", "Devis")
        self.cloud_type_combo.addItem("Factures", "Facture")
        self.cloud_type_combo.setMinimumWidth(170)
        self.cloud_type_combo.currentIndexChanged.connect(self._apply_cloud_filters)
        self._finance_inputs.append(self.cloud_type_combo)
        filter_row.addWidget(self.cloud_type_combo)

        self.cloud_prospect_combo = QComboBox()
        self.cloud_prospect_combo.setMinimumWidth(220)
        self.cloud_prospect_combo.setMaximumWidth(320)
        self.cloud_prospect_combo.currentIndexChanged.connect(self._load_cloud_documents)
        self._finance_inputs.append(self.cloud_prospect_combo)
        filter_row.addWidget(self.cloud_prospect_combo)

        self.cloud_history_check = QCheckBox("Inclure l’historique")
        self.cloud_history_check.toggled.connect(self._load_cloud_documents)
        filter_row.addWidget(self.cloud_history_check)
        filter_row.addStretch()

        filters_layout.addLayout(filter_row)

        divider = QFrame()
        divider.setProperty("financeToolbarDivider", True)
        divider.setFixedHeight(1)
        filters_layout.addWidget(divider)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        action_label = QLabel("ACTIONS")
        action_label.setProperty("financeToolbarLabel", True)
        actions.addWidget(action_label)

        self.cloud_download_button = QPushButton("↓  Télécharger")
        self.cloud_download_button.setMinimumHeight(38)
        self.cloud_download_button.setEnabled(False)
        self.cloud_download_button.clicked.connect(self._download_cloud_document)
        self._finance_secondary_buttons.append(self.cloud_download_button)
        actions.addWidget(self.cloud_download_button)

        actions.addStretch()

        self.cloud_upload_button = QPushButton("+  Déposer un devis / une facture")
        self.cloud_upload_button.setMinimumHeight(38)
        self.cloud_upload_button.clicked.connect(self._upload_cloud_document)
        self._finance_primary_buttons.append(self.cloud_upload_button)
        actions.addWidget(self.cloud_upload_button)

        filters_layout.addLayout(actions)
        layout.addWidget(filters)

        self.cloud_status = QLabel("")
        self.cloud_status.setWordWrap(True)
        self.cloud_status.setMinimumHeight(18)
        self.cloud_status.setProperty("financeStatus", True)
        layout.addWidget(self.cloud_status)

        self.cloud_table = QTableWidget(0, 8)
        self.cloud_table.setMinimumHeight(220)
        self.cloud_table.setHorizontalHeaderLabels(
            ["Type", "Numéro", "Client", "Formation", "Fichier", "Statut", "Version", "Créé le"]
        )
        self._finance_tables.append(self.cloud_table)

        cloud_header = self.cloud_table.horizontalHeader()
        cloud_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        cloud_header.setSectionResizeMode(0, QHeaderView.Fixed)
        cloud_header.setSectionResizeMode(1, QHeaderView.Fixed)
        cloud_header.setSectionResizeMode(2, QHeaderView.Fixed)
        cloud_header.setSectionResizeMode(3, QHeaderView.Stretch)
        cloud_header.setSectionResizeMode(4, QHeaderView.Stretch)
        cloud_header.setSectionResizeMode(5, QHeaderView.Fixed)
        cloud_header.setSectionResizeMode(6, QHeaderView.Fixed)
        cloud_header.setSectionResizeMode(7, QHeaderView.Fixed)

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

        self.cloud_empty_state = QLabel(
            "Aucun document disponible pour cette sélection.\n"
            "Affinez les filtres, créez une demande ou déposez un document."
        )
        self.cloud_empty_state.setAlignment(Qt.AlignCenter)
        self.cloud_empty_state.setWordWrap(True)
        self.cloud_empty_state.setMinimumHeight(104)
        self.cloud_empty_state.setMaximumHeight(122)
        self.cloud_empty_state.setProperty("financeCompactEmpty", True)
        self._finance_empty_states.append(self.cloud_empty_state)
        layout.addWidget(self.cloud_empty_state, 1)
        self.cloud_empty_state.setVisible(False)

        return page

    def _build_cloud_requests_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)

        workspace_header = QFrame()
        workspace_header.setProperty("financeWorkspaceHeader", True)
        workspace_header.setMinimumHeight(68)
        header_layout = QHBoxLayout(workspace_header)
        header_layout.setContentsMargins(14, 11, 14, 11)
        header_layout.setSpacing(11)

        icon = QLabel("REQ")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setProperty("financeWorkspaceIcon", True)
        header_layout.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        eyebrow = QLabel("WORKFLOW FINANCIER")
        eyebrow.setProperty("financeOverline", True)

        title = QLabel("Demandes de documents")
        title.setProperty("financeSectionTitle", True)

        subtitle = QLabel(
            "Suivez les demandes en cours et récupérez les documents dès qu’ils sont disponibles."
        )
        subtitle.setProperty("financeBody", True)
        subtitle.setWordWrap(True)

        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box, 1)

        self.cloud_request_count_badge = QLabel("0 demande")
        self.cloud_request_count_badge.setAlignment(Qt.AlignCenter)
        self.cloud_request_count_badge.setMinimumWidth(94)
        self.cloud_request_count_badge.setFixedHeight(30)
        self.cloud_request_count_badge.setProperty("financeCountBadge", True)
        header_layout.addWidget(self.cloud_request_count_badge)

        layout.addWidget(workspace_header)

        filters = QFrame()
        filters.setProperty("financeCard", True)
        filters.setProperty("financeToolbar", True)
        filters.setMinimumHeight(170)
        self._finance_filter_frames.append(filters)

        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(12, 9, 12, 9)
        filters_layout.setSpacing(7)

        toolbar_meta = QHBoxLayout()
        toolbar_meta.setSpacing(8)

        toolbar_label = QLabel("RECHERCHE & FILTRES")
        toolbar_label.setProperty("financeToolbarLabel", True)
        toolbar_meta.addWidget(toolbar_label)

        toolbar_hint = QLabel("Filtrez le workflow par type, statut ou demandeur")
        toolbar_hint.setProperty("financeToolbarHint", True)
        toolbar_meta.addWidget(toolbar_hint)
        toolbar_meta.addStretch()

        filters_layout.addLayout(toolbar_meta)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.cloud_request_search = QLineEdit()
        self.cloud_request_search.setPlaceholderText(
            "Rechercher un client, une formation, un demandeur ou une note…"
        )
        self.cloud_request_search.setClearButtonEnabled(True)
        self.cloud_request_search.setMinimumHeight(38)
        self.cloud_request_search.textChanged.connect(self._apply_cloud_quote_filters)
        self._finance_inputs.append(self.cloud_request_search)
        search_row.addWidget(self.cloud_request_search, 1)
        filters_layout.addLayout(search_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.cloud_request_type_combo = QComboBox()
        self.cloud_request_type_combo.addItem("Tous les types", "")
        self.cloud_request_type_combo.addItem("Devis", "Devis")
        self.cloud_request_type_combo.addItem("Factures", "Facture")
        self.cloud_request_type_combo.setMinimumWidth(180)
        self.cloud_request_type_combo.currentIndexChanged.connect(self._apply_cloud_quote_filters)
        self._finance_inputs.append(self.cloud_request_type_combo)
        filter_row.addWidget(self.cloud_request_type_combo)

        self.cloud_request_status_combo = QComboBox()
        self.cloud_request_status_combo.addItem("Tous les statuts", "")
        self.cloud_request_status_combo.addItem("À traiter", "pending")
        self.cloud_request_status_combo.addItem("En préparation", "preparing")
        self.cloud_request_status_combo.addItem("Document disponible", "available")
        self.cloud_request_status_combo.addItem("Refusée", "rejected")
        self.cloud_request_status_combo.addItem("Annulée", "cancelled")
        self.cloud_request_status_combo.setMinimumWidth(200)
        self.cloud_request_status_combo.currentIndexChanged.connect(self._apply_cloud_quote_filters)
        self._finance_inputs.append(self.cloud_request_status_combo)
        filter_row.addWidget(self.cloud_request_status_combo)
        filter_row.addStretch()

        filters_layout.addLayout(filter_row)

        divider = QFrame()
        divider.setProperty("financeToolbarDivider", True)
        divider.setFixedHeight(1)
        filters_layout.addWidget(divider)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        action_label = QLabel("ACTIONS")
        action_label.setProperty("financeToolbarLabel", True)
        actions.addWidget(action_label)

        self.cloud_request_prepare_button = QPushButton("Mettre en préparation")
        self.cloud_request_prepare_button.clicked.connect(
            lambda: self._update_cloud_quote_status("preparing")
        )
        self._finance_secondary_buttons.append(self.cloud_request_prepare_button)
        actions.addWidget(self.cloud_request_prepare_button)

        self.cloud_request_upload_button = QPushButton("Déposer le document")
        self.cloud_request_upload_button.clicked.connect(self._upload_requested_quote)
        self._finance_primary_buttons.append(self.cloud_request_upload_button)
        actions.addWidget(self.cloud_request_upload_button)

        self.cloud_request_reject_button = QPushButton("Refuser")
        self.cloud_request_reject_button.clicked.connect(
            lambda: self._update_cloud_quote_status("rejected")
        )
        self._finance_danger_buttons.append(self.cloud_request_reject_button)
        actions.addWidget(self.cloud_request_reject_button)

        self.cloud_request_cancel_button = QPushButton("Annuler la demande")
        self.cloud_request_cancel_button.setEnabled(False)
        self.cloud_request_cancel_button.clicked.connect(
            lambda: self._update_cloud_quote_status("cancelled")
        )
        self._finance_danger_buttons.append(self.cloud_request_cancel_button)
        actions.addWidget(self.cloud_request_cancel_button)

        actions.addStretch()

        self.cloud_request_create_button = QPushButton("+  Demander un devis / une facture")
        self.cloud_request_create_button.clicked.connect(self._create_cloud_quote_request)
        self._finance_primary_buttons.append(self.cloud_request_create_button)
        actions.addWidget(self.cloud_request_create_button)

        filters_layout.addLayout(actions)
        layout.addWidget(filters)

        self.cloud_request_status = QLabel("")
        self.cloud_request_status.setWordWrap(True)
        self.cloud_request_status.setMinimumHeight(18)
        self.cloud_request_status.setProperty("financeStatus", True)
        layout.addWidget(self.cloud_request_status)

        self.cloud_request_table = QTableWidget(0, 10)
        self.cloud_request_table.setMinimumHeight(220)
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

        role = self._current_role()
        self._hide_request_commercial_column = role == "commercial"
        self.cloud_request_table.setColumnHidden(
            5, self._hide_request_commercial_column
        )
        self._finance_tables.append(self.cloud_request_table)

        request_header = self.cloud_request_table.horizontalHeader()
        request_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        request_header.setSectionResizeMode(0, QHeaderView.Fixed)
        request_header.setSectionResizeMode(1, QHeaderView.Fixed)
        request_header.setSectionResizeMode(2, QHeaderView.Stretch)
        request_header.setSectionResizeMode(6, QHeaderView.Stretch)
        request_header.setSectionResizeMode(7, QHeaderView.Fixed)

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

        self.cloud_request_empty_state = QLabel(
            "Aucune demande pour cette sélection.\n"
            "Créez une nouvelle demande pour démarrer le suivi financier."
        )
        self.cloud_request_empty_state.setAlignment(Qt.AlignCenter)
        self.cloud_request_empty_state.setWordWrap(True)
        self.cloud_request_empty_state.setMinimumHeight(104)
        self.cloud_request_empty_state.setMaximumHeight(122)
        self.cloud_request_empty_state.setProperty("financeCompactEmpty", True)
        self._finance_empty_states.append(self.cloud_request_empty_state)
        layout.addWidget(self.cloud_request_empty_state, 1)
        self.cloud_request_empty_state.setVisible(False)

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
        self.finance_cockpit.setVisible(True)
        self.cloud_content.setVisible(True)
        self.mode_chip.setText("●  CLOUD FINANCE  •  LIVE")
        self.subtitle.setText(
            "Consultez les devis et factures, et suivez les demandes de documents transmises à l'administrateur."
        )
        can_manage = self._can_manage_quote_requests()
        self.finance_action_card.setVisible(True)
        self.quick_request_button.setVisible(self._can_create_quote_request())
        self.quick_upload_button.setVisible(self._can_admin_upload())
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
        self._refresh_kpis()

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
            self.cloud_table.setVisible(False)
            self.cloud_empty_state.setText(f"Chargement impossible\n{exc}")
            self.cloud_empty_state.setVisible(True)
            self.cloud_status.setText(f"⛔ {exc}")
            self._refresh_kpis()
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
        has_documents = bool(visible)
        self.cloud_table.setVisible(has_documents)
        self.cloud_empty_state.setVisible(not has_documents)
        if not has_documents:
            self.cloud_empty_state.setText(
                "Aucun document disponible pour cette sélection.\n"
                "Affinez les filtres, créez une demande ou déposez un document."
            )
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
            f"color:{self._palette['muted']};font-size:9px;font-weight:700;"
        )
        self._refresh_kpis()

    def _load_cloud_quote_requests(self, *_args) -> None:
        if not self._is_cloud() or not CloudRuntime.is_active():
            return
        try:
            self.cloud_quote_requests = CloudRuntime.api().list_cloud_quote_requests()
        except CloudAPIError as exc:
            self.cloud_quote_requests = []
            self.cloud_visible_quote_requests = []
            self.cloud_request_table.setRowCount(0)
            self.cloud_request_table.setVisible(False)
            self.cloud_request_empty_state.setText(f"Chargement impossible\n{exc}")
            self.cloud_request_empty_state.setVisible(True)
            self.cloud_request_status.setText(f"⛔ {exc}")
            self._refresh_kpis()
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
        has_requests = bool(visible)
        self.cloud_request_table.setVisible(has_requests)
        self.cloud_request_empty_state.setVisible(not has_requests)
        if not has_requests:
            self.cloud_request_empty_state.setText(
                "Aucune demande pour cette sélection.\n"
                "Créez une nouvelle demande pour démarrer le suivi financier."
            )
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
            f"color:{self._palette['muted']};font-size:9px;font-weight:700;"
        )
        self.cloud_request_table.clearSelection()
        self._refresh_request_action_state()
        self._refresh_kpis()

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
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("FinanceTabs")

        cases_page = self._cases_tab()
        quotes_page = self._quotes_tab()
        self._finance_tab_pages.extend((cases_page, quotes_page))

        self.tabs.addTab(cases_page, "Dossiers & devis")
        self.tabs.addTab(quotes_page, "Demandes de devis")
        layout.addWidget(self.tabs, 1)
        return page

    def _cases_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        eyebrow = QLabel("DOSSIERS DE FORMATION")
        eyebrow.setProperty("financeOverline", True)
        title = QLabel("Suivi local des dossiers")
        title.setProperty("financeSectionTitle", True)
        subtitle = QLabel(
            "Recherchez un dossier, téléchargez son devis ou créez une nouvelle demande."
        )
        subtitle.setProperty("financeBody", True)
        subtitle.setWordWrap(True)

        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        layout.addLayout(top)

        tools_frame = QFrame()
        tools_frame.setProperty("financeCard", True)
        self._finance_filter_frames.append(tools_frame)
        tools = QHBoxLayout(tools_frame)
        tools.setContentsMargins(12, 10, 12, 10)
        tools.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Rechercher un client, une formation ou un commercial…"
        )
        self.search.textChanged.connect(self._load_cases)
        self._finance_inputs.append(self.search)
        tools.addWidget(self.search, 1)

        refresh = QPushButton("↻  Actualiser")
        refresh.clicked.connect(self.rafraichir)
        self._finance_secondary_buttons.append(refresh)
        tools.addWidget(refresh)

        self.download_btn = QPushButton("↓  Télécharger le devis")
        self.download_btn.clicked.connect(self._download_case_quote)
        self._finance_secondary_buttons.append(self.download_btn)
        tools.addWidget(self.download_btn)

        self.delete_case_btn = QPushButton("Supprimer le dossier")
        self.delete_case_btn.clicked.connect(self._delete_case)
        self.delete_case_btn.setVisible(SessionState.has_role("Administrateur"))
        self._finance_danger_buttons.append(self.delete_case_btn)
        tools.addWidget(self.delete_case_btn)

        self.request_btn = QPushButton("+  Demander un devis")
        self.request_btn.clicked.connect(self._request_quote)
        self._finance_primary_buttons.append(self.request_btn)
        tools.addWidget(self.request_btn)

        layout.addWidget(tools_frame)

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
        self._finance_tables.append(self.case_table)

        header = self.case_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.case_table.itemDoubleClicked.connect(
            lambda _item: self._download_case_quote()
        )
        layout.addWidget(self.case_table, 1)

        self.case_empty_state = QLabel(
            "Aucun dossier de formation à afficher.\n"
            "Ouvrez ou créez un dossier pour démarrer le suivi financier."
        )
        self.case_empty_state.setAlignment(Qt.AlignCenter)
        self.case_empty_state.setWordWrap(True)
        self.case_empty_state.setMinimumHeight(210)
        self._finance_empty_states.append(self.case_empty_state)
        layout.addWidget(self.case_empty_state, 1)
        self.case_empty_state.setVisible(False)

        return page

    def _quotes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(1)

        eyebrow = QLabel("DEMANDES DE DEVIS")
        eyebrow.setProperty("financeOverline", True)
        title = QLabel("Suivi des demandes")
        title.setProperty("financeSectionTitle", True)
        subtitle = QLabel(
            "Pilotez le statut des demandes et récupérez les PDF disponibles."
        )
        subtitle.setProperty("financeBody", True)
        subtitle.setWordWrap(True)

        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        layout.addLayout(top)

        tools_frame = QFrame()
        tools_frame.setProperty("financeCard", True)
        self._finance_filter_frames.append(tools_frame)

        tools = QHBoxLayout(tools_frame)
        tools.setContentsMargins(12, 10, 12, 10)
        tools.setSpacing(8)
        tools.addStretch()

        self.status_combo = QComboBox()
        self.status_combo.addItems(TrainingCaseService.QUOTE_STATUSES)
        self.status_combo.setMinimumWidth(180)
        self._finance_inputs.append(self.status_combo)

        self.download_quote_btn = QPushButton("↓  Télécharger le PDF")
        self.download_quote_btn.clicked.connect(self._download_selected_quote)
        self._finance_secondary_buttons.append(self.download_quote_btn)

        self.status_btn = QPushButton("Mettre à jour le statut")
        self.status_btn.clicked.connect(self._update_status)
        self._finance_secondary_buttons.append(self.status_btn)

        self.import_btn = QPushButton("↑  Importer le devis PDF")
        self.import_btn.clicked.connect(self._import_quote)
        self._finance_primary_buttons.append(self.import_btn)

        is_admin = SessionState.has_role("Administrateur")
        self.status_combo.setVisible(is_admin)
        self.status_btn.setVisible(is_admin)
        self.import_btn.setVisible(is_admin)

        tools.addWidget(self.download_quote_btn)
        tools.addWidget(self.status_combo)
        tools.addWidget(self.status_btn)
        tools.addWidget(self.import_btn)
        layout.addWidget(tools_frame)

        self.quote_table = QTableWidget(0, 8)
        self.quote_table.setHorizontalHeaderLabels(
            ["Client", "Formation", "Dates", "Demandeur", "Note", "Statut", "PDF", "Créée le"]
        )
        self._finance_tables.append(self.quote_table)

        header = self.quote_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.quote_table.itemDoubleClicked.connect(
            lambda _item: self._download_selected_quote()
        )
        layout.addWidget(self.quote_table, 1)

        self.quote_empty_state = QLabel(
            "Aucune demande de devis pour le moment.\n"
            "Les prochaines demandes apparaîtront ici avec leur statut."
        )
        self.quote_empty_state.setAlignment(Qt.AlignCenter)
        self.quote_empty_state.setWordWrap(True)
        self.quote_empty_state.setMinimumHeight(210)
        self._finance_empty_states.append(self.quote_empty_state)
        layout.addWidget(self.quote_empty_state, 1)
        self.quote_empty_state.setVisible(False)

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
                self.finance_cockpit.setVisible(False)
                self.info_state.setText(
                    "La session Form@Prospect Cloud n'est pas active. Reconnectez-vous pour accéder aux devis et factures."
                )
                self.info_state.setVisible(True)
                return
            self._load_cloud_mode()
            return

        self.cloud_content.setVisible(False)
        self.info_state.setVisible(False)
        self.finance_cockpit.setVisible(True)
        self.local_content.setVisible(True)
        self.finance_action_card.setVisible(False)
        self.mode_chip.setText("●  LOCAL FINANCE  •  ACTIF")
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
        has_cases = bool(self.case_rows)
        self.case_table.setVisible(has_cases)
        self.case_empty_state.setVisible(not has_cases)
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
        self._refresh_kpis()

    def _load_quotes(self) -> None:
        if self._is_cloud() or not self._ensure_service():
            return
        self.quote_rows = self.service.list_quote_requests()
        has_quotes = bool(self.quote_rows)
        self.quote_table.setVisible(has_quotes)
        self.quote_empty_state.setVisible(not has_quotes)
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
        self._refresh_kpis()

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
