#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.85"
NEW = "0.5.86"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected source fragment not found in {path}: {old[:160]!r}")
    write(path, text.replace(old, new, count))


def regex_replace(path: str, pattern: str, replacement: str, count: int = 1) -> None:
    text = read(path)
    updated, changes = re.subn(pattern, replacement, text, count=count, flags=re.S)
    if changes != count:
        raise RuntimeError(f"Expected {count} regex replacement(s) in {path}, got {changes}: {pattern}")
    write(path, updated)


# Build/version synchronization.
replace("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
write("static/index.html", read("static/index.html").replace(OLD, NEW))
replace("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
sw = read("static/sw.js").replace("torrent-dashboard-v0585", "torrent-dashboard-v0586").replace(OLD, NEW)
write("static/sw.js", sw)

# Remove the temporary Settings-based column organizer. Column management now
# belongs to the torrent table header itself.
replace(
    "static/index.html",
    '<fieldset class="column-prefs"><legend>Torrent columns</legend><p class="column-pref-help">Choose which columns are shown and arrange their order. Name is always shown.</p><div class="column-pref-list" id="columnPrefList"></div><button class="secondary small-btn column-pref-reset" id="resetColumns" type="button">Reset columns</button></fieldset>\n',
    '',
)

# Make the actual data headers draggable and add a dedicated header context menu.
html = read("static/index.html")
html, changed = re.subn(r'<th data-col="([^"]+)">', r'<th draggable="true" data-col="\1">', html)
if changed != 14:
    raise RuntimeError(f"Expected 14 draggable torrent data headers, updated {changed}")
needle = '<div class="menu hidden" id="contextMenu"></div>\n'
if needle not in html:
    raise RuntimeError("Torrent context-menu anchor not found")
html = html.replace(
    needle,
    needle + '<div class="menu column-menu hidden" id="columnMenu" role="menu" aria-label="Torrent columns"></div>\n',
    1,
)
write("static/index.html", html)

# Remove Settings controller dependencies on the retired organizer.
settings = read("static/settings.js")
for fragment in (
    "    document.querySelector('#columnPrefList')?.addEventListener('click', e => { const button=e.target.closest('[data-column-move]'); if(button){ const row=button.closest('[data-column-key]'); moveTorrentColumnPreference(row?.dataset.columnKey||'',button.dataset.columnMove); } });\n",
    "    document.querySelector('#resetColumns')?.addEventListener('click', resetTorrentColumnPreferences);\n",
    "    renderTorrentColumnPreferences();\n",
    "      saveTorrentColumnPreferencesFromSettings();\n",
):
    if fragment not in settings:
        raise RuntimeError(f"Expected Settings column-organizer fragment not found: {fragment.strip()}")
    settings = settings.replace(fragment, '', 1)
write("static/settings.js", settings)

# Replace the v0.5.84/v0.5.85 column organizer implementation with direct
# manipulation: drag headers to reorder, right-click the header bar to show/hide.
column_block = r'''const TORRENT_COLUMN_DEFS=[
  {key:'name',label:'Name',required:true,defaultVisible:true},{key:'size',label:'Size',defaultVisible:false},{key:'progress',label:'Progress',defaultVisible:true},{key:'state',label:'Status',defaultVisible:true},{key:'seeds',label:'Seeds',defaultVisible:true},{key:'peers',label:'Peers',defaultVisible:true},{key:'down',label:'Download',defaultVisible:true},{key:'up',label:'Upload',defaultVisible:true},{key:'eta',label:'ETA',defaultVisible:true},{key:'ratio',label:'Ratio',defaultVisible:true},{key:'category',label:'Category',defaultVisible:true},{key:'tags',label:'Tags',defaultVisible:true},{key:'tracker',label:'Tracker',defaultVisible:false},{key:'added',label:'Added',defaultVisible:false},
];
const DEFAULT_TORRENT_COLUMN_ORDER=TORRENT_COLUMN_DEFS.map(column=>column.key);
function defaultTorrentColumnPreferences(){return{order:[...DEFAULT_TORRENT_COLUMN_ORDER],visible:Object.fromEntries(TORRENT_COLUMN_DEFS.map(column=>[column.key,!!column.defaultVisible]))}}
function torrentColumnPreferences(){
  let raw={};try{raw=JSON.parse(localStorage.tdColumns||'{}')||{}}catch{raw={}}
  const known=new Set(DEFAULT_TORRENT_COLUMN_ORDER),legacy=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{},source=raw?.visible&&typeof raw.visible==='object'?raw.visible:legacy;
  const supplied=Array.isArray(raw?.order)?raw.order.map(String).filter((key,index,list)=>known.has(key)&&list.indexOf(key)===index):[];
  const order=[...supplied,...DEFAULT_TORRENT_COLUMN_ORDER.filter(key=>!supplied.includes(key))];
  const previousDefault={name:true,size:false,progress:true,state:true,seeds:true,peers:true,down:true,up:true,eta:true,ratio:true,category:false,tags:true,tracker:false,added:false};
  const savedPreviousDefault=!!raw?.visible&&Array.isArray(raw.order)&&raw.order.length===DEFAULT_TORRENT_COLUMN_ORDER.length&&raw.order.every((key,index)=>key===DEFAULT_TORRENT_COLUMN_ORDER[index])&&DEFAULT_TORRENT_COLUMN_ORDER.every(key=>raw.visible[key]===previousDefault[key]);
  const visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(savedPreviousDefault&&column.key==='category'?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible));
  return{order,visible};
}
function torrentColumnVisible(key,prefs=torrentColumnPreferences()){const def=TORRENT_COLUMN_DEFS.find(column=>column.key===key);return !!def?.required||prefs.visible[key]!==false}
function saveTorrentColumnPreferences(prefs){localStorage.tdColumns=JSON.stringify(prefs)}
function resetTorrentColumns(){saveTorrentColumnPreferences(defaultTorrentColumnPreferences());render()}
function setTorrentColumnVisibility(key,visible){const column=TORRENT_COLUMN_DEFS.find(item=>item.key===key);if(!column||column.required)return;const prefs=torrentColumnPreferences();prefs.visible[key]=!!visible;saveTorrentColumnPreferences(prefs);render()}
function reorderTorrentColumns(sourceKey,targetKey,after=false){
  if(!sourceKey||!targetKey||sourceKey===targetKey)return;const prefs=torrentColumnPreferences(),order=[...prefs.order],source=order.indexOf(sourceKey),target=order.indexOf(targetKey);if(source<0||target<0)return;
  order.splice(source,1);let insert=order.indexOf(targetKey)+(after?1:0);insert=Math.max(0,Math.min(order.length,insert));order.splice(insert,0,sourceKey);prefs.order=order;saveTorrentColumnPreferences(prefs);applyColumnPrefs();
}
let draggedTorrentColumn='';
function clearTorrentColumnDropHints(){document.querySelectorAll('#torrentTable thead th.column-drop-before,#torrentTable thead th.column-drop-after').forEach(th=>th.classList.remove('column-drop-before','column-drop-after'))}
function renderTorrentColumnMenu(){
  const menu=$('#columnMenu');if(!menu)return;const prefs=torrentColumnPreferences(),defs=new Map(TORRENT_COLUMN_DEFS.map(column=>[column.key,column]));
  menu.innerHTML='<div class="menu-caption">Columns</div>'+prefs.order.map(key=>{const column=defs.get(key);if(!column)return'';const checked=torrentColumnVisible(key,prefs),required=!!column.required;return `<button class="column-menu-item" type="button" role="menuitemcheckbox" aria-checked="${checked}" data-column-toggle="${esc(key)}" ${required?'disabled':''}><span class="column-menu-check">${checked?materialIconSvg('check'):''}</span><span>${esc(column.label)}</span>${required?'<small>Required</small>':''}</button>`}).join('')+'<div class="menu-separator" role="separator"></div><button class="column-menu-reset" data-column-reset="1" type="button">Reset columns</button>';
  menu.querySelectorAll('[data-column-toggle]').forEach(button=>button.addEventListener('click',()=>{if(button.disabled)return;setTorrentColumnVisibility(button.dataset.columnToggle,button.getAttribute('aria-checked')!=='true');renderTorrentColumnMenu()}));
  menu.querySelector('[data-column-reset]')?.addEventListener('click',()=>{resetTorrentColumns();renderTorrentColumnMenu()});
}
function showTorrentColumnMenu(x,y){
  const menu=$('#columnMenu');if(!menu)return;$$('.menu').forEach(item=>{if(item!==menu)item.classList.add('hidden')});renderTorrentColumnMenu();menu.classList.remove('hidden');const rect=menu.getBoundingClientRect();menu.style.left=Math.max(8,Math.min(innerWidth-rect.width-8,x))+'px';menu.style.top=Math.max(8,Math.min(innerHeight-rect.height-8,y))+'px';
}
function bindTorrentColumnHeaderUI(){
  const head=$('#torrentTable thead');if(!head||head.dataset.columnUiBound==='1')return;head.dataset.columnUiBound='1';
  head.querySelectorAll('th[data-col]').forEach(th=>{th.draggable=true;th.title='Drag to reorder. Right-click to show or hide columns.'});
  head.addEventListener('contextmenu',event=>{event.preventDefault();showTorrentColumnMenu(event.clientX,event.clientY)});
  head.addEventListener('dragstart',event=>{const th=event.target.closest('th[data-col]');if(!th)return;draggedTorrentColumn=th.dataset.col||'';event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedTorrentColumn);requestAnimationFrame(()=>th.classList.add('column-dragging'))});
  head.addEventListener('dragover',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th||th.dataset.col===draggedTorrentColumn)return;event.preventDefault();clearTorrentColumnDropHints();const after=event.clientX>th.getBoundingClientRect().left+th.getBoundingClientRect().width/2;th.classList.add(after?'column-drop-after':'column-drop-before');event.dataTransfer.dropEffect='move'});
  head.addEventListener('drop',event=>{if(!draggedTorrentColumn)return;const th=event.target.closest('th[data-col]');if(!th)return;event.preventDefault();const rect=th.getBoundingClientRect(),after=event.clientX>rect.left+rect.width/2;reorderTorrentColumns(draggedTorrentColumn,th.dataset.col,after);clearTorrentColumnDropHints()});
  head.addEventListener('dragend',event=>{event.target.closest('th[data-col]')?.classList.remove('column-dragging');draggedTorrentColumn='';clearTorrentColumnDropHints()});
}
'''
regex_replace(
    "static/app.js",
    r"const TORRENT_COLUMN_DEFS=\[.*?function saveTorrentColumnPreferencesFromSettings\(\)\{.*?\}\n\n(?=function esc)",
    column_block + "\n",
)

# Add a local Material check icon for the column menu.
replace(
    "static/app.js",
    "  arrow_downward:'M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.59-5.58L4 12l8 8 8-8Z',\n};",
    "  arrow_downward:'M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.59-5.58L4 12l8 8 8-8Z',\n  check:'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',\n};",
)

# Bind the header interaction and let Escape dismiss the column menu before it
# falls through to selection/detail disclosure behavior.
replace(
    "static/app.js",
    "  $('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);\n",
    "  $('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);bindTorrentColumnHeaderUI();\n",
)
replace(
    "static/app.js",
    "if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}",
    "if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#columnMenu')?.classList.contains('hidden')){$('#columnMenu').classList.add('hidden');return}",
)

# Remove dead Settings-era column CSS, then style drag targets and the direct
# header context menu.
app_css = read("static/app.css")
app_css, changes = re.subn(
    r'\.column-prefs\{border:1px solid var\(--border\);border-radius:10px;padding:10px;margin:0 0 12px\}.*?\.hide-col-ratio \[data-col="ratio"\]\{display:none!important\}\n',
    '',
    app_css,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not remove legacy app.css column preference block")
app_css += r'''

/* 0.5.86 direct torrent-column manipulation. */
#torrentTable thead th[data-col]{cursor:grab;user-select:none;-webkit-user-select:none}
#torrentTable thead th[data-col]:active{cursor:grabbing}
#torrentTable thead th.column-dragging{opacity:.46}
#torrentTable thead th.column-drop-before{box-shadow:inset 3px 0 0 var(--accent)}
#torrentTable thead th.column-drop-after{box-shadow:inset -3px 0 0 var(--accent)}
.column-menu{min-width:224px;max-height:min(72vh,540px);overflow:auto;padding:6px}
.column-menu .menu-caption{padding:7px 9px 8px;color:var(--muted);font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}
.column-menu-item{display:grid!important;grid-template-columns:22px minmax(0,1fr) auto;align-items:center;gap:8px;min-height:34px;padding:7px 9px!important;color:var(--text)!important}
.column-menu-item .column-menu-check{display:grid;place-items:center;width:18px;height:18px;color:var(--accent)}
.column-menu-item .column-menu-check .material-symbol-icon{width:17px;height:17px}
.column-menu-item small{color:var(--muted);font-size:8.5px}
.column-menu-item:disabled{opacity:.68;cursor:default}
.column-menu-reset{margin-top:2px;color:var(--muted)!important}
.column-menu-reset:hover{color:var(--text)!important}
'''
write("static/app.css", app_css)

settings_css = read("static/settings.css")
settings_css, changes = re.subn(r'\n\n/\* 0\.5\.84 torrent column organizer\. \*/\n.*?\Z', '\n', settings_css, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not remove v0.5.84 Settings column-organizer styles")
write("static/settings.css", settings_css)

# Update current design/testing contracts to the direct-manipulation model.
design = read("DESIGN_LANGUAGE.md")
design_section = '''## Configurable torrent columns

The torrent table is a user-configurable local workspace, and column management lives where the columns are used.

- **Name** is required and cannot be hidden. The selection checkbox and row-actions control remain fixed at the outer edges; visible data columns can be reordered directly.
- On desktop/tablet, drag a visible torrent column header horizontally to change its position. The chosen order is persisted immediately and must survive the one-second live refresh and browser reloads.
- Right-click anywhere on the torrent header bar to open the **Columns** menu. Optional columns can be shown or hidden there without opening Settings; **Reset columns** restores the documented default.
- The available column catalog includes Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added.
- Seeds, Peers, Category, and Tags are part of the default visible layout. Size, Tracker, and Added remain available but hidden by default to limit unnecessary width.
- Column layout is a browser-local presentation preference. It must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own visible column, the Name cell should avoid repeating the same value in its secondary summary line.
- Direct manipulation should use clear drag/drop feedback and a conventional header context menu rather than duplicating the same controls in Settings.
'''
design, changes = re.subn(r'## Configurable torrent columns\n.*\Z', design_section, design, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns design section")
write("DESIGN_LANGUAGE.md", design.rstrip() + "\n")

testing = read("TESTING.md")
testing_section = '''### Configurable torrent columns

- On a browser with no saved column preference, verify Seeds, Peers, Category, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.
- Verify Settings → General no longer contains a duplicate torrent-column organizer.
- Drag several visible column headers left and right and verify the table follows the new order immediately, after the next one-second refresh, and after a full browser reload.
- Right-click the torrent header bar and verify the Columns menu lists every data column, keeps Name required, and can show/hide every optional column.
- Hide and restore several columns from the header menu and verify the table updates immediately without changing qBitTorrent state.
- Use Reset columns from the header menu and verify the default order/visibility is restored, including Category.
- Verify Size, Tracker, and Added can be enabled; Seeds displays connected seeds with the total in parentheses when qBitTorrent supplies a total, and Peers follows the same convention.
- Verify the selection checkbox and row-actions control remain fixed at the outer edges regardless of data-column order.
- Verify a browser with an existing customized v0.5.84/v0.5.85 layout keeps that custom order and visibility instead of being overwritten by the new interaction model.
'''
testing, changes = re.subn(r'### Configurable torrent columns\n.*\Z', testing_section, testing, count=1, flags=re.S)
if changes != 1:
    raise RuntimeError("Could not replace configurable torrent columns testing section")
write("TESTING.md", testing.rstrip() + "\n")

# Replace the now-superseded Settings-organizer UI assertions with the direct
# header manipulation contract.
validator = read("release_tools/validate_ui_strings.py")
validator_block = '''    # 0.5.84-v0.5.86 keeps torrent columns locally configurable; v0.5.86
    # moves management from Settings to direct table-header interactions.
    assert 'id="columnPrefList"' not in html and 'id="resetColumns"' not in html
    assert 'class="menu column-menu hidden" id="columnMenu"' in html and 'aria-label="Torrent columns"' in html
    assert html.count('draggable="true" data-col=') == 14
    assert "{key:'seeds',label:'Seeds',defaultVisible:true}" in app_js
    assert "{key:'peers',label:'Peers',defaultVisible:true}" in app_js
    assert "{key:'category',label:'Category',defaultVisible:true}" in app_js
    assert "{key:'tags',label:'Tags',defaultVisible:true}" in app_js
    assert "{key:'size',label:'Size',defaultVisible:false}" in app_js
    assert "savedPreviousDefault&&column.key==='category'?true" in app_js
    assert 'function torrentColumnPreferences()' in app_js and 'function saveTorrentColumnPreferences(prefs)' in app_js
    assert 'function bindTorrentColumnHeaderUI()' in app_js and "head.addEventListener('contextmenu'" in app_js
    assert "head.addEventListener('dragstart'" in app_js and "head.addEventListener('dragover'" in app_js and "head.addEventListener('drop'" in app_js
    assert 'function reorderTorrentColumns(sourceKey,targetKey,after=false)' in app_js
    assert 'function renderTorrentColumnMenu()' in app_js and 'function showTorrentColumnMenu(x,y)' in app_js
    assert "materialIconSvg('check')" in app_js
    assert "row.querySelector('.row-actions-head,.row-actions')" in app_js and 'applyColumnPrefs();const empty=' in app_js
    assert 'data-col="seeds" data-label="Seeds"' in app_js and 'data-col="peers" data-label="Peers"' in app_js and 'data-col="tags" data-label="Tags"' in app_js
    assert 'swarmColumnValue(t.num_seeds,t.num_complete)' in app_js and 'swarmColumnValue(t.num_leechs,t.num_incomplete)' in app_js
    assert 'renderTorrentColumnPreferences' not in app_js and 'saveTorrentColumnPreferencesFromSettings' not in app_js
    assert "document.querySelector('#columnPrefList')" not in settings_js and 'saveTorrentColumnPreferencesFromSettings' not in settings_js
    assert '.torrent-column-hidden{display:none!important}' in app_css
    assert '0.5.86 direct torrent-column manipulation' in app_css
    assert '0.5.84 torrent column organizer' not in settings_css
    assert '## Configurable torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'Right-click anywhere on the torrent header bar' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Configurable torrent columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
validator, changes = re.subn(
    r'    # 0\.5\.84 makes torrent data columns locally configurable and reorderable\.\n.*?(?=\n    print\("UI string audit passed"\))',
    validator_block.rstrip(),
    validator,
    count=1,
    flags=re.S,
)
if changes != 1:
    raise RuntimeError("Could not replace v0.5.84 column validator block")
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
decisions.append("Manage torrent columns directly from the torrent header: drag visible headers to reorder and use the header context menu to show/hide optional columns; keep Name required and Category visible in the default layout.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Direct torrent column controls",
    "summary": "Moves torrent-column customization out of Settings and onto the torrent table itself with draggable headers, a right-click Columns menu, and Category retained in the default visible layout.",
    "highlights": [
        "Visible torrent data columns can be dragged horizontally to reorder them directly in the table header.",
        "Right-clicking the torrent header bar opens a Columns menu for showing or hiding optional columns and restoring defaults.",
        "Category remains visible by default alongside Seeds, Peers, and Tags.",
        "The Settings → General torrent-column organizer has been removed so column management has one clear interaction surface."
    ],
    "fixes": [
        "Removes the extra navigation round trip required to adjust a table layout while looking at the Dashboard.",
        "Preserves existing customized browser column layouts while retaining the v0.5.85 migration that promotes Category for browsers still using the previous default snapshot."
    ],
    "technical": [
        "Header drag/drop updates the same browser-local tdColumns order used by the one-second render path, so live refreshes cannot reset the layout.",
        "The header context menu uses the existing local menu surface and embedded Material SVG check icon; no remote UI dependency is added.",
        "Selection and row-action columns remain outside the reorderable data-column set, while Name is required but may participate in data-column ordering."
    ],
    "validation": [
        "The UI audit rejects the retired Settings organizer and requires draggable data headers, the header context menu, Category default visibility, local persistence, and drag/drop handlers.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} direct torrent column controls")
