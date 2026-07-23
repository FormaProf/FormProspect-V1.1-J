from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame

from core.constants import APP_NAME, VERSION, PRIMARY_COLOR
from core.paths import resource_path


class AboutDialog(QDialog):
    """Fenêtre À propos de Form@Prospect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"À propos de {APP_NAME}")
        self.setFixedSize(460, 520)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo = QPixmap(resource_path("assets/images/logo_formaprospect.png"))
        if not logo.isNull():
            logo_label.setPixmap(logo.scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 30px; font-weight: 900; color: #111827;")

        version = QLabel(f"Version {VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("font-size: 14px; font-weight: 700; color: #6B7280;")

        slogan = QLabel("Prospecter. Suivre. Convertir.")
        slogan.setAlignment(Qt.AlignCenter)
        slogan.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {PRIMARY_COLOR};")

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E5E7EB;")

        description = QLabel(
            "CRM de prospection B2B conçu pour importer, suivre, qualifier et convertir vos prospects."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("font-size: 13px; color: #374151; line-height: 1.4;")

        company = QLabel("Développé par NM FORMATION")
        company.setAlignment(Qt.AlignCenter)
        company.setStyleSheet("font-size: 14px; font-weight: 800; color: #111827;")

        copyright_label = QLabel("© 2026 NM FORMATION — Tous droits réservés")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("font-size: 12px; color: #6B7280;")

        close_button = QPushButton("Fermer")
        close_button.setFixedHeight(42)
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background-color: #256DB4;
            }}
            QPushButton:pressed {{
                background-color: #1D4F86;
            }}
        """)

        layout.addWidget(logo_label)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(slogan)
        layout.addWidget(separator)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addWidget(company)
        layout.addWidget(copyright_label)
        layout.addStretch()
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
        """)
