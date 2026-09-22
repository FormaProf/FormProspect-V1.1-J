from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    normalize_theme_mode,
)


def commissions_palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)

    if mode == THEME_UI_DARK:
        return {
            "page": "#07101A",
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
            "primary_pressed": "#2575BF",
            "primary_soft": "#102A46",
            "primary_text": "#83C6FF",
            "finance": "#8FB8FF",
            "input_bg": "#0A1624",
            "table_header": "#0A2340",
            "table_row": "#0D1826",
            "table_row_alt": "#101E2E",
            "row_selected": "#123B63",
            "scroll": "#2A4864",
            "disabled_bg": "#142335",
            "disabled_text": "#6F8297",
            "success": "#4DD6A1",
            "success_bg": "#102D27",
            "success_text": "#83E7BD",
            "success_border": "#245A4C",
            "warning": "#F5C761",
            "warning_bg": "#332A16",
            "warning_text": "#FFD979",
            "warning_border": "#67562A",
            "danger": "#FF8498",
            "danger_bg": "#351923",
            "danger_text": "#FF9CAD",
            "danger_border": "#6A3340",
            "info_bg": "#102A46",
            "info_text": "#83C6FF",
            "info_border": "#27547C",
            "violet": "#B7A7FF",
            "violet_bg": "#24203F",
            "violet_text": "#CABEFF",
            "violet_border": "#50467B",
            "neutral_bg": "#132233",
            "neutral_text": "#B7C6D6",
            "neutral_border": "#2B435D",
        }

    if mode == THEME_UI_LIGHT:
        return {
            "page": "#F4F8FC",
            "card": "#FFFFFF",
            "card_alt": "#F8FBFF",
            "header_a": "#FFFFFF",
            "header_b": "#EAF4FF",
            "text": "#0A1526",
            "text_soft": "#3F536B",
            "muted": "#71839A",
            "border": "#DDE7F1",
            "border_strong": "#C9D9E8",
            "primary": "#338CE4",
            "primary_hover": "#247BD0",
            "primary_pressed": "#1D66B2",
            "primary_soft": "#EAF4FF",
            "primary_text": "#1768AE",
            "finance": "#0B2A52",
            "input_bg": "#FFFFFF",
            "table_header": "#0B2A52",
            "table_row": "#FFFFFF",
            "table_row_alt": "#FAFCFF",
            "row_selected": "#EAF4FF",
            "scroll": "#C4D2E1",
            "disabled_bg": "#E8EEF5",
            "disabled_text": "#8A9AAE",
            "success": "#16A34A",
            "success_bg": "#ECFDF3",
            "success_text": "#166534",
            "success_border": "#BBF7D0",
            "warning": "#D97706",
            "warning_bg": "#FFF7ED",
            "warning_text": "#9A3412",
            "warning_border": "#FED7AA",
            "danger": "#DC2626",
            "danger_bg": "#FEF2F2",
            "danger_text": "#991B1B",
            "danger_border": "#FECACA",
            "info_bg": "#EFF8FF",
            "info_text": "#075985",
            "info_border": "#BAE6FD",
            "violet": "#7C3AED",
            "violet_bg": "#F5F3FF",
            "violet_text": "#5B21B6",
            "violet_border": "#C4B5FD",
            "neutral_bg": "#F8FAFC",
            "neutral_text": "#475569",
            "neutral_border": "#E2E8F0",
        }

    return {
        "page": "#F8FAFD",
        "card": "#FFFFFF",
        "card_alt": "#FBFDFF",
        "header_a": "#FFFFFF",
        "header_b": "#EEF6FF",
        "text": "#0B1220",
        "text_soft": "#334155",
        "muted": "#6B7A90",
        "border": "#E4EBF4",
        "border_strong": "#D4E0EC",
        "primary": "#338CE4",
        "primary_hover": "#247BD0",
        "primary_pressed": "#1D66B2",
        "primary_soft": "#EAF4FF",
        "primary_text": "#1768AE",
        "finance": "#0B2A52",
        "input_bg": "#FFFFFF",
        "table_header": "#0B2A52",
        "table_row": "#FFFFFF",
        "table_row_alt": "#FBFDFF",
        "row_selected": "#EAF4FF",
        "scroll": "#CBD5E1",
        "disabled_bg": "#E8EEF5",
        "disabled_text": "#94A3B8",
        "success": "#16A34A",
        "success_bg": "#ECFDF3",
        "success_text": "#166534",
        "success_border": "#BBF7D0",
        "warning": "#D97706",
        "warning_bg": "#FFF7ED",
        "warning_text": "#9A3412",
        "warning_border": "#FED7AA",
        "danger": "#DC2626",
        "danger_bg": "#FEF2F2",
        "danger_text": "#991B1B",
        "danger_border": "#FECACA",
        "info_bg": "#EFF8FF",
        "info_text": "#075985",
        "info_border": "#BAE6FD",
        "violet": "#7C3AED",
        "violet_bg": "#F5F3FF",
        "violet_text": "#5B21B6",
        "violet_border": "#C4B5FD",
        "neutral_bg": "#F8FAFC",
        "neutral_text": "#475569",
        "neutral_border": "#E2E8F0",
    }


