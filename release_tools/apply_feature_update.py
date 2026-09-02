#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.72"
NEW = "0.5.73"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Persistent inspector markup: no close button; the whole bar is the disclosure target.
html = read("static/index.html")
old_detail = '''<section class="torrent-detail-pane hidden" id="torrentDetailPane" aria-label="Torrent details">
<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><div class="detail-pane-actions"><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details" title="Close torrent details">×</button></div></header>
<div class="torrent-detail-tabs" role="tablist" aria-label="Torrent information"><button class="active" data-detailtab="general" type="button">General</button><button data-detailtab="trackers" type="button">Trackers</button><button data-detailtab="peers" type="button">Peers</button><button data-detailtab="webseeds" type="button">HTTP Sources</button><button data-detailtab="content" type="button">Content</button></div>
<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>
</section>'''
new_detail = '''<section class="torrent-detail-pane collapsed" id="torrentDetailPane" aria-label="Torrent details">
<button class="torrent-detail-handle" id="detailHandle" type="button" aria-expanded="false" aria-controls="detailPanelContent">
<span class="torrent-detail-handle-label">Torrent details</span><span class="torrent-detail-handle-selection" id="detailHandleSelection">No torrent selected</span>
<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m6 15 6-6 6 6"/></svg>
</button>
<div class="torrent-detail-content" id="detailPanelContent">
<div class="torrent-detail-context"><strong id="detailName">No torrent selected</strong><span id="detailMeta">Select a torrent to view details.</span></div>
<div class="torrent-detail-tabs" role="tablist" aria-label="Torrent information"><button class="active" data-detailtab="general" type="button">General</button><button data-detailtab="trackers" type="button">Trackers</button><button data-detailtab="peers" type="button">Peers</button><button data-detailtab="webseeds" type="button">HTTP Sources</button><button data-detailtab="content" type="button">Content</button></div>
<div class="torrent-detail-body" id="detailBody"><div class="empty detail-empty"><strong>No torrent selected</strong><span>Select a torrent to view details.</span></div></div>
</div>
</section>'''
html = replace_once(html, old_detail, new_detail, "persistent detail markup")
html = html.replace(OLD, NEW)
write("static/index.html", html)


# Detail state now separates disclosure from selection.
js = read("static/app.js")
js = replace_once(
    js,
    "selected:new Set(),detail:null,detailTab:'general',settings:null",
    "selected:new Set(),detail:null,detailExpanded:false,detailTab:'general',settings:null",
    "detail state",
)

old_detail_block = re.compile(
    r"let detailRefreshAt=0;\nasync function openDetail\(server,hash\)\{.*?\nfunction detailCurrentTorrent\(\)",
    re.S,
)
new_detail_block = '''let detailRefreshAt=0;
function detailEmptyMarkup(){return '<div class="empty detail-empty"><strong>No torrent selected</strong><span>Select a torrent to view details.</span></div>'}
function syncDetailDock(){
  const pane=$('#torrentDetailPane'),handle=$('#detailHandle'),workspace=pane?.closest('.torrent-workspace');if(!pane||!handle)return;
  const expanded=!!state.detailExpanded,selected=!!state.detail;
  pane.classList.toggle('collapsed',!expanded);pane.classList.toggle('has-selection',selected);workspace?.classList.toggle('detail-expanded',expanded);
  handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?($('#detailName')?.textContent||'Selected torrent'):'No torrent selected';
  syncTorrentWorkspaceLayout();
}
async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}
function resetDetailPane(){
  state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='No torrent selected';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='No torrent selected';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();render();
}
async function openDetail(server,hash){
  const same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash),name=t?.name||hash;$('#detailName').textContent=name;$('#detailMeta').textContent=`${t?._server_name||server} · ${hash}`;$('#detailHandleSelection').textContent=name;syncDetailDock();$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}
async function refreshDetailData(force=false){
  if(!state.detail||(!state.detailExpanded&&!force))return;const now=Date.now();if(!force&&now-detailRefreshAt<3000)return;detailRefreshAt=now;const {server,hash}=state.detail;
  if(!state.detail.data)$('#detailBody').innerHTML='<div class="empty">Loading…</div>';
  try{const data=await api(`/api/detail?server=${encodeURIComponent(server)}&hash=${encodeURIComponent(hash)}`);if(!state.detail||state.detail.server!==server||state.detail.hash!==hash)return;state.detail.data=data;renderDetail()}catch(e){if(state.detail)$('#detailBody').innerHTML=`<div class="banner error">${esc(e.message)}</div>`}
}
function detailCurrentTorrent()'''
js, count = old_detail_block.subn(new_detail_block, js, count=1)
if count != 1:
    raise SystemExit(f"detail function block: expected one match, found {count}")

