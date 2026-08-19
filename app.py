import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core.application_state import ApplicationState
from core.constants import APP_NAME, VERSION
from core.paths import resource_path
from core.session import SessionState
from services.auth_service import AuthService
from services.cloud_auth_service import (
    AccountDisabledError,
    CloudAuthError,
    CloudAuthService,
)
from services.cloud_api_client import CloudAPIError
from services.cloud_runtime import CloudRuntime
from ui.dialogs.login_dialog import LoginDialog
from ui.widgets.splash_screen import SplashScreen
from ui.windows.main_window import MainWindow


def activate_commercial_cloud_project(user) -> None:
    """
    Active automatiquement le projet Cloud le plus récemment mis à jour
    pour un utilisateur commercial.

    Les administrateurs et managers conservent leur fonctionnement actuel.
    """

    if user is None:
        return

    if user.role != "Commercial":
        return

    cloud_user_id = getattr(user, "cloud_user_id", "") or ""

    if not cloud_user_id:
        return

    projects_result = CloudRuntime.api().list_projects(
        assigned_to=cloud_user_id,
        sort_by="updated_at",
        sort_direction="desc",
        limit=100,
        offset=0,
    )

    if not projects_result.items:
        ApplicationState.clear_project()
        return

    most_recent_project = projects_result.items[0]
    ApplicationState.set_cloud_project(most_recent_project)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("NM FORMATION")
    app.setWindowIcon(
        QIcon(resource_path("assets/icons/formaprospect.ico"))
    )

    auth_service = CloudAuthService(AuthService())
    CloudRuntime.configure(auth_service)

    try:
        authenticated_user = auth_service.restore_session()
    except (CloudAuthError, CloudAPIError):
        authenticated_user = None

    if authenticated_user is None:
        login = LoginDialog(auth_service)

        if (
            login.exec() != QDialog.Accepted
            or login.authenticated_user is None
        ):
            return 0

        authenticated_user = login.authenticated_user

    SessionState.login(authenticated_user)

    try:
        activate_commercial_cloud_project(authenticated_user)

    except (CloudAuthError, CloudAPIError) as exc:
        QMessageBox.warning(
            None,
            "Projet Cloud indisponible",
            (
                "Votre compte est bien connecté, mais votre projet Cloud "
                "n'a pas pu être chargé.\n\n"
                f"{exc}"
            ),
        )

    splash = SplashScreen()
    splash.show()
    app.processEvents()


    print("[DEBUG 1] Création du splash...", flush=True)

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    print("[DEBUG 2] Splash affiché.", flush=True)
    print("[DEBUG 3] Début de création de MainWindow...", flush=True)

    window = MainWindow(auth_service)

    print("[DEBUG 4] MainWindow créée avec succès.", flush=True)


    session_timer = QTimer(window)
    session_timer.setInterval(60_000)

    def validate_cloud_session():
        try:
            refreshed_user = auth_service.heartbeat()
            SessionState.login(refreshed_user)

        except (AccountDisabledError, CloudAuthError) as exc:
            session_timer.stop()
            ApplicationState.clear_project()
            SessionState.logout()

            QMessageBox.critical(
                window,
                "Session interrompue",
                (
                    "Votre accès Form@Prospect n'est plus valide.\n\n"
                    f"{exc}"
                ),
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
