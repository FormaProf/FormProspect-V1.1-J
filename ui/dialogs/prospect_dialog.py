from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout,
    QTextEdit, QListWidget, QComboBox, QScrollArea, QWidget
)

from core.constants import PRIMARY_COLOR
from core.crm import (
    PIPELINE,
    PIPELINE_DEFAULT,
    PRIORITES,
    PRIORITE_DEFAULT,
    ACTIONS,
    ACTION_DEFAULT,
)
from services.prospect_service import ProspectService
from services.note_service import NoteService
from services.activity_service import ActivityService
from services.scoring_service import ScoringService
from core.database import init_database
from services.cloud_runtime import CloudRuntime


class ProspectDialog(QDialog):
    def __init__(self, database_path, prospect_id):
        super().__init__()

        self.database_path = database_path
        self.prospect_id = prospect_id

        self.prospect_service = ProspectService()
        self.note_service = NoteService()
        self.activity_service = ActivityService()

        self.ancien_pipeline = PIPELINE_DEFAULT
        self.ancienne_priorite = PRIORITE_DEFAULT
        self.ancienne_action = ACTION_DEFAULT
        self.ancienne_date_action = ""
        self.ancien_commercial = ""

        if not CloudRuntime.is_active():
            init_database(self.database_path)

        self.setWindowTitle("Fiche prospect")
        # La fiche reste utilisable sur les écrans de faible hauteur.
        # Son contenu est placé dans une zone défilable au lieu d'imposer
        # une fenêtre fixe de 1080 px qui dépassait de l'écran.
        self.resize(800, 820)
        self.setMinimumSize(700, 600)

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #F9FAFB;
                border: none;
            }
            QScrollBar:vertical {
                background: #E5E7EB;
                width: 12px;
                margin: 0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #9CA3AF;
                min-height: 36px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6B7280;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background-color: #F9FAFB;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 22)
        layout.setSpacing(14)

        self.titre = QLabel("Fiche prospect")
        self.titre.setStyleSheet("font-size: 24px; font-weight: 800; color: #111827;")

        self.form = QFormLayout()
        self.form.setSpacing(10)

        self.entreprise_input = QLineEdit()
        self.ville_input = QLineEdit()
        self.cp_input = QLineEdit()
        self.telephone_input = QLineEdit()
        self.site_input = QLineEdit()
        self.email_input = QLineEdit()
        self.facebook_input = QLineEdit()
        self.linkedin_input = QLineEdit()
        self.instagram_input = QLineEdit()
        self.youtube_input = QLineEdit()

        self.pipeline_input = QComboBox()
        self.pipeline_input.addItems(PIPELINE)

        self.priorite_input = QComboBox()
        self.priorite_input.addItems(PRIORITES)

        self.prochaine_action_input = QComboBox()
        self.prochaine_action_input.addItems(ACTIONS)

        self.date_prochaine_action_input = QLineEdit()
        self.date_prochaine_action_input.setPlaceholderText("Exemple : 15/07/2026 ou 2026-07-15")

        self.commercial_input = QLineEdit()
        self.commercial_input.setPlaceholderText("Nom du commercial assigné")

        self.score_input = QLineEdit()
        self.score_input.setReadOnly(True)
        self.score_input.setStyleSheet("font-weight: 900; color: #047857; background: #ECFDF5;")
        self.score_details_input = QTextEdit()
        self.score_details_input.setReadOnly(True)
        self.score_details_input.setFixedHeight(90)

        self.entreprise_input.setReadOnly(True)
        self.ville_input.setReadOnly(True)
        self.cp_input.setReadOnly(True)

        self.form.addRow("Entreprise", self.entreprise_input)
        self.form.addRow("Ville", self.ville_input)
        self.form.addRow("Code postal", self.cp_input)
        self.form.addRow("Téléphone", self.telephone_input)
        self.form.addRow("Site web", self.site_input)
        self.form.addRow("Email", self.email_input)
        self.form.addRow("Facebook", self.facebook_input)
        self.form.addRow("LinkedIn", self.linkedin_input)
        self.form.addRow("Instagram", self.instagram_input)
        self.form.addRow("YouTube", self.youtube_input)
        self.form.addRow("Pipeline", self.pipeline_input)
        self.form.addRow("Priorité", self.priorite_input)
        self.form.addRow("Prochaine action", self.prochaine_action_input)
        self.form.addRow("Date prochaine action", self.date_prochaine_action_input)
        self.form.addRow("Commercial assigné", self.commercial_input)
        self.form.addRow("Score commercial", self.score_input)
        self.form.addRow("Explication du score", self.score_details_input)

        titre_notes = QLabel("📝 Notes CRM")
        titre_notes.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")

        self.notes_liste = QListWidget()
        self.notes_liste.setFixedHeight(110)

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Ajouter une nouvelle note...")
        self.note_input.setFixedHeight(70)

        bouton_ajouter_note = QPushButton("➕ Ajouter la note")
        bouton_ajouter_note.setFixedHeight(40)
        bouton_ajouter_note.clicked.connect(self.ajouter_note)

        titre_historique = QLabel("📅 Historique des actions")
        titre_historique.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")

        self.activities_liste = QListWidget()
        self.activities_liste.setFixedHeight(130)

        self.bouton_enregistrer = QPushButton("💾 Enregistrer les informations")
        self.bouton_enregistrer.setFixedHeight(44)
        self.bouton_enregistrer.clicked.connect(self.enregistrer)

        for bouton in [bouton_ajouter_note, self.bouton_enregistrer]:
            bouton.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY_COLOR};
                    color: white;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #256DB4;
                }}
            """)

        layout.addWidget(self.titre)
        layout.addLayout(self.form)
        layout.addWidget(titre_notes)
        layout.addWidget(self.notes_liste)
        layout.addWidget(self.note_input)
        layout.addWidget(bouton_ajouter_note)
        layout.addWidget(titre_historique)
        layout.addWidget(self.activities_liste)
        layout.addWidget(self.bouton_enregistrer)

        self.scroll_area.setWidget(content)
        page_layout.addWidget(self.scroll_area)

        self.charger_prospect()
        self.charger_notes()
        self.charger_activities()

    def charger_prospect(self):
        prospect = self.prospect_service.recuperer_prospect_par_id(
            self.database_path,
            self.prospect_id
        )

        if not prospect:
            QMessageBox.critical(self, "Erreur", "Prospect introuvable.")
            self.reject()
            return

        (
            prospect_id,
            entreprise,
            siret,
            siren,
            adresse,
            code_postal,
            ville,
            code_naf,
            telephone,
            site_web,
            email,
            facebook,
            linkedin,
            instagram,
            youtube,
            statut_enrichissement,
            date_collecte,
            pipeline,
            priorite,
            prochaine_action,
            date_prochaine_action,
            commercial_assigne,
            score_prospect,
            score_grade,
            score_label,
            score_details,
            date_score,
        ) = prospect

        pipeline_final = pipeline if pipeline in PIPELINE else PIPELINE_DEFAULT
        priorite_finale = priorite if priorite in PRIORITES else PRIORITE_DEFAULT
        action_finale = prochaine_action if prochaine_action in ACTIONS else ACTION_DEFAULT
        date_action_finale = str(date_prochaine_action or "")
        commercial_final = str(commercial_assigne or "")

        self.ancien_pipeline = pipeline_final
        self.ancienne_priorite = priorite_finale
        self.ancienne_action = action_finale
        self.ancienne_date_action = date_action_finale
        self.ancien_commercial = commercial_final

        self.entreprise_input.setText(str(entreprise or ""))
        self.ville_input.setText(str(ville or ""))
        self.cp_input.setText(str(code_postal or ""))
        self.telephone_input.setText(str(telephone or ""))
        self.site_input.setText(str(site_web or ""))
        self.email_input.setText(str(email or ""))
        self.facebook_input.setText(str(facebook or ""))
        self.linkedin_input.setText(str(linkedin or ""))
        self.instagram_input.setText(str(instagram or ""))
        self.youtube_input.setText(str(youtube or ""))
        self.pipeline_input.setCurrentText(pipeline_final)
        self.priorite_input.setCurrentText(priorite_finale)
        self.prochaine_action_input.setCurrentText(action_finale)
        self.date_prochaine_action_input.setText(date_action_finale)
        self.commercial_input.setText(commercial_final)
        self.score_input.setText(f"{score_grade or '★☆☆☆☆'}  —  {int(score_prospect or 0)}/100  —  {score_label or ''}")
        try:
            import json
            details = json.loads(score_details or "[]")
        except Exception:
            details = []
        self.score_details_input.setPlainText("\n".join(details) if details else "Score non calculé.")

    def charger_notes(self):
        self.notes_liste.clear()
        notes = self.note_service.get_notes(self.database_path, self.prospect_id)

        if not notes:
            self.notes_liste.addItem("Aucune note pour ce prospect.")
            return

        for note in notes:
            note_id, date_creation, contenu = note
            self.notes_liste.addItem(f"{date_creation} — {contenu}")

    def charger_activities(self):
        self.activities_liste.clear()
        activities = self.activity_service.get_activities(self.database_path, self.prospect_id)

        if not activities:
            self.activities_liste.addItem("Aucune action enregistrée.")
            return

        for activity in activities:
            activity_id, date_creation, type_action, description = activity
            self.activities_liste.addItem(f"{date_creation} — {type_action} — {description}")

    def ajouter_note(self):
        contenu = self.note_input.toPlainText().strip()

        if not contenu:
            QMessageBox.warning(self, "Attention", "La note est vide.")
            return

        try:
            self.note_service.add_note(self.database_path, self.prospect_id, contenu)

            self.activity_service.add_activity(
                self.database_path,
                self.prospect_id,
                "Note",
                "Nouvelle note ajoutée"
            )

            if not CloudRuntime.is_active():
                ScoringService.score_prospect(self.database_path, self.prospect_id)
            self.note_input.clear()
            self.charger_notes()
            self.charger_activities()
            self.charger_prospect()

            QMessageBox.information(self, "Note ajoutée", "La note a été ajoutée.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def enregistrer(self):
        try:
            nouveau_pipeline = self.pipeline_input.currentText()
            nouvelle_priorite = self.priorite_input.currentText()
            nouvelle_action = self.prochaine_action_input.currentText()
            nouvelle_date_action = self.date_prochaine_action_input.text().strip()
            nouveau_commercial = self.commercial_input.text().strip()

            self.prospect_service.mettre_a_jour_contact(
                self.database_path,
                self.prospect_id,
                self.telephone_input.text().strip(),
                self.site_input.text().strip(),
                self.email_input.text().strip(),
                self.facebook_input.text().strip(),
                self.linkedin_input.text().strip(),
                self.instagram_input.text().strip(),
                self.youtube_input.text().strip(),
                nouveau_pipeline,
                nouvelle_priorite,
                nouvelle_action,
                nouvelle_date_action,
                nouveau_commercial,
            )

            modifications = []

            if nouveau_pipeline != self.ancien_pipeline:
                modifications.append((
                    "Pipeline",
                    f"Pipeline modifié : {self.ancien_pipeline} → {nouveau_pipeline}"
                ))

            if nouvelle_priorite != self.ancienne_priorite:
                modifications.append((
                    "Priorité",
                    f"Priorité modifiée : {self.ancienne_priorite} → {nouvelle_priorite}"
                ))

            if nouvelle_action != self.ancienne_action:
                modifications.append((
                    "Prochaine action",
                    f"Prochaine action modifiée : {self.ancienne_action} → {nouvelle_action}"
                ))

            if nouvelle_date_action != self.ancienne_date_action:
                ancienne_date = self.ancienne_date_action or "Aucune"
                nouvelle_date = nouvelle_date_action or "Aucune"
                modifications.append((
                    "Date action",
                    f"Date de prochaine action modifiée : {ancienne_date} → {nouvelle_date}"
                ))

            if nouveau_commercial != self.ancien_commercial:
                ancien_commercial = self.ancien_commercial or "Aucun"
                commercial = nouveau_commercial or "Aucun"
                modifications.append((
                    "Commercial",
                    f"Commercial assigné modifié : {ancien_commercial} → {commercial}"
                ))

            if not modifications:
                modifications.append((
                    "Modification",
                    "Informations du prospect mises à jour"
                ))

            for type_action, description in modifications:
                self.activity_service.add_activity(
                    self.database_path,
                    self.prospect_id,
                    type_action,
                    description
                )

            if not CloudRuntime.is_active():
                ScoringService.score_prospect(self.database_path, self.prospect_id)
            self.charger_activities()

            QMessageBox.information(self, "Succès", "Prospect mis à jour dans le Cloud." if CloudRuntime.is_active() else "Prospect mis à jour et score V2 recalculé.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
