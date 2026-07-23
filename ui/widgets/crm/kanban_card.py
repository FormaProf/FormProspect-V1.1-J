from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag

from core.crm import PRIORITE_DEFAULT, ACTION_DEFAULT


class KanbanCard(QFrame):
    """Carte prospect affichée dans la vue Kanban.

    La carte est également déplaçable en drag & drop. Elle transporte
    uniquement l'identifiant du prospect afin que la colonne cible puisse
    demander la mise à jour du pipeline sans manipuler directement la base.
    """

    double_clicked = Signal(object)
    MIME_TYPE = "application/x-formaprospect-kanban-card"

    def __init__(self, prospect):
        super().__init__()
        self.prospect = prospect
        self.prospect_id = int(prospect[0])
        self._drag_start_position = None

        entreprise = prospect[1] or "Sans nom"
        ville = prospect[2] or "Ville non renseignée"
        telephone = prospect[4] or "Téléphone non renseigné"
        priorite = prospect[8] if len(prospect) > 8 and prospect[8] else PRIORITE_DEFAULT
        prochaine_action = prospect[9] if len(prospect) > 9 and prospect[9] else ACTION_DEFAULT
        commercial = prospect[11] if len(prospect) > 11 and prospect[11] else "Non assigné"
        score = prospect[12] if len(prospect) > 12 and prospect[12] is not None else 0
        score_grade = prospect[13] if len(prospect) > 13 and prospect[13] else "★☆☆☆☆"

        self.setObjectName("KanbanCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumWidth(230)
        self.setMaximumWidth(260)
        self.setStyleSheet(self._style_normal())

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(7)

        titre = QLabel(f"🏢 {entreprise}")
        titre.setWordWrap(True)
        titre.setStyleSheet("font-size: 14px; font-weight: 800; color: #111827;")

        infos_layout = QVBoxLayout()
        infos_layout.setSpacing(5)

        ville_label = self._label_info(f"📍 {ville}")
        tel_label = self._label_info(f"☎ {telephone}")
        action_label = self._label_info(f"📅 {prochaine_action}")

        score_label = QLabel(f"{score_grade}  {score}/100")
        score_label.setStyleSheet("""
            QLabel {
                background-color: #ECFDF5;
                color: #047857;
                border-radius: 8px;
                padding: 4px 7px;
                font-size: 12px;
                font-weight: 800;
            }
        """)

        bas_layout = QHBoxLayout()
        bas_layout.setContentsMargins(0, 0, 0, 0)
        bas_layout.setSpacing(6)

        priorite_label = QLabel(str(priorite))
        priorite_label.setStyleSheet("""
            QLabel {
                background-color: #FEF3C7;
                color: #92400E;
                border-radius: 8px;
                padding: 4px 7px;
                font-size: 12px;
                font-weight: 700;
            }
        """)

        commercial_label = QLabel(f"👤 {commercial}")
        commercial_label.setStyleSheet("""
            QLabel {
                background-color: #EFF6FF;
                color: #1D4ED8;
                border-radius: 8px;
                padding: 4px 7px;
                font-size: 12px;
                font-weight: 700;
            }
        """)
        commercial_label.setWordWrap(True)

        bas_layout.addWidget(priorite_label)
        bas_layout.addWidget(commercial_label, 1)

        infos_layout.addWidget(ville_label)
        infos_layout.addWidget(tel_label)
        infos_layout.addWidget(action_label)

        layout.addWidget(titre)
        layout.addLayout(infos_layout)
        layout.addWidget(score_label)
        layout.addLayout(bas_layout)
        self.setLayout(layout)

    def _style_normal(self):
        return """
            QFrame#KanbanCard {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
            QFrame#KanbanCard:hover {
                border: 1px solid #338CE4;
                background-color: #F8FBFF;
            }
            QLabel {
                background: transparent;
            }
        """

    def _label_info(self, texte):
        label = QLabel(texte)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 12px; color: #4B5563;")
        return label

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)

        if self._drag_start_position is None:
            return super().mouseMoveEvent(event)

        distance = (event.position().toPoint() - self._drag_start_position).manhattanLength()
        if distance < 10:
            return super().mouseMoveEvent(event)

        self._start_drag()

    def _start_drag(self):
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, str(self.prospect_id).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._drag_pixmap())
        drag.setHotSpot(self.rect().center())

        self.setCursor(Qt.OpenHandCursor)
        drag.exec(Qt.MoveAction)

    def _drag_pixmap(self):
        """Retourne une image de la carte pour le glisser-déposer.

        En PySide6, QWidget.render(QPainter) peut être sensible aux surcharges
        selon les versions. QWidget.grab() est plus robuste et suffit ici :
        il capture visuellement la carte sans provoquer d'erreur de type.
        """
        return self.grab()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.prospect_id)
        super().mouseDoubleClickEvent(event)
