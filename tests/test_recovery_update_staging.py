from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from torrent_dashboard.recovery_update_staging import READY_STATE, read_staged_update, stage_latest_update


class RecoveryUpdateStagingTests(unittest.TestCase):
    def _updater(self, version="0.5.154", digest=None):
        content = b"verified release bytes"
        digest = digest or hashlib.sha256(content).hexdigest()
        release = {
            "html_url": "https://github.com/example/project/releases/tag/v0.5.154",
            "published_at": "2026-09-11T00:00:00Z",
            "prerelease": True,
        }
        asset = {
            "name": f"Torrent-Dashboard-{version}.zip",
            "digest": f"sha256:{digest}",
            "browser_download_url": f"https://github.com/example/project/releases/download/v{version}/package.zip",
        }
        updater = SimpleNamespace()
        updater.installation_distribution = mock.Mock(return_value="source")
        updater.current_version = mock.Mock(return_value="0.5.153")
        updater.version_key = lambda value: tuple(int(part) for part in str(value).lstrip("v").split("."))
        updater.newest_release = mock.Mock(return_value=(version, release, asset))
        updater.release_asset_name = mock.Mock(return_value=asset["name"])

        def download(_url, destination):
            Path(destination).write_bytes(content)
            return hashlib.sha256(content).hexdigest()

        updater.download_file = mock.Mock(side_effect=download)

        def extract(_archive, destination):
            source = Path(destination) / f"Torrent-Dashboard-{version}"
            (source / "static").mkdir(parents=True)
            (source / "static" / "index.html").write_text("ok", encoding="utf-8")
            return source

        updater.extract_release = mock.Mock(side_effect=extract)
        updater.validate_staged_source = mock.Mock(return_value="source")
        updater.write_staged_release_info = mock.Mock(return_value={})
        return updater

    def test_download_retains_verified_release_for_later_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater = self._updater()
            state = stage_latest_update(target, "example/project", updater)
            self.assertEqual(state["state"], READY_STATE)
            self.assertEqual(state["version"], "0.5.154")
            self.assertTrue(Path(state["package"]).is_file())
            self.assertTrue(Path(state["source"]).is_dir())
            persisted = json.loads((target / "data" / "update-status.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["sha256"], state["sha256"])

    def test_up_to_date_release_does_not_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater = self._updater(version="0.5.153")
            state = stage_latest_update(target, "example/project", updater)
            self.assertEqual(state["state"], "upToDate")
            updater.download_file.assert_not_called()

    def test_digest_mismatch_is_rejected_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater = self._updater(digest="0" * 64)
            with self.assertRaisesRegex(RuntimeError, "SHA-256 verification failed"):
                stage_latest_update(target, "example/project", updater)
            state = json.loads((target / "data" / "update-status.json").read_text(encoding="utf-8"))
            self.assertEqual(state["state"], "failed")

    def test_retained_package_is_rehashed_before_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater = self._updater()
            state = stage_latest_update(target, "example/project", updater)
            ready = read_staged_update(target, updater, "0.5.154")
            self.assertEqual(ready["state"], READY_STATE)
            Path(state["package"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "SHA-256 recheck"):
                read_staged_update(target, updater, "0.5.154")

    def test_requested_version_must_match_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater = self._updater()
            stage_latest_update(target, "example/project", updater)
            with self.assertRaisesRegex(RuntimeError, "version changed"):
                read_staged_update(target, updater, "0.5.155")


if __name__ == "__main__":
    unittest.main()
