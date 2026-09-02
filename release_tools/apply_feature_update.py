#!/usr/bin/env python3
"""Apply the v0.5.67 docked torrent-details workspace update."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.66"
NEW = "0.5.67"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"{path}: expected text not found: {old!r}")
    write(path, text.replace(old, new, 1))


# Synchronized build identity.
replace_once("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
index = read("static/index.html")
if OLD not in index:
    raise SystemExit("static/index.html: old build version not found")
index = index.replace(OLD, NEW)
app_js = read("static/app.js")
if f"const FRONTEND_BUILD='{OLD}';" not in app_js:
    raise SystemExit("static/app.js: old frontend build not found")
app_js = app_js.replace(f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", 1)
sw = read("static/sw.js")
if OLD not in sw or "v0566" not in sw:
    raise SystemExit("static/sw.js: expected v0.5.66 cache generation not found")
sw = sw.replace(OLD, NEW).replace("v0566", "v0567")

# Dock the detail inspector inside the torrent workspace so it cannot cover rows.
old_panel_open = '<section class="torrent-panel">\n<div class="table-wrap">'
new_panel_open = '<section class="torrent-panel torrent-workspace">\n<div class="torrent-list-region">\n<div class="table-wrap">'
if old_panel_open not in index:
    raise SystemExit("static/index.html: torrent panel opening not found")
index = index.replace(old_panel_open, new_panel_open, 1)

old_panel_boundary = '<div class="empty hidden" id="empty"><strong>No Torrents Match This View</strong><span>Change the filter or search query.</span></div>\n</section>\n<section class="torrent-detail-pane hidden" id="torrentDetailPane" aria-label="Torrent details">'
new_panel_boundary = '<div class="empty hidden" id="empty"><strong>No Torrents Match This View</strong><span>Change the filter or search query.</span></div>\n</div>\n<section class="torrent-detail-pane hidden" id="torrentDetailPane" aria-label="Torrent details">'
if old_panel_boundary not in index:
    raise SystemExit("static/index.html: torrent/detail boundary not found")
index = index.replace(old_panel_boundary, new_panel_boundary, 1)

old_header = '<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details">×</button></header>'
new_header = '<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><div class="detail-pane-actions"><button class="detail-pane-toggle" id="detailToggle" type="button" aria-expanded="true" aria-label="Collapse torrent details" title="Collapse torrent details"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details" title="Close torrent details">×</button></div></header>'
if old_header not in index:
    raise SystemExit("static/index.html: detail header not found")
index = index.replace(old_header, new_header, 1)

old_detail_end = '<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>\n</section>\n</section>\n<section class="view" id="view-notifications">'
new_detail_end = '<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>\n</section>\n</section>\n</section>\n<section class="view" id="view-notifications">'
if old_detail_end not in index:
    raise SystemExit("static/index.html: detail/dashboard closing boundary not found")
index = index.replace(old_detail_end, new_detail_end, 1)
write("static/index.html", index)

# Preserve a user's collapse preference while keeping close semantically distinct.
state_old = "detail:null,detailTab:'general',settings:null"
state_new = "detail:null,detailTab:'general',detailCollapsed:localStorage.tdDetailCollapsed==='1',settings:null"
if state_old not in app_js:
    raise SystemExit("static/app.js: detail state anchor not found")
app_js = app_js.replace(state_old, state_new, 1)

start = app_js.find("let detailRefreshAt=0;")
end = app_js.find("function detailCurrentTorrent()", start)
if start < 0 or end < 0:
    raise SystemExit("static/app.js: detail function block not found")
new_detail_logic = r'''let detailRefreshAt=0;
function syncDetailPaneState(){
  const pane=$('#torrentDetailPane'),toggle=$('#detailToggle');if(!pane||!toggle)return;
  const collapsed=!!state.detailCollapsed;pane.classList.toggle('collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));
  const label=collapsed?'Expand torrent details':'Collapse torrent details';toggle.setAttribute('aria-label',label);toggle.title=label;
}
async function toggleDetailPane(){
  if(!state.detail)return;state.detailCollapsed=!state.detailCollapsed;localStorage.tdDetailCollapsed=state.detailCollapsed?'1':'0';syncDetailPaneState();
  if(!state.detailCollapsed)await refreshDetailData(true);
}
async function openDetail(server,hash){
  const same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailTab=state.detailTab||'general';
  $('#torrentDetailPane').classList.remove('hidden');syncDetailPaneState();$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));
  const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);$('#detailName').textContent=t?.name||hash;$('#detailMeta').textContent=`${t?._server_name||server} · ${hash}`;render();
  if(!state.detailCollapsed)await refreshDetailData(true);
}
function closeDetailPane(){$('#torrentDetailPane').classList.add('hidden');state.detail=null;render()}
async function refreshDetailData(force=false){
  if(!state.detail||state.detailCollapsed&&!force)return;const now=Date.now();if(!force&&now-detailRefreshAt<3000)return;detailRefreshAt=now;const {server,hash}=state.detail;
  if(!state.detail.data)$('#detailBody').innerHTML='<div class="empty">Loading…</div>';
  try{const data=await api(`/api/detail?server=${encodeURIComponent(server)}&hash=${encodeURIComponent(hash)}`);if(!state.detail||state.detail.server!==server||state.detail.hash!==hash)return;state.detail.data=data;renderDetail()}catch(e){if(state.detail)$('#detailBody').innerHTML=`<div class="banner error">${esc(e.message)}</div>`}
}
'''
app_js = app_js[:start] + new_detail_logic + app_js[end:]

binding_old = "$('#detailClose').addEventListener('click',closeDetailPane);$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));"
binding_new = "$('#detailToggle').addEventListener('click',toggleDetailPane);$('#detailClose').addEventListener('click',closeDetailPane);$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));"
if binding_old not in app_js:
    raise SystemExit("static/app.js: detail binding anchor not found")
app_js = app_js.replace(binding_old, binding_new, 1)
write("static/app.js", app_js)
write("static/sw.js", sw)

# The desktop/tablet inspector is part of the torrent workspace. Mobile keeps the
# established fixed bottom-sheet presentation, with the same collapse behavior.
app_css = read("static/app.css")
marker = "/* 0.5.67 docked collapsible torrent details. */"
if marker in app_css:
    raise SystemExit("static/app.css: v0.5.67 marker already present")
app_css += r'''

/* 0.5.67 docked collapsible torrent details. */
.torrent-list-region{min-width:0;min-height:0}
.detail-pane-actions{display:flex;align-items:center;gap:4px;flex:0 0 auto}
.detail-pane-toggle{width:32px;height:32px;padding:0;border:0;background:transparent;color:var(--muted);display:grid;place-items:center;border-radius:8px}
.detail-pane-toggle:hover,.detail-pane-close:hover{background:var(--panel2);color:var(--text)}
.detail-pane-toggle svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s ease}
.detail-pane-toggle[aria-expanded="true"] svg{transform:rotate(180deg)}
@media(min-width:701px){
  .torrent-workspace{display:flex;flex-direction:column;overflow:hidden}
  .torrent-list-region{display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}
  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}
  .torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:0;max-height:none;border:0;border-top:1px solid var(--border);border-radius:0;box-shadow:none;display:flex;flex-direction:column;background:var(--panel)}
  .torrent-detail-header{flex:0 0 auto;border-bottom:1px solid var(--border)}
  .torrent-detail-tabs{flex:0 0 auto}
  .torrent-detail-body{flex:1 1 auto;min-height:0;overflow:auto}
  .torrent-detail-pane.collapsed{flex:0 0 58px!important;min-height:58px!important;max-height:58px!important}
  .torrent-detail-pane.collapsed .torrent-detail-tabs,.torrent-detail-pane.collapsed .torrent-detail-body{display:none}
  .torrent-detail-pane.collapsed .torrent-detail-header{height:58px;border-bottom:0}
}
@media(min-width:1024px){
  .torrent-workspace{height:calc(100dvh - 320px);min-height:480px}
  .torrent-detail-pane{flex:0 0 clamp(230px,36%,390px)}
}
@media(max-width:700px){
  .torrent-detail-pane.collapsed{top:auto!important;height:58px!important;min-height:58px!important;max-height:58px!important}
  .torrent-detail-pane.collapsed .torrent-detail-tabs,.torrent-detail-pane.collapsed .torrent-detail-body{display:none}
  .torrent-detail-pane.collapsed .torrent-detail-header{height:58px;border-bottom:0}
}
'''
write("static/app.css", app_css)

# Record the interaction rule so later detail surfaces do not regress to overlays.
design = read("DESIGN_LANGUAGE.md")
if "## Docked inspectors" not in design:
    design += """

