from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.session import SessionState
from core.theme_settings import get_theme_preference
from services.auth_service import AuthService
from ui.account_premium_theme import (
    account_page_palette,
    commercial_account_stylesheet,
)
from ui.components.notifications import NotificationManager
from ui.utils_profile import circular_avatar


def _preserve_cloud_session_identity(local_user, current_user):
    # Preserve Cloud identity when the local shadow profile is reloaded.
    if local_user is None or current_user is None:
        return local_user

    cloud_user_id = str(
        getattr(current_user, "cloud_user_id", "") or ""
    ).strip()
    if not cloud_user_id:
        return local_user

    return replace(
        local_user,
        role=current_user.role,
        cloud_user_id=current_user.cloud_user_id,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization_name,
        permissions=current_user.permissions,
        can_create_prospect_manually=(
            current_user.can_create_prospect_manually
        ),
    )


class CommercialAccountPage(QWidget):
    profile_updated = Signal()

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.setObjectName("CommercialAccountPage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("AccountScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("CommercialAccountContent")

        root = QVBoxLayout(content)
        self.content_layout = root
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(12)

        root.addWidget(self._build_hero())

        metrics = QHBoxLayout()
        metrics.setSpacing(10)

        identity_card, self.metric_identity_value, self.metric_identity_caption = (
            self._build_metric_card(
                "●",
                "Identité",
                "—",
                "Profil utilisateur",
                "blue",
            )
        )
        access_card, self.metric_access_value, self.metric_access_caption = (
            self._build_metric_card(
                "↗",
                "Accès",
                "—",
                "Mode de connexion",
                "violet",
            )
        )
        license_card, self.metric_license_value, self.metric_license_caption = (
            self._build_metric_card(
                "◆",
                "Licence",
                "—",
                "État de l'abonnement",
                "green",
            )
        )

        metrics.addWidget(identity_card, 1)
        metrics.addWidget(access_card, 1)
        metrics.addWidget(license_card, 1)
        root.addLayout(metrics)

        self.profile_card = self._build_profile_card()
        self.profile_card.setMinimumHeight(365)
        root.addWidget(self.profile_card)

        self.organization_card = self._build_commercial_organization_card()
        self.organization_card.setVisible(False)
        root.addWidget(self.organization_card)

        root.addWidget(self._build_security_card())
        root.addWidget(self._build_license_card())
        root.addStretch(1)

        self.scroll_area.setWidget(content)
        outer.addWidget(self.scroll_area)

        self.apply_appearance_theme()
        self.rafraichir()

    def add_scroll_footer(self, widget: QWidget) -> None:
        """Ajoute un bloc au contenu défilant, avant l'espace final."""
        index = max(0, self.content_layout.count() - 1)
        self.content_layout.insertWidget(index, widget)

    def apply_appearance_theme(self) -> None:
        self.setStyleSheet(self._style())

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("AccountHero")
        hero.setMinimumHeight(142)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(20, 16, 18, 16)
        layout.setSpacing(16)

        orb = QFrame()
        orb.setObjectName("AccountHeroOrb")
        orb.setFixedSize(68, 68)
        orb_layout = QVBoxLayout(orb)
        orb_layout.setContentsMargins(0, 0, 0, 0)

        glyph = QLabel("◎")
        glyph.setObjectName("AccountHeroGlyph")
        glyph.setAlignment(Qt.AlignCenter)
        orb_layout.addWidget(glyph)
        layout.addWidget(orb, 0, Qt.AlignVCenter)

        copy = QVBoxLayout()
        copy.setSpacing(4)

        eyebrow = QLabel("ACCOUNT CENTER  •  IDENTITÉ & SÉCURITÉ")
        eyebrow.setObjectName("AccountHeroEyebrow")

        title = QLabel("Mon compte")
        title.setObjectName("AccountHeroTitle")

        subtitle = QLabel(
            "Gérez votre identité, vos accès et les paramètres essentiels "
            "de votre espace Form@Prospect."
        )
        subtitle.setObjectName("AccountHeroSubtitle")
        subtitle.setWordWrap(True)

        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(subtitle)
        layout.addLayout(copy, 1)

        status = QVBoxLayout()
        status.setSpacing(7)
        status.setAlignment(Qt.AlignTop | Qt.AlignRight)

        active = QLabel("●  COMPTE ACTIF")
        active.setObjectName("AccountActiveBadge")
        active.setAlignment(Qt.AlignCenter)
        active.setFixedHeight(30)
        active.setMinimumWidth(150)

        self.hero_role_value = QLabel("Utilisateur")
        self.hero_role_value.setObjectName("AccountHeroMeta")
        self.hero_role_value.setAlignment(Qt.AlignCenter)
        self.hero_role_value.setMinimumWidth(150)

        self.hero_access_value = QLabel("LOCAL")
        self.hero_access_value.setObjectName("AccountHeroMeta")
        self.hero_access_value.setAlignment(Qt.AlignCenter)
        self.hero_access_value.setMinimumWidth(150)

        status.addWidget(active)
        status.addWidget(self.hero_role_value)
        status.addWidget(self.hero_access_value)
        layout.addLayout(status)

        return hero

    @staticmethod
    def _build_metric_card(
        icon: str,
        name: str,
        value: str,
        caption: str,
        tone: str,
    ):
        card = QFrame()
        card.setProperty("accountMetricCard", True)
        card.setMinimumHeight(82)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(13, 11, 13, 11)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setProperty("accountMetricIcon", True)
        icon_label.setProperty("accountTone", tone)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(34, 34)
        layout.addWidget(icon_label, 0, Qt.AlignTop)

        copy = QVBoxLayout()
        copy.setSpacing(2)

        name_label = QLabel(name)
        name_label.setProperty("accountMetricName", True)

        value_label = QLabel(value)
        value_label.setProperty("accountMetricValue", True)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        caption_label = QLabel(caption)
        caption_label.setProperty("accountMetricCaption", True)
        caption_label.setWordWrap(True)

        copy.addWidget(name_label)
        copy.addWidget(value_label)
        copy.addWidget(caption_label)
        layout.addLayout(copy, 1)

        return card, value_label, caption_label

    def _build_profile_card(self) -> QFrame:
        card = self._card(
            "Mon profil",
            "IDENTITÉ",
            "Informations visibles dans votre espace utilisateur.",
        )
        body = QHBoxLayout()
        body.setSpacing(18)

        avatar_panel = QFrame()
        avatar_panel.setObjectName("AvatarPanel")
        avatar_panel.setMinimumWidth(238)

        left = QVBoxLayout(avatar_panel)
        left.setContentsMargins(18, 16, 18, 16)
        left.setSpacing(8)
        left.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.avatar = QLabel()
        self.avatar.setObjectName("LargeAvatar")
        self.avatar.setFixedSize(174, 174)
        self.avatar.setAlignment(Qt.AlignCenter)
        left.addWidget(self.avatar, 0, Qt.AlignHCenter)

        upload = QPushButton("↑  Modifier ma photo")
        upload.setObjectName("PrimaryButton")
        upload.setFixedWidth(190)
        upload.clicked.connect(self._upload_photo)
        left.addWidget(upload, 0, Qt.AlignHCenter)

        remove = QPushButton("Supprimer la photo")
        remove.setObjectName("TextButton")
        remove.clicked.connect(self._remove_photo)
        left.addWidget(remove, 0, Qt.AlignHCenter)

        formats = QLabel("JPG / PNG  •  2 Mo maximum")
        formats.setObjectName("Hint")
        formats.setAlignment(Qt.AlignCenter)
        left.addWidget(formats)
        body.addWidget(avatar_panel)

        details = QVBoxLayout()
        details.setSpacing(0)

        self.name_value = self._detail_row(details, "●", "Nom et prénom")
        self.role_value = self._detail_row(details, "■", "Rôle", badge=True)
        self.status_value = self._detail_row(
            details,
            "✓",
            "Statut du compte",
            success=True,
        )
        self.email_value = self._detail_row(details, "✉", "Adresse e-mail")
        self.login_value = self._detail_row(details, "↗", "Dernière connexion")

        edit_identity = QPushButton("✎  Modifier mes informations")
        edit_identity.setObjectName("SecondaryButton")
        edit_identity.setMinimumWidth(205)
        edit_identity.clicked.connect(self._edit_identity)

        details.addSpacing(14)
        details.addWidget(edit_identity, 0, Qt.AlignRight)
        details.addStretch(1)

        body.addLayout(details, 1)
        card.layout().addLayout(body)

        return card

    def _build_commercial_organization_card(self) -> QFrame:
        card = self._card(
            "Organisation commerciale",
            "RATTACHEMENT",
            "Informations de rattachement de votre compte Cloud.",
        )

        body = QVBoxLayout()
        body.setSpacing(0)

        self.partner_name_value = self._detail_row(
            body,
            "◆",
            "Partenaire",
        )
        self.partner_responsible_value = self._detail_row(
            body,
            "●",
            "Responsable partenaire",
        )
        self.partner_attachment_value = self._detail_row(
            body,
            "↳",
            "Rattachement",
            badge=True,
        )

        card.layout().addLayout(body)
        return card

    def _build_security_card(self) -> QFrame:
        card = self._card(
            "Sécurité",
            "PROTECTION DU COMPTE",
            "Contrôlez les accès à votre espace Form@Prospect.",
        )

        panel = QFrame()
        panel.setObjectName("FeaturePanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        lock = QLabel("◉")
        lock.setObjectName("FeatureIcon")
        lock.setFixedSize(46, 46)
        lock.setAlignment(Qt.AlignCenter)
        row.addWidget(lock)

        text = QVBoxLayout()
        text.setSpacing(3)

        strong = QLabel("Changer mon mot de passe")
        strong.setObjectName("FeatureTitle")

        desc = QLabel(
            "Mettez à jour votre mot de passe régulièrement pour protéger votre compte."
        )
        desc.setObjectName("FeatureDescription")
        desc.setWordWrap(True)

        text.addWidget(strong)
        text.addWidget(desc)
        row.addLayout(text, 1)

        button = QPushButton("Changer le mot de passe  ›")
        button.setObjectName("SecondaryButton")
        button.clicked.connect(self._change_password)
        row.addWidget(button)

        card.layout().addWidget(panel)
        return card

    def _build_license_card(self) -> QFrame:
        card = self._card(
            "Licence",
            "ENVIRONNEMENT",
            "Informations de licence liées à votre espace utilisateur.",
        )

        panel = QFrame()
        panel.setObjectName("FeaturePanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        icon = QLabel("◆")
        icon.setObjectName("FeatureIcon")
        icon.setFixedSize(46, 46)
        icon.setAlignment(Qt.AlignCenter)
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(3)

        self.license_plan = QLabel("Licence Pro")
        self.license_plan.setObjectName("LicensePlan")

        self.license_status = QLabel("Statut : Active")
        self.license_status.setObjectName("LicenseStatus")

        text.addWidget(self.license_plan)
        text.addWidget(self.license_status)
        row.addLayout(text, 1)

        card.layout().addWidget(panel)
        return card

    @staticmethod
    def _card(
        title: str,
        eyebrow: str = "PARAMÈTRES",
        description: str = "",
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("AccountCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 16)
        layout.setSpacing(10)

        heading = QVBoxLayout()
        heading.setSpacing(2)

        overline = QLabel(eyebrow)
        overline.setObjectName("SectionEyebrow")

        label = QLabel(title)
        label.setObjectName("SectionTitle")

        heading.addWidget(overline)
        heading.addWidget(label)

        if description:
            desc = QLabel(description)
            desc.setObjectName("SectionDescription")
            desc.setWordWrap(True)
            heading.addWidget(desc)

        layout.addLayout(heading)
        return card

    def _detail_row(
        self,
        layout: QVBoxLayout,
        icon: str,
        label: str,
        *,
        badge=False,
        success=False,
    ) -> QLabel:
        frame = QFrame()
        frame.setObjectName("DetailRow")
        frame.setMinimumHeight(48)

        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 6, 6, 6)
        row.setSpacing(12)

        symbol = QLabel(icon)
        symbol.setObjectName("RowIcon")
        symbol.setFixedSize(30, 30)
        symbol.setAlignment(Qt.AlignCenter)

        name = QLabel(label)
        name.setObjectName("RowLabel")
        name.setFixedWidth(170)

        value = QLabel("—")
        value.setObjectName(
            "SuccessValue"
            if success
            else "BadgeValue"
            if badge
            else "RowValue"
        )
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        row.addWidget(symbol)
        row.addWidget(name)
        row.addWidget(value, 1)

        layout.addWidget(frame)
        return value

    def rafraichir(self):
        current_user = SessionState.user()
        user = (
            self.auth_service.get_user(current_user.id)
            if current_user
            else None
        )
        if not user:
            return

        user = _preserve_cloud_session_identity(
            user,
            current_user,
        )
        SessionState.login(user)

        self.avatar.setPixmap(
            circular_avatar(
                user.photo_path,
                user.display_name,
                170,
            )
        )
        self.name_value.setText(user.display_name)
        self.role_value.setText(user.role)
        self.status_value.setText("Actif  ✓")
        self.email_value.setText(user.email or "Non renseignée")

        self.hero_role_value.setText(user.display_name or "Utilisateur")
        self.metric_identity_value.setText(user.display_name or "Profil")
        self.metric_identity_caption.setText(user.email or "E-mail non renseigné")

        access_label = (
            "Cloud"
            if getattr(self.auth_service, "is_cloud", False)
            else "Local"
        )
        self.hero_access_value.setText(f"{access_label.upper()}  •  {user.role}")
        self.metric_access_value.setText(access_label)
        self.metric_access_caption.setText(
            "Synchronisé avec l'organisation"
            if access_label == "Cloud"
            else "Profil stocké sur cet appareil"
        )

        record = self.auth_service.get_user_record(user.id) or {}
        last_login = record.get("last_login")
        self.login_value.setText(self._format_datetime(last_login))

        self._refresh_commercial_organization(user)

        # La route Cloud /admin/license est réservée à la console administrateur.
        # Les profils non administrateurs utilisent CommercialAccountPage :
        # ne jamais bloquer le démarrage avec une permission admin.
        if getattr(self.auth_service, "is_cloud", False):
            self.license_plan.setText("Licence Form@Prospect Cloud")
            self.license_status.setText("Gérée par votre organisation")
            self.metric_license_value.setText("Cloud")
            self.metric_license_caption.setText("Gérée par votre organisation")
        else:
            licence = self.auth_service.license_info()
            plan = str(licence.get("plan", "Pro") or "Pro")
            status = str(licence.get("status", "Active") or "Active")
            self.license_plan.setText(f"Licence {plan}")
            self.license_status.setText(f"Statut : {status}")
            self.metric_license_value.setText(plan)
            self.metric_license_caption.setText(f"Statut : {status}")

    def _refresh_commercial_organization(self, user) -> None:
        """Affiche uniquement le rattachement du compte Cloud connecté."""
        self.organization_card.setVisible(False)

        if not getattr(self.auth_service, "is_cloud", False):
            return

        api = getattr(self.auth_service, "api", None)
        if api is None or not hasattr(api, "get_json"):
            return

        try:
            payload = api.get_json("/identity/commercial-organization")
        except Exception:
            # Carte informative : une indisponibilité réseau ne doit jamais
            # empêcher l'accès à Mon compte.
            return

        if not isinstance(payload, dict) or not payload.get("attached"):
            return

        partner_name = str(payload.get("partner_name") or "").strip()
        country = str(payload.get("country") or "").strip()
        responsible_name = str(
            payload.get("responsible_name") or ""
        ).strip()
        relationship = str(payload.get("relationship") or "").strip()

        if country and partner_name:
            partner_display = f"{partner_name} — {country}"
        else:
            partner_display = partner_name or country or "Partenaire"

        self.partner_name_value.setText(partner_display)

        if relationship == "partner_director":
            self.partner_responsible_value.setText(
                responsible_name or user.display_name or "Vous"
            )
            self.partner_attachment_value.setText("Responsable partenaire")
        else:
            self.partner_responsible_value.setText(
                responsible_name or "Non renseigné"
            )
            self.partner_attachment_value.setText("Équipe partenaire")

        self.organization_card.setVisible(True)

    @staticmethod
    def _format_datetime(value: str | None) -> str:
        if not value:
            return "Jamais"

        try:
            date = datetime.fromisoformat(value)
            return date.strftime("%d/%m/%Y à %H:%M")
        except ValueError:
            return value

    def _edit_identity(self):
        user = SessionState.user()
        if not user:
            return

        if not hasattr(self.auth_service, "update_profile_identity"):
            QMessageBox.information(
                self,
                "Profil",
                "La modification du nom et du prénom est disponible pour les comptes Cloud.",
            )
            return

        first_name, ok = QInputDialog.getText(
            self,
            "Modifier mon profil",
            "Prénom :",
            text=user.first_name or "",
        )
        if not ok:
            return

        last_name, ok = QInputDialog.getText(
            self,
            "Modifier mon profil",
            "Nom :",
            text=user.last_name or "",
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
                "Profil mis à jour",
                "Votre nom et votre prénom ont été enregistrés.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Modification impossible",
                str(exc),
            )

    def _upload_photo(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une photo de profil",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if not filename:
            return

        try:
            path = Path(filename)

            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError(
                    "La photo dépasse la taille maximale de 2 Mo."
                )

            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                raise ValueError(
                    "Le fichier sélectionné n'est pas une image valide."
                )

            user = SessionState.user()
            self.auth_service.update_profile_photo(
                user.id,
                path,
            )
            refreshed = self.auth_service.get_user(user.id)
            SessionState.login(
                _preserve_cloud_session_identity(
                    refreshed,
                    SessionState.user(),
                )
            )
            self.rafraichir()
            self.profile_updated.emit()

            NotificationManager.success(
                "Photo mise à jour",
                "Votre nouvelle photo de profil a été enregistrée.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Photo impossible",
                str(exc),
            )

    def _remove_photo(self):
        user = SessionState.user()
        if not user or not user.photo_path:
            return

        answer = QMessageBox.question(
            self,
            "Supprimer la photo",
            "Voulez-vous supprimer votre photo de profil ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer == QMessageBox.Yes:
            self.auth_service.remove_profile_photo(user.id)
            refreshed = self.auth_service.get_user(user.id)
            SessionState.login(
                _preserve_cloud_session_identity(
                    refreshed,
                    SessionState.user(),
                )
            )
            self.rafraichir()
            self.profile_updated.emit()

    def _change_password(self):
        user = SessionState.user()
        if not user:
            return

        current, ok = QInputDialog.getText(
            self,
            "Mot de passe actuel",
            "Saisissez votre mot de passe actuel :",
            echo=QLineEdit.Password,
        )
        if not ok:
            return

        new, ok = QInputDialog.getText(
            self,
            "Nouveau mot de passe",
            "Nouveau mot de passe (8 caractères minimum) :",
            echo=QLineEdit.Password,
        )
        if not ok:
            return

        confirm, ok = QInputDialog.getText(
            self,
            "Confirmation",
            "Confirmez le nouveau mot de passe :",
            echo=QLineEdit.Password,
        )
        if not ok:
            return

        if new != confirm:
            QMessageBox.warning(
                self,
                "Mot de passe",
                "Les deux mots de passe ne correspondent pas.",
            )
            return

        try:
            self.auth_service.change_password(
                user.id,
                current,
                new,
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
    def _style() -> str:
        palette = account_page_palette(get_theme_preference())
        return commercial_account_stylesheet(palette)
