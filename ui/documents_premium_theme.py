from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    normalize_theme_mode,
)


def documents_palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)

    if mode == THEME_UI_DARK:
        return {
            "page": "#07101A",
            "card": "#0D1826",
            "card_alt": "#101E2E",
            "header_a": "#0A1C30",
            "header_b": "#123A5C",
            "header_text": "#F8FBFF",
            "header_muted": "#AFC3D8",
            "header_accent": "#69B7FF",
            "text": "#F7FAFC",
            "text_soft": "#D4DEE9",
            "muted": "#92A6BC",
            "muted_2": "#6F8297",
            "border": "#1E3248",
            "border_strong": "#2B4662",
            "primary": "#338CE4",
            "primary_hover": "#4A9BE8",
            "primary_soft": "#102A46",
            "primary_text": "#83C6FF",
            "success": "#4DD6A1",
            "success_soft": "#102D27",
            "warning": "#F5C761",
            "warning_soft": "#332A16",
            "danger": "#FF8498",
            "danger_soft": "#351923",
            "violet": "#B7A7FF",
            "violet_soft": "#24203F",
            "table_header": "#101E2E",
            "table_header_text": "#C9D7E6",
            "row_selected": "#123B63",
            "disabled_bg": "#142335",
            "disabled_text": "#6F8297",
        }

    if mode == THEME_UI_LIGHT:
        return {
            "page": "#F4F7FB",
            "card": "#FFFFFF",
            "card_alt": "#F8FBFF",
            "header_a": "#0B223A",
            "header_b": "#0E365D",
            "header_text": "#FFFFFF",
            "header_muted": "#B9CCE0",
            "header_accent": "#69B7FF",
            "text": "#0B1220",
            "text_soft": "#334155",
            "muted": "#64748B",
            "muted_2": "#94A3B8",
            "border": "#E3EAF2",
            "border_strong": "#CBD7E4",
            "primary": "#338CE4",
            "primary_hover": "#247BD0",
            "primary_soft": "#EAF4FF",
            "primary_text": "#0B5EA8",
            "success": "#15803D",
            "success_soft": "#ECFDF5",
            "warning": "#B45309",
            "warning_soft": "#FFF7ED",
            "danger": "#B42318",
            "danger_soft": "#FFF1F0",
            "violet": "#6D28D9",
            "violet_soft": "#F5F3FF",
            "table_header": "#F1F5F9",
            "table_header_text": "#334155",
            "row_selected": "#EAF4FF",
            "disabled_bg": "#E8EEF5",
            "disabled_text": "#8A9AAE",
        }

    return {
        "page": "#F8FAFD",
        "card": "#FFFFFF",
        "card_alt": "#FBFDFF",
        "header_a": "#0B223A",
        "header_b": "#0E365D",
        "header_text": "#FFFFFF",
        "header_muted": "#B9CCE0",
        "header_accent": "#69B7FF",
        "text": "#0B1220",
        "text_soft": "#334155",
        "muted": "#6B7A90",
        "muted_2": "#94A3B8",
        "border": "#E7ECF3",
        "border_strong": "#D9E2EC",
        "primary": "#338CE4",
        "primary_hover": "#256DB4",
        "primary_soft": "#EAF4FF",
        "primary_text": "#0B5EA8",
        "success": "#16A34A",
        "success_soft": "#ECFDF5",
        "warning": "#B45309",
        "warning_soft": "#FFF7ED",
        "danger": "#B42318",
        "danger_soft": "#FFF1F0",
        "violet": "#6D28D9",
        "violet_soft": "#F5F3FF",
        "table_header": "#F4F7FA",
        "table_header_text": "#334155",
        "row_selected": "#EAF4FF",
        "disabled_bg": "#E8EEF5",
        "disabled_text": "#94A3B8",
    }


