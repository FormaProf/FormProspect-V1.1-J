from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap


def initials(name: str) -> str:
    parts = [part for part in (name or '').split() if part]
    return ''.join(part[0] for part in parts[:2]).upper() or 'U'


def circular_avatar(photo_path: str | None, name: str, size: int, *, background: str = '#338CE4') -> QPixmap:
    canvas = QPixmap(size, size)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(path)

    source = QPixmap(str(photo_path)) if photo_path and Path(photo_path).is_file() else QPixmap()
    if not source.isNull():
        scaled = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (scaled.width() - size) // 2)
        y = max(0, (scaled.height() - size) // 2)
        painter.drawPixmap(0, 0, scaled.copy(x, y, size, size))
    else:
        painter.fillPath(path, QColor(background))
        painter.setPen(Qt.white)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(max(12, int(size * 0.34)))
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials(name))

    painter.setClipping(False)
    painter.setPen(QColor('#FFFFFF'))
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    painter.end()
    return canvas
