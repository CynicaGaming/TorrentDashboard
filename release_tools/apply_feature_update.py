#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.86"
NEW = "0.5.87"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected source fragment not found in {path}: {old[:180]!r}")
    write(path, text.replace(old, new, count))


# Build/version synchronization.
replace("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
write("static/index.html", read("static/index.html").replace(OLD, NEW))
replace("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
sw = read("static/sw.js").replace("torrent-dashboard-v0586", "torrent-dashboard-v0587").replace(OLD, NEW)
write("static/sw.js", sw)

# Extend the existing browser-local column preference object with widths.
replace(
    "static/app.js",
    "const DEFAULT_TORRENT_COLUMN_ORDER=TORRENT_COLUMN_DEFS.map(column=>column.key);\nfunction defaultTorrentColumnPreferences(){return{order:[...DEFAULT_TORRENT_COLUMN_ORDER],visible:Object.fromEntries(TORRENT_COLUMN_DEFS.map(column=>[column.key,!!column.defaultVisible]))}}\n",
    "const DEFAULT_TORRENT_COLUMN_ORDER=TORRENT_COLUMN_DEFS.map(column=>column.key);\nconst TORRENT_COLUMN_MIN_WIDTHS={name:220,size:90,progress:180,state:110,seeds:82,peers:82,down:104,up:104,eta:82,ratio:82,category:110,tags:120,tracker:150,added:160};\nconst TORRENT_COLUMN_MAX_WIDTH=720;\nfunction torrentColumnMinWidth(key){return TORRENT_COLUMN_MIN_WIDTHS[key]||82}\nfunction defaultTorrentColumnPreferences(){return{order:[...DEFAULT_TORRENT_COLUMN_ORDER],visible:Object.fromEntries(TORRENT_COLUMN_DEFS.map(column=>[column.key,!!column.defaultVisible])),widths:{}}}\n",
)
replace(
    "static/app.js",
    "  const visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(savedPreviousDefault&&column.key==='category'?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible));\n  return{order,visible};\n",
    "  const visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(savedPreviousDefault&&column.key==='category'?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible));\n  const widths={};for(const [key,value] of Object.entries(raw?.widths||{})){const width=Math.round(Number(value));if(known.has(key)&&Number.isFinite(width)&&width>=torrentColumnMinWidth(key)&&width<=TORRENT_COLUMN_MAX_WIDTH)widths[key]=width}\n  return{order,visible,widths};\n",
)

# Width application is independent of row rendering. New rows created by the
# one-second refresh receive the persisted width immediately after render.
replace(
    "static/app.js",
    "function saveTorrentColumnPreferences(prefs){localStorage.tdColumns=JSON.stringify(prefs)}\nfunction resetTorrentColumns(){saveTorrentColumnPreferences(defaultTorrentColumnPreferences());render()}\n",
    "function saveTorrentColumnPreferences(prefs){localStorage.tdColumns=JSON.stringify(prefs)}\nfunction applyTorrentColumnWidth(key,width=null){const valid=Number.isFinite(Number(width)),value=valid?`${Math.round(Number(width))}px`:'';document.querySelectorAll(`#torrentTable [data-col=\"${key}\"]`).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value})}\nfunction applyTorrentColumnWidths(prefs=torrentColumnPreferences()){for(const column of TORRENT_COLUMN_DEFS)applyTorrentColumnWidth(column.key,prefs.widths?.[column.key])}\nfunction saveTorrentColumnWidth(key,width){const prefs=torrentColumnPreferences(),value=Math.max(torrentColumnMinWidth(key),Math.min(TORRENT_COLUMN_MAX_WIDTH,Math.round(Number(width)||0)));prefs.widths[key]=value;saveTorrentColumnPreferences(prefs);applyTorrentColumnWidth(key,value)}\nfunction resetTorrentColumns(){saveTorrentColumnPreferences(defaultTorrentColumnPreferences());render()}\n",
)
replace(
    "static/app.js",
    "  order.splice(source,1);let insert=order.indexOf(targetKey)+(after?1:0);insert=Math.max(0,Math.min(order.length,insert));order.splice(insert,0,sourceKey);prefs.order=order;saveTorrentColumnPreferences(prefs);applyColumnPrefs();\n}\nlet draggedTorrentColumn='';\n",
    "  order.splice(source,1);let insert=order.indexOf(targetKey)+(after?1:0);insert=Math.max(0,Math.min(order.length,insert));order.splice(insert,0,sourceKey);prefs.order=order;saveTorrentColumnPreferences(prefs);applyColumnPrefs();applyTorrentColumnWidths(prefs);\n}\nlet draggedTorrentColumn='',torrentColumnResize=null;\nfunction startTorrentColumnResize(event,handle){\n  if(event.button!==0)return;const th=handle.closest('th[data-col]');if(!th)return;event.preventDefault();event.stopPropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';\n  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width);torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,pointerId:event.pointerId,handle};\n  handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');\n}\nfunction moveTorrentColumnResize(event){\n  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(torrentColumnMinWidth(resize.key),Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);\n}\nfunction finishTorrentColumnResize(event){\n  const resize=torrentColumnResize;if(!resize||(event?.pointerId!==undefined&&event.pointerId!==resize.pointerId))return;torrentColumnResize=null;document.body.classList.remove('torrent-column-resizing');try{resize.handle.releasePointerCapture?.(resize.pointerId)}catch{}saveTorrentColumnWidth(resize.key,resize.width);\n}\n",
)

# Give each data header a local resize handle and keep resize gestures separate
# from the existing native header drag/drop reorder behavior.
replace(
    "static/app.js",
    "  head.querySelectorAll('th[data-col]').forEach(th=>{th.draggable=true;th.title='Drag to reorder. Right-click to show or hide columns.'});\n  head.addEventListener('contextmenu',event=>{event.preventDefault();showTorrentColumnMenu(event.clientX,event.clientY)});\n  head.addEventListener('dragstart',event=>{const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});\n",
    "  head.querySelectorAll('th[data-col]').forEach(th=>{th.draggable=true;th.title='Drag to reorder. Drag the right edge to resize. Right-click to show or hide columns.';if(!th.querySelector('.column-resize-handle')){const handle=document.createElement('span');handle.className='column-resize-handle';handle.setAttribute('aria-hidden','true');handle.draggable=false;th.appendChild(handle)}});\n  head.addEventListener('contextmenu',event=>{event.preventDefault();showTorrentColumnMenu(event.clientX,event.clientY)});\n  head.addEventListener('pointerdown',event=>{const handle=event.target.closest('.column-resize-handle');if(handle)startTorrentColumnResize(event,handle)});\n  head.addEventListener('pointermove',moveTorrentColumnResize);head.addEventListener('pointerup',finishTorrentColumnResize);head.addEventListener('pointercancel',finishTorrentColumnResize);\n  head.addEventListener('dragstart',event=>{if(event.target.closest('.column-resize-handle')){event.preventDefault();return}const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});\n",
)

# Widths must be re-applied after startup preferences and every live row render.
replace(
    "static/app.js",
    "function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyColumnPrefs()}\n",
    "function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyColumnPrefs();applyTorrentColumnWidths()}\n",
)
replace(
    "static/app.js",
    "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyColumnPrefs();const empty=$('#empty');",
    "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyColumnPrefs();applyTorrentColumnWidths();const empty=$('#empty');",
)

# Resize affordance styling. Header drag/reorder remains the broader hit target;
# the narrow edge handle gets col-resize semantics and visible hover feedback.
app_css = read("static/app.css")
app_css += r'''

/* 0.5.87 resizable torrent columns. */
#torrentTable thead th[data-col]{padding-right:18px}
#torrentTable th[data-col],#torrentTable td[data-col]{box-sizing:border-box}
.column-resize-handle{position:absolute;top:0;right:-4px;z-index:6;width:9px;height:100%;cursor:col-resize;touch-action:none}
.column-resize-handle::after{content:"";position:absolute;top:22%;bottom:22%;right:4px;width:1px;border-radius:1px;background:var(--accent);opacity:0;transition:opacity .12s ease}
#torrentTable thead th[data-col]:hover>.column-resize-handle::after,.column-resize-handle:hover::after,body.torrent-column-resizing .column-resize-handle::after{opacity:.72}
body.torrent-column-resizing,body.torrent-column-resizing *{cursor:col-resize!important;user-select:none!important;-webkit-user-select:none!important}
@media(max-width:820px){.column-resize-handle{display:none!important}}
'''
write("static/app.css", app_css)

# Keep design and manual-testing contracts aligned with the direct table model.
design = read("DESIGN_LANGUAGE.md")
design_section = '''## Configurable torrent columns

The torrent table is a user-configurable local workspace, and column management lives where the columns are used.

- **Name** is required and cannot be hidden. The selection checkbox and row-actions control remain fixed at the outer edges; visible data columns can be reordered directly.
- On desktop/tablet, drag a visible torrent column header horizontally to change its position. The chosen order is persisted immediately and must survive the one-second live refresh and browser reloads.
- Drag the narrow right edge of a visible data header to resize that column. Widths are stored with the same browser-local column layout and must survive live refreshes, visibility changes, reordering, and reloads.
- Column resizing has per-column minimums that preserve legibility and a bounded maximum width. The fixed selection and row-actions columns are not user-resizable.
- Right-click anywhere on the torrent header bar to open the **Columns** menu. Optional columns can be shown or hidden there without opening Settings; **Reset columns** restores the documented default order/visibility and clears custom widths.
- The available column catalog includes Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added.
- Seeds, Peers, Category, and Tags are part of the default visible layout. Size, Tracker, and Added remain available but hidden by default to limit unnecessary width.
- Column layout is a browser-local presentation preference. It must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own visible column, the Name cell should avoid repeating the same value in its secondary summary line.
- Direct manipulation should use clear drag/drop and resize feedback plus a conventional header context menu rather than duplicating the same controls in Settings.
'''
design, changes = re.subn(r'## Configurable torrent columns\n.*\Z', design_section, design, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns design section")
write("DESIGN_LANGUAGE.md", design.rstrip() + "\n")

testing = read("TESTING.md")
testing_section = '''### Configurable torrent columns

- On a browser with no saved column preference, verify Seeds, Peers, Category, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.
- Verify Settings → General does not contain a duplicate torrent-column organizer.
- Drag several visible column headers left and right and verify the table follows the new order immediately, after the next one-second refresh, and after a full browser reload.
- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Verify each stops at a readable minimum, remains stable during the one-second refresh, and persists after reload.
- Hide a resized optional column from the Columns menu, show it again, and verify its saved width returns.
- Verify resizing a header does not accidentally start header reordering and reordering does not discard a saved width.
- Right-click the torrent header bar and verify the Columns menu lists every data column, keeps Name required, and can show/hide every optional column.
- Hide and restore several columns from the header menu and verify the table updates immediately without changing qBitTorrent state.
- Use Reset columns from the header menu and verify the default order/visibility is restored, Category remains visible, and custom widths are cleared.
- Verify Size, Tracker, and Added can be enabled; Seeds displays connected seeds with the total in parentheses when qBitTorrent supplies a total, and Peers follows the same convention.
- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize handles.
- Verify a browser with an existing customized v0.5.84-v0.5.86 layout keeps its custom order and visibility; missing width data should simply use automatic sizing until the user resizes a column.
'''
testing, changes = re.subn(r'### Configurable torrent columns\n.*\Z', testing_section, testing, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns testing section")
write("TESTING.md", testing.rstrip() + "\n")

# Extend the UI audit to make column-width persistence and the resize gesture a
# release-gated interaction rather than incidental CSS.
validator = read("release_tools/validate_ui_strings.py")
validator_block = '''    # 0.5.84-v0.5.87 keeps torrent columns browser-local and directly
    # configurable from the header; v0.5.87 adds persisted edge resizing.
    assert 'id="columnPrefList"' not in html and 'id="resetColumns"' not in html
    assert 'class="menu column-menu hidden" id="columnMenu"' in html and 'aria-label="Torrent columns"' in html
    assert html.count('draggable="true" data-col=') == 14
    assert "{key:'seeds',label:'Seeds',defaultVisible:true}" in app_js
    assert "{key:'peers',label:'Peers',defaultVisible:true}" in app_js
    assert "{key:'category',label:'Category',defaultVisible:true}" in app_js
    assert "{key:'tags',label:'Tags',defaultVisible:true}" in app_js
    assert "{key:'size',label:'Size',defaultVisible:false}" in app_js
    assert "savedPreviousDefault&&column.key==='category'?true" in app_js
    assert 'widths:{}' in app_js and 'TORRENT_COLUMN_MIN_WIDTHS' in app_js and 'TORRENT_COLUMN_MAX_WIDTH=720' in app_js
    assert 'function torrentColumnPreferences()' in app_js and 'function saveTorrentColumnPreferences(prefs)' in app_js
    assert 'function applyTorrentColumnWidths' in app_js and 'function saveTorrentColumnWidth' in app_js
    assert 'function bindTorrentColumnHeaderUI()' in app_js and "head.addEventListener('contextmenu'" in app_js
    assert "head.addEventListener('dragstart'" in app_js and "head.addEventListener('dragover'" in app_js and "head.addEventListener('drop'" in app_js
    assert "head.addEventListener('pointerdown'" in app_js and "head.addEventListener('pointermove'" in app_js and "head.addEventListener('pointerup'" in app_js
    assert 'function startTorrentColumnResize' in app_js and 'function finishTorrentColumnResize' in app_js
    assert "handle.className='column-resize-handle'" in app_js and "event.target.closest('.column-resize-handle')" in app_js
    assert 'function reorderTorrentColumns(sourceKey,targetKey,after=false)' in app_js
    assert 'function renderTorrentColumnMenu()' in app_js and 'function showTorrentColumnMenu(x,y)' in app_js
    assert "materialIconSvg('check')" in app_js
    assert "row.querySelector('.row-actions-head,.row-actions')" in app_js and 'applyColumnPrefs();applyTorrentColumnWidths();const empty=' in app_js
    assert 'data-col="seeds" data-label="Seeds"' in app_js and 'data-col="peers" data-label="Peers"' in app_js and 'data-col="tags" data-label="Tags"' in app_js
    assert 'swarmColumnValue(t.num_seeds,t.num_complete)' in app_js and 'swarmColumnValue(t.num_leechs,t.num_incomplete)' in app_js
    assert 'renderTorrentColumnPreferences' not in app_js and 'saveTorrentColumnPreferencesFromSettings' not in app_js
    assert "document.querySelector('#columnPrefList')" not in settings_js and 'saveTorrentColumnPreferencesFromSettings' not in settings_js
    assert '.torrent-column-hidden{display:none!important}' in app_css
    assert '0.5.86 direct torrent-column manipulation' in app_css and '0.5.87 resizable torrent columns' in app_css
    assert '.column-resize-handle{' in app_css and 'body.torrent-column-resizing' in app_css
    assert '0.5.84 torrent column organizer' not in settings_css
    assert '## Configurable torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'Drag the narrow right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Configurable torrent columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
validator, changes = re.subn(
    r'    # 0\.5\.84-v0\.5\.86 keeps torrent columns locally configurable; v0\.5\.86\n.*?(?=\n    print\("UI string audit passed"\))',
    validator_block.rstrip(),
    validator,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not replace v0.5.86 column validator block")
write("release_tools/validate_ui_strings.py", validator)

# Release metadata and continuity state.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")
decisions = list(previous.get("decisions") or [])
decisions.append("Treat torrent column width as part of the browser-local table layout: resize from the header edge, preserve widths across refresh/reorder/visibility changes, and clear them with Reset columns.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Resizable torrent columns",
    "summary": "Adds direct, persistent column-width resizing to the torrent table while preserving the existing drag-to-reorder and right-click visibility workflow.",
    "highlights": [
        "Drag the right edge of any torrent data header to resize that column directly on the Dashboard.",
        "Custom widths persist locally through one-second refreshes, browser reloads, column reordering, and hide/show changes.",
        "Per-column minimum widths preserve readable Name, Progress, Status, transfer, category, tag, tracker, and date content.",
        "Reset columns now restores default order/visibility and clears all custom widths."
    ],
    "fixes": [
        "Keeps resizing separate from native header drag/drop so grabbing the resize edge does not accidentally reorder a column.",
        "Existing v0.5.84-v0.5.86 column preferences migrate without intervention; layouts without width data retain automatic sizing until resized."
    ],
    "technical": [
        "The existing tdColumns browser preference now carries an optional widths map alongside order and visibility.",
        "Header resize handles use pointer capture and apply widths to matching header/body data-col cells, including rows recreated by live polling.",
        "Selection and row-action columns remain fixed and are intentionally excluded from the resize contract."
    ],
    "validation": [
        "The UI audit requires persisted width state, per-column minimums, resize handles, pointer-event bindings, refresh-time width application, and dedicated resize CSS.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} resizable torrent columns")
