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


def replace_regex_once(text, pattern, replacement, label, flags=0):
    text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one regex match, found {count}')
    return text


# ---------------------------------------------------------------------------
# Backend: hard-code the live collector to one second and retire the old
# user-configurable refresh_seconds setting.
# ---------------------------------------------------------------------------
dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.15"', 'VERSION = "0.5.16"\nSTATUS_REFRESH_SECONDS = 1.0', 'dashboard version')
dashboard = replace_once(dashboard, '        "refresh_seconds": 2,\n', '', 'default refresh setting')
dashboard = replace_once(
    dashboard,
    '    merged = deep_merge(DEFAULT_CONFIG, raw)\n',
    '    merged = deep_merge(DEFAULT_CONFIG, raw)\n    # 0.5.16 makes status collection a fixed one-second application behavior.\n    # Ignore and retire any refresh_seconds value left by an older install.\n    merged.setdefault("dashboard", {}).pop("refresh_seconds", None)\n',
    'legacy refresh cleanup',
)
dashboard = replace_once(
    dashboard,
    '        stop_event.wait(max(1, float(cfg["dashboard"].get("refresh_seconds", 2))))',
    '        stop_event.wait(STATUS_REFRESH_SECONDS)',
    'collector refresh interval',
)
dashboard = replace_once(
    dashboard,
    ',"refresh_seconds":cfg["dashboard"].get("refresh_seconds",2)',
    '',
    'me refresh field',
)
dashboard = replace_once(
    dashboard,
    '            out["dashboard"]["refresh_seconds"]=max(1,min(60,int(dashboard.get("refresh_seconds") or 2)))\n',
    '',
    'setup refresh setting',
)
dashboard = replace_once(
    dashboard,
    '    for k in ("title","port","refresh_seconds","history_retention_days","history_sample_seconds","low_disk_gb","https_enabled","https_cert","https_key"):',
    '    for k in ("title","port","history_retention_days","history_sample_seconds","low_disk_gb","https_enabled","https_cert","https_key"): ',
    'settings refresh field list',
)
dashboard = replace_once(
    dashboard,
    '    out.setdefault("dashboard",{}).pop("read_only",None)\n',
    '    out.setdefault("dashboard",{}).pop("read_only",None)\n    out["dashboard"].pop("refresh_seconds",None)\n',
    'settings legacy refresh cleanup',
)
write('dashboard.py', dashboard)


# ---------------------------------------------------------------------------
# HTML: remove refresh controls and add one reusable application dialog.
# ---------------------------------------------------------------------------
html = read('static/index.html')
html = html.replace('?v=0.5.15', '?v=0.5.16')
html = replace_once(
    html,
    '<label>Refresh Interval<select id="wRefresh"><option value="1">1 Second</option><option selected="" value="2">2 Seconds</option><option value="5">5 Seconds</option><option value="10">10 Seconds</option></select></label>\n',
    '',
    'wizard refresh control',
)
html = replace_once(
    html,
    '<label>Refresh Interval Seconds<input id="sRefresh" max="60" min="1" type="number"/></label>\n',
    '',
    'settings refresh control',
)

action_modal = '''<div class="modal hidden" id="actionDialogModal"><div class="modal-backdrop" data-action-dialog-cancel=""></div><form class="modal-card action-dialog-card" id="actionDialogForm"><header><div><h2 id="actionDialogTitle">Action</h2><p class="hidden" id="actionDialogMessage"></p></div><button class="icon-btn" data-action-dialog-cancel="" type="button" aria-label="Cancel">×</button></header><div class="action-dialog-content"><label id="actionDialogField"><span id="actionDialogLabel">Value</span><input autocomplete="off" id="actionDialogInput"/></label><div class="field-help hidden" id="actionDialogHelp"></div></div><footer class="action-dialog-actions"><button class="primary action-dialog-confirm" id="actionDialogConfirm" type="submit">Save</button><button class="secondary" data-action-dialog-cancel="" type="button">Cancel</button></footer></form></div>\n'''
html = replace_once(
    html,
    '<div class="modal hidden" id="removeModal">',
    action_modal + '<div class="modal hidden" id="removeModal">',
    'generic action modal',
)
write('static/index.html', html)


