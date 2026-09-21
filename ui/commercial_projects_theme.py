from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    get_theme_preference,
    normalize_theme_mode,
)


LIGHT = {
    "bg": "#F3F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FBFF",
    "surface_soft": "#EEF6FD",
    "border": "#D6E4F1",
    "border_strong": "#B9D4EA",
    "text": "#0B1E33",
    "text_soft": "#43617F",
    "muted": "#71879E",
    "primary": "#338CE4",
    "cyan": "#0D8FCF",
    "hot": "#F97316",
    "success": "#16A36A",
    "danger": "#DC5A67",
    "warning": "#E9A318",
    "input": "#F8FBFF",
}

DARK = {
    "bg": "#06111F",
    "surface": "#0A1A2B",
    "surface_alt": "#0D2136",
    "surface_soft": "#102942",
    "border": "#1B3C5B",
    "border_strong": "#2A628E",
    "text": "#F3F8FE",
    "text_soft": "#B8CDE2",
    "muted": "#7893AE",
    "primary": "#338CE4",
    "cyan": "#66DAFF",
    "hot": "#FF8756",
    "success": "#53D89B",
    "danger": "#FF7885",
    "warning": "#FFD15A",
    "input": "#0C2136",
}

CLASSIC = {
    "bg": "#F3F3F3",
    "surface": "#FFFFFF",
    "surface_alt": "#FFFFFF",
    "surface_soft": "#F8FAFC",
    "border": "#D7DCE2",
    "border_strong": "#B9C3CF",
    "text": "#0B1220",
    "text_soft": "#334155",
    "muted": "#6B7A90",
    "primary": "#338CE4",
    "cyan": "#338CE4",
    "hot": "#F97316",
    "success": "#16A36A",
    "danger": "#DC5A67",
    "warning": "#E9A318",
    "input": "#FFFFFF",
}


def projects_theme_mode() -> str:
    return normalize_theme_mode(get_theme_preference())


def projects_palette(mode: str | None = None) -> dict[str, str]:
    mode = normalize_theme_mode(mode or projects_theme_mode())
    if mode == THEME_UI_DARK:
        return DARK
    if mode == THEME_UI_LIGHT:
        return LIGHT
    return CLASSIC


def premium_projects_enabled(mode: str | None = None) -> bool:
    # 8E unified UI: all appearance modes share the same premium layout.
    # The selected theme changes only the palette, never the page structure.
    return True


def add_soft_shadow(widget: QWidget, *, dark: bool = False, blur: int = 24, y: int = 5) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(float(blur))
    effect.setOffset(0.0, float(y))
    effect.setColor(QColor(0, 0, 0, 105 if dark else 32))
    widget.setGraphicsEffect(effect)


