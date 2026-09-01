#!/usr/bin/env python3
from pathlib import Path
import math
import re
import struct
import wave

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.4"
NEW = "0.5.5"


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


def sub_once(text, pattern, repl, label, flags=0):
    out, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one {label}, replaced {count}")
    return out


def patch_dashboard():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
    text = replace_once(
        text,
        'UPDATE_STATE_PATH = DATA_DIR / "update-status.json"\n',
        'UPDATE_STATE_PATH = DATA_DIR / "update-status.json"\nCUSTOM_SOUND_BASENAME = "custom-notification-sound"\nMAX_CUSTOM_SOUND_BYTES = 2 * 1024 * 1024\n',
        "custom sound constants",
    )

    text = sub_once(
        text,
        r'    "notifications": \{.*?\n    \},\n    "integrations": \[\]',
        '''    "notifications": {
        "browser": True,
        "sound": False,
        "sound_mode": "default",
        "custom_sound_file": "",
        "custom_sound_name": "",
        "custom_sound_mime": ""
    },
    "integrations": []''',
        "default notification settings",
        re.S,
    )

    integration_insert = '''    "discord": {
        "label": "Discord",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "placeholder": "https://discord.com/api/webhooks/...", "secret": True, "required": True},
        ],
    },
    "ntfy": {
        "label": "ntfy",
        "fields": [
            {"key": "topic_url", "label": "Topic URL", "placeholder": "https://ntfy.sh/topic", "required": True},
            {"key": "access_token", "label": "Access Token", "secret": True, "required": False},
        ],
    },
    "generic_webhook": {
        "label": "Generic Webhook",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "placeholder": "https://example.com/webhook", "secret": True, "required": True},
        ],
    },
'''
    text = replace_once(text, '    "home_assistant": {\n', integration_insert + '    "home_assistant": {\n', "notification integration catalog")

    migration = '''    # Notification delivery endpoints moved into Integrations in 0.5.5.
    # Preserve existing configured destinations without exposing legacy fields
    # on the Notifications page.
    legacy_notifications = raw.get("notifications", {}) if isinstance(raw.get("notifications"), dict) else {}
    legacy_destinations = [
        ("generic_webhook", "webhook_url", str(legacy_notifications.get("webhook_url") or "").strip()),
        ("discord", "webhook_url", str(legacy_notifications.get("discord_webhook") or "").strip()),
        ("ntfy", "topic_url", str(legacy_notifications.get("ntfy_url") or "").strip()),
    ]
    for provider, field, value in legacy_destinations:
        if not value:
            continue
        if any(item.get("type") == provider and item.get(field) == value for item in merged.get("integrations", [])):
            continue
        payload = {"id": stable_record_id("integration", provider, value), "type": provider, "name": INTEGRATION_TYPES[provider]["label"], field: value, "enabled": True}
        try:
            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))
        except Exception:
            pass
    for legacy_key in ("webhook_url", "discord_webhook", "ntfy_url"):
        merged.setdefault("notifications", {}).pop(legacy_key, None)

'''
    text = replace_once(text, '    sync_legacy_auth(merged)\n    return merged\n', migration + '    sync_legacy_auth(merged)\n    return merged\n', "legacy notification migration")

    send_func = '''def send_notification(cfg, title, message):
    for integration in cfg.get("integrations", []):
        if not integration.get("enabled", True):
            continue
        provider = integration.get("type")
        try:
            if provider == "generic_webhook" and integration.get("webhook_url"):
                data = json.dumps({"title": title, "message": message}).encode("utf-8")
                req = urllib.request.Request(integration["webhook_url"], data=data, headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=5).read()
            elif provider == "discord" and integration.get("webhook_url"):
                data = json.dumps({"content": f"**{title}**\\n{message}"}).encode("utf-8")
                req = urllib.request.Request(integration["webhook_url"], data=data, headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=5).read()
            elif provider == "ntfy" and integration.get("topic_url"):
                headers = {"Title": title.encode("ascii", "ignore").decode() or "Torrent Dashboard"}
                if integration.get("access_token"):
                    headers["Authorization"] = f"Bearer {integration['access_token']}"
                req = urllib.request.Request(integration["topic_url"], data=message.encode("utf-8"), headers=headers, method="POST")
                urllib.request.urlopen(req, timeout=5).read()
            elif provider == "home_assistant" and integration.get("webhook_url"):
                data = json.dumps({"title": title, "message": message}).encode("utf-8")
                req = urllib.request.Request(integration["webhook_url"], data=data, headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass

    # Keep manually configured legacy Gotify/Telegram delivery working until
    # those destinations are promoted into the modular Integrations catalog.
    n = cfg.get("notifications", {})
    if n.get("gotify_url") and n.get("gotify_token"):
        try:
            url = n["gotify_url"].rstrip("/") + "/message?token=" + urllib.parse.quote(n["gotify_token"])
            data = json.dumps({"title": title, "message": message, "priority": 5}).encode("utf-8")
            urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST"), timeout=5).read()
        except Exception:
            pass
    if n.get("telegram_bot_token") and n.get("telegram_chat_id"):
        try:
            url = f"https://api.telegram.org/bot{n['telegram_bot_token']}/sendMessage"
            data = json.dumps({"chat_id": n["telegram_chat_id"], "text": f"{title}\\n{message}"}).encode("utf-8")
            urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST"), timeout=5).read()
        except Exception:
            pass
'''
    text = sub_once(text, r'def send_notification\(cfg, title, message\):.*?\n\ndef collector_loop', send_func + '\n\ndef collector_loop', "notification sender", re.S)

    connection_branches = '''        elif provider == "discord":
            body = json.dumps({"content": "Torrent Dashboard integration connection test"}).encode("utf-8")
            req = urllib.request.Request(item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "ntfy":
            headers = {"Title": "Torrent Dashboard Test"}
            if item.get("access_token"):
                headers["Authorization"] = f"Bearer {item['access_token']}"
            req = urllib.request.Request(item["topic_url"], data=b"Integration connection test", headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "generic_webhook":
            body = json.dumps({"title": "Torrent Dashboard Test", "message": "Integration connection test"}).encode("utf-8")
            req = urllib.request.Request(item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
'''
    text = replace_once(text, '        elif provider == "home_assistant":\n', connection_branches + '        elif provider == "home_assistant":\n', "notification integration tests")

    sound_helpers = '''SOUND_MIME_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg"}


def store_custom_notification_sound(cfg, filename, content):
    filename = Path(str(filename or "sound")).name
    ext = Path(filename).suffix.lower()
    if ext not in SOUND_MIME_TYPES:
        raise RuntimeError("Custom sound must be a WAV, MP3, or OGG file")
    if not content or len(content) > MAX_CUSTOM_SOUND_BYTES:
        raise RuntimeError("Custom sound must be between 1 byte and 2 MB")
    if ext == ".wav" and not (content.startswith(b"RIFF") and content[8:12] == b"WAVE"):
        raise RuntimeError("The selected WAV file is not valid")
    if ext == ".ogg" and not content.startswith(b"OggS"):
        raise RuntimeError("The selected OGG file is not valid")
    if ext == ".mp3" and not (content.startswith(b"ID3") or (len(content) > 1 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0)):
        raise RuntimeError("The selected MP3 file is not valid")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for old_ext in SOUND_MIME_TYPES:
        old = DATA_DIR / f"{CUSTOM_SOUND_BASENAME}{old_ext}"
        if old.exists():
            try: old.unlink()
            except Exception: pass
    dest = DATA_DIR / f"{CUSTOM_SOUND_BASENAME}{ext}"
    dest.write_bytes(content)
    out = json.loads(json.dumps(cfg))
    n = out.setdefault("notifications", {})
    n["custom_sound_file"] = dest.name
    n["custom_sound_name"] = filename[:255]
    n["custom_sound_mime"] = SOUND_MIME_TYPES[ext]
    return out, {"name": n["custom_sound_name"], "mime": n["custom_sound_mime"]}


def configured_notification_sound(cfg):
    n = cfg.get("notifications", {})
    name = Path(str(n.get("custom_sound_file") or "")).name
    if not name.startswith(CUSTOM_SOUND_BASENAME):
        return None, None
    path = DATA_DIR / name
    if not path.exists() or not path.is_file():
        return None, None
    mime = str(n.get("custom_sound_mime") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    return path, mime


'''
    text = replace_once(text, '\ndef normalize_github_repository(value: str) -> str:\n', '\n' + sound_helpers + 'def normalize_github_repository(value: str) -> str:\n', "custom sound helpers")

    get_target = '        if path=="/api/network/interfaces": return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")},new_cookie)\n        if path=="/api/update-check": return self.update_check(cfg,new_cookie)\n'
    get_repl = '''        if path=="/api/network/interfaces": return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")},new_cookie)
        if path=="/api/notification-sound":
            sound_path, sound_mime = configured_notification_sound(cfg)
            if not sound_path:
                return self.send_json(404,{"error":"No custom notification sound is configured"},new_cookie)
            return self.send_bytes(200,sound_path.read_bytes(),sound_mime,new_cookie)
        if path=="/api/update-check": return self.update_check(cfg,new_cookie)
'''
    text = replace_once(text, get_target, get_repl, "custom sound GET route")

    post_target = '            if path=="/api/notification-test":\n                send_notification(cfg,"Torrent Dashboard Test","Notifications are configured correctly.")\n                return self.send_json(200,{"ok":True},new_cookie)\n'
    post_repl = '''            if path=="/api/notification-sound":
                fields, files = parse_multipart(self, max_bytes=MAX_CUSTOM_SOUND_BYTES + 256000)
                if not files:
                    raise RuntimeError("Choose a custom sound file")
                _, filename, content = files[0]
                updated, info = store_custom_notification_sound(cfg, filename, content)
                save_config(updated)
                HISTORY.event("dashboard","notification_sound_changed",info.get("name", ""),"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True,**info},new_cookie)
            if path=="/api/notification-test":
                send_notification(cfg,"Torrent Dashboard Test","Notifications are configured correctly.")
                return self.send_json(200,{"ok":True},new_cookie)
'''
    text = replace_once(text, post_target, post_repl, "custom sound POST route")
    path.write_text(text, encoding="utf-8")


