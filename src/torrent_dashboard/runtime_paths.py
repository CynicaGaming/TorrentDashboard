"""Runtime path helpers shared by source and packaged Torrent Dashboard builds."""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Return the writable installation directory containing runtime state/assets."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    here = Path(__file__).resolve()
    # Legacy layout: <root>/torrent_dashboard/runtime_paths.py
    # Src layout:    <root>/src/torrent_dashboard/runtime_paths.py
    if here.parent.parent.name == "src":
        return here.parents[2]
    return here.parents[1]


def source_root(target: Path | None = None) -> Path:
    return (target or app_dir()).resolve() / "src"


def dashboard_source(target: Path | None = None) -> Path | None:
    target = (target or app_dir()).resolve()
    candidates = (
        target / "src" / "torrent_dashboard" / "runtime.py",
        target / "src" / "torrent_dashboard" / "dashboard.py",
        target / "dashboard.py",
    )
    return next((path for path in candidates if path.is_file()), None)


def updater_source(target: Path | None = None) -> Path | None:
    target = (target or app_dir()).resolve()
    candidates = (
        target / "src" / "torrent_dashboard" / "updater.py",
        target / "updater.py",
    )
    return next((path for path in candidates if path.is_file()), None)


def recovery_source(target: Path | None = None) -> Path | None:
    target = (target or app_dir()).resolve()
    candidates = (
        target / "src" / "torrent_dashboard" / "recovery_tool.py",
        target / "recovery_tool.py",
    )
    return next((path for path in candidates if path.is_file()), None)


def source_python_env(target: Path | None = None) -> dict[str, str]:
    """Return an environment that can import the src-layout package when present."""
    target = (target or app_dir()).resolve()
    env = dict(os.environ)
    src = target / "src"
    if src.is_dir():
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(src) + (os.pathsep + existing if existing else "")
    return env


def runtime_distribution(target: Path | None = None) -> str:
    """Return the release artifact family appropriate for this installation."""
    target = (target or app_dir()).resolve()
    if os.name == "nt" and (is_frozen() or (target / "Dashboard.exe").is_file()):
        return "windows-x64"
    return "source"


def _source_interpreter() -> str:
    if not is_frozen():
        return sys.executable
    interpreter = shutil.which("python") or shutil.which("python3")
    if not interpreter:
        raise RuntimeError("No Python interpreter is available for the source installation")
    return interpreter


def dashboard_command(target: Path | None = None, *, no_browser: bool = True) -> list[str]:
    """Return a command that starts Dashboard in packaged or source installs."""
    target = (target or app_dir()).resolve()
    executable = target / ("Dashboard.exe" if os.name == "nt" else "Dashboard")
    if executable.is_file():
        command = [str(executable)]
    else:
        source = dashboard_source(target)
        if source is None:
            raise RuntimeError("Dashboard executable/source is missing")
        command = [_source_interpreter(), str(source)]
    if no_browser:
        command.append("--no-browser")
    return command


def _detached_updater_copy(executable: Path, target: Path) -> Path:
    """Copy standalone Updater.exe outside the managed install before replacement."""
    runner_dir = target / "data" / "update-runner"
    runner_dir.mkdir(parents=True, exist_ok=True)
    # Best-effort cleanup of old detached runners. Never remove the current process.
    now = time.time()
    for path in runner_dir.glob("Updater-*.exe"):
        try:
            if now - path.stat().st_mtime > 86400:
                path.unlink()
        except Exception:
            pass
    runner = runner_dir / f"Updater-{os.getpid()}-{int(now * 1000)}.exe"
    shutil.copy2(executable, runner)
    return runner


def updater_command(target: Path | None = None, *, detached: bool = False) -> list[str]:
    """Return the packaged updater when present, otherwise the source updater.

    Packaged updates use a detached copy so Windows can replace the installed
    Updater.exe while the update process itself is still running.
    """
    target = (target or app_dir()).resolve()
    executable = target / ("Updater.exe" if os.name == "nt" else "Updater")
    if executable.is_file():
        if detached and os.name == "nt":
            executable = _detached_updater_copy(executable, target)
        return [str(executable)]
    source = updater_source(target)
    if source is None:
        raise RuntimeError("Updater executable/source is missing")
    return [_source_interpreter(), str(source)]


def recovery_command(target: Path | None = None) -> list[str]:
    target = (target or app_dir()).resolve()
    executable = target / ("Recovery.exe" if os.name == "nt" else "Recovery")
    if executable.is_file():
        return [str(executable)]
    source = recovery_source(target)
    if source is None:
        raise RuntimeError("Recovery executable/source is missing")
    return [_source_interpreter(), str(source)]
