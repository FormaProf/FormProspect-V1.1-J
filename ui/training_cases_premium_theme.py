from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    normalize_theme_mode,
)


def training_cases_palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)

    if mode == THEME_UI_DARK:
        return {
            "page": "#07101A",
            "surface": "#0D1826",
            "surface_alt": "#101E2E",
            "surface_soft": "#0B1725",
            "header_a": "#0B1D31",
            "header_b": "#12385D",
            "text": "#F7FAFC",
            "text_soft": "#D4DEE9",
            "muted": "#93A6BA",
            "border": "#1F344A",
            "border_strong": "#2C4A67",
            "primary": "#338CE4",
            "primary_hover": "#4A9BE8",
            "primary_soft": "#102B48",
            "primary_text": "#86C9FF",
            "success": "#4DD6A1",
            "success_soft": "#102E27",
            "warning": "#F5C761",
            "warning_soft": "#332A16",
            "danger": "#FF8498",
            "danger_soft": "#351923",
            "violet": "#B7A7FF",
            "violet_soft": "#24203F",
            "table_header": "#112B45",
            "row": "#0D1826",
            "row_alt": "#0F1C2B",
            "row_selected": "#123C64",
            "disabled_bg": "#142335",
            "disabled_text": "#708398",
            "scroll": "#2A4864",
        }

    if mode == THEME_UI_LIGHT:
        return {
            "page": "#F4F8FC",
            "surface": "#FFFFFF",
            "surface_alt": "#F8FBFE",
            "surface_soft": "#F1F7FD",
            "header_a": "#0B2442",
            "header_b": "#123E70",
            "text": "#0B1220",
            "text_soft": "#334155",
            "muted": "#68798E",
            "border": "#DFE8F2",
            "border_strong": "#C8D8E8",
            "primary": "#338CE4",
            "primary_hover": "#267BD0",
            "primary_soft": "#EAF4FF",
            "primary_text": "#0B5EA8",
            "success": "#0F9F6E",
            "success_soft": "#EAF9F3",
            "warning": "#C67C12",
            "warning_soft": "#FFF6E5",
            "danger": "#C93D53",
            "danger_soft": "#FFF0F3",
            "violet": "#7256D9",
            "violet_soft": "#F3F0FF",
            "table_header": "#0D3158",
            "row": "#FFFFFF",
            "row_alt": "#FAFCFE",
            "row_selected": "#EAF4FF",
            "disabled_bg": "#E8EEF5",
            "disabled_text": "#8B9AAD",
            "scroll": "#B7C8D9",
        }

    return {
        "page": "#F7F9FC",
        "surface": "#FFFFFF",
        "surface_alt": "#FBFDFF",
        "surface_soft": "#F3F7FB",
        "header_a": "#0B2442",
        "header_b": "#123E70",
        "text": "#0B1220",
        "text_soft": "#334155",
        "muted": "#6B7A90",
        "border": "#E3EAF2",
        "border_strong": "#CFDCE8",
        "primary": "#338CE4",
        "primary_hover": "#267BD0",
        "primary_soft": "#EAF4FF",
        "primary_text": "#0B5EA8",
        "success": "#169A6E",
        "success_soft": "#ECF9F4",
        "warning": "#C67C12",
        "warning_soft": "#FFF6E5",
        "danger": "#C93D53",
        "danger_soft": "#FFF1F3",
        "violet": "#7256D9",
        "violet_soft": "#F4F1FF",
        "table_header": "#0D3158",
        "row": "#FFFFFF",
        "row_alt": "#FBFDFF",
        "row_selected": "#EAF4FF",
        "disabled_bg": "#E8EEF5",
        "disabled_text": "#94A3B8",
        "scroll": "#BBC9D7",
    }


