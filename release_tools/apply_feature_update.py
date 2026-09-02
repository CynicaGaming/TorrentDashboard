#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match in {path}, found {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once("dashboard.py", 'VERSION = "0.5.39"', 'VERSION = "0.5.40"')

settings_diag = r'''(() => {
  const PREFIX = '[Torrent Dashboard]';
  const recent = new Map();
  function errorMessage(error) {
    if (error instanceof Error) return error.message || error.name || 'Unknown error';
    if (error && typeof error === 'object' && error.message) return String(error.message);
    return String(error || 'Unknown error');
  }
  function report(scope, error, context = {}) {
    const message = errorMessage(error);
    const key = `${scope}|${message}|${context.url || context.source || ''}`;
    const now = Date.now();
    if (now - (recent.get(key) || 0) < 3000) return;
    recent.set(key, now);
    const details = {
      time: new Date().toISOString(),
      stage: window.__tdStartupStage || 'unknown',
      ...context,
    };
    if (console.groupCollapsed) console.groupCollapsed(`${PREFIX} ${scope}: ${message}`);
    console.error(error instanceof Error ? error : message);
    console.log('Context:', details);
    if (error instanceof Error && error.stack) console.log(error.stack);
    if (console.groupEnd) console.groupEnd();
  }
  window.__tdReportError = report;
  window.__tdStartupStage = 'loading scripts';
  window.__tdMarkStartupStage = stage => {
    window.__tdStartupStage = stage;
    console.info(`${PREFIX} startup: ${stage}`);
  };
  window.__tdMarkReady = stage => {
    window.__tdStartupStage = stage || 'ready';
    window.__tdBootstrapReady = true;
    console.info(`${PREFIX} startup complete: ${window.__tdStartupStage}`);
  };
  window.addEventListener('error', event => {
    if (event.target && event.target !== window) {
      const target = event.target;
      report('resource load failure', new Error(`Failed to load ${target.tagName || 'resource'}`), {
        source: target.src || target.href || '',
        tag: target.tagName || '',
      });
      return;
    }
    report('uncaught exception', event.error || new Error(event.message || 'Uncaught browser error'), {
      source: event.filename || '',
      line: event.lineno || 0,
      column: event.colno || 0,
    });
  }, true);
  window.addEventListener('unhandledrejection', event => {
    const reason = event.reason instanceof Error ? event.reason : new Error(errorMessage(event.reason));
    report('unhandled promise rejection', reason);
  });
  setTimeout(() => {
    if (!window.__tdBootstrapReady && !window.__tdBootstrapFailed) {
      report('startup watchdog', new Error('Dashboard startup did not complete within 15 seconds'), {
        stage: window.__tdStartupStage || 'unknown',
      });
    }
  }, 15000);
  console.info(`${PREFIX} browser diagnostics enabled`);
})();

'''
replace_once("static/settings.js", "'use strict';\n\n", "'use strict';\n\n" + settings_diag)

old_api = "async function api(url,opt={}){opt.headers={...(opt.headers||{})};if(opt.method&&opt.method!=='GET'&&opt.method!=='HEAD'&&state.csrf)opt.headers['X-CSRF-Token']=state.csrf;const r=await fetch(url,opt);let data;const ct=r.headers.get('content-type')||'';data=ct.includes('json')?await r.json():await r.text();if(r.status===401){showLogin();throw new Error(data.error||'Authentication required')}if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}"
new_api = """async function api(url,opt={}){
  opt.headers={...(opt.headers||{})};
  const method=opt.method||'GET';
  if(method!=='GET'&&method!=='HEAD'&&state.csrf)opt.headers['X-CSRF-Token']=state.csrf;
  let r;
  try{r=await fetch(url,opt)}catch(e){window.__tdReportError?.('API network failure',e,{url,method});throw e}
  let data;
  try{const ct=r.headers.get('content-type')||'';data=ct.includes('json')?await r.json():await r.text()}
  catch(e){window.__tdReportError?.('API response parse failure',e,{url,method,status:r.status});throw e}
  if(r.status===401){showLogin();const e=new Error(data?.error||'Authentication required');window.__tdReportError?.('API authentication',e,{url,method,status:r.status});throw e}
  if(!r.ok){const e=new Error(data?.error||`HTTP ${r.status}`);window.__tdReportError?.('API request failure',e,{url,method,status:r.status});throw e}
  return data
}"""
replace_once("static/app.js", old_api, new_api)

old_raw = "async function rawJson(url,opt={}){const r=await fetch(url,opt);const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}"
new_raw = """async function rawJson(url,opt={}){
  const method=opt.method||'GET';let r;
  try{r=await fetch(url,opt)}catch(e){window.__tdReportError?.('Public API network failure',e,{url,method});throw e}
  let data={};
  try{data=await r.json()}catch(e){window.__tdReportError?.('Public API response parse failure',e,{url,method,status:r.status})}
  if(!r.ok){const e=new Error(data.error||`HTTP ${r.status}`);window.__tdReportError?.('Public API request failure',e,{url,method,status:r.status});throw e}
  return data
}"""
replace_once("static/app.js", old_raw, new_raw)

