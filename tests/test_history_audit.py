import tempfile
from pathlib import Path
import unittest

from torrent_dashboard.history import HistoryStore


class HistoryAuditIntegrationTests(unittest.TestCase):
    def test_security_events_are_mirrored_and_redacted(self):
        with tempfile.TemporaryDirectory() as temp_name:
            store = HistoryStore(Path(temp_name) / "history.sqlite3")
            store.event(
                "dashboard",
                "login_failed",
                "admin",
                "",
                {"client_ip": "127.0.0.1", "password": "never-store-this", "reason": "bad credentials"},
            )
            rows = store.audit.entries(limit=10, action="login_failed")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["actor"], "admin")
            self.assertEqual(rows[0]["client_ip"], "127.0.0.1")
            self.assertEqual(rows[0]["outcome"], "failure")
            self.assertEqual(rows[0]["details"]["password"], "<redacted>")
            self.assertEqual(rows[0]["details"]["reason"], "bad credentials")

    def test_non_security_torrent_events_are_not_mirrored(self):
        with tempfile.TemporaryDirectory() as temp_name:
            store = HistoryStore(Path(temp_name) / "history.sqlite3")
            store.event("client-a", "completed", "Example", "hash", {})
            self.assertEqual(store.audit.entries(limit=10), [])


if __name__ == "__main__":
    unittest.main()
