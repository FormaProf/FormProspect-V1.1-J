import threading

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QWidget

from core.constants import *
from core.paths import resource_path
from core.session import SessionState
from services.auth_service import AuthService
from services.update_service import UpdateError, UpdateService
from ui.components.notifications import NotificationManager
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.update_dialog import UpdateDialog
from ui.pages.account_page import AccountPage
from ui.pages.admin_account_page import AdminAccountPage
from ui.pages.ai_assistant_page import AIAssistantPage
from ui.pages.activity_page import ActivityPage
from ui.pages.agenda_page import AgendaPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.admin_statistics_page import AdminStatisticsPage
from ui.pages.documents_page import DocumentsPage
from ui.pages.trainers_page import TrainersPage
from ui.pages.trainer_availability_page import TrainerAvailabilityPage
from ui.pages.trainer_dashboard_page import TrainerDashboardPage
from ui.pages.trainer_sessions_page import TrainerSessionsPage
from ui.pages.trainer_planning_page import TrainerPlanningPage
from ui.pages.trainer_session_detail_page import TrainerSessionDetailPage
from ui.pages.commercial_profiles_page import CommercialProfilesPage
from ui.pages.training_cases_page import TrainingCasesPage
from ui.pages.campaigns_page import CampaignsPage
from ui.pages.commissions_page import CommissionsPage
from ui.pages.sequences_page import SequencesPage
from ui.pages.prospects_page import ProspectsPage
from ui.pages.treatment_page import TreatmentPage
from ui.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setWindowIcon(QIcon(resource_path("assets/icons/formaprospect.ico")))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.pages = QStackedWidget()

        self.is_trainer_space = SessionState.has_role("Formateur")

        if self.is_trainer_space:
            # Le rôle Formateur charge uniquement son espace métier. Les pages
            # CRM lourdes ne sont ni instanciées ni interrogées au démarrage.
            print("[MAIN] TrainerDashboard", flush=True)
            self.trainer_dashboard_page = TrainerDashboardPage()
            print("[MAIN] TrainerSessions", flush=True)
            self.trainer_sessions_page = TrainerSessionsPage()
            print("[MAIN] TrainerPlanning", flush=True)
            self.trainer_planning_page = TrainerPlanningPage()
            print("[MAIN] TrainerSessionDetail", flush=True)
            self.trainer_session_detail_page = TrainerSessionDetailPage()
            self._trainer_detail_return_page = self.trainer_sessions_page

            self.trainer_dashboard_page.session_open_requested.connect(
                lambda session_id: self.ouvrir_detail_session_formateur(session_id, self.trainer_dashboard_page)
            )
            self.trainer_sessions_page.session_open_requested.connect(
                lambda session_id: self.ouvrir_detail_session_formateur(session_id, self.trainer_sessions_page)
            )
            self.trainer_planning_page.session_open_requested.connect(
                lambda session_id: self.ouvrir_detail_session_formateur(session_id, self.trainer_planning_page)
            )
            self.trainer_session_detail_page.back_requested.connect(self.retour_session_formateur)

            print("[MAIN] Account", flush=True)
            self.account_page = AccountPage(auth_service)
            self.account_page.profile_updated.connect(self._refresh_connected_profile)

            for page in (
                self.trainer_dashboard_page,
                self.trainer_sessions_page,
                self.trainer_planning_page,
                self.trainer_session_detail_page,
                self.account_page,
            ):
                self.pages.addWidget(page)
        else:
            # Chemin historique conservé pour Administrateur / Manager / Commercial.
            print("[MAIN] Dashboard", flush=True)
            self.dashboard_page = DashboardPage()
            print("[MAIN] Treatment", flush=True)
            self.treatment_page = TreatmentPage()
            print("[MAIN] Prospects", flush=True)
            self.prospects_page = ProspectsPage()
            print("[MAIN] Agenda", flush=True)
            self.agenda_page = AgendaPage()
            print("[MAIN] Campaigns", flush=True)
            self.campaigns_page = CampaignsPage()
            print("[MAIN] Sequences", flush=True)
            self.sequences_page = SequencesPage()
            print("[MAIN] Commissions", flush=True)
            self.commissions_page = CommissionsPage()
            print("[MAIN] Documents", flush=True)
            self.documents_page = DocumentsPage()
            print("[MAIN] Trainers", flush=True)
            self.trainers_page = TrainersPage()
            print("[MAIN] TrainerAvailability", flush=True)
            self.trainer_availability_page = TrainerAvailabilityPage()
            print("[MAIN] CommercialProfiles", flush=True)
            self.commercial_profiles_page = CommercialProfilesPage()
            print("[MAIN] TrainingCases", flush=True)
            self.training_cases_page = TrainingCasesPage()
            print("[MAIN] AdminStatistics", flush=True)
            self.admin_statistics_page = AdminStatisticsPage()
            print("[MAIN] Activity", flush=True)
            self.activity_page = ActivityPage()
            print("[MAIN] AdminAccount", flush=True)
            self.admin_account_page = AdminAccountPage(auth_service)
            print("[MAIN] Account", flush=True)
            self.account_page = AccountPage(auth_service)
            self.account_page.profile_updated.connect(self._refresh_connected_profile)
            print("[MAIN] AI", flush=True)
            self.ai_assistant_page = AIAssistantPage()

            for page in (
                self.dashboard_page, self.treatment_page, self.prospects_page,
                self.agenda_page, self.campaigns_page, self.sequences_page,
                self.commissions_page, self.documents_page, self.trainers_page,
                self.trainer_availability_page, self.commercial_profiles_page,
                self.training_cases_page, self.admin_statistics_page,
                self.ai_assistant_page, self.activity_page,
                self.admin_account_page, self.account_page,
            ):
                self.pages.addWidget(page)

        print("[MAIN] Toutes les pages autorisées créées", flush=True)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages)
        self.setCentralWidget(root)
        NotificationManager.configure(self)

        self.sidebar.buttons_by_key["dashboard"].clicked.connect(self.ouvrir_dashboard)
        self.sidebar.buttons_by_key["trainer_dashboard"].clicked.connect(self.ouvrir_trainer_dashboard)
        self.sidebar.buttons_by_key["trainer_sessions"].clicked.connect(self.ouvrir_sessions_formateur)
        self.sidebar.buttons_by_key["trainer_planning"].clicked.connect(self.ouvrir_planning_formateur)
        self.sidebar.buttons_by_key["treatment"].clicked.connect(self.ouvrir_traitement)
        self.sidebar.buttons_by_key["crm"].clicked.connect(self.ouvrir_prospects)
        self.sidebar.buttons_by_key["agenda"].clicked.connect(self.ouvrir_agenda)
        self.sidebar.buttons_by_key["campaigns"].clicked.connect(self.ouvrir_campagnes)
        self.sidebar.buttons_by_key["sequences"].clicked.connect(self.ouvrir_sequences)
        self.sidebar.buttons_by_key["sales"].clicked.connect(self.ouvrir_commissions)
        self.sidebar.buttons_by_key["documents"].clicked.connect(self.ouvrir_documents)
        self.sidebar.buttons_by_key["trainers"].clicked.connect(self.ouvrir_formateurs)
        self.sidebar.buttons_by_key["trainer_availability"].clicked.connect(
            self.ouvrir_disponibilites_formateurs
        )
        self.sidebar.buttons_by_key["commercial_profiles"].clicked.connect(self.ouvrir_commerciaux)
        self.sidebar.buttons_by_key["training_cases"].clicked.connect(self.ouvrir_dossiers_formation)
        self.sidebar.buttons_by_key["statistics"].clicked.connect(self.ouvrir_statistiques)
        self.sidebar.buttons_by_key["ai"].clicked.connect(self.ouvrir_assistant_ia)
        self.sidebar.buttons_by_key["activity"].clicked.connect(self.ouvrir_activite)
        self.sidebar.buttons_by_key["admin_users"].clicked.connect(self.ouvrir_compte_utilisateurs)
        self.sidebar.buttons_by_key["account"].clicked.connect(self.ouvrir_compte)
        self.sidebar.logout_button.clicked.connect(self.deconnexion)

        self.creer_menus()
        self.mettre_a_jour_barre_statut()

        self.update_service = UpdateService(VERSION)
        self._update_check_running = False
        self._update_check_result = None
        self._update_check_error = None
        self._update_check_manual = False
        self._update_poll_timer = QTimer(self)
        self._update_poll_timer.setInterval(250)
        self._update_poll_timer.timeout.connect(self._poll_update_check)

        # Présence Cloud : un heartbeat léger toutes les 60 secondes.
        self._presence_heartbeat_running = False
        self._presence_timer = QTimer(self)
        self._presence_timer.setInterval(60_000)
        self._presence_timer.timeout.connect(self._send_presence_heartbeat)
        if getattr(self.auth_service, "is_cloud", False):
            self._presence_timer.start()
            QTimer.singleShot(8_000, self._send_presence_heartbeat)

        # Vérification discrète après l'ouverture complète de l'application.
        QTimer.singleShot(3500, lambda: self.verifier_mises_a_jour(False))

        # Le premier chargement des données Formateur est différé afin de ne pas
        # ralentir la construction de la fenêtre ni afficher le Dashboard commercial.
        if self.is_trainer_space:
            QTimer.singleShot(1200, self.ouvrir_trainer_dashboard)

    def creer_menus(self):
        menu_compte = self.menuBar().addMenu("Compte")
        action_account = QAction("Mon compte", self)
        action_account.triggered.connect(self.ouvrir_compte)
        menu_compte.addAction(action_account)
        if SessionState.has_role("Administrateur"):
            action_admin_users = QAction("Compte utilisateurs", self)
            action_admin_users.triggered.connect(self.ouvrir_compte_utilisateurs)
            menu_compte.addAction(action_admin_users)
        action_logout = QAction("Se déconnecter", self)
        action_logout.triggered.connect(self.deconnexion)
        menu_compte.addAction(action_logout)

        # Les outils commerciaux ne sont jamais proposés dans l'espace Formateur.
        if not SessionState.has_role("Formateur"):
            menu_outils = self.menuBar().addMenu("Outils")
            action_agenda = QAction("Agenda commercial", self)
            action_agenda.triggered.connect(self.ouvrir_agenda)
            menu_outils.addAction(action_agenda)
            action_campaigns = QAction("Campagnes intelligentes", self)
            action_campaigns.triggered.connect(self.ouvrir_campagnes)
            menu_outils.addAction(action_campaigns)
            action_sales = QAction("Ventes et commissions", self)
            action_sales.triggered.connect(self.ouvrir_commissions)
            menu_outils.addAction(action_sales)
            action_documents = QAction("Documents", self)
            action_documents.triggered.connect(self.ouvrir_documents)
            menu_outils.addAction(action_documents)
            if SessionState.has_role("Administrateur"):
                action_trainers = QAction("Formateurs", self)
                action_trainers.triggered.connect(self.ouvrir_formateurs)
                menu_outils.addAction(action_trainers)
                action_trainer_availability = QAction("Disponibilités formateurs", self)
                action_trainer_availability.triggered.connect(self.ouvrir_disponibilites_formateurs)
                menu_outils.addAction(action_trainer_availability)
                action_commercials = QAction("Commerciaux", self)
                action_commercials.triggered.connect(self.ouvrir_commerciaux)
                menu_outils.addAction(action_commercials)
                action_statistics = QAction("Statistiques administrateur", self)
                action_statistics.triggered.connect(self.ouvrir_statistiques)
                menu_outils.addAction(action_statistics)
            action_cases = QAction("Devis et factures", self)
            action_cases.triggered.connect(self.ouvrir_dossiers_formation)
            menu_outils.addAction(action_cases)
            action_sequences = QAction("Séquences commerciales", self)
            action_sequences.triggered.connect(self.ouvrir_sequences)
            menu_outils.addAction(action_sequences)
            action_ai = QAction("Assistant IA commercial", self)
            action_ai.triggered.connect(self.ouvrir_assistant_ia)
            menu_outils.addAction(action_ai)
            action_activity = QAction("Centre d'activité", self)
            action_activity.triggered.connect(self.ouvrir_activite)
            menu_outils.addAction(action_activity)

        menu_help = self.menuBar().addMenu("Aide")
        action_update = QAction("Rechercher des mises à jour", self)
        action_update.triggered.connect(lambda: self.verifier_mises_a_jour(True))
        menu_help.addAction(action_update)
        menu_help.addSeparator()
        action_about = QAction("À propos de Form@Prospect", self)
        action_about.triggered.connect(lambda: AboutDialog(self).exec())
        menu_help.addAction(action_about)

    def verifier_mises_a_jour(self, manual: bool = False):
        if self._update_check_running:
            if manual:
                QMessageBox.information(
                    self,
                    "Mise à jour",
                    "Une vérification est déjà en cours.",
                )
            return

        self._update_check_running = True
        self._update_check_result = None
        self._update_check_error = None
        self._update_check_manual = bool(manual)

        def worker():
            try:
                self._update_check_result = self.update_service.check_for_update()
            except UpdateError as exc:
                self._update_check_error = str(exc)
            except Exception:
                self._update_check_error = (
                    "Impossible de vérifier les mises à jour pour le moment."
                )
            finally:
                self._update_check_running = False

        threading.Thread(target=worker, daemon=True).start()
        self._update_poll_timer.start()

    def _poll_update_check(self):
        if self._update_check_running:
            return

        self._update_poll_timer.stop()
        manual = self._update_check_manual
        error = self._update_check_error
        info = self._update_check_result

        self._update_check_manual = False
        self._update_check_error = None
        self._update_check_result = None

        if error:
            if manual:
                QMessageBox.warning(
                    self,
                    "Mise à jour",
                    error,
                )
            return

        if info is None:
            if manual:
                QMessageBox.information(
                    self,
                    "Form@Prospect à jour",
                    f"Vous utilisez déjà la dernière version disponible ({VERSION}).",
                )
            return

        UpdateDialog(self.update_service, info, self).exec()

    def _send_presence_heartbeat(self):
        if self._presence_heartbeat_running:
            return
        if not getattr(self.auth_service, "is_cloud", False):
            return
        if not hasattr(self.auth_service, "send_presence_heartbeat"):
            return

        self._presence_heartbeat_running = True

        def worker():
            try:
                self.auth_service.send_presence_heartbeat()
            except Exception:
                # La présence ne doit jamais bloquer l'utilisation du logiciel.
                pass
            finally:
                self._presence_heartbeat_running = False

        threading.Thread(target=worker, daemon=True).start()

    def mettre_a_jour_barre_statut(self):
        try:
            from core.application_state import ApplicationState
            project = ApplicationState.get_project() if ApplicationState.has_project() else None
            project_text = project.name if project else "Aucun projet"
        except Exception:
            project_text = "Aucun projet"
        user = SessionState.user()
        user_text = f"{user.display_name} ({user.role})" if user else "Non connecté"
        if SessionState.has_role("Formateur"):
            self.statusBar().showMessage(
                f"Utilisateur : {user_text}  •  Espace Formateur  •  {APP_NAME} v{VERSION}"
            )
        else:
            self.statusBar().showMessage(
                f"Utilisateur : {user_text}  •  Projet : {project_text}  •  {APP_NAME} v{VERSION}"
            )

    def _refuser_espace_commercial_au_formateur(self) -> bool:
        """Seconde barrière Desktop ; l'API Backend reste l'autorité de sécurité."""
        if not SessionState.has_role("Formateur"):
            return False
        QMessageBox.warning(
            self,
            "Accès interdit",
            "Cette fonction n'est pas disponible dans l'espace Formateur.",
        )
        return True

    def ouvrir_trainer_dashboard(self):
        if not SessionState.has_role("Formateur"):
            return
        self.trainer_dashboard_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainer_dashboard_page)

    def ouvrir_sessions_formateur(self):
        if not SessionState.has_role("Formateur"):
            return
        self.trainer_sessions_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainer_sessions_page)

    def ouvrir_planning_formateur(self):
        if not SessionState.has_role("Formateur"):
            return
        self.trainer_planning_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainer_planning_page)

    def ouvrir_detail_session_formateur(self, session_id: str, return_page=None):
        if not SessionState.has_role("Formateur"):
            return
        session_id = str(session_id or "").strip()
        if not session_id:
            return
        if return_page is not None:
            self._trainer_detail_return_page = return_page
        self.trainer_session_detail_page.charger_session(session_id)
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainer_session_detail_page)

    def retour_session_formateur(self):
        if not SessionState.has_role("Formateur"):
            return
        target = getattr(self, "_trainer_detail_return_page", self.trainer_sessions_page)
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(target)

    def ouvrir_dashboard(self):
        if SessionState.has_role("Formateur"):
            self.ouvrir_trainer_dashboard()
            return
        self.dashboard_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.dashboard_page)

    def ouvrir_traitement(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.treatment_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.treatment_page)

    def ouvrir_prospects(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.prospects_page.charger_prospects()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.prospects_page)

    def ouvrir_agenda(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.agenda_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.agenda_page)

    def ouvrir_campagnes(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.campaigns_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.campaigns_page)

    def ouvrir_sequences(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.sequences_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.sequences_page)

    def ouvrir_commissions(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        # Afficher d'abord la page : une éventuelle erreur Cloud reste ainsi
        # visible dans la zone de statut au lieu de donner l'impression que
        # le bouton ne répond pas.
        self.pages.setCurrentWidget(self.commissions_page)
        self.mettre_a_jour_barre_statut()
        self.commissions_page.rafraichir()

    def ouvrir_documents(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.documents_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.documents_page)


    def ouvrir_formateurs(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.trainers_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainers_page)

    def ouvrir_disponibilites_formateurs(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.trainer_availability_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.trainer_availability_page)

    def ouvrir_commerciaux(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.commercial_profiles_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.commercial_profiles_page)

    def ouvrir_dossiers_formation(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.training_cases_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.training_cases_page)

    def ouvrir_statistiques(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        if not SessionState.has_role("Administrateur"):
            QMessageBox.warning(
                self,
                "Accès interdit",
                "Les statistiques globales sont réservées à l'administrateur.",
            )
            return
        self.pages.setCurrentWidget(self.admin_statistics_page)
        self.mettre_a_jour_barre_statut()
        self.admin_statistics_page.rafraichir()

    def ouvrir_assistant_ia(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.ai_assistant_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.ai_assistant_page)

    def ouvrir_activite(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        self.activity_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.activity_page)

    def ouvrir_compte_utilisateurs(self):
        if self._refuser_espace_commercial_au_formateur():
            return
        if not SessionState.has_role("Administrateur"):
            return
        self.admin_account_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.admin_account_page)

    def ouvrir_compte(self):
        self.account_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.account_page)

    def _refresh_connected_profile(self):
        self.sidebar.refresh_profile()
        self.mettre_a_jour_barre_statut()
        try:
            if SessionState.has_role("Formateur"):
                self.trainer_dashboard_page.rafraichir()
            else:
                self.dashboard_page.rafraichir()
        except Exception:
            pass

    def deconnexion(self):
        answer = QMessageBox.question(
            self, "Déconnexion", "Voulez-vous fermer votre session Form@Prospect ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            if hasattr(self, "_presence_timer"):
                self._presence_timer.stop()
            if hasattr(self.auth_service, "logout"):
                self.auth_service.logout()
            SessionState.logout()
            QApplication.quit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        NotificationManager.reposition()
