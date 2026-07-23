from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .notification import NotificationToast


class NotificationContainer(QWidget):
    """Calque transparent qui empile les notifications en bas à droite."""

    MAX_VISIBLE = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 18, 24, 28)
        self.layout.setSpacing(10)
        self.layout.addStretch(1)
        self.layout.setAlignment(Qt.AlignRight | Qt.AlignBottom)

    def add_notification(self, title, message="", kind="info", duration_ms=4500):
        toasts = self.findChildren(NotificationToast, options=Qt.FindDirectChildrenOnly)
        while len(toasts) >= self.MAX_VISIBLE:
            oldest = toasts.pop(0)
            self.remove_toast(oldest)
            oldest.deleteLater()

        toast = NotificationToast(title, message, kind, duration_ms, self)
        self.layout.addWidget(toast, 0, Qt.AlignRight)
        toast.show_animated()
        self.raise_()
        return toast

    def remove_toast(self, toast):
        self.layout.removeWidget(toast)
