from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QPlainTextEdit, QVBoxLayout


class QuoteRequestDialog(QDialog):
    def __init__(self, case: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Demander un devis")
        self.setMinimumWidth(560)
        root = QVBoxLayout(self)
        title = QLabel("Nouvelle demande de devis")
        title.setStyleSheet("font-size:21px;font-weight:800;color:#0B1F3A;")
        root.addWidget(title)
        summary = QLabel(
            f"<b>{case['company_name']}</b><br>{case['training_name']}<br>"
            f"Du {case['start_date']} au {case['end_date']} • {case['participant_count']} participant(s)<br>"
            f"Montant indicatif : {case['price_cents']/100:,.2f} €".replace(',', ' ')
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("background:#F3F8FE;border:1px solid #CFE4FA;border-radius:10px;padding:14px;")
        root.addWidget(summary)
        form = QFormLayout()
        self.note = QPlainTextEdit()
        self.note.setPlaceholderText("Précisions utiles pour l'administrateur : conditions, financeur, urgence, remise validée…")
        self.note.setMinimumHeight(120)
        form.addRow("Note", self.note)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Envoyer la demande")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
