from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.theme_settings import (
    get_theme_preference,
    theme_label,
)
from services.auth_service import AuthService
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
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

        self.google_calendar_bar = self._build_google_calendar_bar()
        self.view.add_scroll_footer(self.google_calendar_bar)

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

    def _build_google_calendar_bar(self) -> QFrame:
        bar = QFrame()
        # Reuse the premium account footer surface so the new integration
        # follows all existing themes without introducing another theme read.
        bar.setObjectName("AppearanceBar")
        bar.setMinimumHeight(82)

        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(12)

        icon = QLabel("31")
        icon.setObjectName("AppearanceIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(38, 38)
        row.addWidget(icon)

        copy = QVBoxLayout()
        copy.setSpacing(2)

        eyebrow = QLabel("AGENDA CONNECTÉ")
        eyebrow.setObjectName("AppearanceEyebrow")

        title = QLabel("Google Agenda")
        title.setObjectName("AppearanceTitle")

        description = QLabel(
            "Connectez votre agenda Google à Form@Prospect pour préparer "
            "la synchronisation de vos rendez-vous."
        )
        description.setObjectName("AppearanceDescription")
        description.setWordWrap(True)

        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(description)
        row.addLayout(copy, 1)

        self.google_calendar_status = QLabel("À vérifier")
        self.google_calendar_status.setObjectName("AppearanceValue")
        self.google_calendar_status.setAlignment(Qt.AlignCenter)
        self.google_calendar_status.setMinimumWidth(120)
        self.google_calendar_status.setFixedHeight(32)
        row.addWidget(self.google_calendar_status)

        self.google_calendar_refresh_button = QPushButton("Actualiser")
        self.google_calendar_refresh_button.setObjectName("AppearanceButton")
        self.google_calendar_refresh_button.setCursor(Qt.PointingHandCursor)
        self.google_calendar_refresh_button.setFixedHeight(38)
        self.google_calendar_refresh_button.clicked.connect(
            self.refresh_google_calendar_status
        )
        row.addWidget(self.google_calendar_refresh_button)

        self.google_calendar_sync_button = QPushButton("Synchroniser")
        self.google_calendar_sync_button.setObjectName("AppearanceButton")
        self.google_calendar_sync_button.setCursor(Qt.PointingHandCursor)
        self.google_calendar_sync_button.setFixedHeight(38)
        self.google_calendar_sync_button.setEnabled(False)
        self.google_calendar_sync_button.clicked.connect(
            self._sync_google_calendar_planned_actions
        )
        row.addWidget(self.google_calendar_sync_button)

        self.google_calendar_action_button = QPushButton(
            "Connecter Google Agenda"
        )
        self.google_calendar_action_button.setObjectName("AppearanceButton")
        self.google_calendar_action_button.setCursor(Qt.PointingHandCursor)
        self.google_calendar_action_button.setFixedHeight(38)
        self.google_calendar_action_button.clicked.connect(
            self._toggle_google_calendar
        )
        row.addWidget(self.google_calendar_action_button)

        self._google_calendar_connected = False
        self._google_calendar_configured = False
        return bar

    def _set_google_calendar_state(
        self,
        *,
        configured: bool,
        connected: bool,
        error: str = "",
    ) -> None:
        self._google_calendar_configured = bool(configured)
        self._google_calendar_connected = bool(connected)

        if error:
            self.google_calendar_status.setText("Indisponible")
            self.google_calendar_action_button.setText(
                "Connecter Google Agenda"
            )
            self.google_calendar_action_button.setEnabled(False)
            self.google_calendar_sync_button.setEnabled(False)
            return

        if not configured:
            self.google_calendar_status.setText("Non configuré")
            self.google_calendar_action_button.setText(
                "Connecter Google Agenda"
            )
            self.google_calendar_action_button.setEnabled(False)
            self.google_calendar_sync_button.setEnabled(False)
            return

        self.google_calendar_action_button.setEnabled(True)
        self.google_calendar_sync_button.setEnabled(bool(connected))
        if connected:
            self.google_calendar_status.setText("Connecté")
            self.google_calendar_action_button.setText(
                "Déconnecter"
            )
        else:
            self.google_calendar_status.setText("Non connecté")
            self.google_calendar_action_button.setText(
                "Connecter Google Agenda"
            )

    def refresh_google_calendar_status(self) -> None:
        if not CloudRuntime.is_active():
            self._set_google_calendar_state(
                configured=False,
                connected=False,
                error="cloud_inactive",
            )
            return

        self.google_calendar_refresh_button.setEnabled(False)
        try:
            status = CloudRuntime.api().get_google_calendar_status()
            self._set_google_calendar_state(
                configured=bool(status.get("configured")),
                connected=bool(status.get("connected")),
            )
        except (CloudAPIError, RuntimeError):
            self._set_google_calendar_state(
                configured=False,
                connected=False,
                error="cloud_error",
            )
        finally:
            self.google_calendar_refresh_button.setEnabled(True)

    def _sync_google_calendar_planned_actions(self) -> None:
        if not self._google_calendar_connected:
            return

        self.google_calendar_sync_button.setEnabled(False)
        self.google_calendar_refresh_button.setEnabled(False)
        self.google_calendar_status.setText("Synchronisation…")
        try:
            result = (
                CloudRuntime.api().sync_google_calendar_planned_actions()
            )
            created = int(result.get("created") or 0)
            updated = int(result.get("updated") or 0)
            deleted = int(result.get("deleted") or 0)
            errors = int(result.get("errors") or 0)

            if errors:
                self.google_calendar_status.setText(
                    f"Partiel · {errors} erreur(s)"
                )
            else:
                self.google_calendar_status.setText(
                    f"Synchronisé · +{created} / ↻{updated} / -{deleted}"
                )
        except (CloudAPIError, RuntimeError):
            self.google_calendar_status.setText("Échec synchronisation")
        finally:
            self.google_calendar_refresh_button.setEnabled(True)
            self.google_calendar_sync_button.setEnabled(
                self._google_calendar_connected
            )

    def _toggle_google_calendar(self) -> None:
        if not self._google_calendar_configured:
            return

        if self._google_calendar_connected:
            answer = QMessageBox.question(
                self,
                "Google Agenda",
                "Déconnecter votre Google Agenda de Form@Prospect ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

            try:
                CloudRuntime.api().disconnect_google_calendar()
            except (CloudAPIError, RuntimeError) as exc:
                QMessageBox.critical(
                    self,
                    "Google Agenda",
                    str(exc),
                )
                return

            self.refresh_google_calendar_status()
            return

        try:
            authorization_url = (
                CloudRuntime.api().get_google_calendar_connect_url()
            )
        except (CloudAPIError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Google Agenda",
                str(exc),
            )
            return

        if not authorization_url:
            QMessageBox.critical(
                self,
                "Google Agenda",
                "Form@Prospect n'a pas reçu l'adresse de connexion Google.",
            )
            return

        if not QDesktopServices.openUrl(QUrl(authorization_url)):
            QMessageBox.critical(
                self,
                "Google Agenda",
                "Impossible d'ouvrir votre navigateur.",
            )
            return

        QMessageBox.information(
            self,
            "Google Agenda",
            "La page Google vient de s'ouvrir dans votre navigateur.\n\n"
            "Autorisez Form@Prospect, revenez ensuite ici puis cliquez "
            "sur « Actualiser ».",
        )

    def apply_appearance_theme(self):
        palette = account_page_palette(get_theme_preference())
        self.setStyleSheet(account_shell_stylesheet(palette))
        if hasattr(self.view, "apply_appearance_theme"):
            self.view.apply_appearance_theme()

    def rafraichir(self):
        if hasattr(self.view, "rafraichir"):
            self.view.rafraichir()
        self.refresh_google_calendar_status()
        self.refresh_appearance_summary()

    def refresh_appearance_summary(self):
        self.appearance_value.setText(
            theme_label(get_theme_preference())
        )
        self.apply_appearance_theme()
