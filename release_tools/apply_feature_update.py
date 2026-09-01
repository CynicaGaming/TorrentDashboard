#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


# Version.
dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.14"', 'VERSION = "0.5.15"', 'dashboard version')
write('dashboard.py', dashboard)

# HTML navigation, notification center, settings parent, removal dialog, asset revisions.
html = read('static/index.html')
html = html.replace('?v=0.5.14', '?v=0.5.15')
html = replace_once(
    html,
    '<button class="nav nav-root" data-view="history">Transfer History</button>',
    '<button class="nav nav-root" data-view="notifications">Notifications</button>',
    'desktop notifications nav',
)
html = replace_once(
    html,
    '<button class="nav nav-root nav-parent" data-view="settings" id="settingsNavToggle" aria-expanded="false"><span>Settings</span><span class="nav-caret" aria-hidden="true">⌄</span></button>',
    '<button class="nav nav-root nav-parent" data-view="settings" id="settingsNavToggle"><span>Settings</span></button>',
    'settings parent button',
)
old_history = '''<section class="view" id="view-history">
<div class="history-head"><div><h2>Transfer History</h2><p>Persistent dashboard samples and completion events.</p></div><select id="historyRange"><option value="60">1 Hour</option><option value="360">6 Hours</option><option value="1440">24 Hours</option><option value="10080">7 Days</option></select></div>
<section class="metrics compact"><article><span>Seven Day Average</span><strong id="aAvg">—</strong></article><article><span>Seven Day Peak</span><strong id="aPeak">—</strong></article><article><span>Known Torrents</span><strong id="aKnown">—</strong></article><article><span>Completed</span><strong id="aComplete">—</strong></article></section>
<section class="panel chart-panel"><canvas height="220" id="speedChart"></canvas></section>
<section class="panel"><div class="panel-title">Recent Events</div><div class="event-list" id="eventList"></div></section>
</section>'''
new_notifications = '''<section class="view" id="view-notifications">
<section class="panel notification-center">
<div class="notification-toolbar"><div><strong>Recent activity</strong><span>Torrent completions, account activity, updates, integrations, and dashboard events.</span></div><div class="notification-toolbar-actions"><select id="notificationFilter" aria-label="Notification category"><option value="all">All activity</option><option value="torrents">Torrents</option><option value="system">System</option><option value="security">Security</option><option value="updates">Updates</option></select><button class="secondary" id="refreshNotifications" type="button">Refresh</button></div></div>
<div class="notification-list" id="notificationList"></div>
</section>
</section>'''
html = replace_once(html, old_history, new_notifications, 'history view')
html = replace_once(
    html,
    '<nav class="mobile-nav"><button class="active" data-view="dashboard">Dashboard</button><button data-view="history">Transfer History</button><button class="admin-only" data-view="settings">Settings</button></nav>',
    '<nav class="mobile-nav"><button class="active" data-view="dashboard">Dashboard</button><button data-view="notifications">Notifications</button><button class="admin-only" data-view="settings">Settings</button></nav>',
    'mobile notifications nav',
)
remove_modal = '''<div class="modal hidden" id="removeModal"><div class="modal-backdrop" data-remove-cancel=""></div><form class="modal-card remove-modal-card" id="removeForm"><header><div><h2>Remove torrent(s)</h2><p>Remove torrents from qBitTorrent.</p></div><button class="icon-btn" data-remove-cancel="" type="button" aria-label="Cancel removal">×</button></header><div class="remove-dialog-body"><div class="remove-warning-row"><div class="remove-warning-icon" aria-hidden="true">!</div><div class="remove-warning-copy"><strong id="removePrompt">Are you sure you want to remove this torrent from the transfer list?</strong><p>This action removes the selected torrent from qBitTorrent. Downloaded files are kept unless you choose otherwise below.</p></div></div><div class="remove-target-list hidden" id="removeTargets"></div><label class="remove-files-option"><input id="removeFiles" type="checkbox"/><span>Also delete the downloaded files</span></label></div><footer class="remove-dialog-actions"><button class="danger remove-confirm" type="submit">Remove</button><button class="secondary" data-remove-cancel="" type="button">Cancel</button></footer></form></div>
'''
html = replace_once(html, '<div class="menu hidden" id="menu">', remove_modal + '<div class="menu hidden" id="menu">', 'remove modal insertion')
write('static/index.html', html)

