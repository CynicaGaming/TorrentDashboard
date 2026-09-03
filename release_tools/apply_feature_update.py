#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.91"
NEW = "0.5.92"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


# Synchronize application/frontend build identifiers.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
filters_old = '''<div class="filters">
<input id="search" placeholder="Search torrents…" type="search"/>
<select id="categoryFilter"><option value="">All categories</option></select>
<select id="tagFilter"><option value="">All tags</option></select>
<select id="trackerFilter"><option value="">All trackers</option></select>
<select id="sort"><option value="added_desc">Newest</option><option value="name_asc">Name</option><option value="progress_desc">Progress</option><option value="down_desc">Download speed</option><option value="up_desc">Upload speed</option><option value="eta_asc">ETA</option><option value="size_desc">Size</option><option value="ratio_desc">Ratio</option></select>
</div>'''
filters_new = '''<div class="filters">
<input id="search" placeholder="Search torrents…" type="search"/>
</div>'''
html = replace_once(html, filters_old, filters_new, "torrent filter/sort controls")
html = html.replace(OLD, NEW)
write("static/index.html", html)

sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0591", "torrent-dashboard-v0592").replace(OLD, NEW)
write("static/sw.js", sw)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")

state_old = "const state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:localStorage.tdServer||'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailExpanded:false,detailTab:'general',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};"
state_new = "for(const key of ['tdCategory','tdTag','tdTracker'])localStorage.removeItem(key);\nconst state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:localStorage.tdServer||'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',selected:new Set(),detail:null,detailExpanded:false,detailTab:'general',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};"
app_js = replace_once(app_js, state_old, state_new, "torrent state declaration")

sort_helpers = r'''
const TORRENT_SORT_DEFAULT_DIRECTIONS={name:'asc',size:'desc',progress:'desc',state:'asc',seeds:'desc',peers:'desc',down:'desc',up:'desc',eta:'asc',ratio:'desc',category:'asc',tags:'asc',tracker:'asc',added:'desc'};
function normalizedTorrentSort(value=state.sort){
  const match=String(value||'').match(/^([a-z]+)_(asc|desc)$/),key=match?.[1],dir=match?.[2];
  return TORRENT_COLUMN_DEFS.some(column=>column.key===key)?[key,dir]:['added','desc'];
}
function torrentSortValue(t,key){
  if(key==='name')return String(t.name||'').toLowerCase();
  if(key==='size')return Number(t.size||0);
  if(key==='progress')return Number(t.progress||0);
  if(key==='state')return String(stateInfo(t)[0]||'').toLowerCase();
  if(key==='seeds')return Number(t.num_seeds||0);
  if(key==='peers')return Number(t.num_leechs||0);
  if(key==='down')return Number(t.dlspeed||0);
  if(key==='up')return Number(t.upspeed||0);
  if(key==='eta'){const value=Number(t.eta);return Number.isFinite(value)&&value>=0&&value<8640000?value:9e15}
  if(key==='ratio')return Number(t.ratio||0);
  if(key==='category')return String(t.category||'').toLowerCase();
  if(key==='tags')return String(t.tags||'').toLowerCase();
  if(key==='tracker')return String(trackerHost(t.tracker)||'').toLowerCase();
  if(key==='added')return Number(t.added_on||0);
  return 0;
}
function compareTorrentSortValues(a,b){
  if(typeof a==='string'||typeof b==='string')return String(a).localeCompare(String(b),undefined,{numeric:true,sensitivity:'base'});
  return a<b?-1:a>b?1:0;
}
function syncTorrentSortHeaders(){
  const [key,dir]=normalizedTorrentSort();
  document.querySelectorAll('#torrentTable thead th[data-col]').forEach(th=>{
    const active=th.dataset.col===key;th.classList.toggle('torrent-sort-active',active);
    if(active)th.setAttribute('aria-sort',dir==='asc'?'ascending':'descending');else th.removeAttribute('aria-sort');
  });
}
function setTorrentSort(key){
  if(!TORRENT_COLUMN_DEFS.some(column=>column.key===key))return;
  const [current,dir]=normalizedTorrentSort(),next=current===key?(dir==='asc'?'desc':'asc'):(TORRENT_SORT_DEFAULT_DIRECTIONS[key]||'asc');
  state.sort=`${key}_${next}`;localStorage.tdSort=state.sort;syncTorrentSortHeaders();render();
}
'''
needle = "function torrentColumnVisible(key,prefs=torrentColumnPreferences()){const def=TORRENT_COLUMN_DEFS.find(column=>column.key===key);return !!def?.required||prefs.visible[key]!==false}\n"
if needle not in app_js:
    raise RuntimeError("Could not locate torrentColumnVisible insertion point")
