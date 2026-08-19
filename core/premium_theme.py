PRIMARY = "#338CE4"
PRIMARY_DARK = "#256DB4"
PRIMARY_SOFT = "#EAF4FF"
PRIMARY_GLOW = "#D9ECFF"

NAVY = "#071B38"
NAVY_2 = "#0B2A52"

PAGE_BG = "#F8FAFD"
CARD = "#FFFFFF"
CARD_ALT = "#FBFDFF"

TEXT = "#0B1220"
TEXT_SOFT = "#334155"
MUTED = "#6B7A90"
MUTED_LIGHT = "#94A3B8"

BORDER = "#E7ECF3"
BORDER_STRONG = "#D9E2EC"

SUCCESS = "#16A34A"
DANGER = "#DC2626"
WARNING = "#D97706"

INPUT_STYLE = f"""
QLineEdit, QComboBox {{
    background: white;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 11px;
    padding: 0 13px;
    min-height: 40px;
    font-size: 13px;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 2px solid {PRIMARY};
    background: #FFFFFF;
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
"""

PRIMARY_BUTTON = f"""
QPushButton {{
    background: {PRIMARY};
    color: white;
    border: none;
    border-radius: 11px;
    min-height: 40px;
    padding: 0 18px;
    font-weight: 800;
    font-size: 13px;
}}
QPushButton:hover {{ background: {PRIMARY_DARK}; }}
QPushButton:pressed {{ background: #1D4F86; }}
QPushButton:disabled {{ background: #DDE4EC; color: #94A3B8; }}
"""

SECONDARY_BUTTON = f"""
QPushButton {{
    background: white;
    color: #334155;
    border: 1px solid {BORDER};
    border-radius: 11px;
    min-height: 40px;
    padding: 0 16px;
    font-weight: 750;
    font-size: 13px;
}}
QPushButton:hover {{
    border-color: #AFCFF0;
    color: {PRIMARY};
    background: #F8FBFF;
}}
"""

DANGER_BUTTON = f"""
QPushButton {{
    background: transparent;
    color: #FCA5A5;
    border: 1px solid #7F1D1D;
    border-radius: 11px;
    min-height: 40px;
    font-weight: 800;
}}
QPushButton:hover {{ background: #991B1B; color: white; }}
"""

CARD_STYLE = f"""
QFrame#PremiumCard {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}
"""
