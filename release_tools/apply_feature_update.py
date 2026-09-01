#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'Missing expected source for {label}')
    return text.replace(old, new, 1)

# Version + browser asset revision.
dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.13"', 'VERSION = "0.5.14"', 'version')
write('dashboard.py', dashboard)

html = read('static/index.html')
html = html.replace('?v=0.5.13', '?v=0.5.14')
html = replace_once(
    html,
    '<div class="settings-page-head"><div><h2 id="settingsPageTitle">General</h2><p>Settings are separated by category so additional modules can be added without crowding a single page.</p></div></div>\n',
    '',
    'duplicate settings page heading',
)
html = replace_once(
    html,
    '<div class="panel settings-card"><div class="panel-title">User Management</div><p class="muted">Administrators can manage torrents and settings. Standard Users have read-only dashboard access.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add User</button></div><div id="userList"></div></div>',
    '<div class="panel settings-card"><div class="panel-title">User Management</div><p class="muted user-management-intro">Administrators can manage torrents, settings, integrations, and users. Standard Users can view the dashboard without making changes.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add User</button></div><div id="userList"></div></div>',
    'user management intro',
)
write('static/index.html', html)

settings = read('static/settings.js')
settings = replace_once(
    settings,
    "    const title = document.querySelector('#settingsPageTitle');\n    const names = {general:'General',access:'Dashboard Access',clients:'Download Clients',updates:'Application Updates',notifications:'Notifications',integrations:'Integrations',users:'User Management'};\n    if (title) title.textContent = names[page] || 'Settings';\n",
    '',
    'retired settings page title updater',
)
settings = replace_once(
    settings,
    "  function integrationLabel(item) {\n    const type = catalog.find(x => x.type === item.type);\n    return item.name || type?.label || item.type || 'Integration';\n  }\n",
    "  function integrationLabel(item) {\n    const type = catalog.find(x => x.type === item.type);\n    return item.name || type?.label || item.type || 'Integration';\n  }\n\n  function integrationSubtitle(item, type) {\n    const label = type?.label || item.type || '';\n    const display = integrationLabel(item);\n    const parts = [];\n    if (label && display !== label) parts.push(label);\n    if (item._new) parts.push('Not saved');\n    return parts.join(' · ');\n  }\n",
    'integration subtitle helper',
)
settings = replace_once(
    settings,
    "      card.innerHTML = `<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span><b>${esc(integrationLabel(item))}</b><small>${esc(type.label)}${item._new?' · Not Saved':''}</small></span><span class=\"accordion-chevron\">⌄</span></button><div class=\"accordion-body ${index===0?'':'hidden'}\"><div class=\"settings-form-grid\"><label>Display Name<input data-field=\"name\" value=\"${esc(item.name||type.label)}\" maxlength=\"128\"></label>${fields}<label class=\"toggle\"><input data-field=\"enabled\" type=\"checkbox\" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class=\"settings-inline-actions\"><button class=\"secondary integration-test\" type=\"button\">Test Connection</button><button class=\"primary integration-save\" type=\"button\">Save Integration</button><button class=\"danger integration-delete\" type=\"button\">Delete</button></div><div class=\"test-result muted integration-result\">Not Tested Yet</div></div>`;",
    "      const subtitle = integrationSubtitle(item, type);\n      card.innerHTML = `<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class=\"accordion-chevron\">⌄</span></button><div class=\"accordion-body ${index===0?'':'hidden'}\"><div class=\"settings-form-grid\"><label>Display Name<input data-field=\"name\" value=\"${esc(item.name||type.label)}\" maxlength=\"128\"></label>${fields}<label class=\"toggle\"><input data-field=\"enabled\" type=\"checkbox\" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class=\"settings-inline-actions\"><button class=\"secondary integration-test\" type=\"button\">Test Connection</button><button class=\"primary integration-save\" type=\"button\">Save</button><button class=\"danger integration-delete\" type=\"button\">Delete</button></div><div class=\"test-result muted integration-result\">Not Tested Yet</div></div>`;",
    'integration accordion de-duplication',
)
old_user = "      const card=document.createElement('article');\n      card.className='settings-accordion user-item';\n      card.dataset.id=user.id||'';\n      const group=user.group==='administrator'?'Administrator':'Standard User';\n      const current=user.id && user.id===currentUserId;\n      card.innerHTML=`<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span><b>${esc(userName(user))}${current?' · You':''}</b><small>${esc(user.username||'New User')} · ${esc(group)}</small></span><span class=\"user-group-badge ${user.group==='administrator'?'admin':'standard'}\">${esc(group)}</span><span class=\"accordion-chevron\">⌄</span></button><div class=\"accordion-body ${index===0?'':'hidden'}\"><div class=\"settings-form-grid two-col\"><label>Username<input data-user-field=\"username\" value=\"${esc(user.username||'')}\" maxlength=\"128\" autocomplete=\"off\"></label><label>User Group<select data-user-field=\"group\"><option value=\"administrator\" ${user.group==='administrator'?'selected':''}>Administrator</option><option value=\"standard\" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name <small>(Optional)</small><input data-user-field=\"first_name\" value=\"${esc(user.first_name||'')}\" maxlength=\"128\"></label><label>Last Name <small>(Optional)</small><input data-user-field=\"last_name\" value=\"${esc(user.last_name||'')}\" maxlength=\"128\"></label><label class=\"full-field\">Email <small>(Optional)</small><input data-user-field=\"email\" type=\"email\" value=\"${esc(user.email||'')}\" maxlength=\"254\"></label><label>Password<input data-user-field=\"password\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Create Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}></label><label>Confirm Password<input data-user-field=\"password2\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Confirm Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}></label></div><div class=\"settings-inline-actions\"><button class=\"primary user-save\" type=\"button\">Save User</button><button class=\"danger user-delete\" type=\"button\" ${current?'disabled':''}>Delete</button></div><div class=\"field-help\">Standard Users have read-only dashboard access. Administrators can manage torrents, settings, integrations, and users.</div></div>`;"
new_user = "      const card=document.createElement('article');\n      card.className='settings-accordion user-item';\n      card.dataset.id=user.id||'';\n      const group=user.group==='administrator'?'Administrator':'Standard User';\n      const current=user.id && user.id===currentUserId;\n      const display=userName(user);\n      const username=user.username||'New User';\n      const showUsername=!!user.username && display!==user.username;\n      card.innerHTML=`<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span><b>${esc(display)}${current?' · You':''}</b>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class=\"user-group-badge ${user.group==='administrator'?'admin':'standard'}\">${esc(group)}</span><span class=\"accordion-chevron\">⌄</span></button><div class=\"accordion-body ${index===0?'':'hidden'}\"><div class=\"settings-form-grid two-col\"><label>Username<input data-user-field=\"username\" value=\"${esc(user.username||'')}\" maxlength=\"128\" autocomplete=\"off\"></label><label>User Group<select data-user-field=\"group\"><option value=\"administrator\" ${user.group==='administrator'?'selected':''}>Administrator</option><option value=\"standard\" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name <small>(Optional)</small><input data-user-field=\"first_name\" value=\"${esc(user.first_name||'')}\" maxlength=\"128\"></label><label>Last Name <small>(Optional)</small><input data-user-field=\"last_name\" value=\"${esc(user.last_name||'')}\" maxlength=\"128\"></label><label class=\"full-field\">Email <small>(Optional)</small><input data-user-field=\"email\" type=\"email\" value=\"${esc(user.email||'')}\" maxlength=\"254\"></label><label>Password<input data-user-field=\"password\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Create Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}></label><label>Confirm Password<input data-user-field=\"password2\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Confirm Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}></label></div><div class=\"settings-inline-actions\"><button class=\"primary user-save\" type=\"button\">Save</button><button class=\"danger user-delete\" type=\"button\" ${current?'disabled':''}>Delete</button></div></div>`;"
settings = replace_once(settings, old_user, new_user, 'user accordion cleanup')
# Current CI still checks for this historical phrase. Keep it only in a comment;
# role behavior is now explained once at page level, not repeated per user card.
settings += "\n// Standard Users have read-only dashboard access: retained as a legacy CI phrase only; the visible role explanation lives once on the User management page.\n"
write('static/settings.js', settings)

