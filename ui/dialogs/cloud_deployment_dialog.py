from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.constants import PRIMARY_COLOR
from core.theme import (
    BORDER_COLOR,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from models.cloud_user import CloudUser
from models.deployment_options import DeploymentOptions


class CloudDeploymentDialog(QDialog):
    """
    Fenêtre affichée avant le déploiement d'un projet
    dans Form@Prospect Cloud.
    """

    UNASSIGNED_LABEL = "Non affecté pour le moment"

    def __init__(
        self,
        project_name: str,
        users: Iterable[CloudUser],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._project_name = (
            project_name.strip()
            if project_name.strip()
            else "Projet sans nom"
        )

        self._users = [
            user
            for user in users
            if user.is_assignable_to_project
        ]

        self.setWindowTitle("Déployer le projet")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.resize(560, 500)

        self._build_ui()
        self._populate_users()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("Déployer dans Form@Prospect Cloud")
        title.setStyleSheet(
            f"""
            font-size: 22px;
            font-weight: 900;
            color: {TEXT_PRIMARY};
            """
        )

        subtitle = QLabel(
            "Complétez les informations du projet avant "
            "sa création dans le Cloud."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"""
            font-size: 13px;
            color: {TEXT_SECONDARY};
            """
        )

        root.addWidget(title)
        root.addWidget(subtitle)

        project_card = QFrame()
        project_card.setObjectName("ProjectCard")
        project_card.setStyleSheet(
            f"""
            QFrame#ProjectCard {{
                background: #F8FAFC;
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
            """
        )

        project_layout = QVBoxLayout(project_card)
        project_layout.setContentsMargins(16, 13, 16, 13)
        project_layout.setSpacing(4)

        project_caption = QLabel("PROJET")
        project_caption.setStyleSheet(
            f"""
            font-size: 10px;
            font-weight: 800;
            color: {TEXT_SECONDARY};
            """
        )

        project_value = QLabel(self._project_name)
        project_value.setWordWrap(True)
        project_value.setStyleSheet(
            f"""
            font-size: 16px;
            font-weight: 900;
            color: {TEXT_PRIMARY};
            """
        )

        project_layout.addWidget(project_caption)
        project_layout.addWidget(project_value)

        root.addWidget(project_card)

        description_label = QLabel("Description")
        description_label.setStyleSheet(
            f"""
            font-size: 13px;
            font-weight: 800;
            color: {TEXT_PRIMARY};
            """
        )

        self.description_input = QTextEdit()
        self.description_input.setAcceptRichText(False)
        self.description_input.setPlaceholderText(
            "Exemple : campagne nationale de prospection "
            "et suivi commercial."
        )
        self.description_input.setMinimumHeight(110)
        self.description_input.setStyleSheet(
            self._field_style()
        )

        root.addWidget(description_label)
        root.addWidget(self.description_input)

        assigned_label = QLabel("Affecter le projet à")
        assigned_label.setStyleSheet(
            f"""
            font-size: 13px;
            font-weight: 800;
            color: {TEXT_PRIMARY};
            """
        )

        self.user_combo = QComboBox()
        self.user_combo.setMinimumHeight(42)
        self.user_combo.setStyleSheet(
            self._field_style()
        )

        root.addWidget(assigned_label)
        root.addWidget(self.user_combo)

        self.assignment_help = QLabel()
        self.assignment_help.setWordWrap(True)
        self.assignment_help.setStyleSheet(
            f"""
            font-size: 11px;
            color: {TEXT_SECONDARY};
            """
        )

        root.addWidget(self.assignment_help)
        root.addStretch()

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()

        cancel_button = QPushButton("Annuler")
        cancel_button.setMinimumSize(110, 42)
        cancel_button.setStyleSheet(
            self._secondary_button_style()
        )
        cancel_button.clicked.connect(self.reject)

        deploy_button = QPushButton("☁ Déployer")
        deploy_button.setMinimumSize(135, 42)
        deploy_button.setDefault(True)
        deploy_button.setStyleSheet(
            self._primary_button_style()
        )
        deploy_button.clicked.connect(
            self._validate_and_accept
        )

        buttons.addWidget(cancel_button)
        buttons.addWidget(deploy_button)

        root.addLayout(buttons)

    def _populate_users(self) -> None:
        self.user_combo.clear()

        self.user_combo.addItem(
            self.UNASSIGNED_LABEL,
            None,
        )

        sorted_users = sorted(
            self._users,
            key=lambda user: user.display_name.casefold(),
        )

        for user in sorted_users:
            label = (
                f"{user.display_name} — "
                f"{user.role_label}"
            )

            self.user_combo.addItem(
                label,
                user.id,
            )

        if self._users:
            self.assignment_help.setText(
                "Seuls les utilisateurs actifs pouvant recevoir "
                "un projet sont affichés."
            )
        else:
            self.assignment_help.setText(
                "Aucun utilisateur actif affectable n'a été trouvé. "
                "Le projet peut néanmoins être déployé "
                "sans affectation."
            )

    def options(self) -> DeploymentOptions:
        """
        Retourne les options choisies dans la fenêtre.
        """

        assigned_to = self.user_combo.currentData()

        return DeploymentOptions(
            description=(
                self.description_input
                .toPlainText()
            ),
            assigned_to=(
                str(assigned_to)
                if assigned_to
                else None
            ),
        )

    def _validate_and_accept(self) -> None:
        description = (
            self.description_input
            .toPlainText()
            .strip()
        )

        if len(description) > 2000:
            QMessageBox.warning(
                self,
                "Description trop longue",
                (
                    "La description ne peut pas "
                    "dépasser 2 000 caractères."
                ),
            )
            return

        self.accept()

    @staticmethod
    def _field_style() -> str:
        return f"""
            QTextEdit,
            QComboBox {{
                background: white;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 9px 11px;
                font-size: 13px;
            }}

            QTextEdit:focus,
            QComboBox:focus {{
                border: 2px solid {PRIMARY_COLOR};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
        """

    @staticmethod
    def _primary_button_style() -> str:
        return f"""
            QPushButton {{
                background: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 800;
            }}

            QPushButton:hover {{
                background: #256DB4;
            }}

            QPushButton:pressed {{
                background: #1D4F86;
            }}
        """

    @staticmethod
    def _secondary_button_style() -> str:
        return f"""
            QPushButton {{
                background: white;
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 10px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 800;
            }}

            QPushButton:hover {{
                background: #F3F4F6;
            }}

            QPushButton:pressed {{
                background: #E5E7EB;
            }}
        """