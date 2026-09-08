from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_top_level_function(path: Path, name: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker = f"def {name}("
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"Could not find function {name} in {path}")
    end = text.find("\ndef ", start + len(marker))
    if end < 0:
        end = text.find("\n\n__all__", start + len(marker))
    if end < 0:
        raise SystemExit(f"Could not determine end of function {name} in {path}")
    text = text[:start] + replacement.rstrip() + "\n" + text[end + 1:]
    path.write_text(text, encoding="utf-8")


def replace_test_method(path: Path, name: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker = f"    def {name}("
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"Could not find test method {name}")
    end = text.find("\n    def ", start + len(marker))
    if end < 0:
        end = text.find("\n\nif __name__", start + len(marker))
    if end < 0:
        raise SystemExit(f"Could not determine end of test method {name}")
    text = text[:start] + replacement.rstrip() + "\n" + text[end + 1:]
    path.write_text(text, encoding="utf-8")


def update_version() -> None:
    init = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    replace_once(init, '__version__ = "0.5.148"', '__version__ = "0.5.149"')
    for path in (ROOT / "static").iterdir():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace("0.5.148", "0.5.149").replace("v05148", "v05149")
        path.write_text(text, encoding="utf-8")


def update_login_visual() -> None:
    css = ROOT / "static" / "app.css"
    old = (
        ".login-shell{min-height:100vh;display:grid;place-items:center;padding:20px}"
        ".login-card{width:min(410px,100%);background:var(--panel);border:1px solid var(--border);"
        "border-radius:22px;padding:30px;box-shadow:var(--shadow);display:grid;gap:13px}"
    )
    new = (
        ".login-shell{min-height:100vh;display:grid;place-items:center;padding:20px;position:relative;overflow:hidden;isolation:isolate}"
        ".login-shell::before{content:\"\";position:absolute;inset:-28%;pointer-events:none;z-index:-1;"
        "background:radial-gradient(circle at 28% 34%,color-mix(in srgb,var(--accent) 24%,transparent),transparent 34%),"
        "radial-gradient(circle at 72% 66%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 40%);"
        "filter:blur(42px);opacity:.38;transform:scale(.94) translate3d(-1%,0,0);animation:login-gradient-pulse 9s ease-in-out infinite}"
        "@keyframes login-gradient-pulse{0%,100%{opacity:.34;transform:scale(.94) translate3d(-1%,0,0)}"
        "50%{opacity:.68;transform:scale(1.07) translate3d(1%,1%,0)}}"
        "@media (prefers-reduced-motion:reduce){.login-shell::before{animation:none;opacity:.46;transform:none}}"
        ".login-card{width:min(410px,100%);background:var(--panel);border:1px solid var(--border);border-radius:22px;"
        "padding:30px;box-shadow:var(--shadow);display:grid;gap:13px;position:relative;z-index:1}"
    )
    replace_once(css, old, new)


def update_recovery_delay() -> None:
    js = ROOT / "static" / "app.js"
    old = (
        "function showSetupRecoveryKey(key,title='Save your recovery key'){const modal=$('#setupRecoveryModal'),"
        "value=$('#setupRecoveryKeyValue'),heading=$('#setupRecoveryTitle');if(!modal||!value)return;"
        "value.textContent=String(key||'');if(heading)heading.textContent=title;modal.classList.remove('hidden')}"
    )
    new = (
        "let setupRecoveryReadyAt=0,setupRecoveryTimer=null;\n"
        "function armSetupRecoveryDelay(){const button=$('#setupRecoveryContinue');if(!button)return;"
        "if(setupRecoveryTimer){clearInterval(setupRecoveryTimer);setupRecoveryTimer=null}"
        "setupRecoveryReadyAt=Date.now()+10000;"
        "const refresh=()=>{const remaining=Math.max(0,Math.ceil((setupRecoveryReadyAt-Date.now())/1000));"
        "if(remaining>0){button.disabled=true;button.textContent=`Continue in ${remaining}s`;return}"
        "button.disabled=false;button.textContent='Continue to dashboard';"
        "if(setupRecoveryTimer){clearInterval(setupRecoveryTimer);setupRecoveryTimer=null}};"
        "refresh();setupRecoveryTimer=setInterval(refresh,250)}\n"
        "function showSetupRecoveryKey(key,title='Save your recovery key'){const modal=$('#setupRecoveryModal'),"
        "value=$('#setupRecoveryKeyValue'),heading=$('#setupRecoveryTitle');if(!modal||!value)return;"
        "value.textContent=String(key||'');if(heading)heading.textContent=title;modal.classList.remove('hidden');armSetupRecoveryDelay()}"
    )
    replace_once(js, old, new)
    replace_once(
        js,
        "$('#setupRecoveryContinue')?.addEventListener('click',()=>location.reload());",
        "$('#setupRecoveryContinue')?.addEventListener('click',()=>{if(Date.now()<setupRecoveryReadyAt)return;location.reload()});",
    )


