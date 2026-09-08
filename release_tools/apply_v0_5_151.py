from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.151"
PREVIOUS = "0.5.150"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_version() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(f'__version__ = "{PREVIOUS}"', f'__version__ = "{VERSION}"')
    path.write_text(text, encoding="utf-8")


def update_login_and_settings_html() -> None:
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")

    old_style = '''<style>
.login-card{
  position:relative;
  isolation:isolate;
  border-color:color-mix(in srgb,var(--accent) 24%,var(--border));
  box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 8%,transparent);
}
.login-card::before{
  content:"";
  position:absolute;
  inset:-18px;
  z-index:-1;
  border-radius:30px;
  background:radial-gradient(ellipse at center,color-mix(in srgb,var(--accent) 28%,transparent) 0%,color-mix(in srgb,var(--accent) 13%,transparent) 44%,transparent 74%);
  filter:blur(17px);
  opacity:.46;
  transform:scale(.985);
  pointer-events:none;
  animation:login-radiant-glow 7s ease-in-out infinite;
}
@keyframes login-radiant-glow{
  0%,100%{opacity:.38;transform:scale(.985)}
  50%{opacity:.68;transform:scale(1.015)}
}
@media (prefers-reduced-motion:reduce){
  .login-card::before{animation:none;opacity:.52;transform:none}
}
</style>'''
    new_style = '''<style>
.login-card{
  position:relative;
  isolation:isolate;
  border-color:color-mix(in srgb,var(--accent) 24%,var(--border));
  box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 8%,transparent);
}
.login-card::before{
  content:"";
  position:absolute;
  inset:-18px;
  z-index:-1;
  border-radius:30px;
  background:radial-gradient(ellipse at center,color-mix(in srgb,var(--accent) 28%,transparent) 0%,color-mix(in srgb,var(--accent) 13%,transparent) 44%,transparent 74%);
  filter:blur(17px);
  opacity:.52;
  transform:none;
  pointer-events:none;
}
</style>'''
    if old_style in text:
        text = text.replace(old_style, new_style, 1)
    elif new_style not in text:
        raise SystemExit("Expected login-card glow style was not found")

    clients_nav = '<button data-view="settings" data-settings-page="clients" type="button">Clients</button>\n'
    backups_nav = '<button data-view="settings" data-settings-page="backups" type="button">Backups</button>\n'
    if backups_nav not in text:
        if clients_nav not in text:
            raise SystemExit("Settings desktop Clients navigation marker was not found")
        text = text.replace(clients_nav, clients_nav + backups_nav, 1)

    old_mobile = '<option value="clients">Clients</option><option value="updates">Updates</option>'
    new_mobile = '<option value="clients">Clients</option><option value="backups">Backups</option><option value="updates">Updates</option>'
    if new_mobile not in text:
        if old_mobile not in text:
            raise SystemExit("Settings mobile navigation marker was not found")
        text = text.replace(old_mobile, new_mobile, 1)

    backup_page = '''<section class="settings-page" data-settings-section="backups">
<div class="panel settings-card backup-settings-card">
<div class="panel-title">Backups</div>
<p class="muted backup-intro">Create portable backups of dashboard settings, integrations, and download clients. Local users, recovery identity, runtime data, application binaries, and qBitTorrent data are not included.</p>
<div class="backup-warning"><strong>Keep backup files secure.</strong><span>Portable backups can contain saved client and integration credentials in readable archive form.</span></div>
<div class="settings-inline-actions backup-toolbar"><button class="primary" id="backupCreate" type="button">Create backup</button><button class="secondary" id="backupImport" type="button">Import backup</button><input accept=".tdbackup,application/zip" class="hidden" id="backupImportFile" type="file"/></div>
<progress class="backup-progress hidden" id="backupProgress" max="100" aria-label="Backup creation progress"></progress>
<div class="test-result muted backup-status" id="backupStatus">Backups are stored locally under <code>data/backups</code>. Export one to move it to another installation.</div>
<div class="backup-list" id="backupList"><div class="settings-empty"><b>Loading backups…</b><span>Local backup archives will appear here.</span></div></div>
</div>
</section>
'''
    if 'data-settings-section="backups"' not in text:
        marker = '<section class="settings-page" data-settings-section="updates">\n'
        if marker not in text:
            raise SystemExit("Settings Updates section marker was not found")
        text = text.replace(marker, backup_page + marker, 1)

    text = text.replace(
        '<button id="accountSettingsBtn" type="button">Account settings</button>',
        '<button id="accountSettingsBtn" role="menuitem" type="button">Account settings</button>',
        1,
    )
    if 'id="accountSettingsBtn"' not in text:
        raise SystemExit("Account settings profile-menu action is missing")

    text = text.replace(PREVIOUS, VERSION)
    text = text.replace("v05150", "v05151")
    path.write_text(text, encoding="utf-8")