def patch_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8").replace(f'?v={OLD}', f'?v={NEW}')
    text = text.replace('<div class="two network-address-fields"><label>Local IP Address<input id="wLocalIp" readonly value="Detecting…"/></label><label>Port<input id="wPort"', '<div class="field-row local-address-heading"><div><b>Local Dashboard Address</b><small>Address used to reach Torrent Dashboard from your network.</small></div></div>\n<div class="two network-address-fields"><label>IP Address<input id="wLocalIp" readonly value="Detecting…"/></label><label>Port<input id="wPort"')
    text = text.replace('<label>Local IP Address<input id="sLocalIp" readonly value="—"/></label>', '<label>IP Address<input id="sLocalIp" readonly value="—"/></label>')

    notification_section = '''<section class="settings-page" data-settings-section="notifications">
<div class="panel settings-card notification-settings-card"><div class="panel-title">Notifications</div>
<p class="muted notification-intro">Configure notifications generated by this browser. External delivery services such as Discord, ntfy, and webhooks are managed under Integrations.</p>
<div class="notification-options">
<label class="toggle"><input id="nBrowser" type="checkbox"/><span>Browser Notifications</span></label>
<div class="field-help">Uses the browser and operating system notification permission for completion alerts.</div>
<label class="toggle"><input id="nSound" type="checkbox"/><span>Completion Sound</span></label>
<div class="notification-sound-config" id="notificationSoundConfig">
<label>Sound<select id="nSoundMode"><option value="default">Default Torrent Dashboard Sound</option><option value="custom">Custom Sound</option></select></label>
<div class="custom-sound-wrap hidden" id="nCustomSoundWrap">
<label>Custom Sound File<input accept="audio/wav,audio/mpeg,audio/ogg,.wav,.mp3,.ogg" id="nSoundFile" type="file"/></label>
<div class="configured-sound" id="nCustomSoundName">No Custom Sound Uploaded</div>
<div class="field-help">WAV, MP3, or OGG · Maximum 2 MB. Custom sounds are stored in the data directory and preserved during updates.</div>
</div>
<div class="settings-inline-actions notification-actions"><button class="secondary" id="previewSound" type="button">Preview Sound</button><button class="secondary" id="settingsNotifyPermission" type="button">Request Browser Permission</button></div>
<div class="test-result muted" id="soundStatus">Preview the sound once to confirm this browser can play notification audio.</div>
</div>
</div>
</div>
</section>'''
    text = sub_once(text, r'<section class="settings-page" data-settings-section="notifications">.*?</section>', notification_section, "notifications settings section", re.S)
    text = text.replace('No integrations are populated by default. Add only the services you use, test each connection, and save it independently.', 'No integrations are populated by default. Add media services or notification destinations only when you use them, test each connection, and save it independently.')
    path.write_text(text, encoding="utf-8")


