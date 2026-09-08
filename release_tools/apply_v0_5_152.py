from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_version() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    replace_once(path, '__version__ = "0.5.151"', '__version__ = "0.5.152"')


def update_console_help() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "recovery_console.py"
    replace_once(
        path,
        """Available to your account:\n  help\n  status\n  clients\n  integrations\n  jellyfin tasks <integration-id>\n  update status\n""",
        """Available to your account:\n  help\n  status\n  client list\n  integration list\n  torrent list [client-id]\n  jellyfin list <integration-id>\n  update status\n""",
    )


def update_dashboard() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "dashboard.py"
    helper_anchor = '''def _recovery_console_integration(cfg, integration_id):\n    integration_id = str(integration_id or "").strip()\n    item = next((entry for entry in cfg.get("integrations", []) if str(entry.get("id") or "") == integration_id), None)\n    if not item:\n        raise RuntimeError("Integration was not found")\n    return item\n\n\n'''
    helper = helper_anchor + '''def _recovery_console_torrent_list(cfg, server_id=None):\n    if server_id:\n        servers = [_recovery_console_server(cfg, server_id)]\n    else:\n        servers = list(cfg.get("servers", []))\n    if not servers:\n        return "No download clients are configured."\n\n    snapshots = {}\n    with CACHE_LOCK:\n        for server in servers:\n            sid = str(server.get("id") or "")\n            cached = CACHE.get(sid, {})\n            torrents = cached.get("torrents") if isinstance(cached, dict) else None\n            snapshots[sid] = {\n                "ok": bool(isinstance(cached, dict) and cached.get("ok")),\n                "torrents": list(torrents) if isinstance(torrents, list) else None,\n            }\n\n    rows = []\n    unavailable = []\n    for server in servers:\n        sid = str(server.get("id") or "")\n        snapshot = snapshots.get(sid, {})\n        torrents = snapshot.get("torrents")\n        if not snapshot.get("ok") or torrents is None:\n            unavailable.append(sid or "unknown")\n            continue\n        for torrent in torrents:\n            hash_value = str(torrent.get("hash") or "-").strip() or "-"\n            state = " ".join(str(torrent.get("state") or "unknown").split()) or "unknown"\n            name = " ".join(str(torrent.get("name") or "Unnamed torrent").split()) or "Unnamed torrent"\n            try:\n                progress = max(0.0, min(100.0, float(torrent.get("progress", 0) or 0) * 100.0))\n            except (TypeError, ValueError):\n                progress = 0.0\n            rows.append(f"{sid}  {hash_value}  {state}  {progress:5.1f}%  {name}")\n\n    lines = []\n    if rows:\n        lines.append("CLIENT  HASH  STATE  PROGRESS  NAME")\n        lines.extend(rows)\n    else:\n        lines.append("No torrents are currently available.")\n    if unavailable:\n        lines.append("Unavailable clients: " + ", ".join(unavailable))\n    return "\\n".join(lines)\n\n\n'''
    replace_once(path, helper_anchor, helper)

    old_jellyfin = '''    if command == "jellyfin":\n        if len(args) < 2:\n            raise RuntimeError("Usage: jellyfin tasks|start|stop <integration-id> [task-id]")\n        action, integration_id = args[0].lower(), args[1]\n        item = find_jellyfin_integration(cfg, integration_id)\n        if action == "tasks":\n            tasks = jellyfin_scheduled_tasks(item)\n'''
    new_jellyfin = '''    if command == "jellyfin":\n        if len(args) < 2:\n            raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")\n        action, integration_id = args[0].lower(), args[1]\n        item = find_jellyfin_integration(cfg, integration_id)\n        if action in ("list", "tasks"):\n            tasks = jellyfin_scheduled_tasks(item)\n'''
    replace_once(path, old_jellyfin, new_jellyfin)
    replace_once(
        path,
        '        raise RuntimeError("Usage: jellyfin tasks|start|stop <integration-id> [task-id]")\n\n    if command == "torrent":\n        require_console_admin()\n        if len(args) < 4 or args[0].lower() != "action":\n            raise RuntimeError("Usage: torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>")\n        server_id, action, target = args[1], args[2].lower(), args[3]\n',
        '        raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")\n\n    if command in ("torrent", "torrents"):\n        sub = args[0].lower() if args else ""\n        if command == "torrents" or sub == "list":\n            if command == "torrents":\n                if args:\n                    raise RuntimeError("Usage: torrents")\n                server_id = None\n            else:\n                if len(args) > 2:\n                    raise RuntimeError("Usage: torrent list [client-id]")\n                server_id = args[1] if len(args) == 2 else None\n            return {"output": _recovery_console_torrent_list(cfg, server_id)}\n\n        require_console_admin()\n        if len(args) < 4 or sub != "action":\n            raise RuntimeError("Usage: torrent list [client-id] | torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>")\n        server_id, action, target = args[1], args[2].lower(), args[3]\n',
    )