def update_backups() -> None:
    path = ROOT / "src" / "torrent_dashboard" / "backups.py"
    marker = 'EXCLUDED_DATA_NAMES = PRESERVED_DATA_NAMES | EPHEMERAL_DATA_NAMES\n'
    insert = marker + 'IDENTITY_CONFIG_KEYS = {"users", "recovery"}\nLEGACY_AUTH_IDENTITY_KEYS = {"username", "password_hash"}\nPORTABLE_SCOPE = ["settings", "integrations", "clients"]\n'
    replace_once(path, marker, insert)

    payload_marker = '''def _payload_files(staging: Path) -> list[dict]:
    files = []
    for path in sorted((staging / "payload").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(staging).as_posix()
        files.append({"path": rel, "size": path.stat().st_size, "sha256": _sha256(path)})
    return files
'''
    helpers = payload_marker + '''

def _portable_config(config: dict) -> dict:
    """Return portable settings while excluding user and recovery identity."""
    if not isinstance(config, dict):
        raise RuntimeError("Backup configuration must be a JSON object")
    portable = json.loads(json.dumps(config))
    for key in IDENTITY_CONFIG_KEYS:
        portable.pop(key, None)
    auth = portable.get("auth")
    if isinstance(auth, dict):
        for key in LEGACY_AUTH_IDENTITY_KEYS:
            auth.pop(key, None)
    return portable


def _merge_restored_config(restored: dict, current: dict) -> dict:
    """Apply portable settings while retaining destination identity and recovery state."""
    if not isinstance(restored, dict) or not isinstance(current, dict):
        raise RuntimeError("Backup restore configuration is invalid")
    merged = json.loads(json.dumps(restored))
    current_copy = json.loads(json.dumps(current))
    for key in IDENTITY_CONFIG_KEYS:
        if key in current_copy:
            merged[key] = current_copy[key]
        else:
            merged.pop(key, None)
    auth = merged.get("auth")
    if not isinstance(auth, dict):
        auth = {}
    current_auth = current_copy.get("auth") if isinstance(current_copy.get("auth"), dict) else {}
    for key in LEGACY_AUTH_IDENTITY_KEYS:
        if key in current_auth:
            auth[key] = current_auth[key]
        else:
            auth.pop(key, None)
    merged["auth"] = auth
    return merged
'''
    replace_once(path, payload_marker, helpers)

    replace_top_level_function(path, "create_backup", '''def create_backup(app_dir: Path, version: str, config: dict, *, kind: str = "manual", history_lock=None) -> dict:
    """Create a portable configuration backup without users, recovery keys, or runtime data."""
    app_dir = Path(app_dir).resolve()
    directory = backup_directory(app_dir)
    lock = history_lock if history_lock is not None else nullcontext()
    with lock:
        with tempfile.TemporaryDirectory(prefix="torrent-dashboard-backup-") as tmp_name:
            staging = Path(tmp_name)
            payload = staging / "payload"
            payload.mkdir(parents=True, exist_ok=True)
            portable = _portable_config(config)
            (payload / "config.json").write_text(json.dumps(portable, indent=2) + "\\n", encoding="utf-8")
            files = _payload_files(staging)
            if sum(int(item.get("size") or 0) for item in files) > MAX_BACKUP_BYTES:
                raise RuntimeError("Backup payload exceeds the 512 MB safety limit")
            manifest = {
                "schema": BACKUP_SCHEMA,
                "application": APPLICATION_ID,
                "created_at": _utc_now(),
                "source_version": str(version or "unknown"),
                "kind": str(kind or "manual"),
                "portable": True,
                "scope": PORTABLE_SCOPE,
                "contains_secrets": True,
                "files": files,
            }
            (staging / "backup-manifest.json").write_text(json.dumps(manifest, indent=2) + "\\n", encoding="utf-8")
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".creating-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                    archive.write(staging / "backup-manifest.json", "backup-manifest.json")
                    for item in files:
                        archive.write(staging / item["path"], item["path"])
                validate_backup(temporary)
                destination = _publish_backup(temporary, directory, _backup_filename(kind))
            finally:
                temporary.unlink(missing_ok=True)
    return backup_metadata(destination)
''')

    recovery_check = '''            recovery = config.get("recovery") if isinstance(config.get("recovery"), dict) else {}
            if not str(recovery.get("key_hash") or ""):
                raise RuntimeError("Backup is missing the dashboard recovery key hash")
'''
    scoped_check = '''            scope = manifest.get("scope")
            if scope is not None:
                if scope != PORTABLE_SCOPE:
                    raise RuntimeError("Backup contains an unsupported portability scope")
                if any(key in config for key in IDENTITY_CONFIG_KEYS):
                    raise RuntimeError("Portable backup must not contain users or recovery keys")
                auth = config.get("auth") if isinstance(config.get("auth"), dict) else {}
                if any(key in auth for key in LEGACY_AUTH_IDENTITY_KEYS):
                    raise RuntimeError("Portable backup must not contain user credential material")
'''
    replace_once(path, recovery_check, scoped_check)

    replace_top_level_function(path, "_apply_payload", '''def _apply_payload(app_dir: Path, payload: Path, current_config: dict) -> None:
    config_source = payload / "config.json"
    if not config_source.is_file():
        raise RuntimeError("Backup payload is missing config.json")
    try:
        restored = json.loads(config_source.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("Backup payload config.json is invalid") from exc
    merged = _merge_restored_config(restored, current_config)
    atomic_write_bytes(app_dir / "config.json", (json.dumps(merged, indent=2) + "\\n").encode("utf-8"))
''')
    replace_once(path, '                _apply_payload(app_dir, extracted / "payload")\n', '                _apply_payload(app_dir, extracted / "payload", current_config)\n')
    replace_once(path, '                    _apply_payload(app_dir, rollback_dir / "payload")\n', '                    _apply_payload(app_dir, rollback_dir / "payload", current_config)\n')


