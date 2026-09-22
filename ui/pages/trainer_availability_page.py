from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.trainer_availability_premium_theme import (
    trainer_availability_palette,
    trainer_availability_stylesheet,
    trainer_platform_badge_style,
    trainer_row_button_style,
    trainer_status_badge_style,
)


class TrainerAvailabilityPage(QWidget):
    """Pilotage des agendas de disponibilité des formateurs."""

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self._build_ui()
        self._apply_visual_theme()

    def _build_ui(self) -> None:
        self.setObjectName("TrainerAvailabilityPage")

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("TrainerAvailabilityScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setObjectName("TrainerAvailabilityContent")
        root = QVBoxLayout(self.content)
        root.setContentsMargins(26, 22, 26, 30)
        root.setSpacing(12)

        # Header
        hero = QFrame()
        hero.setObjectName("TrainerAvailabilityHero")
        hero.setMinimumHeight(112)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 18, 16)
        hero_layout.setSpacing(14)

        titles = QVBoxLayout()
        titles.setSpacing(3)

        overline = QLabel("RESSOURCES PÉDAGOGIQUES  •  PLANIFICATION")
        overline.setObjectName("TrainerAvailabilityOverline")

        title = QLabel("Disponibilités formateurs")
        title.setObjectName("TrainerAvailabilityTitle")

        subtitle = QLabel(
            "Vérifiez en un coup d'œil les agendas disponibles avant de planifier "
            "une nouvelle session."
        )
        subtitle.setObjectName("TrainerAvailabilitySubtitle")
        subtitle.setWordWrap(True)

        titles.addWidget(overline)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        hero_layout.addLayout(titles, 1)

        hero_actions = QVBoxLayout()
        hero_actions.setSpacing(8)

        self.cloud_chip = QLabel("●  CLOUD FORMATEURS")
        self.cloud_chip.setObjectName("TrainerAvailabilityCloud")
        self.cloud_chip.setAlignment(Qt.AlignCenter)
        self.cloud_chip.setFixedHeight(28)
        self.cloud_chip.setMinimumWidth(142)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.edit_link_button = QPushButton("✎  Modifier le lien")
        self.edit_link_button.setObjectName("TrainerSecondaryButton")
        self.edit_link_button.setCursor(Qt.PointingHandCursor)
        self.edit_link_button.clicked.connect(self._edit_link)

        self.refresh_button = QPushButton("↻  Actualiser")
        self.refresh_button.setObjectName("TrainerPrimaryButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(self.rafraichir)

        buttons.addWidget(self.edit_link_button)
        buttons.addWidget(self.refresh_button)
        hero_actions.addWidget(self.cloud_chip, 0, Qt.AlignRight)
        hero_actions.addLayout(buttons)
        hero_layout.addLayout(hero_actions)

        root.addWidget(hero)

        # KPI
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(9)
        self.kpi_values: dict[str, QLabel] = {}

        for key, label, caption in (
            ("trainers", "Formateurs", "Profils visibles"),
            ("active", "Actifs", "Disponibles dans l'équipe"),
            ("linked", "Agendas connectés", "Liens configurés"),
            ("missing", "À configurer", "Agendas encore manquants"),
        ):
            card = QFrame()
            card.setProperty("trainerCard", True)
            layout = QVBoxLayout(card)
            layout.setContentsMargins(13, 10, 13, 10)
            layout.setSpacing(2)

            label_widget = QLabel(label)
            label_widget.setProperty("trainerLabel", True)

            value_widget = QLabel("0")
            value_widget.setProperty("trainerValue", True)

            caption_widget = QLabel(caption)
            caption_widget.setProperty("trainerCaption", True)

            layout.addWidget(label_widget)
            layout.addWidget(value_widget)
            layout.addWidget(caption_widget)
            self.kpi_values[key] = value_widget
            kpi_row.addWidget(card, 1)

        root.addLayout(kpi_row)

        # Two-column command center
        main_row = QHBoxLayout()
        main_row.setSpacing(10)

        coverage = QFrame()
        coverage.setProperty("trainerCard", True)
        coverage.setMinimumWidth(265)
        coverage.setMaximumWidth(335)
        coverage_layout = QVBoxLayout(coverage)
        coverage_layout.setContentsMargins(15, 14, 15, 15)
        coverage_layout.setSpacing(9)

        over = QLabel("COUVERTURE DES AGENDAS")
        over.setProperty("trainerSectionOverline", True)
        coverage_title = QLabel("Prêt à planifier")
        coverage_title.setProperty("trainerSectionTitle", True)

        coverage_note = QLabel(
            "Un agenda connecté permet d'ouvrir immédiatement les disponibilités "
            "du formateur depuis Form@Prospect."
        )
        coverage_note.setProperty("trainerBody", True)
        coverage_note.setWordWrap(True)

        self.coverage_value = QLabel("0 / 0")
        self.coverage_value.setProperty("trainerValue", True)

        self.coverage_caption = QLabel("Aucun agenda chargé")
        self.coverage_caption.setProperty("trainerCaption", True)

        self.coverage_bar = QProgressBar()
        self.coverage_bar.setObjectName("TrainerCoverageBar")
        self.coverage_bar.setRange(0, 100)
        self.coverage_bar.setValue(0)
        self.coverage_bar.setTextVisible(False)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)

        info = QLabel(
            "Google Sheets, Google Calendar, Microsoft 365 ou toute plateforme "
            "de planning accessible par lien."
        )
        info.setProperty("trainerBody", True)
        info.setWordWrap(True)

        self.open_selected_button = QPushButton("↗  Ouvrir le planning sélectionné")
        self.open_selected_button.setObjectName("TrainerPrimaryButton")
        self.open_selected_button.setEnabled(False)
        self.open_selected_button.clicked.connect(self._open_selected)

        self.summary = QLabel("0 formateur")
        self.summary.setProperty("trainerBody", True)
        self.summary.setWordWrap(True)

        coverage_layout.addWidget(over)
        coverage_layout.addWidget(coverage_title)
        coverage_layout.addWidget(coverage_note)
        coverage_layout.addSpacing(4)
        coverage_layout.addWidget(self.coverage_value)
        coverage_layout.addWidget(self.coverage_caption)
        coverage_layout.addWidget(self.coverage_bar)
        coverage_layout.addWidget(divider)
        coverage_layout.addWidget(info)
        coverage_layout.addStretch(1)
        coverage_layout.addWidget(self.open_selected_button)
        coverage_layout.addWidget(self.summary)

        directory = QFrame()
        directory.setProperty("trainerCard", True)
        directory_layout = QVBoxLayout(directory)
        directory_layout.setContentsMargins(15, 13, 15, 14)
        directory_layout.setSpacing(9)

        directory_top = QHBoxLayout()
        directory_titles = QVBoxLayout()
        directory_titles.setSpacing(1)

        directory_over = QLabel("ÉQUIPE PÉDAGOGIQUE")
        directory_over.setProperty("trainerSectionOverline", True)
        directory_title = QLabel("Répertoire des formateurs")
        directory_title.setProperty("trainerSectionTitle", True)
        directory_subtitle = QLabel(
            "Spécialités, statut et accès direct aux disponibilités."
        )
        directory_subtitle.setProperty("trainerBody", True)

        directory_titles.addWidget(directory_over)
        directory_titles.addWidget(directory_title)
        directory_titles.addWidget(directory_subtitle)

        self.count_badge = QLabel("0 formateur")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setProperty("trainerLabel", True)

        directory_top.addLayout(directory_titles, 1)
        directory_top.addWidget(self.count_badge, 0, Qt.AlignTop)
        directory_layout.addLayout(directory_top)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("TrainerAvailabilityTable")
        self.table.setHorizontalHeaderLabels(
            ["Formateur", "Spécialités", "Statut", "Plateforme", "Planning"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setWordWrap(True)
        self.table.setMinimumHeight(390)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 104)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 175)

        self.table.doubleClicked.connect(self._open_selected)
        self.table.itemSelectionChanged.connect(self._sync_selection_actions)
        directory_layout.addWidget(self.table, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("TrainerAvailabilityStatus")
        self.status_label.setWordWrap(True)
        directory_layout.addWidget(self.status_label)

        main_row.addWidget(coverage)
        main_row.addWidget(directory, 1)
        root.addLayout(main_row, 1)

        self.scroll.setWidget(self.content)
        page.addWidget(self.scroll)

    def _apply_visual_theme(self) -> None:
        palette = trainer_availability_palette()
        self._palette = palette
        self.setStyleSheet(trainer_availability_stylesheet(palette))
        self._restyle_rows()

    def _restyle_rows(self) -> None:
        if not hasattr(self, "table"):
            return
        p = getattr(self, "_palette", trainer_availability_palette())

        for row_index, trainer in enumerate(self.rows):
            active = bool(trainer.get("active"))
            url = str(trainer.get("availability_url") or "").strip()

            status_badge = self.table.cellWidget(row_index, 2)
            if status_badge is not None:
                status_badge.setStyleSheet(
                    trainer_status_badge_style(p, active)
                )

            platform_badge = self.table.cellWidget(row_index, 3)
            if platform_badge is not None:
                platform_badge.setStyleSheet(
                    trainer_platform_badge_style(p, bool(url))
                )

            open_button = self.table.cellWidget(row_index, 4)
            if open_button is not None:
                open_button.setStyleSheet(
                    trainer_row_button_style(p, bool(url))
                )

    @staticmethod
    def _is_admin() -> bool:
        return SessionState.has_role("Administrateur")

    @staticmethod
    def _can_view() -> bool:
        return (
            SessionState.has_role("Administrateur")
            or SessionState.has_role("Commercial")
        )

    @staticmethod
    def _platform_name(url: str) -> str:
        host = (urlparse(url).netloc or "").lower()
        path = (urlparse(url).path or "").lower()
        if "docs.google.com" in host and "spreadsheets" in path:
            return "Google Sheets"
        if "calendar.google.com" in host:
            return "Google Calendar"
        if "outlook" in host or "office.com" in host:
            return "Outlook / Microsoft 365"
        return "Agenda en ligne"

    @staticmethod
    def _short_url(url: str) -> str:
        if not url:
            return "Non renseigné"
        parsed = urlparse(url)
        platform = TrainerAvailabilityPage._platform_name(url)
        return f"{platform} — {parsed.netloc}"

    def _reset_metrics(self) -> None:
        for key in ("trainers", "active", "linked", "missing"):
            self.kpi_values[key].setText("0")
        self.coverage_value.setText("0 / 0")
        self.coverage_caption.setText("Aucun agenda chargé")
        self.coverage_bar.setValue(0)
        self.count_badge.setText("0 formateur")
        self.summary.setText("0 formateur")
        self.open_selected_button.setEnabled(False)

    def _sync_selection_actions(self) -> None:
        row = self.table.currentRow()
        enabled = False
        if 0 <= row < len(self.rows):
            enabled = bool(
                str(self.rows[row].get("availability_url") or "").strip()
            )
        self.open_selected_button.setEnabled(enabled)

    def rafraichir(self) -> None:
        if not self._can_view():
            self.rows = []
            self.table.setRowCount(0)
            self._reset_metrics()
            self.status_label.setText(
                "Cette section est accessible aux administrateurs et aux commerciaux."
            )
            self.edit_link_button.setVisible(False)
            return

        is_admin = self._is_admin()
        self.edit_link_button.setVisible(is_admin)
        self.edit_link_button.setEnabled(is_admin)

        if not CloudRuntime.is_active():
            self.rows = []
            self.table.setRowCount(0)
            self._reset_metrics()
            self.cloud_chip.setText("●  CLOUD INDISPONIBLE")
            self.status_label.setText(
                "Connectez-vous à Form@Prospect Cloud pour consulter "
                "les disponibilités des formateurs."
            )
            return

        self.cloud_chip.setText("●  CLOUD FORMATEURS  •  LIVE")

        try:
            self.rows = CloudRuntime.api().list_cloud_trainers(
                include_inactive=is_admin
            )
        except CloudAPIError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self._reset_metrics()
            self.status_label.setText(f"⛔ {exc}")
            return

        self.table.setRowCount(len(self.rows))
        linked = 0
        active_count = 0

        p = getattr(self, "_palette", trainer_availability_palette())

        for row_index, trainer in enumerate(self.rows):
            self.table.setRowHeight(row_index, 54)
            url = str(trainer.get("availability_url") or "").strip()
            active = bool(trainer.get("active"))

            if active:
                active_count += 1
            if url:
                linked += 1

            values = [
                trainer.get("full_name") or "",
                trainer.get("specialties") or "—",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row_index, column, item)

            status_badge = QLabel("●  Actif" if active else "●  Inactif")
            status_badge.setAlignment(Qt.AlignCenter)
            status_badge.setMinimumSize(80, 29)
            status_badge.setStyleSheet(
                trainer_status_badge_style(p, active)
            )
            self.table.setCellWidget(row_index, 2, status_badge)

            platform_badge = QLabel(self._short_url(url))
            platform_badge.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            platform_badge.setToolTip(url if url else "")
            platform_badge.setStyleSheet(
                trainer_platform_badge_style(p, bool(url))
            )
            self.table.setCellWidget(row_index, 3, platform_badge)

            open_button = QPushButton(
                "↗  Consulter"
                if url
                else "Non renseigné"
            )
            open_button.setCursor(Qt.PointingHandCursor)
            open_button.setMinimumSize(145, 34)
            open_button.setEnabled(bool(url))
            open_button.setStyleSheet(
                trainer_row_button_style(p, bool(url))
            )
            open_button.clicked.connect(
                lambda _checked=False, target=url: self._open_url(target)
            )
            self.table.setCellWidget(row_index, 4, open_button)

        missing = max(0, len(self.rows) - linked)
        coverage = round((linked / len(self.rows)) * 100) if self.rows else 0

        self.kpi_values["trainers"].setText(str(len(self.rows)))
        self.kpi_values["active"].setText(str(active_count))
        self.kpi_values["linked"].setText(str(linked))
        self.kpi_values["missing"].setText(str(missing))

        self.coverage_value.setText(f"{linked} / {len(self.rows)}")
        self.coverage_caption.setText(
            f"{coverage}% des agendas sont configurés"
            if self.rows
            else "Aucun agenda chargé"
        )
        self.coverage_bar.setValue(coverage)

        self.summary.setText(
            f"{len(self.rows)} formateur(s) • {linked} agenda(s) connecté(s)"
        )
        self.count_badge.setText(
            f"{len(self.rows)} formateur"
            if len(self.rows) <= 1
            else f"{len(self.rows)} formateurs"
        )

        if is_admin:
            self.status_label.setText(
                "Sélectionnez un formateur pour ouvrir son planning ou modifier "
                "le lien de disponibilités."
            )
        else:
            self.status_label.setText(
                "Sélectionnez un formateur pour consulter ses disponibilités. "
                "La modification des liens reste réservée à l'administrateur."
            )

        self._sync_selection_actions()
        self._restyle_rows()

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(
                self,
                "Formateur",
                "Sélectionnez d'abord un formateur.",
            )
            return None
        return self.rows[row]

    def _open_selected(self, *_args) -> None:
        trainer = self._selected()
        if trainer is None:
            return
        url = str(trainer.get("availability_url") or "").strip()
        if not url:
            QMessageBox.information(
                self,
                "Disponibilités",
                "Aucun lien de disponibilités n'est encore renseigné "
                "pour ce formateur.",
            )
            return
        self._open_url(url)

    def _open_url(self, url: str) -> None:
        url = str(url or "").strip()
        if not url:
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(
                self,
                "Ouverture impossible",
                "Le lien n'a pas pu être ouvert dans le navigateur.",
            )

    def _edit_link(self) -> None:
        if not self._is_admin():
            QMessageBox.warning(
                self,
                "Modification interdite",
                "Seul l'administrateur peut modifier le lien de disponibilités.",
            )
            return

        trainer = self._selected()
        if trainer is None:
            return

        current = str(trainer.get("availability_url") or "")
        value, accepted = QInputDialog.getText(
            self,
            "Lien de disponibilités",
            (
                f"Agenda de {trainer.get('full_name') or 'ce formateur'} :\n"
                "Collez le lien Google Sheets, Google Calendar ou "
                "de la plateforme utilisée."
            ),
            text=current,
        )
        if not accepted:
            return

        value = value.strip()
        if value and not value.lower().startswith(("http://", "https://")):
            QMessageBox.warning(
                self,
                "Lien invalide",
                "Le lien doit commencer par http:// ou https://.",
            )
            return

        try:
            CloudRuntime.api().update_cloud_trainer(
                str(trainer.get("id") or ""),
                {"availability_url": value},
            )
        except CloudAPIError as exc:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Disponibilités enregistrées",
            (
                "Le lien de disponibilités a été mis à jour."
                if value
                else "Le lien de disponibilités a été supprimé."
            ),
        )
        self.rafraichir()
