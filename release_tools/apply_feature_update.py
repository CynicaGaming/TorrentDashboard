#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.87"
NEW = "0.5.88"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected source fragment not found in {path}: {old[:180]!r}")
    write(path, text.replace(old, new, count))


# Version/build synchronization.
replace("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
write("static/index.html", read("static/index.html").replace(OLD, NEW))
replace("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
sw = read("static/sw.js").replace("torrent-dashboard-v0587", "torrent-dashboard-v0588").replace(OLD, NEW)
write("static/sw.js", sw)

# Name is now a normal configurable data column. It remains visible in the
# default layout, but can be hidden and resized just like the other data fields.
replace(
    "static/app.js",
    "{key:'name',label:'Name',required:true,defaultVisible:true}",
    "{key:'name',label:'Name',required:false,defaultVisible:true}",
)
replace(
    "static/app.js",
    "const TORRENT_COLUMN_MIN_WIDTHS={name:220,size:90,progress:180,state:110,seeds:82,peers:82,down:104,up:104,eta:82,ratio:82,category:110,tags:120,tracker:150,added:160};",
    "const TORRENT_COLUMN_MIN_WIDTHS={name:140,size:90,progress:180,state:110,seeds:82,peers:82,down:104,up:104,eta:82,ratio:82,category:110,tags:120,tracker:150,added:160};",
)

# Update the durable design/testing contract.
design = read("DESIGN_LANGUAGE.md")
old_design = """- **Name** is required and cannot be hidden. The selection checkbox and row-actions control remain fixed at the outer edges; visible data columns can be reordered directly.\n"""
new_design = """- **Name** is visible by default but is otherwise a normal configurable data column: it can be hidden, reordered, and resized. The selection checkbox and row-actions control are the only fixed table columns.\n"""
if old_design not in design:
    raise RuntimeError("Current Name-column design rule not found")
design = design.replace(old_design, new_design, 1)
design = design.replace(
    "- Column resizing has per-column minimums that preserve legibility and a bounded maximum width. The fixed selection and row-actions columns are not user-resizable.\n",
    "- Column resizing has per-column minimums that preserve legibility and a bounded maximum width. Name can shrink to a compact readable width; the fixed selection and row-actions columns are not user-resizable.\n",
    1,
)
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing = testing.replace(
    "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Verify each stops at a readable minimum, remains stable during the one-second refresh, and persists after reload.\n",
    "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Verify Name can shrink to its compact minimum, each column stops at its documented readable minimum, remains stable during the one-second refresh, and persists after reload.\n",
    1,
)
testing = testing.replace(
    "- Right-click the torrent header bar and verify the Columns menu lists every data column, keeps Name required, and can show/hide every optional column.\n",
    "- Right-click the torrent header bar and verify the Columns menu lists every data column, including Name, and can show/hide all data columns. Hide Name and verify the remaining torrent columns continue to render and operate normally.\n",
    1,
)
write("TESTING.md", testing)

# Update the executable UI contract so the old Name-required decision cannot
# silently return.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace(
    "    # 0.5.84-v0.5.87 keeps torrent columns browser-local and directly\n    # configurable from the header; v0.5.87 adds persisted edge resizing.\n",
    "    # 0.5.84-v0.5.88 keeps torrent columns browser-local and directly\n    # configurable from the header; v0.5.88 makes Name optional as well.\n",
    1,
)
anchor = "    assert \"{key:'size',label:'Size',defaultVisible:false}\" in app_js\n"
if anchor not in validator:
    raise RuntimeError("Torrent-column validator anchor not found")
validator = validator.replace(
    anchor,
    "    assert \"{key:'name',label:'Name',required:false,defaultVisible:true}\" in app_js\n"
    "    assert \"{key:'name',label:'Name',required:true,defaultVisible:true}\" not in app_js\n"
    "    assert 'const TORRENT_COLUMN_MIN_WIDTHS={name:140,' in app_js\n"
    + anchor,
    1,
)
validator = validator.replace(
    "    assert 'Drag the narrow right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n",
    "    assert 'Drag the narrow right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n"
    "    assert '**Name** is visible by default but is otherwise a normal configurable data column' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n"
    "    assert 'including Name, and can show/hide all data columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n",
    1,
)
write("release_tools/validate_ui_strings.py", validator)

# Release metadata and continuity state. Remove the two superseded Name-required
# decisions before carrying the decision list forward.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")

superseded = {
    "Keep Name, the selection checkbox, and row actions fixed; allow the remaining torrent data columns to be hidden and reordered.",
    "Manage torrent columns directly from the torrent header: drag visible headers to reorder and use the header context menu to show/hide optional columns; keep Name required and Category visible in the default layout.",
}
decisions = [item for item in (previous.get("decisions") or []) if item not in superseded]
decisions.append(
    "Treat Name as a normal torrent data column: keep it visible by default but allow users to hide, reorder, and resize it; only the selection checkbox and row-actions columns remain fixed."
)

releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Fully configurable Name column",
    "summary": "Removes the last special-case restriction from torrent data columns so Name can be hidden and resized like the rest of the configurable table.",
    "highlights": [
        "Name remains visible in the default torrent layout but can now be hidden from the header Columns menu.",
        "Name remains draggable and resizable, with its minimum width reduced from 220 px to 140 px for denser desktop layouts.",
        "The selection checkbox and row-actions control are now the only fixed/non-configurable torrent-table columns."
    ],
    "fixes": [
        "Removes the inconsistent Name-required exception from an otherwise directly configurable torrent table.",
        "Cleans superseded Name-required decisions from the generated engineering handoff so future work follows the current table contract."
    ],
    "technical": [
        "Name uses the same browser-local tdColumns visibility, order, and widths state as every other torrent data column.",
        "Existing layouts remain unchanged because Name is still default-visible and previously saved visibility/order/width data is preserved."
    ],
    "validation": [
        "The UI audit explicitly requires Name to be optional, rejects the previous required:true definition, and verifies the 140 px Name minimum.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} optional Name column")
