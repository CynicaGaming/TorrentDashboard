#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.115"
NEW = "0.5.116"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Frontend: keep the Torrent Details shell structurally present without a
# selection, while using animated skeletons only during a real detail fetch.
app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    "detail:null,detailExpanded:false,detailTab:'general'",
    "detail:null,detailExpanded:window.matchMedia('(min-width:701px)').matches,detailTab:'general'",
    "initial detail shell state",
)

old_empty = "function detailEmptyMarkup(){return '<div class=\"empty detail-empty\"><span>Select a torrent to view details.</span></div>'}"
new_empty = r'''const DETAIL_TEMPLATE_GROUPS={
  transfer:['Time active','Downloaded','Download speed','Download limit','Share ratio','Popularity','ETA','Uploaded','Upload speed','Upload limit','Reannounce in'],
  swarm:['Connections','Seeds','Peers','Wasted','Last seen complete'],
  information:['Total size','Added on','Completed on','Private','Pieces','Created by','Created on','Save path','Comment'],
};
function detailTemplateValue(loading=false){return loading?'<span class="detail-skeleton-line" aria-hidden="true"></span>':'—'}
function detailTemplateStat(label,loading=false){return`<div class="detail-stat"><span>${esc(label)}</span><b>${detailTemplateValue(loading)}</b></div>`}
function detailGeneralTemplateMarkup(loading=false){
  const mode=loading?'detail-loading':'detail-template-empty',value=detailTemplateValue(loading),bar=loading?' detail-skeleton-block':'';
  return`<div class="detail-template ${mode}"><div class="detail-progress-grid"><div class="detail-progress-row"><span>Progress</span><div class="detail-progress-bar${bar}"><span style="width:0"></span></div><b>${value}</b></div><div class="detail-progress-row"><span>Availability</span><div class="detail-progress-bar availability${bar}"><span style="width:0"></span></div><b>${value}</b></div></div><div class="detail-general-grid"><section class="detail-general-section"><strong>Transfer</strong>${DETAIL_TEMPLATE_GROUPS.transfer.map(x=>detailTemplateStat(x,loading)).join('')}</section><section class="detail-general-section"><strong>Swarm</strong>${DETAIL_TEMPLATE_GROUPS.swarm.map(x=>detailTemplateStat(x,loading)).join('')}</section><section class="detail-general-section"><strong>Information</strong>${DETAIL_TEMPLATE_GROUPS.information.map(x=>detailTemplateStat(x,loading)).join('')}</section></div></div>`
}
function detailTemplateTable(headers,loading=false,rows=3){
  const body=loading?Array.from({length:rows},()=>`<tr>${headers.map(()=>`<td><span class="detail-skeleton-line" aria-hidden="true"></span></td>`).join('')}</tr>`).join(''):'';
  return`<div class="detail-desktop-only detail-table-wrap detail-template ${loading?'detail-loading':'detail-template-empty'}"><table class="detail-table compact"><thead><tr>${headers.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></div>`
}
function detailTemplateMobile(tab,loading=false){
  const value=detailTemplateValue(loading),mode=loading?'detail-loading':'detail-template-empty';
  if(tab==='peers')return`<div class="detail-mobile-only detail-record-list detail-template ${mode}"><article class="detail-record-card detail-peer-card"><div class="detail-record-heading"><div class="detail-record-title"><strong>${value}</strong><span>${value}</span></div></div><div class="detail-record-metrics"><div class="detail-record-metric"><span>Progress</span><b>${value}</b></div><div class="detail-record-metric"><span>Download</span><b>${value}</b></div><div class="detail-record-metric"><span>Upload</span><b>${value}</b></div></div></article></div>`;
  if(tab==='trackers')return`<div class="detail-mobile-only detail-record-list detail-template ${mode}"><article class="detail-record-card detail-tracker-card"><div class="detail-record-heading"><div class="detail-record-title"><strong>${value}</strong></div><span class="detail-status-badge neutral">${value}</span></div><div class="detail-record-metrics"><div class="detail-record-metric"><span>Seeds</span><b>${value}</b></div><div class="detail-record-metric"><span>Peers</span><b>${value}</b></div></div></article></div>`;
  if(tab==='webseeds')return`<div class="detail-mobile-only detail-record-list detail-template ${mode}"><article class="detail-record-card"><div class="detail-record-metric"><span>URL</span><b>${value}</b></div></article></div>`;
  return`<div class="detail-mobile-only detail-record-list detail-template ${mode}"><article class="detail-record-card"><div class="detail-record-title"><strong>${value}</strong></div><div class="detail-record-metrics"><div class="detail-record-metric"><span>Progress</span><b>${value}</b></div><div class="detail-record-metric"><span>Size</span><b>${value}</b></div><div class="detail-record-metric"><span>Priority</span><b>${value}</b></div></div></article></div>`
}
function detailTemplateMarkup(tab=state.detailTab,loading=false){
  if(tab==='general')return detailGeneralTemplateMarkup(loading);
  const headers=tab==='trackers'?['Tracker','Status','Seeds','Peers','Message']:tab==='peers'?['Address','Client','Progress','Down','Up']:tab==='webseeds'?['URL']:['Name','Progress','Size','Priority'];
  return detailTemplateTable(headers,loading,tab==='webseeds'?2:3)+detailTemplateMobile(tab,loading)
}
function detailEmptyMarkup(tab=state.detailTab){return detailTemplateMarkup(tab,false)}
function detailLoadingMarkup(tab=state.detailTab){return detailTemplateMarkup(tab,true)}'''
app_js = replace_once(app_js, old_empty, new_empty, "detail empty template")

