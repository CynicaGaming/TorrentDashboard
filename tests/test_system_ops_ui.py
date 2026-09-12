from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemOperationsUiTests(unittest.TestCase):
    def test_ops_script_exposes_required_surfaces(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        for marker in (
            "System health", "Backup protection and schedule", "Automatic updates",
            "Retention", "Security audit", "/api/system-health", "/api/audit",
            "/api/retention/run", "schedule_frequency", "window_start", "audit_days",
        ):
            self.assertIn(marker, source)

    def test_main_settings_controller_accepts_system_page(self):
        source = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("'users','system']", source)
        self.assertIn("activate(btn.dataset.settingsPage)", source)

    def test_system_status_rows_follow_notification_layout_contract(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        self.assertIn('class="notification-dot"', source)
        self.assertIn('class="notification-copy"', source)
        self.assertIn('id="opsSavePolicy" type="button">Save</button>', source)
        self.assertNotIn('>Save system settings</button>', source)

    def test_runtime_injects_ops_script_into_application_shell(self):
        source = (ROOT / "src" / "torrent_dashboard" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('/static/ops.js?v=', source)
        self.assertIn('path == "/api/system-health"', source)
        self.assertIn('path == "/api/audit"', source)
        self.assertIn('path == "/api/retention/run"', source)


if __name__ == "__main__":
    unittest.main()
