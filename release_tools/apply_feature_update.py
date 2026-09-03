#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.100"
TARGET_VERSION = "0.5.101"


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
        raise RuntimeError("Expected v0.5.100 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(ROOT / "static" / "app.js", f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v05100" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.100 service-worker references")
    text = text.replace("torrent-dashboard-v05100", "torrent-dashboard-v05101")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_index() -> None:
    path = ROOT / "static" / "index.html"
    old_header = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="progress">Progress</th><th data-col="state">Status</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th><th data-col="tracker">Tracker</th><th data-col="added">Added</th><th class="row-spacer-head" aria-hidden="true"></th><th class="row-actions-head"></th></tr></thead>'
    new_header = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="state">Status</th><th data-col="progress">Progress</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th><th class="row-actions-head"></th></tr></thead>'
    replace_once(path, old_header, new_header, "fixed torrent header")
    replace_once(path, '<div class="menu column-menu hidden" id="columnMenu" role="menu" aria-label="Torrent columns"></div>\n', '', "column menu removal")


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    replace_once(
        path,
        "for(const key of ['tdCategory','tdTag','tdTracker'])localStorage.removeItem(key);",
        "for(const key of ['tdCategory','tdTag','tdTracker','tdColumns'])localStorage.removeItem(key);",
        "legacy torrent table preference cleanup",
    )

    fixed_model = """const FIXED_TORRENT_COLUMN_ORDER=['name','size','state','progress','seeds','peers','down','up','eta','ratio','category','tags'];
const FIXED_TORRENT_COLUMN_RATIOS={name:.29,size:.05,state:.07,progress:.20,seeds:.045,peers:.045,down:.045,up:.045,eta:.035,ratio:.045,category:.065,tags:.065};
const TORRENT_FIXED_COLUMN_WIDTH=88;
const TORRENT_SORT_DEFAULT_DIRECTIONS={name:'asc',size:'desc',progress:'desc',state:'asc',seeds:'desc',peers:'desc',down:'desc',up:'desc',eta:'asc',ratio:'desc',category:'asc',tags:'asc',added:'desc'};"""
    regex_once(
        path,
        r"const TORRENT_COLUMN_DEFS=\[.*?\nconst TORRENT_SORT_DEFAULT_DIRECTIONS=\{.*?\};",
        fixed_model,
        "fixed torrent column model",
    )

    regex_once(
        path,
        r"function normalizedTorrentSort\(value=state\.sort\)\{.*?\n\}",
        """function normalizedTorrentSort(value=state.sort){
  const match=String(value||'').match(/^([a-z]+)_(asc|desc)$/),key=match?.[1],dir=match?.[2];
  return FIXED_TORRENT_COLUMN_ORDER.includes(key)||key==='added'?[key,dir]:['added','desc'];
}""",
        "fixed sort normalization",
    )
    replace_once(
        path,
        "if(!TORRENT_COLUMN_DEFS.some(column=>column.key===key))return;",
        "if(!FIXED_TORRENT_COLUMN_ORDER.includes(key))return;",
        "fixed sort key guard",
    )

    fixed_ui = """function applyFixedTorrentColumnLayout(){
  const table=$('#torrentTable'),wrap=table?.closest('.table-wrap');if(!table||!wrap)return;
  const cellsFor=key=>document.querySelectorAll(`#torrentTable [data-col=\"${key}\"]`);
  if(window.matchMedia?.('(max-width:820px)').matches){
    table.style.width='';table.style.minWidth='';table.style.tableLayout='';
    for(const key of FIXED_TORRENT_COLUMN_ORDER)cellsFor(key).forEach(cell=>{cell.style.width='';cell.style.minWidth='';cell.style.maxWidth=''});
    return;
  }
  const available=Math.max(0,Math.floor(wrap.clientWidth-TORRENT_FIXED_COLUMN_WIDTH));let used=0;
  FIXED_TORRENT_COLUMN_ORDER.forEach((key,index)=>{
    const last=index===FIXED_TORRENT_COLUMN_ORDER.length-1,width=last?Math.max(0,available-used):Math.max(0,Math.floor(available*(FIXED_TORRENT_COLUMN_RATIOS[key]||0)));
    used+=width;const value=`${width}px`;cellsFor(key).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value});
  });
  table.style.width='100%';table.style.minWidth='0';table.style.tableLayout='fixed';
}
function bindTorrentColumnHeaderUI(){
  const head=$('#torrentTable thead');if(!head||head.dataset.columnUiBound==='1')return;head.dataset.columnUiBound='1';
  const [sortKey,sortDir]=normalizedTorrentSort();state.sort=`${sortKey}_${sortDir}`;localStorage.tdSort=state.sort;
  head.querySelectorAll('th[data-col]').forEach(th=>{
    th.tabIndex=0;th.title='Click to sort.';
    const label=th.textContent.trim();th.textContent='';
    const heading=document.createElement('span');heading.className='torrent-sort-heading';
    const copy=document.createElement('span');copy.className='torrent-sort-label';copy.textContent=label;
    const sortIcon=document.createElement('span');sortIcon.className='torrent-sort-icon';sortIcon.setAttribute('aria-hidden','true');sortIcon.innerHTML=materialIconSvg('expand_more');
    heading.append(copy,sortIcon);th.appendChild(heading);
  });
  syncTorrentSortHeaders();
  head.addEventListener('click',event=>{const th=event.target.closest('th[data-col]');if(th)setTorrentSort(th.dataset.col)});
  head.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;const th=event.target.closest('th[data-col]');if(!th)return;event.preventDefault();setTorrentSort(th.dataset.col)});
}
"""
    regex_once(
        path,
        r"function saveTorrentColumnPreferences\(prefs\).*?\n\}\n\nfunction esc",
        fixed_ui + "\nfunction esc",
        "fixed torrent header UI",
    )

    replace_once(
        path,
        "function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyColumnPrefs();applyTorrentColumnWidths()}",
        "function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyFixedTorrentColumnLayout()}",
        "fixed layout preferences",
    )
    replace_once(
        path,
        "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();syncTorrentTableWidth()}));",
        "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout()}));",
        "fixed layout resize sync",
    )
    regex_once(
        path,
        r"function torrentSubtitle\(t,prefs=torrentColumnPreferences\(\)\)\{.*?\}",
        "function torrentSubtitle(t){const parts=[];if(t._server_name)parts.push(t._server_name);return parts.join(' · ')}",
        "fixed torrent subtitle",
    )
    regex_once(
        path,
        r"function render\(\)\{if\(torrentColumnResize\).*?\}\nfunction rowHtml",
        """function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyFixedTorrentColumnLayout();syncTorrentSortHeaders();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));syncTorrentWorkspaceLayout()}
function rowHtml""",
        "fixed torrent render",
    )
    regex_once(
        path,
        r"function rowHtml\(t\)\{.*?\}\nfunction rowChange",
        """function rowHtml(t){const pct=Math.max(0,Math.min(100,Number(t.progress||0)*100)),[label,cls]=stateInfo(t),sub=torrentSubtitle(t),tags=String(t.tags||'').trim();return`<tr class=\"${state.detail&&state.detail.server===(t._server_id||state.server)&&state.detail.hash===t.hash?'torrent-detail-selected':''}\" data-key=\"${esc(keyFor(t))}\" data-hash=\"${esc(t.hash)}\" data-server=\"${esc(t._server_id||state.server)}\"><td class=\"check\"><input class=\"rowcheck\" type=\"checkbox\" ${state.selected.has(keyFor(t))?'checked':''}></td><td data-col=\"name\"><div class=\"torrent-name\" title=\"${esc(t.name)}\">${esc(t.name)}</div><div class=\"torrent-sub${sub?'':' hidden'}\">${esc(sub)}</div></td><td class=\"mobile-grid\" data-col=\"size\" data-label=\"Size\"><span class=\"mono\">${bytes(t.size)}</span></td><td class=\"mobile-grid\" data-col=\"state\" data-label=\"Status\"><span class=\"state ${cls}\">${esc(uiText(label))}</span></td><td class=\"progress-cell\" data-col=\"progress\"><div class=\"progress-top\"><span>${pct.toFixed(1)}%</span><span>${bytes(t.amount_left)} Left</span></div><div class=\"track\"><div class=\"fill\" style=\"width:${pct}%\"></div></div></td><td class=\"mobile-grid\" data-col=\"seeds\" data-label=\"Seeds\"><span class=\"mono\">${esc(swarmColumnValue(t.num_seeds,t.num_complete))}</span></td><td class=\"mobile-grid\" data-col=\"peers\" data-label=\"Peers\"><span class=\"mono\">${esc(swarmColumnValue(t.num_leechs,t.num_incomplete))}</span></td><td class=\"mobile-grid\" data-col=\"down\" data-label=\"Download\"><span class=\"mono\">${speed(t.dlspeed||0)}</span></td><td class=\"mobile-grid\" data-col=\"up\" data-label=\"Upload\"><span class=\"mono\">${speed(t.upspeed||0)}</span></td><td class=\"mobile-grid\" data-col=\"eta\" data-label=\"ETA\"><span class=\"mono\">${eta(t.eta)}</span></td><td class=\"mobile-grid\" data-col=\"ratio\" data-label=\"Ratio\"><span class=\"mono\">${Number(t.ratio||0).toFixed(2)}</span></td><td class=\"mobile-grid\" data-col=\"category\" data-label=\"Category\"><span class=\"torrent-column-text\" title=\"${esc(t.category||'')}\">${esc(t.category||'—')}</span></td><td class=\"mobile-grid\" data-col=\"tags\" data-label=\"Tags\"><span class=\"torrent-column-text\" title=\"${esc(tags)}\">${esc(tags||'—')}</span></td><td class=\"row-actions\"><button class=\"more-row\" aria-label=\"Actions\">•••</button></td></tr>`}
function rowChange""",
        "fixed torrent row order",
    )
    regex_once(path, r"\nfunction applyColumnPrefs\(\)\{.*?\}\n\nfunction hideAccountMenu", "\nfunction hideAccountMenu", "obsolete column preference application")
    replace_once(
        path,
        "if(!$('#columnMenu')?.classList.contains('hidden')){$('#columnMenu').classList.add('hidden');return}",
        "",
        "column menu escape handling",
    )

    text = path.read_text(encoding="utf-8")
    forbidden = (
        'torrentColumnPreferences', 'torrentColumnResize', 'column-resize-handle', 'reorderTorrentColumns',
        'renderTorrentColumnMenu', 'showTorrentColumnMenu', 'row-spacer', 'columnMenu', 'applyTorrentColumnWidths',
        'syncTorrentTableWidth', 'torrentRightmostColumnResizeMaxWidth', 'draggedTorrentColumn',
    )
    leaked = [token for token in forbidden if token in text]
    if leaked:
        raise RuntimeError("Obsolete configurable torrent-column code remains: " + ", ".join(leaked))


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    new_block = """/* 0.5.101 fixed torrent table layout. */
.torrent-column-hidden{display:none!important}
#torrentTable{width:100%;min-width:0;table-layout:fixed}
#torrentTable th[data-col],#torrentTable td[data-col]{box-sizing:border-box;min-width:0;overflow:hidden}
#torrentTable thead th[data-col]{cursor:pointer;user-select:none;-webkit-user-select:none;text-align:left;padding-left:12px;padding-right:26px;outline:none}
#torrentTable [data-col=\"size\"],#torrentTable [data-col=\"seeds\"],#torrentTable [data-col=\"peers\"],#torrentTable [data-col=\"down\"],#torrentTable [data-col=\"up\"],#torrentTable [data-col=\"eta\"],#torrentTable [data-col=\"ratio\"]{text-align:right;white-space:nowrap}
.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px;cursor:pointer;pointer-events:auto}
#torrentTable thead th[data-col=\"size\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"seeds\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"peers\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"down\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"up\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"eta\"] .torrent-sort-heading,#torrentTable thead th[data-col=\"ratio\"] .torrent-sort-heading{justify-content:flex-end;padding-left:18px;padding-right:0}
#torrentTable thead th[data-col=\"size\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"seeds\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"peers\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"down\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"up\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"eta\"] .torrent-sort-icon,#torrentTable thead th[data-col=\"ratio\"] .torrent-sort-icon{left:0;right:auto}
.torrent-sort-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.torrent-sort-icon{position:absolute;right:0;display:grid;place-items:center;width:14px;height:14px;color:var(--muted);opacity:0;transition:opacity .12s ease,color .12s ease;pointer-events:none}
.torrent-sort-icon .material-symbol-icon{width:14px;height:14px;transition:transform .14s ease}
#torrentTable thead th[data-col]:hover .torrent-sort-icon,#torrentTable thead th[data-col]:focus-visible .torrent-sort-icon{opacity:.32}
#torrentTable thead th.torrent-sort-active .torrent-sort-icon{opacity:1;color:var(--accent)}
#torrentTable thead th[aria-sort=\"ascending\"] .torrent-sort-icon .material-symbol-icon{transform:rotate(180deg)}
#torrentTable thead th[data-col]:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 60%,transparent)}
#torrentTable td[data-col=\"name\"] .torrent-name{max-width:100%;min-width:0;width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#torrentTable .torrent-column-text{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#torrentTable .progress-cell .track{min-width:0}
#torrentTable th.check,#torrentTable td.check{width:40px!important;min-width:40px!important;max-width:40px!important;inline-size:40px!important;position:sticky;left:0;box-sizing:border-box;box-shadow:1px 0 0 color-mix(in srgb,var(--border) 78%,transparent)}
#torrentTable th.check{z-index:9;background:var(--panel3)}
#torrentTable td.check{z-index:4;background:var(--panel)}
#torrentTable tbody tr:hover td.check{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}
#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important;white-space:nowrap;box-sizing:border-box;box-shadow:-1px 0 0 color-mix(in srgb,var(--border) 78%,transparent)}
#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden;cursor:default!important;padding-left:0;padding-right:0}
#torrentTable td.row-actions{display:table-cell!important;position:sticky;right:0;z-index:3;text-align:right;background:var(--panel);padding-left:5px;padding-right:5px;overflow:hidden}
#torrentTable tbody tr:hover td.row-actions{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}
#torrentTable td.row-actions .more-row{max-width:38px}
.torrent-list-panel,.torrent-list-region,.torrent-list-region .table-wrap{min-width:0;max-width:100%}
@media(min-width:821px){.torrent-list-region .table-wrap{width:100%;max-inline-size:100%;overflow-x:hidden;overflow-y:auto;contain:inline-size}#torrentTable{min-width:0!important}}
@media(max-width:820px){#torrentTable{table-layout:auto}#torrentTable th.check,#torrentTable td.check{position:static;left:auto;box-shadow:none}#torrentTable td.row-actions{display:block!important;position:absolute;right:7px;bottom:5px;width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;box-shadow:none;background:transparent;padding:5px 0}#torrentTable tbody tr:hover td.row-actions{background:transparent}}

"""
    regex_once(
        path,
        r"/\* 0\.5\.84 configurable torrent table columns\. \*/.*?(?=\.controls-panel \.filters\{margin-left:auto\})",
        new_block,
        "fixed torrent table CSS",
    )


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    section = """## Fixed torrent columns

For the current desktop/tablet interaction model, the torrent list uses one fixed visible column set rather than exposing per-browser column customization. This deliberately trades configurability for predictable geometry while the table interaction layer is simplified.

- The visible data-column order is **Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags**. The selection checkbox remains a fixed 40 px left rail and row Actions remains a fixed 48 px right rail.
- Desktop/tablet widths are deterministic proportions of the available data area after the two fixed rails are reserved: Name 29%, Size 5%, Status 7%, Progress 20%, Seeds 4.5%, Peers 4.5%, Down 4.5%, Up 4.5%, ETA 3.5%, Ratio 4.5%, Category 6.5%, Tags 6.5%.
- Those proportions are recalculated from the live torrent viewport when the window changes size. The desktop table remains exactly viewport-width, so this fixed layout must not introduce a horizontal scrollbar.
- Header labels follow their body alignment. Size, Seeds, Peers, Down, Up, ETA, and Ratio are right-aligned; other data columns are left-aligned. Header clicks and keyboard activation continue to sort, with the active direction shown by the locally embedded chevron.
- Column resize handles, drag reorder, header visibility menus, Reset columns, spacer geometry, and browser-local `tdColumns` width/order/visibility persistence are intentionally inactive in this fixed-layout phase. Existing `tdColumns` state is discarded during migration so an old customized layout cannot leak into the fixed table.
- Name and other text cells use only their assigned cell width for ellipsis. There is no historical independent Name maximum-width cap.
- Mobile keeps the existing card presentation; the fixed desktop width calculation is cleared at the mobile breakpoint.
- Sorting remains browser-local in `tdSort`. The default may still be Added descending even though Added is not one of the visible fixed columns.
"""
    regex_once(design, r"## Configurable torrent columns\n.*\Z", section, "fixed torrent design section")

    testing = ROOT / "TESTING.md"
    matrix = """### Fixed torrent columns

- On desktop/tablet, verify the visible data columns appear exactly in this order: Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags. Selection must remain on the far left and Actions on the far right.
- Verify there are no resize cursors/handles, drag-reorder gestures, Columns context menu, Reset columns action, Tracker/Added visible columns, or other column-visibility controls.
- Seed browser-local `tdColumns` with an old customized order/visibility/width payload before loading and verify it is discarded and cannot affect the rendered table.
- Resize the browser through several desktop/tablet widths above the mobile breakpoint. The table must continue fitting its torrent viewport without a horizontal scrollbar, and the Actions rail must remain at the far right.
- Verify the fixed desktop width proportions keep Name and Progress visually dominant while Size, Seeds, Peers, Down, Up, ETA, and Ratio remain compact; Category and Tags should retain enough room to be recognizable before ellipsis.
- Verify header labels match body alignment: compact numeric columns are right-aligned and the remaining columns are left-aligned. The sort chevron must not shift the visible column boundary.
- Click and keyboard-activate every visible data header and verify sorting still works and `aria-sort` follows the active direction.
- Verify an unresized Name cell reveals as much text as its assigned fixed share permits and ellipsizes only when that actual cell width is insufficient.
- Hold the dashboard open across several one-second polling intervals and browser resizes; row content and fixed widths must remain stable without column jumps.
- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing or row Actions placement.
"""
    regex_once(testing, r"### Configurable torrent columns\n.*\Z", matrix, "fixed torrent testing section")


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    block = """    # 0.5.101 temporarily standardizes the torrent table on one fixed
    # desktop column set and deterministic proportional sizing while retaining sorting.
    fixed_header = '<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="state">Status</th><th data-col="progress">Progress</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th><th class="row-actions-head"></th></tr></thead>'
    assert fixed_header in html
    assert 'id="columnMenu"' not in html and 'row-spacer-head' not in html
    assert "const FIXED_TORRENT_COLUMN_ORDER=['name','size','state','progress','seeds','peers','down','up','eta','ratio','category','tags'];" in app_js
    assert "const FIXED_TORRENT_COLUMN_RATIOS={name:.29,size:.05,state:.07,progress:.20,seeds:.045,peers:.045,down:.045,up:.045,eta:.035,ratio:.045,category:.065,tags:.065};" in app_js
    assert 'const TORRENT_FIXED_COLUMN_WIDTH=88;' in app_js
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
    assert '0.5.101 fixed torrent table layout' in app_css
    assert '.column-resize-handle' not in app_css and '.column-menu' not in app_css and '.column-dragging' not in app_css
    assert '#torrentTable{width:100%;min-width:0;table-layout:fixed}' in app_css
    assert '#torrentTable td[data-col="name"] .torrent-name{max-width:100%;min-width:0;width:100%' in app_css
    assert 'width:40px!important;min-width:40px!important;max-width:40px!important;inline-size:40px!important' in app_css
    assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css
    assert '@media(min-width:821px){.torrent-list-region .table-wrap{width:100%;max-inline-size:100%;overflow-x:hidden' in app_css
    assert '## Fixed torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'Name 29%, Size 5%, Status 7%, Progress 20%' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'must not introduce a horizontal scrollbar' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Fixed torrent columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'there are no resize cursors/handles' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'without a horizontal scrollbar' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
"""
    regex_once(path, r"    # 0\.5\.94 consolidates direct torrent-column interaction.*?(?=    print\(\"UI string audit passed\"\))", block, "fixed torrent validator contract")


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
    decisions.append("Temporarily prefer one fixed torrent-table column set and deterministic proportional sizing over resize/reorder/visibility customization while the interaction model is simplified.")
    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Fixed torrent table layout",
        "summary": "Replaces the iterative configurable-column geometry with the requested fixed torrent column set, fixed order, and deterministic viewport-fitting proportions while retaining header sorting and the mobile card layout.",
        "highlights": [
            "Uses the fixed visible order Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags, with selection/actions remaining the only fixed rails.",
            "Allocates the desktop data plane proportionally on every viewport resize so the table fits the available width without a horizontal scrollbar.",
            "Removes active resize, drag reorder, visibility menu, Reset columns, spacer geometry, and tdColumns persistence; old tdColumns state is discarded during migration.",
            "Retains sortable headers, content-aligned labels, real-width Name ellipsis, one-second polling stability, and the existing responsive card presentation."
        ],
        "fixes": [
            "Eliminates the resize/overflow tradeoff by removing user-resizable desktop column geometry for this phase.",
            "Keeps the Actions surface at the far right without requiring sticky-overflow compensation or rightmost resize exceptions."
        ],
        "technical_notes": [
            "Desktop widths are computed from table-wrap.clientWidth minus the fixed 88 px control rails and assigned in deterministic ratios that sum to 100% of the remaining data plane.",
            "The last Tags column receives the integer rounding remainder so assigned widths plus fixed rails exactly match the available desktop viewport.",
            "At 820 px and below, inline desktop widths/table-layout are cleared so the established mobile card CSS owns presentation."
        ],
        "validation": [
            "The UI audit requires the exact fixed column order/ratios and rejects the former resize/reorder/menu/persistence machinery.",
            "Manual coverage checks no desktop horizontal scrollbar across viewport resizing, fixed header/body alignment, sorting, old tdColumns migration, and mobile card recovery.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "decisions": decisions,
    })
    data["releases"] = releases
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    update_versions()
    update_index()
    update_javascript()
    update_css()
    update_docs()
    update_validator()
    update_release_metadata()
    print(f"Staged v{TARGET_VERSION} fixed torrent table layout")


if __name__ == "__main__":
    main()
