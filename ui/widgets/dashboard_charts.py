from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.constants import PRIMARY_COLOR


class QualityDonut(QWidget):
    """Anneau léger sans dépendance externe pour le score de qualité."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setMinimumSize(180, 180)
        self.setMaximumHeight(230)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_value(self, value: int):
        self._value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 34
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        pen = QPen(QColor("#E5E7EB"), 16, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        pen.setColor(QColor(PRIMARY_COLOR))
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -self._value * 360 * 16 // 100)

        painter.setPen(QColor("#111827"))
        font = QFont("Segoe UI", 25)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self._value} %")


class HorizontalBarChart(QWidget):
    """Graphique à barres horizontal compact pour les données de contact."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, int]] = []
        self.setMinimumHeight(235)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_items(self, items):
        self._items = [(str(label), max(0, int(value))) for label, value in items]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self._items:
            painter.setPen(QColor("#9CA3AF"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Aucune donnée")
            return

        left = 98
        right = 55
        top = 18
        row_height = max(30, (self.height() - top * 2) // len(self._items))
        max_value = max(value for _, value in self._items) or 1
        available = max(40, self.width() - left - right)

        label_font = QFont("Segoe UI", 10)
        value_font = QFont("Segoe UI", 10)
        value_font.setBold(True)

        for index, (label, value) in enumerate(self._items):
            y = top + index * row_height
            painter.setFont(label_font)
            painter.setPen(QColor("#4B5563"))
            painter.drawText(QRectF(0, y, left - 10, row_height), Qt.AlignVCenter | Qt.AlignRight, label)

            bar_y = y + row_height * 0.27
            bar_h = row_height * 0.46
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#EEF2F7"))
            painter.drawRoundedRect(QRectF(left, bar_y, available, bar_h), 6, 6)

            width = available * value / max_value
            painter.setBrush(QColor(PRIMARY_COLOR))
            painter.drawRoundedRect(QRectF(left, bar_y, width, bar_h), 6, 6)

            painter.setFont(value_font)
            painter.setPen(QColor("#111827"))
            painter.drawText(
                QRectF(left + available + 8, y, right - 8, row_height),
                Qt.AlignVCenter | Qt.AlignLeft,
                f"{value:,}".replace(",", " "),
            )
