#!/usr/bin/env python3
from __future__ import annotations
import copy, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD='0.5.73'; NEW='0.5.74'
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def one(s,a,b,label):
    if s.count(a)!=1: raise SystemExit(f'{label}: expected one match, found {s.count(a)}')
    return s.replace(a,b,1)

# Dashboard chrome.
html=read('static/index.html')
html=one(html,'<header class="topbar">\n<div><h1 id="pageTitle">Dashboard</h1><p id="subtitle">Live Torrent Activity</p></div>','<header class="topbar dashboard-mode" id="topbar">\n<div class="topbar-heading"><h1 id="pageTitle">Dashboard</h1><p id="subtitle">Live Torrent Activity</p></div>','topbar')
html=html.replace(OLD,NEW)
write('static/index.html',html)

# Bottom-anchored workspace and view-specific topbar state.
js=read('static/app.js')
js,n=re.subn(r"function syncTorrentWorkspaceLayout\(\)\{.*?\n\}\nwindow\.addEventListener\('resize',\(\)=>requestAnimationFrame\(syncTorrentWorkspaceLayout\)\);",'''function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-workspace-height');return}
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(360,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-height')!==value)workspace.style.setProperty('--torrent-workspace-height',value);
}
window.addEventListener('resize',()=>requestAnimationFrame(syncTorrentWorkspaceLayout));''',js,count=1,flags=re.S)
if n!=1: raise SystemExit('workspace layout function not replaced')
old="function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator access is required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
new="function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator access is required','error')}const settingsView=view==='settings',dashboardView=view==='dashboard';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#topbar')?.classList.toggle('dashboard-mode',dashboardView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout);if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
js=one(js,old,new,'setView')
js=js.replace(f"const FRONTEND_BUILD='{OLD}';",f"const FRONTEND_BUILD='{NEW}';",1)
write('static/app.js',js)

# Replace the current detail-layout tail.
css=read('static/app.css'); marker='/* 0.5.73 persistent collapsible torrent details. */'
if css.count(marker)!=1: raise SystemExit('v0.5.73 CSS marker missing')
css=css.split(marker,1)[0].rstrip()+'''\n\n/* 0.5.74 bottom-anchored client workspace. */
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
write('static/app.css',css)

# Durable design/testing guidance.
design=read('DESIGN_LANGUAGE.md')
if '## Client-style dashboard chrome' not in design:
    design+='''\n\n## Client-style dashboard chrome\n\nOn the Dashboard view, navigation already establishes location, so the redundant Dashboard title/subtitle is hidden while server, torrent-control, and account actions remain visible. On desktop/tablet, the torrent workspace fills the actual remaining viewport so the persistent Torrent details disclosure stays anchored to the bottom. Collapsed it reads as a compact client-style bar; expanded it grows upward while the torrent list scrolls above it.\n'''
write('DESIGN_LANGUAGE.md',design)
testing=read('TESTING.md')
if '### Bottom-anchored torrent dock' not in testing:
    testing+='''\n\n### Bottom-anchored torrent dock\n\n- Verify Dashboard / Live torrent activity is not visible on Dashboard while top-right controls remain available.\n- With details collapsed, verify the disclosure bar sits at the bottom of the visible dashboard workspace.\n- Expand details and verify the inspector grows upward from the same anchor while the torrent list scrolls above it.\n- Resize desktop/tablet and verify both states remain bottom-aligned without overlaying torrent rows.\n- Verify mobile retains the persistent collapsed bar above mobile navigation and expands into the sheet.\n'''
write('TESTING.md',testing)

