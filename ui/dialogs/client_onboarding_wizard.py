from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core.constants import PRIMARY_COLOR
from services.client_onboarding_service import ClientOnboardingService


class ClientOnboardingWizard(QDialog):
    def __init__(self, database_path, project_folder, prospect_id: int, parent=None):
        super().__init__(parent)
        self.service = ClientOnboardingService(database_path, project_folder)
        self.prospect_id = int(prospect_id)
        self.prospect = self.service.prospect_as_dict(self.prospect_id)
        self.trainings = self.service.list_trainings()
        self.result_data = None
        self.setWindowTitle("Transformer en client")
        self.setMinimumSize(760, 610)
        self._build_ui()
        self._load_prospect()
        self._update_navigation()

    def _field(self, placeholder=""):
        edit = QLineEdit(); edit.setPlaceholderText(placeholder); edit.setMinimumHeight(38); return edit

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(28, 24, 28, 24); root.setSpacing(16)
        title = QLabel("Transformer le prospect en client")
        title.setStyleSheet("font-size:24px;font-weight:800;color:#111827;")
        self.step_label = QLabel(); self.step_label.setStyleSheet("color:#6B7280;font-weight:700;")
        root.addWidget(title); root.addWidget(self.step_label)
        self.stack = QStackedWidget(); root.addWidget(self.stack, 1)
        self.stack.addWidget(self._client_page())
        self.stack.addWidget(self._training_page())
        self.stack.addWidget(self._organization_page())
        self.stack.addWidget(self._summary_page())
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Précédent")
        self.next_btn = QPushButton("Suivant →")
        self.cancel_btn = QPushButton("Annuler")
        self.back_btn.clicked.connect(self._back); self.next_btn.clicked.connect(self._next); self.cancel_btn.clicked.connect(self.reject)
        self.next_btn.setStyleSheet(f"background:{PRIMARY_COLOR};color:white;border:none;border-radius:9px;padding:10px 18px;font-weight:800;")
        nav.addWidget(self.cancel_btn); nav.addStretch(); nav.addWidget(self.back_btn); nav.addWidget(self.next_btn)
        root.addLayout(nav)

    def _page(self, heading, subtitle):
        page = QWidget(); layout = QVBoxLayout(page); layout.setSpacing(14)
        h = QLabel(heading); h.setStyleSheet("font-size:19px;font-weight:800;color:#111827;")
        s = QLabel(subtitle); s.setWordWrap(True); s.setStyleSheet("color:#6B7280;")
        layout.addWidget(h); layout.addWidget(s); return page, layout

    def _client_page(self):
        page, layout = self._page("1. Informations client", "Vérifiez les informations récupérées depuis le prospect.")
        form = QFormLayout(); form.setSpacing(12)
        self.company = self._field(); self.siret = self._field(); self.address = self._field(); self.postal = self._field();
        self.city = self._field(); self.contact = self._field("Nom du dirigeant ou contact"); self.phone = self._field(); self.email = self._field()
        for label, field in (("Entreprise *",self.company),("SIRET",self.siret),("Adresse",self.address),("Code postal",self.postal),("Ville",self.city),("Contact",self.contact),("Téléphone",self.phone),("E-mail",self.email)): form.addRow(label,field)
        layout.addLayout(form); layout.addStretch(); return page

    def _training_page(self):
        page, layout = self._page("2. Formation", "Sélectionnez une formation active du catalogue RC2.0.1.")
        form = QFormLayout(); form.setSpacing(12)
        self.training = QComboBox(); self.training.setMinimumHeight(38)
        for item in self.trainings: self.training.addItem(f"{item['reference']} — {item['name']}", item['id'])
        self.training.currentIndexChanged.connect(self._training_changed)
        self.duration = QDoubleSpinBox(); self.duration.setRange(0.5,10000); self.duration.setSuffix(" h"); self.duration.setDecimals(1); self.duration.setMinimumHeight(38)
        self.price = QDoubleSpinBox(); self.price.setRange(0,1000000); self.price.setSuffix(" €"); self.price.setDecimals(2); self.price.setMinimumHeight(38)
        self.modality = QComboBox(); self.modality.addItems(self.service.document_service.MODALITIES); self.modality.setMinimumHeight(38)
        self.participants = QSpinBox(); self.participants.setRange(1,500); self.participants.setMinimumHeight(38)
        form.addRow("Formation *",self.training); form.addRow("Durée",self.duration); form.addRow("Prix",self.price); form.addRow("Modalité",self.modality); form.addRow("Participants",self.participants)
        layout.addLayout(form); layout.addStretch(); self._training_changed(); return page

    def _organization_page(self):
        page, layout = self._page("3. Organisation", "Renseignez les dates, le formateur, le commercial et le financement.")
        form = QFormLayout(); form.setSpacing(12)
        self.trainer = self._field("Nom du formateur"); self.commercial = self._field()
        self.funder = QComboBox(); self.funder.addItems(self.service.FUNDERS); self.funder.setMinimumHeight(38)
        self.funder_details = self._field("Nom de l’OPCO, n° de dossier…")
        self.start = QDateEdit(QDate.currentDate()); self.start.setCalendarPopup(True); self.start.setDisplayFormat("dd/MM/yyyy"); self.start.setMinimumHeight(38)
        self.end = QDateEdit(QDate.currentDate()); self.end.setCalendarPopup(True); self.end.setDisplayFormat("dd/MM/yyyy"); self.end.setMinimumHeight(38)
        # La date de fin ne peut jamais être antérieure à la date de début.
        self.end.setMinimumDate(self.start.date())
        self.start.dateChanged.connect(self._sync_training_dates)
        self.schedule = self._field(); self.schedule.setText("9h-12h / 13h-17h")
        for label, field in (("Formateur",self.trainer),("Commercial",self.commercial),("Financeur",self.funder),("Détails financeur",self.funder_details),("Date de début *",self.start),("Date de fin *",self.end),("Horaires",self.schedule)): form.addRow(label,field)
        layout.addLayout(form); layout.addStretch(); return page


    def _sync_training_dates(self, start_date: QDate):
        """Maintient une plage de dates cohérente dans l'assistant."""
        self.end.setMinimumDate(start_date)
        if self.end.date() < start_date:
            self.end.setDate(start_date)

    def _summary_page(self):
        page, layout = self._page("4. Validation", "Contrôlez les informations avant de créer le dossier client.")
        self.summary = QLabel(); self.summary.setAlignment(Qt.AlignTop); self.summary.setWordWrap(True)
        self.summary.setStyleSheet("background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:18px;color:#111827;")
        layout.addWidget(self.summary,1); return page

    def _load_prospect(self):
        p=self.prospect; self.company.setText(p.get('entreprise') or ''); self.siret.setText(p.get('siret') or ''); self.address.setText(p.get('adresse') or ''); self.postal.setText(p.get('code_postal') or ''); self.city.setText(p.get('ville') or ''); self.phone.setText(p.get('telephone') or ''); self.email.setText(p.get('email') or ''); self.commercial.setText(p.get('commercial_assigne') or '')

    def _training_changed(self):
        idx=self.training.currentIndex()
        if idx<0 or not self.trainings: return
        item=next((x for x in self.trainings if x['id']==self.training.currentData()),None)
        if not item:return
        self.duration.setValue(float(item['duration_hours'])); self.price.setValue(int(item['price_cents'])/100); self.modality.setCurrentText(item['modality'])

    def _update_navigation(self):
        idx=self.stack.currentIndex(); self.step_label.setText(f"Étape {idx+1} sur 4"); self.back_btn.setEnabled(idx>0); self.next_btn.setText("Créer le dossier client" if idx==3 else "Suivant →")

    def _back(self): self.stack.setCurrentIndex(max(0,self.stack.currentIndex()-1)); self._update_navigation()

    def _next(self):
        idx=self.stack.currentIndex()
        if idx==0 and not self.company.text().strip(): QMessageBox.warning(self,"Informations manquantes","Le nom de l’entreprise est obligatoire."); return
        if idx==1 and self.training.currentData() is None: QMessageBox.warning(self,"Formation manquante","Créez ou activez d’abord une formation dans Documents."); return
        if idx==2 and self.end.date() < self.start.date():
            QMessageBox.warning(self, "Dates incohérentes", "La date de fin ne peut pas précéder la date de début.")
            return
        if idx<3:
            if idx==2: self._refresh_summary()
            self.stack.setCurrentIndex(idx+1); self._update_navigation(); return
        self._finish()

    def _refresh_summary(self):
        self.summary.setText(
            f"<b>Client</b><br>{self.company.text()}<br>{self.address.text()} {self.postal.text()} {self.city.text()}<br><br>"
            f"<b>Formation</b><br>{self.training.currentText()}<br>{self.duration.value():g} h — {self.price.value():.2f} € — {self.modality.currentText()}<br>"
            f"{self.participants.value()} participant(s)<br><br><b>Organisation</b><br>Du {self.start.date().toString('dd/MM/yyyy')} au {self.end.date().toString('dd/MM/yyyy')}<br>"
            f"{self.schedule.text()}<br>Formateur : {self.trainer.text() or 'Non renseigné'}<br>Financeur : {self.funder.currentText()} {self.funder_details.text()}"
        )

    def _finish(self):
        try:
            self.result_data=self.service.transform(
                prospect_id=self.prospect_id, company_name=self.company.text(), siret=self.siret.text(), address=self.address.text(), postal_code=self.postal.text(), city=self.city.text(), contact_name=self.contact.text(), phone=self.phone.text(), email=self.email.text(), training_id=int(self.training.currentData()), trainer_name=self.trainer.text(), commercial_name=self.commercial.text(), funder=self.funder.currentText(), funder_details=self.funder_details.text(), start_date=self.start.date().toString('yyyy-MM-dd'), end_date=self.end.date().toString('yyyy-MM-dd'), daily_schedule=self.schedule.text(), modality=self.modality.currentText(), duration_hours=self.duration.value(), price_cents=round(self.price.value()*100), participant_count=self.participants.value())
        except Exception as exc:
            QMessageBox.critical(self,"Transformation impossible",str(exc)); return
        self.accept()
