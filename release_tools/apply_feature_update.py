#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.102"
TARGET_VERSION = "0.5.103"


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
        raise RuntimeError("Expected v0.5.102 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(ROOT / "static" / "app.js", f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v05102" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.102 service-worker references")
    text = text.replace("torrent-dashboard-v05102", "torrent-dashboard-v05103")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    old_layout = """function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-workspace-height');return}
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(360,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-height')!==value)workspace.style.setProperty('--torrent-workspace-height',value);
}
window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout()}));"""
    new_layout = """function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-workspace-height');return}
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(360,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-height')!==value)workspace.style.setProperty('--torrent-workspace-height',value);
}
function syncMobileBulkbarOffset(){
  const bulk=$('#bulkbar'),pane=$('#torrentDetailPane');if(!bulk||!pane)return;
  if(!window.matchMedia?.('(max-width:700px)').matches){bulk.style.removeProperty('--torrent-bulk-bottom');return}
  const viewportHeight=window.visualViewport?.height||window.innerHeight;
  const paneTop=pane.getBoundingClientRect().top;
  const clearance=Math.max(116,Math.min(Math.max(116,viewportHeight-56),Math.ceil(viewportHeight-paneTop+10)));
  bulk.style.setProperty('--torrent-bulk-bottom',`${clearance}px`);
}
window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout();syncMobileBulkbarOffset()}));
window.visualViewport?.addEventListener('resize',()=>requestAnimationFrame(syncMobileBulkbarOffset));"""
    replace_once(path, old_layout, new_layout, "mobile bulkbar workspace synchronization")

    old_render = "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyFixedTorrentColumnLayout();syncTorrentSortHeaders();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));syncTorrentWorkspaceLayout()}"
    new_render = "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyFixedTorrentColumnLayout();syncTorrentSortHeaders();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));syncTorrentWorkspaceLayout();requestAnimationFrame(syncMobileBulkbarOffset)}"
    replace_once(path, old_render, new_render, "render-time mobile bulkbar synchronization")

    old_detail = """function syncDetailDock(){
  const pane=$('#torrentDetailPane'),handle=$('#detailHandle'),workspace=pane?.closest('.torrent-workspace');if(!pane||!handle)return;
  const expanded=!!state.detailExpanded,selected=!!state.detail;
  pane.classList.toggle('collapsed',!expanded);pane.classList.toggle('has-selection',selected);workspace?.classList.toggle('detail-expanded',expanded);
  handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?(detailCurrentTorrent()?.name||'Selected torrent'):'';
  syncTorrentWorkspaceLayout();
}"""
    new_detail = """function syncDetailDock(){
  const pane=$('#torrentDetailPane'),handle=$('#detailHandle'),workspace=pane?.closest('.torrent-workspace');if(!pane||!handle)return;
  const expanded=!!state.detailExpanded,selected=!!state.detail;
  pane.classList.toggle('collapsed',!expanded);pane.classList.toggle('has-selection',selected);workspace?.classList.toggle('detail-expanded',expanded);
  handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?(detailCurrentTorrent()?.name||'Selected torrent'):'';
  syncTorrentWorkspaceLayout();requestAnimationFrame(syncMobileBulkbarOffset);setTimeout(syncMobileBulkbarOffset,180);
}"""
    replace_once(path, old_detail, new_detail, "detail-dock bulkbar synchronization")


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    marker = "/* 0.5.102 contextual torrent row actions. */\n@media(max-width:820px){#torrentTable tbody tr{-webkit-touch-callout:none}}"
    addition = marker + "\n\n/* 0.5.103 mobile bulk action layering. */\n@media(max-width:700px){.bulkbar{bottom:var(--torrent-bulk-bottom,116px)!important;z-index:74}}"
    replace_once(path, marker, addition, "mobile bulk action layering CSS")


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    needle = "- Torrent row commands use one shared context menu: right-click opens it on pointer-based desktop interfaces, while a deliberate long press opens it on touch. Touch movement cancels the pending long press so normal vertical scrolling is not intercepted.\n"
    addition = "- On mobile, the bulk-selection overlay must clear the current Torrent details pane rather than sharing its bottom stack. Its bottom offset follows the rendered detail pane so selection actions remain fully visible in both collapsed and expanded detail states.\n"
    text = design.read_text(encoding="utf-8")
    if text.count(needle) != 1:
        raise RuntimeError("Expected torrent row command guidance exactly once")
    design.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")

    testing = ROOT / "TESTING.md"
    needle = "- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing. Long-press a non-control area of a torrent card for roughly half a second and verify the same torrent context menu opens; move/scroll before the threshold and verify no menu opens. A normal tap must still open Torrent details, while the tap following a completed long press must not.\n"
    addition = "- On mobile, check a torrent while Torrent details is collapsed and verify the bulk action bar is fully visible above the disclosure bar and mobile navigation. Expand Torrent details while the torrent remains checked and verify the bulk action bar moves above the expanded sheet instead of being covered by it.\n"
    text = testing.read_text(encoding="utf-8")
    if text.count(needle) != 1:
        raise RuntimeError("Expected mobile fixed-column test exactly once")
    testing.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")


def update_validation() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    needle = "    assert 'Long-press a non-control area of a torrent card' in testing\n    print(\"UI string audit passed\")"
    replacement = """    assert 'Long-press a non-control area of a torrent card' in testing

    # 0.5.103 keeps the mobile bulk-selection overlay above the persistent
    # Torrent details surface instead of letting equal-z-index bottom overlays collide.
    assert 'function syncMobileBulkbarOffset()' in app_js
    assert "bulk.style.setProperty('--torrent-bulk-bottom'" in app_js
    assert "window.visualViewport?.addEventListener('resize'" in app_js
    assert 'setTimeout(syncMobileBulkbarOffset,180)' in app_js
    assert '0.5.103 mobile bulk action layering' in app_css
    assert 'bottom:var(--torrent-bulk-bottom,116px)!important;z-index:74' in app_css
    assert 'bulk-selection overlay must clear the current Torrent details pane' in design
    assert 'bulk action bar is fully visible above the disclosure bar' in testing
    print("UI string audit passed")"""
    replace_once(path, needle, replacement, "v0.5.103 UI validation")


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data["releases"]
    if any(item.get("version") == TARGET_VERSION for item in releases):
        raise RuntimeError(f"Release {TARGET_VERSION} already exists")
    previous = next((item for item in reversed(releases) if item.get("version") == PREVIOUS_VERSION), None)
    if previous is None:
        raise RuntimeError(f"Release {PREVIOUS_VERSION} not found")
    decisions = copy.deepcopy(previous.get("decisions", []))
    decisions.append("Treat the mobile bulk-selection overlay and Torrent details as stacked bottom surfaces: bulk actions must remain fully visible above the current detail pane instead of competing for the same layer and screen region.")
    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Mobile bulk action layering",
        "summary": "Keeps mobile bulk-selection controls above the persistent Torrent details dock or sheet instead of allowing the two bottom overlays to cover one another.",
        "highlights": [
            "Moves the mobile bulk-selection overlay above the currently rendered Torrent details surface rather than using a fixed bottom offset that collides with the detail dock.",
            "Tracks the detail pane's rendered top edge so the action bar remains clear when Torrent details is collapsed or expanded.",
            "Raises the bulk-selection overlay above the detail pane while keeping dialogs and context menus on their existing higher application layers."
        ],
        "fixes": [
            "Fixes checked-torrent bulk actions being partially hidden behind the collapsed Torrent details disclosure on mobile.",
            "Prevents the same layering conflict when Torrent details is expanded into the mobile sheet."
        ],
        "technical_notes": [
            "The mobile bulk bar now uses --torrent-bulk-bottom with a 116 px collapsed-state fallback and z-index 74, above the detail pane's z-index 72.",
            "syncMobileBulkbarOffset measures the rendered detail-pane top against the current visual viewport and keeps a 10 px separation while clamping the bulk bar on-screen.",
            "The offset is refreshed after torrent renders, detail collapse/expand transitions, window resizes, and visual-viewport resizes."
        ],
        "validation": [
            "The UI audit requires the dynamic mobile bulk offset, higher bulk layer, detail-transition synchronization, and documentation of the stacking contract.",
            "Manual mobile coverage checks checked torrents with Torrent details both collapsed and expanded and verifies all bulk controls remain visible and tappable.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "decisions": decisions,
        "known_issues": []
    })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    update_versions()
    update_javascript()
    update_css()
    update_docs()
    update_validation()
    update_release_metadata()
    subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", TARGET_VERSION], cwd=ROOT, check=True)
    print(f"Applied v{TARGET_VERSION} mobile bulk action layering fix")


if __name__ == "__main__":
    main()
