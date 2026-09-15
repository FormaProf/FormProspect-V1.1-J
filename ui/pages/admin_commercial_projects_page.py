from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.session import SessionState


PUBLIC_LANDING_BASE_URL = "https://pilotage.forma-prof.fr/"


class ParentProjectDialog(QDialog):
    def __init__(self, parent=None, *, name="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Projet commercial")
        self.name_edit = QLineEdit(str(name or ""))
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(str(description or ""))

        form = QFormLayout(self)
        form.addRow("Nom", self.name_edit)
        form.addRow("Description", self.description_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
        )


class CommercialAssignmentDialog(QDialog):
    def __init__(self, parent=None, *, commercials=()):
        super().__init__(parent)
        self.setWindowTitle("Affecter un commercial")
        self.combo = QComboBox()

        for commercial in commercials:
            label = commercial.name
            if commercial.email:
                label = f"{label} — {commercial.email}"
            self.combo.addItem(label, commercial.id)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Commercial"))
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_user_id(self):
        return str(self.combo.currentData() or "").strip()


class ChildProjectDialog(QDialog):
    def __init__(self, parent=None, *, projects=()):
        super().__init__(parent)
        self.setWindowTitle("Rattacher un projet")
        self.combo = QComboBox()

        for project in projects:
            label = project.name
            if project.status:
                label = f"{label} — {project.status}"
            self.combo.addItem(label, project.id)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Projet disponible"))
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_project_id(self):
        return str(self.combo.currentData() or "").strip()


