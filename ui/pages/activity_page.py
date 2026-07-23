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
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #F4F6F9; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: #F4F6F9;")
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(35, 30, 35, 36)
        self.root.setSpacing(18)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Centre d'activité")
        title.setStyleSheet("font-size: 30px; font-weight: 900; color: #111827;")
        self.subtitle = QLabel("Historique des actions du projet actif")
        self.subtitle.setStyleSheet("font-size: 15px; color: #6B7280;")
        header_text.addWidget(title)
        header_text.addWidget(self.subtitle)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Toutes les activités", "all")
        for key, label in CATEGORY_LABELS.items():
            self.filter_combo.addItem(label, key)
        self.filter_combo.setFixedHeight(40)
        self.filter_combo.currentIndexChanged.connect(self._render_events)

        refresh = QPushButton("↻ Rafraîchir")
        refresh.setFixedHeight(40)
        refresh.setStyleSheet(f"""
            QPushButton {{ background: {PRIMARY_COLOR}; color: white; border: none;
                border-radius: 9px; padding: 0 16px; font-weight: 700; }}
            QPushButton:hover {{ background: #256DB4; }}
        """)
        refresh.clicked.connect(self.rafraichir)

        header.addLayout(header_text, 1)
        header.addWidget(self.filter_combo)
        header.addWidget(refresh)
        self.root.addLayout(header)

        self.timeline = QVBoxLayout()
        self.timeline.setSpacing(12)
        self.root.addLayout(self.timeline)
        self.root.addStretch()

        scroll.setWidget(content)
        page.addWidget(scroll)

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.events = []
            self.subtitle.setText("Aucun projet actif")
        else:
            project = ApplicationState.get_project()
            self.subtitle.setText(f"Historique du projet : {project.name}")
            self.events = ActivityService.list_events(limit=500)
        self._render_events()

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
                    if child.widget() is not None:
                        child.widget().deleteLater()

    def _render_events(self):
        self._clear_timeline()
        selected = self.filter_combo.currentData() or "all"
        events = [e for e in self.events if selected == "all" or e.get("category") == selected]

        if not ApplicationState.has_project():
            self.timeline.addWidget(self._empty_card("Ouvrez ou créez un projet pour consulter son activité."))
            return
        if not events:
            self.timeline.addWidget(self._empty_card("Aucune activité enregistrée pour ce filtre."))
            return

        grouped = defaultdict(list)
        for event in events:
            try:
                dt = datetime.fromisoformat(event.get("timestamp", ""))
                day_key = dt.date()
            except ValueError:
                day_key = datetime.now().date()
            grouped[day_key].append(event)

        today = datetime.now().date()
        for day, day_events in grouped.items():
            if day == today:
                day_text = "Aujourd'hui"
            else:
                day_text = day.strftime("%d/%m/%Y")
            heading = QLabel(day_text)
            heading.setStyleSheet("font-size: 17px; font-weight: 900; color: #111827; margin-top: 8px;")
            self.timeline.addWidget(heading)
            for event in day_events:
                self.timeline.addWidget(self._event_card(event))

    def _empty_card(self, text):
        card = QFrame()
        card.setStyleSheet("QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 16px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 28, 24, 28)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 14px; color: #6B7280;")
        layout.addWidget(label)
        return card

    def _event_card(self, event):
        level = event.get("level", "info")
        bg, fg, icon = LEVEL_STYLE.get(level, LEVEL_STYLE["info"])
        category = CATEGORY_LABELS.get(event.get("category", "general"), "Général")

        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        card.setStyleSheet("QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 15px; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 18, 14)
        layout.setSpacing(14)

        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(38, 38)
        badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 19px; font-size: 18px; font-weight: 900;"
        )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        title = QLabel(event.get("title", "Activité"))
        title.setStyleSheet("font-size: 15px; font-weight: 900; color: #111827;")
        message = QLabel(event.get("message", ""))
        message.setWordWrap(True)
        message.setStyleSheet("font-size: 13px; color: #4B5563;")
        text_layout.addWidget(title)
        if event.get("message"):
            text_layout.addWidget(message)

        try:
            dt = datetime.fromisoformat(event.get("timestamp", ""))
            time_text = dt.strftime("%H:%M:%S")
        except ValueError:
            time_text = "—"
        meta = QLabel(f"{category}  •  {time_text}")
        meta.setStyleSheet("font-size: 12px; color: #9CA3AF; font-weight: 700;")

        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(text_layout, 1)
        layout.addWidget(meta, 0, Qt.AlignTop)
        return card
