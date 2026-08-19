from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import (
    BORDER,
    CARD,
    MUTED,
    NAVY,
    PAGE_BG,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.dialogs.trainer_dialog import CloudTrainerDialog


def _user_value(user, *names, default=""):
    for name in names:
        if isinstance(user, dict) and name in user:
            value = user.get(name)
            if value not in (None, ""):
                return value
        value = getattr(user, name, None)
        if value not in (None, ""):
            return value
    return default


def _normalized_role(user) -> str:
    value = _user_value(user, "role", default="")
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _user_id(user) -> str:
    return str(_user_value(user, "user_id", "id", default="") or "").strip()


def _user_label(user) -> str:
    display = str(_user_value(user, "display_name", "full_name", default="") or "").strip()
    first = str(_user_value(user, "first_name", default="") or "").strip()
    last = str(_user_value(user, "last_name", default="") or "").strip()
    email = str(_user_value(user, "email", default="") or "").strip()
    name = display or " ".join(part for part in (first, last) if part).strip()
    if name and email:
        return f"{name} — {email}"
    return name or email or "Compte Formateur"


class TrainerAccountLinkDialog(QDialog):
    """Rattachement administrateur d'une fiche Trainer à un compte Cloud."""

    def __init__(self, api, trainer: dict, parent=None):
        super().__init__(parent)
        self.api = api
        self.trainer = dict(trainer or {})
        self.saved_trainer: dict | None = None
        self.users = []
        self.setWindowTitle("Rattacher un compte Formateur")
        self.resize(620, 260)
        self._build_ui()
        self._load_users()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel("Compte Cloud du formateur")
        title.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:900;")
        root.addWidget(title)

        name = str(self.trainer.get("full_name") or "ce formateur")
        note = QLabel(
            f"Choisissez le compte Cloud ayant le rôle Formateur à rattacher à « {name} ». "
            "Le rattachement est explicite : aucune correspondance automatique par e-mail."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED};")
        root.addWidget(note)

        self.combo = QComboBox()
        self.combo.setMinimumHeight(38)
        root.addWidget(self.combo)

        current = str(self.trainer.get("user_id") or "").strip()
        self.current_label = QLabel(
            "Compte actuellement rattaché : "
            + ("oui" if current else "aucun")
        )
        self.current_label.setStyleSheet(f"color:{MUTED};")
        root.addWidget(self.current_label)

        actions = QHBoxLayout()
        self.unlink_button = QPushButton("Délier le compte")
        self.unlink_button.setStyleSheet(SECONDARY_BUTTON)
        self.unlink_button.setEnabled(bool(current))
        self.unlink_button.clicked.connect(self._unlink)

        cancel = QPushButton("Annuler")
        cancel.setStyleSheet(SECONDARY_BUTTON)
        cancel.clicked.connect(self.reject)

        save = QPushButton("Rattacher ce compte")
        save.setStyleSheet(PRIMARY_BUTTON)
        save.clicked.connect(self._save)

        actions.addWidget(self.unlink_button)
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

    def _load_users(self) -> None:
        try:
            all_users = self.api.list_users(active_only=True)
        except CloudAPIError as exc:
            QMessageBox.critical(
                self,
                "Comptes indisponibles",
                str(exc),
            )
            self.reject()
            return

        self.users = [
            user
            for user in all_users
            if _normalized_role(user) in {"trainer", "formateur"}
            and _user_id(user)
        ]

        self.combo.clear()
        if not self.users:
            self.combo.addItem("Aucun compte actif avec le rôle Formateur", "")
            self.combo.setEnabled(False)
            return

        current = str(self.trainer.get("user_id") or "").strip()
        selected_index = 0
        for index, user in enumerate(self.users):
            uid = _user_id(user)
            self.combo.addItem(_user_label(user), uid)
            if current and uid == current:
                selected_index = index
        self.combo.setCurrentIndex(selected_index)

    def _save(self) -> None:
        user_id = str(self.combo.currentData() or "").strip()
        if not user_id:
            QMessageBox.warning(
                self,
                "Compte requis",
                "Aucun compte Formateur actif n'est disponible.",
            )
            return
        try:
            self.saved_trainer = self.api.link_cloud_trainer_user(
                str(self.trainer.get("id") or ""),
                user_id,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Rattachement impossible", str(exc))
            return

        QMessageBox.information(
            self,
            "Compte rattaché",
            "Le compte Cloud a été rattaché à la fiche formateur.",
        )
        self.accept()

    def _unlink(self) -> None:
        if QMessageBox.question(
            self,
            "Délier le compte",
            "Voulez-vous retirer le rattachement entre ce compte Cloud et la fiche formateur ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            self.saved_trainer = self.api.link_cloud_trainer_user(
                str(self.trainer.get("id") or ""),
                None,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Déliaison impossible", str(exc))
            return
        QMessageBox.information(
            self,
            "Compte délié",
            "La fiche formateur n'est plus rattachée à un compte Cloud.",
        )
        self.accept()


class TrainersPage(QWidget):
    """Annuaire Cloud des formateurs, réservé à l'administration."""

    STATUS_LABELS = {
        "subcontractor": "Sous-traitant",
        "independent": "Indépendant",
        "employee": "Salarié",
    }

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 30)
        root.setSpacing(16)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Formateurs")
        title.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:900;")
        subtitle = QLabel(
            "Gérez l'annuaire des intervenants, leurs comptes Cloud et les "
            "informations nécessaires aux sessions, aux documents et au suivi Qualiopi."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Ajouter un formateur")
        self.add_button.setStyleSheet(PRIMARY_BUTTON)
        self.add_button.clicked.connect(self._add)

        self.edit_button = QPushButton("Modifier")
        self.edit_button.setStyleSheet(SECONDARY_BUTTON)
        self.edit_button.clicked.connect(self._edit)

        self.link_button = QPushButton("Rattacher un compte")
        self.link_button.setStyleSheet(SECONDARY_BUTTON)
        self.link_button.clicked.connect(self._link_account)

        self.toggle_button = QPushButton("Activer / désactiver")
        self.toggle_button.setStyleSheet(SECONDARY_BUTTON)
        self.toggle_button.clicked.connect(self._toggle)

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)

        header.addWidget(self.add_button)
        header.addWidget(self.edit_button)
        header.addWidget(self.link_button)
        header.addWidget(self.toggle_button)
        header.addWidget(refresh)
        root.addLayout(header)

        info = QFrame()
        info.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)
        self.summary = QLabel("0 formateur")
        self.summary.setStyleSheet(f"color:{NAVY}; font-weight:800;")
        note = QLabel(
            "Le compte Cloud donne ensuite accès au futur espace personnel "
            "« Mon profil / Mes formations » du formateur."
        )
        note.setStyleSheet(f"color:{MUTED};")
        info_layout.addWidget(self.summary)
        info_layout.addStretch()
        info_layout.addWidget(note)
        root.addWidget(info)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Formateur",
                "Statut",
                "E-mail / téléphone",
                "SIRET",
                "Spécialités",
                "Diplômes / certifications",
                "Contrat",
                "Compte Cloud",
                "État",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            f"QTableWidget{{background:white; alternate-background-color:#F8FAFC; "
            f"color:{TEXT}; border:1px solid {BORDER}; border-radius:10px; "
            f"gridline-color:{BORDER};}}"
            f"QHeaderView::section{{background:#F8FAFC; color:{MUTED}; border:none; "
            f"border-bottom:1px solid {BORDER}; padding:9px; font-weight:800;}}"
        )
        self.table.doubleClicked.connect(self._edit)
        root.addWidget(self.table, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color:{MUTED};")
        root.addWidget(self.status_label)

    @staticmethod
    def _is_admin() -> bool:
        return SessionState.has_role("Administrateur")

    def rafraichir(self) -> None:
        if not self._is_admin():
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(
                "Cette section est réservée à l'administrateur."
            )
            self.add_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.link_button.setEnabled(False)
            self.toggle_button.setEnabled(False)
            return

        if not CloudRuntime.is_active():
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(
                "Connectez-vous à Form@Prospect Cloud pour gérer les formateurs."
            )
            return

        try:
            self.rows = CloudRuntime.api().list_cloud_trainers(
                include_inactive=True
            )
        except CloudAPIError as exc:
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(f"⛔ {exc}")
            self.status_label.setStyleSheet("color:#B42318;")
            return

        self.status_label.setStyleSheet(f"color:{MUTED};")
        self.table.setRowCount(len(self.rows))
        active_count = 0
        linked_count = 0

        for row_index, trainer in enumerate(self.rows):
            active = bool(trainer.get("active"))
            linked = bool(str(trainer.get("user_id") or "").strip())
            active_count += int(active)
            linked_count += int(linked)

            contact_parts = [
                str(trainer.get("email") or "").strip(),
                str(trainer.get("phone") or "").strip(),
            ]
            qualifications = " — ".join(
                part
                for part in (
                    str(trainer.get("diplomas") or "").strip(),
                    str(trainer.get("certifications") or "").strip(),
                )
                if part
            )
            values = [
                trainer.get("full_name") or "",
                self.STATUS_LABELS.get(
                    str(trainer.get("professional_status") or ""),
                    str(trainer.get("professional_status") or ""),
                ),
                "\n".join(part for part in contact_parts if part) or "—",
                trainer.get("siret") or "—",
                trainer.get("specialties") or "—",
                qualifications or "—",
                "Présent" if trainer.get("contract_present") else "Manquant",
                "Rattaché" if linked else "Non rattaché",
                "Actif" if active else "Inactif",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignVCenter
                    | (
                        Qt.AlignCenter
                        if column in (6, 7, 8)
                        else Qt.AlignLeft
                    )
                )
                self.table.setItem(row_index, column, item)

        self.summary.setText(
            f"{len(self.rows)} formateur(s) — {active_count} actif(s) — "
            f"{linked_count} compte(s) rattaché(s)"
        )
        self.status_label.setText(
            "Sélectionnez une fiche puis « Rattacher un compte ». "
            "Seuls les comptes actifs ayant le rôle Formateur sont proposés."
        )
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(True)
        self.link_button.setEnabled(True)
        self.toggle_button.setEnabled(True)

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(
                self,
                "Sélection",
                "Sélectionnez d'abord un formateur.",
            )
            return None
        return self.rows[row]

    def _add(self) -> None:
        if not self._is_admin() or not CloudRuntime.is_active():
            return
        if CloudTrainerDialog(CloudRuntime.api(), self).exec():
            self.rafraichir()

    def _edit(self, *_args) -> None:
        trainer = self._selected()
        if not trainer:
            return
        if CloudTrainerDialog(
            CloudRuntime.api(),
            self,
            trainer=trainer,
        ).exec():
            self.rafraichir()

    def _link_account(self) -> None:
        trainer = self._selected()
        if not trainer or not self._is_admin() or not CloudRuntime.is_active():
            return
        if TrainerAccountLinkDialog(
            CloudRuntime.api(),
            trainer,
            self,
        ).exec():
            self.rafraichir()

    def _toggle(self) -> None:
        trainer = self._selected()
        if not trainer:
            return
        active = bool(trainer.get("active"))
        action = "désactiver" if active else "réactiver"
        if QMessageBox.question(
            self,
            "Modifier le statut",
            f"Voulez-vous {action} « {trainer.get('full_name', '')} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            CloudRuntime.api().update_cloud_trainer(
                str(trainer.get("id") or ""),
                {"active": not active},
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))
            return
        self.rafraichir()
