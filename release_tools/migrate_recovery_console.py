#!/usr/bin/env python3
"""One-shot migration that removes the web console and expands local recovery."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.153"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one literal match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected one regex match, found {count}")
    return updated


def patch_dashboard() -> None:
    text = read("src/torrent_dashboard/dashboard.py")
    text = regex_once(
        text,
        r"\nfrom torrent_dashboard\.recovery_console import \(.*?\n\)\n",
        "\n",
        "dashboard recovery_console import",
        re.S,
    )
    text = regex_once(
        text,
        r"\n\ndef _recovery_console_json\(value\):.*?\n\nclass Handler\(BaseHTTPRequestHandler\):",
        "\n\nclass Handler(BaseHTTPRequestHandler):",
        "dashboard console implementation block",
        re.S,
    )
    text = regex_once(
        text,
        r"\n    def recovery_cookie_token\(self\):\n        return self\.cookie_value\(\"td_recovery\"\)\n",
        "",
        "unused recovery cookie helper",
    )
    text = regex_once(
        text,
        r"\n    def recovery_auth\(self\):.*?(?=\n    def recovery_login_route\(self\):)",
        "",
        "console session authorization helpers",
        re.S,
    )
    text = regex_once(
        text,
        r"\n    def recovery_command_route\(self\):.*?(?=\n    def [A-Za-z_])",
        "",
        "console command route method",
        re.S,
    )
    text = replace_once(
        text,
        '        if path=="/api/recovery/command": return self.recovery_command_route()\n',
        "",
        "console POST route",
    )
    for forbidden in ("recovery_console_execute", "/api/recovery/command", "SAFE_TORRENT_ACTIONS", "parse_recovery_command"):
        if forbidden in text:
            raise RuntimeError(f"dashboard still contains removed console marker: {forbidden}")
    if '/api/recovery/login' not in text:
        raise RuntimeError("browser recovery-key sign-in was removed unintentionally")
    write("src/torrent_dashboard/dashboard.py", text)


def patch_recovery_tool() -> None:
    text = read("src/torrent_dashboard/recovery_tool.py")
    text = replace_once(text, "import shutil\n", "import shutil\nimport shlex\n", "recovery shlex import")
    import_block = '''from torrent_dashboard.runtime_paths import app_dir, is_frozen, source_python_env, updater_command\nfrom torrent_dashboard.recovery_operations import (\n    SAFE_TORRENT_ACTIONS,\n    history_events,\n    jellyfin_task_action,\n    list_clients,\n    list_integrations,\n    list_jellyfin_tasks,\n    list_torrents,\n    list_users,\n    redacted_configuration,\n    test_client,\n    test_integration,\n    torrent_action,\n)\n'''
    text = replace_once(
        text,
        "from torrent_dashboard.runtime_paths import app_dir, is_frozen, source_python_env, updater_command\n",
        import_block,
        "recovery operation imports",
    )
    text = replace_once(
        text,
        'DATA_DIR = APP_DIR / "data"\n',
        'DATA_DIR = APP_DIR / "data"\nDB_PATH = DATA_DIR / "torrent_desk.sqlite3"\n',
        "recovery history path",
    )
    help_and_execute = r'''def parse_command(command: str) -> list[str]:
    raw = str(command or "").strip()
    if not raw:
        return []
    if len(raw) > 4096:
        raise RuntimeError("Recovery command is too long")
    if "\n" in raw or "\r" in raw:
        raise RuntimeError("Run one recovery command at a time")
    try:
        return shlex.split(raw, posix=True)
    except ValueError as exc:
        raise RuntimeError(f"Invalid recovery command: {exc}") from exc


def print_json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def print_update_status() -> None:
    if not UPDATE_STATE_PATH.exists():
        print_json({"state": "idle", "currentVersion": current_version()})
        return
    try:
        value = json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Update status is unreadable: {exc}") from exc
    print_json(value if isinstance(value, dict) else {"state": "unknown"})


def print_help() -> None:
    print("""
