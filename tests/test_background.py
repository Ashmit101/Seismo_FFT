"""Headless regression coverage for the Tk/worker hand-off."""

import heapq
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ground_motion_analyzer.background import BackgroundTask


class FakeTkOwner:
    """A small owner-thread-only after scheduler; never creates a Tcl interpreter."""

    def __init__(self):
        self.thread_id = threading.get_ident()
        self.callbacks = {}
        self.queue = []
        self.bindings = {}
        self.sequence = 0
        self.thread_violations = []
        self.scheduled_delays = []
        self.cancelled = []
        self.destroyed = False

    def _check_thread(self):
        if threading.get_ident() != self.thread_id:
            self.thread_violations.append(threading.get_ident())
            raise AssertionError("Tk owner accessed outside its main thread")

    def bind(self, event, callback, add=None):
        self._check_thread()
        self.bindings[event] = callback

    def after(self, delay, callback, *args):
        self._check_thread()
        if self.destroyed:
            raise AssertionError("after called after destruction")
        self.sequence += 1
        callback_id = f"after#{self.sequence}"
        self.callbacks[callback_id] = (callback, args, delay)
        self.scheduled_delays.append(delay)
        heapq.heappush(
            self.queue, (time.monotonic() + delay / 1000, self.sequence, callback_id)
        )
        return callback_id

    def after_cancel(self, callback_id):
        self._check_thread()
        self.cancelled.append(callback_id)
        self.callbacks.pop(callback_id, None)

    def destroy_event(self, widget=None):
        self._check_thread()
        self.bindings["<Destroy>"](
            SimpleNamespace(widget=self if widget is None else widget)
        )
        if widget is None:
            self.destroyed = True

    def run_until(self, predicate, timeout=3):
        """Run real scheduled callbacks on this thread, with a bounded timeout."""
        self._check_thread()
        deadline = time.monotonic() + timeout
        while not predicate():
            now = time.monotonic()
            if now >= deadline:
                raise AssertionError("Timed out waiting for background callback")
            if self.queue and self.queue[0][0] <= now:
                _, _, callback_id = heapq.heappop(self.queue)
                entry = self.callbacks.pop(callback_id, None)
                if entry is not None:
                    callback, args, _ = entry
                    callback(*args)
            else:
                # Yield to the real worker without calling any Tk API there.
                threading.Event().wait(min(0.001, deadline - now))

    def has_delivery(self):
        return any(delay == 0 for _, _, delay in self.callbacks.values())


