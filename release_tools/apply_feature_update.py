#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index_path = ROOT / 'static' / 'index.html'
app_path = ROOT / 'static' / 'app.js'
app_css_path = ROOT / 'static' / 'app.css'
settings_path = ROOT / 'static' / 'settings.js'
settings_css_path = ROOT / 'static' / 'settings.css'
sw_path = ROOT / 'static' / 'sw.js'
dash_path = ROOT / 'dashboard.py'
validator_path = ROOT / 'release_tools' / 'validate_ui_strings.py'

index = index_path.read_text(encoding='utf-8')
app = app_path.read_text(encoding='utf-8')
app_css = app_css_path.read_text(encoding='utf-8')
settings = settings_path.read_text(encoding='utf-8')
settings_css = settings_css_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
dash = dash_path.read_text(encoding='utf-8')
validator = validator_path.read_text(encoding='utf-8')

# Version and cache revision.
if 'VERSION = "0.5.11"' not in dash:
    raise SystemExit('Expected Torrent Dashboard 0.5.11 source')
dash = dash.replace('VERSION = "0.5.11"', 'VERSION = "0.5.12"', 1)
index = index.replace('?v=0.5.11', '?v=0.5.12')
sw = sw.replace('torrent-dashboard-v0511', 'torrent-dashboard-v0512').replace('?v=0.5.11', '?v=0.5.12')

# Main sidebar: Settings becomes an expandable navigation parent with category children.
old_sidebar = '''<nav>\n<button class="nav active" data-view="dashboard">Dashboard</button>\n<button class="nav" data-view="history">Transfer History</button>\n<button class="nav admin-only" data-view="settings">Settings</button>\n</nav>'''
new_sidebar = '''<nav>\n<button class="nav nav-root active" data-view="dashboard">Dashboard</button>\n<button class="nav nav-root" data-view="history">Transfer History</button>\n<div class="nav-group admin-only" id="settingsNavGroup">\n<button class="nav nav-root nav-parent" data-view="settings" id="settingsNavToggle" aria-expanded="false"><span>Settings</span><span class="nav-caret" aria-hidden="true">⌄</span></button>\n<div class="settings-subnav hidden" id="settingsSubnav">\n<button data-view="settings" data-settings-page="general" type="button">General</button>\n<button data-view="settings" data-settings-page="access" type="button">Dashboard Access</button>\n<button data-view="settings" data-settings-page="clients" type="button">Download Clients</button>\n<button data-view="settings" data-settings-page="updates" type="button">Application Updates</button>\n<button data-view="settings" data-settings-page="notifications" type="button">Notifications</button>\n<button data-view="settings" data-settings-page="integrations" type="button">Integrations</button>\n<button data-view="settings" data-settings-page="users" type="button">User Management</button>\n</div>\n</div>\n</nav>'''
if old_sidebar not in index:
    raise SystemExit('Could not locate main sidebar navigation')
index = index.replace(old_sidebar, new_sidebar, 1)

# Remove the second desktop settings menu. Mobile gets a compact selector using the same page state.
old_settings_nav = '''<div class="settings-layout">\n<nav class="settings-nav" aria-label="Settings Categories">\n<button class="active" data-settings-page="general" type="button">General</button>\n<button data-settings-page="access" type="button">Dashboard Access</button>\n<button data-settings-page="clients" type="button">Download Clients</button>\n<button data-settings-page="updates" type="button">Application Updates</button>\n<button data-settings-page="notifications" type="button">Notifications</button>\n<button data-settings-page="integrations" type="button">Integrations</button>\n<button data-settings-page="users" type="button">User Management</button>\n</nav>\n<div class="settings-content">'''
new_settings_nav = '''<div class="settings-layout">\n<label class="settings-mobile-picker">Settings category<select id="settingsMobilePage" aria-label="Settings category"><option value="general">General</option><option value="access">Dashboard Access</option><option value="clients">Download Clients</option><option value="updates">Application Updates</option><option value="notifications">Notifications</option><option value="integrations">Integrations</option><option value="users">User Management</option></select></label>\n<div class="settings-content">'''
if old_settings_nav not in index:
    raise SystemExit('Could not locate internal settings navigation')
index = index.replace(old_settings_nav, new_settings_nav, 1)

