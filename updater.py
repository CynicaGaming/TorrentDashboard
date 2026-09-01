#!/usr/bin/env python3
"""Torrent Dashboard out-of-process update installer.

This helper is launched by dashboard.py after an update package has been
verified and staged. It waits for the running dashboard process to exit,
overlays the new application files while preserving config/data, restarts the
app, and rolls back overwritten files if the new version fails its health check.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PRESERVE_TOP_LEVEL = {"config.json", "data", ".git"}


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def wait_for_exit(pid: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.25)
    return not process_exists(pid)


def iter_release_files(source: Path):
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if rel.parts and rel.parts[0] in PRESERVE_TOP_LEVEL:
            continue
        if "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        yield path, rel


def apply_update(source: Path, target: Path, backup_root: Path):
    backup_root.mkdir(parents=True, exist_ok=True)
    overwritten, created = [], []
    for src, rel in iter_release_files(source):
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            b = backup_root / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, b)
            overwritten.append(str(rel))
        else:
            created.append(str(rel))
        shutil.copy2(src, dst)
    state = {"overwritten": overwritten, "created": created}
    (backup_root / "rollback.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def rollback(target: Path, backup_root: Path, state: dict):
    for rel in state.get("created", []):
        p = target / rel
        try:
            if p.exists() and p.is_file():
                p.unlink()
        except Exception:
            pass
    for rel in state.get("overwritten", []):
        src = backup_root / rel
        dst = target / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def start_dashboard(target: Path):
    cmd = [sys.executable, str(target / "dashboard.py"), "--no-browser"]
    kwargs = {"cwd": str(target), "stdin": subprocess.DEVNULL}
    log_dir = target / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = open(log_dir / "update-restart.log", "ab", buffering=0)
    kwargs["stdout"] = log
    kwargs["stderr"] = log
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs), log


def health_url(target: Path, fallback_port: int = 8765):
    cfg_path = target / "config.json"
    scheme, port = "http", fallback_port
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        dash = cfg.get("dashboard", {})
        port = int(dash.get("port", fallback_port))
        scheme = "https" if dash.get("https_enabled") else "http"
    except Exception:
        pass
    return f"{scheme}://127.0.0.1:{port}/health"


def wait_for_health(url: str, expected_version: str, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    ctx = ssl._create_unverified_context() if url.startswith("https://") else None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok") and str(data.get("version")) == expected_version:
                    return True
        except Exception:
            pass
        time.sleep(0.75)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.is_dir() or not (source / "dashboard.py").exists():
        raise SystemExit("Invalid staged update source")

    data_dir = target / "data"
    backup_root = data_dir / "update-backups" / f"pre-{args.version}-{int(time.time())}"
    status_path = data_dir / "update-status.json"
    data_dir.mkdir(parents=True, exist_ok=True)

    status_path.write_text(json.dumps({"state": "waitingForShutdown", "version": args.version}), encoding="utf-8")
    if not wait_for_exit(args.pid):
        status_path.write_text(json.dumps({"state": "failed", "error": "dashboardDidNotStop", "version": args.version}), encoding="utf-8")
        raise SystemExit(2)

    state = apply_update(source, target, backup_root)
    status_path.write_text(json.dumps({"state": "restarting", "version": args.version}), encoding="utf-8")
    proc, log = start_dashboard(target)
    url = health_url(target)
    if wait_for_health(url, args.version):
        status_path.write_text(json.dumps({"state": "installed", "version": args.version, "backup": str(backup_root)}), encoding="utf-8")
        log.close()
        return

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    rollback(target, backup_root, state)
    status_path.write_text(json.dumps({"state": "rolledBack", "version": args.version}), encoding="utf-8")
    try:
        old_proc, old_log = start_dashboard(target)
        old_log.close()
    except Exception as exc:
        status_path.write_text(json.dumps({"state": "rollbackRestartFailed", "version": args.version, "error": str(exc)}), encoding="utf-8")
    log.close()
    raise SystemExit(3)


if __name__ == "__main__":
    main()