def patch_settings_js():
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")

    old_bind = "    document.querySelector('#testNotify')?.addEventListener('click', () => post('/api/notification-test',{}).then(() => toast('testNotificationSent')).catch(e => toast(e.message,'error')));"
    new_bind = '''    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);
    document.querySelector('#nSoundFile')?.addEventListener('change', updateNotificationSoundUi);
    document.querySelector('#previewSound')?.addEventListener('click', previewNotificationSound);
    document.querySelector('#settingsNotifyPermission')?.addEventListener('click', requestBrowserNotificationPermission);'''
    text = replace_once(text, old_bind, new_bind, "notification event bindings")

    text = sub_once(
        text,
        r"    const n = s\.notifications \|\| \{\};\n    setChecked\('nBrowser'.*?setValue\('nNtfy'.*?;\n",
        '''    const n = s.notifications || {};
    setChecked('nBrowser', n.browser !== false);
    setChecked('nSound', n.sound);
    setValue('nSoundMode', n.sound_mode || 'default');
    const soundFile = document.querySelector('#nSoundFile');
    if (soundFile) soundFile.value = '';
    const soundName = document.querySelector('#nCustomSoundName');
    if (soundName) soundName.textContent = n.custom_sound_name || 'No Custom Sound Uploaded';
    updateNotificationSoundUi();
''',
        "notification settings fill",
        re.S,
    )

    text = sub_once(
        text,
        r"      notifications: \{\n        browser:.*?\n      \}\n",
        '''      notifications: {
        browser: document.querySelector('#nBrowser')?.checked !== false,
        sound: !!document.querySelector('#nSound')?.checked,
        sound_mode: document.querySelector('#nSoundMode')?.value || 'default'
      }
''',
        "notification save payload",
        re.S,
    )

    text = replace_once(text, "      const d = await post('/api/settings', payload);", "      await uploadNotificationSoundIfNeeded();\n      const d = await post('/api/settings', payload);", "custom sound upload before save")

    helpers = '''  function updateNotificationSoundUi() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const wrap = document.querySelector('#nCustomSoundWrap');
    if (wrap) wrap.classList.toggle('hidden', mode !== 'custom');
    const file = document.querySelector('#nSoundFile')?.files?.[0];
    const name = document.querySelector('#nCustomSoundName');
    if (name && file) name.textContent = file.name;
  }

  async function uploadNotificationSoundIfNeeded() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const input = document.querySelector('#nSoundFile');
    const file = input?.files?.[0];
    if (mode !== 'custom' || !file) return null;
    const form = new FormData();
    form.append('sound', file, file.name);
    const response = await fetch('/api/notification-sound', {method:'POST', headers:{'X-CSRF-Token':state.csrf}, body:form});
    const data = await response.json().catch(()=>({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    const name = document.querySelector('#nCustomSoundName');
    if (name) name.textContent = data.name || file.name;
    return data;
  }

  async function previewNotificationSound() {
    const status = document.querySelector('#soundStatus');
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = document.querySelector('#nSoundFile')?.files?.[0];
    let url = '';
    let revoke = false;
    if (mode === 'custom' && file) {
      url = URL.createObjectURL(file);
      revoke = true;
    } else if (mode === 'custom') {
      url = `/api/notification-sound?ts=${Date.now()}`;
    } else {
      url = `/static/default-completion.wav?v=${encodeURIComponent(state.me?.version || '')}`;
    }
    try {
      if (status) { status.className='test-result muted'; status.textContent='Playing Sound…'; }
      await playSoundUrl(url);
      if (status) { status.className='test-result ok'; status.textContent='Sound Playback Ready'; }
    } catch (e) {
      if (status) { status.className='test-result bad'; status.textContent=e.message || 'Sound Playback Failed'; }
    } finally {
      if (revoke) URL.revokeObjectURL(url);
    }
  }

  async function requestBrowserNotificationPermission() {
    const status = document.querySelector('#soundStatus');
    if (!('Notification' in window)) {
      if (status) { status.className='test-result bad'; status.textContent='Browser Notifications Are Not Supported'; }
      return;
    }
    const permission = await Notification.requestPermission();
    if (status) {
      status.className = `test-result ${permission === 'granted' ? 'ok' : 'muted'}`;
      status.textContent = `Browser Notification Permission: ${permission}`;
    }
  }

'''
    text = replace_once(text, '  async function loadExtras() {\n', helpers + '  async function loadExtras() {\n', "notification helpers")
    path.write_text(text, encoding="utf-8")