def update_login_css() -> None:
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(\.login-shell::before\{content:"";position:absolute;inset:-28%;pointer-events:none;z-index:-1;'
        r'background:radial-gradient\(circle at 28% 34%,color-mix\(in srgb,var\(--accent\) 24%,transparent\),transparent 34%\),'
        r'radial-gradient\(circle at 72% 66%,color-mix\(in srgb,var\(--accent\) 14%,transparent\),transparent 40%\);'
        r'filter:blur\(42px\);)opacity:\.38;transform:scale\(\.94\) translate3d\(-1%,0,0\);'
        r'animation:login-gradient-pulse 9s ease-in-out infinite\}@keyframes login-gradient-pulse\{.*?\}'
        r'@media \(prefers-reduced-motion:reduce\)\{\.login-shell::before\{animation:none;opacity:\.46;transform:none\}\}',
        re.S,
    )
    if "login-gradient-pulse" in text:
        text, count = pattern.subn(r'\1opacity:.46;transform:none}', text, count=1)
        if count != 1:
            raise SystemExit("Could not remove the login background animation")
    if "login-gradient-pulse" in text:
        raise SystemExit("Login background animation still remains")
    path.write_text(text, encoding="utf-8")


def update_backup_css() -> None:
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    marker = "/* 0.5.151 backup lifecycle controls */"
    if marker not in text:
        text += '''

/* 0.5.151 backup lifecycle controls */
.backup-progress{display:block;width:100%;height:8px;margin:0 0 12px;border:0;border-radius:999px;overflow:hidden;background:var(--panel3);accent-color:var(--accent)}
.backup-progress::-webkit-progress-bar{background:var(--panel3);border-radius:999px}.backup-progress::-webkit-progress-value{background:var(--accent);border-radius:999px}.backup-progress::-moz-progress-bar{background:var(--accent);border-radius:999px}
.backup-item-actions .backup-delete{min-width:78px}
@media(max-width:640px){.backup-item-actions{grid-template-columns:repeat(3,1fr)}}
@media(max-width:420px){.backup-item-actions{grid-template-columns:1fr}}
'''
    path.write_text(text, encoding="utf-8")


def update_backup_js() -> None:
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")

    old_row = """      row.innerHTML=`<div class=\"backup-item-copy\"><strong>${esc(item.name||'Backup')}</strong><span>${esc(formatBackupDate(item.created_at))} · ${esc(details.join(' · '))}</span>${item.valid===false?`<small>${esc(item.error||'Backup metadata is invalid')}</small>`:''}</div><div class=\"backup-item-actions\"><button class=\"secondary backup-export\" type=\"button\">Export</button><button class=\"primary backup-restore\" type=\"button\" ${item.valid===false?'disabled':''}>Restore</button></div>`;
      row.querySelector('.backup-export')?.addEventListener('click',()=>exportBackup(item.name));
      row.querySelector('.backup-restore')?.addEventListener('click',()=>restoreBackup(item));
"""
    new_row = """      row.innerHTML=`<div class=\"backup-item-copy\"><strong>${esc(item.name||'Backup')}</strong><span>${esc(formatBackupDate(item.created_at))} · ${esc(details.join(' · '))}</span>${item.valid===false?`<small>${esc(item.error||'Backup metadata is invalid')}</small>`:''}</div><div class=\"backup-item-actions\"><button class=\"secondary backup-export\" type=\"button\">Export</button><button class=\"danger backup-delete\" type=\"button\">Delete</button><button class=\"primary backup-restore\" type=\"button\" ${item.valid===false?'disabled':''}>Restore</button></div>`;
      row.querySelector('.backup-export')?.addEventListener('click',()=>exportBackup(item.name));
      row.querySelector('.backup-delete')?.addEventListener('click',()=>deleteBackup(item));
      row.querySelector('.backup-restore')?.addEventListener('click',()=>restoreBackup(item));
"""
    if old_row in text:
        text = text.replace(old_row, new_row, 1)
    elif new_row not in text:
        raise SystemExit("Backup row rendering block was not found")

    delete_fn = '''  async function deleteBackup(item) {
    const name=String(item?.name||'');if(!name)return;
    if(!confirm(`Delete ${name}?\\n\\nThis permanently removes the local backup archive. It does not change the currently running dashboard configuration.`))return;
    const rowButtons=[...document.querySelectorAll('.backup-item-actions button')];rowButtons.forEach(button=>button.disabled=true);
    setBackupStatus(`Deleting ${name}…`);
    try{await post('/api/backups/delete',{name});setBackupStatus(`Backup deleted: ${name}`,'ok');toast('Backup deleted');await loadBackups()}
    catch(error){setBackupStatus(error.message||'Backup deletion failed.','bad');renderBackups()}
  }

'''
    restore_marker = "  async function restoreBackup(item) {\n"
    if "async function deleteBackup(item)" not in text:
        if restore_marker not in text:
            raise SystemExit("Backup restore function marker was not found")
        text = text.replace(restore_marker, delete_fn + restore_marker, 1)

    old_create = '''  async function createBackup() {
    const button=document.querySelector('#backupCreate');if(button)button.disabled=true;
    setBackupStatus('Creating a consistent backup of dashboard state…');
    try{const data=await post('/api/backups/create',{});setBackupStatus(`Backup created: ${data.backup?.name||'complete'}`,'ok');toast('Backup created');await loadBackups()}
    catch(error){setBackupStatus(error.message||'Backup creation failed.','bad')}
    finally{if(button)button.disabled=false}
  }
'''
    new_create = '''  async function createBackup() {
    const button=document.querySelector('#backupCreate'),progress=document.querySelector('#backupProgress');if(button)button.disabled=true;
    if(progress){progress.classList.remove('hidden');progress.removeAttribute('value');progress.setAttribute('aria-valuetext','Creating backup')}
    setBackupStatus('Creating a consistent backup of portable dashboard settings…');
    try{const data=await post('/api/backups/create',{});if(progress){progress.value=100;progress.setAttribute('aria-valuetext','Backup complete')}setBackupStatus(`Backup created: ${data.backup?.name||'complete'}`,'ok');toast('Backup created');await loadBackups()}
    catch(error){setBackupStatus(error.message||'Backup creation failed.','bad')}
    finally{if(button)button.disabled=false;if(progress){progress.classList.add('hidden');progress.removeAttribute('value');progress.removeAttribute('aria-valuetext')}}
  }
'''
    if old_create in text:
        text = text.replace(old_create, new_create, 1)
    elif new_create not in text:
        raise SystemExit("Backup create function block was not found")

    old_warning = "Torrent Dashboard will first create a safety backup of the current state, then replace configuration and dashboard data with this backup. You will be signed out and must use the restored installation credentials. Application binaries and qBitTorrent data are not changed."
    new_warning = "Torrent Dashboard will first create a safety backup, then replace portable settings, integrations, and download clients with this backup. Local users, recovery identity, runtime data, application binaries, and qBitTorrent data are not changed. You will be signed out after the restore."
    text = text.replace(old_warning, new_warning)
    path.write_text(text, encoding="utf-8")


def update_backups_backend() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "backups.py"
    text = path.read_text(encoding="utf-8")
    marker = '''def import_backup(app_dir: Path, filename: str, content: bytes, *, current_version: str | None = None) -> dict:\n'''
    delete_fn = '''def delete_backup(app_dir: Path, name: str) -> str:
    """Delete one local portable backup archive and return its file name."""
    supplied = str(name or "")
    safe = _safe_filename(supplied)
    if supplied != safe:
        raise RuntimeError("Backup file was not found")
    path = backup_path(app_dir, safe)
    path.unlink()
    return path.name


'''
    if "def delete_backup(" not in text:
        if marker not in text:
            raise SystemExit("Backup import function marker was not found")
        text = text.replace(marker, delete_fn + marker, 1)
    path.write_text(text, encoding="utf-8")


def update_dashboard_backend() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    if "    delete_backup,\n" not in text:
        text = text.replace("    create_backup,\n", "    create_backup,\n    delete_backup,\n", 1)
    handler_marker = '''            if path=="/api/backups/import":\n'''
    delete_handler = '''            if path=="/api/backups/delete":
                data=parse_json_body(self,12000)
                name=delete_backup(APP_DIR,data.get("name"))
                HISTORY.event("dashboard","backup_deleted",name,"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True,"name":name},new_cookie)
'''
    if 'path=="/api/backups/delete"' not in text:
        if handler_marker not in text:
            raise SystemExit("Backup import API marker was not found")
        text = text.replace(handler_marker, delete_handler + handler_marker, 1)
    path.write_text(text, encoding="utf-8")


def update_tests() -> None:
    path = ROOT / "tests" / "test_backups.py"
    text = path.read_text(encoding="utf-8")
    if "    delete_backup,\n" not in text:
        text = text.replace("    create_backup,\n", "    create_backup,\n    delete_backup,\n", 1)
    test = '''    def test_delete_backup_removes_only_named_local_archive(self):
        item = create_backup(self.app, "0.5.151", config(), history_lock=self.lock)
        path = backup_path(self.app, item["name"])
        outside = self.app / "outside.tdbackup"
        outside.write_bytes(b"outside")
        self.assertEqual(delete_backup(self.app, item["name"]), item["name"])
        self.assertFalse(path.exists())
        self.assertTrue(outside.exists())
        self.assertEqual(list_backups(self.app), [])
        with self.assertRaisesRegex(RuntimeError, "not found"):
            delete_backup(self.app, "../outside.tdbackup")
        self.assertTrue(outside.exists())

'''
    class_marker = "    def test_create_backup_contains_configuration_only_and_excludes_identity(self):\n"
    if "test_delete_backup_removes_only_named_local_archive" not in text:
        if class_marker not in text:
            raise SystemExit("Backup test insertion marker was not found")
        text = text.replace(class_marker, test + class_marker, 1)
    path.write_text(text, encoding="utf-8")


def update_ui_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    marker = "    assert 'data-view=\"console\"' in html and 'id=\"accountConsoleBtn\"' not in html\n"
    checks = '''    assert 'id="accountSettingsBtn"' in html and '>Account settings</button>' in html
    assert "$('#accountSettingsBtn').addEventListener('click'" in app_js
    assert 'login-gradient-pulse' not in app_css and 'login-radiant-glow' not in html
    assert 'data-settings-page="backups"' in html and 'data-settings-section="backups"' in html
    assert 'id="backupProgress"' in html and 'class="backup-progress hidden"' in html
    assert 'backup-delete' in settings_js and "post('/api/backups/delete',{name})" in settings_js
    assert 'path=="/api/backups/delete"' in dashboard_py and 'backup_deleted' in dashboard_py
'''
    if "id=\"backupProgress\"" not in text:
        if marker not in text:
            raise SystemExit("UI validator insertion marker was not found")
        text = text.replace(marker, marker + checks, 1)
    path.write_text(text, encoding="utf-8")


def update_frontend_versions() -> None:
    for name in ("app.js", "sw.js"):
        path = ROOT / "static" / name
        text = path.read_text(encoding="utf-8")
        text = text.replace(PREVIOUS, VERSION).replace("v05150", "v05151")
        path.write_text(text, encoding="utf-8")


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not any(str(item.get("version")) == VERSION for item in data.get("releases", [])):
        data["releases"].insert(0, {
            "version": VERSION,
            "date": "2026-09-08",
            "status": "prerelease",
            "title": "Profile and backup lifecycle polish",
            "summary": "Restores the backup-management surface, keeps Account settings in the profile menu, removes login-screen animation, and adds safer backup deletion and creation feedback.",
            "highlights": [
                "Keeps Account settings as an explicit profile-menu action and adds a UI contract check so it cannot disappear silently in a future merge.",
                "Removes the animated login background and card glow while retaining a static accent treatment.",
                "Restores Settings → Backups navigation and the backup manager that was dropped from the v0.5.150 HTML merge.",
                "Adds a Delete action to every local backup row with confirmation before the archive is removed.",
                "Shows an indeterminate progress bar while a backup is being created, then returns to the normal backup list when creation finishes."
            ],
            "fixes": [
                "Repairs the missing Backups Settings page and navigation while preserving the already-implemented backup backend and JavaScript lifecycle.",
                "Synchronizes the next frontend build so stale cached profile-menu markup is replaced by the current Account settings contract."
            ],
            "technical": [
                "Adds delete_backup() with strict local-backup filename validation plus an administrator-only /api/backups/delete endpoint and backup_deleted history event.",
                "Uses the native indeterminate progress element for synchronous backup creation so the UI does not invent a file-by-file percentage that the server does not expose.",
                "Updates backup copy to match the identity-safe portable scope: settings, integrations, and clients move; local users, recovery identity, and runtime data do not."
            ],
            "validation": [
                "Adds backup deletion coverage that confirms only a named local archive can be removed and traversal-style names cannot delete outside data/backups.",
                "Extends UI contract validation for Account settings, the restored Backups page, backup deletion, backup progress, and the absence of login animation.",
                "Runs source validation, UI validation, unit tests, JavaScript syntax checks, generated documentation, repository hygiene, and source-package validation."
            ],
            "known_issues": [
                "Portable backup archives can contain saved client and integration credentials in plaintext; store exported .tdbackup files securely."
            ],
            "architecture": [],
            "decisions": [
                "Keep login accent styling static rather than animated.",
                "Treat backup creation progress as indeterminate until the synchronous server operation completes instead of reporting fabricated percentages.",
                "Require confirmation for destructive backup deletion and constrain deletion to the local backup library."
            ],
            "next_steps": [
                {"priority": 1, "title": "Exercise backup lifecycle on Windows", "detail": "Create, export, delete, import, and restore portable backups on a compiled Windows installation and confirm the profile menu remains stable after update."}
            ]
        })
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    current_path = ROOT / "development" / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current.update({
        "status": "ready",
        "objective": "Validate the v0.5.151 profile and backup lifecycle fixes on compiled Windows",
        "why": "The backup UI regression and profile/login polish are corrected in source; the remaining step is operational validation through a real compiled backup lifecycle and update.",
        "acceptance_criteria": [
            "Source/unit, UI, syntax, generated-documentation, hygiene, and source-package checks pass.",
            "Account settings remains visible and functional from the profile menu after update and cache recovery.",
            "The login screen retains a static accent treatment with no background or card animation.",
            "Settings → Backups lists archives, shows progress during creation, and deletes only the explicitly confirmed local archive.",
            "Portable backup restore continues preserving destination users, recovery identity, and runtime data."
        ],
        "decisions": [
            "Keep login accent styling static rather than animated.",
            "Use indeterminate progress for synchronous backup creation rather than fabricated percentages.",
            "Keep destructive backup deletion administrator-only and constrained to data/backups."
        ],
        "files": [
            "src/torrent_dashboard/backups.py",
            "src/torrent_dashboard/dashboard.py",
            "static/index.html",
            "static/app.css",
            "static/settings.js",
            "static/settings.css",
            "tests/test_backups.py",
            "release_tools/validate_ui_strings.py"
        ],
        "blockers": [],
        "out_of_scope": [
            "Backup encryption, scheduled backups, cloud destinations, streaming byte-level backup progress, code signing, and broader authentication redesign."
        ],
        "next_action": "Run create/delete/import/restore on a compiled Windows build, then verify Account settings and the static login treatment after an updater-driven install."
    })
    current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def validate_applied_source() -> None:
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "src" / "torrent_dashboard" / "dashboard.py").read_text(encoding="utf-8")
    required_html = ('id="accountSettingsBtn"', 'data-settings-page="backups"', 'data-settings-section="backups"', 'id="backupProgress"')
    missing = [item for item in required_html if item not in html]
    if missing:
        raise SystemExit("Applied UI contract is incomplete: " + ", ".join(missing))
    if "login-gradient-pulse" in app_css or "login-radiant-glow" in html:
        raise SystemExit("Login animation still exists")
    if "backup-delete" not in settings_js or "/api/backups/delete" not in dashboard:
        raise SystemExit("Backup deletion contract is incomplete")


def main() -> None:
    update_version()
    update_login_and_settings_html()
    update_login_css()
    update_backup_css()
    update_backup_js()
    update_backups_backend()
    update_dashboard_backend()
    update_tests()
    update_ui_validator()
    update_frontend_versions()
    update_release_metadata()
    validate_applied_source()


if __name__ == "__main__":
    main()