def update_tests() -> None:
    path = ROOT / "tests" / "test_recovery_console.py"
    replace_once(
        path,
        '        self.assertIn("read-only", standard)\n        self.assertNotIn("update apply --confirm", standard)\n',
        '        self.assertIn("read-only", standard)\n        self.assertIn("client list", standard)\n        self.assertIn("integration list", standard)\n        self.assertIn("torrent list [client-id]", standard)\n        self.assertIn("jellyfin list <integration-id>", standard)\n        self.assertNotIn("update apply --confirm", standard)\n',
    )
    runtime = ROOT / "tests" / "test_recovery_console_runtime.py"
    runtime.write_text('''from __future__ import annotations\n\nimport unittest\nfrom unittest import mock\n\nfrom torrent_dashboard import dashboard\n\n\nclass _Handler:\n    def client_ip(self):\n        return "127.0.0.1"\n\n\nclass RecoveryConsoleRuntimeTests(unittest.TestCase):\n    def setUp(self):\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE.clear()\n\n    def tearDown(self):\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE.clear()\n\n    def test_torrent_list_is_read_only_and_exposes_actionable_identifiers(self):\n        cfg = {\n            "servers": [{"id": "desktop", "name": "Desktop", "enabled": True}],\n            "integrations": [],\n            "users": [],\n            "auth": {"mode": "password"},\n        }\n        torrent_hash = "a" * 40\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE["desktop"] = {\n                "ok": True,\n                "torrents": [{\n                    "hash": torrent_hash,\n                    "name": "Example Torrent",\n                    "state": "downloading",\n                    "progress": 0.425,\n                }],\n            }\n        result = dashboard.recovery_console_execute(\n            _Handler(), cfg, "torrent list", sess={"group": "standard"}\n        )\n        self.assertIn("CLIENT  HASH  STATE  PROGRESS  NAME", result["output"])\n        self.assertIn("desktop", result["output"])\n        self.assertIn(torrent_hash, result["output"])\n        self.assertIn("42.5%", result["output"])\n        self.assertIn("Example Torrent", result["output"])\n        with self.assertRaisesRegex(RuntimeError, "Administrator access"):\n            dashboard.recovery_console_execute(\n                _Handler(), cfg, f"torrent action desktop stop {torrent_hash}", sess={"group": "standard"}\n            )\n\n    def test_torrent_list_can_filter_to_one_client(self):\n        cfg = {\n            "servers": [\n                {"id": "one", "name": "One", "enabled": True},\n                {"id": "two", "name": "Two", "enabled": True},\n            ],\n            "integrations": [],\n            "users": [],\n            "auth": {"mode": "password"},\n        }\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE["one"] = {"ok": True, "torrents": [{"hash": "1" * 40, "name": "First", "state": "paused", "progress": 1}]}\n            dashboard.CACHE["two"] = {"ok": True, "torrents": [{"hash": "2" * 40, "name": "Second", "state": "seeding", "progress": 1}]}\n        result = dashboard.recovery_console_execute(\n            _Handler(), cfg, "torrent list two", sess={"group": "standard"}\n        )\n        self.assertIn("Second", result["output"])\n        self.assertNotIn("First", result["output"])\n\n    def test_jellyfin_list_alias_lists_actionable_task_ids(self):\n        cfg = {"servers": [], "integrations": [], "users": [], "auth": {"mode": "password"}}\n        task = {"id": "task-1", "category": "Library", "name": "Scan media library", "state": "Idle"}\n        with mock.patch.object(dashboard, "find_jellyfin_integration", return_value={"id": "jf"}), \\\n             mock.patch.object(dashboard, "jellyfin_scheduled_tasks", return_value=[task]):\n            result = dashboard.recovery_console_execute(\n                _Handler(), cfg, "jellyfin list jf", sess={"group": "standard"}\n            )\n        self.assertIn("task-1", result["output"])\n        self.assertIn("Scan media library", result["output"])\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")


def update_frontend_version() -> None:
    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if "0.5.151" not in text and "0.5.152" not in text:
        raise SystemExit("Expected frontend version marker was not found in static/index.html")
    index.write_text(text.replace("0.5.151", "0.5.152"), encoding="utf-8")

    app_js = ROOT / "static" / "app.js"
    replace_once(app_js, "const FRONTEND_BUILD='0.5.151';", "const FRONTEND_BUILD='0.5.152';")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "0.5.151" not in text and "0.5.152" not in text:
        raise SystemExit("Expected frontend version marker was not found in static/sw.js")
    sw.write_text(text.replace("0.5.151", "0.5.152").replace("v05151", "v05152"), encoding="utf-8")


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.setdefault("releases", [])
    if not any(str(item.get("version")) == "0.5.152" for item in releases):
        releases.insert(0, {
            "version": "0.5.152",
            "date": "2026-09-08",
            "status": "prerelease",
            "title": "Recovery Console list parity",
            "summary": "Adds explicit read-only list commands for actionable Recovery Console resources while preserving the v0.5.151 profile, login, backup, and update behavior.",
            "highlights": [
                "Makes client list and integration list explicit in Console help while retaining the existing clients and integrations compatibility aliases.",
                "Adds torrent list [client-id] so standard sessions can enumerate actionable torrent hashes, client IDs, states, progress, and names without mutation privileges.",
                "Adds jellyfin list <integration-id> as the explicit list counterpart to Jellyfin task start and stop actions while retaining jellyfin tasks as an alias.",
                "Carries the console parity work forward on top of the current main branch without reintroducing the superseded animated login treatment."
            ],
            "fixes": [
                "Closes the Console discoverability gap where torrent and Jellyfin actions required identifiers that the Console did not provide an explicit list command to obtain."
            ],
            "technical": [
                "Torrent listing snapshots the existing server-side torrent cache under CACHE_LOCK and does not perform additional qBitTorrent polling or expose stored client credentials.",
                "Read-only list commands remain available to standard sessions; torrent and Jellyfin mutation commands remain administrator-gated.",
                "Synchronizes the frontend build marker and service-worker cache namespace to v0.5.152 so auto-update clients receive a coherent application build."
            ],
            "validation": [
                "Adds runtime coverage for torrent list output, per-client filtering, read-only authorization, and the jellyfin list alias.",
                "Extends Console help tests for explicit client, integration, torrent, and Jellyfin list syntax.",
                "Runs the cross-platform pull-request matrix on Linux and Windows with Python 3.13 and 3.14 plus source-package validation before publishing."
            ],
            "known_issues": [
                "Portable backup archives can contain saved client and integration credentials in plaintext; store exported .tdbackup files securely.",
                "Windows executables are not code-signed yet."
            ],
            "architecture": [
                "Actionable Recovery Console resource families expose explicit read-only list forms while mutation commands remain separated behind administrator authorization."
            ],
            "decisions": [
                "Keep existing plural and jellyfin tasks forms as compatibility aliases instead of removing established Console syntax.",
                "Use the existing torrent cache for Console listing instead of introducing an extra qBitTorrent request path.",
                "Preserve the static v0.5.151 login treatment and backup lifecycle behavior while carrying forward only the non-conflicting Console parity work."
            ],
            "next_steps": [
                {
                    "priority": 1,
                    "title": "Exercise v0.5.152 on compiled Windows",
                    "detail": "Install v0.5.152 through the built-in updater, verify client/integration/torrent/Jellyfin list commands, and repeat the create/delete/import/restore backup lifecycle on the compiled package."
                }
            ]
        })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    active_path = ROOT / "development" / "current.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    active.update({
        "status": "ready",
        "objective": "Validate v0.5.152 auto-update, Recovery Console list parity, and the backup lifecycle on compiled Windows",
        "why": "The list-command parity work has been carried forward onto the current main baseline; the remaining risk is operational validation through the updater and compiled Windows package.",
        "acceptance_criteria": [
            "Source/unit, UI, syntax, generated-documentation, hygiene, source-package, and pull-request matrix checks pass.",
            "The built-in updater detects and installs v0.5.152 from the GitHub prerelease without manual file replacement.",
            "client list, integration list, torrent list [client-id], and jellyfin list <integration-id> expose actionable identifiers to read-only sessions.",
            "Torrent and Jellyfin mutation commands remain administrator-only.",
            "The static login treatment and Settings → Backups create/delete/import/restore behavior from v0.5.151 remain intact."
        ],
        "decisions": [
            "Keep list commands read-only and preserve administrator gates on mutations.",
            "Keep compatibility aliases for established Console syntax.",
            "Use the existing torrent cache for Console listing rather than adding another qBitTorrent polling path.",
            "Do not reintroduce superseded login animation while merging the Console parity work."
        ],
        "files": [
            "src/torrent_dashboard/dashboard.py",
            "src/torrent_dashboard/recovery_console.py",
            "tests/test_recovery_console.py",
            "tests/test_recovery_console_runtime.py",
            "release_notes/releases.json",
            "static/index.html",
            "static/app.js",
            "static/sw.js"
        ],
        "blockers": [],
        "out_of_scope": [
            "Backup encryption, scheduled backups, cloud destinations, code signing, broader authentication redesign, and new Console mutation capabilities."
        ],
        "next_action": "Install v0.5.152 through the built-in updater on compiled Windows, verify the four list forms and admin mutation gates, then repeat the portable backup lifecycle."
    })
    active_path.write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    update_version()
    update_console_help()
    update_dashboard()
    update_tests()
    update_frontend_version()
    update_release_metadata()


if __name__ == "__main__":
    main()
