from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, QSize
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QFrame,
    QLayout,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)


DESKTOP = "desktop"
LAPTOP = "laptop"
COMPACT = "compact"


@dataclass(frozen=True)
class ResponsiveMetrics:
    mode: str
    viewport_width: int
    viewport_height: int


def fit_window_to_available_geometry(
    window: QMainWindow,
    preferred_width: int,
    preferred_height: int,
) -> None:
    """Cap the initial window size to the usable desktop geometry.

    Qt exposes the *logical* available geometry, so Windows scaling at 125/150 %
    is already taken into account. This avoids opening Form@Prospect larger than
    the real laptop workspace without forcing a maximized window.
    """

    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        window.resize(int(preferred_width), int(preferred_height))
        return

    available = screen.availableGeometry()
    width = min(int(preferred_width), max(1, int(available.width())))
    height = min(int(preferred_height), max(1, int(available.height())))
    window.resize(width, height)


class ResponsiveStackedWidget(QStackedWidget):
    """QStackedWidget whose hints reflect only the visible page.

    A stock QStackedWidget can use the largest size hint of every page. Inside a
    scroll area that may create unnecessary scrollbars because one hidden page is
    tall. Keeping the public QStackedWidget API while basing hints on the current
    page makes the global responsive host predictable.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ResponsivePageStack")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def _current_hint(self, *, minimum: bool) -> QSize:
        page = self.currentWidget()
        if page is None:
            return super().minimumSizeHint() if minimum else super().sizeHint()

        hint = page.minimumSizeHint() if minimum else page.sizeHint()
        explicit = page.minimumSize()
        return QSize(
            max(0, int(hint.width()), int(explicit.width())),
            max(0, int(hint.height()), int(explicit.height())),
        )

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self._current_hint(minimum=False)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self._current_hint(minimum=True)


class ResponsivePageHost(QScrollArea):
    """One transparent overflow host for the whole application workspace.

    Crucially, pages remain children of the same QStackedWidget as before. No
    page is wrapped, re-parented or rebuilt. Therefore their objectName/QSS theme
    hierarchy is preserved. The host only becomes scrollable when the current
    page's *minimum* layout size exceeds the available viewport.
    """

    def __init__(self, stack: ResponsiveStackedWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stack = stack
        self._last_page: Optional[QWidget] = None
        self._scroll_positions: dict[int, tuple[int, int]] = {}

        self.setObjectName("ResponsivePageHost")
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)

        # Keep the new container visually neutral. In particular, never paint a
        # white viewport behind dark themed pages.
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        transparent = self.viewport().palette()
        transparent.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.viewport().setPalette(transparent)
        self.setStyleSheet(
            "QScrollArea#ResponsivePageHost { background: transparent; border: none; }"
        )

        self.setWidget(self.stack)
        # QScrollArea.setWidget() may enable autoFillBackground on the child.
        # Disable it immediately so the stack never introduces a theme colour.
        self.stack.setAutoFillBackground(False)
        self.stack.setAttribute(Qt.WA_TranslucentBackground, True)

        self.stack.currentChanged.connect(self._on_current_changed)
        QTimer.singleShot(0, self.sync_current_page)

    @staticmethod
    def _layout_minimum(page: QWidget) -> QSize:
        layout = page.layout()
        if layout is None:
            return QSize(0, 0)
        layout.activate()
        minimum = layout.minimumSize()
        margins = layout.contentsMargins()
        return QSize(
            max(0, minimum.width()),
            max(0, minimum.height()),
        )

    def _required_size(self, page: QWidget) -> QSize:
        page.ensurePolished()
        hint = page.minimumSizeHint()
        layout_hint = self._layout_minimum(page)
        explicit = page.minimumSize()
        return QSize(
            max(0, hint.width(), layout_hint.width(), explicit.width()),
            max(0, hint.height(), layout_hint.height(), explicit.height()),
        )

    def _remember_scroll(self, page: Optional[QWidget]) -> None:
        if page is None:
            return
        self._scroll_positions[id(page)] = (
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
        )

    def _restore_scroll(self, page: Optional[QWidget]) -> None:
        if page is None:
            return
        horizontal, vertical = self._scroll_positions.get(id(page), (0, 0))
        self.horizontalScrollBar().setValue(horizontal)
        self.verticalScrollBar().setValue(vertical)

    def _on_current_changed(self, _index: int) -> None:
        self._remember_scroll(self._last_page)
        self._last_page = self.stack.currentWidget()

        def refresh() -> None:
            self.sync_current_page()
            self._restore_scroll(self._last_page)

        QTimer.singleShot(0, refresh)

    def sync_current_page(self) -> None:
        """Update only geometry/minimums; never reload business data."""

        page = self.stack.currentWidget()
        if page is None:
            self.stack.setMinimumSize(0, 0)
            return

        required = self._required_size(page)
        viewport = self.viewport().size()

        # If the page fits, widgetResizable keeps the stack exactly on the
        # viewport. If it does not, the relevant scrollbar appears instead of
        # clipping bottom/right actions.
        min_height = required.height() if required.height() > viewport.height() else 0
        min_width = required.width() if required.width() > viewport.width() else 0

        self.stack.setMinimumHeight(max(0, min_height))
        self.stack.setMinimumWidth(max(0, min_width))
        self.stack.updateGeometry()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self.sync_current_page)


class ResponsiveManager(QObject):
    """Central responsive controller for every page in the workspace.

    The manager deliberately avoids page-specific widget surgery. It only:
    - computes a mode from the *real central viewport*;
    - reduces the top-level page margins/spacing on smaller screens;
    - keeps the already-scrollable sidebar visually unchanged;
    - lets a page opt into extra responsive behaviour in the future through an
      optional ``apply_responsive_mode`` method.

    No service, Cloud API or page refresh method is called here.
    """

    def __init__(
        self,
        *,
        window: QMainWindow,
        host: ResponsivePageHost,
        stack: ResponsiveStackedWidget,
        sidebar: QWidget,
    ):
        super().__init__(window)
        self.window = window
        self.host = host
        self.stack = stack
        self.sidebar = sidebar
        self.mode = DESKTOP
        self.metrics = ResponsiveMetrics(DESKTOP, 0, 0)
        self._page_layout_defaults: dict[int, tuple[QWidget, tuple[int, int, int, int], int]] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(0)
        self._refresh_timer.timeout.connect(self.refresh)

        self.window.installEventFilter(self)
        self.host.viewport().installEventFilter(self)
        self.stack.currentChanged.connect(lambda _index: self.schedule_refresh())
        self.schedule_refresh()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.schedule_refresh()
        return super().eventFilter(watched, event)

    def schedule_refresh(self) -> None:
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    @staticmethod
    def _mode_for(width: int, height: int) -> str:
        # Widths are central-workspace widths after the sidebar. 1366×768 laptops
        # usually land around 1100 logical px here; Windows 125 % scaling can be
        # lower, hence the compact fallback.
        if width >= 1240 and height >= 760:
            return DESKTOP
        if width >= 1020 and height >= 620:
            return LAPTOP
        return COMPACT

    def _remember_layout_defaults(self, page: QWidget) -> None:
        key = id(page)
        if key in self._page_layout_defaults:
            return
        layout = page.layout()
        if layout is None:
            return
        margins = layout.contentsMargins()
        self._page_layout_defaults[key] = (
            page,
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            layout.spacing(),
        )

    def _apply_root_density(self, page: QWidget, mode: str) -> None:
        self._remember_layout_defaults(page)
        saved = self._page_layout_defaults.get(id(page))
        if saved is None:
            return

        _page, original, original_spacing = saved
        layout = page.layout()
        if layout is None:
            return

        left, top, right, bottom = original
        if mode == DESKTOP:
            layout.setContentsMargins(left, top, right, bottom)
            if original_spacing >= 0:
                layout.setSpacing(original_spacing)
            return

        if mode == LAPTOP:
            caps = (20, 16, 20, 18)
            spacing_cap = 12
        else:
            caps = (14, 12, 14, 14)
            spacing_cap = 10

        layout.setContentsMargins(
            min(left, caps[0]),
            min(top, caps[1]),
            min(right, caps[2]),
            min(bottom, caps[3]),
        )
        if original_spacing >= 0:
            layout.setSpacing(min(original_spacing, spacing_cap))

    def refresh(self) -> None:
        viewport = self.host.viewport().size()
        width = max(0, int(viewport.width()))
        height = max(0, int(viewport.height()))
        mode = self._mode_for(width, height)

        self.mode = mode
        self.metrics = ResponsiveMetrics(mode, width, height)
        self.window.setProperty("responsiveMode", mode)
        self.host.setProperty("responsiveMode", mode)
        self.sidebar.setProperty("responsiveMode", mode)

        page = self.stack.currentWidget()
        if page is not None:
            page.setProperty("responsiveMode", mode)
            self._apply_root_density(page, mode)

            callback = getattr(page, "apply_responsive_mode", None)
            if callable(callback):
                callback(mode, QSize(width, height))

        self.host.sync_current_page()
