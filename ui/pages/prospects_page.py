from math import ceil

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QFileDialog,
    QStackedWidget,
    QButtonGroup,
)

from core.constants import PRIMARY_COLOR
from core.application_state import ApplicationState
from core.crm import PIPELINE, PRIORITES
from services.prospect_service import ProspectService
from services.export_service import ExportService
from ui.dialogs.prospect_dialog import ProspectDialog
from ui.dialogs.client_onboarding_wizard import ClientOnboardingWizard
from ui.widgets.crm.filters_bar import CRMFiltersBar
from ui.widgets.crm.prospects_table import ProspectsTableWidget
from ui.widgets.crm.kanban_view import KanbanView
from ui.components.notifications import NotificationManager
from services.system import ActivityService
from services.cloud_runtime import CloudRuntime
from core.session import SessionState


class ProspectsPage(QWidget):
    """Page CRM principale.

    Cette page orchestre les composants CRM : barre de filtres, vue tableau,
    vue Kanban, services métier, pagination et fiche prospect. Les vues sont
    séparées dans des widgets dédiés afin de garder une architecture maintenable.
    """

    DISPLAY_LIMIT = 100

    def __init__(self):
        super().__init__()

        self.prospect_service = ProspectService()
        self.export_service = ExportService()
        self.current_prospects = []
        self.page_courante = 1
        self.total_filtre_courant = 0
        self.total_general_courant = 0
        self.total_pages = 1

        layout = QVBoxLayout()
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        titre_layout = QHBoxLayout()
        titre_layout.setSpacing(12)

        titre = QLabel("CRM")
        titre.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827;")

        self.label_info = QLabel("Aucun projet actif")
        self.label_info.setStyleSheet("font-size: 15px; color: #6B7280;")

        titre_layout.addWidget(titre)
        titre_layout.addStretch()

        self.filters_bar = CRMFiltersBar()
        self.filters_bar.filters_changed.connect(lambda: self.appliquer_filtres(reset_page=True))

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        self.bouton_tableau = QPushButton("📋 Tableau")
        self.bouton_kanban = QPushButton("📌 Kanban")

        self.bouton_tableau.setCheckable(True)
        self.bouton_kanban.setCheckable(True)
        self.bouton_tableau.setChecked(True)

        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        self.view_group.addButton(self.bouton_tableau, 0)
        self.view_group.addButton(self.bouton_kanban, 1)
        self.view_group.idClicked.connect(self.changer_vue)

        for bouton in [self.bouton_tableau, self.bouton_kanban]:
            bouton.setFixedHeight(40)
            bouton.setStyleSheet(self.style_bouton_vue())

        bouton_rafraichir = QPushButton("🔄 Rafraîchir")
        bouton_rafraichir.setFixedHeight(40)
        bouton_rafraichir.clicked.connect(self.charger_prospects)

        bouton_exporter = QPushButton("📤 Exporter Excel")
        bouton_exporter.setFixedHeight(40)
        bouton_exporter.clicked.connect(self.exporter_excel)

        bouton_scoring = QPushButton("⭐ Calculer les scores")
        bouton_scoring.setFixedHeight(40)
        bouton_scoring.clicked.connect(self.recalculer_scores)

        bouton_client = QPushButton("✓ Transformer en client")
        bouton_client.setFixedHeight(40)
        bouton_client.clicked.connect(self.transformer_selection_en_client)

        for bouton in [bouton_rafraichir, bouton_exporter, bouton_scoring, bouton_client]:
            bouton.setStyleSheet(self.style_bouton_principal())

        toolbar_layout.addWidget(self.bouton_tableau)
        toolbar_layout.addWidget(self.bouton_kanban)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(bouton_rafraichir)
        toolbar_layout.addWidget(bouton_exporter)
        toolbar_layout.addWidget(bouton_scoring)
        toolbar_layout.addWidget(bouton_client)
        toolbar_layout.addStretch()

        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)

        self.bouton_premiere_page = QPushButton("⏮ Première")
        self.bouton_page_precedente = QPushButton("◀ Précédente")
        self.label_pagination = QLabel("Page 1 / 1")
        self.bouton_page_suivante = QPushButton("Suivante ▶")
        self.bouton_derniere_page = QPushButton("Dernière ⏭")
        self.label_affichage = QLabel("Aucun prospect affiché")

        self.bouton_premiere_page.clicked.connect(self.aller_premiere_page)
        self.bouton_page_precedente.clicked.connect(self.aller_page_precedente)
        self.bouton_page_suivante.clicked.connect(self.aller_page_suivante)
        self.bouton_derniere_page.clicked.connect(self.aller_derniere_page)

        for bouton in [
            self.bouton_premiere_page,
            self.bouton_page_precedente,
            self.bouton_page_suivante,
            self.bouton_derniere_page,
        ]:
            bouton.setFixedHeight(34)
            bouton.setStyleSheet(self.style_bouton_secondaire())

        self.label_pagination.setStyleSheet("font-size: 13px; font-weight: 800; color: #111827; padding: 0 8px;")
        self.label_affichage.setStyleSheet("font-size: 13px; font-weight: 600; color: #6B7280;")

        pagination_layout.addWidget(self.bouton_premiere_page)
        pagination_layout.addWidget(self.bouton_page_precedente)
        pagination_layout.addWidget(self.label_pagination)
        pagination_layout.addWidget(self.bouton_page_suivante)
        pagination_layout.addWidget(self.bouton_derniere_page)
        pagination_layout.addSpacing(12)
        pagination_layout.addWidget(self.label_affichage)
        pagination_layout.addStretch()

        self.views_stack = QStackedWidget()

        self.table = ProspectsTableWidget()
        self.table.prospect_double_clicked.connect(self.ouvrir_fiche_prospect)

        self.kanban = KanbanView()
        self.kanban.prospect_double_clicked.connect(self.ouvrir_fiche_prospect)
        self.kanban.pipeline_change_requested.connect(self.changer_pipeline_prospect)

        self.views_stack.addWidget(self.table)
        self.views_stack.addWidget(self.kanban)

        layout.addLayout(titre_layout)
        layout.addWidget(self.label_info)
        layout.addWidget(self.filters_bar)
        layout.addLayout(toolbar_layout)
        layout.addLayout(pagination_layout)
        layout.addWidget(self.views_stack, 1)

        self.setLayout(layout)
        self.mettre_a_jour_pagination_ui()

    def _has_data_source(self):
        return CloudRuntime.is_active() or ApplicationState.has_project()

    def _database_path(self):
        if CloudRuntime.is_active():
            return None
        return ApplicationState.get_project().database

    def _source_name(self):
        if CloudRuntime.is_active():
            user = SessionState.user()
            return user.organization_name if user and user.organization_name else "Form@Prospect Cloud"
        return ApplicationState.get_project().name

    def style_bouton_principal(self):
        return f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                padding-left: 16px;
                padding-right: 16px;
            }}
            QPushButton:hover {{
                background-color: #256DB4;
            }}
            QPushButton:pressed {{
                background-color: #1D4F86;
            }}
        """

    def style_bouton_secondaire(self):
        return """
            QPushButton {
                background-color: #F3F4F6;
                color: #111827;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding-left: 12px;
                padding-right: 12px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
            QPushButton:pressed {
                background-color: #D1D5DB;
            }
            QPushButton:disabled {
                background-color: #F9FAFB;
                color: #9CA3AF;
                border: 1px solid #E5E7EB;
            }
        """

    def style_bouton_vue(self):
        return f"""
            QPushButton {{
                background-color: #F3F4F6;
                color: #111827;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                padding-left: 16px;
                padding-right: 16px;
            }}
            QPushButton:hover {{
                background-color: #E5E7EB;
            }}
            QPushButton:checked {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: 1px solid {PRIMARY_COLOR};
            }}
        """

    def changer_vue(self, view_id):
        self.views_stack.setCurrentIndex(view_id)
        self.afficher_donnees_vue_active()

    def afficher_donnees_vue_active(self):
        premier_numero = self.offset_courant() + 1

        if self.views_stack.currentIndex() == 0:
            self.table.afficher_lignes(self.current_prospects, start_number=premier_numero)
        else:
            self.kanban.afficher_lignes(self.current_prospects)

    def offset_courant(self):
        return max(0, (self.page_courante - 1) * self.DISPLAY_LIMIT)

    def calculer_total_pages(self, total):
        if total <= 0:
            return 1
        return max(1, ceil(total / self.DISPLAY_LIMIT))

    def charger_options_filtres(self):
        if not self._has_data_source():
            return

        try:
            database_path = self._database_path()
            options = self.prospect_service.recuperer_options_filtres(database_path)
            self.filters_bar.charger_options(
                options,
                pipelines_ordonnes=PIPELINE,
                priorites_ordonnees=PRIORITES,
            )

        except Exception as e:
            QMessageBox.warning(self, "Filtres", f"Impossible de charger les filtres :\n{e}")

    def charger_prospects(self):
        if not self._has_data_source():
            QMessageBox.warning(self, "Attention", "Aucun projet actif.")
            return

        try:
            self.page_courante = 1
            self.charger_options_filtres()
            self.appliquer_filtres(reset_page=False)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger les prospects :\n{e}")

    def appliquer_filtres(self, reset_page=True):
        if not self._has_data_source():
            self.current_prospects = []
            self.total_filtre_courant = 0
            self.total_general_courant = 0
            self.total_pages = 1
            self.mettre_a_jour_pagination_ui()
            return

        try:
            database_path = self._database_path()
            criteres = self.filters_bar.criteres()

            if reset_page:
                self.page_courante = 1

            self.total_general_courant = self.prospect_service.compter_prospects(database_path)
            self.total_filtre_courant = self.prospect_service.compter_prospects_filtres(
                database_path,
                **criteres,
            )
            self.total_pages = self.calculer_total_pages(self.total_filtre_courant)
            self.page_courante = min(max(1, self.page_courante), self.total_pages)

            prospects = self.prospect_service.rechercher_prospects_filtres(
                database_path,
                **criteres,
                limite=self.DISPLAY_LIMIT,
                offset=self.offset_courant(),
            )

            self.current_prospects = prospects
            self.mettre_a_jour_infos(self._source_name())
            self.mettre_a_jour_pagination_ui()
            self.afficher_donnees_vue_active()

        except Exception as e:
            QMessageBox.critical(self, "Erreur filtres", str(e))

    def mettre_a_jour_infos(self, nom_projet):
        total = self.total_filtre_courant
        total_general = self.total_general_courant
        debut, fin = self.plage_affichee()

        if self.filters_bar.filtres_actifs():
            self.label_info.setText(
                f"{total} résultat(s) sur {total_general} prospects dans {nom_projet} — "
                f"page {self.page_courante} / {self.total_pages}"
            )
        else:
            self.label_info.setText(
                f"{total_general} prospects dans {nom_projet} — "
                f"page {self.page_courante} / {self.total_pages}"
            )

        if total == 0:
            self.label_affichage.setText("Aucun prospect affiché")
        else:
            self.label_affichage.setText(
                f"Affichage de {debut} à {fin} sur {total} prospect(s)"
            )

    def plage_affichee(self):
        total = self.total_filtre_courant
        if total <= 0:
            return 0, 0

        debut = self.offset_courant() + 1
        fin = min(self.offset_courant() + len(self.current_prospects), total)
        return debut, fin

    def mettre_a_jour_pagination_ui(self):
        self.label_pagination.setText(f"Page {self.page_courante} / {self.total_pages}")

        has_project = self._has_data_source()
        has_results = self.total_filtre_courant > 0
        can_go_previous = has_project and has_results and self.page_courante > 1
        can_go_next = has_project and has_results and self.page_courante < self.total_pages

        self.bouton_premiere_page.setEnabled(can_go_previous)
        self.bouton_page_precedente.setEnabled(can_go_previous)
        self.bouton_page_suivante.setEnabled(can_go_next)
        self.bouton_derniere_page.setEnabled(can_go_next)

        if not has_project:
            self.label_affichage.setText("Aucun projet actif")
        elif not has_results:
            self.label_affichage.setText("Aucun prospect affiché")

    def aller_premiere_page(self):
        if self.page_courante == 1:
            return
        self.page_courante = 1
        self.appliquer_filtres(reset_page=False)

    def aller_page_precedente(self):
        if self.page_courante <= 1:
            return
        self.page_courante -= 1
        self.appliquer_filtres(reset_page=False)

    def aller_page_suivante(self):
        if self.page_courante >= self.total_pages:
            return
        self.page_courante += 1
        self.appliquer_filtres(reset_page=False)

    def aller_derniere_page(self):
        if self.page_courante == self.total_pages:
            return
        self.page_courante = self.total_pages
        self.appliquer_filtres(reset_page=False)

    def rechercher(self):
        self.appliquer_filtres(reset_page=True)

    def ouvrir_fiche_prospect(self, prospect_id):
        if not self._has_data_source():
            return

        if prospect_id is None:
            return

        dialog = ProspectDialog(self._database_path(), prospect_id)

        if dialog.exec():
            self.charger_options_filtres()
            self.appliquer_filtres(reset_page=False)

    def changer_pipeline_prospect(self, prospect_id, nouveau_pipeline):
        if not self._has_data_source():
            return

        if prospect_id is None or not nouveau_pipeline:
            return

        try:
            succes = self.prospect_service.mettre_a_jour_pipeline(
                self._database_path(),
                prospect_id,
                nouveau_pipeline,
            )

            if not succes:
                QMessageBox.warning(
                    self,
                    "Pipeline",
                    "Impossible de mettre à jour le pipeline de ce prospect.",
                )
                return

            self.charger_options_filtres()
            self.appliquer_filtres(reset_page=False)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur pipeline",
                f"Impossible de déplacer le prospect :\n{e}",
            )


    def transformer_selection_en_client(self):
        if CloudRuntime.is_active():
            QMessageBox.information(self, "Transformation", "La transformation Cloud en client sera activée dans un prochain lot.")
            return
        if not self._has_data_source():
            QMessageBox.warning(self, "Transformation", "Aucun projet actif.")
            return
        if self.views_stack.currentIndex() != 0:
            QMessageBox.information(self, "Transformation", "Passez en vue Tableau puis sélectionnez un prospect.")
            return
        row = self.table.currentRow()
        prospect_id = self.table.prospect_id_from_row(row) if row >= 0 else None
        if prospect_id is None:
            QMessageBox.warning(self, "Transformation", "Sélectionnez d’abord une ligne de prospect.")
            return
        projet = ApplicationState.get_project()
        dialog = ClientOnboardingWizard(projet.database, projet.folder, int(prospect_id), self)
        if dialog.exec():
            result = dialog.result_data
            QMessageBox.information(
                self,
                "Client créé",
                f"Le prospect a été transformé en client.\n\nDossier : {result.client_folder}",
            )
            self.charger_options_filtres()
            self.appliquer_filtres(reset_page=False)

    def recalculer_scores(self):
        if CloudRuntime.is_active():
            QMessageBox.information(self, "Scoring", "Le scoring Cloud sera activé dans un prochain lot.")
            return
        if not self._has_data_source():
            QMessageBox.warning(self, "Scoring", "Aucun projet actif.")
            return

        answer = QMessageBox.question(
            self,
            "Scoring commercial",
            "Calculer ou actualiser le score de tous les prospects du projet ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            projet = ApplicationState.get_project()
            result = self.prospect_service.recalculer_scores(projet.database)
            total = result.get("total", 0)
            ActivityService.record(
                "Scoring commercial actualisé",
                f"{total} prospect(s) analysé(s).",
                category="scoring",
                level="success",
                metadata=result,
            )
            NotificationManager.success(
                "Scoring terminé",
                f"{total} prospect(s) ont été analysés et classés.",
            )
            self.charger_prospects()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur scoring", str(exc))

    def exporter_excel(self):
        if CloudRuntime.is_active():
            QMessageBox.information(self, "Export", "L'export Cloud sera activé dans un prochain lot.")
            return
        if not self._has_data_source():
            QMessageBox.warning(self, "Attention", "Aucun projet actif.")
            return

        fichier_sortie, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les prospects",
            "prospects_export.xlsx",
            "Fichiers Excel (*.xlsx)",
        )

        if not fichier_sortie:
            return

        try:
            projet = ApplicationState.get_project()

            total = self.export_service.exporter_prospects_excel(
                projet.database,
                fichier_sortie,
            )

            QMessageBox.information(
                self,
                "Export terminé",
                f"{total} prospects exportés avec succès.",
            )

        except Exception as e:
            QMessageBox.critical(self, "Erreur export", str(e))