# Bulk actions stay available but no longer consume vertical layout space.
old_bulk = '<section class="bulkbar hidden" id="bulkbar"><span><b id="selectedCount">0</b> Selected</span><div><button data-bulk="start">Resume</button><button data-bulk="stop">Pause</button><button data-bulk="recheck">Recheck</button><button class="danger" data-bulk="delete">Delete</button></div></section>'
new_bulk = '<section class="bulkbar hidden" id="bulkbar" aria-live="polite"><span class="bulk-summary"><b id="selectedCount">0</b> Selected</span><div class="bulk-actions"><button data-bulk="start">Resume</button><button data-bulk="stop">Pause</button><button data-bulk="recheck">Recheck</button><button class="danger" data-bulk="delete">Delete</button><button class="bulk-clear" data-bulk-clear="1" type="button" aria-label="Clear selection" title="Clear selection">×</button></div></section>'
if old_bulk not in index:
    raise SystemExit('Could not locate bulk action bar')
index = index.replace(old_bulk, new_bulk, 1)

# Bind all actual view controls, while letting Settings children share one Settings view.
old_bind = "  $$('.nav,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));"
new_bind = "  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));"
if old_bind not in app:
    raise SystemExit('Could not locate view binding')
app = app.replace(old_bind, new_bind, 1)

old_bulk_bind = "  $('#bulkbar').addEventListener('click',e=>{const a=e.target.dataset.bulk;if(a)bulkAction(a)});"
new_bulk_bind = "  $('#bulkbar').addEventListener('click',e=>{if(e.target.closest('[data-bulk-clear]')){state.selected.clear();render();return}const a=e.target.closest('[data-bulk]')?.dataset.bulk;if(a)bulkAction(a)});"
if old_bulk_bind not in app:
    raise SystemExit('Could not locate bulk action binding')
app = app.replace(old_bulk_bind, new_bulk_bind, 1)

old_escape = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){closeDrawer();$('#addModal').classList.add('hidden')}});"
new_escape = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});"
if old_escape not in app:
    raise SystemExit('Could not locate keyboard handler')
app = app.replace(old_escape, new_escape, 1)

old_set_view = "function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));$('#pageTitle').textContent=uiText(view==='history'?'transferHistory':view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='history'?'transferAndCompletionHistory':'dashboardConfiguration');if(view==='history')loadHistory();if(view==='settings'){loadSettings().then(()=>TDSettings.loadExtras())}}"
new_set_view = "function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav'),toggle=$('#settingsNavToggle');if(!group||!submenu||!toggle)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded);toggle.setAttribute('aria-expanded',String(!!expanded))}\nfunction setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view==='history'?'transferHistory':view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='history'?'transferAndCompletionHistory':'dashboardConfiguration');if(view==='history')loadHistory();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
if old_set_view not in app:
    raise SystemExit('Could not locate setView implementation')
app = app.replace(old_set_view, new_set_view, 1)

# Settings module synchronizes nested sidebar buttons and the mobile category selector.
old_activate_tail = "    document.querySelectorAll('[data-settings-page]').forEach(el => el.classList.toggle('active', el.dataset.settingsPage === page));\n    const savebar = document.querySelector('#settingsSavebar');"
new_activate_tail = "    document.querySelectorAll('[data-settings-page]').forEach(el => el.classList.toggle('active', el.dataset.settingsPage === page));\n    const mobilePage = document.querySelector('#settingsMobilePage');\n    if (mobilePage && mobilePage.value !== page) mobilePage.value = page;\n    const savebar = document.querySelector('#settingsSavebar');"
if old_activate_tail not in settings:
    raise SystemExit('Could not locate settings activation state')
settings = settings.replace(old_activate_tail, new_activate_tail, 1)

old_settings_bind = "    document.querySelectorAll('[data-settings-page]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.settingsPage)));\n    document.querySelector('#settingsForm')?.addEventListener('submit', saveCore);"
new_settings_bind = "    document.querySelectorAll('[data-settings-page]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.settingsPage)));\n    document.querySelector('#settingsMobilePage')?.addEventListener('change', e => activate(e.target.value));\n    document.querySelector('#settingsForm')?.addEventListener('submit', saveCore);"
if old_settings_bind not in settings:
    raise SystemExit('Could not locate settings page bindings')
settings = settings.replace(old_settings_bind, new_settings_bind, 1)

