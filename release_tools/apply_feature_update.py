#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "release_tools" / "validate_ui_strings.py"
CSS = ROOT / "static" / "app.css"
TEMP = ROOT / "release_tools" / "_apply_feature_update_original.py"
ORIGINAL_STAGING_COMMIT = "db484bfb14726425036a56967027ce7677edbfac"
TARGET_VERSION = "0.5.101"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} match")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        VALIDATOR,
        "        'Torrent columns','Copy address','Add client','GitHub repository',",
        "        'Copy address','Add client','GitHub repository',",
        "retired Torrent columns copy assertion",
    )
    replace_once(
        CSS,
        "@media(max-width:820px){.column-resize-handle{display:none!important}#torrentTable td.row-spacer{display:none!important}#torrentTable th.check,#torrentTable td.check{position:static;left:auto;box-shadow:none}}\n",
        "",
        "retired mobile resize/spacer rule",
    )

    original = subprocess.check_output(
        ["git", "show", f"{ORIGINAL_STAGING_COMMIT}:release_tools/apply_feature_update.py"],
        cwd=ROOT,
        text=True,
    )
    TEMP.write_text(original, encoding="utf-8")
    try:
        subprocess.run([sys.executable, str(TEMP)], cwd=ROOT, check=True)
    finally:
        TEMP.unlink(missing_ok=True)

    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