def update_backup_tests() -> None:
    path = ROOT / "tests" / "test_backups.py"
    replace_test_method(path, "test_create_backup_contains_portable_state_and_excludes_ephemeral_files", '''    def test_create_backup_contains_configuration_only_and_excludes_identity(self):
        source = config()
        source["servers"] = [{"id": "client", "name": "Desktop", "url": "http://127.0.0.1:8080", "password": "client-secret"}]
        source["integrations"] = [{"id": "sonarr", "type": "sonarr", "name": "Sonarr", "url": "http://sonarr", "api_key": "integration-secret"}]
        source.setdefault("auth", {})["username"] = "admin"
        source["auth"]["password_hash"] = "legacy-user-hash"
        item = create_backup(self.app, "0.5.149", source, history_lock=self.lock)
        archive = backup_path(self.app, item["name"])
        manifest = validate_backup(archive, current_version="0.5.149")
        self.assertEqual(manifest["scope"], ["settings", "integrations", "clients"])
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist())
            portable = json.loads(zipped.read("payload/config.json"))
        self.assertEqual(names, {"backup-manifest.json", "payload/config.json"})
        self.assertNotIn("users", portable)
        self.assertNotIn("recovery", portable)
        self.assertNotIn("username", portable.get("auth", {}))
        self.assertNotIn("password_hash", portable.get("auth", {}))
        self.assertEqual(portable["servers"][0]["password"], "client-secret")
        self.assertEqual(portable["integrations"][0]["api_key"], "integration-secret")
''')

    replace_test_method(path, "test_import_and_restore_round_trip_preserves_backup_libraries", '''    def test_import_and_restore_round_trip_preserves_backup_libraries(self):
        original_config = config()
        original_config["servers"] = [{"id": "original-client", "name": "Original", "url": "http://original"}]
        original_config["integrations"] = [{"id": "original-integration", "type": "sonarr", "name": "Sonarr", "url": "http://original-sonarr"}]
        original = create_backup(self.app, "0.5.149", original_config, history_lock=self.lock)
        original_path = backup_path(self.app, original["name"])
        destination = self.app / "destination"
        (destination / "data").mkdir(parents=True)
        imported = import_backup(destination, "moved.tdbackup", original_path.read_bytes())
        self.assertEqual(imported["name"], "moved.tdbackup")
        changed = config("Changed")
        changed["users"][0]["username"] = "destination-admin"
        changed["users"][0]["password_hash"] = "destination-user-hash"
        changed["recovery"] = {"key_hash": "destination-recovery-hash", "last4": "9876"}
        (self.app / "config.json").write_text(json.dumps(changed, indent=2) + "\\n", encoding="utf-8")
        (self.app / "data" / "stale-state.txt").write_text("preserve me", encoding="utf-8")
        result = restore_backup(self.app, original["name"], current_version="0.5.149", current_config=changed, history_lock=self.lock, validator=lambda: json.loads((self.app / "config.json").read_text(encoding="utf-8")))
        restored = json.loads((self.app / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(restored["dashboard"]["title"], "Original")
        self.assertEqual(restored["servers"], original_config["servers"])
        self.assertEqual(restored["integrations"], original_config["integrations"])
        self.assertEqual(restored["users"], changed["users"])
        self.assertEqual(restored["recovery"], changed["recovery"])
        self.assertTrue((self.app / "data" / "stale-state.txt").exists())
        self.assertTrue((self.app / "data" / "recovery-backups" / "config-old.json").exists())
        self.assertEqual(result["safety_backup"]["kind"], "pre-restore")
''')

    replace_test_method(path, "test_temporary_updater_and_sqlite_sidecars_are_excluded", '''    def test_all_runtime_data_is_excluded_from_new_portable_backups(self):
        item = create_backup(self.app, "0.5.149", config())
        with zipfile.ZipFile(backup_path(self.app, item["name"])) as archive:
            self.assertEqual(set(archive.namelist()), {"backup-manifest.json", "payload/config.json"})
''')

    replace_test_method(path, "test_invalid_creation_never_publishes_a_backup", '''    def test_invalid_creation_never_publishes_a_backup(self):
        invalid = config()
        invalid["setup"]["complete"] = False
        with self.assertRaisesRegex(RuntimeError, "completed"):
            create_backup(self.app, "0.5.149", invalid)
        self.assertEqual(list_backups(self.app), [])
        self.assertEqual(list((self.app / "data" / "backups").iterdir()), [])
''')

    replace_test_method(path, "test_cross_install_restore_and_safety_backup_round_trip", '''    def test_cross_install_restore_preserves_destination_identity_and_runtime_data(self):
        source_config = config()
        source_config["users"][0]["username"] = "source-admin"
        source_config["recovery"] = {"key_hash": "source-recovery", "last4": "1111"}
        source_config["servers"] = [{"id": "source-client", "name": "Source", "url": "http://source"}]
        original = create_backup(self.app, "0.5.149", source_config)
        content = backup_path(self.app, original["name"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            destination_config = config("Destination")
            destination_config["users"][0]["username"] = "destination-admin"
            destination_config["users"][0]["password_hash"] = "destination-user-hash"
            destination_config["recovery"] = {"key_hash": "destination-recovery", "last4": "9999"}
            (destination / "config.json").write_text(json.dumps(destination_config))
            (destination / "data").mkdir()
            (destination / "data" / "destination.txt").write_text("must remain local")
            imported = import_backup(destination, "portable.tdbackup", content)
            result = restore_backup(destination, imported["name"], current_version="0.5.149", current_config=destination_config)
            restored = json.loads((destination / "config.json").read_text())
            self.assertEqual(restored["dashboard"]["title"], "Original")
            self.assertEqual(restored["servers"], source_config["servers"])
            self.assertEqual(restored["users"], destination_config["users"])
            self.assertEqual(restored["recovery"], destination_config["recovery"])
            self.assertTrue((destination / "data" / "destination.txt").is_file())
            restore_backup(destination, result["safety_backup"]["name"], current_version="0.5.149", current_config=restored)
            rolled_back = json.loads((destination / "config.json").read_text())
            self.assertEqual(rolled_back["dashboard"]["title"], "Destination")
            self.assertEqual(rolled_back["users"], destination_config["users"])
            self.assertEqual(rolled_back["recovery"], destination_config["recovery"])
''')

    text = path.read_text(encoding="utf-8")
    anchor = "    def test_failed_restore_rolls_back_previous_state(self):\n"
    legacy_test = '''    def test_legacy_backup_identity_and_data_are_ignored_on_restore(self):
        legacy = config("Legacy source")
        legacy["users"][0]["username"] = "legacy-admin"
        legacy["recovery"] = {"key_hash": "legacy-recovery", "last4": "1111"}
        payload = {"payload/config.json": json.dumps(legacy).encode(), "payload/data/legacy-state.txt": b"legacy data"}
        source = self.archive(payload=payload, version="0.5.149")
        imported = import_backup(self.app, "legacy.tdbackup", source.read_bytes(), current_version="0.5.149")
        current = config("Current destination")
        current["users"][0]["username"] = "current-admin"
        current["recovery"] = {"key_hash": "current-recovery", "last4": "2222"}
        (self.app / "data" / "current-state.txt").write_text("keep", encoding="utf-8")
        restore_backup(self.app, imported["name"], current_version="0.5.149", current_config=current)
        restored = json.loads((self.app / "config.json").read_text())
        self.assertEqual(restored["dashboard"]["title"], "Legacy source")
        self.assertEqual(restored["users"], current["users"])
        self.assertEqual(restored["recovery"], current["recovery"])
        self.assertTrue((self.app / "data" / "current-state.txt").exists())
        self.assertFalse((self.app / "data" / "legacy-state.txt").exists())

'''
    if "test_legacy_backup_identity_and_data_are_ignored_on_restore" not in text:
        if anchor not in text:
            raise SystemExit("Could not insert legacy backup isolation test")
        path.write_text(text.replace(anchor, legacy_test + anchor, 1), encoding="utf-8")