# JavaScript behavior.
js = read('static/app.js')
js = replace_once(js, 'updateInfo:null};', 'updateInfo:null,notificationEvents:[]};', 'notification state')
js = replace_once(
    js,
    "  $$('.nav-root:not(#settingsNavToggle),.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));\n  $('#settingsNavToggle')?.addEventListener('click',()=>{const inSettings=$('#view-settings')?.classList.contains('active');if(inSettings){const expanded=$('#settingsNavToggle').getAttribute('aria-expanded')==='true';setSettingsNavExpanded(!expanded)}else setView('settings')});",
    "  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));",
    'settings navigation binding',
)
js = replace_once(
    js,
    "  $('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;state.selected.clear();await refreshStatus();if(!['all'].includes(state.server))await loadMeta()});",
    "  $('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;state.selected.clear();await refreshStatus();if(!['all'].includes(state.server))await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});",
    'server selector notifications refresh',
)
js = replace_once(
    js,
    "  $('#historyRange').addEventListener('change',loadHistory);",
    "  $('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',loadNotifications);",
    'notification controls binding',
)
js = replace_once(
    js,
    "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});",
    "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});",
    'escape handling',
)
js = replace_once(
    js,
    "  $('#addBtn').addEventListener('click',()=>$('#addModal').classList.remove('hidden'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));$('#addForm').addEventListener('submit',addTorrent);",
    "  $('#addBtn').addEventListener('click',()=>$('#addModal').classList.remove('hidden'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));$('#addForm').addEventListener('submit',addTorrent);$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));",
    'remove modal binding',
)
js = replace_once(
    js,
    "function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav'),toggle=$('#settingsNavToggle');if(!group||!submenu||!toggle)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded);toggle.setAttribute('aria-expanded',String(!!expanded))}",
    "function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav');if(!group||!submenu)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded)}",
    'settings submenu state',
)
old_set_view = "function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view==='history'?'transferHistory':view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='history'?'transferAndCompletionHistory':'dashboardConfiguration');if(view==='history')loadHistory();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
new_set_view = "function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}"
js = replace_once(js, old_set_view, new_set_view, 'setView notifications')

old_context_delete = '''    if(a==='delete'){
      const files=confirm('Also delete downloaded files?\\
Cancel = keep files.');
      if(!confirm(`Remove ${t.name} from Torrent Dashboard?`))return;
      return doAction('delete',{server:sid,hashes:[h],delete_files:files});
    }'''
js = replace_once(js, old_context_delete, "    if(a==='delete')return removeTorrentTargets([{server:sid,hash:h,name:t.name||h}]);", 'context delete')

old_bulk = "async function bulkAction(a){let grouped={};for(const k of state.selected){let [sid,...rest]=k.split(':');(grouped[sid]??=[]).push(rest.join(':'))}if(a==='delete'&&!confirm(`Delete ${state.selected.size} selected torrents? Downloaded files will be kept.`))return;for(const [sid,hashes]of Object.entries(grouped))await doAction(a,{server:sid,hashes,delete_files:false});state.selected.clear();render()}"
new_bulk = "async function bulkAction(a){if(a==='delete'){const targets=[...state.selected].map(k=>{let [sid,...rest]=k.split(':');const hash=rest.join(':');const t=state.torrents.find(x=>(x._server_id||state.server)===sid&&x.hash===hash);return{server:sid,hash,name:t?.name||hash}});const removed=await removeTorrentTargets(targets);if(removed){state.selected.clear();render()}return}let grouped={};for(const k of state.selected){let [sid,...rest]=k.split(':');(grouped[sid]??=[]).push(rest.join(':'))}for(const [sid,hashes]of Object.entries(grouped))await doAction(a,{server:sid,hashes});state.selected.clear();render()}"
js = replace_once(js, old_bulk, new_bulk, 'bulk delete')
old_detail_delete = "if(a==='delete'){let files=confirm('Delete downloaded files too?');if(confirm('Confirm torrent deletion?')){await doAction(a,{server,hashes:[hash],delete_files:files});closeDrawer()}return}"
new_detail_delete = "if(a==='delete'){const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);if(await removeTorrentTargets([{server,hash,name:t?.name||hash}]))closeDrawer();return}"
js = replace_once(js, old_detail_delete, new_detail_delete, 'detail delete')

