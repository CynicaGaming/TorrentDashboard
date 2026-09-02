#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.47"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_dashboard():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.46"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")

    handler_marker = "\n\nclass Handler(BaseHTTPRequestHandler):\n"
    recovery_helper = r"""

def frontend_recovery_script(version):
    build = json.dumps(str(version))
    script = '''(() => {
  const build = __BUILD__;
  if (window.__tdFrontendRecoveryStarted) return;
  window.__tdFrontendRecoveryStarted = true;
  console.error('[Torrent Dashboard] Frontend build mismatch detected. Clearing cached application shell.', { build });
  (async () => {
    try {
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map(registration => registration.unregister()));
      }
    } catch (error) { console.error('[Torrent Dashboard] Service worker cleanup failed', error); }
    try {
      if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.filter(key => key.startsWith('torrent-dashboard-')).map(key => caches.delete(key)));
      }
    } catch (error) { console.error('[Torrent Dashboard] Cache cleanup failed', error); }
    const url = new URL(window.location.href);
    url.searchParams.set('td-recover', build);
    window.location.replace(url.toString());
  })();
})();'''
    return script.replace("__BUILD__", build).encode("utf-8")
"""
    text = replace_once(text, handler_marker, recovery_helper + handler_marker, "HTTP handler marker")

    old_static = '        if path.startswith("/static/"): return self.serve_static(path[len("/static/"):])\n'
    new_static = '''        if path.startswith("/static/"):\n            name=path[len("/static/"):]\n            requested=(qs.get("v") or [""])[0]\n            if name in ("app.js","settings.js") and requested and requested != VERSION:\n                return self.send_bytes(200,frontend_recovery_script(VERSION),"application/javascript; charset=utf-8")\n            return self.serve_static(name)\n'''
    text = replace_once(text, old_static, new_static, "version-aware static route")
    path.write_text(text, encoding="utf-8")


def update_index():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    if "v=0.5.46" not in text:
        raise RuntimeError("Expected v0.5.46 asset references")
    text = text.replace("v=0.5.46", f"v={TARGET_VERSION}")
    theme_meta = '<meta content="#0b0d10" name="theme-color"/>\n'
    build_meta = theme_meta + f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>\n'
    text = replace_once(text, theme_meta, build_meta, "frontend build metadata")
    body_marker = "<body>\n"
    failure = body_marker + '<div class="startup-failure hidden" id="startupFailure" role="alert" aria-live="assertive"><strong>Dashboard failed to initialize</strong><span id="startupFailureMessage">Reload the page. If the problem continues, open the browser console for details.</span></div>\n'
    text = replace_once(text, body_marker, failure, "startup failure surface")
    path.write_text(text, encoding="utf-8")


def update_service_worker():
    path = ROOT / "static" / "sw.js"
    text = f'''const CACHE='torrent-dashboard-v0547';\nconst ASSETS=['/static/app.css?v={TARGET_VERSION}','/static/settings.css?v={TARGET_VERSION}','/static/settings.js?v={TARGET_VERSION}','/static/app.js?v={TARGET_VERSION}','/manifest.webmanifest'];\nself.addEventListener('install',event=>{{self.skipWaiting();event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)))}});\nself.addEventListener('activate',event=>event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),self.clients.claim()])));\nself.addEventListener('fetch',event=>{{if(event.request.method!=='GET')return;const url=new URL(event.request.url);if(url.origin!==self.location.origin||url.pathname.startsWith('/api/')||event.request.mode==='navigate'||url.pathname==='/'||url.pathname==='/index.html')return;event.respondWith(fetch(event.request,{{cache:'no-store'}}).then(response=>{{if(response.ok){{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy))}}return response}}).catch(()=>caches.match(event.request)))}});\n'''
    path.write_text(text, encoding="utf-8")


