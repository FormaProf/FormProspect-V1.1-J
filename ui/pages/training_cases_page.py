from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QComboBox,
)

from core.application_state import ApplicationState
from core.premium_theme import PAGE_BG, PRIMARY_BUTTON, SECONDARY_BUTTON
from core.session import SessionState
from services.training_case_service import TrainingCaseService
from ui.dialogs.quote_request_dialog import QuoteRequestDialog


class TrainingCasesPage(QWidget):
    """RC2.1.2 — dossiers formation, devis téléchargeables et suppression admin."""

    def __init__(self):
        super().__init__()
        self.service = None
        self.case_rows = []
        self.quote_rows = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("Dossiers formation")
        title.setStyleSheet("font-size:27px;font-weight:900;color:#0B1F3A;")
        subtitle = QLabel("Centralisez les clients, sessions, financeurs, documents et demandes de devis.")
        subtitle.setStyleSheet("color:#64748B;font-size:13px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.addTab(self._cases_tab(), "Dossiers")
        self.tabs.addTab(self._quotes_tab(), "Demandes de devis")

    def _cases_tab(self):
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
        self.case_table.setHorizontalHeaderLabels([
            "Client", "Formation", "Dates", "Modalité", "Participants",
            "Commercial", "Financeur", "Étape", "Devis",
        ])
        self.case_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.case_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.case_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.case_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.case_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.case_table.itemDoubleClicked.connect(lambda _item: self._download_case_quote())
        layout.addWidget(self.case_table, 1)
        return page

    def _quotes_tab(self):
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
        self.quote_table.setHorizontalHeaderLabels([
            "Client", "Formation", "Dates", "Demandeur", "Note", "Statut", "PDF", "Créée le",
        ])
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

    def _ensure_service(self):
        if not ApplicationState.has_project():
            return False

        project = ApplicationState.get_project()
        db = getattr(project, "database", None) or getattr(project, "database_path", None)
        if db is None:
            QMessageBox.critical(self, "Projet incompatible", "Impossible de localiser la base de données du projet ouvert.")
            return False

        db = Path(db)
        if not self.service or Path(self.service.database_path) != db:
            self.service = TrainingCaseService(db)
        return True

    def rafraichir(self):
        if not self._ensure_service():
            return
        self._load_cases()
        self._load_quotes()

    def _load_cases(self):
        if not self._ensure_service():
            return
        self.case_rows = self.service.list_cases(self.search.text() if hasattr(self, "search") else "")
        self.case_table.setRowCount(len(self.case_rows))
        for r, row in enumerate(self.case_rows):
            values = [
                row["company_name"], row["training_name"], f"{row['start_date']} → {row['end_date']}",
                row["modality"], str(row["participant_count"]), row["commercial_name"], row["funder"],
                f"{row['current_step']} ({row['progress_percent']} %)", row["quote_status"],
            ]
            for c, value in enumerate(values):
                self.case_table.setItem(r, c, QTableWidgetItem(str(value or "—")))

    def _load_quotes(self):
        if not self._ensure_service():
            return
        self.quote_rows = self.service.list_quote_requests()
        self.quote_table.setRowCount(len(self.quote_rows))
        for r, row in enumerate(self.quote_rows):
            values = [
                row["company_name"], row["training_name"], f"{row['start_date']} → {row['end_date']}",
                row["requested_by"], row["note"], row["status"],
                "Disponible" if row["quote_file_path"] else "—", row["created_at"].replace("T", " "),
            ]
            for c, value in enumerate(values):
                self.quote_table.setItem(r, c, QTableWidgetItem(str(value or "—")))

    def _selected_case(self):
        row = self.case_table.currentRow()
        return self.case_rows[row] if 0 <= row < len(self.case_rows) else None

    def _selected_quote(self):
        row = self.quote_table.currentRow()
        return self.quote_rows[row] if 0 <= row < len(self.quote_rows) else None

    def _save_quote_copy(self, source: Path):
        target, _ = QFileDialog.getSaveFileName(self, "Télécharger le devis", source.name, "Documents PDF (*.pdf)")
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

    def _download_case_quote(self):
        case = self._selected_case()
        if not case:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez un dossier formation.")
            return
        request_id = case.get("quote_request_id")
        if not request_id or not case.get("quote_file_path"):
            QMessageBox.information(self, "Devis indisponible", "Aucun devis PDF n'a encore été importé pour ce dossier.")
            return
        try:
            source = self.service.get_quote_file(int(request_id))
        except Exception as exc:
            QMessageBox.critical(self, "Devis indisponible", str(exc))
            return
        self._save_quote_copy(source)

    def _download_selected_quote(self):
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

    def _request_quote(self):
        case = self._selected_case()
        if not case:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez un dossier formation.")
            return
        dlg = QuoteRequestDialog(case, self)
        if dlg.exec():
            user = SessionState.user()
            requested_by = user.display_name if user else case.get("commercial_name", "")
            try:
                self.service.create_quote_request(case["session_id"], requested_by, dlg.note.toPlainText())
            except Exception as exc:
                QMessageBox.critical(self, "Demande impossible", str(exc))
                return
            self.rafraichir()
            self.tabs.setCurrentIndex(1)
            QMessageBox.information(self, "Demande envoyée", "La demande de devis a été transmise à l'administrateur.")

    def _update_status(self):
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

    def _import_quote(self):
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

    def _delete_case(self):
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
