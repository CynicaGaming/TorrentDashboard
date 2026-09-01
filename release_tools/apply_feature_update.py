#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'Expected text not found in {path}: {old[:100]!r}')
    p.write_text(text.replace(old, new), encoding='utf-8')

# Version and browser cache revision.
replace('dashboard.py', 'VERSION = "0.5.2"', 'VERSION = "0.5.3"')
replace('static/index.html', '?v=0.5.2', '?v=0.5.3')
replace('static/sw.js', "const CACHE='torrent-dashboard-v052';", "const CACHE='torrent-dashboard-v053';")
replace('static/sw.js', '?v=0.5.2', '?v=0.5.3')

# settings.js is loaded before app.js. Keep its load-time constants self-contained so the
# settings module cannot fail before its navigation handlers bind.
replace('static/settings.js', 'const SECRET_MASK = CONFIGURED_SECRET_MASK;', "const SECRET_MASK = '••••••••••';")
replace(
    'static/settings.js',
    "    document.querySelector('#checkUpdate')?.addEventListener('click', () => checkForUpdates(false));\n    document.querySelector('#downloadUpdate')?.addEventListener('click', downloadUpdate);\n    document.querySelector('#installUpdate')?.addEventListener('click', installUpdate);",
    "    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);"
)

replace(
    'static/index.html',
    '<div class="update-actions"><button class="secondary" id="testUpdateAccess" type="button">Test GitHub Connection</button><button class="secondary" id="checkUpdate" type="button">Check For Updates</button><button class="secondary" disabled="" id="downloadUpdate" type="button">Download Update</button><button class="primary" disabled="" id="installUpdate" type="button">Install And Restart</button></div>',
    '<div class="update-actions"><button class="secondary" id="testUpdateAccess" type="button">Test GitHub Connection</button><button class="secondary update-action" id="updateAction" type="button">Check For Updates</button></div>'
)

replace(
    'static/app.js',
    "function showLogin(){\n  $('#setup').classList.add('hidden');$('#app').classList.add('hidden');$('#login').classList.remove('hidden');\n  $('#loginUser').value='';$('#loginPass').value='';\n}",
    "function showLogin(reset=false){\n  const login=$('#login'), entering=login.classList.contains('hidden');\n  $('#setup').classList.add('hidden');$('#app').classList.add('hidden');login.classList.remove('hidden');\n  if(reset||entering){$('#loginUser').value='';$('#loginPass').value='';}\n}"
)

old_updates = """function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};$('#updateCurrent').textContent=current;$('#updateLatest').textContent=manifest.version||st.version||uiText('notChecked');$('#updateState').textContent=uiText(st.state||'idle');const msg=$('#updateMessage');msg.className='muted update-message';let text='';if(data?.error){text=data.error;msg.classList.add('bad')}else if(data?.configured===false){text='updatesNotConfigured'}else if(data?.updateAvailable){text=`updateAvailable ${manifest.version}${manifest.publishedAt?` · ${manifest.publishedAt}`:''}`;msg.classList.add('ok')}else if(manifest.version){text=`upToDate ${current}`;msg.classList.add('ok')}else if(st.state&&st.state!=='idle'){text=st.error||st.state}else{text='checkForUpdatesWhenReady'}msg.textContent=data?.error?text:uiText(text);$('#downloadUpdate').disabled=!(data?.updateAvailable);$('#installUpdate').disabled=st.state!=='readyToInstall';if(st.state==='readyToInstall'){$('#installUpdate').disabled=false;$('#downloadUpdate').disabled=true}}
async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}
async function downloadUpdate(){const b=$('#downloadUpdate');b.disabled=true;b.textContent=uiText('downloading…');try{const d=await post('/api/update-download',{});renderUpdateInfo({configured:true,currentVersion:state.me?.version,manifest:d.manifest,updateAvailable:true,state:d});toast('updateReadyToInstall')}catch(e){toast(e.message,'error')}finally{b.textContent=uiText('downloadUpdate');if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;if(!confirm(`installAndRestart ${version}?`))return;const b=$('#installUpdate');b.disabled=true;b.textContent=uiText('restarting…');try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){b.disabled=false;b.textContent=uiText('installAndRestart');toast(e.message,'error')}}
"""
new_updates = """function updateActionButton(data=state.updateInfo){const b=$('#updateAction');if(!b)return;const st=data?.state||state.settings?.runtime?.updateState||{};b.classList.remove('primary','secondary');if(st.state==='readyToInstall'){b.disabled=false;b.classList.add('primary');b.textContent=uiText('installUpdate');return}if(st.state==='downloading'){b.disabled=true;b.classList.add('secondary');b.textContent=uiText('downloading…');return}if(st.state==='installing'){b.disabled=true;b.classList.add('primary');b.textContent=uiText('installing…');return}b.disabled=false;b.classList.add('secondary');b.textContent=uiText('checkForUpdates')}
function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};$('#updateCurrent').textContent=current;$('#updateLatest').textContent=manifest.version||st.version||uiText('notChecked');$('#updateState').textContent=uiText(st.state||'idle');const msg=$('#updateMessage');msg.className='muted update-message';let text='';if(data?.error){text=data.error;msg.classList.add('bad')}else if(data?.configured===false){text='updatesNotConfigured'}else if(st.state==='readyToInstall'){text=`updateReadyToInstall ${st.version||manifest.version||''}`;msg.classList.add('ok')}else if(data?.updateAvailable){text=`updateAvailable ${manifest.version}${manifest.publishedAt?` · ${manifest.publishedAt}`:''}`;msg.classList.add('ok')}else if(manifest.version){text=`upToDate ${current}`;msg.classList.add('ok')}else if(st.state&&st.state!=='idle'){text=st.error||st.state}else{text='checkForUpdatesWhenReady'}msg.textContent=data?.error?text:uiText(text);updateActionButton(data)}
async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}
async function downloadUpdate(){const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('downloading…')}try{const d=await post('/api/update-download',{});renderUpdateInfo({configured:true,currentVersion:state.me?.version,manifest:d.manifest,updateAvailable:true,state:d});toast('updateReadyToInstall');return d}catch(e){toast(e.message,'error');throw e}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function handleUpdateAction(){const st=state.updateInfo?.state||state.settings?.runtime?.updateState||{};if(st.state==='readyToInstall')return installUpdate();const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('checkingForUpdates…')}try{const d=await checkForUpdates(true);if(d?.updateAvailable){toast(`updateAvailable ${d.manifest.version}`);await downloadUpdate()}else if(!d?.error){toast(d.configured===false?'updatesNotConfigured':'upToDate')}}catch(e){if(!state.updateInfo?.error)toast(e.message,'error')}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;if(!confirm(`installAndRestart ${version}?`))return;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}
"""
replace('static/app.js', old_updates, new_updates)

css = ROOT / 'static/settings.css'
css_text = css.read_text(encoding='utf-8')
css_text += """

/* 0.5.3 settings navigation and update-action alignment. */
@media(min-width:821px){.settings-nav{margin-top:52px}}
.update-actions .update-action{min-width:170px}
@media(max-width:820px){.settings-nav{margin-top:0}.update-actions .update-action{flex:1 1 160px}}
@media(max-width:560px){.update-actions{display:grid;grid-template-columns:1fr}.update-actions button{width:100%}}
"""
css.write_text(css_text, encoding='utf-8')

print('Applied Torrent Dashboard 0.5.3 navigation, login, update action, and layout changes.')
