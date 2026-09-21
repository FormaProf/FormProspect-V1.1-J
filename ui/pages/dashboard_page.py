
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.application_state import ApplicationState
from core.constants import PRIMARY_COLOR
from core.crm import PIPELINE, PIPELINE_COLORS
from core.session import SessionState
from core.theme_settings import get_theme_preference
from core.theme import BACKGROUND_COLOR, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
from services.backup_service import BackupService
from services.dashboard_service import DashboardService
from services.project_deployment_service import (
    ProjectDeploymentError,
    ProjectDeploymentService,
)
from services.project_manager import ProjectManager
from services.system import ActivityService
from ui.components.notifications import NotificationManager
from ui.dialogs.new_project_dialog import NewProjectDialog
from services.cloud_runtime import CloudRuntime
from ui.dialogs.cloud_deployment_dialog import (
    CloudDeploymentDialog,
)
from ui.dialogs.project_archive_dialog import ProjectArchiveDialog
from ui.widgets.dashboard_charts import HorizontalBarChart, QualityDonut
from ui.dashboard_premium_theme import dashboard_palette, dashboard_stylesheet


class DashboardPage(QWidget):
    """Dashboard Premium : centre de commandement de Form@Prospect."""

    WEEKLY_QUOTES = [('Persévérance', 'La constance transforme ce qui paraît lent en progrès durable.'), ('Courage', 'Le courage commence souvent au moment précis où l’on pourrait renoncer.'), ('Discipline', 'La discipline donne une direction aux jours où la motivation se tait.'), ('Temps', 'Ce que l’on construit avec patience résiste mieux à l’urgence.'), ('Échec', 'Un échec observé avec lucidité devient une information utile.'), ('Progression', 'Avancer de peu reste avancer.'), ('Confiance', 'La confiance se construit par des actes répétés, pas par des promesses.'), ('Persévérance', 'Les résultats visibles arrivent souvent après une longue période de travail invisible.'), ('Courage', 'Faire ce qui doit être fait malgré le doute est déjà une forme de victoire.'), ('Discipline', 'Les habitudes modestes finissent par produire des écarts immenses.'), ('Temps', 'Le temps ne récompense pas la précipitation, mais la continuité.'), ('Échec', 'Ce qui n’a pas fonctionné indique parfois plus clairement la prochaine direction.'), ('Progression', 'Ne mesure pas seulement la distance restante ; regarde aussi celle déjà parcourue.'), ('Confiance', 'La compétence nourrit une confiance plus solide que l’apparence.'), ('Persévérance', 'La répétition n’est pas un manque d’imagination lorsqu’elle construit la maîtrise.'), ('Courage', 'Il faut parfois accepter l’inconfort présent pour protéger l’avenir que l’on veut.'), ('Discipline', 'Faire l’essentiel avant l’urgent change la trajectoire d’une journée.'), ('Temps', 'Tout n’a pas besoin d’être accéléré pour être amélioré.'), ('Échec', 'Une erreur reconnue tôt coûte moins cher qu’une certitude défendue trop longtemps.'), ('Progression', 'Le progrès durable préfère la régularité aux exploits occasionnels.'), ('Confiance', 'On devient plus sûr de soi en tenant les engagements pris envers soi-même.'), ('Persévérance', 'Certaines portes ne s’ouvrent pas à la force, mais à la constance.'), ('Courage', 'Décider malgré l’incertitude est souvent le premier acte du courage.'), ('Discipline', 'La liberté de demain se prépare dans la discipline d’aujourd’hui.'), ('Temps', 'Ce que tu fais régulièrement finit par compter davantage que ce que tu fais intensément.'), ('Échec', 'Tomber n’apprend rien par lui-même ; comprendre pourquoi, oui.'), ('Progression', 'Une journée imparfaite peut tout de même contenir un pas utile.'), ('Confiance', 'La confiance grandit lorsque l’on cesse d’attendre la certitude parfaite.'), ('Persévérance', 'La patience active consiste à continuer de construire sans exiger un résultat immédiat.'), ('Courage', 'Le courage n’efface pas la peur ; il l’empêche de décider à ta place.'), ('Discipline', 'La discipline simplifie ce que l’hésitation complique.'), ('Temps', 'Le bon rythme est celui que tu peux encore tenir demain.'), ('Échec', 'Chaque difficulté mérite une question : qu’est-ce qu’elle peut m’apprendre ?'), ('Progression', 'La progression n’est pas toujours spectaculaire ; elle est souvent silencieuse.'), ('Confiance', 'La confiance la plus utile est celle qui accepte encore d’apprendre.'), ('Persévérance', 'Continuer intelligemment vaut mieux que recommencer sans comprendre.'), ('Courage', 'Il existe des moments où avancer prudemment demande plus de courage que foncer.'), ('Discipline', 'Choisir ses priorités, c’est aussi choisir ce que l’on accepte de laisser attendre.'), ('Temps', 'Certaines réponses deviennent évidentes seulement après avoir laissé le temps faire son travail.'), ('Échec', 'Le revers n’efface pas le chemin parcouru.'), ('Progression', 'Comparer ton présent à ton passé est souvent plus juste que le comparer aux autres.'), ('Confiance', 'La confiance n’est pas croire que tout sera facile, mais savoir que l’on saura s’adapter.'), ('Persévérance', 'Les petits efforts répétés ont une mémoire.'), ('Courage', 'Dire non à ce qui détourne de l’essentiel est aussi une forme de courage.'), ('Discipline', 'Une bonne routine protège l’énergie des décisions inutiles.'), ('Temps', 'Il y a un moment pour accélérer et un moment pour consolider.'), ('Échec', 'Ce qui échoue peut encore avoir servi : à préciser, simplifier ou réorienter.'), ('Progression', 'Ce qui compte n’est pas d’aller vite, mais de ne pas marcher au hasard.'), ('Confiance', 'Se préparer sérieusement est une manière concrète de croire en soi.'), ('Persévérance', 'La difficulté d’aujourd’hui peut devenir la facilité de demain par répétition.'), ('Courage', 'Le premier pas n’a pas besoin d’être grand ; il doit seulement être réel.'), ('Discipline', 'La qualité d’un projet se joue souvent dans ce que personne ne voit.')]

    PREMIUM_BLUE = "#338CE4"
    PREMIUM_BLUE_SOFT = "#EAF4FF"
    PREMIUM_NAVY = "#071B38"
    PREMIUM_TEXT = "#0B1220"
    PREMIUM_MUTED = "#6B7A90"
    PREMIUM_BORDER = "#E7ECF3"
    PREMIUM_BG = "#F8FAFD"

    def __init__(self):
        super().__init__()
        self.dashboard_service = DashboardService()
        self.project_manager = ProjectManager()
        self.backup_service = BackupService()
        self.deployment_service = ProjectDeploymentService()
        self._cloud_assignment_checked_for: set[str] = set()
        self.kpi_values: dict[str, QLabel] = {}
        self.pipeline_values: dict[str, QLabel] = {}
        self.action_values: dict[str, QLabel] = {}
        self._theme_mode = get_theme_preference()
        self._status_kind = "ready"
        self._last_activity_events = []
        self._pipeline_frames: list[tuple[QFrame, str]] = []
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.dashboard_scroll = QScrollArea()
        self.dashboard_scroll.setObjectName("DashboardScroll")
        self.dashboard_scroll.setWidgetResizable(True)
        self.dashboard_scroll.setFrameShape(QFrame.NoFrame)
        self.dashboard_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.dashboard_content = QWidget()
        self.dashboard_content.setObjectName("DashboardContent")
        root = QVBoxLayout(self.dashboard_content)
        root.setContentsMargins(28, 22, 28, 30)
        root.setSpacing(12)

        # 1) Contexte et commandes.
        root.addWidget(self._build_header())

        # 2) La citation reste volontairement en haut du cockpit.
        root.addWidget(self._build_quote_card())

        # 3) Les six indicateurs essentiels tiennent sur une seule ligne.
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10)
        kpi_grid.setVerticalSpacing(10)
        kpis = [
            ("prospects", "Prospects", "👥", "Base active"),
            ("telephones", "Téléphones", "📞", "Contacts joignables"),
            ("emails", "Emails", "✉️", "Adresses disponibles"),
            ("sites", "Sites web", "🌐", "Présence digitale"),
            ("average_prospect_score", "Score moyen", "🎯", "Potentiel commercial"),
            (
                "annual_revenue",
                (
                    f"Commissions {datetime.now().year}"
                    if self._is_commercial()
                    else f"CA annuel {datetime.now().year}"
                ),
                "€",
                (
                    "Commissions générées"
                    if self._is_commercial()
                    else "Ventes signées"
                ),
            ),
        ]
        for column, (key, title, icon, caption) in enumerate(kpis):
            card, value = self._metric_card(title, icon, caption)
            self.kpi_values[key] = value
            kpi_grid.addWidget(card, 0, column)
            kpi_grid.setColumnStretch(column, 1)
        root.addLayout(kpi_grid)

        # 4) Le coeur opérationnel est visible sans parcourir une longue page.
        command_grid = QGridLayout()
        command_grid.setHorizontalSpacing(12)
        command_grid.setVerticalSpacing(12)
        command_grid.setColumnStretch(0, 3)
        command_grid.setColumnStretch(1, 2)
        command_grid.addWidget(self._build_pipeline_card(), 0, 0)
        command_grid.addWidget(self._build_actions_card(), 0, 1)
        root.addLayout(command_grid)

        # 5) Santé de la base : contact, qualité et progression sur une ligne.
        health_grid = QGridLayout()
        health_grid.setHorizontalSpacing(12)
        health_grid.setVerticalSpacing(12)
        health_grid.setColumnStretch(0, 2)
        health_grid.setColumnStretch(1, 1)
        health_grid.setColumnStretch(2, 1)

        contact_card = self._section(
            "Données de contact",
            "Richesse exploitable de votre base.",
            "BASE COMMERCIALE",
        )
        self.contact_chart = HorizontalBarChart()
        self.contact_chart.setMaximumHeight(150)
        self.contact_chart.setMinimumHeight(132)
        self.contact_empty = QLabel("Aucune donnée à afficher pour le moment.")
        self.contact_empty.setObjectName("DashboardEmptyText")
        self.contact_empty.setAlignment(Qt.AlignCenter)
        self.contact_empty.setFixedHeight(38)
        contact_card.layout().addWidget(self.contact_chart)
        contact_card.layout().addWidget(self.contact_empty)
        health_grid.addWidget(contact_card, 0, 0)

        quality_card = self._section(
            "Qualité",
            "Complétude des informations de contact.",
            "QUALITÉ BASE",
        )
        self.quality_donut = QualityDonut()
        self.quality_donut.setMaximumHeight(145)
        self.quality_donut.setMinimumHeight(132)
        self.quality_details = QLabel("Aucun projet actif")
        self.quality_details.setObjectName("DashboardBodyMuted")
        self.quality_details.setAlignment(Qt.AlignCenter)
        self.quality_details.setWordWrap(True)
        quality_card.layout().addWidget(self.quality_donut)
        quality_card.layout().addWidget(self.quality_details)
        health_grid.addWidget(quality_card, 0, 1)

        health_grid.addWidget(self._build_enrichment_card(), 0, 2)
        root.addLayout(health_grid)

        # 6) Priorisation et historique ferment la page sans grand espace mort.
        bottom_grid = QGridLayout()
        bottom_grid.setHorizontalSpacing(12)
        bottom_grid.setVerticalSpacing(12)
        bottom_grid.setColumnStretch(0, 3)
        bottom_grid.setColumnStretch(1, 2)
        bottom_grid.addWidget(self._build_scoring_card(), 0, 0)
        bottom_grid.addWidget(self._build_recent_activity_card(), 0, 1)
        root.addLayout(bottom_grid)

        self.dashboard_scroll.setWidget(self.dashboard_content)
        main.addWidget(self.dashboard_scroll)
        self._apply_visual_theme()

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("DashboardHero")
        frame.setMinimumHeight(112)
        self._apply_shadow(frame, blur=30, y=7, alpha=24)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(22, 17, 18, 17)
        layout.setSpacing(16)

        texts = QVBoxLayout()
        texts.setSpacing(3)

        eyebrow = QLabel("FORM@PROSPECT  •  PILOTAGE COMMERCIAL")
        eyebrow.setObjectName("DashboardEyebrow")

        self.title = QLabel("Bonjour 👋")
        self.title.setObjectName("DashboardTitle")

        self.subtitle = QLabel(
            "Ouvrez un projet pour afficher votre centre de commandement."
        )
        self.subtitle.setObjectName("DashboardSubtitle")

        self.hero_status = QLabel("●  Prêt à prospecter")
        self.hero_status.setObjectName("DashboardStatus")

        texts.addWidget(eyebrow)
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)
        texts.addWidget(self.hero_status)

        context = QFrame()
        context.setObjectName("DashboardContext")
        context_layout = QVBoxLayout(context)
        context_layout.setContentsMargins(13, 10, 13, 10)
        context_layout.setSpacing(2)

        context_label = QLabel("ESPACE ACTIF")
        context_label.setObjectName("DashboardContextLabel")
        self.context_project_value = QLabel("Aucun projet actif")
        self.context_project_value.setObjectName("DashboardContextValue")
        self.context_project_value.setWordWrap(True)
        self.context_source_value = QLabel("Aucune source")
        self.context_source_value.setObjectName("DashboardContextSource")
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_project_value)
        context_layout.addWidget(self.context_source_value)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        self.new_project_button = None
        self.open_project_button = None
        self.deploy_button = None
        self.archive_button = None
        self._header_buttons = []

        buttons = (
            ("＋ Nouveau", self.ouvrir_nouveau_projet),
            ("📂 Ouvrir", self.ouvrir_projet_existant),
            ("💾 Sauver", self.sauvegarder_projet),
            ("☁ Déployer", self.deploy_project),
            ("📦 Archives", self.ouvrir_archives_projets),
            ("↻", self.rafraichir),
        )
        for index, (label, slot) in enumerate(buttons):
            button = QPushButton(label)
            button.setFixedHeight(38)
            button.clicked.connect(slot)
            if "Nouveau" in label:
                self.new_project_button = button
            elif "Ouvrir" in label:
                self.open_project_button = button
            elif "Déployer" in label:
                self.deploy_button = button
            elif "Archives" in label:
                self.archive_button = button
            button.setProperty(
                "dashboardButtonKind",
                "primary" if index in (0, 3) else "secondary",
            )
            button.setStyleSheet(
                self._button_style()
                if index in (0, 3)
                else self._secondary_header_button_style()
            )
            self._header_buttons.append(button)
            actions.addWidget(button)

        self._apply_role_permissions()

        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(context)
        right.addLayout(actions)

        layout.addLayout(texts, 1)
        layout.addLayout(right)
        return frame

    def _button_style(self):
        p = dashboard_palette(self._theme_mode)
        return f"""
            QPushButton {{
                background: {p['primary']};
                color: #FFFFFF;
                border: 1px solid {p['primary']};
                border-radius: 10px;
                padding: 0 13px;
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {p['primary_hover']};
                border-color: {p['primary_hover']};
            }}
            QPushButton:pressed {{ background: {p['primary_pressed']}; }}
            QPushButton:disabled {{
                background: {p['button_disabled']};
                color: {p['muted_light']};
                border-color: {p['border']};
            }}
        """

    def _secondary_header_button_style(self):
        p = dashboard_palette(self._theme_mode)
        return f"""
            QPushButton {{
                background: {p['button_bg']};
                color: {p['text_soft']};
                border: 1px solid {p['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {p['button_hover_bg']};
                color: {p['primary']};
                border-color: {p['primary_soft_border']};
            }}
            QPushButton:disabled {{
                background: {p['button_disabled']};
                color: {p['muted_light']};
                border-color: {p['border']};
            }}
        """

    def _deployed_button_style(self):
        p = dashboard_palette(self._theme_mode)
        return f"""
            QPushButton {{
                background: {p['success']};
                color: white;
                border: 1px solid {p['success']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 800;
            }}
            QPushButton:disabled {{
                background: {p['success']};
                color: white;
            }}
        """

    @staticmethod
    def _connected_first_name() -> str:
        """Retourne le prénom du compte connecté pour le message d'accueil."""
        user = SessionState.user()
        if user is None:
            return ""

        first_name = str(getattr(user, "first_name", "") or "").strip()
        if first_name:
            return first_name[:1].upper() + first_name[1:].lower()

        display_name = str(getattr(user, "display_name", "") or "").strip()
        if display_name:
            first_word = display_name.split()[0]
            return first_word[:1].upper() + first_word[1:].lower()

        username = str(getattr(user, "username", "") or "").strip()
        if username:
            first_word = username.split()[0]
            return first_word[:1].upper() + first_word[1:].lower()

        return ""

    def _update_greeting(self) -> None:
        first_name = self._connected_first_name()
        self.title.setText(
            f"Bonjour {first_name} 👋" if first_name else "Bonjour 👋"
        )

    def _current_role(self) -> str:
        user = SessionState.user()
        if user is None:
            return ""
        return str(getattr(user, "role", "") or "").strip().lower()

    def _is_commercial(self) -> bool:
        return self._current_role() == "commercial"

    def _can_manage_project_archives(self) -> bool:
        return self._current_role() in {
            "admin",
            "administrator",
            "administrateur",
            "manager",
        }

    def _apply_role_permissions(self) -> None:
        """Applique les droits visibles de gestion des projets."""
        commercial = self._is_commercial()

        for button in (
            self.new_project_button,
            self.open_project_button,
        ):
            if button is not None:
                button.setEnabled(not commercial)
                button.setToolTip(
                    "Fonction réservée à l'administration."
                    if commercial
                    else ""
                )

        if self.archive_button is not None:
            allowed = self._can_manage_project_archives()
            self.archive_button.setEnabled(allowed)
            self.archive_button.setToolTip(
                ""
                if allowed
                else "Archivage réservé à l'administrateur et au manager."
            )

        if commercial and self.deploy_button is not None:
            self.deploy_button.setText("☁ Déployer")
            self.deploy_button.setEnabled(False)
            self.deploy_button.setStyleSheet(self._button_style())
            self.deploy_button.setToolTip(
                "Le déploiement d'un projet est réservé à l'administration."
            )

    def _update_deploy_button(self, project=None):
        """Actualise l'état visuel du bouton de déploiement Cloud."""

        if self.deploy_button is None:
            return

        if self._is_commercial():
            self._apply_role_permissions()
            return

        if project is None:
            self.deploy_button.setText("☁ Déployer")
            self.deploy_button.setEnabled(False)
            self.deploy_button.setToolTip(
                "Créez ou ouvrez un projet avant de le déployer."
            )
            self.deploy_button.setStyleSheet(self._button_style())
            return

        try:
            cloud = self.deployment_service.get_deployment_status(project)
            deployed = self.deployment_service.is_deployed(project)
        except Exception:
            self.deploy_button.setText("☁ État indisponible")
            self.deploy_button.setEnabled(False)
            self.deploy_button.setToolTip(
                "Impossible de lire l'état Cloud du projet."
            )
            self.deploy_button.setStyleSheet(self._button_style())
            return

        if deployed:
            project_id = str(cloud.get("project_id") or "").strip()

            if project_id and CloudRuntime.is_active():
                try:
                    cloud_project = CloudRuntime.api().get_project(project_id)
                    if str(cloud_project.get("status") or "").lower() == "archived":
                        self.deploy_button.setText("☁ Projet archivé")
                        self.deploy_button.setEnabled(False)
                        self.deploy_button.setStyleSheet(
                            self._secondary_header_button_style()
                        )
                        self.deploy_button.setToolTip(
                            "Restaurez ce projet depuis « Archives » avant de le synchroniser."
                        )
                        return
                except Exception:
                    pass

            self.deploy_button.setText("☁ Synchroniser")
            self.deploy_button.setEnabled(True)
            self.deploy_button.setStyleSheet(self._deployed_button_style())
            self.deploy_button.setToolTip(
                (
                    f"Synchroniser les données locales avec le projet Cloud : {project_id}"
                    if project_id
                    else "Synchroniser ce projet avec le Cloud."
                )
            )
            return

        self.deploy_button.setText("☁ Déployer")
        self.deploy_button.setEnabled(True)
        self.deploy_button.setStyleSheet(self._button_style())
        self.deploy_button.setToolTip(
            "Créer ce projet dans Form@Prospect Cloud."
        )

    def _apply_visual_theme(self):
        self._theme_mode = get_theme_preference()
        self.setStyleSheet(dashboard_stylesheet(self._theme_mode))

        for chart in (
            getattr(self, "contact_chart", None),
            getattr(self, "quality_donut", None),
            getattr(self, "scoring_chart", None),
        ):
            apply_theme = getattr(chart, "apply_theme", None)
            if callable(apply_theme):
                apply_theme(self._theme_mode)

        for frame, accent in getattr(self, "_pipeline_frames", []):
            self._style_pipeline_frame(frame, accent)

        for button in getattr(self, "_header_buttons", []):
            if button is getattr(self, "deploy_button", None):
                text = button.text()
                if "Synchroniser" in text:
                    button.setStyleSheet(self._deployed_button_style())
                elif "archivé" in text.lower():
                    button.setStyleSheet(
                        self._secondary_header_button_style()
                    )
                else:
                    button.setStyleSheet(self._button_style())
                continue

            kind = str(button.property("dashboardButtonKind") or "")
            button.setStyleSheet(
                self._button_style()
                if kind == "primary"
                else self._secondary_header_button_style()
            )

        self._set_hero_status(
            getattr(self.hero_status, "text", lambda: "")(),
            self._status_kind,
        )
        self._render_activity(self._last_activity_events)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_visual_theme()

    def _set_hero_status(self, text: str, kind: str = "ready") -> None:
        self._status_kind = str(kind or "ready")
        self.hero_status.setText(text)
        p = dashboard_palette(self._theme_mode)
        color = (
            p["success"]
            if self._status_kind == "ready"
            else p["primary"]
        )
        self.hero_status.setStyleSheet(
            f"color:{color}; background:transparent; border:none;"
        )

    @staticmethod
    def _apply_shadow(widget, *, blur=28, y=6, alpha=20):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(QColor(2, 12, 27, alpha))
        widget.setGraphicsEffect(effect)

    def _section(self, title: str, subtitle: str = "", eyebrow: str = ""):
        card = QFrame()
        card.setObjectName("DashboardCard")
        self._apply_shadow(card, blur=22, y=5, alpha=16)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 14, 17, 16)
        layout.setSpacing(5)

        if eyebrow:
            eyebrow_label = QLabel(eyebrow)
            eyebrow_label.setObjectName("DashboardSectionEyebrow")
            layout.addWidget(eyebrow_label)

        title_label = QLabel(title)
        title_label.setObjectName("DashboardSectionTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("DashboardSectionSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        layout.addSpacing(2)
        return card

    def _metric_card(self, title: str, icon: str, caption: str = ""):
        card = QFrame()
        card.setObjectName("DashboardMetric")
        card.setMinimumHeight(96)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setAttribute(Qt.WA_Hover, True)
        self._apply_shadow(card, blur=18, y=4, alpha=13)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        head = QHBoxLayout()
        head.setSpacing(6)

        icon_chip = QLabel(icon)
        icon_chip.setObjectName("DashboardMetricIcon")
        icon_chip.setFixedSize(28, 28)
        icon_chip.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("DashboardMetricTitle")
        title_label.setWordWrap(True)
        head.addWidget(icon_chip)
        head.addWidget(title_label, 1)

        value = QLabel("0")
        value.setObjectName("DashboardMetricValue")
        value.setWordWrap(True)

        caption_label = QLabel(caption)
        caption_label.setObjectName("DashboardMetricCaption")
        caption_label.setWordWrap(True)

        layout.addLayout(head)
        layout.addWidget(value)
        layout.addWidget(caption_label)
        return card, value

    def _build_quote_card(self):
        week = max(1, datetime.now().isocalendar().week)
        theme, quote = self.WEEKLY_QUOTES[(week - 1) % len(self.WEEKLY_QUOTES)]

        card = QFrame()
        card.setObjectName("WeeklyQuoteCard")
        card.setMinimumHeight(82)
        self._apply_shadow(card, blur=26, y=6, alpha=28)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 12, 20, 12)
        layout.setSpacing(13)

        badge = QLabel("✦")
        badge.setObjectName("DashboardQuoteIcon")
        badge.setFixedSize(38, 38)
        badge.setAlignment(Qt.AlignCenter)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        overline = QLabel(f"IMPULSION DE LA SEMAINE  •  {theme.upper()}")
        overline.setObjectName("DashboardQuoteOverline")
        quote_label = QLabel(f"« {quote} »")
        quote_label.setObjectName("DashboardQuoteText")
        quote_label.setWordWrap(True)
        author = QLabel("— Form@Prospect")
        author.setObjectName("DashboardQuoteAuthor")
        texts.addWidget(overline)
        texts.addWidget(quote_label)
        texts.addWidget(author)

        layout.addWidget(badge)
        layout.addLayout(texts, 1)
        return card

    def _build_enrichment_card(self):
        card = self._section(
            "Enrichissement",
            "Avancement du traitement des prospects.",
            "DATA FLOW",
        )
        self.enrichment_label = QLabel("0 / 0 prospects enrichis")
        self.enrichment_label.setObjectName("DashboardBodyStrong")

        self.enrichment_progress = QProgressBar()
        self.enrichment_progress.setObjectName("EnrichmentProgress")
        self.enrichment_progress.setRange(0, 100)
        self.enrichment_progress.setValue(0)
        self.enrichment_progress.setFixedHeight(17)

        self.enrichment_detail = QLabel("Aucune donnée")
        self.enrichment_detail.setObjectName("DashboardBodyMuted")
        self.enrichment_detail.setWordWrap(True)

        card.layout().addWidget(self.enrichment_label)
        card.layout().addWidget(self.enrichment_progress)
        card.layout().addWidget(self.enrichment_detail)
        card.layout().addStretch(1)
        return card

    def _set_health_compact(self, compact: bool) -> None:
        """Réduit la ligne santé uniquement quand aucun projet n'est actif."""
        if compact:
            self.quality_donut.setMinimumHeight(78)
            self.quality_donut.setMaximumHeight(90)
        else:
            self.quality_donut.setMinimumHeight(132)
            self.quality_donut.setMaximumHeight(145)

    def _build_actions_card(self):
        card = self._section(
            "Priorités du jour",
            "Les signaux à traiter maintenant.",
            "FOCUS",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        items = [
            ("actions_today", "Aujourd'hui", "📅"),
            ("actions_overdue", "En retard", "⚠️"),
            ("high_priority", "Priorités fortes", "🔥"),
            ("actions_next_7_days", "7 prochains jours", "🗓️"),
        ]
        for index, (key, title, icon) in enumerate(items):
            item, value = self._mini_action(title, icon)
            self.action_values[key] = value
            grid.addWidget(item, index // 2, index % 2)
        card.layout().addLayout(grid)
        return card

    def _mini_action(self, title, icon):
        frame = QFrame()
        frame.setObjectName("DashboardMiniAction")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(7)

        chip = QLabel(icon)
        chip.setObjectName("DashboardMiniActionIcon")
        chip.setFixedSize(25, 25)
        chip.setAlignment(Qt.AlignCenter)

        label = QLabel(title)
        label.setObjectName("DashboardMiniActionLabel")
        label.setWordWrap(True)

        value = QLabel("0")
        value.setObjectName("DashboardMiniActionValue")

        layout.addWidget(chip)
        layout.addWidget(label, 1)
        layout.addWidget(value)
        return frame, value

    def _style_pipeline_frame(self, frame: QFrame, accent: str) -> None:
        p = dashboard_palette(self._theme_mode)
        frame.setStyleSheet(
            f"""
            QFrame#DashboardPipelineItem {{
                background:{p['surface_alt']};
                border:1px solid {p['border']};
                border-left:4px solid {accent};
                border-radius:10px;
            }}
            """
        )

    def _build_pipeline_card(self):
        card = self._section(
            "Pipeline commercial",
            "Répartition immédiate du portefeuille par étape.",
            "CONVERSION",
        )
        self.pipeline_grid = QGridLayout()
        self.pipeline_grid.setHorizontalSpacing(7)
        self.pipeline_grid.setVerticalSpacing(7)

        for index, name in enumerate(PIPELINE):
            frame = QFrame()
            frame.setObjectName("DashboardPipelineItem")
            is_new = "Nouveau" in str(name)
            color = "#338CE4" if is_new else PIPELINE_COLORS.get(name, "#94A3B8")
            self._pipeline_frames.append((frame, color))
            self._style_pipeline_frame(frame, color)

            layout = QHBoxLayout(frame)
            layout.setContentsMargins(9, 7, 9, 7)
            layout.setSpacing(6)

            display_name = str(name)
            if is_new:
                display_name = display_name.replace("🟢", "").strip()
                label = QLabel(
                    f'<span style="color:#338CE4;font-size:12px;">■</span>&nbsp;&nbsp;{display_name}'
                )
                label.setTextFormat(Qt.RichText)
            else:
                label = QLabel(display_name)
            label.setObjectName("DashboardPipelineLabel")
            label.setWordWrap(True)

            value = QLabel("0")
            value.setObjectName("DashboardPipelineValue")

            layout.addWidget(label, 1)
            layout.addWidget(value)
            self.pipeline_values[name] = value
            self.pipeline_grid.addWidget(frame, index // 3, index % 3)

        card.layout().addLayout(self.pipeline_grid)
        return card

    def _build_scoring_card(self):
        card = self._section(
            "Scoring commercial",
            "Le potentiel commercial mis en évidence sans masquer les données.",
            "PRIORISATION",
        )
        self.scoring_chart = HorizontalBarChart()
        self.scoring_chart.setMaximumHeight(142)
        self.scoring_chart.setMinimumHeight(120)

        self.scoring_empty = QFrame()
        self.scoring_empty.setObjectName("DashboardEmptyState")
        empty_layout = QHBoxLayout(self.scoring_empty)
        empty_layout.setContentsMargins(13, 10, 13, 10)
        empty_layout.setSpacing(9)

        empty_icon = QLabel("◎")
        empty_icon.setObjectName("DashboardEmptyIcon")
        empty_icon.setFixedSize(30, 30)
        empty_icon.setAlignment(Qt.AlignCenter)

        empty_texts = QVBoxLayout()
        empty_texts.setSpacing(1)
        self.scoring_empty_title = QLabel("Scoring à initialiser")
        self.scoring_empty_title.setObjectName("DashboardEmptyTitle")
        self.scoring_empty_detail = QLabel(
            "Utilisez « Calculer les scores » dans le CRM pour prioriser le portefeuille."
        )
        self.scoring_empty_detail.setObjectName("DashboardEmptyDetail")
        self.scoring_empty_detail.setWordWrap(True)
        empty_texts.addWidget(self.scoring_empty_title)
        empty_texts.addWidget(self.scoring_empty_detail)

        empty_layout.addWidget(empty_icon)
        empty_layout.addLayout(empty_texts, 1)

        self.scoring_summary = QLabel(
            "Cliquez sur « Calculer les scores » dans le CRM pour initialiser le classement."
        )
        self.scoring_summary.setObjectName("DashboardBodyMuted")
        self.scoring_summary.setWordWrap(True)

        card.layout().addWidget(self.scoring_chart)
        card.layout().addWidget(self.scoring_empty)
        card.layout().addWidget(self.scoring_summary)
        return card

    def _build_recent_activity_card(self):
        card = self._section(
            "Activité récente",
            "Les dernières opérations visibles du projet.",
            "HISTORIQUE",
        )
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(5)
        card.layout().addLayout(self.activity_layout)
        return card

    def _clear_activity(self):
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_activity(self, events):
        self._last_activity_events = list(events or [])
        self._clear_activity()

        if not self._last_activity_events:
            empty = QFrame()
            empty.setObjectName("DashboardEmptyState")
            empty_layout = QHBoxLayout(empty)
            empty_layout.setContentsMargins(12, 10, 12, 10)

            icon = QLabel("✦")
            icon.setObjectName("DashboardEmptyIcon")
            icon.setFixedSize(28, 28)
            icon.setAlignment(Qt.AlignCenter)

            label = QLabel(
                "Aucune activité récente. Les prochaines actions apparaîtront ici."
            )
            label.setObjectName("DashboardEmptyDetail")
            label.setWordWrap(True)

            empty_layout.addWidget(icon)
            empty_layout.addWidget(label, 1)
            self.activity_layout.addWidget(empty)
            return

        level_icons = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
        }
        for event in self._last_activity_events[:5]:
            timestamp = event.get("timestamp", "")
            try:
                time_text = datetime.fromisoformat(timestamp).strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                time_text = timestamp[:16].replace("T", " ")

            row = QFrame()
            row.setObjectName("DashboardActivityRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(9, 7, 9, 7)
            layout.setSpacing(7)

            icon = level_icons.get(event.get("level"), "•")
            title = QLabel(f"{icon}  {event.get('title', 'Activité')}")
            title.setObjectName("DashboardActivityTitle")
            title.setWordWrap(True)

            when = QLabel(time_text)
            when.setObjectName("DashboardActivityTime")

            layout.addWidget(title, 1)
            layout.addWidget(when)
            self.activity_layout.addWidget(row)

    @staticmethod
    def _format_number(value):
        try:
            return f"{int(value):,}".replace(",", " ")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_euro(cents: int) -> str:
        return f"{int(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")

    def _load_annual_signed_revenue(self) -> int | None:
        """Retourne le KPI annuel adapté au rôle connecté.

        - Administrateur / Manager : chiffre d'affaires signé visible.
        - Commercial : commissions générées sur ses propres ventes visibles.

        Les ventes annulées sont toujours exclues.
        """
        if not CloudRuntime.is_active():
            return None

        api = CloudRuntime.api()
        current_year = datetime.now().year
        sales = api.list_cloud_sales()

        total = 0
        is_commercial = self._is_commercial()

        for sale in sales:
            status = str(sale.get("status") or "").strip().lower()

            if status == "cancelled":
                continue

            raw_signed_at = str(sale.get("signed_at") or "").strip()

            try:
                sale_year = int(raw_signed_at[:4])
            except (TypeError, ValueError):
                continue

            if sale_year != current_year:
                continue

            amount_key = "commission_cents" if is_commercial else "price_cents"
            total += int(sale.get(amount_key) or 0)

        return total

    def _refresh_annual_revenue(self) -> None:
        """Actualise le KPI annuel Cloud même lorsqu'aucun projet n'est ouvert."""
        value = self.kpi_values.get("annual_revenue")

        if value is None:
            return

        try:
            annual_revenue_cents = self._load_annual_signed_revenue()
        except Exception:
            annual_revenue_cents = None

        value.setText(
            self._format_euro(annual_revenue_cents)
            if annual_revenue_cents is not None
            else "—"
        )

    def _set_empty(self):
        self._update_greeting()
        self._apply_role_permissions()
        self.subtitle.setText("Créez ou ouvrez un projet pour commencer.")
        self.context_project_value.setText("Aucun projet actif")
        self.context_source_value.setText("Aucune source")
        if self._is_commercial():
            self._set_hero_status("●  Espace Cloud actif", "active")
        else:
            self._set_hero_status("●  Prêt à prospecter", "ready")
        for key, value in self.kpi_values.items():
            if key == "annual_revenue":
                continue
            if key == "average_prospect_score":
                value.setText("0/100")
            else:
                value.setText("0")

        # Le KPI annuel est une donnée Cloud et ne dépend pas
        # de l'ouverture d'un projet local.
        self._refresh_annual_revenue()
        self.contact_chart.set_items([])
        self.contact_chart.setVisible(False)
        self.contact_empty.setVisible(True)
        self._set_health_compact(True)
        self.quality_donut.set_value(0)
        self.quality_details.setText("Aucun projet actif")
        self.enrichment_label.setText("0 / 0 prospects enrichis")
        self.enrichment_progress.setValue(0)
        self.enrichment_progress.setFormat("0 %")
        self.enrichment_detail.setText("Aucune donnée")
        for value in self.action_values.values():
            value.setText("0")
        for value in self.pipeline_values.values():
            value.setText("0")
        self.scoring_chart.set_items([])
        self.scoring_chart.setVisible(False)
        self.scoring_empty.setVisible(True)
        self.scoring_empty_title.setText("Scoring à initialiser")
        self.scoring_empty_detail.setText(
            "Ouvrez un projet ou votre CRM Cloud pour commencer à prioriser les prospects."
        )
        self.scoring_summary.setText("Aucun projet actif")
        self._render_activity([])
        self._update_deploy_button()

    def rafraichir(self):
        if not ApplicationState.has_project():
            self._set_empty()
            return

        try:
            context = self.dashboard_service.resolver.resolve()
            active_project = context.project

            if active_project is None:
                self._set_empty()
                return

            # Le bouton Déployer / Synchroniser doit toujours recevoir le projet
            # actif. Un projet déjà déployé est lu en mode Cloud par le resolver,
            # mais il reste le projet local de référence pour la synchronisation.
            self._update_deploy_button(active_project)

            # DashboardService sélectionne automatiquement le provider
            # SQLite ou Cloud. Aucun chemin de base locale ne doit être
            # transmis lorsqu'un projet Cloud est actif.
            data = self.dashboard_service.get_dashboard_data()

            project_name = (
                getattr(active_project, "name", None)
                or getattr(active_project, "title", None)
                or "Projet Cloud"
            )

            self._update_greeting()
            self._apply_role_permissions()
            self.subtitle.setText(
                "Voici l'état de votre prospection et les priorités à traiter."
            )
            self.context_project_value.setText(str(project_name))
            self.context_source_value.setText(
                "Source Cloud" if context.is_cloud else "Source locale"
            )
            self._set_hero_status(
                "●  Espace Cloud actif" if self._is_commercial() else "●  Projet actif",
                "active",
            )

            for key in ("prospects", "telephones", "emails", "sites"):
                self.kpi_values[key].setText(
                    self._format_number(data["kpi"][key])
                )

            # Le KPI annuel provient des ventes Cloud visibles selon le rôle
            # et reste indépendant du projet actif.
            self._refresh_annual_revenue()
            self.kpi_values["average_prospect_score"].setText(
                f"{data['kpi']['average_prospect_score']}/100"
            )

            contact_items = data["contact_distribution"]
            self.contact_chart.set_items(contact_items)
            self.contact_chart.setVisible(bool(contact_items))
            self.contact_empty.setVisible(not bool(contact_items))
            self._set_health_compact(False)

            score = data["kpi"]["quality_score"]
            self.quality_donut.set_value(score)

            missing_phone = data["activity"]["missing_phone"]
            missing_email = data["activity"]["missing_email"]
            self.quality_details.setText(
                f"Il manque {self._format_number(missing_phone)} téléphone(s) "
                f"et {self._format_number(missing_email)} email(s)."
            )

            enrichment = data["enrichment"]
            treated = int(enrichment.get("treated", enrichment["enriched"]) or 0)
            no_reliable = int(enrichment.get("no_reliable_result", 0) or 0)

            self.enrichment_label.setText(
                f"{self._format_number(treated)} / "
                f"{self._format_number(data['kpi']['prospects'])} prospects traités"
            )
            self.enrichment_progress.setValue(enrichment["percentage"])
            self.enrichment_progress.setFormat(
                f"{enrichment['percentage']} %"
            )
            self.enrichment_detail.setText(
                f"{self._format_number(enrichment['enriched'])} enrichi(s) • "
                f"{self._format_number(no_reliable)} sans résultat fiable • "
                f"{self._format_number(enrichment['remaining'])} restant(s) • "
                f"{self._format_number(enrichment['errors'])} erreur(s)"
            )

            for key, value in self.action_values.items():
                value.setText(
                    self._format_number(data["activity"].get(key, 0))
                )

            for name, value in self.pipeline_values.items():
                value.setText(
                    self._format_number(data["pipeline"].get(name, 0))
                )

            scoring_order = [
                "★★★★★", "★★★★☆", "★★★☆☆",
                "★★☆☆☆", "★☆☆☆☆", "Non calculé",
            ]
            scoring_items = [
                (grade, data["scoring"].get(grade, 0))
                for grade in scoring_order
                if data["scoring"].get(grade, 0)
            ]
            calculated_items = [
                (grade, count)
                for grade, count in scoring_items
                if grade != "Non calculé"
            ]
            not_scored = int(data["scoring"].get("Non calculé", 0) or 0)

            if calculated_items:
                self.scoring_chart.set_items(scoring_items)
                self.scoring_chart.setVisible(True)
                self.scoring_empty.setVisible(False)
            else:
                self.scoring_chart.set_items([])
                self.scoring_chart.setVisible(False)
                self.scoring_empty.setVisible(True)
                self.scoring_empty_title.setText(
                    f"{self._format_number(not_scored)} prospect(s) à scorer"
                    if not_scored
                    else "Scoring à initialiser"
                )
                self.scoring_empty_detail.setText(
                    "Ouvrez le CRM puis utilisez « Calculer les scores » "
                    "pour faire apparaître les priorités commerciales."
                )

            top_scores = (
                data["scoring"].get("★★★★★", 0)
                + data["scoring"].get("★★★★☆", 0)
            )
            if calculated_items:
                self.scoring_summary.setText(
                    f"{self._format_number(top_scores)} prospect(s) sont classés "
                    f"en priorité forte ou très forte."
                )
            else:
                self.scoring_summary.setText(
                    "Le classement apparaîtra ici dès que le scoring aura été calculé."
                )

            # ActivityService utilise encore le stockage local.
            if context.is_cloud:
                events = []
            else:
                events = ActivityService.list_events(
                    project=active_project,
                    limit=6,
                )

            self._render_activity(events)
            self._show_cloud_assignment_once(active_project)

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur Dashboard",
                "Impossible de charger le dashboard :\n"
                f"{exc}",
            )

    def _show_cloud_assignment_once(self, project) -> None:
        """Affiche une fois l'affectation Cloud du projet actif, sans modifier les données."""
        if not CloudRuntime.is_active():
            return

        try:
            cloud = self.deployment_service.get_deployment_status(project)
            project_id = str(cloud.get("project_id") or "").strip()
        except Exception:
            return

        if not project_id or project_id in self._cloud_assignment_checked_for:
            return

        self._cloud_assignment_checked_for.add(project_id)

        try:
            api = CloudRuntime.api()
            cloud_project = api.get_project(project_id)

            assigned_to = str(cloud_project.get("assigned_to") or "").strip()
            status_value = str(cloud_project.get("status") or "").strip() or "—"
            project_name = str(cloud_project.get("name") or getattr(project, "name", "") or "Projet Cloud")

            assignee_label = "Non affecté"
            if assigned_to:
                assignee_label = assigned_to
                try:
                    users = api.list_users(active_only=False)
                    for user in users:
                        user_id = str(
                            getattr(user, "id", None)
                            or getattr(user, "user_id", None)
                            or getattr(user, "cloud_user_id", None)
                            or ""
                        ).strip()
                        if user_id != assigned_to:
                            continue

                        display_name = str(
                            getattr(user, "display_name", None)
                            or getattr(user, "full_name", None)
                            or getattr(user, "name", None)
                            or ""
                        ).strip()
                        email = str(getattr(user, "email", None) or "").strip()
                        assignee_label = display_name or email or assigned_to
                        break
                except Exception:
                    pass

            QMessageBox.information(
                self,
                "Affectation du projet Cloud",
                (
                    f"Projet Cloud : {project_name}\n"
                    f"Statut : {status_value}\n"
                    f"Affecté à : {assignee_label}\n\n"
                    f"Identifiant affectation : {assigned_to or 'Aucun'}"
                ),
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Vérification de l'affectation",
                (
                    "Impossible de vérifier l'affectation du projet Cloud.\n\n"
                    f"{exc}"
                ),
            )

    def ouvrir_archives_projets(self):
        """Ouvre le centre d'archivage des projets Cloud."""
        if not self._can_manage_project_archives():
            QMessageBox.warning(
                self,
                "Accès refusé",
                "L'archivage des projets est réservé à l'administrateur et au manager.",
            )
            return

        if not CloudRuntime.is_active():
            QMessageBox.warning(
                self,
                "Cloud indisponible",
                "Connectez-vous à Form@Prospect Cloud pour gérer les archives.",
            )
            return

        dialog = ProjectArchiveDialog(
            api=CloudRuntime.api(),
            parent=self,
        )
        dialog.exec()
        self.rafraichir()

    def deploy_project(self):
        """
        Ouvre la fenêtre de configuration puis déploie
        le projet actif dans Form@Prospect Cloud.
        """

        if not ApplicationState.has_project():
            NotificationManager.warning(
                "Déploiement Cloud",
                "Aucun projet actif.",
            )
            return

        project = ApplicationState.get_project()

        # Un projet déjà déployé utilise le même bouton pour réparer ou
        # relancer l'import vers son projet Cloud existant. Aucun nouveau
        # projet Cloud n'est créé.
        if self.deployment_service.is_deployed(project):
            try:
                cloud_info = self.deployment_service.get_deployment_status(project)
                project_id = str(cloud_info.get("project_id") or "").strip()
                if project_id and CloudRuntime.is_active():
                    cloud_project = CloudRuntime.api().get_project(project_id)
                    if str(cloud_project.get("status") or "").lower() == "archived":
                        QMessageBox.warning(
                            self,
                            "Projet archivé",
                            "Ce projet est archivé dans le Cloud. "
                            "Restaurez-le depuis « Archives » avant toute synchronisation.",
                        )
                        self._update_deploy_button(project)
                        return
            except Exception:
                pass

            if self.deploy_button is not None:
                self.deploy_button.setEnabled(False)
                self.deploy_button.setText("☁ Synchronisation…")
            try:
                result = self.deployment_service.synchronize(project)
                imported = result.import_result.imported_prospects
                NotificationManager.success(
                    "Synchronisation terminée",
                    f"{imported} prospect(s) synchronisé(s) avec le Cloud.",
                )
                self.rafraichir()
            except Exception as exc:
                self._update_deploy_button(project)
                QMessageBox.warning(
                    self,
                    "Synchronisation impossible",
                    str(exc),
                )
            return

        try:
            api_client = CloudRuntime.api()

            users = api_client.list_users(
                active_only=True,
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Utilisateurs Cloud indisponibles",
                (
                    "Impossible de charger les utilisateurs "
                    "de l'organisation.\n\n"
                    f"{exc}"
                ),
            )
            return

        dialog = CloudDeploymentDialog(
            project_name=project.name,
            users=users,
            parent=self,
        )

        if not dialog.exec():
            return

        options = dialog.options()

        if self.deploy_button is not None:
            self.deploy_button.setEnabled(False)
            self.deploy_button.setText(
                "☁ Déploiement…"
            )

        try:
            QMessageBox.information(
        self,
        "Debug affectation",
        f"assigned_to = {options.assigned_to}"
        )
            result = self.deployment_service.deploy(
                project,
                description=options.description,
                assigned_to=options.assigned_to,
            )

            NotificationManager.success(
                "Projet déployé",
                (
                    f"{project.name} a été déployé dans Form@Prospect Cloud. "
                    f"{result.import_result.imported_prospects} prospect(s) importé(s)."
                ),
            )

            self.rafraichir()

        except ProjectDeploymentError as exc:
            self._update_deploy_button(project)

            QMessageBox.warning(
                self,
                "Déploiement impossible",
                str(exc),
            )

        except Exception as exc:
            self._update_deploy_button(project)

            QMessageBox.critical(
                self,
                "Erreur de déploiement",
                (
                    "Une erreur inattendue est survenue "
                    "pendant le déploiement du projet :\n"
                    f"{exc}"
                ),
            )

    def ouvrir_nouveau_projet(self):
        dialog = NewProjectDialog()

        if dialog.exec():
            NotificationManager.success(
                "Projet créé",
                "Le nouveau projet est prêt.",
            )

            self.rafraichir()

    def ouvrir_projet_existant(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier du projet existant",
        )

        if not folder:
            return

        try:
            project = self.project_manager.open_project(
                folder
            )

            NotificationManager.success(
                "Projet ouvert",
                (
                    f"Le projet {project.name} "
                    "est maintenant actif."
                ),
            )

            self.rafraichir()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur",
                (
                    "Impossible d'ouvrir ce projet :\n"
                    f"{exc}"
                ),
            )

    def sauvegarder_projet(self):
        if not ApplicationState.has_project():
            NotificationManager.warning(
                "Sauvegarde",
                "Aucun projet actif à sauvegarder.",
            )
            return

        project = ApplicationState.get_project()

        default_path = (
            self.backup_service.default_backup_path(
                project
            )
        )

        output, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder le projet",
            str(default_path),
            "Sauvegardes Form@Prospect (*.fpbackup)",
        )

        if not output:
            return

        try:
            path = self.backup_service.create_backup(
                project,
                output,
            )

            ActivityService.record(
                "Sauvegarde manuelle créée",
                path.name,
                category="backup",
                level="success",
                project=project,
            )

            NotificationManager.success(
                "Sauvegarde terminée",
                path.name,
            )

            self.rafraichir()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                str(exc),
            )


