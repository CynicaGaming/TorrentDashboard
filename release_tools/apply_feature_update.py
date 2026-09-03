#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_OLD = "0.5.92"
VERSION_NEW = "0.5.93"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"{path}: expected source fragment not found: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# Restore normal table-header alignment without undoing the resize/sort gesture
# protections added in v0.5.89-v0.5.92. Resize discovery belongs to the edge,
# not to artificially centered labels.
css = read("static/app.css")
marker = "/* 0.5.93 content-aligned sortable torrent headers. */"
if marker not in css:
    css += """

/* 0.5.93 content-aligned sortable torrent headers. */
#torrentTable thead th[data-col]{text-align:left;padding-left:12px;padding-right:22px}
#torrentTable thead th[data-col=\"seeds\"],#torrentTable thead th[data-col=\"peers\"]{text-align:left}
.torrent-sort-heading{justify-content:flex-start}
"""
    write("static/app.css", css)

# Durable design rule: label alignment follows the table, while the internal
# resize gutter remains the explicit manipulation affordance.
design = read("DESIGN_LANGUAGE.md")
needle = "- Header sorting, header reordering, and edge resizing are separate gestures. Completing a resize or reorder must not accidentally trigger a sort click."
addition = needle + "\n- Torrent header labels follow the table's normal content flow rather than being centered as a resize aid. Resize discovery belongs to the internal edge gutter and divider, so label placement should not distort the relationship between headers and row content."
if "Torrent header labels follow the table's normal content flow" not in design:
    if needle not in design:
        raise SystemExit("DESIGN_LANGUAGE.md: configurable-column gesture rule not found")
    design = design.replace(needle, addition, 1)
    write("DESIGN_LANGUAGE.md", design)

# Replace the manual test that encoded v0.5.91's centered-header experiment.
testing = read("TESTING.md")
old_test = "- Verify each header label is centered within its column; the sort affordance must not offset the label, and the 20 px resize gutter remains entirely inside the owning header."
new_test = "- Verify torrent header labels follow the table's normal left/content flow rather than being centered; the sort affordance stays at the far edge and the 20 px resize gutter remains entirely inside the owning header."
if old_test in testing:
    testing = testing.replace(old_test, new_test, 1)
elif new_test not in testing:
    raise SystemExit("TESTING.md: centered-header regression test not found")
write("TESTING.md", testing)

# Keep the polling-stable portion of the v0.5.91 contract, but explicitly
# supersede the centered-label assertion with the new late CSS override.
validator = read("release_tools/validate_ui_strings.py")
old_validator = '''    # 0.5.91 centers configurable headers and prevents polling-driven DOM
    # rebuilds from moving a column while the user is actively resizing it.
    assert "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false" in app_js
    assert "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}" in app_js
    assert "const renderPending=torrentColumnRenderPending;torrentColumnResize=null" in app_js
    assert "if(renderPending){torrentColumnRenderPending=false;render()}" in app_js
    assert '0.5.91 centered and polling-stable torrent-column resizing' in app_css
    assert '#torrentTable thead th[data-col]{text-align:center;padding-left:22px;padding-right:22px}' in app_css
    assert '#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:center}' in app_css
    assert '.column-resize-handle{right:0;width:20px}' in app_css
    assert 'inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important' in app_css
    assert 'defer torrent-row DOM rendering' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'header label is centered within its column' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
new_validator = '''    # 0.5.91 introduced polling-stable resizing; v0.5.93 keeps that gesture
    # protection but supersedes centered labels with normal content alignment.
    assert "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false" in app_js
    assert "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}" in app_js
    assert "const renderPending=torrentColumnRenderPending;torrentColumnResize=null" in app_js
    assert "if(renderPending){torrentColumnRenderPending=false;render()}" in app_js
    assert '0.5.91 centered and polling-stable torrent-column resizing' in app_css
    assert '.column-resize-handle{right:0;width:20px}' in app_css
    assert 'inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important' in app_css
    assert '0.5.93 content-aligned sortable torrent headers' in app_css
    assert '#torrentTable thead th[data-col]{text-align:left;padding-left:12px;padding-right:22px}' in app_css
    assert '#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:left}' in app_css
    assert '.torrent-sort-heading{justify-content:flex-start}' in app_css
    assert app_css.rfind('0.5.93 content-aligned sortable torrent headers') > app_css.rfind('0.5.91 centered and polling-stable torrent-column resizing')
    assert 'defer torrent-row DOM rendering' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert "Torrent header labels follow the table's normal content flow" in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert "header labels follow the table's normal left/content flow" in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
if old_validator not in validator:
    raise SystemExit("validate_ui_strings.py: v0.5.91 validator block not found")
validator = validator.replace(old_validator, new_validator, 1)
write("release_tools/validate_ui_strings.py", validator)

# Version synchronization.
replace_once("dashboard.py", 'VERSION = "0.5.92"', 'VERSION = "0.5.93"')
for path in ("static/index.html", "static/app.js", "static/sw.js"):
    text = read(path)
    if VERSION_OLD not in text:
        raise SystemExit(f"{path}: {VERSION_OLD} version marker not found")
    text = text.replace(VERSION_OLD, VERSION_NEW)
    if path == "static/sw.js":
        text = text.replace("torrent-dashboard-v0592", "torrent-dashboard-v0593")
    write(path, text)

# Append public release metadata and carry forward only current decisions.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if releases[-1]["version"] != VERSION_OLD:
    raise SystemExit(f"Expected latest release {VERSION_OLD}, found {releases[-1]['version']}")
if any(item.get("version") == VERSION_NEW for item in releases):
    raise SystemExit(f"Release {VERSION_NEW} already exists")
prev = releases[-1]
decisions = [
    d for d in prev.get("decisions", [])
    if not d.startswith("Center configurable torrent-column headers")
]
decisions.append(
    "Align sortable torrent header labels with the table's normal content flow rather than centering them; keep resize discovery on the internal edge gutter so header placement and row content remain visually coherent."
)
releases.append({
    "version": VERSION_NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Content-aligned torrent headers",
    "summary": "Restores natural torrent-table header alignment while retaining the stabilized resize, reorder, sorting, overflow, and fixed-actions behavior from the preceding column releases.",
    "highlights": [
        "Sortable torrent header labels return to normal left/content flow instead of being centered independently of their row data.",
        "The 20 px inward-only resize gutter remains unchanged, so column boundaries stay easy to grab without using label centering as a resize cue.",
        "Header sorting, drag-to-reorder, persistent resizing, long-name expansion, and the fixed 48 px actions column remain intact."
    ],
    "fixes": [
        "Corrects the visual mismatch where centered headers made left-flowing row content appear offset from its own column.",
        "Preserves the exclusive resize gesture and polling deferral that prevent accidental column movement or resize jumps."
    ],
    "technical": [
        "A late CSS override supersedes only v0.5.91's centered-header presentation; the resize gutter, pointer capture, live-render deferral, sort click suppression, Name overflow behavior, and actions-column lock are unchanged.",
        "The sort chevron remains positioned at the far side of the header so it does not alter the label's content alignment."
    ],
    "validation": [
        "The UI audit requires the v0.5.93 late alignment override to follow the historical centered rule while retaining the 20 px resize gutter and polling-stable resize state.",
        "Manual coverage verifies header/row visual alignment, resize stability across live refreshes, genuine overflow ellipsis, and the fixed non-resizable actions column.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": prev.get("architecture", []),
    "next_steps": prev.get("next_steps", []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_NEW],
    cwd=ROOT,
    check=True,
)
