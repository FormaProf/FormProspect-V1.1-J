import threading

from PySide6.QtCore import QObject, Signal, Slot

from services.enrichment_service import EnrichmentService


class EnrichmentWorker(QObject):
    progress = Signal(dict)
    finished = Signal(dict)
    failed = Signal(str)
    paused_changed = Signal(bool)

    def __init__(self, database_path, limite=None):
        super().__init__()
        self.database_path = database_path
        self.limite = limite
        self._stop_event = threading.Event()
        self._pause_condition = threading.Condition()
        self._paused = False

    @Slot()
    def run(self):
        try:
            service = EnrichmentService()
            resultat = service.enrichir(
                self.database_path,
                limite=self.limite,
                progress_callback=self.progress.emit,
                should_stop=self._stop_event.is_set,
                wait_if_paused=self._wait_if_paused,
            )
            self.finished.emit(resultat)
        except Exception as exc:
            self.failed.emit(str(exc))

    def request_stop(self):
        self._stop_event.set()
        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()

    def pause(self):
        with self._pause_condition:
            self._paused = True
        self.paused_changed.emit(True)

    def resume(self):
        with self._pause_condition:
            self._paused = False
            self._pause_condition.notify_all()
        self.paused_changed.emit(False)

    def _wait_if_paused(self):
        with self._pause_condition:
            while self._paused and not self._stop_event.is_set():
                self._pause_condition.wait(timeout=0.25)
