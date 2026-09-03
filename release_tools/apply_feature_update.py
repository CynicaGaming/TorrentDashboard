#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.90"
NEW = "0.5.91"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


# Synchronized build identifiers.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if f'content="{OLD}" name="torrent-dashboard-build"' not in html:
    raise RuntimeError("Could not find HTML frontend build")
html = html.replace(OLD, NEW)
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")

# Keep resize and reorder mutually exclusive, and defer torrent-row DOM rebuilds
# while a resize gesture is active. Polling can still update state/metrics; the
# latest rows are rendered once after pointer release.
app_js = replace_once(
    app_js,
    "let draggedTorrentColumn='',torrentColumnResize=null;",
    "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false;",
    "torrent column gesture state",
)
app_js = replace_once(
    app_js,
    "event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';",
    "event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;",
    "resize gesture initialization",
)
app_js = replace_once(
    app_js,
    "const nearResizeEdge=event.clientX>=rect.right-14&&event.clientX<=rect.right;",
    "const nearResizeEdge=event.clientX>=rect.right-20&&event.clientX<=rect.right;",
    "resize edge hit target",
)

finish_pattern = re.compile(
    r"function finishTorrentColumnResize\(event\)\{\n"
    r"  const resize=torrentColumnResize;if\(!resize\|\|\(event\?\.pointerId!==undefined&&event\.pointerId!==resize\.pointerId\)\)return;\n"
    r"  torrentColumnResize=null;document\.body\.classList\.remove\('torrent-column-resizing'\);resize\.th\?\.classList\.remove\('column-resizing'\);if\(resize\.th\)resize\.th\.draggable=true;\n"
    r"  try\{resize\.handle\.releasePointerCapture\?\.\(resize\.pointerId\)\}catch\{\}saveTorrentColumnWidth\(resize\.key,resize\.width\);\n"
    r"\}"
)
finish_replacement = """function finishTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||(event?.pointerId!==undefined&&event.pointerId!==resize.pointerId))return;
  const renderPending=torrentColumnRenderPending;torrentColumnResize=null;document.body.classList.remove('torrent-column-resizing');resize.th?.classList.remove('column-resizing');if(resize.th)resize.th.draggable=true;
  try{resize.handle.releasePointerCapture?.(resize.pointerId)}catch{}saveTorrentColumnWidth(resize.key,resize.width);
  if(renderPending){torrentColumnRenderPending=false;render()}
}"""
app_js, changes = finish_pattern.subn(finish_replacement, app_js, count=1)
if changes != 1:
    raise RuntimeError("Could not replace resize completion handler")

app_js = replace_once(
    app_js,
    "function render(){const list=visibleTorrents();",
    "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}const list=visibleTorrents();",
    "torrent render deferral",
)
write("static/app.js", app_js)

# The resize target is fully inside its own header and large enough to acquire
# comfortably. Symmetric padding keeps the visible header label centered on the
# actual column rather than biased away from the resize edge.
app_css = read("static/app.css")
app_css += r'''

/* 0.5.91 centered and polling-stable torrent-column resizing. */
#torrentTable thead th[data-col]{text-align:center;padding-left:22px;padding-right:22px}
#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:center}
.column-resize-handle{right:0;width:20px}
.column-resize-handle::after{right:0}
#torrentTable th.row-actions-head,#torrentTable td.row-actions{inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important;white-space:nowrap}
'''
write("static/app.css", app_css)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0590", "torrent-dashboard-v0591", "service worker cache generation")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)