old_toggle_reset = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}
function resetDetailPane(renderList=true){
  state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();
}"""
new_toggle_reset = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded){renderDetail();if(state.detail)await refreshDetailData(true)}
}
function resetDetailPane(renderList=true){
  state.detail=null;state.detailExpanded=window.matchMedia('(min-width:701px)').matches;detailRefreshAt=0;$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();
}"""
app_js = replace_once(app_js, old_toggle_reset, new_toggle_reset, "detail toggle/reset behavior")

app_js = replace_once(
    app_js,
    "if(!state.detail.data)$('#detailBody').innerHTML='<div class=\"empty\">Loading…</div>';",
    "if(!state.detail.data)renderDetail();",
    "detail loading state",
)

old_render = "function renderDetail(){if(!state.detail?.data)return;const d=state.detail.data,p=d.properties||{},t=detailCurrentTorrent()||{};if(state.detailTab==='general')renderDetailGeneral(t,p);else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='webseeds')renderWebSeeds(d.webseeds||[]);else renderFiles(d.files||[]);requestAnimationFrame(syncDesktopDetailPaneHeight)}"
new_render = "function renderDetail(){if(!state.detail){$('#detailBody').innerHTML=detailEmptyMarkup();requestAnimationFrame(syncDesktopDetailPaneHeight);return}if(!state.detail.data){$('#detailBody').innerHTML=detailLoadingMarkup();requestAnimationFrame(syncDesktopDetailPaneHeight);return}const d=state.detail.data,p=d.properties||{},t=detailCurrentTorrent()||{};if(state.detailTab==='general')renderDetailGeneral(t,p);else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='webseeds')renderWebSeeds(d.webseeds||[]);else renderFiles(d.files||[]);requestAnimationFrame(syncDesktopDetailPaneHeight)}"
app_js = replace_once(app_js, old_render, new_render, "detail renderer")

app_js = replace_once(
    app_js,
    "const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;",
    "const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&(!state.detail||!!state.detail.data);",
    "desktop empty General fit",
)

app_js = replace_once(
    app_js,
    "  bound=true;\n}",
    "  syncDetailDock();renderDetail();\n  bound=true;\n}",
    "initial detail shell render",
)

app_js = replace_once(app_js, "const FRONTEND_BUILD='0.5.115';", "const FRONTEND_BUILD='0.5.116';", "frontend build")
write("static/app.js", app_js)

