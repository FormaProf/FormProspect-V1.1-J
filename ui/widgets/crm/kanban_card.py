from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag

from core.crm import PRIORITE_DEFAULT, ACTION_DEFAULT
from ui.crm_premium_theme import (
    CRM_THEME_CLASSIC,
    CRM_THEME_DARK,
    crm_palette,
    normalize_crm_theme,
)


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
        self._current_theme = CRM_THEME_CLASSIC

        entreprise = prospect[1] or "Sans nom"
        ville = prospect[2] or "Ville non renseignée"
        telephone = prospect[4] or "Téléphone non renseigné"
        priorite = prospect[8] if len(prospect) > 8 and prospect[8] else PRIORITE_DEFAULT
        prochaine_action = prospect[9] if len(prospect) > 9 and prospect[9] else ACTION_DEFAULT
        commercial = prospect[11] if len(prospect) > 11 and prospect[11] else "Non assigné"
        self._commercial_raw = str(commercial).strip() or "Non assigné"
        self._commercial_display = self._compact_commercial_name(self._commercial_raw)
        source = prospect[16] if len(prospect) > 16 and prospect[16] else "Non renseignee"
        score = prospect[12] if len(prospect) > 12 and prospect[12] is not None else 0
        score_grade = prospect[13] if len(prospect) > 13 and prospect[13] else "★☆☆☆☆"
        self._classic_score_text = f"{score_grade}  {score}/100"
        self._premium_score_text = f"Score  •  {score}/100"

        self.setObjectName("KanbanCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumWidth(236)
        self.setMaximumWidth(272)
        self.setStyleSheet(self._style_normal())

        layout = QVBoxLayout()
        layout.setContentsMargins(13, 12, 13, 12)
        layout.setSpacing(8)

        titre = QLabel(str(entreprise))
        self.title_label = titre
        titre.setWordWrap(True)
        titre.setStyleSheet(
            "font-size:14px; font-weight:900; color:#111827; letter-spacing:0.1px;"
        )

        infos_layout = QVBoxLayout()
        infos_layout.setSpacing(5)

        ville_label = self._label_info(f"Ville  •  {ville}")
        tel_label = self._label_info(f"Tél.  •  {telephone}")
        action_label = self._label_info(f"Action  •  {prochaine_action}")
        source_label = self._label_info(f"Source : {source}")
        self.info_labels = (
            ville_label,
            tel_label,
            action_label,
            source_label,
        )

        score_label = QLabel(self._classic_score_text)
        self.score_label = score_label
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
        self.priority_label = priorite_label
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

        commercial_label = QLabel(self._commercial_raw)
        self.commercial_label = commercial_label
        commercial_label.setToolTip(self._commercial_raw)
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
        infos_layout.addWidget(source_label)

        layout.addWidget(titre)
        layout.addLayout(infos_layout)
        layout.addWidget(score_label)
        layout.addLayout(bas_layout)
        self.setLayout(layout)

    def apply_theme(self, theme=None):
        theme = normalize_crm_theme(theme)
        self._current_theme = theme

        if theme == CRM_THEME_CLASSIC:
            self.score_label.setText(self._classic_score_text)
            self.commercial_label.setText(self._commercial_raw)
            self.commercial_label.setWordWrap(True)
            self.setStyleSheet(self._style_normal())
            self.title_label.setStyleSheet(
                "font-size:14px; font-weight:900; color:#111827; letter-spacing:0.1px;"
            )
            for label in self.info_labels:
                label.setStyleSheet(
                    "font-size:11px; color:#62748A; font-weight:650;"
                )
            self.score_label.setStyleSheet(
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
            self.priority_label.setStyleSheet(
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
            self.commercial_label.setStyleSheet(
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
            return

        self.score_label.setText(self._premium_score_text)
        self.commercial_label.setText(f"Commercial  •  {self._commercial_display}")
        self.commercial_label.setWordWrap(False)

        p = crm_palette(theme)
        dark = theme == CRM_THEME_DARK
        card_bg = "#0D2034" if dark else "#FFFFFF"
        card_hover = "#102944" if dark else "#F9FCFF"
        score_bg = "#0D2D46" if dark else "#EAF6FF"
        priority_bg = "#332A13" if dark else "#FFF8E7"
        commercial_bg = "transparent"

        self.setStyleSheet(f"""
            QFrame#KanbanCard {{
                background:{card_bg};
                border:1px solid {p['border']};
                border-radius:15px;
            }}
            QFrame#KanbanCard:hover {{
                background:{card_hover};
                border:1px solid {p['cyan']};
            }}
            QLabel {{
                background:transparent;
            }}
        """)
        self.title_label.setStyleSheet(
            f"font-size:14px; font-weight:950; color:{p['text']}; "
            "letter-spacing:0.1px; background:transparent; border:none;"
        )
        for label in self.info_labels:
            label.setStyleSheet(
                f"font-size:11px; color:{p['muted']}; font-weight:700; "
                "background:transparent; border:none;"
            )
        self.score_label.setStyleSheet(f"""
            QLabel {{
                background:{score_bg};
                color:{p['cyan']};
                border:1px solid {p['border_strong']};
                border-radius:8px;
                padding:4px 7px;
                font-size:10px;
                font-weight:950;
            }}
        """)
        self.priority_label.setStyleSheet(f"""
            QLabel {{
                background:{priority_bg};
                color:{'#F4C96B' if dark else '#9A6700'};
                border:1px solid {p['border']};
                border-radius:8px;
                padding:4px 7px;
                font-size:10px;
                font-weight:850;
            }}
        """)
        self.commercial_label.setStyleSheet(f"""
            QLabel {{
                background:{commercial_bg};
                color:{p['muted']};
                border:none;
                padding:2px 3px;
                font-size:10px;
                font-weight:800;
            }}
        """)

    @staticmethod
    def _compact_commercial_name(raw):
        text = str(raw or "").strip()
        if not text:
            return "Non assigné"

        first_line = text.splitlines()[0].strip()
        for marker in (" (", " <", " | "):
            if marker in first_line:
                first_line = first_line.split(marker, 1)[0].strip()
        if "@" in first_line and " " not in first_line:
            return first_line
        if len(first_line) > 24:
            return first_line[:23].rstrip() + "…"
        return first_line

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