Commands:
  status                                      Show local installation and recovery state
  validate                                    Validate config and critical application files
  config show                                 Show redacted dashboard configuration
  client list                                 List configured qBittorrent clients
  client test <client-id>                     Test one qBittorrent client directly
  integration list                            List configured integrations with secrets redacted
  integration test <integration-id>           Test one integration directly
  torrent list [client-id]                    Fetch live torrent identifiers and state from qBittorrent
  torrent action <client-id> <action> <hash|all>
                                              Run start, stop, recheck, or reannounce only
  jellyfin list <integration-id>              List Jellyfin scheduled tasks
  jellyfin start <integration-id> <task-id>   Start a Jellyfin scheduled task
  jellyfin stop <integration-id> <task-id>    Stop a Jellyfin scheduled task
  users                                       Show redacted local user/account records
  events [limit]                              Show recent local dashboard history events
  repo                                        Show the configured GitHub repository
  repo <owner/repository|default>             Back up config and change the update repository
  check                                       Check the configured repository for releases
  install                                     Download, verify, and install the latest newer release
  reinstall                                   Reinstall the latest verified release
  update status                               Show local update state
  update check                                Check for a release
  update repo [owner/repository|default]      Show or change the update repository
  update install|apply                        Download, verify, and install the latest release
  update reinstall                            Reinstall the latest verified release
  update clear                                Clear stuck staged update files/status
  backup                                      Back up config.json
  backups                                     List local config backups
  restore <backup-file>                       Restore a recovery config backup
  network-reset                               Reset bind to 0.0.0.0:8765 and disable HTTPS
  clear-update                                Clear a stuck staged update and update status
  start                                       Start Torrent Dashboard without opening a browser
  log [lines]                                 Show the recovery/update restart log
  help                                        Show this help
  exit                                        Exit local recovery

