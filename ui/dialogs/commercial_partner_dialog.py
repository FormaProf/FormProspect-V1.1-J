from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.premium_theme import MUTED, PRIMARY, TEXT


class CommercialPartnerDialog(QDialog):
    """Administration d'une structure commerciale étrangère et de son équipe."""

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)

        self.auth_service = auth_service
        self.users: list[dict] = []
        self.partners: list[dict] = []
        self.current_partner_id: str | None = None

        self.setWindowTitle("Partenaires commerciaux hors France")
        self.setMinimumSize(760, 560)
        self.resize(860, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.partner_scroll_area = QScrollArea()
        self.partner_scroll_area.setWidgetResizable(True)
        self.partner_scroll_area.setFrameShape(QFrame.NoFrame)
        self.partner_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll_content = QWidget()
        root = QVBoxLayout(scroll_content)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        self.partner_scroll_area.setWidget(scroll_content)
        outer.addWidget(self.partner_scroll_area)

        # --------------------------------------------------------------
        # Titre
        # --------------------------------------------------------------
        title = QLabel("Partenaires commerciaux hors France")
        title.setStyleSheet(
            f"color:{TEXT};font-size:23px;font-weight:900;"
        )
        root.addWidget(title)

        intro = QLabel(
            "Créez la structure partenaire, choisissez son dirigeant, "
            "rattachez les setters et définissez son barème de commission. "
            "La facturation partenaire par autoliquidation sera gérée "
            "dans le lot dédié à la facturation mensuelle."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color:{MUTED};font-size:12px;"
        )
        root.addWidget(intro)

        # --------------------------------------------------------------
        # Sélection du partenaire
        # --------------------------------------------------------------
        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)

        selector_row.addWidget(QLabel("Partenaire"))

        self.partner_combo = QComboBox()
        self.partner_combo.currentIndexChanged.connect(
            self._load_selected_partner
        )
        selector_row.addWidget(self.partner_combo, 1)

        new_button = QPushButton("＋ Nouveau")
        new_button.clicked.connect(self._new_partner)
        selector_row.addWidget(new_button)

        root.addLayout(selector_row)

        # --------------------------------------------------------------
        # Informations du partenaire
        # --------------------------------------------------------------
        details = QFrame()
        details.setStyleSheet(
            "QFrame {"
            "background:#FFFFFF;"
            "border:1px solid #DCE6F2;"
            "border-radius:14px;"
            "}"
            "QLineEdit,QComboBox,QDoubleSpinBox {"
            "min-height:34px;"
            "border:1px solid #CAD6E2;"
            "border-radius:8px;"
            "padding:0 10px;"
            "background:#FFFFFF;"
            "}"
        )

        form = QFormLayout(details)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self.legal_name = QLineEdit()
        self.country = QLineEdit("Cameroun")
        self.address = QLineEdit()
        self.postal_code = QLineEdit()
        self.city = QLineEdit()
        self.billing_email = QLineEdit()
        self.registration_number = QLineEdit()
        self.tax_id = QLineEdit()

        self.commission_rate_tier_1 = QDoubleSpinBox()
        self.commission_rate_tier_2 = QDoubleSpinBox()
        self.commission_rate_tier_3 = QDoubleSpinBox()

        for rate_field in (
            self.commission_rate_tier_1,
            self.commission_rate_tier_2,
            self.commission_rate_tier_3,
        ):
            rate_field.setRange(0.0, 100.0)
            rate_field.setDecimals(2)
            rate_field.setSingleStep(0.5)
            rate_field.setSuffix(" %")

        self.commission_rate_tier_1.setValue(10.0)
        self.commission_rate_tier_2.setValue(15.0)
        self.commission_rate_tier_3.setValue(20.0)

        self.active = QCheckBox("Partenaire actif")
        self.active.setChecked(True)

        form.addRow("Raison sociale *", self.legal_name)
        form.addRow("Pays *", self.country)
        form.addRow("Adresse", self.address)
        form.addRow("Code postal", self.postal_code)
        form.addRow("Ville", self.city)
        form.addRow("E-mail de facturation", self.billing_email)
        form.addRow(
            "N° d'immatriculation local",
            self.registration_number,
        )
        form.addRow("Identifiant fiscal", self.tax_id)
        form.addRow(
            "Commission tranche 1",
            self.commission_rate_tier_1,
        )
        form.addRow(
            "Commission tranche 2",
            self.commission_rate_tier_2,
        )
        form.addRow(
            "Commission tranche 3",
            self.commission_rate_tier_3,
        )
        form.addRow(
            "Régime préparé",
            QLabel("Autoliquidation / reverse charge"),
        )
        form.addRow("Statut", self.active)

        root.addWidget(details)

        # --------------------------------------------------------------
        # Équipe du partenaire
        # --------------------------------------------------------------
        team_frame = QFrame()
        team_frame.setStyleSheet(
            "QFrame {"
            "background:#F8FBFF;"
            "border:1px solid #D8E8F8;"
            "border-radius:14px;"
            "}"
            "QListWidget {"
            "background:#FFFFFF;"
            "border:1px solid #D8E1EA;"
            "border-radius:10px;"
            "padding:4px;"
            "}"
        )

        team_layout = QVBoxLayout(team_frame)
        team_layout.setContentsMargins(16, 14, 16, 14)
        team_layout.setSpacing(9)

        team_title = QLabel("Équipe du partenaire")
        team_title.setStyleSheet(
            f"color:{TEXT};font-size:17px;font-weight:900;"
        )
        team_layout.addWidget(team_title)

        director_row = QFormLayout()

        self.director_combo = QComboBox()
        director_row.addRow(
            "Dirigeant hors France",
            self.director_combo,
        )

        team_layout.addLayout(director_row)

        help_label = QLabel(
            "Cochez les commerciaux salariés du call center. "
            "Un commercial déjà rattaché à un Head of Sales ou à un autre "
            "partenaire ne peut pas être sélectionné."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            f"color:{MUTED};font-size:11px;"
        )
        team_layout.addWidget(help_label)

        self.commercials = QListWidget()
        self.commercials.setMinimumHeight(180)
        team_layout.addWidget(self.commercials)

        root.addWidget(team_frame, 1)

        # --------------------------------------------------------------
        # Statut / information
        # --------------------------------------------------------------
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            f"color:{MUTED};font-size:11px;"
        )
        root.addWidget(self.status)

        # --------------------------------------------------------------
        # Boutons
        # --------------------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Close
        )

        buttons.button(
            QDialogButtonBox.Save
        ).setText("Enregistrer le partenaire")

        buttons.button(
            QDialogButtonBox.Close
        ).setText("Fermer")

        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        root.addWidget(buttons)

        self._reload_data()

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    @staticmethod
    def _display_name(user: dict) -> str:
        name = " ".join(
            part
            for part in (
                str(user.get("first_name") or "").strip(),
                str(user.get("last_name") or "").strip(),
            )
            if part
        )

        return name or str(
            user.get("email") or "Utilisateur"
        )

    # ------------------------------------------------------------------
    # Chargement des données
    # ------------------------------------------------------------------
    def _reload_data(
        self,
        *,
        select_partner_id: str | None = None,
    ) -> None:
        try:
            self.users = self.auth_service.list_users()
            self.partners = (
                self.auth_service.list_commercial_partners()
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Chargement impossible",
                str(exc),
            )
            return

        self.partner_combo.blockSignals(True)
        self.partner_combo.clear()

        self.partner_combo.addItem(
            "Nouveau partenaire…",
            None,
        )

        for partner in self.partners:
            label = str(
                partner.get("legal_name")
                or "Partenaire"
            )

            if not partner.get("active", True):
                label += " — Inactif"

            self.partner_combo.addItem(
                label,
                str(partner.get("id") or ""),
            )

        self.partner_combo.blockSignals(False)

        if select_partner_id:
            for index in range(
                self.partner_combo.count()
            ):
                if (
                    self.partner_combo.itemData(index)
                    == select_partner_id
                ):
                    self.partner_combo.setCurrentIndex(
                        index
                    )
                    break
            else:
                self.partner_combo.setCurrentIndex(0)
        else:
            self.partner_combo.setCurrentIndex(0)

        self._load_selected_partner()

    # ------------------------------------------------------------------
    # Nouveau partenaire
    # ------------------------------------------------------------------
    def _new_partner(self) -> None:
        self.partner_combo.setCurrentIndex(0)
        self._clear_form()

    def _clear_form(self) -> None:
        self.current_partner_id = None

        self.legal_name.clear()
        self.country.setText("Cameroun")
        self.address.clear()
        self.postal_code.clear()
        self.city.clear()
        self.billing_email.clear()
        self.registration_number.clear()
        self.tax_id.clear()

        self.commission_rate_tier_1.setValue(10.0)
        self.commission_rate_tier_2.setValue(15.0)
        self.commission_rate_tier_3.setValue(20.0)

        self.active.setChecked(True)

        self._populate_team(None)

        self.status.setText(
            "Nouveau partenaire : renseignez la structure "
            "puis son équipe."
        )

    # ------------------------------------------------------------------
    # Chargement d'un partenaire existant
    # ------------------------------------------------------------------
    def _load_selected_partner(
        self,
        *_args,
    ) -> None:
        partner_id = self.partner_combo.currentData()

        if not partner_id:
            self._clear_form()
            return

        partner = next(
            (
                item
                for item in self.partners
                if str(item.get("id") or "")
                == str(partner_id)
            ),
            None,
        )

        if partner is None:
            self._clear_form()
            return

        self.current_partner_id = str(partner_id)

        self.legal_name.setText(
            str(partner.get("legal_name") or "")
        )
        self.country.setText(
            str(partner.get("country") or "")
        )
        self.address.setText(
            str(partner.get("address") or "")
        )
        self.postal_code.setText(
            str(partner.get("postal_code") or "")
        )
        self.city.setText(
            str(partner.get("city") or "")
        )
        self.billing_email.setText(
            str(partner.get("billing_email") or "")
        )
        self.registration_number.setText(
            str(
                partner.get(
                    "registration_number"
                )
                or ""
            )
        )
        self.tax_id.setText(
            str(partner.get("tax_id") or "")
        )

        self.commission_rate_tier_1.setValue(
            float(
                partner.get("commission_rate_tier_1")
                if partner.get("commission_rate_tier_1") is not None
                else 10.0
            )
        )
        self.commission_rate_tier_2.setValue(
            float(
                partner.get("commission_rate_tier_2")
                if partner.get("commission_rate_tier_2") is not None
                else 15.0
            )
        )
        self.commission_rate_tier_3.setValue(
            float(
                partner.get("commission_rate_tier_3")
                if partner.get("commission_rate_tier_3") is not None
                else 20.0
            )
        )

        self.active.setChecked(
            bool(partner.get("active", True))
        )

        self._populate_team(partner)

        count = int(
            partner.get("commercial_count") or 0
        )

        self.status.setText(
            f"{count} commercial"
            + ("aux" if count != 1 else "")
            + " rattaché"
            + ("s" if count != 1 else "")
            + "."
        )

    # ------------------------------------------------------------------
    # Équipe
    # ------------------------------------------------------------------
    def _populate_team(
        self,
        partner: dict | None,
    ) -> None:
        current_partner_id = (
            str(partner.get("id") or "")
            if partner
            else ""
        )

        current_director_id = (
            str(
                partner.get(
                    "director_user_id"
                )
                or ""
            )
            if partner
            else ""
        )

        selected_commercials = (
            {
                str(value)
                for value in (
                    partner.get(
                        "commercial_user_ids"
                    )
                    or []
                )
            }
            if partner
            else set()
        )

        # --------------------------------------------------------------
        # Dirigeants hors France
        # --------------------------------------------------------------
        self.director_combo.clear()

        self.director_combo.addItem(
            "— Sélectionner —",
            None,
        )

        for user in self.users:
            if (
                user.get("active")
                and user.get("role")
                == "Dirigeant hors France"
            ):
                partner_id = str(
                    user.get(
                        "commercial_partner_id"
                    )
                    or ""
                )

                if (
                    partner_id
                    and partner_id
                    != current_partner_id
                ):
                    continue

                label = (
                    f"{self._display_name(user)}"
                    f" — {user.get('email') or ''}"
                )

                self.director_combo.addItem(
                    label,
                    str(
                        user.get("user_id")
                        or user.get(
                            "cloud_user_id"
                        )
                        or ""
                    ),
                )

        if current_director_id:
            for index in range(
                self.director_combo.count()
            ):
                if (
                    self.director_combo.itemData(
                        index
                    )
                    == current_director_id
                ):
                    self.director_combo.setCurrentIndex(
                        index
                    )
                    break

        # --------------------------------------------------------------
        # Commerciaux
        # --------------------------------------------------------------
        self.commercials.clear()

        for user in self.users:
            if (
                not user.get("active")
                or user.get("role")
                != "Commercial"
            ):
                continue

            user_id = str(
                user.get("user_id")
                or user.get("cloud_user_id")
                or ""
            )

            # list_users expose maintenant normalement user_id.
            # On évite d'utiliser l'id du membership comme identifiant
            # utilisateur pour l'affectation d'équipe.
            if not user_id:
                continue

            partner_id = str(
                user.get(
                    "commercial_partner_id"
                )
                or ""
            )

            manager_id = str(
                user.get("manager_user_id")
                or ""
            )

            unavailable = bool(
                manager_id
                or (
                    partner_id
                    and partner_id
                    != current_partner_id
                )
            )

            suffix = ""

            if manager_id:
                suffix = (
                    " — rattaché à un Head of Sales"
                )

            elif (
                partner_id
                and partner_id
                != current_partner_id
            ):
                suffix = " — autre partenaire"

            item = QListWidgetItem(
                f"{self._display_name(user)}"
                f" — {user.get('email') or ''}"
                f"{suffix}"
            )

            item.setData(
                Qt.UserRole,
                user_id,
            )

            item.setFlags(
                item.flags()
                | Qt.ItemIsUserCheckable
            )

            item.setCheckState(
                Qt.Checked
                if user_id
                in selected_commercials
                else Qt.Unchecked
            )

            if unavailable:
                item.setFlags(
                    item.flags()
                    & ~Qt.ItemIsEnabled
                )

            self.commercials.addItem(item)

    # ------------------------------------------------------------------
    # Payload partenaire
    # ------------------------------------------------------------------
    def _payload(self) -> dict:
        return {
            "legal_name": (
                self.legal_name.text().strip()
            ),
            "country": (
                self.country.text().strip()
            ),
            "address": (
                self.address.text().strip()
            ),
            "postal_code": (
                self.postal_code.text().strip()
            ),
            "city": (
                self.city.text().strip()
            ),
            "billing_email": (
                self.billing_email.text()
                .strip()
                .lower()
            ),
            "registration_number": (
                self.registration_number.text()
                .strip()
            ),
            "tax_id": (
                self.tax_id.text().strip()
            ),
            "commission_rate_tier_1": float(
                self.commission_rate_tier_1.value()
            ),
            "commission_rate_tier_2": float(
                self.commission_rate_tier_2.value()
            ),
            "commission_rate_tier_3": float(
                self.commission_rate_tier_3.value()
            ),
            "tax_regime": "reverse_charge",
        }

    def _selected_commercial_ids(
        self,
    ) -> list[str]:
        result: list[str] = []

        for index in range(
            self.commercials.count()
        ):
            item = self.commercials.item(
                index
            )

            if (
                item.checkState()
                == Qt.Checked
            ):
                result.append(
                    str(
                        item.data(
                            Qt.UserRole
                        )
                        or ""
                    )
                )

        return [
            value
            for value in result
            if value
        ]

    # ------------------------------------------------------------------
    # Enregistrement
    # ------------------------------------------------------------------
    def _save(self) -> None:
        payload = self._payload()

        if len(payload["legal_name"]) < 2:
            QMessageBox.warning(
                self,
                "Raison sociale",
                "Renseignez la raison sociale "
                "du partenaire.",
            )
            return

        if len(payload["country"]) < 2:
            QMessageBox.warning(
                self,
                "Pays",
                "Renseignez le pays du partenaire.",
            )
            return

        if (
            payload["billing_email"]
            and "@"
            not in payload["billing_email"]
        ):
            QMessageBox.warning(
                self,
                "E-mail",
                "L'adresse de facturation "
                "n'est pas valide.",
            )
            return

        try:
            # ----------------------------------------------------------
            # Création ou mise à jour du partenaire
            # ----------------------------------------------------------
            if self.current_partner_id:
                update_payload = {
                    **payload,
                    "active": (
                        self.active.isChecked()
                    ),
                }

                partner = (
                    self.auth_service
                    .update_commercial_partner(
                        self.current_partner_id,
                        update_payload,
                    )
                )

            else:
                partner = (
                    self.auth_service
                    .create_commercial_partner(
                        payload
                    )
                )

                self.current_partner_id = str(
                    partner.get("id") or ""
                )

            # ----------------------------------------------------------
            # Sécurité :
            # l'identifiant du partenaire doit impérativement exister
            # avant de rattacher son dirigeant ou ses commerciaux.
            # ----------------------------------------------------------
            if not self.current_partner_id:
                raise ValueError(
                    "Impossible de rattacher "
                    "l'équipe : identifiant du "
                    "partenaire indisponible."
                )

            director_user_id = (
                self.director_combo.currentData()
            )

            commercial_ids = (
                self._selected_commercial_ids()
            )

            # ----------------------------------------------------------
            # Affectation de l'équipe
            # ----------------------------------------------------------
            if (
                self.active.isChecked()
                and (
                    director_user_id
                    or commercial_ids
                )
            ):
                if not director_user_id:
                    raise ValueError(
                        "Sélectionnez le Dirigeant "
                        "hors France avant de "
                        "rattacher des commerciaux."
                    )

                partner = (
                    self.auth_service
                    .set_commercial_partner_team(
                        self.current_partner_id,
                        director_user_id=str(
                            director_user_id
                        ),
                        commercial_user_ids=(
                            commercial_ids
                        ),
                    )
                )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                str(exc),
            )
            return

        partner_id = str(
            partner.get("id")
            or self.current_partner_id
            or ""
        )

        self._reload_data(
            select_partner_id=partner_id
        )

        QMessageBox.information(
            self,
            "Partenaire enregistré",
            "La structure partenaire et son "
            "équipe ont été enregistrées "
            "dans le Cloud.",
        )