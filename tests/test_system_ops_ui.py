from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemOperationsUiTests(unittest.TestCase):
    def test_ops_script_exposes_reorganized_surfaces(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        for marker in (
            "System health", "Backup protection", "Backup schedule", "Automatic updates",
            "Retention", "/api/system-health", "/api/retention/run", "schedule_frequency",
            "window_start", "backup_count",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("Security audit", source)
        self.assertNotIn("opsAuditList", source)
        self.assertNotIn("/api/audit?", source)

    def test_operational_settings_use_existing_settings_pages(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        settings = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("addCard('backups','opsBackupProtectionCard'", source)
        self.assertIn("addCard('backups','opsBackupScheduleCard'", source)
        self.assertIn("addCard('backups','opsRetentionCard'", source)
        self.assertIn("addCard('updates','opsAutomaticUpdatesCard'", source)
        self.assertIn("'clients','backups','updates','notifications'", settings)
        self.assertIn("window.TDOps.saveBackupSettings", settings)
        self.assertIn("window.TDOps.saveUpdateSettings", settings)

    def test_system_health_uses_human_readable_labels(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        self.assertIn("dashboard:'Torrent Dashboard'", source)
        self.assertIn("disk:'Disk space'", source)
        self.assertIn("clients:'qBittorrent clients'", source)
        self.assertIn("stateLabel(health.state", source)
        self.assertIn('class="notification-dot"', source)
        self.assertIn('class="notification-copy"', source)

    def test_multi_card_settings_pages_have_spacing(self):
        source = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
        self.assertIn('.settings-page>.settings-card+.settings-card{margin-top:12px}', source)

    def test_runtime_keeps_durable_audit_api_without_duplicate_ui(self):
        source = (ROOT / "src" / "torrent_dashboard" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('/static/ops.js?v=', source)
        self.assertIn('path == "/api/system-health"', source)
        self.assertIn('path == "/api/audit"', source)
        self.assertIn('path == "/api/retention/run"', source)


if __name__ == "__main__":
    unittest.main()
