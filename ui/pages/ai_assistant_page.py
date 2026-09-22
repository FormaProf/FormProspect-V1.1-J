from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QHeaderView, QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.theme_settings import get_theme_preference
from ui.ai_premium_theme import assistant_page_palette, assistant_page_stylesheet
from services.ai import AssistantService, CloudAssistantService
from services.cloud_runtime import CloudRuntime
from services.system.activity_service import ActivityService
from ui.components.notifications import NotificationManager


class AIAssistantPage(QWidget):
    """Assistant commercial local, explicable et sans transfert de données."""

    def __init__(self):
        super().__init__()
        self.service = None
        self.current_prospect_id = None
        self._theme_mode = get_theme_preference()
        self._palette = assistant_page_palette(self._theme_mode)
        self.setObjectName("AIAssistantRoot")
        self._build_ui()
        self._apply_visual_theme()

    @staticmethod
    def _card() -> QFrame:
        frame = QFrame()
        frame.setProperty("aiCard", True)
        return frame

    def _apply_visual_theme(self) -> None:
        """Rafraîchit uniquement la couche visuelle, sans appel métier ni Cloud."""
        self._theme_mode = get_theme_preference()
        self._palette = assistant_page_palette(self._theme_mode)
        self.setStyleSheet(assistant_page_stylesheet(self._palette))

    def showEvent(self, event):
        if get_theme_preference() != self._theme_mode:
            self._apply_visual_theme()
        super().showEvent(event)

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("AiPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("AiViewport")
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 20, 24, 28)
        root.setSpacing(14)

        # ------------------------------------------------------------------
        # HERO — identité IA, statut et promesse
        # ------------------------------------------------------------------
        hero = QFrame()
        hero.setObjectName("AiHero")
        hero.setMinimumHeight(142)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 19, 22, 19)
        hero_layout.setSpacing(18)

        orb = QFrame()
        orb.setObjectName("AiOrb")
        orb.setFixedSize(76, 76)
        orb_layout = QVBoxLayout(orb)
        orb_layout.setContentsMargins(0, 0, 0, 0)
        ai_glyph = QLabel("✦")
        ai_glyph.setObjectName("AiOrbGlyph")
        ai_glyph.setAlignment(Qt.AlignCenter)
        orb_layout.addWidget(ai_glyph)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)
        eyebrow = QLabel("AI COMMAND CENTER  •  INTELLIGENCE COMMERCIALE")
        eyebrow.setObjectName("AiHeroEyebrow")
        hero_title = QLabel("Assistant IA")
        hero_title.setObjectName("AiHeroTitle")
        hero_subtitle = QLabel(
            "Priorisez les meilleures opportunités, préparez chaque échange et "
            "transformez le contexte CRM en actions commerciales concrètes."
        )
        hero_subtitle.setObjectName("AiHeroSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)

        hero_status = QVBoxLayout()
        hero_status.setSpacing(7)
        live_badge = QLabel("●  COPILOTE ACTIF")
        live_badge.setObjectName("AiLiveBadge")
        live_badge.setAlignment(Qt.AlignCenter)
        live_badge.setFixedHeight(32)
        live_badge.setMinimumWidth(158)

        privacy = QLabel("ANALYSE INTERNE\nAucune donnée envoyée à une IA externe")
        privacy.setObjectName("AiPrivacyBadge")
        privacy.setAlignment(Qt.AlignCenter)
        privacy.setWordWrap(True)
        privacy.setMinimumWidth(220)

        hero_status.addWidget(live_badge)
        hero_status.addWidget(privacy)

        hero_layout.addWidget(orb, 0, Qt.AlignVCenter)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(hero_status)
        root.addWidget(hero)

        self.empty_label = QLabel("Ouvrez un projet pour activer le copilote commercial.")
        self.empty_label.setObjectName("AiEmptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setMinimumHeight(96)
        root.addWidget(self.empty_label)

        self.main_content = QWidget()
        self.main_content.setObjectName("AiMainContent")
        main_layout = QVBoxLayout(self.main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        # ------------------------------------------------------------------
        # KPI — lecture exécutive compacte
        # ------------------------------------------------------------------
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setHorizontalSpacing(10)
        self.kpi_grid.setVerticalSpacing(10)
        self.kpi_labels = {}

        metrics = [
            ("priorities", "Prioritaires", "!", "À traiter maintenant", "amber"),
            ("due_today", "Aujourd'hui", "↗", "Actions planifiées", "blue"),
            ("overdue", "En retard", "!", "Relances à reprendre", "red"),
            ("quality", "Qualité CRM", "✦", "Complétude des contacts", "violet"),
        ]

        for column, (key, label, icon, caption, tone) in enumerate(metrics):
            card = QFrame()
            card.setObjectName(f"AiMetric_{key}")
            card.setProperty("aiMetric", True)
            card.setProperty("aiTone", tone)
            card.setMinimumHeight(100)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 11)
            layout.setSpacing(4)

            top_row = QHBoxLayout()
            top_row.setSpacing(7)
            icon_box = QLabel(icon)
            icon_box.setProperty("aiMetricIcon", True)
            icon_box.setProperty("aiTone", tone)
            icon_box.setFixedSize(29, 29)
            icon_box.setAlignment(Qt.AlignCenter)

            metric_name = QLabel(label)
            metric_name.setProperty("aiMetricName", True)
            top_row.addWidget(icon_box)
            top_row.addWidget(metric_name)
            top_row.addStretch()

            value = QLabel("0")
            value.setProperty("aiMetricValue", True)
            foot = QLabel(caption)
            foot.setProperty("aiMetricCaption", True)

            accent_line = QFrame()
            accent_line.setProperty("aiMetricAccent", True)
            accent_line.setProperty("aiTone", tone)
            accent_line.setFixedHeight(3)

            layout.addLayout(top_row)
            layout.addWidget(value)
            layout.addWidget(foot)
            layout.addWidget(accent_line)

            self.kpi_grid.addWidget(card, 0, column)
            self.kpi_labels[key] = value

        main_layout.addLayout(self.kpi_grid)

        # ------------------------------------------------------------------
        # COMMAND CENTER — radar d'opportunités + cockpit prospect
        # ------------------------------------------------------------------
        split = QSplitter(Qt.Horizontal)
        split.setObjectName("AiCommandSplitter")
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)

        # Opportunity radar
        left = QFrame()
        left.setObjectName("AiRadarCard")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 15, 16, 16)
        left_layout.setSpacing(9)

        left_top = QHBoxLayout()
        left_titles = QVBoxLayout()
        left_titles.setSpacing(1)

        section = QLabel("OPPORTUNITY RADAR")
        section.setProperty("aiOverline", True)
        left_title = QLabel("Prospects à fort potentiel")
        left_title.setProperty("aiSectionTitle", True)
        left_sub = QLabel(
            "Le copilote classe les opportunités pour concentrer l'effort commercial."
        )
        left_sub.setProperty("aiSectionSubtitle", True)
        left_sub.setWordWrap(True)

        left_titles.addWidget(section)
        left_titles.addWidget(left_title)
        left_titles.addWidget(left_sub)

        radar_badge = QLabel("LIVE")
        radar_badge.setObjectName("AiRadarLive")
        radar_badge.setAlignment(Qt.AlignCenter)
        radar_badge.setFixedSize(48, 24)

        left_top.addLayout(left_titles, 1)
        left_top.addWidget(radar_badge, 0, Qt.AlignTop)
        left_layout.addLayout(left_top)

        search_shell = QFrame()
        search_shell.setObjectName("AiSearchShell")
        search_layout = QHBoxLayout(search_shell)
        search_layout.setContentsMargins(10, 0, 8, 0)
        search_layout.setSpacing(6)

        search_icon = QLabel("⌕")
        search_icon.setObjectName("AiSearchIcon")
        self.search_input = QLineEdit()
        self.search_input.setObjectName("AiSearchInput")
        self.search_input.setPlaceholderText(
            "Rechercher entreprise, ville, téléphone ou e-mail…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(38)
        self.search_input.textChanged.connect(self._load_prospects)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input, 1)
        left_layout.addWidget(search_shell)

        controls = QHBoxLayout()
        controls.setSpacing(7)
        top_label = QLabel("AFFICHER")
        top_label.setProperty("aiControlLabel", True)

        self.limit_combo = QComboBox()
        self.limit_combo.setObjectName("AiLimitCombo")
        self.limit_combo.addItems(["10", "25", "50", "100"])
        self.limit_combo.setCurrentText("25")
        self.limit_combo.setFixedWidth(76)
        self.limit_combo.setMinimumHeight(31)
        self.limit_combo.currentTextChanged.connect(self._load_prospects)

        self.results_label = QLabel("")
        self.results_label.setObjectName("AiResultsLabel")
        self.results_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        controls.addWidget(top_label)
        controls.addWidget(self.limit_combo)
        controls.addStretch()
        controls.addWidget(self.results_label)
        left_layout.addLayout(controls)

        self.prospect_table = QTableWidget(0, 4)
        self.prospect_table.setObjectName("AiProspectTable")
        self.prospect_table.setHorizontalHeaderLabels(
            ["Entreprise", "Score", "Niveau", "Contact"]
        )
        self.prospect_table.verticalHeader().setVisible(False)
        self.prospect_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospect_table.setSelectionMode(QTableWidget.SingleSelection)
        self.prospect_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prospect_table.setShowGrid(False)
        self.prospect_table.setAlternatingRowColors(False)
        self.prospect_table.setWordWrap(False)
        self.prospect_table.setMinimumHeight(410)
        self.prospect_table.setFocusPolicy(Qt.NoFocus)
        self.prospect_table.itemSelectionChanged.connect(self._on_selection)

        header = self.prospect_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        left_layout.addWidget(self.prospect_table, 1)

        # Prospect cockpit
        right = QFrame()
        right.setObjectName("AiConsole")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        prospect_hero = QFrame()
        prospect_hero.setObjectName("ProspectHero")
        prospect_hero_layout = QVBoxLayout(prospect_hero)
        prospect_hero_layout.setContentsMargins(17, 14, 17, 14)
        prospect_hero_layout.setSpacing(3)

        right_section = QLabel("PROSPECT INTELLIGENCE")
        right_section.setObjectName("AiProspectEyebrow")
        self.selected_title = QLabel("Sélectionnez un prospect")
        self.selected_title.setObjectName("AiSelectedTitle")
        self.selected_title.setWordWrap(True)
        self.selected_meta = QLabel(
            "Le copilote préparera une recommandation personnalisée."
        )
        self.selected_meta.setObjectName("AiSelectedMeta")
        self.selected_meta.setWordWrap(True)

        prospect_hero_layout.addWidget(right_section)
        prospect_hero_layout.addWidget(self.selected_title)
        prospect_hero_layout.addWidget(self.selected_meta)
        right_layout.addWidget(prospect_hero)

        console_body = QWidget()
        console_body.setObjectName("AiConsoleBody")
        console_layout = QVBoxLayout(console_body)
        console_layout.setContentsMargins(14, 12, 14, 14)
        console_layout.setSpacing(10)

        self.copilot_card = QFrame()
        self.copilot_card.setObjectName("CopilotSummary")
        copilot_layout = QVBoxLayout(self.copilot_card)
        copilot_layout.setContentsMargins(13, 11, 13, 12)
        copilot_layout.setSpacing(6)

        synth_head = QHBoxLayout()
        copilot_caption = QLabel("✦  SYNTHÈSE DU COPILOTE")
        copilot_caption.setObjectName("AiCopilotCaption")
        confidence_chip = QLabel("ANALYSE LIVE")
        confidence_chip.setObjectName("AiAnalysisChip")
        confidence_chip.setAlignment(Qt.AlignCenter)
        confidence_chip.setFixedHeight(23)

        synth_head.addWidget(copilot_caption)
        synth_head.addStretch()
        synth_head.addWidget(confidence_chip)
        copilot_layout.addLayout(synth_head)

        self.copilot_priority = QLabel("Priorité : —")
        self.copilot_objective = QLabel("Objectif : sélectionnez un prospect")
        self.copilot_action = QLabel("Action conseillée : —")
        for label in (
            self.copilot_priority,
            self.copilot_objective,
            self.copilot_action,
        ):
            label.setProperty("aiCopilotLine", True)
            label.setWordWrap(True)

        copilot_layout.addWidget(self.copilot_priority)
        copilot_layout.addWidget(self.copilot_objective)
        copilot_layout.addWidget(self.copilot_action)
        console_layout.addWidget(self.copilot_card)

        main_cta = QHBoxLayout()
        main_cta.setSpacing(8)

        open_copilot_btn = QPushButton("✦  Ouvrir le copilote")
        open_copilot_btn.setProperty("aiDarkButton", True)
        open_copilot_btn.setCursor(Qt.PointingHandCursor)
        open_copilot_btn.setMinimumHeight(42)
        open_copilot_btn.clicked.connect(self.open_prospect_copilot)

        qualification_btn = QPushButton("Qualification automatique")
        qualification_btn.setProperty("aiPrimaryButton", True)
        qualification_btn.setCursor(Qt.PointingHandCursor)
        qualification_btn.setMinimumHeight(42)
        qualification_btn.clicked.connect(self.open_automatic_qualification)

        main_cta.addWidget(open_copilot_btn, 1)
        main_cta.addWidget(qualification_btn, 1)
        console_layout.addLayout(main_cta)

        tools_shell = QFrame()
        tools_shell.setObjectName("AiToolsShell")
        tools_box = QVBoxLayout(tools_shell)
        tools_box.setContentsMargins(11, 10, 11, 11)
        tools_box.setSpacing(8)

        tools_head = QHBoxLayout()
        tools_title = QLabel("OUTILS INTELLIGENTS")
        tools_title.setProperty("aiToolbarTitle", True)
        tools_hint = QLabel("Choisissez une action pour le prospect sélectionné")
        tools_hint.setProperty("aiToolbarHint", True)
        tools_head.addWidget(tools_title)
        tools_head.addStretch()
        tools_head.addWidget(tools_hint)
        tools_box.addLayout(tools_head)

        families = QGridLayout()
        families.setHorizontalSpacing(8)
        families.setVerticalSpacing(8)

        family_specs = [
            (
                "ANALYSER", "✦", "blue",
                [
                    ("Qualification", self.open_automatic_qualification),
                    ("Expliquer le score", self.explain_score),
                    ("Knowledge Engine", self.show_knowledge_overview),
                ],
            ),
            (
                "PRÉPARER", "☎", "amber",
                [
                    ("Préparer l'appel", self.prepare_call),
                    ("Questions découverte", self.prepare_call),
                    ("Traiter les objections", self.generate_objections),
                ],
            ),
            (
                "COMMUNIQUER", "✉", "violet",
                [
                    ("Script Form@Prof", self.generate_call_script),
                    ("E-mail Form@Prof", self.generate_email),
                ],
            ),
            (
                "SUIVRE", "↗", "green",
                [
                    ("Prochaine action", self.recommend_action),
                    ("Plan de relance", self.generate_follow_up_plan),
                    ("Mémoire commerciale", self.open_commercial_memory),
                    ("Ajouter une mémoire", self.add_commercial_memory),
                ],
            ),
        ]

        for family_index, (family_name, family_icon, tone, buttons) in enumerate(
            family_specs
        ):
            family = QFrame()
            family.setProperty("aiFamilyCard", True)
            family.setProperty("aiFamilyTone", tone)
            family_layout = QVBoxLayout(family)
            family_layout.setContentsMargins(9, 8, 9, 9)
            family_layout.setSpacing(6)

            family_head = QHBoxLayout()
            family_head.setSpacing(6)

            family_badge = QLabel(family_icon)
            family_badge.setProperty("aiFamilyBadge", True)
            family_badge.setProperty("aiFamilyTone", tone)
            family_badge.setFixedSize(25, 25)
            family_badge.setAlignment(Qt.AlignCenter)

            family_label = QLabel(family_name)
            family_label.setProperty("aiFamilyLabel", True)
            family_label.setProperty("aiFamilyTone", tone)

            family_head.addWidget(family_badge)
            family_head.addWidget(family_label)
            family_head.addStretch()
            family_layout.addLayout(family_head)

            for caption, callback in buttons:
                button = QPushButton(caption)
                button.setProperty("aiToolButton", True)
                button.setCursor(Qt.PointingHandCursor)
                button.setMinimumHeight(34)
                button.clicked.connect(callback)
                family_layout.addWidget(button)

            family_layout.addStretch()
            families.addWidget(family, family_index // 2, family_index % 2)

        tools_box.addLayout(families)
        console_layout.addWidget(tools_shell)

        output_card = QFrame()
        output_card.setObjectName("AiOutputCard")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(11, 10, 11, 11)
        output_layout.setSpacing(7)

        output_head = QHBoxLayout()
        output_identity = QHBoxLayout()
        output_identity.setSpacing(8)

        output_orb = QLabel("✦")
        output_orb.setObjectName("AiOutputOrb")
        output_orb.setFixedSize(30, 30)
        output_orb.setAlignment(Qt.AlignCenter)

        output_titles = QVBoxLayout()
        output_titles.setSpacing(0)
        output_title = QLabel("RÉPONSE DU COPILOTE")
        output_title.setObjectName("AiOutputTitle")
        output_subtitle = QLabel(
            "Analyse structurée • recommandation • argumentaire"
        )
        output_subtitle.setObjectName("AiOutputSubtitle")
        output_titles.addWidget(output_title)
        output_titles.addWidget(output_subtitle)

        output_identity.addWidget(output_orb)
        output_identity.addLayout(output_titles)

        copy_button = QPushButton("⧉  Copier")
        copy_button.setProperty("aiSecondaryButton", True)
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setMinimumHeight(29)
        copy_button.clicked.connect(self.copy_output)

        output_head.addLayout(output_identity)
        output_head.addStretch()
        output_head.addWidget(copy_button)

        self.output = QTextEdit()
        self.output.setObjectName("AiOutput")
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Choisissez une action : le copilote affichera ici son analyse, "
            "son script ou sa recommandation…"
        )
        self.output.setMinimumHeight(215)

        output_layout.addLayout(output_head)
        output_layout.addWidget(self.output, 1)
        console_layout.addWidget(output_card, 1)
        right_layout.addWidget(console_body, 1)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([480, 680])
        main_layout.addWidget(split, 1)

        # ------------------------------------------------------------------
        # FEED — priorités opérationnelles et historique
        # ------------------------------------------------------------------
        bottom = QSplitter(Qt.Horizontal)
        bottom.setObjectName("AiFeedSplitter")
        bottom.setChildrenCollapsible(False)
        bottom.setHandleWidth(10)

        insight_card = QFrame()
        insight_card.setObjectName("AiInsightCard")
        insight_card.setProperty("aiFeedCard", True)
        insight_layout = QVBoxLayout(insight_card)
        insight_layout.setContentsMargins(15, 13, 15, 14)
        insight_layout.setSpacing(6)

        insight_overline = QLabel("PRIORITÉS OPÉRATIONNELLES")
        insight_overline.setProperty("aiOverline", True)
        insight_title = QLabel("Priorités recommandées")
        insight_title.setProperty("aiFeedTitle", True)
        self.insights_list = QListWidget()
        self.insights_list.setObjectName("AiInsightsList")
        self.insights_list.setAlternatingRowColors(False)

        insight_layout.addWidget(insight_overline)
        insight_layout.addWidget(insight_title)
        insight_layout.addWidget(self.insights_list)

        history_card = QFrame()
        history_card.setObjectName("AiHistoryCard")
        history_card.setProperty("aiFeedCard", True)
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(15, 13, 15, 14)
        history_layout.setSpacing(6)

        history_overline = QLabel("ACTIVITY STREAM")
        history_overline.setProperty("aiOverline", True)
        history_title = QLabel("Activité du copilote")
        history_title.setProperty("aiFeedTitle", True)
        self.history_list = QListWidget()
        self.history_list.setObjectName("AiHistoryList")
        self.history_list.itemClicked.connect(self._open_history)

        history_layout.addWidget(history_overline)
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_list)

        bottom.addWidget(insight_card)
        bottom.addWidget(history_card)
        bottom.setSizes([560, 560])
        bottom.setMinimumHeight(220)
        main_layout.addWidget(bottom)

        root.addWidget(self.main_content)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.main_content.setVisible(False)

    def rafraichir(self):
        """Charge l'assistant sans jamais bloquer l'ouverture de la page."""
        try:
            if CloudRuntime.is_active():
                if not isinstance(self.service, CloudAssistantService):
                    self.service = CloudAssistantService(CloudRuntime.api())
                else:
                    self.service.refresh()
            elif ApplicationState.has_project():
                project = ApplicationState.get_project()
                database = getattr(project, "database", None)
                if not database:
                    raise RuntimeError("La base locale du projet est introuvable.")
                self.service = AssistantService(database)
            else:
                self.service = None
                self.empty_label.setText("Ouvrez un projet pour utiliser l'Assistant IA.")
                self.empty_label.setVisible(True)
                self.main_content.setVisible(False)
                return

            data = self.service.dashboard_summary()
            self.empty_label.setVisible(False)
            self.main_content.setVisible(True)
            self.kpi_labels["priorities"].setText(str(data["priorities"]))
            self.kpi_labels["due_today"].setText(str(data["due_today"]))
            self.kpi_labels["overdue"].setText(str(data["overdue"]))
            self.kpi_labels["quality"].setText(f"{data['quality']} %")
            self._load_prospects()
            self._load_insights()
            self._load_history()
        except Exception as exc:
            self.service = None
            self.empty_label.setText(
                "L'Assistant IA n'a pas pu charger les données.\n\n"
                f"{exc}"
            )
            self.empty_label.setVisible(True)
            self.main_content.setVisible(False)

    def _load_prospects(self, *_args):
        if not self.service:
            return

        limit = int(self.limit_combo.currentText())
        query = self.search_input.text().strip()
        previous_id = (
            str(self.current_prospect_id)
            if self.current_prospect_id is not None
            else None
        )

        if query and hasattr(self.service, "search_prospects"):
            prospects = self.service.search_prospects(query, limit)
            self.results_label.setText(
                f"{len(prospects)} résultat(s) dans tous les prospects visibles"
            )
        else:
            prospects = self.service.top_prospects(limit)
            self.results_label.setText(
                f"Top {len(prospects)} prospect(s) recommandé(s)"
            )

        self.prospect_table.blockSignals(True)
        self.prospect_table.setUpdatesEnabled(False)
        self.prospect_table.clearContents()
        self.prospect_table.setRowCount(len(prospects))
        selected_row = None
        for row_index, prospect in enumerate(prospects):
            name_item = QTableWidgetItem(prospect.entreprise)
            name_item.setData(Qt.UserRole, prospect.prospect_id)
            score_item = QTableWidgetItem(f"{prospect.score}/100")
            grade_item = QTableWidgetItem(prospect.grade)
            contact = (
                "📞 📧"
                if prospect.telephone and prospect.email
                else (
                    "📞"
                    if prospect.telephone
                    else ("📧" if prospect.email else "—")
                )
            )
            contact_item = QTableWidgetItem(contact)
            for column, item in enumerate(
                (name_item, score_item, grade_item, contact_item)
            ):
                self.prospect_table.setItem(row_index, column, item)
            if previous_id == str(prospect.prospect_id):
                selected_row = row_index

        self.prospect_table.resizeColumnsToContents()
        self.prospect_table.setUpdatesEnabled(True)
        self.prospect_table.blockSignals(False)

        if prospects:
            self.prospect_table.selectRow(
                selected_row if selected_row is not None else 0
            )
        else:
            self.current_prospect_id = None
            self.selected_title.setText("Aucune entreprise trouvée")
            self.selected_meta.setText(
                "Modifiez la recherche pour afficher un autre prospect."
            )
            self.copilot_priority.setText("Priorité : —")
            self.copilot_objective.setText("Objectif : aucun prospect sélectionné")
            self.copilot_action.setText("Action conseillée : —")
            self.output.clear()

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
        raw_id = first.data(Qt.UserRole)
        self.current_prospect_id = str(raw_id) if isinstance(self.service, CloudAssistantService) else int(raw_id)
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
        NotificationManager.success(title, "Le contenu a été généré par Form@Prospect.")
        try:
            # Le journal historique SQLite n'est disponible qu'en mode local.
            if not isinstance(self.service, CloudAssistantService):
                ActivityService.record(
                    title,
                    "Contenu généré par l'Assistant IA local.",
                    category="ai",
                    level="success",
                )
        except Exception:
            pass
        self._load_history()

    def add_commercial_memory(self):
        if not self._require_selection():
            return

        p = assistant_page_palette(get_theme_preference())

        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une mémoire commerciale")
        dialog.setModal(True)
        dialog.resize(650, 520)
        dialog.setMinimumSize(610, 480)
        dialog.setStyleSheet(
            f"""
            QDialog {{
                background:{p['page']};
                color:{p['text']};
            }}
            QLabel {{
                background:transparent;
                border:none;
            }}
            QFrame#MemoryHeader {{
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p['hero_1']},
                    stop:1 {p['hero_3']}
                );
                border:none;
            }}
            QFrame#MemoryProspectCard {{
                background:{p['primary_soft']};
                border:1px solid {p['border_strong']};
                border-radius:13px;
            }}
            QFrame#MemoryFormCard {{
                background:{p['surface']};
                border:1px solid {p['border']};
                border-radius:15px;
            }}
            QComboBox {{
                background:{p['surface']};
                color:{p['text']};
                border:1px solid {p['border']};
                border-radius:10px;
                padding:0 11px;
                font-size:10px;
                font-weight:800;
            }}
            QComboBox:focus {{
                border:1px solid #338CE4;
            }}
            QComboBox::drop-down {{
                border:none;
                width:30px;
            }}
            QComboBox QAbstractItemView {{
                background:{p['surface']};
                color:{p['text']};
                border:1px solid {p['border']};
                selection-background-color:{p['selection']};
                selection-color:{p['selection_text']};
            }}
            QTextEdit {{
                background:{p['surface_alt']};
                color:{p['text']};
                border:1px solid {p['border']};
                border-radius:11px;
                padding:11px;
                font-size:10px;
                selection-background-color:#338CE4;
                selection-color:#FFFFFF;
            }}
            QTextEdit:focus {{
                border:1px solid #338CE4;
            }}
            QPushButton#MemoryCancel {{
                background:{p['surface']};
                color:{p['text_soft']};
                border:1px solid {p['border']};
                border-radius:10px;
                padding:0 17px;
                font-size:10px;
                font-weight:850;
            }}
            QPushButton#MemoryCancel:hover {{
                background:{p['surface_alt']};
                color:{p['primary_text']};
                border-color:{p['border_strong']};
            }}
            QPushButton#MemorySave {{
                background:#338CE4;
                color:#FFFFFF;
                border:1px solid #5FAFF5;
                border-radius:10px;
                padding:0 19px;
                font-size:10px;
                font-weight:900;
            }}
            QPushButton#MemorySave:hover {{
                background:#287FD4;
            }}
            QPushButton#MemorySave:disabled {{
                background:{p['surface_soft']};
                color:{p['muted']};
                border-color:{p['border']};
            }}
            """
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("MemoryHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 19, 24, 17)
        header_layout.setSpacing(4)

        overline = QLabel("MÉMOIRE COMMERCIALE  •  COPILOTE")
        overline.setStyleSheet(
            "color:#79C7FF;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        title = QLabel("Ajouter une information à retenir")
        title.setStyleSheet("color:#FFFFFF;font-size:22px;font-weight:950;")
        subtitle = QLabel(
            "Cette information enrichira le contexte du prospect et pourra être "
            "réutilisée lors des prochains échanges."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#C5D7E9;font-size:10px;")

        header_layout.addWidget(overline)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(22, 17, 22, 19)
        body_layout.setSpacing(12)

        prospect_card = QFrame()
        prospect_card.setObjectName("MemoryProspectCard")
        prospect_layout = QHBoxLayout(prospect_card)
        prospect_layout.setContentsMargins(13, 10, 13, 10)

        prospect_text = QVBoxLayout()
        prospect_text.setSpacing(1)
        prospect_caption = QLabel("PROSPECT SÉLECTIONNÉ")
        prospect_caption.setStyleSheet(
            f"color:{p['primary_text']};font-size:8px;font-weight:900;"
            "letter-spacing:.7px;"
        )
        prospect_name = QLabel(
            self.selected_title.text().strip() or "Prospect sélectionné"
        )
        prospect_name.setStyleSheet(
            f"color:{p['text']};font-size:11px;font-weight:900;"
        )

        prospect_text.addWidget(prospect_caption)
        prospect_text.addWidget(prospect_name)
        prospect_layout.addLayout(prospect_text, 1)
        body_layout.addWidget(prospect_card)

        form_card = QFrame()
        form_card.setObjectName("MemoryFormCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(15, 14, 15, 15)
        form_layout.setSpacing(8)

        category_label = QLabel("Catégorie de mémoire")
        category_label.setStyleSheet(
            f"color:{p['text_soft']};font-size:10px;font-weight:850;"
        )
        category_combo = QComboBox()
        category_combo.addItems(list(self.service.MEMORY_TYPES))
        category_combo.setMinimumHeight(40)

        content_label = QLabel("Information à mémoriser")
        content_label.setStyleSheet(
            f"color:{p['text_soft']};font-size:10px;font-weight:850;"
        )
        content_edit = QTextEdit()
        content_edit.setPlaceholderText(
            "Exemple : le dirigeant souhaite gagner du temps sur le suivi des "
            "chantiers et veut revoir la proposition après la rentrée…"
        )
        content_edit.setMinimumHeight(145)

        helper = QLabel(
            "Conseil : saisissez une information courte, factuelle et utile pour "
            "le prochain échange."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color:{p['muted']};font-size:9px;")

        form_layout.addWidget(category_label)
        form_layout.addWidget(category_combo)
        form_layout.addSpacing(2)
        form_layout.addWidget(content_label)
        form_layout.addWidget(content_edit)
        form_layout.addWidget(helper)
        body_layout.addWidget(form_card, 1)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        actions.addStretch()

        cancel_button = QPushButton("Annuler")
        cancel_button.setObjectName("MemoryCancel")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumSize(104, 40)

        save_button = QPushButton("＋  Ajouter à la mémoire")
        save_button.setObjectName("MemorySave")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumSize(190, 40)
        save_button.setEnabled(False)

        def update_save_state():
            save_button.setEnabled(bool(content_edit.toPlainText().strip()))

        content_edit.textChanged.connect(update_save_state)
        cancel_button.clicked.connect(dialog.reject)
        save_button.clicked.connect(dialog.accept)

        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        body_layout.addLayout(actions)
        root.addWidget(body, 1)

        if dialog.exec() != QDialog.Accepted:
            return

        memory_type = category_combo.currentText().strip()
        content = content_edit.toPlainText().strip()

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
        try:
            if not isinstance(self.service, CloudAssistantService):
                ActivityService.record(
                    "Mémoire commerciale",
                    f"Une information « {memory_type} » a été ajoutée.",
                    category="ai",
                    level="success",
                )
        except Exception:
            pass

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
