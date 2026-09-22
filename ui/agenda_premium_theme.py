from __future__ import annotations

from core.theme_settings import (
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    normalize_theme_mode,
)


def agenda_palette(mode) -> dict[str, str]:
    mode = normalize_theme_mode(mode)

    if mode == THEME_UI_DARK:
        return {
            "page": "#07101A",
            "surface": "#07101A",
            "card": "#0D1826",
            "card_alt": "#101E2E",
            "header_a": "#0C1A29",
            "header_b": "#123456",
            "text": "#F7FAFC",
            "text_soft": "#D4DEE9",
            "muted": "#92A6BC",
            "border": "#1E3248",
            "border_strong": "#2B4662",
            "primary": "#338CE4",
            "primary_hover": "#4A9BE8",
            "primary_soft": "#102A46",
            "primary_text": "#83C6FF",
            "navy": "#0A1B2D",
            "navy_hover": "#123A5C",
            "success": "#4DD6A1",
            "success_soft": "#102D27",
            "danger": "#FF8498",
            "danger_soft": "#351923",
            "warning": "#F5C761",
            "warning_soft": "#332A16",
            "violet": "#B7A7FF",
            "violet_soft": "#24203F",
            "row_selected": "#123B63",
            "scroll": "#2A4864",
            "disabled_bg": "#142335",
            "disabled_text": "#6F8297",
            "calendar_header_bg": "#0B1725",
            "calendar_header_text": "#AFC2D7",
            "calendar_weekend": "#FF8498",
            "calendar_outside": "#61758B",
        }

    if mode == THEME_UI_LIGHT:
        return {
            "page": "#F4F8FD",
            "surface": "#F4F8FD",
            "card": "#FFFFFF",
            "card_alt": "#F9FCFF",
            "header_a": "#FFFFFF",
            "header_b": "#EAF4FF",
            "text": "#0A1628",
            "text_soft": "#334A63",
            "muted": "#6E8198",
            "border": "#DDE7F2",
            "border_strong": "#CBD9E8",
            "primary": "#338CE4",
            "primary_hover": "#247BD0",
            "primary_soft": "#EAF4FF",
            "primary_text": "#0B5FC6",
            "navy": "#0B2A52",
            "navy_hover": "#123966",
            "success": "#168A5B",
            "success_soft": "#EAF8F1",
            "danger": "#C43D52",
            "danger_soft": "#FFF0F3",
            "warning": "#A66B0D",
            "warning_soft": "#FFF7E8",
            "violet": "#7455C9",
            "violet_soft": "#F2EEFF",
            "row_selected": "#EAF4FF",
            "scroll": "#BDD0E2",
            "disabled_bg": "#E8EEF5",
            "disabled_text": "#8A9AAE",
            "calendar_header_bg": "#F3F7FB",
            "calendar_header_text": "#5F738A",
            "calendar_weekend": "#D6485C",
            "calendar_outside": "#9AA9BA",
        }

    return {
        "page": "#F5F8FC",
        "surface": "#F5F8FC",
        "card": "#FFFFFF",
        "card_alt": "#FBFDFF",
        "header_a": "#FFFFFF",
        "header_b": "#EDF6FF",
        "text": "#0B1220",
        "text_soft": "#334155",
        "muted": "#6B7A90",
        "border": "#E4EBF4",
        "border_strong": "#D5E0EC",
        "primary": "#338CE4",
        "primary_hover": "#247BD0",
        "primary_soft": "#EAF4FF",
        "primary_text": "#075985",
        "navy": "#0B2A52",
        "navy_hover": "#123966",
        "success": "#168A5B",
        "success_soft": "#ECF8F2",
        "danger": "#C43D52",
        "danger_soft": "#FFF0F3",
        "warning": "#A66B0D",
        "warning_soft": "#FFF7E8",
        "violet": "#7455C9",
        "violet_soft": "#F2EEFF",
        "row_selected": "#EAF4FF",
        "scroll": "#CBD5E1",
        "disabled_bg": "#E8EEF5",
        "disabled_text": "#94A3B8",
        "calendar_header_bg": "#F4F7FB",
        "calendar_header_text": "#5F6F82",
        "calendar_weekend": "#D6485C",
        "calendar_outside": "#A3AFBE",
    }


