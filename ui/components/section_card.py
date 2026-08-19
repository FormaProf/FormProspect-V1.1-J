from PySide6.QtWidgets import QFrame, QVBoxLayout

from core.theme import BORDER_COLOR, CARD_BACKGROUND, CARD_PADDING, CARD_RADIUS


class SectionCard(QFrame):
    """Conteneur visuel homogène pour les sections Form@Prospect."""

    def __init__(self, parent=None, padding=CARD_PADDING, spacing=14):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.setStyleSheet(f"""
            QFrame#sectionCard {{
                background-color: {CARD_BACKGROUND};
                border: 1px solid {BORDER_COLOR};
                border-radius: {CARD_RADIUS}px;
            }}
        """)
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(padding, padding, padding, padding)
        self.content_layout.setSpacing(spacing)
