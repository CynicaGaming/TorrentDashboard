#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "93b9b1dc978b44a7b3eea89c496a03af6c6bd14c"  # v0.5.38 materialized source
RESTORE = (
    "dashboard.py",
    "static/app.js",
    "static/app.css",
    "static/index.html",
    "static/sw.js",
    "release_tools/validate_ui_strings.py",
)


def git_show(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True, encoding="utf-8"
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match for {label}, found {count}")
    return text.replace(old, new, 1)


for rel in RESTORE:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(git_show(rel), encoding="utf-8")

# Keep the recovery updater/launchers and diagnostic settings.js from 0.5.40,
# but put the application runtime itself back on the known-good 0.5.38 base.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text = replace_once(text, 'VERSION = "0.5.38"', 'VERSION = "0.5.41"', "dashboard version")

old_get = '        path,_,query=self.path.partition("?"); qs=urllib.parse.parse_qs(query)\n        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION,"pid":os.getpid(),"application":str(APP_DIR),"python":sys.executable})'
new_get = '''        path,_,query=self.path.partition("?"); qs=urllib.parse.parse_qs(query)\n        # A service worker can briefly retain an older HTML shell across an update.\n        # Static query versions are cache keys only, so without this guard an old\n        # shell could execute a newer app.js against incompatible DOM. When that\n        # happens, serve a tiny recovery script instead of mixed-generation code.\n        if path in ("/static/settings.js", "/static/app.js"):\n            requested = str(qs.get("v", [""])[0] or "")\n            if requested and requested != VERSION:\n                recovery = f"""\nconsole.warn('[Torrent Dashboard] Frontend build mismatch: requested {requested}, server {VERSION}. Clearing stale application caches.');\n(async()=>{{\n  try{{\n    if('serviceWorker' in navigator){{\n      const regs=await navigator.serviceWorker.getRegistrations();\n      await Promise.all(regs.map(reg=>reg.unregister()));\n    }}\n    if('caches' in window){{\n      const keys=await caches.keys();\n      await Promise.all(keys.filter(key=>key.startsWith('torrent-dashboard-')).map(key=>caches.delete(key)));\n    }}\n  }}catch(error){{console.error('[Torrent Dashboard] Cache recovery failed',error)}}\n  finally{{location.replace('/?td-recover={VERSION}&ts='+Date.now())}}\n}})();\n""".encode("utf-8")\n                return self.send_bytes(200,recovery,"application/javascript; charset=utf-8")\n        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION,"pid":os.getpid(),"application":str(APP_DIR),"python":sys.executable})'''
text = replace_once(text, old_get, new_get, "static build mismatch guard")
dashboard.write_text(text, encoding="utf-8")

index = ROOT / "static/index.html"
text = index.read_text(encoding="utf-8")
if text.count("0.5.38") < 4:
    raise SystemExit("Unexpected v0.5.38 index asset references")
index.write_text(text.replace("0.5.38", "0.5.41"), encoding="utf-8")

# Preserve console diagnostics from 0.5.40. Add fetch-level diagnostics so even
# errors caught by normal UI code remain visible in DevTools.
settings = ROOT / "static/settings.js"
text = settings.read_text(encoding="utf-8")
needle = "  window.__tdMarkReady=stage=>{window.__tdStartupStage=stage||'ready';window.__tdBootstrapReady=true;console.info(`${PREFIX} startup complete: ${window.__tdStartupStage}`)};\n"
addition = '''  window.__tdMarkReady=stage=>{window.__tdStartupStage=stage||'ready';window.__tdBootstrapReady=true;console.info(`${PREFIX} startup complete: ${window.__tdStartupStage}`)};\n  if(typeof window.fetch==='function'&&!window.__tdFetchDiagnostics){\n    window.__tdFetchDiagnostics=true;\n    const nativeFetch=window.fetch.bind(window);\n    window.fetch=async function(input,init={}){\n      const url=typeof input==='string'?input:(input?.url||String(input||''));\n      const method=String(init?.method||'GET').toUpperCase();\n      const started=performance?.now?.()||Date.now();\n      try{\n        const response=await nativeFetch(input,init);\n        if(!response.ok&&response.status!==401)report('HTTP request failure',new Error(`${method} ${url} returned HTTP ${response.status}`),{url,method,status:response.status});\n        return response;\n      }catch(error){report('network request failure',error,{url,method});throw error}\n      finally{const elapsed=(performance?.now?.()||Date.now())-started;if(elapsed>5000)console.warn(`${PREFIX} slow request: ${method} ${url} (${Math.round(elapsed)} ms)`)}\n    };\n  }\n'''
text = replace_once(text, needle, addition, "fetch diagnostics")
settings.write_text(text, encoding="utf-8")

app = ROOT / "static/app.js"
text = app.read_text(encoding="utf-8")
old_bootstrap_start = "async function bootstrap(){\n  bindPublicUI();\n  try{"
new_bootstrap_start = "async function bootstrap(){\n  window.__tdMarkStartupStage?.('binding public UI');\n  try{bindPublicUI()}catch(e){window.__tdReportError?.('public UI binding',e);throw e}\n  try{\n    window.__tdMarkStartupStage?.('checking setup status');"
text = replace_once(text, old_bootstrap_start, new_bootstrap_start, "bootstrap diagnostics start")
old_session = "    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();"
new_session = "    window.__tdMarkStartupStage?.('loading session');state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();"
text = replace_once(text, old_session, new_session, "session startup stage")
old_tail = "    await loadServers();bindUI();applyPrefs();await refreshStatus();scheduleRefresh();registerPwa();\n  }\n  catch(e){if(!$('#login').classList.contains('hidden'))return;toast(e.message,'error')}"
new_tail = "    window.__tdMarkStartupStage?.('loading clients');await loadServers();window.__tdMarkStartupStage?.('binding dashboard UI');bindUI();applyPrefs();window.__tdMarkStartupStage?.('loading torrent status');await refreshStatus();scheduleRefresh();registerPwa();window.__tdMarkReady?.('dashboard ready');\n  }\n  catch(e){window.__tdBootstrapFailed=true;window.__tdReportError?.('dashboard bootstrap',e,{stage:window.__tdStartupStage||'unknown'});if(!$('#login').classList.contains('hidden')){window.__tdMarkReady?.('login');return}showApp();const banner=$('#errorBanner');if(banner){banner.textContent=`Startup failed: ${e.message}. Open the browser developer console for details.`;banner.classList.remove('hidden')}try{toast(e.message,'error')}catch{}}"
text = replace_once(text, old_tail, new_tail, "bootstrap diagnostics tail")
app.write_text(text, encoding="utf-8")

# Do not cache navigations. An offline application shell has little value for a
# local dashboard whose backend is unavailable, and it is dangerous at an update
# boundary because HTML and JavaScript must come from the same build.
sw = ROOT / "static/sw.js"
sw.write_text("""const CACHE='torrent-dashboard-v0541';\nconst ASSETS=['/static/app.css?v=0.5.41','/static/settings.css?v=0.5.41','/static/settings.js?v=0.5.41','/static/app.js?v=0.5.41','/manifest.webmanifest'];\nself.addEventListener('install',event=>{self.skipWaiting();event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)))});\nself.addEventListener('activate',event=>event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),self.clients.claim()])));\nself.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.pathname.startsWith('/api/')||event.request.mode==='navigate'||url.pathname==='/'||url.pathname==='/index.html')return;event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy))}return response}).catch(()=>caches.match(event.request)))});\n""", encoding="utf-8")

# The restored validator matches the stable runtime. Add recovery-specific checks.
validator = ROOT / "release_tools/validate_ui_strings.py"
text = validator.read_text(encoding="utf-8")
marker = '    print("UI string audit passed")\n'
checks = '''    assert 'Frontend build mismatch' in dashboard_py\n    assert 'requested != VERSION' in dashboard_py\n    assert "event.request.mode==='navigate'" in sw\n    assert "url.pathname==='/'" in sw\n    assert '[Torrent Dashboard]' in settings_js\n    assert '__tdFetchDiagnostics' in settings_js\n    assert '__tdReportError' in app_js\n    print("UI string audit passed")\n'''
text = replace_once(text, marker, checks, "recovery validator checks")
validator.write_text(text, encoding="utf-8")

# Feature-specific sanity checks before the normal release validation.
assert 'VERSION = "0.5.41"' in dashboard.read_text(encoding="utf-8")
assert 'id="drawer"' in index.read_text(encoding="utf-8")
assert 'id="torrentDetailPane"' not in index.read_text(encoding="utf-8")
assert 'fetch_torrent_metadata' not in dashboard.read_text(encoding="utf-8")
assert 'Metadata retrieval complete' not in app.read_text(encoding="utf-8")
assert (ROOT / "Update Dashboard.bat").exists()
assert '--github-update' in (ROOT / "updater.py").read_text(encoding="utf-8")

print("Applied 0.5.41 stable runtime and cache-boundary recovery update")