Recovery.exe is the command and diagnostic recovery surface. The dashboard does not expose
an embedded command console. This is not an operating-system shell and no command starts a
listening recovery server.
""".strip())


def execute(command: str, cfg: dict) -> dict:
    parts = parse_command(command)
    if not parts:
        return cfg
    op = parts[0].lower()
    if op in ("exit", "quit", "q"):
        raise EOFError
    if op in ("help", "?"):
        print_help()
    elif op == "status":
        show_status(cfg)
    elif op == "validate":
        rows = validation_report(cfg)
        for name, ok, detail in rows:
            print(f"{'OK' if ok else 'FAIL':4}  {name}: {detail}")
        if not all(row[1] for row in rows):
            print("One or more recovery checks failed.")
    elif op == "config":
        if len(parts) > 2 or (len(parts) == 2 and parts[1].lower() != "show"):
            raise RuntimeError("Usage: config show")
        print_json(redacted_configuration(cfg))
    elif op in ("clients", "client"):
        if op == "clients" or len(parts) == 1 or parts[1].lower() == "list":
            rows = list_clients(cfg)
            if not rows:
                print("No download clients are configured.")
            for item in rows:
                print(f"{item['id']}  {item['name']}  {'enabled' if item['enabled'] else 'disabled'}  {item['base_url']}")
        elif parts[1].lower() == "test" and len(parts) == 3:
            print_json(test_client(cfg, parts[2]))
        else:
            raise RuntimeError("Usage: client list | client test <client-id>")
    elif op in ("integrations", "integration"):
        if op == "integrations" or len(parts) == 1 or parts[1].lower() == "list":
            rows = list_integrations(cfg)
            if not rows:
                print("No integrations are configured.")
            for item in rows:
                print(f"{item.get('id','')}  {item.get('type','')}  {item.get('name') or item.get('type') or 'Integration'}  {'enabled' if item.get('enabled', True) else 'disabled'}")
        elif parts[1].lower() == "test" and len(parts) == 3:
            print_json(test_integration(cfg, parts[2]))
        else:
            raise RuntimeError("Usage: integration list | integration test <integration-id>")
    elif op in ("torrents", "torrent"):
        if op == "torrents":
            if len(parts) != 1:
                raise RuntimeError("Usage: torrents")
            client_id = None
            rows = list_torrents(cfg)
        elif len(parts) >= 2 and parts[1].lower() == "list":
            if len(parts) > 3:
                raise RuntimeError("Usage: torrent list [client-id]")
            client_id = parts[2] if len(parts) == 3 else None
            rows = list_torrents(cfg, client_id)
        elif len(parts) == 5 and parts[1].lower() == "action":
            action = parts[3].lower()
            if action not in SAFE_TORRENT_ACTIONS:
                raise RuntimeError("Recovery torrent actions are limited to start, stop, recheck, and reannounce")
            result = torrent_action(cfg, parts[2], action, parts[4])
            print(f"Torrent action {action} sent to {result['client_id']} (status {result['status']}).")
            return cfg
        else:
            raise RuntimeError("Usage: torrent list [client-id] | torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>")
        if not rows:
            print("No torrents are currently available.")
        else:
            print("CLIENT  HASH  STATE  PROGRESS  NAME")
            for item in rows:
                print(f"{item['client_id']}  {item['hash'] or '-'}  {item['state']}  {item['progress']:5.1f}%  {item['name']}")
    elif op == "jellyfin":
        if len(parts) < 3:
            raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")
        action, integration_id = parts[1].lower(), parts[2]
        if action in ("list", "tasks"):
            tasks = list_jellyfin_tasks(cfg, integration_id)
            if not tasks:
                print("Jellyfin reported no visible scheduled tasks.")
            for task in tasks:
                progress = task.get("progress")
                suffix = f" {progress:.0f}%" if isinstance(progress, (int, float)) else ""
                print(f"{task.get('id','')}  [{task.get('category','Other')}] {task.get('name','Scheduled task')}  {task.get('state','Idle')}{suffix}")
        elif action in ("start", "stop") and len(parts) == 4:
            result = jellyfin_task_action(cfg, integration_id, action, parts[3])
            print(result.get("message") or f"Jellyfin task {action} requested.")
        else:
            raise RuntimeError("Usage: jellyfin list|tasks|start|stop <integration-id> [task-id]")
    elif op == "users":
        if len(parts) != 1:
            raise RuntimeError("Usage: users")
        print_json(list_users(cfg))
    elif op == "events":
        if len(parts) > 2:
            raise RuntimeError("Usage: events [limit]")
        try:
            limit = int(parts[1]) if len(parts) == 2 else 50
        except ValueError as exc:
            raise RuntimeError("Events limit must be a number from 1 to 200") from exc
        print_json(history_events(DB_PATH, max(1, min(200, limit))))
    elif op == "repo":
        if len(parts) == 1:
            print(configured_repository(cfg))
        elif len(parts) == 2:
            requested = DEFAULT_REPOSITORY if parts[1].lower() == "default" else parts[1]
            value = set_repository(cfg, requested)
            cfg = load_config()
            print(f"Update repository set to {value}.")
        else:
            raise RuntimeError("Usage: repo [owner/repository|default]")
    elif op == "check":
        check_update(cfg)
    elif op in ("install", "reinstall"):
        action = "reinstall" if op == "reinstall" else "install"
        if not confirm(f"This will {action} Torrent Dashboard from {configured_repository(cfg)}."):
            print("Cancelled.")
        else:
            install_update(cfg, force=op == "reinstall")
    elif op == "update":
        sub = parts[1].lower() if len(parts) > 1 else "status"
        if sub == "status" and len(parts) == 2:
            print_update_status()
        elif sub == "check" and len(parts) == 2:
            check_update(cfg)
        elif sub == "repo":
            if len(parts) == 2:
                print(configured_repository(cfg))
            elif len(parts) == 3:
                requested = DEFAULT_REPOSITORY if parts[2].lower() == "default" else parts[2]
                value = set_repository(cfg, requested)
                cfg = load_config()
                print(f"Update repository set to {value}.")
            else:
                raise RuntimeError("Usage: update repo [owner/repository|default]")
        elif sub in ("install", "apply", "reinstall") and len(parts) == 2:
            force = sub == "reinstall"
            action = "reinstall" if force else "install"
            if not confirm(f"This will {action} Torrent Dashboard from {configured_repository(cfg)}."):
                print("Cancelled.")
            else:
                install_update(cfg, force=force)
        elif sub == "download" and len(parts) == 2:
            raise RuntimeError("Recovery.exe does not keep a separate staged download; use update install to download, verify, and apply in one operation")
        elif sub == "clear" and len(parts) == 2:
            if confirm("Delete staged update files and update-status.json?"):
                clear_update_state()
            else:
                print("Cancelled.")
        else:
            raise RuntimeError("Usage: update status|check|repo|install|apply|reinstall|clear")
    elif op == "backup":
        print(f"Config backup created: {backup_config()}")
    elif op == "backups":
        items = list_backups()
        if not items:
            print("No recovery config backups exist.")
        for item in items:
            print(item.name)
    elif op == "restore":
        if len(parts) != 2:
            raise RuntimeError("Usage: restore <backup-file>")
        if not confirm(f"Restore {parts[1]} and replace the current config.json?"):
            print("Cancelled.")
        else:
            source = restore_config(parts[1])
            cfg = load_config()
            print(f"Restored {source.name}.")
    elif op == "network-reset":
        if not confirm("Reset dashboard bind/port/HTTPS settings?"):
            print("Cancelled.")
        else:
            network_reset(cfg)
            cfg = load_config()
    elif op == "clear-update":
        if not confirm("Delete staged update files and update-status.json?"):
            print("Cancelled.")
        else:
            clear_update_state()
    elif op == "start":
        start_dashboard()
    elif op == "log":
        if len(parts) > 2:
            raise RuntimeError("Usage: log [lines]")
        try:
            lines = int(parts[1]) if len(parts) == 2 else 80
        except ValueError as exc:
            raise RuntimeError("Log line count must be a number") from exc
        tail_log(lines)
    else:
        raise RuntimeError("Unknown recovery command. Type help.")
    return cfg
'''
    text = regex_once(
        text,
        r"def print_help\(\) -> None:.*?(?=\ndef interactive\(cfg: dict\) -> None:)",
        help_and_execute + "\n",
        "recovery help and command dispatcher",
        re.S,
    )
    write("src/torrent_dashboard/recovery_tool.py", text)


def patch_frontend() -> None:
    html = read("static/index.html")
    html = html.replace("0.5.152", VERSION)
    html = replace_once(
        html,
        "Reload the page. If the problem continues, use the Recovery Console.",
        "Reload the page. If the problem continues, run Recovery.exe on the Torrent Dashboard host.",
        "startup recovery guidance",
    )
    html = re.sub(r'<button[^>]*data-view="console"[^>]*>.*?</button>\n?', "", html)
    html = regex_once(
        html,
        r'<section class="view" id="view-console">.*?(?=<section class="view" id="view-settings">)',
        "",
        "embedded console HTML",
        re.S,
    )
    if 'data-view="console"' in html or 'id="view-console"' in html or "embeddedConsole" in html:
        raise RuntimeError("embedded console HTML remains")
    write("static/index.html", html)

    app_js = read("static/app.js").replace("0.5.152", VERSION)
    app_js = regex_once(
        app_js,
        r"\nconst embeddedConsoleState=.*?(?=\nasync function rawJson)",
        "",
        "embedded console JavaScript",
        re.S,
    )
    app_js = replace_once(
        app_js,
        "const settingsView=view==='settings',dashboardView=view==='dashboard',consoleView=view==='console';",
        "const settingsView=view==='settings',dashboardView=view==='dashboard';",
        "console view state",
    )
    app_js = replace_once(
        app_js,
        ":consoleView?'Recovery and diagnostic commands':uiText('dashboardConfiguration')",
        ":uiText('dashboardConfiguration')",
        "console subtitle",
    )
    app_js = regex_once(
        app_js,
        r"if\(consoleView\)\{initializeEmbeddedConsole\(\);setTimeout\(\(\)=>\$\('#embeddedConsoleCommand'\)\?\.focus\(\),0\)\}",
        "",
        "console view initialization",
    )
    app_js = replace_once(app_js, "bindAddTorrentUI();bindEmbeddedConsole();", "bindAddTorrentUI();", "console binding")
    for forbidden in ("embeddedConsole", "/api/recovery/command", "consoleView"):
        if forbidden in app_js:
            raise RuntimeError(f"app.js still contains removed console marker: {forbidden}")
    write("static/app.js", app_js)

    css = read("static/app.css")
    css = css.replace("/* 0.5.138 recovery console entry points. */", "/* Recovery access and shared link entry points. */")
    css = regex_once(
        css,
        r"\n/\* 0\.5\.139 embedded administrator console\. \*/.*?(?=\n/\* 0\.5\.147 dashboard-wide recovery login\. \*/)",
        "",
        "embedded console CSS",
        re.S,
    )
    if "embedded-console" in css:
        raise RuntimeError("embedded console CSS remains")
    write("static/app.css", css)

    sw = read("static/sw.js").replace("0.5.152", VERSION)
    write("static/sw.js", sw)


def patch_validators_and_tests() -> None:
    ui = read("release_tools/validate_ui_strings.py")
    old = '''    assert 'id="view-console"' in html and 'id="embeddedConsoleForm"' in html\n    assert 'data-view="console"' in html and 'id="accountConsoleBtn"' not in html\n    assert 'id="accountSettingsBtn"' in html and '>Account settings</button>' in html\n    assert "$('#accountSettingsBtn').addEventListener('click'" in app_js\n    assert 'login-gradient-pulse' not in app_css and 'login-radiant-glow' not in html\n    assert 'data-settings-page="backups"' in html and 'data-settings-section="backups"' in html\n    assert 'id="backupProgress"' in html and 'class="backup-progress hidden"' in html\n    assert 'backup-delete' in settings_js and "post('/api/backups/delete',{name})" in settings_js\n    assert 'path=="/api/backups/delete"' in dashboard_py and 'backup_deleted' in dashboard_py\n    assert 'const embeddedConsoleState=' in app_js and "post('/api/recovery/command',{command})" in app_js\n'''
    new = '''    assert 'id="view-console"' not in html and 'id="embeddedConsoleForm"' not in html\n    assert 'data-view="console"' not in html and 'id="accountConsoleBtn"' not in html\n    assert 'id="accountSettingsBtn"' in html and '>Account settings</button>' in html\n    assert "$('#accountSettingsBtn').addEventListener('click'" in app_js\n    assert 'login-gradient-pulse' not in app_css and 'login-radiant-glow' not in html\n    assert 'data-settings-page="backups"' in html and 'data-settings-section="backups"' in html\n    assert 'id="backupProgress"' in html and 'class="backup-progress hidden"' in html\n    assert 'backup-delete' in settings_js and "post('/api/backups/delete',{name})" in settings_js\n    assert 'path=="/api/backups/delete"' in dashboard_py and 'backup_deleted' in dashboard_py\n    assert 'embeddedConsole' not in app_js and '/api/recovery/command' not in app_js\n    assert '/api/recovery/command' not in dashboard_py and 'recovery_console_execute' not in dashboard_py\n    assert 'Recovery.exe' in html\n'''
    ui = replace_once(ui, old, new, "UI console contract")
    write("release_tools/validate_ui_strings.py", ui)

    security = read("tests/test_http_security.py")
    security = regex_once(
        security,
        r"    def test_recovery_console_rechecks_bypass_authorization\(self\):.*?(?=\n    def test_restore_cannot_overlap_a_launched_updater)",
        '''    def test_recovery_console_endpoint_is_removed(self):\n        token, session = self.sessions.create("admin", 24, "password", group="administrator")\n        request = self.request("/api/recovery/command", token, session["csrf"])\n        request.do_POST()\n        self.assertEqual(request.send_json.call_args.args[0], 404)\n        self.assertFalse(hasattr(dashboard, "recovery_console_execute"))\n\n''',
        "HTTP console removal test",
        re.S,
    )
    write("tests/test_http_security.py", security)

    local = read("tests/test_local_recovery.py")
    insertion = '''\n    def test_recovery_command_parser_supports_quoted_identifiers(self):\n        self.assertEqual(rt.parse_command('client test "desktop one"'), ["client", "test", "desktop one"])\n        with self.assertRaisesRegex(RuntimeError, "one recovery command"):\n            rt.parse_command("status\\nhelp")\n\n    def test_local_help_contains_migrated_console_operations(self):\n        with mock.patch("builtins.print") as output:\n            rt.print_help()\n        rendered = "\\n".join(str(call.args[0]) for call in output.call_args_list if call.args)\n        for command in ("client list", "integration list", "torrent list", "jellyfin list", "users", "events"):\n            self.assertIn(command, rendered)\n        self.assertIn("does not expose", rendered)\n'''
    local = replace_once(local, "\n\nif __name__ == \"__main__\":\n", insertion + "\n\nif __name__ == \"__main__\":\n", "local recovery migration tests")
    write("tests/test_local_recovery.py", local)

    for path in (
        ROOT / "src" / "torrent_dashboard" / "recovery_console.py",
        ROOT / "tests" / "test_recovery_console.py",
        ROOT / "tests" / "test_recovery_console_runtime.py",
    ):
        path.unlink()


def patch_docs() -> None:
    readme = read("README.md")
    marker = "## Security and Privacy\n"
    section = '''## Local recovery\n\nThe dashboard does not expose an embedded command console. Administrative diagnostics and recovery commands run locally through `Recovery.exe` on Windows or `torrent-dashboard-recovery` from the source package. The local recovery tool requires the setup-generated recovery key and never starts a listening recovery server. It can inspect redacted configuration, clients, integrations, users, history events, live qBittorrent torrent state, and Jellyfin tasks; its torrent mutations are limited to start, stop, recheck, and reannounce.\n\nThe browser recovery-key sign-in remains a separate account-recovery path; it does not expose the local command surface.\n\n'''
    if section not in readme:
        readme = replace_once(readme, marker, section + marker, "README recovery section")
    write("README.md", readme)

    architecture = read("ARCHITECTURE.md")
    marker = "### `src/torrent_dashboard/updater.py`\n"
    section = '''### `src/torrent_dashboard/recovery_tool.py` and `recovery_operations.py`\n\nOwn the out-of-band, recovery-key-gated command surface. `recovery_tool.py` handles local authentication, config backup/restore, update orchestration, command parsing, and terminal interaction. `recovery_operations.py` owns direct diagnostic/service operations needed outside the running dashboard, including redacted configuration/account inspection, qBittorrent client tests and safe torrent actions, integration tests, Jellyfin scheduled-task operations, and local history reads. Neither module imports the dashboard composition root or starts a listening server.\n\nThe browser application intentionally has no embedded command console and no `/api/recovery/command` execution endpoint. Browser recovery-key sign-in remains an authentication-recovery path rather than a general command channel.\n\n'''
    if section not in architecture:
        architecture = replace_once(architecture, marker, section + marker, "architecture recovery boundary")
    write("ARCHITECTURE.md", architecture)

    testing = read("TESTING.md")
    marker = "- A deliberately invalid test build rolls back rather than leaving the installation unusable.\n"
    extra = '''- The authenticated dashboard has no Console navigation/view and `/api/recovery/command` is not exposed.\n- `Recovery.exe` accepts the setup recovery key, lists configured clients/integrations/users/events, and can fetch live torrent identifiers directly from qBittorrent.\n- `Recovery.exe` client/integration tests and Jellyfin task listing work without importing or starting the dashboard HTTP application.\n- Recovery torrent mutations accept only start, stop, recheck, and reannounce; destructive torrent deletion is rejected.\n'''
    if extra not in testing:
        testing = replace_once(testing, marker, marker + extra, "testing recovery migration")
    write("TESTING.md", testing)


def patch_release_state() -> None:
    init = read("src/torrent_dashboard/__init__.py")
    init = replace_once(init, '__version__ = "0.5.152"', f'__version__ = "{VERSION}"', "package version")
    write("src/torrent_dashboard/__init__.py", init)

    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not any(item.get("version") == VERSION for item in data.get("releases", [])):
        data["releases"].insert(0, {
            "version": VERSION,
            "date": "2026-09-11",
            "status": "prerelease",
            "title": "Local recovery command migration",
            "summary": "Removes the embedded dashboard Console and moves its diagnostic and safe operational command surface into the recovery-key-gated local Recovery tool.",
            "highlights": [
                "Removes Console from desktop/mobile navigation, deletes the embedded terminal UI, and removes the authenticated /api/recovery/command endpoint.",
                "Expands Recovery.exe with redacted config, client, integration, torrent, Jellyfin, users, events, and update diagnostics while retaining existing config backup/restore and network recovery commands.",
                "Fetches torrent identifiers and state directly from qBittorrent in local recovery instead of depending on the running dashboard cache.",
                "Keeps browser recovery-key sign-in as a separate account-recovery path without exposing command execution through the dashboard."
            ],
            "fixes": [
                "Narrows the dashboard HTTP attack surface by removing the general allowlisted recovery-command dispatcher from the web application.",
                "Keeps safe torrent and Jellyfin operational recovery available when the dashboard UI is unavailable by moving those operations to the local executable."
            ],
            "technical": [
                "Adds recovery_operations.py as a dashboard-independent local operations boundary with direct qBittorrent authentication, client testing, live torrent listing, and a start/stop/recheck/reannounce allowlist.",
                "Deletes recovery_console.py and its dashboard runtime cache coupling; Recovery.exe remains a non-listening process and does not import the dashboard composition root.",
                "Recovery update install/apply now uses the existing standalone verified updater path; a separate staged-download command is intentionally not retained in Recovery.exe."
            ],
            "validation": [
                "Adds unit coverage for secret redaction, client identifiers, live torrent normalization, the safe torrent action allowlist, Jellyfin task lookup, and local history event reads.",
                "Changes the HTTP security contract to assert /api/recovery/command is absent while preserving /api/recovery/login.",
                "Changes UI contract validation to fail if Console navigation, embeddedConsole JavaScript/CSS, or the removed recovery command endpoint reappears."
            ],
            "known_issues": [
                "Portable backup archives can contain saved client and integration credentials in plaintext; store exported .tdbackup files securely.",
                "Windows executables are not code-signed yet."
            ],
            "architecture": [
                "Operational recovery commands belong to the local recovery executable rather than the browser/HTTP composition root."
            ],
            "decisions": [
                "Keep browser recovery-key sign-in as a separate authentication recovery path while removing browser command execution.",
                "Keep Recovery.exe non-listening and dashboard-independent; service diagnostics connect directly to configured endpoints.",
                "Limit Recovery.exe torrent mutations to the former safe action allowlist and do not add delete or other destructive torrent operations."
            ],
            "next_steps": [
                {
                    "priority": 1,
                    "title": "Exercise Recovery.exe migration on compiled Windows",
                    "detail": "Install v0.5.153 through the built-in updater, confirm Console is absent from the dashboard, then validate Recovery.exe client/integration/torrent/Jellyfin/users/events commands plus update and backup recovery flows."
                }
            ]
        })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    current = {
        "schema": 1,
        "status": "ready",
        "objective": "Validate v0.5.153 local Recovery.exe command migration on compiled Windows",
        "why": "The embedded dashboard Console and its HTTP command endpoint have been removed; the remaining risk is compiled-Windows validation of the expanded out-of-band recovery surface and updater flow.",
        "acceptance_criteria": [
            "Source/unit, UI, syntax, generated-documentation, hygiene, source-package, and pull-request matrix checks pass.",
            "The dashboard exposes no Console navigation/view and no /api/recovery/command endpoint, while browser recovery-key sign-in still works as an authentication-recovery path.",
            "Recovery.exe lists and tests configured clients/integrations, lists live torrents and Jellyfin tasks, and shows redacted config/users/events after recovery-key authentication.",
            "Recovery.exe torrent mutations remain limited to start, stop, recheck, and reannounce.",
            "The built-in updater installs the compiled v0.5.153 package and the existing portable backup lifecycle remains intact."
        ],
        "decisions": [
            "Keep command execution out of the dashboard HTTP surface.",
            "Keep browser recovery-key sign-in separate from the local command surface.",
            "Use direct service connections from Recovery.exe instead of importing dashboard.py or depending on its in-memory torrent cache.",
            "Do not add destructive torrent mutations to local recovery."
        ],
        "files": [
            "src/torrent_dashboard/recovery_tool.py",
            "src/torrent_dashboard/recovery_operations.py",
            "src/torrent_dashboard/dashboard.py",
            "tests/test_recovery_operations.py",
            "tests/test_local_recovery.py",
            "tests/test_http_security.py",
            "static/index.html",
            "static/app.js",
            "static/app.css",
            "release_tools/validate_ui_strings.py",
            "release_notes/releases.json"
        ],
        "blockers": [],
        "out_of_scope": [
            "Removing browser recovery-key sign-in, backup encryption, scheduled backups, cloud destinations, code signing, broader authentication redesign, and destructive Recovery.exe torrent actions."
        ],
        "next_action": "Install v0.5.153 on compiled Windows, verify the dashboard has no Console surface, then exercise Recovery.exe diagnostics/actions and repeat updater plus portable-backup recovery flows."
    }
    (ROOT / "development" / "current.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def final_contract_checks() -> None:
    source = read("src/torrent_dashboard/dashboard.py")
    frontend = read("static/app.js") + read("static/index.html") + read("static/app.css")
    for marker in ("/api/recovery/command", "recovery_console_execute", "recovery_console.py"):
        if marker in source:
            raise RuntimeError(f"removed dashboard console marker remains: {marker}")
    for marker in ("view-console", "embeddedConsole", "data-view=\"console\""):
        if marker in frontend:
            raise RuntimeError(f"removed frontend console marker remains: {marker}")
    if "/api/recovery/login" not in source or "recoveryLoginForm" not in read("static/index.html"):
        raise RuntimeError("browser recovery-key sign-in was removed outside requested scope")


def main() -> None:
    patch_dashboard()
    patch_recovery_tool()
    patch_frontend()
    patch_validators_and_tests()
    patch_docs()
    patch_release_state()
    final_contract_checks()
    print("Recovery console migration applied")


if __name__ == "__main__":
    main()
