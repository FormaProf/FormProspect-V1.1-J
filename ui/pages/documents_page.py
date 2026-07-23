from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLineEdit,
)

from core.application_state import ApplicationState
from core.premium_theme import BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from services.document_service import DocumentService
from services.document_generator_service import DocumentGeneratorService
from ui.dialogs.generate_documents_dialog import GenerateDocumentsDialog
from ui.dialogs.document_template_dialog import DocumentTemplateDialog
from ui.dialogs.training_dialog import TrainingDialog


class DocumentsPage(QWidget):
    """RC2.0.1 — catalogue de formations et modèles documentaires."""

    def __init__(self):
        super().__init__()
        self.service: DocumentService | None = None
        self.training_rows: list[dict] = []
        self.template_rows: list[dict] = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("DocumentCard")
        card.setStyleSheet(f"QFrame#DocumentCard{{background:{CARD}; border:1px solid {BORDER}; border-radius:16px;}}")
        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 30)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Documents")
        title.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:900;")
        subtitle = QLabel("Préparez le catalogue des formations et les modèles qui alimenteront le moteur documentaire.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        title_box.addWidget(title); title_box.addWidget(subtitle)
        header.addLayout(title_box); header.addStretch()
        generate = QPushButton("Générer des documents")
        generate.setStyleSheet(PRIMARY_BUTTON)
        generate.clicked.connect(self.generate_documents)
        header.addWidget(generate)
        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)
        header.addWidget(refresh)
        root.addLayout(header)

        self.empty = QLabel("Ouvrez un projet pour accéder au moteur documentaire.")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(95)
        self.empty.setStyleSheet(f"background:white; color:{MUTED}; border:1px dashed {BORDER}; border-radius:14px;")
        root.addWidget(self.empty)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        kpis = QGridLayout(); kpis.setSpacing(10)
        self.kpi_labels = {}
        for col, (key, caption) in enumerate([
            ("trainings", "Formations"), ("templates", "Modèles"),
            ("active_templates", "Modèles actifs"), ("documents", "Documents générés"),
        ]):
            card = self._card(); box = QVBoxLayout(card)
            label = QLabel(caption); label.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:800;")
            value = QLabel("0"); value.setStyleSheet(f"color:{NAVY}; font-size:25px; font-weight:900;")
            box.addWidget(label); box.addWidget(value); kpis.addWidget(card, 0, col)
            self.kpi_labels[key] = value
        content_layout.addLayout(kpis)

        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab{padding:10px 18px; font-weight:700;} QTabWidget::pane{border:0;}")
        tabs.addTab(self._build_trainings_tab(), "Catalogue des formations")
        tabs.addTab(self._build_templates_tab(), "Modèles documentaires")
        tabs.addTab(self._build_history_tab(), "Documents générés")
        tabs.addTab(self._build_foundations_tab(), "Fondations RC2")
        content_layout.addWidget(tabs, 1)
        root.addWidget(self.content, 1)
        self.content.setVisible(False)

    def _build_trainings_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 14, 0, 0); layout.setSpacing(10)
        toolbar = QHBoxLayout()
        add = QPushButton("+ Nouvelle formation"); add.setStyleSheet(PRIMARY_BUTTON); add.clicked.connect(self.add_training)
        edit = QPushButton("Modifier"); edit.setStyleSheet(SECONDARY_BUTTON); edit.clicked.connect(self.edit_training)
        duplicate = QPushButton("Dupliquer"); duplicate.setStyleSheet(SECONDARY_BUTTON); duplicate.clicked.connect(self.duplicate_training)
        toggle = QPushButton("Activer / désactiver"); toggle.setStyleSheet(SECONDARY_BUTTON); toggle.clicked.connect(self.toggle_training)
        delete = QPushButton("Supprimer"); delete.setStyleSheet(SECONDARY_BUTTON); delete.clicked.connect(self.delete_training)
        self.training_search = QLineEdit(); self.training_search.setPlaceholderText("Rechercher une formation..."); self.training_search.setMinimumWidth(220); self.training_search.textChanged.connect(self._load_trainings)
        toolbar.addWidget(add); toolbar.addWidget(edit); toolbar.addWidget(duplicate); toolbar.addWidget(toggle); toolbar.addWidget(delete); toolbar.addStretch(); toolbar.addWidget(self.training_search); layout.addLayout(toolbar)
        self.trainings_table = QTableWidget(0, 9)
        self.trainings_table.setHorizontalHeaderLabels(["Référence", "Formation", "Catégorie", "Durée", "Prix", "Modalité", "Places", "Certification", "Statut"])
        self._style_table(self.trainings_table)
        layout.addWidget(self.trainings_table, 1)
        return page

    def _build_templates_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 14, 0, 0); layout.setSpacing(10)
        toolbar = QHBoxLayout()
        add = QPushButton("+ Nouveau modèle"); add.setStyleSheet(PRIMARY_BUTTON); add.clicked.connect(self.add_template)
        edit = QPushButton("Modifier"); edit.setStyleSheet(SECONDARY_BUTTON); edit.clicked.connect(self.edit_template)
        toggle = QPushButton("Activer / désactiver"); toggle.setStyleSheet(SECONDARY_BUTTON); toggle.clicked.connect(self.toggle_template)
        toolbar.addWidget(add); toolbar.addWidget(edit); toolbar.addWidget(toggle); toolbar.addStretch(); layout.addLayout(toolbar)
        self.templates_table = QTableWidget(0, 6)
        self.templates_table.setHorizontalHeaderLabels(["Nom", "Type", "Formation liée", "Fichier source", "Sortie", "Statut"])
        self._style_table(self.templates_table)
        layout.addWidget(self.templates_table, 1)
        return page


    def _build_history_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 14, 0, 0); layout.setSpacing(10)
        toolbar = QHBoxLayout()
        generate = QPushButton("+ Générer des documents"); generate.setStyleSheet(PRIMARY_BUTTON); generate.clicked.connect(self.generate_documents)
        toolbar.addWidget(generate); toolbar.addStretch(); layout.addLayout(toolbar)
        self.documents_table = QTableWidget(0, 5)
        self.documents_table.setHorizontalHeaderLabels(["Numéro", "Type", "Client", "Statut", "Fichier"])
        self._style_table(self.documents_table); layout.addWidget(self.documents_table, 1)
        return page

    def _load_documents(self):
        rows = self.service.list_documents() if self.service else []
        self.documents_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [item["document_number"], item["document_type"], item.get("company_name") or "—", item["status"], item["file_path"]]
            for col, value in enumerate(values): self.documents_table.setItem(row, col, QTableWidgetItem(str(value)))

    def generate_documents(self):
        if not ApplicationState.has_project():
            QMessageBox.information(self, "Documents", "Ouvrez d’abord un projet."); return
        project = ApplicationState.get_project()
        service = DocumentGeneratorService(project.database, project.folder)
        dialog = GenerateDocumentsDialog(service, self)
        dialog.exec()
        self.rafraichir()

    def _build_foundations_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 14, 0, 0)
        card = self._card(); box = QVBoxLayout(card); box.setContentsMargins(22, 20, 22, 20); box.setSpacing(10)
        heading = QLabel("Fondations installées")
        heading.setStyleSheet(f"color:{TEXT}; font-size:18px; font-weight:900;")
        text = QLabel(
            "✓ Catalogue des formations\n"
            "✓ Gestion des modèles Devis, Convention, Programme, Convocation, Facture et Attestation\n"
            "✓ Séquences de numérotation uniques par type de document\n"
            "✓ Paramètres documentaires et table d'historique\n\n"
            "✓ Assistant « Transformer en client »\n"
            "✓ Génération automatique DOCX/PDF pour devis, convention, programme et convocation\n"
            "✓ Fusion des variables et classement automatique dans le dossier client"
        )
        text.setWordWrap(True); text.setStyleSheet(f"color:{MUTED}; font-size:13px; line-height:1.5;")
        box.addWidget(heading); box.addWidget(text); box.addStretch(); layout.addWidget(card); layout.addStretch()
        return page

    def _style_table(self, table: QTableWidget):
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(
            f"QTableWidget{{background:white; alternate-background-color:#F8FAFC; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px; gridline-color:{BORDER};}}"
            f"QHeaderView::section{{background:#F8FAFC; color:{MUTED}; border:none; border-bottom:1px solid {BORDER}; padding:9px; font-weight:800;}}"
        )

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.service = None; self.empty.setVisible(True); self.content.setVisible(False); return
        self.service = DocumentService(ApplicationState.get_project().database)
        self.service.ensure_official_templates()
        self.service.ensure_default_training()
        self.empty.setVisible(False); self.content.setVisible(True)
        stats = self.service.stats()
        for key in self.kpi_labels: self.kpi_labels[key].setText(str(getattr(stats, key)))
        self._load_trainings(); self._load_templates(); self._load_documents()

    def _load_trainings(self):
        rows = self.service.list_trainings() if self.service else []
        query = self.training_search.text().strip().lower() if hasattr(self, "training_search") else ""
        self.training_rows = [item for item in rows if not query or query in (f"{item.get('reference','')} {item.get('name','')} {item.get('category','')}").lower()]
        self.trainings_table.setRowCount(len(self.training_rows))
        for row, item in enumerate(self.training_rows):
            values = [item["reference"], item["name"], item.get("category") or "—", f"{item['duration_hours']:g} h", f"{item['price_cents']/100:,.2f} €".replace(",", " "),
                      item["modality"], item.get("max_participants", 8), item["certification"] or "—", "Active" if item["active"] else "Inactive"]
            for col, value in enumerate(values): self.trainings_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _load_templates(self):
        self.template_rows = self.service.list_templates() if self.service else []
        self.templates_table.setRowCount(len(self.template_rows))
        for row, item in enumerate(self.template_rows):
            values = [item["name"], item["document_type"], item.get("training_name") or "Toutes", item["source_path"] or "À sélectionner",
                      item["output_format"], "Actif" if item["active"] else "Inactif"]
            for col, value in enumerate(values): self.templates_table.setItem(row, col, QTableWidgetItem(str(value)))

    def _selected(self, table: QTableWidget, rows: list[dict]) -> dict | None:
        row = table.currentRow()
        if row < 0 or row >= len(rows):
            QMessageBox.information(self, "Sélection", "Sélectionnez d'abord une ligne."); return None
        return rows[row]

    def add_training(self):
        if self.service and TrainingDialog(self.service, parent=self).exec(): self.rafraichir()

    def edit_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item and TrainingDialog(self.service, item, self).exec(): self.rafraichir()

    def toggle_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item: self.service.set_training_active(item["id"], not bool(item["active"])); self.rafraichir()

    def duplicate_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if item:
            self.service.duplicate_training(item["id"]); self.rafraichir()

    def delete_training(self):
        item = self._selected(self.trainings_table, self.training_rows)
        if not item: return
        if QMessageBox.question(self, "Supprimer la formation", f"Supprimer définitivement « {item['name']} » ?") != QMessageBox.Yes: return
        try:
            self.service.delete_training(item["id"])
        except ValueError as exc:
            QMessageBox.warning(self, "Suppression impossible", str(exc)); return
        self.rafraichir()

    def add_template(self):
        if self.service and DocumentTemplateDialog(self.service, parent=self).exec(): self.rafraichir()

    def edit_template(self):
        item = self._selected(self.templates_table, self.template_rows)
        if item and DocumentTemplateDialog(self.service, item, self).exec(): self.rafraichir()

    def toggle_template(self):
        item = self._selected(self.templates_table, self.template_rows)
        if item: self.service.set_template_active(item["id"], not bool(item["active"])); self.rafraichir()
