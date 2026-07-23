from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.constants import PRIMARY_COLOR
from core.crm import PIPELINE, PIPELINE_COLORS
from core.theme import BACKGROUND_COLOR, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
from services.backup_service import BackupService
from services.dashboard_service import DashboardService
from services.project_manager import ProjectManager
from services.system import ActivityService
from ui.components.notifications import NotificationManager
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.widgets.dashboard_charts import HorizontalBarChart, QualityDonut


class DashboardPage(QWidget):
    """Dashboard 2.0 : centre de commandement de Form@Prospect."""

    def __init__(self):
        super().__init__()
        self.dashboard_service = DashboardService()
        self.project_manager = ProjectManager()
        self.backup_service = BackupService()
        self.kpi_values: dict[str, QLabel] = {}
        self.pipeline_values: dict[str, QLabel] = {}
        self.action_values: dict[str, QLabel] = {}
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: #F4F6F9; border: none; }")

        content = QWidget()
        content.setStyleSheet(f"background: {BACKGROUND_COLOR};")
        root = QVBoxLayout(content)
        root.setContentsMargins(34, 28, 34, 38)
        root.setSpacing(18)

        root.addWidget(self._build_header())

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)
        kpis = [
            ("prospects", "Prospects", "👥"),
            ("telephones", "Téléphones", "📞"),
            ("emails", "Emails", "📧"),
            ("sites", "Sites web", "🌐"),
            ("quality_score", "Qualité de la base", "⭐"),
            ("average_prospect_score", "Score commercial moyen", "🎯"),
        ]
        for column, (key, title, icon) in enumerate(kpis):
            card, value = self._metric_card(title, icon)
            self.kpi_values[key] = value
            kpi_grid.addWidget(card, 0, column)
            kpi_grid.setColumnStretch(column, 1)
        root.addLayout(kpi_grid)

        insight_grid = QGridLayout()
        insight_grid.setHorizontalSpacing(14)
        insight_grid.setVerticalSpacing(14)
        insight_grid.setColumnStretch(0, 3)
        insight_grid.setColumnStretch(1, 2)

        contact_card = self._section("Données de contact", "Volume des informations disponibles dans la base")
        self.contact_chart = HorizontalBarChart()
        contact_card.layout().addWidget(self.contact_chart)
        insight_grid.addWidget(contact_card, 0, 0)

        quality_card = self._section("Score qualité", "Moyenne téléphone, email, site et LinkedIn")
        self.quality_donut = QualityDonut()
        self.quality_details = QLabel("Aucun projet actif")
        self.quality_details.setAlignment(Qt.AlignCenter)
        self.quality_details.setWordWrap(True)
        self.quality_details.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        quality_card.layout().addWidget(self.quality_donut)
        quality_card.layout().addWidget(self.quality_details)
        insight_grid.addWidget(quality_card, 0, 1)
        root.addLayout(insight_grid)

        lower_grid = QGridLayout()
        lower_grid.setHorizontalSpacing(14)
        lower_grid.setVerticalSpacing(14)
        lower_grid.setColumnStretch(0, 1)
        lower_grid.setColumnStretch(1, 1)

        lower_grid.addWidget(self._build_enrichment_card(), 0, 0)
        lower_grid.addWidget(self._build_actions_card(), 0, 1)
        lower_grid.addWidget(self._build_pipeline_card(), 1, 0)
        lower_grid.addWidget(self._build_recent_activity_card(), 1, 1)
        lower_grid.addWidget(self._build_scoring_card(), 2, 0, 1, 2)
        root.addLayout(lower_grid)
        root.addStretch()

        scroll.setWidget(content)
        main.addWidget(scroll)

    def _build_header(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        texts = QVBoxLayout()
        self.title = QLabel("Bonjour 👋")
        self.title.setStyleSheet(f"font-size: 30px; font-weight: 900; color: {TEXT_PRIMARY};")
        self.subtitle = QLabel("Ouvrez un projet pour afficher votre centre de commandement.")
        self.subtitle.setStyleSheet(f"font-size: 14px; color: {TEXT_SECONDARY};")
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        for label, slot in (
            ("➕ Nouveau projet", self.ouvrir_nouveau_projet),
            ("📂 Ouvrir", self.ouvrir_projet_existant),
            ("💾 Sauvegarder", self.sauvegarder_projet),
            ("🔄 Rafraîchir", self.rafraichir),
        ):
            button = QPushButton(label)
            button.setFixedHeight(42)
            button.setStyleSheet(self._button_style())
            button.clicked.connect(slot)
            actions.addWidget(button)

        layout.addLayout(texts, 1)
        layout.addLayout(actions)
        return frame

    @staticmethod
    def _button_style():
        return f"""
            QPushButton {{
                background: {PRIMARY_COLOR}; color: white; border: none;
                border-radius: 10px; padding: 0 14px; font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #256DB4; }}
            QPushButton:pressed {{ background: #1D4F86; }}
        """

    @staticmethod
    def _card_style():
        return f"""
            QFrame#DashboardCard {{
                background: white; border: 1px solid {BORDER_COLOR}; border-radius: 16px;
            }}
        """

    def _section(self, title: str, subtitle: str = ""):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setStyleSheet(self._card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 17px; font-weight: 900; color: {TEXT_PRIMARY};")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
        return card

    def _metric_card(self, title: str, icon: str):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setMinimumHeight(112)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet(self._card_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        head = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {TEXT_SECONDARY}; border: none;")
        head.addWidget(icon_label)
        head.addWidget(title_label)
        head.addStretch()

        value = QLabel("0")
        value.setStyleSheet(f"font-size: 25px; font-weight: 900; color: {TEXT_PRIMARY}; border: none;")
        value.setWordWrap(True)
        layout.addLayout(head)
        layout.addWidget(value)
        return card, value

    def _build_enrichment_card(self):
        card = self._section("Enrichissement", "Progression globale du projet actif")
        self.enrichment_label = QLabel("0 / 0 prospects enrichis")
        self.enrichment_label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {TEXT_PRIMARY};")
        self.enrichment_progress = QProgressBar()
        self.enrichment_progress.setRange(0, 100)
        self.enrichment_progress.setValue(0)
        self.enrichment_progress.setFixedHeight(24)
        self.enrichment_progress.setStyleSheet(f"""
            QProgressBar {{ background: #EEF2F7; border: none; border-radius: 10px;
                text-align: center; color: {TEXT_PRIMARY}; font-weight: 800; }}
            QProgressBar::chunk {{ background: {PRIMARY_COLOR}; border-radius: 10px; }}
        """)
        self.enrichment_detail = QLabel("Aucune donnée")
        self.enrichment_detail.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        card.layout().addWidget(self.enrichment_label)
        card.layout().addWidget(self.enrichment_progress)
        card.layout().addWidget(self.enrichment_detail)
        return card

    def _build_actions_card(self):
        card = self._section("Priorités du jour", "Les actions qui demandent votre attention")
        grid = QGridLayout()
        items = [
            ("actions_today", "Actions aujourd'hui", "📅"),
            ("actions_overdue", "Actions en retard", "⚠️"),
            ("high_priority", "Priorités fortes", "🔥"),
            ("actions_next_7_days", "7 prochains jours", "🗓️"),
        ]
        for index, (key, title, icon) in enumerate(items):
            item, value = self._mini_action(title, icon)
            self.action_values[key] = value
            grid.addWidget(item, index // 2, index % 2)
        card.layout().addLayout(grid)
        return card

    def _mini_action(self, title, icon):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        label = QLabel(f"{icon}  {title}")
        label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {TEXT_SECONDARY}; border: none;")
        value = QLabel("0")
        value.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {TEXT_PRIMARY}; border: none;")
        layout.addWidget(label, 1)
        layout.addWidget(value)
        return frame, value

    def _build_pipeline_card(self):
        card = self._section("Pipeline commercial", "Répartition des prospects par étape")
        self.pipeline_grid = QGridLayout()
        self.pipeline_grid.setSpacing(8)
        for index, name in enumerate(PIPELINE):
            frame = QFrame()
            color = PIPELINE_COLORS.get(name, "#F3F4F6")
            frame.setStyleSheet(f"QFrame {{ background: {color}; border: 1px solid #E5E7EB; border-radius: 10px; }}")
            layout = QHBoxLayout(frame)
            layout.setContentsMargins(10, 8, 10, 8)
            label = QLabel(name)
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 11px; font-weight: 800; color: #111827; border: none;")
            value = QLabel("0")
            value.setStyleSheet("font-size: 16px; font-weight: 900; color: #111827; border: none;")
            layout.addWidget(label, 1)
            layout.addWidget(value)
            self.pipeline_values[name] = value
            self.pipeline_grid.addWidget(frame, index // 2, index % 2)
        card.layout().addLayout(self.pipeline_grid)
        return card

    def _build_scoring_card(self):
        card = self._section(
            "Scoring commercial",
            "Classement explicable des prospects selon la qualité et la complétude de leurs données",
        )
        self.scoring_chart = HorizontalBarChart()
        self.scoring_summary = QLabel("Cliquez sur « Calculer les scores » dans le CRM pour initialiser le classement.")
        self.scoring_summary.setWordWrap(True)
        self.scoring_summary.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        card.layout().addWidget(self.scoring_chart)
        card.layout().addWidget(self.scoring_summary)
        return card

    def _build_recent_activity_card(self):
        card = self._section("Activité récente", "Les dernières opérations du projet")
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(6)
        card.layout().addLayout(self.activity_layout)
        return card

    def _clear_activity(self):
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_activity(self, events):
        self._clear_activity()
        if not events:
            label = QLabel("Aucune activité enregistrée pour le moment.")
            label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
            self.activity_layout.addWidget(label)
            return
        level_icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        for event in events[:6]:
            timestamp = event.get("timestamp", "")
            try:
                time_text = datetime.fromisoformat(timestamp).strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                time_text = timestamp[:16].replace("T", " ")
            row = QFrame()
            row.setStyleSheet("QFrame { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px; }")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 8, 10, 8)
            icon = level_icons.get(event.get("level"), "•")
            title = QLabel(f"{icon}  {event.get('title', 'Activité')}")
            title.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {TEXT_PRIMARY}; border: none;")
            when = QLabel(time_text)
            when.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; border: none;")
            layout.addWidget(title, 1)
            layout.addWidget(when)
            self.activity_layout.addWidget(row)

    @staticmethod
    def _format_number(value):
        try:
            return f"{int(value):,}".replace(",", " ")
        except (TypeError, ValueError):
            return str(value)

    def _set_empty(self):
        self.title.setText("Bonjour 👋")
        self.subtitle.setText("Créez ou ouvrez un projet pour commencer.")
        for key, value in self.kpi_values.items():
            value.setText("0 %" if key == "quality_score" else ("0/100" if key == "average_prospect_score" else "0"))
        self.contact_chart.set_items([])
        self.quality_donut.set_value(0)
        self.quality_details.setText("Aucun projet actif")
        self.enrichment_label.setText("0 / 0 prospects enrichis")
        self.enrichment_progress.setValue(0)
        self.enrichment_progress.setFormat("0 %")
        self.enrichment_detail.setText("Aucune donnée")
        for value in self.action_values.values():
            value.setText("0")
        for value in self.pipeline_values.values():
            value.setText("0")
        self.scoring_chart.set_items([])
        self.scoring_summary.setText("Aucun projet actif")
        self._render_activity([])

    def rafraichir(self):
        if not ApplicationState.has_project():
            self._set_empty()
            return
        try:
            project = ApplicationState.get_project()
            data = self.dashboard_service.get_dashboard_data(project.database)
            self.title.setText(f"Bonjour 👋  {project.name}")
            self.subtitle.setText("Voici l'état de votre prospection et les priorités à traiter.")

            for key in ("prospects", "telephones", "emails", "sites"):
                self.kpi_values[key].setText(self._format_number(data["kpi"][key]))
            self.kpi_values["quality_score"].setText(f"{data['kpi']['quality_score']} %")
            self.kpi_values["average_prospect_score"].setText(
                f"{data['kpi']['average_prospect_score']}/100"
            )

            self.contact_chart.set_items(data["contact_distribution"])
            score = data["kpi"]["quality_score"]
            self.quality_donut.set_value(score)
            missing_phone = data["activity"]["missing_phone"]
            missing_email = data["activity"]["missing_email"]
            self.quality_details.setText(
                f"Il manque {self._format_number(missing_phone)} téléphone(s) et "
                f"{self._format_number(missing_email)} email(s)."
            )

            enrichment = data["enrichment"]
            self.enrichment_label.setText(
                f"{self._format_number(enrichment['enriched'])} / "
                f"{self._format_number(data['kpi']['prospects'])} prospects enrichis"
            )
            self.enrichment_progress.setValue(enrichment["percentage"])
            self.enrichment_progress.setFormat(f"{enrichment['percentage']} %")
            self.enrichment_detail.setText(
                f"{self._format_number(enrichment['remaining'])} restant(s) • "
                f"{self._format_number(enrichment['errors'])} erreur(s)"
            )

            for key, value in self.action_values.items():
                value.setText(self._format_number(data["activity"].get(key, 0)))
            for name, value in self.pipeline_values.items():
                value.setText(self._format_number(data["pipeline"].get(name, 0)))

            scoring_order = ["★★★★★", "★★★★☆", "★★★☆☆", "★★☆☆☆", "★☆☆☆☆", "Non calculé"]
            scoring_items = [
                (grade, data["scoring"].get(grade, 0))
                for grade in scoring_order
                if data["scoring"].get(grade, 0)
            ]
            self.scoring_chart.set_items(scoring_items)
            top_scores = data["scoring"].get("★★★★★", 0) + data["scoring"].get("★★★★☆", 0)
            self.scoring_summary.setText(
                f"{self._format_number(top_scores)} prospect(s) sont classés en priorité forte ou très forte."
            )

            self._render_activity(ActivityService.list_events(project=project, limit=6))
        except Exception as exc:
            QMessageBox.critical(self, "Erreur Dashboard", f"Impossible de charger le dashboard :\n{exc}")

    def ouvrir_nouveau_projet(self):
        dialog = NewProjectDialog()
        if dialog.exec():
            NotificationManager.success("Projet créé", "Le nouveau projet est prêt.")
            self.rafraichir()

    def ouvrir_projet_existant(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier du projet existant")
        if not folder:
            return
        try:
            project = self.project_manager.open_project(folder)
            NotificationManager.success("Projet ouvert", f"Le projet {project.name} est maintenant actif.")
            self.rafraichir()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir ce projet :\n{exc}")

    def sauvegarder_projet(self):
        if not ApplicationState.has_project():
            NotificationManager.warning("Sauvegarde", "Aucun projet actif à sauvegarder.")
            return
        project = ApplicationState.get_project()
        default_path = self.backup_service.default_backup_path(project)
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder le projet",
            str(default_path),
            "Sauvegardes Form@Prospect (*.fpbackup)",
        )
        if not output:
            return
        try:
            path = self.backup_service.create_backup(project, output)
            ActivityService.record(
                "Sauvegarde manuelle créée",
                path.name,
                category="backup",
                level="success",
                project=project,
            )
            NotificationManager.success("Sauvegarde terminée", path.name)
            self.rafraichir()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de sauvegarde", str(exc))
