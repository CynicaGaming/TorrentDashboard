import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeEntryContractTests(unittest.TestCase):
    def test_runtime_composes_dashboard_without_direct_import_statement(self):
        path = ROOT / "src" / "torrent_dashboard" / "runtime.py"
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        tree = ast.parse(source)
        self.assertIn('importlib.import_module("torrent_dashboard.dashboard")', source)
        direct = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "torrent_dashboard.dashboard":
                direct.append(node.lineno)
        self.assertEqual(direct, [])

    def test_launchers_use_runtime_entry(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        start = (ROOT / "Start Dashboard.bat").read_text(encoding="utf-8")
        spec = (ROOT / "release_tools" / "windows.spec").read_text(encoding="utf-8")
        self.assertIn('torrent-dashboard = "torrent_dashboard.runtime:main"', pyproject)
        self.assertIn("-m torrent_dashboard.runtime", start)
        self.assertIn('dashboard = analysis("runtime.py")', spec)


if __name__ == "__main__":
    unittest.main()