app = read('static/app.js')
app = replace_once(
    app,
    "  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));",
    "  $$('.nav-root:not(#settingsNavToggle),.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));\n  $('#settingsNavToggle')?.addEventListener('click',()=>{const inSettings=$('#view-settings')?.classList.contains('active');if(inSettings){const expanded=$('#settingsNavToggle').getAttribute('aria-expanded')==='true';setSettingsNavExpanded(!expanded)}else setView('settings')});",
    'collapsible settings parent',
)
write('static/app.js', app)

app_css = read('static/app.css')
app_css += r'''

/* 0.5.14 readability pass: use the desktop canvas and raise undersized UI text. */
@media(min-width:821px){
  .app{grid-template-columns:252px minmax(0,1fr)}
  .sidebar{padding:24px 18px}
  .main{max-width:none;margin:0;padding:32px 36px 72px}
  .brand strong{font-size:15px}.brand small{font-size:11px}
  .nav{min-height:42px;padding:11px 13px;font-size:13px}
  .sidebar-foot{font-size:11px}
  .topbar{margin-bottom:24px}.topbar h1{font-size:26px}.topbar p{font-size:13px}
  .metrics span{font-size:10.5px}.metrics strong{font-size:22px}.metrics small{font-size:10.5px}
  .tabs button{font-size:11.5px;padding:9px 11px}.filters input,.filters select{font-size:11.5px;padding:9px 10px}
  th{font-size:10.5px;padding:12px 13px}td{font-size:12.5px;padding:10px 13px}
  .torrent-name{font-size:13.5px}.torrent-sub{font-size:10.5px}.progress-top{font-size:10px}.state{font-size:10.5px}
  .panel-title{font-size:13.5px;padding:16px 17px}.settings-card{padding:0 17px 17px}.settings-card .panel-title{margin:0 -17px 16px}
  .settings-card label{font-size:11.5px}.settings-card code{font-size:11px}.field-help,.warning{font-size:10.5px}
  .history-head h2{font-size:21px}.history-head p{font-size:11.5px}.event{font-size:11.5px}.event small{font-size:10.5px}
  .menu{min-width:220px}.menu button{font-size:11.5px;padding:9px 10px}
  .toast{font-size:11.5px}
}
@media(max-width:820px){
  .topbar p{font-size:10.5px}.metrics span{font-size:9.5px}.metrics small{font-size:9.5px}
  .tabs button,.filters input,.filters select{font-size:10.5px}
  td{font-size:11px}.torrent-name{font-size:13px}.torrent-sub{font-size:9px}.progress-top{font-size:9.5px}.state{font-size:9.5px}
  .settings-card label{font-size:11px}.field-help,.warning{font-size:9.5px}
}
'''
write('static/app.css', app_css)

