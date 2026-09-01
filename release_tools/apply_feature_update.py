from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")

def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected exactly one match, found {count}")
    write(rel, text.replace(old, new, 1))

def replace_all(rel, old, new, minimum=1):
    text = read(rel)
    count = text.count(old)
    if count < minimum:
        raise RuntimeError(f"{rel}: expected at least {minimum} matches, found {count}")
    write(rel, text.replace(old, new))

replace_once("dashboard.py", 'VERSION = "0.5.26"', 'VERSION = "0.5.27"')
replace_once(
    "dashboard.py",
    '''self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'")''',
    '''self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'")'''
)

replace_once(
    "static/index.html",
    '''<link href="/manifest.webmanifest" rel="manifest"/>
<link href="/static/app.css?v=0.5.26" rel="stylesheet"/>''',
    '''<link href="/manifest.webmanifest" rel="manifest"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..24,400,0,0&amp;icon_names=visibility,visibility_lock" rel="stylesheet"/>
<link href="/static/app.css?v=0.5.26" rel="stylesheet"/>'''
)

replace_once(
    "static/index.html",
    '''<div class="panel settings-card"><div class="panel-title">Clients</div><p class="muted client-settings-intro">Manage each download client connection here. Live qBitTorrent transfer preferences are available from Client Settings on each saved client.</p><div id="serverSettings"></div><button id="addServerSetting" type="button">＋ Add Server</button></div>''',
    '''<div class="panel settings-card"><div class="panel-title">Clients</div><p class="muted client-settings-intro">Manage each download client connection here. Use Settings on a saved client for its live qBitTorrent transfer preferences.</p><div id="serverSettings"></div><button id="addServerSetting" type="button">＋ Add Server</button></div>'''
)

replace_once(
    "static/index.html",
    '''<div class="modal hidden" id="clientSettingsModal"><div class="modal-backdrop" data-client-settings-close=""></div><form class="modal-card client-settings-card" id="clientSettingsForm"><header><div><h2>Client settings</h2><p id="clientSettingsClientName">qBitTorrent</p></div><button class="icon-btn" data-client-settings-close="" type="button" aria-label="Close client settings">×</button></header><div class="client-settings-body"><section class="client-settings-section"><div class="client-settings-section-title">Transfer limits</div><label class="toggle client-alt-speed"><input id="clientAltSpeed" type="checkbox"/><span>Alternative speed limits</span></label><div class="field-help">Uses qBitTorrent's alternative speed-limit mode for this client only.</div><div class="client-limit-grid"><label>Global download limit <span>KB/s</span><input id="clientGlobalDl" min="0" step="1" type="number" value="0"/></label><label>Global upload limit <span>KB/s</span><input id="clientGlobalUl" min="0" step="1" type="number" value="0"/></label></div><div class="field-help">Use 0 for unlimited. Values are read from and written directly to the selected qBitTorrent instance.</div></section><div class="test-result muted" id="clientSettingsStatus"></div></div><footer class="client-settings-actions"><button class="primary" id="saveClientSettings" type="submit">Save client settings</button><button class="secondary" data-client-settings-close="" type="button">Cancel</button></footer></form></div>''',
    '''<div class="modal hidden" id="clientSettingsModal"><div class="modal-backdrop" data-client-settings-close=""></div><form class="modal-card client-settings-card" id="clientSettingsForm"><header><div><h2>Settings</h2><p id="clientSettingsClientName">qBitTorrent</p></div><button class="icon-btn" data-client-settings-close="" type="button" aria-label="Close settings">×</button></header><div class="client-settings-body"><section class="client-settings-section"><div class="client-settings-section-heading"><strong>Transfer limits</strong><span>Control the global speed limits for this qBitTorrent client.</span></div><label class="client-setting-row"><span class="client-setting-copy"><strong>Alternative speed limits</strong><span>Use qBitTorrent's alternative rate profile for this client.</span></span><span class="client-switch"><input id="clientAltSpeed" type="checkbox"/><span aria-hidden="true"></span></span></label><div class="client-settings-divider" aria-hidden="true"></div><div class="client-limit-grid"><label><span>Download limit</span><span class="client-limit-input"><input id="clientGlobalDl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label><label><span>Upload limit</span><span class="client-limit-input"><input id="clientGlobalUl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label></div><p class="client-settings-note">Changes are read from and written directly to this qBitTorrent client.</p></section><div class="client-settings-status muted" id="clientSettingsStatus"></div></div><footer class="client-settings-actions"><button class="primary" id="saveClientSettings" type="submit">Save</button><button class="secondary" data-client-settings-close="" type="button">Cancel</button></footer></form></div>'''
)

