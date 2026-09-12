import tempfile
from pathlib import Path
import unittest

from torrent_dashboard.backup_crypto import decrypt_file, encrypt_file, is_encrypted_backup


class BackupCryptoTests(unittest.TestCase):
    def test_round_trip_and_authentication(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "plain.bin"
            encrypted = root / "encrypted.tdbackup"
            restored = root / "restored.bin"
            source.write_bytes((b"torrent-dashboard\x00" * 10000) + b"end")
            encrypt_file(source, encrypted, "correct horse battery staple", iterations=100_000)
            self.assertTrue(is_encrypted_backup(encrypted))
            decrypt_file(encrypted, restored, "correct horse battery staple")
            self.assertEqual(source.read_bytes(), restored.read_bytes())

    def test_wrong_password_and_tamper_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "plain.bin"
            encrypted = root / "encrypted.tdbackup"
            target = root / "target.bin"
            source.write_bytes(b"sensitive backup payload")
            encrypt_file(source, encrypted, "correct horse battery staple", iterations=100_000)
            with self.assertRaises(RuntimeError):
                decrypt_file(encrypted, target, "wrong password value")
            self.assertFalse(target.exists())
            payload = bytearray(encrypted.read_bytes())
            payload[-40] ^= 0x01
            encrypted.write_bytes(payload)
            with self.assertRaises(RuntimeError):
                decrypt_file(encrypted, target, "correct horse battery staple")
            self.assertFalse(target.exists())

    def test_short_password_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "plain.bin"
            source.write_bytes(b"x")
            with self.assertRaisesRegex(RuntimeError, "at least 12"):
                encrypt_file(source, root / "encrypted.tdbackup", "short", iterations=100_000)


if __name__ == "__main__":
    unittest.main()