class BackgroundTaskTests(unittest.TestCase):
    def setUp(self):
        self.owner = FakeTkOwner()
        self.results = []
        self.errors = []
        self.callback_threads = []
        self.task = BackgroundTask(self.owner, self.on_result, self.on_error)
        # Expected worker errors should not swamp unittest output with tracebacks.
        self.log_patch = patch("ground_motion_analyzer.background.logger")
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def tearDown(self):
        if not self.owner.destroyed:
            self.owner.destroy_event()
        self.assertEqual(self.owner.thread_violations, [])

    def on_result(self, result):
        self.callback_threads.append(threading.get_ident())
        self.results.append(result)

    def on_error(self, error):
        self.callback_threads.append(threading.get_ident())
        self.errors.append(error)

    def blocking_worker(self, result=None, error=None):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        self.addCleanup(release.set)

        def work():
            started.set()
            try:
                if not release.wait(3):
                    raise AssertionError("Test did not release worker")
                if error is not None:
                    raise error
                return result
            finally:
                finished.set()

        return work, started, release, finished

    def test_work_is_daemon_and_results_are_deferred_to_main_thread(self):
        worker_threads = []

        def work(value, *, suffix):
            worker_threads.append(threading.current_thread())
            return value + suffix

        self.task.submit(work, "answer", suffix="!")
        self.assertEqual(self.results, [])
        self.owner.run_until(self.owner.has_delivery)
        self.assertEqual(
            self.results, []
        )  # Polling schedules, rather than calls, delivery.
        self.owner.run_until(lambda: bool(self.results))

        self.assertEqual(self.results, ["answer!"])
        self.assertEqual(self.errors, [])
        self.assertNotEqual(worker_threads[0].ident, self.owner.thread_id)
        self.assertTrue(worker_threads[0].daemon)
        self.assertEqual(self.callback_threads, [self.owner.thread_id])
        self.assertIn(0, self.owner.scheduled_delays)

    def test_latest_pending_request_replaces_intermediate_work(self):
        first, started, release, _ = self.blocking_worker("obsolete")
        executed = []
        self.task.submit(first)
        self.assertTrue(started.wait(3))
        self.task.submit(lambda: executed.append("intermediate"))
        self.task.submit(lambda: executed.append("latest") or "current")
        release.set()
        self.owner.run_until(lambda: bool(self.results))

        self.assertEqual(executed, ["latest"])
        self.assertEqual(self.results, ["current"])
        self.assertEqual(self.errors, [])

    def test_obsolete_worker_error_is_not_delivered(self):
        first, started, release, _ = self.blocking_worker(error=ValueError("obsolete"))
        self.task.submit(first)
        self.assertTrue(started.wait(3))
        self.task.submit(lambda: "latest")
        release.set()
        self.owner.run_until(lambda: bool(self.results))

        self.assertEqual(self.results, ["latest"])
        self.assertEqual(self.errors, [])

    def test_new_submission_invalidates_already_queued_success_and_error(self):
        for obsolete_error in (False, True):
            with self.subTest(obsolete_error=obsolete_error):
                self.results.clear()
                self.errors.clear()

                def obsolete(should_fail=obsolete_error):
                    if should_fail:
                        raise ValueError("already queued obsolete error")
                    return "already queued obsolete result"

                self.task.submit(obsolete)
                self.owner.run_until(self.owner.has_delivery)
                self.task.submit(lambda: "newest")
                self.owner.run_until(lambda: bool(self.results))
                self.assertEqual(self.results, ["newest"])
                self.assertEqual(self.errors, [])

    def test_invalidate_drops_running_and_pending_work(self):
        first, started, release, _ = self.blocking_worker("obsolete")
        executed = []
        self.task.submit(first)
        self.assertTrue(started.wait(3))
        self.task.submit(lambda: executed.append("pending"))
        self.task.invalidate()
        release.set()
        self.owner.run_until(
            lambda: not self.task._running and not self.owner.callbacks
        )
        self.assertEqual(executed, [])
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors, [])
        self.task.submit(lambda: "valid again")
        self.owner.run_until(lambda: bool(self.results))
        self.assertEqual(self.results, ["valid again"])

    def test_worker_error_reaches_main_thread_and_next_request_recovers(self):
        error = ValueError("bad analysis")

        def fail():
            raise error

        self.task.submit(fail)
        self.owner.run_until(lambda: bool(self.errors))
        self.assertIs(self.errors[0], error)
        self.assertEqual(self.results, [])
        self.task.submit(lambda: "recovered")
        self.owner.run_until(lambda: bool(self.results))
        self.assertEqual(self.results, ["recovered"])
        self.assertEqual(self.callback_threads, [self.owner.thread_id] * 2)

    def test_result_callback_error_is_reported_and_does_not_poison_worker(self):
        error = RuntimeError("display failed")

        def display(result):
            self.assertEqual(threading.get_ident(), self.owner.thread_id)
            if result == "bad":
                raise error
            self.on_result(result)

        self.task.on_result = display
        self.task.submit(lambda: "bad")
        self.owner.run_until(lambda: bool(self.errors))
        self.assertIs(self.errors[0], error)
        self.task.submit(lambda: "good")
        self.owner.run_until(lambda: bool(self.results))
        self.assertEqual(self.results, ["good"])
        self.assertEqual(self.callback_threads, [self.owner.thread_id] * 2)

    def test_destruction_cancels_poll_and_discards_pending_and_future_work(self):
        work, started, release, finished = self.blocking_worker("too late")
        executed = []
        self.task.submit(work)
        self.assertTrue(started.wait(3))
        self.task.submit(lambda: executed.append("pending"))
        queued = set(self.owner.callbacks)
        self.owner.destroy_event()
        self.task.submit(lambda: executed.append("after destruction"))
        release.set()
        self.assertTrue(finished.wait(3))

        self.assertTrue(queued.issubset(self.owner.cancelled))
        self.assertEqual(self.owner.callbacks, {})
        self.assertEqual(executed, [])
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors, [])

    def test_destruction_cancels_queued_delivery(self):
        self.task.submit(lambda: "too late")
        self.owner.run_until(self.owner.has_delivery)
        queued = set(self.owner.callbacks)
        self.owner.destroy_event()

        self.assertTrue(queued.issubset(self.owner.cancelled))
        self.assertEqual(self.owner.callbacks, {})
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors, [])

    def test_child_destruction_does_not_close_owner_task(self):
        self.owner.destroy_event(widget=object())
        self.task.submit(lambda: "still alive")
        self.owner.run_until(lambda: bool(self.results))
        self.assertEqual(self.results, ["still alive"])


if __name__ == "__main__":
    unittest.main()
