from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.147"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_version() -> None:
    init = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    text = init.read_text(encoding="utf-8").replace('__version__ = "0.5.146"', f'__version__ = "{VERSION}"')
    init.write_text(text, encoding="utf-8")
    for path in (ROOT / "static").iterdir():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace("0.5.146", VERSION).replace("v05146", "v05147")
        path.write_text(text, encoding="utf-8")


def update_backup_module() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "backups.py"
    text = path.read_text(encoding="utf-8")
    old = '''            files = _payload_files(staging)\n            manifest = {\n'''
    new = '''            files = _payload_files(staging)\n            if sum(int(item.get("size") or 0) for item in files) > MAX_BACKUP_BYTES:\n                raise RuntimeError("Backup payload exceeds the 512 MB safety limit")\n            manifest = {\n'''
    if old in text:
        text = text.replace(old, new, 1)
    old = '''            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:\n                archive.write(staging / "backup-manifest.json", "backup-manifest.json")\n                for item in files:\n                    archive.write(staging / item["path"], item["path"])\n\n    return backup_metadata(destination, validate=True)\n'''
    new = '''            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:\n                archive.write(staging / "backup-manifest.json", "backup-manifest.json")\n                for item in files:\n                    archive.write(staging / item["path"], item["path"])\n            if destination.stat().st_size > MAX_BACKUP_BYTES:\n                destination.unlink(missing_ok=True)\n                raise RuntimeError("Backup archive exceeds the 512 MB safety limit")\n\n    return backup_metadata(destination, validate=True)\n'''
    if old in text:
        text = text.replace(old, new, 1)
    old = '''    current_config: dict,\n    history_lock=None,\n) -> dict:\n'''
    new = '''    current_config: dict,\n    history_lock=None,\n    validator=None,\n) -> dict:\n'''
    if old in text:
        text = text.replace(old, new, 1)
    old = '''            try:\n                _apply_payload(app_dir, extracted / "payload")\n            except Exception as exc:\n'''
    new = '''            try:\n                _apply_payload(app_dir, extracted / "payload")\n                if validator is not None:\n                    validator()\n            except Exception as exc:\n'''
    if old in text:
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def update_dashboard() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    marker = "from torrent_dashboard.config_store import ConfigStore\n"
    block = '''from torrent_dashboard.backups import (\n    BACKUP_EXTENSION,\n    MAX_BACKUP_BYTES,\n    backup_path,\n    create_backup,\n    import_backup,\n    list_backups,\n    restore_backup,\n)\n'''
    if block not in text:
        if marker not in text:
            raise SystemExit("dashboard backup import marker not found")
        text = text.replace(marker, marker + block, 1)

    marker = '''    def remove_user_except(self, user_id, keep_token):\n        uid = str(user_id or "")\n        with self.lock:\n            doomed = [token for token, item in self.sessions.items() if item.get("user_id") == uid and token != keep_token]\n            for token in doomed:\n                self.sessions.pop(token, None)\n\n\nSESSIONS = SessionStore()\n'''
    replacement = '''    def remove_user_except(self, user_id, keep_token):\n        uid = str(user_id or "")\n        with self.lock:\n            doomed = [token for token, item in self.sessions.items() if item.get("user_id") == uid and token != keep_token]\n            for token in doomed:\n                self.sessions.pop(token, None)\n\n    def clear(self):\n        with self.lock:\n            self.sessions.clear()\n\n\nSESSIONS = SessionStore()\n'''
    if "    def clear(self):\n        with self.lock:\n            self.sessions.clear()" not in text:
        if marker not in text:
            raise SystemExit("SessionStore marker not found")
        text = text.replace(marker, replacement, 1)

    marker = '''    def send_json(self, code, obj, cookie_token=None, extra=None):\n        self.send_bytes(code,json.dumps(obj,separators=(",",":"),default=str).encode(),"application/json; charset=utf-8",cookie_token,extra)\n\n    def require_auth(self, mutation=False):\n'''
    replacement = '''    def send_json(self, code, obj, cookie_token=None, extra=None):\n        self.send_bytes(code,json.dumps(obj,separators=(",",":"),default=str).encode(),"application/json; charset=utf-8",cookie_token,extra)\n\n    def send_file(self, code, path, content_type="application/octet-stream", filename=None, cookie_token=None):\n        path = Path(path)\n        safe_name = Path(str(filename or path.name)).name.replace('"', '')\n        self.send_response(code)\n        self.send_header("Content-Type", content_type)\n        self.send_header("Content-Length", str(path.stat().st_size))\n        self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')\n        self.send_header("Cache-Control", "no-store")\n        self.send_header("X-Content-Type-Options", "nosniff")\n        self.send_header("Referrer-Policy", "same-origin")\n        self.send_header("X-Frame-Options", "DENY")\n        if cookie_token:\n            secure = "; Secure" if load_config()["dashboard"].get("https_enabled") else ""\n            self.send_header("Set-Cookie", f"td_session={cookie_token}; Path=/; HttpOnly; SameSite=Lax{secure}")\n        self.end_headers()\n        with path.open("rb") as handle:\n            while True:\n                chunk = handle.read(1024 * 1024)\n                if not chunk:\n                    break\n                self.wfile.write(chunk)\n\n    def require_auth(self, mutation=False):\n'''
    if "    def send_file(self, code, path" not in text:
        if marker not in text:
            raise SystemExit("send_json marker not found")
        text = text.replace(marker, replacement, 1)

    old = '''        if path in ("/api/settings","/api/integrations","/api/integration-health","/api/integrations/jellyfin/status","/api/integrations/jellyfin/tasks","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):\n'''
    new = '''        if path in ("/api/settings","/api/integrations","/api/integration-health","/api/integrations/jellyfin/status","/api/integrations/jellyfin/tasks","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save","/api/backups","/api/backups/export") and not session_is_admin(sess):\n'''
    if old in text:
        text = text.replace(old, new, 1)

    marker = '''        if path=="/api/users": return self.send_json(200,{"users":[public_user(u) for u in cfg.get("users",[])],"current_user_id":sess.get("user_id","")},new_cookie)\n        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)\n'''
    replacement = '''        if path=="/api/users": return self.send_json(200,{"users":[public_user(u) for u in cfg.get("users",[])],"current_user_id":sess.get("user_id","")},new_cookie)\n        if path=="/api/backups":\n            return self.send_json(200,{"backups":list_backups(APP_DIR),"extension":BACKUP_EXTENSION,"max_bytes":MAX_BACKUP_BYTES},new_cookie)\n        if path=="/api/backups/export":\n            try:\n                item=backup_path(APP_DIR,qs.get("name",[""])[0])\n                return self.send_file(200,item,"application/octet-stream",item.name,new_cookie)\n            except Exception as exc:\n                return self.send_json(404,{"error":str(exc)},new_cookie)\n        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)\n'''
    if 'if path=="/api/backups":' not in text:
        if marker not in text:
            raise SystemExit("GET backup route marker not found")
        text = text.replace(marker, replacement, 1)

    marker = '''            if path=="/api/settings":\n                data=parse_json_body(self); updated,_=mutate_config(lambda current: (apply_settings_update(current,data),None))\n                HISTORY.event("dashboard", "settings_changed", sess.get("username",""), "", {"client_ip": self.client_ip()})\n                return self.send_json(200,{"ok":True,"settings":redacted_config(updated)},new_cookie)\n            if path=="/api/update-source":\n'''
    replacement = '''            if path=="/api/settings":\n                data=parse_json_body(self); updated,_=mutate_config(lambda current: (apply_settings_update(current,data),None))\n                HISTORY.event("dashboard", "settings_changed", sess.get("username",""), "", {"client_ip": self.client_ip()})\n                return self.send_json(200,{"ok":True,"settings":redacted_config(updated)},new_cookie)\n            if path=="/api/backups/create":\n                item=create_backup(APP_DIR,VERSION,cfg,history_lock=HISTORY.lock)\n                HISTORY.event("dashboard","backup_created",item.get("name", ""),"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True,"backup":item},new_cookie)\n            if path=="/api/backups/import":\n                fields,files=parse_multipart(self,max_bytes=MAX_BACKUP_BYTES+256000)\n                if not files:\n                    raise RuntimeError("Choose a Torrent Dashboard backup file")\n                _,filename,content=files[0]\n                item=import_backup(APP_DIR,filename,content)\n                HISTORY.event("dashboard","backup_imported",item.get("name", ""),"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True,"backup":item},new_cookie)\n            if path=="/api/backups/restore":\n                data=parse_json_body(self,12000)\n                result=restore_backup(\n                    APP_DIR,str(data.get("name") or ""),current_version=VERSION,current_config=cfg,\n                    history_lock=HISTORY.lock,validator=load_config,\n                )\n                with CACHE_LOCK:\n                    CLIENTS.clear(); CACHE.clear()\n                HISTORY.event("dashboard","backup_restored",result.get("backup",{}).get("name", ""),"",{"client_ip":self.client_ip()})\n                SESSIONS.clear()\n                return self.send_json(200,{"ok":True,"backup":result.get("backup"),"safety_backup":result.get("safety_backup"),"reauthenticate":True},None)\n            if path=="/api/update-source":\n'''
    if 'if path=="/api/backups/create":' not in text:
        if marker not in text:
            raise SystemExit("POST backup route marker not found")
        text = text.replace(marker, replacement, 1)

    path.write_text(text, encoding="utf-8")


