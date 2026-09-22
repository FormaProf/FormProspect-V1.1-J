from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    get_theme_preference,
    normalize_theme_mode,
)


def trainer_availability_palette(mode: str | None = None) -> dict[str, str]:
    mode = normalize_theme_mode(mode or get_theme_preference())

    if mode == THEME_UI_DARK:
        return {
            "page": "#07101A",
            "card": "#0D1826",
            "card_alt": "#101E2E",
            "header_a": "#0B1B2D",
            "header_b": "#123B63",
            "text": "#F7FAFC",
            "text_soft": "#D4DEE9",
            "muted": "#92A6BC",
            "border": "#1E3248",
            "border_strong": "#2B4662",
            "primary": "#338CE4",
            "primary_hover": "#4A9BE8",
            "primary_soft": "#102A46",
            "primary_text": "#8BCBFF",
            "success": "#4DD6A1",
            "success_soft": "#102D27",
            "warning": "#F5C761",
            "warning_soft": "#332A16",
            "danger": "#FF8498",
            "danger_soft": "#351923",
            "violet": "#B7A7FF",
            "violet_soft": "#24203F",
            "table_header": "#102B47",
            "table_row": "#0D1826",
            "table_row_alt": "#0F1C2C",
            "selected": "#123B63",
            "scroll": "#2A4864",
            "disabled_bg": "#142335",
            "disabled_text": "#6F8297",
        }

    if mode == THEME_CLASSIC:
        return {
            "page": "#F3F6FA",
            "card": "#FFFFFF",
            "card_alt": "#F8FBFE",
            "header_a": "#071B38",
            "header_b": "#0B2A52",
            "text": "#0B1220",
            "text_soft": "#334155",
            "muted": "#6B7A90",
            "border": "#DDE6F0",
            "border_strong": "#CAD7E6",
            "primary": "#338CE4",
            "primary_hover": "#287FD4",
            "primary_soft": "#EAF4FF",
            "primary_text": "#166FC1",
            "success": "#16A36A",
            "success_soft": "#ECFDF5",
            "warning": "#C98510",
            "warning_soft": "#FFF8E8",
            "danger": "#D64B62",
            "danger_soft": "#FFF0F3",
            "violet": "#7C5CE7",
            "violet_soft": "#F4F1FF",
            "table_header": "#0B2A52",
            "table_row": "#FFFFFF",
            "table_row_alt": "#FAFCFF",
            "selected": "#EAF4FF",
            "scroll": "#C1CFDE",
            "disabled_bg": "#E8EEF5",
            "disabled_text": "#94A3B8",
        }

    return {
        "page": "#F7F9FC",
        "card": "#FFFFFF",
        "card_alt": "#F8FBFF",
        "header_a": "#0B2037",
        "header_b": "#164C78",
        "text": "#071A31",
        "text_soft": "#3A5068",
        "muted": "#71849A",
        "border": "#E0E8F1",
        "border_strong": "#CEDAE7",
        "primary": "#338CE4",
        "primary_hover": "#287FD4",
        "primary_soft": "#EAF4FF",
        "primary_text": "#1473C9",
        "success": "#15956A",
        "success_soft": "#ECFDF5",
        "warning": "#BE7A0B",
        "warning_soft": "#FFF8E8",
        "danger": "#CF4860",
        "danger_soft": "#FFF0F3",
        "violet": "#7657DA",
        "violet_soft": "#F4F1FF",
        "table_header": "#0D2A46",
        "table_row": "#FFFFFF",
        "table_row_alt": "#FBFDFF",
        "selected": "#EAF4FF",
        "scroll": "#C5D2E0",
        "disabled_bg": "#E8EEF5",
        "disabled_text": "#8A9AAE",
    }


