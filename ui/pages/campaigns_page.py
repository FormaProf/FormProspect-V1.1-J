from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.premium_theme import (
    BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON,
    SECONDARY_BUTTON, SUCCESS, TEXT,
)
from services.campaign_service import CampaignService
from ui.components.notifications import NotificationManager


class CampaignsPage(QWidget):
    """Création locale de campagnes, audiences et messages personnalisés."""

    def __init__(self):
        super().__init__()
        self.service = None
        self.current_campaign_id = None
        self.setStyleSheet(f"background: {PAGE_BG};")
        self._build_ui()

    def _card(self):
        card = QFrame()
        card.setObjectName("CampaignCard")
        card.setStyleSheet(
            f"QFrame#CampaignCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}"
        )
        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 30)
        root.setSpacing(16)

        title = QLabel("Campagnes intelligentes")
        title.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:900;")
        subtitle = QLabel(
            "Préparez les audiences, personnalisez les messages et suivez les résultats. "
            "Aucun envoi n'est effectué automatiquement dans cette version."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.empty = QLabel("Ouvrez un projet pour utiliser les campagnes.")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(80)
        self.empty.setStyleSheet(
            f"background:white; color:{MUTED}; border:1px dashed {BORDER}; border-radius:14px;"
        )
        root.addWidget(self.empty)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        kpi = QGridLayout()
        kpi.setSpacing(10)
        self.kpis = {}
        for col, (key, label) in enumerate([
            ("campaigns", "Campagnes"),
            ("recipients", "Destinataires"),
            ("ready", "Prêts"),
            ("replied", "Réponses"),
            ("appointments", "Rendez-vous"),
        ]):
            card = self._card()
            layout = QVBoxLayout(card)
            caption = QLabel(label)
            caption.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:800;")
            value = QLabel("0")
            value.setStyleSheet(f"color:{NAVY}; font-size:25px; font-weight:900;")
            layout.addWidget(caption)
            layout.addWidget(value)
            kpi.addWidget(card, 0, col)
            self.kpis[key] = value
        content_layout.addLayout(kpi)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        editor = self._card()
        form = QVBoxLayout(editor)
        form.setContentsMargins(18, 16, 18, 18)
        form.setSpacing(9)
        form_title = QLabel("Nouvelle campagne")
        form_title.setStyleSheet(f"color:{TEXT}; font-size:17px; font-weight:900;")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ex. Campagne Étancheurs Hauts-de-France")
        self.template_combo = QComboBox()
        self.template_combo.addItems(CampaignService.template_names())
        self.template_combo.currentTextChanged.connect(self._load_template)
        self.min_score = QSpinBox()
        self.min_score.setRange(0, 100)
        self.min_score.setValue(45)
        self.min_score.setSuffix(" / 100 minimum")
        self.subject_edit = QLineEdit()
        self.body_edit = QTextEdit()
        self.body_edit.setMinimumHeight(230)
        for widget in (self.name_edit, self.template_combo, self.min_score, self.subject_edit, self.body_edit):
            widget.setStyleSheet(
                f"background:white; color:{TEXT}; border:1px solid {BORDER}; border-radius:9px; padding:8px;"
            )
        form.addWidget(form_title)
        form.addWidget(QLabel("Nom"))
        form.addWidget(self.name_edit)
        form.addWidget(QLabel("Modèle"))
        form.addWidget(self.template_combo)
        form.addWidget(QLabel("Score minimal de l'audience"))
        form.addWidget(self.min_score)
        form.addWidget(QLabel("Objet"))
        form.addWidget(self.subject_edit)
        form.addWidget(QLabel("Message"))
        form.addWidget(self.body_edit)
        create = QPushButton("Créer la campagne")
        create.setStyleSheet(PRIMARY_BUTTON)
        create.clicked.connect(self.create_campaign)
        form.addWidget(create)
        split.addWidget(editor)

        right = self._card()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 16, 18, 18)
        right_layout.setSpacing(10)
        campaign_title = QLabel("Campagnes")
        campaign_title.setStyleSheet(f"color:{TEXT}; font-size:17px; font-weight:900;")
        self.campaigns_table = QTableWidget(0, 5)
        self.campaigns_table.setHorizontalHeaderLabels(["Nom", "Statut", "Score min.", "Audience", "Réponses"])
        self.campaigns_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.campaigns_table.setSelectionMode(QTableWidget.SingleSelection)
        self.campaigns_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.campaigns_table.verticalHeader().setVisible(False)
        self.campaigns_table.itemSelectionChanged.connect(self._campaign_selected)
        self.campaigns_table.horizontalHeader().setStretchLastSection(True)
        self.campaigns_table.setStyleSheet(
            f"QTableWidget{{background:white; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px;}}"
        )

        actions = QHBoxLayout()
        build = QPushButton("Générer l'audience")
        build.setStyleSheet(PRIMARY_BUTTON)
        build.clicked.connect(self.build_audience)
        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)
        actions.addWidget(build)
        actions.addWidget(refresh)
        actions.addStretch()

        self.recipients_table = QTableWidget(0, 6)
        self.recipients_table.setHorizontalHeaderLabels(
            ["Entreprise", "E-mail", "Score", "Canal conseillé", "Statut", "Objet personnalisé"]
        )
        self.recipients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recipients_table.verticalHeader().setVisible(False)
        self.recipients_table.horizontalHeader().setStretchLastSection(True)
        self.recipients_table.setStyleSheet(
            f"QTableWidget{{background:white; color:{TEXT}; border:1px solid {BORDER}; border-radius:10px;}}"
        )
        right_layout.addWidget(campaign_title)
        right_layout.addWidget(self.campaigns_table, 1)
        right_layout.addLayout(actions)
        right_layout.addWidget(QLabel("Audience et messages personnalisés"))
        right_layout.addWidget(self.recipients_table, 1)
        split.addWidget(right)
        split.setSizes([430, 760])

        content_layout.addWidget(split, 1)
        root.addWidget(self.content, 1)
        self.content.setVisible(False)
        self._load_template(self.template_combo.currentText())

    def _load_template(self, name):
        template = CampaignService.template(name)
        self.subject_edit.setText(template["subject"])
        self.body_edit.setPlainText(template["body"])

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.service = None
            self.empty.setVisible(True)
            self.content.setVisible(False)
            return
        self.service = CampaignService(ApplicationState.get_project().database)
        self.empty.setVisible(False)
        self.content.setVisible(True)
        self._load_campaigns()
        self._load_stats()

    def _load_stats(self):
        if not self.service:
            return
        stats = self.service.stats()
        for key in self.kpis:
            self.kpis[key].setText(str(getattr(stats, key)))

    def _load_campaigns(self):
        self.campaigns_table.setRowCount(0)
        if not self.service:
            return
        rows = self.service.campaigns()
        self.campaigns_table.setRowCount(len(rows))
        for row_index, campaign in enumerate(rows):
            values = [
                campaign["name"],
                campaign["status"],
                str(campaign["min_score"]),
                str(campaign["recipient_count"] or 0),
                str(campaign["replied_count"] or 0),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, int(campaign["id"]))
                self.campaigns_table.setItem(row_index, col, item)
        self.campaigns_table.resizeColumnsToContents()

    def create_campaign(self):
        if not self.service:
            return
        try:
            campaign_id = self.service.create_campaign(
                self.name_edit.text(),
                self.template_combo.currentText(),
                self.subject_edit.text(),
                self.body_edit.toPlainText(),
                self.min_score.value(),
            )
        except ValueError as exc:
            NotificationManager.warning("Campagne incomplète", str(exc))
            return
        self.current_campaign_id = campaign_id
        NotificationManager.success("Campagne créée", "Le brouillon est prêt à recevoir une audience.")
        self.name_edit.clear()
        self._load_campaigns()
        self._load_stats()

    def _campaign_selected(self):
        items = self.campaigns_table.selectedItems()
        if not items:
            return
        self.current_campaign_id = int(self.campaigns_table.item(items[0].row(), 0).data(Qt.UserRole))
        self._load_recipients()

    def build_audience(self):
        if not self.service or self.current_campaign_id is None:
            NotificationManager.warning("Campagne requise", "Sélectionnez d'abord une campagne.")
            return
        added = self.service.build_audience(self.current_campaign_id)
        NotificationManager.success("Audience générée", f"{added} nouveau(x) destinataire(s) ajouté(s).")
        self._load_campaigns()
        self._load_recipients()
        self._load_stats()

    def _load_recipients(self):
        self.recipients_table.setRowCount(0)
        if not self.service or self.current_campaign_id is None:
            return
        rows = self.service.recipients(self.current_campaign_id)
        self.recipients_table.setRowCount(len(rows))
        for r, item in enumerate(rows):
            values = [
                item["entreprise"] or "",
                item["email"],
                str(item["score_prospect"] or 0),
                item["recommended_channel"],
                item["status"],
                item["personalized_subject"],
            ]
            for c, value in enumerate(values):
                self.recipients_table.setItem(r, c, QTableWidgetItem(value))
        self.recipients_table.resizeColumnsToContents()
