#!/usr/bin/env python3
"""Torrent Dashboard update and recovery installer.

Normal dashboard updates launch this helper after a release has already been
verified and staged. Recovery mode (``--github-update``) works without the web
UI: it discovers the latest GitHub prerelease, verifies GitHub's SHA-256 asset
digest, extracts the release, installs it with a backup, restarts the dashboard,
and rolls back if the new version fails its health check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

PRESERVE_TOP_LEVEL = {"config.json", "data", ".git"}
DEFAULT_REPOSITORY = "CynicaGaming/TorrentDashboard"
GITHUB_API = "https://api.github.com"
USER_AGENT = "Torrent-Dashboard-Recovery-Updater"


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


def dashboard_instance_running() -> bool:
    """Check the same machine-level guard used by dashboard.py."""
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, "Local\\TorrentDashboard.SingleInstance")
        if not handle:
            return True
        already_exists = kernel32.GetLastError() == 183
        kernel32.CloseHandle(handle)
        return already_exists

    import fcntl
    lock_path = Path(tempfile.gettempdir()) / "torrent-dashboard.lock"
    lock_file = open(lock_path, "a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        return False
    finally:
        lock_file.close()


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


def current_version(target: Path) -> str:
    text = (target / "dashboard.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', text, re.M)
    return match.group(1) if match else "0.0.0"


def version_key(value: str):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value or "").strip())
    if not match:
        return None
    return tuple(int(x) for x in match.groups())


def configured_repository(target: Path) -> str:
    repo = DEFAULT_REPOSITORY
    try:
        cfg = json.loads((target / "config.json").read_text(encoding="utf-8"))
        repo = str(cfg.get("updates", {}).get("repository") or repo).strip()
    except Exception:
        pass
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RuntimeError(f"Invalid GitHub repository: {repo}")
    return repo


def github_json(url: str):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def newest_release(repository: str):
    releases = github_json(f"{GITHUB_API}/repos/{repository}/releases?per_page=30")
    candidates = []
    for release in releases if isinstance(releases, list) else []:
        if release.get("draft"):
            continue
        version = str(release.get("tag_name") or "").lstrip("v")
        key = version_key(version)
        if not key:
            continue
        expected_name = f"Torrent-Dashboard-{version}.zip"
        asset = next((x for x in release.get("assets", []) if x.get("name") == expected_name), None)
        if not asset:
            continue
        candidates.append((key, version, release, asset))
    if not candidates:
        raise RuntimeError("No installable Torrent Dashboard GitHub release was found")
    return max(candidates, key=lambda x: x[0])[1:]


def download_file(url: str, destination: Path):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=60) as resp, destination.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            h.update(chunk)
    return h.hexdigest()


def extract_release(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            candidate = (destination / member.filename).resolve()
            if candidate != root and root not in candidate.parents:
                raise RuntimeError("Release archive contains an unsafe path")
        zf.extractall(destination)
    if (destination / "dashboard.py").exists():
        return destination
    roots = [p for p in destination.iterdir() if p.is_dir() and (p / "dashboard.py").exists()]
    if len(roots) != 1:
        raise RuntimeError("Release archive does not contain a valid Torrent Dashboard application")
    return roots[0]


def validate_staged_source(source: Path, expected_version: str):
    for name in ("dashboard.py", "updater.py"):
        path = source / name
        if not path.exists():
            raise RuntimeError(f"Release is missing {name}")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    if current_version(source) != expected_version:
        raise RuntimeError("Release version does not match the downloaded package")


def recovery_update(target: Path, repository: str | None = None, force: bool = False):
    target = target.resolve()
    if dashboard_instance_running():
        raise RuntimeError(
            "Torrent Dashboard is still running. Close the existing dashboard/Python process, then run the recovery update again."
        )

    repository = repository or configured_repository(target)
    installed = current_version(target)
    version, release, asset = newest_release(repository)
    if not force and version_key(version) <= version_key(installed):
        print(f"Torrent Dashboard {installed} is already current.")
        return

    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise RuntimeError("GitHub did not provide a SHA-256 digest for the release asset")
    expected_digest = digest.partition(":")[2].lower()
    download_url = str(asset.get("browser_download_url") or "")
    if not download_url.startswith("https://github.com/"):
        raise RuntimeError("Release asset has an invalid download URL")

    print(f"Installed version: {installed}")
    print(f"Latest version:    {version}")
    print(f"Repository:        {repository}")
    print("Downloading and verifying release...")

    data_dir = target / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    status_path = data_dir / "update-status.json"
    with tempfile.TemporaryDirectory(prefix="recovery-update-", dir=str(data_dir)) as tmp_name:
        tmp = Path(tmp_name)
        archive = tmp / str(asset.get("name") or f"Torrent-Dashboard-{version}.zip")
        actual_digest = download_file(download_url, archive)
        if actual_digest.lower() != expected_digest:
            raise RuntimeError(
                f"Release SHA-256 verification failed (expected {expected_digest}, got {actual_digest})"
            )
        source = extract_release(archive, tmp / "release")
        validate_staged_source(source, version)

        backup_root = data_dir / "update-backups" / f"pre-{version}-{int(time.time())}"
        status_path.write_text(json.dumps({"state": "installingRecovery", "version": version}), encoding="utf-8")
        state = apply_update(source, target, backup_root)
        status_path.write_text(json.dumps({"state": "restarting", "version": version}), encoding="utf-8")
        proc, log = start_dashboard(target)
        if wait_for_health(health_url(target), version):
            status_path.write_text(
                json.dumps({"state": "installed", "version": version, "backup": str(backup_root)}),
                encoding="utf-8",
            )
            log.close()
            print(f"Torrent Dashboard {version} installed and restarted successfully.")
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
        status_path.write_text(json.dumps({"state": "rolledBack", "version": version}), encoding="utf-8")
        try:
            _, old_log = start_dashboard(target)
            old_log.close()
        except Exception as exc:
            status_path.write_text(
                json.dumps({"state": "rollbackRestartFailed", "version": version, "error": str(exc)}),
                encoding="utf-8",
            )
        log.close()
        raise RuntimeError("The updated dashboard failed its health check and was rolled back")


def normal_update(args):
    missing = [name for name in ("pid", "source", "target", "version") if getattr(args, name) in (None, "")]
    if missing:
        raise RuntimeError("Normal update mode requires --pid, --source, --target, and --version")

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.is_dir() or not (source / "dashboard.py").exists():
        raise RuntimeError("Invalid staged update source")

    data_dir = target / "data"
    backup_root = data_dir / "update-backups" / f"pre-{args.version}-{int(time.time())}"
    status_path = data_dir / "update-status.json"
    data_dir.mkdir(parents=True, exist_ok=True)

    status_path.write_text(json.dumps({"state": "waitingForShutdown", "version": args.version}), encoding="utf-8")
    if not wait_for_exit(args.pid):
        status_path.write_text(json.dumps({"state": "failed", "error": "dashboardDidNotStop", "version": args.version}), encoding="utf-8")
        raise RuntimeError("Dashboard did not stop before the update timeout")

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
        _, old_log = start_dashboard(target)
        old_log.close()
    except Exception as exc:
        status_path.write_text(json.dumps({"state": "rollbackRestartFailed", "version": args.version, "error": str(exc)}), encoding="utf-8")
    log.close()
    raise RuntimeError("Updated dashboard failed its health check and was rolled back")


def main():
    ap = argparse.ArgumentParser(description="Torrent Dashboard updater and recovery tool")
    ap.add_argument("--github-update", action="store_true", help="Update directly from the configured GitHub releases without using the dashboard UI")
    ap.add_argument("--repository", help="Override the configured owner/repository for recovery mode")
    ap.add_argument("--force", action="store_true", help="Reinstall the latest release even when the version is unchanged")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--source")
    ap.add_argument("--target")
    ap.add_argument("--version")
    args = ap.parse_args()

    try:
        if args.github_update:
            recovery_update(Path(__file__).resolve().parent, args.repository, args.force)
        else:
            normal_update(args)
    except Exception as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
