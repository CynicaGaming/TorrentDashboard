"""History connections must close before state files can be restored on Windows."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from torrent_dashboard.history import HistoryStore


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = HistoryStore(Path(self.temp.name) / "history.sqlite3")

    def test_connections_close_after_commit_and_rollback(self):
        with self.store._db() as connection:
            connection.execute("INSERT INTO events(ts, event) VALUES(1, 'committed')")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with self.store._db() as failed:
                failed.execute("INSERT INTO events(ts, event) VALUES(2, 'rolled-back')")
                raise RuntimeError("abort")
        with self.assertRaises(sqlite3.ProgrammingError):
            failed.execute("SELECT 1")
        self.assertEqual([row["event"] for row in self.store.events()], ["committed"])
        # A real filesystem check catches Windows file-handle leaks.
        renamed = self.store.path.with_suffix(".moved")
        self.store.path.replace(renamed)
        renamed.replace(self.store.path)

    def test_reads_events_and_cleanup_wait_for_restore_lock(self):
        for operation in (lambda: self.store.event("test", "event"),
                          lambda: self.store.cleanup(30), self.store.events,
                          lambda: self.store.analytics("all")):
            with self.subTest(operation=operation), ThreadPoolExecutor(max_workers=1) as pool:
                entered, finished = threading.Event(), threading.Event()
                def run():
                    entered.set()
                    operation()
                    finished.set()
                with self.store.lock:
                    future = pool.submit(run)
                    self.assertTrue(entered.wait(2))
                    self.assertFalse(finished.wait(0.03))
                future.result(timeout=2)
                self.assertTrue(finished.is_set())

    def test_reset_tracking_allows_new_installation_to_sample(self):
        self.store.last_seen[("old", "hash")] = True
        self.store.last_sample["old"] = 9999999999
        self.store.reset_tracking()
        self.assertEqual(self.store.last_seen, {})
        self.assertEqual(self.store.last_sample, {})
