#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.93"
NEW = "0.5.94"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


# Version/build synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if html.count(f'draggable="true" data-col=') != 14:
    raise RuntimeError("Expected 14 legacy draggable torrent headers")
html = html.replace('draggable="true" data-col=', 'data-col=')
html = html.replace(OLD, NEW)
write("static/index.html", html)

sw = read("static/sw.js").replace("torrent-dashboard-v0593", "torrent-dashboard-v0594").replace(OLD, NEW)
write("static/sw.js", sw)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")

# Use ergonomic minima for normal resizing, but accept the actually rendered
# width as the current gesture floor when auto-layout produced something
# narrower. This removes the resize dead zone/jump without allowing a new drag
# to collapse a normally sized column into an unusable sliver.
old_widths = "const TORRENT_COLUMN_MIN_WIDTHS={name:140,size:90,progress:180,state:110,seeds:82,peers:82,down:104,up:104,eta:82,ratio:82,category:110,tags:120,tracker:150,added:160};\nconst TORRENT_COLUMN_MAX_WIDTH=720;"
new_widths = "const TORRENT_COLUMN_MIN_WIDTHS={name:96,size:72,progress:130,state:82,seeds:64,peers:64,down:88,up:88,eta:64,ratio:64,category:82,tags:90,tracker:120,added:128};\nconst TORRENT_COLUMN_HARD_MIN=48;\nconst TORRENT_COLUMN_MAX_WIDTH=720;"
app_js = replace_once(app_js, old_widths, new_widths, "torrent column width limits")
app_js = replace_once(
    app_js,
    "if(known.has(key)&&Number.isFinite(width)&&width>=torrentColumnMinWidth(key)&&width<=TORRENT_COLUMN_MAX_WIDTH)widths[key]=width",
    "if(known.has(key)&&Number.isFinite(width)&&width>=TORRENT_COLUMN_HARD_MIN&&width<=TORRENT_COLUMN_MAX_WIDTH)widths[key]=width",
    "persisted width validation",
)
app_js = replace_once(
    app_js,
    "function saveTorrentColumnWidth(key,width){const prefs=torrentColumnPreferences(),value=Math.max(torrentColumnMinWidth(key),Math.min(TORRENT_COLUMN_MAX_WIDTH,Math.round(Number(width)||0)));prefs.widths[key]=value;saveTorrentColumnPreferences(prefs);applyTorrentColumnWidth(key,value)}",
    "function saveTorrentColumnWidth(key,width){const prefs=torrentColumnPreferences(),value=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(TORRENT_COLUMN_MAX_WIDTH,Math.round(Number(width)||0)));prefs.widths[key]=value;saveTorrentColumnPreferences(prefs);applyTorrentColumnWidth(key,value)}",
    "width persistence clamp",
)

