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
from core.constants import PRIMARY_COLOR
from core.datasource_resolver import DataSourceResolver
from services.system import ActivityService


LEVEL_STYLE = {
    "success": ("#DCFCE7", "#166534", "✓"),
    "warning": ("#FEF3C7", "#92400E", "!"),
    "error": ("#FEE2E2", "#991B1B", "×"),
    "info": ("#DBEAFE", "#1D4ED8", "i"),
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
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:#F4F7FB;border:none;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#CBD5E1;min-height:40px;border-radius:5px;}"
            "QScrollBar::handle:vertical:hover{background:#94A3B8;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        content = QWidget()
        content.setStyleSheet("background:#F4F7FB;")
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(28, 24, 28, 34)
        self.root.setSpacing(16)

        # ==============================================================
        # HEADER PREMIUM
        # ==============================================================
        hero = QFrame()
        hero.setObjectName("ActivityHero")
        hero.setMinimumHeight(126)
        hero.setStyleSheet(
            "QFrame#ActivityHero{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF, stop:1 #EEF6FF);"
            "border:1px solid #DCE7F3;border-radius:22px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 20, 18)
        hero_layout.setSpacing(16)

        icon = QLabel("◷")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background:#0B2A52;color:#FFFFFF;border-radius:17px;"
            "font-size:26px;font-weight:900;"
        )

        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)

        overline = QLabel("HISTORIQUE  •  TRAÇABILITÉ COMMERCIALE")
        overline.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1.1px;"
        )
        title = QLabel("Centre d'activité")
        title.setStyleSheet(
            "color:#0B1220;font-size:28px;font-weight:900;"
        )
        self.subtitle = QLabel("Historique des actions du projet actif")
        self.subtitle.setStyleSheet(
            "color:#718096;font-size:11px;"
        )
        hero_text.addWidget(overline)
        hero_text.addWidget(title)
        hero_text.addWidget(self.subtitle)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Toutes les activités", "all")
        for key, label in CATEGORY_LABELS.items():
            self.filter_combo.addItem(label, key)
        self.filter_combo.setMinimumSize(180, 40)
        self.filter_combo.setStyleSheet(
            "QComboBox{background:#FFFFFF;color:#172033;"
            "border:1px solid #D8E3EE;border-radius:10px;"
            "padding:0 12px;font-size:10px;font-weight:800;}"
            "QComboBox:focus{border:2px solid #338CE4;}"
            "QComboBox::drop-down{border:none;border-left:1px solid #E8EEF5;"
            "width:34px;background:#F8FBFF;}"
            "QComboBox QAbstractItemView{background:#FFFFFF;color:#172033;"
            "border:1px solid #D8E3EE;selection-background-color:#EAF4FF;"
            "selection-color:#0B2A52;padding:4px;}"
        )
        self.filter_combo.currentIndexChanged.connect(self._render_events)

        refresh = QPushButton("↻  Rafraîchir")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setMinimumSize(126, 40)
        refresh.setStyleSheet(
            f"QPushButton{{background:{PRIMARY_COLOR};color:white;border:none;"
            "border-radius:10px;padding:0 16px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
            "QPushButton:pressed{background:#1F6DBA;}"
        )
        refresh.clicked.connect(self.rafraichir)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.filter_combo)
        actions.addWidget(refresh)

        hero_layout.addWidget(icon)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(actions)
        self.root.addWidget(hero)

        # ==============================================================
        # KPI
        # ==============================================================
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(12)
        self.kpi_values = {}

        kpis = [
            ("today", "Aujourd'hui", "0", "Actions enregistrées", "#338CE4", "#EEF6FF", "◷"),
            ("week", "7 derniers jours", "0", "Activités récentes", "#8B5CF6", "#F5F3FF", "7"),
            ("commercial", "Activité commerciale", "0", "Événements métier", "#F59E0B", "#FFF7ED", "↗"),
            ("system", "Système & documents", "0", "Traçabilité technique", "#10B981", "#ECFDF5", "✓"),
        ]

        for key, label, value, caption, accent, soft, glyph in kpis:
            card = QFrame()
            card.setObjectName(f"ActivityMetric_{key}")
            card.setMinimumHeight(96)
            card.setStyleSheet(
                f"QFrame#ActivityMetric_{key}{{background:#FFFFFF;"
                "border:1px solid #E2EAF3;border-radius:16px;}"
                "QLabel{background:transparent;border:none;}"
            )
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 11)
            layout.setSpacing(4)

            top = QHBoxLayout()
            badge = QLabel(glyph)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background:{soft};color:{accent};border-radius:9px;"
                "font-size:12px;font-weight:900;"
            )
            label_widget = QLabel(label)
            label_widget.setStyleSheet(
                "color:#53657C;font-size:9px;font-weight:850;"
            )
            top.addWidget(badge)
            top.addWidget(label_widget)
            top.addStretch()

            value_widget = QLabel(value)
            value_widget.setStyleSheet(
                "color:#071A31;font-size:24px;font-weight:900;"
            )
            caption_widget = QLabel(caption)
            caption_widget.setStyleSheet(
                "color:#94A3B8;font-size:8px;"
            )

            layout.addLayout(top)
            layout.addWidget(value_widget)
            layout.addWidget(caption_widget)

            self.kpi_values[key] = value_widget
            self.kpi_row.addWidget(card)

        self.root.addLayout(self.kpi_row)

        # ==============================================================
        # ACTIVITY FEED CARD
        # ==============================================================
        feed_card = QFrame()
        feed_card.setObjectName("ActivityFeed")
        feed_card.setStyleSheet(
            "QFrame#ActivityFeed{background:#FFFFFF;border:1px solid #E2EAF3;"
            "border-radius:18px;}"
            "QLabel{background:transparent;border:none;}"
        )
        feed_layout = QVBoxLayout(feed_card)
        feed_layout.setContentsMargins(18, 16, 18, 18)
        feed_layout.setSpacing(12)

        feed_top = QHBoxLayout()
        feed_titles = QVBoxLayout()
        feed_titles.setSpacing(2)

        feed_overline = QLabel("FLUX D'ACTIVITÉ")
        feed_overline.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        feed_title = QLabel("Dernières opérations")
        feed_title.setStyleSheet(
            "color:#0B1220;font-size:18px;font-weight:900;"
        )
        feed_sub = QLabel(
            "Suivez les actions enregistrées dans Form@Prospect et leur chronologie."
        )
        feed_sub.setStyleSheet(
            "color:#7A8A9E;font-size:10px;"
        )
        feed_titles.addWidget(feed_overline)
        feed_titles.addWidget(feed_title)
        feed_titles.addWidget(feed_sub)

        self.events_count_badge = QLabel("0 activité")
        self.events_count_badge.setAlignment(Qt.AlignCenter)
        self.events_count_badge.setMinimumSize(92, 28)
        self.events_count_badge.setStyleSheet(
            "background:#EEF6FF;color:#1473C9;border:1px solid #CFE4F8;"
            "border-radius:9px;padding:0 9px;font-size:9px;font-weight:900;"
        )

        feed_top.addLayout(feed_titles, 1)
        feed_top.addWidget(self.events_count_badge, 0, Qt.AlignTop)
        feed_layout.addLayout(feed_top)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background:#EEF2F7;border:none;")
        feed_layout.addWidget(separator)

        self.timeline = QVBoxLayout()
        self.timeline.setSpacing(10)
        feed_layout.addLayout(self.timeline)
        self.root.addWidget(feed_card)

        self.root.addStretch()

        scroll.setWidget(content)
        page.addWidget(scroll)

    def rafraichir(self):
        self.events = []
        self.is_cloud_workspace = False

        if not ApplicationState.has_project():
            self.subtitle.setText("Aucun projet actif")
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

            # ActivityService utilise actuellement le journal local du projet.
            # Aucun accès SQLite ne doit être tenté pour un workspace Cloud.
            self.events = []
            self._update_kpis()
            self._render_events()
            return

        project = active_project or ApplicationState.get_project()

        if project is None:
            self.subtitle.setText("Aucun projet local actif")
            self._render_events()
            return

        self.subtitle.setText(
            f"Historique du projet : {project.name}"
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

            heading_row = QHBoxLayout()
            heading = QLabel(day_text)
            heading.setStyleSheet(
                "color:#0B1220;font-size:13px;font-weight:900;"
            )
            day_count = QLabel(
                f"{len(day_events)} événement" if len(day_events) <= 1
                else f"{len(day_events)} événements"
            )
            day_count.setStyleSheet(
                "color:#94A3B8;font-size:9px;font-weight:800;"
            )
            heading_row.addWidget(heading)
            heading_row.addStretch()
            heading_row.addWidget(day_count)
            self.timeline.addLayout(heading_row)

            for event in day_events:
                self.timeline.addWidget(self._event_card(event))

    def _empty_card(self, icon, title, text):
        card = QFrame()
        card.setMinimumHeight(210)
        card.setStyleSheet(
            "QFrame{background:#FBFDFF;border:1px dashed #C9D7E6;"
            "border-radius:16px;}"
            "QLabel{background:transparent;border:none;}"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 30, 24, 30)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        badge = QLabel(icon)
        badge.setFixedSize(52, 52)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:#EEF6FF;color:#338CE4;border-radius:16px;"
            "font-size:22px;font-weight:900;"
        )

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "color:#0B1220;font-size:16px;font-weight:900;"
        )

        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setMaximumWidth(620)
        text_label.setStyleSheet(
            "color:#718096;font-size:10px;"
        )

        layout.addWidget(badge, 0, Qt.AlignHCenter)
        layout.addWidget(title_label)
        layout.addWidget(text_label)
        return card

    def _event_card(self, event):
        level = event.get("level", "info")
        bg, fg, icon = LEVEL_STYLE.get(
            level,
            LEVEL_STYLE["info"],
        )
        category = CATEGORY_LABELS.get(
            event.get("category", "general"),
            "Général",
        )

        card = QFrame()
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )
        card.setObjectName("ActivityEventCard")
        card.setStyleSheet(
            "QFrame#ActivityEventCard{background:#FFFFFF;"
            "border:1px solid #E5ECF4;border-radius:13px;}"
            "QLabel{background:transparent;border:none;}"
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(34, 34)
        badge.setStyleSheet(
            f"background:{bg};color:{fg};border-radius:11px;"
            "font-size:14px;font-weight:900;"
        )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        title = QLabel(event.get("title", "Activité"))
        title.setStyleSheet(
            "color:#172033;font-size:11px;font-weight:900;"
        )

        message = QLabel(event.get("message", ""))
        message.setWordWrap(True)
        message.setStyleSheet(
            "color:#64748B;font-size:10px;"
        )

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
        category_badge.setAlignment(Qt.AlignCenter)
        category_badge.setMinimumHeight(24)
        category_badge.setStyleSheet(
            "background:#F8FBFF;color:#476078;border:1px solid #E0E8F1;"
            "border-radius:8px;padding:0 9px;font-size:8px;font-weight:850;"
        )
        time_label = QLabel(time_text)
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet(
            "color:#94A3B8;font-size:9px;font-weight:800;"
        )
        meta_box.addWidget(category_badge)
        meta_box.addWidget(time_label)

        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(text_layout, 1)
        layout.addLayout(meta_box)

        return card

