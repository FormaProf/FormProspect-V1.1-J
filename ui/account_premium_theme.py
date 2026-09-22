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
    "surface_soft": "#EEF5FC",
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
    "hero_soft": "#C5D8EC",
    "success_soft": "#E9FFF3",
    "success_text": "#087A45",
    "success_border": "#A7F3D0",
    "violet_soft": "#F5F3FF",
    "violet_text": "#7250D6",
    "amber_soft": "#FFF7ED",
    "amber_text": "#B85D10",
    "green_soft": "#ECFDF5",
    "green_text": "#0F8A59",
    "scrollbar": "#CBD5E1",
    "scrollbar_hover": "#94A3B8",
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
    "hero_soft": "#C5D8EC",
    "success_soft": "#E8FBF2",
    "success_text": "#087A45",
    "success_border": "#A7E5C7",
    "violet_soft": "#F3EFFF",
    "violet_text": "#7B5BE5",
    "amber_soft": "#FFF4E6",
    "amber_text": "#C96C00",
    "green_soft": "#EAFBF3",
    "green_text": "#07875A",
    "scrollbar": "#BFD2E3",
    "scrollbar_hover": "#8DAAC2",
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
    "hero_soft": "#C5D8EC",
    "success_soft": "#12382D",
    "success_text": "#69D6AB",
    "success_border": "#245E4C",
    "violet_soft": "#251E47",
    "violet_text": "#B5A4FF",
    "amber_soft": "#3A2917",
    "amber_text": "#F2B75F",
    "green_soft": "#12382D",
    "green_text": "#69D6AB",
    "scrollbar": "#25435F",
    "scrollbar_hover": "#356486",
}


def account_page_palette(mode: str) -> dict[str, str]:
    mode = normalize_theme_mode(mode)
    if mode == THEME_UI_DARK:
        return DARK
    if mode == THEME_UI_LIGHT:
        return LIGHT
    return CLASSIC