resize_block = r'''let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;
function startTorrentColumnResize(event,handle){
  if(event.button!==0||torrentColumnResize)return;const th=handle?.closest('th[data-col]');if(!th)return;
  event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();clearTorrentColumnDropHints();draggedTorrentColumn='';torrentColumnRenderPending=false;
  const key=th.dataset.col||'',startWidth=Math.round(th.getBoundingClientRect().width),minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth));
  th.classList.add('column-resizing');torrentColumnResize={key,startX:event.clientX,startWidth,width:startWidth,minWidth,pointerId:event.pointerId,handle,th};
  applyTorrentColumnWidth(key,startWidth);handle.setPointerCapture?.(event.pointerId);document.body.classList.add('torrent-column-resizing');
}
function moveTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||event.pointerId!==resize.pointerId)return;event.preventDefault();const width=Math.max(resize.minWidth,Math.min(TORRENT_COLUMN_MAX_WIDTH,resize.startWidth+(event.clientX-resize.startX)));resize.width=Math.round(width);applyTorrentColumnWidth(resize.key,resize.width);
}
function finishTorrentColumnResize(event){
  const resize=torrentColumnResize;if(!resize||(event?.pointerId!==undefined&&event.pointerId!==resize.pointerId))return;
  const renderPending=torrentColumnRenderPending;torrentColumnResize=null;torrentColumnClickSuppressedUntil=performance.now()+250;document.body.classList.remove('torrent-column-resizing');resize.th?.classList.remove('column-resizing');
  try{resize.handle.releasePointerCapture?.(resize.pointerId)}catch{}saveTorrentColumnWidth(resize.key,resize.width);
  if(renderPending){torrentColumnRenderPending=false;render()}
}
'''
app_js, changes = re.subn(
    r"let draggedTorrentColumn='',torrentColumnResize=null,torrentColumnRenderPending=false,torrentColumnClickSuppressedUntil=0;\nfunction startTorrentColumnResize\(event,handle\)\{.*?(?=function clearTorrentColumnDropHints\(\))",
    resize_block,
    app_js,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not replace torrent resize state/functions")

bind_block = r'''function bindTorrentColumnHeaderUI(){
  const head=$('#torrentTable thead');if(!head||head.dataset.columnUiBound==='1')return;head.dataset.columnUiBound='1';
  const [sortKey,sortDir]=normalizedTorrentSort();state.sort=`${sortKey}_${sortDir}`;localStorage.tdSort=state.sort;
  head.querySelectorAll('th[data-col]').forEach(th=>{
    th.draggable=false;th.tabIndex=0;th.title='Click to sort. Drag the label to reorder. Drag the right edge to resize. Right-click to show or hide columns.';
    const label=th.textContent.trim();th.textContent='';
    const heading=document.createElement('span');heading.className='torrent-sort-heading';heading.draggable=true;heading.dataset.columnDrag='1';
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
    if(event.button!==0)return;const handle=event.target.closest('.column-resize-handle');if(handle)startTorrentColumnResize(event,handle);
  },true);
  head.addEventListener('pointermove',moveTorrentColumnResize);head.addEventListener('pointerup',finishTorrentColumnResize);head.addEventListener('pointercancel',finishTorrentColumnResize);
  head.addEventListener('dragstart',event=>{
    if(torrentColumnResize){event.preventDefault();return}const heading=event.target.closest('.torrent-sort-heading');if(!heading){event.preventDefault();return}const th=heading.closest('th[data-col]');if(!th)return;
    draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'));
  });
  head.addEventListener('dragover',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th||th.dataset.col===draggedTorrentColumn)return;event.preventDefault();clearTorrentColumnDropHints();const after=event.clientX>th.getBoundingClientRect().left+th.getBoundingClientRect().width/2;th.classList.add(after?'column-drop-after':'column-drop-before');event.dataTransfer.dropEffect='move'});
  head.addEventListener('drop',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th)return;event.preventDefault();const rect=th.getBoundingClientRect(),after=event.clientX>rect.left+rect.width/2;reorderTorrentColumns(draggedTorrentColumn,th.dataset.col,after);torrentColumnClickSuppressedUntil=performance.now()+250;clearTorrentColumnDropHints()});
  head.addEventListener('dragend',event=>{event.target.closest('th[data-col]')?.classList.remove('column-dragging');draggedTorrentColumn='';torrentColumnClickSuppressedUntil=performance.now()+250;clearTorrentColumnDropHints()});
}
'''
app_js, changes = re.subn(
    r"function bindTorrentColumnHeaderUI\(\)\{.*?\n\}\n\n(?=function esc\()",
    bind_block + "\n",
    app_js,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not replace torrent header binding")
write("static/app.js", app_js)

# Consolidate the accumulated 0.5.86-0.5.93 header overrides into one current
# interaction contract. This removes contradictory alignment/hit-target rules.
app_css = read("static/app.css")
column_css = r'''

/* 0.5.94 deterministic torrent-column header interactions. */
#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:center;padding-left:28px;padding-right:28px;outline:none}
#torrentTable thead th[data-col="seeds"],#torrentTable thead th[data-col="peers"]{text-align:center}
.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:center;cursor:grab;pointer-events:auto}
.torrent-sort-heading:active{cursor:grabbing}
.torrent-sort-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.torrent-sort-icon{position:absolute;right:0;display:grid;place-items:center;width:14px;height:14px;color:var(--muted);opacity:0;transition:opacity .12s ease,color .12s ease;pointer-events:none}
.torrent-sort-icon .material-symbol-icon{width:14px;height:14px;transition:transform .14s ease}
#torrentTable thead th[data-col]:hover .torrent-sort-icon,#torrentTable thead th[data-col]:focus-visible .torrent-sort-icon{opacity:.32}
#torrentTable thead th.torrent-sort-active .torrent-sort-icon{opacity:1;color:var(--accent)}
#torrentTable thead th[aria-sort="ascending"] .torrent-sort-icon .material-symbol-icon{transform:rotate(180deg)}
#torrentTable thead th[data-col]:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 60%,transparent)}
#torrentTable thead th.column-dragging{opacity:.46}
#torrentTable thead th.column-drop-before{box-shadow:inset 3px 0 0 var(--accent)}
#torrentTable thead th.column-drop-after{box-shadow:inset -3px 0 0 var(--accent)}
#torrentTable th[data-col],#torrentTable td[data-col]{box-sizing:border-box}
.column-resize-handle{position:absolute;top:0;right:0;z-index:8;width:24px;height:100%;cursor:col-resize;touch-action:none}
.column-resize-handle::after{content:"";position:absolute;top:20%;bottom:20%;right:0;width:1px;border-radius:1px;background:var(--accent);opacity:0;transition:opacity .12s ease}
#torrentTable thead th[data-col]:hover>.column-resize-handle::after,.column-resize-handle:hover::after,body.torrent-column-resizing .column-resize-handle::after{opacity:.78}
#torrentTable thead th.column-resizing{cursor:col-resize}
body.torrent-column-resizing,body.torrent-column-resizing *{cursor:col-resize!important;user-select:none!important;-webkit-user-select:none!important}
#torrentTable td[data-col="name"] .torrent-name{max-width:none;min-width:0;width:auto}
#torrentTable td.torrent-column-sized[data-col="name"] .torrent-name{max-width:none;width:100%}
#torrentTable td.torrent-column-sized .torrent-column-text{max-width:none}
#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important;white-space:nowrap;box-sizing:border-box}
#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden;cursor:default!important;padding-left:0;padding-right:0}
#torrentTable td.row-actions{display:table-cell!important;position:sticky;right:0;z-index:3;text-align:right;background:var(--panel);padding-left:5px;padding-right:5px;overflow:hidden}
#torrentTable tbody tr:hover td.row-actions{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}
#torrentTable td.row-actions .more-row{max-width:38px}
.torrent-list-panel,.torrent-list-region,.torrent-list-region .table-wrap{min-width:0;max-width:100%}
.torrent-list-region .table-wrap{overflow:auto;contain:inline-size;overscroll-behavior-x:contain}
.column-menu{min-width:224px;max-height:min(72vh,540px);overflow:auto;padding:6px}
.column-menu .menu-caption{padding:7px 9px 8px;color:var(--muted);font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}
.column-menu-item{display:grid!important;grid-template-columns:22px minmax(0,1fr) auto;align-items:center;gap:8px;min-height:34px;padding:7px 9px!important;color:var(--text)!important}
.column-menu-item .column-menu-check{display:grid;place-items:center;width:18px;height:18px;color:var(--accent)}
.column-menu-item .column-menu-check .material-symbol-icon{width:17px;height:17px}
.column-menu-item small{color:var(--muted);font-size:8.5px}
.column-menu-item:disabled{opacity:.68;cursor:default}
.column-menu-reset{margin-top:2px;color:var(--muted)!important}
.column-menu-reset:hover{color:var(--text)!important}
.controls-panel .filters{margin-left:auto}
.controls-panel .filters input{width:min(360px,36vw)}
@media(max-width:820px){.column-resize-handle{display:none!important}}
@media(max-width:700px){.controls-panel .filters{width:100%;margin-left:0}.controls-panel .filters input{width:100%}}
'''
app_css, changes = re.subn(
    r'\n\n/\* 0\.5\.86 direct torrent-column manipulation\. \*/.*\Z',
    column_css,
    app_css,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not consolidate torrent column CSS")
write("static/app.css", app_css.rstrip() + "\n")

# Current design/testing contract.
design = read("DESIGN_LANGUAGE.md")
design_section = '''## Configurable torrent columns

The torrent table is a user-configurable local workspace, and column management lives where the columns are used.

- **Name** is visible by default but is otherwise a normal configurable data column. The selection checkbox and row-actions control are the only fixed outer-edge columns.
- On desktop/tablet, drag the centered header-label area horizontally to reorder a visible data column. The label drag surface is separate from the resize gutter so native reordering cannot begin from the resize target.
- Drag the right-edge gutter of a visible data header to resize it. The gutter is a forgiving 24 px target that stays entirely inside its owning data header, while the visible divider remains on the true column boundary.
- Resize starts from the exact width currently rendered on screen. If automatic table layout rendered a column narrower than its normal ergonomic minimum, that existing width becomes the floor for that gesture rather than creating a pointer dead zone or jump. A 48 px hard safety floor protects persisted state.
- During an active resize, defer torrent-row DOM rendering until the gesture ends so one-second live polling cannot move the target. Completing a resize or reorder must not accidentally trigger sorting.
- Torrent names and other text columns should consume the width actually assigned to their cell. Name has no historical fixed max-width; ellipsis is an overflow treatment used only when the final rendered cell is genuinely narrower than its content.
- Torrent data header labels are centered with symmetric padding. The resize gutter occupies reserved edge padding and the sort chevron sits inside the centered label area, so neither affordance changes where the visible column boundary feels located.
- Right-click anywhere on the torrent header bar to open the **Columns** menu. Every data column, including Name, can be shown or hidden there; **Reset columns** restores the documented default order/visibility and clears custom widths.
- Click a data-column header to sort by that field. Clicking the active sort header toggles ascending/descending; the active direction is shown with the local Material-style chevron and exposed through `aria-sort`.
- The far-right row-actions column is a fixed 48 px sticky control surface. It has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior, and horizontal table overflow remains contained by the torrent viewport.
- The sort choice is a browser-local preference and remains compatible with existing `tdSort` values from the retired sort dropdown.
- The available column catalog includes Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added. Seeds, Peers, Category, and Tags are part of the default visible layout.
- The Dashboard keeps the status tabs (All, Downloading, Completed, Paused) plus one text search. Search matches torrent name, category, tags, and tracker; separate Category/Tags/Tracker dropdown filters are intentionally omitted because they duplicate searchable metadata.
- Retired metadata-filter preferences must be cleared during migration so an old hidden Category/Tag/Tracker selection can never continue filtering the table after its control is removed.
- Column order, visibility, width, and sort are browser-local presentation preferences. They must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own visible column, the Name cell should avoid repeating the same value in its secondary summary line.
'''
design, changes = re.subn(r'## Configurable torrent columns\n.*\Z', design_section, design, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent-column design section")
write("DESIGN_LANGUAGE.md", design.rstrip() + "\n")

testing = read("TESTING.md")
testing_section = '''### Configurable torrent columns

- On a browser with no saved column preference, verify Seeds, Peers, Category, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.
- Verify Settings → General does not contain a duplicate torrent-column organizer.
- Verify the Dashboard filter row contains only the torrent search box; Category, Tags, Tracker, and standalone Sort selects must not be present.
- Seed old `tdCategory`, `tdTag`, and `tdTracker` local-storage values before loading and verify they are cleared and cannot silently filter the torrent list.
- Search for text that appears only in a torrent category, tag, or tracker hostname and verify the matching torrent is found.
- Click Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added headers and verify each can sort the table.
- Verify all data-header labels are visually centered between their column boundaries. The sort chevron must not shift the label toward the resize divider.
- Use Enter and Space on a focused data header and verify keyboard sorting matches pointer sorting.
- Drag several header labels left and right and verify the table follows the new order immediately, after the next one-second refresh, and after a full browser reload. Reordering must not also change the sort field/direction.
- Verify dragging from the right-edge resize gutter can never start a column reorder. Conversely, begin a reorder from the header-label area and verify it cannot become a resize gesture.
- Drag the right edge of Name, Progress, Status, Category, and Tags by only a few pixels in both directions. Width must begin changing immediately with the pointer; there must be no dead travel before movement and no initial jump.
- Hold at least one resize gesture open for several seconds across multiple live refresh intervals; verify there is no snap, row rebuild, accidental reorder, or accidental sort.
- Test a column whose automatic rendered width is smaller than its configured ergonomic minimum and verify resizing still begins from the visible width instead of waiting for the pointer to cross the nominal minimum.
- Hide a resized data column from the Columns menu, show it again, and verify its saved width returns. Verify the Columns menu includes every data column, including Name, and can show/hide all data columns.
- Use Reset columns from the header menu and verify default order/visibility returns, Category remains visible, and custom widths are cleared. The current sort preference may remain independent of the layout reset.
- Verify an unresized Name column no longer truncates because of the historical fixed max-width. Resize Name narrower than its content and verify ellipsis appears only once the rendered Name cell actually cannot fit the text; widening it must reveal more of the name immediately.
- Horizontally scroll a wide customized table and verify the far-right actions column remains fixed at exactly 48 px. It must never show a resize cursor/handle, change width, or create page-level horizontal overflow.
- Verify Size, Tracker, and Added can be enabled; Seeds displays connected seeds with the total in parentheses when qBitTorrent supplies a total, and Peers follows the same convention.
- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize, reorder, hide, or sort behavior.
- Verify a browser with an existing customized column layout keeps its saved order, visibility, and widths; persisted widths down to the hard safety floor remain valid after reload.
'''
testing, changes = re.subn(r'### Configurable torrent columns\n.*\Z', testing_section, testing, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent-column test section")
write("TESTING.md", testing.rstrip() + "\n")

# Replace the layered historical torrent-column implementation assertions with
# one current contract. Historical release notes remain intact; validation
# should enforce today's behavior, not contradictory intermediate CSS shapes.
validator = read("release_tools/validate_ui_strings.py")
current_contract = r'''    # 0.5.94 consolidates direct torrent-column interaction around distinct
    # sort/reorder and resize surfaces with immediate, polling-stable resizing.
    assert 'id="columnPrefList"' not in html and 'id="resetColumns"' not in html
    assert 'class="menu column-menu hidden" id="columnMenu"' in html and 'aria-label="Torrent columns"' in html
    assert html.count('draggable="true" data-col=') == 0
    assert html.count('data-col=') >= 14 and '<th class="row-actions-head"></th>' in html and 'data-col="actions"' not in html
    assert "{key:'name',label:'Name',required:false,defaultVisible:true}" in app_js
    assert "{key:'seeds',label:'Seeds',defaultVisible:true}" in app_js
    assert "{key:'peers',label:'Peers',defaultVisible:true}" in app_js
    assert "{key:'category',label:'Category',defaultVisible:true}" in app_js
    assert "{key:'tags',label:'Tags',defaultVisible:true}" in app_js
    assert 'const TORRENT_COLUMN_HARD_MIN=48' in app_js and 'const TORRENT_COLUMN_MAX_WIDTH=720' in app_js
    assert 'const TORRENT_COLUMN_MIN_WIDTHS={name:96,size:72,progress:130' in app_js
    assert 'width>=TORRENT_COLUMN_HARD_MIN' in app_js
    assert 'function torrentColumnPreferences()' in app_js and 'function saveTorrentColumnPreferences(prefs)' in app_js
    assert 'function applyTorrentColumnWidths' in app_js and 'function saveTorrentColumnWidth' in app_js
    assert "const liveWidth=torrentColumnResize?.key===column.key?torrentColumnResize.width:null" in app_js
    assert "function render(){if(torrentColumnResize){torrentColumnRenderPending=true;return}" in app_js
    assert "minWidth=Math.max(TORRENT_COLUMN_HARD_MIN,Math.min(torrentColumnMinWidth(key),startWidth))" in app_js
    assert 'applyTorrentColumnWidth(key,startWidth)' in app_js and 'Math.max(resize.minWidth' in app_js
    assert 'event.stopImmediatePropagation()' in app_js
    assert "const handle=event.target.closest('.column-resize-handle');if(handle)startTorrentColumnResize(event,handle)" in app_js
    assert 'nearResizeEdge' not in app_js
    assert "th.draggable=false" in app_js and "heading.draggable=true" in app_js and "heading.dataset.columnDrag='1'" in app_js
    assert "const heading=event.target.closest('.torrent-sort-heading');if(!heading){event.preventDefault();return}" in app_js
    assert "if(torrentColumnResize){event.preventDefault();return}" in app_js
    assert "head.addEventListener('dragstart'" in app_js and "head.addEventListener('dragover'" in app_js and "head.addEventListener('drop'" in app_js
    assert "head.addEventListener('pointerdown'" in app_js and "head.addEventListener('pointermove'" in app_js and "head.addEventListener('pointerup'" in app_js
    assert 'torrentColumnClickSuppressedUntil=performance.now()+250' in app_js
    assert 'function normalizedTorrentSort' in app_js and 'function torrentSortValue' in app_js and 'function setTorrentSort' in app_js
    assert "sortIcon.innerHTML=materialIconSvg('expand_more')" in app_js and "th.setAttribute('aria-sort'" in app_js
    assert "for(const key of ['tdCategory','tdTag','tdTracker'])localStorage.removeItem(key)" in app_js
    assert 'state.category' not in app_js and 'state.tag' not in app_js and 'state.tracker' not in app_js
    assert 'function syncFilterSelect' not in app_js and 'function updateFilters' not in app_js
    assert "${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}" in app_js
    assert '0.5.94 deterministic torrent-column header interactions' in app_css
    for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers'):
        assert stale not in app_css
    assert '#torrentTable thead th[data-col]{cursor:default;user-select:none;-webkit-user-select:none;text-align:center;padding-left:28px;padding-right:28px;outline:none}' in app_css
    assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:center;cursor:grab;pointer-events:auto}' in app_css
    assert '.column-resize-handle{position:absolute;top:0;right:0;z-index:8;width:24px;height:100%;cursor:col-resize;touch-action:none}' in app_css
    assert '#torrentTable td[data-col="name"] .torrent-name{max-width:none;min-width:0;width:auto}' in app_css
    assert '#torrentTable td.torrent-column-sized[data-col="name"] .torrent-name{max-width:none;width:100%}' in app_css
    assert '#torrentTable td.torrent-column-sized .torrent-column-text{max-width:none}' in app_css
    assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css
    assert '#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden;cursor:default!important' in app_css
    assert '.torrent-list-region .table-wrap{overflow:auto;contain:inline-size;overscroll-behavior-x:contain}' in app_css
    assert '## Configurable torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'exact width currently rendered on screen' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'header labels are visually centered' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'no dead travel before movement and no initial jump' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
validator, changes = re.subn(
    r'    # 0\.5\.84-v0\.5\.88 keeps torrent columns browser-local.*?(?=\n    print\("UI string audit passed"\))',
    current_contract.rstrip(),
    validator,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not replace torrent-column validator contract")
write("release_tools/validate_ui_strings.py", validator)

# Release metadata. Preserve useful current decisions but drop the immediately
# superseded v0.5.93 left-alignment decision.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")
decisions = [
    item for item in (previous.get("decisions") or [])
    if not item.startswith("Align sortable torrent header labels with the table's normal content flow")
]
decisions.append("Keep torrent header labels centered, isolate native reordering to the header-label drag surface, reserve a separate inward-only resize gutter, and begin resizing from the exact rendered width so pointer movement maps immediately to column movement.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Deterministic torrent column gestures",
    "summary": "Removes the remaining resize lag and gesture ambiguity by separating reorder and resize hit surfaces, centering headers, starting resize math from the visible width, and consolidating the accumulated column CSS rules.",
    "highlights": [
        "Torrent column headers are centered again with symmetric padding so visual labels line up cleanly with their resize boundaries.",
        "A 24 px inward-only resize gutter owns the divider while only the centered header-label area can initiate native column reordering.",
        "Resizing begins from the exact rendered width, including columns currently narrower than their normal ergonomic minimum, eliminating dead pointer travel and initial jumps.",
        "Torrent names no longer inherit the old fixed display cap; ellipsis remains only when the final Name cell truly cannot fit the text.",
        "The far-right actions column remains a fixed, non-resizable 48 px sticky control surface and horizontal overflow is contained inside the torrent viewport."
    ],
    "fixes": [
        "Fixes resizing that appeared to lag until the pointer moved far enough to cross a configured minimum wider than the rendered column.",
        "Prevents resize gestures from being interpreted as column-reorder drags by removing draggable behavior from the header cell itself.",
        "Removes conflicting 0.5.86-0.5.93 CSS override layers that made the active header alignment and resize target harder to reason about."
    ],
    "technical": [
        "Torrent data headers are no longer HTML draggable elements; only torrent-sort-heading is draggable, while column-resize-handle is a separate sibling target.",
        "The active resize stores a gesture-specific minimum equal to the smaller of the visible starting width and the ergonomic column minimum, bounded by a 48 px hard safety floor.",
        "Starting a resize explicitly pins the target to its measured rendered width before pointer movement, and live torrent rendering remains deferred until pointer release.",
        "Current torrent-column styling is consolidated into one v0.5.94 contract instead of relying on a cascade of historical correction blocks."
    ],
    "validation": [
        "The UI audit requires centered headers, separate reorder/resize surfaces, rendered-width resize initialization, the hard safety floor, fixed actions containment, uncapped Name content, and removal of the superseded CSS layers.",
        "Manual regression coverage requires one-pixel-scale resize movement, below-ergonomic-minimum starting widths, multi-refresh held drags, reorder/resize mutual exclusion, real overflow ellipsis, and fixed action-column behavior.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} deterministic torrent column gestures")
