from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QEvent

from core.crm import PIPELINE_COLORS
from ui.widgets.crm.kanban_card import KanbanCard
from ui.crm_premium_theme import (
    CRM_THEME_CLASSIC,
    CRM_THEME_DARK,
    crm_palette,
    normalize_crm_theme,
)


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
        self._current_theme = CRM_THEME_CLASSIC

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
        if self._current_theme == CRM_THEME_CLASSIC:
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

        p = crm_palette(self._current_theme)
        dark = self._current_theme == CRM_THEME_DARK
        background = "#081827" if dark else "#F4FAFF"
        border = p["cyan"] if highlight else p["border"]
        width = 2 if highlight else 1
        return f"""
            QFrame#KanbanColumn {{
                background:{background};
                border:{width}px solid {border};
                border-radius:18px;
            }}
            QLabel {{
                background:transparent;
            }}
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
        card.apply_theme(self._current_theme)
        card.double_clicked.connect(
            self.card_double_clicked.emit
        )
        self.cards_layout.insertWidget(
            self.cards_layout.count() - 1,
            card,
        )
        self.cards_count += 1
        self._update_header()

    def apply_theme(self, theme=None):
        self._current_theme = normalize_crm_theme(theme)
        self.setStyleSheet(self._style_column(highlight=self._highlighted))
        self._update_header()

        p = crm_palette(self._current_theme)
        if self._current_theme == CRM_THEME_CLASSIC:
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
        else:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background:transparent;
                    border:none;
                }}
                QScrollBar:vertical {{
                    background:transparent;
                    width:5px;
                    margin:2px 0 2px 0;
                }}
                QScrollBar::handle:vertical {{
                    background:{p['border_strong']};
                    min-height:30px;
                    border-radius:2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background:{p['primary']};
                }}
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {{
                    height:0;
                }}
            """)

        for index in range(self.cards_layout.count() - 1):
            widget = self.cards_layout.itemAt(index).widget()
            if widget is not None and hasattr(widget, "apply_theme"):
                widget.apply_theme(self._current_theme)

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

    def _pipeline_accent(self):
        name = str(self.pipeline_name or "").casefold()
        if "perdu" in name:
            return "#F87171"
        if "client" in name:
            return "#5EE6A8"
        if "négoci" in name or "negoci" in name:
            return "#F7B955"
        if "proposition" in name:
            return "#A78BFA"
        if "rdv" in name:
            return "#F38CC6"
        if "lead chaud" in name:
            return "#FF8B5B"
        if "contacté" in name or "contacte" in name:
            return "#4DA3FF"
        if "contacter" in name or "qualification" in name:
            return "#F6D44A"
        if "nouveau" in name:
            return "#338CE4"
        return "#6AAEF5"

    def _update_header(self):
        if "nouveau" in str(self.pipeline_name).lower():
            couleur = "#338CE4"
        else:
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

        if self._current_theme == CRM_THEME_CLASSIC:
            self.header.setStyleSheet(
                "font-size:12px; font-weight:900; color:#172033; "
                "background:transparent; border:none;"
            )
            self.count_badge.setStyleSheet(
                "font-size:11px; font-weight:900; color:#23344D; "
                "background:#FFFFFF; border:1px solid #DCE5EF; border-radius:10px;"
            )
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
            return

        p = crm_palette(self._current_theme)
        dark = self._current_theme == CRM_THEME_DARK
        accent = self._pipeline_accent()
        header_bg = "#0C2338" if dark else "#FFFFFF"
        self.header.setStyleSheet(
            f"font-size:12px; font-weight:950; color:{p['text']}; "
            "background:transparent; border:none;"
        )
        self.count_badge.setStyleSheet(
            f"font-size:11px; font-weight:950; color:{accent}; "
            f"background:{p['surface_soft']}; border:1px solid {p['border_strong']}; "
            "border-radius:10px;"
        )
        self.header_frame.setStyleSheet(
            f"""
            QFrame#KanbanHeader {{
                background:{header_bg};
                border:1px solid {p['border']};
                border-top:3px solid {accent};
                border-radius:13px;
            }}
            QLabel {{
                background:transparent;
            }}
            """
        )
