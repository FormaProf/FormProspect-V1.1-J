from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.theme_settings import THEME_CLASSIC
from ui.commercial_projects_theme import (
    add_soft_shadow,
    premium_projects_enabled,
    projects_palette,
    projects_stylesheet,
    projects_theme_mode,
)
from ui.widgets.commercial_project_card import CommercialProjectCard


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
        self._choice_bundles = []
        self._landing_project_id = ""
        self._current_landing = None
        self._theme_mode = projects_theme_mode()

        # 8E unified UI: Classique / Clair / Sombre use the exact same
        # premium workspace. Only the palette is allowed to change.
        self._classic_mode = False
        self._theme_sync_window = None
        self._build_premium_ui()

        if auto_refresh:
            self.rafraichir()

    # ------------------------------------------------------------------
    # Construction UI
    # ------------------------------------------------------------------

    def _build_classic_ui(self):
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

        self.subtitle_label = QLabel(
            "Choisissez votre univers commercial puis le projet sur lequel "
            "vous souhaitez travailler."
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("font-size:13px; color:#6B7A90;")
        self.layout.addWidget(self.subtitle_label)

        self.empty_label = QLabel("Aucun projet disponible pour le moment.")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(
            "font-size:14px; color:#6B7A90; padding:18px 0;"
        )
        self.empty_label.hide()
        self.layout.addWidget(self.empty_label)

        self.back_button = QPushButton("Retour")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.hide()
        self.back_button.clicked.connect(self.rafraichir)
        self.layout.addWidget(self.back_button)

        self._build_landing_panel(classic=True)
        self.choice_grid = None
        self.choice_host = None

    def _build_premium_ui(self):
        self.setObjectName("CommercialProjectsRoot")
        self.setStyleSheet(projects_stylesheet(self._theme_mode))
        p = projects_palette(self._theme_mode)
        dark = self._theme_mode != THEME_CLASSIC and p["bg"] == "#06111F"

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(26, 22, 26, 26)
        self.layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("ProjectsHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 16, 22, 17)
        hero_layout.setSpacing(3)

        eyebrow = QLabel(
            "WORKSPACE  •  PILOTAGE ÉQUIPE"
            if self.workspace_mode == "manager"
            else "WORKSPACE  •  PORTEFEUILLE COMMERCIAL"
        )
        eyebrow.setObjectName("ProjectsEyebrow")
        hero_layout.addWidget(eyebrow)

        title_text = (
            "Projets de mon équipe"
            if self.workspace_mode == "manager"
            else "Mes projets commerciaux"
        )
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("ProjectsTitle")
        hero_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Choisissez un univers commercial, ouvrez un projet et accédez "
            "directement à votre portefeuille de prospection."
        )
        self.subtitle_label.setObjectName("ProjectsSubtitle")
        self.subtitle_label.setWordWrap(True)
        hero_layout.addWidget(self.subtitle_label)
        self.layout.addWidget(hero)
        add_soft_shadow(hero, dark=dark, blur=25, y=5)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        (
            self.stat_univers_value,
            univers_card,
        ) = self._metric_card("UNIVERS", "0")
        (
            self.stat_projects_value,
            projects_card,
        ) = self._metric_card("PROJETS", "0")
        (
            self.stat_prospects_value,
            prospects_card,
        ) = self._metric_card("PROSPECTS", "0")
        (
            self.stat_hot_value,
            hot_card,
        ) = self._metric_card("LEADS CHAUDS", "0")

        for card in (univers_card, projects_card, prospects_card, hot_card):
            metrics.addWidget(card, 1)
        self.layout.addLayout(metrics)

        self.navigation_panel = QFrame()
        self.navigation_panel.setObjectName("ProjectsPanel")
        nav_layout = QVBoxLayout(self.navigation_panel)
        nav_layout.setContentsMargins(14, 12, 14, 14)
        nav_layout.setSpacing(9)

        nav_header = QHBoxLayout()
        nav_title_box = QVBoxLayout()
        nav_title_box.setSpacing(1)
        self.nav_title_label = QLabel("Votre portefeuille visuel")
        self.nav_title_label.setObjectName("PanelTitle")
        self.nav_hint_label = QLabel(
            "Chaque univers possède son identité. Survolez une carte puis ouvrez le projet ou sa Landing Page."
        )
        self.nav_hint_label.setObjectName("PanelHint")
        nav_title_box.addWidget(self.nav_title_label)
        nav_title_box.addWidget(self.nav_hint_label)
        nav_header.addLayout(nav_title_box)
        nav_header.addStretch(1)

        self.back_button = QPushButton("← Retour aux univers")
        self.back_button.setObjectName("SecondaryAction")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.rafraichir)
        self.back_button.hide()
        nav_header.addWidget(self.back_button)
        nav_layout.addLayout(nav_header)

        self.empty_label = QLabel("Aucun projet disponible pour le moment.")
        self.empty_label.setObjectName("PanelHint")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setMinimumHeight(82)
        self.empty_label.hide()
        nav_layout.addWidget(self.empty_label)

        self.choice_scroll = QScrollArea()
        self.choice_scroll.setObjectName("ProjectChoicesScroll")
        self.choice_scroll.setWidgetResizable(True)
        self.choice_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.choice_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.choice_scroll.setMinimumHeight(252)
        self.choice_scroll.setMaximumHeight(520)

        self.choice_host = QWidget()
        self.choice_host.setObjectName("ProjectChoicesHost")
        self.choice_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.choice_grid = QGridLayout(self.choice_host)
        self.choice_grid.setContentsMargins(2, 2, 2, 4)
        self.choice_grid.setHorizontalSpacing(14)
        self.choice_grid.setVerticalSpacing(14)
        self.choice_grid.setAlignment(Qt.AlignTop)
        self.choice_grid.setColumnStretch(0, 1)
        self.choice_grid.setColumnStretch(1, 1)
        self.choice_scroll.setWidget(self.choice_host)
        nav_layout.addWidget(self.choice_scroll)

        self.layout.addWidget(self.navigation_panel)
        add_soft_shadow(self.navigation_panel, dark=dark, blur=18, y=4)

        self._build_landing_panel(classic=False)
        self.layout.addStretch(1)

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
        for card in (*self.parent_buttons.values(), *self.child_buttons.values()):
            if isinstance(card, CommercialProjectCard):
                card.set_theme_mode(mode)

    def _metric_card(self, caption: str, value: str):
        card = QFrame()
        card.setObjectName("MetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(1)
        label = QLabel(caption)
        label.setObjectName("MetricCaption")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return value_label, card

    def _build_landing_panel(self, *, classic: bool):
        if classic:
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

            self.create_landing_button.clicked.connect(
                self._on_create_landing_clicked
            )
            self.copy_landing_button.clicked.connect(
                self._on_copy_landing_clicked
            )
            self.open_landing_button.clicked.connect(
                self._on_open_landing_clicked
            )

            actions.addWidget(self.create_landing_button)
            actions.addWidget(self.copy_landing_button)
            actions.addWidget(self.open_landing_button)
            actions.addStretch(1)
            panel_layout.addLayout(actions)

            self.landing_panel.hide()
            self.layout.addWidget(self.landing_panel)
            return

        self.landing_panel = QFrame()
        self.landing_panel.setObjectName("ProjectsPanel")
        panel_layout = QVBoxLayout(self.landing_panel)
        panel_layout.setContentsMargins(16, 13, 16, 14)
        panel_layout.setSpacing(9)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.landing_title_label = QLabel("Landing Page personnelle")
        self.landing_title_label.setObjectName("PanelTitle")
        landing_hint = QLabel(
            "Partagez votre lien dédié pour transformer vos prises de contact "
            "en prospects attribués."
        )
        landing_hint.setObjectName("PanelHint")
        title_box.addWidget(self.landing_title_label)
        title_box.addWidget(landing_hint)
        top.addLayout(title_box)
        top.addStretch(1)

        self.landing_status_label = QLabel("Aucun lien")
        self.landing_status_label.setObjectName("StatusBadge")
        top.addWidget(self.landing_status_label)
        panel_layout.addLayout(top)

        url_row = QHBoxLayout()
        self.landing_url_edit = QLineEdit()
        self.landing_url_edit.setReadOnly(True)
        self.landing_url_edit.setPlaceholderText(
            "Le lien apparaîtra ici après sa création."
        )
        url_row.addWidget(self.landing_url_edit, 1)

        self.copy_landing_button = QPushButton("Copier")
        self.copy_landing_button.setObjectName("SecondaryAction")
        self.open_landing_button = QPushButton("Ouvrir")
        self.open_landing_button.setObjectName("SecondaryAction")
        url_row.addWidget(self.copy_landing_button)
        url_row.addWidget(self.open_landing_button)
        panel_layout.addLayout(url_row)

        actions = QHBoxLayout()
        self.create_landing_button = QPushButton("Créer ma Landing Page")
        self.create_landing_button.setObjectName("PrimaryAction")
        actions.addWidget(self.create_landing_button)
        actions.addStretch(1)
        panel_layout.addLayout(actions)

        self.create_landing_button.clicked.connect(
            self._on_create_landing_clicked
        )
        self.copy_landing_button.clicked.connect(
            self._on_copy_landing_clicked
        )
        self.open_landing_button.clicked.connect(
            self._on_open_landing_clicked
        )

        self.landing_panel.hide()
        self.layout.addWidget(self.landing_panel)

    # ------------------------------------------------------------------
    # Landing Page - logique historique conservée
    # ------------------------------------------------------------------

    @staticmethod
    def _landing_public_url(landing):
        organization_id = str(
            getattr(landing, "organization_id", "") or ""
        ).strip()
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
            return

        self.landing_status_label.setText(
            "Actif" if landing.is_active else "Inactif"
        )
        self.landing_url_edit.setText(self._landing_public_url(landing))
        self.create_landing_button.setEnabled(False)
        has_url = bool(self.landing_url_edit.text().strip())
        self.copy_landing_button.setEnabled(has_url)
        self.open_landing_button.setEnabled(has_url)

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

    def _on_copy_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if url:
            QApplication.clipboard().setText(url)

    def _on_open_landing_clicked(self, *_args):
        url = self.landing_url_edit.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    # ------------------------------------------------------------------
    # Rendu portefeuille
    # ------------------------------------------------------------------

    def _clear_choice_widgets(self):
        for button in self.parent_buttons.values():
            button.deleteLater()
        self.parent_buttons.clear()

        for button in self.child_buttons.values():
            button.deleteLater()
        self.child_buttons.clear()

        for button in self.landing_buttons.values():
            button.deleteLater()
        self.landing_buttons.clear()

        for bundle in self._choice_bundles:
            bundle.deleteLater()
        self._choice_bundles.clear()

    def _update_metrics(self, parents):
        if self._classic_mode:
            return
        parents = tuple(parents or ())
        project_count = sum(
            len(tuple(getattr(parent, "projects", ()) or ()))
            for parent in parents
        )
        prospect_count = sum(
            int(getattr(parent, "prospect_count", 0) or 0)
            for parent in parents
        )
        hot_count = sum(
            int(getattr(parent, "lead_chaud_count", 0) or 0)
            for parent in parents
        )
        self.stat_univers_value.setText(str(len(parents)))
        self.stat_projects_value.setText(str(project_count))
        self.stat_prospects_value.setText(str(prospect_count))
        self.stat_hot_value.setText(str(hot_count))

    def _sync_choice_area_height(self, item_count: int, *, has_actions: bool = True) -> None:
        """Keep small portfolios dense while preserving scrolling for larger ones."""
        count = max(1, int(item_count or 0))
        rows = (count + 1) // 2
        row_height = 248 if has_actions and self.workspace_mode == "commercial" else 205
        height = min(520, 12 + rows * row_height + max(0, rows - 1) * 14)
        self.choice_scroll.setMinimumHeight(height)
        self.choice_scroll.setMaximumHeight(height)

    def rafraichir(self):
        if not self._classic_mode:
            self._apply_visual_theme()
        self.back_button.hide()
        self.nav_title_label.setText("Votre portefeuille visuel")
        self.nav_hint_label.setText(
            "Chaque univers possède son identité. Survolez une carte puis ouvrez le projet ou sa Landing Page."
        )
        self._clear_choice_widgets()

        self._landing_project_id = ""
        self._current_landing = None
        self.landing_panel.hide()

        if self.workspace_mode == "manager":
            parents = self.service.list_for_manager()
        else:
            parents = self.service.list_for_commercial(self.user_id)

        parents = tuple(parents or ())
        self._update_metrics(parents)
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

        if self._classic_mode:
            self._render_parent_choices_classic(parents)
        else:
            self._render_parent_choices_premium(parents)

    def _render_parent_choices_classic(self, parents):
        for parent in parents:
            lead_chaud_count = int(
                getattr(parent, "lead_chaud_count", 0) or 0
            )
            button = QPushButton(
                f"{parent.name}\n"
                f"{len(parent.projects)} projet(s) - "
                f"{parent.prospect_count} prospect(s) - "
                f"{lead_chaud_count} lead(s) chaud(s)"
            )
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(86)
            button.setStyleSheet(
                "QPushButton { text-align:left; padding:16px 20px; "
                "font-size:15px; font-weight:700; color:#0B1220; "
                "background:white; border:1px solid #E7ECF3; "
                "border-radius:14px; }"
                "QPushButton:hover { border:1px solid #338CE4; "
                "background:#F8FBFF; }"
            )
            button.clicked.connect(
                lambda _checked=False, current_parent=parent:
                self._on_parent_clicked(current_parent)
            )
            self.parent_buttons[parent.id] = button
            self.layout.addWidget(button)

            projects = tuple(getattr(parent, "projects", ()) or ())
            if self.workspace_mode == "commercial" and len(projects) == 1:
                project_id = str(
                    getattr(projects[0], "id", "") or ""
                ).strip()
                if project_id:
                    landing_button = QPushButton("🚀  Ma Landing Page")
                    landing_button.setCursor(Qt.PointingHandCursor)
                    landing_button.clicked.connect(
                        lambda _checked=False, pid=project_id:
                        self._show_landing(pid)
                    )
                    self.landing_buttons[project_id] = landing_button
                    self.layout.addWidget(landing_button)

    def _render_parent_choices_premium(self, parents):
        row = 0
        col = 0
        parents = tuple(parents or ())
        for parent in parents:
            projects = tuple(getattr(parent, "projects", ()) or ())
            hot = int(getattr(parent, "lead_chaud_count", 0) or 0)
            prospects = int(getattr(parent, "prospect_count", 0) or 0)

            bundle = QWidget()
            bundle.setObjectName("ProjectCardBundle")
            bundle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bundle_layout = QVBoxLayout(bundle)
            bundle_layout.setContentsMargins(0, 0, 0, 0)
            bundle_layout.setSpacing(7)
            bundle_layout.setAlignment(Qt.AlignTop)

            stats_text = (
                f"{len(projects)} projet(s)   •   "
                f"{prospects} prospect(s)   •   "
                f"{hot} lead(s) chaud(s)"
            )
            project_names = [
                str(getattr(project, "name", "") or "").strip()
                for project in projects
                if str(getattr(project, "name", "") or "").strip()
            ]
            context_text = " ".join(project_names)
            if len(project_names) == 1:
                subtitle_text = project_names[0]
            elif project_names:
                subtitle_text = f"{len(project_names)} projets disponibles dans cet univers"
            else:
                subtitle_text = "Aucun projet affecté pour le moment"

            button = CommercialProjectCard(
                title=str(getattr(parent, "name", "") or "Univers"),
                subtitle_text=subtitle_text,
                stats_text=stats_text,
                metrics=(
                    ("PROJETS", str(len(projects))),
                    ("PROSPECTS", str(prospects)),
                    ("LEADS CHAUDS", str(hot)),
                ),
                context_text=context_text,
                kicker="UNIVERS COMMERCIAL",
                theme_mode=self._theme_mode,
            )
            button.clicked.connect(
                lambda _checked=False, current_parent=parent:
                self._on_parent_clicked(current_parent)
            )
            self.parent_buttons[parent.id] = button
            bundle_layout.addWidget(button)

            if self.workspace_mode == "commercial" and len(projects) == 1:
                project_id = str(
                    getattr(projects[0], "id", "") or ""
                ).strip()
                if project_id:
                    landing_button = QPushButton("🚀  ACCÉDER À MA LANDING PAGE")
                    landing_button.setObjectName("ProjectLandingAction")
                    landing_button.setCursor(Qt.PointingHandCursor)
                    landing_button.setFixedHeight(42)
                    landing_button.clicked.connect(
                        lambda _checked=False, pid=project_id:
                        self._show_landing(pid)
                    )
                    self.landing_buttons[project_id] = landing_button
                    bundle_layout.addWidget(landing_button)

            self._choice_bundles.append(bundle)
            self.choice_grid.addWidget(bundle, row, col, Qt.AlignTop)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        self._sync_choice_area_height(
            len(parents),
            has_actions=any(
                len(tuple(getattr(parent, "projects", ()) or ())) == 1
                for parent in parents
            ),
        )

    def _on_parent_clicked(self, parent):
        projects = tuple(getattr(parent, "projects", ()) or ())
        if len(projects) > 1:
            self._show_child_choices(parent)
            return

        if not projects:
            had_parent_choices = bool(self.parent_buttons)
            self._clear_choice_widgets()
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
        self._clear_choice_widgets()
        self.back_button.setVisible(had_parent_choices)

        parent_name = str(getattr(parent, "name", "") or "Univers").strip()
        self.nav_title_label.setText(f"Projets • {parent_name}")
        self.nav_hint_label.setText(
            "Choisissez un projet pour ouvrir son CRM. Votre Landing Page reste accessible directement sous la carte."
        )

        projects = tuple(getattr(parent, "projects", ()) or ())
        if self._classic_mode:
            for project in projects:
                project_id = str(
                    getattr(project, "id", "") or ""
                ).strip()
                if not project_id:
                    continue
                project_name = str(
                    getattr(project, "name", "") or "Projet"
                ).strip()
                prospect_count = int(
                    getattr(project, "prospect_count", 0) or 0
                )
                lead_chaud_count = int(
                    (
                        getattr(parent, "lead_chaud_by_project", {})
                        or {}
                    ).get(project_id, 0)
                    or 0
                )
                button = QPushButton(
                    f"{project_name}\n"
                    f"{prospect_count} prospect(s) - "
                    f"{lead_chaud_count} lead(s) chaud(s)"
                )
                button.setCursor(Qt.PointingHandCursor)
                button.setMinimumHeight(64)
                button.clicked.connect(
                    lambda _checked=False, pid=project_id:
                    self.project_open_requested.emit(pid)
                )
                self.child_buttons[project_id] = button
                self.layout.addWidget(button)

                if self.workspace_mode == "commercial":
                    landing_button = QPushButton("🚀  Ma Landing Page")
                    landing_button.setCursor(Qt.PointingHandCursor)
                    landing_button.clicked.connect(
                        lambda _checked=False, pid=project_id:
                        self._show_landing(pid)
                    )
                    self.landing_buttons[project_id] = landing_button
                    self.layout.addWidget(landing_button)
            return

        row = 0
        col = 0
        for project in projects:
            project_id = str(getattr(project, "id", "") or "").strip()
            if not project_id:
                continue
            project_name = str(
                getattr(project, "name", "") or "Projet"
            ).strip()
            prospect_count = int(
                getattr(project, "prospect_count", 0) or 0
            )
            lead_chaud_count = int(
                (
                    getattr(parent, "lead_chaud_by_project", {})
                    or {}
                ).get(project_id, 0)
                or 0
            )

            bundle = QWidget()
            bundle.setObjectName("ProjectCardBundle")
            bundle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bundle_layout = QVBoxLayout(bundle)
            bundle_layout.setContentsMargins(0, 0, 0, 0)
            bundle_layout.setSpacing(7)
            bundle_layout.setAlignment(Qt.AlignTop)

            stats_text = (
                f"{prospect_count} prospect(s)   •   "
                f"{lead_chaud_count} lead(s) chaud(s)"
            )
            button = CommercialProjectCard(
                title=project_name,
                subtitle_text=f"Univers {parent_name}",
                stats_text=stats_text,
                metrics=(
                    ("PROSPECTS", str(prospect_count)),
                    ("LEADS CHAUDS", str(lead_chaud_count)),
                ),
                context_text=parent_name,
                kicker=f"PROJET • {parent_name}" if parent_name else "PROJET COMMERCIAL",
                theme_mode=self._theme_mode,
            )
            button.clicked.connect(
                lambda _checked=False, pid=project_id:
                self.project_open_requested.emit(pid)
            )
            self.child_buttons[project_id] = button
            bundle_layout.addWidget(button)

            if self.workspace_mode == "commercial":
                landing_button = QPushButton("🚀  ACCÉDER À MA LANDING PAGE")
                landing_button.setObjectName("ProjectLandingAction")
                landing_button.setCursor(Qt.PointingHandCursor)
                landing_button.setFixedHeight(42)
                landing_button.clicked.connect(
                    lambda _checked=False, pid=project_id:
                    self._show_landing(pid)
                )
                self.landing_buttons[project_id] = landing_button
                bundle_layout.addWidget(landing_button)

            self._choice_bundles.append(bundle)
            self.choice_grid.addWidget(bundle, row, col, Qt.AlignTop)
            col += 1
            if col >= 2:
                col = 0
                row += 1

        self._sync_choice_area_height(
            len(projects),
            has_actions=self.workspace_mode == "commercial",
        )
