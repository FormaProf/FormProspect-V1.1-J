from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "ui/windows/main_window.py").read_text(encoding="utf-8")


def test_google_calendar_auto_sync_uses_five_minute_timer():
    assert "self._google_calendar_auto_sync_timer.setInterval(300_000)" in MAIN
    assert "QTimer.singleShot(" in MAIN
    assert "20_000" in MAIN


def test_google_calendar_auto_sync_runs_off_ui_thread():
    assert 'name="FormProspectGoogleCalendarAutoSync"' in MAIN
    assert "daemon=True" in MAIN
    assert "google_calendar_auto_sync_ready = Signal(dict)" in MAIN


def test_google_calendar_auto_sync_checks_connection_before_syncing():
    block = MAIN.split(
        "def _start_google_calendar_auto_sync",
        1,
    )[1].split(
        "def _on_google_calendar_auto_sync_ready",
        1,
    )[0]

    assert "get_google_calendar_status()" in block
    assert "sync_google_calendar_planned_actions()" in block
    assert '"_not_connected": True' in block


def test_opening_agenda_triggers_immediate_reconcile():
    block = MAIN.split("def ouvrir_agenda", 1)[1].split(
        "def ouvrir_campagnes",
        1,
    )[0]

    assert "self._start_google_calendar_auto_sync()" in block
    assert "ensure_loaded" in block


def test_auto_sync_refreshes_visible_agenda_only_when_changed():
    block = MAIN.split(
        "def _on_google_calendar_auto_sync_ready",
        1,
    )[1].split(
        "def _on_google_calendar_auto_sync_failed",
        1,
    )[0]

    assert 'for key in ("created", "updated", "deleted")' in block
    assert "self.pages.currentWidget() is self.agenda_page" in block
    assert "self.agenda_page.rafraichir(force=True)" in block


def test_auto_sync_timer_is_stopped_on_logout_and_close():
    assert MAIN.count(
        'hasattr(self, "_google_calendar_auto_sync_timer")'
    ) >= 2
    assert MAIN.count(
        "self._google_calendar_auto_sync_timer.stop()"
    ) >= 2
