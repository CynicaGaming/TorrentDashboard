#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
previous = subprocess.check_output(
    ["git", "show", "HEAD^^^:release_tools/apply_feature_update.py"],
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

design = HERE.parents[1] / "DESIGN_LANGUAGE.md"
text = design.read_text(encoding="utf-8")
text = text.replace(
    "- On desktop/tablet, drag a visible torrent data header horizontally to change its position. Dragging the narrow right edge resizes that column; resizing takes exclusive control of the pointer and live polling must not rebuild rows underneath an active resize.\n",
    "- On desktop/tablet, drag a visible torrent data header horizontally to change its position. Drag the right edge of a visible data header to resize that column; resizing takes exclusive control of the pointer. During an active resize, defer torrent-row DOM rendering until the gesture ends so live polling cannot move the target.\n",
    1,
)
text = text.replace(
    "- Torrent names and other text columns should consume the width actually assigned to their cell. Ellipsis is a real overflow treatment, not a fixed historical width cap.\n",
    "- Torrent names and other text columns should consume the width actually assigned to their cell. Use ellipsis only when the rendered cell is actually narrower than its content; it is an overflow treatment, not a fixed historical width cap.\n",
    1,
)
design.write_text(text, encoding="utf-8")

testing = HERE.parents[1] / "TESTING.md"
text = testing.read_text(encoding="utf-8")
text = text.replace(
    "- Verify each header label/sort affordance is visually centered within its column and the 20 px resize gutter remains entirely inside the owning header.\n",
    "- Verify each header label is centered within its column; the sort affordance must not offset the label, and the 20 px resize gutter remains entirely inside the owning header.\n",
    1,
)
text = text.replace(
    "- Hide a resized data column from the Columns menu, show it again, and verify its saved width returns. Every data column, including Name, can be hidden.\n",
    "- Hide a resized data column from the Columns menu, show it again, and verify its saved width returns. Verify the menu includes Name, and can show/hide all data columns.\n",
    1,
)
text = text.replace(
    "- Horizontally scroll a wide customized table and verify the far-right actions column remains fixed at 48 px; it must never show resize behavior, change width, or cause page-level horizontal overflow.\n",
    "- Horizontally scroll a wide customized table and verify the far-right actions column remains fixed at 48 px. The actions column must never show resize behavior or change width, and it must not cause page-level horizontal overflow.\n",
    1,
)
testing.write_text(text, encoding="utf-8")