def update_index() -> None:
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    old = '''<button data-view="settings" data-settings-page="clients" type="button">Clients</button>\n<button data-view="settings" data-settings-page="updates" type="button">Updates</button>\n'''
    new = '''<button data-view="settings" data-settings-page="clients" type="button">Clients</button>\n<button data-view="settings" data-settings-page="backups" type="button">Backups</button>\n<button data-view="settings" data-settings-page="updates" type="button">Updates</button>\n'''
    if 'data-settings-page="backups"' not in text:
        if old not in text:
            raise SystemExit("settings subnav marker not found")
        text = text.replace(old, new, 1)
    old = '<label class="settings-mobile-picker">Settings category<select id="settingsMobilePage" aria-label="Settings category"><option value="general">General</option><option value="access">Access</option><option value="clients">Clients</option><option value="updates">Updates</option><option value="notifications">Notifications</option><option value="integrations">Integrations</option><option value="users">Users</option></select></label>'
    new = '<label class="settings-mobile-picker">Settings category<select id="settingsMobilePage" aria-label="Settings category"><option value="general">General</option><option value="access">Access</option><option value="clients">Clients</option><option value="backups">Backups</option><option value="updates">Updates</option><option value="notifications">Notifications</option><option value="integrations">Integrations</option><option value="users">Users</option></select></label>'
    if '<option value="backups">Backups</option>' not in text:
        if old not in text:
            raise SystemExit("settings mobile picker marker not found")
        text = text.replace(old, new, 1)
    marker = '''<section class="settings-page" data-settings-section="clients">\n<div class="panel settings-card"><div class="panel-title">Clients</div><p class="muted client-settings-intro">Manage your qBitTorrent connections. Open Settings on a saved client to change its transfer preferences.</p><div id="serverSettings"></div><button id="addServerSetting" type="button">＋ Add client</button></div>\n</section>\n<section class="settings-page" data-settings-section="updates">\n'''
    backup = '''<section class="settings-page" data-settings-section="clients">\n<div class="panel settings-card"><div class="panel-title">Clients</div><p class="muted client-settings-intro">Manage your qBitTorrent connections. Open Settings on a saved client to change its transfer preferences.</p><div id="serverSettings"></div><button id="addServerSetting" type="button">＋ Add client</button></div>\n</section>\n<section class="settings-page" data-settings-section="backups">\n<div class="panel settings-card backup-settings-card">\n<div class="panel-title">Backups</div>\n<p class="muted backup-intro">Create portable backups of Torrent Dashboard configuration and state. Backups include users, saved credentials, integrations, notification assets, profile pictures, and dashboard history. Application binaries and qBitTorrent data are not included.</p>\n<div class="backup-warning"><strong>Keep backup files secure.</strong><span>Portable backups contain saved credentials and recovery data in readable archive form.</span></div>\n<div class="settings-inline-actions backup-toolbar"><button class="primary" id="backupCreate" type="button">Create backup</button><button class="secondary" id="backupImport" type="button">Import backup</button><input accept=".tdbackup,application/zip" class="hidden" id="backupImportFile" type="file"/></div>\n<div class="test-result muted backup-status" id="backupStatus">Backups are stored locally under <code>data/backups</code>. Export one to move it to another installation.</div>\n<div class="backup-list" id="backupList"><div class="settings-empty"><b>Loading backups…</b><span>Local backup archives will appear here.</span></div></div>\n</div>\n</section>\n<section class="settings-page" data-settings-section="updates">\n'''
    if 'data-settings-section="backups"' not in text:
        if marker not in text:
            raise SystemExit("backup section insertion marker not found")
        text = text.replace(marker, backup, 1)
    path.write_text(text, encoding="utf-8")


