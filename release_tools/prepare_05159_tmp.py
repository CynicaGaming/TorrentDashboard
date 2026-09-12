from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.159"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not locate {label}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not locate {label}")
    return text


# Remove the System health settings surface and all browser-side health presentation code.
ops = read("static/ops.js")
ops = ops.replace("  const pageId='system';\n", "", 1)
ops = sub_once(ops, r"  const COMPONENT_LABELS=\{.*?  \};\n\n", "", "component label table")
ops = sub_once(ops, r"  function escapeHtml\(value=''\) \{.*?  \}\n", "", "escapeHtml helper")
ops = sub_once(ops, r"  function humanizeIdentifier\(value=''\) \{.*?  function componentLabel\(value=''\) \{.*?\}\n\n", "", "health presentation helpers")
ops = sub_once(ops, r"  function buildNavigation\(\) \{.*?  \}\n\n", "", "System health navigation builder")
ops = sub_once(ops, r"  function buildSystemPage\(\) \{.*?  \}\n\n", "", "System health page builder")
ops = replace_once(
    ops,
    "  function buildSurfaces() {\n    buildNavigation();buildSystemPage();buildBackupCards();buildUpdateCard();\n  }",
    "  function buildSurfaces() {\n    buildBackupCards();buildUpdateCard();\n  }",
    "operations surface builder",
)
ops = sub_once(ops, r"\n  async function loadHealth\(\) \{.*?\n  function formatBytes\(value\).*?\n", "\n", "System health loader")
ops = replace_once(
    ops,
    "  function activate(page) {\n    buildSurfaces();\n    if(page==='system')loadHealth();\n    if(page==='backups'||page==='updates')loadPolicy();\n  }",
    "  function activate(page) {\n    buildSurfaces();\n    if(page==='backups'||page==='updates')loadPolicy();\n  }",
    "operations activation hook",
)
ops = replace_once(
    ops,
    "    const current=localStorage.tdSettingsPage||'general';\n    if(current==='system')setTimeout(()=>window.TDSettings?.activate?.('system'),0);\n    else if(current==='backups'||current==='updates')activate(current);",
    "    const current=localStorage.tdSettingsPage||'general';\n    if(current==='backups'||current==='updates')activate(current);",
    "operations initialization",
)
for forbidden in ("System health", "/api/system-health", "opsHealthSummary", "opsHealthComponents", "loadHealth"):
    if forbidden in ops:
        raise SystemExit(f"System health browser reference remains: {forbidden}")
write("static/ops.js", ops)

# Remove System from the settings router so stale browser state falls back to General.
settings = read("static/settings.js")
settings = replace_once(
    settings,
    "    const allowed = ['general','access','clients','backups','updates','notifications','integrations','users','system'];",
    "    const allowed = ['general','access','clients','backups','updates','notifications','integrations','users'];",
    "settings page allowlist",
)
write("static/settings.js", settings)

# Remove the server-side System health endpoint and its now-dead helpers.
runtime = read("src/torrent_dashboard/runtime.py")
runtime = runtime.replace(
    "security-audit APIs, and the consolidated system-health surface.",
    "security-audit APIs, and operational settings adapters.",
    1,
)
runtime = runtime.replace("    build_system_health,\n", "", 1)
runtime = runtime.replace("STARTED_AT = time.time()\n", "", 1)
runtime = sub_once(runtime, r"\ndef _client_health_rows\(config: dict\):.*?\n\ndef _retention\(config: dict\):", "\n\ndef _retention(config: dict):", "System health runtime helpers")
runtime = sub_once(
    runtime,
    r"        if path == \"/api/system-health\":\n.*?                return self\.send_json\(500, \{\"error\": str\(exc\)\}, new_cookie\)\n",
    "",
    "System health GET endpoint",
)
if "system-health" in runtime or "build_system_health" in runtime or "_health_payload" in runtime:
    raise SystemExit("System health runtime references remain")
write("src/torrent_dashboard/runtime.py", runtime)

