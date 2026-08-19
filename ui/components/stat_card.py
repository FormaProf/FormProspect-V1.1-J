from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from core.theme import BORDER_COLOR, SOFT_BACKGROUND, TEXT_PRIMARY, TEXT_SECONDARY


class StatCard(QFrame):
    """Carte de compteur mise à jour en temps réel."""

    def __init__(self, title, value="0", icon="", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumHeight(92)
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {SOFT_BACKGROUND};
                border: 1px solid {BORDER_COLOR};
                border-radius: 14px;
            }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(15, 13, 15, 13)
        root.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setFixedWidth(30)
        icon_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        icon_label.setStyleSheet("font-size: 21px; border: none; background: transparent;")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 700; border: none; background: transparent;"
        )
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 900; border: none; background: transparent;"
        )
        text_layout.addWidget(title_label)
        text_layout.addWidget(self.value_label)

        root.addWidget(icon_label)
        root.addLayout(text_layout, 1)

    def set_value(self, value):
        self.value_label.setText(str(value))