# Overlay bulk actions: fixed and centered in the content area, never affecting table position.
app_css += r'''

/* 0.5.12 non-layout-shifting bulk action overlay. */
.bulkbar{position:fixed!important;top:auto!important;left:calc(50% + 110px);bottom:22px;transform:translateX(-50%);z-index:72;margin:0!important;width:max-content;max-width:calc(100vw - 270px);padding:8px 9px 8px 12px;box-shadow:0 18px 50px rgba(0,0,0,.38);border-radius:14px;background:color-mix(in srgb,var(--panel2) 96%,transparent)}
.bulkbar .bulk-summary{white-space:nowrap}.bulkbar .bulk-actions{display:flex;gap:6px;align-items:center}.bulkbar .bulk-clear{width:30px;height:30px;padding:0;display:grid;place-items:center;font-size:16px;color:var(--muted);background:transparent}.bulkbar .bulk-clear:hover{color:var(--text)}
@media(max-width:820px){.bulkbar{left:50%;bottom:calc(72px + env(safe-area-inset-bottom));max-width:calc(100vw - 18px);width:calc(100vw - 18px);justify-content:space-between;overflow-x:auto}.bulkbar .bulk-actions{flex:0 0 auto}.bulkbar button{min-height:34px}}
@media(max-width:520px){.bulkbar{padding:7px 8px}.bulkbar .bulk-summary{font-size:9px}.bulkbar button{padding:6px 8px;font-size:9px}.bulkbar .bulk-clear{width:29px}}
'''

# Settings use the full content width. Desktop categories live in the main sidebar;
# mobile gets a compact selector above the page heading.
settings_css += r'''

/* 0.5.12 main-sidebar settings navigation. */
.settings-layout{display:block!important;grid-template-columns:none!important;gap:0!important}.settings-content{width:100%;min-width:0}.settings-nav{display:none!important}.settings-mobile-picker{display:none}
.sidebar .nav-group{display:grid;gap:4px;min-width:0}.sidebar .nav-parent{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px}.sidebar .nav-caret{font-size:13px;transition:transform .16s ease;color:var(--muted)}.sidebar .nav-group.expanded .nav-caret{transform:rotate(180deg)}
.settings-subnav{display:grid;gap:2px;margin:1px 0 4px 12px;padding:3px 0 3px 10px;border-left:1px solid color-mix(in srgb,var(--border) 86%,transparent)}.settings-subnav button{width:100%;border:0;background:transparent;color:var(--muted);text-align:left;padding:7px 8px;border-radius:8px;font-size:9px;line-height:1.25}.settings-subnav button:hover{color:var(--text);background:color-mix(in srgb,var(--panel2) 72%,transparent)}.settings-subnav button.active{color:var(--text);background:var(--panel2);box-shadow:inset 2px 0 0 var(--accent)}
.settings-page-head{margin-top:0}.settings-page .settings-card{max-width:none;width:100%}
@media(max-width:820px){.settings-mobile-picker{display:grid;gap:6px;margin:0 0 12px;color:var(--muted);font-size:9px}.settings-mobile-picker select{width:100%;min-height:40px}.settings-page-head{margin-top:0}.settings-content{width:100%}}
'''

# Release audit for the new navigation and overlay behavior.
needle = '    assert "e.target.closest(\'button[data-a]\')" in app_js\n'
if needle not in validator:
    raise SystemExit('Could not locate validator insertion point')
extra = '''    assert 'id="settingsNavGroup"' in html\n    assert 'id="settingsSubnav"' in html\n    assert 'id="settingsMobilePage"' in html\n    assert 'class="settings-nav"' not in html\n    assert 'data-bulk-clear="1"' in html\n    assert "function setSettingsNavExpanded" in app_js\n    assert "state.selected.clear();render();return" in app_js\n    assert "#settingsMobilePage" in settings_js\n    assert "position:fixed!important" in app_css\n'''
validator = validator.replace(needle, needle + extra, 1)

index_path.write_text(index, encoding='utf-8')
app_path.write_text(app, encoding='utf-8')
app_css_path.write_text(app_css, encoding='utf-8')
settings_path.write_text(settings, encoding='utf-8')
settings_css_path.write_text(settings_css, encoding='utf-8')
sw_path.write_text(sw, encoding='utf-8')
dash_path.write_text(dash, encoding='utf-8')
validator_path.write_text(validator, encoding='utf-8')
print('Sidebar settings navigation and bulk overlay applied')
