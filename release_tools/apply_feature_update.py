#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.95"
TARGET_VERSION = "0.5.96"


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
        raise RuntimeError("Expected v0.5.95 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(
        ROOT / "static" / "app.js",
        f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = text.replace("torrent-dashboard-v0595", "torrent-dashboard-v0596")
    if f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.95 service-worker asset references")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    replacements = (
        (
            "/* 0.5.94 deterministic torrent-column header interactions. */",
            "/* 0.5.96 content-aligned one-edge torrent-column resizing. */",
            "torrent-column contract comment",
        ),
        (
            '#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:center;padding-left:28px;padding-right:28px;outline:none}',
            '#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:left;padding-left:12px;padding-right:28px;outline:none}',
            "data-header alignment",
        ),
        (
            '#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:center}',
            '#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:right}',
            "swarm-header alignment",
        ),
        (
            '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:center;cursor:grab;pointer-events:auto}',
            '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px;cursor:grab;pointer-events:auto}\n#torrentTable thead th[data-col="seeds"] .torrent-sort-heading,#torrentTable thead th[data-col="peers"] .torrent-sort-heading{justify-content:flex-end;padding-left:18px;padding-right:0}\n#torrentTable thead th[data-col="seeds"] .torrent-sort-icon,#torrentTable thead th[data-col="peers"] .torrent-sort-icon{left:0;right:auto}',
            "sort-heading alignment",
        ),
        (
            '#torrentTable th[data-col],#torrentTable td[data-col]{box-sizing:border-box}',
            '#torrentTable th[data-col],#torrentTable td[data-col]{box-sizing:border-box}\n#torrentTable.torrent-column-fixed-layout{table-layout:fixed}',
            "fixed resize layout",
        ),
    )
    for old, new, label in replacements:
        replace_once(path, old, new, label)


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    replace_once(
        path,
        "const TORRENT_COLUMN_HARD_MIN=48;\nconst TORRENT_COLUMN_MAX_WIDTH=720;",
        "const TORRENT_COLUMN_HARD_MIN=48;\nconst TORRENT_COLUMN_MAX_WIDTH=8192;\nconst TORRENT_FIXED_COLUMN_WIDTH=88;",
        "torrent-column width limits",
    )

    old = """function saveTorrentColumnPreferences(prefs){localStorage.tdColumns=JSON.stringify(prefs)}
function applyTorrentColumnWidth(key,width=null){const valid=width!==null&&width!==undefined&&Number.isFinite(Number(width)),value=valid?`${Math.round(Number(width))}px`:'';document.querySelectorAll(`#torrentTable [data-col=\"${key}\"]`).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value;cell.classList.toggle('torrent-column-sized',valid)})}
function applyTorrentColumnWidths(prefs=torrentColumnPreferences()){
  for(const column of TORRENT_COLUMN_DEFS){
    const liveWidth=torrentColumnResize?.key===column.key?torrentColumnResize.width:null;
    applyTorrentColumnWidth(column.key,liveWidth??prefs.widths?.[column.key]);
  }
}
function saveTorrentColumnWidth(key,width){const prefs=torrentColumnPreferences(),value=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,Math.round(Number(width)||0)));prefs.widths[key]=value;saveTorrentColumnPreferences(prefs);applyTorrentColumnWidth(key,value)}
"""
    new = """function saveTorrentColumnPreferences(prefs){localStorage.tdColumns=JSON.stringify(prefs)}
function torrentVisibleColumnKeys(prefs=torrentColumnPreferences()){return prefs.order.filter(key=>torrentColumnVisible(key,prefs))}
function torrentColumnLayoutWidth(prefs=torrentColumnPreferences()){
  const keys=torrentVisibleColumnKeys(prefs);if(!keys.length)return null;let total=TORRENT_FIXED_COLUMN_WIDTH;
  for(const key of keys){const liveWidth=torrentColumnResize?.key===key?torrentColumnResize.width:null,width=liveWidth??prefs.widths?.[key];if(!Number.isFinite(Number(width)))return null;total+=Math.round(Number(width))}
  return total;
}
function syncTorrentTableWidth(prefs=torrentColumnPreferences()){
  const table=$('#torrentTable');if(!table)return;const width=torrentColumnLayoutWidth(prefs),locked=Number.isFinite(width);
  table.classList.toggle('torrent-column-fixed-layout',locked);table.style.width=locked?`${width}px`:'';table.style.minWidth=locked?`${width}px`:'';
}
function snapshotTorrentColumnWidths(prefs=torrentColumnPreferences()){
  const table=$('#torrentTable');if(!table)return prefs;
  table.querySelectorAll('thead th[data-col]').forEach(th=>{if(th.classList.contains('torrent-column-hidden'))return;const width=Math.round(th.getBoundingClientRect().width);if(Number.isFinite(width)&&width>=TORRENT_COLUMN_HARD_MIN&&width<=TORRENT_COLUMN_MAX_WIDTH)prefs.widths[th.dataset.col]=width});
  return prefs;
}
function applyTorrentColumnWidth(key,width=null){const valid=width!==null&&width!==undefined&&Number.isFinite(Number(width)),value=valid?`${Math.round(Number(width))}px`:'';document.querySelectorAll(`#torrentTable [data-col=\"${key}\"]`).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value;cell.classList.toggle('torrent-column-sized',valid)})}
function applyTorrentColumnWidths(prefs=torrentColumnPreferences()){
  for(const column of TORRENT_COLUMN_DEFS){
    const liveWidth=torrentColumnResize?.key===column.key?torrentColumnResize.width:null;
    applyTorrentColumnWidth(column.key,liveWidth??prefs.widths?.[column.key]);
  }
  syncTorrentTableWidth(prefs);
}
function saveTorrentColumnWidth(key,width){const prefs=torrentColumnPreferences(),value=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,Math.round(Number(width)||0)));prefs.widths[key]=value;saveTorrentColumnPreferences(prefs);applyTorrentColumnWidths(prefs)}
"""
    replace_once(path, old, new, "torrent-column width helpers")

    old = """function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth));
  th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};
  applyTorrentColumnWidth(key,startWidth);handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}
function moveTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);
}
"""
    new = """function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth)),prefs=snapshotTorrentColumnWidths(torrentColumnPreferences());
  th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};
  saveTorrentColumnPreferences(prefs);applyTorrentColumnWidths(prefs);handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}
function moveTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth();
}
"""
    replace_once(path, old, new, "one-edge resize gesture")


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    replacements = (
        (
            "assert 'const TORRENT_COLUMN_HARD_MIN=48' in app_js and 'const TORRENT_COLUMN_MAX_WIDTH=720' in app_js",
            "assert 'const TORRENT_COLUMN_HARD_MIN=48' in app_js and 'const TORRENT_COLUMN_MAX_WIDTH=8192' in app_js and 'const TORRENT_FIXED_COLUMN_WIDTH=88' in app_js",
            "width-limit validator",
        ),
        (
            "assert 'function applyTorrentColumnWidths' in app_js and 'function saveTorrentColumnWidth' in app_js",
            "assert 'function applyTorrentColumnWidths' in app_js and 'function saveTorrentColumnWidth' in app_js\n    assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js",
            "resize-layout validator",
        ),
        (
            "assert 'applyTorrentColumnWidth(key,startWidth)' in app_js and 'Math.max(resize.minWidth' in app_js",
            "assert 'prefs=snapshotTorrentColumnWidths(torrentColumnPreferences())' in app_js and 'Math.max(resize.minWidth' in app_js\n    assert 'applyTorrentColumnWidth(resize.key,resize.width);syncTorrentTableWidth()' in app_js",
            "resize-start validator",
        ),
        (
            "assert '0.5.94 deterministic torrent-column header interactions' in app_css",
            "assert '0.5.96 content-aligned one-edge torrent-column resizing' in app_css",
            "CSS contract validator",
        ),
        (
            "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers'):",
            "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions'):",
            "stale CSS validator",
        ),
        (
            "assert '#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:center;padding-left:28px;padding-right:28px;outline:none}' in app_css",
            "assert '#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:left;padding-left:12px;padding-right:28px;outline:none}' in app_css\n    assert '#torrentTable thead th[data-col=\"seeds\"],#torrentTable thead th[data-col=\"peers\"]{text-align:right}' in app_css",
            "header-alignment validator",
        ),
        (
            "assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:center;cursor:grab;pointer-events:auto}' in app_css",
            "assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px;cursor:grab;pointer-events:auto}' in app_css\n    assert '#torrentTable.torrent-column-fixed-layout{table-layout:fixed}' in app_css",
            "sort-heading validator",
        ),
        (
            "assert 'exact width currently rendered on screen' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
            "assert 'exact width currently rendered on screen' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'header labels follow the alignment of their body cells' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
            "design-language validator",
        ),
        (
            "assert 'header labels are visually centered' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
            "assert 'only the dragged right boundary moves' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
            "manual-test validator",
        ),
    )
    for old, new, label in replacements:
        replace_once(path, old, new, label)


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- On desktop/tablet, drag the centered header-label area horizontally to reorder a visible data column. The label drag surface is separate from the resize gutter so native reordering cannot begin from the resize target.",
        "- On desktop/tablet, drag the header-label area horizontally to reorder a visible data column. Header labels follow the alignment of their body cells rather than floating in the visual center of wide columns. The label drag surface is separate from the resize gutter so native reordering cannot begin from the resize target.",
        "header alignment design rule",
    )
    replace_once(
        design,
        "- Resize starts from the exact width currently rendered on screen. If automatic table layout rendered a column narrower than its normal ergonomic minimum, that existing width becomes the floor for that gesture rather than creating a pointer dead zone or jump. A 48 px hard safety floor protects persisted state.",
        "- Resize starts from the exact width currently rendered on screen. At pointer-down, the currently visible data-column widths are snapshotted into browser-local `tdColumns` state and held fixed for the gesture; changing the active column changes the table width by the same delta, so only the dragged right boundary moves while later columns translate without changing width. If automatic table layout rendered a column narrower than its normal ergonomic minimum, that existing width becomes the floor for that gesture rather than creating a pointer dead zone or jump. A 48 px hard safety floor protects persisted state.",
        "one-edge resize design rule",
    )
    replace_once(
        design,
        "- Torrent data header labels are centered with symmetric padding. The resize gutter occupies reserved edge padding and the sort chevron sits inside the centered label area, so neither affordance changes where the visible column boundary feels located.",
        "- Torrent data header labels follow body-cell alignment: ordinary text/status/progress columns align from the left content edge, while the right-aligned Seeds and Peers columns keep right-aligned headers. The resize gutter remains reserved at the inside right edge, and the sort chevron stays within the label surface rather than redefining the visible column boundary.",
        "header alignment detail",
    )

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "- Verify all data-header labels are visually centered between their column boundaries. The sort chevron must not shift the label toward the resize divider.",
        "- Verify data-header labels follow their body content instead of centering in wide columns: ordinary columns start from the left content edge, while Seeds and Peers remain right-aligned. The sort chevron must stay separate from the resize divider.",
        "manual header alignment test",
    )
    replace_once(
        testing,
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump.",
        "- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump. Verify the active column's left edge stays fixed and only the dragged right boundary moves; every other visible data column must keep its width while later columns translate as a block.",
        "manual one-edge resize test",
    )


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.get("releases")
    if not isinstance(releases, list):
        raise RuntimeError("release_notes/releases.json is missing releases")
    if any(str(item.get("version")) == TARGET_VERSION for item in releases if isinstance(item, dict)):
        raise RuntimeError(f"Release metadata already contains v{TARGET_VERSION}")
    previous = next((item for item in releases if isinstance(item, dict) and str(item.get("version")) == PREVIOUS_VERSION), None)
    if previous is None:
        raise RuntimeError(f"Could not find v{PREVIOUS_VERSION} release metadata")
    item = {
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Content-aligned one-edge torrent resizing",
        "summary": "Aligns torrent-table headers with their row content and makes a resize gesture move only the grabbed right boundary instead of letting automatic table layout redistribute neighboring widths.",
        "highlights": [
            "Torrent data headers now follow body-cell alignment instead of centering labels across wide columns; Seeds and Peers retain their right-aligned numeric treatment.",
            "Beginning a resize snapshots every currently visible data-column width, so untouched columns keep their exact width while columns to the right translate with the dragged boundary.",
            "The resize target remains the dedicated inward-only header gutter, preserving resize/reorder mutual exclusion and browser-local tdColumns persistence.",
        ],
        "fixes": [
            "Wide Name and other columns no longer make centered headings appear detached from the content beneath them.",
            "Resizing no longer appears to expand or contract a column from both sides because the browser cannot redistribute the other visible column widths during the gesture.",
        ],
        "technical": [
            "The first resize in a visible layout records the current rendered widths of its data columns, excluding the fixed selection checkbox and 48 px row-actions column, then uses a fixed table layout derived from those widths.",
            "The active column is the only data width changed by pointer movement; the table width changes by the identical delta, preserving the grabbed column's left boundary.",
            "The persisted width safety ceiling is raised from 720 px to 8192 px so legitimately wide automatic columns can be captured without snapping before the user begins narrowing them.",
        ],
        "validation": [
            "The UI audit requires content-aligned headers, a visible-column width snapshot, fixed-layout table geometry, one active resized width, and continued exclusion of selection/actions from configurable column identity.",
            "Manual regression coverage requires one-edge boundary movement, unchanged widths for every non-active visible data column, resize/reorder exclusivity, polling stability, and fixed action/select behavior.",
            "Existing source, design-language, JavaScript syntax, generated continuity, frontend/service-worker synchronization, and package-integrity gates remain required.",
        ],
        "known_issues": [],
        "architecture": list(previous.get("architecture") or []),
        "decisions": list(previous.get("decisions") or []) + [
            "Align torrent data headers with their body content rather than centering every label.",
            "When resizing, snapshot visible data-column widths and change table width with the active column so only the grabbed right boundary moves; keep selection and actions outside that model.",
        ],
        "next_steps": list(previous.get("next_steps") or []),
    }
    releases.append(item)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def generate_continuity() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    update_versions()
    update_css()
    update_javascript()
    update_validator()
    update_docs()
    update_release_metadata()
    generate_continuity()


if __name__ == "__main__":
    main()
