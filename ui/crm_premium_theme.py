from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    get_theme_preference,
)

CRM_THEME_CLASSIC = THEME_CLASSIC
CRM_THEME_LIGHT = THEME_UI_LIGHT
CRM_THEME_DARK = THEME_UI_DARK

PALETTES = {
    CRM_THEME_CLASSIC: {
        "bg": "#F8FAFD", "surface": "#FFFFFF", "surface_alt": "#F8FBFE",
        "surface_soft": "#F3F7FB", "border": "#E4EBF4", "border_strong": "#DCE5EF",
        "text": "#0B1220", "text_soft": "#334155", "muted": "#6B7A90",
        "muted_2": "#94A3B8", "primary": "#338CE4", "primary_hover": "#247BD0",
        "cyan": "#338CE4", "row_even": "#FFFFFF", "row_odd": "#FBFDFF",
        "row_selected": "#EAF4FF", "separator": "#EEF2F6",
        "header_start": "#FFFFFF", "header_mid": "#F7FBFF", "header_end": "#EAF4FF",
    },
    CRM_THEME_LIGHT: {
        "bg": "#EDF5FB", "surface": "#FFFFFF", "surface_alt": "#F7FBFF",
        "surface_soft": "#E8F4FF", "border": "#C7DEEF", "border_strong": "#A9CEE7",
        "text": "#0A1D32", "text_soft": "#304A64", "muted": "#6A829B",
        "muted_2": "#8DA3B8", "primary": "#338CE4", "primary_hover": "#257ED0",
        "cyan": "#0E82C6", "row_even": "#FFFFFF", "row_odd": "#F8FCFF",
        "row_selected": "#E4F2FF", "separator": "#E4EEF7",
        "header_start": "#FFFFFF", "header_mid": "#F3F9FF", "header_end": "#E5F3FF",
    },
    CRM_THEME_DARK: {
        "bg": "#06111F", "surface": "#0B1A2B", "surface_alt": "#10243A",
        "surface_soft": "#0A1A2B", "border": "#1A3A59", "border_strong": "#245176",
        "text": "#F4F9FF", "text_soft": "#C4D5E7", "muted": "#7F98B2",
        "muted_2": "#627E9B", "primary": "#338CE4", "primary_hover": "#48A2F2",
        "cyan": "#65D8FF", "row_even": "#0B1A2B", "row_odd": "#0D2034",
        "row_selected": "#12375A", "separator": "#17334F",
        "header_start": "#071321", "header_mid": "#0A2035", "header_end": "#151D43",
    },
}

def normalize_crm_theme(theme=None) -> str:
    value = str(theme or get_theme_preference() or CRM_THEME_CLASSIC).strip()
    return value if value in PALETTES else CRM_THEME_CLASSIC

def crm_palette(theme=None) -> dict[str, str]:
    return PALETTES[normalize_crm_theme(theme)]

def is_classic_theme(theme=None) -> bool:
    return normalize_crm_theme(theme) == CRM_THEME_CLASSIC

def primary_button_qss(theme=None) -> str:
    p = crm_palette(theme)
    if is_classic_theme(theme):
        return f"""
            QPushButton {{
                background:{p['primary']}; color:white; border:none; border-radius:10px;
                font-size:12px; font-weight:850; padding:0 15px;
            }}
            QPushButton:hover {{ background:{p['primary_hover']}; }}
            QPushButton:pressed {{ background:#1D66B2; }}
            QPushButton:disabled {{ background:#E4E9EF; color:#9AA7B8; }}
        """
    return f"""
        QPushButton {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #338CE4, stop:0.58 #257FD4, stop:1 #5C63F2);
            color:#FFFFFF; border:1px solid #5FAFF5; border-radius:11px;
            font-size:12px; font-weight:900; padding:0 16px;
        }}
        QPushButton:hover {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #47A4F5, stop:0.58 #338CE4, stop:1 #7270FF);
            border:1px solid #8BCEFF;
        }}
        QPushButton:pressed {{ background:#1D6FB7; }}
        QPushButton:disabled {{
            background:{p['surface_alt']}; color:{p['muted_2']};
            border:1px solid {p['border']};
        }}
    """

def secondary_button_qss(theme=None) -> str:
    p = crm_palette(theme)
    return f"""
        QPushButton {{
            background:{p['surface']}; color:{p['text_soft']};
            border:1px solid {p['border_strong']}; border-radius:11px;
            font-size:12px; font-weight:850; padding:0 13px;
        }}
        QPushButton:hover {{
            background:{p['surface_soft']}; color:{p['cyan']};
            border:1px solid {p['primary']};
        }}
        QPushButton:pressed {{ background:{p['surface_alt']}; }}
        QPushButton:disabled {{
            background:{p['surface_soft']}; color:{p['muted_2']};
            border:1px solid {p['border']};
        }}
    """

def view_button_qss(theme=None) -> str:
    p = crm_palette(theme)
    return f"""
        QPushButton {{
            background:{p['surface_soft']}; color:{p['muted']};
            border:1px solid {p['border']}; border-radius:11px;
            font-size:12px; font-weight:900; padding:0 18px;
        }}
        QPushButton:hover {{
            background:{p['surface_alt']}; color:{p['cyan']};
            border:1px solid {p['primary']};
        }}
        QPushButton:checked {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0D315D, stop:1 #174E84);
            color:#FFFFFF; border:1px solid #338CE4;
        }}
    """
