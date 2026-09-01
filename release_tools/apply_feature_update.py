#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OLD='0.5.22'; NEW='0.5.23'
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')

# Version and Windows background interface detection.
dashboard=read('dashboard.py')
dashboard,n=re.subn(r'^VERSION\s*=\s*["\'][^"\']+["\']',f'VERSION = "{NEW}"',dashboard,count=1,flags=re.M); assert n==1
old='''def _detect_windows_interfaces():
    try:
        out = subprocess.check_output(["ipconfig"], text=True, errors="replace", timeout=4)
        return _parse_windows_interfaces(out)
    except Exception:
        return []
'''
new='''def _windows_background_process_kwargs():
    if os.name != "nt":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flags} if flags else {}


def _detect_windows_interfaces():
    try:
        out = subprocess.check_output(["ipconfig"], text=True, errors="replace", timeout=4, **_windows_background_process_kwargs())
        return _parse_windows_interfaces(out)
    except Exception:
        return []
'''
assert old in dashboard; dashboard=dashboard.replace(old,new,1); write('dashboard.py',dashboard)

# Notification settings UI.
html=read('static/index.html').replace(OLD,NEW)
old='<div class="settings-inline-actions notification-actions"><button class="secondary" id="previewSound" type="button">Preview Sound</button><button class="secondary" id="settingsNotifyPermission" type="button">Request Browser Permission</button></div>'
new='<div class="settings-inline-actions notification-actions"><button class="secondary" id="testNotification" type="button">Test Notification</button></div>'
assert old in html; html=html.replace(old,new,1)
html=html.replace('Preview the sound once to confirm this browser can play notification audio.','Test browser notifications and completion audio. Browser permission is requested during the test when needed.')
html=html.replace('<button id="notifyPermission">Enable Browser Notifications</button>','')
write('static/index.html',html)

# Browser notification helper and completion path.
app=read('static/app.js')
needle="async function playCompletionSound(){if(!state.settings?.notifications?.sound)return;const n=state.settings.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}\n"
helper="async function showBrowserNotification(title,options={}){if(!('Notification'in window))throw new Error('Browser notifications are not supported');if(Notification.permission!=='granted')throw new Error('Browser notification permission is not granted');if('serviceWorker'in navigator){try{const reg=await navigator.serviceWorker.ready;if(reg?.showNotification){await reg.showNotification(title,options);return}}catch{}}new Notification(title,options)}\n"
assert needle in app; app=app.replace(needle,needle+helper,1)
old="if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')new Notification('torrentCompleted',{body:t.name})"
new="if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')showBrowserNotification(state.settings?.dashboard?.title||'Torrent Dashboard',{body:`Completed: ${t.name}`,tag:`torrent-complete-${k}`}).catch(()=>{})"
assert old in app; app=app.replace(old,new,1)
app=re.sub(r"\n\s*\$\('#notifyPermission'\)\.addEventListener\('click',async\(\)=>\{if\('Notification'in window\)\{const p=await Notification\.requestPermission\(\);toast\(`Notification permission: \$\{p\}`\)\}\}\);",'',app,count=1)
assert '#notifyPermission' not in app; write('static/app.js',app)

