from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame
from PySide6.QtCore import Qt, Signal, QTimer

from core.crm import PIPELINE, PIPELINE_DEFAULT
from ui.widgets.crm.kanban_column import KanbanColumn


class KanbanView(QWidget):
    """Vue Kanban CRM basée sur le pipeline commercial."""

    prospect_double_clicked = Signal(object)
    pipeline_change_requested = Signal(object, str)

    AUTO_SCROLL_MARGIN = 90
    AUTO_SCROLL_STEP = 24
    AUTO_SCROLL_INTERVAL_MS = 35

    def __init__(self):
        super().__init__()
        self.columns = {}
        self._auto_scroll_direction = 0

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        self.info_label = QLabel("Vue Kanban — affichage des prospects chargés avec les filtres actifs")
        self.info_label.setStyleSheet("font-size: 13px; color: #6B7280; font-weight: 600;")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                background: #F3F4F6;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1;
                min-width: 40px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94A3B8;
            }
        """)

        self.content = QWidget()
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(14)
        self.content.setLayout(self.columns_layout)
        self.scroll_area.setWidget(self.content)

        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.setInterval(self.AUTO_SCROLL_INTERVAL_MS)
        self.auto_scroll_timer.timeout.connect(self._auto_scroll_kanban)

        root_layout.addWidget(self.info_label)
        root_layout.addWidget(self.scroll_area, 1)
        self.setLayout(root_layout)

        self._build_columns()

    def _connect_column(self, column):
        column.card_double_clicked.connect(self.prospect_double_clicked.emit)
        column.card_dropped.connect(self._handle_card_dropped)
        column.card_drag_moved.connect(self._handle_drag_position)

    def _build_columns(self):
        for pipeline in PIPELINE:
            column = KanbanColumn(pipeline)
            self._connect_column(column)
            self.columns[pipeline] = column
            self.columns_layout.addWidget(column)
        self.columns_layout.addStretch()

    def afficher_lignes(self, prospects):
        self._stop_auto_scroll()

        for column in self.columns.values():
            column.clear_cards()

        for prospect in prospects:
            pipeline = prospect[7] if len(prospect) > 7 and prospect[7] else PIPELINE_DEFAULT
            column = self.columns.get(pipeline)

            if column is None:
                column = KanbanColumn(pipeline)
                self._connect_column(column)
                self.columns[pipeline] = column
                self.columns_layout.insertWidget(self.columns_layout.count() - 1, column)

            column.add_card(prospect)

        self.info_label.setText(f"Vue Kanban — {len(prospects)} prospect(s) affiché(s) avec les filtres actifs")

    def _handle_card_dropped(self, prospect_id, pipeline_name):
        self._stop_auto_scroll()
        self.pipeline_change_requested.emit(prospect_id, pipeline_name)

    def _handle_drag_position(self, global_position):
        viewport = self.scroll_area.viewport()
        local_position = viewport.mapFromGlobal(global_position)
        viewport_width = viewport.width()

        if local_position.x() < self.AUTO_SCROLL_MARGIN:
            self._set_auto_scroll_direction(-1)
        elif local_position.x() > viewport_width - self.AUTO_SCROLL_MARGIN:
            self._set_auto_scroll_direction(1)
        else:
            self._stop_auto_scroll()

    def _set_auto_scroll_direction(self, direction):
        self._auto_scroll_direction = direction

        if not self.auto_scroll_timer.isActive():
            self.auto_scroll_timer.start()

    def _stop_auto_scroll(self):
        self._auto_scroll_direction = 0

        if self.auto_scroll_timer.isActive():
            self.auto_scroll_timer.stop()

    def _auto_scroll_kanban(self):
        if self._auto_scroll_direction == 0:
            self._stop_auto_scroll()
            return

        scrollbar = self.scroll_area.horizontalScrollBar()
        current_value = scrollbar.value()
        next_value = current_value + (self.AUTO_SCROLL_STEP * self._auto_scroll_direction)
        next_value = max(scrollbar.minimum(), min(scrollbar.maximum(), next_value))

        scrollbar.setValue(next_value)

        if next_value == current_value:
            self._stop_auto_scroll()