replace_all("static/index.html", "0.5.26", "0.5.27", minimum=4)

old_secret = '''function syncSecretToggle(input){
  const btn=input?.parentElement?.querySelector('.secret-toggle');
  if(!btn)return;
  const value=input.value||'';
  const stored=input.dataset.configuredSecret==='1'&&(value===CONFIGURED_SECRET_MASK||value===''||value.includes('•'));
  if(stored){
    input.type='password';
    btn.disabled=true;
    btn.textContent='Stored';
    btn.setAttribute('aria-label','Stored secret cannot be revealed');
    btn.title='Stored secrets are not sent back to the browser. Delete the mask and enter a new value to replace it.';
    return;
  }
  btn.disabled=false;
  btn.removeAttribute('title');
  const showing=input.type==='text';
  btn.textContent=showing?'Hide':'Show';
  btn.setAttribute('aria-label',showing?'Hide secret':'Show secret');
}
'''
new_secret = '''function setSecretToggleIcon(btn,name){btn.innerHTML=`<span class="material-symbols-outlined" aria-hidden="true">${name}</span>`;btn.dataset.materialSymbol=name}
function syncSecretToggle(input){
  const wrap=input?.closest?.('.secret-input');
  const btn=wrap?.querySelector('.secret-toggle');
  if(!btn)return;
  const value=input.value||'';
  const stored=input.dataset.configuredSecret==='1'&&(value===CONFIGURED_SECRET_MASK||value===''||value.includes('•'));
  wrap.classList.toggle('stored-secret',stored);
  btn.hidden=stored;
  if(stored){
    input.type='password';
    btn.innerHTML='';
    btn.removeAttribute('aria-label');
    btn.removeAttribute('title');
    return;
  }
  const showing=input.type==='text';
  setSecretToggleIcon(btn,showing?'visibility_lock':'visibility');
  btn.setAttribute('aria-label',showing?'Hide secret':'Show secret');
  btn.title=showing?'Hide secret':'Show secret';
}
'''
replace_once("static/app.js", old_secret, new_secret)
replace_once(
    "static/app.js",
    '''const btn=document.createElement('button');btn.type='button';btn.className='secret-toggle';btn.textContent='Show';btn.setAttribute('aria-label','Show secret');
    btn.addEventListener('click',()=>{if(btn.disabled)return;const showing=input.type==='text';input.type=showing?'password':'text';syncSecretToggle(input)});''',
    '''const btn=document.createElement('button');btn.type='button';btn.className='secret-toggle';setSecretToggleIcon(btn,'visibility');btn.setAttribute('aria-label','Show secret');
    btn.addEventListener('click',()=>{const showing=input.type==='text';input.type=showing?'password':'text';syncSecretToggle(input)});'''
)
replace_once(
    "static/app.js",
    '''<button type="button" class="secondary client-settings" ${s.id?'':'disabled'}>Client Settings</button>''',
    '''<button type="button" class="secondary client-settings" ${s.id?'':'disabled'}>Settings</button>'''
)

replace_once(
    "static/settings.js",
    '''if (name) name.textContent = server?.name || serverId;''',
    '''if (name) name.textContent = `${server?.name || serverId} · qBitTorrent`;'''
)
replace_once(
    "static/settings.js",
    '''status.className = `test-result ${tone}`;''',
    '''status.className = `client-settings-status ${tone}`;'''
)