app_js = app_js.replace(needle, needle + sort_helpers, 1)

app_js = replace_once(
    app_js,
    "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false;",
    "let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;",
    "torrent column interaction state",
)
app_js = replace_once(
    app_js,
    "const renderPending=torrentColumnRenderPending;torrentColumnResize=null;document.body.classList.remove('torrent-column-resizing');",
    "const renderPending=torrentColumnRenderPending;torrentColumnResize=null;torrentColumnClickSuppressedUntil=performance.now()+250;document.body.classList.remove('torrent-column-resizing');",
    "resize finish suppression",
)

bind_function = r'''function bindTorrentColumnHeaderUI(){
  const head=$('#torrentTable thead');if(!head||head.dataset.columnUiBound==='1')return;head.dataset.columnUiBound='1';
  const [sortKey,sortDir]=normalizedTorrentSort();state.sort=`${sortKey}_${sortDir}`;localStorage.tdSort=state.sort;
  head.querySelectorAll('th[data-col]').forEach(th=>{
    th.draggable=true;th.tabIndex=0;th.title='Click to sort. Drag to reorder. Drag the right edge to resize. Right-click to show or hide columns.';
    const label=th.textContent.trim();th.textContent='';
    const heading=document.createElement('span');heading.className='torrent-sort-heading';
    const copy=document.createElement('span');copy.className='torrent-sort-label';copy.textContent=label;
    const sortIcon=document.createElement('span');sortIcon.className='torrent-sort-icon';sortIcon.setAttribute('aria-hidden','true');sortIcon.innerHTML=materialIconSvg('expand_more');
    heading.append(copy,sortIcon);th.appendChild(heading);
    const handle=document.createElement('span');handle.className='column-resize-handle';handle.setAttribute('aria-hidden','true');handle.draggable=false;th.appendChild(handle);
  });
  syncTorrentSortHeaders();
  head.addEventListener('contextmenu',event=>{event.preventDefault();showTorrentColumnMenu(event.clientX,event.clientY)});
  head.addEventListener('click',event=>{
    if(performance.now()<torrentColumnClickSuppressedUntil||event.target.closest('.column-resize-handle'))return;
    const th=event.target.closest('th[data-col]');if(th)setTorrentSort(th.dataset.col);
  });
  head.addEventListener('keydown',event=>{
    if(event.key!=='Enter'&&event.key!==' ')return;const th=event.target.closest('th[data-col]');if(!th)return;
    event.preventDefault();setTorrentSort(th.dataset.col);
  });
  head.addEventListener('pointerdown',event=>{
    if(event.button!==0)return;const th=event.target.closest('th[data-col]');if(!th)return;
    const rect=th.getBoundingClientRect(),handle=event.target.closest('.column-resize-handle')||th.querySelector('.column-resize-handle');
    const nearResizeEdge=event.clientX>=rect.right-20&&event.clientX<=rect.right;
    if(handle&&(event.target.closest('.column-resize-handle')||nearResizeEdge))startTorrentColumnResize(event,handle);
  },true);
  head.addEventListener('pointermove',moveTorrentColumnResize);head.addEventListener('pointerup',finishTorrentColumnResize);head.addEventListener('pointercancel',finishTorrentColumnResize);
  head.addEventListener('dragstart',event=>{if(torrentColumnResize||event.target.closest('.column-resize-handle')){event.preventDefault();return}const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});
  head.addEventListener('dragover',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th||th.dataset.col===draggedTorrentColumn)return;event.preventDefault();clearTorrentColumnDropHints();const after=event.clientX>th.getBoundingClientRect().left+th.getBoundingClientRect().width/2;th.classList.add(after?'column-drop-after':'column-drop-before');event.dataTransfer.dropEffect='move'});
  head.addEventListener('drop',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th)return;event.preventDefault();const rect=th.getBoundingClientRect(),after=event.clientX>rect.left+rect.width/2;reorderTorrentColumns(draggedTorrentColumn,th.dataset.col,after);torrentColumnClickSuppressedUntil=performance.now()+250;clearTorrentColumnDropHints()});
  head.addEventListener('dragend',event=>{event.target.closest('th[data-col]')?.classList.remove('column-dragging');draggedTorrentColumn='';torrentColumnClickSuppressedUntil=performance.now()+250;clearTorrentColumnDropHints()});
}'''
app_js, changes = re.subn(r'function bindTorrentColumnHeaderUI\(\)\{.*?\n\}\n\nfunction esc', bind_function + '\n\nfunction esc', app_js, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace bindTorrentColumnHeaderUI")

visible_function = r'''function visibleTorrents(){
  let arr=state.torrents.filter(t=>{
    if(state.filter==='active'&&!isActive(t))return false;
    if(state.filter==='completed'&&!isComplete(t))return false;
    if(state.filter==='paused'&&!isPaused(t))return false;
    if(state.search&&!`${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}`.toLowerCase().includes(state.search))return false;
    return true;
  });
  const [field,dir]=normalizedTorrentSort();
  arr.sort((a,b)=>{
    const result=compareTorrentSortValues(torrentSortValue(a,field),torrentSortValue(b,field));
    if(result)return result*(dir==='desc'?-1:1);
    return String(a.name||'').localeCompare(String(b.name||''),undefined,{numeric:true,sensitivity:'base'});
  });
  return arr;
}'''
app_js, changes = re.subn(r'function visibleTorrents\(\)\{.*?\}\nfunction syncTorrentWorkspaceLayout', visible_function + '\nfunction syncTorrentWorkspaceLayout', app_js, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace visibleTorrents")

empty_function = r'''function emptyStateCopy(){
  if(!state.torrents.length)return state.me?.can_manage?['No torrents yet','Add a torrent to get started.']:['No torrents available','There are no torrents on this server.'];
  if(state.search)return['No torrents match your search','Try a different search.'];
  if(state.filter==='active')return['No active torrents','Nothing is downloading right now.'];
  if(state.filter==='completed')return['No completed torrents','Completed torrents will appear here.'];
  if(state.filter==='paused')return['No paused torrents','Paused torrents will appear here.'];
  return['No torrents in this view','Try another status view.'];
}'''
app_js, changes = re.subn(r'function emptyStateCopy\(\)\{.*?\}\nfunction swarmColumnValue', empty_function + '\nfunction swarmColumnValue', app_js, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace emptyStateCopy")

render_old = "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyColumnPrefs();applyTorrentColumnWidths();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters();syncTorrentWorkspaceLayout()}"
render_new = "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyColumnPrefs();applyTorrentColumnWidths();syncTorrentSortHeaders();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));syncTorrentWorkspaceLayout()}"
app_js = replace_once(app_js, render_old, render_new, "torrent render function")

app_js, changes = re.subn(r'function syncFilterSelect\(.*?\n\}\nfunction updateFilters\(\)\{.*?\n\}\nfunction rowChange', 'function rowChange', app_js, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not remove retired metadata-filter helpers")

bind_old = "  $('#search').value=state.search;$('#search').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();localStorage.tdSearch=state.search;render()});\n  $('#categoryFilter').addEventListener('change',e=>{state.category=e.target.value;localStorage.tdCategory=state.category;render()});\n  $('#tagFilter').addEventListener('change',e=>{state.tag=e.target.value;localStorage.tdTag=state.tag;render()});\n  $('#trackerFilter').addEventListener('change',e=>{state.tracker=e.target.value;localStorage.tdTracker=state.tracker;render()});\n  $('#sort').value=state.sort;$('#sort').addEventListener('change',e=>{state.sort=e.target.value;localStorage.tdSort=state.sort;render()});"
bind_new = "  $('#search').value=state.search;$('#search').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();localStorage.tdSearch=state.search;render()});"
app_js = replace_once(app_js, bind_old, bind_new, "filter/sort event bindings")
write("static/app.js", app_js)

# Add direct sort affordance styles without disturbing the established resize contract.
app_css = read("static/app.css")
app_css += r'''

/* 0.5.92 header sorting and streamlined torrent search. */
.controls-panel .filters{margin-left:auto}
.controls-panel .filters input{width:min(360px,36vw)}
#torrentTable thead th[data-col]{outline:none}
.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:center;pointer-events:none}
.torrent-sort-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.torrent-sort-icon{position:absolute;right:0;display:grid;place-items:center;width:14px;height:14px;color:var(--muted);opacity:0;transition:opacity .12s ease,color .12s ease}
.torrent-sort-icon .material-symbol-icon{width:14px;height:14px;transition:transform .14s ease}
#torrentTable thead th[data-col]:hover .torrent-sort-icon,#torrentTable thead th[data-col]:focus-visible .torrent-sort-icon{opacity:.32}
#torrentTable thead th.torrent-sort-active .torrent-sort-icon{opacity:1;color:var(--accent)}
#torrentTable thead th[aria-sort="ascending"] .torrent-sort-icon .material-symbol-icon{transform:rotate(180deg)}
#torrentTable thead th[data-col]:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 60%,transparent)}
@media(max-width:700px){.controls-panel .filters{width:100%;margin-left:0}.controls-panel .filters input{width:100%}}
'''
write("static/app.css", app_css)

# Update durable design/testing contracts.
design = read("DESIGN_LANGUAGE.md")
design_section = '''## Configurable torrent columns

The torrent table is a user-configurable local workspace, and column management lives where the columns are used.

- **Name** is visible by default but is otherwise a normal configurable data column. The selection checkbox and row-actions control are the only fixed outer-edge columns.
- On desktop/tablet, drag a visible torrent data header horizontally to change its position. Dragging the narrow right edge resizes that column; resizing takes exclusive control of the pointer and live polling must not rebuild rows underneath an active resize.
- Torrent names and other text columns should consume the width actually assigned to their cell. Ellipsis is a real overflow treatment, not a fixed historical width cap.
- Right-click anywhere on the torrent header bar to open the **Columns** menu. Every data column, including Name, can be shown or hidden there; **Reset columns** restores the documented default order/visibility and clears custom widths.
- Click a data-column header to sort by that field. Clicking the active sort header toggles ascending/descending; the active direction is shown with the local Material-style chevron and exposed through `aria-sort`.
- Header sorting, header reordering, and edge resizing are separate gestures. Completing a resize or reorder must not accidentally trigger a sort click.
- The sort choice is a browser-local preference and remains compatible with existing `tdSort` values from the retired sort dropdown.
- The available column catalog includes Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added. Seeds, Peers, Category, and Tags are part of the default visible layout.
- The Dashboard keeps the status tabs (All, Downloading, Completed, Paused) plus one text search. Search matches torrent name, category, tags, and tracker; separate Category/Tags/Tracker dropdown filters are intentionally omitted because they duplicate searchable metadata.
- Retired metadata-filter preferences must be cleared during migration so an old hidden Category/Tag/Tracker selection can never continue filtering the table after its control is removed.
- Column order, visibility, width, and sort are browser-local presentation preferences. They must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own visible column, the Name cell should avoid repeating the same value in its secondary summary line.
'''
design, changes = re.subn(r'## Configurable torrent columns\n.*\Z', design_section, design, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns design section")
write("DESIGN_LANGUAGE.md", design.rstrip() + "\n")

testing = read("TESTING.md")
testing_section = '''### Configurable torrent columns

- On a browser with no saved column preference, verify Seeds, Peers, Category, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.
- Verify Settings → General does not contain a duplicate torrent-column organizer.
- Verify the Dashboard filter row contains only the torrent search box; Category, Tags, Tracker, and standalone Sort selects must not be present.
- Seed old `tdCategory`, `tdTag`, and `tdTracker` local-storage values before loading v0.5.92 and verify they are cleared and cannot silently filter the torrent list.
- Search for text that appears only in a torrent category, tag, or tracker hostname and verify the matching torrent is found.
- Click Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added headers and verify each can sort the table.
- On a newly selected sort column, verify the natural initial direction is used; click the same header again and verify ascending/descending toggles and the chevron/`aria-sort` state changes with it.
- Reload the browser and verify the chosen sort field/direction persists through `tdSort`, including an existing sort preference created by the old dropdown.
- Use Enter and Space on a focused data header and verify keyboard sorting matches pointer sorting.
- Drag several visible column headers left and right and verify the table follows the new order immediately, after the next one-second refresh, and after a full browser reload. Reordering must not also change the sort field/direction.
- Drag the right edge of Name, Progress, Status, Category, and Tags to narrower and wider sizes. Hold at least one resize gesture open for several seconds across multiple live refresh intervals; verify there is no snap, row rebuild, accidental reorder, or accidental sort.
- Verify each header label/sort affordance is visually centered within its column and the 20 px resize gutter remains entirely inside the owning header.
- Hide a resized data column from the Columns menu, show it again, and verify its saved width returns. Every data column, including Name, can be hidden.
- Use Reset columns from the header menu and verify default order/visibility returns, Category remains visible, and custom widths are cleared. The current sort preference may remain independent of the layout reset.
- Verify widening Name reveals additional torrent-name text and ellipsis appears only when the rendered cell is actually narrower than the name.
- Horizontally scroll a wide customized table and verify the far-right actions column remains fixed at 48 px; it must never show resize behavior, change width, or cause page-level horizontal overflow.
- Verify Size, Tracker, and Added can be enabled; Seeds displays connected seeds with the total in parentheses when qBitTorrent supplies a total, and Peers follows the same convention.
- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize, reorder, hide, or sort behavior.
- Verify a browser with an existing customized v0.5.84-v0.5.91 layout keeps its custom order, visibility, and widths; missing width data should simply use automatic sizing until the user resizes a column.
'''
testing, changes = re.subn(r'### Configurable torrent columns\n.*\Z', testing_section, testing, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns testing section")
write("TESTING.md", testing.rstrip() + "\n")

# Bring the UI audit forward and retire assertions for controls that no longer exist.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace("        'All categories','Download speed','HTTP sources','Accent color',\n", "        'Download speed','HTTP sources','Accent color',\n", 1)
validator = validator.replace(
    "    assert 'function syncFilterSelect' in app_js\n    assert 'document.activeElement===select' in app_js\n    assert 'optionsSignature' in app_js\n",
    "    assert 'function syncFilterSelect' not in app_js\n    assert 'document.activeElement===select' not in app_js\n    assert 'optionsSignature' not in app_js\n",
    1,
)
validator = validator.replace(
    "    assert \"['No torrents match these filters','Adjust your search or filters.']\" in app_js\n",
    "    assert \"['No torrents match your search','Try a different search.']\" in app_js\n",
    1,
)
validator_insert = r'''
    # 0.5.92 moves torrent sorting into the configurable headers and retires
    # redundant metadata facet selects now covered by the unified search field.
    for retired_id in ('categoryFilter','tagFilter','trackerFilter','sort'):
        assert f'id="{retired_id}"' not in html
    assert "for(const key of ['tdCategory','tdTag','tdTracker'])localStorage.removeItem(key)" in app_js
    assert 'state.category' not in app_js and 'state.tag' not in app_js and 'state.tracker' not in app_js
    assert 'function syncFilterSelect' not in app_js and 'function updateFilters' not in app_js
    assert "${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}" in app_js
    assert 'const TORRENT_SORT_DEFAULT_DIRECTIONS=' in app_js
    assert 'function normalizedTorrentSort' in app_js and 'function torrentSortValue' in app_js
    assert 'function compareTorrentSortValues' in app_js and 'function setTorrentSort' in app_js
    assert 'function syncTorrentSortHeaders' in app_js and "th.setAttribute('aria-sort'" in app_js
    assert "sortIcon.innerHTML=materialIconSvg('expand_more')" in app_js
    assert "head.addEventListener('click'" in app_js and "head.addEventListener('keydown'" in app_js
    assert 'torrentColumnClickSuppressedUntil=performance.now()+250' in app_js
    assert 'syncTorrentSortHeaders();const empty=' in app_js
    assert '0.5.92 header sorting and streamlined torrent search' in app_css
    assert '.torrent-sort-heading{' in app_css and '.torrent-sort-icon{' in app_css
    assert 'th[aria-sort="ascending"] .torrent-sort-icon .material-symbol-icon{transform:rotate(180deg)}' in app_css
    assert 'separate Category/Tags/Tracker dropdown filters are intentionally omitted' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'Dashboard filter row contains only the torrent search box' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
marker = '    print("UI string audit passed")\n'
if marker not in validator:
    raise RuntimeError("Could not locate UI audit print marker")
validator = validator.replace(marker, validator_insert + '\n' + marker, 1)
write("release_tools/validate_ui_strings.py", validator)

# Record the release and regenerate public handoff/change history.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")
decisions = list(previous.get("decisions") or [])
decisions.append("Use the torrent header as the single sorting surface and the unified text search as the single metadata filter: preserve status tabs, retire Category/Tags/Tracker and sort selects, clear obsolete facet preferences, and keep sort direction browser-local.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Header sorting and streamlined torrent search",
    "summary": "Moves torrent sorting directly into the configurable column headers and removes redundant Category, Tags, Tracker, and standalone sort controls while keeping search across all torrent metadata.",
    "highlights": [
        "Click any configurable torrent data header to sort by that field; click the active header again to toggle ascending and descending.",
        "The active sort direction is shown by a local Material-style chevron and exposed through accessible aria-sort state.",
        "Category, Tags, Tracker, and the standalone Sort dropdown are removed from the Dashboard controls; the search box continues to match all four metadata sources plus torrent names.",
        "Existing tdSort preferences remain compatible, while retired category/tag/tracker local preferences are cleared so hidden filters cannot survive the migration."
    ],
    "fixes": [
        "Removes duplicate metadata-filter controls that no longer add capability beyond the unified search field.",
        "Prevents resize or reorder gestures from producing an accidental header-sort click when the pointer is released.",
        "Makes sort state visible at the column where it applies instead of separating sorting into an unrelated dropdown."
    ],
    "technical": [
        "All 14 configurable data columns have normalized sort values and natural initial sort directions; the previous added_desc default and existing tdSort values remain valid.",
        "Header sorting supports pointer and keyboard activation, persists through localStorage, and uses a short post-resize/post-drag click-suppression window to keep gestures independent.",
        "The status tabs remain separate workflow filters, while the search path matches name, category, tags, and tracker text without maintaining separate facet state."
    ],
    "validation": [
        "The UI audit rejects the retired filter/sort controls and hidden facet state, requires header chevrons, aria-sort synchronization, keyboard sorting, persisted tdSort compatibility, and gesture suppression.",
        "Existing 20 backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} header sorting and filter cleanup")
