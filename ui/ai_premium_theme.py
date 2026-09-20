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
