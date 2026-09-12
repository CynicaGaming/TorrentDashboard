import json
import tempfile
from pathlib import Path
import unittest
import zipfile

from torrent_dashboard.backup_crypto import is_encrypted_backup
from torrent_dashboard.backup_service import create_backup, list_backups
from torrent_dashboard.config import normalize_config


class ManagedBackupTests(unittest.TestCase):
    def test_encrypted_backup_excludes_encryption_password_from_payload(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root=Path(temp_name)
            config=normalize_config({"setup":{"complete":True}})
            config["backups"]["encrypt"]=True
            config["backups"]["password"]="correct horse battery staple"
            item=create_backup(root,"0.5.154",config,password=config["backups"]["password"])
            path=root/"data"/"backups"/item["name"]
            self.assertTrue(is_encrypted_backup(path))
            self.assertTrue(item["encrypted"])
            listed=list_backups(root,password=config["backups"]["password"])
            self.assertEqual(listed[0]["name"],item["name"])
            self.assertFalse(listed[0].get("locked",False))

    def test_plain_backup_does_not_embed_stored_backup_password(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root=Path(temp_name)
            config=normalize_config({"setup":{"complete":True}})
            config["backups"]["encrypt"]=False
            config["backups"]["password"]="correct horse battery staple"
            item=create_backup(root,"0.5.154",config,password="")
            path=root/"data"/"backups"/item["name"]
            with zipfile.ZipFile(path) as archive:
                payload=json.loads(archive.read("payload/config.json").decode("utf-8"))
            self.assertEqual((payload.get("backups") or {}).get("password"),"")


if __name__=="__main__":
    unittest.main()
