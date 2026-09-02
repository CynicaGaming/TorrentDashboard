#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.73"
NEW = "0.5.74"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Dashboard top bar: keep global controls, suppress redundant dashboard title/subtitle.
html = read("static/index.html")
html = replace_once(
    html,
    '<header class="topbar">\n<div><h1 id="pageTitle">Dashboard</h1><p id="subtitle">Live Torrent Activity</p></div>',
    '<header class="topbar dashboard-mode" id="topbar">\n<div class="topbar-heading"><h1 id="pageTitle">Dashboard</h1><p id="subtitle">Live Torrent Activity</p></div>',
    "dashboard topbar markup",
)
html = html.replace(OLD, NEW)
write("static/index.html", html)


# Workspace height is now viewport-derived in both collapsed and expanded states.
js = read("static/app.js")
old_sync = re.compile(
    r"function syncTorrentWorkspaceLayout\(\)\{.*?\n\}\nwindow\.addEventListener\('resize',\(\)=>requestAnimationFrame\(syncTorrentWorkspaceLayout\)\);",
    re.S,
)
new_sync = '''function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');
  if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-workspace-height');return}
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(360,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-height')!==value)workspace.style.setProperty('--torrent-workspace-height',value);
}
window.addEventListener('resize',()=>requestAnimationFrame(syncTorrentWorkspaceLayout));'''
js, count = old_sync.subn(new_sync, js, count=1)
if count != 1:
    raise SystemExit(f"workspace sync function: expected one match, found {count}")

old_set_view = "function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator access is required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
new_set_view = "function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator access is required','error')}const settingsView=view==='settings',dashboardView=view==='dashboard';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#topbar')?.classList.toggle('dashboard-mode',dashboardView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout);if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
js = replace_once(js, old_set_view, new_set_view, "dashboard view topbar state")
js = js.replace(f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", 1)
if "--torrent-workspace-open-height" in js:
    raise SystemExit("obsolete open-only workspace height variable remains in app.js")
write("static/app.js", js)


# Replace the previous detail layout tail with the bottom-anchored client workspace.
css = read("static/app.css")
marker = "/* 0.5.73 persistent collapsible torrent details. */"
if css.count(marker) != 1:
    raise SystemExit("Could not find the v0.5.73 torrent detail layout block")
css = css.split(marker, 1)[0].rstrip() + '''\n\n/* 0.5.74 bottom-anchored client workspace. */
.topbar.dashboard-mode{justify-content:flex-end;margin-bottom:12px}
.topbar.dashboard-mode .topbar-heading{display:none}
.torrent-list-region{min-width:0;min-height:0}
@media(min-width:701px){
  .torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height,min(720px,calc(100dvh - 220px)))}
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
  .topbar.dashboard-mode{margin-bottom:14px}
}
@media(max-width:700px){
  .topbar.dashboard-mode{justify-content:flex-end;margin-bottom:10px}
  .torrent-detail-pane{position:fixed;z-index:72;left:8px;right:8px;bottom:58px;top:auto;height:min(68dvh,640px);min-height:240px;max-height:calc(100dvh - 88px);margin:0;border-radius:14px;transition:height .16s ease,min-height .16s ease}
  .torrent-detail-pane.collapsed{height:48px!important;min-height:48px!important;max-height:48px!important;top:auto!important}
  .torrent-detail-handle{min-height:48px;padding-left:14px;padding-right:14px}
  .torrent-detail-handle-label{font-size:12px}.torrent-detail-handle-selection{font-size:10.5px}
  .detail-general-grid{grid-template-columns:1fr}.torrent-detail-tabs{overflow:auto}
}
'''
write("static/app.css", css)


# Update durable interaction/design guidance.
design = read("DESIGN_LANGUAGE.md")
design += '''\n\n## Client-style dashboard chrome\n\nThe dashboard should prioritize live client state over repeated navigation labels. On the Dashboard view, the sidebar/mobile navigation already establishes location, so the redundant page title/subtitle is hidden while server, torrent-control, and account actions remain available.\n\nOn desktop and tablet, the torrent workspace occupies the actual remaining viewport. The persistent Torrent details disclosure is anchored at the bottom of that workspace in both states: collapsed it reads as a compact client-style status/disclosure bar; expanded it grows upward while the torrent list remains scrollable above it. The inspector must not float over torrent rows.\n'''
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += '''\n\n### Bottom-anchored torrent dock\n\n- On Dashboard at desktop/tablet width, verify the redundant Dashboard / Live torrent activity heading is not visible and the server/action/account controls remain aligned at the top.\n- With Torrent details collapsed, verify the disclosure bar sits at the bottom of the visible dashboard workspace rather than immediately following the last torrent row.\n- Expand Torrent details and verify it grows upward from the same bottom anchor while the torrent list remains independently scrollable above it.\n- Resize the browser and verify the collapsed and expanded dock remain bottom-aligned without covering torrent rows.\n- On mobile, verify the persistent collapsed bar remains reachable above mobile navigation and expands into the existing sheet treatment.\n'''
write("TESTING.md", testing)


# UI regression contract for v0.5.74.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace(
    'assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}" in app_css',
    'assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height,min(720px,calc(100dvh - 220px)))}" in app_css',
)
validator = validator.replace(
    'assert ".torrent-workspace.detail-expanded{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css',
    'assert ".topbar.dashboard-mode .topbar-heading{display:none}" in app_css',
)
validator = validator.replace(
    'assert "--torrent-workspace-open-height" in app_js',
    'assert "--torrent-workspace-height" in app_js',
)
late_marker = "    # 0.5.73 supersedes v0.5.72's open/close-only inspector. The dock is\n"
if late_marker not in validator:
    raise SystemExit("Could not find v0.5.73 validator contract")