def update_settings_js() -> None:
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace("  let pendingNotificationSoundFile = null;\n", "  let pendingNotificationSoundFile = null;\n  let backups = [];\n  let backupsLoading = false;\n", 1) if "let backups = [];" not in text else text
    text = text.replace("    const allowed = ['general','access','clients','updates','notifications','integrations','users'];", "    const allowed = ['general','access','clients','backups','updates','notifications','integrations','users'];", 1)
    old = '''    const savebar = document.querySelector('#settingsSavebar');\n    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n  }\n'''
    new = '''    const savebar = document.querySelector('#settingsSavebar');\n    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n    if (page === 'backups') loadBackups();\n  }\n'''
    if "if (page === 'backups') loadBackups();" not in text:
        if old not in text:
            raise SystemExit("settings activate marker not found")
        text = text.replace(old, new, 1)
    old = '''    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);\n    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n'''
    new = '''    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);\n    document.querySelector('#backupCreate')?.addEventListener('click', createBackup);\n    document.querySelector('#backupImport')?.addEventListener('click', () => document.querySelector('#backupImportFile')?.click());\n    document.querySelector('#backupImportFile')?.addEventListener('change', event => importBackupFile(event.target.files?.[0] || null));\n    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);\n'''
    if "document.querySelector('#backupCreate')" not in text:
        if old not in text:
            raise SystemExit("settings bind backup marker not found")
        text = text.replace(old, new, 1)

    marker = '''  function updateSourceRepository() {\n    return document.querySelector('#uRepository')?.value.trim() || '';\n  }\n'''
    block = r'''  function formatBackupBytes(value) {
    let size=Math.max(0,Number(value)||0);const units=['B','KB','MB','GB'];let index=0;
    while(size>=1024&&index<units.length-1){size/=1024;index+=1}
    return `${size>=100||index===0?Math.round(size):size.toFixed(1)} ${units[index]}`;
  }

  function formatBackupDate(value) {
    if(!value)return 'Unknown date';
    const date=new Date(value);return Number.isNaN(date.getTime())?'Unknown date':date.toLocaleString();
  }

  function backupKindLabel(kind) {
    return kind==='pre-restore'?'Safety backup':'Backup';
  }

  function setBackupStatus(message='',tone='muted') {
    const status=document.querySelector('#backupStatus');if(!status)return;
    status.className=`test-result ${tone} backup-status`;status.textContent=message;
  }

  function renderBackups() {
    const list=document.querySelector('#backupList');if(!list)return;
    if(!backups.length){list.innerHTML='<div class="settings-empty"><b>No backups yet</b><span>Create a backup here or import a .tdbackup file from another installation.</span></div>';return}
    list.innerHTML='';
    backups.forEach(item=>{
      const row=document.createElement('article');row.className=`backup-item${item.valid===false?' invalid':''}`;
      const details=[backupKindLabel(item.kind),`v${item.source_version||'unknown'}`,formatBackupBytes(item.size),`${Number(item.files||0)} files`];
      row.innerHTML=`<div class="backup-item-copy"><strong>${esc(item.name||'Backup')}</strong><span>${esc(formatBackupDate(item.created_at))} · ${esc(details.join(' · '))}</span>${item.valid===false?`<small>${esc(item.error||'Backup metadata is invalid')}</small>`:''}</div><div class="backup-item-actions"><button class="secondary backup-export" type="button">Export</button><button class="primary backup-restore" type="button" ${item.valid===false?'disabled':''}>Restore</button></div>`;
      row.querySelector('.backup-export')?.addEventListener('click',()=>exportBackup(item.name));
      row.querySelector('.backup-restore')?.addEventListener('click',()=>restoreBackup(item));
      list.appendChild(row);
    });
    applySentenceCaseUi(list);
  }

  async function loadBackups() {
    if(backupsLoading||!state.me?.can_manage)return;
    backupsLoading=true;
    try{const data=await api('/api/backups');backups=data.backups||[];renderBackups()}
    catch(error){setBackupStatus(error.message||'Could not load backups.','bad')}
    finally{backupsLoading=false}
  }

  async function createBackup() {
    const button=document.querySelector('#backupCreate');if(button)button.disabled=true;
    setBackupStatus('Creating a consistent backup of dashboard state…');
    try{const data=await post('/api/backups/create',{});setBackupStatus(`Backup created: ${data.backup?.name||'complete'}`,'ok');toast('Backup created');await loadBackups()}
    catch(error){setBackupStatus(error.message||'Backup creation failed.','bad')}
    finally{if(button)button.disabled=false}
  }

  async function importBackupFile(file) {
    const input=document.querySelector('#backupImportFile');
    if(!file){if(input)input.value='';return}
    if(!String(file.name||'').toLowerCase().endsWith('.tdbackup')){if(input)input.value='';return setBackupStatus('Choose a .tdbackup file.','bad')}
    if(!Number.isFinite(file.size)||file.size<1||file.size>512*1024*1024){if(input)input.value='';return setBackupStatus('Backup must be between 1 byte and 512 MB.','bad')}
    const button=document.querySelector('#backupImport');if(button)button.disabled=true;
    setBackupStatus(`Importing ${file.name}…`);
    try{
      const form=new FormData();form.append('backup',file,file.name);
      const response=await fetch('/api/backups/import',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:form});
      const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
      setBackupStatus(`Imported ${data.backup?.name||file.name}.`,'ok');toast('Backup imported');await loadBackups();
    }catch(error){setBackupStatus(error.message||'Backup import failed.','bad')}
    finally{if(input)input.value='';if(button)button.disabled=false}
  }

  function exportBackup(name) {
    if(!name)return;
    const link=document.createElement('a');link.href=`/api/backups/export?name=${encodeURIComponent(name)}`;link.download=name;link.rel='noopener';document.body.appendChild(link);link.click();link.remove();
  }

  async function restoreBackup(item) {
    const name=String(item?.name||'');if(!name)return;
    const warning=`Restore ${name}?\n\nTorrent Dashboard will first create a safety backup of the current state, then replace configuration and dashboard data with this backup. You will be signed out and must use the restored installation credentials. Application binaries and qBitTorrent data are not changed.`;
    if(!confirm(warning))return;
    setBackupStatus(`Restoring ${name}…`);
    document.querySelectorAll('.backup-item-actions button').forEach(button=>button.disabled=true);
    try{
      const data=await post('/api/backups/restore',{name});
      const safety=data.safety_backup?.name?` Safety backup: ${data.safety_backup.name}.`:'';
      setBackupStatus(`Restore complete.${safety} Reloading…`,'ok');toast('Backup restored');setTimeout(()=>window.location.reload(),700);
    }catch(error){setBackupStatus(error.message||'Backup restore failed.','bad');renderBackups()}
  }

  function updateSourceRepository() {
    return document.querySelector('#uRepository')?.value.trim() || '';
  }
'''
    if "async function loadBackups()" not in text:
        if marker not in text:
            raise SystemExit("settings backup function insertion marker not found")
        text = text.replace(marker, block, 1)
    path.write_text(text, encoding="utf-8")


