from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class NotificationToast(QFrame):
    """Notification non bloquante affichée dans la fenêtre principale."""

    THEMES = {
        "success": {"icon": "✓", "accent": "#16A34A", "background": "#F0FDF4"},
        "info": {"icon": "ℹ", "accent": "#338CE4", "background": "#EFF6FF"},
        "warning": {"icon": "!", "accent": "#D97706", "background": "#FFFBEB"},
        "error": {"icon": "×", "accent": "#DC2626", "background": "#FEF2F2"},
    }

    def __init__(self, title, message="", kind="info", duration_ms=4500, parent=None):
        super().__init__(parent)
        self.kind = kind if kind in self.THEMES else "info"
        self.duration_ms = max(1200, int(duration_ms))
        self._animation = None

        theme = self.THEMES[self.kind]
        self.setObjectName("NotificationToast")
        self.setFixedWidth(370)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"""
            QFrame#NotificationToast {{
                background-color: {theme['background']};
                border: 1px solid #E5E7EB;
                border-left: 5px solid {theme['accent']};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 13, 16, 13)
        layout.setSpacing(12)

        icon = QLabel(theme["icon"])
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(28, 28)
        icon.setStyleSheet(
            f"color: white; background-color: {theme['accent']}; "
            "border-radius: 14px; font-size: 17px; font-weight: 900;"
        )

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title_label = QLabel(str(title))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #111827; font-size: 14px; font-weight: 800;")
        text_layout.addWidget(title_label)

        if message:
            message_label = QLabel(str(message))
            message_label.setWordWrap(True)
            message_label.setStyleSheet("color: #4B5563; font-size: 12px; font-weight: 500;")
            text_layout.addWidget(message_label)

        layout.addWidget(icon, 0, Qt.AlignTop)
        layout.addLayout(text_layout, 1)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

    def show_animated(self):
        self.show()
        self.raise_()
        self._animate_opacity(0.0, 1.0, 180)
        QTimer.singleShot(self.duration_ms, self.dismiss)

    def dismiss(self):
        if self.parent() is None:
            return
        self._animate_opacity(1.0, 0.0, 180, self._remove)

    def _animate_opacity(self, start, end, duration, finished=None):
        animation = QPropertyAnimation(self._opacity, b"opacity", self)
        animation.setDuration(duration)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        if finished:
            animation.finished.connect(finished)
        self._animation = animation
        animation.start()

    def _remove(self):
        parent = self.parentWidget()
        if parent and hasattr(parent, "remove_toast"):
            parent.remove_toast(self)
        self.deleteLater()
