from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.theme_settings import (
    get_theme_preference,
    theme_label,
)
from services.auth_service import AuthService
from ui.account_premium_theme import (
    account_page_palette,
    account_shell_stylesheet,
)
from ui.pages.commercial_account_page import CommercialAccountPage


class AccountPage(QWidget):
    """Espace personnel commun à tous les rôles, administrateur compris."""

    profile_updated = Signal()
    appearance_requested = Signal()

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.setObjectName("AccountPageShell")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.view = CommercialAccountPage(auth_service)
        self.view.profile_updated.connect(self.profile_updated)
        layout.addWidget(self.view, 1)

        self.appearance_bar = QFrame()
        self.appearance_bar.setObjectName("AppearanceBar")
        self.appearance_bar.setMinimumHeight(72)

        appearance_layout = QHBoxLayout(self.appearance_bar)
        appearance_layout.setContentsMargins(16, 10, 16, 10)
        appearance_layout.setSpacing(12)

        appearance_icon = QLabel("◈")
        appearance_icon.setObjectName("AppearanceIcon")
        appearance_icon.setAlignment(Qt.AlignCenter)
        appearance_icon.setFixedSize(38, 38)
        appearance_layout.addWidget(appearance_icon)

        appearance_copy = QVBoxLayout()
        appearance_copy.setSpacing(2)

        appearance_eyebrow = QLabel("EXPÉRIENCE VISUELLE")
        appearance_eyebrow.setObjectName("AppearanceEyebrow")

        appearance_title = QLabel("Apparence de Form@Prospect")
        appearance_title.setObjectName("AppearanceTitle")

        appearance_description = QLabel(
            "Classique, UI Clair ou UI Sombre — la structure métier reste identique."
        )
        appearance_description.setObjectName("AppearanceDescription")

        appearance_copy.addWidget(appearance_eyebrow)
        appearance_copy.addWidget(appearance_title)
        appearance_copy.addWidget(appearance_description)
        appearance_layout.addLayout(appearance_copy, 1)

        self.appearance_value = QLabel("")
        self.appearance_value.setObjectName("AppearanceValue")
        self.appearance_value.setAlignment(Qt.AlignCenter)
        self.appearance_value.setFixedHeight(32)
        appearance_layout.addWidget(self.appearance_value)

        appearance_button = QPushButton("Modifier l'apparence")
        appearance_button.setObjectName("AppearanceButton")
        appearance_button.setCursor(Qt.PointingHandCursor)
        appearance_button.setFixedHeight(38)
        appearance_button.clicked.connect(self.appearance_requested)
        appearance_layout.addWidget(appearance_button)

        # Le bandeau Apparence fait partie du même contenu défilant que
        # Sécurité et Licence : il ne reste plus épinglé en bas de page.
        self.view.add_scroll_footer(self.appearance_bar)

        self.refresh_appearance_summary()

    def apply_appearance_theme(self):
        palette = account_page_palette(get_theme_preference())
        self.setStyleSheet(account_shell_stylesheet(palette))
        if hasattr(self.view, "apply_appearance_theme"):
            self.view.apply_appearance_theme()

    def rafraichir(self):
        if hasattr(self.view, "rafraichir"):
            self.view.rafraichir()
        self.refresh_appearance_summary()

    def refresh_appearance_summary(self):
        self.appearance_value.setText(
            theme_label(get_theme_preference())
        )
        self.apply_appearance_theme()
