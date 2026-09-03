#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
previous = subprocess.check_output(
    ["git", "show", "HEAD^^:release_tools/apply_feature_update.py"],
    cwd=HERE.parents[1],
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(previous, str(HERE), "exec"), namespace)

validator = HERE.with_name("validate_ui_strings.py")
text = validator.read_text(encoding="utf-8")
replacements = [
    (
        "        'Download speed','HTTP sources','Accent color',\n",
        "        'HTTP sources','Accent color',\n",
        "Download speed copy assertion",
    ),
    (
        "'applyColumnPrefs();applyTorrentColumnWidths();const empty='",
        "'applyColumnPrefs();applyTorrentColumnWidths();syncTorrentSortHeaders();const empty='",
        "torrent render column assertion",
    ),
]
for old, new, label in replacements:
    if old not in text:
        raise RuntimeError(f"Could not retire the old {label}")
    text = text.replace(old, new, 1)
validator.write_text(text, encoding="utf-8")