replace_once(
    "static/app.css",
    '''.secret-input{position:relative;display:flex;align-items:center;width:100%}.secret-input input{width:100%;padding-right:58px!important}.secret-toggle{position:absolute;right:6px;top:50%;transform:translateY(-50%);min-width:46px;height:28px;padding:0 8px;border:1px solid var(--border);border-radius:8px;background:var(--panel3);color:var(--muted);font-size:9px;line-height:1;z-index:2}.secret-toggle:hover{color:var(--text);background:var(--panel2)}''',
    '''.material-symbols-outlined{font-family:"Material Symbols Outlined";font-weight:normal;font-style:normal;font-size:20px;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;font-feature-settings:"liga";-webkit-font-feature-settings:"liga";-webkit-font-smoothing:antialiased}.secret-input{position:relative;display:flex;align-items:center;width:100%}.secret-input input{width:100%;padding-right:44px!important}.secret-input.stored-secret input{padding-right:11px!important}.secret-toggle{position:absolute;right:5px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:32px;min-width:32px;height:32px;padding:0;border:0;border-radius:8px;background:transparent;color:var(--muted);line-height:1;z-index:2}.secret-toggle .material-symbols-outlined{font-size:19px}.secret-toggle:hover{color:var(--text);background:var(--panel2)}.secret-toggle:focus-visible{outline:none;box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 24%,transparent)}'''
)

replace_once(
    "static/settings.css",
    '''.secret-input .secret-toggle:disabled{cursor:default;opacity:.62;color:var(--muted);background:var(--panel2);border-color:var(--border)}.secret-configured{letter-spacing:.08em}''',
    '''.secret-input.stored-secret .secret-toggle{display:none}.secret-configured{letter-spacing:.08em}'''
)

