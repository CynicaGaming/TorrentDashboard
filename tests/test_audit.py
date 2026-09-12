import tempfile
from pathlib import Path
import unittest

from torrent_dashboard.audit import AuditStore, sanitize_details


class AuditStoreTests(unittest.TestCase):
    def test_sensitive_details_are_redacted(self):
        clean = sanitize_details({
            "client_ip": "127.0.0.1",
            "password": "secret",
            "nested": {"api_key": "value", "safe": "ok"},
        })
        self.assertEqual(clean["client_ip"], "127.0.0.1")
        self.assertEqual(clean["password"], "<redacted>")
        self.assertEqual(clean["nested"]["api_key"], "<redacted>")
        self.assertEqual(clean["nested"]["safe"], "ok")

    def test_record_filter_summary_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp_name:
            store = AuditStore(Path(temp_name) / "audit.sqlite3")
            store.record("login_success", actor="admin", client_ip="127.0.0.1", ts=2_000_000_000)
            store.record("login_failed", actor="bad", outcome="failure", client_ip="127.0.0.2", ts=1)
            rows = store.entries(limit=10, action="login_success")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["actor"], "admin")
            removed = store.cleanup(7)
            self.assertGreaterEqual(removed, 1)
            self.assertEqual(store.entries(limit=10, action="login_failed"), [])


if __name__ == "__main__":
    unittest.main()
