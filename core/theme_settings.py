from __future__ import annotations

from PySide6.QtCore import QSettings


THEME_CLASSIC = "classic"
THEME_UI_LIGHT = "ui_light"
THEME_UI_DARK = "ui_dark"
THEME_CHOICES = (
    THEME_CLASSIC,
    THEME_UI_LIGHT,
    THEME_UI_DARK,
)

_THEME_LABELS = {
    THEME_CLASSIC: "Form@Prospect Classique",
    THEME_UI_LIGHT: "Form@Prospect UI Clair",
    THEME_UI_DARK: "Form@Prospect UI Sombre",
}


def normalize_theme_mode(value) -> str:
    raw = str(value or "").strip().lower()

    # Migration transparente depuis le prototype 8E.1B.
    legacy = {
        "light": THEME_UI_LIGHT,
        "dark": THEME_UI_DARK,
        "system": THEME_CLASSIC,
    }
    raw = legacy.get(raw, raw)

    if raw in THEME_CHOICES:
        return raw
    return THEME_CLASSIC


def get_theme_preference() -> str:
    settings = QSettings("NM FORMATION", "Form@Prospect")
    return normalize_theme_mode(
        settings.value("appearance/theme", THEME_CLASSIC)
    )


def set_theme_preference(value) -> str:
    normalized = normalize_theme_mode(value)
    settings = QSettings("NM FORMATION", "Form@Prospect")
    settings.setValue("appearance/theme", normalized)
    settings.sync()
    return normalized


def theme_label(value) -> str:
    normalized = normalize_theme_mode(value)
    return _THEME_LABELS[normalized]
