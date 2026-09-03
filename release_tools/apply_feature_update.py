#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.97"
TARGET_VERSION = "0.5.98"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match in {path.relative_to(ROOT)}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_versions() -> None:
    replace_once(ROOT / "dashboard.py", f'VERSION = "{PREVIOUS_VERSION}"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count(PREVIOUS_VERSION) < 4:
        raise RuntimeError("Expected v0.5.97 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(
        ROOT / "static" / "app.js",
        f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0597" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.97 service-worker references")
    text = text.replace("torrent-dashboard-v0597", "torrent-dashboard-v0598")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    old = """let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;
function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());
  th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};
  saveTorrentColumnPreferences(prefs);applyTorrentColumnWidths(prefs);handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}
function moveTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();
}"""
    new = """let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;
function torrentColumnResizeMaxWidth(th,startWidth){
  const table=th?.closest('table'),wrap=table?.closest('.table-wrap');if(!table||!wrap||wrap.clientWidth<=0)return TORRENT_COLUMN_MAX_WIDTH;
  let reserved=0;for(const selector of ['thead th.check','thead th.row-actions-head']){const cell=table.querySelector(selector);if(cell)reserved+=cell.getBoundingClientRect().width}
  let other=0;table.querySelectorAll('thead th[data-col]').forEach(cell=>{if(cell===th||cell.classList.contains('torrent-column-hidden'))return;other+=cell.getBoundingClientRect().width});
  const room=Math.floor(wrap.clientWidth-reserved-other);if(!Number.isFinite(room))return TORRENT_COLUMN_MAX_WIDTH;
  const ceiling=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,room)),start=Math.max(TORRENT_COLUMN_HARD_MIN,Math.round(Number(startWidth)||0));
  return Math.max(start,ceiling);
}
function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentColumnResizeMaxWidth(th,startWidth),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());
  th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,maxWidth,pointerId:event.pointerId,handle,th};
  saveTorrentColumnPreferences(prefs);applyTorrentColumnWidths(prefs);handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}
function moveTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(resize.maxWidth,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();
}"""
    replace_once(path, old, new, "right-edge resize ceiling")


def update_css() -> None:
    replace_once(
        ROOT / "static" / "app.css",
        "/* 0.5.97 pinned torrent actions and contained horizontal overflow. */",
        "/* 0.5.98 pinned actions with bounded torrent-column resizing. */",
        "torrent-column contract comment",
    )


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary.",
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary. A resize may consume unused spacer width, but the pinned 48 px Actions boundary is a hard right-side ceiling: dragging a data column wider must stop before it can create new horizontal overflow.",
        "bounded resize design rule",
    )
    replace_once(
        design,
        "- The far-right row-actions column is a fixed 48 px sticky control surface. A non-interactive flexible spacer immediately before it absorbs unused table width, keeping the actions column pinned to the torrent viewport's right edge whenever the visible data columns fit. If customized data widths exceed the viewport, only the data region scrolls horizontally beneath the pinned actions surface; page-level horizontal overflow remains contained by the torrent viewport. The actions surface has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior.",
        "- The far-right row-actions column is a fixed 48 px sticky control surface. A non-interactive flexible spacer immediately before it absorbs unused table width, keeping the actions column pinned to the torrent viewport's right edge whenever the visible data columns fit. New resize gestures cannot consume beyond that spacer and pinned Actions boundary, so resizing does not create horizontal overflow. A browser that already has an intentionally oversized saved layout may still scroll its data region internally until those widths are narrowed or Reset columns is used; page-level horizontal overflow remains contained by the torrent viewport. The actions surface has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior.",
        "pinned actions overflow rule",
    )

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump. Verify the active column's left edge stays fixed and only the dragged right boundary moves; every other visible data column must keep its width while later columns translate as a block.",
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump. Verify the active column's left edge stays fixed and only the dragged right boundary moves; every other visible data column must keep its width while later columns translate as a block. Continue widening until the data region reaches the pinned Actions surface and verify the boundary stops there rather than creating new horizontal overflow.",
        "bounded resize manual test",
    )


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    replace_once(
        path,
        "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js",
        "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js and 'function torrentColumnResizeMaxWidth' in app_js",
        "resize ceiling helper validator",
    )
    replace_once(
        path,
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth))\" in app_js",
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentColumnResizeMaxWidth(th,startWidth)\" in app_js",
        "resize ceiling state validator",
    )
    replace_once(
        path,
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js",
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js and 'Math.min(resize.maxWidth' in app_js\n    assert \"['thead th.check','thead th.row-actions-head']\" in app_js and \"wrap.clientWidth-reserved-other\" in app_js",
        "right boundary geometry validator",
    )
    replace_once(
        path,
        "assert '0.5.97 pinned torrent actions and contained horizontal overflow' in app_css",
        "assert '0.5.98 pinned actions with bounded torrent-column resizing' in app_css",
        "CSS contract validator",
    )
    replace_once(
        path,
        "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions','0.5.96 content-aligned one-edge torrent-column resizing'):",
        "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions','0.5.96 content-aligned one-edge torrent-column resizing','0.5.97 pinned torrent actions and contained horizontal overflow'):",
        "stale CSS validator",
    )
    replace_once(
        path,
        "assert 'flexible spacer immediately before it absorbs unused table width' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "assert 'flexible spacer immediately before it absorbs unused table width' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'pinned 48 px Actions boundary is a hard right-side ceiling' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "design bounded-resize validator",
    )
    replace_once(
        path,
        "assert 'only the dragged right boundary moves' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "assert 'only the dragged right boundary moves' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n    assert 'boundary stops there rather than creating new horizontal overflow' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "manual bounded-resize validator",
    )


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.get("releases") or []
    if any(str(item.get("version")) == TARGET_VERSION for item in releases):
        raise RuntimeError(f"Release metadata already contains v{TARGET_VERSION}")
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS_VERSION), None)
    if not previous:
        raise RuntimeError(f"Missing v{PREVIOUS_VERSION} release metadata")

    decisions = copy.deepcopy(previous.get("decisions") or [])
    decisions.append("Treat the pinned Actions edge as the maximum width boundary for new torrent-column resize gestures; consume spacer slack first, then stop rather than creating new horizontal overflow or shrinking unrelated columns.")

    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Bounded torrent-column resizing",
        "summary": "Stops torrent-column resize gestures at the pinned Actions boundary so widening a column cannot create new horizontal overflow.",
        "highlights": [
            "Calculates each resize gesture's maximum width from the live torrent viewport after reserving the rendered selection checkbox, pinned Actions column, and every other visible data column.",
            "A column may expand into the flexible spacer introduced in v0.5.97, but the drag stops when that slack is exhausted and the data region reaches Actions.",
            "Preserves v0.5.96 one-edge geometry: the active column's left edge stays fixed and no unrelated column is shrunk or redistributed.",
            "Existing oversized browser-local layouts are not silently rewritten; they can still be narrowed or reset without allowing a new resize to make them wider."
        ],
        "fixes": [
            "Prevents rightward column resizing from pushing data underneath the pinned Actions surface and creating horizontal overflow.",
            "Makes the right-side fixed boundary behave symmetrically with the already-stable fixed selection edge."
        ],
        "technical": [
            "torrentColumnResizeMaxWidth measures the table viewport and rendered fixed/data header widths at pointer-down, producing a gesture-specific maximum independent of persisted constants.",
            "moveTorrentColumnResize clamps against both the gesture-specific minimum and maximum, while the existing 8192 px safety ceiling remains the absolute fallback.",
            "The cap is based on viewport geometry before fixed-layout locking, so spacer slack is available to the active column without changing any other data width."
        ],
        "validation": [
            "The UI audit requires the live viewport/fixed-column resize ceiling, gesture-specific maxWidth state, and pointer-move clamping against that ceiling.",
            "Manual coverage widens multiple columns until they meet the pinned Actions edge and verifies no new horizontal scrollbar or data-under-actions overflow appears.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "known_issues": [],
        "architecture": copy.deepcopy(previous.get("architecture") or []),
        "next_steps": copy.deepcopy(previous.get("next_steps") or []),
        "decisions": decisions,
    })
    data["releases"] = releases
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_continuity() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    update_versions()
    update_javascript()
    update_css()
    update_docs()
    update_validator()
    update_release_metadata()
    generate_continuity()


if __name__ == "__main__":
    main()
