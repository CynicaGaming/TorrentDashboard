import unittest

from torrent_dashboard.release_selection import select_updater_ready_release


class ReleaseSelectionTests(unittest.TestCase):
    def release(self, version, *, distribution="source", digest=True, draft=False):
        name = (
            f"TorrentDashboard-Windows-{version}-x64.zip"
            if distribution == "windows-x64"
            else f"Torrent-Dashboard-{version}.zip"
        )
        asset = {"name": name, "url": "https://api.github.com/repos/example/project/releases/assets/1"}
        if digest:
            asset["digest"] = "sha256:" + ("a" * 64)
        return {"tag_name": "v" + version, "draft": draft, "assets": [asset]}

    def test_skips_incomplete_newest_release(self):
        releases = [
            self.release("0.5.155", distribution="source"),
            self.release("0.5.154", distribution="windows-x64"),
        ]
        selected = select_updater_ready_release(releases, "windows-x64", current_version="0.5.153")
        self.assertEqual(selected["tag_name"], "v0.5.154")

    def test_skips_assets_without_finalized_digest(self):
        releases = [
            self.release("0.5.155", distribution="windows-x64", digest=False),
            self.release("0.5.154", distribution="windows-x64"),
        ]
        selected = select_updater_ready_release(releases, "windows-x64", current_version="0.5.153")
        self.assertEqual(selected["tag_name"], "v0.5.154")

    def test_ignores_draft_and_non_newer_releases(self):
        releases = [
            self.release("0.5.156", distribution="source", draft=True),
            self.release("0.5.155", distribution="source"),
        ]
        self.assertIsNone(select_updater_ready_release(releases, "source", current_version="0.5.155"))


if __name__ == "__main__":
    unittest.main()
