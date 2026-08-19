
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
        self._build_ui()
        self.rafraichir()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: #F8FAFD; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px 4px 2px; }"
            "QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 5px; min-height: 36px; }"
            "QScrollBar::handle:vertical:hover { background: #94A3B8; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        content = QWidget()
        content.setStyleSheet("background: #F8FAFD;")
        root = QVBoxLayout(content)
        root.setContentsMargins(34, 30, 34, 42)
        root.setSpacing(18)

        root.addWidget(self._build_header())

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(14)
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
                    "Commissions générées — année en cours"
                    if self._is_commercial()
                    else "Ventes signées — année en cours"
                ),
            ),
        ]
        for column, (key, title, icon, caption) in enumerate(kpis):
            card, value = self._metric_card(title, icon, caption)
            self.kpi_values[key] = value
            kpi_grid.addWidget(card, 0, column)
            kpi_grid.setColumnStretch(column, 1)
        root.addLayout(kpi_grid)

        root.addWidget(self._build_quote_card())

        insight_grid = QGridLayout()
        insight_grid.setHorizontalSpacing(16)
        insight_grid.setVerticalSpacing(16)
        insight_grid.setColumnStretch(0, 3)
        insight_grid.setColumnStretch(1, 2)

        contact_card = self._section(
            "Données de contact",
            "Vision instantanée de la richesse de votre base commerciale.",
            "BASE COMMERCIALE",
        )
        self.contact_chart = HorizontalBarChart()
        self.contact_chart.setMaximumHeight(160)
        self.contact_empty = QLabel("Aucune donnée à afficher pour le moment.")
        self.contact_empty.setAlignment(Qt.AlignCenter)
        self.contact_empty.setStyleSheet(
            "font-size:12px; color:#94A3B8; border:none; background:transparent; padding:24px;"
        )
        contact_card.layout().addWidget(self.contact_chart)
        contact_card.layout().addWidget(self.contact_empty)
        insight_grid.addWidget(contact_card, 0, 0)

        quality_card = self._section(
            "Score qualité",
            "Complétude moyenne des informations de contact.",
            "QUALITÉ",
        )
        self.quality_donut = QualityDonut()
        self.quality_donut.setMaximumHeight(175)
        self.quality_details = QLabel("Aucun projet actif")
        self.quality_details.setAlignment(Qt.AlignCenter)
        self.quality_details.setWordWrap(True)
        self.quality_details.setStyleSheet(
            "color:#6B7A90; font-size:12px; border:none; background:transparent;"
        )
        quality_card.layout().addWidget(self.quality_donut)
        quality_card.layout().addWidget(self.quality_details)
        insight_grid.addWidget(quality_card, 0, 1)
        root.addLayout(insight_grid)

        lower_grid = QGridLayout()
        lower_grid.setHorizontalSpacing(16)
        lower_grid.setVerticalSpacing(16)
        lower_grid.setColumnStretch(0, 1)
        lower_grid.setColumnStretch(1, 1)

        lower_grid.addWidget(self._build_actions_card(), 0, 0)
        lower_grid.addWidget(self._build_pipeline_card(), 0, 1)
        lower_grid.addWidget(self._build_enrichment_card(), 1, 0)
        lower_grid.addWidget(self._build_recent_activity_card(), 1, 1)
        lower_grid.addWidget(self._build_scoring_card(), 2, 0, 1, 2)
        root.addLayout(lower_grid)
        root.addStretch()

        scroll.setWidget(content)
        main.addWidget(scroll)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("DashboardHero")
        frame.setMinimumHeight(118)
        frame.setStyleSheet("""
            QFrame#DashboardHero {
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
        self._apply_shadow(frame, blur=34, y=8, alpha=24)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 20, 22, 20)
        layout.setSpacing(18)

        texts = QVBoxLayout()
        texts.setSpacing(4)

        eyebrow = QLabel("FORM@PROSPECT  •  CENTRE DE COMMANDEMENT")
        eyebrow.setStyleSheet(
            "font-size:10px; font-weight:900; letter-spacing:1.2px; "
            "color:#338CE4; border:none; background:transparent;"
        )

        self.title = QLabel("Bonjour 👋")
        self.title.setStyleSheet(
            "font-size:30px; font-weight:900; color:#0B1220; "
            "border:none; background:transparent;"
        )
        self.subtitle = QLabel("Ouvrez un projet pour afficher votre centre de commandement.")
        self.subtitle.setStyleSheet(
            "font-size:13px; color:#6B7A90; border:none; background:transparent;"
        )
        self.hero_status = QLabel("●  Prêt à prospecter")
        self.hero_status.setStyleSheet(
            "font-size:10px; font-weight:800; color:#16A34A; border:none; background:transparent;"
        )

        texts.addWidget(eyebrow)
        texts.addWidget(self.title)
        texts.addWidget(self.subtitle)
        texts.addWidget(self.hero_status)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.new_project_button = None
        self.open_project_button = None
        self.deploy_button = None
        self.archive_button = None

        buttons = (
            ("＋ Nouveau projet", self.ouvrir_nouveau_projet),
            ("📂  Ouvrir", self.ouvrir_projet_existant),
            ("💾  Sauvegarder", self.sauvegarder_projet),
            ("☁  Déployer", self.deploy_project),
            ("📦  Archives", self.ouvrir_archives_projets),
            ("↻  Rafraîchir", self.rafraichir),
        )
        for index, (label, slot) in enumerate(buttons):
            button = QPushButton(label)
            button.setFixedHeight(42)
            button.setStyleSheet(
                self._button_style()
                if index in (0, 3)
                else self._secondary_header_button_style()
            )
            button.clicked.connect(slot)
            if "Nouveau projet" in label:
                self.new_project_button = button
            elif "Ouvrir" in label:
                self.open_project_button = button
            elif "Déployer" in label:
                self.deploy_button = button
            elif "Archives" in label:
                self.archive_button = button
            actions.addWidget(button)

        self._apply_role_permissions()

        layout.addLayout(texts, 1)
        layout.addLayout(actions)
        return frame

    @staticmethod
    def _button_style():
        return """
            QPushButton {
                background: #338CE4;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton:hover { background: #247BD0; }
            QPushButton:pressed { background: #1D66B2; }
            QPushButton:disabled {
                background: #E5EAF0;
                color: #9AA7B8;
            }
        """

    @staticmethod
    def _secondary_header_button_style():
        return """
            QPushButton {
                background: rgba(255,255,255,0.94);
                color: #23344D;
                border: 1px solid #DDE6F0;
                border-radius: 12px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: #FFFFFF;
                color: #338CE4;
                border-color: #AFCFF0;
            }
            QPushButton:disabled {
                background: #F2F5F8;
                color: #A4AFBD;
                border-color: #E7ECF2;
            }
        """

    @staticmethod
    def _deployed_button_style():
        return """
            QPushButton {
                background: #16A34A;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:disabled {
                background: #16A34A;
                color: white;
            }
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

    @staticmethod
    def _card_style():
        return """
            QFrame#DashboardCard {
                background: #FFFFFF;
                border: 1px solid #E7ECF3;
                border-radius: 20px;
            }
        """

    @staticmethod
    def _apply_shadow(widget, *, blur=28, y=6, alpha=20):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(QColor(7, 27, 56, alpha))
        widget.setGraphicsEffect(effect)

    def _section(self, title: str, subtitle: str = "", eyebrow: str = ""):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card.setStyleSheet(self._card_style())
        self._apply_shadow(card, blur=26, y=7, alpha=18)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(7)

        if eyebrow:
            eyebrow_label = QLabel(eyebrow)
            eyebrow_label.setStyleSheet(
                "font-size:9px; font-weight:900; letter-spacing:1px; color:#338CE4; "
                "border:none; background:transparent;"
            )
            layout.addWidget(eyebrow_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size:18px; font-weight:900; color:#0B1220; "
            "border:none; background:transparent;"
        )
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(
                "font-size:12px; color:#62748A; border:none; background:transparent;"
            )
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        layout.addSpacing(4)
        return card

    def _metric_card(self, title: str, icon: str, caption: str = ""):
        card = QFrame()
        card.setObjectName("DashboardMetric")
        card.setMinimumHeight(118)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet("""
            QFrame#DashboardMetric {
                background: #FFFFFF;
                border: 1px solid #E7ECF3;
                border-radius: 18px;
            }
        """)
        self._apply_shadow(card, blur=24, y=6, alpha=16)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 12)
        layout.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(8)

        icon_chip = QLabel(icon)
        icon_chip.setFixedSize(34, 34)
        icon_chip.setAlignment(Qt.AlignCenter)
        icon_chip.setStyleSheet(
            "font-size:16px; background:#EAF4FF; border:none; border-radius:10px;"
        )

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size:12px; font-weight:800; color:#53657C; "
            "border:none; background:transparent;"
        )
        head.addWidget(icon_chip)
        head.addWidget(title_label)
        head.addStretch()

        value = QLabel("0")
        value.setStyleSheet(
            "font-size:27px; font-weight:900; color:#0B1220; "
            "border:none; background:transparent;"
        )
        value.setWordWrap(True)

        caption_label = QLabel(caption)
        caption_label.setStyleSheet(
            "font-size:10px; color:#94A3B8; border:none; background:transparent;"
        )

        layout.addLayout(head)
        layout.addSpacing(2)
        layout.addWidget(value)
        layout.addWidget(caption_label)
        return card, value

    def _build_quote_card(self):
        week = max(1, datetime.now().isocalendar().week)
        theme, quote = self.WEEKLY_QUOTES[(week - 1) % len(self.WEEKLY_QUOTES)]

        card = QFrame()
        card.setObjectName("WeeklyQuoteCard")
        card.setMinimumHeight(120)
        card.setStyleSheet("""
            QFrame#WeeklyQuoteCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #071B38,
                    stop:0.55 #0B2A52,
                    stop:1 #164B7E
                );
                border: 1px solid #183D66;
                border-radius: 22px;
            }
        """)
        self._apply_shadow(card, blur=34, y=8, alpha=34)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(18)

        badge = QLabel("✦")
        badge.setFixedSize(48, 48)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "font-size:22px; color:white; background:rgba(51,140,228,0.25); "
            "border:1px solid rgba(255,255,255,0.12); border-radius:14px;"
        )

        texts = QVBoxLayout()
        texts.setSpacing(4)
        overline = QLabel(f"CITATION DE LA SEMAINE  •  {theme.upper()}")
        overline.setStyleSheet(
            "font-size:9px; font-weight:900; letter-spacing:1.2px; color:#8FC7FF; "
            "border:none; background:transparent;"
        )
        quote_label = QLabel(f"« {quote} »")
        quote_label.setWordWrap(True)
        quote_label.setStyleSheet(
            "font-size:17px; font-weight:700; color:#FFFFFF; "
            "border:none; background:transparent;"
        )
        author = QLabel("— Form@Prospect")
        author.setStyleSheet(
            "font-size:11px; color:#BFD7EE; border:none; background:transparent;"
        )
        texts.addWidget(overline)
        texts.addWidget(quote_label)
        texts.addWidget(author)

        layout.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(texts, 1)
        return card

    def _build_enrichment_card(self):
        card = self._section("Enrichissement", "Progression globale du projet actif.", "PROGRESSION")
        self.enrichment_label = QLabel("0 / 0 prospects enrichis")
        self.enrichment_label.setStyleSheet(
            "font-size:14px; font-weight:800; color:#0B1220; border:none; background:transparent;"
        )
        self.enrichment_progress = QProgressBar()
        self.enrichment_progress.setRange(0, 100)
        self.enrichment_progress.setValue(0)
        self.enrichment_progress.setFixedHeight(18)
        self.enrichment_progress.setStyleSheet(f"""
            QProgressBar {{ background: #EEF4FA; border: none; border-radius: 9px;
                text-align: center; color: #0B1220; font-weight: 800; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #338CE4, stop:1 #67B0F4);
                border-radius: 9px;
            }}
        """)
        self.enrichment_detail = QLabel("Aucune donnée")
        self.enrichment_detail.setStyleSheet(
            "font-size:11px; color:#7A899C; border:none; background:transparent;"
        )
        card.layout().addWidget(self.enrichment_label)
        card.layout().addWidget(self.enrichment_progress)
        card.layout().addWidget(self.enrichment_detail)
        return card

    def _build_actions_card(self):
        card = self._section("Priorités du jour", "Ce qui mérite votre attention maintenant.", "FOCUS")
        card.setStyleSheet("""
            QFrame#DashboardCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FFFFFF, stop:1 #F8FBFF);
                border:1px solid #E3EBF4;
                border-radius:20px;
            }
        """)
        grid = QGridLayout()
        items = [
            ("actions_today", "Actions aujourd'hui", "📅"),
            ("actions_overdue", "Actions en retard", "⚠️"),
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
        frame.setStyleSheet(
            "QFrame { background:#F8FBFE; border:1px solid #E8EEF5; border-radius:14px; }"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(9)

        chip = QLabel(icon)
        chip.setFixedSize(28, 28)
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet(
            "font-size:13px; background:#FFFFFF; border:1px solid #E7ECF3; border-radius:9px;"
        )
        label = QLabel(title)
        label.setStyleSheet(
            "font-size:11px; font-weight:750; color:#61738A; "
            "border:none; background:transparent;"
        )
        value = QLabel("0")
        value.setStyleSheet(
            "font-size:18px; font-weight:900; color:#0B1220; "
            "border:none; background:transparent;"
        )
        layout.addWidget(chip)
        layout.addWidget(label, 1)
        layout.addWidget(value)
        return frame, value

    def _build_pipeline_card(self):
        card = self._section("Pipeline commercial", "Répartition de votre portefeuille par étape.", "CONVERSION")
        card.setStyleSheet("""
            QFrame#DashboardCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FFFFFF, stop:1 #FBFCFF);
                border:1px solid #E3EBF4;
                border-radius:20px;
            }
        """)
        self.pipeline_grid = QGridLayout()
        self.pipeline_grid.setSpacing(8)
        for index, name in enumerate(PIPELINE):
            frame = QFrame()
            color = PIPELINE_COLORS.get(name, "#F3F4F6")
            frame.setStyleSheet(f"QFrame {{ background: {color}; border: 1px solid #E8EDF3; border-radius: 13px; }}")
            layout = QHBoxLayout(frame)
            layout.setContentsMargins(10, 8, 10, 8)
            label = QLabel(name)
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 11px; font-weight: 800; color: #111827; border: none;")
            value = QLabel("0")
            value.setStyleSheet("font-size: 16px; font-weight: 900; color: #111827; border: none;")
            layout.addWidget(label, 1)
            layout.addWidget(value)
            self.pipeline_values[name] = value
            self.pipeline_grid.addWidget(frame, index // 2, index % 2)
        card.layout().addLayout(self.pipeline_grid)
        return card

    def _build_scoring_card(self):
        card = self._section(
            "Scoring commercial",
            "Classement explicable des prospects selon la qualité et la complétude de leurs données.",
            "PRIORISATION",
        )
        self.scoring_chart = HorizontalBarChart()
        self.scoring_chart.setMaximumHeight(170)

        self.scoring_empty = QFrame()
        self.scoring_empty.setStyleSheet(
            "QFrame { background:#F8FBFE; border:1px dashed #D7E4F1; border-radius:16px; }"
        )
        empty_layout = QHBoxLayout(self.scoring_empty)
        empty_layout.setContentsMargins(16, 14, 16, 14)
        empty_layout.setSpacing(12)

        empty_icon = QLabel("◎")
        empty_icon.setFixedSize(34, 34)
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet(
            "font-size:16px; color:#338CE4; background:#EAF4FF; "
            "border:none; border-radius:11px;"
        )

        empty_texts = QVBoxLayout()
        empty_texts.setSpacing(2)
        self.scoring_empty_title = QLabel("Scoring à initialiser")
        self.scoring_empty_title.setStyleSheet(
            "font-size:12px; font-weight:900; color:#23344D; "
            "border:none; background:transparent;"
        )
        self.scoring_empty_detail = QLabel(
            "Ouvrez le CRM puis utilisez « Calculer les scores » pour prioriser votre portefeuille."
        )
        self.scoring_empty_detail.setWordWrap(True)
        self.scoring_empty_detail.setStyleSheet(
            "font-size:11px; color:#7A899C; border:none; background:transparent;"
        )
        empty_texts.addWidget(self.scoring_empty_title)
        empty_texts.addWidget(self.scoring_empty_detail)

        empty_layout.addWidget(empty_icon)
        empty_layout.addLayout(empty_texts, 1)

        self.scoring_summary = QLabel("Cliquez sur « Calculer les scores » dans le CRM pour initialiser le classement.")
        self.scoring_summary.setWordWrap(True)
        self.scoring_summary.setStyleSheet(
            "font-size:11px; color:#7A899C; border:none; background:transparent;"
        )
        card.layout().addWidget(self.scoring_chart)
        card.layout().addWidget(self.scoring_empty)
        card.layout().addWidget(self.scoring_summary)
        return card

    def _build_recent_activity_card(self):
        card = self._section("Activité récente", "Les dernières opérations du projet.", "HISTORIQUE")
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(6)
        card.layout().addLayout(self.activity_layout)
        return card

    def _clear_activity(self):
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_activity(self, events):
        self._clear_activity()
        if not events:
            empty = QFrame()
            empty.setStyleSheet(
                "QFrame { background:#FBFDFF; border:1px dashed #DCE5EF; border-radius:14px; }"
            )
            empty_layout = QHBoxLayout(empty)
            empty_layout.setContentsMargins(14, 12, 14, 12)
            icon = QLabel("✦")
            icon.setFixedSize(28, 28)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(
                "font-size:13px; color:#338CE4; background:#EAF4FF; border:none; border-radius:9px;"
            )
            label = QLabel("Aucune activité récente. Les prochaines actions apparaîtront ici.")
            label.setWordWrap(True)
            label.setStyleSheet(
                "font-size:11px; color:#7A899C; border:none; background:transparent;"
            )
            empty_layout.addWidget(icon)
            empty_layout.addWidget(label, 1)
            self.activity_layout.addWidget(empty)
            return
        level_icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        for event in events[:6]:
            timestamp = event.get("timestamp", "")
            try:
                time_text = datetime.fromisoformat(timestamp).strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                time_text = timestamp[:16].replace("T", " ")
            row = QFrame()
            row.setStyleSheet("QFrame { background:#F8FBFE; border:1px solid #E8EEF5; border-radius:12px; }")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 8, 10, 8)
            icon = level_icons.get(event.get("level"), "•")
            title = QLabel(f"{icon}  {event.get('title', 'Activité')}")
            title.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {TEXT_PRIMARY}; border: none;")
            when = QLabel(time_text)
            when.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; border: none;")
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
        if self._is_commercial():
            self.hero_status.setText("●  Espace Cloud actif")
            self.hero_status.setStyleSheet(
                "font-size:10px; font-weight:800; color:#338CE4; "
                "border:none; background:transparent;"
            )
        else:
            self.hero_status.setText("●  Prêt à prospecter")
            self.hero_status.setStyleSheet(
                "font-size:10px; font-weight:800; color:#16A34A; "
                "border:none; background:transparent;"
            )
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
                "Voici l'état de votre prospection "
                "et les priorités à traiter."
            )
            self.hero_status.setText(
                "●  Espace Cloud actif" if self._is_commercial() else "●  Projet actif"
            )
            self.hero_status.setStyleSheet(
                "font-size:10px; font-weight:800; color:#338CE4; "
                "border:none; background:transparent;"
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


