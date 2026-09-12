import json
import tempfile
from pathlib import Path
import unittest
import zipfile

from torrent_dashboard.backup_crypto import decrypt_file, is_encrypted_backup
from torrent_dashboard.backup_service import create_backup, list_backups
from torrent_dashboard.config import normalize_config
from torrent_dashboard.ops_config import normalize_operations_config


class ManagedBackupTests(unittest.TestCase):
    def config(self):
        return normalize_operations_config(normalize_config({"setup": {"complete": True}}))

    def test_encrypted_backup_excludes_encryption_password_from_payload(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            config = self.config()
            password = "correct horse battery staple"
            config["backups"]["encrypt"] = True
            config["backups"]["password"] = password
            item = create_backup(root, "0.5.155", config, password=password)
            path = root / "data" / "backups" / item["name"]
            self.assertTrue(is_encrypted_backup(path))
            self.assertTrue(item["encrypted"])
            listed = list_backups(root, password=password)
            self.assertEqual(listed[0]["name"], item["name"])
            self.assertFalse(listed[0].get("locked", False))

            decrypted = root / "decrypted.tdbackup"
            decrypt_file(path, decrypted, password)
            with zipfile.ZipFile(decrypted) as archive:
                payload = json.loads(archive.read("payload/config.json").decode("utf-8"))
            self.assertEqual((payload.get("backups") or {}).get("password"), "")

    def test_plain_backup_does_not_embed_stored_backup_password(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            config = self.config()
            config["backups"]["encrypt"] = False
            config["backups"]["password"] = "correct horse battery staple"
            item = create_backup(root, "0.5.155", config, password="")
            path = root / "data" / "backups" / item["name"]
            with zipfile.ZipFile(path) as archive:
                payload = json.loads(archive.read("payload/config.json").decode("utf-8"))
            self.assertEqual((payload.get("backups") or {}).get("password"), "")


if __name__ == "__main__":
    unittest.main()