# Test notification requests permission only as part of the test gesture.
settings=read('static/settings.js')
settings=settings.replace("    document.querySelector('#previewSound')?.addEventListener('click', previewNotificationSound);\n","    document.querySelector('#testNotification')?.addEventListener('click', testNotification);\n")
settings=settings.replace("    document.querySelector('#settingsNotifyPermission')?.addEventListener('click', requestBrowserNotificationPermission);\n",'')
start=settings.index('  async function previewNotificationSound() {'); end=settings.index('  function updateSourceRepository() {',start)
block='''  async function testNotification() {
    const status = document.querySelector('#soundStatus');
    const browserEnabled = !!document.querySelector('#nBrowser')?.checked;
    const soundEnabled = !!document.querySelector('#nSound')?.checked;
    if (!browserEnabled && !soundEnabled) {
      if (status) { status.className='test-result bad'; status.textContent='Enable browser notifications or completion sound before testing.'; }
      return;
    }
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = document.querySelector('#nSoundFile')?.files?.[0];
    let soundUrl = '';
    let revoke = false;
    if (soundEnabled) {
      if (mode === 'custom' && file) { soundUrl=URL.createObjectURL(file); revoke=true; }
      else if (mode === 'custom') soundUrl=`/api/notification-sound?ts=${Date.now()}`;
      else soundUrl=`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version || '')}`;
    }
    try {
      if (status) { status.className='test-result muted'; status.textContent='Testing notification…'; }
      const tested=[];
      if (browserEnabled) {
        if (!('Notification' in window)) throw new Error('Browser notifications are not supported by this browser.');
        let permission=Notification.permission;
        if (permission==='default') permission=await Notification.requestPermission();
        if (permission!=='granted') throw new Error(permission==='denied' ? "Browser notification permission is blocked. Enable it in this site's browser permissions." : 'Browser notification permission was not granted.');
        await showBrowserNotification(state.settings?.dashboard?.title || 'Torrent Dashboard',{body:'This is a test notification from Torrent Dashboard.',tag:'torrent-dashboard-test'});
        tested.push('browser notification');
      }
      if (soundEnabled) { await playSoundUrl(soundUrl); tested.push('completion sound'); }
      if (status) { status.className='test-result ok'; status.textContent=`Test successful: ${tested.join(' and ')}.`; }
    } catch(e) {
      if (status) { status.className='test-result bad'; status.textContent=e.message || 'Notification test failed.'; }
    } finally { if (revoke) URL.revokeObjectURL(soundUrl); }
  }

'''
settings=settings[:start]+block+settings[end:]
assert 'previewNotificationSound' not in settings and 'requestBrowserNotificationPermission' not in settings

# Inline required markers and full-width User Group control.
repls={
'<label>Username <span class="required-mark" aria-hidden="true">*</span><input':'<label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input',
'<label>User Group <span class="required-mark" aria-hidden="true">*</span><select data-user-field="group"':'<label><span class="field-label">User Group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group"',
'<label>Password <span class="required-mark" aria-hidden="true">*</span><input':'<label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input',
'<label>Confirm Password <span class="required-mark" aria-hidden="true">*</span><input':'<label><span class="field-label">Confirm Password <span class="required-mark" aria-hidden="true">*</span></span><input'}
for a,b in repls.items(): assert a in settings; settings=settings.replace(a,b,1)
write('static/settings.js',settings)

css=read('static/settings.css')+'''\n\n/* 0.5.23 user-form alignment and notification test polish. */
.field-label{display:inline-flex;align-items:baseline;gap:3px;line-height:1.25;min-width:0}
.required-mark{margin-left:0!important;color:#ff5d6c;font-weight:800}
.user-group-select{display:block;width:100%;min-width:0}
@media(min-width:821px){.user-group-badge{min-width:112px;text-align:center}}
@media(max-width:820px){.user-group-badge{min-width:0;text-align:center}}
.notification-actions #testNotification{min-width:170px}
'''
write('static/settings.css',css)

sw=read('static/sw.js').replace(OLD,NEW).replace('torrent-dashboard-v0522','torrent-dashboard-v0523'); write('static/sw.js',sw)

validator=read('release_tools/validate_ui_strings.py')
anchor="    assert '.required-mark{color:#ff5d6c' in settings_css\n"
extra=anchor+"    assert 'class=\"field-label\">Username <span class=\"required-mark\"' in settings_js\n    assert 'class=\"user-group-select\"' in settings_js\n    assert '.user-group-select{display:block;width:100%' in settings_css\n    assert 'id=\"testNotification\"' in html\n    assert 'settingsNotifyPermission' not in html and 'settingsNotifyPermission' not in settings_js\n    assert 'id=\"notifyPermission\"' not in html and '#notifyPermission' not in app_js\n    assert 'async function testNotification()' in settings_js\n    assert 'Notification.requestPermission()' in settings_js\n    assert 'async function showBrowserNotification' in app_js\n    assert 'CREATE_NO_WINDOW' in dashboard_py and '**_windows_background_process_kwargs()' in dashboard_py\n"
assert anchor in validator; validator=validator.replace(anchor,extra,1); write('release_tools/validate_ui_strings.py',validator)

assert 'VERSION = "0.5.23"' in read('dashboard.py')
assert '?v=0.5.23' in read('static/sw.js')
print('Staged Torrent Dashboard 0.5.23 notification and Windows UI polish')
