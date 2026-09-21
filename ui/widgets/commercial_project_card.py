from __future__ import annotations

import math
import unicodedata

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QSizePolicy

from ui.commercial_projects_theme import projects_palette, projects_theme_mode


_VISUAL_THEME_LABELS = {
    "btp": "BTP • CHANTIER",
    "cyber": "CYBER • SÉCURITÉ",
    "excel": "DATA • PILOTAGE",
    "ai": "IA • AUTOMATION",
    "generic": "PROJET • WORKSPACE",
}

_VISUAL_THEME_ACCENTS = {
    "btp": "#FACC15",
    "cyber": "#22D3EE",
    "excel": "#22C55E",
    "ai": "#8B5CF6",
    "generic": "#338CE4",
}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.lower()


def resolve_project_visual_theme(*texts: str) -> str:
    haystack = " ".join(_normalize(text) for text in texts)

    if any(
        token in haystack
        for token in (
            "btp",
            "batiment",
            "construction",
            "chantier",
            "etancheite",
            "maconnerie",
            "plomberie",
            "electricite",
            "peinture",
            "couverture",
            "renovation",
        )
    ):
        return "btp"

    if any(
        token in haystack
        for token in (
            "cyber",
            "securite informatique",
            "phishing",
            "ransomware",
        )
    ):
        return "cyber"

    if any(
        token in haystack
        for token in (
            "excel",
            "tableur",
            "reporting",
            "pilotage",
            "data",
        )
    ):
        return "excel"

    if any(
        token in haystack
        for token in (
            "intelligence artificielle",
            " ia ",
            " ia-",
            "ia ",
            "automation",
            "automatisation",
            "form@ai",
        )
    ):
        return "ai"

    return "generic"


def _mix(a: QColor, b: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, float(amount)))
    return QColor(
        round(a.red() + (b.red() - a.red()) * amount),
        round(a.green() + (b.green() - a.green()) * amount),
        round(a.blue() + (b.blue() - a.blue()) * amount),
        round(a.alpha() + (b.alpha() - a.alpha()) * amount),
    )


