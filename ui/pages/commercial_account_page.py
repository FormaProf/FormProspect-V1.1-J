from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from core.premium_theme import BORDER, PAGE_BG, PRIMARY, PRIMARY_DARK, TEXT
from core.session import SessionState
from services.auth_service import AuthService
from ui.components.notifications import NotificationManager
from ui.utils_profile import circular_avatar


class CommercialAccountPage(QWidget):
    profile_updated = Signal()

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.setObjectName('CommercialAccountPage')
        self.setStyleSheet(self._style())

        root = QVBoxLayout(self)
        root.setContentsMargins(42, 28, 42, 30)
        root.setSpacing(16)

        title = QLabel('Mon compte')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Gérez vos informations personnelles et la sécurité de votre compte.')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(5)

        root.addWidget(self._build_profile_card(), 1)
        root.addWidget(self._build_security_card())
        root.addWidget(self._build_license_card())
        root.addStretch(1)
        self.rafraichir()

    def _build_profile_card(self) -> QFrame:
        card = self._card('Mon profil')
        body = QHBoxLayout()
        body.setSpacing(36)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.avatar = QLabel()
        self.avatar.setObjectName('LargeAvatar')
        self.avatar.setFixedSize(174, 174)
        self.avatar.setAlignment(Qt.AlignCenter)
        left.addWidget(self.avatar, 0, Qt.AlignHCenter)
        left.addSpacing(10)

        upload = QPushButton('↥  Modifier ma photo')
        upload.setObjectName('PrimaryButton')
        upload.setFixedWidth(190)
        upload.clicked.connect(self._upload_photo)
        left.addWidget(upload, 0, Qt.AlignHCenter)

        remove = QPushButton('Supprimer la photo')
        remove.setObjectName('TextButton')
        remove.clicked.connect(self._remove_photo)
        left.addWidget(remove, 0, Qt.AlignHCenter)

        formats = QLabel('Formats acceptés : JPG, PNG\nTaille max. : 2 Mo')
        formats.setObjectName('Hint')
        formats.setAlignment(Qt.AlignCenter)
        left.addWidget(formats)
        body.addLayout(left)

        details = QVBoxLayout()
        details.setSpacing(0)
        self.name_value = self._detail_row(details, '♙', 'Nom et prénom')
        self.role_value = self._detail_row(details, '▣', 'Rôle', badge=True)
        self.status_value = self._detail_row(details, '○', 'Statut du compte', success=True)
        self.email_value = self._detail_row(details, '✉', 'Adresse e-mail')
        self.login_value = self._detail_row(details, '◷', 'Dernière connexion')

        edit_identity = QPushButton('✎  Modifier mes informations')
        edit_identity.setObjectName('SecondaryButton')
        edit_identity.clicked.connect(self._edit_identity)
        details.addSpacing(14)
        details.addWidget(edit_identity, 0, Qt.AlignRight)
        details.addStretch(1)
        body.addLayout(details, 1)
        card.layout().addLayout(body)
        return card

    def _build_security_card(self) -> QFrame:
        card = self._card('Sécurité')
        row = QHBoxLayout()
        lock = QLabel('♙')
        lock.setObjectName('FeatureIcon')
        lock.setFixedSize(54, 54)
        lock.setAlignment(Qt.AlignCenter)
        row.addWidget(lock)
        text = QVBoxLayout()
        strong = QLabel('Changer mon mot de passe')
        strong.setObjectName('FeatureTitle')
        desc = QLabel('Mettez à jour votre mot de passe régulièrement pour protéger votre compte.')
        desc.setObjectName('FeatureDescription')
        text.addWidget(strong)
        text.addWidget(desc)
        row.addLayout(text, 1)
        button = QPushButton('🔒  Changer mon mot de passe  ›')
        button.setObjectName('SecondaryButton')
        button.clicked.connect(self._change_password)
        row.addWidget(button)
        card.layout().addLayout(row)
        return card

    def _build_license_card(self) -> QFrame:
        card = self._card('Licence')
        row = QHBoxLayout()
        icon = QLabel('◆')
        icon.setObjectName('FeatureIcon')
        icon.setFixedSize(54, 54)
        icon.setAlignment(Qt.AlignCenter)
        row.addWidget(icon)
        text = QVBoxLayout()
        self.license_plan = QLabel('Licence Pro')
        self.license_plan.setObjectName('FeatureTitle')
        self.license_status = QLabel('Statut : Active')
        self.license_status.setObjectName('LicenseStatus')
        text.addWidget(self.license_plan)
        text.addWidget(self.license_status)
        row.addLayout(text, 1)
        card.layout().addLayout(row)
        return card

    def _card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName('AccountCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        label = QLabel(title)
        label.setObjectName('SectionTitle')
        layout.addWidget(label)
        return card

    def _detail_row(self, layout: QVBoxLayout, icon: str, label: str, *, badge=False, success=False) -> QLabel:
        frame = QFrame()
        frame.setObjectName('DetailRow')
        row = QHBoxLayout(frame)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(16)
        symbol = QLabel(icon)
        symbol.setObjectName('RowIcon')
        symbol.setFixedWidth(28)
        symbol.setAlignment(Qt.AlignCenter)
        name = QLabel(label)
        name.setObjectName('RowLabel')
        name.setFixedWidth(190)
        value = QLabel('—')
        value.setObjectName('SuccessValue' if success else 'BadgeValue' if badge else 'RowValue')
        row.addWidget(symbol)
        row.addWidget(name)
        row.addWidget(value, 1)
        layout.addWidget(frame)
        return value

    def rafraichir(self):
        user = self.auth_service.get_user(SessionState.user().id) if SessionState.user() else None
        if not user:
            return
        SessionState.login(user)
        self.avatar.setPixmap(circular_avatar(user.photo_path, user.display_name, 170))
        self.name_value.setText(user.display_name)
        self.role_value.setText(user.role)
        self.status_value.setText('Actif  ✓')
        self.email_value.setText(user.email or 'Non renseignée')
        record = self.auth_service.get_user_record(user.id) or {}
        last_login = record.get('last_login')
        self.login_value.setText(self._format_datetime(last_login))
        licence = self.auth_service.license_info()
        self.license_plan.setText(f"Licence {licence.get('plan', 'Pro')}")
        self.license_status.setText(f"Statut : {licence.get('status', 'Active')}")

    @staticmethod
    def _format_datetime(value: str | None) -> str:
        if not value:
            return 'Jamais'
        try:
            date = datetime.fromisoformat(value)
            return date.strftime('%d/%m/%Y à %H:%M')
        except ValueError:
            return value


    def _edit_identity(self):
        user = SessionState.user()
        if not user:
            return

        if not hasattr(self.auth_service, 'update_profile_identity'):
            QMessageBox.information(
                self,
                'Profil',
                'La modification du nom et du prénom est disponible pour les comptes Cloud.',
            )
            return

        first_name, ok = QInputDialog.getText(
            self,
            'Modifier mon profil',
            'Prénom :',
            text=user.first_name or '',
        )
        if not ok:
            return

        last_name, ok = QInputDialog.getText(
            self,
            'Modifier mon profil',
            'Nom :',
            text=user.last_name or '',
        )
        if not ok:
            return

        try:
            refreshed = self.auth_service.update_profile_identity(
                first_name,
                last_name,
            )
            SessionState.login(refreshed)
            self.rafraichir()
            self.profile_updated.emit()
            NotificationManager.success(
                'Profil mis à jour',
                'Votre nom et votre prénom ont été enregistrés.',
            )
        except Exception as exc:
            QMessageBox.critical(self, 'Modification impossible', str(exc))

    def _upload_photo(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choisir une photo de profil', '', 'Images (*.png *.jpg *.jpeg)')
        if not filename:
            return
        try:
            path = Path(filename)
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('La photo dépasse la taille maximale de 2 Mo.')
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                raise ValueError("Le fichier sélectionné n'est pas une image valide.")
            user = SessionState.user()
            saved = self.auth_service.update_profile_photo(user.id, path)
            refreshed = self.auth_service.get_user(user.id)
            SessionState.login(refreshed)
            self.rafraichir()
            self.profile_updated.emit()
            NotificationManager.success('Photo mise à jour', 'Votre nouvelle photo de profil a été enregistrée.')
        except Exception as exc:
            QMessageBox.critical(self, 'Photo impossible', str(exc))

    def _remove_photo(self):
        user = SessionState.user()
        if not user or not user.photo_path:
            return
        answer = QMessageBox.question(self, 'Supprimer la photo', 'Voulez-vous supprimer votre photo de profil ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.auth_service.remove_profile_photo(user.id)
            SessionState.login(self.auth_service.get_user(user.id))
            self.rafraichir()
            self.profile_updated.emit()

    def _change_password(self):
        user = SessionState.user()
        if not user:
            return
        current, ok = QInputDialog.getText(self, 'Mot de passe actuel', 'Saisissez votre mot de passe actuel :', echo=QLineEdit.Password)
        if not ok:
            return
        new, ok = QInputDialog.getText(self, 'Nouveau mot de passe', 'Nouveau mot de passe (8 caractères minimum) :', echo=QLineEdit.Password)
        if not ok:
            return
        confirm, ok = QInputDialog.getText(self, 'Confirmation', 'Confirmez le nouveau mot de passe :', echo=QLineEdit.Password)
        if not ok:
            return
        if new != confirm:
            QMessageBox.warning(self, 'Mot de passe', 'Les deux mots de passe ne correspondent pas.')
            return
        try:
            self.auth_service.change_password(user.id, current, new)
            NotificationManager.success('Mot de passe modifié', 'Votre mot de passe a été mis à jour.')
        except Exception as exc:
            QMessageBox.critical(self, 'Modification impossible', str(exc))

    @staticmethod
    def _style() -> str:
        return f'''
        QWidget#CommercialAccountPage {{ background: {PAGE_BG}; color: {TEXT}; }}
        QLabel#PageTitle {{ font-size: 28px; font-weight: 900; color: #0F1F38; }}
        QLabel#PageSubtitle {{ font-size: 13px; color: #64748B; }}
        QFrame#AccountCard {{ background: white; border: 1px solid {BORDER}; border-radius: 14px; }}
        QLabel#SectionTitle {{ color: {PRIMARY}; font-size: 18px; font-weight: 900; }}
        QLabel#LargeAvatar {{ background: transparent; border: 4px solid white; border-radius: 87px; }}
        QPushButton#PrimaryButton {{ min-height: 42px; padding: 0 18px; background: {PRIMARY}; color: white; border: none; border-radius: 9px; font-size: 13px; font-weight: 800; }}
        QPushButton#PrimaryButton:hover {{ background: {PRIMARY_DARK}; }}
        QPushButton#TextButton {{ color: #64748B; background: transparent; border: none; font-size: 11px; }}
        QPushButton#TextButton:hover {{ color: #DC2626; text-decoration: underline; }}
        QLabel#Hint {{ color: #64748B; font-size: 11px; line-height: 1.5; }}
        QFrame#DetailRow {{ border: none; border-bottom: 1px solid #E8EDF4; background: transparent; }}
        QLabel#RowIcon {{ color: #0F1F38; font-size: 21px; }}
        QLabel#RowLabel {{ color: #334155; font-size: 13px; }}
        QLabel#RowValue {{ color: #0F172A; font-size: 13px; font-weight: 700; }}
        QLabel#BadgeValue {{ color: #0B65D8; background: #EAF3FF; border-radius: 7px; padding: 6px 10px; font-size: 12px; font-weight: 800; }}
        QLabel#SuccessValue, QLabel#LicenseStatus {{ color: #16A34A; font-size: 13px; font-weight: 800; }}
        QLabel#FeatureIcon {{ color: {PRIMARY}; background: #EAF3FF; border-radius: 10px; font-size: 24px; }}
        QLabel#FeatureTitle {{ color: #0F172A; font-size: 14px; font-weight: 900; }}
        QLabel#FeatureDescription {{ color: #64748B; font-size: 12px; }}
        QPushButton#SecondaryButton {{ min-height: 40px; padding: 0 16px; background: white; color: {PRIMARY}; border: 1px solid {BORDER}; border-radius: 9px; font-size: 12px; font-weight: 800; }}
        QPushButton#SecondaryButton:hover {{ border-color: {PRIMARY}; background: #F8FBFF; }}
        '''
