#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = "0.5.83", "0.5.84"


def p(name): return ROOT / name
def read(name): return p(name).read_text(encoding="utf-8")
def write(name, text): p(name).write_text(text, encoding="utf-8")
def rep(name, old, new, count=1):
    text=read(name)
    if old not in text: raise RuntimeError(f"Missing fragment in {name}: {old[:100]!r}")
    write(name,text.replace(old,new,count))
def sub(name, pattern, replacement, count=1):
    text=read(name); updated,n=re.subn(pattern,replacement,text,count=count,flags=re.S)
    if n!=count: raise RuntimeError(f"Expected {count} replacement(s) in {name}, got {n}: {pattern}")
    write(name,updated)

# Version and cache generation.
rep("dashboard.py",f'VERSION = "{OLD}"',f'VERSION = "{NEW}"')
write("static/index.html",read("static/index.html").replace(OLD,NEW))
rep("static/app.js",f"const FRONTEND_BUILD='{OLD}';",f"const FRONTEND_BUILD='{NEW}';")
write("static/sw.js",read("static/sw.js").replace("torrent-dashboard-v0583","torrent-dashboard-v0584").replace(OLD,NEW))

# Table structure and Settings surface.
rep("static/index.html",'<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Torrent</th><th data-col="progress">Progress</th><th data-col="state">Status</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th></th></tr></thead>','<thead><tr><th class="check"><input id="selectAll" type="checkbox"/></th><th data-col="name">Name</th><th data-col="size">Size</th><th data-col="progress">Progress</th><th data-col="state">Status</th><th data-col="seeds">Seeds</th><th data-col="peers">Peers</th><th data-col="down">Down</th><th data-col="up">Up</th><th data-col="eta">ETA</th><th data-col="ratio">Ratio</th><th data-col="category">Category</th><th data-col="tags">Tags</th><th data-col="tracker">Tracker</th><th data-col="added">Added</th><th class="row-actions-head"></th></tr></thead>')
rep("static/index.html",'<fieldset class="column-prefs"><legend>Visible desktop columns</legend><label><input checked="" data-column="progress" type="checkbox"/> Progress</label><label><input checked="" data-column="state" type="checkbox"/> Status</label><label><input checked="" data-column="down" type="checkbox"/> Download</label><label><input checked="" data-column="up" type="checkbox"/> Upload</label><label><input checked="" data-column="eta" type="checkbox"/> ETA</label><label><input checked="" data-column="ratio" type="checkbox"/> Ratio</label></fieldset>','<fieldset class="column-prefs"><legend>Torrent columns</legend><p class="column-pref-help">Choose which columns are shown and arrange their order. Name is always shown.</p><div class="column-pref-list" id="columnPrefList"></div><button class="secondary small-btn column-pref-reset" id="resetColumns" type="button">Reset columns</button></fieldset>')

# Material arrows for the organizer.
rep("static/app.js","  expand_more:'M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z',\n};","  expand_more:'M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z',\n  arrow_upward:'M4 12l1.41 1.41L11 7.83V20h2V7.83l5.59 5.58L20 12l-8-8-8 8Z',\n  arrow_downward:'M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.59-5.58L4 12l8 8 8-8Z',\n};")

