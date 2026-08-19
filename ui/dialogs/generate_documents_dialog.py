from __future__ import annotations

import math
import re
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    NAVY,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from services.cloud_api_client import CloudAPIError
from services.document_generator_service import DocumentGeneratorService


class GenerateDocumentsDialog(QDialog):
    """Assistant historique de génération pour les projets SQLite locaux."""

    def __init__(self, service: DocumentGeneratorService, parent=None):
        super().__init__(parent)
        self.service = service
        self.sessions = service.list_sessions()
        self.last_folder: Path | None = None
        self.setWindowTitle("Générer les documents")
        self.resize(720, 620)
        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("Document Engine V1.0")
        title.setStyleSheet(f"color:{TEXT}; font-size:24px; font-weight:900;")
        subtitle = QLabel(
            "Les documents sont fusionnés à partir de vos modèles Word "
            "officiels, sans reconstruction de la mise en page."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title)
        root.addWidget(subtitle)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self._refresh_summary)
        form.addRow("Dossier / session", self.session_combo)
        root.addWidget(card)

        types_card = QFrame()
        types_card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        types_layout = QVBoxLayout(types_card)
        types_layout.setContentsMargins(18, 16, 18, 16)
        types_layout.addWidget(QLabel("Documents à générer"))
        checks = QHBoxLayout()
        self.type_checks = {}
        for doc_type in self.service.UI_TYPES:
            check = QCheckBox(doc_type)
            check.setChecked(True)
            check.setEnabled(False)
            check.setToolTip(
                "Le dossier complet contient automatiquement Convention, "
                "Programme et Convocation."
            )
            self.type_checks[doc_type] = check
            checks.addWidget(check)
        checks.addStretch()
        types_layout.addLayout(checks)
        self.pdf_check = QCheckBox(
            "Créer également les PDF lorsque Word ou LibreOffice est disponible"
        )
        self.pdf_check.setChecked(True)
        types_layout.addWidget(self.pdf_check)
        root.addWidget(types_card)

        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(170)
        self.summary.setStyleSheet(
            f"background:#F8FAFC; color:{NAVY}; border:1px solid {BORDER}; "
            "border-radius:10px; padding:10px;"
        )
        root.addWidget(self.summary, 1)
        self.preflight_label = QLabel("")
        self.preflight_label.setWordWrap(True)
        root.addWidget(self.preflight_label)

        actions = QHBoxLayout()
        self.open_button = QPushButton("Ouvrir le dossier")
        self.open_button.setStyleSheet(SECONDARY_BUTTON)
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_folder)
        actions.addWidget(self.open_button)
        actions.addStretch()
        cancel = QPushButton("Fermer")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        generate = QPushButton("Générer maintenant")
        generate.setStyleSheet(PRIMARY_BUTTON)
        generate.clicked.connect(self._generate)
        actions.addWidget(cancel)
        actions.addWidget(generate)
        root.addLayout(actions)

    def _load_sessions(self):
        self.session_combo.clear()
        for session in self.sessions:
            label = (
                f"{session['company_name']} — {session['training_name']} — "
                f"{session['start_date']}"
            )
            self.session_combo.addItem(label, int(session["session_id"]))
        if not self.sessions:
            self.session_combo.addItem("Aucune session client disponible", None)
            self.summary.setPlainText(
                "Transformez d’abord un prospect en client depuis la page Prospects."
            )
        else:
            self._refresh_summary()

    def _refresh_summary(self):
        index = self.session_combo.currentIndex()
        if index < 0 or index >= len(self.sessions):
            return
        session = self.sessions[index]
        selected = [
            name
            for name, check in self.type_checks.items()
            if check.isChecked()
        ]
        preflight = self.service.preflight(
            int(session["session_id"]),
            selected,
        )
        templates = "\n".join(
            f"• {kind} : {name}"
            for kind, name in preflight.templates.items()
        ) or "• Aucun document sélectionné"
        self.summary.setPlainText(
            (
                f"CLIENT\n{session['company_name']}\n"
                f"{session.get('siret') or 'SIRET non renseigné'}\n\n"
                f"FORMATION\n{session['training_name']} "
                f"({session['duration_hours']:g} h)\n"
                f"Du {session['start_date']} au {session['end_date']} — "
                f"{session['daily_schedule']}\n"
                f"Modalité : {session['modality']}\n"
                f"Formateur : {session.get('trainer_name') or 'Non renseigné'}\n"
                f"Financeur : {session.get('funder') or 'Entreprise'}\n"
                f"Prix : {session['price_cents']/100:,.2f} €\n\n"
                f"MODÈLES UTILISÉS\n{templates}"
            ).replace(",", " ")
        )
        if preflight.errors:
            self.preflight_label.setText(
                "⛔ À corriger avant génération :\n• "
                + "\n• ".join(preflight.errors)
            )
            self.preflight_label.setStyleSheet(
                "color:#B42318; background:#FEF3F2; border:1px solid #FDA29B; "
                "border-radius:8px; padding:9px;"
            )
        elif preflight.warnings:
            self.preflight_label.setText(
                "⚠ Vérifications :\n• "
                + "\n• ".join(preflight.warnings)
            )
            self.preflight_label.setStyleSheet(
                "color:#92400E; background:#FFFBEB; border:1px solid #FDE68A; "
                "border-radius:8px; padding:9px;"
            )
        else:
            self.preflight_label.setText(
                "✓ Dossier complet : la génération peut démarrer."
            )
            self.preflight_label.setStyleSheet(
                "color:#067647; background:#ECFDF3; border:1px solid #ABEFC6; "
                "border-radius:8px; padding:9px;"
            )

    def _generate(self):
        session_id = self.session_combo.currentData()
        if session_id is None:
            QMessageBox.information(
                self,
                "Génération",
                "Aucune session client n’est disponible.",
            )
            return
        selected = [
            name
            for name, check in self.type_checks.items()
            if check.isChecked()
        ]
        preflight = self.service.preflight(int(session_id), selected)
        if preflight.errors:
            QMessageBox.warning(
                self,
                "Dossier incomplet",
                "Corrigez les éléments suivants :\n\n• "
                + "\n• ".join(preflight.errors),
            )
            return
        if preflight.warnings:
            answer = QMessageBox.question(
                self,
                "Vérifications avant génération",
                "Les documents peuvent être générés, mais certains éléments "
                "sont à vérifier :\n\n• "
                + "\n• ".join(preflight.warnings)
                + "\n\nContinuer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            results = self.service.generate(
                session_id=int(session_id),
                document_types=selected,
                generate_pdf=self.pdf_check.isChecked(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Génération impossible", str(exc))
            return
        self.last_folder = results[0].docx_path.parent.parent if results else None
        self.open_button.setEnabled(bool(self.last_folder))
        pdf_count = sum(1 for item in results if item.pdf_path)
        lines = []
        for item in results:
            status_label = "DOCX + PDF" if item.pdf_path else "DOCX"
            line = (
                f"• {item.document_type} {item.document_number} — "
                f"{status_label} — {item.template_name}"
            )
            if item.warning:
                line += f"\n  ⚠ {item.warning}"
            lines.append(line)
        QMessageBox.information(
            self,
            "Documents générés",
            f"{len(results)} document(s) DOCX généré(s) et vérifié(s).\n"
            f"{pdf_count} PDF créé(s).\n\n"
            + "\n".join(lines)
            + "\n\nLes fichiers ont été classés dans le dossier du client.",
        )
        self.accept()

    def _open_folder(self):
        if self.last_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_folder)))