# ---------------------------------------------------------------------------
# Settings JS: refresh speed is no longer a setting.
# ---------------------------------------------------------------------------
settings = read('static/settings.js')
settings = replace_once(settings, "    setValue('sRefresh', s.dashboard?.refresh_seconds || 2);\n", '', 'settings refresh fill')
settings = replace_once(
    settings,
    "        port: Number(document.querySelector('#sPort')?.value || 8765),\n        refresh_seconds: Number(document.querySelector('#sRefresh')?.value || 2)\n",
    "        port: Number(document.querySelector('#sPort')?.value || 8765)\n",
    'settings refresh payload',
)
settings = replace_once(
    settings,
    '      state.refreshMs = Math.max(1000, Number(state.settings.dashboard.refresh_seconds || 2) * 1000);\n      scheduleRefresh();\n',
    '',
    'settings refresh reschedule',
)
write('static/settings.js', settings)


# ---------------------------------------------------------------------------
# App JS: fixed one-second UI refresh plus reusable app-owned dialogs.
# ---------------------------------------------------------------------------
js = read('static/app.js')
js = replace_once(
    js,
    "const state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailTab:'overview',refreshMs:2000,settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};",
    "const LIVE_REFRESH_MS=1000;\nconst state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailTab:'overview',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};",
    'frontend live refresh constant',
)
js = replace_once(
    js,
    "function setupPayload(){return{setup_code:$('#wSetupCode').value.trim(),dashboard:{title:$('#wTitle').value.trim()||'Torrent Dashboard',port:Number($('#wPort').value||state.setup?.port||8765),refresh_seconds:Number($('#wRefresh').value||2)},auth:{mode:$('#wAuthMode').value,username:$('#wDashUser').value.trim()||'admin',password:$('#wDashPass').value,trusted_interfaces:selectedInterfaceIds('#wInterfaceList'),trusted_ips:parseWhitelist('#wTrustedIps')},servers:[setupServer()]}}",
    "function setupPayload(){return{setup_code:$('#wSetupCode').value.trim(),dashboard:{title:$('#wTitle').value.trim()||'Torrent Dashboard',port:Number($('#wPort').value||state.setup?.port||8765)},auth:{mode:$('#wAuthMode').value,username:$('#wDashUser').value.trim()||'admin',password:$('#wDashPass').value,trusted_interfaces:selectedInterfaceIds('#wInterfaceList'),trusted_ips:parseWhitelist('#wTrustedIps')},servers:[setupServer()]}}",
    'wizard refresh payload',
)
js = replace_once(
    js,
    "  $('#wReview').innerHTML=`<div><span>Dashboard</span><b>${esc(p.dashboard.title)}</b><small>${esc($('#wLocalIp').value)}:${p.dashboard.port} · ${p.dashboard.refresh_seconds}s Refresh</small></div>",
    "  $('#wReview').innerHTML=`<div><span>Dashboard</span><b>${esc(p.dashboard.title)}</b><small>${esc($('#wLocalIp').value)}:${p.dashboard.port}</small></div>",
    'wizard review refresh text',
)
js = replace_once(
    js,
    "    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{refresh_seconds:state.me.refresh_seconds||2,low_disk_gb:20},notifications:{browser:false,sound:false}};state.refreshMs=Math.max(1000,Number(state.me.refresh_seconds||2)*1000)}",
    "    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}",
    'standard user refresh state',
)
js = replace_once(
    js,
    "async function loadSettings(){try{state.settings=await api('/api/settings');state.refreshMs=Math.max(1000,Number(state.settings.dashboard.refresh_seconds||2)*1000);fillSettings()}catch(e){toast(e.message,'error')}}",
    "async function loadSettings(){try{state.settings=await api('/api/settings');fillSettings()}catch(e){toast(e.message,'error')}}",
    'settings load refresh state',
)
js = replace_once(
    js,
    'function scheduleRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(refreshStatus,state.refreshMs)}',
    'function scheduleRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(refreshStatus,LIVE_REFRESH_MS)}',
    'fixed browser refresh schedule',
)

