from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_LIGHT,
    THEME_UI_DARK,
    normalize_theme_mode,
)


CLASSIC = {
    "bg": "#F5F8FC",
    "surface": "#FFFFFF",
    "surface_2": "#F8FBFF",
    "surface_3": "#EAF4FF",
    "border": "#E4EBF4",
    "primary": "#338CE4",
    "cyan": "#338CE4",
    "text": "#0B1220",
    "text_soft": "#334155",
    "muted": "#7A899C",
    "input": "#FFFFFF",
    "input_hover": "#FFFFFF",
    "input_focus": "#FFFFFF",
    "readonly": "#F8FAFC",
    "list_bg": "#FBFDFF",
    "list_item": "#FBFDFF",
    "list_hover": "#F8FBFF",
    "list_selected": "#EAF4FF",
}

LIGHT = {
    "bg": "#F2F7FC",
    "surface": "#FFFFFF",
    "surface_2": "#F8FBFF",
    "surface_3": "#EDF6FF",
    "border": "#D4E4F2",
    "primary": "#338CE4",
    "cyan": "#087AB9",
    "text": "#0B1E33",
    "text_soft": "#344E68",
    "muted": "#6B839C",
    "input": "#FFFFFF",
    "input_hover": "#F8FCFF",
    "input_focus": "#FFFFFF",
    "readonly": "#F4F8FC",
    "list_bg": "#EAF3FB",
    "list_item": "#FFFFFF",
    "list_hover": "#EFF7FF",
    "list_selected": "#E5F2FF",
}

DARK = {
    "bg": "#06111F",
    "surface": "#0B1A2B",
    "surface_2": "#10243A",
    "surface_3": "#132C46",
    "border": "#1A3A59",
    "primary": "#338CE4",
    "cyan": "#65D8FF",
    "text": "#F4F9FF",
    "text_soft": "#C5D5E6",
    "muted": "#7892AE",
    "input": "#091827",
    "input_hover": "#0B1D30",
    "input_focus": "#0C2136",
    "readonly": "#081522",
    "list_bg": "#081522",
    "list_item": "#0B1C2E",
    "list_hover": "#102A45",
    "list_selected": "#12365B",
}


def theme_values(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)
    if mode == THEME_UI_DARK:
        return DARK
    if mode == THEME_UI_LIGHT:
        return LIGHT
    return CLASSIC


