#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "release_tools" / "validate_ui_strings.py"
TEMP = ROOT / "release_tools" / "_apply_feature_update_previous.py"


def main() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    old = "        'Torrent columns','Copy address','Add client','GitHub repository',"
    new = "        'Copy address','Add client','GitHub repository',"
    if text.count(old) != 1:
        raise RuntimeError("Expected the retired Torrent columns copy assertion exactly once")
    VALIDATOR.write_text(text.replace(old, new, 1), encoding="utf-8")

    previous = subprocess.check_output(
        ["git", "show", "HEAD^:release_tools/apply_feature_update.py"],
        cwd=ROOT,
        text=True,
    )
    TEMP.write_text(previous, encoding="utf-8")
    try:
        subprocess.run([sys.executable, str(TEMP)], cwd=ROOT, check=True)
    finally:
        TEMP.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
