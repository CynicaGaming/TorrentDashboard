#!/usr/bin/env python3
from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard.py"
VALIDATOR = ROOT / "release_tools" / "validate_ui_strings.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    dashboard = replace_once(
        dashboard,
        "from pathlib import Path\n\nfrom torrent_dashboard.users import (",
        "from pathlib import Path\n\nfrom torrent_dashboard.config_store import ConfigStore\nfrom torrent_dashboard.users import (",
        "ConfigStore import",
    )
    dashboard = replace_once(dashboard, 'VERSION = "0.5.55"', 'VERSION = "0.5.56"', "dashboard version")
    dashboard = replace_once(dashboard, "def load_config():", "def _load_config_unlocked():", "load_config definition")
    dashboard = replace_once(dashboard, "def save_config(cfg):", "def _save_config_unlocked(cfg):", "save_config definition")
    dashboard = replace_once(
        dashboard,
        "    tmp.replace(CONFIG_PATH)\n",
        "    tmp.replace(CONFIG_PATH)\n\n\nCONFIG_STORE = ConfigStore(_load_config_unlocked, _save_config_unlocked)\n\n\ndef load_config():\n    return CONFIG_STORE.load()\n\n\ndef save_config(cfg):\n    return CONFIG_STORE.save(cfg)\n\n\ndef mutate_config(transform):\n    return CONFIG_STORE.mutate(transform)\n",
        "configuration store wrappers",
    )

    replacements = [
        (
            '                updated,user=save_current_user_profile(cfg,sess.get("user_id",""),data)\n                save_config(updated); SESSIONS.update_user(user)',
            '                updated,user=mutate_config(lambda current: save_current_user_profile(current,sess.get("user_id",""),data))\n                SESSIONS.update_user(user)',
            "account profile mutation",
        ),
        (
            '                updated,user=change_current_user_password(cfg,sess.get("user_id",""),data.get("current_password"),data.get("new_password"))\n                save_config(updated); SESSIONS.remove_user_except(user.get("id",""),token)',
            '                updated,user=mutate_config(lambda current: change_current_user_password(current,sess.get("user_id",""),data.get("current_password"),data.get("new_password")))\n                SESSIONS.remove_user_except(user.get("id",""),token)',
            "account password mutation",
        ),
        (
            '                updated,user=store_user_avatar(cfg,sess.get("user_id",""),filename,content)\n                save_config(updated)',
            '                updated,user=mutate_config(lambda current: store_user_avatar(current,sess.get("user_id",""),filename,content))',
            "account avatar mutation",
        ),
        (
            '                updated,user=remove_user_avatar(cfg,sess.get("user_id",""))\n                save_config(updated)',
            '                updated,user=mutate_config(lambda current: remove_user_avatar(current,sess.get("user_id","")))',
            "account avatar delete mutation",
        ),
        (
            '                data=parse_json_body(self,20000); updated,item=save_integration(cfg,data); save_config(updated)',
            '                data=parse_json_body(self,20000); updated,item=mutate_config(lambda current: save_integration(current,data))',
            "integration save mutation",
        ),
        (
            '                data=parse_json_body(self,10000); iid=str(data.get("id") or ""); updated=delete_integration(cfg,iid); save_config(updated)',
            '                data=parse_json_body(self,10000); iid=str(data.get("id") or ""); updated,_=mutate_config(lambda current: (delete_integration(current,iid),None))',
            "integration delete mutation",
        ),
        (
            '                data=parse_json_body(self,20000); updated,user=save_user(cfg,data); save_config(updated); SESSIONS.update_user(user)',
            '                data=parse_json_body(self,20000); updated,user=mutate_config(lambda current: save_user(current,data)); SESSIONS.update_user(user)',
            "user save mutation",
        ),
        (
            '                data=parse_json_body(self,10000); uid=str(data.get("id") or ""); updated=delete_user(cfg,uid,sess.get("user_id","")); save_config(updated); delete_user_avatar_files(uid); SESSIONS.remove_user(uid)',
            '                data=parse_json_body(self,10000); uid=str(data.get("id") or ""); updated,_=mutate_config(lambda current: (delete_user(current,uid,sess.get("user_id","")),None)); delete_user_avatar_files(uid); SESSIONS.remove_user(uid)',
            "user delete mutation",
        ),
        (
            '                data=parse_json_body(self); updated=apply_settings_update(cfg,data); save_config(updated)',
            '                data=parse_json_body(self); updated,_=mutate_config(lambda current: (apply_settings_update(current,data),None))',
            "settings mutation",
        ),
        (
            '                data=parse_json_body(self,10000); previous_repo=update_repository(cfg); updated,repo=save_update_source(cfg,data.get("repository") or ""); save_config(updated)',
            '                data=parse_json_body(self,10000)\n                def update_source_mutation(current):\n                    previous_repo=update_repository(current)\n                    updated,repo=save_update_source(current,data.get("repository") or "")\n                    return updated,(previous_repo,repo)\n                updated,(previous_repo,repo)=mutate_config(update_source_mutation)',
            "update source mutation",
        ),
        (
            '                updated, info = store_custom_notification_sound(cfg, filename, content)\n                save_config(updated)',
            '                updated, info = mutate_config(lambda current: store_custom_notification_sound(current, filename, content))',
            "notification sound mutation",
        ),
        (
            '            save_config(out)\n            with CACHE_LOCK:',
            '            def commit_setup(current):\n                if current.get("setup",{}).get("complete"):\n                    raise RuntimeError("Setup has already been completed")\n                return out,None\n            out,_=mutate_config(commit_setup)\n            with CACHE_LOCK:',
            "setup transaction",
        ),
    ]
    for old, new, label in replacements:
        dashboard = replace_once(dashboard, old, new, label)

    old_cli = '''def set_password_cli(password):
    cfg=load_config()
    admin=next((u for u in cfg.get("users",[]) if u.get("group")=="administrator"),None)
    if admin:
        admin["password_hash"]=hash_password(password)
    else:
        cfg.setdefault("users",[]).append(normalize_user({"username":cfg.get("auth",{}).get("username") or "admin","password":password,"group":"administrator"},require_password=True))
    sync_legacy_auth(cfg); save_config(cfg)
    print("Dashboard password updated.")
'''
    new_cli = '''def set_password_cli(password):
    def update_password(cfg):
        admin=next((u for u in cfg.get("users",[]) if u.get("group")=="administrator"),None)
        if admin:
            admin["password_hash"]=hash_password(password)
        else:
            cfg.setdefault("users",[]).append(normalize_user({"username":cfg.get("auth",{}).get("username") or "admin","password":password,"group":"administrator"},require_password=True))
        sync_legacy_auth(cfg)
        return cfg,None
    mutate_config(update_password)
    print("Dashboard password updated.")
'''
    dashboard = replace_once(dashboard, old_cli, new_cli, "CLI password transaction")

    # All configuration writes after the store definitions must now be transactions.
    handler_and_cli = dashboard.split("class Handler(BaseHTTPRequestHandler):", 1)[1]
    if "save_config(" in handler_and_cli:
        raise RuntimeError("A direct save_config call remains in request/CLI code")
    if dashboard.count("mutate_config(") < 12:
        raise RuntimeError("Expected transactional config mutation call sites were not installed")

    DASHBOARD.write_text(dashboard, encoding="utf-8")

    version_files = [
        ROOT / "static" / "index.html",
        ROOT / "static" / "app.js",
        ROOT / "static" / "sw.js",
    ]
    for path in version_files:
        text = path.read_text(encoding="utf-8")
        if "0.5.55" not in text:
            raise RuntimeError(f"{path.relative_to(ROOT)} does not contain the expected 0.5.55 build identifier")
        text = text.replace("0.5.55", "0.5.56")
        if path.name == "sw.js":
            text = text.replace("torrent-dashboard-v0555", "torrent-dashboard-v0556")
        path.write_text(text, encoding="utf-8")

    validator = VALIDATOR.read_text(encoding="utf-8")
    validator = replace_once(
        validator,
        '    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")\n',
        '    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")\n    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")\n',
        "validator config store source",
    )
    validator = replace_once(
        validator,
        '    print("UI string audit passed")\n',
        '''    # 0.5.56 serializes all configuration read/modify/write mutations.
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(_load_config_unlocked, _save_config_unlocked)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
    mutation_section = dashboard_py.split('class Handler(BaseHTTPRequestHandler):', 1)[1]
    assert 'save_config(' not in mutation_section
    assert mutation_section.count('mutate_config(') >= 12

    print("UI string audit passed")
''',
        "validator transaction contract",
    )
    VALIDATOR.write_text(validator, encoding="utf-8")

    for path in (
        DASHBOARD,
        ROOT / "torrent_dashboard" / "users.py",
        ROOT / "torrent_dashboard" / "config_store.py",
        VALIDATOR,
    ):
        py_compile.compile(str(path), doraise=True)

    subprocess.run([sys.executable, "-m", "unittest", "tests.test_config_store"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, check=True)

    # Verify synchronized frontend build identifiers before committing.
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert '<meta content="0.5.56" name="torrent-dashboard-build"/>' in html
    assert "const FRONTEND_BUILD='0.5.56';" in app_js
    assert "?v=0.5.56" in sw
    assert "torrent-dashboard-v0556" in sw

    print("Applied v0.5.56 serialized configuration transactions")


if __name__ == "__main__":
    main()