old_client_css = '''/* 0.5.26 per-client qBitTorrent settings */
.client-settings-intro{margin:0 0 14px;line-height:1.5;font-size:10.5px}
.server-setting-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.server-setting-actions .client-settings:disabled{opacity:.45;cursor:not-allowed}.client-settings-card{width:min(620px,calc(100% - 24px));padding-bottom:0}.client-settings-card header p{margin:5px 0 0;color:var(--muted);font-size:10px}.client-settings-body{display:grid;gap:12px;padding:16px}.client-settings-section{padding:14px;border:1px solid var(--border);border-radius:13px;background:var(--panel3)}.client-settings-section-title{font-size:12px;font-weight:700;margin-bottom:13px}.client-alt-speed{margin:0 0 8px!important;color:var(--text)!important;font-size:11px!important}.client-limit-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.client-limit-grid label{display:grid;grid-template-columns:1fr auto;gap:6px;align-items:end;margin:0;color:var(--muted);font-size:10px}.client-limit-grid label>span{font-size:8px}.client-limit-grid input{grid-column:1/-1;width:100%}.client-settings-actions{display:flex;justify-content:flex-end;gap:8px;padding:13px 16px 16px;border-top:1px solid var(--border)}.client-settings-actions button{min-width:130px}
@media(max-width:620px){.client-limit-grid{grid-template-columns:1fr}.client-settings-actions{display:grid;grid-template-columns:1fr 1fr}.client-settings-actions button{min-width:0;width:100%}}
@media(max-width:440px){.client-settings-actions{grid-template-columns:1fr}.client-settings-intro{font-size:9.5px}}
'''
new_client_css = '''/* 0.5.27 client settings facelift */
.client-settings-intro{margin:0 0 14px;line-height:1.5;font-size:10.5px}
.server-setting-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.server-setting-actions .client-settings:disabled{opacity:.45;cursor:not-allowed}
.client-settings-card{width:min(560px,calc(100% - 24px));padding-bottom:0;overflow:hidden}.client-settings-card header{align-items:center;padding:19px 20px 17px}.client-settings-card header h2{font-size:18px}.client-settings-card header p{margin:5px 0 0;color:var(--muted);font-size:10px}
.client-settings-body{display:grid;gap:18px;padding:20px}.client-settings-section{display:grid;min-width:0}.client-settings-section-heading{display:grid;gap:4px;margin-bottom:3px}.client-settings-section-heading strong{font-size:13px;color:var(--text)}.client-settings-section-heading span{font-size:9.5px;line-height:1.45;color:var(--muted)}
.client-setting-row{display:flex!important;align-items:center!important;justify-content:space-between;gap:18px;margin:0!important;padding:15px 0!important;color:var(--text)!important}.client-setting-copy{display:grid;gap:4px;min-width:0}.client-setting-copy strong{font-size:11.5px}.client-setting-copy>span{font-size:9.5px;line-height:1.45;color:var(--muted)}
.client-switch{position:relative;display:block;flex:0 0 auto;width:40px;height:23px}.client-switch input{position:absolute!important;width:1px!important;height:1px!important;opacity:0;pointer-events:none}.client-switch>span{display:block;width:40px;height:23px;border:1px solid var(--border);border-radius:999px;background:var(--panel3);transition:background .15s,border-color .15s,box-shadow .15s}.client-switch>span:after{content:"";position:absolute;left:4px;top:4px;width:15px;height:15px;border-radius:50%;background:var(--muted);transition:transform .15s,background .15s}.client-switch input:checked+span{background:color-mix(in srgb,var(--accent) 18%,var(--panel3));border-color:color-mix(in srgb,var(--accent) 55%,var(--border))}.client-switch input:checked+span:after{transform:translateX(17px);background:var(--accent)}.client-switch input:focus-visible+span{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 13%,transparent)}
.client-settings-divider{height:1px;background:color-mix(in srgb,var(--border) 78%,transparent)}.client-limit-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:17px}.client-limit-grid label{display:grid!important;gap:7px!important;margin:0!important;color:var(--text)!important;font-size:10.5px!important}.client-limit-grid label>span:first-child{font-weight:600}.client-limit-input{position:relative;display:block}.client-limit-input input{width:100%;min-height:42px;padding-right:58px!important}.client-limit-input>span{position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:8.5px;color:var(--muted);pointer-events:none}.client-limit-grid small{font-size:9px;color:var(--muted)}.client-settings-note{margin:15px 0 0;color:var(--muted);font-size:9.5px;line-height:1.5}
.client-settings-status{display:flex;align-items:center;gap:8px;min-height:18px;color:var(--muted);font-size:9.5px;line-height:1.4}.client-settings-status:before{content:"";width:7px;height:7px;flex:0 0 auto;border-radius:50%;background:var(--muted)}.client-settings-status.ok{color:var(--good)}.client-settings-status.ok:before{background:var(--good)}.client-settings-status.bad{color:var(--bad)}.client-settings-status.bad:before{background:var(--bad)}
.client-settings-actions{display:flex;justify-content:flex-end;gap:8px;padding:14px 20px 18px;border-top:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 45%,transparent)}.client-settings-actions button{min-width:96px}
@media(max-width:620px){#clientSettingsModal{place-items:end center;padding:0}.client-settings-card{width:100%;max-height:min(88vh,720px);border-radius:18px 18px 0 0;border-bottom:0}.client-settings-body{padding:18px}.client-settings-actions{padding:13px 18px calc(18px + env(safe-area-inset-bottom))}}
@media(max-width:500px){.client-limit-grid{grid-template-columns:1fr}.client-settings-actions{display:grid;grid-template-columns:1fr 1fr}.client-settings-actions button{width:100%;min-width:0}.client-settings-intro{font-size:9.5px}}
'''
replace_once("static/settings.css", old_client_css, new_client_css)

replace_all("static/sw.js", "0.5.26", "0.5.27", minimum=4)
replace_once("static/sw.js", "torrent-dashboard-v0526", "torrent-dashboard-v0527")

print("Applied 0.5.27 settings facelift.")
