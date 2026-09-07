#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_OLD = "0.5.126"
VERSION_NEW = "0.5.127"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Fix multipart filename parsing. The old parser split the entire header block on ';',
# which allowed the following Content-Type line to become part of filename=... .
dashboard = read("dashboard.py")
start = dashboard.index("def parse_multipart(handler, max_bytes=50_000_000):")
end = dashboard.index("\n\n\nSOUND_MIME_TYPES", start)
new_parser = '''def _multipart_disposition_param(disposition: str, key: str):
    match = re.search(
        rf'(?:^|;)\\s*{re.escape(key)}\\s*=\\s*(?:"([^"]*)"|([^;]*))',
        disposition,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1) if match.group(1) is not None else match.group(2)
    return str(value or "").strip()


def parse_multipart(handler, max_bytes=50_000_000):
    ctype = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype or "boundary=" not in ctype:
        raise RuntimeError("Expected multipart/form-data")
    boundary = ctype.split("boundary=",1)[1].strip().strip('"').encode()
    length = int(handler.headers.get("Content-Length","0") or 0)
    if length > max_bytes: raise RuntimeError("Upload too large")
    body = handler.rfile.read(length)
    parts = body.split(b"--"+boundary)
    fields={}; files=[]
    for part in parts:
        if b"\\r\\n\\r\\n" not in part: continue
        head, data = part.split(b"\\r\\n\\r\\n",1)
        if data.endswith(b"\\r\\n"): data=data[:-2]
        header=head.decode(errors="replace")
        disposition = next(
            (line.strip() for line in header.splitlines() if line.lower().startswith("content-disposition:")),
            "",
        )
        if not disposition:
            continue
        name = _multipart_disposition_param(disposition, "name") or ""
        filename = _multipart_disposition_param(disposition, "filename")
        if filename is not None: files.append((name,filename,data))
        else: fields[name]=data.decode(errors="replace")
    return fields, files
'''
dashboard = dashboard[:start] + new_parser + dashboard[end:]
dashboard = replace_once(dashboard, f'VERSION = "{VERSION_OLD}"', f'VERSION = "{VERSION_NEW}"', "dashboard version")
write("dashboard.py", dashboard)

# Replace the native OS select with a controlled dropdown. Native option rendering
# is platform-owned and was producing a partial-width selected-row highlight.
index = read("static/index.html")
old_select = '<label>Sound<select id="nSoundMode"><option value="default">Default</option><option value="custom">Custom</option></select></label>'
new_select = '''<div class="notification-sound-mode-field">
<span class="notification-control-label">Sound</span>
<div class="notification-sound-select" id="nSoundModeControl">
<button aria-controls="nSoundModeMenu" aria-expanded="false" aria-haspopup="listbox" class="notification-sound-select-button" id="nSoundModeButton" type="button"><span id="nSoundModeLabel">Default</span><svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z"/></svg></button>
<div class="notification-sound-menu hidden" id="nSoundModeMenu" role="listbox" aria-label="Sound">
<button aria-selected="true" class="notification-sound-option" data-sound-mode="default" role="option" type="button">Default</button>
<button aria-selected="false" class="notification-sound-option" data-sound-mode="custom" role="option" type="button">Custom</button>
</div>
<select aria-hidden="true" class="hidden" id="nSoundMode" tabindex="-1"><option value="default">Default</option><option value="custom">Custom</option></select>
</div>
</div>'''
index = replace_once(index, old_select, new_select, "notification sound selector")
index = index.replace(VERSION_OLD, VERSION_NEW)
write("static/index.html", index)

