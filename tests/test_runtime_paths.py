import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from torrent_dashboard import runtime_paths


class RuntimePathTests(unittest.TestCase):
    def test_source_app_dir_is_repository_root(self):
        self.assertTrue((runtime_paths.app_dir() / "src" / "torrent_dashboard" / "dashboard.py").is_file())

    def test_frozen_app_dir_uses_executable_parent(self):
        fake = Path(tempfile.gettempdir()) / "td-test" / "Dashboard.exe"
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", str(fake)):
            self.assertEqual(runtime_paths.app_dir(), fake.parent.resolve())

    def test_dashboard_command_prefers_packaged_executable_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Dashboard.exe").write_bytes(b"MZ")
            with mock.patch.object(runtime_paths.os, "name", "nt"):
                command = runtime_paths.dashboard_command(root)
            self.assertEqual(Path(command[0]), root / "Dashboard.exe")
            self.assertEqual(command[-1], "--no-browser")

    def test_updater_command_prefers_packaged_executable_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Updater.exe").write_bytes(b"MZ")
            with mock.patch.object(runtime_paths.os, "name", "nt"):
                command = runtime_paths.updater_command(root)
            self.assertEqual(command, [str(root / "Updater.exe")])


if __name__ == "__main__":
    unittest.main()