def projects_stylesheet(mode: str | None = None) -> str:
    mode = normalize_theme_mode(mode or projects_theme_mode())
    p = projects_palette(mode)
    dark = mode == THEME_UI_DARK
    hero_start = "#08192B" if dark else "#F8FCFF"
    hero_end = "#0D2240" if dark else "#EAF5FF"
    selected = "#123B61" if dark else "#E6F3FF"
    hover = "#102E4C" if dark else "#F0F8FF"

    return f"""
        QWidget#CommercialProjectsRoot,
        QWidget#AdminCommercialProjectsRoot {{
            background:{p['bg']};
            color:{p['text']};
        }}

        QFrame#ProjectsHero {{
            background:qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {hero_start},
                stop:1 {hero_end}
            );
            border:1px solid {p['border']};
            border-radius:20px;
        }}
        QLabel#ProjectsEyebrow {{
            color:{p['cyan']};
            font-size:10px;
            font-weight:900;
            letter-spacing:1px;
        }}
        QLabel#ProjectsTitle {{
            color:{p['text']};
            font-size:27px;
            font-weight:900;
        }}
        QLabel#ProjectsSubtitle {{
            color:{p['muted']};
            font-size:12px;
        }}

        QFrame#MetricCard {{
            background:{p['surface']};
            border:1px solid {p['border']};
            border-radius:15px;
        }}
        QLabel#MetricCaption {{
            color:{p['muted']};
            font-size:10px;
            font-weight:800;
        }}
        QLabel#MetricValue {{
            color:{p['text']};
            font-size:20px;
            font-weight:900;
        }}

        QFrame#ProjectsPanel {{
            background:{p['surface']};
            border:1px solid {p['border']};
            border-radius:18px;
        }}
        QLabel#PanelTitle {{
            color:{p['text']};
            font-size:15px;
            font-weight:900;
        }}
        QLabel#PanelHint {{
            color:{p['muted']};
            font-size:10px;
        }}
        QLabel#StatusBadge {{
            color:{'#89E8B9' if dark else '#087548'};
            background:{'#0D3A2B' if dark else '#E8F8EF'};
            border:1px solid {'#246949' if dark else '#B8E8CD'};
            border-radius:10px;
            padding:3px 9px;
            font-size:10px;
            font-weight:900;
        }}

        QPushButton#PrimaryAction {{
            min-height:34px;
            color:#FFFFFF;
            background:qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #338CE4,
                stop:1 #5D67F2
            );
            border:1px solid #62AEF2;
            border-radius:10px;
            padding:0 14px;
            font-size:11px;
            font-weight:900;
        }}
        QPushButton#PrimaryAction:hover {{
            border-color:#9AD5FF;
        }}
        QPushButton#SecondaryAction {{
            min-height:34px;
            color:{p['text_soft']};
            background:{p['surface_alt']};
            border:1px solid {p['border']};
            border-radius:10px;
            padding:0 13px;
            font-size:11px;
            font-weight:800;
        }}
        QPushButton#SecondaryAction:hover {{
            color:{p['text']};
            background:{hover};
            border-color:{p['primary']};
        }}
        QPushButton#DangerAction {{
            min-height:34px;
            color:{'#FF9AA4' if dark else '#B42335'};
            background:{'#321822' if dark else '#FFF2F3'};
            border:1px solid {'#6A2A38' if dark else '#F4C8CE'};
            border-radius:10px;
            padding:0 13px;
            font-size:11px;
            font-weight:800;
        }}
        QPushButton#DangerAction:hover {{
            border-color:{p['danger']};
        }}

        QPushButton#ProjectChoiceCard {{
            text-align:left;
            min-height:94px;
            color:{p['text']};
            background:{p['surface']};
            border:1px solid {p['border']};
            border-radius:16px;
            padding:14px 17px;
            font-size:12px;
            font-weight:800;
        }}
        QPushButton#ProjectChoiceCard:hover {{
            background:{hover};
            border:1px solid {p['primary']};
        }}
        QPushButton#ProjectChoiceCard:pressed {{
            background:{selected};
        }}
        QPushButton#ProjectLandingAction {{
            min-height:38px;
            color:#FFFFFF;
            background:qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #168FD8,
                stop:1 #5D67F2
            );
            border:1px solid #62AEF2;
            border-radius:10px;
            padding:0 13px;
            font-size:11px;
            font-weight:900;
        }}
        QPushButton#ProjectLandingAction:hover {{
            border-color:#A8DFFF;
        }}

        QLineEdit {{
            min-height:34px;
            color:{p['text']};
            background:{p['input']};
            border:1px solid {p['border']};
            border-radius:10px;
            padding:0 10px;
            selection-background-color:#338CE4;
            selection-color:#FFFFFF;
        }}
        QLineEdit:focus {{
            border:1px solid {p['cyan']};
        }}
        QTextEdit {{
            color:{p['text']};
            background:{p['input']};
            border:1px solid {p['border']};
            border-radius:10px;
            padding:8px;
        }}
        QComboBox {{
            min-height:34px;
            color:{p['text']};
            background:{p['input']};
            border:1px solid {p['border']};
            border-radius:10px;
            padding:0 10px;
        }}
        QComboBox QAbstractItemView {{
            color:{p['text']};
            background:{p['surface']};
            border:1px solid {p['border']};
            selection-background-color:{selected};
        }}

        QTableWidget {{
            color:{p['text_soft']};
            background:{p['surface_alt']};
            alternate-background-color:{p['surface']};
            border:1px solid {p['border']};
            border-radius:11px;
            gridline-color:{p['border']};
            outline:0;
            font-size:11px;
        }}
        QTableWidget::item {{
            padding:7px 8px;
            border-bottom:1px solid {p['border']};
        }}
        QTableWidget::item:selected {{
            color:{p['text']};
            background:{selected};
        }}
        QHeaderView::section {{
            color:{p['text']};
            background:{p['surface_soft']};
            border:none;
            border-right:1px solid {p['border']};
            border-bottom:1px solid {p['border_strong']};
            padding:7px 8px;
            font-size:10px;
            font-weight:900;
        }}

        QScrollArea {{
            border:none;
            background:transparent;
        }}
        QScrollBar:vertical {{
            background:transparent;
            width:8px;
            margin:3px;
        }}
        QScrollBar::handle:vertical {{
            background:{p['border_strong']};
            min-height:32px;
            border-radius:4px;
        }}
    """


def apply_project_dialog_theme(dialog: QWidget, mode: str | None = None) -> None:
    mode = normalize_theme_mode(mode or projects_theme_mode())
    p = projects_palette(mode)
    dialog.setStyleSheet(
        projects_stylesheet(mode)
        + f"""
        QDialog {{
            background:{p['bg']};
            color:{p['text']};
        }}
        QLabel {{
            color:{p['text_soft']};
            font-size:11px;
            font-weight:700;
        }}
        QDialogButtonBox QPushButton {{
            min-width:90px;
            min-height:34px;
            color:{p['text_soft']};
            background:{p['surface']};
            border:1px solid {p['border']};
            border-radius:9px;
            padding:0 12px;
            font-weight:800;
        }}
        QDialogButtonBox QPushButton:hover {{
            border-color:{p['primary']};
            color:{p['text']};
        }}
        """
    )