def update_settings_css() -> None:
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    marker = "/* 0.5.147 portable backup management */"
    if marker in text:
        return
    text += r'''

/* 0.5.147 portable backup management */
.backup-intro{margin:0 0 13px;line-height:1.55}.backup-warning{display:flex;align-items:flex-start;gap:9px;margin:0 0 14px;padding:11px 12px;border:1px solid color-mix(in srgb,#f2b84b 45%,var(--border));border-radius:11px;background:color-mix(in srgb,#f2b84b 8%,var(--panel3))}.backup-warning strong{flex:0 0 auto;font-size:10.5px;color:var(--text)}.backup-warning span{font-size:9.5px;line-height:1.5;color:var(--muted)}.backup-toolbar{margin:0 0 10px}.backup-toolbar button{min-width:145px}.backup-status{margin:0 0 12px}.backup-list{display:grid;gap:8px}.backup-item{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:12px;border:1px solid var(--border);border-radius:12px;background:var(--panel3)}.backup-item.invalid{border-color:color-mix(in srgb,#ff5d6c 40%,var(--border))}.backup-item-copy{display:grid;gap:4px;min-width:0}.backup-item-copy strong{font-size:11.5px;overflow-wrap:anywhere}.backup-item-copy span{font-size:9.5px;line-height:1.45;color:var(--muted)}.backup-item-copy small{font-size:9px;color:#ff7a87;line-height:1.45}.backup-item-actions{display:flex;gap:7px;flex:0 0 auto}.backup-item-actions button{min-width:86px}.backup-status code{font-size:inherit}
@media(max-width:640px){.backup-warning{display:grid}.backup-toolbar{display:grid;grid-template-columns:1fr 1fr}.backup-toolbar button{width:100%;min-width:0}.backup-item{align-items:flex-start;display:grid}.backup-item-actions{display:grid;grid-template-columns:1fr 1fr;width:100%}.backup-item-actions button{width:100%;min-width:0}}
@media(max-width:420px){.backup-toolbar{grid-template-columns:1fr}.backup-item-actions{grid-template-columns:1fr}}
'''
    path.write_text(text, encoding="utf-8")


