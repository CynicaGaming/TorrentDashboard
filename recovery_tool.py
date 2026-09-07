#!/usr/bin/env python3
"""Key-gated local recovery tool for Torrent Dashboard.

This program never starts an HTTP server. It is intended to remain usable when
the dashboard UI or HTTP service cannot start. Update operations make outbound
HTTPS requests to GitHub through updater.py.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import re
import shutil
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DATA_DIR = APP_DIR / "data"
BACKUP_DIR = DATA_DIR / "recovery-backups"
UPDATE_STATE_PATH = DATA_DIR / "update-status.json"
UPDATES_DIR = DATA_DIR / "updates"
DEFAULT_REPOSITORY = "CynicaGaming/TorrentDashboard"
RECOVERY_KEY_PREFIX = "TDRK"


def normalize_recovery_key(value: str) -> str:
    raw = str(value or "").strip().upper()
    return "".join(ch for ch in raw if ch not in "- \t\r\n")


def verify_pbkdf2(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = str(encoded or "").split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        pad = lambda value: value + "=" * (-len(value) % 4)
        salt = base64.urlsafe_b64decode(pad(salt_b64))
        expected = base64.urlsafe_b64decode(pad(digest_b64))
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(expected, got)
    except Exception:
        return False


def load_config(path: Path | None = None) -> dict:
    path = path or CONFIG_PATH
    if not path.exists():
        raise RuntimeError(f"Configuration file was not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Configuration file is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Configuration root must be a JSON object")
    return value


def recovery_key_hash(cfg: dict) -> str:
    recovery = cfg.get("recovery") if isinstance(cfg.get("recovery"), dict) else {}
    return str(recovery.get("key_hash") or "")


def authenticate_key(cfg: dict, supplied: str) -> bool:
    encoded = recovery_key_hash(cfg)
    if not encoded:
        raise RuntimeError("This dashboard has no setup-generated recovery key. Local recovery cannot be unlocked.")
    normalized = normalize_recovery_key(supplied)
    return normalized.startswith(RECOVERY_KEY_PREFIX) and len(normalized) >= 40 and verify_pbkdf2(normalized, encoded)


def require_recovery_key(cfg: dict) -> None:
    for remaining in range(5, 0, -1):
        supplied = getpass.getpass("Recovery key: ")
        if authenticate_key(cfg, supplied):
            return
        if remaining > 1:
            print(f"Invalid recovery key. {remaining - 1} attempt(s) remaining.", file=sys.stderr)
    raise RuntimeError("Recovery authentication failed")


def normalize_repository(value: str) -> str:
    value = str(value or "").strip().removesuffix(".git").strip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip("/")
            break
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise RuntimeError("GitHub repository must be owner/repository")
    return value


def configured_repository(cfg: dict) -> str:
    updates = cfg.get("updates") if isinstance(cfg.get("updates"), dict) else {}
    return normalize_repository(updates.get("repository") or DEFAULT_REPOSITORY)


def atomic_write_config(cfg: dict, path: Path | None = None) -> None:
    path = path or CONFIG_PATH
    tmp = path.with_suffix(path.suffix + ".recovery.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def backup_config(path: Path | None = None) -> Path:
    path = path or CONFIG_PATH
    if not path.exists():
        raise RuntimeError("config.json does not exist")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"config-{stamp}.json"
    index = 1
    while dest.exists():
        dest = BACKUP_DIR / f"config-{stamp}-{index}.json"
        index += 1
    shutil.copy2(path, dest)
    return dest


def list_backups() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("config-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_config(name: str) -> Path:
    candidate = (BACKUP_DIR / Path(str(name)).name).resolve()
    if BACKUP_DIR.resolve() not in candidate.parents or not candidate.is_file():
        raise RuntimeError("Recovery config backup was not found")
    restored = load_config(candidate)
    if not recovery_key_hash(restored):
        raise RuntimeError("Refusing to restore a config backup without a recovery key")
    backup_config()
    atomic_write_config(restored)
    return candidate


def set_repository(cfg: dict, repository: str) -> str:
    repository = normalize_repository(repository)
    backup_config()
    cfg.setdefault("updates", {})["repository"] = repository
    atomic_write_config(cfg)
    return repository


def current_version() -> str:
    text = (APP_DIR / "dashboard.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', text, re.M)
    return match.group(1) if match else "unknown"


def updater_module():
    try:
        import updater
        return updater
    except Exception as exc:
        raise RuntimeError(f"updater.py could not be loaded: {exc}") from exc


def validation_report(cfg: dict) -> list[tuple[str, bool, str]]:
    rows = [
        ("config.json parses", True, str(CONFIG_PATH)),
        ("setup complete", bool(cfg.get("setup", {}).get("complete")), "setup.complete"),
        ("recovery key", bool(recovery_key_hash(cfg)), "setup-generated key hash present"),
    ]
    try:
        rows.append(("update repository", True, configured_repository(cfg)))
    except Exception as exc:
        rows.append(("update repository", False, str(exc)))
    for name in ("dashboard.py", "updater.py", "recovery_tool.py"):
        path = APP_DIR / name
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            rows.append((f"{name} syntax", True, "OK"))
        except Exception as exc:
            rows.append((f"{name} syntax", False, str(exc)))
    return rows


def show_status(cfg: dict) -> None:
    upd = updater_module()
    recovery = cfg.get("recovery", {}) if isinstance(cfg.get("recovery"), dict) else {}
    print(f"Application:       {APP_DIR}")
    print(f"Installed version: {current_version()}")
    print(f"Python:            {sys.executable}")
    print(f"Repository:        {configured_repository(cfg)}")
    print(f"Dashboard running: {'yes' if upd.dashboard_instance_running() else 'no'}")
    print(f"Recovery key:      configured · …{str(recovery.get('last4') or '')}")
    if UPDATE_STATE_PATH.exists():
        try:
            state = json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
            print(f"Update state:      {state.get('state','unknown')}" + (f" · {state.get('version')}" if state.get('version') else ""))
        except Exception:
            print("Update state:      unreadable")
    else:
        print("Update state:      none")


def check_update(cfg: dict):
    upd = updater_module()
    repo = configured_repository(cfg)
    installed = current_version()
    version, release, asset = upd.newest_release(repo)
    print(f"Installed version: {installed}")
    print(f"Latest version:    {version}")
    print(f"Repository:        {repo}")
    print(f"Channel:           {'prerelease' if release.get('prerelease') else 'stable'}")
    print(f"Published:         {release.get('published_at') or release.get('created_at') or 'unknown'}")
    if upd.version_key(installed) and upd.version_key(version):
        relation = "update available" if upd.version_key(version) > upd.version_key(installed) else "current"
        print(f"Status:            {relation}")
    return installed, version, release, asset


def install_update(cfg: dict, force: bool = False) -> None:
    upd = updater_module()
    repo = configured_repository(cfg)
    if upd.dashboard_instance_running():
        raise RuntimeError("Stop Torrent Dashboard before installing from local recovery")
    upd.recovery_update(APP_DIR, repo, force=force)


def network_reset(cfg: dict) -> None:
    backup_config()
    dashboard = cfg.setdefault("dashboard", {})
    dashboard["bind_host"] = "0.0.0.0"
    dashboard["port"] = 8765
    dashboard["https_enabled"] = False
    dashboard["https_cert"] = ""
    dashboard["https_key"] = ""
    atomic_write_config(cfg)
    print("Network settings reset to 0.0.0.0:8765 with HTTPS disabled.")


def clear_update_state() -> None:
    UPDATE_STATE_PATH.unlink(missing_ok=True)
    if UPDATES_DIR.exists():
        shutil.rmtree(UPDATES_DIR, ignore_errors=True)
    print("Staged update files and update-status.json were cleared.")


def start_dashboard() -> None:
    upd = updater_module()
    if upd.dashboard_instance_running():
        print("Torrent Dashboard is already running.")
        return
    proc, log = upd.start_dashboard(APP_DIR)
    log.close()
    print(f"Torrent Dashboard start requested. PID {proc.pid}.")
    print(f"Startup log: {DATA_DIR / 'update-restart.log'}")


def tail_log(lines: int = 80) -> None:
    path = DATA_DIR / "update-restart.log"
    if not path.exists():
        print("No recovery/update restart log exists yet.")
        return
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in text[-max(1, min(500, int(lines))) :]:
        print(line)


def confirm(prompt: str, token: str = "YES") -> bool:
    return input(f"{prompt} Type {token} to continue: ").strip() == token


def print_help() -> None:
    print("""
