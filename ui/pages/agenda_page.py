from __future__ import annotations

from datetime import date, datetime, time, timedelta
from time import monotonic
import threading

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette, QTextCharFormat
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
from core.theme_settings import get_theme_preference
from services.agenda_service import AgendaService
from services.cloud_crm_mapping import priority_to_ui
from services.cloud_runtime import CloudRuntime
from services.activity_service import ActivityService as ProspectActivityService
from services.system import ActivityService
from ui.agenda_premium_theme import (
    agenda_calendar_stylesheet,
    agenda_page_stylesheet,
    agenda_palette,
    agenda_table_stylesheet,
)
from ui.components.notifications import NotificationManager
from ui.dialogs.prospect_dialog import ProspectDialog


class AgendaMetricCard(QFrame):
    """Compact agenda KPI card; structure stays identical in every theme."""

    def __init__(self, title: str, value: str = "0", icon: str = "", tone: str = "primary", parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaMetricCard")
        self.setProperty("tone", tone)
        self.setMinimumHeight(88)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(11)

        icon_label = QLabel(icon)
        icon_label.setObjectName("AgendaMetricIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(38, 38)

        texts = QVBoxLayout()
        texts.setSpacing(1)

        title_label = QLabel(title)
        title_label.setObjectName("AgendaMetricTitle")

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("AgendaMetricValue")

        texts.addWidget(title_label)
        texts.addWidget(self.value_label)

        root.addWidget(icon_label)
        root.addLayout(texts, 1)

    def set_value(self, value):
        self.value_label.setText(str(value))


class AgendaPage(QWidget):
    """Agenda commercial relié aux prochaines actions des prospects."""

    cloud_refresh_ready = Signal()
    cloud_refresh_failed = Signal(str)

    HEADERS = ["Heure", "Entreprise", "Action", "Priorité", "Score", "Commercial", "Contact"]

    def __init__(self):
        super().__init__()
        self.service = AgendaService()
        self.selected_actions: list[dict] = []
        self._cloud_actions: list[dict] = []
        self._owner_names: dict[str, str] = {}
        self._calendar_counts: dict[date, int] = {}
        self._loaded_once = False
        self._last_refresh_monotonic = 0.0
        self._cache_ttl_seconds = 300.0
        self._cloud_refresh_running = False
        self._cloud_refresh_thread = None

        self._palette = agenda_palette(get_theme_preference())
        self._build_ui()
        self._apply_visual_theme()

        self.cloud_refresh_ready.connect(self._on_cloud_refresh_ready)
        self.cloud_refresh_failed.connect(self._on_cloud_refresh_failed)

    def _build_ui(self):
        self.setObjectName("AgendaPageRoot")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("AgendaScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setObjectName("AgendaContent")
        root = QVBoxLayout(self.content)
        root.setContentsMargins(26, 22, 26, 30)
        root.setSpacing(14)

        # --------------------------------------------------------------
        # Header command center
        # --------------------------------------------------------------
        self.header_card = QFrame()
        self.header_card.setObjectName("AgendaHeader")
        header = QHBoxLayout(self.header_card)
        header.setContentsMargins(22, 17, 18, 17)
        header.setSpacing(14)

        texts = QVBoxLayout()
        texts.setSpacing(2)

        eyebrow = QLabel("AGENDA  •  PILOTAGE COMMERCIAL")
        eyebrow.setObjectName("AgendaEyebrow")

        title = QLabel("Agenda commercial")
        title.setObjectName("AgendaTitle")

        self.subtitle = QLabel(
            "Planifiez et exécutez vos prochaines actions sans perdre le rythme."
        )
        self.subtitle.setObjectName("AgendaSubtitle")

        texts.addWidget(eyebrow)
        texts.addWidget(title)
        texts.addWidget(self.subtitle)

        self.today_button = QPushButton("Aujourd'hui")
        self.today_button.setObjectName("AgendaSecondaryButton")
        self.today_button.setFixedHeight(40)
        self.today_button.clicked.connect(self.go_today)

        self.refresh_button = QPushButton("↻  Rafraîchir")
        self.refresh_button.setObjectName("AgendaPrimaryButton")
        self.refresh_button.setFixedHeight(40)
        self.refresh_button.clicked.connect(self.rafraichir)

        header.addLayout(texts, 1)
        header.addWidget(self.today_button)
        header.addWidget(self.refresh_button)
        root.addWidget(self.header_card)

        # --------------------------------------------------------------
        # KPI compacts
        # --------------------------------------------------------------
        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(10)
        summary_grid.setVerticalSpacing(10)

        self.summary_cards = {
            "today": AgendaMetricCard("Aujourd'hui", "0", "◷", "primary"),
            "overdue": AgendaMetricCard("En retard", "0", "!", "danger"),
            "upcoming": AgendaMetricCard("7 prochains jours", "0", "↗", "violet"),
            "total": AgendaMetricCard("Actions planifiées", "0", "✓", "success"),
        }

        for column, card in enumerate(self.summary_cards.values()):
            summary_grid.setColumnStretch(column, 1)
            summary_grid.addWidget(card, 0, column)

        root.addLayout(summary_grid)

        # --------------------------------------------------------------
        # Workspace : calendrier + exécution du jour
        # --------------------------------------------------------------
        workspace = QGridLayout()
        workspace.setHorizontalSpacing(14)
        workspace.setVerticalSpacing(14)
        workspace.setColumnStretch(0, 5)
        workspace.setColumnStretch(1, 8)

        self.calendar_card = QFrame()
        self.calendar_card.setObjectName("AgendaPanel")
        calendar_layout = QVBoxLayout(self.calendar_card)
        calendar_layout.setContentsMargins(17, 16, 17, 15)
        calendar_layout.setSpacing(9)

        calendar_head = QHBoxLayout()
        calendar_head.setSpacing(8)
        calendar_texts = QVBoxLayout()
        calendar_texts.setSpacing(1)

        calendar_eyebrow = QLabel("PLANIFICATION")
        calendar_eyebrow.setObjectName("AgendaSectionEyebrow")
        calendar_title = QLabel("Calendrier")
        calendar_title.setObjectName("AgendaSectionTitle")
        calendar_hint = QLabel("Repérez instantanément les jours avec une action.")
        calendar_hint.setObjectName("AgendaSectionHint")

        calendar_texts.addWidget(calendar_eyebrow)
        calendar_texts.addWidget(calendar_title)
        calendar_texts.addWidget(calendar_hint)
        calendar_head.addLayout(calendar_texts, 1)
        calendar_layout.addLayout(calendar_head)

        self.calendar = QCalendarWidget()
        self.calendar.setObjectName("AgendaCalendar")
        self.calendar.setGridVisible(False)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self.load_selected_day)
        self.calendar.currentPageChanged.connect(self.refresh_calendar_marks)
        calendar_layout.addWidget(self.calendar, 1)

        legend = QHBoxLayout()
        legend.setSpacing(12)
        legend.addWidget(self._legend_item("●", "Aujourd'hui", "primary"))
        legend.addWidget(self._legend_item("●", "Planifié", "planned"))
        legend.addWidget(self._legend_item("●", "En retard", "danger"))
        legend.addStretch()
        calendar_layout.addLayout(legend)

        workspace.addWidget(self.calendar_card, 0, 0)

        self.actions_card = QFrame()
        self.actions_card.setObjectName("AgendaPanel")
        actions_layout = QVBoxLayout(self.actions_card)
        actions_layout.setContentsMargins(17, 16, 17, 14)
        actions_layout.setSpacing(10)

        action_header = QHBoxLayout()
        action_texts = QVBoxLayout()
        action_texts.setSpacing(1)

        action_eyebrow = QLabel("EXÉCUTION DU JOUR")
        action_eyebrow.setObjectName("AgendaSectionEyebrow")
        self.day_title = QLabel("Actions du jour")
        self.day_title.setObjectName("AgendaSectionTitle")
        action_hint = QLabel("Priorisez, ouvrez la fiche et clôturez l'action en un clic.")
        action_hint.setObjectName("AgendaSectionHint")

        action_texts.addWidget(action_eyebrow)
        action_texts.addWidget(self.day_title)
        action_texts.addWidget(action_hint)

        self.day_count = QLabel("0 action")
        self.day_count.setObjectName("AgendaCountBadge")
        self.day_count.setAlignment(Qt.AlignCenter)
        self.day_count.setMinimumWidth(78)
        self.day_count.setFixedHeight(28)

        action_header.addLayout(action_texts, 1)
        action_header.addWidget(self.day_count, 0, Qt.AlignTop)
        actions_layout.addLayout(action_header)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setObjectName("AgendaTable")
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(330)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.doubleClicked.connect(self.open_selected_prospect)
        self.table.setVisible(False)
        actions_layout.addWidget(self.table)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("AgendaEmptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 30, 24, 30)
        empty_layout.setSpacing(5)

        empty_icon = QLabel("✓")
        empty_icon.setObjectName("AgendaEmptyIcon")
        empty_icon.setAlignment(Qt.AlignCenter)

        empty_title = QLabel("Aucune action sur cette journée")
        empty_title.setObjectName("AgendaEmptyTitle")
        empty_title.setAlignment(Qt.AlignCenter)

        empty_hint = QLabel(
            "Sélectionnez une autre date dans le calendrier ou planifiez "
            "une prochaine action depuis une fiche prospect."
        )
        empty_hint.setObjectName("AgendaEmptyHint")
        empty_hint.setWordWrap(True)
        empty_hint.setAlignment(Qt.AlignCenter)

        empty_layout.addStretch()
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)
        empty_layout.addStretch()
        self.empty_state.setMinimumHeight(215)
        self.empty_state.setVisible(True)
        actions_layout.addWidget(self.empty_state)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.open_button = QPushButton("Ouvrir la fiche")
        self.open_button.setObjectName("AgendaSecondaryButton")

        self.complete_button = QPushButton("✓  Marquer comme réalisée")
        self.complete_button.setObjectName("AgendaPrimaryButton")

        self.tomorrow_button = QPushButton("↗  Reporter à demain")
        self.tomorrow_button.setObjectName("AgendaSecondaryButton")

        for button in (
            self.open_button,
            self.complete_button,
            self.tomorrow_button,
        ):
            button.setFixedHeight(40)

        self.open_button.clicked.connect(self.open_selected_prospect)
        self.complete_button.clicked.connect(self.complete_selected_action)
        self.tomorrow_button.clicked.connect(self.reschedule_selected_tomorrow)

        buttons.addWidget(self.open_button)
        buttons.addWidget(self.complete_button)
        buttons.addWidget(self.tomorrow_button)
        buttons.addStretch()
        actions_layout.addLayout(buttons)

        workspace.addWidget(self.actions_card, 0, 1)
        root.addLayout(workspace)

        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

    def _legend_item(self, marker: str, text: str, tone: str) -> QLabel:
        label = QLabel(f"{marker}  {text}")
        label.setObjectName("AgendaLegend")
        label.setProperty("tone", tone)
        return label

    def _apply_visual_theme(self):
        """Apply palette only; never rebuild widgets or trigger Cloud loading."""
        self._palette = agenda_palette(get_theme_preference())
        palette = self._palette

        self.setStyleSheet(agenda_page_stylesheet(palette))
        self.calendar.setStyleSheet(agenda_calendar_stylesheet(palette))
        self.table.setStyleSheet(agenda_table_stylesheet(palette))
        self._apply_calendar_palette(palette)

        if hasattr(self, "calendar"):
            self._render_calendar_marks()

    def _apply_calendar_palette(self, palette: dict[str, str]) -> None:
        # Keep every internal calendar surface aligned with the active theme.
        calendar_palette = self.calendar.palette()

        for role, color in (
            (QPalette.Window, palette["card"]),
            (QPalette.WindowText, palette["text_soft"]),
            (QPalette.Base, palette["card"]),
            (QPalette.AlternateBase, palette["card"]),
            (QPalette.Text, palette["text_soft"]),
            (QPalette.Button, palette["card"]),
            (QPalette.ButtonText, palette["text_soft"]),
            (QPalette.Highlight, palette["primary"]),
            (QPalette.HighlightedText, "#FFFFFF"),
        ):
            calendar_palette.setColor(role, QColor(color))

        self.calendar.setPalette(calendar_palette)

        header_format = QTextCharFormat()
        header_format.setBackground(QColor(palette["calendar_header_bg"]))
        header_format.setForeground(QColor(palette["calendar_header_text"]))
        header_format.setFontWeight(QFont.DemiBold)
        self.calendar.setHeaderTextFormat(header_format)

        weekday_format = QTextCharFormat()
        weekday_format.setForeground(QColor(palette["text_soft"]))

        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor(palette["calendar_weekend"]))

        for day in (
            Qt.DayOfWeek.Monday,
            Qt.DayOfWeek.Tuesday,
            Qt.DayOfWeek.Wednesday,
            Qt.DayOfWeek.Thursday,
            Qt.DayOfWeek.Friday,
        ):
            self.calendar.setWeekdayTextFormat(day, weekday_format)

        for day in (
            Qt.DayOfWeek.Saturday,
            Qt.DayOfWeek.Sunday,
        ):
            self.calendar.setWeekdayTextFormat(day, weekend_format)

    def _priority_brushes(self, value: str) -> tuple[QColor, QColor]:
        text = str(value or "").lower()
        palette = self._palette

        if "urgent" in text or "haute" in text or "élev" in text:
            return QColor(palette["danger_soft"]), QColor(palette["danger"])
        if "basse" in text or "faible" in text:
            return QColor(palette["success_soft"]), QColor(palette["success"])
        return QColor(palette["warning_soft"]), QColor(palette["warning"])

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

    def _load_owner_names(self, *, force: bool = False) -> None:
        if self._owner_names and not force:
            return

        try:
            payload = (
                CloudRuntime.api()
                .get_prospect_filter_options()
            )
        except Exception:
            return

        owner_names: dict[str, str] = {}
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
            owner_names[owner_id] = label

        self._owner_names = owner_names

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

    def _cache_is_fresh(self) -> bool:
        if not self._loaded_once:
            return False
        return (
            monotonic() - self._last_refresh_monotonic
            < self._cache_ttl_seconds
        )

    def _mark_refresh_complete(self) -> None:
        self._loaded_once = True
        self._last_refresh_monotonic = monotonic()

    def ensure_loaded(self, *, force: bool = False) -> None:
        """Open instantly and refresh only when the cached agenda is stale."""
        if not force and self._cache_is_fresh():
            self.refresh_calendar_marks()
            self.load_selected_day()
            return
        self.rafraichir(force=force)

    def _start_cloud_refresh(self) -> None:
        if self._cloud_refresh_running:
            return

        self._cloud_refresh_running = True
        self.subtitle.setText("Synchronisation de l'agenda Cloud…")

        worker = threading.Thread(
            target=self._cloud_refresh_worker,
            name="FormProspectAgendaCloudRefresh",
            daemon=True,
        )
        self._cloud_refresh_thread = worker
        worker.start()

    def _cloud_refresh_worker(self) -> None:
        try:
            self._load_cloud_actions()
        except Exception as exc:
            self.cloud_refresh_failed.emit(str(exc))
            return
        self.cloud_refresh_ready.emit()

    def _on_cloud_refresh_ready(self) -> None:
        self._cloud_refresh_running = False

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
        for key, card in self.summary_cards.items():
            card.set_value(summary.get(key, 0))

        self.refresh_calendar_marks()
        self.load_selected_day()
        self._mark_refresh_complete()

    def _on_cloud_refresh_failed(self, message: str) -> None:
        self._cloud_refresh_running = False
        self.subtitle.setText("Synchronisation Cloud impossible")
        QMessageBox.critical(
            self,
            "Agenda Cloud",
            "Impossible de charger l'agenda Cloud :\n"
            f"{message}",
        )

    def go_today(self):
        self.calendar.setSelectedDate(
            QDate.currentDate()
        )
        self.calendar.showToday()
        self.load_selected_day()

    def rafraichir(self, *_args, force: bool = True):
        # Normal navigation does not hit the network while the cache is fresh.
        if not force and self._cache_is_fresh():
            self.refresh_calendar_marks()
            self.load_selected_day()
            return

        if self._is_cloud():
            # owners + paginated prospects are network calls. They run outside
            # the Qt UI thread so opening Agenda remains immediate.
            self._start_cloud_refresh()
            return

        project = self._project()

        if project is None:
            self.subtitle.setText(
                "Aucun projet actif. Ouvrez un "
                "projet depuis le Dashboard."
            )

            for card in self.summary_cards.values():
                card.set_value("0")

            self.selected_actions = []
            self.table.setRowCount(0)
            self.table.setVisible(False)
            self.empty_state.setVisible(True)
            self.day_count.setText("0 action")
            for button in (
                self.open_button,
                self.complete_button,
                self.tomorrow_button,
            ):
                button.setEnabled(False)
            self._mark_refresh_complete()
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
        self._mark_refresh_complete()

    def refresh_calendar_marks(self, *_args):
        project = self._project()
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()

        if self._is_cloud():
            counts: dict[date, int] = {}

            for item in self._cloud_actions:
                action_date = item["date_action"]
                if action_date.year == year and action_date.month == month:
                    counts[action_date] = counts.get(action_date, 0) + 1
        else:
            if project is None:
                counts = {}
            else:
                counts = self.service.get_month_counts(
                    project.database,
                    year,
                    month,
                )

        self._calendar_counts = counts
        self._render_calendar_marks()

    def _render_calendar_marks(self) -> None:
        """Restyle cached calendar marks only; never fetch or query data."""
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()

        default_format = QTextCharFormat()
        for day in range(1, 32):
            candidate = QDate(year, month, day)
            if candidate.isValid():
                self.calendar.setDateTextFormat(candidate, default_format)

        palette = self._palette
        today = date.today()

        for action_date, count in self._calendar_counts.items():
            if action_date.year != year or action_date.month != month:
                continue

            fmt = QTextCharFormat()

            if action_date < today:
                background = palette["danger_soft"]
                foreground = palette["danger"]
            elif action_date == today:
                background = palette["primary"]
                foreground = "#FFFFFF"
            else:
                background = palette["primary_soft"]
                foreground = palette["primary_text"]

            fmt.setBackground(QColor(background))
            fmt.setForeground(QColor(foreground))
            fmt.setFontWeight(QFont.Bold)
            fmt.setToolTip(f"{count} action(s) planifiée(s)")
            self.calendar.setDateTextFormat(
                QDate(action_date.year, action_date.month, action_date.day),
                fmt,
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

        action_count = len(self.selected_actions)
        self.day_count.setText(
            f"{action_count} action" + ("s" if action_count != 1 else "")
        )
        self.table.setVisible(action_count > 0)
        self.empty_state.setVisible(action_count == 0)

        for button in (
            self.open_button,
            self.complete_button,
            self.tomorrow_button,
        ):
            button.setEnabled(action_count > 0)

        self.table.setRowCount(action_count)

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
                    cell.setForeground(QColor(self._palette["primary_text"]))
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)

                if column == 1:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)

                if column == 3:
                    bg, fg = self._priority_brushes(value)
                    cell.setBackground(bg)
                    cell.setForeground(fg)
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