def write_tests() -> None:
    path = ROOT / "tests" / "test_backups.py"
    path.write_text(r'''from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from torrent_dashboard.backups import (
    backup_path,
    create_backup,
    import_backup,
    list_backups,
    restore_backup,
    validate_backup,
)


def config(title="Original"):
    return {
        "setup": {"complete": True},
        "recovery": {"key_hash": "pbkdf2_sha256$1$c2FsdA$ZGlnZXN0", "last4": "1234"},
        "dashboard": {"title": title},
        "users": [{"id": "admin", "username": "admin", "password_hash": "hash", "group": "administrator"}],
        "servers": [],
        "integrations": [],
    }


class BackupManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name)
        (self.app / "data" / "avatars").mkdir(parents=True)
        (self.app / "data" / "avatars" / "admin.webp").write_bytes(b"avatar")
        (self.app / "data" / "notification-custom.mp3").write_bytes(b"sound")
        (self.app / "data" / "updates" / "0.5.999").mkdir(parents=True)
        (self.app / "data" / "updates" / "0.5.999" / "staged.zip").write_bytes(b"update")
        (self.app / "data" / "update-status.json").write_text("{}", encoding="utf-8")
        (self.app / "data" / "release-integrity.json").write_text("{}", encoding="utf-8")
        (self.app / "data" / "recovery-backups").mkdir(parents=True)
        (self.app / "data" / "recovery-backups" / "config-old.json").write_text("{}", encoding="utf-8")
        db = sqlite3.connect(self.app / "data" / "torrent_desk.sqlite3")
        try:
            db.execute("CREATE TABLE sample(value TEXT)")
            db.execute("INSERT INTO sample VALUES('history')")
            db.commit()
        finally:
            db.close()
        (self.app / "config.json").write_text(json.dumps(config(), indent=2) + "\n", encoding="utf-8")
        self.lock = threading.RLock()

    def tearDown(self):
        self.temp.cleanup()

    def test_create_backup_contains_portable_state_and_excludes_ephemeral_files(self):
        item = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        archive = backup_path(self.app, item["name"])
        manifest = validate_backup(archive, current_version="0.5.147")
        self.assertEqual(manifest["application"], "torrent-dashboard")
        self.assertEqual(manifest["schema"], 1)
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
        self.assertIn("payload/config.json", names)
        self.assertIn("payload/data/torrent_desk.sqlite3", names)
        self.assertIn("payload/data/avatars/admin.webp", names)
        self.assertIn("payload/data/notification-custom.mp3", names)
        self.assertFalse(any(name.startswith("payload/data/updates/") for name in names))
        self.assertNotIn("payload/data/update-status.json", names)
        self.assertNotIn("payload/data/release-integrity.json", names)
        self.assertFalse(any(name.startswith("payload/data/backups/") for name in names))
        self.assertFalse(any(name.startswith("payload/data/recovery-backups/") for name in names))

    def test_import_and_restore_round_trip_preserves_backup_libraries(self):
        original = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        original_path = backup_path(self.app, original["name"])

        destination = self.app / "destination"
        (destination / "data").mkdir(parents=True)
        imported = import_backup(destination, "moved.tdbackup", original_path.read_bytes())
        self.assertEqual(imported["name"], "moved.tdbackup")
        self.assertEqual(len(list_backups(destination)), 1)

        changed = config("Changed")
        (self.app / "config.json").write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
        (self.app / "data" / "stale-state.txt").write_text("remove me", encoding="utf-8")
        result = restore_backup(
            self.app,
            original["name"],
            current_version="0.5.147",
            current_config=changed,
            history_lock=self.lock,
            validator=lambda: json.loads((self.app / "config.json").read_text(encoding="utf-8")),
        )
        restored = json.loads((self.app / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(restored["dashboard"]["title"], "Original")
        self.assertFalse((self.app / "data" / "stale-state.txt").exists())
        self.assertTrue((self.app / "data" / "recovery-backups" / "config-old.json").exists())
        self.assertTrue(backup_path(self.app, original["name"]).exists())
        self.assertEqual(result["safety_backup"]["kind"], "pre-restore")
        self.assertGreaterEqual(len(list_backups(self.app)), 2)

    def test_integrity_failure_is_rejected(self):
        item = create_backup(self.app, "0.5.147", config(), history_lock=self.lock)
        source = backup_path(self.app, item["name"])
        corrupt = self.app / "corrupt.tdbackup"
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(corrupt, "w", zipfile.ZIP_DEFLATED) as rewritten:
            for info in original.infolist():
                data = original.read(info.filename)
                if info.filename == "payload/config.json":
                    data += b" "
                rewritten.writestr(info.filename, data)
        with self.assertRaisesRegex(RuntimeError, "integrity check failed|size mismatch"):
            validate_backup(corrupt, current_version="0.5.147")

    def test_restore_rejects_backup_from_newer_application_version(self):
        item = create_backup(self.app, "9.0.0", config(), history_lock=self.lock)
        with self.assertRaisesRegex(RuntimeError, "update this installation"):
            restore_backup(
                self.app,
                item["name"],
                current_version="0.5.147",
                current_config=config(),
                history_lock=self.lock,
            )


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def update_docs() -> None:
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    section = '''\n## Backups\n\nAdministrators can manage portable installation backups under **Settings → Backups**. A `.tdbackup` archive contains `config.json` plus persistent dashboard state such as history, profile pictures, and notification assets. It does not contain Torrent Dashboard application binaries, staged updates, or qBitTorrent data. Backup archives contain saved credentials and recovery data, so store exported files securely. Restores automatically create a pre-restore safety backup first.\n'''
    if "## Backups\n" not in text:
        text = text.rstrip() + "\n" + section + "\n"
    readme.write_text(text, encoding="utf-8")

    architecture = ROOT / "ARCHITECTURE.md"
    text = architecture.read_text(encoding="utf-8")
    section = '''\n## Portable backup boundary\n\n`src/torrent_dashboard/backups.py` owns portable dashboard-state archives. Backup payloads contain configuration and persistent files under `data/`, use a manifest with per-file SHA-256 digests, and deliberately exclude application code/binaries, updater staging, release caches, nested backup libraries, and qBitTorrent-owned data. The dashboard holds the history-store lock while snapshotting or restoring SQLite state. Restores preserve the local backup and recovery-backup libraries and create a pre-restore safety archive before replacing state.\n'''
    if "## Portable backup boundary\n" not in text:
        text = text.rstrip() + "\n" + section + "\n"
    architecture.write_text(text, encoding="utf-8")

    testing = ROOT / "TESTING.md"
    text = testing.read_text(encoding="utf-8")
    section = '''\n### Portable backup management\n\n- Run `python -m unittest tests.test_backups -v` with `PYTHONPATH=src`.\n- Verify created archives include configuration, history, profile assets, and notification assets while excluding `data/backups`, `data/recovery-backups`, updater staging, and release caches.\n- Export a backup from one installation, import it into a second installation on the same or newer Torrent Dashboard version, restore it, and confirm the restored credentials, integrations, users, history, and assets are present.\n- Confirm restore signs out the current browser session and creates a pre-restore safety backup that can be used to return to the previous state.\n- Corrupt a backup payload and confirm SHA-256 validation prevents restore.\n'''
    if "### Portable backup management\n" not in text:
        text = text.rstrip() + "\n" + section + "\n"
    testing.write_text(text, encoding="utf-8")


def update_release_metadata() -> None:
    notes_path = ROOT / "release_notes" / "releases.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    if not any(str(item.get("version")) == VERSION for item in notes.get("releases", [])):
        notes["releases"].insert(0, {
            "version": VERSION,
            "date": "2026-09-07",
            "status": "prerelease",
            "title": "Portable backup management",
            "summary": "Adds a dedicated in-app backup manager for creating, viewing, restoring, importing, and exporting portable Torrent Dashboard state backups.",
            "highlights": [
                "Adds Settings → Backups as a dedicated administrator maintenance area instead of coupling backup lifecycle to software updates.",
                "Creates portable .tdbackup archives containing configuration, users, saved credentials, integrations, dashboard history, profile pictures, and notification assets while excluding application binaries and qBitTorrent data.",
                "Existing backups can be exported to another installation, imported into its local backup library, and restored from the browser.",
                "Every restore creates a pre-restore safety backup first and signs out active sessions after the restored identity and access configuration becomes active."
            ],
            "fixes": [],
            "technical": [
                "Adds src/torrent_dashboard/backups.py with a versioned manifest, per-file SHA-256 verification, path traversal and symlink rejection, archive size limits, and newer-version restore guards.",
                "SQLite history is captured with the SQLite online backup API while holding the history-store lock so backups remain consistent while the dashboard is running.",
                "Restores preserve local backup/recovery-backup libraries, clear stale runtime/update state, validate the restored configuration, and automatically roll back to the safety backup if applying the payload fails."
            ],
            "validation": [
                "Adds unit coverage for portable archive contents, excluded ephemeral state, import/export library behavior, restore safety snapshots, integrity failures, and newer-version rejection.",
                "Runs source validation, UI string validation, the complete unit-test suite, JavaScript syntax checks, and source-package validation.",
                "Builds and smoke-tests Dashboard.exe, Recovery.exe, and Updater.exe on native Windows after the backup changes are applied."
            ],
            "known_issues": [
                "Portable backup archives are not encrypted and contain saved credentials and recovery data; exported .tdbackup files must be stored securely."
            ],
            "architecture": [
                "Backup archives are state-only portability artifacts. Application code/binaries remain owned by the release/updater system and qBitTorrent-owned data remains outside Torrent Dashboard backups."
            ],
            "decisions": [
                "Place backup management in its own Settings category because backup lifecycle is independent from software update lifecycle.",
                "Preserve the local backup library and legacy recovery config backups across restores so a failed or unwanted migration retains a local escape path.",
                "Do not add backup encryption, scheduling, or remote destinations in the first portable-backup release."
            ],
            "next_steps": [
                {"priority": 1, "title": "Exercise cross-install restore", "detail": "Create and export a backup from one compiled Windows installation, import and restore it on a second same-or-newer build, then use the generated safety backup to return the destination to its prior state."}
            ]
        })
    notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

    current_path = ROOT / "development" / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current.update({
        "status": "ready",
        "objective": "Exercise portable backup migration and restore on compiled Windows installations",
        "why": "Portable backup management is implemented; the remaining risk is operational validation of a full export/import/restore round trip between real installations.",
        "acceptance_criteria": [
            "A compiled Windows installation creates and exports a valid .tdbackup archive from Settings → Backups.",
            "A second same-or-newer installation imports the archive and lists it without modifying current state.",
            "Restoring the imported backup migrates users, credentials, integrations, dashboard history, profile pictures, and notification assets while leaving application binaries and qBitTorrent data untouched.",
            "Restore signs out existing sessions and the automatically created pre-restore safety backup can return the destination to its previous state."
        ],
        "decisions": [
            "Backup management is a dedicated Settings category, not part of Updates.",
            "Portable backups contain dashboard state only and preserve saved secrets for migration fidelity.",
            "Restores always create a safety backup before applying state and reject backups created by a newer Torrent Dashboard version."
        ],
        "files": ["src/torrent_dashboard/backups.py", "src/torrent_dashboard/dashboard.py", "static/index.html", "static/settings.js", "static/settings.css", "tests/test_backups.py"],
        "blockers": [],
        "out_of_scope": ["Encrypted backup archives, scheduled backups, retention policies, and remote/cloud backup destinations in the initial release."],
        "next_action": "Run a compiled Windows create/export/import/restore round trip across two installations, then restore the generated pre-restore safety backup on the destination."
    })
    current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    update_version()
    update_backup_module()
    update_dashboard()
    update_index()
    update_settings_js()
    update_settings_css()
    write_tests()
    update_docs()
    update_release_metadata()


if __name__ == "__main__":
    main()
