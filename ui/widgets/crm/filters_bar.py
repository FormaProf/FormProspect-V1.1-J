from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton
from PySide6.QtCore import Signal

from ui.crm_premium_theme import (
    CRM_THEME_CLASSIC,
    crm_palette,
    normalize_crm_theme,
)


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

        self.project_filtre = self.creer_combo_filtre("Projet")
        self.pipeline_filtre = self.creer_combo_filtre("Pipeline")
        self.priorite_filtre = self.creer_combo_filtre("Priorité")
        self.commercial_filtre = self.creer_combo_filtre("Commercial")
        self.ville_filtre = self.creer_combo_filtre("Ville")

        for combo in [
            self.project_filtre,
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

        filtres_layout.addWidget(self.project_filtre)
        filtres_layout.addWidget(self.pipeline_filtre)
        filtres_layout.addWidget(self.priorite_filtre)
        filtres_layout.addWidget(self.commercial_filtre)
        filtres_layout.addWidget(self.ville_filtre)
        filtres_layout.addWidget(self.bouton_reset)
        filtres_layout.addStretch()

        layout.addWidget(self.recherche_input)
        layout.addLayout(filtres_layout)
        self.setLayout(layout)
        self._current_theme = CRM_THEME_CLASSIC

    def apply_theme(self, theme=None):
        theme = normalize_crm_theme(theme)
        self._current_theme = theme

        if theme == CRM_THEME_CLASSIC:
            self.recherche_input.setStyleSheet(self.style_input())
            for combo in (
                self.project_filtre,
                self.pipeline_filtre,
                self.priorite_filtre,
                self.commercial_filtre,
                self.ville_filtre,
            ):
                combo.setStyleSheet(self.style_combo_filtre())
            self.bouton_reset.setStyleSheet(self.style_bouton_reset())
            return

        p = crm_palette(theme)
        self.recherche_input.setStyleSheet(f"""
            QLineEdit {{
                background:{p['surface_alt']};
                color:{p['text']};
                border:1px solid {p['border']};
                border-radius:12px;
                padding-left:14px;
                padding-right:12px;
                font-size:13px;
                font-weight:650;
                selection-background-color:{p['primary']};
                selection-color:#FFFFFF;
            }}
            QLineEdit:hover {{
                border:1px solid {p['border_strong']};
            }}
            QLineEdit:focus {{
                border:1px solid {p['cyan']};
                background:{p['surface']};
            }}
        """)

        combo_style = f"""
            QComboBox {{
                background:{p['surface_alt']};
                color:{p['text_soft']};
                border:1px solid {p['border']};
                border-radius:11px;
                padding-left:11px;
                padding-right:9px;
                font-size:12px;
                font-weight:750;
            }}
            QComboBox:hover {{
                border:1px solid {p['border_strong']};
                color:{p['text']};
            }}
            QComboBox:focus {{
                border:1px solid {p['cyan']};
            }}
            QComboBox::drop-down {{
                border:none;
                width:25px;
            }}
            QComboBox QAbstractItemView {{
                background:{p['surface']};
                color:{p['text']};
                border:1px solid {p['border']};
                outline:0;
                selection-background-color:{p['surface_soft']};
                selection-color:{p['text']};
                padding:5px;
            }}
        """
        for combo in (
            self.project_filtre,
            self.pipeline_filtre,
            self.priorite_filtre,
            self.commercial_filtre,
            self.ville_filtre,
        ):
            combo.setStyleSheet(combo_style)

        self.bouton_reset.setStyleSheet(f"""
            QPushButton {{
                background:{p['surface_soft']};
                color:{p['muted']};
                border:1px solid {p['border']};
                border-radius:11px;
                font-size:12px;
                font-weight:850;
                padding-left:14px;
                padding-right:14px;
            }}
            QPushButton:hover {{
                background:{p['surface_alt']};
                color:{p['cyan']};
                border:1px solid {p['primary']};
            }}
        """)

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

    def remplir_projets(
        self,
        projets,
    ):
        valeur_actuelle = self.project_filtre.currentData()
        self.project_filtre.blockSignals(True)
        self.project_filtre.clear()
        self.project_filtre.addItem("Projet : Tous", self.FILTER_ALL_VALUE)

        for projet in projets or []:
            if not isinstance(projet, dict):
                continue
            project_id = str(projet.get("id") or "").strip()
            project_name = str(projet.get("name") or "").strip()
            if project_id and project_name:
                self.project_filtre.addItem(project_name, project_id)

        index = self.project_filtre.findData(valeur_actuelle)
        self.project_filtre.setCurrentIndex(index if index >= 0 else 0)
        self.project_filtre.blockSignals(False)

    def project_id_selectionne(self):
        return self.valeur_filtre(self.project_filtre)


    def selectionner_project_id(self, project_id):
        valeur = str(project_id or "").strip()
        index = self.project_filtre.findData(valeur)
        if index < 0:
            index = 0

        signals_bloques = self.project_filtre.blockSignals(True)
        self.project_filtre.setCurrentIndex(index)
        self.project_filtre.blockSignals(signals_bloques)

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

        self.remplir_projets(options.get("projects", []))
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
        self.project_filtre.setCurrentIndex(0)
        self.pipeline_filtre.setCurrentIndex(0)
        self.priorite_filtre.setCurrentIndex(0)
        self.commercial_filtre.setCurrentIndex(0)
        self.ville_filtre.setCurrentIndex(0)
        self._updating = False
        self.reset_requested.emit()
        self.filters_changed.emit()
