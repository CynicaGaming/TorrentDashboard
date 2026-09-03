#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.101"
TARGET_VERSION = "0.5.102"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match in {path.relative_to(ROOT)}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def regex_once(path: Path, pattern: str, replacement: str, label: str, flags: int = re.S) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} regex match in {path.relative_to(ROOT)}, found {count}")
    path.write_text(updated, encoding="utf-8")


def update_versions() -> None:
    replace_once(ROOT / "dashboard.py", f'VERSION = "{PREVIOUS_VERSION}"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count(PREVIOUS_VERSION) < 4:
        raise RuntimeError("Expected v0.5.101 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(ROOT / "static" / "app.js", f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v05101" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.101 service-worker references")
    text = text.replace("torrent-dashboard-v05101", "torrent-dashboard-v05102")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_index() -> None:
    path = ROOT / "static" / "index.html"
    old = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="state">Status</th><th data-col="progress">Progress</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th><th class="row-actions-head"></th></tr></thead>'
    new = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="state">Status</th><th data-col="progress">Progress</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th></tr></thead>'
    replace_once(path, old, new, "torrent header without actions rail")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    replace_once(path, "const TORRENT_FIXED_COLUMN_WIDTH=88;", "const TORRENT_FIXED_COLUMN_WIDTH=40;", "fixed torrent control width")

    replace_once(
        path,
        '<td class=\\"mobile-grid\\" data-col=\\"tags\\" data-label=\\"Tags\\"><span class=\\"torrent-column-text\\" title=\\"${esc(tags)}\\">${esc(tags||\'—\')}</span></td><td class=\\"row-actions\\"><button class=\\"more-row\\" aria-label=\\"Actions\\">•••</button></td></tr>`}',
        '<td class=\\"mobile-grid\\" data-col=\\"tags\\" data-label=\\"Tags\\"><span class=\\"torrent-column-text\\" title=\\"${esc(tags)}\\">${esc(tags||\'—\')}</span></td></tr>`}',
        "torrent row actions cell",
    )

    replace_once(
        path,
        "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}const server=tr.dataset.server,hash=tr.dataset.hash;if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}openDetail(server,hash)}",
        "function rowClick(e){if(Date.now()<torrentLongPressSuppressClickUntil){e.preventDefault();e.stopPropagation();return}const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;const server=tr.dataset.server,hash=tr.dataset.hash;if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}openDetail(server,hash)}",
        "torrent row click without actions button",
    )

    old_context = "function rowContext(e){const tr=e.target.closest('tr');if(!tr)return;e.preventDefault();showTorrentMenu(tr,{getBoundingClientRect:()=>({left:e.clientX,top:e.clientY,bottom:e.clientY,right:e.clientX})},true)}"
    new_context = """const TORRENT_LONG_PRESS_MS=550,TORRENT_LONG_PRESS_MOVE_PX=12;
let torrentLongPress=null,torrentLongPressSuppressClickUntil=0;
function torrentMenuPointAnchor(x,y){return{getBoundingClientRect:()=>({left:x,top:y,bottom:y,right:x})}}
function openTorrentMenuAtPoint(tr,x,y){showTorrentMenu(tr,torrentMenuPointAnchor(x,y),true)}
function clearTorrentLongPress(pointerId=null){
  const press=torrentLongPress;if(!press||(pointerId!==null&&press.pointerId!==pointerId))return;
  if(press.timer!==null)clearTimeout(press.timer);torrentLongPress=null;
}
function rowPointerDown(e){
  if(e.pointerType!=='touch'||e.isPrimary===false||e.button!==0)return;
  const tr=e.target.closest('tr');if(!tr||e.target.closest('input,button,a,select,textarea'))return;
  clearTorrentLongPress();
  const press={pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,tr,timer:null};
  press.timer=setTimeout(()=>{
    if(torrentLongPress!==press)return;
    torrentLongPress=null;torrentLongPressSuppressClickUntil=Date.now()+800;
    openTorrentMenuAtPoint(press.tr,press.startX,press.startY);
  },TORRENT_LONG_PRESS_MS);
  torrentLongPress=press;
}
function rowPointerMove(e){
  const press=torrentLongPress;if(!press||press.pointerId!==e.pointerId)return;
  if(Math.hypot(e.clientX-press.startX,e.clientY-press.startY)>TORRENT_LONG_PRESS_MOVE_PX)clearTorrentLongPress(e.pointerId);
}
function rowPointerEnd(e){clearTorrentLongPress(e.pointerId)}
function rowContext(e){const tr=e.target.closest('tr');if(!tr)return;e.preventDefault();clearTorrentLongPress();torrentLongPressSuppressClickUntil=Date.now()+250;openTorrentMenuAtPoint(tr,e.clientX,e.clientY)}"""
    replace_once(path, old_context, new_context, "context menu and long press handlers")

    replace_once(
        path,
        "$('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);bindTorrentColumnHeaderUI();",
        "$('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);$('#torrentRows').addEventListener('pointerdown',rowPointerDown);$('#torrentRows').addEventListener('pointermove',rowPointerMove);$('#torrentRows').addEventListener('pointerup',rowPointerEnd);$('#torrentRows').addEventListener('pointercancel',rowPointerEnd);bindTorrentColumnHeaderUI();",
        "torrent row input bindings",
    )
    replace_once(
        path,
        "if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')&&!e.target.closest('.more-row'))",
        "if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn'))",
        "menu outside-click rule",
    )

    text = path.read_text(encoding="utf-8")
    for obsolete in ('class=\\"row-actions\\"', 'class=\\"more-row\\"', ".more-row"):
        if obsolete in text:
            raise RuntimeError(f"Obsolete torrent Actions button code remains: {obsolete}")


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    replacements = [
        ('.row-actions{display:flex;justify-content:flex-end}.row-actions button{border:0;background:transparent;padding:5px 8px}', '', 'base row actions styling'),
        ('.row-actions{position:absolute;right:7px;bottom:5px}.row-actions button{font-size:15px}', '', 'mobile row actions styling'),
        ('.row-actions button{min-width:36px;min-height:36px}', '', 'large desktop row actions sizing'),
        ('#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important;white-space:nowrap;box-sizing:border-box;box-shadow:-1px 0 0 color-mix(in srgb,var(--border) 78%,transparent)}\n#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden;cursor:default!important;padding-left:0;padding-right:0}\n#torrentTable td.row-actions{display:table-cell!important;position:sticky;right:0;z-index:3;text-align:right;background:var(--panel);padding-left:5px;padding-right:5px;overflow:hidden}\n#torrentTable tbody tr:hover td.row-actions{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}\n#torrentTable td.row-actions .more-row{max-width:38px}\n', '', 'fixed actions rail styling'),
        ('@media(max-width:820px){#torrentTable{table-layout:auto}#torrentTable th.check,#torrentTable td.check{position:static;left:auto;box-shadow:none}#torrentTable td.row-actions{display:block!important;position:absolute;right:7px;bottom:5px;width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;box-shadow:none;background:transparent;padding:5px 0}#torrentTable tbody tr:hover td.row-actions{background:transparent}}', '@media(max-width:820px){#torrentTable{table-layout:auto}#torrentTable th.check,#torrentTable td.check{position:static;left:auto;box-shadow:none}}', 'fixed mobile actions rail reset'),
    ]
    for old, new, label in replacements:
        replace_once(path, old, new, label)
    text = path.read_text(encoding="utf-8")
    marker = "\n.controls-panel .filters{margin-left:auto}"
    if text.count(marker) != 1:
        raise RuntimeError("Expected controls filter marker exactly once")
    text = text.replace(marker, "\n\n/* 0.5.102 contextual torrent row actions. */\n@media(max-width:820px){#torrentTable tbody tr{-webkit-touch-callout:none}}" + marker, 1)
    if 'row-actions' in text or 'more-row' in text:
        raise RuntimeError("Obsolete torrent Actions rail styling remains")
    path.write_text(text, encoding="utf-8")


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- The visible data-column order is **Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags**. The selection checkbox remains a fixed 40 px left rail and row Actions remains a fixed 48 px right rail.\n- Desktop/tablet widths are deterministic proportions of the available data area after the two fixed rails are reserved: Name 29%, Size 5%, Status 7%, Progress 20%, Seeds 4.5%, Peers 4.5%, Down 4.5%, Up 4.5%, ETA 3.5%, Ratio 4.5%, Category 6.5%, Tags 6.5%.",
        "- The visible data-column order is **Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags**. The selection checkbox remains the only fixed 40 px table rail; torrent commands are contextual rather than occupying a permanent Actions column.\n- Desktop/tablet widths are deterministic proportions of the available data area after the fixed selection rail is reserved: Name 29%, Size 5%, Status 7%, Progress 20%, Seeds 4.5%, Peers 4.5%, Down 4.5%, Up 4.5%, ETA 3.5%, Ratio 4.5%, Category 6.5%, Tags 6.5%.",
        "fixed column rail design guidance",
    )
    text = design.read_text(encoding="utf-8")
    needle = "- Mobile keeps the existing card presentation; the fixed desktop width calculation is cleared at the mobile breakpoint.\n"
    addition = "- Torrent row commands use one shared context menu: right-click opens it on pointer-based desktop interfaces, while a deliberate long press opens it on touch. Touch movement cancels the pending long press so normal vertical scrolling is not intercepted.\n"
    if text.count(needle) != 1:
        raise RuntimeError("Expected mobile fixed-column guidance exactly once")
    design.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "- On desktop/tablet, verify the visible data columns appear exactly in this order: Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags. Selection must remain on the far left and Actions on the far right.",
        "- On desktop/tablet, verify the visible data columns appear exactly in this order: Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags. Selection must remain on the far left and there must be no dedicated Actions column.",
        "fixed column manual test",
    )
    replace_once(
        testing,
        "- Resize the browser through several desktop/tablet widths above the mobile breakpoint. The table must continue fitting its torrent viewport without a horizontal scrollbar, and the Actions rail must remain at the far right.",
        "- Resize the browser through several desktop/tablet widths above the mobile breakpoint. The table must continue fitting its torrent viewport without a horizontal scrollbar; the reclaimed former Actions width should remain available to the fixed data columns.",
        "fixed width manual test",
    )
    replace_once(
        testing,
        "- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing or row Actions placement.",
        "- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing. Long-press a non-control area of a torrent card for roughly half a second and verify the same torrent context menu opens; move/scroll before the threshold and verify no menu opens. A normal tap must still open Torrent details, while the tap following a completed long press must not.",
        "mobile long-press manual test",
    )
    text = testing.read_text(encoding="utf-8")
    needle = "- Verify there are no resize cursors/handles, drag-reorder gestures, Columns context menu, Reset columns action, Tracker/Added visible columns, or other column-visibility controls.\n"
    addition = "- Right-click several torrent rows and verify the shared torrent context menu opens at the pointer location with the same actions previously exposed through the ellipsis button.\n"
    if text.count(needle) != 1:
        raise RuntimeError("Expected fixed-column controls test exactly once")
    testing.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    new_block = r'''    # 0.5.102 keeps the v0.5.101 fixed column set but removes the redundant
    # Actions rail. Torrent commands are contextual: right-click on pointer
    # interfaces and a movement-cancellable long press on touch interfaces.
    fixed_header = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="state">Status</th><th data-col="progress">Progress</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th></tr></thead>'
    assert fixed_header in html
    assert 'id="columnMenu"' not in html and 'row-spacer-head' not in html and 'row-actions-head' not in html
    assert "const FIXED_TORRENT_COLUMN_ORDER=['name','size','state','progress','seeds','peers','down','up','eta','ratio','category','tags'];" in app_js
    assert "const FIXED_TORRENT_COLUMN_RATIOS={name:.29,size:.05,state:.07,progress:.20,seeds:.045,peers:.045,down:.045,up:.045,eta:.035,ratio:.045,category:.065,tags:.065};" in app_js
    assert 'const TORRENT_FIXED_COLUMN_WIDTH=40;' in app_js
    assert "for(const key of ['tdCategory','tdTag','tdTracker','tdColumns'])localStorage.removeItem(key)" in app_js
    assert 'function applyFixedTorrentColumnLayout()' in app_js
    assert "wrap.clientWidth-TORRENT_FIXED_COLUMN_WIDTH" in app_js and "table.style.tableLayout='fixed'" in app_js
    assert "window.matchMedia?.('(max-width:820px)').matches" in app_js and "table.style.tableLayout=''" in app_js
    assert "function bindTorrentColumnHeaderUI()" in app_js and "th.title='Click to sort.'" in app_js
    assert "heading.className='torrent-sort-heading'" in app_js and "heading.draggable" not in app_js
    assert "head.addEventListener('click'" in app_js and "head.addEventListener('keydown'" in app_js
    for obsolete in ('torrentColumnPreferences','torrentColumnResize','column-resize-handle','reorderTorrentColumns','renderTorrentColumnMenu','showTorrentColumnMenu','row-spacer','applyTorrentColumnWidths','syncTorrentTableWidth','torrentRightmostColumnResizeMaxWidth','draggedTorrentColumn'):
        assert obsolete not in app_js
    assert 'function normalizedTorrentSort' in app_js and 'function torrentSortValue' in app_js and 'function setTorrentSort' in app_js
    assert "if(!FIXED_TORRENT_COLUMN_ORDER.includes(key))return" in app_js
    assert "sortIcon.innerHTML=materialIconSvg('expand_more')" in app_js and "th.setAttribute('aria-sort'" in app_js
    assert "${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}" in app_js
    assert 'const TORRENT_LONG_PRESS_MS=550,TORRENT_LONG_PRESS_MOVE_PX=12;' in app_js
    assert "e.pointerType!=='touch'" in app_js and 'Math.hypot(e.clientX-press.startX,e.clientY-press.startY)' in app_js
    assert 'torrentLongPressSuppressClickUntil=Date.now()+800' in app_js
    assert "addEventListener('contextmenu',rowContext)" in app_js
    assert "addEventListener('pointerdown',rowPointerDown)" in app_js and "addEventListener('pointermove',rowPointerMove)" in app_js
    assert "addEventListener('pointerup',rowPointerEnd)" in app_js and "addEventListener('pointercancel',rowPointerEnd)" in app_js
    assert 'row-actions' not in html and 'more-row' not in html and 'row-actions' not in app_js and 'more-row' not in app_js
    assert '0.5.101 fixed torrent table layout' in app_css and '0.5.102 contextual torrent row actions' in app_css
    assert '.column-resize-handle' not in app_css and '.column-menu' not in app_css and '.column-dragging' not in app_css
    assert '#torrentTable{width:100%;min-width:0;table-layout:fixed}' in app_css
    assert '#torrentTable td[data-col="name"] .torrent-name{max-width:100%;min-width:0;width:100%' in app_css
    assert 'width:40px!important;min-width:40px!important;max-width:40px!important;inline-size:40px!important' in app_css
    assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' not in app_css
    assert 'row-actions' not in app_css and 'more-row' not in app_css
    assert '-webkit-touch-callout:none' in app_css
    assert '@media(min-width:821px){.torrent-list-region .table-wrap{width:100%;max-inline-size:100%;overflow-x:hidden' in app_css
    design = (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    testing = (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert '## Fixed torrent columns' in design
    assert 'Name 29%, Size 5%, Status 7%, Progress 20%' in design
    assert 'must not introduce a horizontal scrollbar' in design
    assert 'torrent commands are contextual rather than occupying a permanent Actions column' in design
    assert 'a deliberate long press opens it on touch' in design
    assert '### Fixed torrent columns' in testing
    assert 'there are no resize cursors/handles' in testing
    assert 'without a horizontal scrollbar' in testing
    assert 'there must be no dedicated Actions column' in testing
    assert 'Long-press a non-control area of a torrent card' in testing
'''
    regex_once(
        path,
        r"    # 0\.5\.101 temporarily standardizes the torrent table.*?(?=    print\(\"UI string audit passed\"\))",
        new_block,
        "v0.5.102 torrent interaction validator",
    )


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.get("releases", [])
    if any(str(item.get("version")) == TARGET_VERSION for item in releases):
        raise RuntimeError(f"Release metadata already contains v{TARGET_VERSION}")
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS_VERSION), None)
    if not previous:
        raise RuntimeError(f"Could not find v{PREVIOUS_VERSION} release metadata")
    release = copy.deepcopy(previous)
    release.update({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Contextual torrent row actions",
        "summary": "Removes the redundant torrent Actions ellipsis column and keeps one shared command menu available through desktop right-click and a scroll-safe mobile long press.",
        "highlights": [
            "Removes the permanent 48 px Actions rail and ellipsis button so the fixed torrent data columns can use the reclaimed width.",
            "Keeps the existing torrent context menu as the single row-command surface and opens it at the pointer location on desktop right-click.",
            "Adds a 550 ms touch long press for mobile cards; movement beyond a small threshold cancels the gesture so ordinary scrolling remains natural.",
            "Suppresses the synthetic tap after a completed long press so opening the menu does not also open Torrent details."
        ],
        "fixes": [
            "Removes a duplicate command affordance now that row right-click already exposes the same menu.",
            "Provides a touch equivalent for context-menu access without reserving permanent card space for an Actions button."
        ],
        "technical_notes": [
            "The fixed desktop control-width reservation drops from 88 px to 40 px because only the selection checkbox remains a table rail.",
            "Pointerdown starts the touch-only timer, pointermove cancels after 12 px of movement, and pointerup/pointercancel clear any pending long press.",
            "The existing contextmenu handler remains authoritative and prevents the browser-native menu before opening Torrent Dashboard's shared torrent menu."
        ],
        "validation": [
            "The UI audit requires the Actions header/cell/button/CSS to be absent and requires the right-click plus movement-cancellable long-press bindings.",
            "Manual coverage checks desktop right-click, mobile long press, scroll cancellation, synthetic-tap suppression, fixed-width reclamation, and the existing responsive card layout.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "known_issues": [],
    })
    decisions = list(previous.get("decisions", []))
    decisions.append("Keep torrent row commands contextual instead of reserving a permanent Actions column: use right-click on pointer interfaces and a movement-cancellable long press on touch while retaining the shared menu implementation.")
    release["decisions"] = decisions
    releases.append(release)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regenerate_continuity() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    update_versions()
    update_index()
    update_javascript()
    update_css()
    update_docs()
    update_validator()
    update_release_metadata()
    regenerate_continuity()
    print(f"Staged v{TARGET_VERSION} contextual torrent row actions")


if __name__ == "__main__":
    main()
