from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import PAGE_BG
from services.cloud_runtime import CloudRuntime


class TrainerPlanningPage(QWidget):
    """Vue chronologique légère des sessions du formateur.

    Le véritable calendrier jour/semaine/mois sera introduit avec les futurs
    créneaux structurés. Ce lot évite volontairement d'interpréter le champ
    texte ``daily_schedule`` comme une source de vérité horaire.
    """

    session_open_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("TrainerPlanningPage")
        self.setStyleSheet(f"QWidget#TrainerPlanningPage{{background:{PAGE_BG};}}")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 32)
        root.setSpacing(16)

        hero = QFrame()
        hero.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #DCE7F3;border-radius:18px;}"
            "QLabel{background:transparent;border:none;}"
        )
        row = QHBoxLayout(hero)
        row.setContentsMargins(20, 17, 20, 17)
        titles = QVBoxLayout()
        overline = QLabel("ESPACE FORMATEUR")
        overline.setStyleSheet("color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;")
        title = QLabel("Mon planning")
        title.setStyleSheet("color:#0B1220;font-size:27px;font-weight:900;")
        subtitle = QLabel("Vue chronologique de vos sessions affectées. La vue calendrier détaillée arrivera avec les créneaux structurés.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#718096;font-size:11px;")
        titles.addWidget(overline)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        row.addLayout(titles, 1)
        refresh = QPushButton("↻  Actualiser")
        refresh.setFixedHeight(40)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;padding:0 16px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
        )
        refresh.clicked.connect(self.rafraichir)
        row.addWidget(refresh)
        root.addWidget(hero)

        self.error_label = QLabel("")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FED7AA;border-radius:9px;padding:10px;font-size:10px;"
        )
        root.addWidget(self.error_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.content = QWidget()
        self.content.setStyleSheet("background:transparent;")
        self.list_layout = QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        scroll.setWidget(self.content)
        root.addWidget(scroll, 1)

    @staticmethod
    def _parse_date(value) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        raw = str(value)
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(raw[:10])
            except ValueError:
                return None

    @classmethod
    def _display_date_range(cls, session: dict) -> str:
        start = cls._parse_date(session.get("start_date"))
        end = cls._parse_date(session.get("end_date"))
        if start and end:
            if start == end:
                return start.strftime("%d/%m/%Y")
            return f"{start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}"
        return "Date non renseignée"

    def _clear_cards(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def rafraichir(self) -> None:
        self.error_label.setVisible(False)
        try:
            sessions = CloudRuntime.api().list_my_cloud_trainer_sessions()
        except Exception as exc:
            sessions = []
            self.error_label.setText(f"Impossible de charger votre planning.\n\nDétail : {exc}")
            self.error_label.setVisible(True)

        sessions.sort(key=lambda row: self._parse_date(row.get("start_date")) or date.max)
        self._clear_cards()
        if not sessions:
            empty = QLabel("Aucune session de formation n'est actuellement affectée à votre compte.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "background:#FFFFFF;color:#64748B;border:1px solid #E2E8F0;border-radius:14px;padding:28px;font-size:11px;"
            )
            self.list_layout.addWidget(empty)
        else:
            for session in sessions:
                self.list_layout.addWidget(self._session_card(session))
        self.list_layout.addStretch(1)

    def _session_card(self, session: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#FFFFFF;border:1px solid #E2EAF3;border-radius:15px;}"
            "QLabel{background:transparent;border:none;}"
        )
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        badge = QLabel("📅")
        badge.setFixedSize(42, 42)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background:#EEF6FF;color:#338CE4;border-radius:12px;font-size:18px;")
        row.addWidget(badge)

        text = QVBoxLayout()
        text.setSpacing(3)
        training = QLabel(str(session.get("training_name") or session.get("training_reference") or "Formation"))
        training.setStyleSheet("color:#0F172A;font-size:13px;font-weight:900;")
        client = QLabel(str(session.get("client_name") or "Entreprise non renseignée"))
        client.setStyleSheet("color:#475569;font-size:10px;font-weight:700;")
        detail = QLabel(
            f"{self._display_date_range(session)}   •   {session.get('daily_schedule') or 'Horaires non renseignés'}   •   {session.get('modality') or 'Modalité non renseignée'}"
        )
        detail.setWordWrap(True)
        detail.setStyleSheet("color:#64748B;font-size:9px;")
        text.addWidget(training)
        text.addWidget(client)
        text.addWidget(detail)
        row.addLayout(text, 1)

        status = QLabel(str(session.get("status") or "—"))
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet(
            "background:#F8FAFC;color:#475569;border:1px solid #E2E8F0;border-radius:9px;padding:7px 10px;font-size:9px;font-weight:800;"
        )
        row.addWidget(status)

        session_id = str(session.get("id") or "").strip()
        open_button = QPushButton("Ouvrir")
        open_button.setCursor(Qt.PointingHandCursor)
        open_button.setFixedHeight(34)
        open_button.setEnabled(bool(session_id))
        open_button.setStyleSheet(
            "QPushButton{background:#0B2A52;color:#FFFFFF;border:none;border-radius:9px;padding:0 12px;font-size:9px;font-weight:900;}"
            "QPushButton:hover{background:#123966;}QPushButton:disabled{background:#E2E8F0;color:#94A3B8;}"
        )
        open_button.clicked.connect(
            lambda checked=False, sid=session_id: self.session_open_requested.emit(sid) if sid else None
        )
        row.addWidget(open_button)
        return card
