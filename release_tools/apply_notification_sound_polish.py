#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.125"
NEW = "0.5.126"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return updated


def patch_config() -> None:
    path = "torrent_dashboard/config.py"
    text = read(path)
    text = once(
        text,
        '        "sound_mode": "default",\n        "custom_sound_file": "",',
        '        "sound_mode": "default",\n        "volume": 72,\n        "custom_sound_file": "",',
        "default notification volume",
    )
    anchor = '''    merged["integrations"] = [\n        item for item in merged.get("integrations", []) if item.get("type") != "github"\n    ]\n\n    sync_legacy_auth(merged)\n'''
    replacement = '''    merged["integrations"] = [\n        item for item in merged.get("integrations", []) if item.get("type") != "github"\n    ]\n\n    notifications = merged.setdefault("notifications", {})\n    try:\n        notification_volume = int(round(float(notifications.get("volume", 72))))\n    except (TypeError, ValueError):\n        notification_volume = 72\n    notifications["volume"] = max(0, min(100, notification_volume))\n\n    sync_legacy_auth(merged)\n'''
    text = once(text, anchor, replacement, "notification volume normalization")
    write(path, text)


def patch_dashboard() -> None:
    path = "dashboard.py"
    text = read(path)
    text = once(
        text,
        'CUSTOM_SOUND_BASENAME = "custom-notification-sound"\nMAX_CUSTOM_SOUND_BYTES',
        'CUSTOM_SOUND_BASENAME = "notification-custom"\nLEGACY_CUSTOM_SOUND_BASENAME = "custom-notification-sound"\nMAX_CUSTOM_SOUND_BYTES',
        "custom notification sound basename",
    )
    old_cleanup = '''    for old_ext in SOUND_MIME_TYPES:\n        old = DATA_DIR / f"{CUSTOM_SOUND_BASENAME}{old_ext}"\n        if old.exists():\n            try: old.unlink()\n            except Exception: pass\n'''
    new_cleanup = '''    for basename in (CUSTOM_SOUND_BASENAME, LEGACY_CUSTOM_SOUND_BASENAME):\n        for old_ext in SOUND_MIME_TYPES:\n            old = DATA_DIR / f"{basename}{old_ext}"\n            if old.exists():\n                try: old.unlink()\n                except Exception: pass\n'''
    text = once(text, old_cleanup, new_cleanup, "custom sound cleanup migration")
    old_guard = '''    name = Path(str(n.get("custom_sound_file") or "")).name\n    if not name.startswith(CUSTOM_SOUND_BASENAME):\n        return None, None\n    path = DATA_DIR / name\n'''
    new_guard = '''    name = Path(str(n.get("custom_sound_file") or "")).name\n    sound_name = Path(name)\n    if sound_name.stem not in (CUSTOM_SOUND_BASENAME, LEGACY_CUSTOM_SOUND_BASENAME) or sound_name.suffix.lower() not in SOUND_MIME_TYPES:\n        return None, None\n    path = DATA_DIR / name\n'''
    text = once(text, old_guard, new_guard, "legacy custom sound compatibility")
    old_csp = "default-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'"
    new_csp = "default-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; media-src 'self' blob:; manifest-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'"
    text = once(text, old_csp, new_csp, "notification blob media CSP")
    text = once(text, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
    write(path, text)


def patch_app_js() -> None:
    path = "static/app.js"
    text = read(path)
    old = '''let notificationAudio=null;\nasync function playSoundUrl(src){\n  if(notificationAudio){try{notificationAudio.pause()}catch{}}\n  const audio=new Audio(src);audio.preload='auto';audio.volume=.72;notificationAudio=audio;await audio.play();return audio\n}\nfunction configuredCompletionSoundUrl(){const n=state.settings?.notifications||{};return n.sound_mode==='custom'&&n.custom_sound_file?`/api/notification-sound?ts=${Date.now()}`:`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`}\nasync function playCompletionSound(){if(!state.settings?.notifications?.sound)return;const n=state.settings.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}\n'''
    new = '''let notificationAudio=null;\nfunction notificationVolume(value=state.settings?.notifications?.volume){const raw=Number(value);const percent=Number.isFinite(raw)?raw:72;return Math.max(0,Math.min(100,percent))/100}\nasync function playSoundUrl(src,volumePercent=null){\n  if(notificationAudio){try{notificationAudio.pause()}catch{}}\n  const audio=new Audio(src);audio.preload='auto';audio.volume=volumePercent==null?notificationVolume():notificationVolume(volumePercent);notificationAudio=audio;await audio.play();return audio\n}\nfunction configuredCompletionSoundUrl(){const n=state.settings?.notifications||{};return n.sound_mode==='custom'&&n.custom_sound_file?`/api/notification-sound?ts=${Date.now()}`:`/static/notification-default.wav?v=${encodeURIComponent(state.me?.version||'')}`}\nasync function playCompletionSound(){if(!state.settings?.notifications?.sound)return;const n=state.settings.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/notification-default.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}\n'''
    text = once(text, old, new, "notification playback volume")
    text = once(text, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
    write(path, text)


def patch_settings_js() -> None:
    path = "static/settings.js"
    text = read(path)
    text = once(
        text,
        "  let integrationHealthRefreshing = false;\n",
        "  let integrationHealthRefreshing = false;\n  let pendingNotificationSoundFile = null;\n",
        "pending notification sound state",
    )
    old_bind = '''    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n    document.querySelector('#nSoundFile')?.addEventListener('change', updateNotificationSoundUi);\n    document.querySelector('#testNotification')?.addEventListener('click', testNotification);\n'''
    new_bind = '''    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n    document.querySelector('#nSoundFile')?.addEventListener('change', event => setNotificationSoundFile(event.target.files?.[0] || null));\n    document.querySelector('#nSoundVolume')?.addEventListener('input', updateNotificationVolumeUi);\n    bindNotificationSoundDrop();\n    document.querySelector('#testNotification')?.addEventListener('click', testNotification);\n'''
    text = once(text, old_bind, new_bind, "notification control binding")
    old_fill = '''    setValue('nSoundMode', n.sound_mode || 'default');\n    const soundFile = document.querySelector('#nSoundFile');\n    if (soundFile) soundFile.value = '';\n    const soundName = document.querySelector('#nCustomSoundName');\n    if (soundName) soundName.textContent = n.custom_sound_name || 'No custom sound uploaded';\n    updateNotificationSoundUi();\n'''
    new_fill = '''    setValue('nSoundMode', n.sound_mode || 'default');\n    setValue('nSoundVolume', Number.isFinite(Number(n.volume)) ? Math.max(0, Math.min(100, Number(n.volume))) : 72);\n    pendingNotificationSoundFile = null;\n    const soundFile = document.querySelector('#nSoundFile');\n    if (soundFile) soundFile.value = '';\n    const soundName = document.querySelector('#nCustomSoundName');\n    if (soundName) soundName.textContent = n.custom_sound_name || 'No custom sound uploaded';\n    updateNotificationSoundUi();\n    updateNotificationVolumeUi();\n'''
    text = once(text, old_fill, new_fill, "notification settings fill")
    text = once(
        text,
        "        sound_mode: document.querySelector('#nSoundMode')?.value || 'default'\n",
        "        sound_mode: document.querySelector('#nSoundMode')?.value || 'default',\n        volume: notificationVolumePercent()\n",
        "notification settings save volume",
    )
    new_block = r'''  const NOTIFICATION_SOUND_EXTENSIONS = new Set(['.wav','.mp3','.ogg']);

  function notificationSoundExtension(file) {
    const name=String(file?.name||'').toLowerCase();
    const dot=name.lastIndexOf('.');
    return dot>=0?name.slice(dot):'';
  }

  function validateNotificationSoundFile(file) {
    if(!file)return null;
    const ext=notificationSoundExtension(file);
    if(!NOTIFICATION_SOUND_EXTENSIONS.has(ext))throw new Error('Choose a WAV, MP3, or OGG sound file.');
    if(!Number.isFinite(file.size)||file.size<1||file.size>2*1024*1024)throw new Error('Custom sound must be between 1 byte and 2 MB.');
    return file;
  }

  function setNotificationSoundFile(file) {
    try{pendingNotificationSoundFile=validateNotificationSoundFile(file)}catch(error){pendingNotificationSoundFile=null;const input=document.querySelector('#nSoundFile');if(input)input.value='';toast(error.message,'error')}
    updateNotificationSoundUi();
  }

  function bindNotificationSoundDrop() {
    const drop=document.querySelector('#nSoundDrop'),input=document.querySelector('#nSoundFile');
    if(!drop||!input||drop.dataset.bound==='1')return;
    drop.dataset.bound='1';
    drop.addEventListener('click',()=>input.click());
    for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.add('dragover')});
    for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.remove('dragover')});
    drop.addEventListener('drop',event=>{const file=[...(event.dataTransfer?.files||[])].find(item=>NOTIFICATION_SOUND_EXTENSIONS.has(notificationSoundExtension(item)));if(file)setNotificationSoundFile(file);else toast('Drop a WAV, MP3, or OGG sound file.','error')});
  }

  function notificationVolumePercent() {
    const raw=Number(document.querySelector('#nSoundVolume')?.value ?? 72);
    return Math.round(Math.max(0,Math.min(100,Number.isFinite(raw)?raw:72)));
  }

  function updateNotificationVolumeUi() {
    const value=notificationVolumePercent(),input=document.querySelector('#nSoundVolume'),output=document.querySelector('#nSoundVolumeValue');
    if(input&&Number(input.value)!==value)input.value=String(value);
    if(output)output.textContent=`${value}%`;
  }

  function updateNotificationSoundUi() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const wrap = document.querySelector('#nCustomSoundWrap');
    if (wrap) wrap.classList.toggle('hidden', mode !== 'custom');
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    const name = document.querySelector('#nCustomSoundName');
    const drop = document.querySelector('#nSoundDrop');
    if (name && file) name.textContent = file.name;
    if (drop) drop.classList.toggle('has-file', !!file);
  }

  async function uploadNotificationSoundIfNeeded() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    if (mode !== 'custom' || !file) return null;
    validateNotificationSoundFile(file);
    const form = new FormData();
    form.append('sound', file, file.name);
    const response = await fetch('/api/notification-sound', {method:'POST', headers:{'X-CSRF-Token':state.csrf}, body:form});
    const data = await response.json().catch(()=>({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    const name = document.querySelector('#nCustomSoundName');
    if (name) name.textContent = data.name || file.name;
    return data;
  }

  async function testNotification() {
    const status = document.querySelector('#soundStatus');
    const browserEnabled = !!document.querySelector('#nBrowser')?.checked;
    const soundEnabled = !!document.querySelector('#nSound')?.checked;
    if (!browserEnabled && !soundEnabled) {
      if (status) { status.className='test-result bad'; status.textContent='Enable browser notifications or completion sound before testing.'; }
      return;
    }
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    let soundUrl = '';
    let revoke = false;
    if (soundEnabled) {
      if (mode === 'custom' && file) { validateNotificationSoundFile(file); soundUrl=URL.createObjectURL(file); revoke=true; }
      else if (mode === 'custom') soundUrl=`/api/notification-sound?ts=${Date.now()}`;
      else soundUrl=`/static/notification-default.wav?v=${encodeURIComponent(state.me?.version || '')}`;
    }
    try {
      if (status) { status.className='test-result muted'; status.textContent='Testing notification…'; }
      const tested=[];
      if (browserEnabled) {
        if (!('Notification' in window)) throw new Error('This browser does not support system notifications.');
        let permission=Notification.permission;
        if (permission==='default') permission=await Notification.requestPermission();
        if (permission!=='granted') throw new Error(permission==='denied' ? "Browser notification permission is blocked. Enable it in this site's browser permissions." : 'Browser notification permission was not granted.');
        await showBrowserNotification(state.settings?.dashboard?.title || 'Torrent Dashboard',{body:'This is a test notification from Torrent Dashboard.',tag:'torrent-dashboard-test'});
        tested.push('browser notification');
      }
      if (soundEnabled) {
        try{await playSoundUrl(soundUrl,notificationVolumePercent())}
        catch(error){if(error?.name==='NotSupportedError')throw new Error('This browser could not decode the selected audio file. Try a standard MP3, WAV, or OGG file.');throw error}
        tested.push('completion sound');
      }
      if (status) { status.className='test-result ok'; status.textContent=`Test successful: ${tested.join(' and ')}.`; }
    } catch(e) {
      if (status) { status.className='test-result bad'; status.textContent=e.message || 'Notification test failed.'; }
    } finally { if (revoke) URL.revokeObjectURL(soundUrl); }
  }

  function updateSourceRepository()'''
    text = regex_once(
        text,
        r"  function updateNotificationSoundUi\(\) \{.*?\n  function updateSourceRepository\(\)",
        new_block,
        "notification sound functions",
    )
    write(path, text)


def patch_index() -> None:
    path = "static/index.html"
    text = read(path)
    old = '''<div class="custom-sound-wrap hidden" id="nCustomSoundWrap">\n<label>Custom sound file<input accept="audio/wav,audio/mpeg,audio/ogg,.wav,.mp3,.ogg" id="nSoundFile" type="file"/></label>\n<div class="configured-sound" id="nCustomSoundName">No custom sound uploaded</div>\n<div class="field-help">WAV, MP3, or OGG · Maximum 2 MB. Custom sounds are stored in the data directory and preserved during updates.</div>\n</div>\n<div class="settings-inline-actions notification-actions"><button class="secondary" id="testNotification" type="button">Test notification</button></div>\n'''
    new = '''<div class="custom-sound-wrap hidden" id="nCustomSoundWrap">\n<button class="notification-sound-drop" id="nSoundDrop" type="button"><svg class="material-symbol-icon notification-sound-drop-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2Zm7-17-7 7h4v5h6v-5h4l-7-7Z"/></svg><strong>Drop an audio file here</strong><span>or click to browse</span><small class="configured-sound" id="nCustomSoundName">No custom sound uploaded</small></button>\n<input accept="audio/wav,audio/mpeg,audio/ogg,.wav,.mp3,.ogg" class="hidden" id="nSoundFile" type="file"/>\n<div class="field-help">WAV, MP3, or OGG · Maximum 2 MB.</div>\n</div>\n<div class="notification-volume-row"><label for="nSoundVolume">Volume</label><div class="notification-volume-control"><input aria-label="Notification volume" id="nSoundVolume" max="100" min="0" step="1" type="range" value="72"/><output id="nSoundVolumeValue" for="nSoundVolume">72%</output></div></div>\n<div class="settings-inline-actions notification-actions"><button class="secondary" id="testNotification" type="button">Test notification</button></div>\n'''
    text = once(text, old, new, "notification sound settings markup")
    text = text.replace(OLD, NEW)
    write(path, text)


def patch_settings_css() -> None:
    path = "static/settings.css"
    text = read(path)
    addition = r'''

/* 0.5.126 notification sound upload and volume controls. */
.notification-sound-drop{width:100%;min-height:126px;display:grid;place-items:center;align-content:center;gap:5px;padding:16px;border:1px dashed color-mix(in srgb,var(--border) 90%,var(--muted));border-radius:12px;background:color-mix(in srgb,var(--panel2) 78%,transparent);color:var(--muted);text-align:center;transition:border-color .15s ease,background .15s ease,box-shadow .15s ease}
.notification-sound-drop:hover,.notification-sound-drop:focus-visible,.notification-sound-drop.dragover{border-color:color-mix(in srgb,var(--accent) 72%,var(--border));background:color-mix(in srgb,var(--accent) 8%,var(--panel2));box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 18%,transparent)}
.notification-sound-drop.has-file{border-style:solid}.notification-sound-drop-icon{width:27px;height:27px;color:var(--accent)}.notification-sound-drop strong{font-size:11.5px;color:var(--text)}.notification-sound-drop>span{font-size:9.5px}.notification-sound-drop .configured-sound{display:block;margin-top:3px;max-width:100%;font-size:9px;color:var(--muted);overflow-wrap:anywhere}
.notification-volume-row{display:grid;grid-template-columns:auto minmax(180px,1fr);align-items:center;gap:14px;padding:4px 0}.notification-volume-row>label{margin:0;color:var(--muted);font-size:10px}.notification-volume-control{display:grid;grid-template-columns:minmax(0,1fr) 44px;align-items:center;gap:10px}.notification-volume-control input[type=range]{width:100%;accent-color:var(--accent)}.notification-volume-control output{font-variant-numeric:tabular-nums;text-align:right;color:var(--text);font-size:10px}
@media(max-width:560px){.notification-volume-row{grid-template-columns:1fr;gap:7px}.notification-sound-drop{min-height:116px}}
'''
    if "0.5.126 notification sound upload and volume controls" in text:
        raise RuntimeError("notification sound CSS already present")
    write(path, text.rstrip() + addition + "\n")


def patch_tests() -> None:
    path = "tests/test_config.py"
    text = read(path)
    anchor = '''    def test_public_config_redacts_browser_secrets(self):\n'''
    test = '''    def test_notification_volume_is_defaulted_and_clamped(self):\n        self.assertEqual(normalize_config({})["notifications"]["volume"], 72)\n        self.assertEqual(normalize_config({"notifications": {"volume": 150}})["notifications"]["volume"], 100)\n        self.assertEqual(normalize_config({"notifications": {"volume": -5}})["notifications"]["volume"], 0)\n        self.assertEqual(normalize_config({"notifications": {"volume": "invalid"}})["notifications"]["volume"], 72)\n\n'''
    text = once(text, anchor, test + anchor, "notification volume config tests")
    write(path, text)


def patch_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.setdefault("releases", [])
    if any(str(item.get("version")) == NEW for item in releases):
        raise RuntimeError(f"release metadata already contains {NEW}")
    releases.append({
        "version": NEW,
        "date": "2026-09-06",
        "status": "prerelease",
        "title": "Notification sound upload and volume controls",
        "summary": "Fixes custom notification sound previews and adds a torrent-style drag-and-drop uploader plus a persisted notification volume control.",
        "highlights": [
            "Adds a drag-and-drop custom sound target that mirrors the .torrent file picker and still supports click-to-browse.",
            "Adds a 0–100 notification volume slider used by test playback and normal completion notifications.",
            "Uses notification-default.wav for the bundled sound and notification-custom.<ext> for newly uploaded custom sounds."
        ],
        "fixes": [
            "Allows blob: media only through the media-src CSP directive so local custom-sound previews are no longer rejected by the browser.",
            "Removes the internal storage-directory note from the Notifications settings UI."
        ],
        "technical": [
            "Existing custom-notification-sound files remain readable for migration compatibility; replacement uploads use the notification-custom basename.",
            "Notification volume is normalized to an integer from 0 through 100 and defaults to 72 for existing configurations."
        ],
        "validation": [
            "Source validation, unit tests, UI-string validation, JavaScript syntax checks, renamed default-sound verification, and CSP assertions run before publication."
        ],
        "known_issues": []
    })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rename_default_sound() -> None:
    old = ROOT / "static" / "default-completion.wav"
    new = ROOT / "static" / "notification-default.wav"
    if not old.is_file():
        raise RuntimeError("static/default-completion.wav is missing")
    if new.exists():
        raise RuntimeError("static/notification-default.wav already exists")
    subprocess.run(["git", "mv", str(old.relative_to(ROOT)), str(new.relative_to(ROOT))], cwd=ROOT, check=True)


def patch_versions() -> None:
    path = "static/sw.js"
    text = read(path)
    text = text.replace(f"v{OLD.replace('.', '')}", f"v{NEW.replace('.', '')}")
    text = text.replace(OLD, NEW)
    write(path, text)


def main() -> None:
    patch_config()
    patch_dashboard()
    patch_app_js()
    patch_settings_js()
    patch_index()
    patch_settings_css()
    patch_tests()
    patch_release_metadata()
    rename_default_sound()
    patch_versions()
    print("Applied notification sound polish for", NEW)


if __name__ == "__main__":
    main()
