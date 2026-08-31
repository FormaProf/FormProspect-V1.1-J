from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import PAGE_BG, PRIMARY
from services.cloud_runtime import CloudRuntime


class TrainerDashboardPage(QWidget):
    """Tableau de bord personnel du formateur connecté.

    Cette page ne demande jamais d'identifiant formateur au client : le Backend
    résout le profil et les sessions depuis l'utilisateur authentifié via les
    routes ``/trainers/me`` et ``/trainers/me/sessions``.
    """

    session_open_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._profile: dict = {}
        self._sessions: list[dict] = []
        self.setObjectName("TrainerDashboardPage")
        self.setStyleSheet(f"QWidget#TrainerDashboardPage{{background:{PAGE_BG};}}")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 32)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("TrainerDashboardHero")
        hero.setStyleSheet(
            "QFrame#TrainerDashboardHero{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF,stop:1 #EEF6FF);border:1px solid #DCE7F3;border-radius:20px;}"
            "QLabel{background:transparent;border:none;}"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 20, 18)
        hero_layout.setSpacing(16)

        icon = QLabel("🎓")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(56, 56)
        icon.setStyleSheet(
            "background:#0B2A52;color:#FFFFFF;border-radius:17px;font-size:25px;font-weight:900;"
        )
        hero_layout.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(3)
        overline = QLabel("ESPACE FORMATEUR  •  FORM@PROSPECT")
        overline.setStyleSheet("color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;")
        self.title = QLabel("Bonjour")
        self.title.setStyleSheet("color:#0B1220;font-size:27px;font-weight:900;")
        subtitle = QLabel("Retrouvez vos sessions de formation et les informations nécessaires à leur réalisation.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#718096;font-size:11px;")
        titles.addWidget(overline)
        titles.addWidget(self.title)
        titles.addWidget(subtitle)
        hero_layout.addLayout(titles, 1)

        refresh = QPushButton("↻  Actualiser")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setFixedHeight(40)
        refresh.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 16px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
        )
        refresh.clicked.connect(self.rafraichir)
        hero_layout.addWidget(refresh)
        root.addWidget(hero)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.metric_upcoming = self._metric_card(metrics, "À venir", "Prochaines formations", "📅")
        self.metric_current = self._metric_card(metrics, "En cours", "Sessions actuellement ouvertes", "▶")
        self.metric_done = self._metric_card(metrics, "Terminées", "Historique de vos sessions", "✓")
        root.addLayout(metrics)

        card = QFrame()
        card.setObjectName("TrainerSessionsCard")
        card.setStyleSheet(
            "QFrame#TrainerSessionsCard{background:#FFFFFF;border:1px solid #E2EAF3;border-radius:16px;}"
            "QLabel{background:transparent;border:none;}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        card_layout.setSpacing(10)

        section_title = QLabel("Prochaines formations")
        section_title.setStyleSheet("color:#0F172A;font-size:16px;font-weight:900;")
        card_layout.addWidget(section_title)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FED7AA;border-radius:9px;padding:10px;font-size:10px;"
        )
        card_layout.addWidget(self.error_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Formation", "Entreprise", "Début", "Horaires", "Modalité"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E5EAF0;border-radius:10px;background:white;gridline-color:#EDF1F5;font-size:10px;}"
            "QHeaderView::section{background:#F8FAFC;color:#475569;border:none;border-bottom:1px solid #E2E8F0;"
            "padding:9px;font-size:9px;font-weight:900;}"
        )
        self.table.cellDoubleClicked.connect(self._open_selected_session)
        card_layout.addWidget(self.table, 1)
        root.addWidget(card, 1)

    @staticmethod
    def _metric_card(layout: QHBoxLayout, label: str, caption: str, icon: str) -> QLabel:
        card = QFrame()
        card.setMinimumHeight(98)
        card.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #E2EAF3;border-radius:16px;}"
            "QLabel{background:transparent;border:none;}"
        )
        body = QVBoxLayout(card)
        body.setContentsMargins(14, 12, 14, 11)
        body.setSpacing(3)
        top = QHBoxLayout()
        glyph = QLabel(icon)
        glyph.setFixedSize(28, 28)
        glyph.setAlignment(Qt.AlignCenter)
        glyph.setStyleSheet("background:#EEF6FF;color:#338CE4;border-radius:9px;font-size:12px;font-weight:900;")
        name = QLabel(label)
        name.setStyleSheet("color:#53657C;font-size:9px;font-weight:850;")
        top.addWidget(glyph)
        top.addWidget(name)
        top.addStretch()
        value = QLabel("0")
        value.setStyleSheet("color:#071A31;font-size:24px;font-weight:900;")
        sub = QLabel(caption)
        sub.setStyleSheet("color:#94A3B8;font-size:8px;")
        body.addLayout(top)
        body.addWidget(value)
        body.addWidget(sub)
        layout.addWidget(card)
        return value

    @staticmethod
    def _parse_date(value) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(str(value)[:10])
            except ValueError:
                return None

    @staticmethod
    def _display_date(value) -> str:
        parsed = TrainerDashboardPage._parse_date(value)
        return parsed.strftime("%d/%m/%Y") if parsed else "—"

    @staticmethod
    def _status_bucket(session: dict, today: date) -> str:
        start = TrainerDashboardPage._parse_date(session.get("start_date"))
        end = TrainerDashboardPage._parse_date(session.get("end_date"))
        if start and start > today:
            return "upcoming"
        if start and end and start <= today <= end:
            return "current"
        if end and end < today:
            return "done"
        status = str(session.get("status") or "").strip().lower()
        if status in {"completed", "done", "terminee", "terminée", "closed", "cloturee", "clôturée"}:
            return "done"
        return "upcoming"

    def rafraichir(self) -> None:
        self.error_label.setVisible(False)
        try:
            api = CloudRuntime.api()
            self._profile = api.get_my_cloud_trainer_profile()
            self._sessions = api.list_my_cloud_trainer_sessions()
        except Exception as exc:
            self._profile = {}
            self._sessions = []
            self.error_label.setText(
                "Impossible de charger votre espace Formateur. "
                "Vérifiez que votre compte est bien rattaché à une fiche Formateur.\n\n"
                f"Détail : {exc}"
            )
            self.error_label.setVisible(True)

        first_name = str(self._profile.get("first_name") or "").strip()
        full_name = str(self._profile.get("full_name") or "").strip()
        display = first_name or full_name or ""
        self.title.setText(f"Bonjour {display}".rstrip())

        today = date.today()
        counts = {"upcoming": 0, "current": 0, "done": 0}
        for session in self._sessions:
            counts[self._status_bucket(session, today)] += 1
        self.metric_upcoming.setText(str(counts["upcoming"]))
        self.metric_current.setText(str(counts["current"]))
        self.metric_done.setText(str(counts["done"]))

        upcoming = [
            session for session in self._sessions
            if self._status_bucket(session, today) in {"upcoming", "current"}
        ]
        upcoming.sort(key=lambda item: self._parse_date(item.get("start_date")) or date.max)
        upcoming = upcoming[:8]

        self.table.setRowCount(len(upcoming))
        for row, session in enumerate(upcoming):
            values = [
                session.get("training_name") or session.get("training_reference") or "—",
                session.get("client_name") or "—",
                self._display_date(session.get("start_date")),
                session.get("daily_schedule") or "—",
                session.get("modality") or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, str(session.get("id") or ""))
                self.table.setItem(row, column, item)

    def _open_selected_session(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        session_id = str(item.data(Qt.UserRole) or "").strip() if item else ""
        if session_id:
            self.session_open_requested.emit(session_id)
