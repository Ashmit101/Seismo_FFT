"""Run expensive work without calling Tk (including after) from a worker."""

from queue import Empty, Queue
from threading import Thread

from loguru import logger


class BackgroundTask:
    """Run one job at a time and keep only the latest pending job."""

    def __init__(self, owner, on_result, on_error):
        self.owner = owner
        self.on_result = on_result
        self.on_error = on_error
        self._results = Queue()
        self._running = False
        self._pending = None
        self._generation = 0
        self._closed = False
        self._poll_id = None
        self._delivery_id = None
        owner.bind("<Destroy>", self._on_destroy, add="+")

    def submit(self, function, *args, **kwargs):
        if self._closed:
            return
        self._generation += 1
        request = (self._generation, function, args, kwargs)
        if self._running:
            self._pending = request
        else:
            self._start(request)

    def invalidate(self):
        """Discard outstanding results without trying to interrupt native work."""
        self._generation += 1
        self._pending = None

    def _start(self, request):
        self._running = True
        Thread(
            target=self._run,
            args=(self._results, request),
            daemon=True,
        ).start()
        self._poll_id = self.owner.after(25, self._poll)

    @staticmethod
    def _run(results, request):
        generation, function, args, kwargs = request
        try:
            result = function(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            logger.exception("Background analysis failed")
            results.put((generation, None, error))
        else:
            results.put((generation, result, None))

    def _poll(self):
        self._poll_id = None
        if self._closed:
            return
        try:
            generation, result, error = self._results.get_nowait()
        except Empty:
            self._poll_id = self.owner.after(25, self._poll)
            return
        self._running = False
        if self._pending is not None:
            request, self._pending = self._pending, None
            self._start(request)
        else:
            self._delivery_id = self.owner.after(
                0, self._deliver, generation, result, error
            )

    def _deliver(self, generation, result, error):
        self._delivery_id = None
        if self._closed or generation != self._generation:
            return
        if error is not None:
            self.on_error(error)
        else:
            try:
                self.on_result(result)
            except Exception as display_error:  # noqa: BLE001
                logger.exception("Could not display background result")
                self.on_error(display_error)

    def _on_destroy(self, event):
        if event.widget is not self.owner:
            return
        self._closed = True
        self._pending = None
        for callback_id in (self._poll_id, self._delivery_id):
            if callback_id is not None:
                self.owner.after_cancel(callback_id)