class CommercialProjectCard(QPushButton):
    """Premium clickable project/universe card with animated thematic artwork."""

    def __init__(
        self,
        *,
        title: str,
        stats_text: str,
        subtitle_text: str = "",
        metrics: tuple[tuple[str, str], ...] | None = None,
        context_text: str = "",
        kicker: str = "",
        theme_mode: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._title = str(title or "Projet").strip() or "Projet"
        self._stats_text = str(stats_text or "").strip()
        self._subtitle_text = str(subtitle_text or "").strip()
        self._metrics = tuple(
            (str(label or "").strip(), str(value or "").strip())
            for label, value in tuple(metrics or ())
            if str(label or "").strip()
        )
        self._context_text = str(context_text or "").strip()
        self._visual_theme = resolve_project_visual_theme(
            self._title,
            self._context_text,
        )
        self._kicker = (
            str(kicker or "").strip()
            or _VISUAL_THEME_LABELS[self._visual_theme]
        )
        self._theme_mode = theme_mode or projects_theme_mode()
        self._hover_progress = 0.0

        # Keep a real button text for accessibility and existing UI tests.
        self.setText(
            self._title
            + (f"\n{self._stats_text}" if self._stats_text else "")
        )
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.setMinimumHeight(194)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(28.0)
        self._shadow.setOffset(0.0, 5.0)
        self.setGraphicsEffect(self._shadow)
        self._update_shadow()

        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(185)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

    @property
    def visual_theme(self) -> str:
        return self._visual_theme

    def set_theme_mode(self, mode: str) -> None:
        mode = str(mode or "").strip() or projects_theme_mode()
        if mode == self._theme_mode:
            return
        self._theme_mode = mode
        self._update_shadow()
        self.update()

    def _get_hover_progress(self) -> float:
        return float(self._hover_progress)

    def _set_hover_progress(self, value: float) -> None:
        self._hover_progress = max(0.0, min(1.0, float(value)))
        self._update_shadow()
        self.update()

    hoverProgress = Property(
        float,
        _get_hover_progress,
        _set_hover_progress,
    )

    def _update_shadow(self) -> None:
        palette = projects_palette(self._theme_mode)
        dark = palette["bg"].upper() == "#06111F"
        alpha = int((95 if dark else 34) + self._hover_progress * (45 if dark else 34))
        self._shadow.setColor(QColor(0, 0, 0, alpha))
        self._shadow.setBlurRadius(28.0 + 16.0 * self._hover_progress)
        self._shadow.setOffset(0.0, 6.0 + 3.0 * self._hover_progress)

    def _animate_hover(self, target: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(float(target))
        self._hover_animation.start()

    def enterEvent(self, event):
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        lift = 2.6 * self._hover_progress
        outer = QRectF(self.rect()).adjusted(1.8, 3.4 - lift, -1.8, -5.0 - lift)
        outer_path = QPainterPath()
        outer_path.addRoundedRect(outer, 21.0, 21.0)

        palette = projects_palette(self._theme_mode)
        accent = QColor(_VISUAL_THEME_ACCENTS[self._visual_theme])
        surface = QColor(palette["surface"])
        surface_alt = QColor(palette["surface_alt"])
        text = QColor(palette["text"])
        text_soft = QColor(palette["text_soft"])
        muted = QColor(palette["muted"])

        if not self.isEnabled():
            painter.setOpacity(0.55)

        if self._visual_theme == "btp":
            self._paint_btp_frame(painter, outer_path, outer)
            inner = outer.adjusted(9.0, 9.0, -9.0, -9.0)
        else:
            inner = outer.adjusted(1.0, 1.0, -1.0, -1.0)

        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, 16.0, 16.0)

        base = _mix(surface, accent, 0.025 + self._hover_progress * 0.035)
        hover = _mix(surface_alt, accent, 0.07 + self._hover_progress * 0.06)
        gradient = QLinearGradient(inner.topLeft(), inner.bottomRight())
        gradient.setColorAt(0.0, base)
        gradient.setColorAt(0.64, surface)
        gradient.setColorAt(1.0, hover)
        painter.fillPath(inner_path, gradient)

        # Fine accent rail: gives every universe a product identity without
        # changing the shared layout between Classic / Light / Dark.
        rail = QRectF(inner.left(), inner.top(), 5.0, inner.height())
        rail_color = QColor(accent)
        rail_color.setAlpha(int(205 + 40 * self._hover_progress))
        painter.fillRect(rail, rail_color)

        border = QColor(palette["border"])
        border = _mix(border, accent, 0.25 + self._hover_progress * 0.70)
        if self.hasFocus():
            border = accent
        border.setAlpha(220)
        painter.setPen(QPen(border, 1.25 + self._hover_progress * 1.05))
        painter.drawPath(inner_path)

        painter.save()
        painter.setClipPath(inner_path)
        if self._visual_theme == "btp":
            self._paint_blueprint_grid(painter, inner, accent)
        self._paint_theme_monogram(painter, inner, accent)
        self._paint_theme_artwork(painter, inner, accent)
        self._paint_hover_shine(painter, inner, accent)
        painter.restore()

        content = inner.adjusted(20.0, 14.0, -20.0, -13.0)
        self._paint_text(painter, content, text, text_soft, muted, accent)

    def _paint_blueprint_grid(
        self,
        painter: QPainter,
        rect: QRectF,
        accent: QColor,
    ) -> None:
        painter.save()
        grid = QColor(accent)
        grid.setAlpha(int(12 + 9 * self._hover_progress))
        painter.setPen(QPen(grid, 0.8))
        step = 22.0
        x = rect.left() + rect.width() * 0.56
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = rect.top()
        while y < rect.bottom():
            painter.drawLine(
                QPointF(rect.left() + rect.width() * 0.54, y),
                QPointF(rect.right(), y),
            )
            y += step
        painter.restore()

    def _paint_theme_monogram(
        self,
        painter: QPainter,
        rect: QRectF,
        accent: QColor,
    ) -> None:
        labels = {
            "btp": "BTP",
            "cyber": "SEC",
            "excel": "DATA",
            "ai": "AI",
            "generic": "PRO",
        }
        font = QFont("Segoe UI", 38)
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        ghost = QColor(accent)
        ghost.setAlpha(int(17 + 18 * self._hover_progress))
        painter.setPen(ghost)
        painter.drawText(
            QRectF(rect.right() - 190.0, rect.top() + 14.0, 150.0, 56.0),
            Qt.AlignRight | Qt.AlignTop,
            labels.get(self._visual_theme, "PRO"),
        )

    def _paint_metric_pills(
        self,
        painter: QPainter,
        rect: QRectF,
        text: QColor,
        text_soft: QColor,
        accent: QColor,
    ) -> None:
        items = self._metrics
        if not items:
            return

        max_items = min(3, len(items))
        available = min(rect.width() * 0.68, 390.0)
        gap = 7.0
        pill_w = max(82.0, (available - gap * (max_items - 1)) / max_items)
        pill_h = 39.0
        x = rect.left()
        y = rect.top()

        for label, value in items[:max_items]:
            pill = QRectF(x, y, pill_w, pill_h)
            fill = QColor(accent)
            if "CHAUD" in label.upper():
                fill = QColor("#F97316")
            fill.setAlpha(int(18 + 12 * self._hover_progress))
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(pill, 9.0, 9.0)

            border = QColor(accent)
            if "CHAUD" in label.upper():
                border = QColor("#F97316")
            border.setAlpha(int(65 + 45 * self._hover_progress))
            painter.setPen(QPen(border, 0.9))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(pill, 9.0, 9.0)

            value_font = QFont("Segoe UI", 11)
            value_font.setWeight(QFont.Weight.Black)
            painter.setFont(value_font)
            painter.setPen(text)
            painter.drawText(
                QRectF(pill.left() + 10.0, pill.top() + 4.0, pill.width() - 20.0, 16.0),
                Qt.AlignLeft | Qt.AlignVCenter,
                value,
            )

            label_font = QFont("Segoe UI", 7)
            label_font.setWeight(QFont.Weight.Bold)
            painter.setFont(label_font)
            painter.setPen(text_soft)
            painter.drawText(
                QRectF(pill.left() + 10.0, pill.top() + 20.0, pill.width() - 20.0, 13.0),
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(label, Qt.ElideRight, int(pill.width() - 20.0)),
            )
            x += pill_w + gap

    def _paint_btp_frame(
        self,
        painter: QPainter,
        outer_path: QPainterPath,
        outer: QRectF,
    ) -> None:
        yellow = QColor("#FACC15")
        painter.save()
        painter.setClipPath(outer_path)
        painter.fillPath(outer_path, yellow)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111827"))
        stripe = 24.0
        diagonal = outer.height() * 0.40
        start = outer.left() - outer.height()
        end = outer.right() + outer.height()
        x = start
        while x < end:
            polygon = QPolygonF(
                [
                    QPointF(x, outer.top()),
                    QPointF(x + stripe * 0.48, outer.top()),
                    QPointF(x + diagonal + stripe * 0.48, outer.bottom()),
                    QPointF(x + diagonal, outer.bottom()),
                ]
            )
            painter.drawPolygon(polygon)
            x += stripe
        painter.restore()

    def _paint_hover_shine(
        self,
        painter: QPainter,
        rect: QRectF,
        accent: QColor,
    ) -> None:
        if self._hover_progress <= 0.01:
            return
        shine = QLinearGradient(rect.topLeft(), rect.topRight())
        transparent = QColor(accent)
        transparent.setAlpha(0)
        center = QColor(accent)
        center.setAlpha(int(24 + self._hover_progress * 34))
        shine.setColorAt(0.0, transparent)
        shine.setColorAt(0.62, transparent)
        shine.setColorAt(0.78, center)
        shine.setColorAt(1.0, transparent)
        painter.fillRect(rect, shine)

    def _paint_theme_artwork(
        self,
        painter: QPainter,
        rect: QRectF,
        accent: QColor,
    ) -> None:
        art = QColor(accent)
        art.setAlpha(int(34 + self._hover_progress * 24))
        pen = QPen(art, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self._visual_theme == "btp":
            self._paint_btp_artwork(painter, rect)
        elif self._visual_theme == "cyber":
            self._paint_cyber_artwork(painter, rect)
        elif self._visual_theme == "excel":
            self._paint_excel_artwork(painter, rect)
        elif self._visual_theme == "ai":
            self._paint_ai_artwork(painter, rect)
        else:
            self._paint_generic_artwork(painter, rect)

    @staticmethod
    def _paint_btp_artwork(painter: QPainter, rect: QRectF) -> None:
        right = rect.right() - 24.0
        top = rect.top() + 26.0
        bottom = rect.bottom() - 25.0
        mast_x = right - 66.0
        painter.drawLine(QPointF(mast_x, top + 20.0), QPointF(mast_x, bottom))
        painter.drawLine(QPointF(mast_x - 11.0, bottom), QPointF(mast_x + 11.0, bottom))
        painter.drawLine(QPointF(mast_x, top + 20.0), QPointF(right, top + 20.0))
        painter.drawLine(QPointF(mast_x, top + 20.0), QPointF(mast_x + 26.0, top + 5.0))
        painter.drawLine(QPointF(mast_x + 26.0, top + 5.0), QPointF(right, top + 20.0))
        hook_x = right - 17.0
        painter.drawLine(QPointF(hook_x, top + 20.0), QPointF(hook_x, top + 55.0))
        painter.drawArc(QRectF(hook_x - 5.0, top + 50.0, 10.0, 11.0), 180 * 16, 180 * 16)

        building_left = right - 122.0
        building_top = bottom - 44.0
        painter.drawRect(QRectF(building_left, building_top, 39.0, 44.0))
        for y in (building_top + 13.0, building_top + 27.0):
            painter.drawLine(QPointF(building_left, y), QPointF(building_left + 39.0, y))
        painter.drawLine(
            QPointF(building_left + 19.5, building_top),
            QPointF(building_left + 19.5, bottom),
        )

    @staticmethod
    def _paint_cyber_artwork(painter: QPainter, rect: QRectF) -> None:
        cx = rect.right() - 74.0
        cy = rect.center().y()
        shield = QPainterPath()
        shield.moveTo(cx, cy - 42.0)
        shield.lineTo(cx + 33.0, cy - 28.0)
        shield.lineTo(cx + 27.0, cy + 18.0)
        shield.quadTo(cx, cy + 46.0, cx - 27.0, cy + 18.0)
        shield.lineTo(cx - 33.0, cy - 28.0)
        shield.closeSubpath()
        painter.drawPath(shield)
        for offset in (-62.0, -45.0, 45.0, 62.0):
            painter.drawLine(QPointF(cx + offset, cy - 16.0), QPointF(cx + offset * 0.62, cy - 16.0))
            painter.drawEllipse(QPointF(cx + offset, cy - 16.0), 2.5, 2.5)

    @staticmethod
    def _paint_excel_artwork(painter: QPainter, rect: QRectF) -> None:
        grid = QRectF(rect.right() - 126.0, rect.top() + 28.0, 91.0, 92.0)
        painter.drawRoundedRect(grid, 8.0, 8.0)
        for i in range(1, 4):
            x = grid.left() + grid.width() * i / 4.0
            painter.drawLine(QPointF(x, grid.top()), QPointF(x, grid.bottom()))
        for i in range(1, 5):
            y = grid.top() + grid.height() * i / 5.0
            painter.drawLine(QPointF(grid.left(), y), QPointF(grid.right(), y))

    @staticmethod
    def _paint_ai_artwork(painter: QPainter, rect: QRectF) -> None:
        cx = rect.right() - 78.0
        cy = rect.center().y()
        points = [
            QPointF(cx, cy),
            QPointF(cx - 42.0, cy - 31.0),
            QPointF(cx - 47.0, cy + 29.0),
            QPointF(cx + 38.0, cy - 35.0),
            QPointF(cx + 45.0, cy + 28.0),
        ]
        for point in points[1:]:
            painter.drawLine(points[0], point)
        for index, point in enumerate(points):
            radius = 7.0 if index == 0 else 4.0
            painter.drawEllipse(point, radius, radius)

    @staticmethod
    def _paint_generic_artwork(painter: QPainter, rect: QRectF) -> None:
        start_x = rect.right() - 134.0
        base_y = rect.center().y()
        for index in range(4):
            x = start_x + index * 29.0
            height = 24.0 + index * 13.0
            painter.drawRoundedRect(
                QRectF(x, base_y - height / 2.0, 17.0, height),
                5.0,
                5.0,
            )

    def _paint_text(
        self,
        painter: QPainter,
        content: QRectF,
        text: QColor,
        text_soft: QColor,
        muted: QColor,
        accent: QColor,
    ) -> None:
        theme_label = _VISUAL_THEME_LABELS[self._visual_theme]
        kicker = self._kicker.upper()
        if self._visual_theme != "generic" and theme_label not in kicker:
            kicker = f"{theme_label}   •   {kicker}" if kicker else theme_label

        text_width = int(content.width() * 0.66)

        kicker_font = QFont("Segoe UI", 8)
        kicker_font.setWeight(QFont.Weight.Bold)
        painter.setFont(kicker_font)
        kicker_color = QColor(accent)
        kicker_color.setAlpha(240)
        painter.setPen(kicker_color)
        painter.drawText(
            QRectF(content.left(), content.top(), text_width, 18.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            painter.fontMetrics().elidedText(kicker, Qt.ElideRight, text_width),
        )

        title_font = QFont("Segoe UI", 17)
        title_font.setWeight(QFont.Weight.Black)
        painter.setFont(title_font)
        painter.setPen(text)
        painter.drawText(
            QRectF(content.left(), content.top() + 24.0, text_width, 30.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            painter.fontMetrics().elidedText(self._title, Qt.ElideRight, text_width),
        )

        subtitle = self._subtitle_text or self._stats_text
        if subtitle:
            subtitle_font = QFont("Segoe UI", 8)
            subtitle_font.setWeight(QFont.Weight.Medium)
            painter.setFont(subtitle_font)
            painter.setPen(muted)
            painter.drawText(
                QRectF(content.left(), content.top() + 54.0, text_width, 22.0),
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(subtitle, Qt.ElideRight, text_width),
            )

        metrics_rect = QRectF(
            content.left(),
            content.top() + 83.0,
            content.width(),
            42.0,
        )
        self._paint_metric_pills(painter, metrics_rect, text, text_soft, accent)

        action_font = QFont("Segoe UI", 8)
        action_font.setWeight(QFont.Weight.Bold)
        painter.setFont(action_font)
        action = "OUVRIR LE PROJET"
        if "univers" in self._kicker.lower():
            action = "EXPLORER L’UNIVERS"

        action_color = _mix(muted, accent, 0.66 + self._hover_progress * 0.30)
        painter.setPen(action_color)
        action_y = content.bottom() - 24.0
        painter.drawText(
            QRectF(content.left(), action_y, text_width - 34.0, 22.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            action,
        )

        arrow_x = content.left() + min(text_width - 24.0, 142.0) + 7.0 * self._hover_progress
        painter.drawText(
            QRectF(arrow_x, action_y, 28.0, 22.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            "→",
        )
