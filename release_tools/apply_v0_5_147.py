from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.147"
PREVIOUS_VERSION = "0.5.146"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_version() -> None:
    init = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    replace_once(init, f'__version__ = "{PREVIOUS_VERSION}"', f'__version__ = "{VERSION}"')
    for path in (ROOT / "static").iterdir():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = text.replace(PREVIOUS_VERSION, VERSION).replace("v05146", "v05147")
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def update_login_style() -> None:
    path = ROOT / "static" / "app.css"
    replace_once(
        path,
        ".login-shell{min-height:100vh;display:grid;place-items:center;padding:20px}",
        ".login-shell{min-height:100vh;display:grid;place-items:center;padding:20px;background:var(--bg)}",
    )
    replace_once(
        path,
        ".login-card{width:min(410px,100%);background:var(--panel);border:1px solid var(--border);border-radius:22px;padding:30px;box-shadow:var(--shadow);display:grid;gap:13px}",
        ".login-card{width:min(410px,100%);background:var(--panel);border:1px solid var(--border);border-radius:22px;padding:30px;box-shadow:var(--shadow),0 0 48px color-mix(in srgb,var(--accent) 9%,transparent);display:grid;gap:13px}",
    )


def update_console_help() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "recovery_console.py"
    replace_once(
        path,
        '''Available to your account:\n  help\n  status\n  clients\n  integrations\n  jellyfin tasks <integration-id>\n  update status\n  update check\n  update repo\n''',
        '''Available to your account:\n  help\n  status\n  client list\n  integration list\n  torrent list [client-id]\n  jellyfin list <integration-id>\n  update status\n  update check\n  update repo\n''',
    )


