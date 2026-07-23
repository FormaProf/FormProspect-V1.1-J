from PySide6.QtCore import Qt
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


class AdminAccountPage(QWidget):
    """Page compte/utilisateurs nettoyée : peu de cadres, hiérarchie claire."""

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.setObjectName("AccountPage")
        self.setStyleSheet(self._page_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 26)
        root.setSpacing(18)

        root.addLayout(self._build_header())
        root.addLayout(self._build_summary())
        root.addWidget(self._build_license())

        if getattr(self.auth_service, "is_cloud", False):
            cloud_notice = QLabel(
                "☁  Identité Cloud active — les comptes et permissions sont contrôlés par le serveur."
            )
            cloud_notice.setObjectName("CloudNotice")
            root.addWidget(cloud_notice)

        self.admin_frame = self._build_users_section()
        root.addWidget(self.admin_frame, 1)
        self.admin_frame.setVisible(SessionState.has_role("Administrateur"))

        self.rafraichir()

    def _build_header(self):
        header = QVBoxLayout()
        header.setSpacing(3)
        title = QLabel("Compte, utilisateurs et licence")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Gérez vos utilisateurs, leurs rôles et votre licence Form@Prospect."
        )
        subtitle.setObjectName("PageSubtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        return header

    def _build_summary(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        user = SessionState.user()
        row.addWidget(self._identity_card(user), 2)
        row.addWidget(self._metric_card("Utilisateurs actifs", "0", "users"), 1)
        row.addWidget(self._metric_card("Administrateurs", "0", "admins"), 1)
        row.addWidget(self._metric_card("Managers", "0", "managers"), 1)
        row.addWidget(self._metric_card("Commerciaux", "0", "commercials"), 1)
        return row

    def _identity_card(self, user):
        card = QFrame()
        card.setObjectName("SummaryCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(12)

        avatar = QLabel(self._initials(user.display_name if user else "Utilisateur"))
        avatar.setObjectName("IdentityAvatar")
        avatar.setFixedSize(46, 46)
        avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)

        text = QVBoxLayout()
        text.setSpacing(1)
        name = QLabel(user.display_name if user else "—")
        name.setObjectName("IdentityName")
        role = QLabel(user.role if user else "—")
        role.setObjectName("IdentityRole")
        state = QLabel("●  Compte connecté")
        state.setObjectName("IdentityState")
        text.addWidget(name)
        text.addWidget(role)
        text.addWidget(state)
        layout.addLayout(text, 1)

        button = QPushButton("Changer mon mot de passe")
        button.setObjectName("SecondaryButton")
        button.clicked.connect(self._change_own_password)
        layout.addWidget(button)
        return card

    def _metric_card(self, title, value, key):
        card = QFrame()
        card.setObjectName("SummaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)

        label = QLabel(title)
        label.setObjectName("MetricTitle")
        number = QLabel(value)
        number.setObjectName("MetricValue")
        layout.addWidget(label)
        layout.addWidget(number)
        layout.addStretch(1)
        setattr(self, f"metric_{key}", number)
        return card

    def _build_license(self):
        licence = self.auth_service.license_info()
        card = QFrame()
        card.setObjectName("LicenseCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        icon = QLabel("◆")
        icon.setObjectName("LicenseIcon")
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(1)
        plan = QLabel(f"Licence {licence.get('plan', '—')}")
        plan.setObjectName("LicensePlan")
        detail = QLabel(
            f"Statut : {licence.get('status', '—')}   •   "
            f"Utilisateurs autorisés : {licence.get('max_users', '—')}"
        )
        detail.setObjectName("LicenseDetail")
        text.addWidget(plan)
        text.addWidget(detail)
        layout.addLayout(text)
        layout.addStretch(1)
        return card

    def _build_users_section(self):
        section = QFrame()
        section.setObjectName("UsersSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(13)

        top = QHBoxLayout()
        title = QLabel("Gestion des utilisateurs")
        title.setObjectName("SectionTitle")
        top.addWidget(title)
        top.addStretch(1)

        self.search = QLineEdit()
        self.search.setObjectName("SearchInput")
        self.search.setPlaceholderText("Rechercher un utilisateur...")
        self.search.setFixedWidth(250)
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search)
        layout.addLayout(top)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        add = QPushButton("＋ Ajouter")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self._add_user)
        toggle = QPushButton("Activer / désactiver")
        toggle.setObjectName("SecondaryButton")
        toggle.clicked.connect(self._toggle_user)
        reset = QPushButton("Réinitialiser le mot de passe")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(self._reset_password)
        role = QPushButton("Modifier le rôle")
        role.setObjectName("SecondaryButton")
        role.clicked.connect(self._change_role)
        actions.addWidget(add)
        actions.addWidget(toggle)
        actions.addWidget(role)
        actions.addWidget(reset)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("UsersTable")
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Identifiant",
                "Nom",
                "E-mail",
                "Rôle",
                "Statut",
                "Dernière connexion",
            ]
        )
        self.table.setColumnHidden(0, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnWidth(1, 130)
        layout.addWidget(self.table, 1)

        if getattr(self.auth_service, "is_cloud", False):
            audit_title = QLabel("Journal d'activité Cloud")
            audit_title.setObjectName("SectionTitle")
            layout.addWidget(audit_title)
            self.audit_table = QTableWidget(0, 4)
            self.audit_table.setHorizontalHeaderLabels(["Date", "Utilisateur", "Action", "Appareil / IP"])
            self.audit_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.audit_table.setSelectionMode(QAbstractItemView.NoSelection)
            self.audit_table.verticalHeader().setVisible(False)
            self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.audit_table.setMaximumHeight(190)
            layout.addWidget(self.audit_table)
        return section

    @staticmethod
    def _initials(name: str) -> str:
        parts = [part for part in name.split() if part]
        return "".join(part[0] for part in parts[:2]).upper() or "U"

    def rafraichir(self):
        if not SessionState.has_role("Administrateur"):
            return

        users = self.auth_service.list_users()
        active = sum(1 for user in users if user["active"])
        roles = {
            role: sum(1 for user in users if user["role"] == role)
            for role in ("Administrateur", "Manager", "Commercial")
        }

        self.metric_users.setText(str(active))
        self.metric_admins.setText(str(roles["Administrateur"]))
        self.metric_managers.setText(str(roles["Manager"]))
        self.metric_commercials.setText(str(roles["Commercial"]))

        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = [
                user["id"],
                user["username"],
                f"{user['first_name']} {user['last_name']}".strip(),
                user["email"],
                user["role"],
                "Actif" if user["active"] else "Inactif",
                user["last_login"] or "Jamais",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if column == 4:
                    color = (
                        PRIMARY
                        if value == "Administrateur"
                        else "#7C3AED"
                        if value == "Manager"
                        else "#15803D"
                    )
                    item.setForeground(QColor(color))
                    item.setFont(QFont("", -1, QFont.Bold))
                elif column == 5:
                    item.setForeground(
                        QColor("#15803D" if value == "Actif" else "#DC2626")
                    )
                    item.setFont(QFont("", -1, QFont.Bold))
                self.table.setItem(row, column, item)

        self._filter(self.search.text())
        if getattr(self.auth_service, "is_cloud", False):
            self._refresh_audit()

    def _refresh_audit(self):
        try:
            entries = self.auth_service.list_audit(50)
        except Exception:
            entries = []
        self.audit_table.setRowCount(len(entries))
        labels = {
            "user.invited": "Utilisateur invité",
            "user.updated": "Compte ou rôle modifié",
            "user.password_reset_requested": "Réinitialisation demandée",
            "organization.viewed": "Organisation consultée",
        }
        for row, entry in enumerate(entries):
            values = [
                str(entry.get("occurred_at", "")).replace("T", " ")[:19],
                entry.get("actor_email", "—") or "—",
                labels.get(entry.get("action"), entry.get("action", "")),
                " / ".join(value for value in (entry.get("device_id", ""), entry.get("ip_address", "")) if value) or "—",
            ]
            for column, value in enumerate(values):
                self.audit_table.setItem(row, column, QTableWidgetItem(str(value)))

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
                self, "Utilisateur", "Sélectionnez un utilisateur."
            )
            return None
        raw_id = self.table.item(row, 0).text()
        user_id = raw_id if getattr(self.auth_service, "is_cloud", False) else int(raw_id)
        return user_id, self.table.item(row, 5).text() == "Actif"

    def _add_user(self):
        if UserDialog(self.auth_service, self).exec():
            self.rafraichir()
            NotificationManager.success(
                "Utilisateur créé", "Le nouveau compte est prêt."
            )

    def _toggle_user(self):
        selected = self._selected_user()
        if not selected:
            return
        try:
            self.auth_service.set_active(selected[0], not selected[1])
            self.rafraichir()
            NotificationManager.success(
                "Compte mis à jour", "Le statut de l'utilisateur a été modifié."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))

    def _reset_password(self):
        selected = self._selected_user()
        if not selected:
            return
        if getattr(self.auth_service, "is_cloud", False):
            try:
                self.auth_service.reset_password(selected[0])
                NotificationManager.success("E-mail envoyé", "Le collaborateur a reçu un lien sécurisé de réinitialisation.")
            except Exception as exc:
                QMessageBox.critical(self, "Réinitialisation impossible", str(exc))
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
                    "Mot de passe réinitialisé", "Le nouveau mot de passe est actif."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Réinitialisation impossible", str(exc))

    def _change_role(self):
        selected = self._selected_user()
        if not selected:
            return
        row = self.table.currentRow()
        current = self.table.item(row, 4).text()
        roles = list(AuthService.ROLES)
        role, accepted = QInputDialog.getItem(self, "Modifier le rôle", "Nouveau rôle :", roles, roles.index(current) if current in roles else 0, False)
        if not accepted or role == current:
            return
        try:
            if getattr(self.auth_service, "is_cloud", False):
                self.auth_service.set_role(selected[0], role)
            else:
                QMessageBox.information(self, "Rôle", "La modification directe du rôle est disponible en mode Cloud.")
                return
            self.rafraichir()
            NotificationManager.success("Rôle mis à jour", "Les nouvelles permissions sont actives.")
        except Exception as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))

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
                self.auth_service.change_password(user.id, current, new_password)
                NotificationManager.success(
                    "Mot de passe modifié", "Votre mot de passe a été mis à jour."
                )
            except Exception as exc:
                QMessageBox.critical(self, "Modification impossible", str(exc))

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
            QLabel#PageTitle {{
                color: {TEXT};
                font-size: 29px;
                font-weight: 900;
            }}
            QLabel#PageSubtitle {{
                color: {MUTED};
                font-size: 13px;
            }}
            QFrame#SummaryCard {{
                background: white;
                border: 1px solid {BORDER};
                border-radius: 15px;
            }}
            QLabel#IdentityAvatar {{
                background: #E8F3FF;
                color: {PRIMARY};
                border-radius: 23px;
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
                font-size: 11px;
            }}
            QLabel#IdentityState {{
                color: #16A34A;
                font-size: 10px;
                font-weight: 700;
            }}
            QLabel#MetricTitle {{
                color: {MUTED};
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#MetricValue {{
                color: {TEXT};
                font-size: 25px;
                font-weight: 900;
            }}
            QFrame#LicenseCard {{
                background: #F8FBFF;
                border: 1px solid #BFDBFE;
                border-radius: 15px;
            }}
            QLabel#LicenseIcon {{
                color: {PRIMARY};
                font-size: 25px;
            }}
            QLabel#LicensePlan {{
                color: {TEXT};
                font-size: 16px;
                font-weight: 900;
            }}
            QLabel#LicenseDetail {{
                color: {MUTED};
                font-size: 12px;
            }}
            QLabel#CloudNotice {{
                padding: 11px 14px;
                color: #075985;
                background: #E0F2FE;
                border: 1px solid #7DD3FC;
                border-radius: 10px;
                font-weight: 700;
            }}
            QFrame#UsersSection {{
                background: white;
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QLabel#SectionTitle {{
                color: {TEXT};
                font-size: 18px;
                font-weight: 900;
            }}
            QLineEdit#SearchInput {{
                min-height: 38px;
                padding: 0 12px;
                background: #F8FAFC;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 9px;
            }}
            QLineEdit#SearchInput:focus {{
                background: white;
                border: 2px solid {PRIMARY};
            }}
            QPushButton#PrimaryButton {{
                min-height: 38px;
                padding: 0 17px;
                background: {PRIMARY};
                color: white;
                border: none;
                border-radius: 9px;
                font-size: 13px;
                font-weight: 800;
            }}
            QPushButton#PrimaryButton:hover {{
                background: {PRIMARY_DARK};
            }}
            QPushButton#SecondaryButton {{
                min-height: 38px;
                padding: 0 15px;
                background: white;
                color: #334155;
                border: 1px solid {BORDER};
                border-radius: 9px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#SecondaryButton:hover {{
                color: {PRIMARY};
                border-color: {PRIMARY};
                background: #F8FBFF;
            }}
            QTableWidget#UsersTable {{
                background: white;
                alternate-background-color: #F8FAFC;
                selection-background-color: #E8F3FF;
                selection-color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 11px;
            }}
            QTableWidget#UsersTable QHeaderView::section {{
                background: #F8FAFC;
                color: #475569;
                border: none;
                border-bottom: 1px solid {BORDER};
                padding: 10px;
                font-weight: 800;
            }}
            QTableWidget#UsersTable::item {{
                padding: 9px;
                border-bottom: 1px solid #EEF2F7;
            }}
        """