old_bootstrap = '''async function bootstrap(){
  bindPublicUI();
  try{
    state.setup=await rawJson('/api/setup/status');
    if(state.setup.required){showSetup();$('#wLocalIp').value=state.setup?.lan_ip||'127.0.0.1';$('#wPort').value=state.setup?.port||8765;$('#wTrustedIps').value=(state.setup.trusted_ips||[]).join('\\n');renderInterfaceList('#wInterfaceList',state.setup.network_interfaces||[],state.setup.trusted_interfaces||[],!(state.setup.trusted_interfaces||[]).length);state.setupInterfaceSelectionInitialized=true;$('#setupCodeWrap').classList.toggle('hidden',!state.setup.code_required);updateWizardClientAuth();updateWizardLanVisibility();updateSetupStep();return}
    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();
    document.body.classList.toggle('standard-user',!state.me.can_manage);
    $('#brandTitle').textContent=state.me.title;$('#brandAddress').textContent=state.me.lan_ip||'Local';document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;
    if(state.me.user_id){try{const account=await api('/api/account');applyAccountUser(account.user)}catch{}}
    syncCurrentUserUi();
    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}
    await loadServers();bindUI();applyPrefs();await refreshStatus();scheduleRefresh();registerPwa();
  }
  catch(e){if(!$('#login').classList.contains('hidden'))return;toast(e.message,'error')}
}'''
new_bootstrap = '''async function bootstrap(){
  window.__tdMarkStartupStage?.('binding public UI');
  try{bindPublicUI()}catch(e){window.__tdReportError?.('public UI binding',e);throw e}
  try{
    window.__tdMarkStartupStage?.('checking setup status');
    state.setup=await rawJson('/api/setup/status');
    if(state.setup.required){showSetup();$('#wLocalIp').value=state.setup?.lan_ip||'127.0.0.1';$('#wPort').value=state.setup?.port||8765;$('#wTrustedIps').value=(state.setup.trusted_ips||[]).join('\\n');renderInterfaceList('#wInterfaceList',state.setup.network_interfaces||[],state.setup.trusted_interfaces||[],!(state.setup.trusted_interfaces||[]).length);state.setupInterfaceSelectionInitialized=true;$('#setupCodeWrap').classList.toggle('hidden',!state.setup.code_required);updateWizardClientAuth();updateWizardLanVisibility();updateSetupStep();window.__tdMarkReady?.('first-run setup');return}
    window.__tdMarkStartupStage?.('loading session');
    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();
    document.body.classList.toggle('standard-user',!state.me.can_manage);
    $('#brandTitle').textContent=state.me.title;$('#brandAddress').textContent=state.me.lan_ip||'Local';document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;
    if(state.me.user_id){try{window.__tdMarkStartupStage?.('loading account');const account=await api('/api/account');applyAccountUser(account.user)}catch(e){window.__tdReportError?.('account bootstrap',e)}}
    syncCurrentUserUi();
    window.__tdMarkStartupStage?.('loading settings');
    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}
    window.__tdMarkStartupStage?.('loading clients');
    await loadServers();
    window.__tdMarkStartupStage?.('binding dashboard UI');
    bindUI();applyPrefs();
    window.__tdMarkStartupStage?.('loading torrent status');
    await refreshStatus();scheduleRefresh();registerPwa();
    window.__tdMarkReady?.('dashboard ready');
  }
  catch(e){
    window.__tdBootstrapFailed=true;
    window.__tdReportError?.('dashboard bootstrap',e,{stage:window.__tdStartupStage||'unknown'});
    if(!$('#login').classList.contains('hidden')){window.__tdMarkReady?.('login');return}
    showApp();
    const banner=$('#errorBanner');
    if(banner){banner.textContent=`Startup failed: ${e.message}. Open the browser developer console for details.`;banner.classList.remove('hidden')}
    try{toast(e.message,'error')}catch{}
  }
}'''
replace_once("static/app.js", old_bootstrap, new_bootstrap)

old_load_settings = "async function loadSettings(){try{state.settings=await api('/api/settings');fillSettings()}catch(e){toast(e.message,'error')}}"
new_load_settings = "async function loadSettings(){try{state.settings=await api('/api/settings');fillSettings()}catch(e){window.__tdReportError?.('settings load',e);toast(e.message,'error')}}"
replace_once("static/app.js", old_load_settings, new_load_settings)

old_refresh = "async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};renderMetrics(d);checkCompletions();render();if(state.detail)refreshDetailData(false);$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}"
new_refresh = "async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};renderMetrics(d);checkCompletions();render();if(state.detail)refreshDetailData(false);$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){window.__tdReportError?.('status refresh',e,{server:state.server});$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}"
replace_once("static/app.js", old_refresh, new_refresh)

old_pwa = "function registerPwa(){if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(()=>{});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(sessionStorage.getItem('tdSwReloaded')!=='1'){sessionStorage.setItem('tdSwReloaded','1');location.reload()}})}window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}"
new_pwa = "function registerPwa(){if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(e=>window.__tdReportError?.('service worker registration',e));navigator.serviceWorker.addEventListener('controllerchange',()=>{if(sessionStorage.getItem('tdSwReloaded')!=='1'){sessionStorage.setItem('tdSwReloaded','1');location.reload()}})}window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}"
replace_once("static/app.js", old_pwa, new_pwa)

replace_once(
    "static/app.js",
    "applySentenceCaseUi(document);decorateSecretFields(document);caseObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});bootstrap();",
    "window.__tdMarkStartupStage?.('initializing application');applySentenceCaseUi(document);decorateSecretFields(document);caseObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});bootstrap();",
)

index = ROOT / "static/index.html"
text = index.read_text(encoding="utf-8")
if text.count("0.5.39") < 4:
    raise SystemExit("Unexpected index version references")
index.write_text(text.replace("0.5.39", "0.5.40"), encoding="utf-8")

sw = ROOT / "static/sw.js"
text = sw.read_text(encoding="utf-8")
if "0.5.39" not in text or "v0539" not in text:
    raise SystemExit("Unexpected service worker version")
text = text.replace("0.5.39", "0.5.40").replace("v0539", "v0540")
sw.write_text(text, encoding="utf-8")

print("Applied 0.5.40 recovery diagnostics update")
