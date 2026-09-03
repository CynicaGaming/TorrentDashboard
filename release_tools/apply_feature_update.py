#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / "release_tools" / "_apply_feature_update_v05102.py"


def main() -> None:
    previous = subprocess.check_output(
        ["git", "show", "HEAD^:release_tools/apply_feature_update.py"],
        cwd=ROOT,
        text=True,
    )
    TEMP.write_text(previous, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location("td_v05102_staging", TEMP)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load v0.5.102 staging transform")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_replace_once = module.replace_once

        def patched_replace_once(path: Path, old: str, new: str, label: str) -> None:
            if label != "torrent row actions cell":
                original_replace_once(path, old, new, label)
                return
            text = path.read_text(encoding="utf-8")
            pattern = r'<td class=\\?"row-actions\\?"><button class=\\?"more-row\\?" aria-label=\\?"Actions\\?">•••</button></td>'
            updated, count = re.subn(pattern, "", text, count=1)
            if count != 1:
                raise RuntimeError(f"Expected exactly one {label} regex match in {path.relative_to(ROOT)}, found {count}")
            path.write_text(updated, encoding="utf-8")

        module.replace_once = patched_replace_once
        module.main()
    finally:
        TEMP.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