def patch_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    sound_code = '''let notificationAudio=null;
async function playSoundUrl(src){
  if(notificationAudio){try{notificationAudio.pause()}catch{}}
  const audio=new Audio(src);audio.preload='auto';audio.volume=.72;notificationAudio=audio;await audio.play();return audio
}
function configuredCompletionSoundUrl(){const n=state.settings?.notifications||{};return n.sound_mode==='custom'&&n.custom_sound_file?`/api/notification-sound?ts=${Date.now()}`:`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`}
async function playCompletionSound(){if(!state.settings?.notifications?.sound)return;const n=state.settings.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}
'''
    text = sub_once(text, r'function beep\(\)\{.*?\}\nasync function api', sound_code + 'async function api', "completion sound player", re.S)
    text = text.replace('beep();', 'playCompletionSound().catch(()=>{});')
    path.write_text(text, encoding="utf-8")


def patch_css():
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    text = text.replace('@media(min-width:821px){.settings-nav{margin-top:52px}}', '@media(min-width:821px){.settings-nav{margin-top:0}}')
    addition = '''
/* 0.5.5 settings alignment and notification sound controls. */
.local-address-heading{margin:0 0 8px}
.notification-settings-card .notification-intro{margin:0 0 16px;padding:0 13px}
.notification-options{display:grid;gap:10px;padding:0 13px 13px}
.notification-options>.toggle{margin:0}
.notification-sound-config{display:grid;gap:10px;padding:12px;border:1px solid var(--border);border-radius:12px;background:var(--panel3)}
.notification-sound-config label{margin:0}
.custom-sound-wrap{display:grid;gap:8px}
.custom-sound-wrap input[type=file]{width:100%;padding:8px;background:var(--panel2);border:1px solid var(--border);border-radius:10px;color:var(--text)}
.configured-sound{font-size:9px;color:var(--muted);overflow-wrap:anywhere}
.notification-actions{margin:2px 0 0}
.notification-actions button{min-width:170px}
@media(max-width:820px){.notification-settings-card .notification-intro{padding:0 11px}.notification-options{padding:0 11px 11px}.notification-sound-config{padding:11px}}
@media(max-width:560px){.notification-actions{display:grid;grid-template-columns:1fr}.notification-actions button{width:100%;min-width:0}.network-address-fields{grid-template-columns:1fr 1fr}}
'''
    text += addition
    path.write_text(text, encoding="utf-8")