def update_dashboard_console() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    marker = '''def _recovery_console_integration(cfg, integration_id):\n    integration_id = str(integration_id or "").strip()\n    item = next((entry for entry in cfg.get("integrations", []) if str(entry.get("id") or "") == integration_id), None)\n    if not item:\n        raise RuntimeError("Integration was not found")\n    return item\n\n\ndef recovery_console_execute(handler, cfg, raw_command, sess=None):\n'''
    replacement = '''def _recovery_console_integration(cfg, integration_id):\n    integration_id = str(integration_id or "").strip()\n    item = next((entry for entry in cfg.get("integrations", []) if str(entry.get("id") or "") == integration_id), None)\n    if not item:\n        raise RuntimeError("Integration was not found")\n    return item\n\n\ndef _recovery_console_torrent_list(cfg, server_id=None):\n    if server_id:\n        servers = [_recovery_console_server(cfg, server_id)]\n    else:\n        servers = list(cfg.get("servers", []))\n    if not servers:\n        return "No download clients are configured."\n\n    snapshots = {}\n    with CACHE_LOCK:\n        for server in servers:\n            sid = str(server.get("id") or "")\n            cached = CACHE.get(sid, {})\n            torrents = cached.get("torrents") if isinstance(cached, dict) else None\n            snapshots[sid] = {\n                "ok": bool(isinstance(cached, dict) and cached.get("ok")),\n                "torrents": list(torrents) if isinstance(torrents, list) else None,\n            }\n\n    rows = []\n    unavailable = []\n    for server in servers:\n        sid = str(server.get("id") or "")\n        snapshot = snapshots.get(sid, {})\n        torrents = snapshot.get("torrents")\n        if not snapshot.get("ok") or torrents is None:\n            unavailable.append(sid or "unknown")\n            continue\n        for torrent in torrents:\n            hash_value = str(torrent.get("hash") or "-").strip() or "-"\n            state = " ".join(str(torrent.get("state") or "unknown").split()) or "unknown"\n            name = " ".join(str(torrent.get("name") or "Unnamed torrent").split()) or "Unnamed torrent"\n            try:\n                progress = max(0.0, min(100.0, float(torrent.get("progress", 0) or 0) * 100.0))\n            except (TypeError, ValueError):\n                progress = 0.0\n            rows.append(f"{sid}  {hash_value}  {state}  {progress:5.1f}%  {name}")\n\n    lines = []\n    if rows:\n        lines.append("CLIENT  HASH  STATE  PROGRESS  NAME")\n        lines.extend(rows)\n    else:\n        lines.append("No torrents are currently available.")\n    if unavailable:\n        lines.append("Unavailable clients: " + ", ".join(unavailable))\n    return "\\n".join(lines)\n\n\ndef recovery_console_execute(handler, cfg, raw_command, sess=None):\n'''
    if marker in text:
        text = text.replace(marker, replacement, 1)
    elif "def _recovery_console_torrent_list(cfg, server_id=None):" not in text:
        raise SystemExit("Recovery console helper insertion point not found")

    old_jellyfin = '''    if command == "jellyfin":\n        if len(args) < 2:\n            raise RuntimeError("Usage: jellyfin tasks|start|stop <integration-id> [task-id]")\n        action, integration_id = args[0].lower(), args[1]\n        item = find_jellyfin_integration(cfg, integration_id)\n        if action == "tasks":\n            tasks = jellyfin_scheduled_tasks(item)\n            if not tasks:\n                return {"output": "Jellyfin reported no visible scheduled tasks."}\n            lines = []\n            for task in tasks:\n                progress = task.get("progress")\n                suffix = f" {progress:.0f}%" if isinstance(progress, (int, float)) else ""\n                lines.append(f"{task.get('id','')}  [{task.get('category','Other')}] {task.get('name','Scheduled task')}  {task.get('state','Idle')}{suffix}")\n            return {"output": "\\n".join(lines)}\n        if action in ("start", "stop"):\n            require_console_admin()\n            if len(args) < 3:\n                raise RuntimeError(f"Usage: jellyfin {action} <integration-id> <task-id>")\n            result = start_jellyfin_scheduled_task(item, args[2]) if action == "start" else stop_jellyfin_scheduled_task(item, args[2])\n            return {"output": result.get("message") or f"Jellyfin task {action} requested"}\n        raise RuntimeError("Usage: jellyfin tasks|start|stop <integration-id> [task-id]")\n'''
    new_jellyfin = '''    if command == "jellyfin":\n        if len(args) < 2:\n            raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")\n        action, integration_id = args[0].lower(), args[1]\n        item = find_jellyfin_integration(cfg, integration_id)\n        if action in ("list", "tasks"):\n            tasks = jellyfin_scheduled_tasks(item)\n            if not tasks:\n                return {"output": "Jellyfin reported no visible scheduled tasks."}\n            lines = []\n            for task in tasks:\n                progress = task.get("progress")\n                suffix = f" {progress:.0f}%" if isinstance(progress, (int, float)) else ""\n                lines.append(f"{task.get('id','')}  [{task.get('category','Other')}] {task.get('name','Scheduled task')}  {task.get('state','Idle')}{suffix}")\n            return {"output": "\\n".join(lines)}\n        if action in ("start", "stop"):\n            require_console_admin()\n            if len(args) < 3:\n                raise RuntimeError(f"Usage: jellyfin {action} <integration-id> <task-id>")\n            result = start_jellyfin_scheduled_task(item, args[2]) if action == "start" else stop_jellyfin_scheduled_task(item, args[2])\n            return {"output": result.get("message") or f"Jellyfin task {action} requested"}\n        raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")\n'''
    if old_jellyfin in text:
        text = text.replace(old_jellyfin, new_jellyfin, 1)
    elif 'if action in ("list", "tasks"):' not in text:
        raise SystemExit("Jellyfin console block not found")

    old_torrent = '''    if command == "torrent":\n        require_console_admin()\n        if len(args) < 4 or args[0].lower() != "action":\n            raise RuntimeError("Usage: torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>")\n        server_id, action, target = args[1], args[2].lower(), args[3]\n        if action not in SAFE_TORRENT_ACTIONS:\n            raise RuntimeError("Recovery console torrent actions are limited to start, stop, recheck, and reannounce")\n        result = get_client(cfg, server_id).action(action, {"hashes": [target]})\n        HISTORY.event(server_id, "recovery_action:" + action, "Recovery Console", target, {"client_ip": handler.client_ip()})\n        status = result[0] if isinstance(result, tuple) else 200\n        return {"output": f"Torrent action {action} sent (status {status})."}\n'''
    new_torrent = '''    if command in ("torrent", "torrents"):\n        sub = args[0].lower() if args else ""\n        if command == "torrents" or sub == "list":\n            if command == "torrents":\n                if args:\n                    raise RuntimeError("Usage: torrents")\n                server_id = None\n            else:\n                if len(args) > 2:\n                    raise RuntimeError("Usage: torrent list [client-id]")\n                server_id = args[1] if len(args) == 2 else None\n            return {"output": _recovery_console_torrent_list(cfg, server_id)}\n\n        require_console_admin()\n        if len(args) < 4 or sub != "action":\n            raise RuntimeError("Usage: torrent list [client-id] | torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>")\n        server_id, action, target = args[1], args[2].lower(), args[3]\n        if action not in SAFE_TORRENT_ACTIONS:\n            raise RuntimeError("Recovery console torrent actions are limited to start, stop, recheck, and reannounce")\n        result = get_client(cfg, server_id).action(action, {"hashes": [target]})\n        HISTORY.event(server_id, "recovery_action:" + action, "Recovery Console", target, {"client_ip": handler.client_ip()})\n        status = result[0] if isinstance(result, tuple) else 200\n        return {"output": f"Torrent action {action} sent (status {status})."}\n'''
    if old_torrent in text:
        text = text.replace(old_torrent, new_torrent, 1)
    elif 'if command in ("torrent", "torrents"):' not in text:
        raise SystemExit("Torrent console block not found")

    path.write_text(text, encoding="utf-8")