def update_ui_contract() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    marker = '''    assert 'id="setupRecoveryModal"' in html and 'id="setupRecoveryKeyValue"' in html
    assert '/api/recovery/initialize' not in dashboard_py and 'recovery_configured' not in dashboard_py and 'recovery_configured' not in app_js
'''
    replacement = marker + '''    # 0.5.149 makes recovery-key acknowledgement deliberate and gives login a low-motion pulse.
    assert 'setupRecoveryReadyAt=0' in app_js and 'Date.now()+10000' in app_js
    assert 'Continue in ${remaining}s' in app_js and 'Date.now()<setupRecoveryReadyAt' in app_js
    assert '@keyframes login-gradient-pulse' in app_css and 'animation:login-gradient-pulse 9s ease-in-out infinite' in app_css
    assert '@media (prefers-reduced-motion:reduce)' in app_css
'''
    replace_once(path, marker, replacement)


def update_docs() -> None:
    testing = ROOT / "TESTING.md"
    text = testing.read_text(encoding="utf-8")
    section = '''\n\n### Login recovery acknowledgement and backup identity isolation\n\n- Open the sign-in screen and confirm the background gradient pulses slowly without moving the login card; with reduced-motion enabled, confirm the pulse is static.\n- Complete first-run setup and confirm the recovery-key Continue button starts disabled at 10 seconds, counts down, and cannot continue before the countdown expires.\n- Create a portable backup and inspect `payload/config.json`: settings, integrations, and download clients remain present, while `users`, `recovery`, and legacy authentication credential fields are absent.\n- Restore both a new backup and a legacy backup that contains users, recovery data, and runtime files. Confirm the destination users and recovery key remain unchanged and destination runtime data is not replaced.\n'''
    if "### Login recovery acknowledgement and backup identity isolation" not in text:
        testing.write_text(text.rstrip() + section, encoding="utf-8")
    design = ROOT / "DESIGN_LANGUAGE.md"
    text = design.read_text(encoding="utf-8")
    section = '''\n\n## Login pulse and recovery acknowledgement\n\nThe login surface may use a slow ambient accent gradient behind the card, but the card itself stays stationary and readable. The animation uses a long ease-in-out pulse and must become static when `prefers-reduced-motion: reduce` is active.\n\nThe first-run recovery-key modal deliberately holds the Continue action for ten seconds. The button shows the remaining seconds while disabled, then returns to the normal Continue label when the acknowledgement interval ends.\n'''
    if "## Login pulse and recovery acknowledgement" not in text:
        design.write_text(text.rstrip() + section, encoding="utf-8")


