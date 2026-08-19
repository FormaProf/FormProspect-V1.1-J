from math import ceil

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QColor
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
    QFrame,
    QGraphicsDropShadowEffect,
)

from core.constants import PRIMARY_COLOR
from core.application_state import ApplicationState
from core.datasource_resolver import DataSourceResolver
from core.crm import PIPELINE, PRIORITES
from services.prospect_service import ProspectService
from services.export_service import ExportService
from ui.dialogs.prospect_dialog import ProspectDialog
from ui.dialogs.client_onboarding_wizard import ClientOnboardingWizard
from ui.dialogs.cloud_client_onboarding_dialog import CloudClientOnboardingDialog
from ui.widgets.crm.filters_bar import CRMFiltersBar
from ui.widgets.crm.prospects_table import ProspectsTableWidget
from ui.widgets.crm.kanban_view import KanbanView
from ui.components.notifications import NotificationManager
from services.system import ActivityService
from core.session import SessionState
from services.cloud_runtime import CloudRuntime



class _WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class _FunctionWorker(QRunnable):
    """Exécute une fonction hors du thread graphique Qt."""

    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.function()
        except Exception as exc:
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class ProspectsPage(QWidget):
    """Page CRM principale.

    Cette page orchestre les composants CRM : barre de filtres, vue tableau,
    vue Kanban, services métier, pagination et fiche prospect. Les vues sont
    séparées dans des widgets dédiés afin de garder une architecture maintenable.
    """

    DISPLAY_LIMIT = 100

    def __init__(self):
        super().__init__()

        self.datasource_resolver = DataSourceResolver()
        self.prospect_service = ProspectService(
            resolver=self.datasource_resolver,
        )
        self.export_service = ExportService()
        self.current_prospects = []
        self.page_courante = 1
        self.total_filtre_courant = 0
        self.total_general_courant = 0
        self.total_pages = 1

        # Les appels Cloud sont exécutés hors du thread graphique.
        # Un seul worker à la fois évite les courses entre plusieurs rafraîchissements.
        self.worker_pool = QThreadPool(self)
        self.worker_pool.setMaxThreadCount(1)
        self._active_workers = set()
        self._load_generation = 0
        self._filter_options_loaded = False
        self._pending_pipeline_changes = set()

        self.setStyleSheet("background:#F8FAFD;")

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 26, 30, 30)
        layout.setSpacing(16)

        # --- Hero / entête CRM ---
        hero = QFrame()
        hero.setObjectName("CRMHero")
        hero.setStyleSheet("""
            QFrame#CRMHero {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FFFFFF,
                    stop:0.72 #F7FBFF,
                    stop:1 #EAF4FF
                );
                border: 1px solid #E4EBF4;
                border-radius: 22px;
            }
        """)
        self._apply_shadow(hero, blur=30, y=7, alpha=22)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 20, 18)
        hero_layout.setSpacing(16)

        hero_texts = QVBoxLayout()
        hero_texts.setSpacing(3)

        eyebrow = QLabel("CRM  •  PORTEFEUILLE COMMERCIAL")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.1px; "
            "color:#338CE4; border:none; background:transparent;"
        )

        titre = QLabel("Prospects & opportunités")
        titre.setStyleSheet(
            "font-size:28px; font-weight:900; color:#0B1220; "
            "border:none; background:transparent;"
        )

        self.label_info = QLabel("Aucun projet actif")
        self.label_info.setStyleSheet(
            "font-size:12px; color:#6B7A90; border:none; background:transparent;"
        )

        hero_texts.addWidget(eyebrow)
        hero_texts.addWidget(titre)
        hero_texts.addWidget(self.label_info)

        self.bouton_rafraichir = QPushButton("↻  Rafraîchir")
        self.bouton_rafraichir.setFixedHeight(40)
        self.bouton_rafraichir.clicked.connect(
            lambda: self.charger_prospects(force_refresh=True)
        )
        self.bouton_rafraichir.setStyleSheet(self.style_bouton_secondaire())

        hero_layout.addLayout(hero_texts, 1)
        hero_layout.addWidget(self.bouton_rafraichir)

        # --- Filtres ---
        self.filters_bar = CRMFiltersBar()
        self.filters_bar.setMinimumHeight(96)
        self.filters_bar.filters_changed.connect(
            lambda: self.appliquer_filtres(reset_page=True)
        )
        self.filters_bar.setStyleSheet("""
            QLineEdit, QComboBox {
                background:#FFFFFF;
                color:#0B1220;
                border:1px solid #DCE5EF;
                border-radius:10px;
                min-height:38px;
                padding:0 11px;
                font-size:12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border:2px solid #338CE4;
                background:#FFFFFF;
            }
            QLabel {
                color:#62748A;
                font-size:11px;
                font-weight:700;
                background:transparent;
                border:none;
            }
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                min-height:38px;
                padding:0 13px;
                font-weight:800;
            }
            QPushButton:hover {
                color:#338CE4;
                border-color:#AFCFF0;
                background:#F8FBFF;
            }
        """)

        filters_card = QFrame()
        filters_card.setObjectName("CRMCard")
        filters_card.setStyleSheet(self._card_style())
        self._apply_shadow(filters_card, blur=24, y=6, alpha=16)
        filters_layout = QVBoxLayout(filters_card)
        filters_layout.setContentsMargins(16, 14, 16, 18)
        filters_layout.setSpacing(10)
        filters_header = QHBoxLayout()
        filters_title = QLabel("Filtres intelligents")
        filters_title.setStyleSheet(
            "font-size:13px; font-weight:900; color:#23344D; "
            "border:none; background:transparent;"
        )
        filters_hint = QLabel("Affinez votre portefeuille en quelques secondes")
        filters_hint.setStyleSheet(
            "font-size:10px; color:#94A3B8; border:none; background:transparent;"
        )
        filters_header.addWidget(filters_title)
        filters_header.addSpacing(8)
        filters_header.addWidget(filters_hint)
        filters_header.addStretch()
        filters_layout.addLayout(filters_header)
        filters_layout.addWidget(self.filters_bar)

        # --- Barre d'actions ---
        actions_card = QFrame()
        actions_card.setObjectName("CRMCard")
        actions_card.setStyleSheet(self._card_style())
        self._apply_shadow(actions_card, blur=24, y=6, alpha=14)

        toolbar_layout = QHBoxLayout(actions_card)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        self.bouton_tableau = QPushButton("Tableau")
        self.bouton_kanban = QPushButton("Kanban")

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

        self.bouton_exporter = QPushButton("⇩  Exporter Excel")
        self.bouton_exporter.setFixedHeight(40)
        self.bouton_exporter.clicked.connect(self.exporter_excel)

        current_user = SessionState.user()
        current_role = str(
            getattr(current_user, "role", "") or ""
        ).strip().lower()
        self.bouton_exporter.setVisible(
            current_role != "commercial"
        )

        bouton_scoring = QPushButton("Calculer les scores")
        bouton_scoring.setFixedHeight(40)
        bouton_scoring.clicked.connect(self.recalculer_scores)

        self.bouton_exporter.setStyleSheet(self.style_bouton_secondaire())
        bouton_scoring.setStyleSheet(self.style_bouton_principal())

        toolbar_layout.addWidget(self.bouton_tableau)
        toolbar_layout.addWidget(self.bouton_kanban)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.bouton_exporter)
        toolbar_layout.addWidget(bouton_scoring)

        # --- Pagination compacte ---
        pagination_card = QFrame()
        pagination_card.setObjectName("CRMCard")
        pagination_card.setStyleSheet(self._card_style())
        pagination_layout = QHBoxLayout(pagination_card)
        pagination_layout.setContentsMargins(12, 9, 12, 9)
        pagination_layout.setSpacing(7)

        self.bouton_premiere_page = QPushButton("«")
        self.bouton_page_precedente = QPushButton("‹")
        self.label_pagination = QLabel("Page 1 / 1")
        self.bouton_page_suivante = QPushButton("›")
        self.bouton_derniere_page = QPushButton("»")
        self.label_affichage = QLabel("Aucun prospect affiché")

        self.bouton_premiere_page.setToolTip("Première page")
        self.bouton_page_precedente.setToolTip("Page précédente")
        self.bouton_page_suivante.setToolTip("Page suivante")
        self.bouton_derniere_page.setToolTip("Dernière page")

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
            bouton.setFixedSize(34, 34)
            bouton.setStyleSheet(self.style_bouton_secondaire())

        self.label_pagination.setStyleSheet(
            "font-size:12px; font-weight:900; color:#23344D; "
            "padding:0 8px; border:none; background:transparent;"
        )
        self.label_affichage.setStyleSheet(
            "font-size:11px; font-weight:650; color:#7A899C; "
            "border:none; background:transparent;"
        )

        pagination_layout.addWidget(self.bouton_premiere_page)
        pagination_layout.addWidget(self.bouton_page_precedente)
        pagination_layout.addWidget(self.label_pagination)
        pagination_layout.addWidget(self.bouton_page_suivante)
        pagination_layout.addWidget(self.bouton_derniere_page)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.label_affichage)
        pagination_layout.addStretch()

        # --- Vues CRM ---
        self.views_stack = QStackedWidget()
        self.views_stack.setStyleSheet(
            "QStackedWidget { background:transparent; border:none; }"
        )

        self.table = ProspectsTableWidget()
        self.table.prospect_double_clicked.connect(self.ouvrir_fiche_prospect)
        self.table.setStyleSheet("""
            QTableWidget, QTableView {
                background:#FFFFFF;
                alternate-background-color:#FBFDFF;
                color:#1F2937;
                border:1px solid #E4EBF4;
                border-radius:16px;
                gridline-color:#EEF2F6;
                selection-background-color:#EAF4FF;
                selection-color:#0B1220;
                font-size:11px;
            }
            QHeaderView::section {
                background:#F8FBFE;
                color:#53657C;
                border:none;
                border-bottom:1px solid #E7ECF3;
                padding:10px 7px;
                font-size:10px;
                font-weight:900;
            }
            QTableWidget::item, QTableView::item {
                padding:7px;
                border-bottom:1px solid #F0F3F7;
            }
        """)

        self.kanban = KanbanView()
        self.kanban.prospect_double_clicked.connect(self.ouvrir_fiche_prospect)
        self.kanban.pipeline_change_requested.connect(self.changer_pipeline_prospect)
        self.kanban.setStyleSheet("""
            QWidget { background:transparent; }
            QScrollArea { background:transparent; border:none; }
        """)

        self.views_stack.addWidget(self.table)
        self.views_stack.addWidget(self.kanban)

        view_card = QFrame()
        view_card.setObjectName("CRMViewCard")
        view_card.setStyleSheet("""
            QFrame#CRMViewCard {
                background:#FFFFFF;
                border:1px solid #E4EBF4;
                border-radius:18px;
            }
        """)
        self._apply_shadow(view_card, blur=26, y=7, alpha=16)
        view_layout = QVBoxLayout(view_card)
        view_layout.setContentsMargins(10, 10, 10, 10)
        view_layout.addWidget(self.views_stack)

        layout.addWidget(hero)
        layout.addWidget(filters_card)
        layout.addWidget(actions_card)
        layout.addWidget(pagination_card)
        layout.addWidget(view_card, 1)

        self.setLayout(layout)
        self.mettre_a_jour_pagination_ui()

    def _has_data_source(self):
        return (
            ApplicationState.has_project()
            or CloudRuntime.is_active()
        )

    def _data_context(self):
        if ApplicationState.has_project():
            return self.datasource_resolver.resolve()
        return None

    def _is_cloud(self):
        context = self._data_context()
        if context is not None:
            return context.is_cloud
        return CloudRuntime.is_active()

    def _database_path(self):
        context = self._data_context()
        if context is None:
            return None
        return None if context.is_cloud else context.project.database

    def _source_name(self):
        context = self._data_context()

        if context is None or context.is_cloud:
            user = SessionState.user()
            if user and user.organization_name:
                return user.organization_name
            return "Form@Prospect Cloud"

        return context.project.name

    @staticmethod
    def _apply_shadow(widget, *, blur=26, y=6, alpha=18):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(QColor(7, 27, 56, alpha))
        widget.setGraphicsEffect(effect)

    @staticmethod
    def _card_style():
        return """
            QFrame#CRMCard {
                background:#FFFFFF;
                border:1px solid #E7ECF3;
                border-radius:16px;
            }
        """

    def style_bouton_principal(self):
        return """
            QPushButton {
                background:#338CE4;
                color:white;
                border:none;
                border-radius:10px;
                font-size:12px;
                font-weight:850;
                padding:0 15px;
            }
            QPushButton:hover { background:#247BD0; }
            QPushButton:pressed { background:#1D66B2; }
            QPushButton:disabled {
                background:#E4E9EF;
                color:#9AA7B8;
            }
        """

    def style_bouton_secondaire(self):
        return """
            QPushButton {
                background:#FFFFFF;
                color:#334155;
                border:1px solid #DCE5EF;
                border-radius:10px;
                font-size:12px;
                font-weight:800;
                padding:0 12px;
            }
            QPushButton:hover {
                background:#F8FBFF;
                color:#338CE4;
                border-color:#AFCFF0;
            }
            QPushButton:pressed { background:#EEF6FF; }
            QPushButton:disabled {
                background:#F5F7FA;
                color:#A5B0BE;
                border-color:#E7ECF2;
            }
        """

    def style_bouton_vue(self):
        return """
            QPushButton {
                background:#F8FAFC;
                color:#53657C;
                border:1px solid #E3EAF2;
                border-radius:10px;
                font-size:12px;
                font-weight:850;
                padding:0 18px;
            }
            QPushButton:hover {
                background:#F3F8FE;
                color:#338CE4;
                border-color:#B7D5F1;
            }
            QPushButton:checked {
                background:#0B2A52;
                color:white;
                border:1px solid #0B2A52;
            }
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

    def _start_worker(
        self,
        function,
        *,
        on_result,
        on_error,
        on_finished=None,
    ):
        worker = _FunctionWorker(function)
        self._active_workers.add(worker)

        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)

        def cleanup():
            self._active_workers.discard(worker)
            if on_finished is not None:
                on_finished()

        worker.signals.finished.connect(cleanup)
        self.worker_pool.start(worker)

    @staticmethod
    def _filters_active(criteres):
        return any(
            str(value or "").strip()
            for value in criteres.values()
        )

    def charger_options_filtres(self):
        """
        Chargement synchrone conservé pour les rares appels locaux directs.

        L'ouverture du CRM utilise _lancer_chargement(), qui récupère les
        options dans un worker afin de ne jamais figer l'interface.
        """

        if not self._has_data_source():
            return

        try:
            database_path = self._database_path()
            options = self.prospect_service.recuperer_options_filtres(
                database_path
            )
            self.filters_bar.charger_options(
                options,
                pipelines_ordonnes=PIPELINE,
                priorites_ordonnees=PRIORITES,
            )
            self._filter_options_loaded = True

        except Exception as e:
            QMessageBox.warning(
                self,
                "Filtres",
                f"Impossible de charger les filtres :\n{e}",
            )

    def charger_prospects(self, force_refresh=False):
        if not self._has_data_source():
            QMessageBox.warning(
                self,
                "Attention",
                "Aucun projet actif.",
            )
            return

        if force_refresh:
            self.prospect_service.invalider_caches(
                statistiques=True,
                filtres=True,
            )
            self._filter_options_loaded = False

        self.page_courante = 1
        self._lancer_chargement(
            reset_page=False,
            reload_options=not self._filter_options_loaded,
        )

    def appliquer_filtres(
        self,
        reset_page=True,
        reload_options=False,
    ):
        if not self._has_data_source():
            self.current_prospects = []
            self.total_filtre_courant = 0
            self.total_general_courant = 0
            self.total_pages = 1
            self.mettre_a_jour_pagination_ui()
            return

        self._lancer_chargement(
            reset_page=reset_page,
            reload_options=reload_options,
        )

    def _lancer_chargement(
        self,
        *,
        reset_page,
        reload_options,
    ):
        database_path = self._database_path()
        criteres = dict(self.filters_bar.criteres())

        if reset_page:
            self.page_courante = 1

        requested_page = self.page_courante
        source_name = self._source_name()

        self._load_generation += 1
        generation = self._load_generation

        self.label_info.setText(
            f"Synchronisation du portefeuille • {source_name}…"
        )
        self.label_affichage.setText(
            "Actualisation des opportunités…"
        )
        self.bouton_rafraichir.setEnabled(False)

        def load_data():
            options = None

            if reload_options:
                options = (
                    self.prospect_service
                    .recuperer_options_filtres(database_path)
                )

            total_general = (
                self.prospect_service
                .compter_prospects(database_path)
            )

            if self._filters_active(criteres):
                total_filtered = (
                    self.prospect_service
                    .compter_prospects_filtres(
                        database_path,
                        **criteres,
                    )
                )
            else:
                total_filtered = total_general

            total_pages = self.calculer_total_pages(
                total_filtered
            )
            resolved_page = min(
                max(1, requested_page),
                total_pages,
            )
            offset = max(
                0,
                (resolved_page - 1) * self.DISPLAY_LIMIT,
            )

            prospects = (
                self.prospect_service
                .rechercher_prospects_filtres(
                    database_path,
                    **criteres,
                    limite=self.DISPLAY_LIMIT,
                    offset=offset,
                )
            )

            return {
                "generation": generation,
                "options": options,
                "total_general": total_general,
                "total_filtered": total_filtered,
                "total_pages": total_pages,
                "page": resolved_page,
                "prospects": prospects,
                "source_name": source_name,
            }

        def apply_result(payload):
            if payload["generation"] != self._load_generation:
                return

            if payload["options"] is not None:
                self.filters_bar.charger_options(
                    payload["options"],
                    pipelines_ordonnes=PIPELINE,
                    priorites_ordonnees=PRIORITES,
                )
                self._filter_options_loaded = True

            self.total_general_courant = payload[
                "total_general"
            ]
            self.total_filtre_courant = payload[
                "total_filtered"
            ]
            self.total_pages = payload["total_pages"]
            self.page_courante = payload["page"]
            self.current_prospects = payload["prospects"]

            self.mettre_a_jour_infos(
                payload["source_name"]
            )
            self.mettre_a_jour_pagination_ui()
            self.afficher_donnees_vue_active()

        def show_error(message):
            if generation != self._load_generation:
                return

            self.label_info.setText(
                "Chargement du CRM impossible"
            )
            QMessageBox.critical(
                self,
                "Erreur CRM",
                message,
            )

        def finish():
            if generation == self._load_generation:
                self.bouton_rafraichir.setEnabled(True)

        self._start_worker(
            load_data,
            on_result=apply_result,
            on_error=show_error,
            on_finished=finish,
        )

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

        old_pipeline = None
        for prospect in self.current_prospects:
            if str(prospect[0]) == str(prospect_id):
                old_pipeline = (
                    prospect[7]
                    if len(prospect) > 7
                    else None
                )
                break

        dialog = ProspectDialog(
            self._database_path(),
            prospect_id,
            is_cloud_mode=self._is_cloud(),
        )

        if dialog.exec():
            if getattr(
                dialog,
                "client_conversion_requested",
                False,
            ):
                self._ouvrir_formulaire_conversion_client(
                    prospect_id,
                    old_pipeline,
                )
                return

            self.prospect_service.invalider_caches(
                statistiques=True,
                filtres=True,
            )
            self._filter_options_loaded = False
            self.appliquer_filtres(
                reset_page=False,
                reload_options=True,
            )

    def changer_pipeline_prospect(
        self,
        prospect_id,
        nouveau_pipeline,
    ):
        if not self._has_data_source():
            return

        if prospect_id is None or not nouveau_pipeline:
            return

        prospect_key = str(prospect_id)

        if prospect_key in self._pending_pipeline_changes:
            return

        row_index = None
        old_pipeline = None

        for index, prospect in enumerate(
            self.current_prospects
        ):
            if str(prospect[0]) == prospect_key:
                row_index = index
                old_pipeline = (
                    prospect[7]
                    if len(prospect) > 7
                    else None
                )
                break

        if row_index is None:
            return

        if old_pipeline == nouveau_pipeline:
            return

        # Le statut Client est particulier : il ne doit jamais être validé
        # comme un simple changement de pipeline. On ouvre d'abord la fiche
        # client complète. Le pipeline Client n'est appliqué qu'après validation.
        if nouveau_pipeline == "🟢 Client":
            self._ouvrir_formulaire_conversion_client(
                prospect_id,
                old_pipeline,
            )
            return

        # Mise à jour visuelle immédiate : la carte se dépose sans attendre
        # la réponse du serveur Cloud.
        updated_row = list(
            self.current_prospects[row_index]
        )
        updated_row[7] = nouveau_pipeline
        self.current_prospects[row_index] = tuple(
            updated_row
        )
        self.afficher_donnees_vue_active()

        self._pending_pipeline_changes.add(prospect_key)
        database_path = self._database_path()

        def save_pipeline():
            return (
                self.prospect_service
                .mettre_a_jour_pipeline(
                    database_path,
                    prospect_id,
                    nouveau_pipeline,
                )
            )

        def save_succeeded(success):
            self._pending_pipeline_changes.discard(
                prospect_key
            )

            if not success:
                rollback(
                    "Le serveur n'a pas confirmé "
                    "la mise à jour du pipeline."
                )
                return

            # Avec un filtre actif, un rechargement silencieux remet la
            # liste en cohérence, sans bloquer l'interface.
            if self.filters_bar.filtres_actifs():
                self.appliquer_filtres(
                    reset_page=False
                )

        def rollback(message):
            self._pending_pipeline_changes.discard(
                prospect_key
            )

            for index, prospect in enumerate(
                self.current_prospects
            ):
                if str(prospect[0]) != prospect_key:
                    continue

                restored_row = list(prospect)
                restored_row[7] = old_pipeline
                self.current_prospects[index] = tuple(
                    restored_row
                )
                break

            self.afficher_donnees_vue_active()
            QMessageBox.critical(
                self,
                "Erreur pipeline",
                "Impossible de déplacer le prospect :\n"
                f"{message}",
            )

        self._start_worker(
            save_pipeline,
            on_result=save_succeeded,
            on_error=rollback,
        )


    def _ouvrir_formulaire_conversion_client(
        self,
        prospect_id,
        old_pipeline,
    ) -> None:
        """Ouvre la fiche client complète avant de valider le statut Client."""

        if self._is_cloud():
            dialog = CloudClientOnboardingDialog(
                str(prospect_id),
                self,
            )
        else:
            if not self._has_data_source():
                QMessageBox.warning(
                    self,
                    "Transformation",
                    "Aucun projet actif.",
                )
                return

            projet = ApplicationState.get_project()
            if projet is None:
                QMessageBox.warning(
                    self,
                    "Transformation",
                    "Aucun projet local actif.",
                )
                return

            dialog = ClientOnboardingWizard(
                projet.database,
                projet.folder,
                int(prospect_id),
                self,
            )

        if not dialog.exec():
            # Si le déplacement venait du Kanban, on redessine la vue
            # avec le statut précédent. Aucune conversion n'est enregistrée.
            self.afficher_donnees_vue_active()
            return

        prospect_key = str(prospect_id)
        for index, prospect in enumerate(self.current_prospects):
            if str(prospect[0]) != prospect_key:
                continue

            updated_row = list(prospect)
            updated_row[7] = "🟢 Client"
            self.current_prospects[index] = tuple(updated_row)
            break

        self.prospect_service.invalider_caches(
            statistiques=True,
            filtres=True,
        )
        self._filter_options_loaded = False
        self.appliquer_filtres(
            reset_page=False,
            reload_options=True,
        )

        QMessageBox.information(
            self,
            "Client créé",
            "La fiche client a été validée.\\n\\n"
            "Le prospect est maintenant qualifié en Client.",
        )



    def transformer_selection_en_client(self):
        """Compatibilité interne : conversion normale via Pipeline -> Client."""
        if self.views_stack.currentIndex() != 0:
            return

        row = self.table.currentRow()
        prospect_id = (
            self.table.prospect_id_from_row(row)
            if row >= 0
            else None
        )
        if prospect_id is None:
            return

        old_pipeline = None
        for prospect in self.current_prospects:
            if str(prospect[0]) == str(prospect_id):
                old_pipeline = (
                    prospect[7]
                    if len(prospect) > 7
                    else None
                )
                break

        self._ouvrir_formulaire_conversion_client(
            prospect_id,
            old_pipeline,
        )


    def recalculer_scores(self):
        if self._is_cloud():
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
        current_user = SessionState.user()
        current_role = str(
            getattr(current_user, "role", "") or ""
        ).strip().lower()

        # Double sécurité : même déclenchée autrement que par le bouton,
        # la fonction reste interdite aux commerciaux.
        if current_role == "commercial":
            QMessageBox.warning(
                self,
                "Export interdit",
                "Votre profil commercial ne permet pas d'exporter les données.",
            )
            return

        if self._is_cloud():
            QMessageBox.information(
                self,
                "Export",
                "L'export Cloud sera activé dans un prochain lot.",
            )
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

