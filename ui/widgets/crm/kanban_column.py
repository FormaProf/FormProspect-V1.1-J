from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QEvent

from core.crm import PIPELINE_COLORS
from ui.widgets.crm.kanban_card import KanbanCard


class KanbanColumn(QFrame):
    """Colonne Kanban correspondant à une étape du pipeline."""

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
        self.setMinimumWidth(292)
        self.setMaximumWidth(326)
        self.setStyleSheet(self._style_column())

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("KanbanHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(12, 10, 10, 10)
        header_layout.setSpacing(8)

        self.header = QLabel()
        self.header.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.header.setStyleSheet(
            "font-size:12px; font-weight:900; color:#172033; "
            "background:transparent; border:none;"
        )

        self.count_badge = QLabel("0")
        self.count_badge.setFixedSize(30, 24)
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setStyleSheet(
            "font-size:11px; font-weight:900; color:#23344D; "
            "background:#FFFFFF; border:1px solid #DCE5EF; border-radius:10px;"
        )

        header_layout.addWidget(self.header, 1)
        header_layout.addWidget(self.count_badge)

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
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 3px 1px 3px 1px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            """
        )

        root_layout.addWidget(self.header_frame)
        root_layout.addWidget(self.scroll_area, 1)
        self.setLayout(root_layout)
        self._update_header()

    def _style_column(self, highlight=False):
        if highlight:
            return """
                QFrame#KanbanColumn {
                    background-color: #F7FBFF;
                    border: 2px solid #338CE4;
                    border-radius: 18px;
                }
                QLabel {
                    background: transparent;
                }
            """

        return """
            QFrame#KanbanColumn {
                background-color: #FBFCFE;
                border: 1px solid #E3EAF2;
                border-radius: 18px;
            }
            QLabel {
                background: transparent;
            }
        """

    def _set_highlight(self, enabled):
        if self._highlighted == enabled:
            return

        self._highlighted = enabled
        self.setStyleSheet(
            self._style_column(highlight=enabled)
        )

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
        card.double_clicked.connect(
            self.card_double_clicked.emit
        )
        self.cards_layout.insertWidget(
            self.cards_layout.count() - 1,
            card,
        )
        self.cards_count += 1
        self._update_header()

    def _has_card_mime(self, event):
        return event.mimeData().hasFormat(
            KanbanCard.MIME_TYPE
        )

    def _global_position(self, event, source_widget):
        """Retourne une position globale compatible PySide6/Qt6 et Qt5."""
        try:
            local_pos = event.position().toPoint()
        except AttributeError:
            local_pos = event.pos()

        return source_widget.mapToGlobal(local_pos)

    def _emit_drag_position(self, event, source_widget):
        self.card_drag_moved.emit(
            self._global_position(event, source_widget)
        )

    def _handle_drag_enter(self, event, source_widget):
        if self._has_card_mime(event):
            self._emit_drag_position(
                event,
                source_widget,
            )
            event.acceptProposedAction()
            self._set_highlight(True)
            return True

        event.ignore()
        return True

    def _handle_drag_move(self, event, source_widget):
        if self._has_card_mime(event):
            self._emit_drag_position(
                event,
                source_widget,
            )
            event.acceptProposedAction()
            self._set_highlight(True)
            return True

        event.ignore()
        return True

    def _handle_drag_leave(self, event):
        self._set_highlight(False)
        event.accept()
        return True

    @staticmethod
    def _restore_identifier(raw_id):
        """Restaure un ID local numérique ou conserve un UUID Cloud."""
        normalized = str(raw_id).strip()

        if normalized.isdigit():
            return int(normalized)

        return normalized

    def _handle_drop(self, event):
        self._set_highlight(False)

        if not self._has_card_mime(event):
            event.ignore()
            return True

        try:
            raw_id = bytes(
                event.mimeData().data(KanbanCard.MIME_TYPE)
            ).decode("utf-8")
            prospect_id = self._restore_identifier(raw_id)
        except (TypeError, ValueError, UnicodeDecodeError):
            event.ignore()
            return True

        if prospect_id in (None, ""):
            event.ignore()
            return True

        self.card_dropped.emit(
            prospect_id,
            self.pipeline_name,
        )
        event.acceptProposedAction()
        return True

    def eventFilter(self, watched, event):
        event_type = event.type()

        if event_type == QEvent.DragEnter:
            return self._handle_drag_enter(
                event,
                watched,
            )

        if event_type == QEvent.DragMove:
            return self._handle_drag_move(
                event,
                watched,
            )

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
        couleur = PIPELINE_COLORS.get(
            self.pipeline_name,
            "#F8FAFC",
        )

        labels = {
            "🟢 Nouveau": "NOUVEAU",
            "🟡 Qualification": "QUALIFICATION",
            "🔵 RDV programmé": "RDV PROGRAMMÉ",
            "🟣 Proposition envoyée": "PROPOSITION",
            "🟠 Négociation": "NÉGOCIATION",
            "🟢 Client": "CLIENT",
            "🔴 Perdu": "PERDU",
        }
        title = labels.get(self.pipeline_name, str(self.pipeline_name).strip())

        self.header.setText(title)
        self.count_badge.setText(str(self.cards_count))
        self.header_frame.setStyleSheet(
            f"""
            QFrame#KanbanHeader {{
                background-color: {couleur};
                border: 1px solid #E3EAF2;
                border-radius: 13px;
            }}
            QLabel {{
                background: transparent;
            }}
            """
        )