def update_release_metadata() -> None:
    notes_path = ROOT / "release_notes" / "releases.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    if not any(str(item.get("version")) == "0.5.149" for item in notes.get("releases", [])):
        notes["releases"].insert(0, {
            "version": "0.5.149", "date": "2026-09-07", "status": "prerelease",
            "title": "Login polish and identity-safe backups",
            "summary": "Adds a slow login pulse and deliberate recovery-key acknowledgement while narrowing portable backup restore to configuration without moving user or recovery identity.",
            "highlights": [
                "The login screen now has a slow, smooth ambient accent-gradient pulse with a reduced-motion fallback.",
                "First-run recovery-key acknowledgement enforces a ten-second countdown before Continue becomes available.",
                "New portable backups carry configuration for settings, integrations, and download clients without users, recovery keys, or runtime data."
            ],
            "fixes": [
                "Restore no longer replaces the destination installation's users, password hashes, recovery key, or legacy authentication credential fields.",
                "Legacy backup archives that contain identity or runtime data remain readable, but restore ignores those identity and runtime portions."
            ],
            "technical": [
                "Portable backup manifests declare the settings/integrations/clients scope; new archives contain only payload/config.json plus the manifest.",
                "Restore merges portable configuration onto the destination identity boundary and leaves the data directory untouched.",
                "The recovery countdown uses a deadline check in addition to the disabled button so the Continue handler cannot navigate early."
            ],
            "validation": [
                "Adds regression coverage for identity-free archive creation, destination identity preservation, legacy backup isolation, rollback, and local runtime-data preservation.",
                "Extends the UI contract audit for the ten-second recovery gate, animated login gradient, and reduced-motion behavior."
            ],
            "known_issues": ["Portable backups still contain saved client and integration credentials in plaintext inside the archive; store exported .tdbackup files securely."],
            "architecture": ["Portable backups are configuration portability artifacts; local users, recovery identity, history, avatars, and other runtime data belong to the destination installation."],
            "decisions": [
                "Preserve authentication policy settings while excluding user identity material from backups.",
                "Keep legacy archives importable, but never apply their users, recovery keys, or runtime data during restore."
            ],
            "next_steps": [{"priority": 1, "title": "Exercise identity-safe cross-install restore", "detail": "Export a backup from one compiled Windows installation and restore it on another, confirming clients and integrations move while the destination users and recovery key remain unchanged."}]
        })
    notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

    current_path = ROOT / "development" / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current.update({
        "status": "ready",
        "objective": "Validate identity-safe portable backup restore and the first-run recovery acknowledgement UX on compiled Windows",
        "why": "Portable configuration now excludes user and recovery identity, and the requested login/recovery UX is implemented; compiled cross-install behavior remains the operational validation step.",
        "acceptance_criteria": [
            "Source/unit, UI, syntax, generated-documentation, and hygiene checks pass.",
            "A new backup contains settings, integrations, and clients but no users, recovery key, legacy user hash, or runtime data.",
            "Restoring a new or legacy archive leaves destination users, recovery key, and runtime data unchanged.",
            "The setup recovery-key Continue action remains unavailable for ten seconds and the login pulse respects reduced-motion.",
            "The prerelease source and Windows packages are published from the same validated main commit."
        ],
        "decisions": [
            "Treat users and dashboard recovery identity as installation-local state, never portable backup state.",
            "Retain compatibility with legacy archives but ignore their identity and runtime payload during restore.",
            "Use an ambient nine-second login pulse and a ten-second recovery acknowledgement gate."
        ],
        "files": ["src/torrent_dashboard/backups.py", "static/app.js", "static/app.css", "tests/test_backups.py", "release_tools/validate_ui_strings.py", "TESTING.md", "DESIGN_LANGUAGE.md"],
        "blockers": [],
        "out_of_scope": ["Backup encryption, scheduled backups, cloud destinations, code signing, and broader authentication redesign."],
        "next_action": "Run a compiled Windows cross-install backup/restore using distinct destination users and recovery keys, then confirm update/rollback remains healthy."
    })
    current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    update_version()
    update_login_visual()
    update_recovery_delay()
    update_backups()
    update_backup_tests()
    update_ui_contract()
    update_docs()
    update_release_metadata()


if __name__ == "__main__":
    main()