operations = read("src/torrent_dashboard/operations.py")
operations = operations.replace('"""Operational scheduling, retention, and system-health helpers."""', '"""Operational scheduling and retention helpers."""', 1)
operations = operations.replace("import re\n", "", 1)
operations = sub_once(operations, r"\ndef _safe_disk_usage\(path: Path\):.*?\n\n__all__ = \[", "\n\n__all__ = [", "System health operation helpers")
operations = operations.replace('    "build_system_health",\n', "", 1)
if "build_system_health" in operations or "_display_state" in operations or "_safe_disk_usage" in operations:
    raise SystemExit("System health operation helpers remain")
write("src/torrent_dashboard/operations.py", operations)

# Remove health-specific tests and replace them with removal contracts.
operation_tests = read("tests/test_operations.py")
operation_tests = operation_tests.replace("    build_system_health,\n", "", 1)
operation_tests = sub_once(
    operation_tests,
    r"\n    def test_security_events_do_not_make_service_health_unhealthy\(self\):.*?(?=\n\nif __name__ == \"__main__\":)",
    "",
    "System health operation test",
)
write("tests/test_operations.py", operation_tests)

ui_tests = '''from pathlib import Path\nimport unittest\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\nclass SystemOperationsUiTests(unittest.TestCase):\n    def test_ops_script_exposes_domain_settings_without_system_health(self):\n        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")\n        for marker in (\n            "Backup protection", "Backup schedule", "Automatic updates", "Retention",\n            "/api/retention/run", "schedule_frequency", "window_start", "backup_count",\n        ):\n            self.assertIn(marker, source)\n        for marker in ("System health", "/api/system-health", "opsHealthSummary", "loadHealth", "Security audit"):\n            self.assertNotIn(marker, source)\n\n    def test_operational_settings_use_existing_settings_pages(self):\n        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")\n        settings = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")\n        self.assertIn("addCard('backups','opsBackupProtectionCard'", source)\n        self.assertIn("addCard('backups','opsBackupScheduleCard'", source)\n        self.assertIn("addCard('backups','opsRetentionCard'", source)\n        self.assertIn("addCard('updates','opsAutomaticUpdatesCard'", source)\n        self.assertNotIn("'users','system'", settings)\n        self.assertIn("window.TDOps.saveBackupSettings", settings)\n        self.assertIn("window.TDOps.saveUpdateSettings", settings)\n\n    def test_multi_card_settings_pages_have_spacing(self):\n        source = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")\n        self.assertIn('.settings-page>.settings-card+.settings-card{margin-top:12px}', source)\n\n    def test_runtime_keeps_audit_and_retention_without_system_health_api(self):\n        source = (ROOT / "src" / "torrent_dashboard" / "runtime.py").read_text(encoding="utf-8")\n        self.assertIn('/static/ops.js?v=', source)\n        self.assertNotIn('/api/system-health', source)\n        self.assertIn('path == "/api/audit"', source)\n        self.assertIn('path == "/api/retention/run"', source)\n\n\nif __name__ == "__main__":\n    unittest.main()\n'''
write("tests/test_system_ops_ui.py", ui_tests)

validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert \"window.TDOps?.saveUpdateSettings\" in settings_js\n"
validator = replace_once(
    validator,
    anchor,
    anchor + "    ops_js = (ROOT / 'static' / 'ops.js').read_text(encoding='utf-8')\n    assert 'System health' not in ops_js and '/api/system-health' not in ops_js\n    assert \"'users','system'\" not in settings_js\n",
    "settings operations validator anchor",
)
write("release_tools/validate_ui_strings.py", validator)

# Version bump frontend/runtime cache keys.
init = read("src/torrent_dashboard/__init__.py").replace('__version__ = "0.5.158"', f'__version__ = "{VERSION}"', 1)
write("src/torrent_dashboard/__init__.py", init)
app = read("static/app.js").replace("const FRONTEND_BUILD='0.5.158';", f"const FRONTEND_BUILD='{VERSION}';", 1)
write("static/app.js", app)
html = read("static/index.html").replace("0.5.158", VERSION)
write("static/index.html", html)
sw = read("static/sw.js").replace("torrent-dashboard-v05158", "torrent-dashboard-v05159").replace("0.5.158", VERSION)
write("static/sw.js", sw)