html = read("static/index.html")
html = replace_once(
    html,
    '<div class="torrent-detail-body" id="detailBody"><div class="empty detail-empty"><span>Select a torrent to view details.</span></div></div>',
    '<div class="torrent-detail-body" id="detailBody"></div>',
    "initial detail empty message",
)
html = html.replace(OLD, NEW)
write("static/index.html", html)

css = read("static/app.css")
css = replace_once(css, ".torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}", "", "no-selection tab hiding")
css += r'''

/* 0.5.116 persistent Torrent Details shell */
.detail-template-empty .detail-stat b,.detail-template-empty .detail-progress-row b,.detail-template-empty .detail-record-title strong,.detail-template-empty .detail-record-title span,.detail-template-empty .detail-record-metric b,.detail-template-empty .detail-status-badge{color:var(--muted);font-weight:500}
.detail-template-empty .detail-progress-bar>span{width:0!important}
.detail-skeleton-line,.detail-skeleton-block{position:relative;overflow:hidden;background:color-mix(in srgb,var(--panel2) 76%,var(--border));border-radius:999px;color:transparent!important}
.detail-skeleton-line{display:block;width:min(128px,74%);height:8px;min-width:34px}
.detail-skeleton-block{border:0!important}
.detail-skeleton-line::after,.detail-skeleton-block::after{content:"";position:absolute;inset:0;transform:translateX(-110%);background:linear-gradient(90deg,transparent,color-mix(in srgb,var(--text) 10%,transparent),transparent);animation:detailSkeletonSweep 1.25s ease-in-out infinite}
.detail-loading .detail-progress-bar>span{display:none}
.detail-loading .detail-record-card{pointer-events:none}
@keyframes detailSkeletonSweep{to{transform:translateX(110%)}}
@media(prefers-reduced-motion:reduce){.detail-skeleton-line::after,.detail-skeleton-block::after{animation:none}}
'''
write("static/app.css", css)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    '    assert "detailExpanded:false" in app_js',
    '    assert "detailExpanded:window.matchMedia(\'(min-width:701px)\').matches" in app_js',
    "initial detail expansion validator",
)
validator = replace_once(
    validator,
    "    assert 'detailExpanded:false' in app_js and 'detailCollapsed' not in app_js",
    "    assert \"detailExpanded:window.matchMedia('(min-width:701px)').matches\" in app_js and 'detailCollapsed' not in app_js",
    "legacy detail expansion validator",
)
validator = replace_once(
    validator,
    '    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" in app_css',
    '    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" not in app_css\n    assert "function detailEmptyMarkup(tab=state.detailTab)" in app_js\n    assert "function detailLoadingMarkup(tab=state.detailTab)" in app_js\n    assert "function detailTemplateMarkup(tab=state.detailTab,loading=false)" in app_js\n    assert "Select a torrent to view details." not in html and "Select a torrent to view details." not in app_js\n    assert "detail-skeleton-line" in app_css and "@keyframes detailSkeletonSweep" in app_css',
    "persistent detail shell validator",
)
validator = replace_once(
    validator,
    '    assert "state.detailExpanded=true" in app_js',
    '    assert "state.detailExpanded=true" in app_js\n    assert "state.detailExpanded=window.matchMedia(\'(min-width:701px)\').matches" in app_js\n    assert "if(state.detailExpanded){renderDetail();if(state.detail)await refreshDetailData(true)}" in app_js\n    assert "if(!state.detail){$(\'#detailBody\').innerHTML=detailEmptyMarkup()" in app_js',
    "detail shell behavior validator",
)
validator = replace_once(
    validator,
    '    assert "state.detailTab===\'general\'" in app_js',
    '    assert "state.detailTab===\'general\'" in app_js\n    assert "state.detailTab===\'general\'&&(!state.detail||!!state.detail.data)" in app_js',
    "no-selection General fit validator",
)
write("release_tools/validate_ui_strings.py", validator)

dashboard = read("dashboard.py")
dashboard, count = re.subn(r'VERSION\s*=\s*[\"\']0\.5\.115[\"\']', 'VERSION = "0.5.116"', dashboard, count=1)
if count != 1:
    raise SystemExit(f"dashboard.py VERSION: expected one replacement, found {count}")
write("dashboard.py", dashboard)

