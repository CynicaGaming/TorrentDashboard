#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.99"
TARGET_VERSION = "0.5.100"


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
        raise RuntimeError("Expected v0.5.99 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(
        ROOT / "static" / "app.js",
        f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0599" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.99 service-worker references")
    text = text.replace("torrent-dashboard-v0599", "torrent-dashboard-v05100")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"

    replace_once(
        path,
        "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;\nfunction startTorrentColumnResize(event,handle){",
        """let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;
function torrentRightmostColumnResizeMaxWidth(th,startWidth){
  const table=th?.closest('table'),wrap=table?.closest('.table-wrap');if(!table||!wrap||wrap.clientWidth<=0)return TORRENT_COLUMN_MAX_WIDTH;
  const visible=[...table.querySelectorAll('thead th[data-col]')].filter(cell=>!cell.classList.contains('torrent-column-hidden'));if(!visible.length||visible[visible.length-1]!==th)return TORRENT_COLUMN_MAX_WIDTH;
  let reserved=0;for(const selector of ['thead th.check','thead th.row-actions-head']){const cell=table.querySelector(selector);if(cell)reserved+=cell.getBoundingClientRect().width}
  let other=0;for(const cell of visible){if(cell!==th)other+=cell.getBoundingClientRect().width}
  const room=Math.floor(wrap.clientWidth-reserved-other);if(!Number.isFinite(room))return TORRENT_COLUMN_MAX_WIDTH;
  const ceiling=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,room)),start=Math.max(TORRENT_COLUMN_HARD_MIN,Math.round(Number(startWidth)||0));
  return Math.max(start,ceiling);
}
function startTorrentColumnResize(event,handle){""",
        "rightmost resize ceiling helper",
    )

    replace_once(
        path,
        "const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());",
        "const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentRightmostColumnResizeMaxWidth(th,startWidth),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());",
        "rightmost resize max setup",
    )

    replace_once(
        path,
        "th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};",
        "th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,maxWidth,pointerId:event.pointerId,handle,th};",
        "rightmost resize max state",
    )

    replace_once(
        path,
        "const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();",
        "const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(resize.maxWidth,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();",
        "conditional resize clamp",
    )


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary. A resize changes only that data column. It may consume unused spacer width and, once the visible data columns exceed the available center viewport, extend the configurable data plane into horizontal scrolling rather than shrinking another column or stopping at an artificial Actions boundary.",
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary. A resize changes only that data column. Interior data columns may consume unused spacer width and, once the visible data columns exceed the available center viewport, extend the configurable data plane into horizontal scrolling rather than shrinking another column. The rightmost visible data column is the exception: when the layout fits, its right edge stops at the pinned Actions rail so that column alone cannot create new horizontal overflow. Existing overflow created by earlier columns remains scrollable and is never repaired by silently resizing another column.",
        "hybrid rightmost resize design rule",
    )

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump. Verify the active column's left edge stays fixed and only the dragged right boundary moves; every other visible data column must keep its width while later columns translate as a block. Continue widening after the flexible spacer is exhausted and verify an internal horizontal scrollbar appears without page-level overflow; the dragged column must keep following the pointer without requiring any other column to be resized first.",
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump. Verify the active column's left edge stays fixed and only the dragged right boundary moves; every other visible data column must keep its width while later columns translate as a block. For an interior data column, continue widening after the flexible spacer is exhausted and verify an internal horizontal scrollbar appears without page-level overflow; the dragged column must keep following the pointer without requiring any other column to be resized first. Then use a fitting layout and widen the rightmost visible data column until it reaches Actions: its boundary must stop at the pinned Actions rail and the gesture must not create a new horizontal scrollbar. If the layout already overflows because of earlier columns, resizing the rightmost column must not increase the existing scroll width.",
        "hybrid resize manual test",
    )


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    replace_once(
        path,
        "assert 'function torrentColumnResizeMaxWidth' not in app_js",
        "assert 'function torrentColumnResizeMaxWidth' not in app_js and 'function torrentRightmostColumnResizeMaxWidth' in app_js\n    assert \"visible[visible.length-1]!==th\" in app_js and \"return TORRENT_COLUMN_MAX_WIDTH\" in app_js",
        "rightmost resize helper validator",
    )
    replace_once(
        path,
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths\" in app_js",
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentRightmostColumnResizeMaxWidth(th,startWidth),prefs=snapshotTorrentColumnWidths\" in app_js",
        "rightmost resize start validator",
    )
    replace_once(
        path,
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js and 'Math.min(TORRENT_COLUMN_MAX_WIDTH' in app_js",
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js and 'Math.min(resize.maxWidth' in app_js",
        "rightmost resize clamp validator",
    )
    replace_once(
        path,
        "assert 'maxWidth:torrentColumnResizeMaxWidth' not in app_js and 'resize.maxWidth' not in app_js",
        "assert 'maxWidth:torrentColumnResizeMaxWidth' not in app_js and 'maxWidth=torrentRightmostColumnResizeMaxWidth(th,startWidth)' in app_js and 'resize.maxWidth' in app_js",
        "rightmost max state validator",
    )
    replace_once(
        path,
        "assert 'configurable data plane scrolls horizontally inside the torrent viewport' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "assert 'configurable data plane scrolls horizontally inside the torrent viewport' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'rightmost visible data column is the exception' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "hybrid resize design validator",
    )
    replace_once(
        path,
        "assert 'internal horizontal scrollbar appears without page-level overflow' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "assert 'internal horizontal scrollbar appears without page-level overflow' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n    assert 'gesture must not create a new horizontal scrollbar' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "hybrid resize testing validator",
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
    decisions.append(
        "Use a hybrid resize boundary: interior data columns retain scroll-native independent resizing, while the rightmost visible data column cannot create additional horizontal overflow past the fixed Actions rail."
    )

    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Rightmost column resize boundary",
        "summary": "Keeps v0.5.99's native-feeling independent resizing while preventing the rightmost visible torrent column from creating a new horizontal scrollbar past the pinned Actions rail.",
        "highlights": [
            "Interior columns retain v0.5.99 behavior: they resize independently and may extend the data plane into the torrent viewport's internal horizontal scrolling when the chosen widths require it.",
            "The rightmost visible data column now receives a gesture-specific ceiling derived from the live torrent viewport after reserving the frozen 40 px selection rail, frozen 48 px Actions rail, and every other visible data column.",
            "A fitting layout can use all remaining spacer width, but the rightmost boundary stops when it reaches Actions instead of generating a new horizontal scrollbar.",
            "Already-wide browser-local layouts are not rewritten; overflow from earlier columns remains scrollable and no unrelated column is shrunk automatically."
        ],
        "fixes": [
            "Prevents the rightmost data column from being dragged underneath/past the pinned Actions surface and unnecessarily increasing horizontal scroll width.",
            "Preserves the less-constrained v0.5.99 interaction for all non-rightmost column boundaries."
        ],
        "technical": [
            "Adds torrentRightmostColumnResizeMaxWidth(), which returns the existing 8192 px safety maximum for interior columns and a viewport-derived ceiling only for the last visible data header.",
            "If a saved layout already exceeds the viewport, the rightmost gesture ceiling never starts below the column's rendered width, avoiding resize jumps or silent layout repair.",
            "The fixed selection/actions rails, flexible spacer, polling deferral, drag/reorder exclusivity, and browser-local tdColumns persistence remain unchanged."
        ],
        "validation": [
            "The UI audit requires the conditional rightmost-only ceiling and rejects restoration of the old all-column torrentColumnResizeMaxWidth helper.",
            "Manual coverage distinguishes interior overflow behavior from the rightmost boundary: interior resizing may create contained scrolling, while the last visible data column cannot create or increase overflow past Actions.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "known_issues": copy.deepcopy(previous.get("known_issues") or []),
        "architecture": copy.deepcopy(previous.get("architecture") or []),
        "decisions": decisions,
        "next_steps": copy.deepcopy(previous.get("next_steps") or []),
    })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def regenerate() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    update_versions()
    update_javascript()
    update_docs()
    update_validator()
    update_release_metadata()
    regenerate()


if __name__ == "__main__":
    main()
