"""Verify restore isolation without serializing ordinary requests."""

from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from torrent_dashboard.state_gate import StateGate


class StateGateTests(unittest.TestCase):
    def test_ordinary_activity_can_overlap(self):
        gate = StateGate()
        both_entered = threading.Barrier(2)
        def task():
            with gate.activity():
                both_entered.wait(timeout=2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(task) for _ in range(2)]
            for future in futures:
                future.result(timeout=3)

    def test_maintenance_waits_for_activity_and_blocks_new_activity(self):
        gate = StateGate()
        maintenance_started, maintenance_entered = threading.Event(), threading.Event()
        release_maintenance, activity_entered = threading.Event(), threading.Event()
        def maintain():
            maintenance_started.set()
            with gate.maintenance():
                maintenance_entered.set()
                release_maintenance.wait(3)
        def read():
            with gate.activity():
                activity_entered.set()
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                with gate.activity():
                    maintenance = pool.submit(maintain)
                    self.assertTrue(maintenance_started.wait(2))
                    self.assertFalse(maintenance_entered.wait(0.03))
                self.assertTrue(maintenance_entered.wait(2))
                reader = pool.submit(read)
                self.assertFalse(activity_entered.wait(0.03))
            finally:
                release_maintenance.set()
            maintenance.result(timeout=2)
            reader.result(timeout=2)
            self.assertTrue(activity_entered.is_set())

    def test_exceptions_release_both_kinds_of_entry(self):
        gate = StateGate()
        for enter in (gate.activity, gate.maintenance):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                with enter():
                    raise RuntimeError("failed")
        with gate.maintenance():
            pass
        with gate.activity():
            pass