def widget_styles(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)
    p = theme_values(mode)
    classic = mode == THEME_CLASSIC
    dark = mode == THEME_UI_DARK

    editable = f"""
        QLineEdit, QTextEdit {{
            background:{p['input']};
            color:{p['text'] if not classic else '#172033'};
            border:1px solid {p['border'] if not classic else '#DCE5EF'};
            border-radius:{10 if classic else 12}px;
            padding:8px 10px;
            font-size:12px;
            selection-background-color:#338CE4;
            selection-color:#FFFFFF;
        }}
        QLineEdit:hover, QTextEdit:hover {{
            border:1px solid {'#DCE5EF' if classic else ('#2C5D87' if dark else '#9CC9EE')};
            background:{p['input_hover']};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border:{2 if classic else 1}px solid {p['cyan']};
            background:{p['input_focus']};
        }}
    """

    readonly = f"""
        QLineEdit {{
            background:{p['readonly']};
            color:{'#475569' if classic else p['text_soft']};
            border:1px solid {'#E2E8F0' if classic else p['border']};
            border-radius:{10 if classic else 12}px;
            padding:8px 10px;
            font-size:12px;
            font-weight:750;
        }}
    """

    combo = f"""
        QComboBox {{
            background:{p['input']};
            color:{'#172033' if classic else p['text']};
            border:1px solid {'#DCE5EF' if classic else p['border']};
            border-radius:{10 if classic else 12}px;
            min-height:38px;
            padding:0 10px;
            font-size:12px;
            font-weight:750;
        }}
        QComboBox:hover {{
            border:1px solid {'#DCE5EF' if classic else ('#2C5D87' if dark else '#9CC9EE')};
            background:{p['input_hover']};
        }}
        QComboBox:focus {{
            border:{2 if classic else 1}px solid {p['cyan']};
        }}
        QComboBox::drop-down {{
            border:none;
            width:28px;
        }}
        QComboBox QAbstractItemView {{
            background:{p['surface']};
            color:{p['text']};
            border:1px solid {p['border']};
            padding:6px;
            outline:0;
            selection-background-color:{p['surface_3']};
            selection-color:{p['text']};
        }}
    """

    list_style = f"""
        QListWidget {{
            background:{p['list_bg']};
            color:{'#334155' if classic else p['text_soft']};
            border:1px solid {'#E2E8F0' if classic else p['border']};
            border-radius:{12 if classic else 14}px;
            padding:7px;
            font-size:11px;
            outline:0;
        }}
        QListWidget::item {{
            background:{p['list_item']};
            padding:{9 if classic else 11}px 10px;
            margin:2px 0;
            border:none;
            border-bottom:1px solid {'#EEF2F6' if classic else p['border']};
        }}
        QListWidget::item:hover {{
            background:{p['list_hover']};
            color:{p['text']};
        }}
        QListWidget::item:selected {{
            background:{p['list_selected']};
            color:{p['text']};
            border-radius:8px;
        }}
    """

    if classic:
        primary = """
            QPushButton {
                background:#338CE4;
                color:#FFFFFF;
                border:none;
                border-radius:10px;
                padding:0 18px;
                font-size:12px;
                font-weight:900;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:pressed { background:#1D66B2; }
        """
        secondary = """
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                padding:0 16px;
                font-size:12px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
        """
    else:
        primary = """
            QPushButton {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #338CE4,
                    stop:0.55 #267FD6,
                    stop:1 #5C63F2
                );
                color:#FFFFFF;
                border:1px solid #5FAFF5;
                border-radius:12px;
                padding:0 20px;
                font-size:12px;
                font-weight:900;
            }
            QPushButton:hover {
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #45A0F2,
                    stop:0.55 #338CE4,
                    stop:1 #716FFF
                );
                border:1px solid #89CBFF;
            }
            QPushButton:pressed {
                background:#1D6FB7;
                border:1px solid #338CE4;
            }
        """
        secondary = f"""
            QPushButton {{
                background:{p['surface']};
                color:{p['text_soft']};
                border:1px solid {p['border']};
                border-radius:12px;
                padding:0 17px;
                font-size:12px;
                font-weight:800;
            }}
            QPushButton:hover {{
                background:{p['surface_3']};
                color:{p['text']};
                border:1px solid #338CE4;
            }}
        """

    date_display = f"""
        QLineEdit {{
            background:{p['input']};
            color:{'#172033' if classic else p['text']};
            border:1px solid {'#DCE5EF' if classic else p['border']};
            border-radius:{10 if classic else 12}px;
            padding:8px 10px;
            font-size:12px;
            font-weight:750;
        }}
    """

    date_button = f"""
        QPushButton {{
            background:{'#F8FBFF' if classic else p['surface_2']};
            color:{'#0B2A52' if classic else p['text_soft']};
            border:1px solid {'#D7E6F4' if classic else p['border']};
            border-radius:{10 if classic else 11}px;
            padding:0 12px;
            font-size:11px;
            font-weight:850;
        }}
        QPushButton:hover {{
            background:{'#EAF4FF' if classic else p['surface_3']};
            color:{'#338CE4' if classic else p['text']};
            border:1px solid {'#AFCFF0' if classic else '#338CE4'};
        }}
    """

    score = """
        QLineEdit {
            background:#F1F8FF;
            color:#075985;
            border:1px solid #CFE7FB;
            border-radius:11px;
            padding:8px 12px;
            font-size:13px;
            font-weight:900;
        }
    """ if classic else f"""
        QLineEdit {{
            background:qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {'#0B2742' if dark else '#EAF6FF'},
                stop:1 {'#12264E' if dark else '#F0EEFF'}
            );
            color:{'#8FE7FF' if dark else '#0A659D'};
            border:1px solid {'#2D6B9F' if dark else '#A7D6F5'};
            border-radius:13px;
            padding:9px 13px;
            font-size:14px;
            font-weight:900;
        }}
    """

    score_details = f"""
        QTextEdit {{
            background:{'#F8FAFC' if classic else p['readonly']};
            color:{'#53657C' if classic else p['muted']};
            border:1px solid {'#E2E8F0' if classic else p['border']};
            border-radius:11px;
            padding:9px 10px;
            font-size:11px;
        }}
    """

    return {
        "editable": editable,
        "readonly": readonly,
        "combo": combo,
        "list": list_style,
        "primary": primary,
        "secondary": secondary,
        "date_display": date_display,
        "date_button": date_button,
        "score": score,
        "score_details": score_details,
    }



