from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    NAVY,
    PAGE_BG,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from services.document_generator_service import DocumentGeneratorService
from services.document_service import DocumentService
from ui.dialogs.document_template_dialog import DocumentTemplateDialog
from ui.dialogs.generate_documents_dialog import (
    CloudAdministrativeUploadDialog,
    CloudGenerateDocumentsDialog,
    CloudTemplateUploadDialog,
    CloudTrainingManagementDialog,
    GenerateDocumentsDialog,
)
from ui.dialogs.training_dialog import TrainingDialog


class CloudSignedDocumentUploadDialog(QDialog):
    """Dépôt sécurisé d'une Convention ou d'un Devis signé au format PDF."""

    def __init__(
        self,
        api,
        prospects: list[dict],
        parent=None,
        *,
        initial_prospect_id: str | None = None,
    ):
        super().__init__(parent)
        self.api = api
        self.prospects = list(prospects or [])
        self.file_path = Path()

        self.setWindowTitle("Déposer un document signé")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setStyleSheet("background:#F8FAFD;")

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        title = QLabel("Déposer un document signé")
        title.setStyleSheet(
            "color:#0B1220;font-size:20px;font-weight:900;"
            "background:transparent;border:none;"
        )
        root.addWidget(title)

        help_text = QLabel(
            "Ajoutez la version signée retournée par le client. "
            "Seuls les fichiers PDF sont acceptés."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(
            "color:#64748B;font-size:11px;background:transparent;border:none;"
        )
        root.addWidget(help_text)

        form_card = QFrame()
        form_card.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #E4EBF4;border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        form = QVBoxLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        prospect_label = QLabel("Prospect / client")
        prospect_label.setStyleSheet("color:#334155;font-size:11px;font-weight:850;")
        self.prospect = QComboBox()
        self.prospect.setMinimumHeight(38)
        self.prospect.setStyleSheet(
            "QComboBox{background:white;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:0 34px 0 11px;font-size:11px;font-weight:700;}"
        )
        selected = -1
        for index, item in enumerate(self.prospects):
            prospect_id = str(item.get("id") or "")
            self.prospect.addItem(
                str(item.get("company_name") or "Prospect sans nom"),
                prospect_id,
            )
            if initial_prospect_id and prospect_id == str(initial_prospect_id):
                selected = index
        if selected >= 0:
            self.prospect.setCurrentIndex(selected)

        type_label = QLabel("Type de document signé")
        type_label.setStyleSheet("color:#334155;font-size:11px;font-weight:850;")
        self.document_type = QComboBox()
        self.document_type.addItems(["Convention", "Devis"])
        self.document_type.setMinimumHeight(38)
        self.document_type.setStyleSheet(self.prospect.styleSheet())

        number_label = QLabel("Numéro du document (facultatif)")
        number_label.setStyleSheet("color:#334155;font-size:11px;font-weight:850;")
        self.document_number = QLineEdit()
        self.document_number.setPlaceholderText("Ex. CONV-2026-001")
        self.document_number.setMinimumHeight(38)
        self.document_number.setStyleSheet(
            "QLineEdit{background:white;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:0 11px;font-size:11px;}"
        )

        file_label_title = QLabel("Document PDF signé")
        file_label_title.setStyleSheet("color:#334155;font-size:11px;font-weight:850;")

        file_row = QHBoxLayout()
        self.file_label = QLabel("Aucun fichier sélectionné")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet(
            "color:#64748B;font-size:10px;background:#F8FAFC;"
            "border:1px solid #E2E8F0;border-radius:8px;padding:8px;"
        )
        choose = QPushButton("Choisir un PDF")
        choose.setMinimumHeight(36)
        choose.setStyleSheet(SECONDARY_BUTTON)
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(choose)

        form.addWidget(prospect_label)
        form.addWidget(self.prospect)
        form.addWidget(type_label)
        form.addWidget(self.document_type)
        form.addWidget(number_label)
        form.addWidget(self.document_number)
        form.addWidget(file_label_title)
        form.addLayout(file_row)
        root.addWidget(form_card)

        security = QLabel(
            "Le fichier est contrôlé côté application et côté serveur. "
            "Un autre format renommé en .pdf sera refusé."
        )
        security.setWordWrap(True)
        security.setStyleSheet(
            "color:#64748B;font-size:10px;background:transparent;border:none;"
        )
        root.addWidget(security)

        actions = QHBoxLayout()
        actions.addStretch()

        cancel = QPushButton("Annuler")
        cancel.setMinimumHeight(38)
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)

        upload = QPushButton("Déposer le document signé")
        upload.setMinimumHeight(38)
        upload.setStyleSheet(PRIMARY_BUTTON)
        upload.clicked.connect(self._upload)

        actions.addWidget(cancel)
        actions.addWidget(upload)
        root.addLayout(actions)

    def _choose_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le document signé",
            "",
            "Documents PDF (*.pdf)",
        )
        if filename:
            self.file_path = Path(filename)
            self.file_label.setText(self.file_path.name)

    def _upload(self) -> None:
        prospect_id = self.prospect.currentData()
        if not prospect_id:
            QMessageBox.warning(
                self,
                "Prospect manquant",
                "Sélectionnez le prospect ou le client concerné.",
            )
            return

        if not self.file_path.is_file():
            QMessageBox.warning(
                self,
                "Document manquant",
                "Sélectionnez le document PDF signé.",
            )
            return

        if self.file_path.suffix.lower() != ".pdf":
            QMessageBox.warning(
                self,
                "Format interdit",
                "Seuls les fichiers PDF sont autorisés.",
            )
            return

        try:
            self.api.upload_cloud_signed_document(
                prospect_id=str(prospect_id),
                document_type=self.document_type.currentText(),
                file_path=self.file_path,
                document_number=self.document_number.text().strip(),
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Dépôt impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Document signé enregistré",
            "Le document signé est maintenant conservé dans Form@Prospect "
            "et reste téléchargeable depuis l'espace Documents.",
        )
        self.accept()


