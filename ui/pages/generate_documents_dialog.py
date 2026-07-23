from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from core.premium_theme import BORDER, CARD, MUTED, NAVY, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from services.document_generator_service import DocumentGeneratorService


class GenerateDocumentsDialog(QDialog):
    def __init__(self, service: DocumentGeneratorService, parent=None):
        super().__init__(parent)
        self.service = service
        self.sessions = service.list_sessions()
        self.last_folder: Path | None = None
        self.setWindowTitle("Générer les documents")
        self.resize(720, 620)
        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(24, 22, 24, 22); root.setSpacing(14)
        title = QLabel("Génération automatique")
        title.setStyleSheet(f"color:{TEXT}; font-size:24px; font-weight:900;")
        subtitle = QLabel("Sélectionnez une session puis les documents à produire. Les fichiers seront classés automatiquement dans le dossier client.")
        subtitle.setWordWrap(True); subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title); root.addWidget(subtitle)

        card = QFrame(); card.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;")
        form = QFormLayout(card); form.setContentsMargins(18, 16, 18, 16); form.setSpacing(12)
        self.session_combo = QComboBox(); self.session_combo.currentIndexChanged.connect(self._refresh_summary)
        form.addRow("Dossier / session", self.session_combo)
        root.addWidget(card)

        types_card = QFrame(); types_card.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;")
        types_layout = QVBoxLayout(types_card); types_layout.setContentsMargins(18, 16, 18, 16)
        types_layout.addWidget(QLabel("Documents à générer"))
        checks = QHBoxLayout()
        self.type_checks = {}
        for doc_type in self.service.SUPPORTED_TYPES:
            check = QCheckBox(doc_type); check.setChecked(True)
            self.type_checks[doc_type] = check; checks.addWidget(check)
        checks.addStretch(); types_layout.addLayout(checks)
        self.pdf_check = QCheckBox("Créer également les PDF lorsque Word ou LibreOffice est disponible")
        self.pdf_check.setChecked(True); types_layout.addWidget(self.pdf_check)
        root.addWidget(types_card)

        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True); self.summary.setMinimumHeight(170)
        self.summary.setStyleSheet(f"background:#F8FAFC; color:{NAVY}; border:1px solid {BORDER}; border-radius:10px; padding:10px;")
        root.addWidget(self.summary, 1)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Ouvrir le dossier"); self.open_button.setStyleSheet(SECONDARY_BUTTON)
        self.open_button.setEnabled(False); self.open_button.clicked.connect(self._open_folder)
        actions.addWidget(self.open_button); actions.addStretch()
        cancel = QPushButton("Fermer"); cancel.setStyleSheet(SECONDARY_BUTTON); cancel.clicked.connect(self.reject)
        generate = QPushButton("Générer maintenant"); generate.setStyleSheet(PRIMARY_BUTTON); generate.clicked.connect(self._generate)
        actions.addWidget(cancel); actions.addWidget(generate); root.addLayout(actions)

    def _load_sessions(self):
        self.session_combo.clear()
        for session in self.sessions:
            label = f"{session['company_name']} — {session['training_name']} — {session['start_date']}"
            self.session_combo.addItem(label, int(session["session_id"]))
        if not self.sessions:
            self.session_combo.addItem("Aucune session client disponible", None)
            self.summary.setPlainText("Transformez d’abord un prospect en client depuis la page Prospects.")
        else:
            self._refresh_summary()

    def _refresh_summary(self):
        index = self.session_combo.currentIndex()
        if index < 0 or index >= len(self.sessions): return
        s = self.sessions[index]
        self.summary.setPlainText(
            f"CLIENT\n{s['company_name']}\n{s.get('siret') or 'SIRET non renseigné'}\n\n"
            f"FORMATION\n{s['training_name']} ({s['duration_hours']:g} h)\n"
            f"Du {s['start_date']} au {s['end_date']} — {s['daily_schedule']}\n"
            f"Modalité : {s['modality']}\nFormateur : {s.get('trainer_name') or 'Non renseigné'}\n"
            f"Financeur : {s.get('funder') or 'Entreprise'}\n"
            f"Prix : {s['price_cents']/100:,.2f} €".replace(",", " ")
        )

    def _generate(self):
        session_id = self.session_combo.currentData()
        if session_id is None:
            QMessageBox.information(self, "Génération", "Aucune session client n’est disponible."); return
        selected = [name for name, check in self.type_checks.items() if check.isChecked()]
        try:
            results = self.service.generate(session_id=int(session_id), document_types=selected, generate_pdf=self.pdf_check.isChecked())
        except Exception as exc:
            QMessageBox.critical(self, "Génération impossible", str(exc)); return
        self.last_folder = results[0].docx_path.parent.parent if results else None
        self.open_button.setEnabled(bool(self.last_folder))
        pdf_count = sum(1 for item in results if item.pdf_path)
        QMessageBox.information(self, "Documents générés", f"{len(results)} document(s) DOCX généré(s).\n{pdf_count} PDF créé(s).\n\nLes fichiers ont été classés dans le dossier du client.")
        self.accept()

    def _open_folder(self):
        if self.last_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_folder)))