def agenda_page_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#AgendaPageRoot,
    QWidget#AgendaContent,
    QScrollArea#AgendaScroll,
    QScrollArea#AgendaScroll > QWidget > QWidget {{
        background: {p["page"]};
        border: none;
    }}

    QFrame#AgendaHeader {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {p["header_a"]},
            stop:1 {p["header_b"]}
        );
        border: 1px solid {p["border"]};
        border-radius: 20px;
    }}

    QLabel#AgendaEyebrow,
    QLabel#AgendaSectionEyebrow {{
        color: {p["primary"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#AgendaTitle {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 27px;
        font-weight: 900;
    }}

    QLabel#AgendaSubtitle,
    QLabel#AgendaSectionHint {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 11px;
    }}

    QLabel#AgendaSectionTitle {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 18px;
        font-weight: 900;
    }}

    QFrame#AgendaMetricCard,
    QFrame#AgendaPanel {{
        background: {p["card"]};
        border: 1px solid {p["border"]};
        border-radius: 17px;
    }}

    QLabel#AgendaMetricTitle {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 11px;
        font-weight: 750;
    }}

    QLabel#AgendaMetricValue {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 23px;
        font-weight: 900;
    }}

    QLabel#AgendaMetricIcon {{
        border: none;
        border-radius: 12px;
        font-size: 18px;
        font-weight: 900;
    }}

    QFrame#AgendaMetricCard[tone="primary"] QLabel#AgendaMetricIcon {{
        color: {p["primary"]};
        background: {p["primary_soft"]};
    }}
    QFrame#AgendaMetricCard[tone="danger"] QLabel#AgendaMetricIcon {{
        color: {p["danger"]};
        background: {p["danger_soft"]};
    }}
    QFrame#AgendaMetricCard[tone="violet"] QLabel#AgendaMetricIcon {{
        color: {p["violet"]};
        background: {p["violet_soft"]};
    }}
    QFrame#AgendaMetricCard[tone="success"] QLabel#AgendaMetricIcon {{
        color: {p["success"]};
        background: {p["success_soft"]};
    }}

    QLabel#AgendaCountBadge {{
        color: {p["primary_text"]};
        background: {p["primary_soft"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 10px;
        padding: 0 10px;
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#AgendaLegend {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 750;
    }}
    QLabel#AgendaLegend[tone="primary"] {{ color: {p["primary"]}; }}
    QLabel#AgendaLegend[tone="planned"] {{ color: {p["primary_text"]}; }}
    QLabel#AgendaLegend[tone="danger"] {{ color: {p["danger"]}; }}

    QFrame#AgendaEmptyState {{
        background: {p["card_alt"]};
        border: 1px dashed {p["border_strong"]};
        border-radius: 14px;
    }}
    QLabel#AgendaEmptyIcon {{
        color: {p["success"]};
        background: {p["success_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 18px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        font-size: 18px;
        font-weight: 900;
    }}
    QLabel#AgendaEmptyTitle {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 14px;
        font-weight: 900;
    }}
    QLabel#AgendaEmptyHint {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 11px;
    }}

    QPushButton#AgendaPrimaryButton {{
        background: {p["primary"]};
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        padding: 0 15px;
        font-size: 11px;
        font-weight: 900;
    }}
    QPushButton#AgendaPrimaryButton:hover {{ background: {p["primary_hover"]}; }}
    QPushButton#AgendaPrimaryButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
    }}

    QPushButton#AgendaSecondaryButton {{
        background: {p["card"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 10px;
        padding: 0 14px;
        font-size: 11px;
        font-weight: 850;
    }}
    QPushButton#AgendaSecondaryButton:hover {{
        background: {p["primary_soft"]};
        color: {p["primary"]};
        border-color: {p["primary"]};
    }}
    QPushButton#AgendaSecondaryButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
        border-color: {p["border"]};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p["scroll"]};
        min-height: 38px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def agenda_calendar_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QCalendarWidget {{
        background: {p["card"]};
        color: {p["text"]};
        border: none;
    }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background: {p["navy"]};
        border-radius: 11px;
    }}
    QCalendarWidget QToolButton {{
        color: #FFFFFF;
        background: transparent;
        border: none;
        font-size: 12px;
        font-weight: 900;
        padding: 7px 8px;
        margin: 1px;
    }}
    QCalendarWidget QToolButton:hover {{
        background: {p["navy_hover"]};
        border-radius: 8px;
    }}
    QCalendarWidget QSpinBox {{
        background: {p["card"]};
        color: {p["text"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 7px;
        padding: 4px;
        font-weight: 800;
    }}
    QCalendarWidget QAbstractItemView:enabled {{
        background: {p["card"]};
        color: {p["text_soft"]};
        selection-background-color: {p["primary"]};
        selection-color: #FFFFFF;
        outline: 0;
        font-size: 11px;
    }}
    QCalendarWidget QAbstractItemView:disabled {{
        color: {p["disabled_text"]};
    }}
    """


def agenda_table_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QTableWidget#AgendaTable {{
        background: {p["card"]};
        alternate-background-color: {p["card_alt"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 13px;
        gridline-color: transparent;
        font-size: 11px;
        outline: 0;
    }}
    QTableWidget#AgendaTable::item {{
        padding: 8px 8px;
        border: none;
        border-bottom: 1px solid {p["border"]};
    }}
    QTableWidget#AgendaTable::item:selected {{
        background: {p["row_selected"]};
        color: {p["text"]};
    }}
    QHeaderView {{
        background: {p["navy"]};
        border: none;
    }}
    QHeaderView::section {{
        background: {p["navy"]};
        color: #FFFFFF;
        border: none;
        border-right: 1px solid {p["border_strong"]};
        padding: 9px 8px;
        font-size: 10px;
        font-weight: 900;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 9px;
        margin: 3px 1px;
    }}
    QScrollBar::handle:vertical {{
        background: {p["scroll"]};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 9px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p["scroll"]};
        min-width: 40px;
        border-radius: 4px;
    }}
    """
