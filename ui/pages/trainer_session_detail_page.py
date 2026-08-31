from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import PAGE_BG
from services.cloud_runtime import CloudRuntime


class TrainerSessionDetailPage(QWidget):
    """Détail sécurisé d'une session affectée au formateur connecté."""

    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.session_id = ""
        self.session: dict = {}
        self.learners: list[dict] = []
        self.setObjectName("TrainerSessionDetailPage")
        self.setStyleSheet(f"QWidget#TrainerSessionDetailPage{{background:{PAGE_BG};}}")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 24, 34, 30)
        root.setSpacing(14)

        top = QHBoxLayout()
        self.back_button = QPushButton("←  Mes formations")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setFixedHeight(38)
        self.back_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;border-radius:10px;"
            "padding:0 14px;font-size:10px;font-weight:850;}"
            "QPushButton:hover{background:#F8FBFF;color:#338CE4;border-color:#AFCFF0;}"
        )
        self.back_button.clicked.connect(self.back_requested.emit)
        top.addWidget(self.back_button)
        top.addStretch()
        self.refresh_button = QPushButton("↻  Actualiser")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setFixedHeight(38)
        self.refresh_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:#FFFFFF;border:none;border-radius:10px;"
            "padding:0 15px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
        )
        self.refresh_button.clicked.connect(self.rafraichir)
        top.addWidget(self.refresh_button)
        root.addLayout(top)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FED7AA;border-radius:10px;"
            "padding:11px;font-size:10px;"
        )
        root.addWidget(self.error_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("SessionDetailHero")
        hero.setStyleSheet(
            "QFrame#SessionDetailHero{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF,stop:1 #EEF6FF);border:1px solid #DCE7F3;border-radius:20px;}"
            "QLabel{background:transparent;border:none;}"
        )
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(22, 19, 20, 19)
        hero_row.setSpacing(15)
        icon = QLabel("🎓")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(54, 54)
        icon.setStyleSheet("background:#0B2A52;color:#FFFFFF;border-radius:16px;font-size:23px;")
        hero_row.addWidget(icon)
        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)
        self.reference_label = QLabel("SESSION DE FORMATION")
        self.reference_label.setStyleSheet("color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;")
        self.title_label = QLabel("Session")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color:#0B1220;font-size:24px;font-weight:900;")
        self.client_label = QLabel("—")
        self.client_label.setStyleSheet("color:#64748B;font-size:11px;font-weight:700;")
        hero_text.addWidget(self.reference_label)
        hero_text.addWidget(self.title_label)
        hero_text.addWidget(self.client_label)
        hero_row.addLayout(hero_text, 1)
        self.status_label = QLabel("—")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "background:#F8FAFC;color:#475569;border:1px solid #E2E8F0;border-radius:10px;"
            "padding:8px 12px;font-size:9px;font-weight:900;"
        )
        hero_row.addWidget(self.status_label, 0, Qt.AlignTop)
        self.content_layout.addWidget(hero)

        self.organization_card = self._section_card(
            "ORGANISATION DE LA SESSION",
            "Les informations pratiques nécessaires à la réalisation de la formation.",
        )
        org_grid = QGridLayout()
        org_grid.setHorizontalSpacing(12)
        org_grid.setVerticalSpacing(10)
        self.start_value = self._value_label()
        self.end_value = self._value_label()
        self.schedule_value = self._value_label()
        self.duration_value = self._value_label()
        self.modality_value = self._value_label()
        self.participants_value = self._value_label()
        self.trainer_value = self._value_label()
        org_grid.addWidget(self._field("Début", self.start_value), 0, 0)
        org_grid.addWidget(self._field("Fin", self.end_value), 0, 1)
        org_grid.addWidget(self._field("Horaires", self.schedule_value), 1, 0)
        org_grid.addWidget(self._field("Durée", self.duration_value), 1, 1)
        org_grid.addWidget(self._field("Modalité", self.modality_value), 2, 0)
        org_grid.addWidget(self._field("Participants", self.participants_value), 2, 1)
        org_grid.addWidget(self._field("Formateur", self.trainer_value), 3, 0, 1, 2)
        self.organization_card.layout().addLayout(org_grid)
        self.join_button = QPushButton("🔗  Rejoindre la session")
        self.join_button.setCursor(Qt.PointingHandCursor)
        self.join_button.setFixedHeight(40)
        self.join_button.setVisible(False)
        self.join_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;padding:0 16px;"
            "font-size:10px;font-weight:900;}QPushButton:hover{background:#287FD4;}"
        )
        self.join_button.clicked.connect(self._open_connection_link)
        self.organization_card.layout().addWidget(self.join_button, 0, Qt.AlignLeft)
        self.content_layout.addWidget(self.organization_card)

        self.learners_card = self._section_card(
            "APPRENANTS",
            "Participants nominatifs rattachés à cette session.",
        )
        self.learners_container = QVBoxLayout()
        self.learners_container.setSpacing(8)
        self.learners_empty = QLabel("Aucun apprenant nominatif n'est encore rattaché à cette session.")
        self.learners_empty.setWordWrap(True)
        self.learners_empty.setStyleSheet(
            "background:#F8FAFC;color:#64748B;border:1px solid #E2E8F0;border-radius:10px;"
            "padding:11px;font-size:10px;"
        )
        self.learners_container.addWidget(self.learners_empty)
        self.learners_card.layout().addLayout(self.learners_container)
        self.content_layout.addWidget(self.learners_card)

        self.objectives_card, self.objectives_value = self._text_section(
            "OBJECTIFS", "Objectifs pédagogiques associés à la formation."
        )
        self.prerequisites_card, self.prerequisites_value = self._text_section(
            "PRÉREQUIS", "Prérequis communiqués pour suivre la formation."
        )
        self.description_card, self.description_value = self._text_section(
            "PROGRAMME / DESCRIPTION", "Présentation pédagogique de la formation."
        )
        self.content_layout.addWidget(self.objectives_card)
        self.content_layout.addWidget(self.prerequisites_card)
        self.content_layout.addWidget(self.description_card)

        self.contact_card = self._section_card(
            "CONTACT ENTREPRISE",
            "Coordonnées opérationnelles utiles pour préparer ou réaliser la session.",
        )
        contact_grid = QGridLayout()
        contact_grid.setHorizontalSpacing(12)
        contact_grid.setVerticalSpacing(10)
        self.contact_name = self._value_label()
        self.contact_phone = self._value_label()
        self.contact_email = self._value_label()
        contact_grid.addWidget(self._field("Contact", self.contact_name), 0, 0)
        contact_grid.addWidget(self._field("Téléphone", self.contact_phone), 0, 1)
        contact_grid.addWidget(self._field("E-mail", self.contact_email), 1, 0, 1, 2)
        self.contact_card.layout().addLayout(contact_grid)
        self.content_layout.addWidget(self.contact_card)
        self.content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    @staticmethod
    def _section_card(title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("TrainerSessionSection")
        card.setStyleSheet(
            "QFrame#TrainerSessionSection{background:#FFFFFF;border:1px solid #E2EAF3;border-radius:16px;}"
            "QLabel{background:transparent;border:none;}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setStyleSheet("color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color:#7A899C;font-size:10px;")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card

    @classmethod
    def _text_section(cls, title: str, subtitle: str) -> tuple[QFrame, QLabel]:
        card = cls._section_card(title, subtitle)
        value = QLabel("—")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value.setStyleSheet(
            "background:#F8FAFC;color:#334155;border:1px solid #E2E8F0;border-radius:10px;"
            "padding:11px;font-size:10px;line-height:1.35;"
        )
        card.layout().addWidget(value)
        return card, value

    @staticmethod
    def _value_label() -> QLabel:
        label = QLabel("—")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(
            "background:#F8FAFC;color:#334155;border:1px solid #E2E8F0;border-radius:9px;"
            "padding:9px 10px;font-size:10px;font-weight:750;"
        )
        return label

    @staticmethod
    def _field(title: str, value: QLabel) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(title)
        label.setStyleSheet("color:#64748B;font-size:9px;font-weight:850;")
        layout.addWidget(label)
        layout.addWidget(value)
        return widget

    @staticmethod
    def _display_date(value) -> str:
        if isinstance(value, date):
            return value.strftime("%d/%m/%Y")
        if not value:
            return "—"
        raw = str(value)
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except ValueError:
            try:
                return date.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
            except ValueError:
                return raw

    @staticmethod
    def _first(data: dict, *keys, default="—"):
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return value
        return default

    def charger_session(self, session_id: str) -> None:
        self.session_id = str(session_id or "").strip()
        self.rafraichir()

    def rafraichir(self) -> None:
        if not self.session_id:
            return
        self.error_label.setVisible(False)
        self.refresh_button.setEnabled(False)
        try:
            api = CloudRuntime.api()
            self.session = api.get_my_cloud_trainer_session(self.session_id)
            try:
                self.learners = api.list_my_cloud_trainer_session_learners(self.session_id)
            except Exception:
                self.learners = []
            self._render()
        except Exception as exc:
            self.session = {}
            self.learners = []
            self.error_label.setText(
                "Impossible d'ouvrir cette session. Elle n'est peut-être plus affectée à votre compte "
                "ou votre accès a été modifié.\n\n"
                f"Détail : {exc}"
            )
            self.error_label.setVisible(True)
        finally:
            self.refresh_button.setEnabled(True)

    def _render(self) -> None:
        s = self.session
        reference = str(self._first(s, "training_reference", "reference", default="")).strip()
        category = str(self._first(s, "training_category", "category", default="")).strip()
        overline = "  •  ".join(value for value in (reference, category) if value) or "SESSION DE FORMATION"
        self.reference_label.setText(overline.upper())
        self.title_label.setText(str(self._first(s, "training_name", "name", default="Formation")))
        self.client_label.setText(str(self._first(s, "client_name", default="Entreprise non renseignée")))
        self.status_label.setText(str(self._first(s, "status")))

        self.start_value.setText(self._display_date(s.get("start_date")))
        self.end_value.setText(self._display_date(s.get("end_date")))
        self.schedule_value.setText(str(self._first(s, "daily_schedule")))
        duration = self._first(s, "duration_hours", "training_duration_hours", default="")
        self.duration_value.setText(f"{duration} h" if str(duration).strip() else "—")
        self.modality_value.setText(str(self._first(s, "modality")))
        participants = self._first(s, "participant_count", default=0)
        self.participants_value.setText(str(participants))
        self.trainer_value.setText(str(self._first(s, "trainer_name", "trainer_full_name", default="—")))

        self.objectives_value.setText(str(self._first(s, "training_objectives", "objectives")))
        self.prerequisites_value.setText(str(self._first(s, "training_prerequisites", "prerequisites")))
        description = str(self._first(s, "training_description", "description"))
        certification = str(self._first(s, "training_certification", "certification", default="")).strip()
        if certification:
            description = f"{description}\n\nCertification : {certification}" if description != "—" else f"Certification : {certification}"
        self.description_value.setText(description)

        self.contact_name.setText(str(self._first(s, "client_contact")))
        self.contact_phone.setText(str(self._first(s, "client_phone")))
        self.contact_email.setText(str(self._first(s, "client_email")))
        self._render_learners()

        link = str(self._first(s, "connection_link", default="")).strip()
        self.join_button.setVisible(bool(link))

    def _clear_learner_rows(self) -> None:
        while self.learners_container.count():
            item = self.learners_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_learners(self) -> None:
        self._clear_learner_rows()
        if not self.learners:
            empty = QLabel("Aucun apprenant nominatif n'est encore rattaché à cette session.")
            empty.setWordWrap(True)
            empty.setStyleSheet(
                "background:#F8FAFC;color:#64748B;border:1px solid #E2E8F0;border-radius:10px;"
                "padding:11px;font-size:10px;"
            )
            self.learners_container.addWidget(empty)
            return

        for learner in self.learners:
            row = QFrame()
            row.setStyleSheet(
                "QFrame{background:#F8FBFF;border:1px solid #E2ECF7;border-radius:11px;}"
                "QLabel{background:transparent;border:none;}"
            )
            box = QVBoxLayout(row)
            box.setContentsMargins(12, 10, 12, 10)
            box.setSpacing(4)

            full_name = str(learner.get("full_name") or "").strip() or (
                f"{learner.get('first_name') or ''} {learner.get('last_name') or ''}".strip()
            ) or "Apprenant"
            name = QLabel(full_name)
            name.setStyleSheet("color:#173A5E;font-size:11px;font-weight:900;")
            box.addWidget(name)

            details = []
            job = str(learner.get("job_title") or "").strip()
            company = str(learner.get("company_name") or "").strip()
            email = str(learner.get("email") or "").strip()
            phone = str(learner.get("phone") or "").strip()
            if job:
                details.append(job)
            if company:
                details.append(company)
            if email:
                details.append(email)
            if phone:
                details.append(phone)
            detail_label = QLabel("  •  ".join(details) if details else "Informations complémentaires non renseignées")
            detail_label.setWordWrap(True)
            detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            detail_label.setStyleSheet("color:#64748B;font-size:9px;")
            box.addWidget(detail_label)
            self.learners_container.addWidget(row)

    def _open_connection_link(self) -> None:
        link = str(self.session.get("connection_link") or "").strip()
        if not link:
            return
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            QMessageBox.warning(self, "Lien invalide", "Le lien de connexion enregistré pour cette session n'est pas valide.")
            return
        QDesktopServices.openUrl(QUrl(link))