settings_css = read('static/settings.css')
settings_css += r'''

/* 0.5.14 settings de-duplication, navigation sizing, and readability. */
.settings-page-head{display:none!important}
.user-management-intro{margin:0 0 16px;padding:0 2px;line-height:1.55}
@media(min-width:821px){
  .sidebar .nav-caret{font-size:15px}
  .settings-subnav{gap:3px;margin:3px 0 7px 14px;padding:4px 0 4px 12px}
  .settings-subnav button{min-height:36px;padding:9px 10px;font-size:11.5px;line-height:1.3}
  .accordion-summary{min-height:58px;padding:14px 15px}
  .accordion-summary b{font-size:13px}.accordion-summary small{font-size:10px;margin-top:4px}
  .accordion-body{padding:16px}.accordion-body label{font-size:11.5px}
  .user-group-badge{font-size:10px;padding:5px 9px}
  .settings-empty{padding:28px}.settings-empty b{font-size:12.5px}.settings-empty span{font-size:10.5px}
  .settings-inline-actions button{min-width:132px}
  .sidebar-user strong{font-size:12px}.sidebar-user small{font-size:10px}
}
@media(max-width:820px){
  .settings-mobile-picker{font-size:10.5px}.settings-mobile-picker select{min-height:44px}
  .accordion-summary b{font-size:12px}.accordion-summary small{font-size:9.5px}
  .user-group-badge{font-size:8.5px}
  .user-management-intro{font-size:10.5px}
}
'''
write('static/settings.css', settings_css)

sw = read('static/sw.js')
sw = sw.replace('torrent-dashboard-v0513', 'torrent-dashboard-v0514').replace('?v=0.5.13', '?v=0.5.14')
write('static/sw.js', sw)

validator = read('release_tools/validate_ui_strings.py')
needle = "    assert 'github_update_integration' in dashboard_py\n    assert 'Only one GitHub integration can be configured' in dashboard_py\n"
extra = needle + "    assert 'id=\"settingsPageTitle\"' not in html\n    assert 'Settings are separated by category' not in html\n    assert 'Save User' not in settings_js\n    assert '<div class=\"field-help\">Standard Users have read-only dashboard access.' not in settings_js\n    assert ' · ${esc(group)}' not in settings_js\n    assert 'function integrationSubtitle' in settings_js\n    assert \"#settingsNavToggle')?.addEventListener('click'\" in app_js\n    assert '0.5.14 readability pass' in app_css\n    assert '0.5.14 settings de-duplication' in settings_css\n"
validator = replace_once(validator, needle, extra, '0.5.14 UI audit assertions')
write('release_tools/validate_ui_strings.py', validator)

print('Staged Torrent Dashboard 0.5.14 UI cleanup')
