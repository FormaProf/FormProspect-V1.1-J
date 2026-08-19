from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from core.theme import (
    ERROR_COLOR,
    ERROR_SOFT,
    SUCCESS_COLOR,
    SUCCESS_SOFT,
    TEXT_SECONDARY,
    WARNING_COLOR,
    WARNING_SOFT,
)


class StatusBadge(QLabel):
    """Badge d'état standardisé : attente, recherche, succès ou erreur."""

    STYLES = {
        "idle": ("En attente", "#F3F4F6", TEXT_SECONDARY),
        "running": ("Recherche...", WARNING_SOFT, WARNING_COLOR),
        "success": ("Trouvé", SUCCESS_SOFT, SUCCESS_COLOR),
        "error": ("Introuvable", ERROR_SOFT, ERROR_COLOR),
    }

    def __init__(self, state="idle", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(92)
        self.setFixedHeight(28)
        self.set_state(state)

    def set_state(self, state, text=None):
        default_text, background, foreground = self.STYLES.get(state, self.STYLES["idle"])
        self.setText(text or default_text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {background};
                color: {foreground};
                border: none;
                border-radius: 14px;
                padding: 0 10px;
                font-size: 12px;
                font-weight: 800;
            }}
        """)
