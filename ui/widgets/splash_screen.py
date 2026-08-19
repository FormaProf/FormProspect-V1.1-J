from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QSplashScreen

from core.constants import APP_NAME, VERSION, PRIMARY_COLOR
from core.paths import resource_path


class SplashScreen(QSplashScreen):
    """Écran de démarrage professionnel de Form@Prospect."""

    def __init__(self):
        super().__init__(self._create_pixmap())
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

    def _create_pixmap(self):
        width = 620
        height = 420
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fond principal
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E5E7EB"), 1))
        painter.drawRoundedRect(1, 1, width - 2, height - 2, 24, 24)

        # Bandeau bleu discret
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(PRIMARY_COLOR))
        painter.drawRoundedRect(0, 0, width, 10, 4, 4)

        # Logo
        logo_path = resource_path("assets/images/logo_formaprospect.png")
        logo = QPixmap(logo_path)
        if not logo.isNull():
            logo = logo.scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap((width - logo.width()) // 2, 45, logo)

        # Titre
        painter.setPen(QColor("#111827"))
        font_title = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(font_title)
        painter.drawText(0, 235, width, 44, Qt.AlignCenter, APP_NAME)

        # Slogan
        painter.setPen(QColor("#334155"))
        font_subtitle = QFont("Segoe UI", 13, QFont.DemiBold)
        painter.setFont(font_subtitle)
        painter.drawText(0, 282, width, 28, Qt.AlignCenter, "Prospecter • Suivre • Convertir")

        # Version
        painter.setPen(QColor("#6B7280"))
        font_version = QFont("Segoe UI", 11)
        painter.setFont(font_version)
        painter.drawText(0, 318, width, 24, Qt.AlignCenter, f"Version {VERSION}")

        # Barre de chargement décorative
        bar_width = 260
        bar_height = 8
        bar_x = (width - bar_width) // 2
        bar_y = 360
        painter.setBrush(QColor("#E5E7EB"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 4, 4)
        painter.setBrush(QColor(PRIMARY_COLOR))
        painter.drawRoundedRect(bar_x, bar_y, int(bar_width * 0.72), bar_height, 4, 4)

        painter.setPen(QColor("#6B7280"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(0, 378, width, 22, Qt.AlignCenter, "Chargement...")

        painter.end()
        return pixmap