def assistant_page_palette(mode: str) -> dict[str, str]:
    """Palette du cockpit Assistant IA, sans modifier sa structure."""
    normalized = normalize_theme_mode(mode)
    base = theme_values(normalized)
    dark = normalized == THEME_UI_DARK
    classic = normalized == THEME_CLASSIC

    return {
        **base,
        "page": base["bg"],
        "surface": base["surface"],
        "surface_alt": base["surface_2"],
        "surface_soft": base["surface_3"],
        "border_strong": "#2C5D87" if dark else ("#C7D9EA" if classic else "#AACCE8"),
        "primary_soft": "#102E4B" if dark else "#EAF4FF",
        "primary_text": "#8FD4FF" if dark else "#1473C9",
        "hero_1": "#06182D" if dark else "#071C35",
        "hero_2": "#0A2749" if dark else "#0B2A52",
        "hero_3": "#123D64" if dark else "#145A91",
        "hero_border": "#24567E" if dark else "#173F6D",
        "hero_text": "#FFFFFF",
        "hero_soft": "#C7D8EA",
        "success_soft": "#102B22" if dark else "#E9FFF3",
        "success_text": "#74E6AF" if dark else "#087A45",
        "success_border": "#215F49" if dark else "#A7F3D0",
        "blue_soft": "#102B46" if dark else "#EEF6FF",
        "blue_text": "#8ED4FF" if dark else "#1473C9",
        "amber_soft": "#2D2115" if dark else "#FFF7ED",
        "amber_text": "#F4BC78" if dark else "#B85D10",
        "red_soft": "#321B24" if dark else "#FFF1F2",
        "red_text": "#FF9AA7" if dark else "#DC3545",
        "violet_soft": "#251D43" if dark else "#F5F3FF",
        "violet_text": "#BDB0FF" if dark else "#7250D6",
        "green_soft": "#102A22" if dark else "#ECFDF5",
        "green_text": "#75DDB3" if dark else "#0F8A59",
        "table_header": "#0A2749" if dark else "#081F3D",
        "table_header_border": "#183D5D" if dark else "#153B67",
        "selection": "#123A60" if dark else "#E9F4FF",
        "selection_text": "#F4F9FF" if dark else "#0B2A52",
        "scroll_handle": "#34516E" if dark else "#CBD5E1",
        "scroll_hover": "#496B8D" if dark else "#94A3B8",
        "shadow": "rgba(3, 15, 28, 0.35)" if dark else "rgba(30, 91, 145, 0.08)",
    }


