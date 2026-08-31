from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from services.cloud_api_client import CloudAPIError


_FIELD_STYLE = (
    "QLineEdit{background:#FFFFFF;color:#172033;border:1px solid #DCE5EF;"
    "border-radius:10px;padding:0 10px;min-height:38px;font-size:11px;font-weight:700;}"
    "QLineEdit:focus{border:2px solid #338CE4;}"
)


def _normalize_company_name(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


class LearnerEditDialog(QDialog):
    """Création / modification minimale d'un apprenant Cloud."""

    def __init__(self, api, parent=None, *, learner: dict | None = None, company_name: str = ""):
        super().__init__(parent)
        self.api = api
        self.learner = dict(learner or {})
        self.saved_learner: dict | None = None
        self.setWindowTitle("Apprenant")
        self.resize(520, 420)
        self.setStyleSheet("QDialog{background:#F5F8FC;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        title = QLabel("Modifier l'apprenant" if self.learner else "Nouvel apprenant")
        title.setStyleSheet("color:#0B1220;font-size:20px;font-weight:900;")
        root.addWidget(title)

        subtitle = QLabel(
            "Renseignez uniquement les informations utiles à l'organisation de la formation."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#6B7A90;font-size:10px;")
        root.addWidget(subtitle)

        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.first_name = QLineEdit(str(self.learner.get("first_name") or ""))
        self.last_name = QLineEdit(str(self.learner.get("last_name") or ""))
        self.email = QLineEdit(str(self.learner.get("email") or ""))
        self.phone = QLineEdit(str(self.learner.get("phone") or ""))
        self.job_title = QLineEdit(str(self.learner.get("job_title") or ""))
        self.company_name = QLineEdit(
            str(self.learner.get("company_name") or company_name or "")
        )
        for widget in (
            self.first_name,
            self.last_name,
            self.email,
            self.phone,
            self.job_title,
            self.company_name,
        ):
            widget.setStyleSheet(_FIELD_STYLE)

        form.addRow("Prénom *", self.first_name)
        form.addRow("Nom *", self.last_name)
        form.addRow("E-mail", self.email)
        form.addRow("Téléphone", self.phone)
        form.addRow("Fonction / poste", self.job_title)
        form.addRow("Entreprise", self.company_name)
        root.addWidget(form_host)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setMinimumHeight(38)
        cancel.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 14px;font-weight:850;}"
        )
        cancel.clicked.connect(self.reject)
        save = QPushButton("Enregistrer")
        save.setMinimumHeight(38)
        save.setStyleSheet(
            "QPushButton{background:#338CE4;color:#FFFFFF;border:none;border-radius:10px;"
            "padding:0 16px;font-weight:900;}QPushButton:hover{background:#287FD4;}"
        )
        save.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

    def _payload(self) -> dict:
        return {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "job_title": self.job_title.text().strip(),
            "company_name": self.company_name.text().strip(),
        }

    def _save(self) -> None:
        payload = self._payload()
        if not payload["first_name"] or not payload["last_name"]:
            QMessageBox.warning(self, "Apprenant", "Le prénom et le nom sont obligatoires.")
            return
        try:
            learner_id = str(self.learner.get("id") or "").strip()
            if learner_id:
                self.saved_learner = self.api.update_cloud_learner(learner_id, payload)
            else:
                self.saved_learner = self.api.create_cloud_learner(payload)
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return
        self.accept()


class LearnerSelectionDialog(QDialog):
    """Sélectionne des apprenants existants et permet leur création / modification."""

    def __init__(
        self,
        api,
        parent=None,
        *,
        excluded_ids: set[str] | None = None,
        company_name: str = "",
        max_to_select: int | None = None,
    ):
        super().__init__(parent)
        self.api = api
        self.excluded_ids = {str(value) for value in (excluded_ids or set())}
        self.company_name = company_name
        self.max_to_select = max_to_select
        self.learners: list[dict] = []
        self.selected_learners: list[dict] = []
        self.setWindowTitle("Ajouter des apprenants")
        self.resize(820, 560)
        self.setStyleSheet("QDialog{background:#F5F8FC;}")
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        title = QLabel("Ajouter des apprenants à la session")
        title.setStyleSheet("color:#0B1220;font-size:20px;font-weight:900;")
        root.addWidget(title)
        subtitle_text = (
            f"Seuls les apprenants rattachés à « {self.company_name} » sont affichés."
            if self.company_name
            else "Sélectionnez un ou plusieurs apprenants existants, ou créez une nouvelle fiche."
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#6B7A90;font-size:10px;")
        root.addWidget(subtitle)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher par nom, e-mail, entreprise ou fonction…")
        self.search.setStyleSheet(_FIELD_STYLE)
        self.search.textChanged.connect(self._render)
        top.addWidget(self.search, 1)

        new_button = QPushButton("+ Nouvel apprenant")
        new_button.setMinimumHeight(38)
        new_button.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 14px;font-weight:900;}QPushButton:hover{background:#287FD4;}"
        )
        new_button.clicked.connect(self._new_learner)
        top.addWidget(new_button)

        edit_button = QPushButton("Modifier")
        edit_button.setMinimumHeight(38)
        edit_button.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#334155;border:1px solid #DCE5EF;"
            "border-radius:10px;padding:0 14px;font-weight:850;}"
        )
        edit_button.clicked.connect(self._edit_selected)
        top.addWidget(edit_button)
        root.addLayout(top)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nom", "E-mail", "Téléphone", "Fonction", "Entreprise"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget{background:#FFFFFF;color:#243447;border:1px solid #DCE5EF;"
            "border-radius:12px;gridline-color:#EDF2F7;}"
            "QHeaderView::section{background:#F8FBFF;color:#53657C;border:none;"
            "border-bottom:1px solid #DCE5EF;padding:8px;font-weight:900;}"
            "QTableWidget::item:selected{background:#EAF4FF;color:#173A5E;}"
        )
        self.table.doubleClicked.connect(self._accept_selection)
        root.addWidget(self.table, 1)

        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color:#64748B;font-size:10px;")
        root.addWidget(self.info)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Annuler")
        cancel.setMinimumHeight(38)
        cancel.clicked.connect(self.reject)
        add = QPushButton("Ajouter la sélection")
        add.setMinimumHeight(38)
        add.setStyleSheet(
            "QPushButton{background:#338CE4;color:white;border:none;border-radius:10px;"
            "padding:0 16px;font-weight:900;}QPushButton:hover{background:#287FD4;}"
        )
        add.clicked.connect(self._accept_selection)
        actions.addWidget(cancel)
        actions.addWidget(add)
        root.addLayout(actions)

    def _reload(self) -> None:
        try:
            self.learners = self.api.list_cloud_learners(
                include_inactive=False,
                company_name=self.company_name or None,
            )
        except CloudAPIError as exc:
            QMessageBox.critical(self, "Apprenants", str(exc))
            self.learners = []
        self._render()

    def _filtered(self) -> list[dict]:
        query = self.search.text().strip().lower()
        expected_company = _normalize_company_name(self.company_name)
        rows = [
            item
            for item in self.learners
            if str(item.get("id") or "") not in self.excluded_ids
            and (
                not expected_company
                or _normalize_company_name(item.get("company_name")) == expected_company
            )
        ]
        if not query:
            return rows
        result = []
        for item in rows:
            haystack = " ".join(
                str(item.get(key) or "")
                for key in ("full_name", "first_name", "last_name", "email", "phone", "job_title", "company_name")
            ).lower()
            if query in haystack:
                result.append(item)
        return result

    def _render(self) -> None:
        rows = self._filtered()
        self.table.setRowCount(len(rows))
        for row, learner in enumerate(rows):
            full_name = str(learner.get("full_name") or "").strip() or (
                f"{learner.get('first_name') or ''} {learner.get('last_name') or ''}".strip()
            )
            values = [
                full_name,
                str(learner.get("email") or ""),
                str(learner.get("phone") or ""),
                str(learner.get("job_title") or ""),
                str(learner.get("company_name") or ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value or "—")
                if col == 0:
                    item.setData(Qt.UserRole, learner)
                self.table.setItem(row, col, item)
        available = len(rows)
        limit_text = f" • maximum restant : {self.max_to_select}" if self.max_to_select is not None else ""
        self.info.setText(f"{available} apprenant(s) disponible(s){limit_text}")

    def _current_learner(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        data = item.data(Qt.UserRole) if item else None
        return data if isinstance(data, dict) else None

    def _new_learner(self) -> None:
        dialog = LearnerEditDialog(self.api, self, company_name=self.company_name)
        if dialog.exec() != QDialog.Accepted or not dialog.saved_learner:
            return
        self.learners.append(dialog.saved_learner)
        self._render()
        learner_id = str(dialog.saved_learner.get("id") or "")
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            data = item.data(Qt.UserRole) if item else None
            if isinstance(data, dict) and str(data.get("id") or "") == learner_id:
                self.table.selectRow(row)
                break

    def _edit_selected(self) -> None:
        learner = self._current_learner()
        if not learner:
            QMessageBox.information(self, "Apprenant", "Sélectionnez d'abord un apprenant à modifier.")
            return
        dialog = LearnerEditDialog(self.api, self, learner=learner)
        if dialog.exec() != QDialog.Accepted or not dialog.saved_learner:
            return
        updated = dialog.saved_learner
        updated_id = str(updated.get("id") or "")
        self.learners = [updated if str(item.get("id") or "") == updated_id else item for item in self.learners]
        self._render()

    def _accept_selection(self) -> None:
        selected_rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not selected_rows:
            QMessageBox.information(self, "Apprenants", "Sélectionnez au moins un apprenant.")
            return
        selected: list[dict] = []
        for row in selected_rows:
            item = self.table.item(row, 0)
            learner = item.data(Qt.UserRole) if item else None
            if isinstance(learner, dict):
                selected.append(learner)
        if self.max_to_select is not None and len(selected) > self.max_to_select:
            QMessageBox.warning(
                self,
                "Nombre maximal atteint",
                f"Vous pouvez encore ajouter au maximum {self.max_to_select} apprenant(s) à cette session.",
            )
            return
        self.selected_learners = selected
        self.accept()
