from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from torrent_dashboard import recovery_operations as ro
from torrent_dashboard.history import HistoryStore


class RecoveryOperationsTests(unittest.TestCase):
    def test_redacted_configuration_does_not_expose_client_secrets(self):
        cfg = {
            "servers": [{
                "id": "desktop",
                "name": "Desktop",
                "base_url": "http://127.0.0.1:8080",
                "auth_method": "password",
                "username": "admin",
                "password": "secret",
                "api_key": "not-a-real-api-key",
            }],
            "users": [],
            "integrations": [],
            "notifications": {},
            "recovery": {},
            "auth": {},
        }
        redacted = ro.redacted_configuration(cfg)
        self.assertEqual(redacted["servers"][0]["password"], "<configured>")
        self.assertEqual(redacted["servers"][0]["api_key"], "<configured>")
        self.assertNotIn("secret", str(redacted))

    def test_client_list_exposes_identifiers_without_credentials(self):
        cfg = {"servers": [{
            "id": "desktop",
            "name": "Desktop",
            "base_url": "http://127.0.0.1:8080",
            "auth_method": "password",
            "username": "admin",
            "password": "secret",
            "enabled": True,
        }]}
        rows = ro.list_clients(cfg)
        self.assertEqual(rows[0]["id"], "desktop")
        self.assertNotIn("password", rows[0])
        self.assertNotIn("username", rows[0])

    def test_torrent_list_fetches_live_qbittorrent_state(self):
        cfg = {"servers": [{"id": "desktop", "base_url": "http://127.0.0.1:8080"}]}
        fake = mock.Mock()
        fake.torrents.return_value = [{
            "hash": "a" * 40,
            "name": "Example Torrent",
            "state": "downloading",
            "progress": 0.425,
        }]
        with mock.patch.object(ro, "RecoveryQBitClient", return_value=fake):
            rows = ro.list_torrents(cfg, "desktop")
        self.assertEqual(rows[0]["client_id"], "desktop")
        self.assertEqual(rows[0]["hash"], "a" * 40)
        self.assertEqual(rows[0]["progress"], 42.5)
        self.assertEqual(rows[0]["name"], "Example Torrent")

    def test_torrent_action_allowlist_rejects_destructive_actions_before_network(self):
        client = ro.RecoveryQBitClient({
            "base_url": "http://127.0.0.1:8080",
            "auth_method": "password",
            "username": "admin",
            "password": "secret",
        })
        with self.assertRaisesRegex(RuntimeError, "limited to start, stop, recheck, and reannounce"):
            client.action("delete", "a" * 40)
        self.assertEqual(ro.SAFE_TORRENT_ACTIONS, {"start", "stop", "recheck", "reannounce"})

    def test_jellyfin_task_listing_uses_configured_integration(self):
        cfg = {"integrations": [{"id": "jf", "type": "jellyfin"}]}
        task = {"id": "task-1", "name": "Scan media library"}
        with mock.patch.object(ro, "find_jellyfin_integration", return_value={"id": "jf"}) as find, \
                mock.patch.object(ro, "jellyfin_scheduled_tasks", return_value=[task]):
            rows = ro.list_jellyfin_tasks(cfg, "jf")
        find.assert_called_once_with(cfg, "jf")
        self.assertEqual(rows, [task])

    def test_history_events_reads_local_history_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            history = HistoryStore(path)
            history.event("desktop", "completed", "Example", "a" * 40, {"ok": True})
            rows = ro.history_events(path, 10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "completed")
        self.assertEqual(rows[0]["server_id"], "desktop")


if __name__ == "__main__":
    unittest.main()
