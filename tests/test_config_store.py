from __future__ import annotations

import copy
import threading
import time
import unittest

from torrent_dashboard.config_store import ConfigStore


class ConfigStoreTests(unittest.TestCase):
    def test_concurrent_mutations_preserve_both_changes(self):
        state = {"dashboard": {"title": "Torrent Dashboard"}, "auth": {"mode": "required"}}
        state_lock = threading.Lock()

        def load():
            with state_lock:
                return copy.deepcopy(state)

        def save(updated):
            with state_lock:
                state.clear()
                state.update(copy.deepcopy(updated))

        store = ConfigStore(load, save)
        start = threading.Barrier(3)

        def change_title():
            start.wait()

            def transform(cfg):
                time.sleep(0.03)
                cfg["dashboard"]["title"] = "Concurrent title"
                return cfg, "title"

            store.mutate(transform)

        def change_auth():
            start.wait()

            def transform(cfg):
                cfg["auth"]["mode"] = "lan_bypass"
                return cfg, "auth"

            store.mutate(transform)

        first = threading.Thread(target=change_title)
        second = threading.Thread(target=change_auth)
        first.start()
        second.start()
        start.wait()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(state["dashboard"]["title"], "Concurrent title")
        self.assertEqual(state["auth"]["mode"], "lan_bypass")

    def test_failed_mutation_does_not_save_partial_state(self):
        state = {"value": 1}
        save_count = 0

        def load():
            return copy.deepcopy(state)

        def save(updated):
            nonlocal save_count
            save_count += 1
            state.clear()
            state.update(copy.deepcopy(updated))

        store = ConfigStore(load, save)

        def transform(cfg):
            cfg["value"] = 2
            raise RuntimeError("validation failed")

        with self.assertRaisesRegex(RuntimeError, "validation failed"):
            store.mutate(transform)

        self.assertEqual(state, {"value": 1})
        self.assertEqual(save_count, 0)


if __name__ == "__main__":
    unittest.main()
