from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

THEME = (ROOT / "ui" / "commercial_projects_theme.py").read_text(encoding="utf-8")
COMMERCIAL = (ROOT / "ui" / "pages" / "commercial_projects_page.py").read_text(encoding="utf-8")
ADMIN = (ROOT / "ui" / "pages" / "admin_commercial_projects_page.py").read_text(encoding="utf-8")
CARD = (ROOT / "ui" / "widgets" / "commercial_project_card.py").read_text(encoding="utf-8")


def test_projects_premium_sources_are_valid_python():
    for source in (THEME, COMMERCIAL, ADMIN, CARD):
        ast.parse(source)


def test_three_global_themes_are_respected():
    assert "THEME_CLASSIC" in THEME
    assert "THEME_UI_LIGHT" in THEME
    assert "THEME_UI_DARK" in THEME
    assert "premium_projects_enabled" in THEME
    assert "_build_classic_ui" in COMMERCIAL
    assert "_build_premium_ui" in COMMERCIAL
    assert "_build_classic_ui" in ADMIN
    assert "_build_premium_ui" in ADMIN


def test_commercial_workspace_keeps_navigation_and_landing_contracts():
    for marker in (
        "project_open_requested = Signal(str)",
        "self.service.list_for_manager()",
        "self.service.list_for_commercial(self.user_id)",
        "self.service.get_landing(project_id)",
        "self.service.ensure_landing(self._landing_project_id)",
        "self.project_open_requested.emit(project_id)",
    ):
        assert marker in COMMERCIAL


def test_commercial_workspace_has_command_center_metrics_and_cards():
    for marker in (
        "WORKSPACE  •  PORTEFEUILLE COMMERCIAL",
        "LEADS CHAUDS",
        "CommercialProjectCard",
        "Landing Page personnelle",
        "stat_prospects_value",
    ):
        assert marker in COMMERCIAL


def test_admin_workspace_keeps_all_business_actions():
    for marker in (
        "self.service.create_parent(name, description)",
        "self.service.update_parent(parent_id, name, description)",
        "self.service.set_parent_active(parent_id, is_active)",
        "self.service.assign_commercial(parent_id, user_id)",
        "self.service.remove_commercial(parent_id, user_id)",
        "self.service.attach_project(parent_id, project_id)",
        "self.service.detach_project(project_id)",
        "self.service.assign_project_to_commercial(",
        "self.service.load()",
    ):
        assert marker in ADMIN


def test_admin_workspace_uses_progressive_universe_team_project_flow():
    for marker in (
        "ADMIN  •  PILOTAGE COMMERCIAL",
        "1. Choisir un univers commercial",
        "2. Équipe affectée",
        "3. Projets enfants du commercial",
        "4. Landing Page commerciale",
        "self.commercial_panel.hide()",
        "self.project_panel.hide()",
        "self.landing_panel.hide()",
        "self.parent_table.cellClicked.connect(self._parent_activated)",
        "self.commercial_table.cellClicked.connect(self._commercial_activated)",
        "_filter_projects_for_commercial",
        "stat_available_value",
    ):
        assert marker in ADMIN


def test_admin_filters_child_projects_by_real_assignee():
    assert 'getattr(project, "assigned_to", "")' in ADMIN
    assert "== commercial_user_id" in ADMIN
    assert "self._visible_projects = filtered" in ADMIN
    assert "self._render_project_rows(filtered)" in ADMIN
    assert "projects = self._current_project_rows()" in ADMIN


def test_landing_creation_is_guarded_by_real_project_assignment():
    create_block = ADMIN.split("def _on_create_landing_clicked", 1)[1].split(
        "def _on_toggle_landing_clicked", 1
    )[0]
    assert "assigned_commercial_user_id" in create_block
    assert "Projet à affecter au commercial" in create_block
    assert "Projet à affecter au commercial" in create_block
    assert "creator(project.id, assigned_commercial_user_id)" in create_block
    assert "except CloudAPIError as exc" in create_block


def test_projects_pages_resync_light_and_dark_when_main_window_reactivates():
    for source in (COMMERCIAL, ADMIN):
        assert "QEvent.WindowActivate" in source
        assert "window.installEventFilter(self)" in source
        assert "def _apply_visual_theme" in source
        assert "projects_theme_mode()" in source
        assert "self.setStyleSheet(projects_stylesheet(mode))" in source


def test_premium_layout_does_not_force_previous_large_side_by_side_geometry():
    assert "lower = QHBoxLayout()" not in ADMIN
    assert "self.commercial_table.setMaximumHeight(180)" in ADMIN
    assert "self.project_table.setMaximumHeight(190)" in ADMIN
    assert "self.parent_table.setMaximumHeight(170)" in ADMIN


def test_project_services_are_not_imported_for_mutation():
    assert "commercial_project_workspace_service.py" not in THEME
    assert "commercial_project_admin_service.py" not in THEME


def test_commercial_project_cards_have_thematic_hover_and_btp_hazard_design():
    for marker in (
        "class CommercialProjectCard(QPushButton)",
        "QPropertyAnimation",
        "hoverProgress = Property",
        "resolve_project_visual_theme",
        '"btp": "BTP • CHANTIER"',
        "_paint_btp_frame",
        "_paint_btp_artwork",
        "QGraphicsDropShadowEffect",
        "OUVRIR LE PROJET",
    ):
        assert marker in CARD


def test_commercial_page_uses_visual_cards_for_universes_and_projects():
    assert COMMERCIAL.count("CommercialProjectCard(") >= 2
    assert 'kicker="UNIVERS COMMERCIAL"' in COMMERCIAL
    assert 'f"PROJET • {parent_name}"' in COMMERCIAL
    assert "card.set_theme_mode(mode)" in COMMERCIAL


def test_project_cards_v2_have_dense_grid_metric_pills_and_premium_hover():
    for marker in (
        "_paint_metric_pills",
        "_paint_blueprint_grid",
        "_paint_theme_monogram",
        "subtitle_text",
        "metrics:",
        "lift = 2.6 * self._hover_progress",
        "EXPLORER L’UNIVERS",
    ):
        assert marker in CARD


def test_commercial_portfolio_v2_is_top_aligned_and_does_not_leave_large_empty_canvas():
    for marker in (
        'self.choice_grid.setAlignment(Qt.AlignTop)',
        'self.choice_grid.addWidget(bundle, row, col, Qt.AlignTop)',
        'bundle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)',
        'def _sync_choice_area_height',
        'self.choice_scroll.setMaximumHeight(520)',
        'Votre portefeuille visuel',
        'ACCÉDER À MA LANDING PAGE',
    ):
        assert marker in COMMERCIAL

    assert 'self.layout.addWidget(self.navigation_panel, 1)' not in COMMERCIAL
    assert 'QWidget#ProjectChoicesHost' in THEME
