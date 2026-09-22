from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.theme_settings import get_theme_preference
from services.system import ActivityService
from ui.activity_premium_theme import (
    activity_page_palette,
    activity_page_stylesheet,
)


LEVEL_TONE = {
    "success": ("success", "✓"),
    "warning": ("warning", "!"),
    "error": ("error", "×"),
    "info": ("info", "i"),
}

CATEGORY_LABELS = {
    "project": "Projet",
    "import": "Import",
    "enrichment": "Enrichissement",
    "backup": "Sauvegarde",
    "restore": "Restauration",
    "general": "Général",
}


class ActivityPage(QWidget):
    """Timeline des actions enregistrées dans le projet actif."""

    def __init__(self):
        super().__init__()
        self.events = []
        self.datasource_resolver = DataSourceResolver()
        self.is_cloud_workspace = False
        self._theme_mode = get_theme_preference()
        self._palette = activity_page_palette(self._theme_mode)

        self.setObjectName("ActivityPageRoot")
        self._build_ui()
        self._apply_visual_theme()
        self.rafraichir()

    def _apply_visual_theme(self) -> None:
        """Rafraîchit uniquement le rendu, sans charger de données."""
        self._theme_mode = get_theme_preference()
        self._palette = activity_page_palette(self._theme_mode)
        self.setStyleSheet(activity_page_stylesheet(self._palette))

    def showEvent(self, event):
        if get_theme_preference() != self._theme_mode:
            self._apply_visual_theme()
        super().showEvent(event)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _build_ui(self):
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("ActivityPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("ActivityViewport")
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(24, 20, 24, 28)
        self.root.setSpacing(14)

        # ------------------------------------------------------------------
        # HERO — contexte, filtre et rafraîchissement
        # ------------------------------------------------------------------
        hero = QFrame()
        hero.setObjectName("ActivityHero")
        hero.setMinimumHeight(142)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 19, 22, 19)
        hero_layout.setSpacing(18)

        orb = QFrame()
        orb.setObjectName("ActivityOrb")
        orb.setFixedSize(68, 68)
        orb_layout = QVBoxLayout(orb)
        orb_layout.setContentsMargins(0, 0, 0, 0)

        orb_glyph = QLabel("◷")
        orb_glyph.setObjectName("ActivityOrbGlyph")
        orb_glyph.setAlignment(Qt.AlignCenter)
        orb_layout.addWidget(orb_glyph)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)

        overline = QLabel("ACTIVITY COMMAND CENTER  •  TRAÇABILITÉ")
        overline.setObjectName("ActivityHeroEyebrow")

        title = QLabel("Historique")
        title.setObjectName("ActivityHeroTitle")

        self.subtitle = QLabel("Historique des actions du projet actif")
        self.subtitle.setObjectName("ActivityHeroSubtitle")
        self.subtitle.setWordWrap(True)

        hero_text.addWidget(overline)
        hero_text.addWidget(title)
        hero_text.addWidget(self.subtitle)

        hero_controls = QVBoxLayout()
        hero_controls.setSpacing(8)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addStretch()

        self.workspace_badge = QLabel("AUCUN PROJET")
        self.workspace_badge.setObjectName("ActivityWorkspaceBadge")
        self.workspace_badge.setProperty("activityState", "idle")
        self.workspace_badge.setAlignment(Qt.AlignCenter)
        self.workspace_badge.setMinimumSize(116, 30)

        self.source_note = QLabel("Journal d'activité")
        self.source_note.setObjectName("ActivitySourceNote")
        self.source_note.setAlignment(Qt.AlignCenter)
        self.source_note.setMinimumSize(142, 30)

        status_row.addWidget(self.workspace_badge)
        status_row.addWidget(self.source_note)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("ActivityFilterCombo")
        self.filter_combo.addItem("Toutes les activités", "all")
        for key, label in CATEGORY_LABELS.items():
            self.filter_combo.addItem(label, key)
        self.filter_combo.setMinimumSize(190, 38)
        self.filter_combo.currentIndexChanged.connect(self._render_events)

        refresh = QPushButton("↻  Rafraîchir")
        refresh.setObjectName("ActivityRefreshButton")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setMinimumSize(124, 38)
        refresh.clicked.connect(self.rafraichir)

        action_row.addWidget(self.filter_combo)
        action_row.addWidget(refresh)

        hero_controls.addLayout(status_row)
        hero_controls.addLayout(action_row)

        hero_layout.addWidget(orb, 0, Qt.AlignVCenter)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(hero_controls)

        self.root.addWidget(hero)

        # ------------------------------------------------------------------
        # KPI — synthèse calculée à partir des événements déjà chargés
        # ------------------------------------------------------------------
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(10)
        self.kpi_values = {}

        kpis = [
            ("today", "Aujourd'hui", "0", "Actions enregistrées", "blue", "◷"),
            ("week", "7 derniers jours", "0", "Activités récentes", "violet", "7"),
            ("commercial", "Activité commerciale", "0", "Événements métier", "amber", "↗"),
            ("system", "Système & documents", "0", "Traçabilité technique", "green", "✓"),
        ]

        for key, label, value, caption, tone, glyph in kpis:
            card = QFrame()
            card.setProperty("activityMetricCard", True)
            card.setProperty("activityTone", tone)
            card.setMinimumHeight(94)

            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 11, 14, 10)
            layout.setSpacing(4)

            top = QHBoxLayout()
            top.setSpacing(8)

            badge = QLabel(glyph)
            badge.setProperty("activityMetricIcon", True)
            badge.setProperty("activityTone", tone)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignCenter)

            label_widget = QLabel(label)
            label_widget.setProperty("activityMetricName", True)

            top.addWidget(badge)
            top.addWidget(label_widget)
            top.addStretch()

            value_widget = QLabel(value)
            value_widget.setProperty("activityMetricValue", True)

            caption_widget = QLabel(caption)
            caption_widget.setProperty("activityMetricCaption", True)

            accent_line = QFrame()
            accent_line.setProperty("activityMetricAccent", True)
            accent_line.setProperty("activityTone", tone)
            accent_line.setFixedHeight(3)

            layout.addLayout(top)
            layout.addWidget(value_widget)
            layout.addWidget(caption_widget)
            layout.addWidget(accent_line)

            self.kpi_values[key] = value_widget
            self.kpi_row.addWidget(card)

        self.root.addLayout(self.kpi_row)

        # ------------------------------------------------------------------
        # JOURNAL — timeline groupée par jour
        # ------------------------------------------------------------------
        feed_card = QFrame()
        feed_card.setObjectName("ActivityFeed")
        feed_layout = QVBoxLayout(feed_card)
        feed_layout.setContentsMargins(18, 16, 18, 18)
        feed_layout.setSpacing(11)

        feed_top = QHBoxLayout()
        feed_top.setSpacing(12)

        feed_titles = QVBoxLayout()
        feed_titles.setSpacing(2)

        feed_overline = QLabel("JOURNAL D'ACTIVITÉ")
        feed_overline.setProperty("activityOverline", True)

        feed_title = QLabel("Dernières opérations")
        feed_title.setObjectName("ActivityFeedTitle")

        feed_sub = QLabel(
            "Suivez la chronologie des actions enregistrées dans Form@Prospect."
        )
        feed_sub.setProperty("activitySectionSubtitle", True)
        feed_sub.setWordWrap(True)

        feed_titles.addWidget(feed_overline)
        feed_titles.addWidget(feed_title)
        feed_titles.addWidget(feed_sub)

        self.events_count_badge = QLabel("0 activité")
        self.events_count_badge.setObjectName("ActivityCountBadge")
        self.events_count_badge.setAlignment(Qt.AlignCenter)
        self.events_count_badge.setMinimumSize(94, 28)

        feed_top.addLayout(feed_titles, 1)
        feed_top.addWidget(self.events_count_badge, 0, Qt.AlignTop)
        feed_layout.addLayout(feed_top)

        separator = QFrame()
        separator.setObjectName("ActivityFeedSeparator")
        separator.setFixedHeight(1)
        feed_layout.addWidget(separator)

        self.timeline = QVBoxLayout()
        self.timeline.setSpacing(9)
        feed_layout.addLayout(self.timeline)

        self.root.addWidget(feed_card)
        self.root.addStretch()

        scroll.setWidget(content)
        page.addWidget(scroll)

    def _set_workspace_state(self, text: str, state: str, note: str) -> None:
        self.workspace_badge.setText(text)
        self.workspace_badge.setProperty("activityState", state)
        self.source_note.setText(note)
        self._repolish(self.workspace_badge)

    def rafraichir(self):
        self.events = []
        self.is_cloud_workspace = False

        if not ApplicationState.has_project():
            self.subtitle.setText("Aucun projet actif")
            self._set_workspace_state(
                "AUCUN PROJET",
                "idle",
                "Sélectionnez un projet",
            )
            self._render_events()
            return

        context = self.datasource_resolver.resolve()
        active_project = context.project

        if context.is_cloud:
            self.is_cloud_workspace = True

            project_name = (
                getattr(active_project, "name", None)
                or getattr(active_project, "title", None)
                or "Projet Cloud"
            )

            self.subtitle.setText(
                f"Historique du projet Cloud : {project_name}"
            )
            self._set_workspace_state(
                "CLOUD",
                "cloud",
                "Flux distant à venir",
            )

            # ActivityService utilise actuellement le journal local du projet.
            # Aucun accès SQLite ne doit être tenté pour un workspace Cloud.
            self.events = []
            self._update_kpis()
            self._render_events()
            return

        project = active_project or ApplicationState.get_project()

        if project is None:
            self.subtitle.setText("Aucun projet local actif")
            self._set_workspace_state(
                "LOCAL",
                "local",
                "Projet local indisponible",
            )
            self._render_events()
            return

        self.subtitle.setText(
            f"Historique du projet : {project.name}"
        )
        self._set_workspace_state(
            "LOCAL",
            "local",
            "Journal du projet",
        )
        self.events = ActivityService.list_events(
            project=project,
            limit=500,
        )
        self._update_kpis()
        self._render_events()

    def _update_kpis(self):
        today = datetime.now().date()
        today_count = 0
        week_count = 0
        commercial_count = 0
        system_count = 0

        commercial_categories = {"general", "enrichment", "import"}
        system_categories = {"project", "backup", "restore"}

        for event in self.events:
            try:
                timestamp = event.get("timestamp", "")
                dt = datetime.fromisoformat(timestamp)
                age_days = (today - dt.date()).days
                if dt.date() == today:
                    today_count += 1
                if 0 <= age_days <= 6:
                    week_count += 1
            except (TypeError, ValueError):
                pass

            category = str(event.get("category") or "general")
            if category in commercial_categories:
                commercial_count += 1
            if category in system_categories:
                system_count += 1

        if hasattr(self, "kpi_values"):
            self.kpi_values["today"].setText(str(today_count))
            self.kpi_values["week"].setText(str(week_count))
            self.kpi_values["commercial"].setText(str(commercial_count))
            self.kpi_values["system"].setText(str(system_count))

    def _clear_timeline(self):
        while self.timeline.count():
            item = self.timeline.takeAt(0)

            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

            layout = item.layout()
            if layout is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    child_widget = child.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def _render_events(self):
        self._clear_timeline()

        selected = self.filter_combo.currentData() or "all"
        events = [
            event
            for event in self.events
            if selected == "all"
            or event.get("category") == selected
        ]

        if hasattr(self, "events_count_badge"):
            count = len(events)
            self.events_count_badge.setText(
                f"{count} activité" if count <= 1 else f"{count} activités"
            )

        if not ApplicationState.has_project():
            self.timeline.addWidget(
                self._empty_card(
                    "◷",
                    "Aucun projet actif",
                    "Ouvrez ou créez un projet pour consulter son historique d'activité.",
                )
            )
            return

        if self.is_cloud_workspace:
            self.timeline.addWidget(
                self._empty_card(
                    "☁",
                    "Historique Cloud en préparation",
                    "La traçabilité d'activité Cloud sera disponible dans une prochaine mise à jour. "
                    "Cette page est déjà prête à recevoir le flux d'événements distant.",
                )
            )
            return

        if not events:
            self.timeline.addWidget(
                self._empty_card(
                    "✓",
                    "Aucune activité pour ce filtre",
                    "Aucune opération ne correspond actuellement au filtre sélectionné.",
                )
            )
            return

        grouped = defaultdict(list)

        for event in events:
            try:
                timestamp = event.get("timestamp", "")
                dt = datetime.fromisoformat(timestamp)
                day_key = dt.date()
            except (TypeError, ValueError):
                day_key = datetime.now().date()

            grouped[day_key].append(event)

        today = datetime.now().date()

        for day, day_events in grouped.items():
            if day == today:
                day_text = "Aujourd'hui"
            else:
                day_text = day.strftime("%d/%m/%Y")

            self.timeline.addWidget(
                self._day_header(day_text, len(day_events))
            )

            for event in day_events:
                self.timeline.addWidget(self._event_card(event))

    def _day_header(self, day_text: str, count: int) -> QFrame:
        row = QFrame()
        row.setProperty("activityDayHeader", True)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 2, 8, 2)
        row_layout.setSpacing(8)

        dot = QLabel("•")
        dot.setProperty("activityDayDot", True)
        dot.setAlignment(Qt.AlignCenter)
        dot.setFixedWidth(14)

        heading = QLabel(day_text)
        heading.setProperty("activityDayTitle", True)

        day_count = QLabel(
            f"{count} événement" if count <= 1 else f"{count} événements"
        )
        day_count.setProperty("activityDayCount", True)

        row_layout.addWidget(dot)
        row_layout.addWidget(heading)
        row_layout.addStretch()
        row_layout.addWidget(day_count)
        return row

    def _empty_card(self, icon, title, text):
        card = QFrame()
        card.setObjectName("ActivityEmptyCard")
        card.setMinimumHeight(174)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignCenter)

        badge = QLabel(icon)
        badge.setObjectName("ActivityEmptyBadge")
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("ActivityEmptyTitle")
        title_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(text)
        text_label.setObjectName("ActivityEmptyText")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setMaximumWidth(620)

        layout.addWidget(badge, 0, Qt.AlignHCenter)
        layout.addWidget(title_label)
        layout.addWidget(text_label)
        return card

    def _event_card(self, event):
        level = str(event.get("level") or "info")
        tone, icon = LEVEL_TONE.get(level, LEVEL_TONE["info"])
        category = CATEGORY_LABELS.get(
            event.get("category", "general"),
            "Général",
        )

        card = QFrame()
        card.setObjectName("ActivityEventCard")
        card.setProperty("activityTone", tone)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(11)

        rail = QFrame()
        rail.setProperty("activityEventRail", True)
        rail.setProperty("activityTone", tone)
        rail.setFixedWidth(3)

        badge = QLabel(icon)
        badge.setProperty("activityLevelBadge", True)
        badge.setProperty("activityTone", tone)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(34, 34)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        title = QLabel(event.get("title", "Activité"))
        title.setProperty("activityEventTitle", True)

        message = QLabel(event.get("message", ""))
        message.setProperty("activityEventMessage", True)
        message.setWordWrap(True)

        text_layout.addWidget(title)
        if event.get("message"):
            text_layout.addWidget(message)

        try:
            timestamp = event.get("timestamp", "")
            dt = datetime.fromisoformat(timestamp)
            time_text = dt.strftime("%H:%M")
        except (TypeError, ValueError):
            time_text = "—"

        meta_box = QVBoxLayout()
        meta_box.setSpacing(4)

        category_badge = QLabel(category)
        category_badge.setProperty("activityCategoryBadge", True)
        category_badge.setAlignment(Qt.AlignCenter)
        category_badge.setMinimumHeight(24)

        time_label = QLabel(time_text)
        time_label.setProperty("activityTimeLabel", True)
        time_label.setAlignment(Qt.AlignCenter)

        meta_box.addWidget(category_badge)
        meta_box.addWidget(time_label)

        layout.addWidget(rail)
        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(text_layout, 1)
        layout.addLayout(meta_box)

        return card