class DocumentsPage(QWidget):
    """Moteur documentaire local et espace Documents Cloud sécurisé."""

    def __init__(self):
        super().__init__()
        self.service: DocumentService | None = None
        self.training_rows: list[dict] = []
        self.template_rows: list[dict] = []
        self.cloud_prospects: list[dict] = []
        self.cloud_documents: list[dict] = []
        self.cloud_prospect_names: dict[str, str] = {}
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DocumentCard")
        card.setStyleSheet(
            "QFrame#DocumentCard{"
            "background:#FFFFFF;"
            "border:1px solid #E8EEF5;"
            "border-radius:18px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(14)

        header_card = QFrame()
        header_card.setObjectName("DocumentsHeader")
        header_card.setStyleSheet(
            "QFrame#DocumentsHeader{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #FFFFFF, stop:0.72 #F8FBFF, stop:1 #EAF4FF);"
            "border:1px solid #E4EBF4;"
            "border-radius:20px;"
            "}"
        )
        header = QHBoxLayout(header_card)
        header.setContentsMargins(22, 18, 22, 18)
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        eyebrow = QLabel("DOCUMENTS  •  ESPACE DOCUMENTAIRE")
        eyebrow.setStyleSheet(
            "color:#338CE4; font-size:10px; font-weight:900; "
            "letter-spacing:1.2px; background:transparent;"
        )

        title = QLabel("Documents")
        title.setStyleSheet(
            "color:#0B1220; font-size:28px; font-weight:900; background:transparent;"
        )

        self.subtitle = QLabel(
            "Préparez le catalogue des formations et les modèles qui "
            "alimenteront le moteur documentaire."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(
            "color:#6B7A90; font-size:12px; background:transparent;"
        )

        title_box.addWidget(eyebrow)
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)

        header.addLayout(title_box, 1)

        self.generate_button = QPushButton("Générer des documents")
        self.generate_button.setMinimumHeight(40)
        self.generate_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 16px;font-size:12px;font-weight:900;}"
            "QPushButton:hover{background:#247BD0;}"
            "QPushButton:pressed{background:#1D66B2;}"
        )
        self.generate_button.clicked.connect(self.generate_documents)
        header.addWidget(self.generate_button)

        refresh = QPushButton("Actualiser")
        refresh.setMinimumHeight(40)
        refresh.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 15px;font-size:12px;font-weight:850;}"
            "QPushButton:hover{background:#F8FBFF;color:#338CE4;border-color:#AFCFF0;}"
        )
        refresh.clicked.connect(self.rafraichir)
        header.addWidget(refresh)

        root.addWidget(header_card)

        self.empty = QLabel("Ouvrez un projet pour accéder au moteur documentaire.")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.setMinimumHeight(120)
        self.empty.setStyleSheet(
            f"background:white; color:{MUTED}; border:1px dashed {BORDER}; "
            "border-radius:14px;"
        )
        root.addWidget(self.empty)

        self.cloud_content = self._build_cloud_content()
        root.addWidget(self.cloud_content, 1)
        self.cloud_content.setVisible(False)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        kpis = QGridLayout()
        kpis.setSpacing(10)
        self.kpi_labels = {}
        for col, (key, caption) in enumerate(
            [
                ("trainings", "Formations"),
                ("templates", "Modèles"),
                ("active_templates", "Modèles actifs"),
                ("documents", "Documents générés"),
            ]
        ):
            card = self._card()
            box = QVBoxLayout(card)
            label = QLabel(caption)
            label.setStyleSheet(
                f"color:{MUTED}; font-size:11px; font-weight:800;"
            )
            value = QLabel("0")
            value.setStyleSheet(
                f"color:{NAVY}; font-size:25px; font-weight:900;"
            )
            box.addWidget(label)
            box.addWidget(value)
            kpis.addWidget(card, 0, col)
            self.kpi_labels[key] = value
        content_layout.addLayout(kpis)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabBar::tab{padding:10px 18px; font-weight:700;} "
            "QTabWidget::pane{border:0;}"
        )
        tabs.addTab(self._build_trainings_tab(), "Catalogue des formations")
        tabs.addTab(self._build_templates_tab(), "Modèles documentaires")
        tabs.addTab(self._build_history_tab(), "Documents générés")
        tabs.addTab(self._build_foundations_tab(), "Fondations RC2")
        content_layout.addWidget(tabs, 1)
        root.addWidget(self.content, 1)
        self.content.setVisible(False)

    def _build_cloud_content(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ---- Synthèse Cloud
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.cloud_metric_values = {}

        metric_specs = [
            ("documents", "Documents", "Fichiers disponibles", "📄"),
            ("generated", "Générés", "Créés par Form@Prospect", "✦"),
            ("uploaded", "Déposés", "Administration / documents signés", "⬆"),
        ]
        for key, caption, hint, icon in metric_specs:
            card = self._card()
            card.setMinimumHeight(92)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            box = QVBoxLayout(card)
            box.setContentsMargins(16, 13, 16, 13)
            box.setSpacing(3)

            top = QHBoxLayout()
            top.setSpacing(7)
            icon_label = QLabel(icon)
            icon_label.setFixedSize(28, 28)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(
                "background:#EAF4FF;border-radius:8px;font-size:14px;"
            )
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(
                "color:#53657C;font-size:11px;font-weight:850;"
                "background:transparent;border:none;"
            )
            top.addWidget(icon_label)
            top.addWidget(caption_label)
            top.addStretch()

            value = QLabel("0")
            value.setStyleSheet(
                "color:#0B1220;font-size:22px;font-weight:900;"
                "background:transparent;border:none;"
            )
            hint_label = QLabel(hint)
            hint_label.setStyleSheet(
                "color:#8A98AA;font-size:9px;"
                "background:transparent;border:none;"
            )

            box.addLayout(top)
            box.addWidget(value)
            box.addWidget(hint_label)
            metrics.addWidget(card, 1)
            self.cloud_metric_values[key] = value

        layout.addLayout(metrics)

        # ---- Information
        info = QFrame()
        info.setObjectName("DocumentInfoCard")
        info.setStyleSheet(
            "QFrame#DocumentInfoCard{"
            "background:#F4F9FF;"
            "border:1px solid #DDEBFA;"
            "border-radius:14px;"
            "}"
        )
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(16, 13, 16, 13)
        info_layout.setSpacing(11)

        info_icon = QLabel("i")
        info_icon.setFixedSize(30, 30)
        info_icon.setAlignment(Qt.AlignCenter)
        info_icon.setStyleSheet(
            "background:#338CE4;color:white;border-radius:15px;"
            "font-size:13px;font-weight:900;"
        )

        info_text = QLabel(
            "Les Conventions, Programmes et Convocations sont générés avec les "
            "modèles officiels. Les Devis, Factures et Attestations sont déposés "
            "par l'administrateur puis téléchargés par le commercial concerné. "
            "Le commercial peut aussi déposer les Conventions et Devis signés en PDF."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color:#64748B;font-size:11px;")

        info_layout.addWidget(info_icon, 0, Qt.AlignTop)
        info_layout.addWidget(info_text, 1)
        layout.addWidget(info)

        # ---- Filtres / actions
        controls = QFrame()
        controls.setObjectName("DocumentFilters")
        controls.setStyleSheet(
            "QFrame#DocumentFilters{"
            "background:transparent;"
            "border:none;"
            "border-bottom:1px solid #E7EDF4;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(4, 4, 4, 12)
        controls_layout.setSpacing(9)

        controls_title = QHBoxLayout()
        controls_title.setSpacing(8)

        filters_label = QLabel("FILTRES DOCUMENTAIRES")
        filters_label.setStyleSheet(
            "color:#338CE4;font-size:10px;font-weight:900;letter-spacing:1px;"
        )
        filters_help = QLabel("Affinez les documents visibles dans l'espace Cloud")
        filters_help.setStyleSheet("color:#94A3B8;font-size:9px;")
        controls_title.addWidget(filters_label)
        controls_title.addWidget(filters_help)
        controls_title.addStretch()
        controls_layout.addLayout(controls_title)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.cloud_prospect_combo = QComboBox()
        self.cloud_prospect_combo.setMinimumWidth(280)
        self.cloud_prospect_combo.setMaximumWidth(520)
        self.cloud_prospect_combo.setMinimumHeight(38)
        self.cloud_prospect_combo.setStyleSheet(
            "QComboBox{background:white;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:0 34px 0 11px;font-size:11px;font-weight:700;}"
            "QComboBox:focus{border:2px solid #338CE4;}"
            "QComboBox::drop-down{border:none;border-left:1px solid #E6EDF5;width:28px;}"
        )
        self.cloud_prospect_combo.currentIndexChanged.connect(
            self._load_cloud_documents
        )
        toolbar.addWidget(self.cloud_prospect_combo)

        self.cloud_history_check = QCheckBox("Afficher l'historique des versions")
        self.cloud_history_check.setStyleSheet(
            "QCheckBox{color:#53657C;font-size:11px;font-weight:700;spacing:7px;}"
            "QCheckBox::indicator{width:16px;height:16px;}"
        )
        self.cloud_history_check.toggled.connect(self._load_cloud_documents)
        toolbar.addWidget(self.cloud_history_check)

        self.cloud_training_button = QPushButton("Gérer les formations")
        self.cloud_training_button.setStyleSheet(SECONDARY_BUTTON)
        self.cloud_training_button.clicked.connect(self._create_cloud_training)
        toolbar.addWidget(self.cloud_training_button)

        self.cloud_template_button = QPushButton("Uploader un modèle")
        self.cloud_template_button.setStyleSheet(SECONDARY_BUTTON)
        self.cloud_template_button.clicked.connect(self._upload_cloud_template)
        toolbar.addWidget(self.cloud_template_button)

        self.cloud_upload_button = QPushButton("Déposer un document")
        self.cloud_upload_button.setStyleSheet(PRIMARY_BUTTON)
        self.cloud_upload_button.clicked.connect(self._upload_cloud_document)
        toolbar.addWidget(self.cloud_upload_button)

        self.cloud_signed_upload_button = QPushButton("Déposer un document signé")
        self.cloud_signed_upload_button.setStyleSheet(PRIMARY_BUTTON)
        self.cloud_signed_upload_button.clicked.connect(self._upload_cloud_signed_document)
        toolbar.addWidget(self.cloud_signed_upload_button)

        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        # ---- Liste documentaire
        documents_card = self._card()
        documents_layout = QVBoxLayout(documents_card)
        documents_layout.setContentsMargins(14, 12, 14, 14)
        documents_layout.setSpacing(8)

        list_top = QHBoxLayout()
        list_title_box = QVBoxLayout()
        list_title_box.setSpacing(1)

        list_eyebrow = QLabel("BIBLIOTHÈQUE CLOUD")
        list_eyebrow.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
            "background:transparent;border:none;"
        )
        list_title = QLabel("Documents disponibles")
        list_title.setStyleSheet(
            "color:#0B1220;font-size:16px;font-weight:900;"
            "background:transparent;border:none;"
        )
        list_title_box.addWidget(list_eyebrow)
        list_title_box.addWidget(list_title)

        self.cloud_count_badge = QLabel("0 documents")
        self.cloud_count_badge.setAlignment(Qt.AlignCenter)
        self.cloud_count_badge.setMinimumWidth(92)
        self.cloud_count_badge.setFixedHeight(28)
        self.cloud_count_badge.setStyleSheet(
            "background:#EAF4FF;color:#0B5EA8;border:1px solid #BFDDFC;"
            "border-radius:9px;padding:0 10px;font-size:10px;font-weight:900;"
        )

        self.cloud_status = QLabel("Double-cliquez sur une ligne pour télécharger")
        self.cloud_status.setWordWrap(False)
        self.cloud_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cloud_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
            "background:transparent;border:none;"
        )

        list_top.addLayout(list_title_box)
        list_top.addStretch()
        list_top.addWidget(self.cloud_status)
        list_top.addWidget(self.cloud_count_badge)
        documents_layout.addLayout(list_top)

        self.cloud_table = QTableWidget(0, 7)
        self.cloud_table.setHorizontalHeaderLabels(
            [
                "Type",
                "Numéro",
                "Prospect / client",
                "Fichier",
                "Origine",
                "Version",
                "Créé le",
            ]
        )
        self._style_table(self.cloud_table)
        self.cloud_table.doubleClicked.connect(self._download_cloud_document)
        documents_layout.addWidget(self.cloud_table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self.cloud_download_button = QPushButton("Télécharger le document")
        self.cloud_download_button.setMinimumHeight(38)
        self.cloud_download_button.setEnabled(False)
        self.cloud_download_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:9px;"
            "padding:0 16px;font-size:11px;font-weight:900;}"
            "QPushButton:hover{background:#247BD0;}"
            "QPushButton:disabled{background:#DCE6F0;color:#94A3B8;}"
        )
        self.cloud_download_button.clicked.connect(self._download_cloud_document)
        self.cloud_table.itemSelectionChanged.connect(
            lambda: self.cloud_download_button.setEnabled(
                self.cloud_table.currentRow() >= 0
            )
        )
        actions.addWidget(self.cloud_download_button)

        documents_layout.addLayout(actions)
        layout.addWidget(documents_card, 1)
        return page

    def _build_trainings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(10)
        toolbar = QHBoxLayout()
        add = QPushButton("+ Nouvelle formation")
        add.setStyleSheet(PRIMARY_BUTTON)
        add.clicked.connect(self.add_training)
        edit = QPushButton("Modifier")
        edit.setStyleSheet(SECONDARY_BUTTON)
        edit.clicked.connect(self.edit_training)
        duplicate = QPushButton("Dupliquer")
        duplicate.setStyleSheet(SECONDARY_BUTTON)
        duplicate.clicked.connect(self.duplicate_training)
        toggle = QPushButton("Activer / désactiver")
        toggle.setStyleSheet(SECONDARY_BUTTON)
        toggle.clicked.connect(self.toggle_training)
        delete = QPushButton("Supprimer")
        delete.setStyleSheet(SECONDARY_BUTTON)
        delete.clicked.connect(self.delete_training)
        self.training_search = QLineEdit()
        self.training_search.setPlaceholderText("Rechercher une formation...")
        self.training_search.setMinimumWidth(220)
        self.training_search.textChanged.connect(self._load_trainings)
        toolbar.addWidget(add)
        toolbar.addWidget(edit)
        toolbar.addWidget(duplicate)
        toolbar.addWidget(toggle)
        toolbar.addWidget(delete)
        toolbar.addStretch()
        toolbar.addWidget(self.training_search)
        layout.addLayout(toolbar)
        self.trainings_table = QTableWidget(0, 9)
        self.trainings_table.setHorizontalHeaderLabels(
            [
                "Référence",
                "Formation",
                "Catégorie",
                "Durée",
                "Prix",
                "Modalité",
                "Places",
                "Certification",
                "Statut",
            ]
        )
        self._style_table(self.trainings_table)
        layout.addWidget(self.trainings_table, 1)
        return page

    def _build_templates_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(10)
        toolbar = QHBoxLayout()
        add = QPushButton("+ Nouveau modèle")
        add.setStyleSheet(PRIMARY_BUTTON)
        add.clicked.connect(self.add_template)
        edit = QPushButton("Modifier")
        edit.setStyleSheet(SECONDARY_BUTTON)
        edit.clicked.connect(self.edit_template)
        toggle = QPushButton("Activer / désactiver")
        toggle.setStyleSheet(SECONDARY_BUTTON)
        toggle.clicked.connect(self.toggle_template)
        toolbar.addWidget(add)
        toolbar.addWidget(edit)
        toolbar.addWidget(toggle)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.templates_table = QTableWidget(0, 6)
        self.templates_table.setHorizontalHeaderLabels(
            ["Nom", "Type", "Formation liée", "Fichier source", "Sortie", "Statut"]
        )
        self._style_table(self.templates_table)
        layout.addWidget(self.templates_table, 1)
        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(10)
        toolbar = QHBoxLayout()
        generate = QPushButton("+ Générer des documents")
        generate.setStyleSheet(PRIMARY_BUTTON)
        generate.clicked.connect(self.generate_documents)
        toolbar.addWidget(generate)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.documents_table = QTableWidget(0, 5)
        self.documents_table.setHorizontalHeaderLabels(
            ["Numéro", "Type", "Client", "Statut", "Fichier"]
        )
        self._style_table(self.documents_table)
        layout.addWidget(self.documents_table, 1)
        return page

    def _load_documents(self):
        rows = self.service.list_documents() if self.service else []
        self.documents_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                item["document_number"],
                item["document_type"],
                item.get("company_name") or "—",
                item["status"],
                item["file_path"],
            ]
            for col, value in enumerate(values):
                self.documents_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value)),
                )

    def _project(self):
        return (
            ApplicationState.get_project()
            if ApplicationState.has_project()
            else None
        )

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
        permissions = tuple(getattr(user, "permissions", ()) or ())
        return permission in permissions

    def _can_generate_cloud(self) -> bool:
        role = self._current_role()
        return role in {"admin", "administrateur", "administrator", "manager", "commercial"} or any(
            self._has_permission(permission)
            for permission in (
                "document:generate_all",
                "document:generate_assigned",
            )
        )

    def _can_admin_upload(self) -> bool:
        return self._current_role() in {"admin", "administrateur", "administrator"} or self._has_permission(
            "document:upload"
        )

    def _can_signed_upload(self) -> bool:
        # Le bouton est fonctionnellement destiné au Commercial.
        # Le backend reste l'autorité de sécurité et vérifie la permission
        # document:upload_signed_assigned lors de l'envoi.
        role = self._current_role()
        return (
            role in {"commercial"}
            or self._has_permission("document:upload_signed_assigned")
        )

    def _show_information_state(
        self,
        message: str,
        *,
        allow_generate: bool = False,
    ) -> None:
        self.service = None
        self.empty.setText(message)
        self.empty.setVisible(True)
        self.content.setVisible(False)
        self.cloud_content.setVisible(False)
        self.generate_button.setVisible(allow_generate)

    def generate_documents(self):
        if self._is_cloud():
            if not CloudRuntime.is_active():
                QMessageBox.warning(
                    self,
                    "Documents",
                    "La session Cloud n'est pas active. Reconnectez-vous.",
                )
                return
            if not self._can_generate_cloud():
                QMessageBox.warning(
                    self,
                    "Documents",
                    "Votre profil n'est pas autorisé à générer des documents.",
                )
                return
            initial_prospect_id = self.cloud_prospect_combo.currentData()
            dialog = CloudGenerateDocumentsDialog(
                CloudRuntime.api(),
                self,
                initial_prospect_id=(
                    str(initial_prospect_id) if initial_prospect_id else None
                ),
            )
            if dialog.exec():
                self._load_cloud_documents()
            return

        project = self._project()
        if project is None:
            QMessageBox.information(
                self,
                "Documents",
                "Ouvrez d'abord un projet local.",
            )
            return
        service = DocumentGeneratorService(project.database, project.folder)
        dialog = GenerateDocumentsDialog(service, self)
        dialog.exec()
        self.rafraichir()

    def _build_foundations_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 14, 0, 0)
        card = self._card()
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 20, 22, 20)
        box.setSpacing(10)
        heading = QLabel("Fondations installées")
        heading.setStyleSheet(f"color:{TEXT}; font-size:18px; font-weight:900;")
        text = QLabel(
            "✓ Catalogue des formations\n"
            "✓ Gestion des modèles Devis, Convention, Programme, Convocation, "
            "Facture et Attestation\n"
            "✓ Séquences de numérotation uniques par type de document\n"
            "✓ Paramètres documentaires et table d'historique\n\n"
            "✓ Assistant « Transformer en client »\n"
            "✓ Génération automatique DOCX/PDF pour devis, convention, programme "
            "et convocation\n"
            "✓ Fusion des variables et classement automatique dans le dossier client"
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color:{MUTED}; font-size:13px; line-height:1.5;")
        box.addWidget(heading)
        box.addWidget(text)
        box.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return page

    @staticmethod
    def _document_type_badge_style(doc_type: str) -> str:
        value = (doc_type or "").strip().lower()

        palette = {
            "convention": ("#EFF6FF", "#1D4ED8", "#BFDBFE"),
            "convocation": ("#F5F3FF", "#6D28D9", "#DDD6FE"),
            "programme": ("#FFF7ED", "#C2410C", "#FED7AA"),
            "devis": ("#F0FDF4", "#15803D", "#BBF7D0"),
            "facture": ("#ECFDF5", "#047857", "#A7F3D0"),
            "attestation de formation": ("#FFF7ED", "#B45309", "#FDE68A"),
        }
        bg, fg, border = palette.get(
            value,
            ("#F8FAFC", "#475569", "#E2E8F0"),
        )
        return (
            f"background:{bg};color:{fg};border:1px solid {border};"
            "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        )

    @staticmethod
    def _document_origin_badge_style(origin: str) -> str:
        value = (origin or "").strip().lower()

        if "généré" in value or "genere" in value:
            return (
                "background:#ECFDF5;color:#047857;border:1px solid #A7F3D0;"
                "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
            )

        return (
            "background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE;"
            "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
        )

    def _style_table(self, table: QTableWidget):
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setMinimumHeight(40)
        table.horizontalHeader().setStretchLastSection(False)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet(
            "QTableWidget{"
            "background:#FFFFFF;"
            "color:#172033;"
            "border:1px solid #E4EBF4;"
            "border-radius:12px;"
            "selection-background-color:#EAF4FF;"
            "selection-color:#0B1220;"
            "font-size:11px;"
            "}"
            "QTableWidget::item{"
            "background:#FFFFFF;"
            "border-bottom:1px solid #EEF3F8;"
            "padding:7px 8px;"
            "}"
            "QTableWidget::item:selected{"
            "background:#EAF4FF;"
            "color:#0B1220;"
            "}"
            "QHeaderView::section{"
            "background:#0B2A52;"
            "color:#FFFFFF;"
            "border:none;"
            "border-right:1px solid #173C68;"
            "padding:9px 8px;"
            "font-size:10px;"
            "font-weight:900;"
            "}"
        )

    def rafraichir(self):
        if self._is_cloud():
            if not CloudRuntime.is_active():
                self._show_information_state(
                    "La session Form@Prospect Cloud n'est pas active. "
                    "Reconnectez-vous pour accéder aux documents.",
                    allow_generate=False,
                )
                return
            self._load_cloud_mode()
            return

        self.cloud_content.setVisible(False)
        self.subtitle.setText(
            "Préparez le catalogue des formations et les modèles qui "
            "alimenteront le moteur documentaire."
        )
        project = self._project()
        if project is None:
            self._show_information_state(
                "Ouvrez un projet local pour accéder au moteur documentaire.",
                allow_generate=True,
            )
            return

        try:
            self.service = DocumentService(project.database)
            self.service.ensure_official_templates()
            self.service.ensure_default_training()
            self.empty.setVisible(False)
            self.content.setVisible(True)
            self.generate_button.setVisible(True)
            stats = self.service.stats()
            for key in self.kpi_labels:
                self.kpi_labels[key].setText(str(getattr(stats, key)))
            self._load_trainings()
            self._load_templates()
            self._load_documents()
        except Exception as exc:
            self._show_information_state(
                "Impossible de charger le module Documents.\n\n"
                f"Détail : {exc}",
                allow_generate=False,
            )

    def _load_cloud_mode(self) -> None:
        self.service = None
        self.content.setVisible(False)
        self.empty.setVisible(False)
        self.cloud_content.setVisible(True)
        self.subtitle.setText(
            "Générez, déposez et téléchargez les documents depuis l'espace Cloud privé."
        )

        can_generate = self._can_generate_cloud()
        can_upload = self._can_admin_upload()
        can_signed_upload = self._can_signed_upload()
        self.generate_button.setVisible(can_generate)
        self.cloud_upload_button.setVisible(can_upload)
        self.cloud_signed_upload_button.setVisible(can_signed_upload)
        self.cloud_training_button.setVisible(can_upload)
        self.cloud_template_button.setVisible(can_upload)

        api = CloudRuntime.api()
        selected_id = self.cloud_prospect_combo.currentData()
        try:
            self.cloud_prospects = api.list_prospects(
                include_archived=False,
                limit=500,
            ).items
        except CloudAPIError as exc:
            self.cloud_status.setText(f"⛔ {exc}")
            self.cloud_status.setStyleSheet("color:#B42318;")
            self.cloud_table.setRowCount(0)
            return

        self.cloud_prospect_names = {
            str(item.get("id") or ""): str(
                item.get("company_name") or "Prospect sans nom"
            )
            for item in self.cloud_prospects
        }
        self.cloud_prospect_combo.blockSignals(True)
        self.cloud_prospect_combo.clear()
        self.cloud_prospect_combo.addItem("Tous les prospects visibles", None)
        restore_index = 0
        for index, prospect in enumerate(self.cloud_prospects, start=1):
            prospect_id = str(prospect.get("id") or "")
            self.cloud_prospect_combo.addItem(
                str(prospect.get("company_name") or "Prospect sans nom"),
                prospect_id,
            )
            if selected_id and str(selected_id) == prospect_id:
                restore_index = index
        self.cloud_prospect_combo.setCurrentIndex(restore_index)
        self.cloud_prospect_combo.blockSignals(False)
        self._load_cloud_documents()

    def _load_cloud_documents(self, *_args) -> None:
        if not self._is_cloud() or not CloudRuntime.is_active():
            return
        prospect_id = self.cloud_prospect_combo.currentData()
        try:
            self.cloud_documents = CloudRuntime.api().list_cloud_documents(
                prospect_id=str(prospect_id) if prospect_id else None,
                include_history=self.cloud_history_check.isChecked(),
                include_archived=False,
                limit=500,
            )
        except CloudAPIError as exc:
            self.cloud_status.setText(f"⛔ {exc}")
            self.cloud_status.setStyleSheet("color:#B42318;")
            self.cloud_table.setRowCount(0)
            return

        generated_count = sum(
            1 for item in self.cloud_documents
            if item.get("origin") == "generated"
        )
        uploaded_count = len(self.cloud_documents) - generated_count
        if hasattr(self, "cloud_metric_values"):
            self.cloud_metric_values["documents"].setText(str(len(self.cloud_documents)))
            self.cloud_metric_values["generated"].setText(str(generated_count))
            self.cloud_metric_values["uploaded"].setText(str(uploaded_count))

        self.cloud_download_button.setEnabled(False)
        self.cloud_table.clearSelection()
        self.cloud_table.setRowCount(len(self.cloud_documents))
        for row_index, document in enumerate(self.cloud_documents):
            self.cloud_table.setRowHeight(row_index, 44)
            prospect_name = self.cloud_prospect_names.get(
                str(document.get("prospect_id") or ""),
                "Prospect visible",
            )
            if document.get("origin") == "generated":
                origin = "Généré"
            else:
                storage_path = str(document.get("storage_path") or "").lower()
                origin = (
                    "Document signé déposé"
                    if "signe" in storage_path
                    else "Déposé par l'administration"
                )
            created = str(document.get("created_at") or "")
            if created:
                created = created.replace("T", " ")[:16]
            values = [
                document.get("document_type") or "—",
                document.get("document_number") or "—",
                prospect_name,
                document.get("original_filename") or "—",
                origin,
                document.get("version") or 1,
                created or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(Qt.UserRole, str(document.get("id") or ""))
                    self.cloud_table.setItem(row_index, column, item)

                    type_badge = QLabel(str(value))
                    type_badge.setAlignment(Qt.AlignCenter)
                    type_badge.setFixedHeight(26)
                    type_badge.setStyleSheet(self._document_type_badge_style(str(value)))
                    self.cloud_table.setCellWidget(row_index, column, type_badge)
                    continue

                if column == 4:
                    self.cloud_table.setItem(row_index, column, item)

                    origin_badge = QLabel(str(value))
                    origin_badge.setAlignment(Qt.AlignCenter)
                    origin_badge.setFixedHeight(26)
                    origin_badge.setStyleSheet(self._document_origin_badge_style(str(value)))
                    self.cloud_table.setCellWidget(row_index, column, origin_badge)
                    continue

                if column in (1, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                elif column == 2:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif column == 3:
                    full_name = str(value)
                    item.setToolTip(full_name)

                self.cloud_table.setItem(row_index, column, item)

        count = len(self.cloud_documents)
        if hasattr(self, "cloud_count_badge"):
            self.cloud_count_badge.setText(
                f"{count} document" if count == 1 else f"{count} documents"
            )

        self.cloud_status.setText(
            "Double-cliquez sur une ligne pour télécharger"
        )
        self.cloud_status.setStyleSheet(
            "color:#8A98AA;font-size:9px;font-weight:700;"
        )

    def _selected_cloud_document(self) -> dict | None:
        row = self.cloud_table.currentRow()
        if row < 0 or row >= len(self.cloud_documents):
            QMessageBox.information(
                self,
                "Document",
                "Sélectionnez d'abord un document.",
            )
            return None
        return self.cloud_documents[row]

    def _download_cloud_document(self, *_args) -> None:
        document = self._selected_cloud_document()
        if not document:
            return
        filename = str(document.get("original_filename") or "document")
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Télécharger le document",
            filename,
            "Tous les fichiers (*.*)",
        )
        if not destination:
            return
        try:
            saved = CloudRuntime.api().download_cloud_document(
                str(document.get("id") or ""),
                destination,
            )
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

    def _create_cloud_training(self) -> None:
        if not self._can_admin_upload():
            return
        dialog = CloudTrainingManagementDialog(
            CloudRuntime.api(),
            self,
        )
        dialog.exec()
        if dialog.changed:
            self.rafraichir()

    def _upload_cloud_template(self) -> None:
        if not self._can_admin_upload():
            return
        CloudTemplateUploadDialog(CloudRuntime.api(), self).exec()

    def _upload_cloud_document(self) -> None:
        if not self._can_admin_upload():
            return
        prospect_id = self.cloud_prospect_combo.currentData()
        dialog = CloudAdministrativeUploadDialog(
            CloudRuntime.api(),
            self,
            initial_prospect_id=(str(prospect_id) if prospect_id else None),
        )
        if dialog.exec():
            self._load_cloud_documents()

    def _upload_cloud_signed_document(self) -> None:
        if not self._can_signed_upload():
            return

        if not self.cloud_prospects:
            QMessageBox.information(
                self,
                "Document signé",
                "Aucun prospect ou client n'est disponible pour le dépôt.",
            )
            return

        prospect_id = self.cloud_prospect_combo.currentData()
        dialog = CloudSignedDocumentUploadDialog(
            CloudRuntime.api(),
            self.cloud_prospects,
            self,
            initial_prospect_id=(str(prospect_id) if prospect_id else None),
        )
        if dialog.exec():
            self._load_cloud_documents()

    def _load_trainings(self):
        rows = self.service.list_trainings() if self.service else []
        query = (
            self.training_search.text().strip().lower()
            if hasattr(self, "training_search")
            else ""
        )
        self.training_rows = [
            item
            for item in rows
            if not query
            or query
            in (
                f"{item.get('reference', '')} {item.get('name', '')} "
                f"{item.get('category', '')}"
            ).lower()
        ]
        self.trainings_table.setRowCount(len(self.training_rows))
        for row, item in enumerate(self.training_rows):
            values = [
                item["reference"],
                item["name"],
                item.get("category") or "—",
                f"{item['duration_hours']:g} h",
                f"{item['price_cents']/100:,.2f} €".replace(",", " "),
                item["modality"],
                item.get("max_participants", 8),
                item["certification"] or "—",
                "Active" if item["active"] else "Inactive",
            ]
            for col, value in enumerate(values):
                self.trainings_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value)),
                )

    def _load_templates(self):
        self.template_rows = self.service.list_templates() if self.service else []
        self.templates_table.setRowCount(len(self.template_rows))
        for row, item in enumerate(self.template_rows):
            values = [
                item["name"],
                item["document_type"],
                item.get("training_name") or "Toutes",
                item["source_path"] or "À sélectionner",
                item["output_format"],
                "Actif" if item["active"] else "Inactif",
            ]
            for col, value in enumerate(values):
                self.templates_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value)),
                )

    def _selected(
        self,
        table: QTableWidget,
        rows: list[dict],
    ) -> dict | None:
        row = table.currentRow()
        if row < 0 or row >= len(rows):
            QMessageBox.information(
                self,
                "Sélection",
                "Sélectionnez d'abord une ligne.",
            )
            return None
        return rows[row]

    def add_training(self):
        if self.service and TrainingDialog(self.service, parent=self).exec():
            self.rafraichir()

    def edit_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item and TrainingDialog(self.service, item, self).exec():
            self.rafraichir()

    def toggle_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item:
            self.service.set_training_active(item["id"], not bool(item["active"]))
            self.rafraichir()

    def duplicate_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item:
            self.service.duplicate_training(item["id"])
            self.rafraichir()

    def delete_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if not item:
            return
        if (
            QMessageBox.question(
                self,
                "Supprimer la formation",
                f"Supprimer définitivement « {item['name']} » ?",
            )
            != QMessageBox.Yes
        ):
            return
        try:
            self.service.delete_training(item["id"])
        except ValueError as exc:
            QMessageBox.warning(self, "Suppression impossible", str(exc))
            return
        self.rafraichir()

    def add_template(self):
        if self.service and DocumentTemplateDialog(
            self.service,
            parent=self,
        ).exec():
            self.rafraichir()

    def edit_template(self):
        item = self._selected(self.templates_table, self.template_rows)
        if item and DocumentTemplateDialog(self.service, item, self).exec():
            self.rafraichir()

    def toggle_template(self):
        item = self._selected(self.templates_table, self.template_rows)
        if item:
            self.service.set_template_active(item["id"], not bool(item["active"]))
            self.rafraichir()
