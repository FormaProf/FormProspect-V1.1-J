from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from core.theme_settings import THEME_CLASSIC
from ui.commercial_projects_theme import (
    add_soft_shadow,
    apply_project_dialog_theme,
    projects_palette,
    projects_stylesheet,
    projects_theme_mode,
)


PUBLIC_LANDING_BASE_URL = "https://pilotage.forma-prof.fr/"


class ParentProjectDialog(QDialog):
    def __init__(self, parent=None, *, name="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Projet commercial")
        self.resize(520, 300)
        self.name_edit = QLineEdit(str(name or ""))
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(str(description or ""))
        self.description_edit.setMinimumHeight(120)

        form = QFormLayout(self)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        form.addRow("Nom", self.name_edit)
        form.addRow("Description", self.description_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        apply_project_dialog_theme(self)

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.description_edit.toPlainText().strip(),
        )


class CommercialAssignmentDialog(QDialog):
    def __init__(self, parent=None, *, commercials=()):
        super().__init__(parent)
        self.setWindowTitle("Affecter un commercial")
        self.resize(470, 180)
        self.combo = QComboBox()

        for commercial in commercials:
            label = commercial.name
            if commercial.email:
                label = f"{label} — {commercial.email}"
            self.combo.addItem(label, commercial.id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Commercial"))
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        apply_project_dialog_theme(self)

    def selected_user_id(self):
        return str(self.combo.currentData() or "").strip()


class ChildProjectDialog(QDialog):
    def __init__(self, parent=None, *, projects=()):
        super().__init__(parent)
        self.setWindowTitle("Rattacher un projet")
        self.resize(470, 180)
        self.combo = QComboBox()

        for project in projects:
            label = project.name
            if project.status:
                label = f"{label} — {project.status}"
            self.combo.addItem(label, project.id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Projet disponible"))
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        apply_project_dialog_theme(self)

    def selected_project_id(self):
        return str(self.combo.currentData() or "").strip()


class AdminCommercialProjectsPage(QWidget):
    def __init__(self, *, service, auto_refresh=True):
        super().__init__()
        self.service = service
        self.snapshot = None
        self.parents = ()
        self._theme_mode = projects_theme_mode()

        # 8E unified UI: the progressive premium hierarchy is the only
        # structural layout. Themes now change palette only.
        self._classic_mode = False
        self._project_view_filtered = False
        self._visible_projects = ()
        self._premium_parent_revealed = False
        self._premium_commercial_revealed = False
        self._theme_sync_window = None
        self._build_ui()
        if auto_refresh:
            self.rafraichir()

    def _build_ui(self):
        if self._classic_mode:
            self._build_classic_ui()
        else:
            self._build_premium_ui()

        self.parent_table.currentCellChanged.connect(
            self._parent_selection_changed
        )
        self.commercial_table.currentCellChanged.connect(
            self._commercial_selection_changed
        )
        self.project_table.currentCellChanged.connect(
            self._project_selection_changed
        )
        self.parent_table.cellClicked.connect(self._parent_activated)
        self.commercial_table.cellClicked.connect(self._commercial_activated)

    def _build_classic_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Projets commerciaux")
        title.setStyleSheet(
            "font-size:24px; font-weight:800; color:#0B1220;"
        )
        layout.addWidget(title)

        actions = QHBoxLayout()
        self.create_parent_button = QPushButton("Nouveau projet")
        self.create_parent_button.clicked.connect(
            self._on_create_parent_clicked
        )
        self.edit_parent_button = QPushButton("Modifier")
        self.edit_parent_button.clicked.connect(
            self._on_edit_parent_clicked
        )
        self.toggle_parent_button = QPushButton("Désactiver")
        self.toggle_parent_button.clicked.connect(
            self._on_toggle_parent_clicked
        )

        actions.addWidget(self.create_parent_button)
        actions.addWidget(self.edit_parent_button)
        actions.addWidget(self.toggle_parent_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.parent_table = QTableWidget(0, 5)
        self.parent_table.setHorizontalHeaderLabels([
            "Projet",
            "Description",
            "État",
            "Commerciaux",
            "Projets enfants",
        ])
        self.parent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.parent_table)

        commercial_actions = QHBoxLayout()
        self.add_commercial_button = QPushButton(
            "Affecter un commercial"
        )
        self.add_commercial_button.clicked.connect(
            self._on_add_commercial_clicked
        )
        self.remove_commercial_button = QPushButton("Retirer")
        self.remove_commercial_button.clicked.connect(
            self._on_remove_commercial_clicked
        )
        commercial_actions.addWidget(self.add_commercial_button)
        commercial_actions.addWidget(self.remove_commercial_button)
        commercial_actions.addStretch(1)
        layout.addLayout(commercial_actions)

        self.commercial_table = QTableWidget(0, 3)
        self.commercial_table.setHorizontalHeaderLabels([
            "Commercial", "E-mail", "État"
        ])
        self.commercial_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.commercial_table)

        project_actions = QHBoxLayout()
        self.attach_project_button = QPushButton("Rattacher un projet")
        self.attach_project_button.clicked.connect(
            self._on_attach_project_clicked
        )
        self.detach_project_button = QPushButton("Détacher")
        self.detach_project_button.clicked.connect(
            self._on_detach_project_clicked
        )
        self.assign_project_commercial_button = QPushButton(
            "Affecter au commercial"
        )
        self.assign_project_commercial_button.clicked.connect(
            self._on_assign_project_commercial_clicked
        )
        project_actions.addWidget(self.attach_project_button)
        project_actions.addWidget(self.detach_project_button)
        project_actions.addWidget(
            self.assign_project_commercial_button
        )
        project_actions.addStretch(1)
        layout.addLayout(project_actions)

        self.project_table = QTableWidget(0, 2)
        self.project_table.setHorizontalHeaderLabels([
            "Projet enfant", "Statut"
        ])
        self.project_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
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
        self.create_landing_button.clicked.connect(
            self._on_create_landing_clicked
        )
        self.copy_landing_button = QPushButton("Copier")
        self.copy_landing_button.clicked.connect(
            self._on_copy_landing_clicked
        )
        self.open_landing_button = QPushButton("Ouvrir")
        self.open_landing_button.clicked.connect(
            self._on_open_landing_clicked
        )
        self.toggle_landing_button = QPushButton("Désactiver")
        self.toggle_landing_button.clicked.connect(
            self._on_toggle_landing_clicked
        )
        landing_actions.addWidget(self.create_landing_button)
        landing_actions.addWidget(self.copy_landing_button)
        landing_actions.addWidget(self.open_landing_button)
        landing_actions.addWidget(self.toggle_landing_button)
        landing_actions.addStretch(1)
        layout.addLayout(landing_actions)

    def _build_premium_ui(self):
        self.setObjectName("AdminCommercialProjectsRoot")
        self.setStyleSheet(projects_stylesheet(self._theme_mode))
        p = projects_palette(self._theme_mode)
        dark = p["bg"] == "#06111F"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        content = QWidget()
        content.setObjectName("AdminCommercialProjectsRoot")
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 22, 26, 26)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("ProjectsHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 16, 22, 17)
        hero_layout.setSpacing(14)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        eyebrow = QLabel("ADMIN  •  PILOTAGE COMMERCIAL")
        eyebrow.setObjectName("ProjectsEyebrow")
        title_box.addWidget(eyebrow)
        title = QLabel("Projets commerciaux")
        title.setObjectName("ProjectsTitle")
        title_box.addWidget(title)
        subtitle = QLabel(
            "Choisissez un univers, puis un commercial, puis les projets "
            "qui lui sont affectés."
        )
        subtitle.setObjectName("ProjectsSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(subtitle)
        hero_layout.addLayout(title_box, 1)

        self.create_parent_button = QPushButton("Nouveau projet")
        self.create_parent_button.setObjectName("PrimaryAction")
        self.create_parent_button.clicked.connect(
            self._on_create_parent_clicked
        )
        hero_layout.addWidget(self.create_parent_button)
        layout.addWidget(hero)
        add_soft_shadow(hero, dark=dark, blur=25, y=5)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.stat_parent_value, card_parent = self._metric_card(
            "UNIVERS", "0"
        )
        self.stat_commercial_value, card_commercial = self._metric_card(
            "COMMERCIAUX", "0"
        )
        self.stat_child_value, card_child = self._metric_card(
            "PROJETS LIÉS", "0"
        )
        self.stat_available_value, card_available = self._metric_card(
            "À RATTACHER", "0"
        )
        for card in (
            card_parent,
            card_commercial,
            card_child,
            card_available,
        ):
            metrics.addWidget(card, 1)
        layout.addLayout(metrics)

        portfolio = QFrame()
        portfolio.setObjectName("ProjectsPanel")
        portfolio_layout = QVBoxLayout(portfolio)
        portfolio_layout.setContentsMargins(14, 12, 14, 14)
        portfolio_layout.setSpacing(8)

        portfolio_head = QHBoxLayout()
        portfolio_titles = QVBoxLayout()
        portfolio_titles.setSpacing(1)
        portfolio_title = QLabel("1. Choisir un univers commercial")
        portfolio_title.setObjectName("PanelTitle")
        self.selected_parent_label = QLabel(
            "Sélectionnez BTP, IA ou un autre univers pour continuer."
        )
        self.selected_parent_label.setObjectName("PanelHint")
        portfolio_titles.addWidget(portfolio_title)
        portfolio_titles.addWidget(self.selected_parent_label)
        portfolio_head.addLayout(portfolio_titles)
        portfolio_head.addStretch(1)

        self.edit_parent_button = QPushButton("Modifier")
        self.edit_parent_button.setObjectName("SecondaryAction")
        self.edit_parent_button.clicked.connect(
            self._on_edit_parent_clicked
        )
        self.toggle_parent_button = QPushButton("Désactiver")
        self.toggle_parent_button.setObjectName("DangerAction")
        self.toggle_parent_button.clicked.connect(
            self._on_toggle_parent_clicked
        )
        portfolio_head.addWidget(self.edit_parent_button)
        portfolio_head.addWidget(self.toggle_parent_button)
        portfolio_layout.addLayout(portfolio_head)

        self.parent_table = QTableWidget(0, 5)
        self.parent_table.setHorizontalHeaderLabels([
            "Projet",
            "Description",
            "État",
            "Commerciaux",
            "Projets enfants",
        ])
        self.parent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.parent_table.setAlternatingRowColors(True)
        self.parent_table.setMinimumHeight(118)
        self.parent_table.setMaximumHeight(170)
        self.parent_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        portfolio_layout.addWidget(self.parent_table)
        layout.addWidget(portfolio)
        add_soft_shadow(portfolio, dark=dark, blur=18, y=4)

        self.commercial_panel = QFrame()
        self.commercial_panel.setObjectName("ProjectsPanel")
        commercial_layout = QVBoxLayout(self.commercial_panel)
        commercial_layout.setContentsMargins(14, 12, 14, 14)
        commercial_layout.setSpacing(8)

        commercial_head = QHBoxLayout()
        commercial_title_box = QVBoxLayout()
        commercial_title_box.setSpacing(1)
        commercial_title = QLabel("2. Équipe affectée")
        commercial_title.setObjectName("PanelTitle")
        self.commercial_hint = QLabel(
            "Choisissez un commercial pour afficher uniquement ses projets."
        )
        self.commercial_hint.setObjectName("PanelHint")
        commercial_title_box.addWidget(commercial_title)
        commercial_title_box.addWidget(self.commercial_hint)
        commercial_head.addLayout(commercial_title_box)
        commercial_head.addStretch(1)

        self.add_commercial_button = QPushButton("Affecter un commercial")
        self.add_commercial_button.setObjectName("PrimaryAction")
        self.add_commercial_button.clicked.connect(
            self._on_add_commercial_clicked
        )
        self.remove_commercial_button = QPushButton("Retirer")
        self.remove_commercial_button.setObjectName("DangerAction")
        self.remove_commercial_button.clicked.connect(
            self._on_remove_commercial_clicked
        )
        commercial_head.addWidget(self.add_commercial_button)
        commercial_head.addWidget(self.remove_commercial_button)
        commercial_layout.addLayout(commercial_head)

        self.commercial_table = QTableWidget(0, 3)
        self.commercial_table.setHorizontalHeaderLabels([
            "Commercial", "E-mail", "État"
        ])
        self.commercial_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.commercial_table.setAlternatingRowColors(True)
        self.commercial_table.setMinimumHeight(105)
        self.commercial_table.setMaximumHeight(180)
        self.commercial_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        commercial_layout.addWidget(self.commercial_table)
        layout.addWidget(self.commercial_panel)
        add_soft_shadow(self.commercial_panel, dark=dark, blur=18, y=4)

        self.project_panel = QFrame()
        self.project_panel.setObjectName("ProjectsPanel")
        project_layout = QVBoxLayout(self.project_panel)
        project_layout.setContentsMargins(14, 12, 14, 14)
        project_layout.setSpacing(8)

        project_head = QHBoxLayout()
        project_title_box = QVBoxLayout()
        project_title_box.setSpacing(1)
        project_title = QLabel("3. Projets enfants du commercial")
        project_title.setObjectName("PanelTitle")
        self.available_project_count = QLabel("0 projet disponible")
        self.available_project_count.setObjectName("PanelHint")
        project_title_box.addWidget(project_title)
        project_title_box.addWidget(self.available_project_count)
        project_head.addLayout(project_title_box)
        project_head.addStretch(1)

        self.attach_project_button = QPushButton("Rattacher un projet")
        self.attach_project_button.setObjectName("PrimaryAction")
        self.attach_project_button.clicked.connect(
            self._on_attach_project_clicked
        )
        self.assign_project_commercial_button = QPushButton(
            "Affecter au commercial"
        )
        self.assign_project_commercial_button.setObjectName(
            "SecondaryAction"
        )
        self.assign_project_commercial_button.clicked.connect(
            self._on_assign_project_commercial_clicked
        )
        self.detach_project_button = QPushButton("Détacher")
        self.detach_project_button.setObjectName("DangerAction")
        self.detach_project_button.clicked.connect(
            self._on_detach_project_clicked
        )
        project_head.addWidget(self.attach_project_button)
        project_head.addWidget(self.assign_project_commercial_button)
        project_head.addWidget(self.detach_project_button)
        project_layout.addLayout(project_head)

        self.project_table = QTableWidget(0, 2)
        self.project_table.setHorizontalHeaderLabels([
            "Projet enfant", "Statut"
        ])
        self.project_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.project_table.setAlternatingRowColors(True)
        self.project_table.setMinimumHeight(105)
        self.project_table.setMaximumHeight(190)
        self.project_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        project_layout.addWidget(self.project_table)
        layout.addWidget(self.project_panel)
        add_soft_shadow(self.project_panel, dark=dark, blur=18, y=4)

        self.landing_panel = QFrame()
        self.landing_panel.setObjectName("ProjectsPanel")
        landing_layout = QVBoxLayout(self.landing_panel)
        landing_layout.setContentsMargins(14, 12, 14, 14)
        landing_layout.setSpacing(8)

        landing_head = QHBoxLayout()
        landing_title_box = QVBoxLayout()
        landing_title_box.setSpacing(1)
        self.landing_title = QLabel("4. Landing Page commerciale")
        self.landing_title.setObjectName("PanelTitle")
        landing_hint = QLabel(
            "Le lien devient disponible uniquement pour le commercial "
            "réellement affecté au projet sélectionné."
        )
        landing_hint.setObjectName("PanelHint")
        landing_title_box.addWidget(self.landing_title)
        landing_title_box.addWidget(landing_hint)
        landing_head.addLayout(landing_title_box)
        landing_head.addStretch(1)

        self.landing_status_label = QLabel("Aucun lien")
        self.landing_status_label.setObjectName("StatusBadge")
        landing_head.addWidget(self.landing_status_label)
        landing_layout.addLayout(landing_head)

        info = QHBoxLayout()
        self.landing_commercial_label = QLabel("—")
        self.landing_commercial_label.setObjectName("PanelHint")
        info.addWidget(QLabel("Commercial :"))
        info.addWidget(self.landing_commercial_label)
        info.addStretch(1)
        landing_layout.addLayout(info)

        url_row = QHBoxLayout()
        self.landing_url_edit = QLineEdit()
        self.landing_url_edit.setReadOnly(True)
        self.landing_url_edit.setPlaceholderText(
            "Sélectionnez un projet affecté à ce commercial."
        )
        url_row.addWidget(self.landing_url_edit, 1)

        self.create_landing_button = QPushButton("Créer le lien")
        self.create_landing_button.setObjectName("PrimaryAction")
        self.create_landing_button.clicked.connect(
            self._on_create_landing_clicked
        )
        self.copy_landing_button = QPushButton("Copier")
        self.copy_landing_button.setObjectName("SecondaryAction")
        self.copy_landing_button.clicked.connect(
            self._on_copy_landing_clicked
        )
        self.open_landing_button = QPushButton("Ouvrir")
        self.open_landing_button.setObjectName("SecondaryAction")
        self.open_landing_button.clicked.connect(
            self._on_open_landing_clicked
        )
        self.toggle_landing_button = QPushButton("Désactiver")
        self.toggle_landing_button.setObjectName("DangerAction")
        self.toggle_landing_button.clicked.connect(
            self._on_toggle_landing_clicked
        )

        url_row.addWidget(self.create_landing_button)
        url_row.addWidget(self.copy_landing_button)
        url_row.addWidget(self.open_landing_button)
        url_row.addWidget(self.toggle_landing_button)
        landing_layout.addLayout(url_row)

        layout.addWidget(self.landing_panel)
        add_soft_shadow(self.landing_panel, dark=dark, blur=18, y=4)

        self.commercial_panel.hide()
        self.project_panel.hide()
        self.landing_panel.hide()

    def showEvent(self, event):
        self._install_theme_sync_filter()
        self._apply_visual_theme()
        super().showEvent(event)

    def _install_theme_sync_filter(self):
        window = self.window()
        if window is None or window is self._theme_sync_window:
            return
        if self._theme_sync_window is not None:
            try:
                self._theme_sync_window.removeEventFilter(self)
            except RuntimeError:
                pass
        self._theme_sync_window = window
        window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (
            watched is self._theme_sync_window
            and event.type() == QEvent.WindowActivate
        ):
            self._apply_visual_theme()
        return super().eventFilter(watched, event)

    def _apply_visual_theme(self):
        mode = projects_theme_mode()
        if mode == self._theme_mode:
            return
        self._theme_mode = mode
        self.setStyleSheet(projects_stylesheet(mode))

    def _metric_card(self, caption: str, value: str):
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(1)
        label = QLabel(caption)
        label.setObjectName("MetricCaption")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return value_label, card

    def _update_premium_metrics(self):
        if self._classic_mode or self.snapshot is None:
            return
        child_count = sum(
            len(tuple(parent.projects))
            for parent in self.parents
        )
        self.stat_parent_value.setText(str(len(self.parents)))
        self.stat_commercial_value.setText(
            str(len(tuple(self.snapshot.commercials)))
        )
        self.stat_child_value.setText(str(child_count))
        self.stat_available_value.setText(
            str(len(tuple(self.snapshot.ungrouped_projects)))
        )

    @staticmethod
    def _item(value):
        return QTableWidgetItem(str(value or ""))

    def rafraichir(self, *_args):
        if not self._classic_mode:
            self._apply_visual_theme()
        if not SessionState.has_role("Administrateur"):
            self.parent_table.setRowCount(0)
            self.commercial_table.setRowCount(0)
            self.project_table.setRowCount(0)
            self.available_project_count.setText("0 projet disponible")
            return

        self.snapshot = self.service.load()
        self.parents = tuple(self.snapshot.parents)
        self._update_premium_metrics()
        self.parent_table.setRowCount(len(self.parents))

        for row, parent in enumerate(self.parents):
            self.parent_table.setItem(row, 0, self._item(parent.name))
            self.parent_table.setItem(row, 1, self._item(parent.description))
            self.parent_table.setItem(
                row, 2, self._item("Actif" if parent.is_active else "Inactif")
            )
            self.parent_table.setItem(
                row, 3, self._item(len(parent.assigned_commercials))
            )
            self.parent_table.setItem(
                row, 4, self._item(len(parent.projects))
            )

        count = len(self.snapshot.ungrouped_projects)
        suffix = "projet disponible" if count == 1 else "projets disponibles"
        self.available_project_count.setText(f"{count} {suffix}")

        self._premium_parent_revealed = False
        self._premium_commercial_revealed = False
        self._project_view_filtered = False
        self._visible_projects = ()
        if not self._classic_mode:
            self.commercial_panel.hide()
            self.project_panel.hide()
            self.landing_panel.hide()

        if self.parents:
            # Compatibilité avec les contrats historiques : la première ligne
            # reste la sélection logique, mais les étapes suivantes ne sont
            # révélées qu'après un vrai clic utilisateur.
            self.parent_table.selectRow(0)
            self._show_parent(self.parents[0], reveal=False)
        else:
            self._show_parent(None, reveal=False)

    def _parent_selection_changed(self, row, _column, _old_row, _old_column):
        if 0 <= row < len(self.parents):
            self._show_parent(self.parents[row], reveal=False)

    def _parent_activated(self, row, _column):
        if self._classic_mode:
            return
        if 0 <= row < len(self.parents):
            self._show_parent(self.parents[row], reveal=True)

    def _commercial_activated(self, row, _column):
        if self._classic_mode:
            return
        parent = self._selected_parent()
        commercials = tuple(parent.assigned_commercials) if parent else ()
        if not 0 <= row < len(commercials):
            return
        commercial = commercials[row]
        self._filter_projects_for_commercial(
            str(getattr(commercial, "id", "") or "").strip(),
            reveal=True,
        )

    def _clear_landing(self):
        self.landing_commercial_label.setText("—")
        self.landing_status_label.setText("Aucun lien")
        self.landing_url_edit.clear()
        self.toggle_landing_button.setText("Désactiver")
        if not self._classic_mode:
            self.create_landing_button.setEnabled(False)
            self.copy_landing_button.setEnabled(False)
            self.open_landing_button.setEnabled(False)
            self.toggle_landing_button.setEnabled(False)

    def _selected_commercial_user_id(self):
        parent = self._selected_parent()
        commercials = tuple(parent.assigned_commercials) if parent else ()
        row = self.commercial_table.currentRow()
        if 0 <= row < len(commercials):
            return str(getattr(commercials[row], "id", "") or "").strip()
        return ""

    def _current_project_rows(self):
        parent = self._selected_parent()
        if parent is None:
            return ()
        if self._project_view_filtered:
            return tuple(self._visible_projects)
        return tuple(parent.projects)

    def _render_project_rows(self, projects):
        projects = tuple(projects or ())
        self.project_table.setRowCount(len(projects))
        for row, project in enumerate(projects):
            self.project_table.setItem(row, 0, self._item(project.name))
            self.project_table.setItem(row, 1, self._item(project.status))

    def _filter_projects_for_commercial(self, commercial_user_id, *, reveal):
        parent = self._selected_parent()
        projects = tuple(parent.projects) if parent else ()
        commercial_user_id = str(commercial_user_id or "").strip()
        filtered = tuple(
            project for project in projects
            if str(getattr(project, "assigned_to", "") or "").strip()
            == commercial_user_id
        )
        self._visible_projects = filtered
        self._project_view_filtered = True
        self._render_project_rows(filtered)
        self._clear_landing()

        commercial_name = commercial_user_id
        if parent is not None:
            for commercial in tuple(parent.assigned_commercials):
                if str(getattr(commercial, "id", "") or "").strip() == commercial_user_id:
                    commercial_name = (
                        str(getattr(commercial, "name", "") or "").strip()
                        or commercial_user_id
                    )
                    break
        count = len(filtered)
        suffix = "projet affecté" if count == 1 else "projets affectés"
        self.available_project_count.setText(
            f"{count} {suffix} à {commercial_name}"
        )
        if not self._classic_mode and reveal:
            self._premium_commercial_revealed = True
            self.project_panel.show()
            self.landing_panel.hide()

    def _commercial_selection_changed(
        self,
        row,
        _column,
        _old_row,
        _old_column,
    ):
        if self._classic_mode:
            project_row = self.project_table.currentRow()
            if project_row < 0:
                self._clear_landing()
                return
            self._project_selection_changed(project_row, 0, -1, -1)
            return

        # UI 2.0 : currentCellChanged est aussi emis par les selections
        # programmees de Qt (rafraichissement, selectRow, tests).
        # Le filtrage progressif ne doit etre declenche que par un vrai clic
        # utilisateur, deja branche sur cellClicked -> _commercial_activated.
        return

    def _project_selection_changed(self, row, _column, _old_row, _old_column):
        projects = self._current_project_rows()
        if not 0 <= row < len(projects):
            self._clear_landing()
            if not self._classic_mode:
                self.landing_panel.hide()
            return

        project = projects[row]
        selected_commercial_user_id = self._selected_commercial_user_id()
        assigned_commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        commercial_user_id = (
            selected_commercial_user_id
            or assigned_commercial_user_id
        )
        if not commercial_user_id:
            self._clear_landing()
            if not self._classic_mode:
                self.landing_panel.hide()
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

        # Le Backend refuse justement un lien si le projet n'est pas réellement
        # affecté à ce commercial. On bloque donc l'action côté interface avant
        # tout appel Cloud.
        if (
            selected_commercial_user_id
            and assigned_commercial_user_id
            and selected_commercial_user_id != assigned_commercial_user_id
        ):
            self.landing_status_label.setText(
                "Projet à affecter au commercial"
            )
            self.landing_url_edit.clear()
            if not self._classic_mode:
                self.create_landing_button.setEnabled(False)
                self.copy_landing_button.setEnabled(False)
                self.open_landing_button.setEnabled(False)
                self.toggle_landing_button.setEnabled(False)
                self.landing_panel.show()
            return

        if not assigned_commercial_user_id:
            self.landing_status_label.setText(
                "Projet à affecter au commercial"
            )
            self.landing_url_edit.clear()
            if not self._classic_mode:
                self.create_landing_button.setEnabled(False)
                self.copy_landing_button.setEnabled(False)
                self.open_landing_button.setEnabled(False)
                self.toggle_landing_button.setEnabled(False)
                self.landing_panel.show()
            return

        getter = getattr(self.service, "get_landing", None)
        if getter is None:
            self.landing_status_label.setText("Aucun lien")
            if not self._classic_mode:
                self.create_landing_button.setEnabled(True)
                self.landing_panel.show()
            return

        try:
            landing = getter(project.id, assigned_commercial_user_id)
        except CloudAPIError as exc:
            self._show_cloud_error("Lecture de la Landing Page", exc)
            return

        if landing is None:
            self.landing_status_label.setText("Aucun lien")
            self.landing_url_edit.clear()
            if not self._classic_mode:
                self.create_landing_button.setEnabled(True)
                self.copy_landing_button.setEnabled(False)
                self.open_landing_button.setEnabled(False)
                self.toggle_landing_button.setEnabled(False)
                self.landing_panel.show()
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
        if not self._classic_mode:
            self.create_landing_button.setEnabled(False)
            has_url = bool(self.landing_url_edit.text().strip())
            self.copy_landing_button.setEnabled(has_url)
            self.open_landing_button.setEnabled(has_url)
            self.toggle_landing_button.setEnabled(True)
            self.landing_panel.show()

    def _show_cloud_error(self, action, exc):
        message = str(exc or "Erreur Cloud").strip()
        QMessageBox.warning(
            self,
            str(action or "Action impossible"),
            message,
        )

    def _on_create_landing_clicked(self, *_args):
        if not SessionState.has_role("Administrateur"):
            return

        row = self.project_table.currentRow()
        projects = self._current_project_rows()
        if not 0 <= row < len(projects):
            return

        project = projects[row]
        assigned_commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        selected_commercial_user_id = self._selected_commercial_user_id()

        if not assigned_commercial_user_id:
            self.landing_status_label.setText(
                "Projet à affecter au commercial"
            )
            return
        if (
            selected_commercial_user_id
            and selected_commercial_user_id != assigned_commercial_user_id
        ):
            self.landing_status_label.setText(
                "Projet à affecter au commercial"
            )
            return

        creator = getattr(self.service, "ensure_landing", None)
        if creator is None:
            return

        try:
            landing = creator(project.id, assigned_commercial_user_id)
        except CloudAPIError as exc:
            self._show_cloud_error("Création de la Landing Page", exc)
            return

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
        if not self._classic_mode:
            self.create_landing_button.setEnabled(False)
            has_url = bool(self.landing_url_edit.text().strip())
            self.copy_landing_button.setEnabled(has_url)
            self.open_landing_button.setEnabled(has_url)
            self.toggle_landing_button.setEnabled(True)

    def _on_toggle_landing_clicked(self, *_args):
        if not SessionState.has_role("Administrateur"):
            return

        row = self.project_table.currentRow()
        projects = self._current_project_rows()
        if not 0 <= row < len(projects):
            return

        project = projects[row]
        assigned_commercial_user_id = str(
            getattr(project, "assigned_to", "") or ""
        ).strip()
        selected_commercial_user_id = self._selected_commercial_user_id()
        if not assigned_commercial_user_id:
            return
        if (
            selected_commercial_user_id
            and selected_commercial_user_id != assigned_commercial_user_id
        ):
            return

        getter = getattr(self.service, "get_landing", None)
        setter = getattr(self.service, "set_landing_active", None)
        if getter is None or setter is None:
            return

        try:
            landing = getter(project.id, assigned_commercial_user_id)
            if landing is None:
                return
            updated = setter(
                project.id,
                assigned_commercial_user_id,
                not landing.is_active,
            )
        except CloudAPIError as exc:
            self._show_cloud_error("Mise à jour de la Landing Page", exc)
            return

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

    def _show_parent(self, parent, *, reveal=False):
        self._clear_landing()
        if not self._classic_mode and hasattr(self, "selected_parent_label"):
            if parent is None:
                self.selected_parent_label.setText(
                    "Sélectionnez un univers pour administrer son équipe."
                )
            else:
                state = "Actif" if parent.is_active else "Inactif"
                self.selected_parent_label.setText(
                    f"{parent.name}  •  {state}  •  "
                    f"{len(parent.assigned_commercials)} commercial(aux)  •  "
                    f"{len(parent.projects)} projet(s) enfant(s)"
                )

        self.toggle_parent_button.setText(
            "Désactiver" if parent is not None and parent.is_active else "Activer"
        )
        commercials = tuple(parent.assigned_commercials) if parent else ()
        projects = tuple(parent.projects) if parent else ()
        self.commercial_table.setRowCount(len(commercials))
        self._project_view_filtered = False
        self._visible_projects = projects
        self._render_project_rows(projects)

        for row, commercial in enumerate(commercials):
            self.commercial_table.setItem(row, 0, self._item(commercial.name))
            self.commercial_table.setItem(row, 1, self._item(commercial.email))
            self.commercial_table.setItem(
                row, 2, self._item(
                    "Actif" if commercial.is_active else "Inactif"
                )
            )

        if not self._classic_mode:
            self.project_panel.hide()
            self.landing_panel.hide()
            if reveal and parent is not None:
                self._premium_parent_revealed = True
                self.commercial_panel.show()
                self.commercial_hint.setText(
                    f"Univers {parent.name} sélectionné — choisissez maintenant un commercial."
                )
            elif not reveal:
                self.commercial_panel.hide()

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

    def _assign_project_to_commercial(self, project_id, commercial_user_id):
        if not SessionState.has_role("Administrateur"):
            return
        try:
            self.service.assign_project_to_commercial(
                project_id,
                commercial_user_id,
            )
        except CloudAPIError as exc:
            self._show_cloud_error("Affectation du projet", exc)
            return
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

    def _on_assign_project_commercial_clicked(self, *_args):
        parent = self._selected_parent()
        if parent is None:
            return

        commercial_user_id = self._selected_commercial_user_id()
        if not commercial_user_id:
            return

        projects = tuple(parent.projects)

        # Compatibilité avec les contrats historiques/tests : avant activation
        # progressive, une ligne sélectionnée continue d'être affectée comme avant.
        if not self._project_view_filtered:
            project_row = self.project_table.currentRow()
            if not 0 <= project_row < len(projects):
                return
            self._assign_project_to_commercial(
                projects[project_row].id,
                commercial_user_id,
            )
            return

        # Dans le nouveau parcours progressif, la table ne montre que les projets
        # déjà affectés au commercial. Le bouton ouvre donc les autres projets de
        # l'univers pour permettre une affectation ou réaffectation explicite.
        candidates = tuple(
            project for project in projects
            if str(getattr(project, "assigned_to", "") or "").strip()
            != commercial_user_id
        )
        if not candidates:
            return

        dialog = ChildProjectDialog(self, projects=candidates)
        dialog.setWindowTitle("Affecter au commercial")
        if not dialog.exec():
            return
        project_id = dialog.selected_project_id()
        if not project_id:
            return
        self._assign_project_to_commercial(
            project_id,
            commercial_user_id,
        )

    def _on_detach_project_clicked(self, *_args):
        if self._selected_parent() is None:
            return

        row = self.project_table.currentRow()
        projects = self._current_project_rows()
        if not 0 <= row < len(projects):
            return

        self._detach_project(projects[row].id)
