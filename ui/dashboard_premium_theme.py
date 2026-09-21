from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    get_theme_preference,
    normalize_theme_mode,
)


_PALETTES = {
    THEME_CLASSIC: {
        "page_bg": "#F5F7FA",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFC",
        "surface_soft": "#F2F6FA",
        "text": "#0B1220",
        "text_soft": "#334155",
        "muted": "#66768A",
        "muted_light": "#94A3B8",
        "border": "#E2E8F0",
        "border_strong": "#D4DEE9",
        "primary": "#338CE4",
        "primary_hover": "#247BD0",
        "primary_pressed": "#1D66B2",
        "primary_soft": "#EAF4FF",
        "primary_soft_border": "#AFCFF0",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "button_bg": "#FFFFFF",
        "button_hover_bg": "#F8FBFF",
        "button_disabled": "#E8EDF3",
        "quote_1": "#071B38",
        "quote_2": "#0B2A52",
        "quote_3": "#164B7E",
        "quote_border": "#183D66",
        "quote_text": "#FFFFFF",
        "quote_muted": "#BFD7EE",
        "quote_accent": "#8FC7FF",
        "track": "#E8EEF5",
        "shadow": "#071B38",
    },
    THEME_UI_LIGHT: {
        "page_bg": "#F4F8FC",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FCFF",
        "surface_soft": "#EEF7FF",
        "text": "#081525",
        "text_soft": "#2F435B",
        "muted": "#60768E",
        "muted_light": "#8FA5BA",
        "border": "#DDE8F2",
        "border_strong": "#C9DBEA",
        "primary": "#338CE4",
        "primary_hover": "#207ED6",
        "primary_pressed": "#1766AF",
        "primary_soft": "#E7F3FF",
        "primary_soft_border": "#98C9F5",
        "success": "#159447",
        "warning": "#D97706",
        "danger": "#DC2626",
        "button_bg": "#FFFFFF",
        "button_hover_bg": "#F3F9FF",
        "button_disabled": "#E5EBF1",
        "quote_1": "#06192F",
        "quote_2": "#0B315D",
        "quote_3": "#1C5F9D",
        "quote_border": "#245786",
        "quote_text": "#FFFFFF",
        "quote_muted": "#C6DDF2",
        "quote_accent": "#7FC8FF",
        "track": "#E4EDF5",
        "shadow": "#0B2440",
    },
    THEME_UI_DARK: {
        "page_bg": "#07111F",
        "surface": "#0E1C2D",
        "surface_alt": "#11243A",
        "surface_soft": "#12283F",
        "text": "#F3F8FC",
        "text_soft": "#D0DDEA",
        "muted": "#95AAC0",
        "muted_light": "#71879E",
        "border": "#20374F",
        "border_strong": "#2A4968",
        "primary": "#3EA6FF",
        "primary_hover": "#5AB3FF",
        "primary_pressed": "#248AD8",
        "primary_soft": "#123B5C",
        "primary_soft_border": "#2A78B5",
        "success": "#36C46B",
        "warning": "#F4B04A",
        "danger": "#F06C75",
        "button_bg": "#102338",
        "button_hover_bg": "#15304B",
        "button_disabled": "#172738",
        "quote_1": "#06101E",
        "quote_2": "#082542",
        "quote_3": "#0D4878",
        "quote_border": "#1B527E",
        "quote_text": "#F7FBFF",
        "quote_muted": "#A9C9E5",
        "quote_accent": "#65C8FF",
        "track": "#182B3F",
        "shadow": "#000000",
    },
}


def dashboard_palette(mode: str | None = None) -> dict[str, str]:
    normalized = normalize_theme_mode(
        mode if mode is not None else get_theme_preference()
    )
    return dict(_PALETTES[normalized])