# Reusable modal implementation. This replaces app-owned prompt()/confirm() UI.
action_helpers = r'''
let actionDialogResolve=null,actionDialogHasInput=false,actionDialogBound=false;
function closeActionDialog(result=null){const modal=$('#actionDialogModal');if(modal)modal.classList.add('hidden');const resolve=actionDialogResolve;actionDialogResolve=null;if(resolve)resolve(result)}
function bindActionDialog(){if(actionDialogBound)return;actionDialogBound=true;$('#actionDialogForm')?.addEventListener('submit',e=>{e.preventDefault();const input=$('#actionDialogInput');if(actionDialogHasInput){if(!input.reportValidity())return;closeActionDialog(input.value)}else closeActionDialog(true)});$$('[data-action-dialog-cancel]').forEach(x=>x.addEventListener('click',()=>closeActionDialog(null)))}
function showActionDialog(options={}){bindActionDialog();if(actionDialogResolve)closeActionDialog(null);const modal=$('#actionDialogModal'),title=$('#actionDialogTitle'),message=$('#actionDialogMessage'),field=$('#actionDialogField'),label=$('#actionDialogLabel'),input=$('#actionDialogInput'),help=$('#actionDialogHelp'),confirm=$('#actionDialogConfirm');actionDialogHasInput=options.input!==false;title.textContent=options.title||'Action';message.textContent=options.message||'';message.classList.toggle('hidden',!options.message);field.classList.toggle('hidden',!actionDialogHasInput);label.textContent=options.label||'Value';help.textContent=options.help||'';help.classList.toggle('hidden',!options.help);input.type=options.type||'text';input.value=String(options.value??'');input.placeholder=options.placeholder||'';input.required=actionDialogHasInput&&!options.allowEmpty;for(const attr of ['min','max','step']){if(options[attr]!==undefined&&options[attr]!==null)input.setAttribute(attr,String(options[attr]));else input.removeAttribute(attr)}confirm.textContent=options.confirmLabel||'Save';confirm.className=`${options.danger?'danger':'primary'} action-dialog-confirm`;modal.classList.remove('hidden');return new Promise(resolve=>{actionDialogResolve=resolve;setTimeout(()=>{if(actionDialogHasInput){input.focus();input.select()}else confirm.focus()},0)})}

'''
js = replace_once(js, 'let removeDialogResolve=null;', action_helpers + 'let removeDialogResolve=null;', 'action dialog helpers')

# Update install confirmation.
old_install = "async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;if(!confirm(`${uiText('installAndRestart')} ${version}?`))return;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}"
new_install = "async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;const proceed=await showActionDialog({title:'Install update',message:`Torrent Dashboard ${version} is ready to install. The dashboard will restart to finish the update.`,input:false,confirmLabel:'Install and restart'});if(!proceed)return;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}"
js = replace_once(js, old_install, new_install, 'update install modal')

# Torrent context-menu prompts.
old_context = '''    if(a==='set_location'){
      const v=prompt('New save location:',t.save_path||'');
      if(v!==null&&v.trim())return doAction('set_location',{server:sid,hashes:[h],location:v.trim()});
      return;
    }
    if(a==='rename'){
      const v=prompt('New torrent name:',t.name||'');
      if(v!==null&&v.trim())return doAction('rename',{server:sid,hash:h,hashes:[h],name:v.trim()});
      return;
    }
    if(a==='set_category'){
      const v=prompt('Category:',t.category||'');
      if(v!==null)return doAction('set_category',{server:sid,hashes:[h],category:v.trim()});
      return;
    }
    if(a==='tags'){
      const current=String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean);
      const v=prompt('Tags (comma-separated):',current.join(', '));
      if(v===null)return;
      const next=v.split(',').map(x=>x.trim()).filter(Boolean);
      const remove=current.filter(x=>!next.includes(x));
      const add=next.filter(x=>!current.includes(x));
      if(remove.length)await doAction('remove_tags',{server:sid,hashes:[h],tags:remove.join(',')});
      if(add.length)await doAction('add_tags',{server:sid,hashes:[h],tags:add.join(',')});
      return;
    }'''
new_context = '''    if(a==='set_location'){
      const v=await showActionDialog({title:'Set location',label:'Save location',value:t.save_path||'',confirmLabel:'Save'});
      if(v!==null&&v.trim())return doAction('set_location',{server:sid,hashes:[h],location:v.trim()});
      return;
    }
    if(a==='rename'){
      const v=await showActionDialog({title:'Rename torrent',label:'Torrent name',value:t.name||'',confirmLabel:'Save'});
      if(v!==null&&v.trim())return doAction('rename',{server:sid,hash:h,hashes:[h],name:v.trim()});
      return;
    }
    if(a==='set_category'){
      const v=await showActionDialog({title:'Set category',label:'Category',value:t.category||'',allowEmpty:true,confirmLabel:'Save',help:'Leave blank to clear the category.'});
      if(v!==null)return doAction('set_category',{server:sid,hashes:[h],category:v.trim()});
      return;
    }
    if(a==='tags'){
      const current=String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean);
      const v=await showActionDialog({title:'Edit tags',label:'Tags',value:current.join(', '),allowEmpty:true,confirmLabel:'Save',help:'Separate multiple tags with commas. Leave blank to remove all tags.'});
      if(v===null)return;
      const next=v.split(',').map(x=>x.trim()).filter(Boolean);
      const remove=current.filter(x=>!next.includes(x));
      const add=next.filter(x=>!current.includes(x));
      if(remove.length)await doAction('remove_tags',{server:sid,hashes:[h],tags:remove.join(',')});
      if(add.length)await doAction('add_tags',{server:sid,hashes:[h],tags:add.join(',')});
      return;
    }'''