def patch_sw():
    path = ROOT / "static" / "sw.js"
    text = path.read_text(encoding="utf-8").replace(OLD, NEW).replace('torrent-dashboard-v054', 'torrent-dashboard-v055')
    path.write_text(text, encoding="utf-8")


def create_default_sound():
    out = ROOT / "static" / "default-completion.wav"
    rate = 22050
    duration = 0.62
    frames = int(rate * duration)
    with wave.open(str(out), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        data = bytearray()
        for i in range(frames):
            t = i / rate
            attack = min(1.0, t / 0.025)
            release = min(1.0, max(0.0, (duration - t) / 0.18))
            env = attack * release
            f1 = 660.0 if t < 0.27 else 880.0
            f2 = 990.0 if t < 0.27 else 1320.0
            sample = (math.sin(2 * math.pi * f1 * t) * 0.55 + math.sin(2 * math.pi * f2 * t) * 0.22) * env
            data += struct.pack('<h', int(max(-1, min(1, sample)) * 15000))
        wav.writeframes(bytes(data))


def self_validate():
    dashboard = (ROOT/'dashboard.py').read_text(encoding='utf-8')
    html = (ROOT/'static/index.html').read_text(encoding='utf-8')
    settings = (ROOT/'static/settings.js').read_text(encoding='utf-8')
    app = (ROOT/'static/app.js').read_text(encoding='utf-8')
    css = (ROOT/'static/settings.css').read_text(encoding='utf-8')
    assert f'VERSION = "{NEW}"' in dashboard
    assert all(f'"{kind}": {{' in dashboard for kind in ('discord','ntfy','generic_webhook'))
    assert 'Local IP Address' not in html
    assert '<b>Local Dashboard Address</b>' in html and '>IP Address<input id="wLocalIp"' in html
    assert all(x not in html for x in ('id="nWebhook"','id="nDiscord"','id="nNtfy"','id="testNotify"'))
    assert all(x in html for x in ('id="nSoundMode"','id="nSoundFile"','id="previewSound"'))
    assert 'uploadNotificationSoundIfNeeded' in settings
    assert 'playCompletionSound' in app and 'function beep()' not in app
    assert 'margin-top:52px' not in css
    sound = ROOT/'static/default-completion.wav'
    assert sound.exists() and sound.read_bytes().startswith(b'RIFF') and sound.stat().st_size > 1000


def main():
    patch_dashboard()
    patch_html()
    patch_settings_js()
    patch_app_js()
    patch_css()
    patch_sw()
    create_default_sound()
    self_validate()
    print('Applied Torrent Dashboard 0.5.5 settings and notifications redesign')


if __name__ == '__main__':
    main()
