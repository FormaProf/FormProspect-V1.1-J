PRIMARY = "#338CE4"
PRIMARY_DARK = "#256DB4"
NAVY = "#071B38"
NAVY_2 = "#0B2A52"
PAGE_BG = "#F5F7FB"
CARD = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SUCCESS = "#16A34A"
DANGER = "#DC2626"
WARNING = "#D97706"

INPUT_STYLE = f"""
QLineEdit, QComboBox {{
    background: white; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 9px; padding: 0 12px; min-height: 38px; font-size: 13px;
}}
QLineEdit:focus, QComboBox:focus {{ border: 2px solid {PRIMARY}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
"""

PRIMARY_BUTTON = f"""
QPushButton {{ background: {PRIMARY}; color: white; border: none; border-radius: 9px;
    min-height: 38px; padding: 0 17px; font-weight: 800; font-size: 13px; }}
QPushButton:hover {{ background: {PRIMARY_DARK}; }}
QPushButton:pressed {{ background: #1D4F86; }}
QPushButton:disabled {{ background: #CBD5E1; color: #94A3B8; }}
"""
SECONDARY_BUTTON = f"""
QPushButton {{ background: white; color: #334155; border: 1px solid {BORDER}; border-radius: 9px;
    min-height: 38px; padding: 0 15px; font-weight: 700; font-size: 13px; }}
QPushButton:hover {{ border-color: {PRIMARY}; color: {PRIMARY}; background: #F8FBFF; }}
"""
DANGER_BUTTON = f"""
QPushButton {{ background: transparent; color: #FCA5A5; border: 1px solid #7F1D1D;
    border-radius: 9px; min-height: 40px; font-weight: 800; }}
QPushButton:hover {{ background: #991B1B; color: white; }}
"""
CARD_STYLE = f"QFrame#PremiumCard {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}"
