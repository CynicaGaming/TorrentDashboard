"""Coordinate live requests and collectors with exclusive state restoration."""

from contextlib import contextmanager
import threading


class StateGate:
    """Allow concurrent activity; drain it before maintenance, then pause new work.

    Acquire this gate before configuration, history, or cache locks. Entries are
    intentionally not reentrant: acquire once at the request/collector boundary.
    A waiting maintenance operation takes priority over new activity.
    """

    def __init__(self):
        self._condition = threading.Condition()
        self._readers = 0
        self._waiting_writers = 0
        self._writer = False

    @contextmanager
    def activity(self):
        with self._condition:
            self._condition.wait_for(lambda: not self._writer and not self._waiting_writers)
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                self._condition.notify_all()

    @contextmanager
    def maintenance(self):
        with self._condition:
            self._waiting_writers += 1
            try:
                self._condition.wait_for(lambda: not self._writer and not self._readers)
                self._writer = True
            finally:
                self._waiting_writers -= 1
                self._condition.notify_all()
        try:
            yield
        finally:
            with self._condition:
                self._writer = False
                self._condition.notify_all()


__all__ = ["StateGate"]
