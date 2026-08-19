from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from services.cloud_api_client import CloudAPIError


class CloudQuoteRequestDialog(QDialog):
    """Création d'une demande Cloud de devis ou de facture."""

    DOCUMENT_TYPES = ("Devis", "Facture")

    def __init__(
        self,
        api,
        prospects: list[dict],
        trainings: list[dict],
        parent=None,
        *,
        initial_prospect_id: str | None = None,
        initial_document_type: str = "Devis",
    ):
        super().__init__(parent)
        self.api = api
        self.prospects = [
            item
            for item in prospects
            if str(item.get("pipeline_stage") or "") == "gagne"
        ]
        self.trainings = [item for item in trainings if bool(item.get("active", True))]
        self.initial_prospect_id = initial_prospect_id
        self.initial_document_type = (
            initial_document_type
            if initial_document_type in self.DOCUMENT_TYPES
            else "Devis"
        )
        self.created_request: dict | None = None

        self.setWindowTitle("Demander un devis ou une facture")
        self.resize(700, 540)
        self._build_ui()
        self._load_values()

    @staticmethod
    def _format_price(cents) -> str:
        try:
            value = int(cents or 0) / 100
        except (TypeError, ValueError):
            value = 0
        return f"{value:,.2f} €".replace(",", " ").replace(".00", "")

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(15)

        self.title = QLabel("Nouvelle demande de document")
        self.title.setStyleSheet(f"color:{TEXT};font-size:24px;font-weight:900;")
        root.addWidget(self.title)

        intro = QLabel(
            "Sélectionnez le type de document, le client et la formation. "
            "La demande sera transmise à l'administrateur, qui déposera ensuite "
            "le document dans l'espace Cloud privé."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{MUTED};font-size:13px;")
        root.addWidget(intro)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD};border:1px solid {BORDER};border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        self.document_type_combo = QComboBox()
        self.document_type_combo.addItems(self.DOCUMENT_TYPES)
        self.document_type_combo.setCurrentText(self.initial_document_type)
        self.document_type_combo.currentTextChanged.connect(self._refresh_summary)

        self.prospect_combo = QComboBox()
        self.training_combo = QComboBox()
        self.training_combo.currentIndexChanged.connect(self._refresh_summary)
        self.note = QPlainTextEdit()
        self.note.setPlaceholderText(
            "Précisions facultatives pour l'administrateur : dates, financeur, "
            "délai, référence de commande, besoin particulier…"
        )
        self.note.setMaximumHeight(120)

        form.addRow("Document *", self.document_type_combo)
        form.addRow("Client *", self.prospect_combo)
        form.addRow("Formation *", self.training_combo)
        form.addRow("Précisions", self.note)
        root.addWidget(card)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.summary.setStyleSheet(
            f"background:#F8FAFC;color:{TEXT};border:1px solid {BORDER};"
            "border-radius:12px;padding:14px;font-weight:700;"
        )
        root.addWidget(self.summary)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        self.submit = QPushButton("Envoyer la demande")
        self.submit.setStyleSheet(PRIMARY_BUTTON)
        self.submit.clicked.connect(self._submit)
        actions.addWidget(cancel)
        actions.addWidget(self.submit)
        root.addLayout(actions)

    def _load_values(self) -> None:
        selected_index = -1
        for index, prospect in enumerate(self.prospects):
            prospect_id = str(prospect.get("id") or "")
            self.prospect_combo.addItem(
                str(prospect.get("company_name") or "Client sans nom"),
                prospect_id,
            )
            if prospect_id == self.initial_prospect_id:
                selected_index = index
        if selected_index >= 0:
            self.prospect_combo.setCurrentIndex(selected_index)

        for training in self.trainings:
            name = str(training.get("name") or "Formation")
            reference = str(training.get("reference") or "")
            price = self._format_price(training.get("price_cents"))
            self.training_combo.addItem(
                f"{reference} — {name} — {price}",
                str(training.get("id") or ""),
            )

        self._refresh_summary()

    def _selected_training(self) -> dict | None:
        index = self.training_combo.currentIndex()
        if 0 <= index < len(self.trainings):
            return self.trainings[index]
        return None

    def _refresh_summary(self, *_args) -> None:
        document_type = self.document_type_combo.currentText() or "Document"
        training = self._selected_training() or {}
        self.title.setText(f"Nouvelle demande de {document_type.lower()}")
        self.summary.setText(
            f"DOCUMENT DEMANDÉ : {document_type.upper()}\n"
            f"Formation : {training.get('name') or '—'}\n"
            f"Montant du catalogue : {self._format_price(training.get('price_cents'))} net de TVA"
        )

    def _submit(self) -> None:
        prospect_id = self.prospect_combo.currentData()
        training_id = self.training_combo.currentData()
        document_type = self.document_type_combo.currentText() or "Devis"
        if not prospect_id:
            QMessageBox.warning(
                self,
                "Client manquant",
                "Aucun client finalisé n'est disponible. Finalisez d'abord la fiche client dans le CRM.",
            )
            return
        if not training_id:
            QMessageBox.warning(
                self,
                "Formation manquante",
                "Aucune formation active n'est disponible dans le catalogue Cloud.",
            )
            return
        try:
            self.created_request = self.api.create_cloud_quote_request(
                {
                    "prospect_id": str(prospect_id),
                    "training_id": str(training_id),
                    "document_type": document_type,
                    "note": self.note.toPlainText().strip(),
                }
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Demande impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Demande envoyée",
            f"La demande de {document_type.lower()} a été transmise à l'administrateur.",
        )
        self.accept()
