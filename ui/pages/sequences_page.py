from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from core.application_state import ApplicationState
from core.premium_theme import BORDER, CARD, MUTED, NAVY, PAGE_BG, PRIMARY_BUTTON, SECONDARY_BUTTON, TEXT
from services.sequence_service import SequenceService
from ui.components.notifications import NotificationManager


class SequencesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.service = None
        self.current_sequence_id = None
        self.current_enrollment_id = None
        self.setStyleSheet(f"background:{PAGE_BG};")
        self._build_ui()

    def _card(self):
        frame = QFrame()
        frame.setStyleSheet(f"background:{CARD}; border:1px solid {BORDER}; border-radius:16px;")
        return frame

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 30)
        root.setSpacing(14)

        title = QLabel("Séquences commerciales")
        title.setStyleSheet(f"color:{TEXT}; font-size:30px; font-weight:900;")
        subtitle = QLabel("Organisez les e-mails, appels et relances dans un parcours commercial suivi étape par étape.")
        subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.empty = QLabel("Ouvrez un projet pour utiliser les séquences.")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(80)
        self.empty.setStyleSheet(f"background:white; color:{MUTED}; border:1px dashed {BORDER}; border-radius:14px;")
        root.addWidget(self.empty)

        self.content = QWidget()
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(12)

        self.kpis = {}
        grid = QGridLayout()
        for col, (key, label) in enumerate([
            ("sequences","Séquences"),("enrolled","Prospects inscrits"),("active","Actifs"),
            ("due_today","Actions dues"),("completed","Terminées")
        ]):
            card=self._card(); c=QVBoxLayout(card)
            cap=QLabel(label); cap.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:800;")
            val=QLabel("0"); val.setStyleSheet(f"color:{NAVY}; font-size:25px; font-weight:900;")
            c.addWidget(cap); c.addWidget(val); grid.addWidget(card,0,col); self.kpis[key]=val
        layout.addLayout(grid)

        split=QSplitter(Qt.Horizontal)
        left=self._card(); left_l=QVBoxLayout(left)
        self.name=QLineEdit(); self.name.setPlaceholderText("Nom de la séquence")
        self.description=QTextEdit(); self.description.setPlaceholderText("Objectif et contexte"); self.description.setMaximumHeight(90)
        create=QPushButton("Créer la séquence"); create.setStyleSheet(PRIMARY_BUTTON); create.clicked.connect(self.create_sequence)
        left_l.addWidget(QLabel("Nouvelle séquence")); left_l.addWidget(self.name); left_l.addWidget(self.description); left_l.addWidget(create)

        self.sequence_table=QTableWidget(0,5)
        self.sequence_table.setHorizontalHeaderLabels(["Nom","Statut","Étapes","Inscrits","Actifs"])
        self.sequence_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sequence_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sequence_table.itemSelectionChanged.connect(self.select_sequence)
        self.sequence_table.horizontalHeader().setStretchLastSection(True)
        left_l.addWidget(self.sequence_table,1)

        step_grid=QGridLayout()
        self.day=QSpinBox(); self.day.setRange(0,365); self.day.setPrefix("J+")
        self.step_type=QComboBox(); self.step_type.addItems(SequenceService.STEP_TYPES)
        self.step_title=QLineEdit(); self.step_title.setPlaceholderText("Titre de l'étape")
        self.instructions=QLineEdit(); self.instructions.setPlaceholderText("Consigne")
        add=QPushButton("Ajouter l'étape"); add.setStyleSheet(SECONDARY_BUTTON); add.clicked.connect(self.add_step)
        step_grid.addWidget(self.day,0,0); step_grid.addWidget(self.step_type,0,1)
        step_grid.addWidget(self.step_title,1,0,1,2); step_grid.addWidget(self.instructions,2,0,1,2); step_grid.addWidget(add,3,0,1,2)
        left_l.addLayout(step_grid)
        split.addWidget(left)

        right=self._card(); right_l=QVBoxLayout(right)
        self.steps_table=QTableWidget(0,4)
        self.steps_table.setHorizontalHeaderLabels(["Ordre","Jour","Type","Étape"])
        self.steps_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.steps_table.horizontalHeader().setStretchLastSection(True)

        actions=QHBoxLayout()
        activate=QPushButton("Activer"); activate.setStyleSheet(SECONDARY_BUTTON); activate.clicked.connect(self.activate)
        enroll=QPushButton("Inscrire les prospects éligibles"); enroll.setStyleSheet(PRIMARY_BUTTON); enroll.clicked.connect(self.enroll)
        self.min_score=QSpinBox(); self.min_score.setRange(0,100); self.min_score.setValue(45); self.min_score.setSuffix(" score min.")
        actions.addWidget(activate); actions.addWidget(self.min_score); actions.addWidget(enroll); actions.addStretch()

        self.enrollments_table=QTableWidget(0,7)
        self.enrollments_table.setHorizontalHeaderLabels(["Entreprise","Score","Étape","Type","Échéance","Statut","Contact"])
        self.enrollments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.enrollments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.enrollments_table.itemSelectionChanged.connect(self.select_enrollment)
        self.enrollments_table.horizontalHeader().setStretchLastSection(True)

        done=QPushButton("Marquer l'étape comme terminée"); done.setStyleSheet(PRIMARY_BUTTON); done.clicked.connect(self.complete_step)
        right_l.addWidget(QLabel("Étapes de la séquence")); right_l.addWidget(self.steps_table)
        right_l.addLayout(actions)
        right_l.addWidget(QLabel("Progression des prospects")); right_l.addWidget(self.enrollments_table,1); right_l.addWidget(done)
        split.addWidget(right); split.setSizes([470,750])
        layout.addWidget(split,1)
        root.addWidget(self.content,1)
        self.content.setVisible(False)

    def rafraichir(self):
        if not ApplicationState.has_project():
            self.service=None; self.empty.setVisible(True); self.content.setVisible(False); return
        self.service=SequenceService(ApplicationState.get_project().database)
        self.empty.setVisible(False); self.content.setVisible(True)
        self.load_sequences(); self.load_stats()

    def load_stats(self):
        if not self.service: return
        stats=self.service.stats()
        for key,label in self.kpis.items(): label.setText(str(getattr(stats,key)))

    def load_sequences(self):
        rows=self.service.sequences() if self.service else []
        self.sequence_table.setRowCount(len(rows))
        for r,s in enumerate(rows):
            vals=[s["name"],s["status"],str(s["step_count"] or 0),str(s["enrollment_count"] or 0),str(s["active_count"] or 0)]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(v)
                if c==0: item.setData(Qt.UserRole,int(s["id"]))
                self.sequence_table.setItem(r,c,item)

    def create_sequence(self):
        try:
            sid=self.service.create_sequence(self.name.text(),self.description.toPlainText())
        except ValueError as exc:
            NotificationManager.warning("Séquence incomplète",str(exc)); return
        self.current_sequence_id=sid; self.name.clear(); self.description.clear()
        NotificationManager.success("Séquence créée","Ajoutez maintenant les étapes.")
        self.load_sequences(); self.load_stats()

    def select_sequence(self):
        items=self.sequence_table.selectedItems()
        if not items:return
        self.current_sequence_id=int(self.sequence_table.item(items[0].row(),0).data(Qt.UserRole))
        self.load_steps(); self.load_enrollments()

    def add_step(self):
        if self.current_sequence_id is None:
            NotificationManager.warning("Séquence requise","Sélectionnez une séquence."); return
        try:
            self.service.add_step(self.current_sequence_id,self.day.value(),self.step_type.currentText(),self.step_title.text(),self.instructions.text())
        except ValueError as exc:
            NotificationManager.warning("Étape incomplète",str(exc)); return
        self.step_title.clear(); self.instructions.clear(); self.load_steps(); self.load_sequences()

    def load_steps(self):
        rows=self.service.steps(self.current_sequence_id)
        self.steps_table.setRowCount(len(rows))
        for r,s in enumerate(rows):
            vals=[str(s["step_order"]),f"J+{s['day_offset']}",s["step_type"],s["title"]]
            for c,v in enumerate(vals): self.steps_table.setItem(r,c,QTableWidgetItem(v))

    def activate(self):
        if self.current_sequence_id is None:return
        try:self.service.activate(self.current_sequence_id)
        except ValueError as exc: NotificationManager.warning("Activation impossible",str(exc)); return
        NotificationManager.success("Séquence activée","Elle est prête à recevoir des prospects."); self.load_sequences()

    def enroll(self):
        if self.current_sequence_id is None:
            NotificationManager.warning("Séquence requise","Sélectionnez une séquence."); return
        try: added=self.service.enroll_eligible_prospects(self.current_sequence_id,self.min_score.value())
        except ValueError as exc: NotificationManager.warning("Inscription impossible",str(exc)); return
        NotificationManager.success("Prospects inscrits",f"{added} nouveau(x) prospect(s) ajouté(s).")
        self.load_enrollments(); self.load_sequences(); self.load_stats()

    def load_enrollments(self):
        rows=self.service.enrollments(self.current_sequence_id)
        self.enrollments_table.setRowCount(len(rows))
        for r,e in enumerate(rows):
            contact=e["telephone"] or e["email"] or "—"
            vals=[e["entreprise"],str(e["score_prospect"] or 0),e["current_title"] or "Terminée",e["step_type"] or "—",e["next_action_at"] or "—",e["status"],contact]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(str(v))
                if c==0:item.setData(Qt.UserRole,int(e["id"]))
                self.enrollments_table.setItem(r,c,item)

    def select_enrollment(self):
        items=self.enrollments_table.selectedItems()
        if items:self.current_enrollment_id=int(self.enrollments_table.item(items[0].row(),0).data(Qt.UserRole))

    def complete_step(self):
        if self.current_enrollment_id is None:
            NotificationManager.warning("Prospect requis","Sélectionnez un prospect inscrit."); return
        try:self.service.complete_current_step(self.current_enrollment_id)
        except ValueError as exc: NotificationManager.warning("Action impossible",str(exc)); return
        NotificationManager.success("Étape terminée","La prochaine action a été programmée.")
        self.load_enrollments(); self.load_stats()
