from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

PAGE = (
    ROOT / "ui/pages/trainer_availability_page.py"
).read_text(encoding="utf-8")
THEME = (
    ROOT / "ui/trainer_availability_premium_theme.py"
).read_text(encoding="utf-8")
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def test_trainer_availability_sources_parse():
    for source in (PAGE, THEME, MAIN):
        ast.parse(source)


def test_trainer_availability_has_one_layout_for_all_themes():
    assert "def _build_ui(self)" in PAGE
    assert "def _apply_visual_theme(self)" in PAGE
    theme_block = PAGE[
        PAGE.index("def _apply_visual_theme(self)"):
        PAGE.index("def _restyle_rows(self)")
    ]
    assert "_build_ui(" not in theme_block
    assert "CloudRuntime.api()" not in theme_block


def test_trainer_availability_is_command_center_not_raw_directory_only():
    assert "COUVERTURE DES AGENDAS" in PAGE
    assert "Répertoire des formateurs" in PAGE
    assert "Agendas connectés" in PAGE
    assert "À configurer" in PAGE
    assert "TrainerCoverageBar" in PAGE
    assert "open_selected_button" in PAGE


def test_trainer_availability_theme_supports_dark_mode():
    assert "THEME_UI_DARK" in THEME
    assert '"page": "#07101A"' in THEME
    assert '"primary": "#338CE4"' in THEME
    assert '"table_row": "#0D1826"' in THEME
    assert "trainer_status_badge_style" in THEME
    assert "trainer_platform_badge_style" in THEME


def test_trainer_availability_theme_sync_does_not_rebuild_or_fetch():
    sync_start = MAIN.index("def _sync_commercial_project_theme_pages")
    sync_end = MAIN.index("def ouvrir_admin_projets_commerciaux", sync_start)
    sync = MAIN[sync_start:sync_end]
    assert '"trainer_availability_page"' in sync
    assert "rafraichir()" not in sync
    assert "CloudRuntime" not in sync


def test_trainer_availability_preserves_cloud_operations():
    assert "list_cloud_trainers(" in PAGE
    assert "update_cloud_trainer(" in PAGE
    assert "QDesktopServices.openUrl" in PAGE
