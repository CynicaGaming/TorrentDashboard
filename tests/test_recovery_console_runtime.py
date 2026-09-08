from __future__ import annotations

import unittest
from unittest import mock

from torrent_dashboard import dashboard


class _Handler:
    def client_ip(self):
        return "127.0.0.1"


class RecoveryConsoleRuntimeTests(unittest.TestCase):
    def setUp(self):
        with dashboard.CACHE_LOCK:
            dashboard.CACHE.clear()

    def tearDown(self):
        with dashboard.CACHE_LOCK:
            dashboard.CACHE.clear()

    def test_torrent_list_is_read_only_and_exposes_actionable_identifiers(self):
        cfg = {
            "servers": [{"id": "desktop", "name": "Desktop", "enabled": True}],
            "integrations": [],
            "users": [],
            "auth": {"mode": "password"},
        }
        torrent_hash = "a" * 40
        with dashboard.CACHE_LOCK:
            dashboard.CACHE["desktop"] = {
                "ok": True,
                "torrents": [{
                    "hash": torrent_hash,
                    "name": "Example Torrent",
                    "state": "downloading",
                    "progress": 0.425,
                }],
            }
        result = dashboard.recovery_console_execute(
            _Handler(), cfg, "torrent list", sess={"group": "standard"}
        )
        self.assertIn("CLIENT  HASH  STATE  PROGRESS  NAME", result["output"])
        self.assertIn("desktop", result["output"])
        self.assertIn(torrent_hash, result["output"])
        self.assertIn("42.5%", result["output"])
        self.assertIn("Example Torrent", result["output"])
        with self.assertRaisesRegex(RuntimeError, "Administrator access"):
            dashboard.recovery_console_execute(
                _Handler(), cfg, f"torrent action desktop stop {torrent_hash}", sess={"group": "standard"}
            )

    def test_torrent_list_can_filter_to_one_client(self):
        cfg = {
            "servers": [
                {"id": "one", "name": "One", "enabled": True},
                {"id": "two", "name": "Two", "enabled": True},
            ],
            "integrations": [],
            "users": [],
            "auth": {"mode": "password"},
        }
        with dashboard.CACHE_LOCK:
            dashboard.CACHE["one"] = {"ok": True, "torrents": [{"hash": "1" * 40, "name": "First", "state": "paused", "progress": 1}]}
            dashboard.CACHE["two"] = {"ok": True, "torrents": [{"hash": "2" * 40, "name": "Second", "state": "seeding", "progress": 1}]}
        result = dashboard.recovery_console_execute(
            _Handler(), cfg, "torrent list two", sess={"group": "standard"}
        )
        self.assertIn("Second", result["output"])
        self.assertNotIn("First", result["output"])

    def test_jellyfin_list_alias_lists_actionable_task_ids(self):
        cfg = {"servers": [], "integrations": [], "users": [], "auth": {"mode": "password"}}
        task = {"id": "task-1", "category": "Library", "name": "Scan media library", "state": "Idle"}
        with mock.patch.object(dashboard, "find_jellyfin_integration", return_value={"id": "jf"}), \
             mock.patch.object(dashboard, "jellyfin_scheduled_tasks", return_value=[task]):
            result = dashboard.recovery_console_execute(
                _Handler(), cfg, "jellyfin list jf", sess={"group": "standard"}
            )
        self.assertIn("task-1", result["output"])
        self.assertIn("Scan media library", result["output"])


if __name__ == "__main__":
    unittest.main()
