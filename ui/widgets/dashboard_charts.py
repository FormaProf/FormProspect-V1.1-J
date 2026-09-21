from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui.dashboard_premium_theme import dashboard_palette


class QualityDonut(QWidget):
    """Anneau léger et theme-aware pour le score de qualité."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._palette = dashboard_palette()
        self.setMinimumSize(140, 140)
        self.setMaximumHeight(190)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def apply_theme(self, mode=None):
        self._palette = dashboard_palette(mode)
        self.update()

    def set_value(self, value: int):
        self._value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 30
        rect = QRectF(
            (self.width() - side) / 2,
            (self.height() - side) / 2,
            side,
            side,
        )

        pen = QPen(
            QColor(self._palette["track"]),
            13,
            Qt.SolidLine,
            Qt.RoundCap,
        )
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        pen.setColor(QColor(self._palette["primary"]))
        painter.setPen(pen)
        painter.drawArc(
            rect,
            90 * 16,
            -self._value * 360 * 16 // 100,
        )

        painter.setPen(QColor(self._palette["text"]))
        font = QFont("Segoe UI", 21)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self._value} %")


class HorizontalBarChart(QWidget):
    """Graphique horizontal compact sans dépendance externe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, int]] = []
        self._palette = dashboard_palette()
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def apply_theme(self, mode=None):
        self._palette = dashboard_palette(mode)
        self.update()

    def set_items(self, items):
        self._items = [
            (str(label), max(0, int(value)))
            for label, value in items
        ]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self._items:
            painter.setPen(QColor(self._palette["muted_light"]))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Aucune donnée",
            )
            return

        left = 88
        right = 48
        top = 10
        row_height = max(
            25,
            (self.height() - top * 2) // len(self._items),
        )
        max_value = max(value for _, value in self._items) or 1
        available = max(40, self.width() - left - right)

        label_font = QFont("Segoe UI", 9)
        value_font = QFont("Segoe UI", 9)
        value_font.setBold(True)

        for index, (label, value) in enumerate(self._items):
            y = top + index * row_height

            painter.setFont(label_font)
            painter.setPen(QColor(self._palette["muted"]))
            painter.drawText(
                QRectF(0, y, left - 8, row_height),
                Qt.AlignVCenter | Qt.AlignRight,
                label,
            )

            bar_y = y + row_height * 0.31
            bar_h = row_height * 0.38

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(self._palette["track"]))
            painter.drawRoundedRect(
                QRectF(left, bar_y, available, bar_h),
                5,
                5,
            )

            width = available * value / max_value
            painter.setBrush(QColor(self._palette["primary"]))
            painter.drawRoundedRect(
                QRectF(left, bar_y, width, bar_h),
                5,
                5,
            )

            painter.setFont(value_font)
            painter.setPen(QColor(self._palette["text"]))
            painter.drawText(
                QRectF(
                    left + available + 7,
                    y,
                    right - 7,
                    row_height,
                ),
                Qt.AlignVCenter | Qt.AlignLeft,
                f"{value:,}".replace(",", " "),
            )
