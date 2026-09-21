from core.datasource_resolver import DataSourceResolver
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout,
    QTextEdit, QListWidget, QComboBox, QScrollArea, QWidget,
    QFrame, QHBoxLayout, QGridLayout, QDateEdit, QCalendarWidget, QTimeEdit
)

from core.constants import PRIMARY_COLOR
from core.crm import (
    PIPELINE,
    PIPELINE_DEFAULT,
    PRIORITES,
    PRIORITE_DEFAULT,
    ACTIONS,
    ACTION_DEFAULT,
)
from services.prospect_service import ProspectService
from services.note_service import NoteService
from services.activity_service import ActivityService
from services.scoring_service import ScoringService
from core.database import init_database
from services.cloud_runtime import CloudRuntime
from core.session import SessionState
from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_LIGHT,
    THEME_UI_DARK,
    get_theme_preference,
)
from ui.ai_premium_theme import (
    AIPremiumCard,
    theme_values,
    widget_styles,
)



class OptionalDateTimePicker(QWidget):
    """Sélecteur date + heure avec état vide pour la prochaine action."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._date = QDate()

        self.setStyleSheet("background:transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setPlaceholderText("Aucune date")

        self.time_value = QTime(9, 0)

        self.time_display = QLineEdit()
        self.time_display.setReadOnly(True)
        self.time_display.setFixedWidth(82)
        self.time_display.setText(self.time_value.toString("HH:mm"))
        self.time_display.setToolTip("Heure prévue de la prochaine action")

        self.time_button = QPushButton("Horloge")
        self.time_button.setFixedHeight(40)
        self.time_button.setCursor(Qt.PointingHandCursor)
        self.time_button.clicked.connect(self._open_time_picker)

        self.button = QPushButton("Calendrier")
        self.button.setFixedHeight(40)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self._open_calendar)

        row.addWidget(self.display, 1)
        row.addWidget(self.time_display)
        row.addWidget(self.time_button)
        row.addWidget(self.button)

        self._apply_style()
        self.clear_date()

    def _apply_style(self):
        self.display.setMinimumHeight(40)
        self.display.setStyleSheet("""
            QLineEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:8px 10px;
                font-size:12px;
                font-weight:750;
            }
        """)

        self.time_display.setMinimumHeight(40)
        self.time_display.setStyleSheet("""
            QLineEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:8px 10px;
                font-size:12px;
                font-weight:900;
            }
        """)

        self.time_button.setStyleSheet("""
            QPushButton {
                background:#F8FBFF;
                color:#0B2A52;
                border:1px solid #D7E6F4;
                border-radius:10px;
                padding:0 12px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#EAF4FF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """)

        self.button.setStyleSheet("""
            QPushButton {
                background:#F8FBFF;
                color:#0B2A52;
                border:1px solid #D7E6F4;
                border-radius:10px;
                padding:0 13px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#EAF4FF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """)

    def _open_time_picker(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sélectionner une heure")
        dialog.setModal(True)
        dialog.resize(430, 430)
        dialog.setStyleSheet("background:#FFFFFF;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(14)

        title = QLabel("Choisir l’heure de la prochaine action")
        title.setStyleSheet(
            "font-size:15px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )
        subtitle = QLabel("Sélectionnez d’abord l’heure, puis les minutes.")
        subtitle.setStyleSheet(
            "font-size:11px; color:#7A899C; background:transparent; border:none;"
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Affichage central façon horloge digitale
        selected = {
            "hour": self.time_value.hour(),
            "minute": self.time_value.minute(),
        }
        clock_display = QLabel(
            f"{selected['hour']:02d}:{selected['minute']:02d}"
        )
        clock_display.setAlignment(Qt.AlignCenter)
        clock_display.setFixedHeight(66)
        clock_display.setStyleSheet("""
            QLabel {
                background:#0B2A52;
                color:#FFFFFF;
                border:none;
                border-radius:16px;
                font-size:28px;
                font-weight:900;
                letter-spacing:2px;
            }
        """)
        layout.addWidget(clock_display)

        def refresh_clock():
            clock_display.setText(
                f"{selected['hour']:02d}:{selected['minute']:02d}"
            )

        # Heures
        hours_label = QLabel("HEURE")
        hours_label.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        layout.addWidget(hours_label)

        hours_grid = QGridLayout()
        hours_grid.setHorizontalSpacing(7)
        hours_grid.setVerticalSpacing(7)

        hour_buttons = []
        for h in range(8, 21):  # plage commerciale 08h → 20h
            btn = QPushButton(f"{h:02d}")
            btn.setCheckable(True)
            btn.setFixedSize(52, 38)
            btn.setChecked(h == selected["hour"])
            btn.setStyleSheet("""
                QPushButton {
                    background:#F8FBFF;
                    color:#334155;
                    border:1px solid #DCE5EF;
                    border-radius:10px;
                    font-size:11px;
                    font-weight:850;
                }
                QPushButton:hover {
                    background:#EAF4FF;
                    color:#338CE4;
                    border-color:#AFCFF0;
                }
                QPushButton:checked {
                    background:#338CE4;
                    color:#FFFFFF;
                    border:1px solid #338CE4;
                }
            """)
            hour_buttons.append((h, btn))
            hours_grid.addWidget(btn, (h - 8) // 7, (h - 8) % 7)

        def choose_hour(hour, button):
            selected["hour"] = hour
            for _, b in hour_buttons:
                b.setChecked(b is button)
            refresh_clock()

        for hour, button in hour_buttons:
            button.clicked.connect(
                lambda checked=False, h=hour, b=button: choose_hour(h, b)
            )

        layout.addLayout(hours_grid)

        # Minutes par pas de 5 minutes
        minutes_label = QLabel("MINUTES")
        minutes_label.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        layout.addWidget(minutes_label)

        minutes_row = QHBoxLayout()
        minutes_row.setSpacing(7)
        minute_buttons = []

        for minute in (0, 15, 30, 45):
            btn = QPushButton(f"{minute:02d}")
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setChecked(minute == selected["minute"])
            btn.setStyleSheet("""
                QPushButton {
                    background:#F8FBFF;
                    color:#334155;
                    border:1px solid #DCE5EF;
                    border-radius:10px;
                    font-size:11px;
                    font-weight:850;
                }
                QPushButton:hover {
                    background:#EAF4FF;
                    color:#338CE4;
                    border-color:#AFCFF0;
                }
                QPushButton:checked {
                    background:#0B2A52;
                    color:#FFFFFF;
                    border:1px solid #0B2A52;
                }
            """)
            minute_buttons.append((minute, btn))
            minutes_row.addWidget(btn)

        def choose_minute(minute, button):
            selected["minute"] = minute
            for _, b in minute_buttons:
                b.setChecked(b is button)
            refresh_clock()

        for minute, button in minute_buttons:
            button.clicked.connect(
                lambda checked=False, m=minute, b=button: choose_minute(m, b)
            )

        layout.addLayout(minutes_row)

        actions = QHBoxLayout()
        cancel_btn = QPushButton("Annuler")
        select_btn = QPushButton("Sélectionner")

        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:9px;
                padding:0 14px;
                font-size:11px;
                font-weight:800;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
            }
        """)

        select_btn.setFixedHeight(38)
        select_btn.setStyleSheet("""
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:9px;
                padding:0 16px;
                font-size:11px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
        """)

        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(select_btn)
        layout.addLayout(actions)

        cancel_btn.clicked.connect(dialog.reject)

        def apply_time():
            self.set_time(QTime(selected["hour"], selected["minute"]))
            dialog.accept()

        select_btn.clicked.connect(apply_time)

        dialog.exec()

    def _open_calendar(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sélectionner une date")
        dialog.setModal(True)
        dialog.resize(410, 360)
        dialog.setStyleSheet("background:#FFFFFF;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        title = QLabel("Choisir la date de la prochaine action")
        title.setStyleSheet(
            "font-size:15px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )
        layout.addWidget(title)

        calendar = QCalendarWidget()
        calendar.setGridVisible(False)

        initial = self._date if self._date.isValid() else QDate.currentDate()
        calendar.setSelectedDate(initial)
        calendar.setCurrentPage(initial.year(), initial.month())

        calendar.setStyleSheet("""
            QCalendarWidget {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:14px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background:#0B2A52;
                border-top-left-radius:12px;
                border-top-right-radius:12px;
            }
            QCalendarWidget QToolButton {
                color:#FFFFFF;
                background:transparent;
                border:none;
                font-size:13px;
                font-weight:900;
                padding:7px 8px;
                margin:2px;
            }
            QCalendarWidget QToolButton:hover {
                background:#123966;
                border-radius:8px;
            }
            QCalendarWidget QMenu {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
            }
            QCalendarWidget QSpinBox {
                background:#FFFFFF;
                color:#172033;
                selection-background-color:#338CE4;
                selection-color:#FFFFFF;
                border:1px solid #DCE5EF;
                border-radius:7px;
                padding:4px 6px;
                font-size:12px;
                font-weight:800;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background:#FFFFFF;
                color:#334155;
                selection-background-color:#338CE4;
                selection-color:#FFFFFF;
                outline:0;
                font-size:12px;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color:#CBD5E1;
            }
        """)
        layout.addWidget(calendar, 1)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Effacer la date")
        cancel_btn = QPushButton("Annuler")
        select_btn = QPushButton("Sélectionner")

        for button in (clear_btn, cancel_btn):
            button.setFixedHeight(38)
            button.setStyleSheet("""
                QPushButton {
                    background:#FFFFFF;
                    color:#334155;
                    border:1px solid #DCE5EF;
                    border-radius:9px;
                    padding:0 13px;
                    font-size:11px;
                    font-weight:800;
                }
                QPushButton:hover {
                    background:#F8FBFF;
                    color:#338CE4;
                    border-color:#AFCFF0;
                }
            """)

        select_btn.setFixedHeight(38)
        select_btn.setStyleSheet("""
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:9px;
                padding:0 15px;
                font-size:11px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
        """)

        actions.addWidget(clear_btn)
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(select_btn)
        layout.addLayout(actions)

        clear_btn.clicked.connect(lambda: (self.clear_date(), dialog.accept()))
        cancel_btn.clicked.connect(dialog.reject)

        def choose_date():
            self.set_date(calendar.selectedDate())
            dialog.accept()

        select_btn.clicked.connect(choose_date)
        calendar.activated.connect(
            lambda selected: (self.set_date(selected), dialog.accept())
        )

        dialog.exec()

    def set_date(self, value: QDate):
        if value and value.isValid():
            self._date = value
            self.display.setText(value.toString("dd/MM/yyyy"))
        else:
            self.clear_date()

    def set_time(self, value: QTime):
        if value and value.isValid():
            self.time_value = value
            self.time_display.setText(value.toString("HH:mm"))

    def clear_date(self):
        self._date = QDate()
        self.display.clear()
        self.display.setPlaceholderText("Aucune date")

    def has_date(self):
        return self._date.isValid()

    def date(self):
        return self._date

    def time(self):
        return self.time_value


class ProspectDialog(QDialog):
    def __init__(self, database_path, prospect_id, *, is_cloud_mode=None):
        super().__init__()

        self.database_path = database_path
        self.prospect_id = prospect_id

        self.prospect_service = ProspectService()
        self.datasource = DataSourceResolver()
        # Le contexte de la page CRM est la source fiable. Une session Cloud
        # peut coexister avec un projet local et le dialogue ne doit donc pas
        # déduire seul son mode depuis la session.
        if is_cloud_mode is None:
            try:
                self._is_cloud_mode = self.datasource.resolve().is_cloud
            except Exception:
                self._is_cloud_mode = False
        else:
            self._is_cloud_mode = bool(is_cloud_mode)

        self._can_assign_owner = (
            self._is_cloud_mode
            and SessionState.has_role("Administrateur")
        )

        self._theme_preference = get_theme_preference()
        self._resolved_theme = self._theme_preference

        # Les notes et l'historique doivent suivre le contexte explicite de
        # la fiche. Cela permet d'ouvrir une fiche depuis le CRM Cloud global
        # même lorsqu'aucun projet Form@Prospect n'est ouvert.
        self.note_service = NoteService(is_cloud_mode=self._is_cloud_mode)
        self.activity_service = ActivityService(is_cloud_mode=self._is_cloud_mode)

        self.ancien_pipeline = PIPELINE_DEFAULT
        self.ancienne_priorite = PRIORITE_DEFAULT
        self.ancienne_action = ACTION_DEFAULT
        self.ancienne_date_action = ""
        self.ancien_commercial = ""
        # En mode Cloud, la sélection du statut Client ne doit jamais être
        # enregistrée directement. La page CRM ouvrira ensuite le formulaire
        # juridique complet avant de valider réellement la conversion.
        self.client_conversion_requested = False

        if not self._is_cloud_mode:
            init_database(self.database_path)

        if self._resolved_theme == THEME_CLASSIC:
            self.setWindowTitle("Fiche prospect")
            self.resize(980, 860)
            self.setMinimumSize(820, 640)
        else:
            self.setWindowTitle("Form@Prospect — AI Prospect Command Center")
            self.resize(1120, 900)
            self.setMinimumSize(920, 700)
        self.setStyleSheet(
            f"background:{theme_values(self._resolved_theme)['bg']};"
        )

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # -------------------------
        # Header AI Premium fixe
        # -------------------------
        header = QFrame()
        self.header = header
        header.setObjectName("ProspectHeader")
        header.setStyleSheet("""
            QFrame#ProspectHeader {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #071321,
                    stop:0.52 #0B2137,
                    stop:0.82 #102D4B,
                    stop:1 #151D43
                );
                border:none;
                border-bottom:1px solid #214D70;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 24, 30, 22)
        header_layout.setSpacing(18)

        accent = QFrame()
        self.header_accent = accent
        accent.setFixedWidth(4)
        accent.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #65D8FF, stop:0.55 #338CE4, stop:1 #6C63FF);"
            "border:none; border-radius:2px;"
        )
        header_layout.addWidget(accent)

        header_texts = QVBoxLayout()
        header_texts.setSpacing(4)

        eyebrow = QLabel("FORM@PROSPECT  •  AI SALES COMMAND CENTER")
        self.header_eyebrow = eyebrow
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.35px; "
            "color:#65D8FF; background:transparent; border:none;"
        )

        self.titre = QLabel("Fiche prospect")
        self.titre.setStyleSheet(
            "font-size:30px; font-weight:900; color:#F7FBFF; "
            "background:transparent; border:none;"
        )

        self.header_subtitle = QLabel(
            "Données, actions commerciales, automatisation et historique."
        )
        self.header_subtitle.setStyleSheet(
            "font-size:12px; color:#8EA7C1; background:transparent; border:none;"
        )

        header_texts.addWidget(eyebrow)
        header_texts.addWidget(self.titre)
        header_texts.addWidget(self.header_subtitle)

        header_status = QVBoxLayout()
        header_status.setSpacing(8)

        mode_text = "CLOUD CRM" if self._is_cloud_mode else "LOCAL CRM"
        self.header_mode_chip = QLabel(f"●  {mode_text}")
        self.header_mode_chip.setAlignment(Qt.AlignCenter)
        self.header_mode_chip.setFixedHeight(28)
        self.header_mode_chip.setStyleSheet(
            "font-size:9px; font-weight:900; letter-spacing:0.8px; "
            "color:#8FE7FF; background:#0B2742; "
            "border:1px solid #255B84; border-radius:10px; padding:0 11px;"
        )

        self.header_pipeline_badge = QLabel("PROSPECT")
        self.header_pipeline_badge.setAlignment(Qt.AlignCenter)
        self.header_pipeline_badge.setMinimumWidth(120)
        self.header_pipeline_badge.setFixedHeight(34)

        header_status.addWidget(self.header_mode_chip)
        header_status.addWidget(self.header_pipeline_badge)
        header_status.addStretch()

        header_layout.addLayout(header_texts, 1)
        header_layout.addLayout(header_status)

        # -------------------------
        # Scroll area
        # -------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background:#06111F;
                border:none;
            }
            QScrollBar:vertical {
                background:#06111F;
                width:11px;
                margin:5px 2px 5px 2px;
            }
            QScrollBar::handle:vertical {
                background:#173A58;
                min-height:42px;
                border-radius:5px;
            }
            QScrollBar::handle:vertical:hover {
                background:#338CE4;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background:transparent;
            }
        """)

        content = QWidget()
        self.content = content
        content.setStyleSheet("background:#06111F;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 26, 30, 30)
        layout.setSpacing(20)

        # -------------------------
        # Widgets / champs
        # -------------------------
        self.entreprise_input = QLineEdit()
        self.siret_input = QLineEdit()
        self.ville_input = QLineEdit()
        self.cp_input = QLineEdit()
        self.telephone_input = QLineEdit()
        self.telephone_input.setPlaceholderText("Téléphone principal")
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("Mobile / second numéro")
        self.site_input = QLineEdit()
        self.email_input = QLineEdit()
        self.facebook_input = QLineEdit()
        self.linkedin_input = QLineEdit()
        self.instagram_input = QLineEdit()
        self.twitter_input = QLineEdit()
        self.youtube_input = QLineEdit()
        self.social_other_urls_input = QTextEdit()
        self.social_other_urls_input.setFixedHeight(76)
        self.social_other_urls_input.setPlaceholderText(
            "Autres URL sociales détectées, une par ligne"
        )

        self.pipeline_input = QComboBox()
        from PySide6.QtGui import QColor, QIcon, QPixmap

        for pipeline_value in PIPELINE:
            canonical = str(pipeline_value)
            if "nouveau" in canonical.lower():
                marker = QPixmap(9, 9)
                marker.fill(QColor("#338CE4"))
                self.pipeline_input.addItem(QIcon(marker), "Nouveau", canonical)
            else:
                self.pipeline_input.addItem(canonical, canonical)

        self.pipeline_input.currentIndexChanged.connect(
            lambda _index: self._refresh_header_badge(
                self.pipeline_input.currentData()
                or self.pipeline_input.currentText()
            )
        )

        self.priorite_input = QComboBox()
        self.priorite_input.addItems(PRIORITES)

        self.prochaine_action_input = QComboBox()
        self.prochaine_action_input.addItems(ACTIONS)

        self.date_prochaine_action_input = OptionalDateTimePicker()
        self.date_prochaine_action_input.setToolTip(
            "Sélectionnez la date avec le calendrier puis choisissez l’heure prévue."
        )

        self.commercial_input = QLineEdit()
        self.commercial_input.setPlaceholderText("Nom du commercial assigné")
        self.commercial_selector = QComboBox()
        self.commercial_selector.addItem("Non affecté", None)
        if self._can_assign_owner and CloudRuntime.is_active():
            try:
                for candidate in CloudRuntime.api().list_users(active_only=True):
                    if getattr(candidate, "is_commercial", False):
                        self.commercial_selector.addItem(
                            str(candidate.display_name),
                            str(candidate.id),
                        )
            except Exception:
                pass
        self.commercial_selector.setVisible(self._can_assign_owner)
        self.commercial_input.setVisible(not self._can_assign_owner)
        if self._is_cloud_mode and not self._can_assign_owner:
            self.commercial_input.setReadOnly(True)
        self.commercial_field = (
            self.commercial_selector
            if self._can_assign_owner
            else self.commercial_input
        )

        self.score_input = QLineEdit()
        self.score_input.setReadOnly(True)

        self.score_details_input = QTextEdit()
        self.score_details_input.setReadOnly(True)
        self.score_details_input.setFixedHeight(92)

        self.entreprise_input.setReadOnly(True)
        self.siret_input.setReadOnly(True)
        self.ville_input.setReadOnly(True)
        self.cp_input.setReadOnly(True)

        # Les styles complets sont appliqués après création de tous les widgets
        # (notes_liste, note_input, activities_liste, etc.).

        # -------------------------
        # Carte identité & contact
        # -------------------------
        identity_card = self._section_card(
            "IDENTITÉ & CONTACT",
            "Les informations utiles pour joindre et qualifier l'entreprise."
        )
        identity_grid = QGridLayout()
        identity_grid.setHorizontalSpacing(14)
        identity_grid.setVerticalSpacing(12)

        identity_grid.addWidget(self._field_block("Entreprise", self.entreprise_input), 0, 0)
        identity_grid.addWidget(self._field_block("SIRET", self.siret_input), 0, 1)
        identity_grid.addWidget(self._field_block("Ville", self.ville_input), 1, 0)
        identity_grid.addWidget(self._field_block("Code postal", self.cp_input), 1, 1)
        identity_grid.addWidget(self._field_block("Téléphone", self.telephone_input), 2, 0)
        identity_grid.addWidget(self._field_block("Mobile", self.mobile_input), 2, 1)
        identity_grid.addWidget(self._field_block("E-mail", self.email_input), 3, 0)
        identity_grid.addWidget(self._field_block("Site web", self.site_input), 3, 1)
        identity_card.layout().addLayout(identity_grid)
        layout.addWidget(identity_card)

        # -------------------------
        # Carte réseaux sociaux
        # -------------------------
        social_card = self._section_card(
            "PRÉSENCE DIGITALE",
            "Centralisez les réseaux sociaux et points de contact numériques."
        )
        social_grid = QGridLayout()
        social_grid.setHorizontalSpacing(14)
        social_grid.setVerticalSpacing(12)

        social_grid.addWidget(self._field_block("LinkedIn", self.linkedin_input), 0, 0)
        social_grid.addWidget(self._field_block("Facebook", self.facebook_input), 0, 1)
        social_grid.addWidget(self._field_block("Instagram", self.instagram_input), 1, 0)
        social_grid.addWidget(self._field_block("X / Twitter", self.twitter_input), 1, 1)
        social_grid.addWidget(self._field_block("YouTube", self.youtube_input), 2, 0, 1, 2)
        social_grid.addWidget(self._field_block("Autres réseaux", self.social_other_urls_input), 3, 0, 1, 2)
        social_card.layout().addLayout(social_grid)
        layout.addWidget(social_card)

        # -------------------------
        # Carte suivi commercial
        # -------------------------
        sales_card = self._section_card(
            "SUIVI COMMERCIAL",
            "Pilotez l'étape, la priorité et la prochaine action."
        )
        sales_grid = QGridLayout()
        sales_grid.setHorizontalSpacing(14)
        sales_grid.setVerticalSpacing(12)

        sales_grid.addWidget(self._field_block("Pipeline", self.pipeline_input), 0, 0)
        sales_grid.addWidget(self._field_block("Priorité", self.priorite_input), 0, 1)
        sales_grid.addWidget(self._field_block("Prochaine action", self.prochaine_action_input), 1, 0)
        sales_grid.addWidget(self._field_block("Date et heure prochaine action", self.date_prochaine_action_input), 1, 1)
        sales_grid.addWidget(self._field_block("Commercial assigné", self.commercial_field), 2, 0, 1, 2)
        sales_card.layout().addLayout(sales_grid)
        layout.addWidget(sales_card)

        # -------------------------
        # Carte scoring
        # -------------------------
        score_card = self._section_card(
            "SCORING COMMERCIAL",
            "Mesurez le potentiel et la complétude du prospect."
        )
        score_card.layout().addWidget(self.score_input)
        score_card.layout().addWidget(self.score_details_input)
        layout.addWidget(score_card)

        # -------------------------
        # Notes CRM
        # -------------------------
        notes_card = self._section_card(
            "NOTES CRM",
            "Gardez le contexte commercial et les informations importantes."
        )

        self.notes_liste = QListWidget()
        self.notes_liste.setFixedHeight(150)
        self.notes_liste.setSpacing(4)
        self.notes_liste.setToolTip(
            "Historique des notes saisies manuellement sur ce prospect."
        )
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Ajouter une nouvelle note...")
        self.note_input.setFixedHeight(82)

        bouton_ajouter_note = QPushButton("Ajouter la note")
        self.bouton_ajouter_note = bouton_ajouter_note
        bouton_ajouter_note.setFixedHeight(40)
        bouton_ajouter_note.clicked.connect(self.ajouter_note)
        bouton_ajouter_note.setStyleSheet(self._secondary_action_style())

        notes_card.layout().addWidget(self.notes_liste)
        notes_card.layout().addWidget(self.note_input)
        notes_actions = QHBoxLayout()
        notes_actions.addStretch()
        notes_actions.addWidget(bouton_ajouter_note)
        notes_card.layout().addLayout(notes_actions)
        layout.addWidget(notes_card)

        # -------------------------
        # Historique
        # -------------------------
        history_card = self._section_card(
            "HISTORIQUE DES ACTIONS",
            "Retrouvez les dernières modifications et interactions enregistrées."
        )
        self.activities_liste = QListWidget()
        self.activities_liste.setFixedHeight(190)
        self.activities_liste.setSpacing(4)
        self.activities_liste.setToolTip(
            "Historique chronologique des actions et modifications du prospect."
        )
        history_card.layout().addWidget(self.activities_liste)
        layout.addWidget(history_card)

        # Tous les champs et listes existent maintenant : on peut appliquer
        # les styles sans provoquer d'AttributeError.
        self._apply_field_styles()

        self.scroll_area.setWidget(content)

        # -------------------------
        # Footer fixe
        # -------------------------
        footer = QFrame()
        self.footer = footer
        footer.setObjectName("ProspectFooter")
        footer.setStyleSheet("""
            QFrame#ProspectFooter {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #071522,
                    stop:1 #0A1D30
                );
                border:none;
                border-top:1px solid #1C405F;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(26, 14, 26, 14)
        footer_layout.setSpacing(10)

        footer_hint = QLabel("AI PREMIUM EXPERIENCE  •  Form@Prospect")
        self.footer_hint = footer_hint
        footer_hint.setStyleSheet(
            "font-size:9px; font-weight:800; letter-spacing:1px; "
            "color:#52718D; background:transparent; border:none;"
        )

        cancel_button = QPushButton("Fermer")
        self.cancel_button = cancel_button
        cancel_button.setFixedHeight(44)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(self._secondary_action_style())

        self.bouton_enregistrer = QPushButton("Enregistrer les modifications")
        self.bouton_enregistrer.setFixedHeight(44)
        self.bouton_enregistrer.clicked.connect(self.enregistrer)
        self.bouton_enregistrer.setStyleSheet(self._primary_action_style())

        footer_layout.addWidget(footer_hint)
        footer_layout.addStretch()
        footer_layout.addWidget(cancel_button)
        footer_layout.addWidget(self.bouton_enregistrer)

        page_layout.addWidget(header)
        page_layout.addWidget(self.scroll_area, 1)
        page_layout.addWidget(footer)

        self._apply_theme()

        self.charger_prospect()
        self.charger_notes()
        self.charger_activities()

    @staticmethod
    def _section_card(title, subtitle):
        variant = "ai" if "SCORING" in str(title).upper() else "default"
        card = AIPremiumCard(variant=variant)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(13)

        title_row = QHBoxLayout()
        title_row.setSpacing(9)

        signal = QLabel("●")
        signal.setObjectName("ProspectCardSignal")
        signal.setFixedWidth(12)
        signal.setStyleSheet(
            "font-size:12px; color:#65D8FF; background:transparent; border:none;"
        )

        eyebrow = QLabel(title)
        eyebrow.setObjectName("ProspectCardTitle")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.15px; "
            "color:#65D8FF; background:transparent; border:none;"
        )

        title_row.addWidget(signal)
        title_row.addWidget(eyebrow)
        title_row.addStretch()

        description = QLabel(subtitle)
        description.setObjectName("ProspectCardDescription")
        description.setWordWrap(True)
        description.setStyleSheet(
            "font-size:11px; color:#7892AE; background:transparent; border:none;"
        )

        card_layout.addLayout(title_row)
        card_layout.addWidget(description)
        return card

    @staticmethod
    def _field_block(label_text, field):
        block = QWidget()
        block.setStyleSheet("background:transparent;")
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(7)

        label = QLabel(label_text)
        label.setObjectName("ProspectFieldLabel")
        label.setStyleSheet(
            "font-size:10px; font-weight:850; letter-spacing:0.35px; "
            "color:#8EA7C1; background:transparent; border:none;"
        )

        block_layout.addWidget(label)
        block_layout.addWidget(field)
        return block

    def _apply_field_styles(self):
        styles = widget_styles(self._resolved_theme)
        editable = [
            self.telephone_input,
            self.mobile_input,
            self.site_input,
            self.email_input,
            self.facebook_input,
            self.linkedin_input,
            self.instagram_input,
            self.twitter_input,
            self.youtube_input,
            self.commercial_input,
        ]
        readonly = [
            self.entreprise_input,
            self.siret_input,
            self.ville_input,
            self.cp_input,
        ]
        combos = [
            self.pipeline_input,
            self.priorite_input,
            self.prochaine_action_input,
            self.commercial_selector,
        ]

        for widget in editable:
            widget.setMinimumHeight(42)
            widget.setStyleSheet(styles["editable"])

        for widget in readonly:
            widget.setMinimumHeight(42)
            widget.setStyleSheet(styles["readonly"])

        for widget in combos:
            widget.setMinimumHeight(42)
            widget.setStyleSheet(styles["combo"])

        self.social_other_urls_input.setStyleSheet(styles["editable"])

        picker = self.date_prochaine_action_input
        picker.display.setMinimumHeight(42)
        picker.display.setStyleSheet(styles["date_display"])
        picker.time_display.setMinimumHeight(42)
        picker.time_display.setStyleSheet(styles["date_display"])
        picker.time_button.setMinimumHeight(42)
        picker.time_button.setStyleSheet(styles["date_button"])
        picker.button.setMinimumHeight(42)
        picker.button.setStyleSheet(styles["date_button"])

        self.score_input.setMinimumHeight(50)
        self.score_input.setStyleSheet(styles["score"])
        self.score_details_input.setStyleSheet(styles["score_details"])

        self.notes_liste.setStyleSheet(styles["list"])
        self.note_input.setStyleSheet(styles["editable"])
        self.activities_liste.setStyleSheet(styles["list"])

    def _primary_action_style(self):
        return widget_styles(self._resolved_theme)["primary"]

    def _secondary_action_style(self):
        return widget_styles(self._resolved_theme)["secondary"]

    def _apply_theme(self):
        self._theme_preference = get_theme_preference()
        self._resolved_theme = self._theme_preference
        p = theme_values(self._resolved_theme)
        styles = widget_styles(self._resolved_theme)
        classic = self._resolved_theme == THEME_CLASSIC
        dark = self._resolved_theme == THEME_UI_DARK

        self.setStyleSheet(f"background:{p['bg']};")
        self.content.setStyleSheet(f"background:{p['bg']};")

        if classic:
            self.setWindowTitle("Fiche prospect")
            self.header.layout().setContentsMargins(28, 22, 28, 20)
            self.header.layout().setSpacing(16)
            self.content.layout().setContentsMargins(28, 24, 28, 28)
            self.content.layout().setSpacing(18)
            self.footer.layout().setContentsMargins(24, 14, 24, 14)
            self.header_accent.setVisible(False)
            self.header_eyebrow.setText("CRM  •  FICHE PROSPECT")
            self.header_eyebrow.setStyleSheet(
                "font-size:10px; font-weight:900; letter-spacing:1.1px; "
                "color:#338CE4; background:transparent; border:none;"
            )
            self.header_mode_chip.setVisible(False)
            self.footer_hint.setVisible(False)

            self.header.setStyleSheet("""
                QFrame#ProspectHeader {
                    background:qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #FFFFFF,
                        stop:0.72 #F7FBFF,
                        stop:1 #EAF4FF
                    );
                    border:none;
                    border-bottom:1px solid #E4EBF4;
                }
            """)
            self.footer.setStyleSheet("""
                QFrame#ProspectFooter {
                    background:#FFFFFF;
                    border:none;
                    border-top:1px solid #E4EBF4;
                }
            """)
            self.titre.setStyleSheet(
                "font-size:28px; font-weight:900; color:#0B1220; "
                "background:transparent; border:none;"
            )
            self.header_subtitle.setStyleSheet(
                "font-size:12px; color:#6B7A90; "
                "background:transparent; border:none;"
            )
        else:
            self.setWindowTitle("Form@Prospect — AI Prospect Command Center")
            self.header.layout().setContentsMargins(30, 24, 30, 22)
            self.header.layout().setSpacing(18)
            self.content.layout().setContentsMargins(30, 26, 30, 30)
            self.content.layout().setSpacing(20)
            self.footer.layout().setContentsMargins(26, 14, 26, 14)
            self.header_accent.setVisible(True)
            self.header_eyebrow.setText(
                "FORM@PROSPECT  •  AI SALES COMMAND CENTER"
            )
            self.header_eyebrow.setStyleSheet(
                f"font-size:10px; font-weight:900; letter-spacing:1.35px; "
                f"color:{p['cyan']}; background:transparent; border:none;"
            )
            self.header_mode_chip.setVisible(True)
            self.footer_hint.setVisible(True)

            if dark:
                header_start, header_mid, header_end = (
                    "#071321", "#0B2137", "#151D43"
                )
                footer_start, footer_end = "#071522", "#0A1D30"
            else:
                header_start, header_mid, header_end = (
                    "#FFFFFF", "#F5FAFF", "#E8F4FF"
                )
                footer_start, footer_end = "#FFFFFF", "#F3F8FD"

            self.header.setStyleSheet(f"""
                QFrame#ProspectHeader {{
                    background:qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 {header_start},
                        stop:0.52 {header_mid},
                        stop:1 {header_end}
                    );
                    border:none;
                    border-bottom:1px solid {p['border']};
                }}
            """)
            self.footer.setStyleSheet(f"""
                QFrame#ProspectFooter {{
                    background:qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {footer_start},
                        stop:1 {footer_end}
                    );
                    border:none;
                    border-top:1px solid {p['border']};
                }}
            """)
            self.titre.setStyleSheet(
                f"font-size:30px; font-weight:900; color:{p['text']}; "
                "background:transparent; border:none;"
            )
            self.header_subtitle.setStyleSheet(
                f"font-size:12px; color:{p['muted']}; "
                "background:transparent; border:none;"
            )
            self.header_mode_chip.setStyleSheet(
                f"font-size:9px; font-weight:900; letter-spacing:0.8px; "
                f"color:{p['cyan']}; background:{p['surface_3']}; "
                f"border:1px solid {p['border']}; border-radius:10px; "
                "padding:0 11px;"
            )
            self.footer_hint.setStyleSheet(
                "font-size:9px; font-weight:800; letter-spacing:1px; "
                f"color:{'#52718D' if dark else '#7189A2'}; "
                "background:transparent; border:none;"
            )

        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background:{p['bg']};
                border:none;
            }}
            QScrollBar:vertical {{
                background:{p['bg']};
                width:{10 if classic else 11}px;
                margin:4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background:{'#CBD5E1' if classic else p['border']};
                min-height:40px;
                border-radius:5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background:{'#94A3B8' if classic else '#338CE4'};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height:0;
            }}
        """)

        for card in self.findChildren(AIPremiumCard):
            card.set_theme_mode(self._resolved_theme)
            if card.layout() is not None:
                if classic:
                    card.layout().setContentsMargins(20, 18, 20, 20)
                    card.layout().setSpacing(12)
                else:
                    card.layout().setContentsMargins(22, 20, 22, 22)
                    card.layout().setSpacing(13)

            signal = card.findChild(QLabel, "ProspectCardSignal")
            title = card.findChild(QLabel, "ProspectCardTitle")
            description = card.findChild(QLabel, "ProspectCardDescription")

            if signal is not None:
                signal.setVisible(not classic)
                signal.setStyleSheet(
                    f"font-size:12px; color:{p['cyan']}; "
                    "background:transparent; border:none;"
                )
            if title is not None:
                title.setStyleSheet(
                    "font-size:10px; font-weight:900; letter-spacing:1px; "
                    f"color:{'#338CE4' if classic else p['cyan']}; "
                    "background:transparent; border:none;"
                )
            if description is not None:
                description.setStyleSheet(
                    "font-size:11px; "
                    f"color:{'#7A899C' if classic else p['muted']}; "
                    "background:transparent; border:none;"
                )

        for label in self.findChildren(QLabel, "ProspectFieldLabel"):
            parent = label.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().setSpacing(6 if classic else 7)
            label.setStyleSheet(
                "font-size:11px; font-weight:800; "
                f"color:{'#53657C' if classic else p['muted']}; "
                "background:transparent; border:none;"
            )

        self._apply_field_styles()
        self.cancel_button.setStyleSheet(styles["secondary"])
        self.bouton_ajouter_note.setStyleSheet(styles["secondary"])
        self.bouton_enregistrer.setStyleSheet(styles["primary"])
        self._refresh_header_badge(
            self.pipeline_input.currentData()
            or self.pipeline_input.currentText()
        )

    def _refresh_header_badge(self, pipeline_text):
        text = str(pipeline_text or "")
        lowered = text.lower()
        classic = self._resolved_theme == THEME_CLASSIC
        dark = self._resolved_theme == THEME_UI_DARK

        if classic:
            labels = {
                "nouveau": ("NOUVEAU", "#EAF4FF", "#0B5FC6", "#338CE4"),
                "qualification": ("QUALIFICATION", "#FFFBEB", "#854D0E", "#FDE68A"),
                "rdv": ("RDV PROGRAMMÉ", "#EFF8FF", "#075985", "#BAE6FD"),
                "proposition": ("PROPOSITION", "#FAF5FF", "#6B21A8", "#E9D5FF"),
                "négociation": ("NÉGOCIATION", "#FFF7ED", "#9A3412", "#FED7AA"),
                "negociation": ("NÉGOCIATION", "#FFF7ED", "#9A3412", "#FED7AA"),
                "client": ("CLIENT", "#ECFDF3", "#166534", "#86EFAC"),
                "perdu": ("PERDU", "#FEF2F2", "#991B1B", "#FECACA"),
            }
            values = ("PROSPECT", "#EFF8FF", "#075985", "#BAE6FD")
            for token, candidate in labels.items():
                if token in lowered:
                    values = candidate
                    break
        elif "qualification" in lowered:
            values = (
                ("QUALIFICATION", "#2A2412", "#FFD27A", "#735921")
                if dark else
                ("QUALIFICATION", "#FFF7E4", "#8A5700", "#E8C982")
            )
        elif "rdv" in lowered:
            values = (
                ("RDV PROGRAMMÉ", "#0C2C45", "#7FDBFF", "#276991")
                if dark else
                ("RDV PROGRAMMÉ", "#EAF7FF", "#09608F", "#A8D8F2")
            )
        elif "proposition" in lowered:
            values = (
                ("PROPOSITION", "#241B42", "#C8A8FF", "#5B4288")
                if dark else
                ("PROPOSITION", "#F4EEFF", "#6742A1", "#CDBAEC")
            )
        elif "négociation" in lowered or "negociation" in lowered:
            values = (
                ("NÉGOCIATION", "#382313", "#FFB77A", "#865127")
                if dark else
                ("NÉGOCIATION", "#FFF1E5", "#9A4F0C", "#E9BF98")
            )
        elif "client" in lowered:
            values = (
                ("CLIENT", "#0E3027", "#73E8B4", "#28765B")
                if dark else
                ("CLIENT", "#E9FAF4", "#137450", "#A7DEC9")
            )
        elif "perdu" in lowered:
            values = (
                ("PERDU", "#35171F", "#FF91A2", "#7E3341")
                if dark else
                ("PERDU", "#FFF0F3", "#A62D47", "#EDB7C2")
            )
        elif "nouveau" in lowered:
            values = (
                ("NOUVEAU", "#0B2742", "#8FD6FF", "#338CE4")
                if dark else
                ("NOUVEAU", "#EAF4FF", "#0B5FC6", "#338CE4")
            )
        else:
            values = (
                ("PROSPECT", "#0B2742", "#8FE7FF", "#2A668F")
                if dark else
                ("PROSPECT", "#EAF6FF", "#0A659D", "#A7D6F5")
            )

        label, bg, fg, border = values
        self.header_pipeline_badge.setText(label)
        self.header_pipeline_badge.setStyleSheet(
            f"font-size:10px; font-weight:900; color:{fg}; "
            f"background:{bg}; border:1px solid {border}; border-radius:11px; "
            "padding:0 12px;"
        )

    @staticmethod
    def _pretty_history_line(raw_text):
        """Transforme une ligne technique en libellé plus lisible sans modifier la donnée source."""
        text = str(raw_text or "").strip()
        if not text:
            return ""

        replacements = {
            "task — Date de prochaine action modifiée :": "Date de prochaine action modifiée :",
            "note —": "Note :",
            "status —": "Statut :",
            "pipeline —": "Pipeline :",
            "commercial —": "Commercial :",
        }

        lowered = text.lower()
        for technical, friendly in replacements.items():
            idx = lowered.find(technical.lower())
            if idx != -1:
                before = text[:idx]
                after = text[idx + len(technical):].strip()
                return f"{before}{friendly} {after}".strip()

        return text

    @staticmethod
    def _history_badge_prefix(raw_text):
        text = str(raw_text or "").lower()
        if "note" in text:
            return "NOTE"
        if "date de prochaine action" in text or "task" in text:
            return "ACTION"
        if "pipeline" in text or "statut" in text:
            return "PIPELINE"
        return "ACTIVITÉ"

    def charger_prospect(self):
        prospect = self.prospect_service.recuperer_prospect_par_id(
            self.database_path,
            self.prospect_id
        )

        if not prospect:
            QMessageBox.critical(self, "Erreur", "Prospect introuvable.")
            self.reject()
            return

        # Le provider local historique retourne 27 colonnes.
        # Le provider Cloud ajoute X/Twitter et les autres URL sociales.
        if len(prospect) == 27:
            prospect = tuple(prospect[:15]) + ("", "") + tuple(prospect[15:])

        (
            prospect_id,
            entreprise,
            siret,
            siren,
            adresse,
            code_postal,
            ville,
            code_naf,
            telephone,
            site_web,
            email,
            facebook,
            linkedin,
            instagram,
            social_a,
            social_b,
            social_other_urls,
            statut_enrichissement,
            date_collecte,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
            score_prospect,
            score_grade,
            score_label,
            score_details,
            date_score,
        ) = prospect

        # Compatibilité ancien provider local / provider Cloud : l'ordre
        # Twitter-YouTube a varié. On détecte les domaines au lieu de supposer.
        social_a_text = str(social_a or "")
        social_b_text = str(social_b or "")
        a_low = social_a_text.lower()
        b_low = social_b_text.lower()
        if ("youtube.com" in a_low or "youtu.be" in a_low) and ("twitter.com" in b_low or "x.com" in b_low):
            youtube, twitter = social_a_text, social_b_text
        elif ("twitter.com" in a_low or "x.com" in a_low) and ("youtube.com" in b_low or "youtu.be" in b_low):
            twitter, youtube = social_a_text, social_b_text
        elif "youtube.com" in a_low or "youtu.be" in a_low:
            youtube, twitter = social_a_text, social_b_text
        else:
            twitter, youtube = social_a_text, social_b_text

        pipeline_final = pipeline if pipeline in PIPELINE else PIPELINE_DEFAULT
        priorite_finale = priorite if priorite in PRIORITES else PRIORITE_DEFAULT
        action_finale = prochaine_action if prochaine_action in ACTIONS else ACTION_DEFAULT
        date_action_finale = str(date_prochaine_action or "")
        commercial_final = str(commercial_assigne or "")

        self.ancien_pipeline = pipeline_final
        self.ancienne_priorite = priorite_finale
        self.ancienne_action = action_finale
        self.ancienne_date_action = date_action_finale
        self.ancien_commercial = commercial_final

        self.entreprise_input.setText(str(entreprise or ""))
        self.siret_input.setText(str(siret or ""))
        self.titre.setText(str(entreprise or "Fiche prospect"))
        self.header_subtitle.setText(
            f"{str(ville or 'Ville non renseignée')}  •  "
            f"{str(commercial_final or 'Commercial non assigné')}"
        )
        self._refresh_header_badge(pipeline_final)

        self.ville_input.setText(str(ville or ""))
        self.cp_input.setText(str(code_postal or ""))
        self.telephone_input.setText(str(telephone or ""))

        mobile_value = ""
        try:
            mobile_value = self.prospect_service.recuperer_mobile(
                self.database_path,
                self.prospect_id,
            )
        except Exception:
            mobile_value = ""
        self.mobile_input.setText(str(mobile_value or ""))

        self.site_input.setText(str(site_web or ""))
        self.email_input.setText(str(email or ""))
        self.facebook_input.setText(str(facebook or ""))
        self.linkedin_input.setText(str(linkedin or ""))
        self.instagram_input.setText(str(instagram or ""))
        self.twitter_input.setText(str(twitter or ""))
        self.youtube_input.setText(str(youtube or ""))
        self.social_other_urls_input.setPlainText(
            str(social_other_urls or "")
        )
        pipeline_index = self.pipeline_input.findData(pipeline_final)
        if pipeline_index < 0:
            pipeline_index = self.pipeline_input.findText(pipeline_final)
        if pipeline_index < 0 and "nouveau" in str(pipeline_final).lower():
            for index in range(self.pipeline_input.count()):
                if "nouveau" in str(self.pipeline_input.itemData(index) or "").lower():
                    pipeline_index = index
                    break
        if pipeline_index >= 0:
            self.pipeline_input.setCurrentIndex(pipeline_index)
        self.priorite_input.setCurrentText(priorite_finale)
        self.prochaine_action_input.setCurrentText(action_finale)

        parsed_date = QDate()
        parsed_time = QTime(9, 0)
        raw_date = str(date_action_finale or "").strip()

        if raw_date:
            # Formats acceptés :
            # 2026-08-14
            # 2026-08-14 14:30
            # 2026-08-14T14:30:00
            # 14/08/2026
            # 14/08/2026 14:30
            date_part = raw_date[:10]
            parsed_date = QDate.fromString(date_part, "yyyy-MM-dd")
            if not parsed_date.isValid():
                parsed_date = QDate.fromString(date_part, "dd/MM/yyyy")

            time_text = ""
            if "T" in raw_date:
                time_text = raw_date.split("T", 1)[1][:5]
            elif len(raw_date) >= 16:
                time_text = raw_date[11:16]

            candidate_time = QTime.fromString(time_text, "HH:mm")
            if candidate_time.isValid():
                parsed_time = candidate_time

        if parsed_date.isValid():
            self.date_prochaine_action_input.set_date(parsed_date)
            self.date_prochaine_action_input.set_time(parsed_time)
        else:
            self.date_prochaine_action_input.clear_date()
            self.date_prochaine_action_input.set_time(QTime(9, 0))

        if self._can_assign_owner:
            normalized_owner = commercial_final.strip()
            if not normalized_owner or normalized_owner in {"Non assigné", "Non affecté"}:
                self.commercial_selector.setCurrentIndex(0)
            else:
                owner_index = self.commercial_selector.findText(normalized_owner)
                if owner_index < 0:
                    self.commercial_selector.addItem(normalized_owner, normalized_owner)
                    owner_index = self.commercial_selector.count() - 1
                self.commercial_selector.setCurrentIndex(owner_index)
        else:
            self.commercial_input.setText(commercial_final)
        self.score_input.setText(f"{score_grade or '★☆☆☆☆'}  —  {int(score_prospect or 0)}/100  —  {score_label or ''}")
        try:
            import json
            details = json.loads(score_details or "[]")
        except Exception:
            details = []
        self.score_details_input.setPlainText("\n".join(details) if details else "Score non calculé.")

    @staticmethod
    def _assignment_history_line(event):
        old_owner = str(event.get("old_owner_name") or "Non affecté").strip()
        new_owner = str(event.get("new_owner_name") or "Non affecté").strip()
        source = (
            "Landing Page"
            if str(event.get("source") or "").strip() == "landing"
            else "Réaffectation manuelle"
        )

        raw_date = str(event.get("occurred_at") or "").strip()
        date_text = raw_date.replace("T", " ")[:16]
        if len(date_text) >= 10 and date_text[4:5] == "-" and date_text[7:8] == "-":
            date_text = (
                f"{date_text[8:10]}/{date_text[5:7]}/{date_text[0:4]}"
                f"{date_text[10:]}"
            )

        details = [f"{old_owner} → {new_owner}", source]

        old_project = str(event.get("old_project_name") or "").strip()
        new_project = str(event.get("new_project_name") or "").strip()
        if old_project and new_project and old_project != new_project:
            details.append(f"Projet : {old_project} → {new_project}")
        elif new_project:
            details.append(f"Projet : {new_project}")

        actor = str(event.get("actor_name") or "").strip()
        if actor:
            details.append(f"Effectué par : {actor}")

        prefix = f"{date_text} — " if date_text else ""
        return f"{prefix}AFFECTATION — " + " • ".join(details)

    def charger_notes(self):
        self.notes_liste.clear()
        notes = self.note_service.get_notes(self.database_path, self.prospect_id)

        if not notes:
            self.notes_liste.addItem("Aucune note pour ce prospect.")
            return

        for note in notes:
            note_id, date_creation, contenu = note
            self.notes_liste.addItem(f"{date_creation} — {contenu}")

    def charger_activities(self):
        self.activities_liste.clear()
        activities = self.activity_service.get_activities(self.database_path, self.prospect_id)
        assignment_history = []

        if self._is_cloud_mode and CloudRuntime.is_active():
            try:
                assignment_history = (
                    CloudRuntime.api().list_prospect_assignment_history(
                        str(self.prospect_id)
                    )
                )
            except Exception:
                assignment_history = []

        if not activities and not assignment_history:
            self.activities_liste.addItem("Aucune action enregistrée.")
            return

        for event in assignment_history:
            self.activities_liste.addItem(
                self._assignment_history_line(event)
            )

        for activity in activities:
            activity_id, date_creation, type_action, description = activity
            self.activities_liste.addItem(f"{date_creation} — {type_action} — {description}")

    def ajouter_note(self):
        contenu = self.note_input.toPlainText().strip()

        if not contenu:
            QMessageBox.warning(self, "Attention", "La note est vide.")
            return

        try:
            self.note_service.add_note(self.database_path, self.prospect_id, contenu)

            self.activity_service.add_activity(
                self.database_path,
                self.prospect_id,
                "Note",
                "Nouvelle note ajoutée"
            )

            if not self._is_cloud_mode:
                ScoringService.score_prospect(
                self.database_path,
                self.prospect_id,
                )
            self.note_input.clear()
            self.charger_notes()
            self.charger_activities()
            self.charger_prospect()

            QMessageBox.information(self, "Note ajoutée", "La note a été ajoutée.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def enregistrer(self):
        try:
            nouveau_pipeline = (
                self.pipeline_input.currentData()
                or self.pipeline_input.currentText()
            )
            nouvelle_priorite = self.priorite_input.currentText()
            nouvelle_action = self.prochaine_action_input.currentText()

            selected_date = self.date_prochaine_action_input.date()
            selected_time = self.date_prochaine_action_input.time()

            if not self.date_prochaine_action_input.has_date():
                nouvelle_date_action = ""
            else:
                # Format stable pour stockage / tri chronologique / agenda.
                nouvelle_date_action = (
                    f"{selected_date.toString('yyyy-MM-dd')} "
                    f"{selected_time.toString('HH:mm')}"
                )

            nouveau_commercial = (
                self.commercial_selector.currentData()
                if self._can_assign_owner
                else self.commercial_input.text().strip()
            )

            is_cloud = self._is_cloud_mode
            self.client_conversion_requested = (
                is_cloud
                and nouveau_pipeline == "🟢 Client"
                and self.ancien_pipeline != "🟢 Client"
            )

            # Le serveur Cloud bloque volontairement le passage direct au statut
            # Client tant que la fiche juridique n'est pas complète. On enregistre
            # donc d'abord les autres modifications avec l'ancien pipeline, puis
            # ProspectsPage ouvre le formulaire complet de finalisation.
            pipeline_a_enregistrer = (
                self.ancien_pipeline
                if self.client_conversion_requested
                else nouveau_pipeline
            )

            self.prospect_service.mettre_a_jour_contact(
                self.database_path,
                self.prospect_id,
                self.telephone_input.text().strip(),
                self.mobile_input.text().strip(),
                self.site_input.text().strip(),
                self.email_input.text().strip(),
                self.facebook_input.text().strip(),
                self.linkedin_input.text().strip(),
                self.instagram_input.text().strip(),
                self.youtube_input.text().strip(),
                pipeline_a_enregistrer,
                nouvelle_priorite,
                nouvelle_action,
                nouvelle_date_action,
                nouveau_commercial,
            )

            if self._is_cloud_mode and CloudRuntime.is_active():
                CloudRuntime.api().update_prospect(
                    str(self.prospect_id),
                    {
                        "twitter": self.twitter_input.text().strip(),
                        "social_other_urls": (
                            self.social_other_urls_input.toPlainText().strip()
                        ),
                    },
                )

            modifications = []

            if (
                nouveau_pipeline != self.ancien_pipeline
                and not self.client_conversion_requested
            ):
                modifications.append((
                    "Pipeline",
                    f"Pipeline modifié : {self.ancien_pipeline} → {nouveau_pipeline}"
                ))

            if nouvelle_priorite != self.ancienne_priorite:
                modifications.append((
                    "Priorité",
                    f"Priorité modifiée : {self.ancienne_priorite} → {nouvelle_priorite}"
                ))

            if nouvelle_action != self.ancienne_action:
                modifications.append((
                    "Prochaine action",
                    f"Prochaine action modifiée : {self.ancienne_action} → {nouvelle_action}"
                ))

            if nouvelle_date_action != self.ancienne_date_action:
                ancienne_date = self.ancienne_date_action or "Aucune"
                nouvelle_date = nouvelle_date_action or "Aucune"
                modifications.append((
                    "Date action",
                    f"Date de prochaine action modifiée : {ancienne_date} → {nouvelle_date}"
                ))

            if (
                not self._is_cloud_mode
                and nouveau_commercial != self.ancien_commercial
            ):
                ancien_commercial = self.ancien_commercial or "Aucun"
                commercial = nouveau_commercial or "Aucun"
                modifications.append((
                    "Commercial",
                    f"Commercial assigné modifié : {ancien_commercial} → {commercial}"
                ))

            if not modifications:
                modifications.append((
                    "Modification",
                    "Informations du prospect mises à jour"
                ))

            for type_action, description in modifications:
                self.activity_service.add_activity(
                    self.database_path,
                    self.prospect_id,
                    type_action,
                    description
                )

            if not self._is_cloud_mode:
                ScoringService.score_prospect(
                self.database_path,
                self.prospect_id,
                )
            self.charger_activities()

            if self.client_conversion_requested:
                # La page CRM enchaîne immédiatement avec le formulaire juridique.
                self.accept()
                return

            message = (
                "Prospect mis à jour dans le Cloud."
                if self._is_cloud_mode
                else "Prospect mis à jour et score V2 recalculé."
                )

            QMessageBox.information(
                self,
                "Succès",
                message
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
