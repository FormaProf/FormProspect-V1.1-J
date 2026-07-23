from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QInputDialog, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.premium_theme import (
    BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON,
    SECONDARY_BUTTON, SUCCESS, TEXT,
)
from services.ai import AssistantService
from services.system.activity_service import ActivityService
from ui.components.notifications import NotificationManager


class AIAssistantPage(QWidget):
    """Assistant commercial local, explicable et sans transfert de données."""

    def __init__(self):
        super().__init__()
        self.service = None
        self.current_prospect_id = None
        self.setStyleSheet(f"background: {PAGE_BG};")
        self._build_ui()

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("AiCard")
        frame.setStyleSheet(
            f"QFrame#AiCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}"
        )
        return frame

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(32, 26, 32, 34)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Assistant IA commercial")
        title.setStyleSheet(f"color: {TEXT}; font-size: 30px; font-weight: 900; background: transparent;")
        subtitle = QLabel("Analysez votre base, priorisez les prospects et préparez vos actions commerciales.")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 14px; background: transparent;")
        privacy = QLabel("🔒 Analyse locale — aucune donnée envoyée à un service externe")
        privacy.setStyleSheet(
            f"color: {SUCCESS}; background: #F0FDF4; border: 1px solid #BBF7D0; "
            "border-radius: 10px; padding: 9px 12px; font-size: 11px; font-weight: 800;"
        )
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        header.addWidget(privacy, 0, Qt.AlignTop)
        root.addLayout(header)

        self.empty_label = QLabel("Ouvrez un projet pour utiliser l'Assistant IA.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setMinimumHeight(90)
        self.empty_label.setStyleSheet(
            f"background: white; color: {MUTED}; border: 1px dashed {BORDER}; "
            "border-radius: 14px; font-size: 14px;"
        )
        root.addWidget(self.empty_label)

        self.main_content = QWidget()
        main_layout = QVBoxLayout(self.main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(18)

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(12)
        self.kpi_labels = {}
        metrics = [
            ("priorities", "Prospects prioritaires", "🔥"),
            ("due_today", "Actions aujourd'hui", "📅"),
            ("overdue", "Relances en retard", "⚠"),
            ("quality", "Qualité de la base", "✨"),
        ]
        for column, (key, label, icon) in enumerate(metrics):
            card = self._card()
            layout = QVBoxLayout(card)
            layout.setContentsMargins(18, 15, 18, 16)
            top = QLabel(f"{icon}  {label}")
            top.setStyleSheet(f"color: {MUTED}; font-size: 12px; font-weight: 800; background: transparent;")
            value = QLabel("0")
            value.setStyleSheet(f"color: {NAVY}; font-size: 28px; font-weight: 900; background: transparent;")
            layout.addWidget(top)
            layout.addWidget(value)
            self.kpi_grid.addWidget(card, 0, column)
            self.kpi_labels[key] = value
        main_layout.addLayout(self.kpi_grid)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        left = self._card()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 17, 18, 18)
        left_layout.setSpacing(12)
        left_title = QLabel("Prospects recommandés")
        left_title.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 900; background: transparent;")
        left_sub = QLabel("Classement fondé sur le score et la disponibilité des coordonnées.")
        left_sub.setWordWrap(True)
        left_sub.setStyleSheet(f"color: {MUTED}; font-size: 11px; background: transparent;")
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["10", "25", "50"])
        self.limit_combo.setCurrentText("25")
        self.limit_combo.currentTextChanged.connect(self._load_prospects)
        self.prospect_table = QTableWidget(0, 4)
        self.prospect_table.setHorizontalHeaderLabels(["Entreprise", "Score", "Niveau", "Contact"])
        self.prospect_table.verticalHeader().setVisible(False)
        self.prospect_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospect_table.setSelectionMode(QTableWidget.SingleSelection)
        self.prospect_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prospect_table.setAlternatingRowColors(True)
        self.prospect_table.itemSelectionChanged.connect(self._on_selection)
        self.prospect_table.horizontalHeader().setStretchLastSection(True)
        self.prospect_table.setStyleSheet(
            f"QTableWidget {{ background: white; border: 1px solid {BORDER}; border-radius: 10px; "
            f"gridline-color: {BORDER}; color: {TEXT}; alternate-background-color: #F8FAFC; }}"
            f"QHeaderView::section {{ background: #F8FAFC; color: {MUTED}; border: none; "
            f"border-bottom: 1px solid {BORDER}; padding: 9px; font-weight: 800; }}"
            f"QTableWidget::item:selected {{ background: #EAF4FF; color: {TEXT}; }}"
        )
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Afficher :"))
        controls.addWidget(self.limit_combo)
        controls.addStretch()
        left_layout.addWidget(left_title)
        left_layout.addWidget(left_sub)
        left_layout.addLayout(controls)
        left_layout.addWidget(self.prospect_table, 1)

        right = self._card()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 17, 18, 18)
        right_layout.setSpacing(12)
        self.selected_title = QLabel("Sélectionnez un prospect")
        self.selected_title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 900; background: transparent;")
        self.selected_meta = QLabel("L'Assistant préparera une recommandation personnalisée.")
        self.selected_meta.setWordWrap(True)
        self.selected_meta.setStyleSheet(f"color: {MUTED}; font-size: 11px; background: transparent;")

        self.copilot_card = QFrame()
        self.copilot_card.setObjectName("CopilotSummary")
        self.copilot_card.setStyleSheet(
            f"QFrame#CopilotSummary {{ background: #F8FAFC; border: 1px solid {BORDER}; border-radius: 12px; }}"
        )
        copilot_layout = QGridLayout(self.copilot_card)
        copilot_layout.setContentsMargins(14, 12, 14, 12)
        copilot_layout.setSpacing(8)
        self.copilot_priority = QLabel("Priorité : —")
        self.copilot_objective = QLabel("Objectif : sélectionnez un prospect")
        self.copilot_action = QLabel("Action conseillée : —")
        for label in (self.copilot_priority, self.copilot_objective, self.copilot_action):
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 700; background: transparent;")
        copilot_layout.addWidget(self.copilot_priority, 0, 0)
        copilot_layout.addWidget(self.copilot_objective, 1, 0)
        copilot_layout.addWidget(self.copilot_action, 2, 0)

        actions = QGridLayout()
        actions.setSpacing(8)
        action_specs = [
            ("🧠 Ouvrir le copilote prospect", self.open_prospect_copilot),
            ("🎯 Qualification automatique", self.open_automatic_qualification),
            ("🧠 Mémoire commerciale", self.open_commercial_memory),
            ("➕ Ajouter une mémoire", self.add_commercial_memory),
            ("📞 Préparer mon appel", self.prepare_call),
            ("Prochaine action", self.recommend_action),
            ("Script Form@Prof", self.generate_call_script),
            ("E-mail Form@Prof", self.generate_email),
            ("Questions de découverte", self.prepare_call),
            ("Réponses aux objections", self.generate_objections),
            ("Plan de relance", self.generate_follow_up_plan),
            ("Base de connaissances", self.show_knowledge_overview),
            ("Expliquer le score", self.explain_score),
        ]
        for index, (text, callback) in enumerate(action_specs):
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(PRIMARY_BUTTON if index == 1 else SECONDARY_BUTTON)
            button.clicked.connect(callback)
            actions.addWidget(button, index // 2, index % 2)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Le résultat s'affichera ici...")
        self.output.setMinimumHeight(230)
        self.output.setStyleSheet(
            f"QTextEdit {{ background: #F8FAFC; color: {TEXT}; border: 1px solid {BORDER}; "
            "border-radius: 12px; padding: 14px; font-size: 13px; }}"
        )
        copy_button = QPushButton("Copier le résultat")
        copy_button.setStyleSheet(SECONDARY_BUTTON)
        copy_button.clicked.connect(self.copy_output)
        right_layout.addWidget(self.selected_title)
        right_layout.addWidget(self.selected_meta)
        right_layout.addWidget(self.copilot_card)
        right_layout.addLayout(actions)
        right_layout.addWidget(self.output, 1)
        right_layout.addWidget(copy_button, 0, Qt.AlignRight)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([560, 560])
        main_layout.addWidget(split, 1)

        bottom = QSplitter(Qt.Horizontal)
        bottom.setChildrenCollapsible(False)
        insight_card = self._card()
        insight_layout = QVBoxLayout(insight_card)
        insight_layout.setContentsMargins(18, 16, 18, 18)
        insight_title = QLabel("Recommandations du jour")
        insight_title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 900; background: transparent;")
        self.insights_list = QListWidget()
        self.insights_list.setStyleSheet(
            f"QListWidget {{ border: none; background: transparent; color: {TEXT}; }}"
            "QListWidget::item { padding: 8px 4px; border-bottom: 1px solid #EEF2F7; }"
        )
        insight_layout.addWidget(insight_title)
        insight_layout.addWidget(self.insights_list)

        history_card = self._card()
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(18, 16, 18, 18)
        history_title = QLabel("Historique IA")
        history_title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 900; background: transparent;")
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._open_history)
        self.history_list.setStyleSheet(
            f"QListWidget {{ border: none; background: transparent; color: {TEXT}; }}"
            "QListWidget::item { padding: 8px 4px; border-bottom: 1px solid #EEF2F7; }"
        )
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_list)
        bottom.addWidget(insight_card)
        bottom.addWidget(history_card)
        bottom.setSizes([560, 560])
        bottom.setMinimumHeight(210)
        main_layout.addWidget(bottom)

        root.addWidget(self.main_content)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.main_content.setVisible(False)

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.service = None
            self.empty_label.setVisible(True)
            self.main_content.setVisible(False)
            return
        project = ApplicationState.get_project()
        self.service = AssistantService(project.database)
        self.empty_label.setVisible(False)
        self.main_content.setVisible(True)
        data = self.service.dashboard_summary()
        self.kpi_labels["priorities"].setText(str(data["priorities"]))
        self.kpi_labels["due_today"].setText(str(data["due_today"]))
        self.kpi_labels["overdue"].setText(str(data["overdue"]))
        self.kpi_labels["quality"].setText(f"{data['quality']} %")
        self._load_prospects()
        self._load_insights()
        self._load_history()

    def _load_prospects(self):
        if not self.service:
            return
        prospects = self.service.top_prospects(int(self.limit_combo.currentText()))
        self.prospect_table.setRowCount(len(prospects))
        for row_index, prospect in enumerate(prospects):
            name_item = QTableWidgetItem(prospect.entreprise)
            name_item.setData(Qt.UserRole, prospect.prospect_id)
            score_item = QTableWidgetItem(f"{prospect.score}/100")
            grade_item = QTableWidgetItem(prospect.grade)
            contact = "📞 📧" if prospect.telephone and prospect.email else ("📞" if prospect.telephone else ("📧" if prospect.email else "—"))
            contact_item = QTableWidgetItem(contact)
            for column, item in enumerate((name_item, score_item, grade_item, contact_item)):
                self.prospect_table.setItem(row_index, column, item)
        self.prospect_table.resizeColumnsToContents()

    def _load_insights(self):
        self.insights_list.clear()
        if not self.service:
            return
        icons = {"success": "✅", "warning": "⚠", "info": "💡"}
        for insight in self.service.insights():
            item = QListWidgetItem(f"{icons.get(insight.level, '💡')}  {insight.title}\n{insight.message}")
            self.insights_list.addItem(item)

    def _load_history(self):
        self.history_list.clear()
        if not self.service:
            return
        for entry in self.service.history():
            item = QListWidgetItem(f"{entry['created_at'].replace('T', ' ')}  •  {entry['title']}")
            item.setData(Qt.UserRole, entry)
            self.history_list.addItem(item)

    def _on_selection(self):
        items = self.prospect_table.selectedItems()
        if not items:
            self.current_prospect_id = None
            return
        row = items[0].row()
        first = self.prospect_table.item(row, 0)
        self.current_prospect_id = int(first.data(Qt.UserRole))
        name = first.text()
        score = self.prospect_table.item(row, 1).text()
        grade = self.prospect_table.item(row, 2).text()
        self.selected_title.setText(name)
        self.selected_meta.setText(f"Score {score}  •  {grade}")
        self.output.clear()
        self._refresh_copilot_summary()

    def _require_selection(self) -> bool:
        if self.current_prospect_id is None:
            NotificationManager.warning("Prospect requis", "Sélectionnez d'abord une entreprise dans le tableau.")
            return False
        return True

    def _display(self, title: str, content: str):
        self.output.setPlainText(content)
        NotificationManager.success(title, "Le contenu a été généré localement.")
        ActivityService.record(title, "Contenu généré par l'Assistant IA local.", category="ai", level="success")
        self._load_history()

    def add_commercial_memory(self):
        if not self._require_selection():
            return
        memory_type, accepted = QInputDialog.getItem(
            self,
            "Type de mémoire",
            "Catégorie :",
            list(self.service.MEMORY_TYPES),
            0,
            False,
        )
        if not accepted:
            return
        content, accepted = QInputDialog.getMultiLineText(
            self,
            "Ajouter à la mémoire commerciale",
            "Information à retenir pour les prochains échanges :",
        )
        if not accepted:
            return
        try:
            self.service.add_commercial_memory(
                self.current_prospect_id,
                content,
                memory_type,
            )
        except ValueError as exc:
            NotificationManager.warning("Mémoire non enregistrée", str(exc))
            return
        NotificationManager.success(
            "Mémoire enregistrée",
            "Cette information sera réutilisable lors des prochains contacts.",
        )
        ActivityService.record(
            "Mémoire commerciale",
            f"Une information « {memory_type} » a été ajoutée.",
            category="ai",
            level="success",
        )
        self.open_commercial_memory()

    def open_commercial_memory(self):
        if self._require_selection():
            self._display(
                "Mémoire commerciale",
                self.service.commercial_memory_report(self.current_prospect_id),
            )

    def _refresh_copilot_summary(self):
        if not self.service or self.current_prospect_id is None:
            return
        try:
            data = self.service.prospect_copilot(self.current_prospect_id)
            self.copilot_priority.setText(
                f"Priorité : {data['priority']}  •  Intérêt estimé : {data['probability']}"
            )
            self.copilot_objective.setText(f"Objectif : {data['objective']}")
            qualification = self.service.automatic_qualification(self.current_prospect_id)
            self.copilot_priority.setText(
                f"Priorité : {qualification['urgency']}  •  Score : {qualification['total']}/100  •  Confiance : {qualification['confidence']} %"
            )
            self.copilot_objective.setText(f"Diagnostic : {qualification['maturity']}  •  Potentiel : {qualification['potential']}")
            self.copilot_action.setText(f"Action conseillée : {qualification['recommended_action']}")
        except Exception as exc:
            self.copilot_priority.setText("Priorité : indisponible")
            self.copilot_objective.setText("Objectif : impossible à calculer")
            self.copilot_action.setText(f"Erreur : {exc}")

    def open_automatic_qualification(self):
        if self._require_selection():
            self._display(
                "Qualification automatique",
                self.service.automatic_qualification_report(self.current_prospect_id),
            )
            self._refresh_copilot_summary()

    def open_prospect_copilot(self):
        if self._require_selection():
            self._refresh_copilot_summary()
            self._display(
                "Copilote prospect généré",
                self.service.prospect_copilot_report(self.current_prospect_id),
            )

    def prepare_call(self):
        if self._require_selection():
            self._display(
                "Préparation d'appel générée",
                self.service.call_preparation(self.current_prospect_id),
            )

    def explain_score(self):
        if self._require_selection():
            self._display("Score expliqué", self.service.explain_score(self.current_prospect_id))

    def recommend_action(self):
        if self._require_selection():
            self._display("Action recommandée", self.service.next_action(self.current_prospect_id))

    def generate_call_script(self):
        if self._require_selection():
            self._display("Script d'appel généré", self.service.call_script(self.current_prospect_id))

    def generate_email(self):
        if self._require_selection():
            subject, body = self.service.email_draft(self.current_prospect_id)
            self._display("E-mail généré", f"Objet : {subject}\n\n{body}")

    def generate_objections(self):
        if self._require_selection():
            self._display("Réponses aux objections", self.service.objection_guide(self.current_prospect_id))

    def generate_follow_up_plan(self):
        if self._require_selection():
            self._display("Plan de relance généré", self.service.follow_up_plan(self.current_prospect_id))

    def show_knowledge_overview(self):
        if not self.service:
            NotificationManager.warning("Projet requis", "Ouvrez d'abord un projet.")
            return
        self._display("Knowledge Engine", self.service.knowledge_overview())

    def copy_output(self):
        content = self.output.toPlainText().strip()
        if not content:
            NotificationManager.info("Rien à copier", "Générez d'abord un contenu.")
            return
        QApplication.clipboard().setText(content)
        NotificationManager.success("Copié", "Le contenu est dans le presse-papiers.")

    def _open_history(self, item):
        entry = item.data(Qt.UserRole)
        if entry:
            self.selected_title.setText(entry.get("title", "Historique IA"))
            self.selected_meta.setText(entry.get("created_at", "").replace("T", " "))
            self.output.setPlainText(entry.get("content", ""))