sw = read("static/sw.js")
sw = sw.replace("0.5.115", "0.5.116")
sw = replace_once(sw, "torrent-dashboard-v05115", "torrent-dashboard-v05116", "service-worker cache key")
write("static/sw.js", sw)

design = read("DESIGN_LANGUAGE.md")
if "### Persistent Torrent Details shell" not in design:
    design += '''\n\n### Persistent Torrent Details shell\n\n- On desktop, Torrent Details remains a stable structural part of the dashboard even when no torrent is selected.\n- The no-selection state renders the normal General structure and keeps Trackers, Peers, HTTP sources, and Content tabs available without explanatory empty-state copy.\n- Static em-dash placeholders communicate unavailable values; animated skeletons are reserved for the brief interval after a real torrent is selected and detail data is loading.\n- Mobile keeps Torrent Details collapsed by default so the persistent shell does not obscure the dashboard, but opening it exposes the same no-selection templates.\n- The desktop no-selection General template participates in the existing viewport/detail fitting contract rather than introducing a second sizing model.\n'''
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
if "Persistent no-selection Torrent Details shell" not in testing:
    testing += '''\n\n### Persistent no-selection Torrent Details shell\n\nManual regression coverage:\n\n1. Load the desktop dashboard with no torrent selected and verify Torrent Details is expanded with General, Trackers, Peers, HTTP sources, and Content tabs visible.\n2. Verify General mirrors the normal progress/Transfer/Swarm/Information structure using em-dash values and contains no instructional empty-state message.\n3. Switch through Trackers, Peers, HTTP sources, and Content with no selection; confirm structural headers/templates remain visible without fabricated torrent data.\n4. Select a torrent and confirm the interim state uses animated skeleton placeholders until detail data arrives, then replaces them with live values.\n5. Confirm a selected torrent with legitimately empty Peers/Trackers/HTTP sources still uses the existing meaningful empty-data copy for that selected torrent.\n6. On mobile, confirm Torrent Details remains collapsed by default; manually expand it with no selection and verify the same template contract.\n7. Confirm desktop viewport-proportional torrent-list sizing and General natural-fit behavior remain stable with the persistent shell present.\n'''
write("TESTING.md", testing)

meta_path = ROOT / "release_notes" / "releases.json"
data = json.loads(meta_path.read_text(encoding="utf-8"))
releases = data["releases"]
if releases[-1].get("version") != OLD:
    raise SystemExit(f"latest structured release is {releases[-1].get('version')}, expected {OLD}")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-04",
    "status": "prerelease",
    "title": "Persistent Torrent Details shell",
    "summary": "Keeps Torrent Details structurally populated when no torrent is selected, without instructional empty-state copy.",
    "highlights": [
        "Desktop now opens the no-selection Torrent Details shell by default with all existing detail tabs available.",
        "General preserves its normal progress, Transfer, Swarm, and Information structure with em-dash placeholders instead of an empty message.",
        "Trackers, Peers, HTTP sources, and Content retain their structural headers/templates without inventing torrent data.",
        "Animated skeleton placeholders are used only while a selected torrent's detail request is loading; mobile remains collapsed by default."
    ],
    "fixes": [
        "Removes the 'Select a torrent to view details.' instructional empty state and the CSS rule that hid detail tabs when no torrent was selected.",
        "Lets the no-selection General shell participate in the same desktop natural-fit sizing used by loaded General details."
    ],
    "technical": [
        "Adds shared detailTemplateMarkup/detailLoadingMarkup renderers for no-selection and selected-loading states.",
        "The desktop initial/reset state derives expansion from the 701px breakpoint; mobile keeps the dock collapsed until explicitly opened."
    ],
    "validation": [
        "The UI audit requires persistent no-selection tabs/templates, rejects the removed instructional copy, and requires loading skeleton assets.",
        "Manual coverage distinguishes no-selection placeholders from selected-but-empty torrent datasets and checks desktop/mobile behavior."
    ],
    "known_issues": [],
}
for key in ("architecture", "decisions", "next_steps"):
    if key in previous:
        entry[key] = previous[key]
releases.append(entry)
meta_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
