#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.88"
NEW = "0.5.89"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


# Keep the public build/version markers synchronized.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard VERSION marker")
write("dashboard.py", dashboard)

index = read("static/index.html")
if OLD not in index:
    raise RuntimeError("Current build marker was not found in static/index.html")
index = index.replace(OLD, NEW)
write("static/index.html", index)

sw = read("static/sw.js")
if f"v{OLD.replace('.', '')}" not in sw or OLD not in sw:
    raise RuntimeError("Current service-worker cache/version markers were not found")
sw = sw.replace(f"v{OLD.replace('.', '')}", f"v{NEW.replace('.', '')}").replace(OLD, NEW)
write("static/sw.js", sw)

# Make resize state exclusive from header reordering and preserve the live width
# through the one-second table refresh while the pointer is still down.
app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build marker")
old_apply = "function applyTorrentColumnWidths(prefs=torrentColumnPreferences()){for(const column of TORRENT_COLUMN_DEFS)applyTorrentColumnWidth(column.key,prefs.widths?.[column.key])}"
new_apply = """function applyTorrentColumnWidths(prefs=torrentColumnPreferences()){
  for(const column of TORRENT_COLUMN_DEFS){
    const liveWidth=torrentColumnResize?.key===column.key?torrentColumnResize.width:null;
    applyTorrentColumnWidth(column.key,liveWidth??prefs.widths?.[column.key]);
  }
}"""
app_js = replace_once(app_js, old_apply, new_apply, "torrent-column width application function")

old_start = """function startTorrentColumnResize(event,handle){
  if(event.button!==0)return;const th=handle.closest('th[data-col]');if(!th)return;event.preventDefault();event.stopPropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width);torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,pointerId:event.pointerId,handle};
  handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}"""
new_start = """function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width);
  th.draggable=false;th.classList.add('column-resizing');
  torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,pointerId:event.pointerId,handle,th};
  handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}"""
app_js = replace_once(app_js, old_start, new_start, "column resize start function")

old_finish = """function finishTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||(event?.pointerId!==undefined&&event.pointerId!==resize.pointerId))return;torrentColumnResize=null;document.body.classList.remove('torrent-column-resizing');try{resize.handle.releasePointerCapture?.(resize.pointerId)}catch{}saveTorrentColumnWidth(resize.key,resize.width);
}"""
new_finish = """function finishTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||(event?.pointerId!==undefined&&event.pointerId!==resize.pointerId))return;
  torrentColumnResize=null;document.body.classList.remove('torrent-column-resizing');resize.th?.classList.remove('column-resizing');if(resize.th)resize.th.draggable=true;
  try{resize.handle.releasePointerCapture?.(resize.pointerId)}catch{}saveTorrentColumnWidth(resize.key,resize.width);
}"""
app_js = replace_once(app_js, old_finish, new_finish, "column resize finish function")

old_pointerdown = "  head.addEventListener('pointerdown',event=>{const handle=event.target.closest('.column-resize-handle');if(handle)startTorrentColumnResize(event,handle)});"
new_pointerdown = """  head.addEventListener('pointerdown',event=>{
    if(event.button!==0)return;const th=event.target.closest('th[data-col]');if(!th)return;
    const rect=th.getBoundingClientRect(),handle=event.target.closest('.column-resize-handle')||th.querySelector('.column-resize-handle');
    const nearResizeEdge=event.clientX>=rect.right-14&&event.clientX<=rect.right+8;
    if(handle&&(event.target.closest('.column-resize-handle')||nearResizeEdge))startTorrentColumnResize(event,handle);
  },true);"""
app_js = replace_once(app_js, old_pointerdown, new_pointerdown, "column resize pointerdown binding")

old_dragstart = "  head.addEventListener('dragstart',event=>{if(event.target.closest('.column-resize-handle')){event.preventDefault();return}const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});"
new_dragstart = "  head.addEventListener('dragstart',event=>{if(torrentColumnResize||event.target.closest('.column-resize-handle')){event.preventDefault();return}const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});"
app_js = replace_once(app_js, old_dragstart, new_dragstart, "column dragstart guard")
write("static/app.js", app_js)

app_css = read("static/app.css")
if "/* 0.5.89 stable torrent-column resize gesture. */" in app_css:
    raise RuntimeError("v0.5.89 resize CSS already exists")
app_css += """

/* 0.5.89 stable torrent-column resize gesture. */
.column-resize-handle{right:-8px;width:16px}
.column-resize-handle::after{right:8px}
#torrentTable thead th.column-resizing{cursor:col-resize}
"""
write("static/app.css", app_css)

