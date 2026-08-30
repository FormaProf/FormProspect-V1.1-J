from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from ui.dialogs.commercial_partner_dialog import CommercialPartnerDialog
from ui.dialogs.portfolio_transfer_dialog import PortfolioTransferDialog


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
        row.addWidget(self._kpi_card("Head of Sales", "0", "managers", "◇"), 1)
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
        self.search.textChanged.connect(self._apply_filters)
        top.addWidget(self.search)

        self.add_user_button = QPushButton("＋ Ajouter un utilisateur")
        self.add_user_button.setObjectName("PrimaryButton")
        self.add_user_button.clicked.connect(self._add_user)
        top.addWidget(self.add_user_button)

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

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_label = QLabel("Filtrer :")
        filter_label.setObjectName("FilterLabel")
        filter_row.addWidget(filter_label)

        self.role_filter = QComboBox()
        self.role_filter.setObjectName("FilterCombo")
        self.role_filter.setFixedWidth(190)
        self.role_filter.addItem("Tous les rôles", "")
        self.role_filter.addItem("Administrateur", "Administrateur")
        self.role_filter.addItem("Head of Sales", "Head of Sales")
        self.role_filter.addItem("Dirigeant hors France", "Dirigeant hors France")
        self.role_filter.addItem("Commercial", "Commercial")
        self.role_filter.addItem("Formateur", "Formateur")
        self.role_filter.addItem("Assistant administratif", "Assistant administratif")
        self.role_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.role_filter)

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("FilterCombo")
        self.status_filter.setFixedWidth(150)
        self.status_filter.addItem("Tous les statuts", "")
        self.status_filter.addItem("Actif", "Actif")
        self.status_filter.addItem("Inactif", "Inactif")
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.status_filter)

        self.presence_filter = QComboBox()
        self.presence_filter.setObjectName("FilterCombo")
        self.presence_filter.setFixedWidth(170)
        self.presence_filter.addItem("Toutes les présences", "")
        self.presence_filter.addItem("En ligne", "online")
        self.presence_filter.addItem("Inactif", "idle")
        self.presence_filter.addItem("Hors ligne", "offline")
        self.presence_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.presence_filter)

        reset_filters = QPushButton("Réinitialiser")
        reset_filters.setObjectName("GhostButton")
        reset_filters.clicked.connect(self._reset_filters)
        filter_row.addWidget(reset_filters)

        filter_row.addStretch(1)

        self.filter_result = QLabel("0 membre affiché")
        self.filter_result.setObjectName("FilterResult")
        filter_row.addWidget(self.filter_result)

        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        toggle = QPushButton("Activer / désactiver")
        toggle.setObjectName("SecondaryButton")
        toggle.clicked.connect(self._toggle_user)

        reset = QPushButton("Envoyer un lien de réinitialisation")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(self._reset_password)

        self.promote_button = QPushButton("Promouvoir")
        self.promote_button.setObjectName("PromoteButton")
        self.promote_button.setEnabled(False)
        self.promote_button.setToolTip(
            "Sélectionnez un commercial actif à promouvoir en Head of Sales."
        )
        self.promote_button.clicked.connect(self._promote_user)

        self.transfer_portfolio_button = QPushButton("Transférer le portefeuille")
        self.transfer_portfolio_button.setObjectName("TransferButton")
        self.transfer_portfolio_button.setEnabled(False)
        self.transfer_portfolio_button.setToolTip(
            "Sélectionnez un commercial désactivé dont le portefeuille doit être repris."
        )
        self.transfer_portfolio_button.clicked.connect(self._transfer_portfolio)

        self.partners_button = QPushButton("Partenaires hors France")
        self.partners_button.setObjectName("SecondaryButton")
        self.partners_button.setToolTip(
            "Créer une structure commerciale étrangère et rattacher son dirigeant et ses setters."
        )
        self.partners_button.clicked.connect(self._open_commercial_partners)

        action_row.addWidget(toggle)
        action_row.addWidget(reset)
        action_row.addWidget(self.promote_button)
        action_row.addWidget(self.transfer_portfolio_button)
        action_row.addWidget(self.partners_button)
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
        self.table.itemSelectionChanged.connect(self._update_promote_button)
        self.table.itemSelectionChanged.connect(self._update_transfer_button)

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

    @staticmethod
    def _display_role(value: str) -> str:
        """Conserve le rôle technique Manager mais affiche son intitulé métier."""
        return "Head of Sales" if str(value or "").strip() == "Manager" else str(value or "")

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

        try:
            licence = self.auth_service.license_info()
        except Exception as exc:
            self.license_text.setText("◆  Licence Cloud indisponible")
            self.add_user_button.setEnabled(False)
            self.add_user_button.setToolTip(str(exc))
        else:
            plan_label = str(
                licence.get("plan_label")
                or licence.get("plan")
                or "—"
            ).strip()
            status_value = str(licence.get("status") or "—").strip()
            status_label = (
                status_value[:1].upper() + status_value[1:]
                if status_value
                else "—"
            )
            unlimited = bool(licence.get("unlimited", False))
            max_users = licence.get("max_users")

            if unlimited:
                self.license_text.setText(
                    f"◆  Licence {plan_label}   •   {status_label}   •   "
                    f"{active} compte"
                    + ("s actifs" if active != 1 else " actif")
                    + "   •   Illimité"
                )
            else:
                self.license_text.setText(
                    f"◆  Licence {plan_label}   •   {status_label}   •   "
                    f"{active}/{max_users if max_users is not None else '—'} comptes utilisés"
                )

            # Le Backend reste l'autorité finale. L'état du bouton est seulement
            # un retour UX immédiat pour les futures licences limitées.
            if "can_add_user" in licence:
                can_add_user = bool(licence.get("can_add_user"))
                self.add_user_button.setEnabled(can_add_user)
                if can_add_user:
                    self.add_user_button.setText("＋ Ajouter un utilisateur")
                    self.add_user_button.setToolTip("")
                else:
                    self.add_user_button.setText("Limite de licences atteinte")
                    self.add_user_button.setToolTip(
                        "Désactivez un compte ou augmentez le nombre de licences "
                        "avant d'ajouter un nouvel utilisateur."
                    )
            else:
                # Compatibilité du mode local historique.
                self.add_user_button.setEnabled(True)
                self.add_user_button.setText("＋ Ajouter un utilisateur")
                self.add_user_button.setToolTip("")

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
                self._display_role(user["role"]),
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
                        if value == "Head of Sales"
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

        self._apply_filters()

    @staticmethod
    def _normalized_presence(value: str) -> str:
        text = str(value or "").strip().lower()
        if "en ligne" in text:
            return "online"
        if "inactif" in text:
            return "idle"
        return "offline"

    def _apply_filters(self, *_args):
        query = self.search.text().strip().lower()
        role_filter = str(self.role_filter.currentData() or "").strip().lower()
        status_filter = str(self.status_filter.currentData() or "").strip().lower()
        presence_filter = str(self.presence_filter.currentData() or "").strip().lower()

        visible_count = 0

        for row in range(self.table.rowCount()):
            def cell(column: int) -> str:
                item = self.table.item(row, column)
                return item.text().strip() if item else ""

            searchable = " ".join(
                cell(column)
                for column in range(1, self.table.columnCount())
            ).lower()

            role_value = cell(3).lower()
            status_value = cell(4).lower()
            presence_value = self._normalized_presence(cell(5))

            matches_search = not query or query in searchable
            matches_role = not role_filter or role_value == role_filter
            matches_status = not status_filter or status_value == status_filter
            matches_presence = (
                not presence_filter or presence_value == presence_filter
            )

            visible = (
                matches_search
                and matches_role
                and matches_status
                and matches_presence
            )
            self.table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1

        self.filter_result.setText(
            f"{visible_count} membre"
            + ("s" if visible_count != 1 else "")
            + " affiché"
            + ("s" if visible_count != 1 else "")
        )

        current_row = self.table.currentRow()
        if current_row >= 0 and self.table.isRowHidden(current_row):
            self.table.clearSelection()
        self._update_promote_button()
        self._update_transfer_button()

    def _filter(self, _text=""):
        """Compatibilité avec les anciens appels internes."""
        self._apply_filters()

    def _reset_filters(self):
        self.search.clear()
        self.role_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.presence_filter.setCurrentIndex(0)
        self._apply_filters()

    def _selected_user_details(self, *, show_message: bool = True):
        row = self.table.currentRow()

        if row < 0 or self.table.isRowHidden(row):
            if show_message:
                QMessageBox.information(
                    self,
                    "Utilisateur",
                    "Sélectionnez un utilisateur.",
                )
            return None

        def cell(column: int) -> str:
            item = self.table.item(row, column)
            return item.text().strip() if item else ""

        return {
            "id": cell(0),
            "name": cell(1),
            "email": cell(2),
            "role": cell(3),
            "active": cell(4) == "Actif",
        }

    def _selected_user(self):
        details = self._selected_user_details()
        if details is None:
            return None
        return details["id"], details["active"]

    def _update_promote_button(self):
        if not hasattr(self, "promote_button"):
            return

        if not getattr(self.auth_service, "is_cloud", False):
            self.promote_button.setVisible(False)
            return

        self.promote_button.setVisible(True)
        details = self._selected_user_details(show_message=False)
        enabled = bool(
            details
            and details["role"] == "Commercial"
            and details["active"]
        )
        self.promote_button.setEnabled(enabled)

        if enabled:
            self.promote_button.setToolTip(
                f"Promouvoir {details['name']} en Head of Sales."
            )
        elif details and details["role"] == "Commercial" and not details["active"]:
            self.promote_button.setToolTip(
                "Activez d'abord ce compte avant de le promouvoir."
            )
        elif details and details["role"] == "Head of Sales":
            self.promote_button.setToolTip("Ce membre est déjà Head of Sales.")
        else:
            self.promote_button.setToolTip(
                "Sélectionnez un commercial actif à promouvoir en Head of Sales."
            )

    def _update_transfer_button(self):
        if not hasattr(self, "transfer_portfolio_button"):
            return

        if not getattr(self.auth_service, "is_cloud", False):
            self.transfer_portfolio_button.setVisible(False)
            return

        self.transfer_portfolio_button.setVisible(True)
        details = self._selected_user_details(show_message=False)
        enabled = bool(
            details
            and details["role"] == "Commercial"
            and not details["active"]
        )
        self.transfer_portfolio_button.setEnabled(enabled)

        if enabled:
            self.transfer_portfolio_button.setToolTip(
                f"Transférer le portefeuille de {details['name']} vers un autre commercial."
            )
        elif details and details["role"] == "Commercial" and details["active"]:
            self.transfer_portfolio_button.setToolTip(
                "Désactivez d'abord ce compte avant de transférer son portefeuille."
            )
        else:
            self.transfer_portfolio_button.setToolTip(
                "Sélectionnez un commercial désactivé dont le portefeuille doit être repris."
            )

    def _open_portfolio_transfer(self, details: dict):
        dialog = PortfolioTransferDialog(
            self.auth_service,
            details["id"],
            details.get("name") or "",
            self,
        )
        if dialog.exec() and dialog.transfer_result:
            result = dialog.transfer_result
            self.rafraichir()
            NotificationManager.success(
                "Portefeuille transféré",
                (
                    f"{int(result.get('prospects_transferred') or 0)} prospect(s) "
                    f"et {int(result.get('activities_transferred') or 0)} activité(s) "
                    "planifiée(s) ont été réattribués."
                ),
            )
            return True
        return False

    def _transfer_portfolio(self):
        details = self._selected_user_details()
        if details is None:
            return

        if details["role"] != "Commercial":
            QMessageBox.information(
                self,
                "Transfert de portefeuille",
                "Seul le portefeuille d'un Commercial peut être transféré.",
            )
            return

        if details["active"]:
            QMessageBox.information(
                self,
                "Transfert de portefeuille",
                "Désactivez d'abord ce compte avant de transférer son portefeuille.",
            )
            return

        self._open_portfolio_transfer(details)

    def _promote_user(self):
        details = self._selected_user_details()
        if details is None:
            return

        if details["role"] != "Commercial":
            QMessageBox.information(
                self,
                "Promotion",
                "Seul un commercial peut être promu en Head of Sales depuis cette action.",
            )
            return

        if not details["active"]:
            QMessageBox.information(
                self,
                "Promotion",
                "Activez d'abord ce compte avant de le promouvoir.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Promouvoir en Head of Sales",
            (
                f"Promouvoir {details['name']} en Head of Sales ?\n\n"
                "Son rôle Cloud passera de Commercial à Manager. Il disposera "
                "des droits de supervision de l'activité commerciale et pourra "
                "encadrer des commerciaux.\n\n"
                "Le changement de droits est immédiat côté Cloud."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            self.auth_service.set_role(details["id"], "Manager")
            self.rafraichir()
            NotificationManager.success(
                "Promotion effectuée",
                f"{details['name']} est désormais Head of Sales.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Promotion impossible",
                str(exc),
            )

    def _open_commercial_partners(self):
        if not getattr(self.auth_service, "is_cloud", False):
            QMessageBox.information(
                self,
                "Partenaires Cloud",
                "La gestion des partenaires commerciaux est disponible uniquement en mode Cloud.",
            )
            return
        dialog = CommercialPartnerDialog(self.auth_service, self)
        dialog.exec()
        self.rafraichir()

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
        details = self._selected_user_details()

        if details is None:
            return

        new_active = not details["active"]

        try:
            self.auth_service.set_active(details["id"], new_active)
            self.rafraichir()
            NotificationManager.success(
                "Compte mis à jour",
                "Le statut de l'utilisateur a été modifié.",
            )

            if (
                getattr(self.auth_service, "is_cloud", False)
                and details["role"] == "Commercial"
                and not new_active
            ):
                answer = QMessageBox.question(
                    self,
                    "Compte commercial désactivé",
                    (
                        f"{details['name']} est maintenant désactivé.\n\n"
                        "Souhaitez-vous transférer son portefeuille vers un autre "
                        "Commercial actif maintenant ?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if answer == QMessageBox.Yes:
                    self._open_portfolio_transfer(details)

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

            QLabel#FilterLabel {{
                color: #475569;
                font-size: 10px;
                font-weight: 800;
                padding-right: 2px;
            }}

            QLabel#FilterResult {{
                color: #64748B;
                font-size: 9px;
                font-weight: 700;
                padding: 0 4px;
            }}

            QComboBox#FilterCombo {{
                min-height: 34px;
                padding: 0 30px 0 11px;
                background: #F8FAFC;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
            }}

            QComboBox#FilterCombo:hover {{
                background: white;
                border-color: #B8C8D9;
            }}

            QComboBox#FilterCombo:focus {{
                background: white;
                border: 1px solid {PRIMARY};
            }}

            QComboBox#FilterCombo::drop-down {{
                width: 28px;
                border: none;
                background: transparent;
            }}

            QComboBox#FilterCombo QAbstractItemView {{
                background: white;
                color: {TEXT};
                border: 1px solid {BORDER};
                selection-background-color: #EEF6FF;
                selection-color: {TEXT};
                outline: none;
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

            QPushButton#PromoteButton {{
                min-height: 34px;
                padding: 0 14px;
                background: #EAF4FF;
                color: {PRIMARY};
                border: 1px solid #B9DCFF;
                border-radius: 9px;
                font-size: 10px;
                font-weight: 800;
            }}

            QPushButton#PromoteButton:hover {{
                background: #DCEEFF;
                border-color: {PRIMARY};
            }}

            QPushButton#PromoteButton:disabled {{
                background: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }}

            QPushButton#TransferButton {{
                min-height: 34px;
                padding: 0 14px;
                background: #ECFDF5;
                color: #047857;
                border: 1px solid #A7F3D0;
                border-radius: 9px;
                font-size: 10px;
                font-weight: 800;
            }}

            QPushButton#TransferButton:hover {{
                background: #D1FAE5;
                border-color: #34D399;
            }}

            QPushButton#TransferButton:disabled {{
                background: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
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
