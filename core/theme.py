"""Charte graphique centralisée de Form@Prospect."""

from core.constants import BACKGROUND_COLOR, FONT, PRIMARY_COLOR

# Couleurs
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6B7280"
TEXT_MUTED = "#9CA3AF"
BORDER_COLOR = "#E5E7EB"
CARD_BACKGROUND = "#FFFFFF"
SOFT_BACKGROUND = "#F9FAFB"
SUCCESS_COLOR = "#16A34A"
SUCCESS_SOFT = "#DCFCE7"
WARNING_COLOR = "#D97706"
WARNING_SOFT = "#FEF3C7"
ERROR_COLOR = "#DC2626"
ERROR_SOFT = "#FEE2E2"
INFO_SOFT = "#DBEAFE"
DARK_PANEL = "#111827"
DARK_PANEL_TEXT = "#D1D5DB"

# Dimensions
CARD_RADIUS = 16
SMALL_RADIUS = 10
CARD_PADDING = 20
SECTION_SPACING = 16


def primary_button_style() -> str:
    return f"""
        QPushButton {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border: none;
            border-radius: {SMALL_RADIUS}px;
            font-family: '{FONT}';
            font-size: 14px;
            font-weight: 700;
            padding: 0 16px;
        }}
        QPushButton:hover {{ background-color: #256DB4; }}
        QPushButton:pressed {{ background-color: #1D4F86; }}
        QPushButton:disabled {{ background-color: #D1D5DB; color: #6B7280; }}
    """


def warning_button_style() -> str:
    return f"""
        QPushButton {{
            background-color: {WARNING_COLOR};
            color: white;
            border: none;
            border-radius: {SMALL_RADIUS}px;
            font-family: '{FONT}';
            font-size: 14px;
            font-weight: 700;
            padding: 0 16px;
        }}
        QPushButton:hover {{ background-color: #B45309; }}
        QPushButton:disabled {{ background-color: #D1D5DB; color: #6B7280; }}
    """


def danger_button_style() -> str:
    return f"""
        QPushButton {{
            background-color: {ERROR_COLOR};
            color: white;
            border: none;
            border-radius: {SMALL_RADIUS}px;
            font-family: '{FONT}';
            font-size: 14px;
            font-weight: 700;
            padding: 0 16px;
        }}
        QPushButton:hover {{ background-color: #B91C1C; }}
        QPushButton:disabled {{ background-color: #D1D5DB; color: #6B7280; }}
    """


def progress_bar_style() -> str:
    return f"""
        QProgressBar {{
            background-color: #EEF2F7;
            border: 1px solid {BORDER_COLOR};
            border-radius: 11px;
            color: {TEXT_PRIMARY};
            font-family: '{FONT}';
            font-size: 13px;
            font-weight: 800;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY_COLOR};
            border-radius: 10px;
        }}
    """
