from datetime import datetime

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.theme import (
    BACKGROUND_COLOR,
    DARK_PANEL,
    DARK_PANEL_TEXT,
    FONT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    danger_button_style,
    primary_button_style,
    progress_bar_style,
    warning_button_style,
)
from services.enrichment_service import EnrichmentService
from services.excel_service import ExcelService
from services.import_service import ImportService
from services.prospect_excel_preview_presenter import build_excel_update_preview_text
from services.prospect_excel_update_service import ProspectExcelUpdateService
from ui.components import InfoCard, MetricCard, SectionCard, StatCard, StatusBadge
from ui.components.notifications import NotificationManager
from workers.enrichment_worker import EnrichmentWorker
from services.system import ActivityService, RecoveryManager


class TreatmentPage(QWidget):
    TEST_LIMIT = 20

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; font-family: '{FONT}';")

        self.excel_service = ExcelService()
        self.import_service = ImportService()
        self.excel_update_service = ProspectExcelUpdateService()
        self.enrichment_service = EnrichmentService()
        self.datasource_resolver = DataSourceResolver()
        self.recovery_manager = RecoveryManager()

        self.fichier_excel = None
        self.fichier_excel_mise_a_jour = None
        self.excel_update_preview_stats = None
        self.enrichment_thread = None
        self.enrichment_worker = None
        self.enrichment_running = False
        self.enrichment_paused = False

        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Toute la page est défilable. Cela évite que le journal ou les cartes
        # soient compressés ou se chevauchent sur les écrans de faible hauteur.
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QScrollArea.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.page_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
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
        content.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; font-family: '{FONT}';")
        root = QVBoxLayout(content)
        root.setContentsMargins(35, 28, 35, 36)
        root.setSpacing(18)

        title = QLabel("Centre d'enrichissement")
        title.setStyleSheet(f"font-size: 30px; font-weight: 900; color: {TEXT_PRIMARY};")
        subtitle = QLabel("Importez vos données, lancez l'enrichissement et suivez les résultats en temps réel.")
        subtitle.setStyleSheet(f"font-size: 15px; color: {TEXT_SECONDARY};")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.project_card = SectionCard(padding=18, spacing=10)
        self.project_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.label_projet = QLabel("Aucun projet actif")
        self.label_projet.setStyleSheet(f"font-size: 17px; color: {TEXT_PRIMARY}; font-weight: 900;")
        self.label_fichier = QLabel("Aucun fichier Excel sélectionné")
        self.label_fichier.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        self.label_details = QLabel("")
        self.label_details.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        self.project_card.content_layout.addWidget(self.label_projet)
        self.project_card.content_layout.addWidget(self.label_fichier)
        self.project_card.content_layout.addWidget(self.label_details)

        import_actions = QHBoxLayout()
        import_actions.setSpacing(10)
        self.bouton_excel = QPushButton("📥 Choisir un fichier Excel")
        self.bouton_importer = QPushButton("✅ Importer dans le projet actif")
        self.bouton_aliases = QPushButton("🏷️ Ajouter enseignes / sigles")
        for button in (self.bouton_excel, self.bouton_importer, self.bouton_aliases):
            button.setFixedHeight(44)
            button.setStyleSheet(primary_button_style())
        self.bouton_aliases.setEnabled(False)
        self.bouton_excel.clicked.connect(self.choisir_excel)
        self.bouton_importer.clicked.connect(self.importer_dans_sqlite)
        self.bouton_aliases.clicked.connect(self.mettre_a_jour_noms_recherche)
        import_actions.addWidget(self.bouton_excel)
        import_actions.addWidget(self.bouton_importer)
        import_actions.addWidget(self.bouton_aliases)
        import_actions.addStretch()
        self.project_card.content_layout.addLayout(import_actions)
        root.addWidget(self.project_card)

        self.excel_update_card = SectionCard(padding=18, spacing=12)
        self.excel_update_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        excel_update_header = QHBoxLayout()
        excel_update_header_text = QVBoxLayout()
        excel_update_title = QLabel("Enrichissement par fichier Excel")
        excel_update_title.setStyleSheet(
            f"font-size: 19px; font-weight: 900; color: {TEXT_PRIMARY};"
        )
        excel_update_subtitle = QLabel(
            "Compare un fichier enrichi aux prospects existants par SIRET exact. "
            "Cette étape est en lecture seule : aucun prospect créé et aucune donnée supprimée."
        )
        excel_update_subtitle.setWordWrap(True)
        excel_update_subtitle.setStyleSheet(
            f"font-size: 13px; color: {TEXT_SECONDARY};"
        )
        excel_update_header_text.addWidget(excel_update_title)
        excel_update_header_text.addWidget(excel_update_subtitle)
        self.excel_update_badge = StatusBadge("idle")
        self.excel_update_badge.set_state("idle", "Lecture seule")
        excel_update_header.addLayout(excel_update_header_text, 1)
        excel_update_header.addWidget(self.excel_update_badge, 0, Qt.AlignTop)
        self.excel_update_card.content_layout.addLayout(excel_update_header)

        self.label_fichier_mise_a_jour = QLabel(
            "Aucun fichier d'enrichissement Excel sélectionné"
        )
        self.label_fichier_mise_a_jour.setStyleSheet(
            f"font-size: 13px; color: {TEXT_SECONDARY};"
        )
        self.excel_update_card.content_layout.addWidget(self.label_fichier_mise_a_jour)

        excel_update_actions = QHBoxLayout()
        excel_update_actions.setSpacing(10)
        self.bouton_excel_mise_a_jour = QPushButton(
            "📄 Choisir un fichier enrichi"
        )
        self.bouton_analyser_mise_a_jour = QPushButton(
            "🔎 Analyser les mises à jour"
        )
        for button in (
            self.bouton_excel_mise_a_jour,
            self.bouton_analyser_mise_a_jour,
        ):
            button.setFixedHeight(44)
            button.setStyleSheet(primary_button_style())
        self.bouton_analyser_mise_a_jour.setEnabled(False)
        self.bouton_excel_mise_a_jour.clicked.connect(
            self.choisir_excel_mise_a_jour
        )
        self.bouton_analyser_mise_a_jour.clicked.connect(
            self.analyser_mise_a_jour_excel
        )
        excel_update_actions.addWidget(self.bouton_excel_mise_a_jour)
        excel_update_actions.addWidget(self.bouton_analyser_mise_a_jour)
        excel_update_actions.addStretch()
        self.excel_update_card.content_layout.addLayout(excel_update_actions)

        self.excel_update_preview = QTextEdit()
        self.excel_update_preview.setReadOnly(True)
        self.excel_update_preview.setMinimumHeight(170)
        self.excel_update_preview.setMaximumHeight(320)
        self.excel_update_preview.setPlaceholderText(
            "Sélectionnez un fichier enrichi puis lancez l'analyse. "
            "Aucune donnée ne sera modifiée."
        )
        self.excel_update_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: #FFFFFF;
                color: {TEXT_PRIMARY};
                border: 1px solid #DCE4EE;
                border-radius: 10px;
                padding: 10px;
                font-family: Consolas;
                font-size: 12px;
            }}
        """)
        self.excel_update_card.content_layout.addWidget(self.excel_update_preview)
        root.addWidget(self.excel_update_card)

        control_card = SectionCard(padding=20, spacing=14)
        control_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        control_header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_title = QLabel("Moteur d'enrichissement")
        header_title.setStyleSheet(f"font-size: 19px; font-weight: 900; color: {TEXT_PRIMARY};")
        header_subtitle = QLabel(
            "Enrichissez les non enrichis ou réenrichissez toute la base. "
            "Pour des fiches précises, utilisez la sélection dans Prospects."
        )
        header_subtitle.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        header_text.addWidget(header_title)
        header_text.addWidget(header_subtitle)
        self.badge_state = StatusBadge("idle")
        control_header.addLayout(header_text, 1)
        control_header.addWidget(self.badge_state, 0, Qt.AlignTop)
        control_card.content_layout.addLayout(control_header)

        enrichment_actions = QHBoxLayout()
        enrichment_actions.setSpacing(10)
        self.bouton_test = QPushButton(
            f"🧪 Tester sur {self.TEST_LIMIT} non enrichis"
        )
        self.bouton_enrichir = QPushButton("🚀 Enrichir les non enrichis")
        self.bouton_reenrichir_tout = QPushButton("♻ Réenrichir toute la base")
        for button in (
            self.bouton_test,
            self.bouton_enrichir,
            self.bouton_reenrichir_tout,
        ):
            button.setFixedHeight(46)
            button.setStyleSheet(primary_button_style())

        self.bouton_test.clicked.connect(
            lambda: self.demarrer_enrichissement(
                self.TEST_LIMIT,
                mode=EnrichmentService.MODE_PENDING,
            )
        )
        self.bouton_enrichir.clicked.connect(
            lambda: self.demarrer_enrichissement(
                None,
                mode=EnrichmentService.MODE_PENDING,
            )
        )
        self.bouton_reenrichir_tout.clicked.connect(
            lambda: self.demarrer_enrichissement(
                None,
                mode=EnrichmentService.MODE_ALL,
            )
        )
        enrichment_actions.addWidget(self.bouton_test)
        enrichment_actions.addWidget(self.bouton_enrichir, 1)
        enrichment_actions.addWidget(self.bouton_reenrichir_tout, 1)
        control_card.content_layout.addLayout(enrichment_actions)

        runtime_actions = QHBoxLayout()
        runtime_actions.setSpacing(10)
        self.bouton_reessayer = QPushButton("↻ Retenter les sans résultat")
        self.bouton_pause = QPushButton("⏸ Pause")
        self.bouton_arreter = QPushButton("⏹ Arrêter")
        for button in (
            self.bouton_reessayer,
            self.bouton_pause,
            self.bouton_arreter,
        ):
            button.setFixedHeight(42)
        self.bouton_reessayer.setStyleSheet(warning_button_style())
        self.bouton_pause.setStyleSheet(warning_button_style())
        self.bouton_arreter.setStyleSheet(danger_button_style())
        self.bouton_reessayer.setEnabled(False)
        self.bouton_pause.setEnabled(False)
        self.bouton_arreter.setEnabled(False)
        self.bouton_reessayer.clicked.connect(self.reinitialiser_sans_resultat)
        self.bouton_pause.clicked.connect(self.basculer_pause)
        self.bouton_arreter.clicked.connect(self.demander_arret)
        runtime_actions.addWidget(self.bouton_reessayer)
        runtime_actions.addStretch()
        runtime_actions.addWidget(self.bouton_pause)
        runtime_actions.addWidget(self.bouton_arreter)
        control_card.content_layout.addLayout(runtime_actions)

        self.progression = QProgressBar()
        self.progression.setRange(0, 100)
        self.progression.setValue(0)
        self.progression.setFixedHeight(30)
        self.progression.setFormat("Prêt")
        self.progression.setStyleSheet(progress_bar_style())
        control_card.content_layout.addWidget(self.progression)

        self.current_company_card = InfoCard()
        self.current_company_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        control_card.content_layout.addWidget(self.current_company_card)

        metric_grid = QGridLayout()
        metric_grid.setHorizontalSpacing(12)
        metric_grid.setVerticalSpacing(12)
        metric_grid.setColumnStretch(0, 1)
        metric_grid.setColumnStretch(1, 1)
        metric_grid.setColumnStretch(2, 1)
        metric_grid.setColumnStretch(3, 1)
        self.metric_elapsed = MetricCard("Temps écoulé", "00:00:00", "⏱")
        self.metric_eta = MetricCard("Temps restant", "—", "⌛")
        self.metric_speed = MetricCard("Vitesse", "0,0/min", "⚡")
        self.metric_success = MetricCard("Réussite", "—", "✅")
        metric_grid.addWidget(self.metric_elapsed, 0, 0)
        metric_grid.addWidget(self.metric_eta, 0, 1)
        metric_grid.addWidget(self.metric_speed, 0, 2)
        metric_grid.addWidget(self.metric_success, 0, 3)
        control_card.content_layout.addLayout(metric_grid)

        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(12)
        for column in range(4):
            stats_grid.setColumnStretch(column, 1)
        self.stat_cards = {
            "traites": StatCard("Traités", "0", "🔎"),
            "enrichis": StatCard("Enrichis", "0", "✅"),
            "sans_resultat": StatCard("Sans résultat", "0", "➖"),
            "erreurs": StatCard("Erreurs", "0", "⚠️"),
            "telephones": StatCard("Téléphones", "0", "📞"),
            "sites": StatCard("Sites web", "0", "🌐"),
            "emails": StatCard("Emails", "0", "📧"),
            "facebook": StatCard("Facebook", "0", "📘"),
            "linkedin": StatCard("LinkedIn", "0", "💼"),
            "instagram": StatCard("Instagram", "0", "📸"),
            "source_pages_jaunes": StatCard("PagesJaunes", "0", "🟡"),
            "source_google_maps": StatCard("Google Maps", "0", "📍"),
            "source_siren": StatCard("Réutilisation SIREN", "0", "🔁"),
            "source_web": StatCard("Web secours", "0", "🔎"),
            "api_siren_resolved": StatCard("Contexte API SIREN", "0", "🏢"),
        }
        for index, card in enumerate(self.stat_cards.values()):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            stats_grid.addWidget(card, index // 4, index % 4)
        control_card.content_layout.addLayout(stats_grid)

        journal_title = QLabel("Journal d'activité")
        journal_title.setStyleSheet(f"font-size: 14px; font-weight: 900; color: {TEXT_PRIMARY};")
        self.journal = QTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setMinimumHeight(230)
        self.journal.setMaximumHeight(360)
        self.journal.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.journal.document().setMaximumBlockCount(300)
        self.journal.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_PANEL};
                color: {DARK_PANEL_TEXT};
                border: none;
                border-radius: 12px;
                padding: 12px;
                font-family: Consolas;
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background: #1F2937;
                width: 11px;
                margin: 4px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: #6B7280;
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #9CA3AF;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        control_card.content_layout.addWidget(journal_title)
        control_card.content_layout.addWidget(self.journal)

        root.addWidget(control_card)
        root.addStretch()

        self.page_scroll.setWidget(content)
        page_layout.addWidget(self.page_scroll)

    @staticmethod
    def _format_duration(seconds):
        if seconds is None:
            return "—"
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.journal.append(f"[{timestamp}] {message}")
        scrollbar = self.journal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.label_projet.setText("Aucun projet actif")
            self.label_details.setText(
                "Créez ou ouvrez un projet depuis le Dashboard."
            )
            self.bouton_importer.setEnabled(False)
            self.bouton_aliases.setEnabled(False)
            self.bouton_excel_mise_a_jour.setEnabled(True)
            self.bouton_analyser_mise_a_jour.setEnabled(False)
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
            self.bouton_reenrichir_tout.setEnabled(False)
            self.bouton_reessayer.setEnabled(False)
            return

        context = self.datasource_resolver.resolve()

        if context.is_cloud:
            project_name = (
                getattr(context.project, "name", None)
                or getattr(context.project, "title", None)
                or "Projet Cloud"
            )
            self.label_projet.setText(
                f"Projet Cloud actif : {project_name}"
            )
            self.label_details.setText(
                "Projet déjà déployé dans le Cloud. "
                "Workflow : import local → enrichissement local → contrôle "
                "→ déploiement vers le commercial."
            )
            self.bouton_importer.setEnabled(False)
            self.bouton_aliases.setEnabled(False)
            self.bouton_excel_mise_a_jour.setEnabled(True)
            self.bouton_analyser_mise_a_jour.setEnabled(False)
            self.excel_update_badge.set_state("idle", "Cloud : bientôt")
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
            self.bouton_reenrichir_tout.setEnabled(False)
            self.bouton_reessayer.setEnabled(False)
            return

        project = context.project or ApplicationState.get_project()

        if project is None:
            self.label_projet.setText("Aucun projet local actif")
            self.label_details.setText(
                "Créez ou ouvrez un projet depuis le Dashboard."
            )
            self.bouton_importer.setEnabled(False)
            self.bouton_aliases.setEnabled(False)
            self.bouton_excel_mise_a_jour.setEnabled(True)
            self.bouton_analyser_mise_a_jour.setEnabled(False)
            self.excel_update_badge.set_state("idle", "Lecture seule")
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
            self.bouton_reenrichir_tout.setEnabled(False)
            self.bouton_reessayer.setEnabled(False)
            return

        remaining = self.enrichment_service.compter_a_enrichir(project.database)
        total_reenrichissable = self.enrichment_service.compter_cible(
            project.database,
            mode=EnrichmentService.MODE_ALL,
        )
        without_result = self.enrichment_service.compter_sans_resultat(project.database)
        self.label_projet.setText(f"Projet actif : {project.name}")
        self.label_details.setText(
            f"{remaining} non enrichi(s) | "
            f"{total_reenrichissable} prospect(s) au total | "
            f"{without_result} sans résultat."
        )
        self.bouton_importer.setEnabled(True)
        self.bouton_aliases.setEnabled(bool(self.fichier_excel))
        self.bouton_excel_mise_a_jour.setEnabled(True)
        self.bouton_analyser_mise_a_jour.setEnabled(
            bool(self.fichier_excel_mise_a_jour)
        )
        self.excel_update_badge.set_state("idle", "Lecture seule")
        self.bouton_test.setEnabled(remaining > 0)
        self.bouton_enrichir.setEnabled(remaining > 0)
        self.bouton_reenrichir_tout.setEnabled(total_reenrichissable > 0)
        self.bouton_reessayer.setEnabled(without_result > 0)

    def choisir_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier Excel", "", "Fichiers Excel (*.xlsx)"
        )
        if not file_path:
            return
        try:
            self.fichier_excel = file_path
            self.excel_service.load_excel(file_path)
            self.label_fichier.setText(f"Fichier Excel : {self.excel_service.file_path.name}")
            self.label_details.setText(
                f"{self.excel_service.row_count} lignes | {len(self.excel_service.columns)} colonnes"
            )
            if ApplicationState.has_project():
                context = self.datasource_resolver.resolve()
                self.bouton_aliases.setEnabled(not context.is_cloud)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", f"Impossible de lire le fichier :\n{exc}")

    def choisir_excel_mise_a_jour(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier Excel enrichi",
            "",
            "Fichiers Excel (*.xlsx *.xlsm)",
        )
        if not file_path:
            return

        try:
            analyse = self.excel_update_service.analyser_fichier(file_path)
            self.fichier_excel_mise_a_jour = file_path
            self.excel_update_preview_stats = None
            self.label_fichier_mise_a_jour.setText(
                f"Fichier enrichi : {analyse['nom_fichier']} — "
                f"{analyse['lignes_excel']} ligne(s), "
                f"{analyse['siret_valides']} SIRET valide(s)"
            )
            self.excel_update_preview.setPlainText(
                "Fichier chargé en lecture seule.\n\n"
                "Cliquez sur « Analyser les mises à jour » pour comparer "
                "les SIRET du fichier aux prospects du projet actif.\n\n"
                "Aucun prospect ne sera créé et aucune donnée existante "
                "ne sera supprimée."
            )
            self.excel_update_badge.set_state("idle", "Fichier prêt")
            self.rafraichir()
        except Exception as exc:
            self.fichier_excel_mise_a_jour = None
            self.excel_update_preview_stats = None
            self.bouton_analyser_mise_a_jour.setEnabled(False)
            self.excel_update_badge.set_state("error", "Fichier invalide")
            QMessageBox.critical(
                self,
                "Erreur Excel",
                f"Impossible d'analyser le fichier :\n{exc}",
            )

    def analyser_mise_a_jour_excel(self):
        if not self.fichier_excel_mise_a_jour:
            QMessageBox.warning(
                self,
                "Enrichissement Excel",
                "Choisissez d'abord un fichier Excel enrichi.",
            )
            return

        if not ApplicationState.has_project():
            QMessageBox.warning(
                self,
                "Enrichissement Excel",
                "Ouvrez d'abord un projet Form@Prospect.",
            )
            return

        context = self.datasource_resolver.resolve()
        if context.is_cloud:
            QMessageBox.information(
                self,
                "Projet Cloud",
                "La comparaison Excel Cloud sera activée dans le prochain "
                "lot dédié au Cloud. Ce lot reste volontairement en lecture "
                "seule sur les projets locaux.",
            )
            return

        project = context.project or ApplicationState.get_project()
        if project is None:
            QMessageBox.warning(
                self,
                "Enrichissement Excel",
                "Aucun projet local actif n'est disponible.",
            )
            return

        try:
            self.excel_update_badge.set_state("running", "Analyse")
            stats = self.excel_update_service.comparer_avec_sqlite(
                self.fichier_excel_mise_a_jour,
                project.database,
                apercu_limite=100,
            )
            self.excel_update_preview_stats = stats
            self.excel_update_preview.setPlainText(
                build_excel_update_preview_text(stats, detail_limit=20)
            )
            self.excel_update_badge.set_state("success", "Aperçu prêt")
            self.log(
                "📄 Excel : "
                f"{stats.get('correspondances_siret', 0)} prospect(s) "
                "retrouvé(s) par SIRET, "
                f"{stats.get('introuvables', 0)} introuvable(s), "
                "aucune écriture effectuée."
            )
            NotificationManager.success(
                "Analyse Excel terminée",
                f"{stats.get('correspondances_siret', 0)} prospect(s) "
                "retrouvé(s). Aucune donnée n'a été modifiée.",
            )
        except Exception as exc:
            self.excel_update_preview_stats = None
            self.excel_update_badge.set_state("error", "Erreur")
            QMessageBox.critical(
                self,
                "Erreur d'analyse Excel",
                str(exc),
            )

    def _create_recovery_point(self, action: str, project) -> bool:
        """Crée une sauvegarde automatique avant une action sensible.

        Retourne ``True`` si l'action peut continuer. En cas d'échec, l'utilisateur
        choisit explicitement s'il souhaite poursuivre sans point de restauration.
        """
        try:
            if action == "import":
                point = self.recovery_manager.before_import(project=project)
                label = "avant import"
            elif action == "enrichment":
                point = self.recovery_manager.before_enrichment(project=project)
                label = "avant enrichissement"
            else:
                point = self.recovery_manager.create_checkpoint(action, project=project)
                label = action.replace("_", " ").lower()

            NotificationManager.success(
                "Point de restauration créé",
                f"Sauvegarde {label} : {point.path.name}",
            )
            self.log(f"💾 Point de restauration créé : {point.path.name}")
            return True
        except Exception as exc:
            answer = QMessageBox.question(
                self,
                "Sauvegarde automatique impossible",
                "Form@Prospect n'a pas pu créer le point de restauration.\n\n"
                f"Détail : {exc}\n\n"
                "Voulez-vous continuer l'opération sans sauvegarde automatique ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            return answer == QMessageBox.Yes

    def mettre_a_jour_noms_recherche(self):
        """Ajoute les enseignes/sigles du fichier aux prospects déjà importés."""
        if not ApplicationState.has_project():
            QMessageBox.warning(self, "Attention", "Créez d'abord un projet depuis le Dashboard.")
            return
        if not self.fichier_excel:
            QMessageBox.warning(self, "Attention", "Choisissez d'abord le fichier Excel source.")
            return

        context = self.datasource_resolver.resolve()
        if context.is_cloud:
            QMessageBox.warning(
                self,
                "Projet Cloud",
                "La mise à jour des noms de recherche doit être faite sur le projet local avant déploiement.",
            )
            return

        project = context.project or ApplicationState.get_project()
        if not self._create_recovery_point("search_names", project):
            return

        try:
            stats = self.import_service.mettre_a_jour_noms_recherche_depuis_excel(
                self.fichier_excel,
                project.database,
            )
            updated = int(stats.get("mis_a_jour", 0))
            ActivityService.record(
                "Noms de recherche mis à jour",
                f"{updated} prospect(s) enrichi(s) avec enseigne/sigle/nom usuel.",
                category="enrichment",
                level="success",
                metadata=stats,
            )
            NotificationManager.success(
                "Noms de recherche ajoutés",
                f"{updated} prospect(s) disposent maintenant d'enseignes, sigles ou noms usuels supplémentaires.",
            )
            self.log(
                f"🏷️ Lot 2 : {updated} prospect(s) mis à jour avec des noms de recherche alternatifs."
            )
            if stats.get("ambigus_siren"):
                self.log(
                    f"ℹ️ {stats['ambigus_siren']} ligne(s) ignorée(s) car le SIREN correspond à plusieurs établissements sans SIRET exploitable."
                )
            self.rafraichir()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur mise à jour", str(exc))

    def importer_dans_sqlite(self):
        if not ApplicationState.has_project():
            QMessageBox.warning(self, "Attention", "Créez d'abord un projet depuis le Dashboard.")
            return
        if not self.fichier_excel:
            QMessageBox.warning(self, "Attention", "Choisissez d'abord un fichier Excel.")
            return
        try:
            project = ApplicationState.get_project()
            if not self._create_recovery_point("import", project):
                return
            total = self.import_service.importer_excel_vers_sqlite(self.fichier_excel, project.database)
            ActivityService.record("Import Excel terminé", f"{total} prospects importés.", category="import", level="success", metadata={"total": total})
            NotificationManager.success(
                "Import terminé",
                f"{total} prospects ont été importés dans le projet {project.name}.",
            )
            self.log(f"✅ Import terminé : {total} prospects importés.")
            self.rafraichir()
        except Exception as exc:
            QMessageBox.critical(self, "Erreur import", str(exc))

    def reinitialiser_sans_resultat(self):
        if self.enrichment_running or not ApplicationState.has_project():
            return
        project = ApplicationState.get_project()
        count = self.enrichment_service.compter_sans_resultat(project.database)
        if count <= 0:
            NotificationManager.info(
                "Aucun prospect à retraiter",
                "Aucun prospect n'est actuellement marqué sans résultat.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Retenter les prospects sans résultat",
            f"{count} prospect(s) vont redevenir disponibles pour l'enrichissement.\n\n"
            "Les coordonnées déjà présentes seront conservées. Seuls le statut "
            "et la date de collecte seront réinitialisés.\n\n"
            "Voulez-vous continuer ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if not self._create_recovery_point("retry_no_result", project):
            return

        reset_count = self.enrichment_service.reinitialiser_sans_resultat(
            project.database
        )
        ActivityService.record(
            "Prospects remis en attente d'enrichissement",
            f"{reset_count} prospect(s) sans résultat réinitialisé(s).",
            category="enrichment",
            level="info",
            metadata={"total": reset_count},
        )
        NotificationManager.success(
            "Prospects prêts à être retraités",
            f"{reset_count} prospect(s) peuvent maintenant être enrichis à nouveau.",
        )
        self.log(f"↻ {reset_count} prospect(s) sans résultat remis en attente.")
        self.rafraichir()

    def _set_enrichment_running(self, running):
        self.enrichment_running = running
        for button in (
            self.bouton_excel,
            self.bouton_importer,
            self.bouton_aliases,
            self.bouton_excel_mise_a_jour,
            self.bouton_analyser_mise_a_jour,
            self.bouton_test,
            self.bouton_enrichir,
            self.bouton_reenrichir_tout,
            self.bouton_reessayer,
        ):
            button.setEnabled(not running)
        self.bouton_pause.setEnabled(running)
        self.bouton_arreter.setEnabled(running)
        if not running:
            self.enrichment_paused = False
            self.bouton_pause.setText("⏸ Pause")

    def _reset_dashboard(self, total_expected):
        self.progression.setValue(0)
        self.progression.setFormat(f"0 / {total_expected} — 0 %")
        self.current_company_card.set_info("Initialisation...", "Préparation du moteur")
        self.badge_state.set_state("running", "Initialisation")
        self.metric_elapsed.set_value("00:00:00")
        self.metric_eta.set_value("—")
        self.metric_speed.set_value("0,0/min")
        self.metric_success.set_value("—")
        for card in self.stat_cards.values():
            card.set_value("0")
        self.journal.clear()

    def demarrer_enrichissement(
        self,
        limite=None,
        *,
        mode=EnrichmentService.MODE_PENDING,
    ):
        if self.enrichment_running:
            return
        if not ApplicationState.has_project():
            QMessageBox.warning(self, "Attention", "Aucun projet actif.")
            return

        context = self.datasource_resolver.resolve()
        if context.is_cloud:
            QMessageBox.warning(
                self,
                "Projet Cloud",
                "L'enrichissement doit être réalisé sur le projet local.",
            )
            return

        project = context.project or ApplicationState.get_project()
        total_cible = self.enrichment_service.compter_cible(
            project.database,
            mode=mode,
        )
        if total_cible == 0:
            message = (
                "Aucun prospect non enrichi n'est disponible."
                if mode == EnrichmentService.MODE_PENDING
                else "Aucun prospect n'est disponible dans ce projet."
            )
            NotificationManager.info("Enrichissement", message)
            return

        total_expected = (
            min(total_cible, limite)
            if limite is not None
            else total_cible
        )

        if mode == EnrichmentService.MODE_ALL:
            answer = QMessageBox.question(
                self,
                "Réenrichir toute la base",
                f"Vous allez réenrichir {total_cible} prospect(s).\n\n"
                "Les coordonnées issues de l'enrichissement (téléphones, "
                "site, email et réseaux sociaux) seront recalculées. Une "
                "ancienne valeur peut donc être remplacée ou supprimée si "
                "elle n'est plus retrouvée de façon fiable.\n\n"
                "En cas d'erreur technique, les anciennes coordonnées sont "
                "conservées.\n\n"
                "Voulez-vous continuer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        elif limite is None:
            answer = QMessageBox.question(
                self,
                "Enrichir les prospects non enrichis",
                f"Vous allez lancer l'enrichissement de {total_cible} "
                "prospect(s).\n\n"
                "Le traitement peut durer plusieurs heures. Il pourra être "
                "mis en pause ou arrêté.\n\n"
                "Voulez-vous continuer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        if not self._create_recovery_point("enrichment", project):
            return

        self._reset_dashboard(total_expected)
        self.enrichment_thread = QThread(self)
        self.enrichment_worker = EnrichmentWorker(
            str(project.database),
            limite,
            mode=mode,
        )
        self.enrichment_worker.moveToThread(self.enrichment_thread)
        self.enrichment_thread.started.connect(self.enrichment_worker.run)
        self.enrichment_worker.progress.connect(self.on_progress)
        self.enrichment_worker.finished.connect(self.on_finished)
        self.enrichment_worker.failed.connect(self.on_failed)
        self.enrichment_worker.paused_changed.connect(self.on_paused_changed)
        self.enrichment_worker.finished.connect(self.enrichment_thread.quit)
        self.enrichment_worker.failed.connect(self.enrichment_thread.quit)
        self.enrichment_thread.finished.connect(self._cleanup_thread)

        self._set_enrichment_running(True)
        mode_label = (
            "réenrichissement complet"
            if mode == EnrichmentService.MODE_ALL
            else "enrichissement des non enrichis"
        )
        ActivityService.record(
            "Enrichissement démarré",
            f"{mode_label} prévu sur {total_expected} prospect(s).",
            category="enrichment",
            level="info",
            metadata={"total": total_expected, "mode": mode},
        )
        self.log(
            f"🚀 Démarrage : {mode_label} sur {total_expected} prospect(s)."
        )
        self.enrichment_thread.start()

    def on_progress(self, stats):
        completed = stats.get("completed", 0)
        total = stats.get("total", 0)
        percentage = stats.get("percentage", 0)
        successful = stats.get("enrichis", 0)
        success_rate = (successful / completed * 100) if completed else 0

        self.progression.setValue(percentage)
        self.progression.setFormat(f"{completed} / {total} — {percentage} %")
        self.current_company_card.set_info(
            stats.get("entreprise") or "—", stats.get("message") or "Traitement en cours"
        )
        self.badge_state.set_state("running", "En cours")

        self.metric_elapsed.set_value(self._format_duration(stats.get("elapsed_seconds")))
        self.metric_eta.set_value(self._format_duration(stats.get("eta_seconds")))
        self.metric_speed.set_value(f"{stats.get('speed_per_minute', 0):.1f}/min")
        self.metric_success.set_value(f"{success_rate:.0f} %")

        for key, card in self.stat_cards.items():
            card.set_value(stats.get(key, 0))

        self.log(f"[{completed}/{total}] {stats.get('entreprise') or '—'} — {stats.get('message') or ''}")

    def basculer_pause(self):
        if not self.enrichment_worker:
            return
        if self.enrichment_paused:
            self.enrichment_worker.resume()
        else:
            self.enrichment_worker.pause()

    def on_paused_changed(self, paused):
        self.enrichment_paused = paused
        self.bouton_pause.setText("▶ Reprendre" if paused else "⏸ Pause")
        self.badge_state.set_state("running", "En pause" if paused else "En cours")
        self.log("⏸ Enrichissement en pause." if paused else "▶ Enrichissement repris.")

    def demander_arret(self):
        if self.enrichment_worker:
            self.enrichment_worker.request_stop()
            self.bouton_arreter.setEnabled(False)
            self.bouton_pause.setEnabled(False)
            self.badge_state.set_state("running", "Arrêt en cours")
            self.log("⏹ Arrêt demandé. Le traitement s'arrêtera après le prospect en cours...")

    def on_finished(self, result):
        self._set_enrichment_running(False)
        interrupted = result.get("interrompu", False)
        if not interrupted:
            self.progression.setValue(100)
            self.progression.setFormat("Terminé — 100 %")
            self.badge_state.set_state("success", "Terminé")
        else:
            self.badge_state.set_state("error", "Interrompu")

        self.current_company_card.set_info(
            "Traitement interrompu" if interrupted else "Enrichissement terminé",
            f"{result.get('enrichis', 0)} enrichi(s), "
            f"{result.get('sans_resultat', 0)} sans résultat, "
            f"{result.get('erreurs', 0)} erreur(s)",
        )
        self.log("⏹ Enrichissement interrompu." if interrupted else "✅ Enrichissement terminé.")
        self.log(
            "📊 Apports sources — "
            f"PagesJaunes: {result.get('source_pages_jaunes', 0)} | "
            f"Google Maps: {result.get('source_google_maps', 0)} | "
            f"SIREN réutilisé: {result.get('source_siren', 0)} | "
            f"Web secours: {result.get('source_web', 0)}"
        )
        self.log(
            "🏢 API SIREN — "
            f"{result.get('api_requests', 0)} requête(s) réseau | "
            f"{result.get('api_cache_hits', 0)} cache | "
            f"{result.get('api_failures', 0)} échec(s)"
        )
        ActivityService.record(
            "Enrichissement interrompu" if interrupted else "Enrichissement terminé",
            f"{result.get('enrichis', 0)} enrichi(s), "
            f"{result.get('sans_resultat', 0)} sans résultat, "
            f"{result.get('erreurs', 0)} erreur(s).",
            category="enrichment",
            level="warning" if interrupted else "success",
            metadata=result,
        )
        if interrupted:
            NotificationManager.warning(
                "Enrichissement interrompu",
                f"{result.get('enrichis', 0)} prospect(s) enrichi(s). La reprise reste possible.",
            )
        else:
            NotificationManager.success(
                "Enrichissement terminé",
                f"{result.get('enrichis', 0)} enrichi(s), "
                f"{result.get('sans_resultat', 0)} sans résultat, "
                f"{result.get('erreurs', 0)} erreur(s).",
            )
        self.rafraichir()

    def on_failed(self, message):
        self._set_enrichment_running(False)
        self.badge_state.set_state("error", "Erreur")
        self.current_company_card.set_info("Erreur d'enrichissement", message)
        ActivityService.record("Erreur d'enrichissement", message, category="enrichment", level="error")
        self.log(f"❌ Erreur générale : {message}")
        QMessageBox.critical(self, "Erreur enrichissement", message)
        self.rafraichir()

    def _cleanup_thread(self):
        if self.enrichment_worker:
            self.enrichment_worker.deleteLater()
        if self.enrichment_thread:
            self.enrichment_thread.deleteLater()
        self.enrichment_worker = None
        self.enrichment_thread = None

    def closeEvent(self, event):
        if self.enrichment_running:
            answer = QMessageBox.question(
                self,
                "Enrichissement en cours",
                "Un enrichissement est en cours. Voulez-vous l'arrêter avant de fermer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.demander_arret()
        event.accept()