state_line="const state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:localStorage.tdServer||'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailExpanded:false,detailTab:'general',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};\n"
model=r'''

const TORRENT_COLUMN_DEFS=[
  {key:'name',label:'Name',required:true,defaultVisible:true},{key:'size',label:'Size',defaultVisible:false},{key:'progress',label:'Progress',defaultVisible:true},{key:'state',label:'Status',defaultVisible:true},{key:'seeds',label:'Seeds',defaultVisible:true},{key:'peers',label:'Peers',defaultVisible:true},{key:'down',label:'Download',defaultVisible:true},{key:'up',label:'Upload',defaultVisible:true},{key:'eta',label:'ETA',defaultVisible:true},{key:'ratio',label:'Ratio',defaultVisible:true},{key:'category',label:'Category',defaultVisible:false},{key:'tags',label:'Tags',defaultVisible:true},{key:'tracker',label:'Tracker',defaultVisible:false},{key:'added',label:'Added',defaultVisible:false},
];
const DEFAULT_TORRENT_COLUMN_ORDER=TORRENT_COLUMN_DEFS.map(column=>column.key);
function defaultTorrentColumnPreferences(){return{order:[...DEFAULT_TORRENT_COLUMN_ORDER],visible:Object.fromEntries(TORRENT_COLUMN_DEFS.map(column=>[column.key,!!column.defaultVisible]))}}
function torrentColumnPreferences(){let raw={};try{raw=JSON.parse(localStorage.tdColumns||'{}')||{}}catch{raw={}}const known=new Set(DEFAULT_TORRENT_COLUMN_ORDER),legacy=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{},source=raw?.visible&&typeof raw.visible==='object'?raw.visible:legacy,supplied=Array.isArray(raw?.order)?raw.order.map(String).filter(key=>known.has(key)&&key!=='name'):[],order=['name',...supplied,...DEFAULT_TORRENT_COLUMN_ORDER.filter(key=>key!=='name'&&!supplied.includes(key))],visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible);return{order,visible}}
function torrentColumnVisible(key,prefs=torrentColumnPreferences()){const def=TORRENT_COLUMN_DEFS.find(column=>column.key===key);return !!def?.required||prefs.visible[key]!==false}
function syncColumnPreferenceMoveButtons(){const rows=[...document.querySelectorAll('#columnPrefList [data-column-key]')];rows.forEach((row,index)=>{const required=row.dataset.columnKey==='name',up=row.querySelector('[data-column-move="up"]'),down=row.querySelector('[data-column-move="down"]');if(up)up.disabled=required||index<=1;if(down)down.disabled=required||index===rows.length-1})}
function renderTorrentColumnPreferences(prefs=torrentColumnPreferences()){const list=$('#columnPrefList');if(!list)return;const defs=new Map(TORRENT_COLUMN_DEFS.map(column=>[column.key,column]));list.innerHTML=prefs.order.map(key=>{const column=defs.get(key);if(!column)return'';const checked=torrentColumnVisible(key,prefs),required=!!column.required;return `<div class="column-pref-row${required?' required':''}" data-column-key="${esc(key)}"><label class="column-pref-toggle"><input type="checkbox" data-column="${esc(key)}" ${checked?'checked':''} ${required?'disabled':''}><span>${esc(column.label)}</span>${required?'<small>Always shown</small>':''}</label>${required?'<span class="column-pref-fixed">Fixed</span>':`<span class="column-pref-actions"><button class="column-pref-move" data-column-move="up" type="button" aria-label="Move ${esc(column.label)} up" title="Move up">${materialIconSvg('arrow_upward')}</button><button class="column-pref-move" data-column-move="down" type="button" aria-label="Move ${esc(column.label)} down" title="Move down">${materialIconSvg('arrow_downward')}</button></span>`}</div>`}).join('');syncColumnPreferenceMoveButtons()}
function moveTorrentColumnPreference(key,direction){const list=$('#columnPrefList');if(!list||key==='name')return;const rows=[...list.querySelectorAll('[data-column-key]')],row=rows.find(item=>item.dataset.columnKey===key),index=rows.indexOf(row),delta=direction==='up'?-1:1,target=index+delta;if(!row||target<1||target>=rows.length)return;if(delta<0)list.insertBefore(row,rows[target]);else list.insertBefore(row,rows[target].nextSibling);syncColumnPreferenceMoveButtons()}
function resetTorrentColumnPreferences(){renderTorrentColumnPreferences(defaultTorrentColumnPreferences())}
function saveTorrentColumnPreferencesFromSettings(){const list=$('#columnPrefList');if(!list)return;const order=[...list.querySelectorAll('[data-column-key]')].map(row=>row.dataset.columnKey),visible={};for(const column of TORRENT_COLUMN_DEFS){const input=list.querySelector(`[data-column="${column.key}"]`);visible[column.key]=column.required?true:input?.checked!==false}localStorage.tdColumns=JSON.stringify({order,visible})}
'''
rep("static/app.js",state_line,state_line+model)

# Settings controller uses the ordered local preference schema.
rep("static/settings.js","    document.querySelector('#testNotification')?.addEventListener('click', testNotification);\n","    document.querySelector('#testNotification')?.addEventListener('click', testNotification);\n    document.querySelector('#columnPrefList')?.addEventListener('click', e => { const button=e.target.closest('[data-column-move]'); if(button){ const row=button.closest('[data-column-key]'); moveTorrentColumnPreference(row?.dataset.columnKey||'',button.dataset.columnMove); } });\n    document.querySelector('#resetColumns')?.addEventListener('click', resetTorrentColumnPreferences);\n")
rep("static/settings.js","    let cols = JSON.parse(localStorage.tdColumns || '{}');\n    document.querySelectorAll('[data-column]').forEach(x => x.checked = cols[x.dataset.column] !== false);\n","    renderTorrentColumnPreferences();\n")
rep("static/settings.js","      const cols = {};\n      document.querySelectorAll('[data-column]').forEach(x => cols[x.dataset.column] = x.checked);\n      localStorage.tdColumns = JSON.stringify(cols);\n","      saveTorrentColumnPreferencesFromSettings();\n")

