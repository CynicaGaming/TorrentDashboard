#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.98"
TARGET_VERSION = "0.5.99"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match in {path.relative_to(ROOT)}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_versions() -> None:
    replace_once(
        ROOT / "dashboard.py",
        f'VERSION = "{PREVIOUS_VERSION}"',
        f'VERSION = "{TARGET_VERSION}"',
        "dashboard version",
    )

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count(PREVIOUS_VERSION) < 4:
        raise RuntimeError("Expected v0.5.98 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(
        ROOT / "static" / "app.js",
        f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0598" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.98 service-worker references")
    text = text.replace("torrent-dashboard-v0598", "torrent-dashboard-v0599")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"

    replace_once(
        path,
        """function torrentColumnResizeMaxWidth(th,startWidth){
  const table=th?.closest('table'),wrap=table?.closest('.table-wrap');if(!table||!wrap||wrap.clientWidth<=0)return TORRENT_COLUMN_MAX_WIDTH;
  let reserved=0;for(const selector of ['thead th.check','thead th.row-actions-head']){const cell=table.querySelector(selector);if(cell)reserved+=cell.getBoundingClientRect().width}
  let other=0;table.querySelectorAll('thead th[data-col]').forEach(cell=>{if(cell===th||cell.classList.contains('torrent-column-hidden'))return;other+=cell.getBoundingClientRect().width});
  const room=Math.floor(wrap.clientWidth-reserved-other);if(!Number.isFinite(room))return TORRENT_COLUMN_MAX_WIDTH;
  const ceiling=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,room)),start=Math.max(TORRENT_COLUMN_HARD_MIN,Math.round(Number(startWidth)||0));
  return Math.max(start,ceiling);
}
""",
        "",
        "v0.5.98 resize ceiling helper",
    )

    replace_once(
        path,
        "const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentColumnResizeMaxWidth(th,startWidth),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());",
        "const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());",
        "resize start ceiling removal",
    )

    replace_once(
        path,
        "th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,maxWidth,pointerId:event.pointerId,handle,th};",
        "th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};",
        "resize state ceiling removal",
    )

    replace_once(
        path,
        "const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(resize.maxWidth,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();",
        "const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();",
        "scroll-native resize clamp",
    )


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    replace_once(
        path,
        "/* 0.5.98 pinned actions with bounded torrent-column resizing. */",
        "/* 0.5.99 frozen edge rails and scroll-native torrent-column resizing. */",
        "torrent-column contract comment",
    )

    replace_once(
        path,
        '#torrentTable th.row-spacer-head,#torrentTable td.row-spacer{width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;min-inline-size:0!important;max-inline-size:none!important;padding-left:0;padding-right:0}',
        '#torrentTable th.check,#torrentTable td.check{width:40px!important;min-width:40px!important;max-width:40px!important;inline-size:40px!important;min-inline-size:40px!important;max-inline-size:40px!important;position:sticky;left:0;box-sizing:border-box;box-shadow:1px 0 0 color-mix(in srgb,var(--border) 78%,transparent)}\n'
        '#torrentTable th.check{z-index:9;background:var(--panel3)}\n'
        '#torrentTable td.check{z-index:4;background:var(--panel)}\n'
        '#torrentTable tbody tr:hover td.check{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}\n'
        '#torrentTable th.row-spacer-head,#torrentTable td.row-spacer{width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;min-inline-size:0!important;max-inline-size:none!important;padding-left:0;padding-right:0}',
        "frozen selection rail",
    )

    replace_once(
        path,
        '@media(max-width:820px){.column-resize-handle{display:none!important}#torrentTable td.row-spacer{display:none!important}}',
        '@media(max-width:820px){.column-resize-handle{display:none!important}#torrentTable td.row-spacer{display:none!important}#torrentTable th.check,#torrentTable td.check{position:static;left:auto;box-shadow:none}}',
        "responsive frozen rail reset",
    )


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary. A resize may consume unused spacer width, but the pinned 48 px Actions boundary is a hard right-side ceiling: dragging a data column wider must stop before it can create new horizontal overflow.",
        "- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary. A resize changes only that data column. It may consume unused spacer width and, once the visible data columns exceed the available center viewport, extend the configurable data plane into horizontal scrolling rather than shrinking another column or stopping at an artificial Actions boundary.",
        "scroll-native resize design rule",
    )
    replace_once(
        design,
        "- The far-right row-actions column is a fixed 48 px sticky control surface. A non-interactive flexible spacer immediately before it absorbs unused table width, keeping the actions column pinned to the torrent viewport's right edge whenever the visible data columns fit. New resize gestures cannot consume beyond that spacer and pinned Actions boundary, so resizing does not create horizontal overflow. A browser that already has an intentionally oversized saved layout may still scroll its data region internally until those widths are narrowed or Reset columns is used; page-level horizontal overflow remains contained by the torrent viewport. The actions surface has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior.",
        "- The selection checkbox and far-right row-actions column are frozen edge rails: 40 px on the left and 48 px on the right. A non-interactive flexible spacer immediately before Actions absorbs unused center width when the visible data columns fit. When configured widths exceed the center viewport, the configurable data plane scrolls horizontally inside the torrent viewport while both fixed rails remain available and page-level horizontal overflow stays contained. Neither rail has data-column identity, width persistence, resize handles, reorder gestures, visibility controls, or sorting behavior.",
        "frozen edge rails design rule",
    )

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "Continue widening until the data region reaches the pinned Actions surface and verify the boundary stops there rather than creating new horizontal overflow.",
        "Continue widening after the flexible spacer is exhausted and verify an internal horizontal scrollbar appears without page-level overflow; the dragged column must keep following the pointer without requiring any other column to be resized first.",
        "scroll-native resize manual test",
    )
    replace_once(
        testing,
        "- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize, reorder, hide, or sort behavior.",
        "- Verify the selection checkbox stays frozen at the left edge and the row-actions control stays frozen at the right edge while the configurable data columns scroll horizontally between them. Neither fixed rail may expose resize, reorder, hide, or sort behavior.",
        "frozen rails manual test",
    )


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"

    replace_once(
        path,
        "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js and 'function torrentColumnResizeMaxWidth' in app_js",
        "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js\n    assert 'function torrentColumnResizeMaxWidth' not in app_js",
        "resize helper validator",
    )
    replace_once(
        path,
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),maxWidth=torrentColumnResizeMaxWidth(th,startWidth)\" in app_js",
        "assert \"minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths\" in app_js",
        "resize start validator",
    )
    replace_once(
        path,
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js and 'Math.min(resize.maxWidth' in app_js",
        "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js and 'Math.min(TORRENT_COLUMN_MAX_WIDTH' in app_js",
        "resize clamp validator",
    )
    replace_once(
        path,
        "assert \"['thead th.check','thead th.row-actions-head']\" in app_js and \"wrap.clientWidth-reserved-other\" in app_js",
        "assert 'maxWidth:torrentColumnResizeMaxWidth' not in app_js and 'resize.maxWidth' not in app_js",
        "removed viewport ceiling validator",
    )
    replace_once(
        path,
        "assert '0.5.98 pinned actions with bounded torrent-column resizing' in app_css",
        "assert '0.5.99 frozen edge rails and scroll-native torrent-column resizing' in app_css",
        "CSS contract validator",
    )
    replace_once(
        path,
        "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions','0.5.96 content-aligned one-edge torrent-column resizing','0.5.97 pinned torrent actions and contained horizontal overflow'):",
        "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions','0.5.96 content-aligned one-edge torrent-column resizing','0.5.97 pinned torrent actions and contained horizontal overflow','0.5.98 pinned actions with bounded torrent-column resizing'):",
        "stale CSS validator",
    )
    replace_once(
        path,
        "assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css",
        "assert 'width:40px!important;min-width:40px!important;max-width:40px!important;inline-size:40px!important' in app_css\n    assert '#torrentTable th.check{z-index:9;background:var(--panel3)}' in app_css and '#torrentTable td.check{z-index:4;background:var(--panel)}' in app_css\n    assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css",
        "frozen edge width validator",
    )
    replace_once(
        path,
        "assert 'pinned 48 px Actions boundary is a hard right-side ceiling' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "assert 'configurable data plane scrolls horizontally inside the torrent viewport' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
        "design-language scroll validator",
    )
    replace_once(
        path,
        "assert 'boundary stops there rather than creating new horizontal overflow' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "assert 'internal horizontal scrollbar appears without page-level overflow' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
        "manual scroll validator",
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
        "Prefer native single-column resizing over a viewport-derived resize ceiling: fixed selection/actions rails remain pinned while user-chosen data widths may create horizontal scrolling only inside the torrent viewport."
    )

    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Frozen edge rails and scroll-native column resizing",
        "summary": "Removes the artificial right-side resize ceiling so a torrent column can be resized independently while the fixed selection and Actions controls remain pinned at the viewport edges.",
        "highlights": [
            "Removes the v0.5.98 viewport-derived maximum width from resize gestures; the active column can again follow the pointer up to the existing safety maximum without requiring space to be freed from other columns first.",
            "Makes the 40 px selection checkbox column sticky on the left, matching the existing fixed 48 px Actions surface on the right.",
            "Keeps the flexible spacer for layouts that fit, but allows deliberately wider browser-local data layouts to use the torrent viewport's internal horizontal scroll area.",
            "Preserves one-edge resizing, polling deferral, browser-local tdColumns persistence, header sorting/reordering, and mobile reset behavior."
        ],
        "fixes": [
            "Eliminates the constrained resize behavior where a user had to shrink other columns before widening the column they actually wanted to change.",
            "Keeps both non-configurable control columns available while wide data layouts scroll between them instead of pushing the surrounding dashboard wider."
        ],
        "technical": [
            "The resize state no longer carries a gesture-specific maxWidth and moveTorrentColumnResize clamps only to the per-gesture minimum plus the existing absolute 8192 px safety maximum.",
            "The table min-width still follows the sum of persisted visible data widths plus fixed control widths, so overflow is represented as table-wrap scrollWidth rather than page-level layout growth.",
            "The left selection cells now use sticky left:0 with opaque row/header backgrounds and the same edge-separation treatment as the sticky Actions column; responsive layouts clear that desktop stickiness."
        ],
        "validation": [
            "The UI audit rejects reintroduction of torrentColumnResizeMaxWidth/resize.maxWidth and requires frozen 40 px selection plus 48 px Actions rails.",
            "Manual coverage verifies a column continues widening after spacer slack is exhausted, an internal horizontal scrollbar appears when required, neither fixed rail moves, and no unrelated data column changes width.",
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