def documents_page_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#DocumentsPage {{
        background: {p["page"]};
        color: {p["text"]};
    }}
    QFrame#DocumentsHeader {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {p["header_a"]},
            stop:1 {p["header_b"]}
        );
        border: 1px solid {p["header_b"]};
        border-radius: 20px;
    }}
    QLabel#DocumentsEyebrow {{
        color: {p["header_accent"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1.1px;
    }}
    QLabel#DocumentsTitle {{
        color: {p["header_text"]};
        background: transparent;
        border: none;
        font-size: 28px;
        font-weight: 900;
    }}
    QLabel#DocumentsSubtitle {{
        color: {p["header_muted"]};
        background: transparent;
        border: none;
        font-size: 12px;
    }}
    QLabel#DocumentsModeChip {{
        background: rgba(51, 140, 228, 0.13);
        color: {p["header_accent"]};
        border: 1px solid {p["primary"]};
        border-radius: 10px;
        padding: 0 12px;
        font-size: 10px;
        font-weight: 900;
    }}

    QFrame#DocumentCard,
    QFrame#DocumentsMetricCard,
    QFrame#DocumentsCommandCard,
    QFrame#DocumentsLibraryCard {{
        background: {p["card"]};
        border: 1px solid {p["border"]};
        border-radius: 16px;
    }}
    QFrame#DocumentsMetricCard:hover,
    QFrame#DocumentsCommandCard:hover,
    QFrame#DocumentsLibraryCard:hover {{
        border-color: {p["border_strong"]};
    }}

    QLabel#DocumentsSectionEyebrow {{
        color: {p["primary"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1.05px;
    }}
    QLabel#DocumentsSectionTitle {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 17px;
        font-weight: 900;
    }}
    QLabel#DocumentsFieldLabel {{
        color: {p["text_soft"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 850;
    }}
    QLabel#DocumentsMutedText,
    QLabel#DocumentsStatus {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 650;
    }}
    QLabel#DocumentsStatusError {{
        color: {p["danger"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 850;
    }}

    QLabel#DocumentsMetricIcon {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: none;
        border-radius: 7px;
        font-size: 13px;
        font-weight: 900;
    }}
    QLabel#DocumentsMetricCaption {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 850;
    }}
    QLabel#DocumentsMetricValue {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 21px;
        font-weight: 900;
    }}
    QLabel#DocumentsMetricValueWarning {{
        color: {p["warning"]};
        background: transparent;
        border: none;
        font-size: 21px;
        font-weight: 900;
    }}
    QLabel#DocumentsMetricHint {{
        color: {p["muted_2"]};
        background: transparent;
        border: none;
        font-size: 9px;
    }}
    QLabel#DocumentsMetricHintWarning {{
        color: {p["warning"]};
        background: transparent;
        border: none;
        font-size: 9px;
        font-weight: 800;
    }}

    QLabel#DocumentsCountBadge {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 9px;
        padding: 0 10px;
        font-size: 10px;
        font-weight: 900;
    }}

    QFrame#CloudQuotaAlert {{
        background: {p["warning_soft"]};
        border: 1px solid {p["warning"]};
        border-radius: 13px;
    }}
    QLabel#CloudQuotaIcon {{
        background: {p["warning"]};
        color: white;
        border: none;
        border-radius: 15px;
        font-size: 15px;
        font-weight: 900;
    }}
    QLabel#CloudQuotaTitle {{
        color: {p["warning"]};
        background: transparent;
        border: none;
        font-size: 11px;
        font-weight: 900;
    }}
    QLabel#CloudQuotaText {{
        color: {p["text_soft"]};
        background: transparent;
        border: none;
        font-size: 10px;
        font-weight: 700;
    }}

    QFrame#DocumentInfoCard {{
        background: {p["card_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
    }}
    QLabel#DocumentInfoIcon {{
        background: {p["primary_soft"]};
        color: {p["primary"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 12px;
        font-size: 11px;
        font-weight: 900;
    }}
    QLabel#DocumentInfoText {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 9px;
    }}

    QFrame#DocumentsLibraryEmpty {{
        background: {p["card_alt"]};
        border: 1px dashed {p["border_strong"]};
        border-radius: 14px;
    }}
    QLabel#DocumentsEmptyIcon {{
        background: {p["primary_soft"]};
        color: {p["primary"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 23px;
        font-size: 19px;
        font-weight: 900;
    }}
    QLabel#DocumentsEmptyTitle {{
        color: {p["text"]};
        background: transparent;
        border: none;
        font-size: 15px;
        font-weight: 900;
    }}
    QLabel#DocumentsEmptyText {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 10px;
    }}
    QFrame#DocumentsSelectionBar {{
        background: transparent;
        border: none;
    }}

    QPushButton#DocumentsPrimaryButton {{
        background: {p["primary"]};
        color: white;
        border: none;
        border-radius: 10px;
        min-height: 38px;
        padding: 0 15px;
        font-size: 11px;
        font-weight: 900;
    }}
    QPushButton#DocumentsPrimaryButton:hover {{
        background: {p["primary_hover"]};
    }}
    QPushButton#DocumentsPrimaryButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
        border: 1px solid {p["border"]};
    }}

    QPushButton#DocumentsActionButton {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 1px solid {p["primary"]};
        border-radius: 11px;
        padding: 0 14px;
        text-align: left;
        font-size: 11px;
        font-weight: 900;
    }}
    QPushButton#DocumentsActionButton:hover {{
        background: {p["primary"]};
        color: white;
    }}
    QPushButton#DocumentsActionSuccessButton {{
        background: {p["success_soft"]};
        color: {p["success"]};
        border: 1px solid {p["success"]};
        border-radius: 11px;
        padding: 0 14px;
        text-align: left;
        font-size: 11px;
        font-weight: 900;
    }}
    QPushButton#DocumentsActionSuccessButton:hover {{
        background: {p["success"]};
        color: white;
    }}

    QPushButton#DocumentsSecondaryButton {{
        background: {p["card"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 9px;
        min-height: 36px;
        padding: 0 13px;
        font-size: 10px;
        font-weight: 850;
    }}
    QPushButton#DocumentsSecondaryButton:hover {{
        background: {p["card_alt"]};
        color: {p["primary"]};
        border-color: {p["primary"]};
    }}
    QPushButton#DocumentsDangerButton {{
        background: {p["card"]};
        color: {p["danger"]};
        border: 1px solid {p["danger"]};
        border-radius: 9px;
        min-height: 36px;
        padding: 0 13px;
        font-size: 10px;
        font-weight: 900;
    }}
    QPushButton#DocumentsDangerButton:hover {{
        background: {p["danger_soft"]};
    }}
    QPushButton#DocumentsDangerButton:disabled,
    QPushButton#DocumentsActionButton:disabled,
    QPushButton#DocumentsActionSuccessButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
        border-color: {p["border"]};
    }}

    QComboBox#DocumentsInput,
    QLineEdit#DocumentsInput {{
        background: {p["card_alt"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 9px;
        min-height: 38px;
        padding: 0 32px 0 11px;
        font-size: 11px;
        font-weight: 700;
    }}
    QComboBox#DocumentsInput:focus,
    QLineEdit#DocumentsInput:focus {{
        border: 2px solid {p["primary"]};
    }}
    QCheckBox#DocumentsCheck {{
        color: {p["text_soft"]};
        spacing: 7px;
        font-size: 10px;
        font-weight: 700;
    }}

    QLabel#DocumentsEmptyState {{
        background: {p["card"]};
        color: {p["muted"]};
        border: 1px dashed {p["border_strong"]};
        border-radius: 14px;
        padding: 16px;
        font-size: 12px;
        font-weight: 700;
    }}

    QTabWidget#DocumentsTabs::pane {{
        border: none;
        background: transparent;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {p["muted"]};
        border: none;
        padding: 10px 16px;
        font-weight: 800;
    }}
    QTabBar::tab:selected {{
        color: {p["primary"]};
        border-bottom: 2px solid {p["primary"]};
    }}
    """


def documents_table_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QTableWidget {{
        background: {p["card"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 11px;
        selection-background-color: {p["row_selected"]};
        selection-color: {p["text"]};
        font-size: 10px;
    }}
    QTableWidget::item {{
        background: {p["card"]};
        color: {p["text"]};
        border-bottom: 1px solid {p["border"]};
        padding: 7px 8px;
    }}
    QTableWidget::item:selected {{
        background: {p["row_selected"]};
        color: {p["text"]};
    }}
    QHeaderView::section {{
        background: {p["table_header"]};
        color: {p["table_header_text"]};
        border: none;
        border-right: 1px solid {p["border"]};
        border-bottom: 1px solid {p["border"]};
        padding: 9px 8px;
        font-size: 9px;
        font-weight: 900;
    }}
    """


def documents_badge_style(doc_type: str, mode: str) -> str:
    p = documents_palette(mode)
    value = str(doc_type or "").strip().lower()

    if value in {"devis", "facture"}:
        bg, fg = p["success_soft"], p["success"]
    elif value in {"programme", "attestation de formation"}:
        bg, fg = p["warning_soft"], p["warning"]
    elif value == "convocation":
        bg, fg = p["violet_soft"], p["violet"]
    else:
        bg, fg = p["primary_soft"], p["primary_text"]

    return (
        f"background:{bg};color:{fg};border:1px solid {fg};"
        "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
    )


def documents_origin_badge_style(origin: str, mode: str) -> str:
    p = documents_palette(mode)
    value = str(origin or "").strip().lower()
    generated = "généré" in value or "genere" in value
    bg = p["success_soft"] if generated else p["primary_soft"]
    fg = p["success"] if generated else p["primary_text"]
    return (
        f"background:{bg};color:{fg};border:1px solid {fg};"
        "border-radius:9px;padding:3px 8px;font-size:9px;font-weight:900;"
    )
