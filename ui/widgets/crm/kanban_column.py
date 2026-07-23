from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PySide6.QtCore import Qt, Signal, QEvent

from core.crm import PIPELINE_COLORS
from ui.widgets.crm.kanban_card import KanbanCard


class KanbanColumn(QFrame):
    """Colonne Kanban correspondant à une étape du pipeline.

    Cette version accepte le dépôt sur toute la colonne : le cadre principal,
    la zone de scroll, le viewport et le conteneur interne des cartes. Cela
    évite le symbole interdit lorsque la souris passe au-dessus des zones
    vides ou grisées de la colonne.
    """

    card_double_clicked = Signal(object)
    card_dropped = Signal(object, str)
    card_drag_moved = Signal(object)

    def __init__(self, pipeline_name):
        super().__init__()
        self.pipeline_name = pipeline_name
        self.cards_count = 0
        self._highlighted = False

        self.setObjectName("KanbanColumn")
        self.setAcceptDrops(True)
        self.setMinimumWidth(285)
        self.setMaximumWidth(320)
        self.setStyleSheet(self._style_column())

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.header = QLabel()
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 14px;
                font-weight: 900;
                padding: 8px;
                border-radius: 10px;
                background-color: white;
            }
        """)

        self.cards_container = QWidget()
        self.cards_container.setAcceptDrops(True)
        self.cards_container.installEventFilter(self)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        self.cards_container.setLayout(self.cards_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setAcceptDrops(True)
        self.scroll_area.installEventFilter(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.cards_container)
        self.scroll_area.viewport().setAcceptDrops(True)
        self.scroll_area.viewport().installEventFilter(self)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #F3F4F6;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 28px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
        """)

        root_layout.addWidget(self.header)
        root_layout.addWidget(self.scroll_area, 1)
        self.setLayout(root_layout)
        self._update_header()

    def _style_column(self, highlight=False):
        if highlight:
            return """
                QFrame#KanbanColumn {
                    background-color: #EFF6FF;
                    border: 2px solid #338CE4;
                    border-radius: 14px;
                }
                QLabel {
                    background: transparent;
                }
            """

        return """
            QFrame#KanbanColumn {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
            }
        """

    def _set_highlight(self, enabled):
        if self._highlighted == enabled:
            return

        self._highlighted = enabled
        self.setStyleSheet(self._style_column(highlight=enabled))

    def clear_cards(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards_count = 0
        self._update_header()

    def add_card(self, prospect):
        card = KanbanCard(prospect)
        card.double_clicked.connect(self.card_double_clicked.emit)
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.cards_count += 1
        self._update_header()

    def _has_card_mime(self, event):
        return event.mimeData().hasFormat(KanbanCard.MIME_TYPE)

    def _global_position(self, event, source_widget):
        """Retourne une position globale compatible PySide6/Qt6 et Qt5."""
        try:
            local_pos = event.position().toPoint()
        except AttributeError:
            local_pos = event.pos()

        return source_widget.mapToGlobal(local_pos)

    def _emit_drag_position(self, event, source_widget):
        self.card_drag_moved.emit(self._global_position(event, source_widget))

    def _handle_drag_enter(self, event, source_widget):
        if self._has_card_mime(event):
            self._emit_drag_position(event, source_widget)
            event.acceptProposedAction()
            self._set_highlight(True)
            return True

        event.ignore()
        return True

    def _handle_drag_move(self, event, source_widget):
        if self._has_card_mime(event):
            self._emit_drag_position(event, source_widget)
            event.acceptProposedAction()
            self._set_highlight(True)
            return True

        event.ignore()
        return True

    def _handle_drag_leave(self, event):
        self._set_highlight(False)
        event.accept()
        return True

    def _handle_drop(self, event):
        self._set_highlight(False)

        if not self._has_card_mime(event):
            event.ignore()
            return True

        try:
            raw_id = bytes(event.mimeData().data(KanbanCard.MIME_TYPE)).decode("utf-8")
            prospect_id = int(raw_id)
        except (TypeError, ValueError):
            event.ignore()
            return True

        self.card_dropped.emit(prospect_id, self.pipeline_name)
        event.acceptProposedAction()
        return True

    def eventFilter(self, watched, event):
        event_type = event.type()

        if event_type == QEvent.DragEnter:
            return self._handle_drag_enter(event, watched)

        if event_type == QEvent.DragMove:
            return self._handle_drag_move(event, watched)

        if event_type == QEvent.DragLeave:
            return self._handle_drag_leave(event)

        if event_type == QEvent.Drop:
            return self._handle_drop(event)

        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        self._handle_drag_enter(event, self)

    def dragMoveEvent(self, event):
        self._handle_drag_move(event, self)

    def dragLeaveEvent(self, event):
        self._handle_drag_leave(event)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._handle_drop(event)

    def _update_header(self):
        couleur = PIPELINE_COLORS.get(self.pipeline_name, "#FFFFFF")
        self.header.setText(f"{self.pipeline_name}  ·  {self.cards_count}")
        self.header.setStyleSheet(f"""
            QLabel {{
                color: #111827;
                font-size: 14px;
                font-weight: 900;
                padding: 8px;
                border-radius: 10px;
                background-color: {couleur};
            }}
        """)
