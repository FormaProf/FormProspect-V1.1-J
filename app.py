import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core.constants import APP_NAME, VERSION
from core.paths import resource_path
from core.session import SessionState
from services.auth_service import AuthService
from services.cloud_auth_service import AccountDisabledError, CloudAuthError, CloudAuthService
from services.cloud_runtime import CloudRuntime
from ui.dialogs.login_dialog import LoginDialog
from ui.widgets.splash_screen import SplashScreen
from ui.windows.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("NM FORMATION")
    app.setWindowIcon(QIcon(resource_path("assets/icons/formaprospect.ico")))

    auth_service = CloudAuthService(AuthService())
    CloudRuntime.configure(auth_service)
    restored_user = auth_service.restore_session()

    if restored_user is None:
        login = LoginDialog(auth_service)
        if login.exec() != QDialog.Accepted or login.authenticated_user is None:
            return 0
        SessionState.login(login.authenticated_user)
    else:
        SessionState.login(restored_user)

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    window = MainWindow(auth_service)

    session_timer = QTimer(window)
    session_timer.setInterval(60_000)

    def validate_cloud_session():
        try:
            SessionState.login(auth_service.heartbeat())
        except (AccountDisabledError, CloudAuthError) as exc:
            session_timer.stop()
            SessionState.logout()
            QMessageBox.critical(
                window,
                "Session interrompue",
                f"Votre accès Form@Prospect n'est plus valide.\n\n{exc}",
            )
            QApplication.quit()

    session_timer.timeout.connect(validate_cloud_session)
    session_timer.start()

    def show_main_window():
        window.show()
        splash.finish(window)

    QTimer.singleShot(900, show_main_window)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