def dashboard_stylesheet(mode: str | None = None) -> str:
    p = dashboard_palette(mode)
    return f"""
    QWidget#DashboardContent {{
        background:{p['page_bg']};
    }}

    QScrollArea#DashboardScroll {{
        background:{p['page_bg']};
        border:none;
    }}
    QScrollArea#DashboardScroll > QWidget > QWidget {{
        background:{p['page_bg']};
    }}
    QScrollBar:vertical {{
        background:transparent;
        width:9px;
        margin:4px 2px 4px 1px;
    }}
    QScrollBar::handle:vertical {{
        background:{p['border_strong']};
        border-radius:4px;
        min-height:38px;
    }}
    QScrollBar::handle:vertical:hover {{
        background:{p['primary']};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height:0px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background:transparent;
    }}

    QFrame#DashboardHero {{
        background:{p['surface']};
        border:1px solid {p['border']};
        border-radius:20px;
    }}
    QLabel#DashboardEyebrow,
    QLabel#DashboardSectionEyebrow {{
        color:{p['primary']};
        font-size:9px;
        font-weight:900;
        letter-spacing:1px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardTitle {{
        color:{p['text']};
        font-size:28px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardSubtitle {{
        color:{p['muted']};
        font-size:12px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardStatus {{
        font-size:10px;
        font-weight:800;
        background:transparent;
        border:none;
    }}

    QFrame#DashboardContext {{
        background:{p['surface_alt']};
        border:1px solid {p['border']};
        border-radius:12px;
        min-width:155px;
        max-width:220px;
    }}
    QLabel#DashboardContextLabel {{
        color:{p['muted_light']};
        font-size:8px;
        font-weight:900;
        letter-spacing:1px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardContextValue {{
        color:{p['text']};
        font-size:11px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardContextSource {{
        color:{p['primary']};
        font-size:9px;
        font-weight:800;
        background:transparent;
        border:none;
    }}

    QFrame#WeeklyQuoteCard {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p['quote_1']},
            stop:0.58 {p['quote_2']},
            stop:1 {p['quote_3']}
        );
        border:1px solid {p['quote_border']};
        border-radius:18px;
    }}
    QLabel#DashboardQuoteIcon {{
        color:{p['quote_text']};
        background:rgba(51,140,228,0.22);
        border:1px solid rgba(255,255,255,0.12);
        border-radius:11px;
        font-size:18px;
    }}
    QLabel#DashboardQuoteOverline {{
        color:{p['quote_accent']};
        font-size:8px;
        font-weight:900;
        letter-spacing:1px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardQuoteText {{
        color:{p['quote_text']};
        font-size:15px;
        font-weight:750;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardQuoteAuthor {{
        color:{p['quote_muted']};
        font-size:9px;
        background:transparent;
        border:none;
    }}

    QFrame#DashboardMetric,
    QFrame#DashboardCard {{
        background:{p['surface']};
        border:1px solid {p['border']};
        border-radius:16px;
    }}
    QFrame#DashboardMetric:hover {{
        border-color:{p['primary_soft_border']};
        background:{p['surface_alt']};
    }}
    QLabel#DashboardMetricIcon {{
        color:{p['primary']};
        background:{p['primary_soft']};
        border:1px solid {p['primary_soft_border']};
        border-radius:9px;
        font-size:13px;
    }}
    QLabel#DashboardMetricTitle {{
        color:{p['muted']};
        font-size:10px;
        font-weight:800;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardMetricValue {{
        color:{p['text']};
        font-size:23px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardMetricCaption {{
        color:{p['muted_light']};
        font-size:9px;
        background:transparent;
        border:none;
    }}

    QLabel#DashboardSectionTitle {{
        color:{p['text']};
        font-size:16px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardSectionSubtitle,
    QLabel#DashboardBodyMuted,
    QLabel#DashboardEmptyText {{
        color:{p['muted']};
        font-size:10px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardBodyStrong {{
        color:{p['text']};
        font-size:12px;
        font-weight:850;
        background:transparent;
        border:none;
    }}

    QFrame#DashboardMiniAction,
    QFrame#DashboardActivityRow,
    QFrame#DashboardEmptyState {{
        background:{p['surface_alt']};
        border:1px solid {p['border']};
        border-radius:11px;
    }}
    QLabel#DashboardMiniActionIcon,
    QLabel#DashboardEmptyIcon {{
        color:{p['primary']};
        background:{p['primary_soft']};
        border:1px solid {p['primary_soft_border']};
        border-radius:8px;
        font-size:11px;
    }}
    QLabel#DashboardMiniActionLabel {{
        color:{p['muted']};
        font-size:10px;
        font-weight:750;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardMiniActionValue,
    QLabel#DashboardPipelineValue {{
        color:{p['text']};
        font-size:16px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardPipelineLabel {{
        color:{p['text_soft']};
        font-size:10px;
        font-weight:800;
        background:transparent;
        border:none;
    }}

    QProgressBar#EnrichmentProgress {{
        background:{p['track']};
        border:none;
        border-radius:8px;
        text-align:center;
        color:{p['text']};
        font-weight:800;
        font-size:9px;
    }}
    QProgressBar#EnrichmentProgress::chunk {{
        background:{p['primary']};
        border-radius:8px;
    }}

    QLabel#DashboardEmptyTitle {{
        color:{p['text_soft']};
        font-size:11px;
        font-weight:900;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardEmptyDetail {{
        color:{p['muted']};
        font-size:10px;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardActivityTitle {{
        color:{p['text_soft']};
        font-size:10px;
        font-weight:800;
        background:transparent;
        border:none;
    }}
    QLabel#DashboardActivityTime {{
        color:{p['muted_light']};
        font-size:9px;
        background:transparent;
        border:none;
    }}
    """