remove_helpers = r'''
let removeDialogResolve=null;
function closeRemoveDialog(result=null){const modal=$('#removeModal');if(modal)modal.classList.add('hidden');const resolve=removeDialogResolve;removeDialogResolve=null;if(resolve)resolve(result)}
function showRemoveDialog(targets){targets=(targets||[]).filter(x=>x&&x.hash);if(!targets.length)return Promise.resolve(null);if(removeDialogResolve)closeRemoveDialog(null);const one=targets.length===1;const name=targets[0]?.name||targets[0]?.hash||'this torrent';$('#removePrompt').textContent=one?`Are you sure you want to remove “${name}” from the transfer list?`:`Are you sure you want to remove ${targets.length} torrents from the transfer list?`;const list=$('#removeTargets');if(list){if(one){list.classList.add('hidden');list.innerHTML=''}else{const shown=targets.slice(0,6);list.innerHTML=shown.map(x=>`<div>${esc(x.name||x.hash)}</div>`).join('')+(targets.length>shown.length?`<small>+${targets.length-shown.length} more</small>`:'');list.classList.remove('hidden')}}const files=$('#removeFiles');if(files)files.checked=false;$('#removeModal').classList.remove('hidden');return new Promise(resolve=>{removeDialogResolve=resolve;setTimeout(()=>$('#removeForm .remove-confirm')?.focus(),0)})}
async function removeTorrentTargets(targets){const choice=await showRemoveDialog(targets);if(!choice)return false;const grouped={};for(const item of targets){(grouped[item.server]??=[]).push(item.hash)}for(const [server,hashes] of Object.entries(grouped))await doAction('delete',{server,hashes,delete_files:!!choice.deleteFiles});return true}

'''
js = replace_once(js, 'async function doAction(action,payload={})', remove_helpers + 'async function doAction(action,payload={})', 'remove helpers insertion')

notification_functions = r'''function notificationCategory(item){const event=String(item?.event||'').toLowerCase();if(event==='completed'||event==='torrent_upload'||event.startsWith('action:'))return'torrents';if(event.startsWith('login_')||event.startsWith('user_')||event==='setup_completed')return'security';if(event.startsWith('update_'))return'updates';return'system'}
function notificationPresentation(item){const event=String(item?.event||'').toLowerCase(),category=notificationCategory(item);let title='',message='',tone='neutral';if(event==='completed'){title='Torrent completed';message=`${item.name||'Torrent'} finished downloading${item.server_id&&item.server_id!=='dashboard'?` on ${item.server_id}`:''}.`;tone='good'}else if(event==='torrent_upload'){title='Torrent added';message=item.name?`${item.name} was added to ${item.server_id||'qBitTorrent'}.`:'A torrent was added.';tone='good'}else if(event.startsWith('action:')){const action=event.split(':',2)[1]||'action';const labels={delete:'Torrent removed',start:'Torrent resumed',stop:'Torrent paused',recheck:'Torrent rechecked',reannounce:'Torrent reannounced',rename:'Torrent renamed',set_location:'Torrent location changed',set_category:'Torrent category changed'};title=labels[action]||uiText(`torrent ${action}`);message=`Action sent${item.server_id&&item.server_id!=='dashboard'?` to ${item.server_id}`:''}${item.name?` by ${item.name}`:''}.`;tone=action==='delete'?'warn':'neutral'}else if(event==='login_failed'){title='Failed sign-in';message=`A sign-in attempt failed${item.name?` for ${item.name}`:''}.`;tone='bad'}else if(event==='login_success'){title='Signed in';message=`${item.name||'A user'} signed in to Torrent Dashboard.`;tone='good'}else if(event==='setup_completed'){title='Setup completed';message='Torrent Dashboard first-run setup was completed.';tone='good'}else if(event==='user_saved'){title='User saved';message=`${item.name||'A user account'} was updated.`}else if(event==='user_deleted'){title='User deleted';message='A dashboard user was removed.';tone='warn'}else if(event==='integration_saved'){title='Integration saved';message=`${item.name||'An integration'} was updated.`}else if(event==='integration_deleted'){title='Integration deleted';message='An integration was removed.';tone='warn'}else if(event==='settings_changed'){title='Settings changed';message=`Dashboard settings were updated${item.name?` by ${item.name}`:''}.`}else if(event==='update_downloaded'){title='Update downloaded';message=item.name?`Version ${item.name} is ready to install.`:'An application update was downloaded.';tone='good'}else if(event==='update_install_started'){title='Update installation started';message=item.name?`Torrent Dashboard is installing version ${item.name}.`:'Torrent Dashboard is installing an update.';tone='good'}else if(event==='notification_sound_changed'){title='Notification sound changed';message=item.name?`${item.name} is now configured.`:'The custom notification sound was changed.'}else{title=uiText(event||'dashboardEvent');message=[item.server_id&&item.server_id!=='dashboard'?item.server_id:'',item.name||''].filter(Boolean).join(' · ')||'Torrent Dashboard recorded an event.'}return{category,title,message,tone}}
function renderNotifications(){const list=$('#notificationList');if(!list)return;const filter=$('#notificationFilter')?.value||'all';let items=(state.notificationEvents||[]).filter(x=>state.server==='all'||x.server_id===state.server||x.server_id==='dashboard');if(filter!=='all')items=items.filter(x=>notificationCategory(x)===filter);if(!items.length){list.innerHTML=`<div class="empty"><strong>${uiText('noNotificationsYet')}</strong><span>${uiText('dashboardActivityWillAppearHere')}</span></div>`;return}list.innerHTML=items.map(item=>{const view=notificationPresentation(item);return`<article class="notification-item ${esc(view.tone)}"><span class="notification-dot" aria-hidden="true"></span><div class="notification-copy"><div class="notification-title"><b>${esc(view.title)}</b><span>${esc(uiText(view.category))}</span></div><p>${esc(view.message)}</p></div><time title="${esc(when(item.ts))}">${esc(rel(item.ts))}</time></article>`}).join('')}
async function loadNotifications(){try{const d=await api('/api/events?limit=200');state.notificationEvents=d.events||[];renderNotifications()}catch(err){toast(err.message,'error')}}'''
pattern = re.compile(r"async function loadHistory\(\)\{.*?\n\nfunction renderServerSettings", re.S)
match = pattern.search(js)
if not match:
    raise RuntimeError('history functions block not found')
