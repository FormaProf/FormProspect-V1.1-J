from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag

from core.crm import PRIORITE_DEFAULT, ACTION_DEFAULT


class KanbanCard(QFrame):
    """Carte prospect affichée dans la vue Kanban.

    La carte accepte aussi bien les identifiants locaux numériques que
    les identifiants Cloud UUID.
    """

    double_clicked = Signal(object)
    MIME_TYPE = "application/x-formaprospect-kanban-card"

    def __init__(self, prospect):
        super().__init__()
        self.prospect = prospect

        # Ne jamais forcer l'identifiant en int :
        # - en local, il peut être numérique ;
        # - dans le Cloud, il s'agit d'un UUID sous forme de chaîne.
        self.prospect_id = prospect[0]
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
        self.setMinimumWidth(236)
        self.setMaximumWidth(272)
        self.setStyleSheet(self._style_normal())

        layout = QVBoxLayout()
        layout.setContentsMargins(13, 12, 13, 12)
        layout.setSpacing(8)

        titre = QLabel(str(entreprise))
        titre.setWordWrap(True)
        titre.setStyleSheet(
            "font-size:14px; font-weight:900; color:#111827; letter-spacing:0.1px;"
        )

        infos_layout = QVBoxLayout()
        infos_layout.setSpacing(5)

        ville_label = self._label_info(f"Ville  •  {ville}")
        tel_label = self._label_info(f"Tél.  •  {telephone}")
        action_label = self._label_info(f"Action  •  {prochaine_action}")

        score_label = QLabel(f"{score_grade}  {score}/100")
        score_label.setStyleSheet(
            """
            QLabel {
                background-color: #F1F8FF;
                color: #075985;
                border: 1px solid #D5EAFE;
                border-radius: 9px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 900;
            }
            """
        )

        bas_layout = QHBoxLayout()
        bas_layout.setContentsMargins(0, 0, 0, 0)
        bas_layout.setSpacing(6)

        priorite_label = QLabel(str(priorite))
        priorite_label.setStyleSheet(
            """
            QLabel {
                background-color: #FFF9E8;
                color: #9A6700;
                border: 1px solid #F4E2A0;
                border-radius: 9px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 800;
            }
            """
        )

        commercial_label = QLabel(str(commercial))
        commercial_label.setStyleSheet(
            """
            QLabel {
                background-color: #F5F8FC;
                color: #334155;
                border: 1px solid #E2E8F0;
                border-radius: 9px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 800;
            }
            """
        )
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
                background-color:#FFFFFF;
                border:1px solid #E3EAF2;
                border-radius:14px;
            }
            QFrame#KanbanCard:hover {
                border:1px solid #A9CEF1;
                background-color:#FCFEFF;
            }
            QLabel {
                background:transparent;
            }
        """

    def _label_info(self, texte):
        label = QLabel(texte)
        label.setWordWrap(True)
        label.setStyleSheet("font-size:11px; color:#62748A; font-weight:650;")
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

        distance = (
            event.position().toPoint() - self._drag_start_position
        ).manhattanLength()

        if distance < 10:
            return super().mouseMoveEvent(event)

        self._start_drag()

    def _start_drag(self):
        mime_data = QMimeData()
        mime_data.setData(
            self.MIME_TYPE,
            str(self.prospect_id).encode("utf-8"),
        )

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self._drag_pixmap())
        drag.setHotSpot(self.rect().center())

        self.setCursor(Qt.OpenHandCursor)
        drag.exec(Qt.MoveAction)

    def _drag_pixmap(self):
        """Retourne une image de la carte pour le glisser-déposer."""
        return self.grab()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.prospect_id)
        super().mouseDoubleClickEvent(event)
