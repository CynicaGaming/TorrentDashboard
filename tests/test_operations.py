from datetime import datetime
import tempfile
from pathlib import Path
import unittest

from torrent_dashboard.operations import (
    automatic_update_due,
    prune_backups,
    prune_update_artifacts,
    scheduled_backup_due,
    within_maintenance_window,
)


class OperationsTests(unittest.TestCase):
    def test_maintenance_window_supports_overnight_ranges(self):
        self.assertTrue(within_maintenance_window(datetime(2026, 1, 1, 23, 30), "23:00", "02:00"))
        self.assertTrue(within_maintenance_window(datetime(2026, 1, 2, 1, 30), "23:00", "02:00"))
        self.assertFalse(within_maintenance_window(datetime(2026, 1, 2, 12, 0), "23:00", "02:00"))

    def test_daily_backup_runs_once_per_day_at_configured_hour(self):
        policy = {"schedule_enabled": True, "schedule_frequency": "daily", "schedule_hour": 3, "schedule_weekday": 0}
        now = datetime(2026, 9, 11, 3, 5)
        self.assertTrue(scheduled_backup_due(policy, {}, now))
        state = {"last_backup_ts": int(datetime(2026, 9, 11, 3, 1).timestamp())}
        self.assertFalse(scheduled_backup_due(policy, state, now))

    def test_auto_update_runs_once_per_window_day(self):
        policy = {"enabled": True, "window_start": "03:00", "window_end": "05:00"}
        now = datetime(2026, 9, 11, 4, 0)
        self.assertTrue(automatic_update_due(policy, {}, now))
        self.assertFalse(automatic_update_due(policy, {"last_auto_update_day": "2026-09-11"}, now))

    def test_prune_backups_keeps_newest_count(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            directory = root / "data" / "backups"
            directory.mkdir(parents=True)
            for index in range(5):
                path = directory / f"backup-{index}.tdbackup"
                path.write_bytes(b"x")
                path.touch()
                # Deterministic ordering by mtime.
                path.chmod(0o600)
                import os
                os.utime(path, (100 + index, 100 + index))
            removed = prune_backups(root, 2)
            self.assertEqual(len(removed), 3)
            self.assertEqual(len(list(directory.glob("*.tdbackup"))), 2)

    def test_prune_update_artifacts_preserves_active_version(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            old = root / "0.5.100"
            keep = root / "0.5.154"
            old.mkdir(); keep.mkdir()
            import os, time
            stale = time.time() - 40 * 86400
            os.utime(old, (stale, stale)); os.utime(keep, (stale, stale))
            removed = prune_update_artifacts(root, 14, protected_versions={"0.5.154"})
            self.assertIn("0.5.100", removed)
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()
