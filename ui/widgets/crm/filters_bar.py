from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton
from PySide6.QtCore import Signal


class CRMFiltersBar(QWidget):
    """Barre de recherche et de filtres CRM réutilisable.

    Cette classe ne connaît pas SQLite ni les services métier. Elle expose
    simplement les critères sélectionnés et émet un signal quand l'utilisateur
    modifie la recherche ou un filtre.
    """

    FILTER_ALL_VALUE = ""

    filters_changed = Signal()
    reset_requested = Signal()

    def __init__(self):
        super().__init__()
        self._updating = False

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.recherche_input = QLineEdit()
        self.recherche_input.setPlaceholderText(
            "🔍 Rechercher une entreprise, une ville, un téléphone, un email, un pipeline, une action, un commercial..."
        )
        self.recherche_input.setFixedHeight(42)
        self.recherche_input.setStyleSheet(self.style_input())
        self.recherche_input.textChanged.connect(self._emit_filters_changed)

        filtres_layout = QHBoxLayout()
        filtres_layout.setSpacing(10)

        self.pipeline_filtre = self.creer_combo_filtre("Pipeline")
        self.priorite_filtre = self.creer_combo_filtre("Priorité")
        self.commercial_filtre = self.creer_combo_filtre("Commercial")
        self.ville_filtre = self.creer_combo_filtre("Ville")

        for combo in [
            self.pipeline_filtre,
            self.priorite_filtre,
            self.commercial_filtre,
            self.ville_filtre,
        ]:
            combo.currentIndexChanged.connect(self._emit_filters_changed)

        self.bouton_reset = QPushButton("🧹 Effacer filtres")
        self.bouton_reset.setFixedHeight(38)
        self.bouton_reset.clicked.connect(self.effacer_filtres)
        self.bouton_reset.setStyleSheet(self.style_bouton_reset())

        filtres_layout.addWidget(self.pipeline_filtre)
        filtres_layout.addWidget(self.priorite_filtre)
        filtres_layout.addWidget(self.commercial_filtre)
        filtres_layout.addWidget(self.ville_filtre)
        filtres_layout.addWidget(self.bouton_reset)
        filtres_layout.addStretch()

        layout.addWidget(self.recherche_input)
        layout.addLayout(filtres_layout)
        self.setLayout(layout)

    def style_input(self):
        return """
            QLineEdit {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                padding-left: 14px;
                font-size: 14px;
                color: #111827;
            }
            QLineEdit:focus {
                border: 1px solid #338CE4;
            }
        """

    def style_combo_filtre(self):
        return """
            QComboBox {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 9px;
                padding-left: 10px;
                padding-right: 8px;
                font-size: 13px;
                color: #111827;
            }
            QComboBox:hover {
                border: 1px solid #CBD5E1;
            }
            QComboBox:focus {
                border: 1px solid #338CE4;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """

    def style_bouton_reset(self):
        return """
            QPushButton {
                background-color: #F3F4F6;
                color: #111827;
                border: 1px solid #E5E7EB;
                border-radius: 9px;
                font-size: 13px;
                font-weight: 700;
                padding-left: 14px;
                padding-right: 14px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
            QPushButton:pressed {
                background-color: #D1D5DB;
            }
        """

    def creer_combo_filtre(self, nom):
        combo = QComboBox()
        combo.setFixedHeight(38)
        combo.setMinimumWidth(150)
        combo.setStyleSheet(self.style_combo_filtre())
        combo.addItem(f"{nom} : Tous", self.FILTER_ALL_VALUE)
        return combo

    def _emit_filters_changed(self):
        if not self._updating:
            self.filters_changed.emit()

    def valeur_filtre(self, combo):
        valeur = combo.currentData()
        return "" if valeur is None else str(valeur).strip()

    def criteres(self):
        return {
            "recherche": self.recherche_input.text().strip(),
            "pipeline": self.valeur_filtre(self.pipeline_filtre),
            "priorite": self.valeur_filtre(self.priorite_filtre),
            "commercial": self.valeur_filtre(self.commercial_filtre),
            "ville": self.valeur_filtre(self.ville_filtre),
        }

    def filtres_actifs(self):
        return any(self.criteres().values())

    def remplir_combo(self, combo, libelle, valeurs):
        valeur_actuelle = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(f"{libelle} : Tous", self.FILTER_ALL_VALUE)

        for valeur in valeurs:
            if valeur is None:
                continue
            texte = str(valeur).strip()
            if texte:
                combo.addItem(texte, texte)

        index = combo.findData(valeur_actuelle)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentIndex(0)

        combo.blockSignals(False)

    def charger_options(self, options, pipelines_ordonnes=None, priorites_ordonnees=None):
        self._updating = True

        pipelines_source = options.get(
            "pipelines",
            options.get("pipeline", []),
        )
        priorites_source = options.get(
            "priorites",
            options.get("priorite", []),
        )
        commerciaux_source = options.get(
            "commerciaux",
            options.get("commercial", []),
        )
        villes_source = options.get(
            "villes",
            options.get("ville", []),
        )

        if pipelines_ordonnes:
            pipelines = [p for p in pipelines_ordonnes if p in pipelines_source]
            pipelines.extend([p for p in pipelines_source if p not in pipelines])
        else:
            pipelines = pipelines_source

        if priorites_ordonnees:
            priorites = [p for p in priorites_ordonnees if p in priorites_source]
            priorites.extend([p for p in priorites_source if p not in priorites])
        else:
            priorites = priorites_source

        self.remplir_combo(self.pipeline_filtre, "Pipeline", pipelines)
        self.remplir_combo(self.priorite_filtre, "Priorité", priorites)
        self.remplir_combo(
            self.commercial_filtre,
            "Commercial",
            commerciaux_source,
        )
        self.remplir_combo(
            self.ville_filtre,
            "Ville",
            villes_source,
        )

        self._updating = False

    def effacer_filtres(self):
        self._updating = True
        self.recherche_input.clear()
        self.pipeline_filtre.setCurrentIndex(0)
        self.priorite_filtre.setCurrentIndex(0)
        self.commercial_filtre.setCurrentIndex(0)
        self.ville_filtre.setCurrentIndex(0)
        self._updating = False
        self.reset_requested.emit()
        self.filters_changed.emit()
