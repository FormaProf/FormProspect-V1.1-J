from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from core.premium_theme import INPUT_STYLE
from services.document_service import DocumentService


class DocumentTemplateDialog(QDialog):
    def __init__(self, service: DocumentService, template: dict | None = None, parent=None):
        super().__init__(parent)
        self.service = service; self.template = template or {}; self.template_id = self.template.get("id")
        self.setWindowTitle("Modifier le modèle" if self.template_id else "Nouveau modèle documentaire")
        self.resize(600, 330); self.setStyleSheet(INPUT_STYLE)
        root = QVBoxLayout(self); form = QFormLayout(); form.setSpacing(13)
        self.name = QLineEdit(str(self.template.get("name", "")))
        self.kind = QComboBox(); self.kind.addItems(DocumentService.DOCUMENT_TYPES); self.kind.setCurrentText(str(self.template.get("document_type", "Devis")))
        self.training = QComboBox(); self.training.addItem("Toutes les formations", None)
        for item in service.list_trainings(): self.training.addItem(item["name"], item["id"])
        index = self.training.findData(self.template.get("training_id")); self.training.setCurrentIndex(max(0, index))
        self.path = QLineEdit(str(self.template.get("source_path", "")))
        browse = QPushButton("Parcourir…"); browse.clicked.connect(self._browse)
        path_row = QHBoxLayout(); path_row.addWidget(self.path, 1); path_row.addWidget(browse)
        self.format = QComboBox(); self.format.addItems(["DOCX", "PDF", "DOCX + PDF"]); self.format.setCurrentText(str(self.template.get("output_format", "DOCX")))
        self.active = QCheckBox("Modèle actif"); self.active.setChecked(bool(self.template.get("active", 1)))
        form.addRow("Nom *", self.name); form.addRow("Type *", self.kind); form.addRow("Formation liée", self.training)
        form.addRow("Fichier source", path_row); form.addRow("Sortie prévue", self.format); form.addRow("", self.active)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.button(QDialogButtonBox.Save).setText("Enregistrer")
        buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un modèle", "", "Documents (*.docx *.pdf);;Tous les fichiers (*.*)")
        if path: self.path.setText(path)

    def _save(self):
        try:
            self.service.save_template(template_id=self.template_id, name=self.name.text(), document_type=self.kind.currentText(),
                source_path=self.path.text(), output_format=self.format.currentText(), training_id=self.training.currentData(), active=self.active.isChecked())
        except ValueError as exc:
            QMessageBox.warning(self, "Modèle documentaire", str(exc)); return
        self.accept()
