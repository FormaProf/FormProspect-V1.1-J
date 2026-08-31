from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

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
        "trainer_dashboard",
        "trainer_sessions",
        "trainer_planning",
        "treatment",
        "crm",
        "agenda",
        "campaigns",
        "sequences",
        "sales",
        "documents",
        "trainers",
        "trainer_availability",
        "commercial_profiles",
        "training_cases",
        "statistics",
        "ai",
        "activity",
        "admin_users",
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toute la navigation peut défiler lorsque la hauteur disponible
        # devient insuffisante. Le bouton de déconnexion reste fixe.
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("SidebarScroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet(
            """
            QScrollArea#SidebarScroll {
                background: transparent;
                border: none;
            }
            QScrollArea#SidebarScroll > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 1px 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #315B86;
                min-height: 34px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4A79A8;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                border: none;
                background: transparent;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            """
        )

        scroll_content = QWidget()
        scroll_content.setObjectName("SidebarScrollContent")
        scroll_content.setStyleSheet(
            "QWidget#SidebarScrollContent { background: transparent; border: none; }"
        )
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 12, 8)
        scroll_layout.setSpacing(6)

        self._build_brand(scroll_layout)
        self._build_profile(scroll_layout)
        self._build_navigation(scroll_layout)
        scroll_layout.addStretch(1)

        self.sidebar_scroll.setWidget(scroll_content)
        layout.addWidget(self.sidebar_scroll, 1)

        footer = QWidget()
        footer.setObjectName("SidebarFooter")
        footer.setStyleSheet(
            "QWidget#SidebarFooter { background: transparent; border: none; }"
        )
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(20, 8, 20, 18)
        footer_layout.setSpacing(6)

        self.logout_button = QPushButton("↪  Se déconnecter")
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setFixedHeight(42)
        self.logout_button.setStyleSheet(DANGER_BUTTON)
        footer_layout.addWidget(self.logout_button)

        version_label = QLabel("Form@Prospect  •  NM FORMATION")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(
            "color: #6F93B8; font-size: 9px; padding-top: 8px; background: transparent;"
        )
        footer_layout.addWidget(version_label)

        layout.addWidget(footer, 0)

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

        role = SessionState.user().role if SessionState.user() else ""
        subtitle_text = (
            "Espace de suivi pédagogique et de formation"
            if role == "Formateur"
            else "Plateforme intelligente de prospection commerciale"
        )
        subtitle = QLabel(subtitle_text)
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
            ("trainer_dashboard", "🏠", "Tableau de bord"),
            ("trainer_sessions", "🎓", "Mes formations"),
            ("trainer_planning", "📅", "Mon planning"),
            ("treatment", "📥", "Traitement"),
            ("crm", "👥", "CRM"),
            ("agenda", "📅", "Agenda"),
            ("campaigns", "✉", "Campagnes"),
            ("sequences", "🔁", "Séquences"),
            ("sales", "💶", "Ventes & commissions"),
            ("documents", "📄", "Documents"),
            ("trainers", "🧑‍🏫", "Formateurs"),
            ("trainer_availability", "📆", "Disponibilités formateurs"),
            ("commercial_profiles", "💼", "Commerciaux"),
            ("training_cases", "🧾", "Devis & factures"),
            ("statistics", "📊", "Statistiques"),
            ("ai", "✦", "Assistant IA"),
            ("activity", "🕘", "Historique"),
            ("admin_users", "👥", "Compte utilisateurs"),
            ("account", "👤", "Mon compte"),
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
            button.setFixedHeight(39)
            button.setStyleSheet(button_style)
            layout.addWidget(button)
            self.boutons.append(button)
            self.buttons_by_key[key] = button

    def apply_permissions(self):
        user = SessionState.user()
        role = user.role if user else "Commercial"
        trainer_keys = {"trainer_dashboard", "trainer_sessions", "trainer_planning"}
        standard_keys = set(self.MENU_KEYS) - trainer_keys
        allowed = {
            "Administrateur": standard_keys,
            "Manager": standard_keys - {"trainers", "trainer_availability", "commercial_profiles", "statistics"},
            "Commercial": {"dashboard", "crm", "agenda", "campaigns", "sequences", "sales", "documents", "trainer_availability", "training_cases", "ai", "activity", "account"},
            "Formateur": trainer_keys | {"account"},
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
