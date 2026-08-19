from __future__ import annotations

from datetime import date, datetime, time, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.session import SessionState
from core.constants import PRIMARY_COLOR
from core.theme import BACKGROUND_COLOR, FONT, TEXT_PRIMARY, TEXT_SECONDARY, primary_button_style
from services.agenda_service import AgendaService
from services.cloud_crm_mapping import priority_to_ui
from services.cloud_runtime import CloudRuntime
from services.activity_service import ActivityService as ProspectActivityService
from services.system import ActivityService
from ui.components import SectionCard, StatCard
from ui.components.notifications import NotificationManager
from ui.dialogs.prospect_dialog import ProspectDialog


class AgendaPage(QWidget):
    """Agenda commercial relié aux prochaines actions des prospects."""

    HEADERS = ["Heure", "Entreprise", "Action", "Priorité", "Score", "Commercial", "Contact"]

    def __init__(self):
        super().__init__()
        self.service = AgendaService()
        self.selected_actions: list[dict] = []
        self._cloud_actions: list[dict] = []
        self._owner_names: dict[str, str] = {}
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
        scroll.setStyleSheet("""
            QScrollArea {
                background:#F5F8FC;
                border:none;
            }
            QScrollBar:vertical {
                background:transparent;
                width:10px;
                margin:4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background:#CBD5E1;
                min-height:40px;
                border-radius:5px;
            }
            QScrollBar::handle:vertical:hover {
                background:#94A3B8;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background:#F5F8FC;")
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 34)
        root.setSpacing(18)

        # -------------------------
        # Header premium
        # -------------------------
        header_card = QFrame()
        header_card.setObjectName("AgendaHeader")
        header_card.setStyleSheet("""
            QFrame#AgendaHeader {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:0.72 #F7FBFF,
                    stop:1 #EAF4FF
                );
                border:1px solid #E4EBF4;
                border-radius:20px;
            }
        """)

        header = QHBoxLayout(header_card)
        header.setContentsMargins(22, 18, 20, 18)
        header.setSpacing(14)

        texts = QVBoxLayout()
        texts.setSpacing(3)

        eyebrow = QLabel("AGENDA  •  PILOTAGE COMMERCIAL")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        title = QLabel("Agenda commercial")
        title.setStyleSheet(
            "font-size:28px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        self.subtitle = QLabel("Planifiez et suivez les prochaines actions de vos prospects.")
        self.subtitle.setStyleSheet(
            "font-size:12px; color:#6B7A90; background:transparent; border:none;"
        )

        texts.addWidget(eyebrow)
        texts.addWidget(title)
        texts.addWidget(self.subtitle)

        self.today_button = QPushButton("Aujourd'hui")
        self.today_button.setFixedHeight(40)
        self.today_button.setStyleSheet(self._agenda_secondary_button_style())
        self.today_button.clicked.connect(self.go_today)

        refresh_button = QPushButton("Rafraîchir")
        refresh_button.setFixedHeight(40)
        refresh_button.setStyleSheet(self._agenda_primary_button_style())
        refresh_button.clicked.connect(self.rafraichir)

        header.addLayout(texts, 1)
        header.addWidget(self.today_button)
        header.addWidget(refresh_button)

        root.addWidget(header_card)

        # -------------------------
        # Indicateurs
        # -------------------------
        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(12)
        summary_grid.setVerticalSpacing(12)

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

        # -------------------------
        # Espace principal
        # -------------------------
        workspace = QGridLayout()
        workspace.setHorizontalSpacing(18)
        workspace.setColumnStretch(0, 2)
        workspace.setColumnStretch(1, 5)

        # Calendrier
        calendar_card = QFrame()
        calendar_card.setObjectName("AgendaCalendarCard")
        calendar_card.setStyleSheet("""
            QFrame#AgendaCalendarCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        calendar_layout = QVBoxLayout(calendar_card)
        calendar_layout.setContentsMargins(16, 16, 16, 16)
        calendar_layout.setSpacing(10)

        calendar_eyebrow = QLabel("PLANIFICATION")
        calendar_eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        calendar_title = QLabel("Calendrier")
        calendar_title.setStyleSheet(
            "font-size:18px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        calendar_layout.addWidget(calendar_eyebrow)
        calendar_layout.addWidget(calendar_title)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self.load_selected_day)
        self.calendar.currentPageChanged.connect(self.refresh_calendar_marks)
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background:#FFFFFF;
                border:none;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background:#0B2A52;
                border-radius:12px;
            }
            QCalendarWidget QToolButton {
                color:#FFFFFF;
                background:transparent;
                border:none;
                font-size:12px;
                font-weight:900;
                padding:7px 8px;
                margin:1px;
            }
            QCalendarWidget QToolButton:hover {
                background:#123966;
                border-radius:8px;
            }
            QCalendarWidget QSpinBox {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:7px;
                padding:4px;
                font-weight:800;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background:#FFFFFF;
                color:#334155;
                selection-background-color:#338CE4;
                selection-color:#FFFFFF;
                outline:0;
                font-size:11px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color:#CBD5E1;
            }
        """)

        calendar_layout.addWidget(self.calendar, 1)
        workspace.addWidget(calendar_card, 0, 0)

        # Actions
        actions_card = QFrame()
        actions_card.setObjectName("AgendaActionsCard")
        actions_card.setStyleSheet("""
            QFrame#AgendaActionsCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setContentsMargins(16, 16, 16, 14)
        actions_layout.setSpacing(12)

        action_header = QHBoxLayout()
        action_texts = QVBoxLayout()
        action_texts.setSpacing(2)

        action_eyebrow = QLabel("JOURNÉE")
        action_eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        self.day_title = QLabel("Actions du jour")
        self.day_title.setStyleSheet(
            "font-size:18px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )
        self.day_count = QLabel("0 action")
        self.day_count.setAlignment(Qt.AlignCenter)
        self.day_count.setMinimumWidth(80)
        self.day_count.setFixedHeight(28)
        self.day_count.setStyleSheet(
            "font-size:10px; font-weight:900; color:#075985; "
            "background:#EFF8FF; border:1px solid #BAE6FD; "
            "border-radius:10px; padding:0 10px;"
        )

        action_texts.addWidget(action_eyebrow)
        action_texts.addWidget(self.day_title)
        action_header.addLayout(action_texts, 1)
        action_header.addWidget(self.day_count, 0, Qt.AlignTop)

        actions_layout.addLayout(action_header)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(380)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.doubleClicked.connect(self.open_selected_prospect)
        self.table.setStyleSheet("""
            QTableWidget {
                background:#FFFFFF;
                color:#1F2937;
                border:1px solid #E4EBF4;
                border-radius:14px;
                gridline-color:transparent;
                font-size:11px;
                outline:0;
            }
            QTableWidget::item {
                padding:9px 8px;
                border:none;
                border-bottom:1px solid #EEF2F6;
            }
            QTableWidget::item:selected {
                background:#EAF4FF;
                color:#0B1220;
            }
            QHeaderView {
                background:#0B2A52;
                border:none;
            }
            QHeaderView::section {
                background:#0B2A52;
                color:#FFFFFF;
                border:none;
                border-right:1px solid rgba(255,255,255,0.08);
                padding:10px 8px;
                font-size:10px;
                font-weight:900;
            }
            QScrollBar:vertical {
                background:transparent;
                width:9px;
                margin:3px 1px 3px 1px;
            }
            QScrollBar::handle:vertical {
                background:#CBD5E1;
                min-height:32px;
                border-radius:4px;
            }
            QScrollBar::horizontal {
                background:transparent;
                height:9px;
            }
            QScrollBar::handle:horizontal {
                background:#CBD5E1;
                min-width:40px;
                border-radius:4px;
            }
        """)
        actions_layout.addWidget(self.table)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        open_button = QPushButton("Ouvrir la fiche")
        complete_button = QPushButton("Marquer comme réalisée")
        tomorrow_button = QPushButton("Reporter à demain")

        open_button.setFixedHeight(40)
        complete_button.setFixedHeight(40)
        tomorrow_button.setFixedHeight(40)

        open_button.setStyleSheet(self._agenda_secondary_button_style())
        complete_button.setStyleSheet(self._agenda_primary_button_style())
        tomorrow_button.setStyleSheet(self._agenda_secondary_button_style())

        open_button.clicked.connect(self.open_selected_prospect)
        complete_button.clicked.connect(self.complete_selected_action)
        tomorrow_button.clicked.connect(self.reschedule_selected_tomorrow)

        buttons.addWidget(open_button)
        buttons.addWidget(complete_button)
        buttons.addWidget(tomorrow_button)
        buttons.addStretch()
        actions_layout.addLayout(buttons)

        workspace.addWidget(actions_card, 0, 1)

        root.addLayout(workspace)
        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    @staticmethod
    def _agenda_primary_button_style():
        return """
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 16px;
                font-size:11px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:pressed { background:#1D66B2; }
        """

    @staticmethod
    def _agenda_secondary_button_style():
        return """
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 14px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """

    def _project(self):
        return (
            ApplicationState.get_project()
            if ApplicationState.has_project()
            else None
        )

    def _is_cloud(self) -> bool:
        """
        L'agenda utilise le Cloud lorsqu'un projet Cloud est actif.

        Pour un commercial connecté sans projet local matérialisé, la session
        Cloud reste la source de données de référence.
        """

        project = self._project()

        if project is not None:
            try:
                return DataSourceResolver().resolve(project).is_cloud
            except Exception:
                return False

        return CloudRuntime.is_active()

    @staticmethod
    def _qdate_to_date(value: QDate) -> date:
        return date(
            value.year(),
            value.month(),
            value.day(),
        )

    @staticmethod
    def _parse_cloud_datetime(value) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()

            if not text:
                return None

            try:
                parsed = datetime.fromisoformat(
                    text.replace("Z", "+00:00")
                )
            except ValueError:
                return None

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(
                tzinfo=None
            )

        return parsed

    def _load_owner_names(self) -> None:
        self._owner_names = {}

        try:
            payload = (
                CloudRuntime.api()
                .get_prospect_filter_options()
            )
        except Exception:
            return

        for owner in payload.get("owners", []):
            owner_id = str(
                owner.get("id") or ""
            ).strip()

            if not owner_id:
                continue

            label = (
                str(
                    owner.get("display_name")
                    or ""
                ).strip()
                or str(owner.get("email") or "").strip()
                or owner_id
            )
            self._owner_names[owner_id] = label

    def _load_cloud_actions(self) -> None:
        """
        Charge tous les prospects visibles par pages de 500 et conserve
        uniquement ceux ayant une prochaine action datée.
        """

        self._load_owner_names()

        api = CloudRuntime.api()
        offset = 0
        limit = 500
        total = 1
        prospects: list[dict] = []

        while offset < total:
            page = api.list_prospects(
                limit=limit,
                offset=offset,
                sort_by="next_action_at",
                sort_direction="asc",
            )
            prospects.extend(page.items)
            total = int(page.total)
            offset += len(page.items)

            if not page.items:
                break

        actions: list[dict] = []

        for prospect in prospects:
            action = str(
                prospect.get("next_action")
                or ""
            ).strip()

            if not action or action.lower() == "aucune":
                continue

            scheduled_at = self._parse_cloud_datetime(
                prospect.get("next_action_at")
            )

            if scheduled_at is None:
                continue

            owner_id = str(
                prospect.get("owner_user_id")
                or ""
            ).strip()

            actions.append(
                {
                    "id": str(prospect.get("id")),
                    "entreprise": (
                        prospect.get("company_name")
                        or "Sans nom"
                    ),
                    "prochaine_action": action,
                    "priorite": priority_to_ui(
                        prospect.get("priority")
                        or "normal"
                    ),
                    "score_prospect": 0,
                    "score_grade": "★☆☆☆☆",
                    "commercial_assigne": (
                        self._owner_names.get(
                            owner_id,
                            owner_id or "Non assigné",
                        )
                    ),
                    "telephone": (
                        prospect.get("phone")
                        or prospect.get("mobile")
                        or ""
                    ),
                    "email": prospect.get("email") or "",
                    "date_action": scheduled_at.date(),
                    "scheduled_at": scheduled_at,
                }
            )

        self._cloud_actions = actions

    def _cloud_summary(self) -> dict[str, int]:
        today = date.today()
        seven_days = today + timedelta(days=7)
        dates = [
            item["date_action"]
            for item in self._cloud_actions
        ]

        return {
            "today": sum(
                1 for value in dates
                if value == today
            ),
            "overdue": sum(
                1 for value in dates
                if value < today
            ),
            "upcoming": sum(
                1 for value in dates
                if today < value <= seven_days
            ),
            "total": len(dates),
        }

    def go_today(self):
        self.calendar.setSelectedDate(
            QDate.currentDate()
        )
        self.calendar.showToday()
        self.load_selected_day()

    def rafraichir(self):
        if self._is_cloud():
            try:
                self._load_cloud_actions()

                user = SessionState.user()
                organization_name = str(
                    getattr(
                        user,
                        "organization_name",
                        "",
                    )
                    or "Form@Prospect Cloud"
                )

                self.subtitle.setText(
                    f"Espace Cloud : {organization_name}"
                )

                summary = self._cloud_summary()

                for key, card in (
                    self.summary_cards.items()
                ):
                    card.set_value(
                        summary.get(key, 0)
                    )

                self.refresh_calendar_marks()
                self.load_selected_day()

            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Agenda Cloud",
                    (
                        "Impossible de charger "
                        f"l'agenda Cloud :\n{exc}"
                    ),
                )

            return

        project = self._project()

        if project is None:
            self.subtitle.setText(
                "Aucun projet actif. Ouvrez un "
                "projet depuis le Dashboard."
            )

            for card in self.summary_cards.values():
                card.set_value("0")

            self.table.setRowCount(0)
            self.day_count.setText("0 action")
            return

        self.subtitle.setText(
            f"Projet actif : {project.name}"
        )
        summary = self.service.get_summary(
            project.database
        )

        for key, card in self.summary_cards.items():
            card.set_value(
                summary.get(key, 0)
            )

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
        if self._is_cloud():
            counts: dict[date, int] = {}

            for item in self._cloud_actions:
                action_date = item["date_action"]

                if (
                    action_date.year == year
                    and action_date.month == month
                ):
                    counts[action_date] = (
                        counts.get(action_date, 0) + 1
                    )

        else:
            if project is None:
                return

            counts = self.service.get_month_counts(
                project.database,
                year,
                month,
            )

        for action_date, count in counts.items():
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#EAF4FF"))
            fmt.setForeground(QColor("#075985"))
            fmt.setFontWeight(700)
            fmt.setToolTip(f"{count} action(s) planifiée(s)")
            self.calendar.setDateTextFormat(
                QDate(action_date.year, action_date.month, action_date.day), fmt
            )

    def load_selected_day(self):
        project = self._project()
        selected = self._qdate_to_date(self.calendar.selectedDate())
        self.day_title.setText(f"Actions du {selected.strftime('%d/%m/%Y')}")
        if self._is_cloud():
            self.selected_actions = [
                item
                for item in self._cloud_actions
                if item["date_action"] == selected
            ]
        else:
            self.selected_actions = (
                []
                if project is None
                else self.service.list_for_day(
                    project.database,
                    selected,
                )
            )

        # L'heure fait partie de la prochaine action :
        # l'ordre d'affichage est donc chronologique dans la journée.
        self.selected_actions.sort(
            key=lambda item: item.get("scheduled_at")
            or datetime.combine(
                item.get("date_action") or selected,
                time.min,
            )
        )

        self.day_count.setText(
            f"{len(self.selected_actions)} action(s)"
        )
        self.table.setRowCount(len(self.selected_actions))

        for row, item in enumerate(self.selected_actions):
            contact_parts = [
                part
                for part in (
                    item.get("telephone"),
                    item.get("email"),
                )
                if part
            ]

            scheduled_at = item.get("scheduled_at")
            heure = (
                scheduled_at.strftime("%H:%M")
                if isinstance(scheduled_at, datetime)
                else "—"
            )

            values = [
                heure,
                item.get("entreprise") or "—",
                item.get("prochaine_action") or "—",
                item.get("priorite") or "—",
                f"{item.get('score_grade') or '★☆☆☆☆'} {int(item.get('score_prospect') or 0)}/100",
                item.get("commercial_assigne") or "Non assigné",
                " • ".join(contact_parts) or "Aucun contact",
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.UserRole, item["id"])

                if column == 0:
                    cell.setTextAlignment(Qt.AlignCenter)
                    cell.setForeground(QColor("#075985"))

                if column == 1:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)

                self.table.setItem(row, column, cell)

            self.table.setRowHeight(row, 42)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 72)

    def _selected_item(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.selected_actions):
            NotificationManager.info("Agenda", "Sélectionnez d'abord une action.")
            return None
        return self.selected_actions[row]

    def open_selected_prospect(self, *_args):
        item = self._selected_item()

        if item is None:
            return

        if self._is_cloud():
            dialog = ProspectDialog(
                None,
                item["id"],
            )
        else:
            project = self._project()

            if project is None:
                return

            dialog = ProspectDialog(
                project.database,
                int(item["id"]),
            )

        dialog.exec()
        self.rafraichir()

    def complete_selected_action(self):
        project = self._project()
        item = self._selected_item()

        if item is None:
            return

        if not self._is_cloud() and project is None:
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
        if self._is_cloud():
            CloudRuntime.api().update_prospect(
                str(item["id"]),
                {
                    "next_action": "",
                    "next_action_at": None,
                },
            )
            NotificationManager.success(
                "Action réalisée",
                "La prochaine action a été clôturée.",
            )
            self.rafraichir()
            return

        if self.service.complete_action(
            project.database,
            int(item["id"]),
        ):
            ProspectActivityService().add_activity(
                project.database,
                int(item["id"]),
                "Agenda",
                (
                    "Action commerciale marquée "
                    "comme réalisée"
                ),
            )
            ActivityService.record(
                "Action commerciale réalisée",
                str(
                    item.get("entreprise")
                    or "Prospect"
                ),
                category="agenda",
                level="success",
                metadata={
                    "prospect_id": int(item["id"])
                },
            )
            NotificationManager.success(
                "Action réalisée",
                "La prochaine action a été clôturée.",
            )
            self.rafraichir()

    def reschedule_selected_tomorrow(self):
        project = self._project()
        item = self._selected_item()

        if item is None:
            return

        if not self._is_cloud() and project is None:
            return

        tomorrow = date.today() + timedelta(days=1)

        if self._is_cloud():
            local_timezone = (
                datetime.now().astimezone().tzinfo
            )
            scheduled_at = datetime.combine(
                tomorrow,
                time(hour=9),
                tzinfo=local_timezone,
            )

            CloudRuntime.api().update_prospect(
                str(item["id"]),
                {
                    "next_action_at": (
                        scheduled_at.isoformat()
                    ),
                },
            )
            NotificationManager.info(
                "Action reportée",
                "L'action a été déplacée à demain.",
            )
            self.calendar.setSelectedDate(
                QDate(
                    tomorrow.year,
                    tomorrow.month,
                    tomorrow.day,
                )
            )
            self.rafraichir()
            return
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

