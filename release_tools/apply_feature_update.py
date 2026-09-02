#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release_tools" / "validate_ui_strings.py"
text = path.read_text(encoding="utf-8")
old = "    assert 'id=\"addStopped\"' in html and 'id=\"addSequential\"' in html and 'id=\"addFirstLast\"' in html\n"
new = "    assert 'id=\"addStartTorrent\"' in html and 'id=\"addSequential\"' in html and 'id=\"addFirstLast\"' in html\n"
if text.count(old) != 1:
    raise RuntimeError(f"Expected one stale Add Torrent validator assertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Updated v0.5.49 Add Torrent validator contract")
