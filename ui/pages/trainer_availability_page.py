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
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    NAVY,
    PAGE_BG,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime


class TrainerAvailabilityPage(QWidget):
    """Accès administrateur aux agendas de disponibilité des formateurs."""

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _build_ui(self) -> None:
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:#F4F7FB;border:none;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#CBD5E1;min-height:40px;border-radius:5px;}"
            "QScrollBar::handle:vertical:hover{background:#94A3B8;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        content = QWidget()
        content.setStyleSheet("background:#F4F7FB;")
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 34)
        root.setSpacing(16)

        # ==============================================================
        # HERO
        # ==============================================================
        hero = QFrame()
        hero.setObjectName("TrainerHero")
        hero.setMinimumHeight(128)
        hero.setStyleSheet(
            "QFrame#TrainerHero{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF, stop:1 #EEF6FF);"
            "border:1px solid #DCE7F3;border-radius:22px;"
            "}"
            "QLabel{background:transparent;border:none;}"
        )

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 20, 18)
        hero_layout.setSpacing(16)

        icon = QLabel("▦")
        icon.setFixedSize(58, 58)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background:#0B2A52;color:#FFFFFF;border-radius:18px;"
            "font-size:25px;font-weight:900;"
        )

        titles = QVBoxLayout()
        titles.setSpacing(3)

        overline = QLabel("FORMATEURS  •  PLANIFICATION DES DISPONIBILITÉS")
        overline.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1.1px;"
        )

        title = QLabel("Disponibilités formateurs")
        title.setStyleSheet(
            "color:#0B1220;font-size:28px;font-weight:900;"
        )

        subtitle = QLabel(
            "Consultez les agendas de vos formateurs avant de programmer "
            "une nouvelle session."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "color:#718096;font-size:11px;"
        )

        titles.addWidget(overline)
        titles.addWidget(title)
        titles.addWidget(subtitle)

        self.edit_link_button = QPushButton("✎  Modifier le lien")
        self.edit_link_button.setCursor(Qt.PointingHandCursor)
        self.edit_link_button.setMinimumSize(145, 40)
        self.edit_link_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;"
            "border:1px solid #D3DFEB;border-radius:10px;"
            "padding:0 15px;font-size:10px;font-weight:850;}"
            "QPushButton:hover{background:#F4F9FF;color:#247BD0;"
            "border-color:#92BDEA;}"
            "QPushButton:disabled{background:#F1F5F9;color:#A0AEC0;}"
        )
        self.edit_link_button.clicked.connect(self._edit_link)

        refresh = QPushButton("↻  Actualiser")
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.setMinimumSize(118, 40)
        refresh.setStyleSheet(
            "QPushButton{background:#338CE4;color:#FFFFFF;border:none;"
            "border-radius:10px;padding:0 16px;font-size:10px;font-weight:900;}"
            "QPushButton:hover{background:#287FD4;}"
            "QPushButton:pressed{background:#1E6DBA;}"
        )
        refresh.clicked.connect(self.rafraichir)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.edit_link_button)
        actions.addWidget(refresh)

        hero_layout.addWidget(icon)
        hero_layout.addLayout(titles, 1)
        hero_layout.addLayout(actions)

        root.addWidget(hero)

        # ==============================================================
        # KPI
        # ==============================================================
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self.kpi_values = {}

        kpis = [
            ("trainers", "Formateurs", "0", "Profils visibles", "#338CE4", "#EEF6FF", "👤"),
            ("active", "Actifs", "0", "Formateurs disponibles", "#10B981", "#ECFDF5", "●"),
            ("linked", "Agendas renseignés", "0", "Liens configurés", "#8B5CF6", "#F5F3FF", "▦"),
        ]

        for key, label, value, caption, accent, soft, glyph in kpis:
            card = QFrame()
            card.setObjectName(f"TrainerMetric_{key}")
            card.setMinimumHeight(100)
            card.setStyleSheet(
                f"QFrame#TrainerMetric_{key}{{background:#FFFFFF;"
                "border:1px solid #E2EAF3;border-radius:16px;}"
                "QLabel{background:transparent;border:none;}"
            )
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 11)
            layout.setSpacing(4)

            top = QHBoxLayout()
            badge = QLabel(glyph)
            badge.setFixedSize(28, 28)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background:{soft};color:{accent};border-radius:9px;"
                "font-size:12px;font-weight:900;"
            )
            label_widget = QLabel(label)
            label_widget.setStyleSheet(
                "color:#53657C;font-size:9px;font-weight:850;"
            )
            top.addWidget(badge)
            top.addWidget(label_widget)
            top.addStretch()

            value_widget = QLabel(value)
            value_widget.setStyleSheet(
                "color:#071A31;font-size:24px;font-weight:900;"
            )
            caption_widget = QLabel(caption)
            caption_widget.setStyleSheet(
                "color:#94A3B8;font-size:8px;"
            )

            layout.addLayout(top)
            layout.addWidget(value_widget)
            layout.addWidget(caption_widget)

            self.kpi_values[key] = value_widget
            kpi_row.addWidget(card)

        root.addLayout(kpi_row)

        # ==============================================================
        # INFO BAND
        # ==============================================================
        info = QFrame()
        info.setObjectName("TrainerInfo")
        info.setStyleSheet(
            "QFrame#TrainerInfo{background:#F8FBFF;"
            "border:1px solid #DCE8F5;border-radius:14px;}"
            "QLabel{background:transparent;border:none;}"
        )
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(14, 11, 14, 11)
        info_layout.setSpacing(10)

        info_icon = QLabel("i")
        info_icon.setFixedSize(28, 28)
        info_icon.setAlignment(Qt.AlignCenter)
        info_icon.setStyleSheet(
            "background:#338CE4;color:#FFFFFF;border-radius:9px;"
            "font-size:12px;font-weight:900;"
        )

        self.summary = QLabel("0 formateur")
        self.summary.setStyleSheet(
            "color:#0B2A52;font-size:10px;font-weight:900;"
        )

        note = QLabel(
            "Les liens peuvent pointer vers Google Sheets, Google Calendar, "
            "Microsoft 365 ou toute autre plateforme de disponibilités accessible en ligne."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color:#6B7C90;font-size:9px;"
        )

        info_layout.addWidget(info_icon)
        info_layout.addWidget(self.summary)
        info_layout.addSpacing(8)
        info_layout.addWidget(note, 1)

        root.addWidget(info)

        # ==============================================================
        # DIRECTORY CARD
        # ==============================================================
        directory = QFrame()
        directory.setObjectName("TrainerDirectory")
        directory.setStyleSheet(
            "QFrame#TrainerDirectory{background:#FFFFFF;"
            "border:1px solid #E2EAF3;border-radius:18px;}"
            "QLabel{background:transparent;border:none;}"
        )
        directory_layout = QVBoxLayout(directory)
        directory_layout.setContentsMargins(18, 16, 18, 18)
        directory_layout.setSpacing(12)

        directory_top = QHBoxLayout()
        directory_titles = QVBoxLayout()
        directory_titles.setSpacing(2)

        over = QLabel("ÉQUIPE PÉDAGOGIQUE")
        over.setStyleSheet(
            "color:#338CE4;font-size:9px;font-weight:900;letter-spacing:1px;"
        )
        directory_title = QLabel("Agendas & disponibilités")
        directory_title.setStyleSheet(
            "color:#0B1220;font-size:18px;font-weight:900;"
        )
        directory_sub = QLabel(
            "Retrouvez les spécialités, le statut et le planning de chaque formateur."
        )
        directory_sub.setStyleSheet(
            "color:#7A8A9E;font-size:10px;"
        )

        directory_titles.addWidget(over)
        directory_titles.addWidget(directory_title)
        directory_titles.addWidget(directory_sub)

        self.count_badge = QLabel("0 formateur")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setMinimumSize(94, 28)
        self.count_badge.setStyleSheet(
            "background:#EEF6FF;color:#1473C9;border:1px solid #CFE4F8;"
            "border-radius:9px;padding:0 9px;font-size:9px;font-weight:900;"
        )

        directory_top.addLayout(directory_titles, 1)
        directory_top.addWidget(self.count_badge, 0, Qt.AlignTop)
        directory_layout.addLayout(directory_top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                "Formateur",
                "Spécialités",
                "Statut",
                "Plateforme",
                "Planning",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setWordWrap(True)
        self.table.setMinimumHeight(340)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 105)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 185)

        self.table.setStyleSheet(
            "QTableWidget{background:#FFFFFF;color:#172033;"
            "border:1px solid #E4EBF4;border-radius:13px;"
            "selection-background-color:#EAF4FF;selection-color:#0B2A52;"
            "outline:none;font-size:10px;}"
            "QHeaderView::section{background:#0B2A52;color:#FFFFFF;"
            "border:none;border-right:1px solid #1A416C;"
            "padding:11px 8px;font-size:9px;font-weight:900;}"
            "QTableWidget::item{background:#FFFFFF;border:none;"
            "border-bottom:1px solid #EEF2F7;padding:11px 9px;}"
            "QTableWidget::item:selected{background:#EAF4FF;color:#0B2A52;"
            "border-left:3px solid #338CE4;}"
        )
        self.table.doubleClicked.connect(self._open_selected)
        directory_layout.addWidget(self.table, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "background:#F8FBFE;color:#718096;border:1px solid #E8EEF5;"
            "border-radius:10px;padding:9px 11px;font-size:9px;"
        )
        directory_layout.addWidget(self.status_label)

        root.addWidget(directory, 1)

        scroll.setWidget(content)
        page.addWidget(scroll)

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

    def rafraichir(self) -> None:
        if not self._can_view():
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(
                "Cette section est accessible aux administrateurs et aux commerciaux."
            )
            if hasattr(self, "kpi_values"):
                self.kpi_values["trainers"].setText("0")
                self.kpi_values["active"].setText("0")
                self.kpi_values["linked"].setText("0")
            if hasattr(self, "count_badge"):
                self.count_badge.setText("0 formateur")

            self.edit_link_button.setVisible(False)
            return

        is_admin = self._is_admin()
        self.edit_link_button.setVisible(is_admin)
        self.edit_link_button.setEnabled(is_admin)

        if not CloudRuntime.is_active():
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(
                "Connectez-vous à Form@Prospect Cloud pour consulter "
                "les disponibilités des formateurs."
            )
            if hasattr(self, "kpi_values"):
                self.kpi_values["trainers"].setText("0")
                self.kpi_values["active"].setText("0")
                self.kpi_values["linked"].setText("0")
            if hasattr(self, "count_badge"):
                self.count_badge.setText("0 formateur")

            return

        try:
            self.rows = CloudRuntime.api().list_cloud_trainers(
                include_inactive=is_admin
            )
        except CloudAPIError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(f"⛔ {exc}")
            return

        self.table.setRowCount(len(self.rows))
        for row_index in range(len(self.rows)):
            self.table.setRowHeight(row_index, 56)
        linked = 0
        active_count = 0

        for row_index, trainer in enumerate(self.rows):
            url = str(trainer.get("availability_url") or "").strip()
            active = bool(trainer.get("active"))
            if active:
                active_count += 1
            if url:
                linked += 1

            values = [
                trainer.get("full_name") or "",
                trainer.get("specialties") or "—",
                "Actif" if active else "Inactif",
                self._short_url(url),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignVCenter
                    | (Qt.AlignCenter if column == 2 else Qt.AlignLeft)
                )
                if column == 0:
                    item.setFont(item.font())
                if column == 3 and url:
                    item.setToolTip(url)
                self.table.setItem(row_index, column, item)

            status_badge = QLabel("●  Actif" if active else "●  Inactif")
            status_badge.setAlignment(Qt.AlignCenter)
            status_badge.setMinimumSize(82, 30)
            status_badge.setStyleSheet(
                (
                    "background:#ECFDF5;color:#087A45;border:1px solid #A7F3D0;"
                    "border-radius:9px;padding:0 12px;font-size:9px;font-weight:900;"
                )
                if active
                else
                (
                    "background:#F8FAFC;color:#64748B;border:1px solid #DCE4EC;"
                    "border-radius:9px;padding:0 12px;font-size:9px;font-weight:900;"
                )
            )
            self.table.setCellWidget(row_index, 2, status_badge)

            platform_badge = QLabel(self._short_url(url))
            platform_badge.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            platform_badge.setToolTip(url if url else "")
            platform_badge.setStyleSheet(
                (
                    "background:#F5F3FF;color:#6D28D9;border:1px solid #DDD6FE;"
                    "border-radius:9px;padding:6px 10px;font-size:9px;font-weight:800;"
                )
                if url
                else
                (
                    "background:#F8FAFC;color:#94A3B8;border:1px solid #E2E8F0;"
                    "border-radius:9px;padding:6px 10px;font-size:9px;font-weight:800;"
                )
            )
            self.table.setCellWidget(row_index, 3, platform_badge)

            open_button = QPushButton(
                "🌐  Consulter le planning"
                if url
                else "Planning non renseigné"
            )
            open_button.setCursor(Qt.PointingHandCursor)
            open_button.setMinimumSize(170, 36)
            open_button.setEnabled(bool(url))
            open_button.setStyleSheet(
                (
                    "QPushButton{background:#338CE4;color:#FFFFFF;border:none;"
                    "border-radius:9px;padding:0 16px;font-size:9px;font-weight:900;}"
                    "QPushButton:hover{background:#287FD4;}"
                )
                if url
                else
                (
                    "QPushButton{background:#EEF2F6;color:#94A3B8;border:none;"
                    "border-radius:9px;padding:0 16px;font-size:9px;font-weight:850;}"
                )
            )
            open_button.clicked.connect(
                lambda _checked=False, target=url: self._open_url(target)
            )
            self.table.setCellWidget(row_index, 4, open_button)

        self.summary.setText(
            f"{len(self.rows)} formateur(s) • {linked} agenda(s) renseigné(s)"
        )
        if hasattr(self, "count_badge"):
            self.count_badge.setText(
                f"{len(self.rows)} formateur" if len(self.rows) <= 1
                else f"{len(self.rows)} formateurs"
            )
        if hasattr(self, "kpi_values"):
            self.kpi_values["trainers"].setText(str(len(self.rows)))
            self.kpi_values["active"].setText(str(active_count))
            self.kpi_values["linked"].setText(str(linked))
        if is_admin:
            self.status_label.setText(
                "Double-cliquez sur un formateur pour ouvrir son agenda. "
                "Sélectionnez une ligne puis « Modifier le lien agenda » "
                "pour enregistrer ou remplacer son lien."
            )
            self.edit_link_button.setEnabled(True)
        else:
            self.status_label.setText(
                "Double-cliquez sur un formateur ou utilisez « Ouvrir » "
                "pour consulter ses disponibilités. La modification des liens "
                "reste réservée à l'administrateur."
            )

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
