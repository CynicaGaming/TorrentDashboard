from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemOperationsUiTests(unittest.TestCase):
    def test_ops_script_exposes_domain_settings_without_system_health(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        for marker in (
            "Backup protection", "Backup schedule", "Automatic updates", "Retention",
            "/api/retention/run", "schedule_frequency", "window_start", "backup_count",
        ):
            self.assertIn(marker, source)
        for marker in ("System health", "/api/system-health", "opsHealthSummary", "loadHealth", "Security audit"):
            self.assertNotIn(marker, source)

    def test_operational_settings_use_existing_settings_pages(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        settings = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("addCard('backups','opsBackupProtectionCard'", source)
        self.assertIn("addCard('backups','opsBackupScheduleCard'", source)
        self.assertIn("addCard('backups','opsRetentionCard'", source)
        self.assertIn("addCard('updates','opsAutomaticUpdatesCard'", source)
        self.assertNotIn("'users','system'", settings)
        self.assertIn("window.TDOps.saveBackupSettings", settings)
        self.assertIn("window.TDOps.saveUpdateSettings", settings)

    def test_multi_card_settings_pages_have_spacing(self):
        source = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
        self.assertIn('.settings-page>.settings-card+.settings-card{margin-top:12px}', source)

    def test_runtime_keeps_audit_and_retention_without_system_health_api(self):
        source = (ROOT / "src" / "torrent_dashboard" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('/static/ops.js?v=', source)
        self.assertNotIn('/api/system-health', source)
        self.assertIn('path == "/api/audit"', source)
        self.assertIn('path == "/api/retention/run"', source)


if __name__ == "__main__":
    unittest.main()