js = replace_once(js, old_context, new_context, 'context action modals')

# Torrent-details prompts. Keep behavior aligned with the context menu.
old_detail = "async function detailAction(a){if(!a||!state.detail)return;const {server,hash}=state.detail;if(a==='set_location'){let location=prompt('New save location:');if(location!==null)await doAction(a,{server,hashes:[hash],location});return}if(a==='rename'){let name=prompt('New torrent name:');if(name)await doAction(a,{server,hash,name});return}if(a==='set_category'){let category=prompt('Category name:');if(category!==null)await doAction(a,{server,hashes:[hash],category});return}if(a==='add_tags'){let tags=prompt('Comma-separated tags:');if(tags)await doAction(a,{server,hashes:[hash],tags});return}if(a==='set_download_limit'||a==='set_upload_limit'){let kb=prompt('Limit KB Per Second (0 = Unlimited):','0');if(kb!==null)await doAction(a,{server,hashes:[hash],limit:Number(kb)*1024});return}if(a==='delete'){const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);if(await removeTorrentTargets([{server,hash,name:t?.name||hash}]))closeDrawer();return}await doAction(a,{server,hashes:[hash]})}"
new_detail = "async function detailAction(a){if(!a||!state.detail)return;const {server,hash}=state.detail,t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);if(a==='set_location'){const location=await showActionDialog({title:'Set location',label:'Save location',value:t?.save_path||'',confirmLabel:'Save'});if(location!==null&&location.trim())await doAction(a,{server,hashes:[hash],location:location.trim()});return}if(a==='rename'){const name=await showActionDialog({title:'Rename torrent',label:'Torrent name',value:t?.name||'',confirmLabel:'Save'});if(name!==null&&name.trim())await doAction(a,{server,hash,name:name.trim()});return}if(a==='set_category'){const category=await showActionDialog({title:'Set category',label:'Category',value:t?.category||'',allowEmpty:true,confirmLabel:'Save',help:'Leave blank to clear the category.'});if(category!==null)await doAction(a,{server,hashes:[hash],category:category.trim()});return}if(a==='add_tags'){const current=String(t?.tags||'').split(',').map(x=>x.trim()).filter(Boolean);const tags=await showActionDialog({title:'Edit tags',label:'Tags',value:current.join(', '),allowEmpty:true,confirmLabel:'Save',help:'Separate multiple tags with commas. Leave blank to remove all tags.'});if(tags===null)return;const next=tags.split(',').map(x=>x.trim()).filter(Boolean),remove=current.filter(x=>!next.includes(x)),add=next.filter(x=>!current.includes(x));if(remove.length)await doAction('remove_tags',{server,hashes:[hash],tags:remove.join(',')});if(add.length)await doAction('add_tags',{server,hashes:[hash],tags:add.join(',')});return}if(a==='set_download_limit'||a==='set_upload_limit'){const kb=await showActionDialog({title:a==='set_download_limit'?'Set download limit':'Set upload limit',label:'Limit (KB/s)',value:'0',type:'number',min:0,step:1,confirmLabel:'Apply',help:'Use 0 for unlimited.'});if(kb!==null)await doAction(a,{server,hashes:[hash],limit:Number(kb)*1024});return}if(a==='delete'){if(await removeTorrentTargets([{server,hash,name:t?.name||hash}]))closeDrawer();return}await doAction(a,{server,hashes:[hash]})}"
js = replace_once(js, old_detail, new_detail, 'detail action modals')

# Global bandwidth prompt.
old_global_limit = "async function globalLimit(action){if(state.server==='all')return toast('chooseSpecificServerFirst','error');let kb=prompt('Limit KB Per Second (0 = Unlimited):','0');if(kb!==null)await doAction(action,{limit:Number(kb)*1024})}"
new_global_limit = "async function globalLimit(action){if(state.server==='all')return toast('chooseSpecificServerFirst','error');const kb=await showActionDialog({title:action==='global_download_limit'?'Set global download limit':'Set global upload limit',label:'Limit (KB/s)',value:'0',type:'number',min:0,step:1,confirmLabel:'Apply',help:'Use 0 for unlimited.'});if(kb!==null)await doAction(action,{limit:Number(kb)*1024})}"
js = replace_once(js, old_global_limit, new_global_limit, 'global limit modal')