def assistant_page_stylesheet(p: dict[str, str]) -> str:
    """QSS unique : même structure en Classique, UI Clair et UI Sombre."""
    return f"""
    QWidget#AIAssistantRoot,
    QWidget#AiViewport,
    QWidget#AiMainContent {{
        background:{p["page"]};
        color:{p["text"]};
    }}

    QWidget#AiConsoleBody {{
        background:transparent;
        color:{p["text"]};
    }}

    QScrollArea#AiPageScroll {{
        border:none;
        background:{p["page"]};
    }}

    QScrollArea#AiPageScroll QWidget#qt_scrollarea_viewport {{
        background:{p["page"]};
    }}

    QScrollBar:vertical {{
        background:transparent;
        width:10px;
        margin:4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background:{p["scroll_handle"]};
        min-height:40px;
        border-radius:5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background:{p["scroll_hover"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height:0;
    }}

    QFrame#AiHero {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {p["hero_1"]},
            stop:0.52 {p["hero_2"]},
            stop:1 {p["hero_3"]}
        );
        border:1px solid {p["hero_border"]};
        border-radius:22px;
    }}

    QFrame#AiOrb {{
        background:qradialgradient(
            cx:.35, cy:.28, radius:.82,
            stop:0 #78CAFF,
            stop:.28 #338CE4,
            stop:.72 #145A91,
            stop:1 #0B2A52
        );
        border:1px solid #75C8FF;
        border-radius:38px;
    }}

    QLabel#AiOrbGlyph {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:31px;
        font-weight:950;
    }}

    QLabel#AiHeroEyebrow {{
        color:#79C7FF;
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:1.3px;
    }}

    QLabel#AiHeroTitle {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:29px;
        font-weight:950;
    }}

    QLabel#AiHeroSubtitle {{
        color:{p["hero_soft"]};
        background:transparent;
        border:none;
        font-size:11px;
    }}

    QLabel#AiLiveBadge {{
        background:{p["success_soft"]};
        color:{p["success_text"]};
        border:1px solid {p["success_border"]};
        border-radius:11px;
        padding:0 12px;
        font-size:9px;
        font-weight:900;
    }}

    QLabel#AiPrivacyBadge {{
        color:#D7E7F8;
        background:rgba(255,255,255,0.07);
        border:1px solid rgba(255,255,255,0.14);
        border-radius:11px;
        padding:8px 12px;
        font-size:9px;
        font-weight:750;
    }}

    QLabel#AiEmptyState {{
        background:{p["surface_alt"]};
        color:{p["muted"]};
        border:1px dashed {p["border_strong"]};
        border-radius:16px;
        padding:14px 18px;
        font-size:11px;
        font-weight:750;
    }}

    QFrame[aiMetric="true"],
    QFrame#AiRadarCard,
    QFrame#AiConsole,
    QFrame#AiOutputCard,
    QFrame[aiFeedCard="true"] {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:18px;
    }}

    QLabel[aiMetricName="true"],
    QLabel[aiSectionSubtitle="true"],
    QLabel#AiResultsLabel,
    QLabel[aiToolbarHint="true"],
    QLabel#AiOutputSubtitle {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QLabel[aiMetricValue="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:26px;
        font-weight:950;
    }}

    QLabel[aiMetricCaption="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
    }}

    QLabel[aiMetricIcon="true"] {{
        border:none;
        border-radius:9px;
        font-size:12px;
        font-weight:950;
    }}
    QLabel[aiMetricIcon="true"][aiTone="blue"] {{
        background:{p["blue_soft"]}; color:{p["blue_text"]};
    }}
    QLabel[aiMetricIcon="true"][aiTone="amber"] {{
        background:{p["amber_soft"]}; color:{p["amber_text"]};
    }}
    QLabel[aiMetricIcon="true"][aiTone="red"] {{
        background:{p["red_soft"]}; color:{p["red_text"]};
    }}
    QLabel[aiMetricIcon="true"][aiTone="violet"] {{
        background:{p["violet_soft"]}; color:{p["violet_text"]};
    }}

    QFrame[aiMetricAccent="true"] {{
        border:none;
        border-radius:1px;
    }}
    QFrame[aiMetricAccent="true"][aiTone="blue"] {{ background:{p["blue_text"]}; }}
    QFrame[aiMetricAccent="true"][aiTone="amber"] {{ background:{p["amber_text"]}; }}
    QFrame[aiMetricAccent="true"][aiTone="red"] {{ background:{p["red_text"]}; }}
    QFrame[aiMetricAccent="true"][aiTone="violet"] {{ background:{p["violet_text"]}; }}

    QLabel[aiOverline="true"] {{
        color:{p["primary_text"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:1px;
    }}

    QLabel[aiSectionTitle="true"],
    QLabel[aiFeedTitle="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:16px;
        font-weight:950;
    }}

    QLabel#AiRadarLive {{
        background:{p["success_soft"]};
        color:{p["success_text"]};
        border:1px solid {p["success_border"]};
        border-radius:8px;
        font-size:8px;
        font-weight:900;
    }}

    QFrame#AiSearchShell {{
        background:{p["surface_alt"]};
        border:1px solid {p["border"]};
        border-radius:11px;
    }}

    QLabel#AiSearchIcon {{
        color:{p["primary"]};
        background:transparent;
        border:none;
        font-size:17px;
        font-weight:900;
    }}

    QLineEdit#AiSearchInput {{
        background:transparent;
        color:{p["text"]};
        border:none;
        padding:0 3px;
        font-size:10px;
    }}

    QLabel[aiControlLabel="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:900;
        letter-spacing:.6px;
    }}

    QComboBox#AiLimitCombo {{
        background:{p["surface"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:8px;
        padding:3px 8px;
        font-size:9px;
        font-weight:850;
    }}
    QComboBox#AiLimitCombo:hover {{
        border-color:{p["border_strong"]};
        background:{p["surface_alt"]};
    }}
    QComboBox#AiLimitCombo::drop-down {{
        border:none;
        width:20px;
    }}
    QComboBox#AiLimitCombo QAbstractItemView {{
        background:{p["surface"]};
        color:{p["text"]};
        border:1px solid {p["border"]};
        selection-background-color:{p["selection"]};
        selection-color:{p["selection_text"]};
        outline:0;
    }}

    QTableWidget#AiProspectTable {{
        background:{p["surface"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:12px;
        selection-background-color:{p["selection"]};
        selection-color:{p["selection_text"]};
        outline:none;
        font-size:9px;
    }}
    QTableWidget#AiProspectTable QHeaderView::section {{
        background:{p["table_header"]};
        color:#FFFFFF;
        border:none;
        border-right:1px solid {p["table_header_border"]};
        padding:10px 7px;
        font-size:8px;
        font-weight:900;
    }}
    QTableWidget#AiProspectTable::item {{
        background:{p["surface"]};
        border:none;
        border-bottom:1px solid {p["border"]};
        padding:9px 7px;
    }}
    QTableWidget#AiProspectTable::item:hover {{
        background:{p["surface_alt"]};
    }}
    QTableWidget#AiProspectTable::item:selected {{
        background:{p["selection"]};
        color:{p["selection_text"]};
        border-left:3px solid #338CE4;
    }}

    QFrame#ProspectHero {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["hero_1"]},
            stop:1 {p["hero_3"]}
        );
        border:none;
        border-top-left-radius:17px;
        border-top-right-radius:17px;
    }}

    QLabel#AiProspectEyebrow {{
        color:#79C7FF;
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:900;
        letter-spacing:1px;
    }}
    QLabel#AiSelectedTitle {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:20px;
        font-weight:950;
    }}
    QLabel#AiSelectedMeta {{
        color:#BFD1E4;
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QFrame#CopilotSummary {{
        background:{p["primary_soft"]};
        border:1px solid {p["border_strong"]};
        border-radius:13px;
    }}
    QLabel#AiCopilotCaption {{
        color:{p["primary_text"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:900;
        letter-spacing:.7px;
    }}
    QLabel#AiAnalysisChip {{
        background:{p["surface"]};
        color:{p["primary_text"]};
        border:1px solid {p["border_strong"]};
        border-radius:7px;
        padding:0 8px;
        font-size:7px;
        font-weight:900;
    }}
    QLabel[aiCopilotLine="true"] {{
        color:{p["text_soft"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:750;
    }}

    QPushButton[aiPrimaryButton="true"],
    QPushButton[aiDarkButton="true"] {{
        border-radius:10px;
        padding:0 14px;
        font-size:10px;
        font-weight:900;
    }}
    QPushButton[aiPrimaryButton="true"] {{
        background:#338CE4;
        color:#FFFFFF;
        border:1px solid #5FAFF5;
    }}
    QPushButton[aiPrimaryButton="true"]:hover {{
        background:#287FD4;
        border-color:#86C8FF;
    }}
    QPushButton[aiDarkButton="true"] {{
        background:{p["hero_1"]};
        color:#FFFFFF;
        border:1px solid {p["hero_border"]};
    }}
    QPushButton[aiDarkButton="true"]:hover {{
        background:{p["hero_3"]};
        border-color:#338CE4;
    }}

    QFrame#AiToolsShell {{
        background:{p["surface_alt"]};
        border:1px solid {p["border"]};
        border-radius:13px;
    }}

    QLabel[aiToolbarTitle="true"] {{
        color:{p["text_soft"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:.8px;
    }}

    QFrame[aiFamilyCard="true"] {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:11px;
    }}
    QFrame[aiFamilyCard="true"]:hover {{
        border-color:{p["border_strong"]};
        background:{p["surface_soft"]};
    }}

    QLabel[aiFamilyBadge="true"] {{
        border:none;
        border-radius:7px;
        font-size:11px;
        font-weight:900;
    }}
    QLabel[aiFamilyBadge="true"][aiFamilyTone="blue"] {{
        background:{p["blue_soft"]}; color:{p["blue_text"]};
    }}
    QLabel[aiFamilyBadge="true"][aiFamilyTone="amber"] {{
        background:{p["amber_soft"]}; color:{p["amber_text"]};
    }}
    QLabel[aiFamilyBadge="true"][aiFamilyTone="violet"] {{
        background:{p["violet_soft"]}; color:{p["violet_text"]};
    }}
    QLabel[aiFamilyBadge="true"][aiFamilyTone="green"] {{
        background:{p["green_soft"]}; color:{p["green_text"]};
    }}

    QLabel[aiFamilyLabel="true"] {{
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:.6px;
    }}
    QLabel[aiFamilyLabel="true"][aiFamilyTone="blue"] {{ color:{p["blue_text"]}; }}
    QLabel[aiFamilyLabel="true"][aiFamilyTone="amber"] {{ color:{p["amber_text"]}; }}
    QLabel[aiFamilyLabel="true"][aiFamilyTone="violet"] {{ color:{p["violet_text"]}; }}
    QLabel[aiFamilyLabel="true"][aiFamilyTone="green"] {{ color:{p["green_text"]}; }}

    QPushButton[aiToolButton="true"] {{
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:8px;
        padding:0 10px;
        text-align:left;
        font-size:9px;
        font-weight:800;
    }}
    QPushButton[aiToolButton="true"]:hover {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border-color:{p["border_strong"]};
    }}

    QLabel#AiOutputOrb {{
        background:{p["hero_2"]};
        color:#FFFFFF;
        border:none;
        border-radius:9px;
        font-size:13px;
        font-weight:900;
    }}
    QLabel#AiOutputTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:900;
        letter-spacing:.6px;
    }}

    QPushButton[aiSecondaryButton="true"] {{
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:8px;
        padding:0 11px;
        font-size:9px;
        font-weight:850;
    }}
    QPushButton[aiSecondaryButton="true"]:hover {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border-color:{p["border_strong"]};
    }}

    QTextEdit#AiOutput {{
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:11px;
        padding:13px;
        font-size:11px;
        selection-background-color:#338CE4;
        selection-color:#FFFFFF;
    }}

    QListWidget#AiInsightsList,
    QListWidget#AiHistoryList {{
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:11px;
        padding:5px;
        outline:none;
        font-size:9px;
    }}
    QListWidget#AiInsightsList::item,
    QListWidget#AiHistoryList::item {{
        background:{p["surface"]};
        color:{p["text_soft"]};
        margin:3px 2px;
        padding:9px 9px;
        border:1px solid {p["border"]};
        border-radius:8px;
    }}
    QListWidget#AiInsightsList::item:hover,
    QListWidget#AiHistoryList::item:hover {{
        background:{p["surface_soft"]};
        color:{p["text"]};
        border-color:{p["border_strong"]};
    }}
    QListWidget#AiInsightsList::item:selected,
    QListWidget#AiHistoryList::item:selected {{
        background:{p["selection"]};
        color:{p["selection_text"]};
        border-color:#338CE4;
    }}

    QSplitter#AiCommandSplitter::handle,
    QSplitter#AiFeedSplitter::handle {{
        background:transparent;
    }}
    """


