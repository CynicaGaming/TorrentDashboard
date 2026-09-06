#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

import recover_v0_5_123 as recovery

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    recovery.version_bump()
    recovery.patch_integrations_module()
    recovery.patch_dashboard()
    recovery.patch_settings_js()
    recovery.patch_settings_css()
    recovery.patch_tests()
    recovery.patch_release_metadata()
    subprocess.run([
        "python", "release_tools/generate_release_notes.py", "--version", recovery.NEW
    ], cwd=ROOT, check=True)
    for relative in (
        "release_tools/recover_v0_5_123.py",
        "release_tools/run_recovery_safe.py",
    ):
        path = ROOT / relative
        if path.exists():
            path.unlink()
    print(f"Recovered validated release line as v{recovery.NEW}")


if __name__ == "__main__":
    main()