settings = read("static/settings.js")
settings = replace_once(
    settings,
    "    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n",
    "    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n    bindNotificationSoundModeSelect();\n",
    "sound mode binding",
)
anchor = "  function updateNotificationSoundUi() {\n"
selector_helpers = r'''  function closeNotificationSoundModeSelect() {
    const button=document.querySelector('#nSoundModeButton'),menu=document.querySelector('#nSoundModeMenu');
    if(!button||!menu)return;
    menu.classList.add('hidden');
    button.setAttribute('aria-expanded','false');
  }

  function syncNotificationSoundModeSelect() {
    const mode=document.querySelector('#nSoundMode')?.value==='custom'?'custom':'default';
    const label=document.querySelector('#nSoundModeLabel');
    if(label)label.textContent=mode==='custom'?'Custom':'Default';
    document.querySelectorAll('[data-sound-mode]').forEach(option=>option.setAttribute('aria-selected',String(option.dataset.soundMode===mode)));
  }

  function chooseNotificationSoundMode(mode) {
    const select=document.querySelector('#nSoundMode');
    if(!select)return;
    const next=mode==='custom'?'custom':'default';
    if(select.value!==next){select.value=next;select.dispatchEvent(new Event('change',{bubbles:true}))}
    else updateNotificationSoundUi();
    closeNotificationSoundModeSelect();
    document.querySelector('#nSoundModeButton')?.focus();
  }

  function bindNotificationSoundModeSelect() {
    const control=document.querySelector('#nSoundModeControl'),button=document.querySelector('#nSoundModeButton'),menu=document.querySelector('#nSoundModeMenu');
    if(!control||!button||!menu||control.dataset.bound==='1')return;
    control.dataset.bound='1';
    const options=[...menu.querySelectorAll('[data-sound-mode]')];
    const open=()=>{
      menu.classList.remove('hidden');
      button.setAttribute('aria-expanded','true');
      syncNotificationSoundModeSelect();
      (options.find(option=>option.getAttribute('aria-selected')==='true')||options[0])?.focus();
    };
    button.addEventListener('click',()=>menu.classList.contains('hidden')?open():closeNotificationSoundModeSelect());
    button.addEventListener('keydown',event=>{if(['ArrowDown','ArrowUp','Enter',' '].includes(event.key)){event.preventDefault();open()}});
    options.forEach(option=>option.addEventListener('click',()=>chooseNotificationSoundMode(option.dataset.soundMode)));
    menu.addEventListener('keydown',event=>{
      const current=Math.max(0,options.indexOf(document.activeElement));
      if(event.key==='Escape'){event.preventDefault();closeNotificationSoundModeSelect();button.focus();return}
      if(event.key==='Enter'||event.key===' '){event.preventDefault();chooseNotificationSoundMode(document.activeElement?.dataset?.soundMode);return}
      if(event.key==='ArrowDown'||event.key==='ArrowUp'||event.key==='Home'||event.key==='End'){
        event.preventDefault();
        let next=current;
        if(event.key==='ArrowDown')next=(current+1)%options.length;
        if(event.key==='ArrowUp')next=(current-1+options.length)%options.length;
        if(event.key==='Home')next=0;
        if(event.key==='End')next=options.length-1;
        options[next]?.focus();
      }
    });
    document.addEventListener('pointerdown',event=>{if(!control.contains(event.target))closeNotificationSoundModeSelect()});
    syncNotificationSoundModeSelect();
  }

'''
if selector_helpers.strip() not in settings:
    settings = replace_once(settings, anchor, selector_helpers + anchor, "notification selector helpers")
settings = replace_once(
    settings,
    "  function updateNotificationSoundUi() {\n    const mode = document.querySelector('#nSoundMode')?.value || 'default';",
    "  function updateNotificationSoundUi() {\n    syncNotificationSoundModeSelect();\n    const mode = document.querySelector('#nSoundMode')?.value || 'default';",
    "sound selector synchronization",
)
write("static/settings.js", settings)

css = read("static/settings.css")
css += r'''

/* 0.5.127 notification sound selector */
.notification-sound-mode-field{display:grid;gap:6px;min-width:0;color:var(--muted);font-size:10px}
.notification-control-label{display:block;color:var(--muted)}
.notification-sound-select{position:relative;width:100%;min-width:0}
.notification-sound-select-button{width:100%;min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 11px;border:1px solid var(--border);border-radius:8px;background:var(--panel2);color:var(--text);text-align:left}
.notification-sound-select-button:hover,.notification-sound-select-button:focus-visible{border-color:color-mix(in srgb,var(--accent) 65%,var(--border));outline:none}
.notification-sound-select-button .material-symbol-icon{width:18px;height:18px;flex:0 0 auto;color:var(--muted);transition:transform .14s ease}
.notification-sound-select-button[aria-expanded="true"] .material-symbol-icon{transform:rotate(180deg)}
.notification-sound-menu{position:absolute;z-index:60;left:0;right:0;top:calc(100% + 4px);overflow:hidden;padding:3px;border:1px solid var(--border);border-radius:8px;background:var(--panel);box-shadow:0 14px 32px rgba(0,0,0,.3)}
.notification-sound-option{display:block;width:100%;min-height:34px;padding:8px 10px;border:0;border-radius:6px;background:transparent;color:var(--text);text-align:left}
.notification-sound-option:hover,.notification-sound-option:focus-visible{background:var(--panel2);outline:none}
.notification-sound-option[aria-selected="true"]{background:var(--panel2);box-shadow:inset 2px 0 0 var(--accent);color:var(--text)}
@media(prefers-reduced-motion:reduce){.notification-sound-select-button .material-symbol-icon{transition:none}}
'''
write("static/settings.css", css)

