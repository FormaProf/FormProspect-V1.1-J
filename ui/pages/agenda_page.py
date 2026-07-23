from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.constants import PRIMARY_COLOR
from core.theme import BACKGROUND_COLOR, FONT, TEXT_PRIMARY, TEXT_SECONDARY, primary_button_style
from services.agenda_service import AgendaService
from services.activity_service import ActivityService as ProspectActivityService
from services.system import ActivityService
from ui.components import SectionCard, StatCard
from ui.components.notifications import NotificationManager
from ui.dialogs.prospect_dialog import ProspectDialog


class AgendaPage(QWidget):
    """Agenda commercial relié aux prochaines actions des prospects."""

    HEADERS = ["Entreprise", "Action", "Priorité", "Score", "Commercial", "Contact"]

    def __init__(self):
        super().__init__()
        self.service = AgendaService()
        self.selected_actions: list[dict] = []
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; font-family: '{FONT}';")
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(35, 28, 35, 36)
        root.setSpacing(18)

        header = QHBoxLayout()
        texts = QVBoxLayout()
        title = QLabel("Agenda commercial")
        title.setStyleSheet(f"font-size: 30px; font-weight: 900; color: {TEXT_PRIMARY};")
        self.subtitle = QLabel("Planifiez et suivez les prochaines actions de vos prospects.")
        self.subtitle.setStyleSheet(f"font-size: 15px; color: {TEXT_SECONDARY};")
        texts.addWidget(title)
        texts.addWidget(self.subtitle)
        self.today_button = QPushButton("Aujourd'hui")
        self.today_button.setFixedHeight(42)
        self.today_button.setStyleSheet(primary_button_style())
        self.today_button.clicked.connect(self.go_today)
        refresh_button = QPushButton("🔄 Rafraîchir")
        refresh_button.setFixedHeight(42)
        refresh_button.setStyleSheet(primary_button_style())
        refresh_button.clicked.connect(self.rafraichir)
        header.addLayout(texts, 1)
        header.addWidget(self.today_button)
        header.addWidget(refresh_button)
        root.addLayout(header)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        self.summary_cards = {
            "today": StatCard("Aujourd'hui", "0", "📅"),
            "overdue": StatCard("En retard", "0", "⚠️"),
            "upcoming": StatCard("7 prochains jours", "0", "🗓️"),
            "total": StatCard("Actions planifiées", "0", "✅"),
        }
        for column, card in enumerate(self.summary_cards.values()):
            summary_grid.setColumnStretch(column, 1)
            summary_grid.addWidget(card, 0, column)
        root.addLayout(summary_grid)

        workspace = QGridLayout()
        workspace.setHorizontalSpacing(16)
        workspace.setColumnStretch(0, 2)
        workspace.setColumnStretch(1, 5)

        calendar_card = SectionCard(padding=16, spacing=12)
        calendar_title = QLabel("Calendrier")
        calendar_title.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {TEXT_PRIMARY};")
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self.load_selected_day)
        self.calendar.currentPageChanged.connect(self.refresh_calendar_marks)
        self.calendar.setStyleSheet(f"""
            QCalendarWidget QWidget {{ background: white; color: {TEXT_PRIMARY}; }}
            QCalendarWidget QToolButton {{ color: {TEXT_PRIMARY}; font-weight: 800; padding: 8px; }}
            QCalendarWidget QAbstractItemView:enabled {{ selection-background-color: {PRIMARY_COLOR}; selection-color: white; }}
        """)
        calendar_card.content_layout.addWidget(calendar_title)
        calendar_card.content_layout.addWidget(self.calendar)
        workspace.addWidget(calendar_card, 0, 0)

        actions_card = SectionCard(padding=16, spacing=12)
        action_header = QHBoxLayout()
        self.day_title = QLabel("Actions du jour")
        self.day_title.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {TEXT_PRIMARY};")
        self.day_count = QLabel("0 action")
        self.day_count.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        action_header.addWidget(self.day_title)
        action_header.addStretch()
        action_header.addWidget(self.day_count)
        actions_card.content_layout.addLayout(action_header)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(360)
        self.table.doubleClicked.connect(self.open_selected_prospect)
        self.table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #E5E7EB; border-radius: 10px; gridline-color: #E5E7EB; }
            QHeaderView::section { background: #F3F4F6; color: #374151; border: none; padding: 9px; font-weight: 800; }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background: #DBEAFE; color: #111827; }
        """)
        actions_card.content_layout.addWidget(self.table)

        buttons = QHBoxLayout()
        open_button = QPushButton("👁 Ouvrir la fiche")
        complete_button = QPushButton("✅ Marquer comme réalisée")
        tomorrow_button = QPushButton("➡ Reporter à demain")
        for button in (open_button, complete_button, tomorrow_button):
            button.setFixedHeight(42)
            button.setStyleSheet(primary_button_style())
        open_button.clicked.connect(self.open_selected_prospect)
        complete_button.clicked.connect(self.complete_selected_action)
        tomorrow_button.clicked.connect(self.reschedule_selected_tomorrow)
        buttons.addWidget(open_button)
        buttons.addWidget(complete_button)
        buttons.addWidget(tomorrow_button)
        buttons.addStretch()
        actions_card.content_layout.addLayout(buttons)
        workspace.addWidget(actions_card, 0, 1)

        root.addLayout(workspace)
        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _project(self):
        return ApplicationState.get_project() if ApplicationState.has_project() else None

    @staticmethod
    def _qdate_to_date(value: QDate) -> date:
        return date(value.year(), value.month(), value.day())

    def go_today(self):
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.showToday()
        self.load_selected_day()

    def rafraichir(self):
        project = self._project()
        if project is None:
            self.subtitle.setText("Aucun projet actif. Ouvrez un projet depuis le Dashboard.")
            for card in self.summary_cards.values():
                card.set_value("0")
            self.table.setRowCount(0)
            self.day_count.setText("0 action")
            return

        self.subtitle.setText(f"Projet actif : {project.name}")
        summary = self.service.get_summary(project.database)
        for key, card in self.summary_cards.items():
            card.set_value(summary.get(key, 0))
        self.refresh_calendar_marks()
        self.load_selected_day()

    def refresh_calendar_marks(self, *_args):
        project = self._project()
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        default_format = QTextCharFormat()
        for day in range(1, 32):
            candidate = QDate(year, month, day)
            if candidate.isValid():
                self.calendar.setDateTextFormat(candidate, default_format)
        if project is None:
            return
        counts = self.service.get_month_counts(project.database, year, month)
        for action_date, count in counts.items():
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#DBEAFE"))
            fmt.setForeground(QColor("#1D4ED8"))
            fmt.setFontWeight(700)
            fmt.setToolTip(f"{count} action(s) planifiée(s)")
            self.calendar.setDateTextFormat(
                QDate(action_date.year, action_date.month, action_date.day), fmt
            )

    def load_selected_day(self):
        project = self._project()
        selected = self._qdate_to_date(self.calendar.selectedDate())
        self.day_title.setText(f"Actions du {selected.strftime('%d/%m/%Y')}")
        self.selected_actions = [] if project is None else self.service.list_for_day(project.database, selected)
        self.day_count.setText(f"{len(self.selected_actions)} action(s)")
        self.table.setRowCount(len(self.selected_actions))
        for row, item in enumerate(self.selected_actions):
            contact_parts = [part for part in (item.get("telephone"), item.get("email")) if part]
            values = [
                item.get("entreprise") or "—",
                item.get("prochaine_action") or "—",
                item.get("priorite") or "—",
                f"{item.get('score_grade') or '★☆☆☆☆'} {int(item.get('score_prospect') or 0)}/100",
                item.get("commercial_assigne") or "Non assigné",
                " • ".join(contact_parts) or "Aucun contact",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.UserRole, int(item["id"]))
                self.table.setItem(row, column, cell)
        self.table.resizeColumnsToContents()

    def _selected_item(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.selected_actions):
            NotificationManager.info("Agenda", "Sélectionnez d'abord une action.")
            return None
        return self.selected_actions[row]

    def open_selected_prospect(self, *_args):
        project = self._project()
        item = self._selected_item()
        if project is None or item is None:
            return
        dialog = ProspectDialog(project.database, int(item["id"]))
        dialog.exec()
        self.rafraichir()

    def complete_selected_action(self):
        project = self._project()
        item = self._selected_item()
        if project is None or item is None:
            return
        answer = QMessageBox.question(
            self,
            "Action réalisée",
            f"Marquer l'action « {item.get('prochaine_action')} » pour {item.get('entreprise')} comme réalisée ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if self.service.complete_action(project.database, int(item["id"])):
            ProspectActivityService().add_activity(
                project.database, int(item["id"]), "Agenda", "Action commerciale marquée comme réalisée"
            )
            ActivityService.record(
                "Action commerciale réalisée",
                str(item.get("entreprise") or "Prospect"),
                category="agenda",
                level="success",
                metadata={"prospect_id": int(item["id"])},
            )
            NotificationManager.success("Action réalisée", "La prochaine action a été clôturée.")
            self.rafraichir()

    def reschedule_selected_tomorrow(self):
        project = self._project()
        item = self._selected_item()
        if project is None or item is None:
            return
        tomorrow = date.today().fromordinal(date.today().toordinal() + 1)
        if self.service.reschedule_action(project.database, int(item["id"]), tomorrow):
            ProspectActivityService().add_activity(
                project.database,
                int(item["id"]),
                "Agenda",
                f"Action reportée au {tomorrow.strftime('%d/%m/%Y')}",
            )
            ActivityService.record(
                "Action commerciale reportée",
                f"{item.get('entreprise')} — {tomorrow.isoformat()}",
                category="agenda",
                level="info",
                metadata={"prospect_id": int(item["id"]), "date": tomorrow.isoformat()},
            )
            NotificationManager.info("Action reportée", "L'action a été déplacée à demain.")
            self.calendar.setSelectedDate(QDate(tomorrow.year, tomorrow.month, tomorrow.day))
            self.rafraichir()
