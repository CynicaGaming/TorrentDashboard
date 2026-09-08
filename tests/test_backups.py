from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import stat
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from torrent_dashboard import backups
from torrent_dashboard.backups import (
    backup_path,
    create_backup,
    delete_backup,
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

    def test_delete_backup_removes_only_named_local_archive(self):
        item = create_backup(self.app, "0.5.151", config(), history_lock=self.lock)
        path = backup_path(self.app, item["name"])
        outside = self.app / "outside.tdbackup"
        outside.write_bytes(b"outside")
        self.assertEqual(delete_backup(self.app, item["name"]), item["name"])
        self.assertFalse(path.exists())
        self.assertTrue(outside.exists())
        self.assertEqual(list_backups(self.app), [])
        with self.assertRaisesRegex(RuntimeError, "not found"):
            delete_backup(self.app, "../outside.tdbackup")
        self.assertTrue(outside.exists())

    def test_create_backup_contains_configuration_only_and_excludes_identity(self):
        source = config()
        source["servers"] = [{"id": "client", "name": "Desktop", "url": "http://127.0.0.1:8080", "password": "client-secret"}]
        source["integrations"] = [{"id": "sonarr", "type": "sonarr", "name": "Sonarr", "url": "http://sonarr", "api_key": "integration-secret"}]
        source.setdefault("auth", {})["username"] = "admin"
        source["auth"]["password_hash"] = "legacy-user-hash"
        item = create_backup(self.app, "0.5.149", source, history_lock=self.lock)
        archive = backup_path(self.app, item["name"])
        manifest = validate_backup(archive, current_version="0.5.149")
        self.assertEqual(manifest["scope"], ["settings", "integrations", "clients"])
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
            portable = json.loads(zipped.read("payload/config.json"))
        self.assertEqual(names, {"backup-manifest.json", "payload/config.json"})
        self.assertNotIn("users", portable)
        self.assertNotIn("recovery", portable)
        self.assertNotIn("username", portable.get("auth", {}))
        self.assertNotIn("password_hash", portable.get("auth", {}))
        self.assertEqual(portable["servers"][0]["password"], "client-secret")
        self.assertEqual(portable["integrations"][0]["api_key"], "integration-secret")
    def test_import_and_restore_round_trip_preserves_backup_libraries(self):
        original_config = config()
        original_config["servers"] = [{"id": "original-client", "name": "Original", "url": "http://original"}]
        original_config["integrations"] = [{"id": "original-integration", "type": "sonarr", "name": "Sonarr", "url": "http://original-sonarr"}]
        original = create_backup(self.app, "0.5.149", original_config, history_lock=self.lock)
        original_path = backup_path(self.app, original["name"])
        destination = self.app / "destination"
        (destination / "data").mkdir(parents=True)
        imported = import_backup(destination, "moved.tdbackup", original_path.read_bytes())
        self.assertEqual(imported["name"], "moved.tdbackup")
        changed = config("Changed")
        changed["users"][0]["username"] = "destination-admin"
        changed["users"][0]["password_hash"] = "destination-user-hash"
        changed["recovery"] = {"key_hash": "destination-recovery-hash", "last4": "9876"}
        (self.app / "config.json").write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
        (self.app / "data" / "stale-state.txt").write_text("preserve me", encoding="utf-8")
        result = restore_backup(self.app, original["name"], current_version="0.5.149", current_config=changed, history_lock=self.lock, validator=lambda: json.loads((self.app / "config.json").read_text(encoding="utf-8")))
        restored = json.loads((self.app / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(restored["dashboard"]["title"], "Original")
        self.assertEqual(restored["servers"], original_config["servers"])
        self.assertEqual(restored["integrations"], original_config["integrations"])
        self.assertEqual(restored["users"], changed["users"])
        self.assertEqual(restored["recovery"], changed["recovery"])
        self.assertTrue((self.app / "data" / "stale-state.txt").exists())
        self.assertTrue((self.app / "data" / "recovery-backups" / "config-old.json").exists())
        self.assertEqual(result["safety_backup"]["kind"], "pre-restore")
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


    def archive(self, payload=None, version="0.5.147", extra=None):
        payload = payload or {"payload/config.json": json.dumps(config()).encode()}
        manifest = {
            "application": "torrent-dashboard", "schema": 1, "source_version": version,
            "files": [{"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                      for name, data in payload.items()],
        }
        path = self.app / "crafted.tdbackup"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("backup-manifest.json", json.dumps(manifest))
            for name, data in payload.items():
                archive.writestr(name, data)
            if extra:
                archive.writestr(*extra)
        return path

    def test_all_runtime_data_is_excluded_from_new_portable_backups(self):
        item = create_backup(self.app, "0.5.149", config())
        with zipfile.ZipFile(backup_path(self.app, item["name"])) as archive:
            self.assertEqual(set(archive.namelist()), {"backup-manifest.json", "payload/config.json"})
    def test_invalid_creation_never_publishes_a_backup(self):
        invalid = config()
        invalid["setup"]["complete"] = False
        with self.assertRaisesRegex(RuntimeError, "completed"):
            create_backup(self.app, "0.5.149", invalid)
        self.assertEqual(list_backups(self.app), [])
        self.assertEqual(list((self.app / "data" / "backups").iterdir()), [])
    def test_unsafe_and_windows_ambiguous_archive_paths_are_rejected(self):
        for suffix in ("../escape", "C:/escape", "name:stream", "CON", "nul.txt", "COM¹.log",
                       "folder./file", "trailing ", "double//slash", "./file", "bad\\name", "line\nname"):
            with self.subTest(suffix=suffix):
                payload = {"payload/config.json": json.dumps(config()).encode(), "payload/data/" + suffix: b"test"}
                with self.assertRaisesRegex(RuntimeError, "path"):
                    validate_backup(self.archive(payload))

    def test_case_collisions_and_file_directory_conflicts_are_rejected(self):
        for names in (("Data", "data"), ("folder", "folder/file"), ("FOLDER", "folder/file")):
            with self.subTest(names=names):
                payload = {"payload/config.json": json.dumps(config()).encode()}
                payload.update({"payload/data/" + name: b"test" for name in names})
                with self.assertRaisesRegex(RuntimeError, "colliding|conflicting"):
                    validate_backup(self.archive(payload))

    def test_unlisted_members_and_special_files_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "manifest"):
            validate_backup(self.archive(extra=("unlisted.txt", b"extra")))
        link = zipfile.ZipInfo("payload/data/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaisesRegex(RuntimeError, "link"):
            validate_backup(self.archive(extra=(link, b"target")))

    def test_malformed_version_cannot_bypass_restore_compatibility(self):
        for version in ("unknown", "999bad", "", "1.2"):
            with self.subTest(version=version), self.assertRaisesRegex(RuntimeError, "version"):
                validate_backup(self.archive(version=version), current_version="0.5.147")

    def test_manifest_and_expanded_payload_limits(self):
        path = self.archive()
        with patch.object(backups, "MAX_MANIFEST_BYTES", 1), self.assertRaisesRegex(RuntimeError, "manifest"):
            validate_backup(path)
        path = self.archive({"payload/config.json": json.dumps(config()).encode(), "payload/data/large": b"0" * 100000})
        with patch.object(backups, "MAX_BACKUP_BYTES", 2000), self.assertRaisesRegex(RuntimeError, "expands"):
            validate_backup(path)

    def test_same_name_imports_do_not_overwrite_one_another(self):
        content = self.archive().read_bytes()
        with ThreadPoolExecutor(max_workers=4) as pool:
            items = list(pool.map(lambda _: import_backup(self.app, "shared.tdbackup", content), range(4)))
        self.assertEqual(len({item["name"] for item in items}), 4)
        for item in items:
            self.assertEqual(backup_path(self.app, item["name"]).read_bytes(), content)

    def test_cross_install_restore_preserves_destination_identity_and_runtime_data(self):
        source_config = config()
        source_config["users"][0]["username"] = "source-admin"
        source_config["recovery"] = {"key_hash": "source-recovery", "last4": "1111"}
        source_config["servers"] = [{"id": "source-client", "name": "Source", "url": "http://source"}]
        original = create_backup(self.app, "0.5.149", source_config)
        content = backup_path(self.app, original["name"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            destination_config = config("Destination")
            destination_config["users"][0]["username"] = "destination-admin"
            destination_config["users"][0]["password_hash"] = "destination-user-hash"
            destination_config["recovery"] = {"key_hash": "destination-recovery", "last4": "9999"}
            (destination / "config.json").write_text(json.dumps(destination_config))
            (destination / "data").mkdir()
            (destination / "data" / "destination.txt").write_text("must remain local")
            imported = import_backup(destination, "portable.tdbackup", content)
            result = restore_backup(destination, imported["name"], current_version="0.5.149", current_config=destination_config)
            restored = json.loads((destination / "config.json").read_text())
            self.assertEqual(restored["dashboard"]["title"], "Original")
            self.assertEqual(restored["servers"], source_config["servers"])
            self.assertEqual(restored["users"], destination_config["users"])
            self.assertEqual(restored["recovery"], destination_config["recovery"])
            self.assertTrue((destination / "data" / "destination.txt").is_file())
            restore_backup(destination, result["safety_backup"]["name"], current_version="0.5.149", current_config=restored)
            rolled_back = json.loads((destination / "config.json").read_text())
            self.assertEqual(rolled_back["dashboard"]["title"], "Destination")
            self.assertEqual(rolled_back["users"], destination_config["users"])
            self.assertEqual(rolled_back["recovery"], destination_config["recovery"])
    def test_legacy_backup_identity_and_data_are_ignored_on_restore(self):
        legacy = config("Legacy source")
        legacy["users"][0]["username"] = "legacy-admin"
        legacy["recovery"] = {"key_hash": "legacy-recovery", "last4": "1111"}
        payload = {"payload/config.json": json.dumps(legacy).encode(), "payload/data/legacy-state.txt": b"legacy data"}
        source = self.archive(payload=payload, version="0.5.149")
        imported = import_backup(self.app, "legacy.tdbackup", source.read_bytes(), current_version="0.5.149")
        current = config("Current destination")
        current["users"][0]["username"] = "current-admin"
        current["recovery"] = {"key_hash": "current-recovery", "last4": "2222"}
        (self.app / "data" / "current-state.txt").write_text("keep", encoding="utf-8")
        restore_backup(self.app, imported["name"], current_version="0.5.149", current_config=current)
        restored = json.loads((self.app / "config.json").read_text())
        self.assertEqual(restored["dashboard"]["title"], "Legacy source")
        self.assertEqual(restored["users"], current["users"])
        self.assertEqual(restored["recovery"], current["recovery"])
        self.assertTrue((self.app / "data" / "current-state.txt").exists())
        self.assertFalse((self.app / "data" / "legacy-state.txt").exists())

    def test_failed_restore_rolls_back_previous_state(self):
        item = create_backup(self.app, "0.5.147", config())
        changed = config("Latest destination")
        (self.app / "config.json").write_text(json.dumps(changed))
        with self.assertRaisesRegex(RuntimeError, "previous state was restored"):
            restore_backup(self.app, item["name"], current_version="0.5.147", current_config=changed,
                           validator=lambda: (_ for _ in ()).throw(RuntimeError("invalid restored state")))
        self.assertEqual(json.loads((self.app / "config.json").read_text()), changed)
        self.assertTrue(any(row["kind"] == "pre-restore" for row in list_backups(self.app)))

    def test_failed_rollback_reports_recovery_backup_instead_of_success(self):
        item = create_backup(self.app, "0.5.147", config())
        with patch.object(backups, "_apply_payload", side_effect=OSError("filesystem unavailable")):
            with self.assertRaisesRegex(RuntimeError, "automatic rollback also failed.*PreRestore"):
                restore_backup(self.app, item["name"], current_version="0.5.147", current_config=config())


if __name__ == "__main__":
    unittest.main()
