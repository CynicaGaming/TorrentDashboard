from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("torrent_dashboard_build_release", ROOT / "release_tools" / "build_release.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load release_tools/build_release.py")
build_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_release)


class ReleaseBuildTests(unittest.TestCase):
    def test_package_files_prunes_custom_output_and_excluded_trees(self):
        original_root = build_release.ROOT
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                build_release.ROOT = root

                (root / "src" / "torrent_dashboard").mkdir(parents=True)
                (root / "src" / "torrent_dashboard" / "dashboard.py").write_text("print('ok')\n", encoding="utf-8")
                (root / "release_tools").mkdir()
                (root / "release_tools" / "keep.py").write_text("pass\n", encoding="utf-8")

                (root / ".git" / "objects").mkdir(parents=True)
                (root / ".git" / "objects" / "ignored").write_text("ignored\n", encoding="utf-8")
                (root / "data").mkdir()
                (root / "data" / "ignored.json").write_text("{}\n", encoding="utf-8")

                output = root / "dist-test"
                output.mkdir()
                (output / "existing.zip").write_text("do not package\n", encoding="utf-8")

                files = {
                    path.relative_to(root).as_posix()
                    for path in build_release.package_files(output)
                }

                self.assertIn("src/torrent_dashboard/dashboard.py", files)
                self.assertIn("release_tools/keep.py", files)
                self.assertFalse(any(path.startswith(".git/") for path in files))
                self.assertFalse(any(path.startswith("data/") for path in files))
                self.assertFalse(any(path.startswith("dist-test/") for path in files))
        finally:
            build_release.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