def update_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    strict = "'use strict';\n"
    guard = r'''const FRONTEND_BUILD='0.5.47';
const HTML_BUILD=document.querySelector('meta[name="torrent-dashboard-build"]')?.content||'';
const RECOVERY_KEY=`td-frontend-recovery-${FRONTEND_BUILD}`;
async function recoverFrontendBuild(reason){
  console.error('[Torrent Dashboard] Frontend build mismatch', {reason,htmlBuild:HTML_BUILD,scriptBuild:FRONTEND_BUILD});
  if(window.__tdFrontendRecoveryStarted)return;
  window.__tdFrontendRecoveryStarted=true;
  const attempts=Number(sessionStorage.getItem(RECOVERY_KEY)||0);
  if(attempts>=2){console.error('[Torrent Dashboard] Frontend recovery stopped after repeated mismatches');return}
  sessionStorage.setItem(RECOVERY_KEY,String(attempts+1));
  try{if('serviceWorker'in navigator){const registrations=await navigator.serviceWorker.getRegistrations();await Promise.all(registrations.map(registration=>registration.unregister()))}}catch(error){console.error('[Torrent Dashboard] Service worker cleanup failed',error)}
  try{if('caches'in window){const keys=await caches.keys();await Promise.all(keys.filter(key=>key.startsWith('torrent-dashboard-')).map(key=>caches.delete(key)))}}catch(error){console.error('[Torrent Dashboard] Cache cleanup failed',error)}
  const url=new URL(location.href);url.searchParams.set('td-recover',FRONTEND_BUILD);location.replace(url.toString())
}
if(HTML_BUILD!==FRONTEND_BUILD){recoverFrontendBuild('HTML and JavaScript builds do not match');throw new Error(`Torrent Dashboard frontend build mismatch: HTML ${HTML_BUILD||'unknown'}, JavaScript ${FRONTEND_BUILD}`)}
sessionStorage.removeItem(RECOVERY_KEY);
window.addEventListener('error',event=>console.error('[Torrent Dashboard] Uncaught error',event.error||event.message));
window.addEventListener('unhandledrejection',event=>console.error('[Torrent Dashboard] Unhandled promise rejection',event.reason));
'''
    text = replace_once(text, strict, strict + guard, "frontend build guard")

    show_setup = "function showSetup(){ $('#login').classList.add('hidden');$('#app').classList.add('hidden');$('#setup').classList.remove('hidden') }\n"
    failure_helper = show_setup + r'''function showStartupFailure(error,stage='startup'){
  console.error(`[Torrent Dashboard] ${stage} failed`,error);
  const box=$('#startupFailure');if(!box)return;
  const message=$('#startupFailureMessage');if(message)message.textContent=`${error?.message||error||'Unknown error'} · Open the browser console for details.`;
  box.classList.remove('hidden');
}
function bindAddTorrentUI(){
  const required=['addLinkBtn','addFileBtn','addModal','addForm','addUrls','torrentFile'];
  const missing=required.filter(id=>!document.getElementById(id));
  if(missing.length){console.error('[Torrent Dashboard] Add Torrent UI unavailable; missing elements',missing);return false}
  $('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));
  $('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));
  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));
  $('#addForm').addEventListener('submit',addTorrent);
  return true;
}
'''
    text = replace_once(text, show_setup, failure_helper, "startup failure and Add Torrent binding helpers")

    old_catch = "  catch(e){if(!$('#login').classList.contains('hidden'))return;toast(e.message,'error')}\n}\n\nlet bound=false;\nfunction bindUI(){if(bound)return;bound=true;\n"
    new_catch = "  catch(e){if(!$('#login').classList.contains('hidden'))return;showStartupFailure(e,'bootstrap')}\n}\n\nlet bound=false;\nfunction bindUI(){if(bound)return;\n"
    text = replace_once(text, old_catch, new_catch, "bootstrap catch and binding state")

    old_add_bind = "  $('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));$('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));$('#addForm').addEventListener('submit',addTorrent);$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));\n"
    new_add_bind = "  bindAddTorrentUI();$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));\n"
    text = replace_once(text, old_add_bind, new_add_bind, "isolated Add Torrent binding")

    old_end = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden')){closePasswordConfirmation(null);return}if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDetailPane();$('#addModal').classList.add('hidden')}});\n}\n"
    new_end = "  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden')){closePasswordConfirmation(null);return}if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDetailPane();$('#addModal')?.classList.add('hidden')}});\n  bound=true;\n}\n"
    text = replace_once(text, old_end, new_end, "binding completion marker")
    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    if ".startup-failure{" in text:
        raise RuntimeError("Startup failure styling already present")
    css = "\n\n/* 0.5.47 frontend recovery and startup diagnostics */\n.startup-failure{position:fixed;z-index:3000;left:50%;top:18px;transform:translateX(-50%);width:min(720px,calc(100% - 32px));display:grid;gap:5px;padding:12px 14px;border:1px solid var(--bad);border-radius:10px;background:var(--panel);box-shadow:0 14px 40px rgba(0,0,0,.35)}.startup-failure strong{font-size:11px}.startup-failure span{font-size:9px;color:var(--muted)}\n"
    path.write_text(text.rstrip() + css + "\n", encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    marker = '    assert "Metadata retrieval complete" not in app_js\n'
    addition = marker + r'''    # 0.5.47 frontend generation contract. Navigation HTML is never cached,
    # stale versioned scripts trigger recovery, and optional Add Torrent bindings
    # cannot abort critical dashboard startup.
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    version = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', dashboard_py, re.M).group(1)
    assert f'<meta content="{version}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{version}';" in app_js
    assert "HTML_BUILD!==FRONTEND_BUILD" in app_js and "recoverFrontendBuild" in app_js
    assert "showStartupFailure(e,'bootstrap')" in app_js
    assert "function bindAddTorrentUI()" in app_js
    assert "missing elements" in app_js
    assert "function bindUI(){if(bound)return;" in app_js
    assert "function bindUI(){if(bound)return;bound=true;" not in app_js
    assert "bound=true;\n}" in app_js
    assert 'id="startupFailure"' in html and '.startup-failure{' in app_css
    assert "frontend_recovery_script" in dashboard_py
    assert 'requested and requested != VERSION' in dashboard_py
    assert "event.request.mode==='navigate'" in sw
    assets = sw.split('const ASSETS=',1)[1].split(';',1)[0]
    assert "'/'" not in assets and "'/index.html'" not in assets
'''
    text = replace_once(text, marker, addition, "frontend hardening validator marker")
    path.write_text(text, encoding="utf-8")


def main():
    update_dashboard()
    update_index()
    update_service_worker()
    update_app_js()
    update_css()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert "function bindAddTorrentUI()" in app
    assert "event.request.mode==='navigate'" in sw
    print("Applied v0.5.47 frontend generation and startup hardening")


if __name__ == "__main__":
    main()
