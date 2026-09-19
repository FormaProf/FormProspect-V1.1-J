from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget,
)


class CommercialProjectsPage(QWidget):
    project_open_requested = Signal(str)

    def __init__(
        self,
        *,
        service,
        user_id: str,
        workspace_mode: str = "commercial",
        auto_refresh: bool = True,
    ):
        super().__init__()
        self.service = service
        self.user_id = str(user_id or "").strip()
        self.workspace_mode = (
            "manager"
            if str(workspace_mode or "").strip().lower() == "manager"
            else "commercial"
        )
        self.parent_buttons = {}
        self.child_buttons = {}
        self.landing_buttons = {}
        self._landing_project_id = ""
        self._current_landing = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(34, 30, 34, 42)
        self.layout.setSpacing(14)

        title_text = (
            "Projets de mon équipe"
            if self.workspace_mode == "manager"
            else "Mes projets commerciaux"
        )
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(
            "font-size:28px; font-weight:800; color:#0B1220;"
        )
        self.layout.addWidget(self.title_label)

        subtitle = QLabel("Choisissez votre univers commercial puis le projet sur lequel vous souhaitez travailler.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:13px; color:#6B7A90;")
        self.layout.addWidget(subtitle)

        self.empty_label = QLabel("Aucun projet disponible pour le moment.")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("font-size:14px; color:#6B7A90; padding:18px 0;")
        self.empty_label.hide()
        self.layout.addWidget(self.empty_label)

        self.back_button = QPushButton("Retour")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.hide()
        self.back_button.clicked.connect(self.rafraichir)
        self.layout.addWidget(self.back_button)

        self._build_landing_panel()

        if auto_refresh:
            self.rafraichir()

    def _build_landing_panel(self):
        self.landing_panel = QWidget()
        panel_layout = QVBoxLayout(self.landing_panel)
        panel_layout.setContentsMargins(0, 18, 0, 0)
        panel_layout.setSpacing(10)

        self.landing_title_label = QLabel("Ma Landing Page")
        panel_layout.addWidget(self.landing_title_label)

        self.landing_status_label = QLabel("Aucun lien")
        panel_layout.addWidget(self.landing_status_label)

        self.landing_url_edit = QLineEdit()
        self.landing_url_edit.setReadOnly(True)
        panel_layout.addWidget(self.landing_url_edit)

        actions = QHBoxLayout()
        self.create_landing_button = QPushButton("Créer mon lien")
        self.copy_landing_button = QPushButton("Copier")
        self.open_landing_button = QPushButton("Ouvrir")
        self.toggle_landing_button = QPushButton("Désactiver")

        self.create_landing_button.clicked.connect(self._on_create_landing_clicked)
        self.copy_landing_button.clicked.connect(self._on_copy_landing_clicked)
        self.open_landing_button.clicked.connect(self._on_open_landing_clicked)
        self.toggle_landing_button.clicked.connect(self._on_toggle_landing_clicked)

        actions.addWidget(self.create_landing_button)
        actions.addWidget(self.copy_landing_button)
        actions.addWidget(self.open_landing_button)
        actions.addWidget(self.toggle_landing_button)
        actions.addStretch(1)
        panel_layout.addLayout(actions)

        self.landing_panel.hide()
        self.layout.addWidget(self.landing_panel)

    @staticmethod
    def _landing_public_url(landing):
        organization_id = str(getattr(landing, "organization_id", "") or "").strip()
        token = str(getattr(landing, "token", "") or "").strip()
        if not organization_id or not token:
            return ""
        return (
            "https://pilotage.forma-prof.fr/"
            f"?organization_id={organization_id}&token={token}"
        )

    def _render_landing(self, landing):
        self._current_landing = landing
        self.landing_panel.show()

        if landing is None:
            self.landing_status_label.setText("Aucun lien")
            self.landing_url_edit.clear()
            self.create_landing_button.setEnabled(True)
            self.copy_landing_button.setEnabled(False)
            self.open_landing_button.setEnabled(False)
            self.toggle_landing_button.setEnabled(False)
            return

        self.landing_status_label.setText("Actif" if landing.is_active else "Inactif")
        self.landing_url_edit.setText(self._landing_public_url(landing))
        self.toggle_landing_button.setText("Désactiver" if landing.is_active else "Activer")
        self.create_landing_button.setEnabled(False)
        has_url = bool(self.landing_url_edit.text().strip())
        self.copy_landing_button.setEnabled(has_url)
        self.open_landing_button.setEnabled(has_url)
        self.toggle_landing_button.setEnabled(True)

    def _show_landing(self, project_id):
        project_id = str(project_id or "").strip()
        if not project_id or self.workspace_mode != "commercial":
            return
        self._landing_project_id = project_id
        self._render_landing(self.service.get_landing(project_id))

    def _on_create_landing_clicked(self, *_args):
        if not self._landing_project_id:
            return
        landing = self.service.ensure_landing(self._landing_project_id)
        self._render_landing(landing)

    def _on_toggle_landing_clicked(self, *_args):
        if not self._landing_project_id or self._current_landing is None:
            return
        landing = self.service.set_landing_active(
            self._landing_project_id,
            not self._current_landing.is_active,
        )
        self._render_landing(landing)

    def _on_copy_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if url:
            QApplication.clipboard().setText(url)

    def _on_open_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def rafraichir(self):
        self.back_button.hide()

        for button in self.parent_buttons.values():
            button.deleteLater()
        self.parent_buttons.clear()

        for button in self.child_buttons.values():
            self.layout.removeWidget(button)
            button.deleteLater()
        self.child_buttons.clear()

        for button in self.landing_buttons.values():
            self.layout.removeWidget(button)
            button.deleteLater()
        self.landing_buttons.clear()
        self._landing_project_id = ""
        self._current_landing = None
        self.landing_panel.hide()

        if self.workspace_mode == "manager":
            parents = self.service.list_for_manager()
        else:
            parents = self.service.list_for_commercial(self.user_id)
        self.empty_label.hide()

        if not parents:
            self.empty_label.show()
            return

        if len(parents) == 1:
            only_parent = parents[0]
            projects = tuple(getattr(only_parent, "projects", ()) or ())
            if not projects:
                self.empty_label.show()
                return
            if len(projects) > 1:
                self._show_child_choices(only_parent)
                return

        for parent in parents:
            lead_chaud_count = int(getattr(parent, "lead_chaud_count", 0) or 0)
            button = QPushButton(
                f"{parent.name}\n{len(parent.projects)} projet(s) - {parent.prospect_count} prospect(s) - {lead_chaud_count} lead(s) chaud(s)"
            )
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(86)
            button.setStyleSheet(
                "QPushButton { text-align:left; padding:16px 20px; font-size:15px; font-weight:700; color:#0B1220; background:white; border:1px solid #E7ECF3; border-radius:14px; }"
                "QPushButton:hover { border:1px solid #338CE4; background:#F8FBFF; }"
            )
            button.clicked.connect(lambda _checked=False, current_parent=parent: self._on_parent_clicked(current_parent))
            self.parent_buttons[parent.id] = button
            self.layout.addWidget(button)

            projects = tuple(getattr(parent, "projects", ()) or ())
            if self.workspace_mode == "commercial" and len(projects) == 1:
                project_id = str(getattr(projects[0], "id", "") or "").strip()
                if project_id:
                    landing_button = QPushButton("Ma Landing Page")
                    landing_button.setCursor(Qt.PointingHandCursor)
                    landing_button.clicked.connect(
                        lambda _checked=False, pid=project_id: self._show_landing(pid)
                    )
                    self.landing_buttons[project_id] = landing_button
                    self.layout.addWidget(landing_button)


    def _on_parent_clicked(self, parent):
        projects = tuple(getattr(parent, "projects", ()) or ())
        if len(projects) > 1:
            self._show_child_choices(parent)
            return

        if not projects:
            had_parent_choices = bool(self.parent_buttons)
            for button in self.parent_buttons.values():
                self.layout.removeWidget(button)
                button.hide()
                button.deleteLater()
            self.parent_buttons.clear()
            if had_parent_choices:
                self.back_button.show()
            self.empty_label.show()
            return

        if len(projects) != 1:
            return

        project_id = str(getattr(projects[0], "id", "") or "").strip()
        if project_id:
            self.project_open_requested.emit(project_id)

    def _show_child_choices(self, parent):
        had_parent_choices = bool(self.parent_buttons)

        for button in self.parent_buttons.values():
            self.layout.removeWidget(button)
            button.hide()
            button.deleteLater()
        self.parent_buttons.clear()
        self.back_button.setVisible(had_parent_choices)

        for button in self.child_buttons.values():
            self.layout.removeWidget(button)
            button.deleteLater()
        self.child_buttons.clear()

        projects = tuple(getattr(parent, "projects", ()) or ())
        for project in projects:
            project_id = str(getattr(project, "id", "") or "").strip()
            if not project_id:
                continue
            project_name = str(getattr(project, "name", "") or "Projet").strip()
            prospect_count = int(getattr(project, "prospect_count", 0) or 0)
            lead_chaud_count = int((getattr(parent, "lead_chaud_by_project", {}) or {}).get(project_id, 0) or 0)
            button = QPushButton(
                f"{project_name}\n{prospect_count} prospect(s) - {lead_chaud_count} lead(s) chaud(s)"
            )
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(64)
            button.clicked.connect(lambda _checked=False, pid=project_id: self.project_open_requested.emit(pid))
            self.child_buttons[project_id] = button
            self.layout.addWidget(button)

            if self.workspace_mode == "commercial":
                landing_button = QPushButton("Ma Landing Page")
                landing_button.setCursor(Qt.PointingHandCursor)
                landing_button.clicked.connect(
                    lambda _checked=False, pid=project_id: self._show_landing(pid)
                )
                self.landing_buttons[project_id] = landing_button
                self.layout.addWidget(landing_button)