# Table visibility/order is reapplied after every one-second render.
sub("static/app.js",r"function applyColumnPrefs\(\)\{.*?\}\n\nfunction hideAccountMenu",r'''function applyColumnPrefs(){const table=$('#torrentTable');if(!table)return;const prefs=torrentColumnPreferences(),rows=[];if(table.tHead?.rows?.[0])rows.push(table.tHead.rows[0]);rows.push(...table.querySelectorAll('tbody tr'));table.querySelectorAll('[data-col]').forEach(cell=>cell.classList.toggle('torrent-column-hidden',!torrentColumnVisible(cell.dataset.col,prefs)));for(const row of rows){const anchor=row.querySelector('.row-actions-head,.row-actions');if(!anchor)continue;for(const key of prefs.order){const cell=row.querySelector(`[data-col="${key}"]`);if(cell)row.insertBefore(cell,anchor)}}}

function hideAccountMenu''')
sub("static/app.js",r"function render\(\)\{.*?\}\nfunction rowHtml\(t\)\{.*?\}\nfunction syncFilterSelect",r'''function swarmColumnValue(active,total){const connected=Math.max(0,Number(active)||0),available=Number(total);return Number.isFinite(available)&&available>=0?`${connected} (${Math.trunc(available)})`:String(connected)}
function torrentSubtitle(t,prefs=torrentColumnPreferences()){const parts=[];if(t._server_name)parts.push(t._server_name);if(!torrentColumnVisible('size',prefs))parts.push(bytes(t.size));if(!torrentColumnVisible('category',prefs))parts.push(t.category||'Uncategorized');return parts.join(' · ')}
function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');applyColumnPrefs();const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters();syncTorrentWorkspaceLayout()}
function rowHtml(t){const pct=Math.max(0,Math.min(100,Number(t.progress||0)*100)),[label,cls]=stateInfo(t),sub=torrentSubtitle(t),tags=String(t.tags||'').trim(),tracker=trackerHost(t.tracker);return`<tr class="${state.detail&&state.detail.server===(t._server_id||state.server)&&state.detail.hash===t.hash?'torrent-detail-selected':''}" data-key="${esc(keyFor(t))}" data-hash="${esc(t.hash)}" data-server="${esc(t._server_id||state.server)}"><td class="check"><input class="rowcheck" type="checkbox" ${state.selected.has(keyFor(t))?'checked':''}></td><td data-col="name"><div class="torrent-name" title="${esc(t.name)}">${esc(t.name)}</div><div class="torrent-sub${sub?'':' hidden'}">${esc(sub)}</div></td><td class="mobile-grid" data-col="size" data-label="Size"><span class="mono">${bytes(t.size)}</span></td><td class="progress-cell" data-col="progress"><div class="progress-top"><span>${pct.toFixed(1)}%</span><span>${bytes(t.amount_left)} Left</span></div><div class="track"><div class="fill" style="width:${pct}%"></div></div></td><td class="mobile-grid" data-col="state" data-label="Status"><span class="state ${cls}">${esc(uiText(label))}</span></td><td class="mobile-grid" data-col="seeds" data-label="Seeds"><span class="mono">${esc(swarmColumnValue(t.num_seeds,t.num_complete))}</span></td><td class="mobile-grid" data-col="peers" data-label="Peers"><span class="mono">${esc(swarmColumnValue(t.num_leechs,t.num_incomplete))}</span></td><td class="mobile-grid" data-col="down" data-label="Download"><span class="mono">${speed(t.dlspeed||0)}</span></td><td class="mobile-grid" data-col="up" data-label="Upload"><span class="mono">${speed(t.upspeed||0)}</span></td><td class="mobile-grid" data-col="eta" data-label="ETA"><span class="mono">${eta(t.eta)}</span></td><td class="mobile-grid" data-col="ratio" data-label="Ratio"><span class="mono">${Number(t.ratio||0).toFixed(2)}</span></td><td class="mobile-grid" data-col="category" data-label="Category"><span class="torrent-column-text" title="${esc(t.category||'')}">${esc(t.category||'—')}</span></td><td class="mobile-grid" data-col="tags" data-label="Tags"><span class="torrent-column-text" title="${esc(tags)}">${esc(tags||'—')}</span></td><td class="mobile-grid" data-col="tracker" data-label="Tracker"><span class="torrent-column-text" title="${esc(tracker)}">${esc(tracker||'—')}</span></td><td class="mobile-grid" data-col="added" data-label="Added"><span class="torrent-column-text">${esc(when(t.added_on))}</span></td><td class="row-actions"><button class="more-row" aria-label="Actions">•••</button></td></tr>`}
function syncFilterSelect''')