Commands:
  status                     Show local installation and recovery state
  validate                   Validate config and critical Python files
  repo                       Show the configured GitHub repository
  repo <owner/repository>    Back up config and change the update repository
  check                      Check the configured repository for releases
  install                    Install the latest newer verified release
  reinstall                  Reinstall the latest verified release
  backup                     Back up config.json
  backups                    List local config backups
  restore <backup-file>      Restore a recovery config backup
  network-reset              Reset bind to 0.0.0.0:8765 and disable HTTPS
  clear-update               Clear a stuck staged update and update status
  start                      Start Torrent Dashboard without opening a browser
  log [lines]                Show the recovery/update restart log
  help                       Show this help
  exit                       Exit local recovery

This is not an operating-system shell. No command starts a listening server.
""".strip())


def execute(command: str, cfg: dict) -> dict:
    parts = str(command or "").strip().split()
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
    elif op == "repo":
        if len(parts) == 1:
            print(configured_repository(cfg))
        elif len(parts) == 2:
            value = set_repository(cfg, parts[1])
            cfg = load_config()
            print(f"Update repository set to {value}.")
        else:
            raise RuntimeError("Usage: repo [owner/repository]")
    elif op == "check":
        check_update(cfg)
    elif op in ("install", "reinstall"):
        action = "reinstall" if op == "reinstall" else "install"
        if not confirm(f"This will {action} Torrent Dashboard from {configured_repository(cfg)}."):
            print("Cancelled.")
        else:
            install_update(cfg, force=op == "reinstall")
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
        tail_log(int(parts[1]) if len(parts) > 1 else 80)
    else:
        raise RuntimeError("Unknown recovery command. Type help.")
    return cfg


def interactive(cfg: dict) -> None:
    print(f"\nTorrent Dashboard Local Recovery · {current_version()}")
    print("Authenticated with the setup recovery key. Type help for commands.\n")
    while True:
        try:
            cfg = execute(input("recovery> "), cfg)
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            print("\nUse exit to leave local recovery.")
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Torrent Dashboard local recovery tool")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Optional recovery command to run after authentication")
    args = parser.parse_args(argv)
    try:
        cfg = load_config()
        require_recovery_key(cfg)
        if args.command:
            execute(" ".join(args.command), cfg)
        else:
            interactive(cfg)
        return 0
    except Exception as exc:
        print(f"Recovery failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
