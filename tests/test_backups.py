from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from torrent_dashboard.backups import (
    backup_path,
    create_backup,
    import_backup,
    list_backups,
    restore_backup,
    validate_backup,
)


def config(title="Original"):
    return {
        "setup": {"complete": True},
        "recovery": {"key_hash": "pbkdf2_sha256$1$c2FsdA$ZGlnZXN0", "last4": "1234"},
        "dashboard": {"title": title},
        "users": [{"id": "admin", "username": "admin", "password_hash": "hash", "group": "administrator"}],
        "servers": [],
        "integrations": [],
    }


class BackupManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name)
        (self.app / "data" / "avatars").mkdir(parents=True)
        (self.app / "data" / "avatars" / "admin.webp").write_bytes(b"avatar")
        (self.app / "data" / "notification-custom.mp3").write_bytes(b"sound")
        (self.app / "data" / "updates" / "0.5.999").mkdir(parents=True)
        (self.app / "data" / "updates" / "0.5.999" / "staged.zip").write_bytes(b"update")
        (self.app / "data" / "update-status.json").write_text("{}", encoding="utf-8")
        (self.app / "data" / "release-integrity.json").write_text("{}", encoding="utf-8")
        (self.app / "data" / "recovery-backups").mkdir(parents=True)
        (self.app / "data" / "recovery-backups" / "config-old.json").write_text("{}", encoding="utf-8")
        db = sqlite3.connect(self.app / "data" / "torrent_desk.sqlite3")
        try:
            db.execute("CREATE TABLE sample(value TEXT)")
            db.execute("INSERT INTO sample VALUES('history')")
            db.commit()
        finally:
            db.close()
        (self.app / "config.json").write_text(json.dumps(config(), indent=2) + "\n", encoding="utf-8")
        self.lock = threading.RLock()

    def tearDown(self):
        self.temp.cleanup()

    def test_create_backup_contains_portable_state_and_excludes_ephemeral_files(self):
        item = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        archive = backup_path(self.app, item["name"])
        manifest = validate_backup(archive, current_version="0.5.147")
        self.assertEqual(manifest["application"], "torrent-dashboard")
        self.assertEqual(manifest["schema"], 1)
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
        self.assertIn("payload/config.json", names)
        self.assertIn("payload/data/torrent_desk.sqlite3", names)
        self.assertIn("payload/data/avatars/admin.webp", names)
        self.assertIn("payload/data/notification-custom.mp3", names)
        self.assertFalse(any(name.startswith("payload/data/updates/") for name in names))
        self.assertNotIn("payload/data/update-status.json", names)
        self.assertNotIn("payload/data/release-integrity.json", names)
        self.assertFalse(any(name.startswith("payload/data/backups/") for name in names))
        self.assertFalse(any(name.startswith("payload/data/recovery-backups/") for name in names))

    def test_import_and_restore_round_trip_preserves_backup_libraries(self):
        original = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        original_path = backup_path(self.app, original["name"])

        destination = self.app / "destination"
        (destination / "data").mkdir(parents=True)
        imported = import_backup(destination, "moved.tdbackup", original_path.read_bytes())
        self.assertEqual(imported["name"], "moved.tdbackup")
        self.assertEqual(len(list_backups(destination)), 1)

        changed = config("Changed")
        (self.app / "config.json").write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
        (self.app / "data" / "stale-state.txt").write_text("remove me", encoding="utf-8")
        result = restore_backup(
            self.app,
            original["name"],
            current_version="0.5.147",
            current_config=changed,
            history_lock=self.lock,
            validator=lambda: json.loads((self.app / "config.json").read_text(encoding="utf-8")),
        )
        restored = json.loads((self.app / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(restored["dashboard"]["title"], "Original")
        self.assertFalse((self.app / "data" / "stale-state.txt").exists())
        self.assertTrue((self.app / "data" / "recovery-backups" / "config-old.json").exists())
        self.assertTrue(backup_path(self.app, original["name"]).exists())
        self.assertEqual(result["safety_backup"]["kind"], "pre-restore")
        self.assertGreaterEqual(len(list_backups(self.app)), 2)

    def test_integrity_failure_is_rejected(self):
        item = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        source = backup_path(self.app, item["name"])
        corrupt = self.app / "corrupt.tdbackup"
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(corrupt, "w", zipfile.ZIP_DEFLATED) as rewritten:
            for info in original.infolist():
                data = original.read(info.filename)
                if info.filename == "payload/config.json":
                    data += b" "
                rewritten.writestr(info.filename, data)
        with self.assertRaisesRegex(RuntimeError, "integrity check failed|size mismatch"):
            validate_backup(corrupt, current_version="0.5.147")

    def test_restore_rejects_backup_from_newer_application_version(self):
        item = create_backup(self.app, "9.0.0", config(), history_lock=self.lock)
        with self.assertRaisesRegex(RuntimeError, "update this installation"):
            restore_backup(
                self.app,
                item["name"],
                current_version="0.5.147",
                current_config=config(),
                history_lock=self.lock,
            )


if __name__ == "__main__":
    unittest.main()