# Document the interaction contract in the durable design/test guides.
design = read("DESIGN_LANGUAGE.md")
resize_bullet = "- Drag the right edge of a visible data header to resize that column. The resize gutter stays entirely inside the data header, uses a forgiving hit target, and takes exclusive control of the pointer so it cannot overlap an adjacent column or simultaneously initiate header reordering. The in-progress width must survive the one-second live refresh while the pointer remains down; committed widths are stored with the same browser-local column layout and survive visibility changes, reordering, and reloads."
resize_replacement = "- Drag the right edge of a visible data header to resize that column. The resize gutter stays entirely inside the data header, uses a forgiving hit target, and takes exclusive control of the pointer so it cannot overlap an adjacent column or simultaneously initiate header reordering. While the pointer is held down, live status polling may update state but must defer torrent-row DOM rendering so the column cannot jump under the pointer; render the latest row state once the resize is released. Committed widths are stored with the same browser-local column layout and survive visibility changes, reordering, and reloads."
design = replace_once(design, resize_bullet, resize_replacement, "configurable-column resize design rule")
anchor = "- Column resizing has per-column minimums that preserve legibility and a bounded maximum width. Name can shrink to a compact readable width; the fixed selection and row-actions columns are not user-resizable."
center_rule = anchor + "\n- Configurable data-column headers are visually centered within symmetric horizontal padding. The label center should match the column center even though the right edge contains a resize gutter; selection and row-actions headers are outside this rule."
design = replace_once(design, anchor, center_rule, "centered header design rule")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
hold_test = "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Hold at least one resize gesture open for several seconds across multiple one-second refreshes and verify the live width never snaps back. Verify Name can shrink to its compact minimum, each column stops at its documented readable minimum, and the committed width persists after reload."
hold_replacement = "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Hold at least one resize gesture open for several seconds across multiple one-second refreshes and verify the live width never snaps back or jumps because torrent rows rerendered under the pointer. Release the pointer and verify the latest torrent state renders once without changing the chosen width. Verify Name can shrink to its compact minimum, each column stops at its documented readable minimum, and the committed width persists after reload."
testing = replace_once(testing, hold_test, hold_replacement, "resize polling regression test")
edge_test = "- Verify the resize edge is easy to acquire without pixel-perfect positioning. Start resizing near the divider and verify header reordering cannot begin until the resize gesture is released; then drag from the body of the same header and verify normal reordering still works and does not discard its saved width."
edge_replacement = edge_test + "\n- Verify every configurable data-column header label is centered within its column and remains visually centered before, during, and after resizing. The resize gutter should not make labels appear shifted left, and right-aligned data cells such as Seeds/Peers must still use centered headers."
testing = replace_once(testing, edge_test, edge_replacement, "centered header regression test")
write("TESTING.md", testing)

# Extend the source-level UI contract. Historical 0.5.90 CSS remains in the
# stylesheet, but the effective current hit target is the later 20px rule.
validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    'assert "event.clientX>=rect.right-14&&event.clientX<=rect.right" in app_js',
    'assert "event.clientX>=rect.right-20&&event.clientX<=rect.right" in app_js',
    "current resize hit-target assertion",
)
insert_before = '    print("UI string audit passed")'
new_assertions = '''    # 0.5.91 centers configurable headers and prevents polling-driven DOM\n    # rebuilds from moving a column while the user is actively resizing it.\n    assert "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false" in app_js\n    assert "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}" in app_js\n    assert "const renderPending=torrentColumnRenderPending;torrentColumnResize=null" in app_js\n    assert "if(renderPending){torrentColumnRenderPending=false;render()}" in app_js\n    assert '0.5.91 centered and polling-stable torrent-column resizing' in app_css\n    assert '#torrentTable thead th[data-col]{text-align:center;padding-left:22px;padding-right:22px}' in app_css\n    assert '#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:center}' in app_css\n    assert '.column-resize-handle{right:0;width:20px}' in app_css\n    assert 'inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important' in app_css\n    assert 'defer torrent-row DOM rendering' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'header label is centered within its column' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n\n'''
if insert_before not in validator:
    raise RuntimeError("Could not locate UI audit footer")
validator = validator.replace(insert_before, new_assertions + insert_before, 1)
write("release_tools/validate_ui_strings.py", validator)

# Release metadata and generated continuity files.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")

decisions = list(previous.get("decisions") or [])
decisions.append("Center configurable torrent-column headers with symmetric padding, reserve a fully internal resize gutter, and defer torrent-row DOM rendering during an active resize so polling cannot move the target under the pointer.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Stable centered column resizing",
    "summary": "Finishes the torrent-column resize interaction by centering header labels and preventing one-second live rendering from moving a column while its resize edge is being dragged.",
    "highlights": [
        "All configurable torrent data headers are centered within symmetric horizontal padding so labels visually match their column boundaries.",
        "The resize hit target grows to 20 px while remaining entirely inside the owning data header.",
        "Torrent-row DOM rendering is deferred during an active resize and reconciled once on release, eliminating polling-driven resize jumps."
    ],
    "fixes": [
        "Reduces accidental header reordering when the user intends to resize near a divider.",
        "Prevents the one-second torrent refresh from rebuilding rows underneath an active resize gesture.",
        "Corrects right- and left-aligned header labels that made resize boundaries feel visually offset from their columns."
    ],
    "technical": [
        "A torrentColumnRenderPending flag records refreshes that occur while pointer capture owns a resize gesture; finishTorrentColumnResize performs one deferred render after persisting the width.",
        "The resize gutter is a 20 px inward-only hit target, while the visual divider remains on the actual column boundary.",
        "The row-actions surface retains its fixed 48 px inline-size contract from v0.5.90 and remains outside the configurable resize set."
    ],
    "validation": [
        "The UI audit requires centered/symmetrically padded data headers, the 20 px internal resize target, deferred render state, and the fixed action-column inline-size contract.",
        "Manual regression coverage holds a resize across multiple live refresh intervals and verifies no snap, row rebuild, or accidental reorder occurs before pointer release.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} stable centered torrent-column resizing")
