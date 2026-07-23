import weakref

from .notification_container import NotificationContainer


class NotificationManager:
    """Point d'accès global aux notifications Form@Prospect."""

    _host_ref = None
    _container = None

    @classmethod
    def configure(cls, host_window):
        cls._host_ref = weakref.ref(host_window)
        cls._container = NotificationContainer(host_window)
        cls.reposition()
        cls._container.show()
        cls._container.raise_()

    @classmethod
    def reposition(cls):
        host = cls._host_ref() if cls._host_ref else None
        if host is not None and cls._container is not None:
            cls._container.setGeometry(host.rect())
            cls._container.raise_()

    @classmethod
    def show(cls, title, message="", kind="info", duration_ms=4500):
        if cls._container is None:
            # Sécurité : le logiciel reste utilisable même si le manager n'est pas configuré.
            return None
        return cls._container.add_notification(title, message, kind, duration_ms)

    @classmethod
    def success(cls, title, message="", duration_ms=4200):
        return cls.show(title, message, "success", duration_ms)

    @classmethod
    def info(cls, title, message="", duration_ms=4200):
        return cls.show(title, message, "info", duration_ms)

    @classmethod
    def warning(cls, title, message="", duration_ms=5200):
        return cls.show(title, message, "warning", duration_ms)

    @classmethod
    def error(cls, title, message="", duration_ms=6500):
        return cls.show(title, message, "error", duration_ms)
