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
        self.enrichment_service = EnrichmentService()
        self.datasource_resolver = DataSourceResolver()
        self.recovery_manager = RecoveryManager()

        self.fichier_excel = None
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

        control_card = SectionCard(padding=20, spacing=14)
        control_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        control_header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_title = QLabel("Moteur d'enrichissement")
        header_title.setStyleSheet(f"font-size: 19px; font-weight: 900; color: {TEXT_PRIMARY};")
        header_subtitle = QLabel("Traitement reprenable, pilotable et enregistré prospect par prospect.")
        header_subtitle.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        header_text.addWidget(header_title)
        header_text.addWidget(header_subtitle)
        self.badge_state = StatusBadge("idle")
        control_header.addLayout(header_text, 1)
        control_header.addWidget(self.badge_state, 0, Qt.AlignTop)
        control_card.content_layout.addLayout(control_header)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        self.bouton_test = QPushButton(f"🧪 Tester sur {self.TEST_LIMIT} prospects")
        self.bouton_enrichir = QPushButton("🚀 Enrichir tous les prospects restants")
        self.bouton_reessayer = QPushButton("↻ Retenter les sans résultat")
        self.bouton_pause = QPushButton("⏸ Pause")
        self.bouton_arreter = QPushButton("⏹ Arrêter")
        for button in (
            self.bouton_test,
            self.bouton_enrichir,
            self.bouton_reessayer,
            self.bouton_pause,
            self.bouton_arreter,
        ):
            button.setFixedHeight(46)
        self.bouton_test.setStyleSheet(primary_button_style())
        self.bouton_enrichir.setStyleSheet(primary_button_style())
        self.bouton_reessayer.setStyleSheet(warning_button_style())
        self.bouton_pause.setStyleSheet(warning_button_style())
        self.bouton_arreter.setStyleSheet(danger_button_style())
        self.bouton_reessayer.setEnabled(False)
        self.bouton_pause.setEnabled(False)
        self.bouton_arreter.setEnabled(False)
        self.bouton_test.clicked.connect(lambda: self.demarrer_enrichissement(self.TEST_LIMIT))
        self.bouton_enrichir.clicked.connect(lambda: self.demarrer_enrichissement(None))
        self.bouton_reessayer.clicked.connect(self.reinitialiser_sans_resultat)
        self.bouton_pause.clicked.connect(self.basculer_pause)
        self.bouton_arreter.clicked.connect(self.demander_arret)
        action_layout.addWidget(self.bouton_test)
        action_layout.addWidget(self.bouton_enrichir, 1)
        action_layout.addWidget(self.bouton_reessayer)
        action_layout.addWidget(self.bouton_pause)
        action_layout.addWidget(self.bouton_arreter)
        control_card.content_layout.addLayout(action_layout)

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
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
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
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
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
            self.bouton_test.setEnabled(False)
            self.bouton_enrichir.setEnabled(False)
            self.bouton_reessayer.setEnabled(False)
            return

        remaining = self.enrichment_service.compter_a_enrichir(project.database)
        without_result = self.enrichment_service.compter_sans_resultat(project.database)
        self.label_projet.setText(f"Projet actif : {project.name}")
        self.label_details.setText(
            f"{remaining} prospect(s) restant(s) à enrichir | "
            f"{without_result} sans résultat retraitable(s)."
        )
        self.bouton_importer.setEnabled(True)
        self.bouton_aliases.setEnabled(bool(self.fichier_excel))
        self.bouton_test.setEnabled(remaining > 0)
        self.bouton_enrichir.setEnabled(remaining > 0)
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
            self.bouton_test,
            self.bouton_enrichir,
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

    def demarrer_enrichissement(self, limite=None):
        if self.enrichment_running:
            return
        if not ApplicationState.has_project():
            QMessageBox.warning(self, "Attention", "Aucun projet actif.")
            return

        project = ApplicationState.get_project()
        remaining = self.enrichment_service.compter_a_enrichir(project.database)
        if remaining == 0:
            NotificationManager.info(
                "Enrichissement terminé",
                "Tous les prospects du projet ont déjà été enrichis.",
            )
            return

        total_expected = min(remaining, limite) if limite is not None else remaining
        if limite is None:
            answer = QMessageBox.question(
                self,
                "Enrichissement complet",
                f"Vous allez lancer l'enrichissement de {remaining} prospect(s).\n\n"
                "Le traitement peut durer plusieurs heures. Il pourra être mis en pause ou arrêté.\n\n"
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
        self.enrichment_worker = EnrichmentWorker(str(project.database), limite)
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
        ActivityService.record("Enrichissement démarré", f"Traitement prévu sur {total_expected} prospect(s).", category="enrichment", level="info", metadata={"total": total_expected})
        self.log(f"🚀 Démarrage de l'enrichissement sur {total_expected} prospect(s).")
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