## Docked inspectors

On desktop and tablet layouts, secondary inspection surfaces that describe a selected item should preserve access to the primary list instead of covering it.

- Torrent details dock to the bottom edge of the torrent workspace and share the same outer surface.
- The primary torrent list remains independently scrollable while details are expanded.
- Collapse preserves the current torrent selection and only reduces the inspector to its header; Close clears the inspector entirely.
- Collapse state may be remembered as a user preference, but selecting a torrent must continue to update the docked header even while collapsed.
- Mobile may use a bottom-sheet treatment when the available viewport cannot support a useful split workspace.
"""
write("DESIGN_LANGUAGE.md", design)

# Extend the UI regression contract around the new workspace semantics.
validator = read("release_tools/validate_ui_strings.py")
needle = '    print("UI string audit passed")\n'
if needle not in validator:
    raise SystemExit("release_tools/validate_ui_strings.py: print anchor not found")
checks = '''    # 0.5.67 docks torrent details into the torrent workspace. The list must\n    # remain the flexible scroll region and collapse must preserve selection.\n    assert 'class="torrent-panel torrent-workspace"' in html\n    assert 'class="torrent-list-region"' in html\n    assert 'id="detailToggle"' in html and 'aria-label="Collapse torrent details"' in html\n    assert "detailCollapsed:localStorage.tdDetailCollapsed==='1'" in app_js\n    assert 'function syncDetailPaneState()' in app_js and 'async function toggleDetailPane()' in app_js\n    assert "localStorage.tdDetailCollapsed=state.detailCollapsed?'1':'0'" in app_js\n    assert "if(!state.detailCollapsed)await refreshDetailData(true)" in app_js\n    assert "state.detailCollapsed&&!force" in app_js\n    assert '0.5.67 docked collapsible torrent details' in app_css\n    assert '.torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto' in app_css\n    assert '.torrent-detail-pane{position:static;inset:auto' in app_css\n    assert '.torrent-detail-pane.collapsed{flex:0 0 58px!important' in app_css\n    assert '@media(max-width:700px)' in app_css and 'top:auto!important;height:58px!important' in app_css\n\n'''
validator = validator.replace(needle, checks + needle, 1)
write("release_tools/validate_ui_strings.py", validator)

# Structured release metadata and generated handoff/changelog.
notes_path = ROOT / "release_notes" / "releases.json"
data = json.loads(notes_path.read_text(encoding="utf-8"))
releases = data.get("releases", [])
if any(str(item.get("version")) == NEW for item in releases):
    raise SystemExit(f"release metadata already contains v{NEW}")
releases.append({
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Docked collapsible torrent details",
    "summary": "Reworks torrent details into a docked, collapsible inspector attached to the bottom of the torrent workspace so the torrent list remains visible and independently scrollable.",
    "highlights": [
        "Torrent details now share the torrent panel's outer surface instead of appearing as a separate floating card on desktop and tablet layouts.",
        "The torrent table is the flexible scroll region above the inspector, so expanding details reduces the list viewport rather than covering torrent rows.",
        "The detail header now provides separate Collapse and Close controls; collapse preserves the selected torrent while Close clears the inspector.",
        "The collapsed preference is remembered locally, and mobile retains its existing bottom-sheet presentation with matching collapse behavior."
    ],
    "fixes": [
        "Torrent details no longer compete visually with the torrent list as a second detached panel on larger displays.",
        "Long torrent lists remain usable while details are open because the table area scrolls independently."
    ],
    "technical": [
        "The detail pane is now nested inside torrent-panel/torrent-workspace with torrent-list-region owning scroll behavior.",
        "Collapsed detail panes skip periodic detail-data refreshes until expanded, reducing unnecessary API work while the inspector is hidden.",
        "DESIGN_LANGUAGE.md now records the docked-inspector interaction contract for future selection/detail surfaces."
    ],
    "validation": [
        "The UI regression audit verifies the nested workspace structure, independent table scrolling, collapse state persistence, refresh suppression while collapsed, and mobile fallback.",
        "Existing backend tests, JavaScript syntax validation, generated release metadata, and frontend/service-worker build synchronization remain release gates."
    ],
    "known_issues": [],
    "architecture": [
        "Torrent Dashboard remains a Python standard-library application with dashboard.py as the HTTP composition root.",
        "Configuration, integrations, users, and configuration transaction coordination remain separated into torrent_dashboard package modules.",
        "The torrent detail inspector remains frontend-owned; this release changes layout/state behavior without changing the /api/detail contract.",
        "Desktop and tablet use a docked split workspace while mobile retains a bottom-sheet detail presentation."
    ],
    "decisions": [
        "Prefer docked inspectors over overlays when users need to compare selected-item details with a primary list.",
        "Keep Collapse and Close as distinct actions: collapse preserves selection, close clears the detail context.",
        "Keep the torrent table independently scrollable whenever the detail inspector is expanded."
    ],
    "next_steps": [
        {"priority": 1, "title": "Extract release and update provenance", "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py."},
        {"priority": 2, "title": "Extract qBitTorrent transport and normalization", "detail": "Move QBitClient, server normalization, proxy/preference translation, and Web API transport away from HTTP routing."},
        {"priority": 3, "title": "Expand request-level behavioral tests", "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around extracted service boundaries."},
        {"priority": 4, "title": "Harden secrets at rest", "detail": "Use the configuration boundary to add restrictive file permissions and separate ordinary configuration from stored credentials."}
    ]
})
data["releases"] = releases
notes_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} docked torrent-details workspace")
