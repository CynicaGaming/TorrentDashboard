from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeEntryContractTests(unittest.TestCase):
    def test_runtime_composes_dashboard_and_installs_operations_extensions(self):
        path = ROOT / "src" / "torrent_dashboard" / "runtime.py"
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        self.assertIn("from . import dashboard as core", source)
        self.assertIn("def install_runtime_extensions", source)
        self.assertIn("core.fetch_update_release = _fetch_update_release", source)
        self.assertIn("core.create_backup = _create_backup", source)
        self.assertIn("core.Handler = OperationsHandler", source)

    def test_launchers_use_runtime_entry(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        start = (ROOT / "Start Dashboard.bat").read_text(encoding="utf-8")
        spec = (ROOT / "release_tools" / "windows.spec").read_text(encoding="utf-8")
        release_builder = (ROOT / "release_tools" / "build_release.py").read_text(encoding="utf-8")
        runtime_paths = (ROOT / "src" / "torrent_dashboard" / "runtime_paths.py").read_text(encoding="utf-8")
        self.assertIn('torrent-dashboard = "torrent_dashboard.runtime:main"', pyproject)
        self.assertIn("-m torrent_dashboard.runtime", start)
        self.assertIn('dashboard = analysis("runtime.py")', spec)
        self.assertIn("from torrent_dashboard.runtime import main", release_builder)
        self.assertIn('target / "src" / "torrent_dashboard" / "runtime.py"', runtime_paths)


if __name__ == "__main__":
    unittest.main()
