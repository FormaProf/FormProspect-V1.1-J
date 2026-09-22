from __future__ import annotations

from core.theme_settings import (
    THEME_CLASSIC,
    THEME_UI_DARK,
    THEME_UI_LIGHT,
    normalize_theme_mode,
)


CLASSIC = {
    "bg": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FBFF",
    "surface_soft": "#F1F6FC",
    "border": "#DFE8F2",
    "border_strong": "#BCD4EA",
    "text": "#0B1220",
    "text_soft": "#40546B",
    "muted": "#7B8CA0",
    "primary": "#338CE4",
    "primary_text": "#1473C9",
    "primary_soft": "#EAF4FF",
    "hero_1": "#071C35",
    "hero_2": "#0B2A52",
    "hero_3": "#145A91",
    "hero_border": "#173F6D",
    "selection": "#EAF4FF",
    "selection_text": "#0B2A52",
    "scrollbar": "#CBD5E1",
    "scrollbar_hover": "#94A3B8",
    "blue_soft": "#EEF6FF",
    "blue_text": "#338CE4",
    "violet_soft": "#F5F3FF",
    "violet_text": "#8B5CF6",
    "amber_soft": "#FFF7ED",
    "amber_text": "#D97706",
    "green_soft": "#ECFDF5",
    "green_text": "#059669",
    "red_soft": "#FFF1F2",
    "red_text": "#DC2626",
    "success_soft": "#E9FFF3",
    "success_text": "#087A45",
    "success_border": "#A7F3D0",
    "warning_soft": "#FFF7E6",
    "warning_text": "#A85C00",
    "warning_border": "#F2D09B",
    "error_soft": "#FFF1F2",
    "error_text": "#C92A3B",
    "error_border": "#F1B8C0",
    "info_soft": "#EEF6FF",
    "info_text": "#2476C4",
    "info_border": "#CBE1F6",
}

LIGHT = {
    "bg": "#F2F7FC",
    "surface": "#FFFFFF",
    "surface_alt": "#F7FBFF",
    "surface_soft": "#ECF5FD",
    "border": "#D5E4F1",
    "border_strong": "#9FC7E8",
    "text": "#0B1E33",
    "text_soft": "#38516B",
    "muted": "#6F879F",
    "primary": "#338CE4",
    "primary_text": "#146FBF",
    "primary_soft": "#E8F4FF",
    "hero_1": "#071C35",
    "hero_2": "#0B2A52",
    "hero_3": "#145A91",
    "hero_border": "#20507F",
    "selection": "#E5F2FF",
    "selection_text": "#0B2A52",
    "scrollbar": "#BFD2E3",
    "scrollbar_hover": "#8DAAC2",
    "blue_soft": "#EAF5FF",
    "blue_text": "#247FD0",
    "violet_soft": "#F3EFFF",
    "violet_text": "#7B5BE5",
    "amber_soft": "#FFF4E6",
    "amber_text": "#C96C00",
    "green_soft": "#EAFBF3",
    "green_text": "#07875A",
    "red_soft": "#FFF0F3",
    "red_text": "#D4374B",
    "success_soft": "#E8FBF2",
    "success_text": "#087A45",
    "success_border": "#A7E5C7",
    "warning_soft": "#FFF5E6",
    "warning_text": "#A85C00",
    "warning_border": "#F1CC91",
    "error_soft": "#FFF0F3",
    "error_text": "#C92A3B",
    "error_border": "#EFB2BC",
    "info_soft": "#EAF5FF",
    "info_text": "#2476C4",
    "info_border": "#BEDBF2",
}

DARK = {
    "bg": "#06111F",
    "surface": "#0B1A2B",
    "surface_alt": "#0E2135",
    "surface_soft": "#11283F",
    "border": "#1A3957",
    "border_strong": "#2C5F89",
    "text": "#F4F9FF",
    "text_soft": "#C7D6E6",
    "muted": "#7E98B3",
    "primary": "#338CE4",
    "primary_text": "#6BC2FF",
    "primary_soft": "#102F4B",
    "hero_1": "#071827",
    "hero_2": "#0B2947",
    "hero_3": "#123C65",
    "hero_border": "#1E4F78",
    "selection": "#12365B",
    "selection_text": "#FFFFFF",
    "scrollbar": "#25435F",
    "scrollbar_hover": "#356486",
    "blue_soft": "#102C48",
    "blue_text": "#65B9FF",
    "violet_soft": "#251E47",
    "violet_text": "#B5A4FF",
    "amber_soft": "#3A2917",
    "amber_text": "#F2B75F",
    "green_soft": "#12382D",
    "green_text": "#69D6AB",
    "red_soft": "#3B1F28",
    "red_text": "#FF8798",
    "success_soft": "#12382D",
    "success_text": "#69D6AB",
    "success_border": "#245E4C",
    "warning_soft": "#3A2917",
    "warning_text": "#F2B75F",
    "warning_border": "#6A4A21",
    "error_soft": "#3B1F28",
    "error_text": "#FF8798",
    "error_border": "#713543",
    "info_soft": "#102C48",
    "info_text": "#65B9FF",
    "info_border": "#25557C",
}


