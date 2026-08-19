from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.cloud_api_client import CloudAPIError, CloudAPIClient


class ProjectArchiveDialog(QDialog):
    """Centre d'archivage/restauration des projets Cloud."""

    def __init__(self, api: CloudAPIClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.active_projects: list[dict] = []
        self.archived_projects: list[dict] = []

        self.setWindowTitle("Gestion des projets · Archives")
        self.resize(920, 620)
        self.setMinimumSize(820, 540)
        self.setStyleSheet("background:#F8FAFD;")

        self._build_ui()
        self.refresh_projects()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        hero = QFrame()
        hero.setStyleSheet(
            "QFrame {background:#071B38; border:none; border-radius:18px;}"
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)

        title = QLabel("📦  Cycle de vie des projets")
        title.setStyleSheet(
            "font-size:22px; font-weight:900; color:white; background:transparent;"
        )

        subtitle = QLabel(
            "Archivez les projets terminés sans supprimer leurs données. "
            "Ils peuvent être restaurés à tout moment."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size:12px; color:#C8D8EC; background:transparent;"
        )

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border:1px solid #E7ECF3;
                background:white;
                border-radius:14px;
                top:-1px;
            }
            QTabBar::tab {
                background:#EEF3F8;
                color:#52647A;
                padding:10px 18px;
                margin-right:4px;
                border-top-left-radius:9px;
                border-top-right-radius:9px;
                font-weight:800;
            }
            QTabBar::tab:selected {
                background:#338CE4;
                color:white;
            }
            """
        )

        active_page = QWidget()
        active_layout = QVBoxLayout(active_page)
        active_layout.setContentsMargins(14, 14, 14, 14)
        self.active_table = self._new_table()
        active_layout.addWidget(self.active_table)

        active_actions = QHBoxLayout()
        self.archive_button = QPushButton("📦 Archiver le projet sélectionné")
        self.archive_button.clicked.connect(self.archive_selected)
        self.archive_button.setStyleSheet(self._primary_button())
        active_actions.addStretch()
        active_actions.addWidget(self.archive_button)
        active_layout.addLayout(active_actions)

        archived_page = QWidget()
        archived_layout = QVBoxLayout(archived_page)
        archived_layout.setContentsMargins(14, 14, 14, 14)
        self.archived_table = self._new_table()
        archived_layout.addWidget(self.archived_table)

        archived_actions = QHBoxLayout()
        self.restore_button = QPushButton("↩ Restaurer le projet sélectionné")
        self.restore_button.clicked.connect(self.restore_selected)
        self.restore_button.setStyleSheet(self._secondary_button())
        archived_actions.addStretch()
        archived_actions.addWidget(self.restore_button)
        archived_layout.addLayout(archived_actions)

        self.tabs.addTab(active_page, "Projets actifs")
        self.tabs.addTab(archived_page, "Archives")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size:11px; color:#6B7A90;")

        refresh = QPushButton("↻ Rafraîchir")
        refresh.clicked.connect(self.refresh_projects)
        refresh.setStyleSheet(self._secondary_button())

        close = QPushButton("Fermer")
        close.clicked.connect(self.accept)
        close.setStyleSheet(self._secondary_button())

        footer.addWidget(self.info_label)
        footer.addStretch()
        footer.addWidget(refresh)
        footer.addWidget(close)
        root.addLayout(footer)

    @staticmethod
    def _new_table() -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(
            ["Projet", "Statut", "Affectation", "Dernière modification"]
        )
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 285)
        table.setColumnWidth(1, 130)
        table.setColumnWidth(2, 220)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(
            """
            QTableWidget {
                background:white;
                alternate-background-color:#F8FAFD;
                border:1px solid #E7ECF3;
                border-radius:10px;
                gridline-color:#EEF2F6;
                color:#17253A;
                font-size:12px;
            }
            QHeaderView::section {
                background:#F2F6FA;
                color:#52647A;
                border:none;
                border-bottom:1px solid #DDE6F0;
                padding:9px;
                font-weight:800;
            }
            QTableWidget::item:selected {
                background:#EAF4FF;
                color:#0B1220;
            }
            """
        )
        return table

    @staticmethod
    def _primary_button() -> str:
        return """
            QPushButton {
                background:#338CE4; color:white; border:none;
                border-radius:10px; padding:10px 16px; font-weight:800;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:disabled { background:#DCE4EC; color:#94A3B8; }
        """

    @staticmethod
    def _secondary_button() -> str:
        return """
            QPushButton {
                background:white; color:#23344D; border:1px solid #DDE6F0;
                border-radius:10px; padding:9px 14px; font-weight:800;
            }
            QPushButton:hover { border-color:#9EC6EE; color:#338CE4; }
            QPushButton:disabled { color:#94A3B8; background:#F4F6F8; }
        """

    @staticmethod
    def _format_datetime(value) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "—"
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.astimezone().strftime("%d/%m/%Y %H:%M")
        except Exception:
            return raw[:16].replace("T", " ")

    @staticmethod
    def _assignee_label(item: dict) -> str:
        for key in (
            "assigned_to_name",
            "assignee_name",
            "assigned_to_email",
            "assignee_email",
        ):
            value = str(item.get(key) or "").strip()
            if value:
                return value
        assigned_to = str(item.get("assigned_to") or "").strip()
        return assigned_to if assigned_to else "Non affecté"

    def refresh_projects(self) -> None:
        self.archive_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.info_label.setText("Chargement des projets Cloud…")

        try:
            page = self.api.list_projects(
                include_archived=True,
                limit=500,
                offset=0,
                sort_by="updated_at",
                sort_direction="desc",
            )
        except Exception as exc:
            self.info_label.setText("Impossible de charger les projets.")
            QMessageBox.warning(
                self,
                "Archives indisponibles",
                str(exc),
            )
            return

        projects = [
            item for item in page.items
            if not bool(item.get("is_system"))
        ]

        self.active_projects = [
            item for item in projects
            if str(item.get("status") or "").lower() != "archived"
        ]

        self.archived_projects = [
            item for item in projects
            if str(item.get("status") or "").lower() == "archived"
        ]

        self._populate(self.active_table, self.active_projects)
        self._populate(self.archived_table, self.archived_projects)

        self.tabs.setTabText(
            0,
            f"Projets actifs ({len(self.active_projects)})",
        )
        self.tabs.setTabText(
            1,
            f"Archives ({len(self.archived_projects)})",
        )

        self.info_label.setText(
            f"{len(self.active_projects)} actif(s) • "
            f"{len(self.archived_projects)} archivé(s)"
        )

        self.archive_button.setEnabled(bool(self.active_projects))
        self.restore_button.setEnabled(bool(self.archived_projects))

    def _populate(self, table: QTableWidget, projects: list[dict]) -> None:
        table.setRowCount(len(projects))

        for row, item in enumerate(projects):
            values = (
                str(item.get("name") or "Projet sans nom"),
                str(item.get("status") or "—"),
                self._assignee_label(item),
                self._format_datetime(
                    item.get("updated_at") or item.get("created_at")
                ),
            )

            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.UserRole, str(item.get("id") or ""))
                table.setItem(row, column, cell)

    @staticmethod
    def _selected_project(
        table: QTableWidget,
        projects: list[dict],
    ) -> dict | None:
        row = table.currentRow()
        if row < 0 or row >= len(projects):
            return None
        return projects[row]

    def archive_selected(self) -> None:
        project = self._selected_project(
            self.active_table,
            self.active_projects,
        )

        if project is None:
            QMessageBox.information(
                self,
                "Archiver",
                "Sélectionnez d'abord un projet actif.",
            )
            return

        project_name = str(project.get("name") or "ce projet")

        answer = QMessageBox.question(
            self,
            "Confirmer l'archivage",
            (
                f"Archiver « {project_name} » ?\n\n"
                "Aucune donnée ne sera supprimée. "
                "Le projet pourra être restauré à tout moment."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            self.api.archive_project(str(project["id"]))
        except CloudAPIError as exc:
            QMessageBox.warning(self, "Archivage impossible", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'archivage", str(exc))
            return

        QMessageBox.information(
            self,
            "Projet archivé",
            f"« {project_name} » a été archivé.",
        )

        self.refresh_projects()
        self.tabs.setCurrentIndex(1)

    def restore_selected(self) -> None:
        project = self._selected_project(
            self.archived_table,
            self.archived_projects,
        )

        if project is None:
            QMessageBox.information(
                self,
                "Restaurer",
                "Sélectionnez d'abord un projet archivé.",
            )
            return

        project_name = str(project.get("name") or "ce projet")

        answer = QMessageBox.question(
            self,
            "Confirmer la restauration",
            f"Restaurer « {project_name} » dans les projets actifs ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            self.api.restore_project(str(project["id"]))
        except CloudAPIError as exc:
            QMessageBox.warning(self, "Restauration impossible", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de restauration", str(exc))
            return

        QMessageBox.information(
            self,
            "Projet restauré",
            f"« {project_name} » est de nouveau actif.",
        )

        self.refresh_projects()
        self.tabs.setCurrentIndex(0)
