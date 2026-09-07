"""Runtime path helpers shared by source and packaged Torrent Dashboard builds."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Return the writable installation directory containing the executables/source."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def dashboard_command(target: Path | None = None, *, no_browser: bool = True) -> list[str]:
    """Return a command that starts Dashboard in either packaged or source installs."""
    target = (target or app_dir()).resolve()
    executable = target / ("Dashboard.exe" if os.name == "nt" else "Dashboard")
    if executable.is_file():
        command = [str(executable)]
    else:
        source = target / "dashboard.py"
        if not source.is_file():
            raise RuntimeError("Dashboard executable/source is missing")
        if not is_frozen():
            interpreter = sys.executable
        else:
            interpreter = shutil.which("python") or shutil.which("python3")
            if not interpreter:
                raise RuntimeError("Dashboard.exe is missing and no Python interpreter is available")
        command = [str(interpreter), str(source)]
    if no_browser:
        command.append("--no-browser")
    return command


def updater_command(target: Path | None = None) -> list[str]:
    """Return the packaged updater when present, otherwise the source updater."""
    target = (target or app_dir()).resolve()
    executable = target / ("Updater.exe" if os.name == "nt" else "Updater")
    if executable.is_file():
        return [str(executable)]
    source = target / "updater.py"
    if not source.is_file():
        raise RuntimeError("Updater executable/source is missing")
    if not is_frozen():
        return [sys.executable, str(source)]
    interpreter = shutil.which("python") or shutil.which("python3")
    if not interpreter:
        raise RuntimeError("Updater.exe is missing and no Python interpreter is available")
    return [str(interpreter), str(source)]