# Styling.
write("static/app.css",read("static/app.css")+r'''

/* 0.5.84 configurable torrent table columns. */
.torrent-column-hidden{display:none!important}
#torrentTable [data-col="seeds"],#torrentTable [data-col="peers"]{white-space:nowrap;text-align:right}
#torrentTable th[data-col="seeds"],#torrentTable th[data-col="peers"]{text-align:right}
.torrent-column-text{display:block;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#torrentTable [data-col="added"] .torrent-column-text{max-width:190px}
@media(max-width:820px){.torrent-column-text{justify-self:end;max-width:min(58vw,260px);text-align:right}.torrent-column-hidden{display:none!important}}
''')
write("static/settings.css",read("static/settings.css")+r'''

/* 0.5.84 torrent column organizer. */
.column-prefs{display:grid;gap:10px;padding:12px;margin:2px 0 14px;border:1px solid var(--border);border-radius:12px;background:color-mix(in srgb,var(--panel3) 44%,transparent)}
.column-prefs legend{padding:0 6px;color:var(--text);font-size:11.5px;font-weight:700}.column-pref-help{margin:0;color:var(--muted);font-size:10.5px;line-height:1.45}.column-pref-list{display:grid;gap:5px}
.column-pref-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:10px;min-height:44px;padding:7px 8px;border:1px solid color-mix(in srgb,var(--border) 72%,transparent);border-radius:10px;background:var(--panel3)}.column-pref-row.required{background:color-mix(in srgb,var(--panel2) 58%,var(--panel3))}
.column-pref-toggle{display:flex!important;align-items:center!important;gap:9px!important;margin:0!important;color:var(--text)!important;min-width:0}.column-pref-toggle input{width:16px!important;height:16px!important;margin:0!important;flex:0 0 auto}.column-pref-toggle span{font-size:11.5px}.column-pref-toggle small{color:var(--muted);font-size:9.5px;margin-left:3px}
.column-pref-actions{display:flex;gap:4px}.column-pref-move{display:grid;place-items:center;width:32px;height:32px;padding:0;border:1px solid transparent;background:transparent;color:var(--muted)}.column-pref-move:hover:not(:disabled){background:var(--panel2);border-color:var(--border);color:var(--text)}.column-pref-move:disabled{opacity:.28;cursor:not-allowed}.column-pref-move .material-symbol-icon{width:17px;height:17px}.column-pref-fixed{padding-right:7px;color:var(--muted);font-size:9.5px}.column-pref-reset{justify-self:start;margin-top:2px}
@media(max-width:560px){.column-pref-row{min-height:48px}.column-pref-toggle small{display:none}.column-pref-move{width:36px;height:36px}.column-pref-reset{width:100%}}
''')

# Documentation.
write("DESIGN_LANGUAGE.md",read("DESIGN_LANGUAGE.md")+r'''

## Configurable torrent columns

The torrent table is a user-configurable local workspace rather than a fixed server-side schema.

- **Name** is the required identity column and remains fixed at the beginning of the torrent data columns. The selection checkbox and row-actions control also remain fixed.
- Other torrent columns may be shown, hidden, and reordered from Settings → General. Reordering is exposed through explicit keyboard-accessible move controls rather than requiring pointer-only drag and drop.
- The available column catalog includes Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added.
- Seeds, Peers, and Tags are part of the default visible layout. Size, Category, Tracker, and Added remain available but hidden by default to avoid unnecessary width.
- Column layout is a browser-local presentation preference. It must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own column, the Name cell should avoid repeating the same value in its secondary summary line.
''')
write("TESTING.md",read("TESTING.md")+r'''

### Configurable torrent columns

- On a browser with no saved column preference, verify Seeds, Peers, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.
- Open Settings → General → Torrent columns and verify Name is always enabled/fixed while every other listed column can be enabled or disabled.
- Move several columns up and down, save Settings, and verify the torrent table follows that order after the next one-second refresh and after a full browser reload.
- Verify hidden columns remain hidden after refresh/reload and Reset columns restores the documented default order/visibility after saving.
- Enable Size, Category, Tracker, and Added individually and verify their values render without changing qBitTorrent state.
- Verify Seeds displays connected seeds with the total in parentheses when qBitTorrent supplies a total; Peers follows the same convention.
- Verify the selection checkbox and row-actions control remain fixed at the outer edges of the table regardless of column order.
''')