# Escape closes whichever app-owned modal is active before affecting selection.
old_escape = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});"
new_escape = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});"
js = replace_once(js, old_escape, new_escape, 'escape modal handling')

# No app-owned browser dialogs should remain. The PWA API's .prompt() method is
# browser-owned and intentionally remains.
if re.search(r'(?<!\.)\bprompt\s*\(', js):
    raise RuntimeError('native prompt() remains in app.js')
if re.search(r'\bconfirm\s*\(', js):
    raise RuntimeError('native confirm() remains in app.js')
if 'refreshMs' in js or 'refresh_seconds' in js or "#wRefresh" in js or "#sRefresh" in js:
    raise RuntimeError('retired refresh setting remains in app.js')
write('static/app.js', js)


# ---------------------------------------------------------------------------
# Styling: consistent modal layout on desktop and a bottom-sheet treatment on
# phones for easier keyboard/touch interaction.
# ---------------------------------------------------------------------------
css = read('static/app.css')
css += r'''

/* 0.5.16 unified application dialog. */
.action-dialog-card{width:min(540px,calc(100% - 24px));padding-bottom:0}.action-dialog-card header p{margin:5px 0 0;color:var(--muted);font-size:11px;line-height:1.45}.action-dialog-content{display:grid;gap:10px;padding:18px}.action-dialog-content label{display:grid;gap:7px;color:var(--muted);font-size:11px}.action-dialog-content input{width:100%;min-height:42px}.action-dialog-actions{display:flex;justify-content:flex-end;gap:8px;padding:12px 18px 18px;border-top:1px solid var(--border)}.action-dialog-actions button{min-width:112px}.action-dialog-confirm.danger{font-weight:700}
@media(max-width:560px){#actionDialogModal{place-items:end center;padding:0}.action-dialog-card{width:100%;max-height:min(88vh,720px);border-radius:18px 18px 0 0;border-bottom:0}.action-dialog-content{padding:16px}.action-dialog-content input{min-height:46px}.action-dialog-actions{display:grid;grid-template-columns:1fr 1fr;padding:12px 16px calc(16px + env(safe-area-inset-bottom))}.action-dialog-actions button{width:100%;min-height:44px;min-width:0}}
'''
write('static/app.css', css)


# Service worker asset revision.
sw = read('static/sw.js')
sw = sw.replace('torrent-dashboard-v0515', 'torrent-dashboard-v0516')
sw = sw.replace('?v=0.5.15', '?v=0.5.16')
write('static/sw.js', sw)


# Release-time regression guards.
validator = read('release_tools/validate_ui_strings.py')
validator = replace_once(
    validator,
    '    assert \'0.5.14 settings de-duplication\' in settings_css\n',
    "    assert '0.5.14 settings de-duplication' in settings_css\n    assert 'id=\"wRefresh\"' not in html and 'id=\"sRefresh\"' not in html\n    assert 'id=\"actionDialogModal\"' in html and 'id=\"actionDialogForm\"' in html\n    assert 'LIVE_REFRESH_MS=1000' in app_js\n    assert 'refreshMs' not in app_js and 'refresh_seconds' not in app_js and 'refresh_seconds' not in settings_js\n    assert not re.search(r'(?<!\\.)\\bprompt\\s*\\(', app_js)\n    assert not re.search(r'\\bconfirm\\s*\\(', app_js)\n    assert 'STATUS_REFRESH_SECONDS = 1.0' in dashboard_py\n    assert 'stop_event.wait(STATUS_REFRESH_SECONDS)' in dashboard_py\n    assert '0.5.16 unified application dialog' in app_css\n",
    'validator modal and refresh checks',
)
write('release_tools/validate_ui_strings.py', validator)


# Final staging checks.
assert 'VERSION = "0.5.16"' in read('dashboard.py')
assert 'id="wRefresh"' not in read('static/index.html')
assert 'id="sRefresh"' not in read('static/index.html')
assert 'id="actionDialogModal"' in read('static/index.html')
assert 'LIVE_REFRESH_MS=1000' in read('static/app.js')
assert 'STATUS_REFRESH_SECONDS = 1.0' in read('dashboard.py')
print('Staged Torrent Dashboard 0.5.16')