def page_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#TrainingCasesRoot {{
        background: {p["page"]};
    }}

    QFrame[financeCard="true"] {{
        background: {p["surface"]};
        border: 1px solid {p["border"]};
        border-radius: 16px;
    }}

    QFrame[financeHeroCard="true"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {p["surface"]},
            stop:1 {p["surface_soft"]}
        );
        border: 1px solid {p["border_strong"]};
        border-radius: 18px;
    }}

    QFrame[financeActionCard="true"] {{
        background: {p["surface"]};
        border: 1px solid {p["border"]};
        border-radius: 18px;
    }}

    QFrame[financeFlowCard="true"] {{
        background: {p["surface"]};
        border: 1px solid {p["border"]};
        border-radius: 18px;
    }}

    QFrame[financeMiniStat="true"] {{
        background: {p["surface_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
    }}

    QFrame[financeFlowStage="true"] {{
        background: {p["surface_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
    }}

    QFrame[financeWorkspaceNav="true"] {{
        background: {p["surface"]};
        border: 1px solid {p["border"]};
        border-radius: 18px;
    }}

    QScrollArea#FinanceWorkspaceScroll {{
        background: transparent;
        border: none;
    }}

    QScrollArea#FinanceWorkspaceScroll > QWidget > QWidget {{
        background: transparent;
    }}

    QScrollArea#FinanceWorkspaceScroll QScrollBar:vertical {{
        background: {p["surface_alt"]};
        width: 10px;
        margin: 2px 0 2px 0;
        border: none;
        border-radius: 5px;
    }}

    QScrollArea#FinanceWorkspaceScroll QScrollBar::handle:vertical {{
        background: {p["border_strong"]};
        min-height: 34px;
        border-radius: 5px;
    }}

    QScrollArea#FinanceWorkspaceScroll QScrollBar::handle:vertical:hover {{
        background: {p["primary"]};
    }}

    QScrollArea#FinanceWorkspaceScroll QScrollBar::add-line:vertical,
    QScrollArea#FinanceWorkspaceScroll QScrollBar::sub-line:vertical {{
        height: 0px;
        border: none;
        background: transparent;
    }}

    QPushButton[financeWorkspaceButton="true"] {{
        background: {p["surface_alt"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 13px;
        padding: 7px 14px;
        text-align: left;
        font-size: 10px;
        font-weight: 850;
    }}

    QPushButton[financeWorkspaceButton="true"]:hover {{
        background: {p["surface_soft"]};
        color: {p["primary_text"]};
        border-color: {p["border_strong"]};
    }}

    QPushButton[financeWorkspaceButton="true"]:checked {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 2px solid {p["primary"]};
        padding: 6px 13px;
    }}

    QFrame[financeWorkspaceHeader="true"] {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["surface_alt"]},
            stop:1 {p["surface_soft"]}
        );
        border: 1px solid {p["border"]};
        border-radius: 14px;
    }}

    QLabel[financeWorkspaceIcon="true"] {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 11px;
        font-size: 9px;
        font-weight: 950;
    }}

    QFrame[financeToolbar="true"] {{
        background: {p["surface_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 14px;
    }}

    QLabel[financeToolbarLabel="true"] {{
        color: {p["text_soft"]};
        background: transparent;
        border: none;
        font-size: 9px;
        font-weight: 900;
        letter-spacing: 0.8px;
    }}

    QLabel[financeToolbarHint="true"] {{
        color: {p["muted"]};
        background: transparent;
        border: none;
        font-size: 9px;
        font-weight: 650;
    }}

    QFrame[financeToolbarDivider="true"] {{
        background: {p["border"]};
        border: none;
    }}

    QLabel[financeHeroValue="true"] {{
        color: {p["text"]};
        font-size: 34px;
        font-weight: 950;
        background: transparent;
        border: none;
    }}

    QLabel[financeMiniStatLabel="true"] {{
        color: {p["muted"]};
        font-size: 9px;
        font-weight: 800;
        background: transparent;
        border: none;
    }}

    QLabel[financeMiniStatValue="true"] {{
        color: {p["text"]};
        font-size: 20px;
        font-weight: 950;
        background: transparent;
        border: none;
    }}

    QLabel[financeFlowLabel="true"] {{
        color: {p["text_soft"]};
        font-size: 10px;
        font-weight: 850;
        background: transparent;
        border: none;
    }}

    QLabel[financeFlowValue="true"] {{
        color: {p["text"]};
        font-size: 22px;
        font-weight: 950;
        background: transparent;
        border: none;
    }}

    QLabel[financeFlowCaption="true"] {{
        color: {p["muted"]};
        font-size: 8px;
        background: transparent;
        border: none;
    }}

    QLabel[financeOverline="true"] {{
        color: {p["primary"]};
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1px;
        background: transparent;
        border: none;
    }}

    QLabel[financeSectionTitle="true"] {{
        color: {p["text"]};
        font-size: 18px;
        font-weight: 900;
        background: transparent;
        border: none;
    }}

    QLabel[financeBody="true"] {{
        color: {p["muted"]};
        font-size: 10px;
        background: transparent;
        border: none;
    }}

    QLabel[financeKpiLabel="true"] {{
        color: {p["text_soft"]};
        font-size: 10px;
        font-weight: 800;
        background: transparent;
        border: none;
    }}

    QLabel[financeKpiValue="true"] {{
        color: {p["text"]};
        font-size: 23px;
        font-weight: 950;
        background: transparent;
        border: none;
    }}

    QLabel[financeKpiCaption="true"] {{
        color: {p["muted"]};
        font-size: 9px;
        background: transparent;
        border: none;
    }}

    QLabel[financeStatus="true"] {{
        color: {p["muted"]};
        font-size: 9px;
        font-weight: 700;
        background: transparent;
        border: none;
    }}

    QLabel[financeCountBadge="true"] {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 1px solid {p["border_strong"]};
        border-radius: 9px;
        padding: 0 10px;
        font-size: 10px;
        font-weight: 900;
    }}

    QTabWidget#FinanceTabs::pane {{
        border: 1px solid {p["border"]};
        border-radius: 16px;
        background: {p["surface"]};
        top: -1px;
    }}

    QTabWidget#FinanceTabs QTabBar::tab {{
        background: {p["surface_alt"]};
        color: {p["muted"]};
        border: 1px solid {p["border"]};
        border-radius: 10px;
        padding: 9px 18px;
        margin-right: 6px;
        font-size: 10px;
        font-weight: 850;
    }}

    QTabWidget#FinanceTabs QTabBar::tab:selected {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border: 1px solid {p["primary"]};
    }}

    QTabWidget#FinanceTabs QTabBar::tab:hover:!selected {{
        color: {p["primary_text"]};
        background: {p["surface_soft"]};
        border-color: {p["border_strong"]};
    }}

    QCheckBox {{
        color: {p["text_soft"]};
        spacing: 6px;
        font-size: 10px;
        font-weight: 750;
        background: transparent;
    }}

    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {p["scroll"]};
        min-height: 32px;
        border-radius: 5px;
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal {{
        background: {p["scroll"]};
        min-width: 32px;
        border-radius: 5px;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    """


def header_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QFrame#CommercialDocsHeader {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["header_a"]},
            stop:1 {p["header_b"]}
        );
        border: 1px solid {p["border_strong"]};
        border-radius: 20px;
    }}
    QFrame#CommercialDocsHeader QLabel {{
        background: transparent;
        border: none;
    }}
    """


def input_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QLineEdit, QComboBox {{
        background: {p["surface_alt"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        border-radius: 10px;
        padding: 0 11px;
        min-height: 38px;
        font-size: 11px;
        font-weight: 700;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 2px solid {p["primary"]};
    }}
    QComboBox::drop-down {{
        border: none;
        border-left: 1px solid {p["border"]};
        width: 28px;
        background: {p["surface_soft"]};
    }}
    QComboBox QAbstractItemView {{
        background: {p["surface"]};
        color: {p["text"]};
        border: 1px solid {p["border"]};
        selection-background-color: {p["primary_soft"]};
        selection-color: {p["primary_text"]};
    }}
    """


def primary_button_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QPushButton {{
        background: {p["primary"]};
        color: white;
        border: none;
        border-radius: 10px;
        min-height: 38px;
        padding: 0 15px;
        font-size: 10px;
        font-weight: 900;
    }}
    QPushButton:hover {{
        background: {p["primary_hover"]};
    }}
    QPushButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
    }}
    """


def secondary_button_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QPushButton {{
        background: {p["surface_alt"]};
        color: {p["text_soft"]};
        border: 1px solid {p["border"]};
        border-radius: 10px;
        min-height: 38px;
        padding: 0 14px;
        font-size: 10px;
        font-weight: 850;
    }}
    QPushButton:hover {{
        background: {p["primary_soft"]};
        color: {p["primary_text"]};
        border-color: {p["border_strong"]};
    }}
    QPushButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
        border-color: {p["border"]};
    }}
    """


def danger_button_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QPushButton {{
        background: {p["surface_alt"]};
        color: {p["danger"]};
        border: 1px solid {p["border"]};
        border-radius: 10px;
        min-height: 38px;
        padding: 0 14px;
        font-size: 10px;
        font-weight: 850;
    }}
    QPushButton:hover {{
        background: {p["danger_soft"]};
        border-color: {p["danger"]};
    }}
    QPushButton:disabled {{
        background: {p["disabled_bg"]};
        color: {p["disabled_text"]};
    }}
    """


def table_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QTableWidget {{
        background: {p["surface"]};
        color: {p["text"]};
        alternate-background-color: {p["row_alt"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
        selection-background-color: {p["row_selected"]};
        selection-color: {p["text"]};
        font-size: 10px;
        outline: none;
    }}
    QTableWidget::item {{
        background: {p["row"]};
        border-bottom: 1px solid {p["border"]};
        padding: 7px 8px;
    }}
    QTableWidget::item:selected {{
        background: {p["row_selected"]};
        color: {p["text"]};
    }}
    QHeaderView::section {{
        background: {p["table_header"]};
        color: #FFFFFF;
        border: none;
        border-right: 1px solid {p["border_strong"]};
        padding: 9px 8px;
        font-size: 10px;
        font-weight: 900;
    }}
    """


def type_badge_stylesheet(p: dict[str, str], document_type: str) -> str:
    is_invoice = str(document_type or "").lower() == "facture"
    if is_invoice:
        bg = p["success_soft"]
        fg = p["success"]
    else:
        bg = p["primary_soft"]
        fg = p["primary_text"]
    return (
        f"background:{bg};color:{fg};border:1px solid {p['border_strong']};"
        "border-radius:9px;padding:3px 8px;font-size:10px;font-weight:900;"
    )


def status_badge_stylesheet(p: dict[str, str], status: str) -> str:
    value = str(status or "").lower()
    if any(word in value for word in ("disponible", "available", "signé", "signe")):
        bg, fg = p["success_soft"], p["success"]
    elif any(word in value for word in ("préparation", "preparing", "traiter")):
        bg, fg = p["warning_soft"], p["warning"]
    elif any(word in value for word in ("refus", "rejected", "erreur", "failed")):
        bg, fg = p["danger_soft"], p["danger"]
    elif any(word in value for word in ("annul", "cancelled", "archiv", "remplac")):
        bg, fg = p["surface_soft"], p["muted"]
    else:
        bg, fg = p["violet_soft"], p["violet"]
    return (
        f"background:{bg};color:{fg};border:1px solid {p['border_strong']};"
        "border-radius:9px;padding:3px 8px;font-size:10px;font-weight:900;"
    )


def empty_state_stylesheet(p: dict[str, str]) -> str:
    return (
        f"background:{p['surface_soft']};color:{p['muted']};"
        f"border:1px dashed {p['border_strong']};border-radius:14px;"
        "padding:14px 18px;font-size:10px;font-weight:750;"
    )
