from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import BORDER, MUTED, PAGE_BG, PRIMARY, PRIMARY_DARK, TEXT
from core.session import SessionState
from services.auth_service import AuthService
from ui.components.notifications import NotificationManager
from ui.dialogs.user_dialog import UserDialog
from ui.dialogs.cloud_user_dialog import CloudUserDialog


class AdminAccountPage(QWidget):
    """Cockpit administrateur : comptes, rôles, licence et présence Cloud."""

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.setObjectName("AccountPage")
        self.setStyleSheet(self._page_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 24)
        root.setSpacing(14)

        root.addWidget(self._build_hero())
        root.addLayout(self._build_kpis())
        root.addWidget(self._build_workspace(), 1)

        self._presence_refresh_timer = QTimer(self)
        self._presence_refresh_timer.setInterval(30_000)
        self._presence_refresh_timer.timeout.connect(self._refresh_if_visible)
        self._presence_refresh_timer.start()

        self.rafraichir()

    # ------------------------------------------------------------------
    # HERO
    # ------------------------------------------------------------------

    def _build_hero(self):
        hero = QFrame()
        hero.setObjectName("AdminHero")

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 20, 22, 20)
        layout.setSpacing(18)

        icon = QLabel("◆")
        icon.setObjectName("HeroIcon")
        icon.setFixedSize(72, 72)
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(4)

        eyebrow = QLabel("FORM@PROSPECT  ·  ADMINISTRATION")
        eyebrow.setObjectName("HeroEyebrow")

        title = QLabel("Centre de commandement")
        title.setObjectName("HeroTitle")

        subtitle = QLabel(
            "Supervisez les comptes, les rôles, les accès et la présence de votre équipe depuis un espace unique."
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)

        text.addWidget(eyebrow)
        text.addWidget(title)
        text.addWidget(subtitle)
        layout.addLayout(text, 1)

        side = QVBoxLayout()
        side.setSpacing(8)

        self.cloud_state = QLabel("●  CLOUD CONNECTÉ")
        self.cloud_state.setObjectName("HeroCloud")
        self.cloud_state.setAlignment(Qt.AlignCenter)

        self.hero_presence = QLabel("0 connecté")
        self.hero_presence.setObjectName("HeroPresence")
        self.hero_presence.setAlignment(Qt.AlignCenter)

        side.addWidget(self.cloud_state)
        side.addWidget(self.hero_presence)
        side.addStretch(1)

        layout.addLayout(side)

        return hero

    # ------------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------------

    def _build_kpis(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        row.addWidget(self._identity_card(), 2)
        row.addWidget(self._kpi_card("Comptes actifs", "0", "users", "◉"), 1)
        row.addWidget(self._kpi_card("Connectés", "0", "online", "●"), 1)
        row.addWidget(self._kpi_card("Administrateurs", "0", "admins", "◆"), 1)
        row.addWidget(self._kpi_card("Managers", "0", "managers", "◇"), 1)
        row.addWidget(self._kpi_card("Commerciaux", "0", "commercials", "▲"), 1)

        return row

    def _identity_card(self):
        user = SessionState.user()

        card = QFrame()
        card.setObjectName("IdentityCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(13)

        self.identity_avatar = QLabel(
            self._initials(user.display_name if user else "Utilisateur")
        )
        self.identity_avatar.setObjectName("IdentityAvatar")
        self.identity_avatar.setFixedSize(48, 48)
        self.identity_avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.identity_avatar)

        text = QVBoxLayout()
        text.setSpacing(1)

        self.identity_name = QLabel(user.display_name if user else "—")
        self.identity_name.setObjectName("IdentityName")

        self.identity_role = QLabel(user.role if user else "—")
        self.identity_role.setObjectName("IdentityRole")

        state = QLabel("●  Session administrateur active")
        state.setObjectName("IdentityState")

        text.addWidget(self.identity_name)
        text.addWidget(self.identity_role)
        text.addWidget(state)
        layout.addLayout(text, 1)

        button = QPushButton("Mon mot de passe")
        button.setObjectName("GhostButton")
        button.clicked.connect(self._change_own_password)
        layout.addWidget(button)

        return card

    def _kpi_card(self, title, value, key, icon_text):
        card = QFrame()
        card.setObjectName("KpiCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(6)

        icon = QLabel(icon_text)
        icon.setObjectName("KpiIcon")
        title_label = QLabel(title)
        title_label.setObjectName("KpiTitle")

        top.addWidget(icon)
        top.addWidget(title_label)
        top.addStretch(1)

        number = QLabel(value)
        number.setObjectName("KpiValue")

        layout.addLayout(top)
        layout.addWidget(number)

        setattr(self, f"metric_{key}", number)
        return card

    # ------------------------------------------------------------------
    # MAIN WORKSPACE
    # ------------------------------------------------------------------

    def _build_workspace(self):
        card = QFrame()
        card.setObjectName("WorkspaceCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Gestion des membres")
        title.setObjectName("WorkspaceTitle")

        self.team_presence = QLabel("Vue d’ensemble des accès et connexions")
        self.team_presence.setObjectName("WorkspaceSubtitle")

        title_box.addWidget(title)
        title_box.addWidget(self.team_presence)
        top.addLayout(title_box, 1)

        self.search = QLineEdit()
        self.search.setObjectName("SearchInput")
        self.search.setPlaceholderText("Rechercher un membre...")
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)

        add = QPushButton("＋ Ajouter un utilisateur")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self._add_user)
        top.addWidget(add)

        layout.addLayout(top)

        info_bar = QFrame()
        info_bar.setObjectName("InfoBar")

        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 9, 12, 9)
        info_layout.setSpacing(10)

        self.license_text = QLabel()
        self.license_text.setObjectName("LicenseText")
        info_layout.addWidget(self.license_text)

        info_layout.addStretch(1)

        cloud_info = QLabel("Identités & permissions synchronisées avec le Cloud")
        cloud_info.setObjectName("CloudInfo")
        info_layout.addWidget(cloud_info)

        layout.addWidget(info_bar)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        toggle = QPushButton("Activer / désactiver")
        toggle.setObjectName("SecondaryButton")
        toggle.clicked.connect(self._toggle_user)

        reset = QPushButton("Envoyer un lien de réinitialisation")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(self._reset_password)

        action_row.addWidget(toggle)
        action_row.addWidget(reset)
        action_row.addStretch(1)

        layout.addLayout(action_row)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("UsersTable")
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Nom",
                "E-mail",
                "Rôle",
                "Statut",
                "Présence",
                "Dernière connexion",
            ]
        )

        self.table.setColumnHidden(0, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        layout.addWidget(self.table, 1)

        return card

    # ------------------------------------------------------------------
    # HELPERS / DATA
    # ------------------------------------------------------------------

    @staticmethod
    def _initials(name: str) -> str:
        parts = [part for part in name.split() if part]
        return "".join(part[0] for part in parts[:2]).upper() or "U"

    @staticmethod
    def _format_cloud_datetime(value) -> str:
        if not value:
            return "Jamais"
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone()
            return parsed.strftime("%d/%m/%Y à %H:%M")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _presence_label(value: str) -> str:
        mapping = {
            "online": "●  En ligne",
            "idle": "●  Inactif",
            "offline": "●  Hors ligne",
        }
        return mapping.get(str(value or "").strip().lower(), "●  Hors ligne")

    def _refresh_if_visible(self):
        if self.isVisible() and SessionState.has_role("Administrateur"):
            self.rafraichir()

    def rafraichir(self):
        if not SessionState.has_role("Administrateur"):
            return

        current_user = SessionState.user()
        if current_user is not None:
            self.identity_name.setText(current_user.display_name)
            self.identity_role.setText(current_user.role)
            self.identity_avatar.setText(self._initials(current_user.display_name))

        try:
            users = self.auth_service.list_users()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Utilisateurs Cloud",
                f"Impossible de charger les utilisateurs :\n{exc}",
            )
            return

        active = sum(1 for user in users if user["active"])
        online = sum(
            1
            for user in users
            if user.get("presence_status") == "online" and user.get("active")
        )
        roles = {
            role: sum(1 for user in users if user["role"] == role)
            for role in ("Administrateur", "Manager", "Commercial")
        }

        self.metric_users.setText(str(active))
        self.metric_online.setText(str(online))
        self.metric_admins.setText(str(roles["Administrateur"]))
        self.metric_managers.setText(str(roles["Manager"]))
        self.metric_commercials.setText(str(roles["Commercial"]))

        self.hero_presence.setText(
            f"{online} connecté" + ("s" if online != 1 else "")
        )

        self.team_presence.setText(
            f"{online} membre" + ("s" if online != 1 else "")
            + f" en ligne sur {active} compte"
            + ("s actifs" if active != 1 else " actif")
        )

        licence = self.auth_service.license_info()
        self.license_text.setText(
            f"◆  Licence {licence.get('plan', '—')}   •   "
            f"{licence.get('status', '—')}   •   "
            f"{active}/{licence.get('max_users', '—')} comptes utilisés"
        )

        self.table.setRowCount(len(users))

        for row, user in enumerate(users):
            self.table.setRowHeight(row, 50)

            full_name = f"{user['first_name']} {user['last_name']}".strip()

            if not full_name:
                current = SessionState.user()
                if (
                    current is not None
                    and str(user.get("email") or "").strip().lower()
                    == str(getattr(current, "email", "") or "").strip().lower()
                ):
                    full_name = current.display_name

            full_name = full_name or user["email"]

            values = [
                user["id"],
                full_name,
                user["email"],
                user["role"],
                "Actif" if user["active"] else "Inactif",
                self._presence_label(user.get("presence_status", "offline")),
                self._format_cloud_datetime(user.get("last_login")),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                if column == 1:
                    item.setFont(QFont("", -1, QFont.DemiBold))
                    item.setForeground(QColor(TEXT))

                elif column == 2:
                    item.setForeground(QColor("#64748B"))

                elif column == 3:
                    role_color = (
                        PRIMARY
                        if value == "Administrateur"
                        else "#7C3AED"
                        if value == "Manager"
                        else "#0F766E"
                    )
                    item.setForeground(QColor(role_color))
                    item.setFont(QFont("", -1, QFont.Bold))

                elif column == 4:
                    item.setForeground(
                        QColor("#15803D" if value == "Actif" else "#DC2626")
                    )
                    item.setFont(QFont("", -1, QFont.Bold))

                elif column == 5:
                    if "En ligne" in str(value):
                        color = "#15803D"
                    elif "Inactif" in str(value):
                        color = "#D97706"
                    else:
                        color = "#64748B"
                    item.setForeground(QColor(color))
                    item.setFont(QFont("", -1, QFont.Bold))

                elif column == 6:
                    item.setForeground(QColor("#475569"))

                self.table.setItem(row, column, item)

        self._filter(self.search.text())

    def _filter(self, text):
        query = text.strip().lower()

        for row in range(self.table.rowCount()):
            searchable = " ".join(
                self.table.item(row, column).text()
                if self.table.item(row, column)
                else ""
                for column in range(1, self.table.columnCount())
            ).lower()

            self.table.setRowHidden(row, query not in searchable)

    def _selected_user(self):
        row = self.table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "Utilisateur",
                "Sélectionnez un utilisateur.",
            )
            return None

        return (
            self.table.item(row, 0).text(),
            self.table.item(row, 4).text() == "Actif",
        )

    def _add_user(self):
        dialog = (
            CloudUserDialog(self.auth_service, self)
            if getattr(self.auth_service, "is_cloud", False)
            else UserDialog(self.auth_service, self)
        )

        if dialog.exec():
            self.rafraichir()

            if getattr(self.auth_service, "is_cloud", False):
                NotificationManager.success(
                    "Invitation envoyée",
                    "Le compte Cloud a été créé et l'utilisateur a reçu son invitation.",
                )
            else:
                NotificationManager.success(
                    "Utilisateur créé",
                    "Le nouveau compte est prêt.",
                )

    def _toggle_user(self):
        selected = self._selected_user()

        if not selected:
            return

        try:
            self.auth_service.set_active(selected[0], not selected[1])
            self.rafraichir()
            NotificationManager.success(
                "Compte mis à jour",
                "Le statut de l'utilisateur a été modifié.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))

    def _reset_password(self):
        selected = self._selected_user()

        if not selected:
            return

        if getattr(self.auth_service, "is_cloud", False):
            row = self.table.currentRow()
            email = (
                self.table.item(row, 2).text()
                if row >= 0 and self.table.item(row, 2)
                else "cet utilisateur"
            )

            answer = QMessageBox.question(
                self,
                "Réinitialiser le mot de passe",
                (
                    f"Envoyer un lien sécurisé de réinitialisation à :\n"
                    f"{email} ?\n\n"
                    "L'administrateur ne voit et ne choisit jamais le mot de passe de l'utilisateur."
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if answer != QMessageBox.Yes:
                return

            try:
                self.auth_service.reset_password(selected[0])
                NotificationManager.success(
                    "E-mail envoyé",
                    "Le lien sécurisé de réinitialisation a été envoyé.",
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Réinitialisation impossible",
                    str(exc),
                )
            return

        password, accepted = QInputDialog.getText(
            self,
            "Nouveau mot de passe",
            "Mot de passe (8 caractères minimum) :",
            echo=QLineEdit.Password,
        )

        if accepted:
            try:
                self.auth_service.reset_password(selected[0], password)
                NotificationManager.success(
                    "Mot de passe réinitialisé",
                    "Le nouveau mot de passe est actif.",
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Réinitialisation impossible",
                    str(exc),
                )

    def _change_own_password(self):
        user = SessionState.user()

        if not user:
            return

        current, accepted = QInputDialog.getText(
            self,
            "Mot de passe actuel",
            "Mot de passe actuel :",
            echo=QLineEdit.Password,
        )

        if not accepted:
            return

        new_password, accepted = QInputDialog.getText(
            self,
            "Nouveau mot de passe",
            "Nouveau mot de passe :",
            echo=QLineEdit.Password,
        )

        if accepted:
            try:
                self.auth_service.change_password(
                    user.id,
                    current,
                    new_password,
                )
                NotificationManager.success(
                    "Mot de passe modifié",
                    "Votre mot de passe a été mis à jour.",
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Modification impossible",
                    str(exc),
                )

    @staticmethod
    def _page_style() -> str:
        return f"""
            QWidget#AccountPage {{
                background: {PAGE_BG};
            }}

            QWidget#AccountPage QLabel {{
                background: transparent;
                border: none;
            }}

            QFrame#AdminHero {{
                background: #0B2A4F;
                border: 1px solid #163D69;
                border-radius: 20px;
            }}

            QLabel#HeroIcon {{
                color: white;
                background: #1273C8;
                border: 1px solid #59B6FF;
                border-radius: 36px;
                font-size: 29px;
                font-weight: 900;
            }}

            QLabel#HeroEyebrow {{
                color: #5FC0FF;
                font-size: 9px;
                font-weight: 900;
            }}

            QLabel#HeroTitle {{
                color: white;
                font-size: 27px;
                font-weight: 900;
            }}

            QLabel#HeroSubtitle {{
                color: #D5E7F8;
                font-size: 11px;
            }}

            QLabel#HeroCloud {{
                color: #067647;
                background: #D1FAE5;
                border: 1px solid #A7F3D0;
                border-radius: 10px;
                padding: 8px 15px;
                font-size: 9px;
                font-weight: 900;
            }}

            QLabel#HeroPresence {{
                color: white;
                background: #183D64;
                border: 1px solid #2B5E8E;
                border-radius: 10px;
                padding: 8px 15px;
                font-size: 10px;
                font-weight: 800;
            }}

            QFrame#IdentityCard,
            QFrame#KpiCard {{
                background: white;
                border: 1px solid #DDE6F0;
                border-radius: 16px;
            }}

            QLabel#IdentityAvatar {{
                color: {PRIMARY};
                background: #E8F3FF;
                border: 1px solid #CFE7FF;
                border-radius: 24px;
                font-size: 14px;
                font-weight: 900;
            }}

            QLabel#IdentityName {{
                color: {TEXT};
                font-size: 14px;
                font-weight: 900;
            }}

            QLabel#IdentityRole {{
                color: {MUTED};
                font-size: 10px;
                font-weight: 600;
            }}

            QLabel#IdentityState {{
                color: #15803D;
                font-size: 9px;
                font-weight: 800;
            }}

            QLabel#KpiIcon {{
                color: {PRIMARY};
                font-size: 11px;
                font-weight: 900;
            }}

            QLabel#KpiTitle {{
                color: #64748B;
                font-size: 9px;
                font-weight: 800;
            }}

            QLabel#KpiValue {{
                color: {TEXT};
                font-size: 24px;
                font-weight: 900;
            }}

            QFrame#WorkspaceCard {{
                background: white;
                border: 1px solid #DDE6F0;
                border-radius: 18px;
            }}

            QLabel#WorkspaceTitle {{
                color: {TEXT};
                font-size: 18px;
                font-weight: 900;
            }}

            QLabel#WorkspaceSubtitle {{
                color: #64748B;
                font-size: 10px;
                font-weight: 600;
            }}

            QFrame#InfoBar {{
                background: #F7FAFE;
                border: 1px solid #DCE8F4;
                border-radius: 11px;
            }}

            QLabel#LicenseText {{
                color: #334155;
                font-size: 10px;
                font-weight: 800;
            }}

            QLabel#CloudInfo {{
                color: #0369A1;
                font-size: 9px;
                font-weight: 800;
            }}

            QLineEdit#SearchInput {{
                min-height: 38px;
                padding: 0 12px;
                background: #F8FAFC;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                font-size: 11px;
            }}

            QLineEdit#SearchInput:focus {{
                background: white;
                border: 2px solid {PRIMARY};
            }}

            QPushButton#PrimaryButton {{
                min-height: 38px;
                padding: 0 16px;
                background: {PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 800;
            }}

            QPushButton#PrimaryButton:hover {{
                background: {PRIMARY_DARK};
            }}

            QPushButton#SecondaryButton,
            QPushButton#GhostButton {{
                min-height: 34px;
                padding: 0 13px;
                background: white;
                color: #475569;
                border: 1px solid {BORDER};
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
            }}

            QPushButton#SecondaryButton:hover,
            QPushButton#GhostButton:hover {{
                color: {PRIMARY};
                border-color: {PRIMARY};
                background: #F8FBFF;
            }}

            QTableWidget#UsersTable {{
                background: white;
                selection-background-color: #EEF6FF;
                selection-color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 12px;
                outline: none;
            }}

            QTableWidget#UsersTable QHeaderView::section {{
                background: #F8FAFC;
                color: #64748B;
                border: none;
                border-bottom: 1px solid {BORDER};
                padding: 10px;
                font-size: 9px;
                font-weight: 900;
            }}

            QTableWidget#UsersTable::item {{
                background: white;
                padding: 9px;
                border: none;
                border-bottom: 1px solid #EEF2F7;
            }}

            QTableWidget#UsersTable::item:selected {{
                background: #EEF6FF;
                color: {TEXT};
            }}
        """