class AIPremiumCard(QFrame):
    """Section card shared by Classic, UI Light and UI Dark."""

    def __init__(self, parent=None, *, variant: str = "default"):
        super().__init__(parent)
        self.setObjectName("AIPremiumCard")
        self.setProperty("hovered", False)
        self.setProperty("variant", variant)
        self._theme_mode = THEME_UI_DARK

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(24.0)
        self._shadow.setOffset(0.0, 7.0)
        self.setGraphicsEffect(self._shadow)

        self._blur_animation = QPropertyAnimation(
            self._shadow, b"blurRadius", self
        )
        self._blur_animation.setDuration(170)
        self._blur_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._offset_animation = QPropertyAnimation(
            self._shadow, b"yOffset", self
        )
        self._offset_animation.setDuration(170)
        self._offset_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.set_theme_mode(THEME_UI_DARK)

    def set_theme_mode(self, mode: str) -> None:
        self._theme_mode = normalize_theme_mode(mode)

        if self._theme_mode == THEME_CLASSIC:
            self.setStyleSheet("""
                QFrame#AIPremiumCard {
                    background:#FFFFFF;
                    border:1px solid #E4EBF4;
                    border-radius:18px;
                }
                QFrame#AIPremiumCard[hovered="true"] {
                    background:#FFFFFF;
                    border:1px solid #E4EBF4;
                    border-radius:18px;
                }
            """)
            self._shadow.setBlurRadius(0.0)
            self._shadow.setOffset(0.0, 0.0)
            self._shadow.setColor(QColor(0, 0, 0, 0))
            return

        p = theme_values(self._theme_mode)
        dark = self._theme_mode == THEME_UI_DARK

        if dark:
            starts = ("#0B1A2B", "#0D2035", "#0B1A2B")
            hover = ("#0C1D30", "#113151", "#0C1E31")
        else:
            starts = ("#FFFFFF", "#FBFDFF", "#F6FAFE")
            hover = ("#FFFFFF", "#F1F8FF", "#EAF5FF")

        self.setStyleSheet(f"""
            QFrame#AIPremiumCard {{
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {starts[0]},
                    stop:0.58 {starts[1]},
                    stop:1 {starts[2]}
                );
                border:1px solid {p['border']};
                border-radius:20px;
            }}
            QFrame#AIPremiumCard[hovered="true"] {{
                background:qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {hover[0]},
                    stop:0.62 {hover[1]},
                    stop:1 {hover[2]}
                );
                border:1px solid #338CE4;
            }}
            QFrame#AIPremiumCard[variant="ai"] {{
                border:1px solid {'#2A679D' if dark else '#A7D6F5'};
            }}
        """)
        self._shadow.setBlurRadius(24.0)
        self._shadow.setOffset(0.0, 7.0)
        self._shadow.setColor(
            QColor(0, 0, 0, 115)
            if dark
            else QColor(29, 91, 145, 42)
        )

    def _animate_hover(self, hovered: bool) -> None:
        if self._theme_mode == THEME_CLASSIC:
            return

        self.setProperty("hovered", hovered)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        dark = self._theme_mode == THEME_UI_DARK
        self._blur_animation.stop()
        self._blur_animation.setStartValue(self._shadow.blurRadius())
        self._blur_animation.setEndValue(40.0 if hovered else 24.0)
        self._blur_animation.start()

        self._offset_animation.stop()
        self._offset_animation.setStartValue(self._shadow.yOffset())
        self._offset_animation.setEndValue(10.0 if hovered else 7.0)
        self._offset_animation.start()

        self._shadow.setColor(
            QColor(51, 140, 228, 105 if dark else 65)
            if hovered
            else (QColor(0, 0, 0, 115) if dark else QColor(29, 91, 145, 42))
        )

    def enterEvent(self, event):
        self._animate_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(False)
        super().leaveEvent(event)