def account_shell_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#AccountPageShell {{
        background:{p["bg"]};
        color:{p["text"]};
    }}

    QFrame#AppearanceBar {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:16px;
    }}

    QLabel#AppearanceIcon {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border:1px solid {p["border_strong"]};
        border-radius:10px;
        font-size:15px;
        font-weight:950;
    }}

    QLabel#AppearanceEyebrow {{
        color:{p["primary_text"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:950;
        letter-spacing:1px;
    }}

    QLabel#AppearanceTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:13px;
        font-weight:950;
    }}

    QLabel#AppearanceDescription {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QLabel#AppearanceValue {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border:1px solid {p["border_strong"]};
        border-radius:9px;
        padding:0 11px;
        font-size:9px;
        font-weight:900;
    }}

    QPushButton#AppearanceButton {{
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:10px;
        padding:0 15px;
        font-size:10px;
        font-weight:900;
    }}

    QPushButton#AppearanceButton:hover {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border-color:#338CE4;
    }}
    """


def commercial_account_stylesheet(p: dict[str, str]) -> str:
    return f"""
    QWidget#CommercialAccountPage,
    QWidget#CommercialAccountContent {{
        background:{p["bg"]};
        color:{p["text"]};
    }}

    QScrollArea#AccountScrollArea {{
        border:none;
        background:{p["bg"]};
    }}

    QScrollArea#AccountScrollArea QWidget#qt_scrollarea_viewport {{
        background:{p["bg"]};
    }}

    QScrollArea#AccountScrollArea QScrollBar:vertical {{
        background:transparent;
        width:10px;
        margin:4px 2px;
    }}

    QScrollArea#AccountScrollArea QScrollBar::handle:vertical {{
        background:{p["scrollbar"]};
        min-height:42px;
        border-radius:5px;
    }}

    QScrollArea#AccountScrollArea QScrollBar::handle:vertical:hover {{
        background:{p["scrollbar_hover"]};
    }}

    QScrollArea#AccountScrollArea QScrollBar::add-line:vertical,
    QScrollArea#AccountScrollArea QScrollBar::sub-line:vertical {{
        height:0;
    }}

    QFrame#AccountHero {{
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {p["hero_1"]},
            stop:.54 {p["hero_2"]},
            stop:1 {p["hero_3"]}
        );
        border:1px solid {p["hero_border"]};
        border-radius:22px;
    }}

    QFrame#AccountHeroOrb {{
        background:qradialgradient(
            cx:.35, cy:.28, radius:.82,
            stop:0 #78CAFF,
            stop:.30 #338CE4,
            stop:.74 #145A91,
            stop:1 #0B2A52
        );
        border:1px solid #75C8FF;
        border-radius:34px;
    }}

    QLabel#AccountHeroGlyph {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:27px;
        font-weight:950;
    }}

    QLabel#AccountHeroEyebrow {{
        color:#79C7FF;
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:950;
        letter-spacing:1.2px;
    }}

    QLabel#AccountHeroTitle {{
        color:#FFFFFF;
        background:transparent;
        border:none;
        font-size:28px;
        font-weight:950;
    }}

    QLabel#AccountHeroSubtitle {{
        color:{p["hero_soft"]};
        background:transparent;
        border:none;
        font-size:10px;
    }}

    QLabel#AccountActiveBadge {{
        background:#103B2E;
        color:#76E5B1;
        border:1px solid #2A6B53;
        border-radius:10px;
        padding:0 12px;
        font-size:8px;
        font-weight:950;
        letter-spacing:.5px;
    }}

    QLabel#AccountHeroMeta {{
        background:rgba(255,255,255,.08);
        color:#D7E7F8;
        border:1px solid rgba(255,255,255,.14);
        border-radius:10px;
        padding:7px 11px;
        font-size:8px;
        font-weight:850;
    }}

    QFrame[accountMetricCard="true"] {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:15px;
    }}

    QFrame[accountMetricCard="true"]:hover {{
        background:{p["surface_alt"]};
        border-color:{p["border_strong"]};
    }}

    QLabel[accountMetricIcon="true"] {{
        border:none;
        border-radius:9px;
        font-size:12px;
        font-weight:950;
    }}

    QLabel[accountMetricIcon="true"][accountTone="blue"] {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
    }}

    QLabel[accountMetricIcon="true"][accountTone="violet"] {{
        background:{p["violet_soft"]};
        color:{p["violet_text"]};
    }}

    QLabel[accountMetricIcon="true"][accountTone="green"] {{
        background:{p["green_soft"]};
        color:{p["green_text"]};
    }}

    QLabel[accountMetricName="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:850;
    }}

    QLabel[accountMetricValue="true"] {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:15px;
        font-weight:950;
    }}

    QLabel[accountMetricCaption="true"] {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:8px;
    }}

    QFrame#AccountCard {{
        background:{p["surface"]};
        border:1px solid {p["border"]};
        border-radius:17px;
    }}

    QLabel#SectionEyebrow {{
        color:{p["primary_text"]};
        background:transparent;
        border:none;
        font-size:8px;
        font-weight:950;
        letter-spacing:.9px;
    }}

    QLabel#SectionTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:17px;
        font-weight:950;
    }}

    QLabel#SectionDescription {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QFrame#AvatarPanel {{
        background:{p["surface_alt"]};
        border:1px solid {p["border"]};
        border-radius:15px;
    }}

    QLabel#LargeAvatar {{
        background:transparent;
        border:3px solid {p["border_strong"]};
        border-radius:87px;
    }}

    QLabel#Hint {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QFrame#DetailRow {{
        background:transparent;
        border:none;
        border-bottom:1px solid {p["border"]};
    }}

    QLabel#RowIcon {{
        color:{p["primary_text"]};
        background:{p["primary_soft"]};
        border:1px solid {p["border"]};
        border-radius:8px;
        font-size:12px;
        font-weight:900;
    }}

    QLabel#RowLabel {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:800;
    }}

    QLabel#RowValue {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:11px;
        font-weight:850;
    }}

    QLabel#BadgeValue {{
        color:{p["primary_text"]};
        background:{p["primary_soft"]};
        border:1px solid {p["border_strong"]};
        border-radius:8px;
        padding:4px 9px;
        font-size:9px;
        font-weight:900;
    }}

    QLabel#SuccessValue,
    QLabel#LicenseStatus {{
        color:{p["success_text"]};
        background:transparent;
        border:none;
        font-size:10px;
        font-weight:900;
    }}

    QPushButton#PrimaryButton {{
        min-height:38px;
        padding:0 16px;
        background:qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #338CE4,
            stop:.58 #267FD6,
            stop:1 #5C63F2
        );
        color:#FFFFFF;
        border:1px solid #5FAFF5;
        border-radius:10px;
        font-size:10px;
        font-weight:900;
    }}

    QPushButton#PrimaryButton:hover {{
        border-color:#8BCFFF;
        background:#338CE4;
    }}

    QPushButton#SecondaryButton {{
        min-height:38px;
        padding:0 15px;
        background:{p["surface_alt"]};
        color:{p["text_soft"]};
        border:1px solid {p["border"]};
        border-radius:10px;
        font-size:10px;
        font-weight:900;
    }}

    QPushButton#SecondaryButton:hover {{
        background:{p["primary_soft"]};
        color:{p["primary_text"]};
        border-color:#338CE4;
    }}

    QPushButton#TextButton {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
        font-weight:800;
    }}

    QPushButton#TextButton:hover {{
        color:#E25162;
        text-decoration:underline;
    }}

    QFrame#FeaturePanel {{
        background:{p["surface_alt"]};
        border:1px solid {p["border"]};
        border-radius:13px;
    }}

    QLabel#FeatureIcon {{
        color:{p["primary_text"]};
        background:{p["primary_soft"]};
        border:1px solid {p["border_strong"]};
        border-radius:10px;
        font-size:17px;
        font-weight:950;
    }}

    QLabel#FeatureTitle {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:12px;
        font-weight:950;
    }}

    QLabel#FeatureDescription {{
        color:{p["muted"]};
        background:transparent;
        border:none;
        font-size:9px;
    }}

    QLabel#LicensePlan {{
        color:{p["text"]};
        background:transparent;
        border:none;
        font-size:12px;
        font-weight:950;
    }}
    """
