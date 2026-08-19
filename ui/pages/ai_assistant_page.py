from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QHeaderView, QSplitter, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.premium_theme import (
    BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON,
    SECONDARY_BUTTON, SUCCESS, TEXT,
)
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#CBD5E1;min-height:40px;border-radius:5px;}"
            "QScrollBar::handle:vertical:hover{background:#94A3B8;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        content = QWidget()
        content.setStyleSheet(f"background:{PAGE_BG};")
        root = QVBoxLayout(content)
        root.setContentsMargins(30, 24, 30, 34)
        root.setSpacing(16)

        # HERO
        hero = QFrame()
        hero.setObjectName("AiHero")
        hero.setMinimumHeight(162)
        hero.setStyleSheet(
            "QFrame#AiHero{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #071C35, stop:0.48 #0B2A52, stop:1 #145A91);"
            "border:1px solid #173F6D;border-radius:24px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(26, 22, 24, 22)
        hero_layout.setSpacing(22)

        orb = QFrame()
        orb.setObjectName("AiOrb")
        orb.setFixedSize(92, 92)
        orb.setStyleSheet(
            "QFrame#AiOrb{"
            "background:qradialgradient(cx:.35,cy:.28,radius:.82,"
            "stop:0 #6BC2FF, stop:.28 #338CE4, stop:.72 #145A91, stop:1 #0B2A52);"
            "border:1px solid #75C8FF;border-radius:46px;"
            "}"
        )
        orb_layout = QVBoxLayout(orb)
        orb_layout.setContentsMargins(0, 0, 0, 0)
        ai_glyph = QLabel("✦")
        ai_glyph.setAlignment(Qt.AlignCenter)
        ai_glyph.setStyleSheet(
            "color:#FFFFFF;font-size:38px;font-weight:900;background:transparent;"
        )
        orb_layout.addWidget(ai_glyph)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)
        eyebrow = QLabel("FORM@PROSPECT  •  INTELLIGENCE COMMERCIALE")
        eyebrow.setStyleSheet(
            "color:#79C7FF;font-size:9px;font-weight:900;letter-spacing:1.4px;"
        )
        hero_title = QLabel("Votre copilote commercial")
        hero_title.setStyleSheet("color:#FFFFFF;font-size:31px;font-weight:900;")
        hero_subtitle = QLabel(
            "Détectez les meilleures opportunités, préparez chaque échange "
            "et transformez votre CRM en plan d'action."
        )
        hero_subtitle.setWordWrap(True)
        hero_subtitle.setStyleSheet("color:#C9D8EA;font-size:12px;")
        hero_text.addWidget(eyebrow)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)

        hero_status = QVBoxLayout()
        hero_status.setSpacing(8)
        live_badge = QLabel("●  COPILOTE ACTIF")
        live_badge.setAlignment(Qt.AlignCenter)
        live_badge.setFixedHeight(34)
        live_badge.setMinimumWidth(160)
        live_badge.setStyleSheet(
            "background:#E9FFF3;color:#087A45;border:1px solid #A7F3D0;"
            "border-radius:12px;padding:0 13px;font-size:10px;font-weight:900;"
        )
        privacy = QLabel("🔒  Analyse interne\nAucune donnée envoyée à une IA externe")
        privacy.setAlignment(Qt.AlignCenter)
        privacy.setWordWrap(True)
        privacy.setMinimumWidth(235)
        privacy.setStyleSheet(
            "color:#D7E7F8;background:rgba(255,255,255,0.08);"
            "border:1px solid rgba(255,255,255,0.15);border-radius:13px;"
            "padding:10px 13px;font-size:10px;font-weight:750;"
        )
        hero_status.addWidget(live_badge)
        hero_status.addWidget(privacy)

        hero_layout.addWidget(orb, 0, Qt.AlignVCenter)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(hero_status)
        root.addWidget(hero)

        self.empty_label = QLabel("Ouvrez un projet pour activer le copilote commercial.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setMinimumHeight(110)
        self.empty_label.setStyleSheet(
            f"background:#FFFFFF;color:{MUTED};border:1px dashed #C9D7E6;"
            "border-radius:18px;font-size:13px;"
        )
        root.addWidget(self.empty_label)

        self.main_content = QWidget()
        main_layout = QVBoxLayout(self.main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # KPI executive
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setHorizontalSpacing(12)
        self.kpi_grid.setVerticalSpacing(12)
        self.kpi_labels = {}

        metrics = [
            ("priorities", "Prioritaires", "🔥", "À traiter maintenant", "#FF9A3C", "#FFF5EB"),
            ("due_today", "Aujourd'hui", "📅", "Actions planifiées", "#338CE4", "#EEF6FF"),
            ("overdue", "En retard", "⚠", "Relances à reprendre", "#EF4444", "#FFF1F2"),
            ("quality", "Qualité CRM", "✦", "Complétude des contacts", "#8B5CF6", "#F5F3FF"),
        ]

        for column, (key, label, icon, caption, accent, soft) in enumerate(metrics):
            card = QFrame()
            card.setObjectName(f"AiMetric_{key}")
            card.setMinimumHeight(116)
            card.setStyleSheet(
                f"QFrame#AiMetric_{key}{{background:#FFFFFF;"
                "border:1px solid #E4EBF4;border-radius:18px;}"
                "QLabel{background:transparent;border:none;}"
            )
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 14, 16, 13)
            layout.setSpacing(5)

            top_row = QHBoxLayout()
            icon_box = QLabel(icon)
            icon_box.setFixedSize(32, 32)
            icon_box.setAlignment(Qt.AlignCenter)
            icon_box.setStyleSheet(
                f"background:{soft};color:{accent};border:none;"
                "border-radius:10px;font-size:14px;font-weight:900;"
            )
            metric_name = QLabel(label)
            metric_name.setStyleSheet("color:#53657C;font-size:10px;font-weight:850;")
            top_row.addWidget(icon_box)
            top_row.addWidget(metric_name)
            top_row.addStretch()

            value = QLabel("0")
            value.setStyleSheet("color:#081A31;font-size:28px;font-weight:900;")
            foot = QLabel(caption)
            foot.setStyleSheet("color:#94A3B8;font-size:9px;")
            accent_line = QFrame()
            accent_line.setFixedHeight(3)
            accent_line.setStyleSheet(f"background:{accent};border:none;border-radius:1px;")

            layout.addLayout(top_row)
            layout.addWidget(value)
            layout.addWidget(foot)
            layout.addWidget(accent_line)
            self.kpi_grid.addWidget(card, 0, column)
            self.kpi_labels[key] = value

        main_layout.addLayout(self.kpi_grid)

        # Command center
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(12)
        split.setStyleSheet("QSplitter::handle{background:transparent;}")

        # Opportunity radar
        left = QFrame()
        left.setObjectName("AiRadarCard")
        left.setStyleSheet(
            "QFrame#AiRadarCard{background:#FFFFFF;border:1px solid #E4EBF4;"
            "border-radius:20px;}QLabel{background:transparent;border:none;}"
        )
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 17, 18, 18)
        left_layout.setSpacing(10)

        left_top = QHBoxLayout()
        left_titles = QVBoxLayout()
        left_titles.setSpacing(2)
        section = QLabel("OPPORTUNITY RADAR")
        section.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1.2px;"
        )
        left_title = QLabel("Prospects à fort potentiel")
        left_title.setStyleSheet("color:#0B1220;font-size:18px;font-weight:900;")
        left_sub = QLabel("Le copilote classe automatiquement les opportunités à traiter.")
        left_sub.setWordWrap(True)
        left_sub.setStyleSheet("color:#7A8A9E;font-size:10px;")
        left_titles.addWidget(section)
        left_titles.addWidget(left_title)
        left_titles.addWidget(left_sub)

        radar_badge = QLabel("LIVE")
        radar_badge.setAlignment(Qt.AlignCenter)
        radar_badge.setFixedSize(48, 26)
        radar_badge.setStyleSheet(
            "background:#E9FFF3;color:#087A45;border:1px solid #A7F3D0;"
            "border-radius:9px;font-size:9px;font-weight:900;"
        )
        left_top.addLayout(left_titles, 1)
        left_top.addWidget(radar_badge, 0, Qt.AlignTop)
        left_layout.addLayout(left_top)

        search_shell = QFrame()
        search_shell.setObjectName("AiSearchShell")
        search_shell.setStyleSheet(
            "QFrame#AiSearchShell{background:#F7FAFE;border:1px solid #DDE7F1;"
            "border-radius:12px;}"
        )
        search_layout = QHBoxLayout(search_shell)
        search_layout.setContentsMargins(10, 0, 9, 0)
        search_layout.setSpacing(7)
        search_icon = QLabel("⌕")
        search_icon.setStyleSheet(
            "color:#338CE4;font-size:18px;font-weight:900;background:transparent;"
        )
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher entreprise, ville, téléphone ou e-mail…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet(
            "QLineEdit{background:transparent;color:#172033;border:none;"
            "font-size:11px;padding:0 3px;}"
        )
        self.search_input.textChanged.connect(self._load_prospects)
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input, 1)
        left_layout.addWidget(search_shell)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        top_label = QLabel("TOP")
        top_label.setStyleSheet("color:#7A8A9E;font-size:9px;font-weight:850;")
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["10", "25", "50", "100"])
        self.limit_combo.setCurrentText("25")
        self.limit_combo.setFixedWidth(72)
        self.limit_combo.setMinimumHeight(32)
        self.limit_combo.setStyleSheet(
            "QComboBox{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:4px 8px;font-size:10px;font-weight:800;}"
            "QComboBox QAbstractItemView{background:white;color:#172033;"
            "selection-background-color:#EAF4FF;selection-color:#0B2A52;}"
        )
        self.limit_combo.currentTextChanged.connect(self._load_prospects)
        self.results_label = QLabel("")
        self.results_label.setStyleSheet("color:#8A98AA;font-size:9px;")
        controls.addWidget(top_label)
        controls.addWidget(self.limit_combo)
        controls.addStretch()
        controls.addWidget(self.results_label)
        left_layout.addLayout(controls)

        self.prospect_table = QTableWidget(0, 4)
        self.prospect_table.setHorizontalHeaderLabels(["Entreprise", "Score", "Niveau", "Contact"])
        self.prospect_table.verticalHeader().setVisible(False)
        self.prospect_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospect_table.setSelectionMode(QTableWidget.SingleSelection)
        self.prospect_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prospect_table.setShowGrid(False)
        self.prospect_table.setAlternatingRowColors(False)
        self.prospect_table.setWordWrap(False)
        self.prospect_table.setMinimumHeight(430)
        self.prospect_table.setFocusPolicy(Qt.NoFocus)
        self.prospect_table.itemSelectionChanged.connect(self._on_selection)
        header = self.prospect_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.prospect_table.setStyleSheet(
            "QTableWidget{background:#FFFFFF;color:#172033;border:1px solid #E4EBF4;"
            "border-radius:13px;selection-background-color:#E9F4FF;"
            "selection-color:#0B2A52;outline:none;font-size:10px;}"
            "QHeaderView::section{background:#081F3D;color:#FFFFFF;border:none;"
            "border-right:1px solid #153B67;padding:11px 7px;font-size:9px;font-weight:900;}"
            "QTableWidget::item{background:#FFFFFF;border:none;"
            "border-bottom:1px solid #EFF3F7;padding:10px 8px;}"
            "QTableWidget::item:selected{background:#E9F4FF;color:#0B2A52;"
            "border-left:3px solid #338CE4;}"
        )
        left_layout.addWidget(self.prospect_table, 1)

        # Copilot console
        right = QFrame()
        right.setObjectName("AiConsole")
        right.setStyleSheet(
            "QFrame#AiConsole{background:#FFFFFF;border:1px solid #DCE7F3;"
            "border-radius:20px;}QLabel{background:transparent;border:none;}"
        )
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        prospect_hero = QFrame()
        prospect_hero.setObjectName("ProspectHero")
        prospect_hero.setStyleSheet(
            "QFrame#ProspectHero{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #081F3D, stop:1 #123F70);border:none;"
            "border-top-left-radius:19px;border-top-right-radius:19px;}"
            "QLabel{background:transparent;border:none;}"
        )
        prospect_hero_layout = QVBoxLayout(prospect_hero)
        prospect_hero_layout.setContentsMargins(18, 15, 18, 15)
        prospect_hero_layout.setSpacing(4)
        right_section = QLabel("PROSPECT INTELLIGENCE")
        right_section.setStyleSheet(
            "color:#79C7FF;font-size:9px;font-weight:900;letter-spacing:1.1px;"
        )
        self.selected_title = QLabel("Sélectionnez un prospect")
        self.selected_title.setWordWrap(True)
        self.selected_title.setStyleSheet("color:#FFFFFF;font-size:21px;font-weight:900;")
        self.selected_meta = QLabel("Le copilote préparera une recommandation personnalisée.")
        self.selected_meta.setWordWrap(True)
        self.selected_meta.setStyleSheet("color:#B7CADF;font-size:10px;")
        prospect_hero_layout.addWidget(right_section)
        prospect_hero_layout.addWidget(self.selected_title)
        prospect_hero_layout.addWidget(self.selected_meta)
        right_layout.addWidget(prospect_hero)

        console_body = QWidget()
        console_body.setStyleSheet("background:transparent;")
        console_layout = QVBoxLayout(console_body)
        console_layout.setContentsMargins(16, 14, 16, 16)
        console_layout.setSpacing(11)

        self.copilot_card = QFrame()
        self.copilot_card.setObjectName("CopilotSummary")
        self.copilot_card.setStyleSheet(
            "QFrame#CopilotSummary{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #EEF7FF, stop:1 #F7FBFF);border:1px solid #BFDDFC;"
            "border-radius:15px;}QLabel{background:transparent;border:none;}"
        )
        copilot_layout = QVBoxLayout(self.copilot_card)
        copilot_layout.setContentsMargins(14, 12, 14, 13)
        copilot_layout.setSpacing(7)

        synth_head = QHBoxLayout()
        copilot_caption = QLabel("✦  SYNTHÈSE DU COPILOTE")
        copilot_caption.setStyleSheet(
            "color:#1473C9;font-size:9px;font-weight:900;letter-spacing:.8px;"
        )
        confidence_chip = QLabel("ANALYSE LIVE")
        confidence_chip.setAlignment(Qt.AlignCenter)
        confidence_chip.setFixedHeight(24)
        confidence_chip.setStyleSheet(
            "background:#FFFFFF;color:#338CE4;border:1px solid #CFE4F8;"
            "border-radius:8px;padding:0 8px;font-size:8px;font-weight:900;"
        )
        synth_head.addWidget(copilot_caption)
        synth_head.addStretch()
        synth_head.addWidget(confidence_chip)
        copilot_layout.addLayout(synth_head)

        self.copilot_priority = QLabel("Priorité : —")
        self.copilot_objective = QLabel("Objectif : sélectionnez un prospect")
        self.copilot_action = QLabel("Action conseillée : —")
        for label in (self.copilot_priority, self.copilot_objective, self.copilot_action):
            label.setWordWrap(True)
            label.setStyleSheet("color:#172033;font-size:10px;font-weight:750;")
        copilot_layout.addWidget(self.copilot_priority)
        copilot_layout.addWidget(self.copilot_objective)
        copilot_layout.addWidget(self.copilot_action)
        console_layout.addWidget(self.copilot_card)

        main_cta = QHBoxLayout()
        main_cta.setSpacing(8)
        open_copilot_btn = QPushButton("✦  Ouvrir le copilote")
        open_copilot_btn.setCursor(Qt.PointingHandCursor)
        open_copilot_btn.setMinimumHeight(44)
        open_copilot_btn.setStyleSheet(
            "QPushButton{background:#081F3D;color:#FFFFFF;border:none;border-radius:11px;"
            "padding:0 16px;font-size:11px;font-weight:900;}"
            "QPushButton:hover{background:#123F70;}"
        )
        open_copilot_btn.clicked.connect(self.open_prospect_copilot)

        qualification_btn = QPushButton("🎯  Qualification automatique")
        qualification_btn.setCursor(Qt.PointingHandCursor)
        qualification_btn.setMinimumHeight(44)
        qualification_btn.setStyleSheet(
            "QPushButton{background:#338CE4;color:#FFFFFF;border:none;border-radius:11px;"
            "padding:0 16px;font-size:11px;font-weight:900;}"
            "QPushButton:hover{background:#267FD6;}"
            "QPushButton:pressed{background:#1E6EBB;}"
        )
        qualification_btn.clicked.connect(self.open_automatic_qualification)
        main_cta.addWidget(open_copilot_btn, 1)
        main_cta.addWidget(qualification_btn, 1)
        console_layout.addLayout(main_cta)

        tools_shell = QFrame()
        tools_shell.setObjectName("AiToolsShell")
        tools_shell.setStyleSheet(
            "QFrame#AiToolsShell{background:#F8FBFF;border:1px solid #E4EBF4;"
            "border-radius:15px;}QLabel{background:transparent;border:none;}"
        )
        tools_box = QVBoxLayout(tools_shell)
        tools_box.setContentsMargins(12, 11, 12, 12)
        tools_box.setSpacing(9)

        tools_title = QLabel("OUTILS INTELLIGENTS")
        tools_title.setStyleSheet(
            "color:#526276;font-size:10px;font-weight:900;letter-spacing:.9px;"
        )
        tools_box.addWidget(tools_title)

        families = QGridLayout()
        families.setHorizontalSpacing(8)
        families.setVerticalSpacing(8)

        family_specs = [
            (
                "ANALYSER", "✦", "#EEF6FF", "#1473C9",
                [
                    ("🎯  Qualification", self.open_automatic_qualification),
                    ("📊  Expliquer le score", self.explain_score),
                    ("📚  Knowledge Engine", self.show_knowledge_overview),
                ],
            ),
            (
                "PRÉPARER", "☎", "#FFF7ED", "#C56A14",
                [
                    ("📞  Préparer l'appel", self.prepare_call),
                    ("❓  Questions découverte", self.prepare_call),
                    ("🛡  Traiter objections", self.generate_objections),
                ],
            ),
            (
                "COMMUNIQUER", "✉", "#F5F3FF", "#7C3AED",
                [
                    ("📝  Script Form@Prof", self.generate_call_script),
                    ("✉  E-mail Form@Prof", self.generate_email),
                ],
            ),
            (
                "SUIVRE", "↗", "#ECFDF5", "#0F8A59",
                [
                    ("➡  Prochaine action", self.recommend_action),
                    ("🔁  Plan de relance", self.generate_follow_up_plan),
                    ("🧠  Mémoire commerciale", self.open_commercial_memory),
                    ("＋  Ajouter mémoire", self.add_commercial_memory),
                ],
            ),
        ]

        for family_index, (family_name, family_icon, soft, accent, buttons) in enumerate(family_specs):
            family = QFrame()
            family.setObjectName(f"AiFamily_{family_index}")
            family.setStyleSheet(
                f"QFrame#AiFamily_{family_index}{{background:#FFFFFF;"
                "border:1px solid #E4EBF4;border-radius:12px;}"
                "QLabel{background:transparent;border:none;}"
            )
            family_layout = QVBoxLayout(family)
            family_layout.setContentsMargins(10, 9, 10, 10)
            family_layout.setSpacing(7)

            family_head = QHBoxLayout()
            family_head.setSpacing(7)
            family_badge = QLabel(family_icon)
            family_badge.setFixedSize(26, 26)
            family_badge.setAlignment(Qt.AlignCenter)
            family_badge.setStyleSheet(
                f"background:{soft};color:{accent};border:none;border-radius:8px;"
                "font-size:12px;font-weight:900;"
            )
            family_label = QLabel(family_name)
            family_label.setStyleSheet(
                f"color:{accent};font-size:10px;font-weight:900;letter-spacing:.7px;"
            )
            family_head.addWidget(family_badge)
            family_head.addWidget(family_label)
            family_head.addStretch()
            family_layout.addLayout(family_head)

            for caption, callback in buttons:
                button = QPushButton(caption)
                button.setCursor(Qt.PointingHandCursor)
                button.setMinimumHeight(38)
                button.setStyleSheet(
                    "QPushButton{background:#F9FBFD;color:#173A60;"
                    "border:1px solid #E6EDF5;border-radius:9px;"
                    "padding:0 11px;font-size:10px;font-weight:850;text-align:left;}"
                    "QPushButton:hover{background:#EEF7FF;color:#0D68BA;"
                    "border-color:#A7CEF1;}"
                    "QPushButton:pressed{background:#DFEFFD;}"
                )
                button.clicked.connect(callback)
                family_layout.addWidget(button)

            families.addWidget(family, family_index // 2, family_index % 2)

        tools_box.addLayout(families)
        console_layout.addWidget(tools_shell)

        output_card = QFrame()
        output_card.setObjectName("AiOutputCard")
        output_card.setStyleSheet(
            "QFrame#AiOutputCard{background:#FFFFFF;border:1px solid #DDE7F1;"
            "border-radius:15px;}QLabel{background:transparent;border:none;}"
        )
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(12, 11, 12, 12)
        output_layout.setSpacing(8)

        output_head = QHBoxLayout()
        output_identity = QHBoxLayout()
        output_orb = QLabel("✦")
        output_orb.setFixedSize(32, 32)
        output_orb.setAlignment(Qt.AlignCenter)
        output_orb.setStyleSheet(
            "background:#0B2A52;color:white;border-radius:10px;font-size:15px;font-weight:900;"
        )
        output_titles = QVBoxLayout()
        output_titles.setSpacing(0)
        output_title = QLabel("RÉPONSE DU COPILOTE")
        output_title.setStyleSheet(
            "color:#0B2A52;font-size:11px;font-weight:900;letter-spacing:.7px;"
        )
        output_subtitle = QLabel("Analyse structurée • recommandation • argumentaire")
        output_subtitle.setStyleSheet("color:#7A8A9E;font-size:10px;font-weight:650;")
        output_titles.addWidget(output_title)
        output_titles.addWidget(output_subtitle)
        output_identity.addWidget(output_orb)
        output_identity.addLayout(output_titles)

        copy_button = QPushButton("⧉  Copier")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setMinimumHeight(30)
        copy_button.setStyleSheet(
            "QPushButton{background:#F8FBFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:9px;padding:0 12px;font-size:10px;font-weight:850;}"
            "QPushButton:hover{background:#EAF4FF;color:#1473C9;border-color:#AFCFF0;}"
        )
        copy_button.clicked.connect(self.copy_output)
        output_head.addLayout(output_identity)
        output_head.addStretch()
        output_head.addWidget(copy_button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Choisissez une action : le copilote affichera ici son analyse, "
            "son script ou sa recommandation…"
        )
        self.output.setMinimumHeight(210)
        self.output.setStyleSheet(
            "QTextEdit{background:#F8FBFE;color:#172033;border:1px solid #E4EBF4;"
            "border-radius:12px;padding:15px;font-size:12px;"
            "selection-background-color:#DDEEFF;}"
        )
        output_layout.addLayout(output_head)
        output_layout.addWidget(self.output, 1)
        console_layout.addWidget(output_card, 1)
        right_layout.addWidget(console_body, 1)

        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([500, 650])
        main_layout.addWidget(split, 1)

        # Intelligence feed
        bottom = QSplitter(Qt.Horizontal)
        bottom.setChildrenCollapsible(False)
        bottom.setHandleWidth(12)
        bottom.setStyleSheet("QSplitter::handle{background:transparent;}")

        insight_card = QFrame()
        insight_card.setObjectName("AiInsightCard")
        insight_card.setStyleSheet(
            "QFrame#AiInsightCard{background:#FFFFFF;border:1px solid #E4EBF4;"
            "border-radius:18px;}QLabel{background:transparent;border:none;}"
        )
        insight_layout = QVBoxLayout(insight_card)
        insight_layout.setContentsMargins(17, 15, 17, 15)
        insight_layout.setSpacing(7)
        insight_overline = QLabel("PRIORITÉS OPÉRATIONNELLES")
        insight_overline.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:.9px;"
        )
        insight_title = QLabel("Priorités recommandées")
        insight_title.setStyleSheet("color:#0B1220;font-size:16px;font-weight:900;")
        self.insights_list = QListWidget()
        self.insights_list.setAlternatingRowColors(False)
        self.insights_list.setStyleSheet(
            "QListWidget{border:none;background:#F8FBFE;color:#172033;outline:none;"
            "border-radius:12px;}"
            "QListWidget::item{background:#FFFFFF;margin:4px 5px;padding:10px 10px;"
            "border:1px solid #E6EDF5;border-radius:9px;}"
            "QListWidget::item:selected{background:#EAF4FF;color:#0B2A52;"
            "border-color:#BFDDFC;}"
        )
        insight_layout.addWidget(insight_overline)
        insight_layout.addWidget(insight_title)
        insight_layout.addWidget(self.insights_list)

        history_card = QFrame()
        history_card.setObjectName("AiHistoryCard")
        history_card.setStyleSheet(
            "QFrame#AiHistoryCard{background:#FFFFFF;border:1px solid #E4EBF4;"
            "border-radius:18px;}QLabel{background:transparent;border:none;}"
        )
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(17, 15, 17, 15)
        history_layout.setSpacing(7)
        history_overline = QLabel("ACTIVITY STREAM")
        history_overline.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:.9px;"
        )
        history_title = QLabel("Activité du copilote")
        history_title.setStyleSheet("color:#0B1220;font-size:16px;font-weight:900;")
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self._open_history)
        self.history_list.setStyleSheet(
            "QListWidget{border:none;background:#F8FBFE;color:#172033;outline:none;"
            "border-radius:12px;}"
            "QListWidget::item{background:#FFFFFF;margin:4px 5px;padding:10px 10px;"
            "border:1px solid #E6EDF5;border-radius:9px;}"
            "QListWidget::item:selected{background:#EAF4FF;color:#0B2A52;"
            "border-color:#BFDDFC;}"
        )
        history_layout.addWidget(history_overline)
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_list)

        bottom.addWidget(insight_card)
        bottom.addWidget(history_card)
        bottom.setSizes([560, 560])
        bottom.setMinimumHeight(235)
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

        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une mémoire commerciale")
        dialog.setModal(True)
        dialog.resize(650, 520)
        dialog.setMinimumSize(610, 480)
        dialog.setStyleSheet(
            "QDialog{background:#F5F8FC;}"
            "QLabel{background:transparent;border:none;}"
        )

        root = QVBoxLayout(dialog)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header premium
        header = QFrame()
        header.setObjectName("MemoryHeader")
        header.setStyleSheet(
            "QFrame#MemoryHeader{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #081F3D, stop:1 #123F70);"
            "border:none;}"
            "QLabel{background:transparent;border:none;}"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 18)
        header_layout.setSpacing(5)

        overline = QLabel("MÉMOIRE COMMERCIALE  •  COPILOTE")
        overline.setStyleSheet(
            "color:#79C7FF;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        title = QLabel("Ajouter une information à retenir")
        title.setStyleSheet(
            "color:#FFFFFF;font-size:23px;font-weight:900;"
        )
        subtitle = QLabel(
            "Cette information enrichira le contexte du prospect et pourra être "
            "réutilisée lors des prochains échanges."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "color:#C5D7E9;font-size:10px;"
        )

        header_layout.addWidget(overline)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QWidget()
        body.setStyleSheet("background:#F5F8FC;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(22, 18, 22, 20)
        body_layout.setSpacing(13)

        # Prospect context
        prospect_card = QFrame()
        prospect_card.setObjectName("MemoryProspectCard")
        prospect_card.setStyleSheet(
            "QFrame#MemoryProspectCard{background:#EEF6FF;"
            "border:1px solid #CFE3F7;border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        prospect_layout = QHBoxLayout(prospect_card)
        prospect_layout.setContentsMargins(14, 11, 14, 11)

        prospect_icon = QLabel("🧠")
        prospect_icon.setFixedSize(34, 34)
        prospect_icon.setAlignment(Qt.AlignCenter)
        prospect_icon.setStyleSheet(
            "background:#FFFFFF;border:1px solid #D5E7F8;border-radius:10px;"
            "font-size:15px;"
        )

        prospect_text = QVBoxLayout()
        prospect_text.setSpacing(1)
        prospect_caption = QLabel("PROSPECT SÉLECTIONNÉ")
        prospect_caption.setStyleSheet(
            "color:#338CE4;font-size:8px;font-weight:900;letter-spacing:.7px;"
        )
        prospect_name = QLabel(self.selected_title.text().strip() or "Prospect sélectionné")
        prospect_name.setStyleSheet(
            "color:#0B2A52;font-size:12px;font-weight:900;"
        )
        prospect_text.addWidget(prospect_caption)
        prospect_text.addWidget(prospect_name)

        prospect_layout.addWidget(prospect_icon)
        prospect_layout.addSpacing(7)
        prospect_layout.addLayout(prospect_text, 1)
        body_layout.addWidget(prospect_card)

        # Form card
        form_card = QFrame()
        form_card.setObjectName("MemoryFormCard")
        form_card.setStyleSheet(
            "QFrame#MemoryFormCard{background:#FFFFFF;"
            "border:1px solid #E4EBF4;border-radius:16px;}"
            "QLabel{background:transparent;border:none;}"
        )
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 15, 16, 16)
        form_layout.setSpacing(9)

        category_label = QLabel("Catégorie de mémoire")
        category_label.setStyleSheet(
            "color:#334155;font-size:10px;font-weight:850;"
        )

        category_combo = QComboBox()
        category_combo.addItems(list(self.service.MEMORY_TYPES))
        category_combo.setMinimumHeight(42)
        category_combo.setStyleSheet(
            "QComboBox{background:#FFFFFF;color:#172033;"
            "border:1px solid #D7E2EE;border-radius:10px;"
            "padding:0 12px;font-size:11px;font-weight:800;}"
            "QComboBox:focus{border:2px solid #338CE4;}"
            "QComboBox::drop-down{border:none;border-left:1px solid #E6EDF5;"
            "width:34px;background:#F8FBFF;}"
            "QComboBox QAbstractItemView{background:#FFFFFF;color:#172033;"
            "border:1px solid #D7E2EE;selection-background-color:#EAF4FF;"
            "selection-color:#0B2A52;padding:4px;}"
        )

        content_label = QLabel("Information à mémoriser")
        content_label.setStyleSheet(
            "color:#334155;font-size:10px;font-weight:850;"
        )

        content_edit = QTextEdit()
        content_edit.setPlaceholderText(
            "Exemple : le dirigeant souhaite gagner du temps sur le suivi des chantiers "
            "et veut revoir la proposition après la rentrée…"
        )
        content_edit.setMinimumHeight(150)
        content_edit.setStyleSheet(
            "QTextEdit{background:#FBFDFF;color:#172033;"
            "border:1px solid #D7E2EE;border-radius:12px;"
            "padding:12px;font-size:11px;}"
            "QTextEdit:focus{border:2px solid #338CE4;}"
        )

        helper = QLabel(
            "Conseil : saisissez une information courte, factuelle et utile pour le prochain échange."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(
            "color:#7A8A9E;font-size:9px;"
        )

        form_layout.addWidget(category_label)
        form_layout.addWidget(category_combo)
        form_layout.addSpacing(2)
        form_layout.addWidget(content_label)
        form_layout.addWidget(content_edit)
        form_layout.addWidget(helper)
        body_layout.addWidget(form_card, 1)

        # Buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        cancel_button = QPushButton("Annuler")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumSize(105, 42)
        cancel_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;"
            "border:1px solid #CBD8E6;border-radius:11px;"
            "padding:0 18px;font-size:10px;font-weight:850;}"
            "QPushButton:hover{background:#F4F9FF;color:#247BD0;"
            "border-color:#8DBCEB;}"
            "QPushButton:pressed{background:#EAF4FE;}"
        )

        save_button = QPushButton("＋  Ajouter à la mémoire")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumSize(190, 42)
        save_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:#FFFFFF;border:none;"
            "border-radius:11px;padding:0 20px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
            "QPushButton:pressed{background:#1E6DBA;}"
            "QPushButton:disabled{background:#DCE6F0;color:#94A3B8;}"
        )
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