def update_tests() -> None:
    path = ROOT / "tests" / "test_recovery_console.py"
    text = path.read_text(encoding="utf-8")
    old = '''        self.assertIn("read-only", standard)\n        self.assertNotIn("update apply --confirm", standard)\n        self.assertIn("update apply --confirm", admin)\n        self.assertIn("torrent action", admin)\n'''
    new = '''        self.assertIn("read-only", standard)\n        self.assertIn("client list", standard)\n        self.assertIn("integration list", standard)\n        self.assertIn("torrent list [client-id]", standard)\n        self.assertIn("jellyfin list <integration-id>", standard)\n        self.assertNotIn("update apply --confirm", standard)\n        self.assertIn("update apply --confirm", admin)\n        self.assertIn("torrent action", admin)\n'''
    if old in text:
        text = text.replace(old, new, 1)
    elif 'self.assertIn("torrent list [client-id]", standard)' not in text:
        raise SystemExit("Recovery console help test block not found")
    path.write_text(text, encoding="utf-8")

    runtime = ROOT / "tests" / "test_recovery_console_runtime.py"
    runtime.write_text(
        '''from __future__ import annotations\n\nimport unittest\nfrom unittest import mock\n\nfrom torrent_dashboard import dashboard\n\n\nclass _Handler:\n    def client_ip(self):\n        return "127.0.0.1"\n\n\nclass RecoveryConsoleRuntimeTests(unittest.TestCase):\n    def setUp(self):\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE.clear()\n\n    def tearDown(self):\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE.clear()\n\n    def test_torrent_list_is_read_only_and_exposes_actionable_identifiers(self):\n        cfg = {\n            "servers": [{"id": "desktop", "name": "Desktop", "enabled": True}],\n            "integrations": [],\n            "users": [],\n            "auth": {"mode": "password"},\n        }\n        torrent_hash = "a" * 40\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE["desktop"] = {\n                "ok": True,\n                "torrents": [{\n                    "hash": torrent_hash,\n                    "name": "Example Torrent",\n                    "state": "downloading",\n                    "progress": 0.425,\n                }],\n            }\n        result = dashboard.recovery_console_execute(\n            _Handler(), cfg, "torrent list", sess={"group": "standard"}\n        )\n        self.assertIn("CLIENT  HASH  STATE  PROGRESS  NAME", result["output"])\n        self.assertIn("desktop", result["output"])\n        self.assertIn(torrent_hash, result["output"])\n        self.assertIn("42.5%", result["output"])\n        self.assertIn("Example Torrent", result["output"])\n        with self.assertRaisesRegex(RuntimeError, "Administrator access"):\n            dashboard.recovery_console_execute(\n                _Handler(), cfg, f"torrent action desktop stop {torrent_hash}", sess={"group": "standard"}\n            )\n\n    def test_torrent_list_can_filter_to_one_client(self):\n        cfg = {\n            "servers": [\n                {"id": "one", "name": "One", "enabled": True},\n                {"id": "two", "name": "Two", "enabled": True},\n            ],\n            "integrations": [],\n            "users": [],\n            "auth": {"mode": "password"},\n        }\n        with dashboard.CACHE_LOCK:\n            dashboard.CACHE["one"] = {"ok": True, "torrents": [{"hash": "1" * 40, "name": "First", "state": "paused", "progress": 1}]}\n            dashboard.CACHE["two"] = {"ok": True, "torrents": [{"hash": "2" * 40, "name": "Second", "state": "seeding", "progress": 1}]}\n        result = dashboard.recovery_console_execute(\n            _Handler(), cfg, "torrent list two", sess={"group": "standard"}\n        )\n        self.assertIn("Second", result["output"])\n        self.assertNotIn("First", result["output"])\n\n    def test_jellyfin_list_alias_lists_actionable_task_ids(self):\n        cfg = {"servers": [], "integrations": [], "users": [], "auth": {"mode": "password"}}\n        task = {"id": "task-1", "category": "Library", "name": "Scan media library", "state": "Idle"}\n        with mock.patch.object(dashboard, "find_jellyfin_integration", return_value={"id": "jf"}), \\\n             mock.patch.object(dashboard, "jellyfin_scheduled_tasks", return_value=[task]):\n            result = dashboard.recovery_console_execute(\n                _Handler(), cfg, "jellyfin list jf", sess={"group": "standard"}\n            )\n        self.assertIn("task-1", result["output"])\n        self.assertIn("Scan media library", result["output"])\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
        encoding="utf-8",
    )


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.setdefault("releases", [])
    if not any(str(item.get("version") or "") == VERSION for item in releases):
        releases.insert(0, {
            "version": VERSION,
            "date": "2026-09-08",
            "status": "prerelease",
            "title": "Console list parity and login polish",
            "summary": "Adds explicit read-only list commands for actionable Recovery Console resources and refines the login page to use a flat background with a soft card glow.",
            "highlights": [
                "Adds torrent list [client-id] so the console can enumerate actionable torrent hashes, client IDs, state, progress, and names.",
                "Adds jellyfin list <integration-id> as the list counterpart to Jellyfin task start and stop actions while retaining jellyfin tasks as a compatibility alias.",
                "Makes client list and integration list explicit in console help while retaining the existing clients and integrations aliases.",
                "Removes the accent wash from the login-page background and keeps a subtle accent glow around the login card."
            ],
            "fixes": [],
            "technical": [
                "Torrent listing reads the dashboard's current server-side torrent cache and does not expose stored download-client credentials.",
                "Read-only list commands remain available to standard sessions; torrent and Jellyfin mutation commands remain administrator-gated.",
                "The source and frontend build version advances to v0.5.147 so the login CSS change gets a fresh service-worker cache namespace."
            ],
            "validation": [
                "Runs source validation, UI string auditing, JavaScript syntax checks, and the full unit-test suite.",
                "Adds runtime coverage for torrent list output, per-client filtering, read-only authorization, and the jellyfin list alias.",
                "Builds and validates the editable source release ZIP for v0.5.147."
            ],
            "known_issues": [
                "Windows executables are not code-signed yet; code signing remains deferred until compiled update behavior has been exercised across multiple releases."
            ],
            "architecture": [
                "Actionable Recovery Console resource families now expose an explicit list form: client, integration, torrent, and Jellyfin scheduled tasks."
            ],
            "decisions": [
                "Keep list commands read-only and preserve administrator gates on mutations.",
                "Keep legacy plural and jellyfin tasks forms as compatibility aliases rather than removing established console syntax.",
                "Use the existing torrent cache for console listing instead of introducing additional qBitTorrent polling from the command path."
            ],
            "next_steps": [
                {"priority": 1, "title": "Exercise executable updates", "detail": "Run v0.5.146 to v0.5.147 Windows prerelease upgrade, recovery reinstall, failed health-check, and rollback scenarios before removing preview labeling or adding code signing."}
            ]
        })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    update_version()
    update_login_style()
    update_console_help()
    update_dashboard_console()
    update_tests()
    update_release_metadata()


if __name__ == "__main__":
    main()