class AdminCommercialProjectsPage(QWidget):
    def __init__(self, *, service, auto_refresh=True):
        super().__init__()
        self.service = service
        self.snapshot = None
        self.parents = ()
        self._build_ui()
        if auto_refresh:
            self.rafraichir()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Projets commerciaux")
        title.setStyleSheet("font-size:24px; font-weight:800; color:#0B1220;")
        layout.addWidget(title)

        actions = QHBoxLayout()
        self.create_parent_button = QPushButton("Nouveau projet")
        self.create_parent_button.clicked.connect(self._on_create_parent_clicked)
        self.edit_parent_button = QPushButton("Modifier")
        self.edit_parent_button.clicked.connect(self._on_edit_parent_clicked)
        self.toggle_parent_button = QPushButton("Désactiver")
        self.toggle_parent_button.clicked.connect(self._on_toggle_parent_clicked)

        actions.addWidget(self.create_parent_button)
        actions.addWidget(self.edit_parent_button)
        actions.addWidget(self.toggle_parent_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.parent_table = QTableWidget(0, 5)
        self.parent_table.setHorizontalHeaderLabels([
            "Projet", "Description", "État", "Commerciaux", "Projets enfants"
        ])
        self.parent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.parent_table)

        commercial_actions = QHBoxLayout()
        self.add_commercial_button = QPushButton("Affecter un commercial")
        self.add_commercial_button.clicked.connect(self._on_add_commercial_clicked)
        self.remove_commercial_button = QPushButton("Retirer")
        self.remove_commercial_button.clicked.connect(self._on_remove_commercial_clicked)
        commercial_actions.addWidget(self.add_commercial_button)
        commercial_actions.addWidget(self.remove_commercial_button)
        commercial_actions.addStretch(1)
        layout.addLayout(commercial_actions)

        self.commercial_table = QTableWidget(0, 3)
        self.commercial_table.setHorizontalHeaderLabels([
            "Commercial", "E-mail", "État"
        ])
        self.commercial_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.commercial_table)

        project_actions = QHBoxLayout()
        self.attach_project_button = QPushButton("Rattacher un projet")
        self.attach_project_button.clicked.connect(self._on_attach_project_clicked)
        self.detach_project_button = QPushButton("Détacher")
        self.detach_project_button.clicked.connect(self._on_detach_project_clicked)
        project_actions.addWidget(self.attach_project_button)
        project_actions.addWidget(self.detach_project_button)
        project_actions.addStretch(1)
        layout.addLayout(project_actions)

        self.project_table = QTableWidget(0, 2)
        self.project_table.setHorizontalHeaderLabels(["Projet enfant", "Statut"])
        self.project_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.project_table)

        self.available_project_count = QLabel("0 projet disponible")
        layout.addWidget(self.available_project_count)

        self.landing_title = QLabel("Landing Page")
        self.landing_title.setStyleSheet(
            "font-size:18px; font-weight:700; color:#0B1220;"
        )
        layout.addWidget(self.landing_title)

        landing_form = QFormLayout()
        self.landing_commercial_label = QLabel("—")
        self.landing_status_label = QLabel("Aucun lien")
        self.landing_url_edit = QLineEdit()
        self.landing_url_edit.setReadOnly(True)
        landing_form.addRow("Commercial", self.landing_commercial_label)
        landing_form.addRow("Statut", self.landing_status_label)
        landing_form.addRow("Lien", self.landing_url_edit)
        layout.addLayout(landing_form)

        landing_actions = QHBoxLayout()
        self.create_landing_button = QPushButton("Créer le lien")
        self.create_landing_button.clicked.connect(self._on_create_landing_clicked)
        self.copy_landing_button = QPushButton("Copier")
        self.copy_landing_button.clicked.connect(self._on_copy_landing_clicked)
        self.open_landing_button = QPushButton("Ouvrir")
        self.open_landing_button.clicked.connect(self._on_open_landing_clicked)
        self.toggle_landing_button = QPushButton("Désactiver")
        self.toggle_landing_button.clicked.connect(self._on_toggle_landing_clicked)
        landing_actions.addWidget(self.create_landing_button)
        landing_actions.addWidget(self.copy_landing_button)
        landing_actions.addWidget(self.open_landing_button)
        landing_actions.addWidget(self.toggle_landing_button)
        landing_actions.addStretch(1)
        layout.addLayout(landing_actions)

        self.parent_table.currentCellChanged.connect(
            self._parent_selection_changed
        )
        self.project_table.currentCellChanged.connect(
            self._project_selection_changed
        )

    @staticmethod
    def _item(value):
        return QTableWidgetItem(str(value or ""))

    def rafraichir(self, *_args):
        if not SessionState.has_role("Administrateur"):
            self.parent_table.setRowCount(0)
            self.commercial_table.setRowCount(0)
            self.project_table.setRowCount(0)
            self.available_project_count.setText("0 projet disponible")
            return

        self.snapshot = self.service.load()
        self.parents = tuple(self.snapshot.parents)
        self.parent_table.setRowCount(len(self.parents))

        for row, parent in enumerate(self.parents):
            self.parent_table.setItem(row, 0, self._item(parent.name))
            self.parent_table.setItem(row, 1, self._item(parent.description))
            self.parent_table.setItem(row, 2, self._item(
                "Actif" if parent.is_active else "Inactif"
            ))
            self.parent_table.setItem(
                row, 3, self._item(len(parent.assigned_commercials))
            )
            self.parent_table.setItem(
                row, 4, self._item(len(parent.projects))
            )

        count = len(self.snapshot.ungrouped_projects)
        suffix = "projet disponible" if count == 1 else "projets disponibles"
        self.available_project_count.setText(f"{count} {suffix}")

        if self.parents:
            self.parent_table.selectRow(0)
            self._show_parent(self.parents[0])
        else:
            self._show_parent(None)

    def _parent_selection_changed(self, row, _column, _old_row, _old_column):
        if 0 <= row < len(self.parents):
            self._show_parent(self.parents[row])

    def _clear_landing(self):
        self.landing_commercial_label.setText("—")
        self.landing_status_label.setText("Aucun lien")
        self.landing_url_edit.clear()

    def _project_selection_changed(self, row, _column, _old_row, _old_column):
        parent = self._selected_parent()
        projects = tuple(parent.projects) if parent else ()
        if not 0 <= row < len(projects):
            self._clear_landing()
            return

        project = projects[row]
        commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        if not commercial_user_id:
            self._clear_landing()
            return

        commercial_name = commercial_user_id
        if self.snapshot is not None:
            for commercial in self.snapshot.commercials:
                if commercial.id == commercial_user_id:
                    commercial_name = (
                        commercial.name
                        or commercial.email
                        or commercial_user_id
                    )
                    break

        self.landing_commercial_label.setText(commercial_name)

        getter = getattr(self.service, "get_landing", None)
        if getter is None:
            self.landing_status_label.setText("Aucun lien")
            self.landing_url_edit.clear()
            return

        landing = getter(project.id, commercial_user_id)
        if landing is None:
            self.landing_status_label.setText("Aucun lien")
            self.landing_url_edit.clear()
            return

        self.landing_status_label.setText(
            "Actif" if landing.is_active else "Inactif"
        )
        self.toggle_landing_button.setText(
            "Désactiver" if landing.is_active else "Activer"
        )
        if landing.organization_id and landing.token:
            self.landing_url_edit.setText(
                f"{PUBLIC_LANDING_BASE_URL}"
                f"?organization_id={landing.organization_id}"
                f"&token={landing.token}"
            )
        else:
            self.landing_url_edit.clear()

    def _on_create_landing_clicked(self, *_args):
        if not SessionState.has_role("Administrateur"):
            return

        parent = self._selected_parent()
        row = self.project_table.currentRow()
        projects = tuple(parent.projects) if parent else ()
        if not 0 <= row < len(projects):
            return

        project = projects[row]
        commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        if not commercial_user_id:
            return

        creator = getattr(self.service, "ensure_landing", None)
        if creator is None:
            return

        landing = creator(project.id, commercial_user_id)
        self.landing_status_label.setText(
            "Actif" if landing.is_active else "Inactif"
        )
        if landing.organization_id and landing.token:
            self.landing_url_edit.setText(
                f"{PUBLIC_LANDING_BASE_URL}"
                f"?organization_id={landing.organization_id}"
                f"&token={landing.token}"
            )
        else:
            self.landing_url_edit.clear()

    def _on_toggle_landing_clicked(self, *_args):
        if not SessionState.has_role("Administrateur"):
            return

        parent = self._selected_parent()
        row = self.project_table.currentRow()
        projects = tuple(parent.projects) if parent else ()
        if not 0 <= row < len(projects):
            return

        project = projects[row]
        commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        if not commercial_user_id:
            return

        getter = getattr(self.service, "get_landing", None)
        setter = getattr(self.service, "set_landing_active", None)
        if getter is None or setter is None:
            return

        landing = getter(project.id, commercial_user_id)
        if landing is None:
            return

        updated = setter(
            project.id,
            commercial_user_id,
            not landing.is_active,
        )
        self.landing_status_label.setText(
            "Actif" if updated.is_active else "Inactif"
        )
        self.toggle_landing_button.setText(
            "Désactiver" if updated.is_active else "Activer"
        )

    def _on_copy_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if not url:
            return
        QApplication.clipboard().setText(url)

    def _on_open_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))

    def _show_parent(self, parent):
        self._clear_landing()
        if parent is None:
            self.toggle_parent_button.setText("Désactiver")
        else:
            self.toggle_parent_button.setText(
                "Désactiver" if parent.is_active else "Activer"
            )
        commercials = tuple(parent.assigned_commercials) if parent else ()
        projects = tuple(parent.projects) if parent else ()
        self.commercial_table.setRowCount(len(commercials))
        self.project_table.setRowCount(len(projects))

        for row, commercial in enumerate(commercials):
            self.commercial_table.setItem(row, 0, self._item(commercial.name))
            self.commercial_table.setItem(row, 1, self._item(commercial.email))
            self.commercial_table.setItem(
                row, 2, self._item(
                    "Actif" if commercial.is_active else "Inactif"
                )
            )

        for row, project in enumerate(projects):
            self.project_table.setItem(row, 0, self._item(project.name))
            self.project_table.setItem(row, 1, self._item(project.status))

    def _create_parent(self, name, description):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.create_parent(name, description)
        self.rafraichir()

    def _update_parent(self, parent_id, name, description):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.update_parent(parent_id, name, description)
        self.rafraichir()

    def _set_parent_active(self, parent_id, is_active):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.set_parent_active(parent_id, is_active)
        self.rafraichir()

    def _assign_commercial(self, parent_id, user_id):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.assign_commercial(parent_id, user_id)
        self.rafraichir()

    def _remove_commercial(self, parent_id, user_id):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.remove_commercial(parent_id, user_id)
        self.rafraichir()

    def _attach_project(self, parent_id, project_id):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.attach_project(parent_id, project_id)
        self.rafraichir()

    def _detach_project(self, project_id):
        if not SessionState.has_role("Administrateur"):
            return
        self.service.detach_project(project_id)
        self.rafraichir()


    def _selected_parent(self):
        row = self.parent_table.currentRow()
        if 0 <= row < len(self.parents):
            return self.parents[row]
        return None

    def _on_toggle_parent_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None:
            return
        self._set_parent_active(parent.id, not parent.is_active)


    def _on_create_parent_clicked(self, *_args):
        dialog = ParentProjectDialog(self)
        if not dialog.exec():
            return
        name, description = dialog.values()
        if not name:
            return
        self._create_parent(name, description)

    def _on_edit_parent_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None:
            return
        dialog = ParentProjectDialog(
            self,
            name=parent.name,
            description=parent.description,
        )
        if not dialog.exec():
            return
        name, description = dialog.values()
        if not name:
            return
        self._update_parent(parent.id, name, description)


    def _on_add_commercial_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None or self.snapshot is None:
            return

        assigned_ids = {
            commercial.id for commercial in parent.assigned_commercials
        }
        available = tuple(
            commercial
            for commercial in self.snapshot.commercials
            if commercial.is_active and commercial.id not in assigned_ids
        )
        if not available:
            return

        dialog = CommercialAssignmentDialog(self, commercials=available)
        if not dialog.exec():
            return
        user_id = dialog.selected_user_id()
        if user_id:
            self._assign_commercial(parent.id, user_id)

    def _on_remove_commercial_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None:
            return

        row = self.commercial_table.currentRow()
        commercials = tuple(parent.assigned_commercials)
        if not 0 <= row < len(commercials):
            return

        self._remove_commercial(
            parent.id,
            commercials[row].id,
        )

    def _on_attach_project_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None or self.snapshot is None:
            return

        available = tuple(self.snapshot.ungrouped_projects)
        if not available:
            return

        dialog = ChildProjectDialog(self, projects=available)
        if not dialog.exec():
            return

        project_id = dialog.selected_project_id()
        if project_id:
            self._attach_project(parent.id, project_id)

    def _on_detach_project_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None:
            return

        row = self.project_table.currentRow()
        projects = tuple(parent.projects)
        if not 0 <= row < len(projects):
            return

        self._detach_project(projects[row].id)
