from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from services.auth_service import AuthService
from ui.pages.commercial_account_page import CommercialAccountPage
from core.theme_settings import get_theme_preference, theme_label


class AccountPage(QWidget):
    """Espace personnel commun à tous les rôles, administrateur compris."""

    profile_updated = Signal()
    appearance_requested = Signal()

    def __init__(self, auth_service: AuthService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = CommercialAccountPage(auth_service)
        self.view.profile_updated.connect(self.profile_updated)
        layout.addWidget(self.view, 1)

        appearance_bar = QFrame()
        appearance_bar.setObjectName("AppearanceBar")
        appearance_bar.setStyleSheet("""
            QFrame#AppearanceBar {
                background:#FFFFFF;
                border:1px solid #DCE5EF;
                border-radius:14px;
            }
        """)
        appearance_layout = QHBoxLayout(appearance_bar)
        appearance_layout.setContentsMargins(18, 12, 18, 12)
        appearance_layout.setSpacing(12)

        appearance_title = QLabel("Apparence")
        appearance_title.setStyleSheet(
            "font-size:12px; font-weight:900; color:#0B1E33; "
            "background:transparent; border:none;"
        )

        self.appearance_value = QLabel("")
        self.appearance_value.setStyleSheet(
            "font-size:11px; color:#6B839C; background:transparent; border:none;"
        )

        appearance_button = QPushButton("Modifier")
        appearance_button.setCursor(Qt.PointingHandCursor)
        appearance_button.setFixedHeight(36)
        appearance_button.setStyleSheet("""
            QPushButton {
                background:#F2F8FF;
                color:#1769A8;
                border:1px solid #BFDDF4;
                border-radius:10px;
                padding:0 14px;
                font-size:11px;
                font-weight:850;
            }
            QPushButton:hover {
                background:#E7F3FF;
                border-color:#338CE4;
                color:#0B5F9B;
            }
        """)
        appearance_button.clicked.connect(self.appearance_requested)

        appearance_layout.addWidget(appearance_title)
        appearance_layout.addWidget(self.appearance_value)
        appearance_layout.addStretch()
        appearance_layout.addWidget(appearance_button)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(appearance_bar)
        self.refresh_appearance_summary()

    def rafraichir(self):
        if hasattr(self.view, "rafraichir"):
            self.view.rafraichir()
        self.refresh_appearance_summary()

    def refresh_appearance_summary(self):
        self.appearance_value.setText(
            theme_label(get_theme_preference())
        )
