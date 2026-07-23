from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap
import requests

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.constants import APP_NAME, VERSION
from core.paths import resource_path
from core.premium_theme import BORDER, MUTED, PRIMARY, PRIMARY_DARK, TEXT
from services.auth_service import AuthService
from services.cloud_auth_service import AccountDisabledError, CloudAuthError


class LoginDialog(QDialog):
    """Écran de connexion premium, volontairement épuré."""

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.authenticated_user = None
        self.settings = QSettings("NM FORMATION", APP_NAME)

        self.setWindowTitle(f"Connexion — {APP_NAME}")
        self.setModal(True)
        self.setFixedSize(920, 610)
        self.setObjectName("LoginDialog")
        self.setStyleSheet(self._dialog_style())

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_brand_panel())
        outer.addWidget(self._build_form_panel(), 1)

        remembered = self.settings.value("auth/remembered_username", "", type=str)
        if remembered:
            self.username.setText(remembered)
            self.remember.setChecked(True)
            self.password.setFocus()
        else:
            self.username.setFocus()

        self.password.returnPressed.connect(self._login)

    def _build_brand_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("BrandPanel")
        panel.setFixedWidth(390)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(48, 48, 48, 38)
        layout.setSpacing(14)
        layout.addStretch(1)

        logo = QLabel()
        logo.setObjectName("LoginLogo")
        logo.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(resource_path("assets/images/logo_formaprospect.png"))
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(230, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo.setText("Form@Prospect")
            logo.setStyleSheet("font-size: 30px; font-weight: 900; color: white;")
        layout.addWidget(logo)

        tagline = QLabel("Plateforme intelligente de prospection BTP")
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setObjectName("BrandTagline")
        layout.addWidget(tagline)

        layout.addStretch(1)

        promise = QLabel("Prospectez mieux. Décidez plus vite.")
        promise.setAlignment(Qt.AlignCenter)
        promise.setObjectName("BrandPromise")
        layout.addWidget(promise)
        return panel

    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("FormPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(72, 54, 72, 34)
        layout.setSpacing(0)
        layout.addStretch(1)

        card = QFrame()
        card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 34, 38, 34)
        card_layout.setSpacing(11)

        title = QLabel("Connexion à votre compte")
        title.setObjectName("LoginTitle")
        subtitle = QLabel("Accédez à votre espace Form@Prospect")
        subtitle.setObjectName("LoginSubtitle")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)

        card_layout.addWidget(self._field_label("Adresse e-mail professionnelle"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("prenom.nom@entreprise.fr")
        self.username.setClearButtonEnabled(True)
        card_layout.addWidget(self.username)

        card_layout.addSpacing(4)
        card_layout.addWidget(self._field_label("Mot de passe"))

        password_row = QHBoxLayout()
        password_row.setSpacing(8)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Votre mot de passe")
        self.password.setEchoMode(QLineEdit.Password)
        password_row.addWidget(self.password, 1)

        self.show_button = QPushButton("Afficher")
        self.show_button.setObjectName("ShowPasswordButton")
        self.show_button.setFixedWidth(88)
        self.show_button.clicked.connect(self._toggle_password)
        password_row.addWidget(self.show_button)
        card_layout.addLayout(password_row)

        self.remember = QCheckBox("Se souvenir de mon identifiant")
        card_layout.addWidget(self.remember)
        self.keep_session = QCheckBox("Maintenir ma session dans le coffre sécurisé Windows")
        self.keep_session.setChecked(True)
        card_layout.addWidget(self.keep_session)
        card_layout.addSpacing(4)

        login_button = QPushButton("Se connecter")
        login_button.setObjectName("LoginButton")
        login_button.setCursor(Qt.PointingHandCursor)
        login_button.clicked.connect(self._login)
        card_layout.addWidget(login_button)

        forgot_button = QPushButton("Mot de passe oublié ?")
        forgot_button.setObjectName("TextButton")
        forgot_button.clicked.connect(self._forgot_password)
        card_layout.addWidget(forgot_button, 0, Qt.AlignCenter)

        layout.addWidget(card)
        layout.addStretch(1)

        version = QLabel(f"Version {VERSION}  •  NM FORMATION")
        version.setObjectName("VersionLabel")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        return panel

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _toggle_password(self):
        currently_visible = self.password.echoMode() == QLineEdit.Normal
        self.password.setEchoMode(
            QLineEdit.Password if currently_visible else QLineEdit.Normal
        )
        self.show_button.setText("Afficher" if currently_visible else "Masquer")

    def _login(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            user = self.auth_service.authenticate(
                self.username.text(),
                self.password.text(),
                remember_session=self.keep_session.isChecked(),
            )
        except AccountDisabledError as exc:
            QMessageBox.warning(self, "Connexion refusée", str(exc))
            return
        except (CloudAuthError, requests.RequestException) as exc:
            QMessageBox.critical(
                self,
                "Service indisponible",
                f"La connexion sécurisée n'a pas pu être établie.\n\n{exc}",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        if user is None:
            QMessageBox.warning(
                self,
                "Connexion refusée",
                "Identifiant ou mot de passe incorrect.",
            )
            self.password.clear()
            self.password.setFocus()
            return

        if self.remember.isChecked():
            self.settings.setValue("auth/remembered_username", user.username)
        else:
            self.settings.remove("auth/remembered_username")

        self.authenticated_user = user
        self.accept()

    def _forgot_password(self):
        email = self.username.text().strip()
        if not email:
            QMessageBox.information(self, "Mot de passe oublié", "Saisissez d'abord votre adresse e-mail.")
            self.username.setFocus()
            return
        try:
            self.auth_service.request_password_reset(email)
        except (CloudAuthError, requests.RequestException) as exc:
            QMessageBox.critical(self, "Envoi impossible", str(exc))
            return
        QMessageBox.information(
            self,
            "E-mail envoyé",
            "Si ce compte existe, un lien sécurisé de réinitialisation vient d'être envoyé.",
        )

    @staticmethod
    def _dialog_style() -> str:
        return f"""
            QDialog#LoginDialog {{
                background: #F5F7FB;
            }}
            QDialog#LoginDialog QLabel {{
                background: transparent;
                border: none;
            }}
            QFrame#BrandPanel {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #061A36,
                    stop: 0.60 #0B4D86,
                    stop: 1 #338CE4
                );
                border: none;
            }}
            QLabel#LoginLogo {{
                background: transparent;
                border: none;
            }}
            QLabel#BrandTagline {{
                color: #D9ECFF;
                font-size: 15px;
                font-weight: 600;
            }}
            QLabel#BrandPromise {{
                color: #C7E3FF;
                font-size: 12px;
            }}
            QFrame#FormPanel {{
                background: #F5F7FB;
                border: none;
            }}
            QFrame#LoginCard {{
                background: white;
                border: 1px solid {BORDER};
                border-radius: 22px;
            }}
            QLabel#LoginTitle {{
                color: {TEXT};
                font-size: 24px;
                font-weight: 900;
            }}
            QLabel#LoginSubtitle {{
                color: {MUTED};
                font-size: 13px;
            }}
            QLabel#FieldLabel {{
                color: #334155;
                font-size: 12px;
                font-weight: 800;
            }}
            QLineEdit {{
                min-height: 42px;
                padding: 0 13px;
                background: #F8FAFC;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                background: white;
                border: 2px solid {PRIMARY};
            }}
            QPushButton#ShowPasswordButton {{
                min-height: 42px;
                background: white;
                color: #475569;
                border: 1px solid {BORDER};
                border-radius: 10px;
                font-weight: 700;
            }}
            QPushButton#ShowPasswordButton:hover {{
                color: {PRIMARY};
                border-color: {PRIMARY};
            }}
            QPushButton#TextButton {{
                color: {PRIMARY};
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 700;
            }}
            QCheckBox {{
                color: #475569;
                font-size: 12px;
                spacing: 7px;
                background: transparent;
                border: none;
            }}
            QPushButton#LoginButton {{
                min-height: 46px;
                background: {PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 900;
            }}
            QPushButton#LoginButton:hover {{
                background: {PRIMARY_DARK};
            }}
            QLabel#VersionLabel {{
                color: #94A3B8;
                font-size: 11px;
                padding-top: 16px;
            }}
        """
