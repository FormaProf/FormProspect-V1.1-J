from datetime import datetime

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QStyle
)
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QFont
from PySide6.QtCore import Qt, QSettings, QTimer, Signal, QRect

from core.crm import PIPELINE_DEFAULT, PIPELINE_COLORS, PRIORITE_DEFAULT, ACTION_DEFAULT


class SortableTableWidgetItem(QTableWidgetItem):
    """Item de tableau avec une valeur de tri propre."""

    def __init__(self, text="", sort_value=None):
        super().__init__(text)
        self.sort_value = text.lower() if sort_value is None and isinstance(text, str) else sort_value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem):
            left = self.sort_value
            right = other.sort_value
            try:
                return left < right
            except TypeError:
                return str(left) < str(right)
        return super().__lt__(other)


class PremiumCRMDelegate(QStyledItemDelegate):
    """Rendu premium : cellules aérées et badges arrondis."""

    PIPELINE_BADGES = {
        "🟢 Nouveau": ("Nouveau", "#ECFDF3", "#166534", "#BBF7D0"),
        "🟡 Qualification": ("Qualification", "#FFFBEB", "#854D0E", "#FDE68A"),
        "🔵 RDV programmé": ("RDV programmé", "#EFF8FF", "#075985", "#BAE6FD"),
        "🟣 Proposition envoyée": ("Proposition envoyée", "#FAF5FF", "#6B21A8", "#E9D5FF"),
        "🟠 Négociation": ("Négociation", "#FFF7ED", "#9A3412", "#FED7AA"),
        "🟢 Client": ("Client", "#ECFDF3", "#166534", "#86EFAC"),
        "🔴 Perdu": ("Perdu", "#FEF2F2", "#991B1B", "#FECACA"),
    }

    def paint(self, painter, option, index):
        painter.save()

        # Fond de ligne / sélection.
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#EAF4FF"))
        elif index.row() % 2:
            painter.fillRect(option.rect, QColor("#FBFDFF"))
        else:
            painter.fillRect(option.rect, QColor("#FFFFFF"))

        col = index.column()
        raw = str(index.data(Qt.DisplayRole) or "")

        if col == 8:
            self._paint_pipeline_badge(painter, option.rect, raw)
        elif col == 9:
            self._paint_priority_badge(painter, option.rect, raw)
        elif col == 13:
            self._paint_score_badge(painter, option.rect, raw)
        elif col == 14:
            self._paint_level_badge(painter, option.rect, raw)
        else:
            self._paint_text(painter, option.rect, raw, col)

        # séparateur discret
        pen = QPen(QColor("#EEF2F6"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(
            option.rect.left(),
            option.rect.bottom(),
            option.rect.right(),
            option.rect.bottom(),
        )
        painter.restore()

    def _paint_text(self, painter, rect, text, col):
        color = QColor("#1F2937")
        font = painter.font()

        if col == 1:  # Entreprise
            font.setBold(True)
            color = QColor("#111827")
        elif text in {"", "—"}:
            color = QColor("#A7B2C0")
        elif col == 10 and text.lower() not in {"", "aucune", "—"}:
            font.setBold(True)
            color = QColor("#334155")

        painter.setFont(font)
        painter.setPen(color)

        alignment = Qt.AlignVCenter | (
            Qt.AlignCenter if col in {0, 3, 4, 5, 11, 12} else Qt.AlignLeft
        )
        inner = rect.adjusted(10, 0, -10, 0)
        metrics = painter.fontMetrics()
        elided = metrics.elidedText(text, Qt.ElideRight, inner.width())
        painter.drawText(inner, alignment, elided)

    def _paint_pipeline_badge(self, painter, rect, raw):
        label, bg, fg, border = self.PIPELINE_BADGES.get(
            raw, (raw, "#F8FAFC", "#475569", "#E2E8F0")
        )
        self._paint_badge(painter, rect, label, bg, fg, border)

    def _paint_priority_badge(self, painter, rect, raw):
        stars = raw or "☆☆☆☆☆"
        filled = stars.count("★")
        if filled >= 4:
            bg, fg, border = "#FFF8E6", "#A16207", "#F6D98B"
        elif filled >= 2:
            bg, fg, border = "#FFFBEB", "#9A6700", "#F5E7A6"
        else:
            bg, fg, border = "#F8FAFC", "#64748B", "#E2E8F0"
        self._paint_badge(painter, rect, stars, bg, fg, border)

    def _paint_score_badge(self, painter, rect, raw):
        try:
            value = int(raw.split("/", 1)[0].strip())
        except Exception:
            value = 0
        if value >= 80:
            bg, fg, border = "#ECFDF3", "#166534", "#BBF7D0"
        elif value >= 60:
            bg, fg, border = "#EFF8FF", "#075985", "#BAE6FD"
        elif value >= 40:
            bg, fg, border = "#FFFBEB", "#854D0E", "#FDE68A"
        elif value > 0:
            bg, fg, border = "#FFF7ED", "#9A3412", "#FED7AA"
        else:
            bg, fg, border = "#F8FAFC", "#64748B", "#E2E8F0"
        self._paint_badge(painter, rect, raw, bg, fg, border)

    def _paint_level_badge(self, painter, rect, raw):
        self._paint_badge(
            painter, rect, raw or "—",
            "#F8FAFC", "#475569", "#E2E8F0"
        )

    def _paint_badge(self, painter, rect, text, bg, fg, border):
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(8, font.pointSize() - 1))
        painter.setFont(font)

        metrics = painter.fontMetrics()
        width = min(rect.width() - 16, max(64, metrics.horizontalAdvance(text) + 24))
        height = min(28, rect.height() - 10)
        x = rect.center().x() - width // 2
        y = rect.center().y() - height // 2
        badge = QRect(x, y, width, height)

        painter.setPen(QPen(QColor(border)))
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(badge, 9, 9)

        painter.setPen(QColor(fg))
        painter.drawText(badge, Qt.AlignCenter, text)


class ProspectsTableWidget(QTableWidget):
    """Tableau CRM réutilisable pour l'affichage des prospects."""

    prospect_double_clicked = Signal(object)

    SETTINGS_GROUP = "prospects_table"

    PIPELINE_ORDER = {
        "🟢 Nouveau": 1,
        "🟡 Qualification": 2,
        "🔵 RDV programmé": 3,
        "🟣 Proposition envoyée": 4,
        "🟠 Négociation": 5,
        "🟢 Client": 6,
        "🔴 Perdu": 7,
    }

    COLUMN_WIDTHS = {
        0: 52,    # N°
        1: 245,   # Entreprise
        2: 145,   # Ville
        3: 78,    # CP
        4: 128,   # Téléphone
        5: 128,   # Mobile
        6: 150,   # Site web
        7: 190,   # Email
        8: 178,   # Pipeline
        9: 118,   # Priorité
        10: 190,  # Prochaine action
        11: 118,  # Date action
        12: 145,  # Commercial
        13: 105,  # Score
        14: 120,  # Niveau
    }

    def __init__(self):
        super().__init__()
        self.prospect_ids = []
        self.settings = QSettings("NM FORMATION", "Form@Prospect")
        self._loading_table = False

        self.setColumnCount(15)
        self.setHorizontalHeaderLabels([
            "N°",
            "Entreprise",
            "Ville",
            "CP",
            "Téléphone",
            "Mobile",
            "Site web",
            "Email",
            "Pipeline",
            "Priorité",
            "Prochaine action",
            "Date action",
            "Commercial",
            "Score",
            "Niveau",
        ])

        self.cellDoubleClicked.connect(self._handle_double_click)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(Qt.StrongFocus)

        header = self.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.sectionResized.connect(self.sauvegarder_largeur_colonne)

        self.setItemDelegate(PremiumCRMDelegate(self))
        self.setStyleSheet(self.style_tableau())
        QTimer.singleShot(0, self.restaurer_largeurs_colonnes)

    def style_tableau(self):
        return """
            QTableWidget {
                background:#FFFFFF;
                color:#1F2937;
                border:1px solid #DDE6F0;
                border-radius:18px;
                gridline-color:transparent;
                font-size:12px;
                outline:0;
            }
            QHeaderView {
                background:#0B2A52;
                border:none;
            }
            QHeaderView::section {
                background:#0B2A52;
                color:#FFFFFF;
                font-weight:900;
                font-size:10px;
                padding:12px 8px;
                border:none;
                border-right:1px solid rgba(255,255,255,0.08);
            }
            QHeaderView::section:hover {
                background:#123966;
            }
            QTableCornerButton::section {
                background:#0B2A52;
                border:none;
            }
            QScrollBar:vertical {
                background:transparent;
                width:10px;
                margin:4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background:#CBD5E1;
                min-height:38px;
                border-radius:5px;
            }
            QScrollBar::handle:vertical:hover {
                background:#94A3B8;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height:0;
            }
            QScrollBar:horizontal {
                background:transparent;
                height:10px;
                margin:2px 4px 2px 4px;
            }
            QScrollBar::handle:horizontal {
                background:#CBD5E1;
                min-width:38px;
                border-radius:5px;
            }
            QScrollBar::handle:horizontal:hover {
                background:#94A3B8;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width:0;
            }
        """

    def creer_item(self, texte, sort_value=None, alignement=None, prospect_id=None):
        item = SortableTableWidgetItem(str(texte or ""), sort_value)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        if alignement is not None:
            item.setTextAlignment(alignement)

        if prospect_id is not None:
            item.setData(Qt.UserRole, prospect_id)

        return item

    def normaliser_date_tri(self, valeur):
        if not valeur:
            return "9999-12-31"

        texte = str(valeur).strip()
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]

        for fmt in formats:
            try:
                return datetime.strptime(texte, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

        return texte.lower()

    def style_pipeline(self, item, pipeline):
        # Le delegate PremiumCRMDelegate peint le badge arrondi.
        item.setText(str(pipeline or ""))
        item.setTextAlignment(Qt.AlignCenter)

    def afficher_lignes(self, prospects, start_number=1):
        self._loading_table = True
        self.prospect_ids = []
        self.setSortingEnabled(False)
        self.setRowCount(len(prospects))

        for row_index, prospect in enumerate(prospects):
            prospect_id = prospect[0]
            entreprise = prospect[1]
            ville = prospect[2]
            code_postal = prospect[3]
            telephone = prospect[4]
            mobile = prospect[15] if len(prospect) > 15 and prospect[15] else ""
            site_web = prospect[5]
            email = prospect[6]
            pipeline = prospect[7] if len(prospect) > 7 and prospect[7] else PIPELINE_DEFAULT
            priorite = prospect[8] if len(prospect) > 8 and prospect[8] else PRIORITE_DEFAULT
            prochaine_action = prospect[9] if len(prospect) > 9 and prospect[9] else ACTION_DEFAULT
            date_prochaine_action = prospect[10] if len(prospect) > 10 and prospect[10] else ""
            commercial_assigne = prospect[11] if len(prospect) > 11 and prospect[11] else ""
            score_prospect = prospect[12] if len(prospect) > 12 and prospect[12] is not None else 0
            score_grade = prospect[13] if len(prospect) > 13 and prospect[13] else "★☆☆☆☆"
            score_label = prospect[14] if len(prospect) > 14 and prospect[14] else "Données insuffisantes"

            self.prospect_ids.append(prospect_id)

            items = [
                self.creer_item(start_number + row_index, start_number + row_index, Qt.AlignCenter, prospect_id),
                self.creer_item(entreprise, str(entreprise or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(ville, str(ville or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(code_postal, str(code_postal or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(telephone, str(telephone or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(mobile, str(mobile or ""), Qt.AlignCenter, prospect_id),
                self.creer_item(site_web, str(site_web or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(email, str(email or "").lower(), Qt.AlignVCenter, prospect_id),
                self.creer_item(pipeline, self.PIPELINE_ORDER.get(pipeline, 999), Qt.AlignCenter, prospect_id),
                self.creer_item(priorite, len(str(priorite or "")), Qt.AlignCenter, prospect_id),
                self.creer_item(prochaine_action, str(prochaine_action or "").lower(), Qt.AlignCenter, prospect_id),
                self.creer_item(
                    date_prochaine_action,
                    self.normaliser_date_tri(date_prochaine_action),
                    Qt.AlignCenter,
                    prospect_id,
                ),
                self.creer_item(commercial_assigne, str(commercial_assigne or "").lower(), Qt.AlignCenter, prospect_id),
                self.creer_item(f"{score_prospect}/100", int(score_prospect or 0), Qt.AlignCenter, prospect_id),
                self.creer_item(score_grade, int(score_prospect or 0), Qt.AlignCenter, prospect_id),
            ]
            items[14].setToolTip(score_label)

            self.style_pipeline(items[8], pipeline)

            # Les données manquantes deviennent visuellement discrètes.
            if not str(telephone or "").strip():
                items[4].setText("—")
            if not str(mobile or "").strip():
                items[5].setText("—")
            if not str(site_web or "").strip():
                items[6].setText("—")
            if not str(email or "").strip():
                items[7].setText("—")
            if str(prochaine_action or "").strip().lower() in {"", "aucune"}:
                items[10].setText("Aucune")

            for col_index, item in enumerate(items):
                self.setItem(row_index, col_index, item)

            self.setRowHeight(row_index, 46)

        self.setSortingEnabled(True)
        self.restaurer_largeurs_colonnes()
        self._loading_table = False

    def restaurer_largeurs_colonnes(self):
        header = self.horizontalHeader()

        for col_index, largeur_defaut in self.COLUMN_WIDTHS.items():
            largeur = self.settings.value(
                f"{self.SETTINGS_GROUP}/column_{col_index}_width",
                largeur_defaut,
                type=int,
            )
            header.resizeSection(col_index, largeur)

    def sauvegarder_largeur_colonne(self, logical_index, old_size, new_size):
        if self._loading_table:
            return

        if new_size <= 0:
            return

        self.settings.setValue(
            f"{self.SETTINGS_GROUP}/column_{logical_index}_width",
            new_size,
        )

    def prospect_id_from_row(self, row):
        item_id = self.item(row, 0)
        if item_id is None:
            return None
        return item_id.data(Qt.UserRole)

    def _handle_double_click(self, row, column):
        prospect_id = self.prospect_id_from_row(row)
        if prospect_id is not None:
            # Les projets locaux utilisent des identifiants entiers, tandis que
            # le Cloud utilise des UUID. Le signal doit transmettre l'identifiant
            # tel quel au lieu de forcer une conversion en int.
            self.prospect_double_clicked.emit(prospect_id)