# Update superseded UI contracts and add the new one.
v=read('release_tools/validate_ui_strings.py')
v=v.replace('assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}" in app_css','assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height,min(720px,calc(100dvh - 220px)))}" in app_css')
v=v.replace('assert ".torrent-workspace.detail-expanded{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css','assert ".topbar.dashboard-mode .topbar-heading{display:none}" in app_css')
v=v.replace('assert "--torrent-workspace-open-height" in app_js','assert "--torrent-workspace-height" in app_js')
v=v.replace("assert '0.5.73 persistent collapsible torrent details' in app_css","assert '0.5.74 bottom-anchored client workspace' in app_css")
needle="    # 0.5.73 supersedes v0.5.72's open/close-only inspector. The dock is\n"
if needle not in v: raise SystemExit('late inspector validator marker missing')
pos=v.index(needle)
extra='''    # 0.5.74 bottom-anchors the persistent disclosure and removes redundant Dashboard chrome.\n    assert 'id="topbar"' in html and 'class="topbar dashboard-mode"' in html and 'class="topbar-heading"' in html\n    assert "$('#topbar')?.classList.toggle('dashboard-mode',dashboardView)" in app_js\n    assert "if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout)" in app_js\n    assert "--torrent-workspace-height" in app_js and "--torrent-workspace-open-height" not in app_js\n    assert "const available=Math.max(360,Math.floor(window.innerHeight-top-16))" in app_js\n    assert '.topbar.dashboard-mode{justify-content:flex-end;margin-bottom:12px}' in app_css\n    assert '.topbar.dashboard-mode .topbar-heading{display:none}' in app_css\n    assert '## Client-style dashboard chrome' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert '### Bottom-anchored torrent dock' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n\n'''
v=v[:pos]+extra+v[pos:]
write('release_tools/validate_ui_strings.py',v)

# Version/cache synchronization.
d=read('dashboard.py'); d=one(d,f'VERSION = "{OLD}"',f'VERSION = "{NEW}"','dashboard version'); write('dashboard.py',d)
sw=read('static/sw.js')
sw=re.sub(r"const CACHE='torrent-dashboard-v\d+';", "const CACHE='torrent-dashboard-v0574';", sw, count=1)
sw=sw.replace('v=0.5.73','v=0.5.74')
write('static/sw.js',sw)

# Release metadata and generated continuity files.
p=ROOT/'release_notes/releases.json'; meta=json.loads(p.read_text(encoding='utf-8')); rel=meta['releases']
if any(x.get('version')==NEW for x in rel): raise SystemExit('v0.5.74 already authored')
prev=rel[-1]
e={
 'version':NEW,'date':'2026-09-02','status':'prerelease','title':'Bottom-anchored torrent details',
 'summary':'Anchors the persistent Torrent details disclosure to the bottom of the visible dashboard workspace and removes redundant Dashboard heading chrome to reclaim vertical space.',
 'highlights':['Desktop and tablet torrent workspaces now use the actual remaining viewport in both collapsed and expanded states, keeping Torrent details anchored to the bottom like a native client.','Expanding Torrent details grows upward while the torrent list remains the flexible scroll region above it.','The redundant Dashboard / Live torrent activity heading is hidden on Dashboard while server, torrent-control, and account actions remain visible.','Other views retain their page headings.'],
 'fixes':['Collapsed Torrent details no longer appears immediately beneath the last torrent row.','Reclaims vertical dashboard space previously consumed by duplicated page-location text.'],
 'technical':['syncTorrentWorkspaceLayout now computes a shared --torrent-workspace-height for all desktop/tablet disclosure states.','The topbar uses a dashboard-mode class so heading visibility is view-specific.'],
 'validation':['UI regression checks cover bottom anchoring, dashboard heading suppression, viewport measurement, persistent disclosure behavior, and mobile treatment.','Existing backend tests, source validation, JavaScript syntax checks, generated documentation checks, and package-integrity gates remain required.'],
 'known_issues':[]}
for k in ('architecture','decisions','next_steps'):
    if k in prev: e[k]=copy.deepcopy(prev[k])
rel.append(e); p.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
subprocess.run(['python','release_tools/generate_release_notes.py','--version',NEW],cwd=ROOT,check=True)
print('Applied Torrent Dashboard v0.5.74 bottom-anchored client workspace')