# Frontend build/version synchronization.
app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{VERSION_OLD}';", f"const FRONTEND_BUILD='{VERSION_NEW}';", "app frontend version")
write("static/app.js", app)

sw = read("static/sw.js").replace(VERSION_OLD, VERSION_NEW).replace("torrent-dashboard-v05126", "torrent-dashboard-v05127")
write("static/sw.js", sw)

# Regression coverage for the multipart filename bug.
test_path = "tests/test_torrent_add.py"
test = read(test_path)
test = replace_once(test, "import unittest\n", "import io\nimport unittest\nfrom types import SimpleNamespace\n", "test imports")
test = replace_once(test, "from dashboard import QBitClient\n", "from dashboard import QBitClient, parse_multipart\n", "multipart test import")
method_anchor = "    def test_cached_add_serializes_file_priorities(self):\n"
method = '''    def test_multipart_filename_stops_at_content_disposition_line(self):
        boundary = "----TorrentDashboardTest"
        payload = b"ID3\\x04\\x00\\x00audio"
        body = (
            f"--{boundary}\\r\\n"
            'Content-Disposition: form-data; name="sound"; filename="alert.mp3"\\r\\n'
            "Content-Type: audio/mpeg\\r\\n\\r\\n"
        ).encode() + payload + f"\\r\\n--{boundary}--\\r\\n".encode()
        handler = SimpleNamespace(
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            rfile=io.BytesIO(body),
        )
        fields, files = parse_multipart(handler)
        self.assertEqual(fields, {})
        self.assertEqual(files[0][0], "sound")
        self.assertEqual(files[0][1], "alert.mp3")
        self.assertEqual(files[0][2], payload)

'''
test = replace_once(test, method_anchor, method + method_anchor, "multipart regression test")
write(test_path, test)

# Structured release metadata, then regenerate generated docs deterministically.
notes_path = ROOT / "release_notes" / "releases.json"
notes = json.loads(notes_path.read_text(encoding="utf-8"))
if not any(str(item.get("version")) == VERSION_NEW for item in notes.get("releases", [])):
    notes.setdefault("releases", []).append({
        "version": VERSION_NEW,
        "date": "2026-09-07",
        "status": "prerelease",
        "title": "Notification sound save and selector fixes",
        "summary": "Fixes custom notification sound uploads that tested successfully but failed on save, and replaces the platform-native sound selector with a consistently highlighted full-width dropdown.",
        "highlights": [
            "Custom WAV, MP3, and OGG filenames are now parsed correctly from browser multipart uploads.",
            "The Sound control now uses a keyboard-accessible custom dropdown whose selected row fills the full control width."
        ],
        "fixes": [
            "Saving a valid custom audio file no longer reports that the file must be WAV, MP3, or OGG after a successful preview.",
            "Default and Custom options no longer rely on inconsistent operating-system option highlighting."
        ],
        "technical": [
            "Multipart parsing now extracts name and filename only from the Content-Disposition header line instead of allowing subsequent MIME headers to contaminate the filename.",
            "The hidden native select remains the settings value source while the visible listbox mirrors and updates it."
        ],
        "validation": [
            "Adds a multipart regression test with a Content-Type header after filename=alert.mp3.",
            "Runs source validation, unit tests, UI-string validation, and JavaScript syntax checks before publication."
        ],
        "known_issues": []
    })
notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", VERSION_NEW], cwd=ROOT, check=True)

# The patch/workflow are temporary branch tooling and must not reach main.
for relative in (
    "release_tools/apply_notification_sound_save_fix.py",
    ".github/workflows/apply-notification-sound-save-fix.yml",
    ".github/notification-sound-save-fix-trigger.txt",
):
    path = ROOT / relative
    if path.exists():
        path.unlink()

print(f"Applied notification sound save fix for v{VERSION_NEW}")
