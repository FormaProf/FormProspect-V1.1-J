from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt

from core.constants import APP_NAME, PRIMARY_COLOR
from ui.dialogs.new_project_dialog import NewProjectDialog


class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(25)

        titre = QLabel(APP_NAME)
        titre.setAlignment(Qt.AlignCenter)
        titre.setStyleSheet("""
            font-size: 42px;
            font-weight: 800;
            color: #111827;
        """)

        sous_titre = QLabel("Prospection intelligente B2B")
        sous_titre.setAlignment(Qt.AlignCenter)
        sous_titre.setStyleSheet("""
            font-size: 18px;
            color: #6B7280;
        """)

        card = QFrame()
        card.setFixedWidth(520)
        card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 18px;
                border: 1px solid #E5E7EB;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 30, 35, 30)
        card_layout.setSpacing(18)

        btn_nouveau = QPushButton("➕ Nouveau projet")
        btn_nouveau.clicked.connect(self.ouvrir_nouveau_projet)

        btn_ouvrir = QPushButton("📂 Ouvrir un projet")

        for btn in [btn_nouveau, btn_ouvrir]:
            btn.setFixedHeight(46)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PRIMARY_COLOR};
                    color: white;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #256DB4;
                }}
            """)

        card_layout.addWidget(btn_nouveau)
        card_layout.addWidget(btn_ouvrir)

        layout.addWidget(titre)
        layout.addWidget(sous_titre)
        layout.addWidget(card)

        self.setLayout(layout)

    def ouvrir_nouveau_projet(self):
        dialog = NewProjectDialog()
        dialog.exec()