def activity_page_palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)
    if mode == THEME_UI_DARK:
        return DARK
    if mode == THEME_UI_LIGHT:
        return LIGHT
    return CLASSIC


def activity_page_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#ActivityPageRoot {{
        background:{p["bg"]};
    }}

    QScrollArea#ActivityPageScroll,
    QWidget#ActivityViewport {{
        background:{p["bg"]};
        border:none;
    }}

    QScrollArea#ActivityPageScroll QScrollBar:vertical {{
        background:transparent;
        width:10px;
        margin:4px 2px;
    }}
    QScrollArea#ActivityPageScroll QScrollBar::handle:vertical {{
        background:{p["scrollbar"]};
        min-height:40px;
        border-radius:5px;
    }}
    QScrollArea#ActivityPageScroll QScrollBar::handle:vertical:hover {{
        background:{p["scrollbar_hover"]};
    }}
    QScrollArea#ActivityPageScroll QScrollBar::add-line:vertical,
    QScrollArea#ActivityPageScroll QScrollBar::sub-line:vertical {{
        height:0;
    }}

    QFrame#ActivityHero {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["hero_1"]},
            stop:0.52 {p["hero_2"]},
            stop:1 {p["hero_3"]}
        );
        border:1px solid {p["hero_border"]};
        border-radius:22px;
    }}

    QFrame#ActivityOrb {{
        background:qradialgradient(
            cx:.35, cy:.28, radius:.82,
            stop:0 #6BC2FF,
            stop:.30 #338CE4,
            stop:.76 #145A91,
            stop:1 #0B2A52
        );
        border:1px solid #72C4FF;
        border-radius:34px;
    }}

    QLabel#ActivityOrbGlyph {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:28px;
        font-weight:950;
    }}

    QLabel#ActivityHeroEyebrow {{
        color:#79C7FF;
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:1.2px;
    }}

    QLabel#ActivityHeroTitle {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:28px;
        font-weight:950;
    }}

    QLabel#ActivityHeroSubtitle {{
        color:#C5D8EC;
        background:transparent;
        border:none;
        font-size:10px;
    }}

    QLabel#ActivityWorkspaceBadge {{
        border-radius:9px;
        padding:0 10px;
        font-size:8px;
        font-weight:950;
        letter-spacing:.5px;
    }}
    QLabel#ActivityWorkspaceBadge[activityState="idle"] {{
        background:rgba(255,255,255,.08);
        color:#C9D8EA;
        border:1px solid rgba(255,255,255,.16);
    }}
    QLabel#ActivityWorkspaceBadge[activityState="local"] {{
        background:#E9FFF3;
        color:#087A45;
        border:1px solid #A7F3D0;
    }}
    QLabel#ActivityWorkspaceBadge[activityState="cloud"] {{
        background:#EAF4FF;
        color:#1473C9;
        border:1px solid #B8D9F5;
    }}

    QLabel#ActivitySourceNote {{
        background:rgba(255,255,255,.08);
        color:#D6E4F2;
        border:1px solid rgba(255,255,255,.14);
        border-radius:9px;
        padding:0 10px;
        font-size:8px;
        font-weight:800;
    }}

    QComboBox#ActivityFilterCombo {{
        background:{p["surface"]};
        color:{p["text"]};
        border:1px solid {p["border"]};
        border-radius:9px;
        padding:0 10px;
        font-size:9px;
        font-weight:850;
    }}
    QComboBox#ActivityFilterCombo:hover {{
        border-color:#67B7F4;
    }}
    QComboBox#ActivityFilterCombo:focus {{
        border:1px solid #338CE4;
    }}
    QComboBox#ActivityFilterCombo::drop-down {{
        border:none;
        width:26px;
    }}
    QComboBox#ActivityFilterCombo QAbstractItemView {{
        background:{p["surface"]};
        color:{p["text"]};
        border:1px solid {p["border"]};
        selection-background-color:{p["selection"]};
        selection-color:{p["selection_text"]};
        outline:0;
        padding:4px;
    }}

    QPushButton#ActivityRefreshButton {{
        background:#338CE4;
        color:#FFFFFF;
        border:1px solid #5FAFF5;
        border-radius:9px;
        padding:0 14px;
        font-size:9px;
        font-weight:900;
    }}
    QPushButton#ActivityRefreshButton:hover {{
        background:#287FD4;
        border-color:#86C8FF;
    }}
    QPushButton#ActivityRefreshButton:pressed {{
        background:#1F6DBA;
    }}

    QFrame[activityMetricCard="true"] {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:15px;
    }}
    QFrame[activityMetricCard="true"]:hover {{
        background:{p["surface_alt"]};
        border-color:{p["border_strong"]};
    }}

    QLabel[activityMetricName="true"] {{
        color:{p["text_soft"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:850;
    }}

    QLabel[activityMetricValue="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:23px;
        font-weight:950;
    }}

    QLabel[activityMetricCaption="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
    }}

    QLabel[activityMetricIcon="true"] {{
        border:none;
        border-radius:9px;
        font-size:12px;
        font-weight:950;
    }}
    QLabel[activityMetricIcon="true"][activityTone="blue"] {{
        background:{p["blue_soft"]};
        color:{p["blue_text"]};
    }}
    QLabel[activityMetricIcon="true"][activityTone="violet"] {{
        background:{p["violet_soft"]};
        color:{p["violet_text"]};
    }}
    QLabel[activityMetricIcon="true"][activityTone="amber"] {{
        background:{p["amber_soft"]};
        color:{p["amber_text"]};
    }}
    QLabel[activityMetricIcon="true"][activityTone="green"] {{
        background:{p["green_soft"]};
        color:{p["green_text"]};
    }}

    QFrame[activityMetricAccent="true"] {{
        border:none;
        border-radius:1px;
    }}
    QFrame[activityMetricAccent="true"][activityTone="blue"] {{
        background:{p["blue_text"]};
    }}
    QFrame[activityMetricAccent="true"][activityTone="violet"] {{
        background:{p["violet_text"]};
    }}
    QFrame[activityMetricAccent="true"][activityTone="amber"] {{
        background:{p["amber_text"]};
    }}
    QFrame[activityMetricAccent="true"][activityTone="green"] {{
        background:{p["green_text"]};
    }}

    QFrame#ActivityFeed {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:18px;
    }}

    QLabel[activityOverline="true"] {{
        color:{p["primary_text"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:900;
        letter-spacing:1px;
    }}

    QLabel#ActivityFeedTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:17px;
        font-weight:950;
    }}

    QLabel[activitySectionSubtitle="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QLabel#ActivityCountBadge {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border:1px solid {p["border_strong"]};
        border-radius:9px;
        padding:0 9px;
        font-size:8px;
        font-weight:900;
    }}

    QFrame#ActivityFeedSeparator {{
        background:{p["border"]};
        border:none;
    }}

    QFrame[activityDayHeader="true"] {{
        background:transparent;
        border:none;
    }}

    QLabel[activityDayDot="true"] {{
        color:{p["primary"]};
        background:transparent;
        border:none;
        font-size:18px;
        font-weight:950;
    }}

    QLabel[activityDayTitle="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:11px;
        font-weight:900;
    }}

    QLabel[activityDayCount="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:800;
    }}

    QFrame#ActivityEventCard {{
        background:{p["surface_alt"]};
        border:1px solid {p["border"]};
        border-radius:12px;
    }}
    QFrame#ActivityEventCard:hover {{
        background:{p["surface_soft"]};
        border-color:{p["border_strong"]};
    }}

    QFrame[activityEventRail="true"] {{
        border:none;
        border-radius:1px;
    }}
    QFrame[activityEventRail="true"][activityTone="success"] {{
        background:{p["success_text"]};
    }}
    QFrame[activityEventRail="true"][activityTone="warning"] {{
        background:{p["warning_text"]};
    }}
    QFrame[activityEventRail="true"][activityTone="error"] {{
        background:{p["error_text"]};
    }}
    QFrame[activityEventRail="true"][activityTone="info"] {{
        background:{p["info_text"]};
    }}

    QLabel[activityLevelBadge="true"] {{
        border-radius:10px;
        font-size:13px;
        font-weight:950;
    }}
    QLabel[activityLevelBadge="true"][activityTone="success"] {{
        background:{p["success_soft"]};
        color:{p["success_text"]};
        border:1px solid {p["success_border"]};
    }}
    QLabel[activityLevelBadge="true"][activityTone="warning"] {{
        background:{p["warning_soft"]};
        color:{p["warning_text"]};
        border:1px solid {p["warning_border"]};
    }}
    QLabel[activityLevelBadge="true"][activityTone="error"] {{
        background:{p["error_soft"]};
        color:{p["error_text"]};
        border:1px solid {p["error_border"]};
    }}
    QLabel[activityLevelBadge="true"][activityTone="info"] {{
        background:{p["info_soft"]};
        color:{p["info_text"]};
        border:1px solid {p["info_border"]};
    }}

    QLabel[activityEventTitle="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:900;
    }}

    QLabel[activityEventMessage="true"] {{
        color:{p["text_soft"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QLabel[activityCategoryBadge="true"] {{
        background:{p["surface"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:8px;
        padding:0 8px;
        font-size:8px;
        font-weight:850;
    }}

    QLabel[activityTimeLabel="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:800;
    }}

    QFrame#ActivityEmptyCard {{
        background:{p["surface_alt"]};
        border:1px dashed {p["border_strong"]};
        border-radius:14px;
    }}

    QLabel#ActivityEmptyBadge {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border:1px solid {p["border_strong"]};
        border-radius:14px;
        font-size:19px;
        font-weight:950;
    }}

    QLabel#ActivityEmptyTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:14px;
        font-weight:950;
    }}

    QLabel#ActivityEmptyText {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}
    """
