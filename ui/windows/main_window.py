from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QWidget

from core.constants import *
from core.paths import resource_path
from core.session import SessionState
from services.auth_service import AuthService
from ui.components.notifications import NotificationManager
from ui.dialogs.about_dialog import AboutDialog
from ui.pages.account_page import AccountPage
from ui.pages.ai_assistant_page import AIAssistantPage
from ui.pages.activity_page import ActivityPage
from ui.pages.agenda_page import AgendaPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.documents_page import DocumentsPage
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

        self.dashboard_page = DashboardPage()
        self.treatment_page = TreatmentPage()
        self.prospects_page = ProspectsPage()
        self.agenda_page = AgendaPage()
        self.campaigns_page = CampaignsPage()
        self.sequences_page = SequencesPage()
        self.commissions_page = CommissionsPage()
        self.documents_page = DocumentsPage()
        self.training_cases_page = TrainingCasesPage()
        self.activity_page = ActivityPage()
        self.account_page = AccountPage(auth_service)
        self.account_page.profile_updated.connect(self.sidebar.refresh_profile)
        self.ai_assistant_page = AIAssistantPage()
        for page in (
            self.dashboard_page, self.treatment_page, self.prospects_page,
            self.agenda_page, self.campaigns_page, self.sequences_page, self.commissions_page, self.documents_page, self.training_cases_page, self.ai_assistant_page, self.activity_page, self.account_page,
        ):
            self.pages.addWidget(page)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages)
        self.setCentralWidget(root)
        NotificationManager.configure(self)

        self.sidebar.buttons_by_key["dashboard"].clicked.connect(self.ouvrir_dashboard)
        self.sidebar.buttons_by_key["treatment"].clicked.connect(self.ouvrir_traitement)
        self.sidebar.buttons_by_key["crm"].clicked.connect(self.ouvrir_prospects)
        self.sidebar.buttons_by_key["agenda"].clicked.connect(self.ouvrir_agenda)
        self.sidebar.buttons_by_key["campaigns"].clicked.connect(self.ouvrir_campagnes)
        self.sidebar.buttons_by_key["sequences"].clicked.connect(self.ouvrir_sequences)
        self.sidebar.buttons_by_key["sales"].clicked.connect(self.ouvrir_commissions)
        self.sidebar.buttons_by_key["documents"].clicked.connect(self.ouvrir_documents)
        self.sidebar.buttons_by_key["training_cases"].clicked.connect(self.ouvrir_dossiers_formation)
        self.sidebar.buttons_by_key["statistics"].clicked.connect(self.ouvrir_dashboard)
        self.sidebar.buttons_by_key["ai"].clicked.connect(self.ouvrir_assistant_ia)
        self.sidebar.buttons_by_key["activity"].clicked.connect(self.ouvrir_activite)
        self.sidebar.buttons_by_key["account"].clicked.connect(self.ouvrir_compte)
        self.sidebar.logout_button.clicked.connect(self.deconnexion)

        self.creer_menus()
        self.mettre_a_jour_barre_statut()

    def creer_menus(self):
        menu_compte = self.menuBar().addMenu("Compte")
        action_account = QAction("Compte et utilisateurs" if SessionState.has_role("Administrateur") else "Mon compte", self)
        action_account.triggered.connect(self.ouvrir_compte)
        menu_compte.addAction(action_account)
        action_logout = QAction("Se déconnecter", self)
        action_logout.triggered.connect(self.deconnexion)
        menu_compte.addAction(action_logout)

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
        action_cases = QAction("Dossiers formation", self)
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
        action_about = QAction("À propos de Form@Prospect", self)
        action_about.triggered.connect(lambda: AboutDialog(self).exec())
        menu_help.addAction(action_about)

    def mettre_a_jour_barre_statut(self):
        try:
            from core.application_state import ApplicationState
            project = ApplicationState.get_project() if ApplicationState.has_project() else None
            project_text = project.name if project else "Aucun projet"
        except Exception:
            project_text = "Aucun projet"
        user = SessionState.user()
        user_text = f"{user.display_name} ({user.role})" if user else "Non connecté"
        self.statusBar().showMessage(
            f"Utilisateur : {user_text}  •  Projet : {project_text}  •  {APP_NAME} v{VERSION}"
        )

    def ouvrir_dashboard(self):
        self.dashboard_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.dashboard_page)

    def ouvrir_traitement(self):
        self.treatment_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.treatment_page)

    def ouvrir_prospects(self):
        self.prospects_page.charger_prospects()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.prospects_page)

    def ouvrir_agenda(self):
        self.agenda_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.agenda_page)

    def ouvrir_campagnes(self):
        self.campaigns_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.campaigns_page)

    def ouvrir_sequences(self):
        self.sequences_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.sequences_page)

    def ouvrir_commissions(self):
        self.commissions_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.commissions_page)

    def ouvrir_documents(self):
        self.documents_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.documents_page)


    def ouvrir_dossiers_formation(self):
        self.training_cases_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.training_cases_page)

    def ouvrir_assistant_ia(self):
        self.ai_assistant_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.ai_assistant_page)

    def ouvrir_activite(self):
        self.activity_page.rafraichir()
        self.mettre_a_jour_barre_statut()
        self.pages.setCurrentWidget(self.activity_page)

    def ouvrir_compte(self):
        self.account_page.rafraichir()
        self.pages.setCurrentWidget(self.account_page)

    def deconnexion(self):
        answer = QMessageBox.question(
            self, "Déconnexion", "Voulez-vous fermer votre session Form@Prospect ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            if hasattr(self.auth_service, "logout"):
                self.auth_service.logout()
            SessionState.logout()
            QApplication.quit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        NotificationManager.reposition()