js = js[:match.start()] + notification_functions + '\n\nfunction renderServerSettings' + js[match.end():]

write('static/app.js', js)

# Styles for the qBitTorrent-inspired removal dialog and activity-oriented notifications page.
css = read('static/app.css')
css += r'''

/* 0.5.15 removal dialog and notification center. */
.remove-modal-card{width:min(640px,calc(100% - 24px));padding-bottom:0}.remove-modal-card header p{margin:4px 0 0;color:var(--muted);font-size:11px}.remove-dialog-body{padding:20px}.remove-warning-row{display:grid;grid-template-columns:42px minmax(0,1fr);gap:14px;align-items:start}.remove-warning-icon{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:color-mix(in srgb,var(--warn) 14%,var(--panel3));border:1px solid color-mix(in srgb,var(--warn) 42%,var(--border));color:var(--warn);font-size:22px;font-weight:800}.remove-warning-copy strong{display:block;font-size:14px;line-height:1.45}.remove-warning-copy p{margin:7px 0 0;color:var(--muted);font-size:11px;line-height:1.55}.remove-target-list{margin:14px 0 0 56px;max-height:142px;overflow:auto;padding:9px 11px;border:1px solid var(--border);border-radius:10px;background:var(--panel3);font-size:10.5px}.remove-target-list div{padding:3px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.remove-target-list small{display:block;margin-top:4px;color:var(--muted)}.remove-files-option{display:flex!important;align-items:center;gap:9px;margin:18px 0 0 56px!important;padding:11px 12px;border:1px solid var(--border);border-radius:10px;background:var(--panel3);color:var(--text)!important;font-size:11px!important}.remove-files-option input{width:auto!important;margin:0}.remove-dialog-actions{display:flex;justify-content:flex-end;gap:8px;padding:14px 18px;border-top:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 58%,transparent)}.remove-dialog-actions button{min-width:96px}.remove-confirm{color:#ffdada!important;background:color-mix(in srgb,var(--bad) 14%,var(--panel3))!important}.notification-center{overflow:hidden}.notification-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 18px;border-bottom:1px solid var(--border)}.notification-toolbar>div:first-child{display:grid;gap:4px}.notification-toolbar strong{font-size:14px}.notification-toolbar span{color:var(--muted);font-size:10.5px;line-height:1.45}.notification-toolbar-actions{display:flex;gap:8px;align-items:center}.notification-toolbar-actions select{min-width:150px}.notification-list{display:grid}.notification-item{display:grid;grid-template-columns:9px minmax(0,1fr) auto;gap:12px;align-items:start;padding:14px 18px;border-bottom:1px solid color-mix(in srgb,var(--border) 70%,transparent)}.notification-item:last-child{border-bottom:0}.notification-dot{width:8px;height:8px;border-radius:50%;margin-top:5px;background:var(--muted)}.notification-item.good .notification-dot{background:var(--good)}.notification-item.warn .notification-dot{background:var(--warn)}.notification-item.bad .notification-dot{background:var(--bad)}.notification-copy{min-width:0}.notification-title{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.notification-title b{font-size:12px}.notification-title span{display:inline-flex;padding:3px 6px;border:1px solid var(--border);border-radius:999px;color:var(--muted);font-size:8.5px}.notification-copy p{margin:5px 0 0;color:var(--muted);font-size:10.5px;line-height:1.45}.notification-item time{color:var(--muted);font-size:9.5px;white-space:nowrap;padding-top:2px}
@media(max-width:700px){.remove-dialog-body{padding:16px}.remove-warning-row{grid-template-columns:36px minmax(0,1fr);gap:11px}.remove-warning-icon{width:34px;height:34px;font-size:19px}.remove-warning-copy strong{font-size:12.5px}.remove-target-list,.remove-files-option{margin-left:47px!important}.remove-dialog-actions{padding:12px 14px}.remove-dialog-actions button{flex:1;min-height:42px}.notification-toolbar{align-items:stretch;flex-direction:column;padding:14px}.notification-toolbar-actions{display:grid;grid-template-columns:minmax(0,1fr) auto}.notification-toolbar-actions select{min-width:0;width:100%}.notification-item{grid-template-columns:8px minmax(0,1fr);gap:10px;padding:13px 14px}.notification-item time{grid-column:2;margin-top:2px}.notification-title b{font-size:11.5px}.notification-copy p{font-size:10px}}
@media(max-width:480px){.remove-target-list,.remove-files-option{margin-left:0!important}.remove-files-option{margin-top:14px!important}.notification-toolbar-actions{grid-template-columns:1fr}.notification-toolbar-actions button{width:100%}}
'''
write('static/app.css', css)