# Supersede the older copy contract and add the v0.5.84 UI contract.
validator=read("release_tools/validate_ui_strings.py").replace("'Visible desktop columns','Copy address'","'Torrent columns','Copy address'",1)
marker='    print("UI string audit passed")'
checks=r'''    # 0.5.84 makes torrent data columns locally configurable and reorderable.
    assert 'id="columnPrefList"' in html and 'id="resetColumns"' in html
    assert '<legend>Torrent columns</legend>' in html and '<legend>Visible desktop columns</legend>' not in html
    assert "{key:'seeds',label:'Seeds',defaultVisible:true}" in app_js
    assert "{key:'peers',label:'Peers',defaultVisible:true}" in app_js
    assert "{key:'tags',label:'Tags',defaultVisible:true}" in app_js
    assert "{key:'size',label:'Size',defaultVisible:false}" in app_js
    assert 'function torrentColumnPreferences()' in app_js and 'function renderTorrentColumnPreferences' in app_js
    assert 'function moveTorrentColumnPreference' in app_js and 'function saveTorrentColumnPreferencesFromSettings' in app_js
    assert "row.querySelector('.row-actions-head,.row-actions')" in app_js and 'applyColumnPrefs();const empty=' in app_js
    assert 'data-col="seeds" data-label="Seeds"' in app_js and 'data-col="peers" data-label="Peers"' in app_js and 'data-col="tags" data-label="Tags"' in app_js
    assert 'swarmColumnValue(t.num_seeds,t.num_complete)' in app_js and 'swarmColumnValue(t.num_leechs,t.num_incomplete)' in app_js
    assert "document.querySelector('#columnPrefList')?.addEventListener('click'" in settings_js and 'saveTorrentColumnPreferencesFromSettings();' in settings_js
    assert '.torrent-column-hidden{display:none!important}' in app_css and '0.5.84 torrent column organizer' in settings_css
    assert '## Configurable torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Configurable torrent columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')

'''
if marker not in validator: raise RuntimeError('UI validator marker missing')
write("release_tools/validate_ui_strings.py",validator.replace(marker,checks+marker,1))

# Release metadata.
rp=p("release_notes/releases.json"); data=json.loads(rp.read_text(encoding="utf-8")); prev=data["releases"][-1]
if any(str(x.get('version'))==NEW for x in data['releases']): raise RuntimeError(f'v{NEW} already documented')
data['releases'].append({
 "version":NEW,"date":"2026-09-03","status":"prerelease","title":"Configurable torrent table columns",
 "summary":"Adds a persistent torrent-column organizer with visibility and ordering controls, expands the available table data, and makes Seeds, Peers, and Tags part of the default dashboard layout.",
 "highlights":["Settings → General now provides a Torrent columns organizer where optional columns can be shown, hidden, and moved up or down.","Seeds, Peers, and Tags are visible by default, with Size, Category, Tracker, and Added available as optional columns.","Name remains the required first data column while the selection checkbox and row-actions control remain fixed.","Column visibility and order persist as a browser-local preference and survive live refreshes and reloads.","Legacy visibility-only tdColumns preferences are migrated automatically into the ordered preference model."],
 "fixes":["Removes the fixed torrent-table column order so users can tailor the dashboard to the information they actually monitor.","Avoids duplicating Size or Category in the Name subtitle when either value is promoted to its own visible column."],
 "technical":["The frontend owns a normalized TORRENT_COLUMN_DEFS catalog and applies visibility/order after every torrent-row render so the one-second refresh cannot reset the chosen layout.","Seeds and Peers use qBitTorrent's connected counts and include the reported total in parentheses when that total is available.","Reorder controls use locally embedded Material-style SVG arrows and remain keyboard accessible without introducing a remote icon dependency."],
 "validation":["The UI audit requires the new column catalog, default Seeds/Peers/Tags visibility, ordered local preference schema, Settings organizer, and live-render reapplication path.","Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."],
 "known_issues":[],"architecture":prev.get('architecture',[]),"next_steps":prev.get('next_steps',[]),
 "decisions":prev.get('decisions',[])+["Treat torrent-table column layout as a browser-local presentation preference rather than shared application configuration.","Keep Name, the selection checkbox, and row actions fixed; allow the remaining torrent data columns to be hidden and reordered.","Expose Seeds, Peers, and Tags in the default torrent table while keeping less frequently needed Size, Category, Tracker, and Added available but hidden by default."]
})
rp.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
subprocess.run([sys.executable,str(p("release_tools/generate_release_notes.py")),"--version",NEW],cwd=ROOT,check=True)
print(f"Applied v{NEW} configurable torrent columns")
