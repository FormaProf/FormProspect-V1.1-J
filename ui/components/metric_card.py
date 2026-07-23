from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from core.theme import BORDER_COLOR, CARD_BACKGROUND, TEXT_PRIMARY, TEXT_SECONDARY


class MetricCard(QFrame):
    """Carte compacte pour temps, vitesse, réussite ou état."""

    def __init__(self, title, value="—", icon="", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(86)
        self.setStyleSheet(f"""
            QFrame#metricCard {{
                background-color: {CARD_BACKGROUND};
                border: 1px solid {BORDER_COLOR};
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(3)

        title_label = QLabel(f"{icon}  {title}" if icon else title)
        title_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 700; border: none;"
        )
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 900; border: none;"
        )
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value))
