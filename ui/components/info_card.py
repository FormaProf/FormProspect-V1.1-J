from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from core.theme import INFO_SOFT, PRIMARY_COLOR, TEXT_PRIMARY, TEXT_SECONDARY


class InfoCard(QFrame):
    """Carte d'information pour le prospect et l'étape en cours."""

    def __init__(self, title="Entreprise en cours", value="—", detail="En attente", parent=None):
        super().__init__(parent)
        self.setObjectName("infoCard")
        self.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: {INFO_SOFT};
                border: 1px solid #BFDBFE;
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {PRIMARY_COLOR}; font-size: 12px; font-weight: 800; border: none;"
        )
        self.value_label = QLabel(value)
        self.value_label.setWordWrap(True)
        self.value_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 900; border: none;"
        )
        self.detail_label = QLabel(detail)
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; border: none;"
        )
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_info(self, value, detail=""):
        self.value_label.setText(value or "—")
        self.detail_label.setText(detail or "")