# Add v0.5.159 release metadata and active handoff state.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == VERSION for item in release_data.get("releases", [])):
    raise SystemExit(f"Release {VERSION} already exists")
release_data["releases"].insert(0, {
    "version": VERSION,
    "date": "2026-09-11",
    "status": "prerelease",
    "title": "Remove the System health settings page",
    "summary": "Removes the standalone System health settings category and its dedicated API because it duplicates status already available in the settings areas where users can act on it.",
    "highlights": [
        "Removes System health from desktop and mobile Settings navigation.",
        "Removes the dynamic System health card and browser polling code.",
        "Removes the dedicated /api/system-health endpoint and its unused health aggregation helpers.",
        "Browsers that previously stored System as the active Settings page now fall back to General."
    ],
    "fixes": [
        "Eliminates an irrelevant settings category after backup, update, notification, and integration controls were moved to their proper domains."
    ],
    "technical": [
        "Keeps the durable audit API, retention scheduler, backup scheduler, automatic updater, and domain-specific settings cards unchanged.",
        "Removes dead health formatting and aggregation code from the operations runtime instead of merely hiding the page."
    ],
    "validation": [
        "Runs source/unit validation, browser contract checks, JavaScript syntax checks, generated documentation validation, the source updater package build, and the Windows PyInstaller smoke build."
    ],
    "known_issues": [
        "Backup encryption remains opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.",
        "Windows executables are not code-signed yet."
    ],
    "architecture": [
        "Operational status is surfaced through actionable domain pages and notifications rather than a standalone aggregate System health page."
    ],
    "decisions": [
        "Do not keep a separate System settings category solely for passive health summaries.",
        "Remove the unused health API and aggregation helpers together with the UI to avoid dead maintenance surface."
    ],
    "next_steps": [
        {
            "priority": 1,
            "title": "Verify Settings navigation after update",
            "detail": "Confirm System health no longer appears on desktop or mobile and that Backups and Updates retain their reorganized operational controls."
        }
    ]
})
release_path.write_text(json.dumps(release_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

active = {
    "schema": 1,
    "status": "release-candidate",
    "objective": "Publish v0.5.159 without the standalone System health settings surface",
    "why": "System health became a passive duplicate after operational controls were organized under Backups, Updates, Notifications, and Integrations.",
    "acceptance_criteria": [
        "System health is absent from desktop and mobile Settings navigation.",
        "No browser code requests /api/system-health.",
        "The /api/system-health endpoint and health aggregation helpers are removed.",
        "Backups, Updates, retention, audit persistence, and notification behavior remain unchanged.",
        "Ubuntu/Windows Python 3.13/3.14 validation passes.",
        "The source updater ZIP and compiled Windows package build successfully, and all three Windows executables pass smoke tests.",
        "v0.5.159 is published with both source and Windows updater ZIPs and SHA-256 digests."
    ],
    "decisions": [
        "Remove System health entirely rather than hide it while retaining dead browser/API code.",
        "Keep durable audit logging and operational schedulers because they support real features outside the removed page."
    ],
    "files": [
        "static/ops.js", "static/settings.js", "src/torrent_dashboard/runtime.py",
        "src/torrent_dashboard/operations.py", "tests/test_system_ops_ui.py",
        "tests/test_operations.py", "release_tools/validate_ui_strings.py",
        "src/torrent_dashboard/__init__.py", "static/index.html", "static/app.js",
        "static/sw.js", "release_notes/releases.json", "development/current.json"
    ],
    "blockers": [],
    "out_of_scope": [
        "No changes to backup behavior, automatic-update behavior, retention execution, audit persistence, or notification delivery."
    ],
    "next_action": "Run the full pull-request validation and Windows smoke build; if green, merge and verify the updater-visible v0.5.159 release."
}
(ROOT / "development" / "current.json").write_text(json.dumps(active, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
