#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
app_path = root / "static" / "app.js"
app = app_path.read_text(encoding="utf-8")
old = '<span title="${esc(filePath)}">${esc(filePath)}</span>'
new = '<span>${esc(filePath)}</span>'
if app.count(old) != 1:
    raise RuntimeError(f"Expected one dynamic Add Torrent file title, found {app.count(old)}")
app = app.replace(old, new, 1)
app_path.write_text(app, encoding="utf-8")

validator_path = root / "release_tools" / "validate_ui_strings.py"
validator = validator_path.read_text(encoding="utf-8")
marker = "    assert 'id=\"addFileRows\"' in html\n"
addition = marker + "    assert 'title=\"${esc(filePath)}\"' not in app_js\n"
if validator.count(marker) != 1:
    raise RuntimeError("Expected one Add Torrent file-list validator marker")
validator = validator.replace(marker, addition, 1)
validator_path.write_text(validator, encoding="utf-8")

assert old not in app_path.read_text(encoding="utf-8")
print("Removed redundant dynamic Add Torrent file title attribute")
