from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class CommercialProjectsPage(QWidget):
    project_open_requested = Signal(str)

    def __init__(self, *, service, user_id: str, auto_refresh: bool = True):
        super().__init__()
        self.service = service
        self.user_id = str(user_id or "").strip()
        self.parent_buttons = {}
        self.child_buttons = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(34, 30, 34, 42)
        self.layout.setSpacing(14)

        title = QLabel("Mes projets commerciaux")
        title.setStyleSheet("font-size:28px; font-weight:800; color:#0B1220;")
        self.layout.addWidget(title)

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

        if auto_refresh:
            self.rafraichir()

    def rafraichir(self):
        self.back_button.hide()

        for button in self.parent_buttons.values():
            button.deleteLater()
        self.parent_buttons.clear()

        for button in self.child_buttons.values():
            self.layout.removeWidget(button)
            button.deleteLater()
        self.child_buttons.clear()

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
            button = QPushButton(
                f"{parent.name}\n{len(parent.projects)} projet(s) - {parent.prospect_count} prospect(s)"
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
            button = QPushButton(project_name)
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(64)
            button.clicked.connect(lambda _checked=False, pid=project_id: self.project_open_requested.emit(pid))
            self.child_buttons[project_id] = button
            self.layout.addWidget(button)