def commissions_page_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#CommissionsPage {{
        background:{p["page"]};
        color:{p["text"]};
    }}

    QFrame#SalesHeader {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {p["header_a"]},
            stop:1 {p["header_b"]}
        );
        border:1px solid {p["border"]};
        border-radius:20px;
    }}
    QLabel#SalesEyebrow, QLabel#SalesSectionEyebrow {{
        color:{p["primary"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:900;
        letter-spacing:1px;
    }}
    QLabel#SalesTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:28px;
        font-weight:900;
    }}
    QLabel#SalesSubtitle {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:12px;
    }}

    QFrame#SalesPeriodPanel {{
        background:{p["card_alt"]};
        border:1px solid {p["border"]};
        border-radius:14px;
    }}
    QLabel#SalesPeriodLabel {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:1px;
    }}
    QComboBox#SalesPeriodCombo {{
        background:{p["input_bg"]};
        color:{p["text"]};
        border:1px solid {p["border_strong"]};
        border-radius:9px;
        padding:0 10px;
        font-size:11px;
        font-weight:800;
    }}
    QComboBox#SalesPeriodCombo:focus {{
        border:2px solid {p["primary"]};
    }}
    QComboBox#SalesPeriodCombo::drop-down {{
        border:none;
        width:22px;
    }}
    QComboBox#SalesPeriodCombo QAbstractItemView {{
        background:{p["card"]};
        color:{p["text"]};
        border:1px solid {p["border_strong"]};
        selection-background-color:{p["row_selected"]};
        selection-color:{p["text"]};
        outline:0;
    }}

    QLabel#SalesCloudBadge {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border:1px solid {p["info_border"]};
        border-radius:10px;
        padding:5px 10px;
        font-size:9px;
        font-weight:900;
    }}

    QPushButton#SalesPrimaryButton {{
        background:{p["primary"]};
        color:#FFFFFF;
        border:none;
        border-radius:10px;
        padding:0 15px;
        font-size:11px;
        font-weight:900;
    }}
    QPushButton#SalesPrimaryButton:hover {{
        background:{p["primary_hover"]};
    }}
    QPushButton#SalesPrimaryButton:pressed {{
        background:{p["primary_pressed"]};
    }}
    QPushButton#SalesPrimaryButton:disabled {{
        background:{p["disabled_bg"]};
        color:{p["disabled_text"]};
    }}

    QPushButton#SalesSecondaryButton {{
        background:{p["card"]};
        color:{p["text_soft"]};
        border:1px solid {p["border_strong"]};
        border-radius:10px;
        padding:0 14px;
        font-size:11px;
        font-weight:850;
    }}
    QPushButton#SalesSecondaryButton:hover {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border-color:{p["primary"]};
    }}
    QPushButton#SalesSecondaryButton:disabled {{
        background:{p["disabled_bg"]};
        color:{p["disabled_text"]};
        border-color:{p["border"]};
    }}

    QPushButton#SalesDangerButton {{
        background:{p["card"]};
        color:{p["danger_text"]};
        border:1px solid {p["danger_border"]};
        border-radius:10px;
        padding:0 14px;
        font-size:11px;
        font-weight:850;
    }}
    QPushButton#SalesDangerButton:hover {{
        background:{p["danger_bg"]};
        border-color:{p["danger"]};
    }}
    QPushButton#SalesDangerButton:disabled {{
        background:{p["disabled_bg"]};
        color:{p["disabled_text"]};
        border-color:{p["border"]};
    }}

    QFrame#SalesKpiCard, QFrame#SalesTableCard, QFrame#SalesFooter {{
        background:{p["card"]};
        border:1px solid {p["border"]};
    }}
    QFrame#SalesKpiCard {{
        border-radius:15px;
    }}
    QLabel#SalesKpiLabel {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:850;
    }}
    QLabel#SalesKpiValue {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:21px;
        font-weight:900;
    }}
    QLabel#SalesKpiHelper {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QFrame#SalesTableCard {{
        border-radius:18px;
    }}
    QLabel#SalesTableTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:18px;
        font-weight:900;
    }}
    QLabel#SalesTableHelper {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:10px;
    }}
    QLabel#SalesPeriodSummary {{
        color:{p["info_text"]};
        background:{p["info_bg"]};
        border:1px solid {p["info_border"]};
        border-radius:10px;
        padding:0 10px;
        font-size:10px;
        font-weight:900;
    }}

    QFrame#SalesEmptyState {{
        background:{p["card_alt"]};
        border:1px dashed {p["border_strong"]};
        border-radius:14px;
    }}
    QLabel#SalesEmptyIcon {{
        color:{p["success"]};
        background:{p["success_bg"]};
        border:1px solid {p["success_border"]};
        border-radius:18px;
        font-size:18px;
        font-weight:900;
    }}
    QLabel#SalesEmptyTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:14px;
        font-weight:900;
    }}
    QLabel#SalesEmptyHelper {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:10px;
    }}

    QFrame#SalesFooter {{
        border-radius:14px;
    }}
    QLabel#SalesStatusText {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:10px;
    }}
    """


def commissions_table_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QTableWidget {{
        background:{p["table_row"]};
        alternate-background-color:{p["table_row_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:14px;
        gridline-color:transparent;
        font-size:11px;
        outline:0;
        selection-background-color:{p["row_selected"]};
        selection-color:{p["text"]};
    }}
    QTableWidget::item {{
        padding:9px 8px;
        border:none;
        border-bottom:1px solid {p["border"]};
    }}
    QTableWidget::item:selected {{
        background:{p["row_selected"]};
        color:{p["text"]};
    }}
    QHeaderView {{
        background:{p["table_header"]};
        border:none;
    }}
    QHeaderView::section {{
        background:{p["table_header"]};
        color:#FFFFFF;
        border:none;
        border-right:1px solid rgba(255,255,255,0.08);
        padding:10px 8px;
        font-size:10px;
        font-weight:900;
    }}
    QScrollBar:vertical {{
        background:transparent;
        width:9px;
        margin:3px 1px 3px 1px;
    }}
    QScrollBar::handle:vertical {{
        background:{p["scroll"]};
        min-height:32px;
        border-radius:4px;
    }}
    QScrollBar:horizontal {{
        background:transparent;
        height:9px;
    }}
    QScrollBar::handle:horizontal {{
        background:{p["scroll"]};
        min-width:40px;
        border-radius:4px;
    }}
    """
