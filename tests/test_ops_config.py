import unittest

from torrent_dashboard.config import DEFAULT_CONFIG, normalize_config, public_config
from torrent_dashboard.ops_config import apply_operations_update


class OperationsConfigTests(unittest.TestCase):
    def test_defaults_and_public_secret_mask(self):
        config = normalize_config(DEFAULT_CONFIG)
        self.assertEqual(config["maintenance"]["retention"]["backup_count"], 14)
        config["backups"]["password"] = "correct horse battery staple"
        config["backups"]["encrypt"] = True
        public = public_config(config)
        self.assertEqual(public["backups"]["password"], "<configured>")
        self.assertTrue(public["backups"]["password_configured"])

    def test_update_preserves_configured_password(self):
        config = normalize_config(DEFAULT_CONFIG)
        config["backups"]["password"] = "correct horse battery staple"
        config["backups"]["encrypt"] = True
        updated = apply_operations_update(config, {"backups": {"password": "<configured>", "encrypt": True}})
        self.assertEqual(updated["backups"]["password"], "correct horse battery staple")

    def test_encryption_requires_password(self):
        config = normalize_config(DEFAULT_CONFIG)
        with self.assertRaisesRegex(RuntimeError, "password"):
            apply_operations_update(config, {"backups": {"encrypt": True}})

    def test_auto_update_window_and_retention_are_normalized(self):
        config = normalize_config(DEFAULT_CONFIG)
        updated = apply_operations_update(config, {
            "maintenance": {
                "auto_update": {"enabled": True, "window_start": "22:30", "window_end": "01:15", "pre_backup": True},
                "retention": {"history_days": 45, "audit_days": 120, "backup_count": 20, "update_days": 30},
            }
        })
        self.assertTrue(updated["maintenance"]["auto_update"]["enabled"])
        self.assertEqual(updated["maintenance"]["auto_update"]["window_start"], "22:30")
        self.assertEqual(updated["maintenance"]["retention"]["history_days"], 45)
        self.assertEqual(updated["dashboard"]["history_retention_days"], 45)


if __name__ == "__main__":
    unittest.main()