def trainer_availability_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#TrainerAvailabilityPage {{
        background: {p["page"]};
    }}
    QScrollArea#TrainerAvailabilityScroll {{
        background: transparent;
        border: none;
    }}
    QWidget#TrainerAvailabilityContent {{
        background: {p["page"]};
    }}

    QFrame#TrainerAvailabilityHero {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["header_a"]},
            stop:1 {p["header_b"]}
        );
        border: 1px solid {p["border_strong"]};
        border-radius: 18px;
    }}
    QLabel#TrainerAvailabilityOverline {{
        color: #62B5FF;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1.1px;
        background: transparent;
        border: none;
    }}
    QLabel#TrainerAvailabilityTitle {{
        color: #FFFFFF;
        font-size: 27px;
        font-weight: 900;
        background: transparent;
        border: none;
    }}
    QLabel#TrainerAvailabilitySubtitle {{
        color: #BFD0E3;
        font-size: 11px;
        background: transparent;
        border: none;
    }}
    QLabel#TrainerAvailabilityCloud {{
        background: rgba(0, 0, 0, 45);
        color: #8ED1FF;
        border: 1px solid #2A6595;
        border-radius: 9px;
        padding: 0 10px;
        font-size: 10px;
        font-weight: 900;
    }}

    QFrame[trainerCard="true"] {{
        background: {p["card"]};
        border: 1px solid {p["border"]};
        border-radius: 15px;
    }}
    QLabel[trainerLabel="true"] {{
        color: {p["text_soft"]};
        font-size: 10px;
        font-weight: 850;
        background: transparent;
        border: none;
    }}
    QLabel[trainerValue="true"] {{
        color: {p["text"]};
        font-size: 22px;
        font-weight: 900;
        background: transparent;
        border: none;
    }}
    QLabel[trainerCaption="true"] {{
        color: {p["muted"]};
        font-size: 9px;
        background: transparent;
        border: none;
    }}
    QLabel[trainerSectionOverline="true"] {{
        color: {p["primary"]};
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1px;
        background: transparent;
        border: none;
    }}
    QLabel[trainerSectionTitle="true"] {{
        color: {p["text"]};
        font-size: 18px;
        font-weight: 900;
        background: transparent;
        border: none;
    }}
    QLabel[trainerBody="true"] {{
        color: {p["muted"]};
        font-size: 10px;
        background: transparent;
        border: none;
    }}

    QPushButton#TrainerPrimaryButton {{
        background: {p["primary"]};
        color: white;
        border: none;
        border-radius: 10px;
        min-height: 38px;
        padding: 0 16px;
        font-size: 10px;
        font-weight: 900;
    }}
    QPushButton#TrainerPrimaryButton:hover {{
        background: {p["primary_hover"]};
    }}
    QPushButton#TrainerSecondaryButton {{
        background: {p["card_alt"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 10px;
        min-height: 38px;
        padding: 0 14px;
        font-size: 10px;
        font-weight: 850;
    }}
    QPushButton#TrainerSecondaryButton:hover {{
        color: {p["primary"]};
        border-color: {p["primary"]};
    }}
    QPushButton#TrainerSecondaryButton:disabled,
    QPushButton#TrainerPrimaryButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
        border-color: {p["border"]};
    }}

    QProgressBar#TrainerCoverageBar {{
        background: {p["card_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 7px;
        height: 12px;
        color: transparent;
        text-align: center;
    }}
    QProgressBar#TrainerCoverageBar::chunk {{
        background: {p["primary"]};
        border-radius: 6px;
    }}

    QTableWidget#TrainerAvailabilityTable {{
        background: {p["table_row"]};
        alternate-background-color: {p["table_row_alt"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
        gridline-color: transparent;
        selection-background-color: {p["selected"]};
        selection-color: {p["text"]};
        outline: none;
        font-size: 10px;
    }}
    QTableWidget#TrainerAvailabilityTable::item {{
        border: none;
        border-bottom: 1px solid {p["border"]};
        padding: 9px 8px;
    }}
    QTableWidget#TrainerAvailabilityTable::item:selected {{
        background: {p["selected"]};
        color: {p["text"]};
    }}
    QHeaderView::section {{
        background: {p["table_header"]};
        color: #FFFFFF;
        border: none;
        border-right: 1px solid rgba(255,255,255,35);
        padding: 10px 8px;
        font-size: 10px;
        font-weight: 900;
    }}

    QLabel#TrainerAvailabilityStatus {{
        background: {p["card_alt"]};
        color: {p["muted"]};
        border: 1px solid {p["border"]};
        border-radius: 9px;
        padding: 8px 10px;
        font-size: 9px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p["scroll"]};
        min-height: 40px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """


def trainer_status_badge_style(p: dict[str, str], active: bool) -> str:
    if active:
        return (
            f"background:{p['success_soft']};color:{p['success']};"
            f"border:1px solid {p['success']};border-radius:9px;"
            "padding:0 11px;font-size:10px;font-weight:900;"
        )
    return (
        f"background:{p['card_alt']};color:{p['muted']};"
        f"border:1px solid {p['border']};border-radius:9px;"
        "padding:0 11px;font-size:10px;font-weight:900;"
    )


def trainer_platform_badge_style(p: dict[str, str], linked: bool) -> str:
    if linked:
        return (
            f"background:{p['violet_soft']};color:{p['violet']};"
            f"border:1px solid {p['violet']};border-radius:9px;"
            "padding:6px 10px;font-size:10px;font-weight:850;"
        )
    return (
        f"background:{p['card_alt']};color:{p['muted']};"
        f"border:1px solid {p['border']};border-radius:9px;"
        "padding:6px 10px;font-size:10px;font-weight:800;"
    )


def trainer_row_button_style(p: dict[str, str], enabled: bool) -> str:
    if enabled:
        return (
            f"QPushButton{{background:{p['primary']};color:#FFFFFF;border:none;"
            "border-radius:9px;padding:0 14px;font-size:10px;font-weight:900;}"
            f"QPushButton:hover{{background:{p['primary_hover']};}}"
        )
    return (
        f"QPushButton{{background:{p['disabled_bg']};color:{p['disabled_text']};"
        "border:none;border-radius:9px;padding:0 14px;font-size:10px;font-weight:850;}"
    )