js = replace_once(
    js,
    "const hasDetail=workspace.classList.contains('has-detail');\n  if(mobile||!hasDetail){workspace.style.removeProperty('--torrent-workspace-open-height');return}",
    "const detailExpanded=workspace.classList.contains('detail-expanded');\n  if(mobile||!detailExpanded){workspace.style.removeProperty('--torrent-workspace-open-height');return}",
    "workspace disclosure layout",
)
js = replace_once(js, "state.selected.clear();closeDetailPane();await refreshStatus();", "state.selected.clear();resetDetailPane();await refreshStatus();", "server detail reset")
js = replace_once(
    js,
    "$('#detailClose').addEventListener('click',closeDetailPane);$$('[data-detailtab]').forEach",
    "$('#detailHandle').addEventListener('click',toggleDetailPane);$$('[data-detailtab]').forEach",
    "detail disclosure binding",
)
if any(token in js for token in ("detailClose", "closeDetailPane", "has-detail")):
    raise SystemExit("obsolete close/has-detail state remains in static/app.js")
js = js.replace(f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", 1)
write("static/app.js", js)


# Base detail component: semantic disclosure bar, selected-context row, and clean collapsed state.
css = read("static/app.css")
old_header_css = '.torrent-detail-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 13px;border-bottom:1px solid var(--border);background:var(--panel3)}.torrent-detail-header>div{min-width:0;display:grid;gap:2px}.torrent-detail-header strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-header span{color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.detail-pane-close{width:30px;height:30px;padding:0;border:0;background:transparent;color:var(--muted);font-size:18px}.detail-pane-close:hover{color:var(--text);background:var(--panel2)}'
new_header_css = '.torrent-detail-handle{appearance:none;width:100%;min-height:48px;border:0;border-radius:0;background:linear-gradient(180deg,color-mix(in srgb,var(--panel2) 72%,var(--panel3)),var(--panel3));color:var(--text);padding:0 13px;display:flex;align-items:center;gap:10px;text-align:left}.torrent-detail-handle:hover{background:var(--panel2)}.torrent-detail-handle:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 72%,transparent)}.torrent-detail-handle-label{font-size:11px;font-weight:720;white-space:nowrap}.torrent-detail-handle-selection{min-width:0;flex:1;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-handle svg{width:17px;height:17px;flex:0 0 auto;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s ease}.torrent-detail-handle[aria-expanded="true"] svg{transform:rotate(180deg)}.torrent-detail-content{display:flex;flex:1 1 auto;min-height:0;flex-direction:column}.torrent-detail-context{display:grid;gap:2px;padding:10px 13px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:var(--panel)}.torrent-detail-context strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-context span{color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-pane.collapsed .torrent-detail-content{display:none}.torrent-detail-pane:not(.has-selection) .torrent-detail-context,.torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}'
css = replace_once(css, old_header_css, new_header_css, "base detail handle CSS")

old_desktop_detail = '  .torrent-detail-pane{min-height:320px;max-height:48vh}.torrent-detail-header{padding:12px 15px}.torrent-detail-header strong{font-size:13.5px}.torrent-detail-header span{font-size:11.5px}'
new_desktop_detail = '  .torrent-detail-pane{min-height:320px;max-height:48vh}.torrent-detail-handle{min-height:52px;padding:0 15px}.torrent-detail-handle-label{font-size:13.5px}.torrent-detail-handle-selection{font-size:11.5px}.torrent-detail-context{padding:12px 15px}.torrent-detail-context strong{font-size:13.5px}.torrent-detail-context span{font-size:11.5px}'
css = replace_once(css, old_desktop_detail, new_desktop_detail, "desktop detail legibility CSS")

marker = "/* 0.5.72 separated viewport-docked torrent details. */"
if css.count(marker) != 1:
    raise SystemExit("Could not find the v0.5.72 detail layout block")
css = css.split(marker, 1)[0].rstrip() + '''\n\n/* 0.5.73 persistent collapsible torrent details. */
.torrent-list-region{min-width:0;min-height:0}
@media(min-width:701px){
  .torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}
  .torrent-workspace.detail-expanded{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}
  .torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}
  .torrent-list-region{position:relative;display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}
  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}
  .torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center;padding:20px;text-align:center;pointer-events:none}
  .torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:48px;max-height:none;border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);display:flex;flex:0 0 48px;flex-direction:column;background:var(--panel);overflow:hidden}
  .torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 clamp(260px,46%,420px)}
  .torrent-detail-pane.collapsed{min-height:48px!important;max-height:48px!important;flex-basis:48px!important}
  .torrent-detail-body{flex:1 1 auto;min-height:0;overflow:auto}
}
@media(min-width:1024px){
  .torrent-detail-pane:not(.collapsed){flex-basis:clamp(300px,46%,440px)}
  .torrent-detail-pane.collapsed{min-height:52px!important;max-height:52px!important;flex-basis:52px!important}
}
@media(max-width:700px){
  .torrent-detail-pane{position:fixed;z-index:72;left:8px;right:8px;bottom:58px;top:auto;height:min(68dvh,640px);min-height:240px;max-height:calc(100dvh - 88px);margin:0;border-radius:14px;transition:height .16s ease,min-height .16s ease}
  .torrent-detail-pane.collapsed{height:48px!important;min-height:48px!important;max-height:48px!important;top:auto!important}
  .torrent-detail-handle{min-height:48px;padding-left:14px;padding-right:14px}
  .torrent-detail-handle-label{font-size:12px}.torrent-detail-handle-selection{font-size:10.5px}
  .detail-general-grid{grid-template-columns:1fr}.torrent-detail-tabs{overflow:auto}
}
'''
if any(token in css for token in (".detail-pane-close", ".torrent-detail-header")):
    raise SystemExit("obsolete close/header CSS remains")
write("static/app.css", css)


# Design-language and manual test contracts follow the persistent disclosure model.
design = read("DESIGN_LANGUAGE.md")
design = replace_once(
    design,
    "- Torrent details do not collapse. Selecting a torrent opens the inspector; Close clears the detail context and returns the list to its bounded list-only layout.\n- Mobile may use a bottom-sheet treatment when the available viewport cannot support a useful split workspace.",
    "- Torrent details are persistent and collapsible rather than closable. The collapsed state is a compact disclosure bar; it never clears the selected torrent.\n- Selecting a torrent expands the inspector automatically and updates its content. With no selection, the dock remains available and may be expanded to an empty state.\n- The full disclosure bar is the interaction target and must remain keyboard- and touch-accessible; small icon-only collapse/close controls are not required.\n- Mobile may use a bottom-sheet treatment when expanded, but the collapsed disclosure bar remains persistently reachable.",
    "design disclosure behavior",
)
design = replace_once(
    design,
    "When torrent details are open, the workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above a visually separate detail panel, and allocate enough height to the inspector for its primary content to remain legible.",
    "When torrent details are expanded, the workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above a visually separate detail panel, and allocate enough height to the inspector for its primary content to remain legible. When collapsed, the inspector remains as a compact dock bar without forcing the expanded workspace height.",
    "viewport disclosure wording",
)
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing = replace_once(
    testing,
    "- Selecting a torrent opens the docked inspector on desktop/tablet.\n- Torrent list and detail body scroll independently when needed.\n- Details remain open while a torrent is selected; Close clears the detail context.\n- General, Trackers, Peers, HTTP Sources, and Content tabs render without errors.\n- Mobile retains the bottom-sheet detail presentation.",
    "- The docked torrent-details bar is always present on desktop/tablet and starts collapsed with no selection.\n- Clicking the disclosure bar expands/collapses the inspector without clearing the selected torrent.\n- Selecting a torrent automatically expands the inspector and updates the selected-torrent context.\n- Expanding with no torrent selected shows the empty detail state without errors.\n- Torrent list and detail body scroll independently when needed.\n- General, Trackers, Peers, HTTP Sources, and Content tabs render without errors.\n- Mobile keeps the persistent collapsed bar and uses the bottom-sheet presentation when expanded.",
    "torrent detail testing",
)
testing = replace_once(testing, "- Torrent detail sheet can be opened and closed.", "- Torrent detail bar remains reachable, expands as a bottom sheet, and collapses again with a full-width touch target.", "mobile detail testing")
testing = replace_once(
    testing,
    "- With a torrent selected at normal desktop zoom, verify the torrent list and inspector both remain visible without scrolling the overall page.",
    "- With no torrent selected, verify the compact Torrent details bar remains visible below the torrent list without consuming the expanded workspace height.\n- With a torrent selected at normal desktop zoom, verify the inspector expands automatically and the torrent list and inspector both remain visible without scrolling the overall page.\n- Collapse the inspector and verify the selected row remains selected; expand it again and verify the same torrent details return.",
    "desktop inspector disclosure testing",
)
write("TESTING.md", testing)


# Regression audit: v0.5.73 supersedes v0.5.72's open/close-only contract.
validator = read("release_tools/validate_ui_strings.py")
start = validator.index('    assert "function closeDetailPane" in app_js')
end = validator.index("    assert 'id=\"mTotal\"' in html", start)
new_contract = '''    assert "function toggleDetailPane" in app_js and "function resetDetailPane" in app_js and "function refreshDetailData" in app_js
    assert "now-detailRefreshAt<3000" in app_js
    assert "detailExpanded:false" in app_js
    assert "workspace?.classList.toggle('detail-expanded',expanded)" in app_js
    assert 'class="torrent-workspace"' in html and 'class="torrent-panel torrent-list-panel"' in html
    assert 'class="torrent-detail-pane collapsed"' in html and 'id="detailHandle"' in html
    assert 'aria-expanded="false"' in html and 'aria-controls="detailPanelContent"' in html
    assert 'id="detailClose"' not in html and "closeDetailPane" not in app_js
    assert "detailCollapsed" not in app_js and "tdDetailCollapsed" not in app_js
    assert "state.detailExpanded=!state.detailExpanded" in app_js
    assert "state.detailExpanded=true" in app_js
    assert "(!state.detailExpanded&&!force)" in app_js
    assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}" in app_css
    assert ".torrent-workspace.detail-expanded{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css
    assert ".torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}" in app_css
    assert ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 clamp(260px,46%,420px)}" in app_css
    assert ".torrent-detail-pane.collapsed{min-height:48px!important;max-height:48px!important;flex-basis:48px!important}" in app_css
    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-context,.torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" in app_css
    assert ".torrent-detail-handle{appearance:none;width:100%;min-height:48px" in app_css
    assert ".detail-pane-close" not in app_css and ".torrent-detail-header" not in app_css
    assert "function syncTorrentWorkspaceLayout()" in app_js
    assert "window.innerHeight-top-16" in app_js
    assert "--torrent-workspace-open-height" in app_js
    assert "height:calc(100dvh - 320px);min-height:480px" not in app_css
'''
validator = validator[:start] + new_contract + validator[end:]

late_start = validator.index("    # 0.5.72 supersedes the original collapsible inspector contract.")
late_end = validator.index('    print("UI string audit passed")', late_start)
late_contract = '''    # 0.5.73 supersedes v0.5.72's open/close-only inspector. The dock is
    # persistent, selection and disclosure are independent, and the full bar is
    # the accessible collapse/expand target on desktop and mobile.
    assert 'class="torrent-workspace"' in html
    assert 'class="torrent-panel torrent-list-panel"' in html
    assert 'class="torrent-list-region"' in html
    assert 'class="torrent-detail-pane collapsed"' in html
    assert 'id="detailHandle"' in html and 'id="detailHandleSelection"' in html
    assert 'id="detailClose"' not in html and 'Close torrent details' not in html
    assert 'detailExpanded:false' in app_js and 'detailCollapsed' not in app_js
    assert 'function syncDetailDock()' in app_js and 'async function toggleDetailPane()' in app_js
    assert 'function resetDetailPane()' in app_js and 'closeDetailPane' not in app_js
    assert '0.5.73 persistent collapsible torrent details' in app_css
    assert '.torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto' in app_css
    assert '.torrent-detail-pane{position:static;inset:auto' in app_css
    assert '.torrent-detail-pane.collapsed{min-height:48px!important' in app_css
    assert '.torrent-detail-handle[aria-expanded="true"] svg{transform:rotate(180deg)}' in app_css
    assert '@media(max-width:700px)' in app_css and 'bottom:58px;top:auto;height:min(68dvh,640px)' in app_css

'''
validator = validator[:late_start] + late_contract + validator[late_end:]
write("release_tools/validate_ui_strings.py", validator)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

sw = read("static/sw.js")
sw = sw.replace(OLD, NEW).replace("torrent-dashboard-v0572", "torrent-dashboard-v0573")
write("static/sw.js", sw)


# Structured release metadata; preserve the existing architecture roadmap.
notes_path = ROOT / "release_notes" / "releases.json"
notes = json.loads(notes_path.read_text(encoding="utf-8"))
releases = notes.get("releases") or []
if not releases or releases[-1].get("version") != OLD:
    raise SystemExit(f"Expected latest release metadata to be {OLD}")
if any(item.get("version") == NEW for item in releases):
    raise SystemExit(f"Release metadata already contains {NEW}")
previous = releases[-1]
release = {
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Persistent collapsible torrent details",
    "summary": "Reworks torrent details into a persistent disclosure dock: the inspector can collapse to a compact full-width bar but is no longer closable, and torrent selection remains independent from inspector visibility.",
    "highlights": [
        "Torrent details now remain permanently available below the torrent list as a compact collapsed bar instead of disappearing when dismissed.",
        "The entire styled Torrent details bar toggles expansion, replacing small collapse/close icon controls with a larger keyboard- and touch-friendly target.",
        "Selecting a torrent automatically expands the inspector; collapsing it preserves the selected torrent and expanding again restores the same context.",
        "With no torrent selected, the dock remains available and can expand into a simple empty state rather than vanishing from the dashboard.",
        "Mobile keeps the bottom-sheet detail presentation when expanded while retaining the persistent collapsed bar at the bottom of the interface."
    ],
    "fixes": [
        "Removes the ambiguous Close action that coupled inspector visibility to torrent selection.",
        "Makes torrent details easier to discover and operate on touch devices by keeping a persistent full-width disclosure target."
    ],
    "technical": [
        "Frontend state now tracks detailExpanded independently from state.detail so disclosure and selection are separate concerns.",
        "Periodic detail refreshes pause while the inspector is collapsed and resume when it is expanded.",
        "The workspace only adopts viewport-derived expanded height while the disclosure is open; the collapsed dock stays compact.",
        "DESIGN_LANGUAGE.md, TESTING.md, and the UI regression audit now define the persistent disclosure contract."
    ],
    "validation": [
        "The UI regression audit requires the persistent collapsed dock, full-width disclosure handle, selection-preserving collapse behavior, automatic expansion on row selection, and mobile collapsed-bar treatment.",
        "Existing backend tests, JavaScript syntax validation, generated release metadata, frontend/service-worker version synchronization, and public-repository validation remain release gates."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "decisions": list(previous.get("decisions") or []) + [
        "Treat torrent-detail selection and inspector disclosure as independent state: collapse changes presentation, not selection.",
        "Keep the torrent-detail dock persistently discoverable and use the full disclosure bar as the primary keyboard/touch interaction target."
    ],
    "next_steps": list(previous.get("next_steps") or []),
}
releases.append(release)
notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

# Regenerate deterministic changelog/handoff/project-state artifacts.
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)

print(f"Applied Torrent Dashboard {NEW} persistent collapsible detail dock")
