"""Private state replacement must preserve the previous file on write failure."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from torrent_dashboard.persistence import atomic_write_bytes


class PersistenceTests(unittest.TestCase):
    def test_failed_replacement_preserves_previous_state_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_bytes(b"previous")
            with patch.object(Path, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    atomic_write_bytes(path, b"new")
            self.assertEqual(path.read_bytes(), b"previous")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    @unittest.skipIf(os.name == "nt", "POSIX file permissions")
    def test_secret_file_is_owner_only_after_creation_and_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            atomic_write_bytes(path, b"private")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.chmod(0o644)
            atomic_write_bytes(path, b"updated")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
