from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.premium_theme import (
    BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT,
)
from core.session import SessionState
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.dialogs.commercial_profile_dialog import CloudCommercialProfileDialog


class CommercialProfilesPage(QWidget):
    """Annuaire Cloud des setters, closers et commerciaux."""

    STATUS_LABELS = {
        "subcontractor": "Sous-traitant",
        "independent": "Indépendant",
        "employee": "Salarié",
    }

    ROLE_LABELS = {
        "setter": "Setter",
        "closer": "Closer",
        "setter_closer": "Setter / Closer",
        "manager": "Manager commercial",
        "other": "Autre",
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
        title = QLabel("Commerciaux")
        title.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:900;")
        subtitle = QLabel(
            "Référencez vos setters, closers et managers commerciaux avec leurs "
            "informations administratives et contractuelles."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Ajouter un commercial")
        self.add_button.setStyleSheet(PRIMARY_BUTTON)
        self.add_button.clicked.connect(self._add)

        self.edit_button = QPushButton("Modifier")
        self.edit_button.setStyleSheet(SECONDARY_BUTTON)
        self.edit_button.clicked.connect(self._edit)

        self.toggle_button = QPushButton("Activer / désactiver")
        self.toggle_button.setStyleSheet(SECONDARY_BUTTON)
        self.toggle_button.clicked.connect(self._toggle)

        refresh = QPushButton("Actualiser")
        refresh.setStyleSheet(SECONDARY_BUTTON)
        refresh.clicked.connect(self.rafraichir)

        header.addWidget(self.add_button)
        header.addWidget(self.edit_button)
        header.addWidget(self.toggle_button)
        header.addWidget(refresh)
        root.addLayout(header)

        info = QFrame()
        info.setStyleSheet(
            f"background:{CARD}; border:1px solid {BORDER}; border-radius:14px;"
        )
        info_layout = QHBoxLayout(info)
        info_layout.setContentsMargins(16, 12, 16, 12)
        self.summary = QLabel("0 commercial")
        self.summary.setStyleSheet(f"color:{NAVY}; font-weight:800;")
        note = QLabel(
            "Les fiches commerciales sont distinctes des comptes de connexion "
            "Form@Prospect."
        )
        note.setStyleSheet(f"color:{MUTED};")
        info_layout.addWidget(self.summary)
        info_layout.addStretch()
        info_layout.addWidget(note)
        root.addWidget(info)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Commercial", "Fonction", "Statut", "E-mail / téléphone",
                "SIRET", "Spécialités", "Diplômes / certifications",
                "Contrat", "État",
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
            self.status_label.setText("Cette section est réservée à l'administrateur.")
            return

        if not CloudRuntime.is_active():
            self.rows = []
            self.table.setRowCount(0)
            self.status_label.setText(
                "Connectez-vous à Form@Prospect Cloud pour gérer les commerciaux."
            )
            return

        try:
            self.rows = CloudRuntime.api().list_cloud_commercial_profiles(
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

        for row_index, profile in enumerate(self.rows):
            active = bool(profile.get("active"))
            active_count += int(active)
            contact_parts = [
                str(profile.get("email") or "").strip(),
                str(profile.get("phone") or "").strip(),
            ]
            qualifications = " — ".join(
                part for part in (
                    str(profile.get("diplomas") or "").strip(),
                    str(profile.get("certifications") or "").strip(),
                ) if part
            )
            values = [
                profile.get("full_name") or "",
                self.ROLE_LABELS.get(
                    str(profile.get("commercial_role") or ""),
                    str(profile.get("commercial_role") or ""),
                ),
                self.STATUS_LABELS.get(
                    str(profile.get("professional_status") or ""),
                    str(profile.get("professional_status") or ""),
                ),
                "\n".join(part for part in contact_parts if part) or "—",
                profile.get("siret") or "—",
                profile.get("specialties") or "—",
                qualifications or "—",
                "Présent" if profile.get("contract_present") else "Manquant",
                "Actif" if active else "Inactif",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignVCenter |
                    (Qt.AlignCenter if column in (7, 8) else Qt.AlignLeft)
                )
                self.table.setItem(row_index, column, item)

        self.summary.setText(
            f"{len(self.rows)} commercial(aux) — {active_count} actif(s)"
        )
        self.status_label.setText(
            "Double-cliquez sur une ligne pour consulter ou modifier la fiche."
        )
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(True)
        self.toggle_button.setEnabled(True)

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            QMessageBox.information(
                self, "Sélection", "Sélectionnez d'abord un commercial."
            )
            return None
        return self.rows[row]

    def _add(self) -> None:
        if self._is_admin() and CloudRuntime.is_active():
            if CloudCommercialProfileDialog(CloudRuntime.api(), self).exec():
                self.rafraichir()

    def _edit(self, *_args) -> None:
        profile = self._selected()
        if not profile:
            return
        if CloudCommercialProfileDialog(
            CloudRuntime.api(), self, profile=profile
        ).exec():
            self.rafraichir()

    def _toggle(self) -> None:
        profile = self._selected()
        if not profile:
            return
        active = bool(profile.get("active"))
        action = "désactiver" if active else "réactiver"
        if QMessageBox.question(
            self,
            "Modifier le statut",
            f"Voulez-vous {action} « {profile.get('full_name', '')} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        try:
            CloudRuntime.api().update_cloud_commercial_profile(
                str(profile.get("id") or ""),
                {"active": not active},
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Modification impossible", str(exc))
            return
        self.rafraichir()
