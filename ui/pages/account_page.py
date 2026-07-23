from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.session import SessionState
from services.auth_service import AuthService
from ui.pages.admin_account_page import AdminAccountPage
from ui.pages.commercial_account_page import CommercialAccountPage


class AccountPage(QWidget):
    profile_updated = Signal()

    def __init__(self, auth_service: AuthService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = AdminAccountPage(auth_service) if SessionState.has_role('Administrateur') else CommercialAccountPage(auth_service)
        if isinstance(self.view, CommercialAccountPage):
            self.view.profile_updated.connect(self.profile_updated)
        layout.addWidget(self.view)

    def rafraichir(self):
        if hasattr(self.view, 'rafraichir'):
            self.view.rafraichir()
