import json
import tempfile
import unittest
from pathlib import Path

from torrent_dashboard import updater


class UpdaterDistributionTests(unittest.TestCase):
    def test_windows_package_managed_roots_replace_stale_files_and_roll_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            backup = root / "backup"
            (source / "_internal").mkdir(parents=True)
            (source / "static").mkdir()
            target.mkdir()
            (target / "_internal").mkdir()
            (target / "static").mkdir()
            (target / "data").mkdir()

            info = {
                "distribution": "windows-x64",
                "version": "0.5.145",
                "managed_roots": [
                    "Dashboard.exe", "Recovery.exe", "Updater.exe", "_internal", "static", "package-info.json"
                ],
            }
            (source / "package-info.json").write_text(json.dumps(info), encoding="utf-8")
            for name in ("Dashboard.exe", "Recovery.exe", "Updater.exe"):
                (source / name).write_bytes(b"new-" + name.encode())
                (target / name).write_bytes(b"old-" + name.encode())
            (source / "_internal" / "new.dll").write_bytes(b"new")
            (source / "static" / "index.html").write_text("new", encoding="utf-8")
            (target / "_internal" / "stale.dll").write_bytes(b"stale")
            (target / "static" / "index.html").write_text("old", encoding="utf-8")
            (target / "config.json").write_text("preserve", encoding="utf-8")
            (target / "data" / "state.txt").write_text("preserve", encoding="utf-8")

            state = updater.apply_update(source, target, backup)
            self.assertFalse((target / "_internal" / "stale.dll").exists())
            self.assertEqual((target / "_internal" / "new.dll").read_bytes(), b"new")
            self.assertEqual((target / "config.json").read_text(), "preserve")
            self.assertEqual((target / "data" / "state.txt").read_text(), "preserve")

            updater.rollback(target, backup, state)
            self.assertEqual((target / "Dashboard.exe").read_bytes(), b"old-Dashboard.exe")
            self.assertTrue((target / "_internal" / "stale.dll").is_file())
            self.assertFalse((target / "_internal" / "new.dll").exists())
            self.assertEqual((target / "static" / "index.html").read_text(), "old")

    def test_src_layout_can_retire_legacy_python_tree_and_roll_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            backup = root / "backup"
            package = source / "src" / "torrent_dashboard"
            package.mkdir(parents=True)
            (source / "static").mkdir()
            target.mkdir()
            (target / "torrent_dashboard").mkdir()

            info = {
                "distribution": "source",
                "layout": "src",
                "version": "0.5.146",
                "migration_remove": ["dashboard.py", "updater.py", "recovery_tool.py", "torrent_dashboard"],
            }
            (source / "package-info.json").write_text(json.dumps(info), encoding="utf-8")
            (package / "dashboard.py").write_text('VERSION = "0.5.146"\n', encoding="utf-8")
            (package / "updater.py").write_text("VALUE = 1\n", encoding="utf-8")
            (source / "static" / "index.html").write_text("new", encoding="utf-8")
            (target / "dashboard.py").write_text('VERSION = "0.5.145"\n', encoding="utf-8")
            (target / "updater.py").write_text("legacy\n", encoding="utf-8")
            (target / "recovery_tool.py").write_text("legacy\n", encoding="utf-8")
            (target / "torrent_dashboard" / "legacy.py").write_text("legacy\n", encoding="utf-8")

            self.assertEqual(updater.detect_release_distribution(source), "source")
            state = updater.apply_update(source, target, backup)
            self.assertFalse((target / "dashboard.py").exists())
            self.assertFalse((target / "torrent_dashboard").exists())
            self.assertTrue((target / "src" / "torrent_dashboard" / "dashboard.py").is_file())

            updater.rollback(target, backup, state)
            self.assertTrue((target / "dashboard.py").is_file())
            self.assertTrue((target / "torrent_dashboard" / "legacy.py").is_file())
            self.assertFalse((target / "src" / "torrent_dashboard" / "dashboard.py").exists())


if __name__ == "__main__":
    unittest.main()
