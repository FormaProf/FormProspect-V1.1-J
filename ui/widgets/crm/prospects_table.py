from datetime import datetime

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import Qt, QSettings, QTimer, Signal

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
        0: 58,    # N°
        1: 250,   # Entreprise
        2: 140,   # Ville
        3: 85,    # CP
        4: 130,   # Téléphone
        5: 150,   # Site web
        6: 190,   # Email
        7: 150,   # Pipeline
        8: 95,    # Priorité
        9: 170,   # Prochaine action
        10: 120,  # Date action
        11: 140,  # Commercial
        12: 100,  # Score
        13: 110,  # Niveau
    }

    def __init__(self):
        super().__init__()
        self.prospect_ids = []
        self.settings = QSettings("NM FORMATION", "Form@Prospect")
        self._loading_table = False

        self.setColumnCount(14)
        self.setHorizontalHeaderLabels([
            "N°",
            "Entreprise",
            "Ville",
            "CP",
            "Téléphone",
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
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
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

        self.setStyleSheet(self.style_tableau())
        QTimer.singleShot(0, self.restaurer_largeurs_colonnes)

    def style_tableau(self):
        return """
            QTableWidget {
                background-color: white;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                gridline-color: #E5E7EB;
                font-size: 13px;
                color: #111827;
                selection-background-color: #DBEAFE;
                selection-color: #111827;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #DBEAFE;
                color: #111827;
            }
            QHeaderView::section {
                background-color: #F3F4F6;
                color: #111827;
                font-weight: 800;
                padding: 9px;
                border: none;
                border-right: 1px solid #E5E7EB;
                border-bottom: 1px solid #D1D5DB;
            }
            QHeaderView::section:hover {
                background-color: #E5E7EB;
            }
            QTableCornerButton::section {
                background-color: #F3F4F6;
                border: none;
            }
            QScrollBar:vertical {
                background: #F3F4F6;
                width: 12px;
                margin: 0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar:horizontal {
                background: #F3F4F6;
                height: 12px;
                margin: 0;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                min-width: 30px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94A3B8;
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
        couleur_fond = PIPELINE_COLORS.get(pipeline, "#FFFFFF")
        item.setBackground(QBrush(QColor(couleur_fond)))
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
            items[13].setToolTip(score_label)

            self.style_pipeline(items[7], pipeline)

            for col_index, item in enumerate(items):
                self.setItem(row_index, col_index, item)

            self.setRowHeight(row_index, 34)

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
            self.prospect_double_clicked.emit(int(prospect_id))
