from __future__ import annotations

import threading
import traceback

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
        """
        Lance l'enrichissement dans un thread Python natif dédié.

        Pourquoi ?
        ----------
        Form@Prospect utilise déjà un QThread pour ne pas bloquer l'interface.
        Sur certaines configurations Qt/qasync/Playwright, le thread Qt peut
        néanmoins être vu par Playwright comme étant associé à une boucle
        asyncio active. L'API Sync de Playwright refuse alors de démarrer.

        Un thread Python natif neuf ne possède pas de boucle asyncio active.
        Playwright Sync est donc créé et utilisé intégralement dans CE thread,
        conformément à sa contrainte d'utilisation par thread.
        """
        result_holder = {}
        error_holder = {}

        def _execute():
            try:
                # Important : créer le service dans le thread natif lui-même.
                # Ses instances GoogleMapsFinder / PagesJaunesFinder et
                # sync_playwright() resteront ainsi dans le même thread.
                service = EnrichmentService()
                result_holder["result"] = service.enrichir(
                    self.database_path,
                    limite=self.limite,
                    progress_callback=self.progress.emit,
                    should_stop=self._stop_event.is_set,
                    wait_if_paused=self._wait_if_paused,
                )
            except Exception as exc:
                error_holder["message"] = str(exc)
                error_holder["traceback"] = traceback.format_exc()

        worker_thread = threading.Thread(
            target=_execute,
            name="FormProspect-Enrichment-Playwright",
            daemon=True,
        )
        worker_thread.start()
        worker_thread.join()

        if "message" in error_holder:
            # On conserve un message lisible dans l'UI tout en envoyant aussi
            # la dernière ligne de traceback si le message Python est vide.
            message = error_holder["message"].strip()
            if not message:
                message = error_holder["traceback"].strip().splitlines()[-1]
            self.failed.emit(message)
            return

        self.finished.emit(
            result_holder.get(
                "result",
                {
                    "total": 0,
                    "traites": 0,
                    "erreurs": 0,
                    "interrompu": bool(self._stop_event.is_set()),
                },
            )
        )

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
