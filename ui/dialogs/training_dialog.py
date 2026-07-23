from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLineEdit, QMessageBox, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from core.premium_theme import INPUT_STYLE
from services.document_service import DocumentService


class TrainingDialog(QDialog):
    def __init__(self, service: DocumentService, training: dict | None = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.training = training or {}
        self.training_id = self.training.get("id")
        self.setWindowTitle("Modifier la formation" if self.training_id else "Nouvelle formation")
        self.resize(680, 700)
        self.setStyleSheet(INPUT_STYLE)

        root = QVBoxLayout(self)
        tabs = QTabWidget()

        general = QWidget(); form = QFormLayout(general); form.setSpacing(12)
        self.reference = QLineEdit(str(self.training.get("reference", "")))
        self.name = QLineEdit(str(self.training.get("name", "")))
        self.category = QLineEdit(str(self.training.get("category", "")))
        self.duration = QDoubleSpinBox(); self.duration.setRange(0.5, 2000); self.duration.setDecimals(1); self.duration.setSuffix(" h"); self.duration.setValue(float(self.training.get("duration_hours", 14)))
        self.price = QDoubleSpinBox(); self.price.setRange(0, 1_000_000); self.price.setDecimals(2); self.price.setSuffix(" €"); self.price.setValue(float(self.training.get("price_cents", 0)) / 100)
        self.modality = QComboBox(); self.modality.addItems(DocumentService.MODALITIES); self.modality.setCurrentText(str(self.training.get("modality", "À distance")))
        self.max_participants = QSpinBox(); self.max_participants.setRange(1, 500); self.max_participants.setValue(int(self.training.get("max_participants", 8)))
        self.certification = QLineEdit(str(self.training.get("certification", "")))
        self.active = QCheckBox("Formation active"); self.active.setChecked(bool(self.training.get("active", 1)))
        for label, widget in [("Référence *", self.reference), ("Nom *", self.name), ("Catégorie", self.category), ("Durée *", self.duration),
                              ("Prix", self.price), ("Modalité", self.modality), ("Participants maximum", self.max_participants),
                              ("Certification", self.certification), ("", self.active)]:
            form.addRow(label, widget)

        pedagogy = QWidget(); pf = QFormLayout(pedagogy)
        self.description = QTextEdit(str(self.training.get("description", "")))
        self.objectives = QTextEdit(str(self.training.get("objectives", "")))
        self.target_audience = QTextEdit(str(self.training.get("target_audience", "")))
        self.prerequisites = QTextEdit(str(self.training.get("prerequisites", "")))
        self.teaching_methods = QTextEdit(str(self.training.get("teaching_methods", "")))
        self.evaluation_methods = QTextEdit(str(self.training.get("evaluation_methods", "")))
        for widget in (self.description, self.objectives, self.target_audience, self.prerequisites, self.teaching_methods, self.evaluation_methods):
            widget.setMinimumHeight(75)
        for label, widget in [("Description", self.description), ("Objectifs", self.objectives), ("Public visé", self.target_audience),
                              ("Prérequis", self.prerequisites), ("Méthodes pédagogiques", self.teaching_methods),
                              ("Modalités d'évaluation", self.evaluation_methods)]:
            pf.addRow(label, widget)

        tabs.addTab(general, "Informations générales")
        tabs.addTab(pedagogy, "Contenu pédagogique")
        root.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Enregistrer")
        buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self):
        try:
            self.service.save_training(
                training_id=self.training_id, reference=self.reference.text(), name=self.name.text(),
                duration_hours=self.duration.value(), price_cents=round(self.price.value() * 100),
                modality=self.modality.currentText(), certification=self.certification.text(),
                description=self.description.toPlainText(), objectives=self.objectives.toPlainText(),
                prerequisites=self.prerequisites.toPlainText(), active=self.active.isChecked(),
                category=self.category.text(), target_audience=self.target_audience.toPlainText(),
                teaching_methods=self.teaching_methods.toPlainText(), evaluation_methods=self.evaluation_methods.toPlainText(),
                max_participants=self.max_participants.value(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Formation", str(exc)); return
        self.accept()
