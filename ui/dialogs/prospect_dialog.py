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

        # Le dialogue connaît maintenant explicitement sa source de données.
        # On transmet cette information au service de notes afin qu'une fiche
        # Prospect Cloud puisse être ouverte depuis la vue globale Admin même
        # lorsqu'aucun projet/workspace n'est actuellement ouvert.
        self.note_service = NoteService(
            resolver=self.datasource,
            is_cloud_mode=self._is_cloud_mode,
        )
        self.activity_service = ActivityService(
            resolver=self.datasource,
            is_cloud_mode=self._is_cloud_mode,
        )

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

        self.setWindowTitle("Fiche prospect")
        self.resize(980, 860)
        self.setMinimumSize(820, 640)
        self.setStyleSheet("background:#F5F8FC;")

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # -------------------------
        # Header premium fixe
        # -------------------------
        header = QFrame()
        header.setObjectName("ProspectHeader")
        header.setStyleSheet("""
            QFrame#ProspectHeader {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:0.72 #F7FBFF,
                    stop:1 #EAF4FF
                );
                border: none;
                border-bottom: 1px solid #E4EBF4;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 22, 28, 20)
        header_layout.setSpacing(16)

        header_texts = QVBoxLayout()
        header_texts.setSpacing(3)

        eyebrow = QLabel("CRM  •  FICHE PROSPECT")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.1px; "
            "color:#338CE4; background:transparent; border:none;"
        )

        self.titre = QLabel("Fiche prospect")
        self.titre.setStyleSheet(
            "font-size:28px; font-weight:900; color:#0B1220; "
            "background:transparent; border:none;"
        )

        self.header_subtitle = QLabel("Coordonnées, suivi commercial, scoring et historique.")
        self.header_subtitle.setStyleSheet(
            "font-size:12px; color:#6B7A90; background:transparent; border:none;"
        )

        header_texts.addWidget(eyebrow)
        header_texts.addWidget(self.titre)
        header_texts.addWidget(self.header_subtitle)

        self.header_pipeline_badge = QLabel("PROSPECT")
        self.header_pipeline_badge.setAlignment(Qt.AlignCenter)
        self.header_pipeline_badge.setMinimumWidth(110)
        self.header_pipeline_badge.setFixedHeight(32)
        self.header_pipeline_badge.setStyleSheet(
            "font-size:10px; font-weight:900; color:#075985; "
            "background:#EFF8FF; border:1px solid #BAE6FD; border-radius:11px; "
            "padding:0 12px;"
        )

        header_layout.addLayout(header_texts, 1)
        header_layout.addWidget(self.header_pipeline_badge, 0, Qt.AlignTop)

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
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # -------------------------
        # Widgets / champs
        # -------------------------
        self.entreprise_input = QLineEdit()
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
        self.pipeline_input.addItems(PIPELINE)
        self.pipeline_input.currentTextChanged.connect(self._refresh_header_badge)

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

        self.score_input = QLineEdit()
        self.score_input.setReadOnly(True)

        self.score_details_input = QTextEdit()
        self.score_details_input.setReadOnly(True)
        self.score_details_input.setFixedHeight(92)

        self.entreprise_input.setReadOnly(True)
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

        identity_grid.addWidget(self._field_block("Entreprise", self.entreprise_input), 0, 0, 1, 2)
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
        sales_grid.addWidget(self._field_block("Commercial assigné", self.commercial_input), 2, 0, 1, 2)
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
        self.notes_liste.setFixedHeight(138)
        self.notes_liste.setToolTip(
            "Historique des notes saisies manuellement sur ce prospect."
        )
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Ajouter une nouvelle note...")
        self.note_input.setFixedHeight(82)

        bouton_ajouter_note = QPushButton("Ajouter la note")
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
        self.activities_liste.setFixedHeight(170)
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
        footer.setObjectName("ProspectFooter")
        footer.setStyleSheet("""
            QFrame#ProspectFooter {
                background:#FFFFFF;
                border:none;
                border-top:1px solid #E4EBF4;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 14, 24, 14)
        footer_layout.setSpacing(10)

        cancel_button = QPushButton("Fermer")
        cancel_button.setFixedHeight(42)
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet(self._secondary_action_style())

        self.bouton_enregistrer = QPushButton("Enregistrer les modifications")
        self.bouton_enregistrer.setFixedHeight(42)
        self.bouton_enregistrer.clicked.connect(self.enregistrer)
        self.bouton_enregistrer.setStyleSheet(self._primary_action_style())

        footer_layout.addStretch()
        footer_layout.addWidget(cancel_button)
        footer_layout.addWidget(self.bouton_enregistrer)

        page_layout.addWidget(header)
        page_layout.addWidget(self.scroll_area, 1)
        page_layout.addWidget(footer)

        self.charger_prospect()
        self.charger_notes()
        self.charger_activities()

    @staticmethod
    def _section_card(title, subtitle):
        card = QFrame()
        card.setObjectName("ProspectSection")
        card.setStyleSheet("""
            QFrame#ProspectSection {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 20)
        card_layout.setSpacing(12)

        eyebrow = QLabel(title)
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1px; "
            "color:#338CE4; background:transparent; border:none;"
        )
        description = QLabel(subtitle)
        description.setWordWrap(True)
        description.setStyleSheet(
            "font-size:11px; color:#7A899C; background:transparent; border:none;"
        )

        card_layout.addWidget(eyebrow)
        card_layout.addWidget(description)
        return card

    @staticmethod
    def _field_block(label_text, field):
        block = QWidget()
        block.setStyleSheet("background:transparent;")
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet(
            "font-size:11px; font-weight:800; color:#53657C; "
            "background:transparent; border:none;"
        )

        block_layout.addWidget(label)
        block_layout.addWidget(field)
        return block

    def _apply_field_styles(self):
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
            self.date_prochaine_action_input,
            self.commercial_input,
        ]
        readonly = [
            self.entreprise_input,
            self.ville_input,
            self.cp_input,
        ]
        combos = [
            self.pipeline_input,
            self.priorite_input,
            self.prochaine_action_input,
        ]

        normal_style = """
            QLineEdit, QTextEdit {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:8px 10px;
                font-size:12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border:2px solid #338CE4;
                background:#FFFFFF;
            }
        """

        readonly_style = """
            QLineEdit {
                background:#F8FAFC;
                color:#475569;
                border:1px solid #E2E8F0;
                border-radius:10px;
                padding:8px 10px;
                font-size:12px;
                font-weight:750;
            }
        """

        combo_style = """
            QComboBox {
                background:#FFFFFF;
                color:#172033;
                border:1px solid #DCE5EF;
                border-radius:10px;
                min-height:38px;
                padding:0 10px;
                font-size:12px;
                font-weight:750;
            }
            QComboBox:focus {
                border:2px solid #338CE4;
            }
            QComboBox::drop-down {
                border:none;
                width:28px;
            }
        """

        for widget in editable:
            widget.setMinimumHeight(40)
            widget.setStyleSheet(normal_style)

        for widget in readonly:
            widget.setMinimumHeight(40)
            widget.setStyleSheet(readonly_style)

        for widget in combos:
            widget.setMinimumHeight(40)
            widget.setStyleSheet(combo_style)

        self.social_other_urls_input.setStyleSheet(normal_style)

        self.score_input.setMinimumHeight(46)
        self.score_input.setStyleSheet("""
            QLineEdit {
                background:#F1F8FF;
                color:#075985;
                border:1px solid #CFE7FB;
                border-radius:11px;
                padding:8px 12px;
                font-size:13px;
                font-weight:900;
            }
        """)

        self.score_details_input.setStyleSheet("""
            QTextEdit {
                background:#F8FAFC;
                color:#53657C;
                border:1px solid #E2E8F0;
                border-radius:11px;
                padding:9px 10px;
                font-size:11px;
            }
        """)

        list_style = """
            QListWidget {
                background:#FBFDFF;
                color:#334155;
                border:1px solid #E2E8F0;
                border-radius:12px;
                padding:7px;
                font-size:11px;
                outline:0;
            }
            QListWidget::item {
                padding:9px 10px;
                margin:2px 0;
                border:none;
                border-bottom:1px solid #EEF2F6;
            }
            QListWidget::item:selected {
                background:#EAF4FF;
                color:#0B1220;
                border-radius:8px;
            }
        """

        self.notes_liste.setStyleSheet(list_style)
        self.note_input.setStyleSheet(normal_style)
        self.activities_liste.setStyleSheet(list_style)

    @staticmethod
    def _primary_action_style():
        return """
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 18px;
                font-size:12px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:pressed { background:#1D66B2; }
        """

    @staticmethod
    def _secondary_action_style():
        return """
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 16px;
                font-size:12px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """

    def _refresh_header_badge(self, pipeline_text):
        labels = {
            "🟢 Nouveau": ("NOUVEAU", "#ECFDF3", "#166534", "#BBF7D0"),
            "🟡 Qualification": ("QUALIFICATION", "#FFFBEB", "#854D0E", "#FDE68A"),
            "🔵 RDV programmé": ("RDV PROGRAMMÉ", "#EFF8FF", "#075985", "#BAE6FD"),
            "🟣 Proposition envoyée": ("PROPOSITION", "#FAF5FF", "#6B21A8", "#E9D5FF"),
            "🟠 Négociation": ("NÉGOCIATION", "#FFF7ED", "#9A3412", "#FED7AA"),
            "🟢 Client": ("CLIENT", "#ECFDF3", "#166534", "#86EFAC"),
            "🔴 Perdu": ("PERDU", "#FEF2F2", "#991B1B", "#FECACA"),
        }
        label, bg, fg, border = labels.get(
            pipeline_text,
            ("PROSPECT", "#EFF8FF", "#075985", "#BAE6FD")
        )
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
        if self._is_cloud_mode and CloudRuntime.is_active():
            try:
                cloud_record = CloudRuntime.api().get_prospect(str(self.prospect_id))
                mobile_value = str(cloud_record.get("mobile") or "")
            except Exception:
                mobile_value = ""
        self.mobile_input.setText(mobile_value)

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
        self.pipeline_input.setCurrentText(pipeline_final)
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

        self.commercial_input.setText(commercial_final)
        self.score_input.setText(f"{score_grade or '★☆☆☆☆'}  —  {int(score_prospect or 0)}/100  —  {score_label or ''}")
        try:
            import json
            details = json.loads(score_details or "[]")
        except Exception:
            details = []
        self.score_details_input.setPlainText("\n".join(details) if details else "Score non calculé.")

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

        if not activities:
            self.activities_liste.addItem("Aucune action enregistrée.")
            return

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
            nouveau_pipeline = self.pipeline_input.currentText()
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

            nouveau_commercial = self.commercial_input.text().strip()

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
                        "mobile": self.mobile_input.text().strip(),
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

            if nouveau_commercial != self.ancien_commercial:
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
