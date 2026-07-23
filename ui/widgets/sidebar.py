from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.paths import resource_path
from core.premium_theme import DANGER_BUTTON, NAVY, PRIMARY
from core.session import SessionState
from ui.utils_profile import circular_avatar


class Sidebar(QFrame):
    """Barre latérale premium de Form@Prospect.

    L'API publique reste compatible avec MainWindow : ``boutons``,
    ``buttons_by_key`` et ``logout_button`` sont conservés.
    """

    MENU_KEYS = [
        "dashboard",
        "treatment",
        "crm",
        "agenda",
        "campaigns",
        "sequences",
        "sales",
        "documents",
        "training_cases",
        "statistics",
        "ai",
        "activity",
        "account",
    ]

    def __init__(self):
        super().__init__()
        self.boutons = []
        self.buttons_by_key = {}

        self.setObjectName("PremiumSidebar")
        self.setFixedWidth(250)
        self.setStyleSheet(
            """
            QFrame#PremiumSidebar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #061A36,
                    stop: 1 #0B2A52
                );
                border: none;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(6)

        self._build_brand(layout)
        self._build_profile(layout)
        self._build_navigation(layout)

        layout.addStretch(1)

        self.logout_button = QPushButton("↪  Se déconnecter")
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setFixedHeight(42)
        self.logout_button.setStyleSheet(DANGER_BUTTON)
        layout.addWidget(self.logout_button)

        version_label = QLabel("Form@Prospect  •  NM FORMATION")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(
            "color: #6F93B8; font-size: 9px; padding-top: 8px; background: transparent;"
        )
        layout.addWidget(version_label)

        self.apply_permissions()

    def _build_brand(self, layout: QVBoxLayout) -> None:
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background: transparent; border: none;")

        logo_path = resource_path("assets/images/logo_formaprospect.png")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    148,
                    148,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            logo.setFixedHeight(148)
        else:
            logo.setText("Form@Prospect")
            logo.setStyleSheet(
                "color: white; font-size: 21px; font-weight: 900; "
                "background: transparent; border: none;"
            )
            logo.setFixedHeight(60)

        layout.addWidget(logo)

        subtitle = QLabel("Plateforme intelligente de prospection commerciale")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "color: #9EC8F3; font-size: 10px; padding: 0 4px 12px 4px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(subtitle)

    def _build_profile(self, layout: QVBoxLayout) -> None:
        user = SessionState.user()
        display_name = user.display_name if user else "Utilisateur"
        role_text = user.role if user else ""
        initials = "U"
        if user and display_name.strip():
            initials = "".join(
                part[0] for part in display_name.split()[:2] if part
            ).upper()

        profile = QFrame()
        profile.setObjectName("SidebarProfile")
        profile.setStyleSheet(
            """
            QFrame#SidebarProfile {
                background: transparent;
                border: none;
                border-bottom: 1px solid #1E4773;
            }
            """
        )
        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(2, 4, 2, 14)
        profile_layout.setSpacing(11)

        self.profile_avatar = QLabel()
        self.profile_avatar.setFixedSize(42, 42)
        self.profile_avatar.setAlignment(Qt.AlignCenter)
        self.profile_avatar.setStyleSheet("background: transparent; border: none;")
        self.profile_avatar.setPixmap(circular_avatar(user.photo_path if user else "", display_name, 42))

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.profile_name = QLabel(display_name)
        self.profile_name.setStyleSheet(
            "color: white; font-size: 12px; font-weight: 800; "
            "background: transparent; border: none;"
        )
        self.profile_role = QLabel(role_text)
        self.profile_role.setStyleSheet(
            "color: #5CA9F3; font-size: 10px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        online = QLabel("●  En ligne")
        online.setStyleSheet(
            "color: #4ADE80; font-size: 9px; "
            "background: transparent; border: none;"
        )

        text_layout.addWidget(self.profile_name)
        text_layout.addWidget(self.profile_role)
        text_layout.addWidget(online)

        profile_layout.addWidget(self.profile_avatar)
        profile_layout.addLayout(text_layout, 1)
        layout.addWidget(profile)

    def _build_navigation(self, layout: QVBoxLayout) -> None:
        section = QLabel("NAVIGATION")
        section.setStyleSheet(
            "color: #6F93B8; font-size: 9px; font-weight: 900; "
            "padding: 13px 4px 6px 4px; letter-spacing: 1px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(section)

        menus = [
            ("dashboard", "🏠", "Dashboard"),
            ("treatment", "📥", "Traitement"),
            ("crm", "👥", "CRM"),
            ("agenda", "📅", "Agenda"),
            ("campaigns", "✉", "Campagnes"),
            ("sequences", "🔁", "Séquences"),
            ("sales", "💶", "Ventes & commissions"),
            ("documents", "📄", "Documents"),
            ("training_cases", "🎓", "Dossiers formation"),
            ("statistics", "📊", "Statistiques"),
            ("ai", "✦", "Assistant IA"),
            ("activity", "🕘", "Historique"),
            ("account", "👤", "Mon compte" if not SessionState.has_role("Administrateur") else "Compte utilisateurs"),
        ]

        button_style = f"""
            QPushButton {{
                text-align: left;
                padding-left: 14px;
                background: transparent;
                color: #D9E7F5;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: #123E70;
                color: white;
            }}
            QPushButton:checked {{
                background: {PRIMARY};
                color: white;
            }}
            QPushButton:disabled {{
                color: #537497;
            }}
        """

        for key, icon, title in menus:
            button = QPushButton(f"{icon}   {title}")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(43)
            button.setStyleSheet(button_style)
            layout.addWidget(button)
            self.boutons.append(button)
            self.buttons_by_key[key] = button

    def apply_permissions(self):
        user = SessionState.user()
        role = user.role if user else "Commercial"
        allowed = {
            "Administrateur": set(self.MENU_KEYS),
            "Manager": set(self.MENU_KEYS),
            "Commercial": {"dashboard", "crm", "agenda", "campaigns", "sequences", "sales", "documents", "training_cases", "ai", "activity", "account"},
        }.get(role, {"dashboard", "crm", "account"})

        for key, button in self.buttons_by_key.items():
            button.setVisible(key in allowed)

    def refresh_profile(self):
        user = SessionState.user()
        if not user:
            return
        self.profile_avatar.setPixmap(circular_avatar(user.photo_path, user.display_name, 42))
        self.profile_name.setText(user.display_name)
        self.profile_role.setText(user.role)