# Document the interaction contract explicitly.
design = read("DESIGN_LANGUAGE.md")
old_design = "- Drag the narrow right edge of a visible data header to resize that column. Widths are stored with the same browser-local column layout and must survive live refreshes, visibility changes, reordering, and reloads."
new_design = "- Drag the right edge of a visible data header to resize that column. The resize edge uses a forgiving hit target and takes exclusive control of the pointer so it cannot simultaneously initiate header reordering. The in-progress width must survive the one-second live refresh while the pointer remains down; committed widths are stored with the same browser-local column layout and survive visibility changes, reordering, and reloads."
design = replace_once(design, old_design, new_design, "configurable-column resize design rule")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
old_test = "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Verify Name can shrink to its compact minimum, each column stops at its documented readable minimum, remains stable during the one-second refresh, and persists after reload."
new_test = "- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Hold at least one resize gesture open for several seconds across multiple one-second refreshes and verify the live width never snaps back. Verify Name can shrink to its compact minimum, each column stops at its documented readable minimum, and the committed width persists after reload."
testing = replace_once(testing, old_test, new_test, "configurable-column resize smoke test")
old_conflict = "- Verify resizing a header does not accidentally start header reordering and reordering does not discard a saved width."
new_conflict = "- Verify the resize edge is easy to acquire without pixel-perfect positioning. Start resizing near the divider and verify header reordering cannot begin until the resize gesture is released; then drag from the body of the same header and verify normal reordering still works and does not discard its saved width."
testing = replace_once(testing, old_conflict, new_conflict, "resize/reorder conflict smoke test")
write("TESTING.md", testing)

# Add source-level regression checks for the two causes of the observed jitter.
validator = read("release_tools/validate_ui_strings.py")
marker = '    print("UI string audit passed")'
if marker not in validator:
    raise RuntimeError("Could not find UI validator completion marker")
block = '''    # 0.5.89 makes resize and reorder mutually exclusive and preserves an
    # in-progress resize across the one-second torrent render loop.
    assert "const liveWidth=torrentColumnResize?.key===column.key?torrentColumnResize.width:null" in app_js
    assert "liveWidth??prefs.widths?.[column.key]" in app_js
    assert "th.draggable=false;th.classList.add('column-resizing')" in app_js
    assert "if(resize.th)resize.th.draggable=true" in app_js
    assert "event.stopImmediatePropagation()" in app_js
    assert "event.clientX>=rect.right-14&&event.clientX<=rect.right+8" in app_js
    assert "if(torrentColumnResize||event.target.closest('.column-resize-handle'))" in app_js
    assert '.column-resize-handle{right:-8px;width:16px}' in app_css
    assert '0.5.89 stable torrent-column resize gesture' in app_css
    assert 'Hold at least one resize gesture open for several seconds' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'takes exclusive control of the pointer' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')

'''
validator = validator.replace(marker, block + marker, 1)
write("release_tools/validate_ui_strings.py", validator)

# Add the release metadata and carry the current decision set forward.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")
decisions = list(previous.get("decisions") or [])
decisions.append("Treat torrent-column resizing as an exclusive pointer gesture: use a forgiving edge target, suppress native header drag until release, and preserve the live width through polling before committing it to browser-local preferences.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Stable torrent column resizing",
    "summary": "Eliminates resize/reorder gesture overlap and one-second polling snap-back so torrent columns resize predictably even during slow drags.",
    "highlights": [
        "The resize edge now has a wider, more forgiving pointer target instead of requiring pixel-perfect divider placement.",
        "Beginning a resize temporarily disables native header dragging, so the same gesture cannot reorder the column.",
        "An in-progress width is retained across the one-second torrent refresh instead of snapping back to the last saved width mid-drag."
    ],
    "fixes": [
        "Fixes intermittent column movement when the browser interpreted an edge resize as an HTML drag operation.",
        "Fixes visible width jumps when the live torrent render occurred before the resize pointer was released."
    ],
    "technical": [
        "The active torrentColumnResize width now takes precedence over persisted tdColumns width state during render-time width application.",
        "Resize pointerdown runs in the capture phase, reserves a 14 px interior edge zone, disables the active header's draggable flag, and restores it when resizing completes.",
        "The visible resize handle expands to a 16 px hit target while retaining a one-pixel visual divider so the affordance stays visually light."
    ],
    "validation": [
        "The UI audit requires live-width precedence, resize/reorder exclusion, the expanded hit target, and the updated manual multi-refresh resize test.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} stable torrent column resizing")
