from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import PAGE_BG
from services.cloud_runtime import CloudRuntime


class TrainerSessionsPage(QWidget):
    """Liste sécurisée des sessions affectées au formateur connecté."""

    session_open_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self.setObjectName("TrainerSessionsPage")
        self.setStyleSheet(f"QWidget#TrainerSessionsPage{{background:{PAGE_BG};}}")
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
        title = QLabel("Mes formations")
        title.setStyleSheet("color:#0B1220;font-size:27px;font-weight:900;")
        subtitle = QLabel("Sessions auxquelles vous êtes personnellement affecté(e).")
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

        self.summary = QLabel("0 session")
        self.summary.setStyleSheet("color:#475569;font-size:11px;font-weight:800;")
        root.addWidget(self.summary)

        self.error_label = QLabel("")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FED7AA;border-radius:9px;padding:10px;font-size:10px;"
        )
        root.addWidget(self.error_label)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Formation", "Entreprise", "Début", "Fin", "Horaires", "Modalité", "Participants", "Statut"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column in range(2, 8):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E5EAF0;border-radius:10px;background:white;gridline-color:#EDF1F5;font-size:10px;}"
            "QHeaderView::section{background:#F8FAFC;color:#475569;border:none;border-bottom:1px solid #E2E8F0;"
            "padding:9px;font-size:9px;font-weight:900;}"
        )
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.open_session_button = QPushButton("Ouvrir la session")
        self.open_session_button.setEnabled(False)
        self.open_session_button.setCursor(Qt.PointingHandCursor)
        self.open_session_button.setFixedHeight(40)
        self.open_session_button.setStyleSheet(
            "QPushButton{background:#0B2A52;color:#FFFFFF;border:none;border-radius:10px;padding:0 15px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#123966;}QPushButton:disabled{color:#94A3B8;background:#E2E8F0;}"
        )
        self.open_session_button.clicked.connect(self._open_selected_session)
        actions.addWidget(self.open_session_button)

        self.open_link_button = QPushButton("🔗  Ouvrir le lien de connexion")
        self.open_link_button.setEnabled(False)
        self.open_link_button.setCursor(Qt.PointingHandCursor)
        self.open_link_button.setFixedHeight(40)
        self.open_link_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#338CE4;border:1px solid #BCD7F1;border-radius:10px;padding:0 15px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#F2F8FF;}QPushButton:disabled{color:#94A3B8;border-color:#E2E8F0;background:#F8FAFC;}"
        )
        self.open_link_button.clicked.connect(self._open_selected_link)
        actions.addWidget(self.open_link_button)
        root.addLayout(actions)

        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._open_selected_session())

    @staticmethod
    def _display_date(value) -> str:
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        if not value:
            return "—"
        raw = str(value)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            try:
                return date.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
            except ValueError:
                return raw

    def rafraichir(self) -> None:
        self.error_label.setVisible(False)
        try:
            self.rows = CloudRuntime.api().list_my_cloud_trainer_sessions()
        except Exception as exc:
            self.rows = []
            self.error_label.setText(
                "Impossible de charger vos formations. Votre compte doit être rattaché à une fiche Formateur active.\n\n"
                f"Détail : {exc}"
            )
            self.error_label.setVisible(True)

        self.rows.sort(key=lambda row: str(row.get("start_date") or ""), reverse=True)
        self.summary.setText(f"{len(self.rows)} session{'s' if len(self.rows) != 1 else ''}")
        self.table.setRowCount(len(self.rows))
        for row_index, session in enumerate(self.rows):
            values = [
                session.get("training_name") or session.get("training_reference") or "—",
                session.get("client_name") or "—",
                self._display_date(session.get("start_date")),
                self._display_date(session.get("end_date")),
                session.get("daily_schedule") or "—",
                session.get("modality") or "—",
                session.get("participant_count", 0),
                session.get("status") or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row_index)
                self.table.setItem(row_index, column, item)
        self._selection_changed()

    def _selected_session(self) -> dict | None:
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected:
            return None
        row = selected[0].row()
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def _selection_changed(self) -> None:
        session = self._selected_session()
        link = str((session or {}).get("connection_link") or "").strip()
        self.open_session_button.setEnabled(bool(session and session.get("id")))
        self.open_link_button.setEnabled(bool(link))

    def _open_selected_session(self) -> None:
        session = self._selected_session()
        session_id = str((session or {}).get("id") or "").strip()
        if session_id:
            self.session_open_requested.emit(session_id)

    def _open_selected_link(self) -> None:
        session = self._selected_session()
        link = str((session or {}).get("connection_link") or "").strip()
        if not link:
            return
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            QMessageBox.warning(self, "Lien invalide", "Le lien de connexion enregistré pour cette session n'est pas valide.")
            return
        QDesktopServices.openUrl(QUrl(link))