insert_at = validator.index(late_marker)
validator = validator[:insert_at] + '''    # 0.5.74 anchors the persistent disclosure at the bottom of the live dashboard workspace and removes redundant dashboard chrome.\n    assert 'id="topbar"' in html and 'class="topbar dashboard-mode"' in html and 'class="topbar-heading"' in html\n    assert "$('#topbar')?.classList.toggle('dashboard-mode',dashboardView)" in app_js\n    assert "if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout)" in app_js\n    assert "--torrent-workspace-height" in app_js and "--torrent-workspace-open-height" not in app_js\n    assert "const available=Math.max(360,Math.floor(window.innerHeight-top-16))" in app_js\n    assert '0.5.74 bottom-anchored client workspace' in app_css\n    assert '.topbar.dashboard-mode{justify-content:flex-end;margin-bottom:12px}' in app_css\n    assert '.topbar.dashboard-mode .topbar-heading{display:none}' in app_css\n    assert '.torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height' in app_css\n    assert '## Client-style dashboard chrome' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert '### Bottom-anchored torrent dock' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n\n''' + validator[insert_at:]
write("release_tools/validate_ui_strings.py", validator)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

sw = read("static/sw.js")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)


# Structured release metadata; inherit durable architecture/roadmap context.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(r.get("version") == NEW for r in releases):
    raise SystemExit(f"release {NEW} already exists")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Bottom-anchored torrent details",
    "summary": "Anchors the persistent Torrent details disclosure to the bottom of the visible dashboard workspace and removes redundant Dashboard heading chrome to reclaim vertical space.",
    "highlights": [
        "Desktop and tablet torrent workspaces now measure the remaining viewport in both collapsed and expanded detail states, keeping the disclosure bar at the bottom edge like a native torrent client.",
        "Expanding Torrent details grows the inspector upward from its bottom anchor while the torrent list remains the flexible scroll region above it.",
        "The Dashboard / Live torrent activity heading is hidden on the Dashboard view because navigation already establishes location; server, torrent-control, and account actions remain visible.",
        "Other application views retain their page heading context."
    ],
    "fixes": [
        "Collapsed Torrent details no longer appears to collapse upward immediately beneath the torrent list.",
        "Reclaims vertical dashboard space previously consumed by redundant page title and subtitle text."
    ],
    "technical": [
        "syncTorrentWorkspaceLayout now computes one --torrent-workspace-height value for all non-mobile dashboard disclosure states rather than sizing only the expanded inspector.",
        "The global topbar toggles a dashboard-mode class so heading visibility is view-specific without removing headings from Settings or Notifications."
    ],
    "validation": [
        "The UI regression audit verifies the bottom-anchored workspace variable, dashboard-mode heading suppression, viewport measurement, persistent disclosure behavior, and responsive mobile treatment.",
        "Existing backend tests, source validation, JavaScript syntax checks, generated documentation checks, and release package integrity remain required."
    ],
    "known_issues": [],
}
for key in ("architecture", "decisions", "next_steps"):
    if key in previous:
        entry[key] = copy.deepcopy(previous[key])
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate public continuity/release documents deterministically.
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)

print(f"Applied Torrent Dashboard v{NEW} bottom-anchored detail dock")