class CloudGenerateDocumentsDialog(QDialog):
    """Option A: le commercial prépare la session puis génère les documents."""

    DOCUMENT_TYPES = ("Convention", "Programme", "Convocation")

    def __init__(
        self,
        api,
        parent=None,
        *,
        initial_prospect_id: str | None = None,
    ):
        super().__init__(parent)
        self.api = api
        self.initial_prospect_id = initial_prospect_id
        self.prospects: list[dict] = []
        self.trainings: list[dict] = []
        self.trainers: list[dict] = []
        self.generated_documents: list[dict] = []
        self.generated_prospect_id: str | None = None
        self.generated_client_name: str = ""
        self.setWindowTitle("Générer les documents Cloud")
        self.resize(900, 800)
        self.setMinimumSize(820, 700)
        self._build_ui()
        self._load_cloud_data()

    @staticmethod
    def _field() -> QLineEdit:
        widget = QLineEdit()
        widget.setMinimumHeight(34)
        return widget

    @staticmethod
    def _configure_date_editor(editor: QDateEdit) -> None:
        """Rend le mois et l'année lisibles dans le calendrier déroulant."""
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("dd/MM/yyyy")
        editor.setMinimumHeight(34)

        calendar = editor.calendarWidget()
        if calendar is None:
            return

        calendar.setNavigationBarVisible(True)
        calendar.setMinimumWidth(300)
        calendar.setStyleSheet(
            """
            QCalendarWidget {
                background: #FFFFFF;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background: #F8FAFC;
                border-bottom: 1px solid #D9E2EC;
            }
            QCalendarWidget QToolButton {
                color: #10233C;
                background: transparent;
                border: none;
                font-weight: 800;
                padding: 5px 8px;
            }
            QCalendarWidget QToolButton:hover {
                background: #EAF3FC;
                border-radius: 5px;
            }
            QCalendarWidget QToolButton#qt_calendar_monthbutton {
                min-width: 95px;
            }
            QCalendarWidget QToolButton#qt_calendar_yearbutton {
                min-width: 55px;
            }
            QCalendarWidget QSpinBox {
                color: #10233C;
                background: #FFFFFF;
                selection-background-color: #338CE4;
                selection-color: #FFFFFF;
            }
            QCalendarWidget QMenu {
                color: #10233C;
                background: #FFFFFF;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #10233C;
                background: #FFFFFF;
                selection-background-color: #338CE4;
                selection-color: #FFFFFF;
                outline: none;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #94A3B8;
            }
            """
        )

    def _build_ui(self) -> None:
        self.setStyleSheet("QDialog{background:#F5F8FC;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --------------------------------------------------------------
        # Header premium
        # --------------------------------------------------------------
        header = QFrame()
        header.setObjectName("CloudDocumentsHeader")
        header.setStyleSheet(
            "QFrame#CloudDocumentsHeader{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #FFFFFF, stop:0.72 #F8FBFF, stop:1 #EAF4FF);"
            "border:none;"
            "border-bottom:1px solid #E4EBF4;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(26, 20, 26, 18)
        header_layout.setSpacing(4)

        eyebrow = QLabel("DOCUMENTS  •  PRÉPARATION DE SESSION")
        eyebrow.setStyleSheet(
            "color:#338CE4;font-size:10px;font-weight:900;letter-spacing:1.1px;"
        )

        title = QLabel("Préparer la session de formation")
        title.setStyleSheet(
            "color:#0B1220;font-size:27px;font-weight:900;"
        )

        subtitle = QLabel(
            "Renseignez les informations opérationnelles de la session. "
            "Le tarif et les modèles documentaires restent verrouillés "
            "par l'administration."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#6B7A90;font-size:11px;")

        header_layout.addWidget(eyebrow)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        # --------------------------------------------------------------
        # Zone scrollable
        # --------------------------------------------------------------
        body = QWidget()
        body.setStyleSheet("background:#F5F8FC;")
        content = QVBoxLayout(body)
        content.setContentsMargins(24, 18, 24, 18)
        content.setSpacing(14)

        field_style = (
            "QLineEdit,QComboBox,QDateEdit,QSpinBox{"
            "background:#FFFFFF;color:#172033;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 10px;min-height:40px;"
            "font-size:11px;font-weight:700;"
            "}"
            "QLineEdit:focus,QComboBox:focus,QDateEdit:focus,QSpinBox:focus{"
            "border:2px solid #338CE4;"
            "}"
            "QComboBox::drop-down,QDateEdit::drop-down{"
            "border:none;border-left:1px solid #E6EDF5;width:28px;"
            "background:#F8FBFF;"
            "}"
        )

        def section_card(kicker: str, title_text: str, help_text: str = ""):
            card = QFrame()
            card.setObjectName("CloudSessionCard")
            card.setStyleSheet(
                "QFrame#CloudSessionCard{"
                "background:#FFFFFF;border:1px solid #E4EBF4;border-radius:18px;"
                "}"
                "QLabel{background:transparent;border:none;}"
            )
            box = QVBoxLayout(card)
            box.setContentsMargins(18, 15, 18, 17)
            box.setSpacing(9)

            kicker_label = QLabel(kicker)
            kicker_label.setStyleSheet(
                "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
            )
            section_title = QLabel(title_text)
            section_title.setStyleSheet(
                "color:#0B1220;font-size:16px;font-weight:900;"
            )
            box.addWidget(kicker_label)
            box.addWidget(section_title)

            if help_text:
                helper = QLabel(help_text)
                helper.setWordWrap(True)
                helper.setStyleSheet("color:#8492A6;font-size:9px;")
                box.addWidget(helper)

            return card, box

        def field_block(label_text: str, widget):
            block = QWidget()
            block.setStyleSheet("background:transparent;")
            box = QVBoxLayout(block)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(5)
            label = QLabel(label_text)
            label.setStyleSheet(
                "color:#53657C;font-size:10px;font-weight:850;"
                "background:transparent;border:none;"
            )
            box.addWidget(label)
            box.addWidget(widget)
            return block

        # --------------------------------------------------------------
        # 1. Client & formation
        # --------------------------------------------------------------
        selection_card, selection_box = section_card(
            "01  •  DOSSIER",
            "Client & formation",
            "Sélectionnez le bénéficiaire et la formation à rattacher au dossier.",
        )

        self.prospect_combo = QComboBox()
        self.prospect_combo.setStyleSheet(field_style)
        self.prospect_combo.currentIndexChanged.connect(self._refresh_summary)

        self.training_combo = QComboBox()
        self.training_combo.setStyleSheet(field_style)
        self.training_combo.currentIndexChanged.connect(self._training_changed)

        selection_box.addWidget(field_block("Prospect / client *", self.prospect_combo))
        selection_box.addWidget(field_block("Formation *", self.training_combo))
        content.addWidget(selection_card)

        # --------------------------------------------------------------
        # 2. Planification
        # --------------------------------------------------------------
        planning_card, planning_box = section_card(
            "02  •  PLANIFICATION",
            "Dates & organisation",
            "Les dates sont calculées selon la durée et les horaires renseignés.",
        )

        planning_grid = QGridLayout()
        planning_grid.setHorizontalSpacing(12)
        planning_grid.setVerticalSpacing(10)

        self.start_date = QDateEdit(QDate.currentDate())
        self._configure_date_editor(self.start_date)
        self.start_date.setStyleSheet(field_style)

        self.end_date = QDateEdit(QDate.currentDate())
        self._configure_date_editor(self.end_date)
        self.end_date.setStyleSheet(field_style)

        self.start_date.dateChanged.connect(self._dates_changed)
        self.end_date.dateChanged.connect(self._refresh_summary)

        planning_grid.addWidget(field_block("Date de début *", self.start_date), 0, 0)
        planning_grid.addWidget(field_block("Date de fin *", self.end_date), 0, 1)

        self.daily_schedule = self._field()
        self.daily_schedule.setStyleSheet(field_style)
        self.daily_schedule.setPlaceholderText("Ex. 9h00–12h00 / 13h00–17h00")
        self.daily_schedule.setText("9h00–12h00 / 13h00–15h00")
        self.daily_schedule.textChanged.connect(self._schedule_changed)
        planning_grid.addWidget(
            field_block("Horaires *", self.daily_schedule),
            1, 0, 1, 2,
        )

        self.schedule_validation = QLabel("")
        self.schedule_validation.setWordWrap(True)
        self.schedule_validation.setStyleSheet(
            "color:#64748B;font-size:10px;background:#F8FBFF;"
            "border:1px solid #E2ECF7;border-radius:9px;padding:8px 10px;"
        )
        planning_grid.addWidget(self.schedule_validation, 2, 0, 1, 2)

        self.modality = QComboBox()
        self.modality.addItem("À distance", "distance")
        self.modality.addItem("Présentiel", "presentiel")
        self.modality.addItem("Hybride", "hybride")
        self.modality.setStyleSheet(field_style)
        self.modality.currentIndexChanged.connect(self._refresh_summary)

        self.participant_count = QSpinBox()
        self.participant_count.setRange(1, 1000)
        self.participant_count.setValue(1)
        self.participant_count.setStyleSheet(field_style)
        self.participant_count.valueChanged.connect(self._refresh_summary)

        planning_grid.addWidget(field_block("Modalité *", self.modality), 3, 0)
        planning_grid.addWidget(
            field_block("Participants *", self.participant_count),
            3, 1,
        )

        planning_box.addLayout(planning_grid)
        content.addWidget(planning_card)

        # --------------------------------------------------------------
        # 3. Intervenant & financement
        # --------------------------------------------------------------
        logistics_card, logistics_box = section_card(
            "03  •  INTERVENANTS",
            "Formateur & financement",
            "Complétez les informations nécessaires aux documents administratifs.",
        )

        self.trainer_combo = QComboBox()
        self.trainer_combo.setStyleSheet(field_style)
        self.trainer_combo.currentIndexChanged.connect(self._trainer_changed)

        self.open_trainer_schedule = QPushButton("Ouvrir le planning")
        self.open_trainer_schedule.setMinimumHeight(40)
        self.open_trainer_schedule.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 14px;font-size:11px;font-weight:850;}"
            "QPushButton:hover{background:#F8FBFF;color:#338CE4;border-color:#AFCFF0;}"
            "QPushButton:disabled{background:#F8FAFC;color:#B6C0CC;}"
        )
        self.open_trainer_schedule.clicked.connect(
            self._open_selected_trainer_schedule
        )
        self.open_trainer_schedule.setEnabled(False)

        trainer_widget = QWidget()
        trainer_widget.setStyleSheet("background:transparent;")
        trainer_row = QHBoxLayout(trainer_widget)
        trainer_row.setContentsMargins(0, 0, 0, 0)
        trainer_row.setSpacing(8)
        trainer_row.addWidget(self.trainer_combo, 1)
        trainer_row.addWidget(self.open_trainer_schedule)

        logistics_box.addWidget(field_block("Formateur *", trainer_widget))

        logistics_grid = QGridLayout()
        logistics_grid.setHorizontalSpacing(12)
        logistics_grid.setVerticalSpacing(10)

        self.funder = QComboBox()
        for label in ("Entreprise", "FAFCEA", "CONSTRUCTYS", "Autre"):
            self.funder.addItem(label, label)
        self.funder.setStyleSheet(field_style)
        self.funder.currentIndexChanged.connect(self._funder_changed)

        self.funder_details = self._field()
        self.funder_details.setStyleSheet(field_style)
        self.funder_details.setPlaceholderText(
            "OPCO, FAFCEA, référence de dossier…"
        )

        logistics_grid.addWidget(field_block("Financeur *", self.funder), 0, 0)
        logistics_grid.addWidget(
            field_block("Détails financeur", self.funder_details),
            0, 1,
        )

        self.connection_link = self._field()
        self.connection_link.setStyleSheet(field_style)
        self.connection_link.setPlaceholderText(
            "Lien Google Meet ou adresse du lieu"
        )
        logistics_grid.addWidget(
            field_block("Connexion / lieu", self.connection_link),
            1, 0, 1, 2,
        )

        logistics_box.addLayout(logistics_grid)
        content.addWidget(logistics_card)

        # --------------------------------------------------------------
        # 4. Documents
        # --------------------------------------------------------------
        docs_card, docs_box = section_card(
            "04  •  DOCUMENTS",
            "Dossier à générer",
            "Les trois documents constituent le dossier administratif standard.",
        )

        checks = QHBoxLayout()
        checks.setSpacing(10)
        self.type_checks: dict[str, QCheckBox] = {}

        for document_type in self.DOCUMENT_TYPES:
            check = QCheckBox(document_type)
            check.setChecked(True)
            check.toggled.connect(self._refresh_summary)
            check.setStyleSheet(
                "QCheckBox{background:#F8FBFF;color:#334155;"
                "border:1px solid #DDE8F4;border-radius:9px;"
                "padding:8px 12px;font-size:10px;font-weight:850;spacing:7px;}"
                "QCheckBox:checked{background:#EAF4FF;color:#0B5EA8;"
                "border-color:#BFDDFC;}"
                "QCheckBox::indicator{width:15px;height:15px;}"
            )
            self.type_checks[document_type] = check
            checks.addWidget(check)

        checks.addStretch()
        docs_box.addLayout(checks)
        content.addWidget(docs_card)

        # --------------------------------------------------------------
        # 5. Aperçu
        # --------------------------------------------------------------
        summary_card, summary_box = section_card(
            "05  •  CONTRÔLE",
            "Aperçu du dossier",
            "Vérifiez les informations avant de lancer la génération.",
        )

        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(150)
        self.summary.setStyleSheet(
            "QPlainTextEdit{background:#F8FBFF;color:#0B2A52;"
            "border:1px solid #DCE8F4;border-radius:11px;"
            "padding:11px;font-size:10px;}"
        )
        summary_box.addWidget(self.summary)
        content.addWidget(summary_card)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color:#64748B;font-size:10px;background:transparent;"
        )
        content.addWidget(self.status_label)

        content.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:#F5F8FC;border:none;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#CBD5E1;min-height:36px;"
            "border-radius:5px;}"
            "QScrollBar::handle:vertical:hover{background:#94A3B8;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # --------------------------------------------------------------
        # Footer fixe
        # --------------------------------------------------------------
        footer = QFrame()
        footer.setObjectName("CloudSessionFooter")
        footer.setStyleSheet(
            "QFrame#CloudSessionFooter{background:#FFFFFF;border:none;"
            "border-top:1px solid #E4EBF4;}"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)
        footer_layout.setSpacing(10)

        cancel = QPushButton("Annuler")
        cancel.setMinimumHeight(40)
        cancel.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 16px;font-size:11px;font-weight:850;}"
            "QPushButton:hover{background:#F8FBFF;color:#338CE4;}"
        )
        cancel.clicked.connect(self.reject)

        self.generate_button = QPushButton(
            "Créer la session et générer le dossier complet"
        )
        self.generate_button.setMinimumHeight(40)
        self.generate_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 18px;font-size:11px;font-weight:900;}"
            "QPushButton:hover{background:#247BD0;}"
            "QPushButton:pressed{background:#1D66B2;}"
            "QPushButton:disabled{background:#DCE6F0;color:#94A3B8;}"
        )
        self.generate_button.clicked.connect(self._generate)

        footer_layout.addStretch()
        footer_layout.addWidget(cancel)
        footer_layout.addWidget(self.generate_button)
        root.addWidget(footer)

    def _load_cloud_data(self) -> None:
        try:
            self.prospects = self.api.list_prospects(
                include_archived=False,
                limit=500,
            ).items
            self.trainings = self.api.list_document_trainings(
                include_inactive=False
            )
            self.trainers = self.api.list_cloud_trainers(
                include_inactive=False
            )
        except CloudAPIError as exc:
            self.generate_button.setEnabled(False)
            self.status_label.setText(f"⛔ {exc}")
            self.status_label.setStyleSheet("color:#B42318;")
            return

        self.prospect_combo.clear()
        selected_index = -1
        for index, prospect in enumerate(self.prospects):
            company = str(prospect.get("company_name") or "Prospect sans nom")
            contact = str(prospect.get("contact_name") or "").strip()
            label = company if not contact else f"{company} — {contact}"
            prospect_id = str(prospect.get("id") or "")
            self.prospect_combo.addItem(label, prospect_id)
            if prospect_id == self.initial_prospect_id:
                selected_index = index
        if selected_index >= 0:
            self.prospect_combo.setCurrentIndex(selected_index)

        self.trainer_combo.clear()
        for trainer in self.trainers:
            trainer_id = str(trainer.get("id") or "").strip()
            if not trainer_id:
                continue
            full_name = str(
                trainer.get("full_name")
                or (
                    f"{trainer.get('first_name') or ''} "
                    f"{trainer.get('last_name') or ''}"
                ).strip()
                or trainer.get("email")
                or "Formateur"
            ).strip()
            specialties = str(
                trainer.get("specialties") or ""
            ).strip()
            label = (
                f"{full_name} — {specialties}"
                if specialties
                else full_name
            )
            self.trainer_combo.addItem(
                label,
                {
                    "id": trainer_id,
                    "name": full_name,
                    "availability_url": str(
                        trainer.get("availability_url") or ""
                    ).strip(),
                },
            )

        self.training_combo.clear()
        for training in self.trainings:
            price = self._format_price(training.get("price_cents", 0))
            duration = self._safe_float(training.get("duration_hours", 0))
            self.training_combo.addItem(
                f"{training.get('reference', '')} — {training.get('name', '')} "
                f"— {duration:g} h — {price}",
                str(training.get("id") or ""),
            )

        if not self.prospects:
            self.status_label.setText(
                "⛔ Aucun prospect visible n'est disponible pour la génération."
            )
            self.status_label.setStyleSheet("color:#B42318;")
            self.generate_button.setEnabled(False)
        elif not self.trainings:
            self.status_label.setText(
                "⛔ Aucune formation Cloud active. L'administrateur doit d'abord "
                "créer une formation dans la page Documents."
            )
            self.status_label.setStyleSheet("color:#B42318;")
            self.generate_button.setEnabled(False)
        elif self.trainer_combo.count() == 0:
            self.status_label.setText(
                "⛔ Aucun formateur actif n'est disponible dans l'annuaire. "
                "L'administrateur doit d'abord activer un formateur."
            )
            self.status_label.setStyleSheet("color:#B42318;")
            self.generate_button.setEnabled(False)
        else:
            self.status_label.setText(
                "✓ Le tarif sera repris automatiquement depuis le catalogue Cloud."
            )
            self.status_label.setStyleSheet("color:#067647;")
            self.generate_button.setEnabled(True)
            self._funder_changed()
            self._trainer_changed()
            self._training_changed()

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _format_price(cents) -> str:
        try:
            value = int(cents or 0) / 100
        except (TypeError, ValueError):
            value = 0
        return f"{value:,.2f} €".replace(",", " ").replace(".00", "")

    def _selected_training(self) -> dict | None:
        index = self.training_combo.currentIndex()
        if 0 <= index < len(self.trainings):
            return self.trainings[index]
        return None

    def _selected_prospect(self) -> dict | None:
        index = self.prospect_combo.currentIndex()
        if 0 <= index < len(self.prospects):
            return self.prospects[index]
        return None

    @staticmethod
    def _time_to_minutes(hour_text: str, minute_text: str | None) -> int:
        hour = int(hour_text)
        minute = int(minute_text or 0)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Horaire invalide.")
        return hour * 60 + minute

    def _daily_duration_hours(self) -> float:
        text = self.daily_schedule.text().strip().lower()
        if not text:
            return 0.0

        # Accepte 9h, 9h00, 09:00, tiret simple ou typographique.
        matches = re.findall(
            r"(\d{1,2})(?:h|:)(\d{0,2})",
            text,
        )
        if len(matches) < 2 or len(matches) % 2:
            return 0.0

        total_minutes = 0
        for index in range(0, len(matches), 2):
            start = self._time_to_minutes(*matches[index])
            end = self._time_to_minutes(*matches[index + 1])
            if end <= start:
                return 0.0
            total_minutes += end - start

        return total_minutes / 60.0

    @staticmethod
    def _add_training_days(start: QDate, training_days: int) -> QDate:
        if training_days <= 1:
            return start

        current = QDate(start)
        counted = 1
        while counted < training_days:
            current = current.addDays(1)
            # Qt: Monday=1 ... Sunday=7.
            if current.dayOfWeek() <= 5:
                counted += 1
        return current

    @staticmethod
    def _business_days_inclusive(start: QDate, end: QDate) -> int:
        if end < start:
            return 0
        current = QDate(start)
        count = 0
        while current <= end:
            if current.dayOfWeek() <= 5:
                count += 1
            current = current.addDays(1)
        return count

    def _recalculate_end_date(self) -> None:
        training = self._selected_training()
        duration = self._safe_float(
            (training or {}).get("duration_hours")
        )
        daily_hours = self._daily_duration_hours()

        if duration <= 0 or daily_hours <= 0:
            self.schedule_validation.setText(
                "⚠ Renseignez un horaire valide pour calculer automatiquement "
                "la date de fin."
            )
            self.schedule_validation.setStyleSheet("color:#B54708;")
            return

        days = max(1, math.ceil(duration / daily_hours))
        calculated_end = self._add_training_days(
            self.start_date.date(),
            days,
        )
        self.end_date.blockSignals(True)
        self.end_date.setDate(calculated_end)
        self.end_date.blockSignals(False)

        scheduled_hours = days * daily_hours
        if abs(scheduled_hours - duration) <= 0.05:
            self.schedule_validation.setText(
                f"✓ {duration:g} h réparties sur {days} jour(s) ouvré(s) "
                f"à {daily_hours:g} h/jour. Fin calculée : "
                f"{calculated_end.toString('dd/MM/yyyy')}."
            )
            self.schedule_validation.setStyleSheet("color:#067647;")
        else:
            self.schedule_validation.setText(
                f"⚠ La plage horaire représente {scheduled_hours:g} h sur "
                f"{days} jour(s), alors que la formation dure {duration:g} h. "
                "Vous serez averti avant la génération."
            )
            self.schedule_validation.setStyleSheet("color:#B54708;")

    def _schedule_changed(self) -> None:
        self._recalculate_end_date()
        self._refresh_summary()

    def _trainer_changed(self) -> None:
        data = self.trainer_combo.currentData()
        availability_url = ""
        if isinstance(data, dict):
            availability_url = str(
                data.get("availability_url") or ""
            ).strip()

        self.open_trainer_schedule.setEnabled(bool(availability_url))
        self.open_trainer_schedule.setToolTip(
            availability_url
            if availability_url
            else "Aucun lien de disponibilités renseigné pour ce formateur."
        )
        self._refresh_summary()

    def _open_selected_trainer_schedule(self) -> None:
        data = self.trainer_combo.currentData()
        if not isinstance(data, dict):
            return
        url = str(data.get("availability_url") or "").strip()
        if not url:
            QMessageBox.information(
                self,
                "Planning formateur",
                "Aucun lien de planning n'est renseigné pour ce formateur.",
            )
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(
                self,
                "Planning formateur",
                "Le planning n'a pas pu être ouvert dans le navigateur.",
            )

    def _funder_changed(self) -> None:
        is_company = self.funder.currentText() == "Entreprise"
        self.funder_details.setEnabled(not is_company)
        if is_company:
            self.funder_details.clear()
        self._refresh_summary()

    def _training_changed(self) -> None:
        training = self._selected_training()
        if training:
            modality = str(training.get("modality") or "distance").lower()
            for index in range(self.modality.count()):
                if str(self.modality.itemData(index)).lower() == modality:
                    self.modality.setCurrentIndex(index)
                    break
            maximum = int(training.get("max_participants") or 1)
            self.participant_count.setMaximum(max(1, maximum))
        self._recalculate_end_date()
        self._refresh_summary()

    def _dates_changed(self) -> None:
        self._recalculate_end_date()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        prospect = self._selected_prospect() or {}
        training = self._selected_training() or {}
        selected = [
            name
            for name, check in self.type_checks.items()
            if check.isChecked()
        ]
        self.summary.setPlainText(
            "CLIENT\n"
            f"{prospect.get('company_name') or '—'}\n"
            f"{prospect.get('siret') or 'SIRET non renseigné'}\n\n"
            "FORMATION\n"
            f"{training.get('name') or '—'}\n"
            f"Durée : {self._safe_float(training.get('duration_hours')):g} h\n"
            f"Prix verrouillé : {self._format_price(training.get('price_cents'))}\n"
            f"Dates : {self.start_date.date().toString('dd/MM/yyyy')} au "
            f"{self.end_date.date().toString('dd/MM/yyyy')}\n"
            f"Horaires : {self.daily_schedule.text().strip() or '—'}\n"
            f"Modalité : {self.modality.currentText()}\n"
            f"Participants : {self.participant_count.value()}\n"
            f"Formateur : {self._selected_trainer_name() or 'Non renseigné'}\n"
            f"Financeur : {self.funder.currentText() or 'Entreprise'}\n\n"
            "DOCUMENTS\n"
            + ("\n".join(f"• {item}" for item in selected) or "• Aucun")
        )

    def _selected_trainer(self) -> dict | None:
        data = self.trainer_combo.currentData()
        return data if isinstance(data, dict) else None

    def _selected_trainer_name(self) -> str:
        trainer = self._selected_trainer() or {}
        return str(trainer.get("name") or "").strip()

    def _generate(self) -> None:
        prospect_id = self.prospect_combo.currentData()
        training_id = self.training_combo.currentData()
        document_types = list(self.DOCUMENT_TYPES)
        if not prospect_id or not training_id:
            QMessageBox.warning(
                self,
                "Dossier incomplet",
                "Sélectionnez un prospect et une formation.",
            )
            return
        if not self.daily_schedule.text().strip():
            QMessageBox.warning(
                self,
                "Dossier incomplet",
                "Renseignez les horaires de la formation.",
            )
            return
        trainer = self._selected_trainer()
        if not trainer or not str(trainer.get("id") or "").strip():
            QMessageBox.warning(
                self,
                "Formateur obligatoire",
                "Sélectionnez un formateur actif dans l'annuaire.",
            )
            return

        training = self._selected_training() or {}
        duration = self._safe_float(training.get("duration_hours"))
        daily_hours = self._daily_duration_hours()
        if daily_hours <= 0:
            QMessageBox.warning(
                self,
                "Horaires invalides",
                (
                    "Les horaires ne peuvent pas être interprétés. "
                    "Utilisez par exemple : 9h00–12h00 / 13h00–15h00."
                ),
            )
            return

        training_days = self._business_days_inclusive(
            self.start_date.date(),
            self.end_date.date(),
        )
        scheduled_hours = training_days * daily_hours
        if abs(scheduled_hours - duration) > 0.05:
            answer = QMessageBox.warning(
                self,
                "Durée incohérente",
                (
                    f"La formation sélectionnée dure {duration:g} h.\n\n"
                    f"Les dates et horaires saisis représentent "
                    f"{scheduled_hours:g} h "
                    f"({training_days} jour(s) × {daily_hours:g} h).\n\n"
                    "Vérifiez les horaires ou les dates avant de générer "
                    "les documents.\n\n"
                    "Voulez-vous continuer malgré cette incohérence ?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        if self.end_date.date() < self.start_date.date():
            QMessageBox.warning(
                self,
                "Dates invalides",
                "La date de fin ne peut pas précéder la date de début.",
            )
            return
        if not document_types:
            QMessageBox.warning(
                self,
                "Documents",
                "Sélectionnez au moins un document à générer.",
            )
            return

        payload = {
            "prospect_id": str(prospect_id),
            "training_id": str(training_id),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),
            "daily_schedule": self.daily_schedule.text().strip(),
            "modality": str(self.modality.currentData() or "distance"),
            "trainer_id": str(trainer.get("id") or ""),
            "trainer_name": self._selected_trainer_name(),
            "funder": self.funder.currentText() or "Entreprise",
            "funder_details": self.funder_details.text().strip(),
            "participant_count": self.participant_count.value(),
            "connection_link": self.connection_link.text().strip(),
            "status": "planned",
        }

        selected_prospect = next(
            (
                item for item in self.prospects
                if str(item.get("id") or "") == str(prospect_id)
            ),
            {},
        )
        self.generated_prospect_id = str(prospect_id)
        self.generated_client_name = str(
            selected_prospect.get("company_name")
            or self.prospect_combo.currentText()
            or "CLIENT"
        ).strip()

        self.generate_button.setEnabled(False)
        self.status_label.setText("Génération sécurisée du dossier client…")
        self.status_label.setStyleSheet(f"color:{MUTED};")
        try:
            session = self.api.create_document_session(payload)
            self.generated_documents = self.api.generate_cloud_documents(
                str(session["id"]),
                document_types,
            )
        except (CloudAPIError, KeyError) as exc:
            self.generate_button.setEnabled(True)
            self.status_label.setText(f"⛔ {exc}")
            self.status_label.setStyleSheet("color:#B42318;")
            QMessageBox.critical(self, "Génération impossible", str(exc))
            return

        lines = [
            f"• {item.get('document_type', 'Document')} "
            f"{item.get('document_number', '')}"
            for item in self.generated_documents
        ]
        answer = QMessageBox.question(
            self,
            "Dossier client créé",
            (
                f"Le dossier Cloud de {self.generated_client_name} a été créé.\n\n"
                f"{len(self.generated_documents)} document(s) généré(s) :\n"
                + "\n".join(lines)
                + "\n\nTélécharger aussi le dossier documentaire complet sur votre PC ?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._download_complete_client_folder()
        self.accept()

    def _download_complete_client_folder(self) -> None:
        if not self.generated_prospect_id:
            return
        destination = QFileDialog.getExistingDirectory(
            self,
            "Choisir l'emplacement du dossier client",
        )
        if not destination:
            return
        try:
            folder, count = self.api.download_cloud_client_folder(
                prospect_id=self.generated_prospect_id,
                client_name=self.generated_client_name,
                destination_root=destination,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Téléchargement impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Dossier client téléchargé",
            (
                f"{count} document(s) classé(s) dans :\n\n{folder}\n\n"
                "01 Devis • 02 Conventions • 03 Programmes • 04 Convocations • "
                "05 Factures • 06 Attestations"
            ),
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


class CloudTrainingDialog(QDialog):
    """Création ou modification d'une formation Cloud."""

    def __init__(self, api, parent=None, training: dict | None = None):
        super().__init__(parent)
        self.api = api
        self.training = dict(training or {})
        self.saved_training: dict | None = None
        self.created_training: dict | None = None
        self.setWindowTitle(
            "Modifier la formation Cloud"
            if self.training
            else "Nouvelle formation Cloud"
        )
        self.resize(700, 720)
        self._build_ui()
        self._populate()

    @staticmethod
    def _line(placeholder: str = "") -> QLineEdit:
        widget = QLineEdit()
        widget.setPlaceholderText(placeholder)
        widget.setMinimumHeight(34)
        return widget

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel(
            "Modifier la formation du catalogue Cloud"
            if self.training
            else "Ajouter une formation au catalogue Cloud"
        )
        title.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:900;")
        root.addWidget(title)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        self.reference = self._line("Ex. FP-BTP-PILOTAGE")
        self.name = self._line("Intitulé officiel")
        self.category = self._line("Ex. Pilotage d'activité")
        self.modality = QComboBox()
        self.modality.addItem("À distance", "distance")
        self.modality.addItem("Présentiel", "presentiel")
        self.modality.addItem("Hybride", "hybride")
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0.5, 999)
        self.duration.setDecimals(2)
        self.duration.setValue(14)
        self.duration.setSuffix(" h")
        self.price = QDoubleSpinBox()
        self.price.setRange(0, 999999)
        self.price.setDecimals(2)
        self.price.setSuffix(" €")
        self.participants = QSpinBox()
        self.participants.setRange(1, 1000)
        self.participants.setValue(1)
        self.certification = self._line("Certification éventuelle")
        self.description = QTextEdit()
        self.description.setMinimumHeight(90)
        self.objectives = QTextEdit()
        self.objectives.setMinimumHeight(90)
        self.prerequisites = QTextEdit()
        self.prerequisites.setMinimumHeight(70)

        form.addRow("Référence *", self.reference)
        form.addRow("Intitulé *", self.name)
        form.addRow("Catégorie", self.category)
        form.addRow("Durée *", self.duration)
        form.addRow("Tarif verrouillé", self.price)
        form.addRow("Modalité", self.modality)
        form.addRow("Participants maximum", self.participants)
        form.addRow("Certification", self.certification)
        form.addRow("Description / contenu", self.description)
        form.addRow("Objectifs", self.objectives)
        form.addRow("Prérequis", self.prerequisites)
        root.addWidget(card, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton(
            "Enregistrer les modifications"
            if self.training
            else "Créer la formation"
        )
        self.save_button.setStyleSheet(PRIMARY_BUTTON)
        self.save_button.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(self.save_button)
        root.addLayout(actions)

    def _populate(self) -> None:
        if not self.training:
            return
        self.reference.setText(str(self.training.get("reference") or ""))
        self.name.setText(str(self.training.get("name") or ""))
        self.category.setText(str(self.training.get("category") or ""))
        try:
            self.duration.setValue(float(self.training.get("duration_hours") or 14))
        except (TypeError, ValueError):
            self.duration.setValue(14)
        try:
            self.price.setValue(float(self.training.get("price_cents") or 0) / 100)
        except (TypeError, ValueError):
            self.price.setValue(0)
        modality_index = self.modality.findData(
            str(self.training.get("modality") or "distance")
        )
        if modality_index >= 0:
            self.modality.setCurrentIndex(modality_index)
        try:
            self.participants.setValue(
                int(self.training.get("max_participants") or 1)
            )
        except (TypeError, ValueError):
            self.participants.setValue(1)
        self.certification.setText(
            str(self.training.get("certification") or "")
        )
        self.description.setPlainText(
            str(self.training.get("description") or "")
        )
        self.objectives.setPlainText(
            str(self.training.get("objectives") or "")
        )
        self.prerequisites.setPlainText(
            str(self.training.get("prerequisites") or "")
        )

    def _save(self) -> None:
        if not self.reference.text().strip() or not self.name.text().strip():
            QMessageBox.warning(
                self,
                "Formation incomplète",
                "La référence et l'intitulé sont obligatoires.",
            )
            return
        payload = {
            "reference": self.reference.text().strip(),
            "name": self.name.text().strip(),
            "category": self.category.text().strip(),
            "description": self.description.toPlainText().strip(),
            "objectives": self.objectives.toPlainText().strip(),
            "prerequisites": self.prerequisites.toPlainText().strip(),
            "duration_hours": self.duration.value(),
            "price_cents": int(round(self.price.value() * 100)),
            "modality": str(self.modality.currentData() or "distance"),
            "max_participants": self.participants.value(),
            "certification": self.certification.text().strip(),
        }
        try:
            if self.training:
                self.saved_training = self.api.update_document_training(
                    str(self.training.get("id") or ""),
                    payload,
                )
            else:
                self.saved_training = self.api.create_document_training(payload)
                self.created_training = self.saved_training
        except CloudAPIError as exc:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                str(exc),
            )
            return
        QMessageBox.information(
            self,
            "Formation enregistrée",
            (
                "Les modifications ont été enregistrées."
                if self.training
                else "La formation est maintenant disponible dans le catalogue Cloud."
            ),
        )
        self.accept()


class CloudTrainingManagementDialog(QDialog):
    """Gestion complète du catalogue de formations Cloud."""

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.rows: list[dict] = []
        self.changed = False
        self.setWindowTitle("Catalogue des formations Cloud")
        self.resize(980, 560)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("Catalogue des formations Cloud")
        title.setStyleSheet(f"color:{TEXT}; font-size:24px; font-weight:900;")
        subtitle = QLabel(
            "Créez, modifiez, désactivez ou supprimez les formations "
            "qui n'ont encore jamais été utilisées."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED};")
        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        add = QPushButton("+ Nouvelle formation")
        add.setStyleSheet(PRIMARY_BUTTON)
        add.clicked.connect(self._add)
        edit = QPushButton("Modifier")
        edit.setStyleSheet(SECONDARY_BUTTON)
        edit.clicked.connect(self._edit)
        toggle = QPushButton("Activer / désactiver")
        toggle.setStyleSheet(SECONDARY_BUTTON)
        toggle.clicked.connect(self._toggle)
        delete = QPushButton("Supprimer")
        delete.setStyleSheet(SECONDARY_BUTTON)
        delete.clicked.connect(self._delete)
        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self._load)
        toolbar.addWidget(add)
        toolbar.addWidget(edit)
        toolbar.addWidget(toggle)
        toolbar.addWidget(delete)
        toolbar.addStretch()
        toolbar.addWidget(refresh)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Référence",
                "Intitulé",
                "Durée",
                "Tarif",
                "Modalité",
                "Participants",
                "Statut",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            f"QTableWidget{{background:white; alternate-background-color:#F8FAFC; "
            f"color:{TEXT}; border:1px solid {BORDER}; border-radius:10px; "
            f"gridline-color:{BORDER};}}"
            f"QHeaderView::section{{background:#F8FAFC; color:{MUTED}; border:none; "
            f"border-bottom:1px solid {BORDER}; padding:9px; font-weight:800;}}"
        )
        self.table.doubleClicked.connect(self._edit)
        root.addWidget(self.table, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color:{MUTED};")
        root.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.addStretch()
        close = QPushButton("Fermer")
        close.setStyleSheet(PRIMARY_BUTTON)
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        root.addLayout(actions)

    def _load(self) -> None:
        try:
            self.rows = self.api.list_document_trainings(
                include_inactive=True
            )
        except CloudAPIError as exc:
            QMessageBox.critical(
                self,
                "Catalogue indisponible",
                str(exc),
            )
            return
        self.table.setRowCount(len(self.rows))
        for row_index, item in enumerate(self.rows):
            try:
                price = int(item.get("price_cents") or 0) / 100
            except (TypeError, ValueError):
                price = 0
            try:
                duration = float(item.get("duration_hours") or 0)
            except (TypeError, ValueError):
                duration = 0
            values = [
                item.get("reference") or "",
                item.get("name") or "",
                f"{duration:g} h",
                f"{price:,.2f} €".replace(",", " "),
                item.get("modality") or "",
                item.get("max_participants") or 1,
                "Active" if item.get("active") else "Inactive",
            ]
            for column, value in enumerate(values):
                self.table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )
        self.status_label.setText(
            f"{len(self.rows)} formation(s) dans le catalogue Cloud."
        )

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(
                self,
                "Sélection",
                "Sélectionnez d'abord une formation.",
            )
            return None
        return self.rows[row]

    def _add(self) -> None:
        if CloudTrainingDialog(self.api, self).exec():
            self.changed = True
            self._load()

    def _edit(self, *_args) -> None:
        item = self._selected()
        if not item:
            return
        if CloudTrainingDialog(
            self.api,
            self,
            training=item,
        ).exec():
            self.changed = True
            self._load()

    def _toggle(self) -> None:
        item = self._selected()
        if not item:
            return
        active = bool(item.get("active"))
        action = "désactiver" if active else "réactiver"
        if QMessageBox.question(
            self,
            "Modifier le statut",
            f"Voulez-vous {action} la formation « {item.get('name', '')} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            self.api.update_document_training(
                str(item.get("id") or ""),
                {"active": not active},
            )
        except CloudAPIError as exc:
            QMessageBox.critical(
                self,
                "Modification impossible",
                str(exc),
            )
            return
        self.changed = True
        self._load()

    def _delete(self) -> None:
        item = self._selected()
        if not item:
            return
        if QMessageBox.question(
            self,
            "Supprimer la formation",
            (
                f"Supprimer définitivement « {item.get('name', '')} » ?\n\n"
                "Cette action n'est possible que si la formation n'a jamais "
                "été utilisée dans une session, un modèle ou un document."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            self.api.delete_document_training(
                str(item.get("id") or "")
            )
        except CloudAPIError as exc:
            if exc.status_code == 409:
                answer = QMessageBox.question(
                    self,
                    "Suppression impossible",
                    f"{exc}\n\nVoulez-vous désactiver cette formation à la place ?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if answer == QMessageBox.Yes:
                    try:
                        self.api.update_document_training(
                            str(item.get("id") or ""),
                            {"active": False},
                        )
                    except CloudAPIError as update_exc:
                        QMessageBox.critical(
                            self,
                            "Désactivation impossible",
                            str(update_exc),
                        )
                        return
                    self.changed = True
                    self._load()
                return
            QMessageBox.critical(
                self,
                "Suppression impossible",
                str(exc),
            )
            return
        self.changed = True
        QMessageBox.information(
            self,
            "Formation supprimée",
            "La formation a été supprimée du catalogue Cloud.",
        )
        self._load()


class CloudTemplateUploadDialog(QDialog):
    """Upload d'un modèle DOCX officiel, réservé à l'administrateur."""

    DOCUMENT_TYPES = ("Convention", "Programme", "Convocation")

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.trainings: list[dict] = []
        self.file_path = Path()
        self.setWindowTitle("Uploader un modèle officiel")
        self.resize(650, 360)
        self._build_ui()
        self._load_trainings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("Modèle documentaire Cloud")
        title.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:900;")
        root.addWidget(title)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(11)
        self.document_type = QComboBox()
        self.document_type.addItems(self.DOCUMENT_TYPES)
        self.training = QComboBox()
        self.training.addItem("Toutes les formations", None)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ex. Convention officielle Form@Prof")
        file_row = QHBoxLayout()
        self.file_label = QLineEdit()
        self.file_label.setReadOnly(True)
        choose = QPushButton("Parcourir…")
        choose.setStyleSheet(SECONDARY_BUTTON)
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(choose)
        form.addRow("Type *", self.document_type)
        form.addRow("Formation liée", self.training)
        form.addRow("Nom du modèle", self.name)
        form.addRow("Fichier DOCX *", file_row)
        root.addWidget(card)

        note = QLabel(
            "Le fichier reste privé. Les balises {{CLIENT_NOM}}, "
            "{{FORMATION_NOM}}, {{FORMATION_DATES}} et les autres variables "
            "officielles seront fusionnées côté serveur."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED};")
        root.addWidget(note)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        upload = QPushButton("Uploader le modèle")
        upload.setStyleSheet(PRIMARY_BUTTON)
        upload.clicked.connect(self._upload)
        actions.addWidget(cancel)
        actions.addWidget(upload)
        root.addLayout(actions)

    def _load_trainings(self) -> None:
        try:
            self.trainings = self.api.list_document_trainings(
                include_inactive=True
            )
        except CloudAPIError as exc:
            QMessageBox.warning(self, "Catalogue indisponible", str(exc))
            return
        for training in self.trainings:
            self.training.addItem(
                f"{training.get('reference', '')} — {training.get('name', '')}",
                str(training.get("id") or ""),
            )

    def _choose_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le modèle Word",
            "",
            "Modèle Word (*.docx)",
        )
        if filename:
            self.file_path = Path(filename)
            self.file_label.setText(filename)
            if not self.name.text().strip():
                self.name.setText(self.file_path.stem)

    def _upload(self) -> None:
        if not self.file_path.is_file():
            QMessageBox.warning(
                self,
                "Modèle manquant",
                "Sélectionnez un fichier DOCX officiel.",
            )
            return
        try:
            self.api.upload_cloud_document_template(
                document_type=self.document_type.currentText(),
                file_path=self.file_path,
                name=self.name.text().strip(),
                training_id=self.training.currentData(),
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Upload impossible", str(exc))
            return
        QMessageBox.information(
            self,
            "Modèle disponible",
            "Le modèle officiel est maintenant disponible dans le Cloud privé.",
        )
        self.accept()


class CloudAdministrativeUploadDialog(QDialog):
    """Upload d'un Devis, d'une Facture ou d'une Attestation par l'admin."""

    DOCUMENT_TYPES = ("Devis", "Facture", "Attestation de formation")

    def __init__(
        self,
        api,
        parent=None,
        *,
        initial_prospect_id: str | None = None,
    ):
        super().__init__(parent)
        self.api = api
        self.initial_prospect_id = initial_prospect_id
        self.prospects: list[dict] = []
        self.file_path = Path()
        self.setWindowTitle("Déposer un document administratif")
        self.resize(650, 380)
        self._build_ui()
        self._load_prospects()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        title = QLabel("Déposer un document pour un commercial")
        title.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:900;")
        root.addWidget(title)

        card = QFrame()
        card.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(11)
        self.prospect = QComboBox()
        self.document_type = QComboBox()
        self.document_type.addItems(self.DOCUMENT_TYPES)
        self.document_number = QLineEdit()
        self.document_number.setPlaceholderText("Facultatif : numéro du document")
        file_row = QHBoxLayout()
        self.file_label = QLineEdit()
        self.file_label.setReadOnly(True)
        choose = QPushButton("Parcourir…")
        choose.setStyleSheet(SECONDARY_BUTTON)
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(choose)
        form.addRow("Prospect / client *", self.prospect)
        form.addRow("Type *", self.document_type)
        form.addRow("Numéro", self.document_number)
        form.addRow("Fichier PDF ou DOCX *", file_row)
        root.addWidget(card)

        note = QLabel(
            "Le commercial pourra uniquement consulter et télécharger ce "
            "document. Il ne pourra ni le modifier, ni le remplacer, ni le supprimer."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED};")
        root.addWidget(note)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)
        upload = QPushButton("Déposer dans le Cloud")
        upload.setStyleSheet(PRIMARY_BUTTON)
        upload.clicked.connect(self._upload)
        actions.addWidget(cancel)
        actions.addWidget(upload)
        root.addLayout(actions)

    def _load_prospects(self) -> None:
        try:
            self.prospects = self.api.list_prospects(
                include_archived=False,
                limit=500,
            ).items
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Prospects indisponibles", str(exc))
            return
        selected = -1
        for index, prospect in enumerate(self.prospects):
            prospect_id = str(prospect.get("id") or "")
            self.prospect.addItem(
                str(prospect.get("company_name") or "Prospect sans nom"),
                prospect_id,
            )
            if prospect_id == self.initial_prospect_id:
                selected = index
        if selected >= 0:
            self.prospect.setCurrentIndex(selected)

    def _choose_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir le document",
            "",
            "Documents (*.pdf *.docx)",
        )
        if filename:
            self.file_path = Path(filename)
            self.file_label.setText(filename)

    def _upload(self) -> None:
        prospect_id = self.prospect.currentData()
        if not prospect_id:
            QMessageBox.warning(
                self,
                "Prospect manquant",
                "Sélectionnez le prospect ou le client concerné.",
            )
            return
        if not self.file_path.is_file():
            QMessageBox.warning(
                self,
                "Document manquant",
                "Sélectionnez un fichier PDF ou DOCX.",
            )
            return
        try:
            self.api.upload_cloud_administrative_document(
                prospect_id=str(prospect_id),
                document_type=self.document_type.currentText(),
                file_path=self.file_path,
                document_number=self.document_number.text().strip(),
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Dépôt impossible", str(exc))
            return
        QMessageBox.information(
            self,
            "Document disponible",
            "Le document est maintenant visible et téléchargeable par le commercial concerné.",
        )
        self.accept()