# Service worker revisions.
sw = read('static/sw.js')
sw = replace_once(sw, "torrent-dashboard-v0514", "torrent-dashboard-v0515", 'service worker cache')
sw = sw.replace('0.5.14', '0.5.15')
write('static/sw.js', sw)

# Extend release UI audit to protect the new interaction contracts.
validator = read('release_tools/validate_ui_strings.py')
validator = validator.replace("    assert \"#settingsNavToggle')?.addEventListener('click'\" in app_js\n", "")
marker = "    assert '0.5.14 settings de-duplication' in settings_css\n"
addition = """    assert '0.5.14 settings de-duplication' in settings_css
    assert 'data-view=\"history\"' not in html
    assert 'Transfer History' not in html
    assert 'data-view=\"notifications\"' in html
    assert 'id=\"view-notifications\"' in html
    assert 'id=\"notificationList\"' in html
    assert 'async function loadNotifications' in app_js
    assert 'async function loadHistory' not in app_js
    assert 'id=\"removeModal\"' in html
    assert 'id=\"removeFiles\"' in html
    assert 'Also delete the downloaded files' in html
    assert 'async function removeTorrentTargets' in app_js
    assert "confirm('Also delete downloaded files?" not in app_js
    assert "confirm('Delete downloaded files too?')" not in app_js
    assert 'nav-caret' not in html
    assert 'setSettingsNavExpanded(!expanded)' not in app_js
    assert "$$('.nav-root,.settings-subnav button,.mobile-nav button')" in app_js
    assert '0.5.15 removal dialog and notification center' in app_css
"""
validator = replace_once(validator, marker, addition, 'validator additions')
write('release_tools/validate_ui_strings.py', validator)

print('Staged Torrent Dashboard 0.5.15 notification/removal/navigation changes')
