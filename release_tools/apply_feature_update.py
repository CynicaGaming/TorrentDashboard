#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not find expected {label} block")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, label: str, flags=0) -> str:
    out, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Expected one {label} match, found {count}")
    return out


def patch_dashboard() -> None:
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.4.0"', 'VERSION = "0.5.0"', 'version')
    text = replace_once(text, '        "read_only": False,\n', '', 'legacy read-only default')

    old_auth = '''    "auth": {
        "mode": "lan_bypass",
        "username": "admin",
        "password_hash": "",
        "trusted_interfaces": [],
        "trusted_ips": [],
        "session_hours": 24,
        "max_login_attempts_per_10m": 20
    },
    "servers": [],'''
    new_auth = '''    "auth": {
        "mode": "lan_bypass",
        "trusted_interfaces": [],
        "trusted_ips": [],
        "session_hours": 24,
        "max_login_attempts_per_10m": 20
    },
    "users": [],
    "servers": [],'''
    text = replace_once(text, old_auth, new_auth, 'auth defaults')

    old_integrations = '''    "integrations": {
        "sonarr": {"url": "", "api_key": ""},
        "radarr": {"url": "", "api_key": ""},
        "lidarr": {"url": "", "api_key": ""},
        "prowlarr": {"url": "", "api_key": ""},
        "jellyfin": {"url": "", "api_key": ""},
        "plex": {"url": "", "token": ""},
        "home_assistant_webhook": ""
    }'''
    text = replace_once(text, old_integrations, '    "integrations": []', 'integration defaults')

    old_return = '''    if legacy_manifest and not updates_raw.get("manifest_url"):
        updates_raw["manifest_url"] = legacy_manifest
        updates_raw["enabled"] = True
    return deep_merge(DEFAULT_CONFIG, raw)
'''
    new_return = '''    if legacy_manifest and not updates_raw.get("manifest_url"):
        updates_raw["manifest_url"] = legacy_manifest
        updates_raw["enabled"] = True

    merged = deep_merge(DEFAULT_CONFIG, raw)
    # Read-only mode is replaced by per-user roles in 0.5.0. Standard Users
    # are read-only; Administrators retain management access.
    merged.setdefault("dashboard", {}).pop("read_only", None)

    raw_users = raw.get("users")
    if isinstance(raw_users, list) and raw_users:
        merged["users"] = [normalize_user(item, item) for item in raw_users if isinstance(item, dict)]
    else:
        legacy_auth = raw.get("auth", {}) if isinstance(raw.get("auth"), dict) else {}
        legacy_hash = str(legacy_auth.get("password_hash") or "")
        if legacy_hash:
            username = str(legacy_auth.get("username") or "admin")[:128]
            merged["users"] = [normalize_user({
                "id": stable_record_id("user", username),
                "username": username,
                "password_hash": legacy_hash,
                "group": "administrator",
            }, require_password=True)]
        else:
            merged["users"] = []

    raw_integrations = raw.get("integrations")
    if isinstance(raw_integrations, list):
        migrated = []
        for item in raw_integrations:
            if not isinstance(item, dict):
                continue
            try:
                migrated.append(normalize_integration(item, item))
            except Exception:
                continue
        merged["integrations"] = migrated
    elif isinstance(raw_integrations, dict):
        migrated = []
        for provider in ("sonarr", "radarr", "lidarr", "prowlarr", "jellyfin", "plex"):
            value = raw_integrations.get(provider) or {}
            if not isinstance(value, dict) or not value.get("url"):
                continue
            payload = {"id": stable_record_id("integration", provider, value.get("url")), "type": provider, "name": INTEGRATION_TYPES[provider]["label"], **value}
            try:
                migrated.append(normalize_integration(payload, payload))
            except Exception:
                continue
        webhook = str(raw_integrations.get("home_assistant_webhook") or "").strip()
        if webhook:
            payload = {"id": stable_record_id("integration", "home_assistant", webhook), "type": "home_assistant", "name": "Home Assistant", "webhook_url": webhook}
            try:
                migrated.append(normalize_integration(payload, payload))
            except Exception:
                pass
        merged["integrations"] = migrated
    else:
        merged["integrations"] = []

    sync_legacy_auth(merged)
    return merged
'''
    text = replace_once(text, old_return, new_return, 'configuration migration')

    session_block = '''class SessionStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}

    def create(self, username, hours, auth_kind, group="administrator", user_id="", display_name=""):
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        expires = time.time() + max(1, float(hours)) * 3600
        with self.lock:
            self.sessions[token] = {
                "username": username,
                "csrf": csrf,
                "expires": expires,
                "auth_kind": auth_kind,
                "group": group,
                "user_id": user_id,
                "display_name": display_name or username,
            }
        return token, dict(self.sessions[token])

    def get(self, token):
        if not token:
            return None
        with self.lock:
            item = self.sessions.get(token)
            if not item:
                return None
            if item["expires"] < time.time():
                self.sessions.pop(token, None)
                return None
            return dict(item)

    def remove(self, token):
        with self.lock:
            self.sessions.pop(token, None)

    def update_user(self, user):
        uid = str(user.get("id") or "")
        if not uid:
            return
        with self.lock:
            for item in self.sessions.values():
                if item.get("user_id") == uid:
                    item["username"] = user.get("username", item.get("username", ""))
                    item["group"] = user.get("group", item.get("group", "standard"))
                    item["display_name"] = user_display_name(user)

    def remove_user(self, user_id):
        uid = str(user_id or "")
        with self.lock:
            doomed = [token for token, item in self.sessions.items() if item.get("user_id") == uid]
            for token in doomed:
                self.sessions.pop(token, None)
'''
    text = sub_once(text, r'class SessionStore:.*?\n\nSESSIONS = SessionStore\(\)', session_block + '\n\nSESSIONS = SessionStore()', 'session store', re.S)

    feature_helpers = r'''
USER_GROUPS = {
    "administrator": "Administrator",
    "standard": "Standard User",
}

INTEGRATION_TYPES = {
    "sonarr": {
        "label": "Sonarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:8989", "required": True},
            {"key": "api_key", "label": "API Key", "secret": True, "required": True},
        ],
    },
    "radarr": {
        "label": "Radarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:7878", "required": True},
            {"key": "api_key", "label": "API Key", "secret": True, "required": True},
        ],
    },
    "lidarr": {
        "label": "Lidarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:8686", "required": True},
            {"key": "api_key", "label": "API Key", "secret": True, "required": True},
        ],
    },
    "prowlarr": {
        "label": "Prowlarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:9696", "required": True},
            {"key": "api_key", "label": "API Key", "secret": True, "required": True},
        ],
    },
    "jellyfin": {
        "label": "Jellyfin",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:8096", "required": True},
            {"key": "api_key", "label": "API Key", "secret": True, "required": True},
        ],
    },
    "plex": {
        "label": "Plex",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:32400", "required": True},
            {"key": "token", "label": "Token", "secret": True, "required": True},
        ],
    },
    "home_assistant": {
        "label": "Home Assistant",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "placeholder": "https://home-assistant.example/api/webhook/...", "required": True},
        ],
    },
}


def stable_record_id(kind, *parts):
    raw = kind + ":" + ":".join(str(x or "") for x in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def user_display_name(user):
    full = " ".join(x for x in (str(user.get("first_name") or "").strip(), str(user.get("last_name") or "").strip()) if x).strip()
    return full or str(user.get("username") or "User")


def normalize_user(data, existing=None, require_password=False):
    existing = existing or {}
    uid = str(data.get("id") or existing.get("id") or uuid.uuid4().hex[:12])[:64]
    username = str(data.get("username") if data.get("username") is not None else existing.get("username") or "").strip()[:128]
    if not username:
        raise RuntimeError("Username is required")
    if not re.fullmatch(r"[A-Za-z0-9_.@-]+", username):
        raise RuntimeError("Username may contain letters, numbers, dots, underscores, hyphens, and @")
    group_raw = str(data.get("group") or existing.get("group") or "standard").strip().lower().replace(" ", "_")
    if group_raw in ("admin", "administrator"):
        group = "administrator"
    elif group_raw in ("standard", "standard_user", "user"):
        group = "standard"
    else:
        raise RuntimeError("User group must be Administrator or Standard User")
    email = str(data.get("email") if data.get("email") is not None else existing.get("email") or "").strip()[:254]
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        raise RuntimeError("Enter a valid email address or leave it blank")
    password_hash = str(data.get("password_hash") or existing.get("password_hash") or "")
    password = str(data.get("password") or "")
    if password:
        password_hash = hash_password(password)
    if require_password and not password_hash:
        raise RuntimeError("Password is required for a new user")
    return {
        "id": uid,
        "username": username,
        "password_hash": password_hash,
        "first_name": str(data.get("first_name") if data.get("first_name") is not None else existing.get("first_name") or "").strip()[:128],
        "last_name": str(data.get("last_name") if data.get("last_name") is not None else existing.get("last_name") or "").strip()[:128],
        "email": email,
        "group": group,
    }


def public_user(user):
    return {
        "id": str(user.get("id") or ""),
        "username": str(user.get("username") or ""),
        "first_name": str(user.get("first_name") or ""),
        "last_name": str(user.get("last_name") or ""),
        "email": str(user.get("email") or ""),
        "group": "administrator" if user.get("group") == "administrator" else "standard",
        "group_label": USER_GROUPS.get(user.get("group"), "Standard User"),
        "display_name": user_display_name(user),
    }


def user_by_username(cfg, username):
    wanted = str(username or "").casefold()
    return next((u for u in cfg.get("users", []) if str(u.get("username") or "").casefold() == wanted), None)


def user_by_id(cfg, user_id):
    wanted = str(user_id or "")
    return next((u for u in cfg.get("users", []) if str(u.get("id") or "") == wanted), None)


def session_is_admin(sess):
    return bool(sess and sess.get("group") == "administrator")


def sync_legacy_auth(cfg):
    auth = cfg.setdefault("auth", {})
    admins = [u for u in cfg.get("users", []) if u.get("group") == "administrator"]
    chosen = admins[0] if admins else (cfg.get("users") or [None])[0]
    if chosen:
        auth["username"] = chosen.get("username", "admin")
        auth["password_hash"] = chosen.get("password_hash", "")
    else:
        auth["username"] = "admin"
        auth["password_hash"] = ""
    return cfg


def save_user(cfg, data):
    out = json.loads(json.dumps(cfg))
    users = out.setdefault("users", [])
    user_id = str(data.get("id") or "")
    existing = next((u for u in users if str(u.get("id") or "") == user_id), None) if user_id else None
    item = normalize_user(data, existing, require_password=existing is None)
    duplicate = next((u for u in users if str(u.get("id") or "") != item["id"] and str(u.get("username") or "").casefold() == item["username"].casefold()), None)
    if duplicate:
        raise RuntimeError("That username is already in use")
    if existing:
        users[users.index(existing)] = item
    else:
        users.append(item)
    if not any(u.get("group") == "administrator" for u in users):
        raise RuntimeError("At least one Administrator account is required")
    sync_legacy_auth(out)
    return out, item


def delete_user(cfg, user_id, current_user_id=""):
    user_id = str(user_id or "")
    if not user_id:
        raise RuntimeError("User ID is required")
    if current_user_id and user_id == str(current_user_id):
        raise RuntimeError("You cannot delete the account you are currently using")
    out = json.loads(json.dumps(cfg))
    before = len(out.get("users", []))
    out["users"] = [u for u in out.get("users", []) if str(u.get("id") or "") != user_id]
    if len(out["users"]) == before:
        raise RuntimeError("User was not found")
    if not any(u.get("group") == "administrator" for u in out["users"]):
        raise RuntimeError("At least one Administrator account is required")
    sync_legacy_auth(out)
    return out


def integration_catalog():
    out = []
    for provider, spec in INTEGRATION_TYPES.items():
        fields = []
        for field in spec.get("fields", []):
            fields.append({k: v for k, v in field.items() if k in ("key", "label", "placeholder", "secret", "required", "input_type")})
        out.append({"type": provider, "label": spec["label"], "fields": fields})
    return out


def normalize_integration(data, existing=None):
    existing = existing or {}
    provider = str(data.get("type") or existing.get("type") or "").strip().lower()
    spec = INTEGRATION_TYPES.get(provider)
    if not spec:
        raise RuntimeError("Unsupported integration type")
    item = {
        "id": str(data.get("id") or existing.get("id") or uuid.uuid4().hex[:12])[:64],
        "type": provider,
        "name": str(data.get("name") or existing.get("name") or spec["label"]).strip()[:128],
        "enabled": bool(data.get("enabled", existing.get("enabled", True))),
    }
    for field in spec.get("fields", []):
        key = field["key"]
        supplied = data.get(key)
        if field.get("secret") and supplied in (None, "", "<configured>"):
            value = existing.get(key, "")
        elif supplied is None:
            value = existing.get(key, "")
        else:
            value = str(supplied).strip()
        if field.get("required") and not value:
            raise RuntimeError(f"{field['label']} is required")
        if key.endswith("url") or key == "url":
            if value and not str(value).startswith(("http://", "https://")):
                raise RuntimeError(f"{field['label']} must start with http:// or https://")
            value = str(value).rstrip("/") if key == "url" else str(value)
        item[key] = value
    return item


def redacted_integrations(cfg):
    result = []
    for source in cfg.get("integrations", []):
        item = json.loads(json.dumps(source))
        configured = []
        spec = INTEGRATION_TYPES.get(item.get("type"), {})
        for field in spec.get("fields", []):
            if field.get("secret") and item.get(field["key"]):
                configured.append(field["key"])
                item[field["key"]] = "<configured>"
        item["configured_secrets"] = configured
        result.append(item)
    return result


def test_integration_connection(item):
    item = normalize_integration(item, item)
    provider = item["type"]
    spec = INTEGRATION_TYPES[provider]
    label = spec["label"]
    try:
        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):
            req = urllib.request.Request(item["url"].rstrip("/") + "/api/v3/system/status", headers={"X-Api-Key": item["api_key"], "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read(200000).decode("utf-8"))
            version = str(data.get("version") or "").strip()
        elif provider == "jellyfin":
            req = urllib.request.Request(item["url"].rstrip("/") + "/System/Info", headers={"X-Emby-Token": item["api_key"], "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read(200000).decode("utf-8"))
            version = str(data.get("Version") or data.get("ProductVersion") or "").strip()
        elif provider == "plex":
            req = urllib.request.Request(item["url"].rstrip("/") + "/identity", headers={"X-Plex-Token": item["token"]})
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "home_assistant":
            body = json.dumps({"title": "Torrent Dashboard Test", "message": "Integration connection test"}).encode("utf-8")
            req = urllib.request.Request(item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        else:
            raise RuntimeError("Unsupported integration type")
        return {"ok": True, "message": f"Connected · {label}{(' ' + version) if version else ''}"}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{label} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to {label}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned an invalid response") from exc


def save_integration(cfg, data):
    out = json.loads(json.dumps(cfg))
    integrations = out.setdefault("integrations", [])
    item_id = str(data.get("id") or "")
    existing = next((x for x in integrations if str(x.get("id") or "") == item_id), None) if item_id else None
    item = normalize_integration(data, existing)
    if existing:
        integrations[integrations.index(existing)] = item
    else:
        integrations.append(item)
    return out, item


def delete_integration(cfg, integration_id):
    integration_id = str(integration_id or "")
    if not integration_id:
        raise RuntimeError("Integration ID is required")
    out = json.loads(json.dumps(cfg))
    before = len(out.get("integrations", []))
    out["integrations"] = [x for x in out.get("integrations", []) if str(x.get("id") or "") != integration_id]
    if len(out["integrations"]) == before:
        raise RuntimeError("Integration was not found")
    return out

'''
    text = replace_once(text, 'SETUP_CODE = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()\n\n\ndef normalize_qbittorrent_server', 'SETUP_CODE = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()\n\n' + feature_helpers + '\ndef normalize_qbittorrent_server', 'feature helpers')

    old_ha = '''    ha = cfg.get("integrations", {}).get("home_assistant_webhook")
    if ha:
        try:
            data = json.dumps({"title":title,"message":message}).encode()
            urllib.request.urlopen(urllib.request.Request(ha,data=data,headers={"Content-Type":"application/json"},method="POST"),timeout=5).read()
        except Exception: pass
'''
    new_ha = '''    for integration in cfg.get("integrations", []):
        if integration.get("type") != "home_assistant" or not integration.get("enabled", True) or not integration.get("webhook_url"):
            continue
        try:
            data = json.dumps({"title":title,"message":message}).encode()
            urllib.request.urlopen(urllib.request.Request(integration["webhook_url"],data=data,headers={"Content-Type":"application/json"},method="POST"),timeout=5).read()
        except Exception:
            pass
'''
    text = replace_once(text, old_ha, new_ha, 'Home Assistant notification integration')

    new_matcher = '''def torrent_integration_matches(cfg, hash_):
    out=[]
    for integration in cfg.get("integrations", []):
        name=integration.get("type")
        if name not in ("sonarr","radarr","lidarr") or not integration.get("enabled",True):
            continue
        if not integration.get("url") or not integration.get("api_key"):
            continue
        url=integration["url"].rstrip("/")+"/api/v3/queue?page=1&pageSize=200&includeUnknownSeriesItems=true&includeUnknownMovieItems=true"
        try:
            req=urllib.request.Request(url,headers={"X-Api-Key":integration["api_key"]})
            data=json.loads(urllib.request.urlopen(req,timeout=5).read().decode())
            records=data.get("records",data if isinstance(data,list) else [])
            for rec in records:
                if str(rec.get("downloadId","")).lower()==hash_.lower():
                    out.append({"integration":integration.get("name") or INTEGRATION_TYPES[name]["label"],"title":rec.get("title") or rec.get("series",{}).get("title") or rec.get("movie",{}).get("title"),"status":rec.get("status"),"trackedDownloadStatus":rec.get("trackedDownloadStatus")})
        except Exception:
            pass
    return out


def parse_json_body'''
    text = sub_once(text, r'def integrations_status\(cfg\):.*?\ndef parse_json_body', new_matcher, 'integration status/matcher', re.S)

    text = replace_once(text,
        '            token,sess=SESSIONS.create("LAN" if mode!="disabled" else "Guest",a.get("session_hours",24),"lan_bypass" if mode!="disabled" else "disabled")',
        '            token,sess=SESSIONS.create("LAN" if mode!="disabled" else "Guest",a.get("session_hours",24),"lan_bypass" if mode!="disabled" else "disabled",group="administrator",display_name="Trusted Network" if mode!="disabled" else "Guest")',
        'trusted-network session')

    old_me = '            safe={"authenticated":True,"username":sess["username"],"auth_kind":sess["auth_kind"],"csrf":sess["csrf"],"auth_mode":cfg["auth"].get("mode"),"read_only":cfg["dashboard"].get("read_only",False),"title":cfg["dashboard"].get("title"),"version":VERSION,"lan_ip":local_lan_ip(),"port":cfg["dashboard"].get("port",8765),"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http"}'
    new_me = '            safe={"authenticated":True,"username":sess["username"],"display_name":sess.get("display_name") or sess["username"],"user_id":sess.get("user_id","") ,"group":sess.get("group","standard"),"group_label":USER_GROUPS.get(sess.get("group"),"Standard User"),"can_manage":session_is_admin(sess),"auth_kind":sess["auth_kind"],"csrf":sess["csrf"],"auth_mode":cfg["auth"].get("mode"),"title":cfg["dashboard"].get("title"),"version":VERSION,"refresh_seconds":cfg["dashboard"].get("refresh_seconds",2),"lan_ip":local_lan_ip(),"port":cfg["dashboard"].get("port",8765),"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http"}'
    text = replace_once(text, old_me, new_me, 'current-user response')

    get_anchor = '''        cfg,token,sess,new_cookie=ctx

        if path=="/api/status":'''
    get_guard = '''        cfg,token,sess,new_cookie=ctx
        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces") and not session_is_admin(sess):
            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)

        if path=="/api/status":'''
    text = replace_once(text, get_anchor, get_guard, 'administrator GET guard')

    old_get_routes = '''        if path=="/api/integrations": return self.send_json(200,integrations_status(cfg),new_cookie)
        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)'''
    new_get_routes = '''        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)
        if path=="/api/users": return self.send_json(200,{"users":[public_user(u) for u in cfg.get("users",[])],"current_user_id":sess.get("user_id","")},new_cookie)
        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)'''
    text = replace_once(text, old_get_routes, new_get_routes, 'settings GET routes')

    post_guard = '''        cfg,token,sess,new_cookie=ctx
        if not session_is_admin(sess):
            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)
        try:'''
    text = sub_once(text, r'        cfg,token,sess,new_cookie=ctx\n        if cfg\["dashboard"\]\.get\("read_only"\).*?\n        try:', post_guard, 'administrator POST guard', re.S)

    client_test_route = '''            if path=="/api/client-test":
                data=parse_json_body(self); sid=str(data.get("id") or "")
                existing=next((x for x in cfg.get("servers",[]) if x.get("id")==sid),{})
                server=normalize_qbittorrent_server(data,existing)
                return self.send_json(200,test_server_connection(server),new_cookie)
'''
    new_routes = client_test_route + '''            if path=="/api/integration-test":
                data=parse_json_body(self,20000); iid=str(data.get("id") or "")
                existing=next((x for x in cfg.get("integrations",[]) if str(x.get("id") or "")==iid),{})
                item=normalize_integration(data,existing)
                return self.send_json(200,test_integration_connection(item),new_cookie)
            if path=="/api/integrations":
                data=parse_json_body(self,20000); updated,item=save_integration(cfg,data); save_config(updated)
                HISTORY.event("dashboard","integration_saved",item.get("name",item.get("type","")),"",{"client_ip":self.client_ip(),"type":item.get("type")})
                return self.send_json(200,{"ok":True,"integration":redacted_integrations({"integrations":[item]})[0]},new_cookie)
            if path=="/api/integrations/delete":
                data=parse_json_body(self,10000); iid=str(data.get("id") or ""); updated=delete_integration(cfg,iid); save_config(updated)
                HISTORY.event("dashboard","integration_deleted",iid,"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True},new_cookie)
            if path=="/api/users":
                data=parse_json_body(self,20000); updated,user=save_user(cfg,data); save_config(updated); SESSIONS.update_user(user)
                HISTORY.event("dashboard","user_saved",user.get("username",""),"",{"client_ip":self.client_ip(),"group":user.get("group")})
                return self.send_json(200,{"ok":True,"user":public_user(user)},new_cookie)
            if path=="/api/users/delete":
                data=parse_json_body(self,10000); uid=str(data.get("id") or ""); updated=delete_user(cfg,uid,sess.get("user_id","")); save_config(updated); SESSIONS.remove_user(uid)
                HISTORY.event("dashboard","user_deleted",uid,"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True},new_cookie)
'''
    text = replace_once(text, client_test_route, new_routes, 'integration and user POST routes')

    text = replace_once(text, '            out["dashboard"]["read_only"]=bool(dashboard.get("read_only",False))\n', '', 'setup read-only write')
    old_setup_auth = '''            out["auth"]["mode"]=mode
            out["auth"]["username"]=username
            out["auth"]["trusted_interfaces"]=trusted_interfaces
            out["auth"]["trusted_ips"]=trusted_ips
            out["auth"]["password_hash"]=hash_password(password) if password else ""
            out["servers"]=normalized
            save_config(out)'''
    new_setup_auth = '''            out["auth"]["mode"]=mode
            out["auth"]["trusted_interfaces"]=trusted_interfaces
            out["auth"]["trusted_ips"]=trusted_ips
            admin_user=normalize_user({"username":username,"password":password,"group":"administrator"},require_password=mode in ("required","lan_bypass"))
            out["users"]=[admin_user]
            out["integrations"]=[]
            sync_legacy_auth(out)
            out["servers"]=normalized
            save_config(out)'''
    text = replace_once(text, old_setup_auth, new_setup_auth, 'setup administrator creation')
    text = replace_once(text,
        '            token,sess=SESSIONS.create(username,out["auth"].get("session_hours",24),auth_kind)',
        '            token,sess=SESSIONS.create(username,out["auth"].get("session_hours",24),auth_kind,group="administrator",user_id=admin_user["id"],display_name=user_display_name(admin_user))',
        'setup administrator session')

    login_route = '''    def login_route(self):
        cfg=load_config(); a=cfg["auth"]; ip=self.client_ip(); now=time.time(); limit=max(1,int(a.get("max_login_attempts_per_10m",20)))
        with LOGIN_LOCK:
            q=LOGIN_ATTEMPTS[ip]
            while q and q[0]<now-600: q.popleft()
            if len(q)>=limit: return self.send_json(429,{"error":"Too many login attempts"})
            q.append(now)
        try: data=parse_json_body(self,10000)
        except Exception as e: return self.send_json(400,{"error":str(e)})
        username=str(data.get("username","")).strip()
        user=user_by_username(cfg,username)
        encoded=str((user or {}).get("password_hash") or "")
        if not user or not encoded or not verify_password(str(data.get("password","")),encoded):
            HISTORY.event("dashboard", "login_failed", username[:128], "", {"client_ip": ip})
            return self.send_json(401,{"error":"Invalid username or password"})
        token,sess=SESSIONS.create(user["username"],a.get("session_hours",24),"password",group=user.get("group","standard"),user_id=user.get("id",""),display_name=user_display_name(user))
        HISTORY.event("dashboard", "login_success", user["username"], "", {"client_ip": ip,"group":user.get("group")})
        return self.send_json(200,{"ok":True,"csrf":sess["csrf"],"group":user.get("group")},token)

    def serve_static'''
    text = sub_once(text, r'    def login_route\(self\):.*?\n    def serve_static', login_route, 'multi-user login route', re.S)

    redacted_and_settings = '''def redacted_config(cfg):
    out=json.loads(json.dumps(cfg))
    out.setdefault("auth",{}).pop("password_hash",None)
    out.setdefault("auth",{}).pop("username",None)
    if out.get("updates",{}).get("github_token"): out["updates"]["github_token"]="<configured>"
    for s in out.get("servers",[]):
        if s.get("password"): s["password"]="<configured>"
        if s.get("api_key"): s["api_key"]="<configured>"
    out["users"]=[public_user(u) for u in cfg.get("users",[])]
    out["integrations"]=redacted_integrations(cfg)
    n=out.get("notifications",{})
    for secret in ("gotify_token","telegram_bot_token"):
        if n.get(secret): n[secret]="<configured>"
    out["runtime"]={
        "detected_lan": detect_lan_network(),
        "local_ip": local_lan_ip(),
        "network_interfaces": detect_network_interfaces(),
        "trusted_interface_networks": interface_networks(cfg.get("auth",{}).get("trusted_interfaces",[])),
        "effective_trusted_cidrs": effective_trusted_cidrs(cfg.get("auth",{})),
        "updateState": update_state(),
    }
    return out


def apply_settings_update(cfg,data):
    # Core settings are intentionally separate from user and integration CRUD.
    out=json.loads(json.dumps(cfg))
    dash=data.get("dashboard",{})
    for k in ("title","port","refresh_seconds","history_retention_days","history_sample_seconds","low_disk_gb","https_enabled","https_cert","https_key"):
        if k in dash: out["dashboard"][k]=dash[k]
    out.setdefault("dashboard",{}).pop("read_only",None)
    if "port" in dash:
        out["dashboard"]["port"]=max(1,min(65535,int(dash.get("port") or 8765)))
    updates=data.get("updates",{})
    if "enabled" in updates: out["updates"]["enabled"]=bool(updates.get("enabled"))
    if "repository" in updates:
        repo=str(updates.get("repository") or "").strip()
        out["updates"]["repository"]=normalize_github_repository(repo) if repo else ""
    if "github_token" in updates:
        token=str(updates.get("github_token") or "")
        if token and token != "<configured>": out["updates"]["github_token"]=token.strip()
    if "auto_check" in updates: out["updates"]["auto_check"]=bool(updates.get("auto_check"))
    if "check_hours" in updates: out["updates"]["check_hours"]=max(1,min(168,int(updates.get("check_hours") or 6)))
    if out["updates"].get("enabled") and not out["updates"].get("repository"):
        raise RuntimeError("Set a GitHub repository before enabling updates")
    auth=data.get("auth",{})
    if "mode" in auth:
        if auth["mode"] not in ("required","lan_bypass","disabled"): raise RuntimeError("Invalid auth mode")
        if auth["mode"] in ("required","lan_bypass") and not any(u.get("password_hash") for u in out.get("users",[])):
            raise RuntimeError("Set a user password in User Management before enabling password-protected access")
        out["auth"]["mode"]=auth["mode"]
    if "trusted_interfaces" in auth:
        ids=[str(x) for x in (auth.get("trusted_interfaces") or []) if str(x)]
        detected_ids={x.get("interface_id") for x in detect_network_interfaces()}
        missing=[x for x in ids if x not in detected_ids]
        if missing: raise RuntimeError("Selected network interface is unavailable: " + ", ".join(missing))
        out["auth"]["trusted_interfaces"]=ids
    if "trusted_ips" in auth:
        values=[str(x).strip() for x in (auth.get("trusted_ips") or []) if str(x).strip()]
        for value in values: normalize_trusted_entry(value)
        out["auth"]["trusted_ips"]=values
    if out["auth"].get("mode")=="lan_bypass" and not out["auth"].get("trusted_interfaces") and not out["auth"].get("trusted_ips"):
        raise RuntimeError("Select at least one trusted network interface or add an IP address to the whitelist.")
    if "servers" in data:
        existing={s.get("id"):s for s in out.get("servers",[])}; new=[]
        for s in data["servers"]:
            sid=str(s.get("id") or uuid.uuid4().hex[:8])[:64]
            prev=existing.get(sid,{})
            item=normalize_qbittorrent_server({**s,"id":sid},prev)
            new.append(item)
        out["servers"]=new
    if "notifications" in data:
        for k,v in data["notifications"].items():
            if k in out["notifications"] and v!="<configured>": out["notifications"][k]=v
    sync_legacy_auth(out)
    return out


def set_password_cli(password):
    cfg=load_config()
    admin=next((u for u in cfg.get("users",[]) if u.get("group")=="administrator"),None)
    if admin:
        admin["password_hash"]=hash_password(password)
    else:
        cfg.setdefault("users",[]).append(normalize_user({"username":cfg.get("auth",{}).get("username") or "admin","password":password,"group":"administrator"},require_password=True))
    sync_legacy_auth(cfg); save_config(cfg)
    print("Dashboard password updated.")
'''
    text = sub_once(text, r'def redacted_config\(cfg\):.*?\ndef set_password_cli\(password\):.*?\n    print\("Dashboard password updated\."\)\n', redacted_and_settings, 'redacted settings and password CLI', re.S)

    path.write_text(text, encoding="utf-8")


def patch_index() -> None:
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace('/static/app.css?v=0.4.0-pre1', '/static/app.css?v=0.5.0')
    text = replace_once(text, '<link href="/static/app.css?v=0.5.0" rel="stylesheet"/>', '<link href="/static/app.css?v=0.5.0" rel="stylesheet"/>\n<link href="/static/settings.css?v=0.5.0" rel="stylesheet"/>', 'settings stylesheet link')
    text = text.replace('<label class="toggle"><input id="wReadOnly" type="checkbox"/><span>Start In Read Only Mode</span></label>\n', '')
    text = text.replace(" · ${p.dashboard.read_only?'Read Only':'Management Enabled'}", '')

    text = text.replace('<button class="nav" data-view="settings">Settings</button>', '<button class="nav admin-only" data-view="settings">Settings</button>')
    text = replace_once(text, '<div class="sidebar-foot"><small id="version">—</small></div>', '<div class="sidebar-foot"><div class="sidebar-user"><strong id="currentUserName">—</strong><small id="currentUserGroup">—</small></div><small id="version">—</small></div>', 'sidebar account footer')
    text = replace_once(text, '<div class="top-actions">\n<select id="serverSelect"></select>', '<div class="top-actions">\n<span class="mobile-account" id="mobileAccount">—</span>\n<select id="serverSelect"></select>', 'mobile account badge')
    text = text.replace('<button class="primary" id="addBtn">＋ Add</button>', '<button class="primary admin-only" id="addBtn">＋ Add</button>')
    text = text.replace('<button class="icon-btn" id="moreBtn">•••</button>', '<button class="icon-btn admin-only" id="moreBtn">•••</button>')

    settings_markup = '''<section class="view" id="view-settings">
<div class="settings-layout">
<nav class="settings-nav" aria-label="Settings Categories">
<button class="active" data-settings-page="general" type="button">General</button>
<button data-settings-page="access" type="button">Dashboard Access</button>
<button data-settings-page="clients" type="button">Download Clients</button>
<button data-settings-page="updates" type="button">Application Updates</button>
<button data-settings-page="notifications" type="button">Notifications</button>
<button data-settings-page="integrations" type="button">Integrations</button>
<button data-settings-page="users" type="button">User Management</button>
</nav>
<div class="settings-content">
<div class="settings-page-head"><div><h2 id="settingsPageTitle">General</h2><p>Settings are separated by category so additional modules can be added without crowding a single page.</p></div></div>
<form id="settingsForm">
<section class="settings-page active" data-settings-section="general">
<div class="panel settings-card">
<div class="panel-title">General Dashboard Settings</div>
<label>Dashboard Title<input id="sTitle"/></label>
<label>Refresh Interval Seconds<input id="sRefresh" max="60" min="1" type="number"/></label>
<label>Theme<select id="sTheme"><option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option></select></label>
<label>Density<select id="sDensity"><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label>
<label>Accent Color<input id="sAccent" type="color" value="#72a9ff"/></label>
<fieldset class="column-prefs"><legend>Visible Desktop Columns</legend><label><input checked="" data-column="progress" type="checkbox"/> Progress</label><label><input checked="" data-column="state" type="checkbox"/> Status</label><label><input checked="" data-column="down" type="checkbox"/> Download</label><label><input checked="" data-column="up" type="checkbox"/> Upload</label><label><input checked="" data-column="eta" type="checkbox"/> ETA</label><label><input checked="" data-column="ratio" type="checkbox"/> Ratio</label></fieldset>
</div>
</section>
<section class="settings-page" data-settings-section="access">
<div class="panel settings-card">
<div class="panel-title">Dashboard Access</div>
<label>Authentication Mode<select id="sAuth"><option value="required">Required Everywhere</option><option value="lan_bypass">Bypass For Trusted Addresses</option><option value="disabled">Disabled</option></select></label>
<div class="field-help">Usernames, passwords, profile information, and access roles are managed under User Management.</div>
<div class="field-row"><div><b>Trusted Network Interfaces</b><small>Select one or more NICs whose current subnet should bypass dashboard authentication.</small></div><button class="secondary small-btn" id="sRefreshInterfaces" type="button">Refresh Interfaces</button></div>
<div class="interface-list" id="sInterfaceList"></div>
<label>IP Address Whitelist<textarea id="sTrustedIps" placeholder="10.0.0.25\n10.20.0.0/24" rows="3"></textarea></label>
<div class="lan-access-block">
<div><b>Local Dashboard Address</b><small>Use the local IP address and port from another device on an allowed network.</small></div>
<div class="two network-address-fields"><label>Local IP Address<input id="sLocalIp" readonly value="—"/></label><label>Port<input id="sPort" max="65535" min="1" type="number"/></label></div>
<div class="lan-url-row"><code id="localDashboardUrl">—</code><button class="secondary" id="copyLocalAddress" type="button">Copy Address</button></div>
</div>
</div>
</section>
<section class="settings-page" data-settings-section="clients">
<div class="panel settings-card"><div class="panel-title">qBitTorrent Servers</div><div id="serverSettings"></div><button id="addServerSetting" type="button">＋ Add Server</button></div>
</section>
<section class="settings-page" data-settings-section="updates">
<div class="panel settings-card" id="updateSettingsCard">
<div class="panel-title">Application Updates</div>
<div class="update-config">
<label class="toggle"><input id="sUpdatesEnabled" type="checkbox"/><span>Enable GitHub Updates</span></label>
<label class="full-field">GitHub Repository<input autocomplete="off" id="sUpdateRepo" placeholder="owner/repository or https://github.com/owner/repository"/></label><label class="full-field">GitHub Update Token <small>(Required For Private Repositories)</small><input autocomplete="off" id="sUpdateToken" placeholder="Leave Blank To Keep Current Token" type="password"/></label>
<label class="toggle"><input id="sUpdateAutoCheck" type="checkbox"/><span>Check Automatically</span></label>
<label>Check Interval Hours<input id="sUpdateHours" max="168" min="1" type="number" value="6"/></label>
</div>
<div class="update-status" id="updateStatus"><div><span>Current Version</span><strong id="updateCurrent">—</strong></div><div><span>Latest Version</span><strong id="updateLatest">Not Checked</strong></div><div><span>Update State</span><strong id="updateState">Idle</strong></div></div>
<div class="update-actions"><button class="secondary" id="testUpdateAccess" type="button">Test GitHub Connection</button><button class="secondary" id="checkUpdate" type="button">Check For Updates</button><button class="secondary" disabled="" id="downloadUpdate" type="button">Download Update</button><button class="primary" disabled="" id="installUpdate" type="button">Install And Restart</button></div>
<div class="test-result muted update-access-result" id="updateAccessResult">Not Tested Yet</div>
<div class="muted update-message" id="updateMessage">Configure the GitHub repository and, for a private repository, a token with <code>Contents: Read</code>. Releases are checked directly through GitHub and verified against the ZIP digest before installation.</div>
</div>
</section>
<section class="settings-page" data-settings-section="notifications">
<div class="panel settings-card"><div class="panel-title">Notifications</div>
<label class="toggle"><input id="nBrowser" type="checkbox"/><span>Browser Notifications</span></label>
<label class="toggle"><input id="nSound" type="checkbox"/><span>Completion Sound</span></label>
<label>Generic Webhook<input id="nWebhook" placeholder="https://…"/></label>
<label>Discord Webhook<input id="nDiscord" placeholder="https://discord.com/api/webhooks/…"/></label>
<label>ntfy Topic URL<input id="nNtfy" placeholder="https://ntfy.sh/topic"/></label>
<button id="testNotify" type="button">Send Test Notification</button>
</div>
</section>
<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save Settings</button></div>
</form>
<section class="settings-page" data-settings-section="integrations">
<div class="panel settings-card"><div class="panel-title">Integrations</div><p class="muted">No integrations are populated by default. Add only the services you use, test each connection, and save it independently.</p><div class="integration-add-row"><select id="integrationTypeSelect"><option value="">Choose Integration…</option></select><button class="primary" id="addIntegrationSetting" type="button">＋ Add Integration</button></div><div id="integrationList"></div></div>
</section>
<section class="settings-page" data-settings-section="users">
<div class="panel settings-card"><div class="panel-title">User Management</div><p class="muted">Administrators can manage torrents and settings. Standard Users have read-only dashboard access.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add User</button></div><div id="userList"></div></div>
</section>
</div>
</div>
</section>
</main>'''
    text = sub_once(text, r'<section class="view" id="view-settings">.*?\n</section>\n</main>', settings_markup, 'settings view', re.S)
    text = text.replace('<nav class="mobile-nav"><button class="active" data-view="dashboard">Dashboard</button><button data-view="history">Transfer History</button><button data-view="settings">Settings</button></nav>', '<nav class="mobile-nav"><button class="active" data-view="dashboard">Dashboard</button><button data-view="history">Transfer History</button><button class="admin-only" data-view="settings">Settings</button></nav>')
    text = text.replace('<script src="/static/app.js?v=0.4.0-pre1"></script>', '<script src="/static/settings.js?v=0.5.0"></script>\n<script src="/static/app.js?v=0.5.0"></script>')
    path.write_text(text, encoding="utf-8")


def patch_app_js() -> None:
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    new_setup_payload = '''function setupPayload(){return{setup_code:$('#wSetupCode').value.trim(),dashboard:{title:$('#wTitle').value.trim()||'Torrent Dashboard',port:Number($('#wPort').value||state.setup?.port||8765),refresh_seconds:Number($('#wRefresh').value||2)},updates:{enabled:$('#wUpdatesEnabled').checked,repository:$('#wUpdateRepo').value.trim(),github_token:$('#wUpdateToken').value.trim(),auto_check:$('#wUpdateAutoCheck').checked,check_hours:6},auth:{mode:$('#wAuthMode').value,username:$('#wDashUser').value.trim()||'admin',password:$('#wDashPass').value,trusted_interfaces:selectedInterfaceIds('#wInterfaceList'),trusted_ips:parseWhitelist('#wTrustedIps')},servers:[setupServer()]}}

function interfaceCard'''
    text = sub_once(text, r'function setupPayload\(\)\{.*?\}\n\nfunction interfaceCard', new_setup_payload, 'setup payload', re.S)

    new_review = '''function renderSetupReview(){
  const p=setupPayload(),mode={required:'Required Everywhere',lan_bypass:'Trusted Address Bypass',disabled:'Disabled'}[p.auth.mode]||uiText(p.auth.mode),client=p.servers[0],clientAuth=client.auth_method==='api_key'?'API Key':'Username And Password',interfaceNames=p.auth.trusted_interfaces.length?p.auth.trusted_interfaces.join(', '):'None',whitelist=p.auth.trusted_ips.length?`${p.auth.trusted_ips.length} Whitelist ${p.auth.trusted_ips.length===1?'Entry':'Entries'}`:'No Whitelist Entries';
  $('#wReview').innerHTML=`<div><span>Dashboard</span><b>${esc(p.dashboard.title)}</b><small>${esc($('#wLocalIp').value)}:${p.dashboard.port} · ${p.dashboard.refresh_seconds}s Refresh</small></div><div><span>Dashboard Access</span><b>${esc(mode)}</b><small>${esc(interfaceNames)} · ${esc(whitelist)}</small></div><div><span>Administrator</span><b>${esc(p.auth.username)}</b><small>The first setup account is an Administrator.</small></div><div><span>Download Client</span><b>${esc(client.name)}</b><small>${esc(client.base_url)}</small></div><div><span>qBitTorrent Authentication</span><b>${esc(clientAuth)}</b><small>${client.auth_method==='api_key'?'Bearer API Key · No Login Cookie':esc(client.username)}</small></div><div><span>Application Updates</span><b>${p.updates.enabled?'GitHub Updates Enabled':'Manual Updates'}</b><small>${p.updates.enabled?esc(p.updates.repository):'Can Be Enabled Later Under Settings.'}</small></div>`;
  applyTitleCaseUi($('#wReview'));
}
function updateWizardClientAuth'''
    text = sub_once(text, r'function renderSetupReview\(\)\{.*?\n\}\nfunction updateWizardClientAuth', new_review, 'setup review', re.S)

    new_bootstrap = '''async function bootstrap(){
  bindPublicUI();
  try{
    state.setup=await rawJson('/api/setup/status');
    if(state.setup.required){showSetup();$('#wLocalIp').value=state.setup?.lan_ip||'127.0.0.1';$('#wPort').value=state.setup?.port||8765;$('#wUpdateRepo').value=state.setup?.updates?.repository||$('#wUpdateRepo').value||'CynicaGaming/TorrentDashboard';$('#wUpdatesEnabled').checked=state.setup?.updates?.enabled!==false;$('#wTrustedIps').value=(state.setup.trusted_ips||[]).join('\n');renderInterfaceList('#wInterfaceList',state.setup.network_interfaces||[],state.setup.trusted_interfaces||[],!(state.setup.trusted_interfaces||[]).length);state.setupInterfaceSelectionInitialized=true;$('#setupCodeWrap').classList.toggle('hidden',!state.setup.code_required);updateWizardClientAuth();updateWizardLanVisibility();updateSetupStep();return}
    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();
    document.body.classList.toggle('standard-user',!state.me.can_manage);
    $('#brandTitle').textContent=state.me.title;document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;
    const display=state.me.display_name||state.me.username||'User',group=state.me.group_label||uiText(state.me.group||'standardUser');
    if($('#currentUserName'))$('#currentUserName').textContent=display;if($('#currentUserGroup'))$('#currentUserGroup').textContent=group;if($('#mobileAccount'))$('#mobileAccount').textContent=group;
    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{refresh_seconds:state.me.refresh_seconds||2,low_disk_gb:20},notifications:{browser:false,sound:false}};state.refreshMs=Math.max(1000,Number(state.me.refresh_seconds||2)*1000)}
    await loadServers();bindUI();applyPrefs();await refreshStatus();scheduleRefresh();registerPwa();if(state.me.can_manage)setTimeout(maybeAutoCheckUpdates,1200);
  }
  catch(e){if(!$('#login').classList.contains('hidden'))return;toast(e.message,'error')}
}

let bound=false;'''
    text = sub_once(text, r'async function bootstrap\(\)\{.*?\n\}\n\nlet bound=false;', new_bootstrap, 'bootstrap', re.S)

    new_set_view = '''function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));$('#pageTitle').textContent=uiText(view==='history'?'transferHistory':view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='history'?'transferAndCompletionHistory':'dashboardConfiguration');if(view==='history')loadHistory();if(view==='settings'){loadSettings().then(()=>TDSettings.loadExtras())}}

async function loadServers'''
    text = sub_once(text, r'function setView\(view\)\{.*?\}\n\nasync function loadServers', new_set_view, 'settings view navigation', re.S)

    text = sub_once(text, r'function fillSettings\(\)\{.*?\}\nfunction renderUpdateInfo', 'function fillSettings(){if(!state.settings)return;TDSettings.fill(state.settings)}\nfunction renderUpdateInfo', 'settings fill delegate', re.S)
    text = sub_once(text, r'async function saveSettings\(e\)\{.*?\}\n\nasync function loadIntegrations\(\)\{.*?\}\n\nfunction loadSavedViews', 'async function saveSettings(e){return TDSettings.saveCore(e)}\n\nasync function loadIntegrations(){return TDSettings.loadIntegrations()}\n\nfunction loadSavedViews', 'settings save/integration delegates', re.S)

    bind_pattern = r"  \$\('#historyRange'\)\.addEventListener\('change',loadHistory\);[^\n]*\n"
    bind_replacement = "  $('#historyRange').addEventListener('change',loadHistory);\n  if(state.me?.can_manage)TDSettings.bind();\n"
    text = sub_once(text, bind_pattern, bind_replacement, 'settings UI bindings')
    text = text.replace("navigator.serviceWorker.register('/sw.js?v=3.4.0-cleanup3')", "navigator.serviceWorker.register('/sw.js?v=0.5.0')")
    path.write_text(text, encoding="utf-8")


def patch_config_example() -> None:
    path = ROOT / "config.example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("dashboard", {}).pop("read_only", None)
    data.setdefault("auth", {}).pop("username", None)
    data.setdefault("auth", {}).pop("password_hash", None)
    data["users"] = []
    data["integrations"] = []
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_service_worker() -> None:
    path = ROOT / "static" / "sw.js"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"const CACHE='[^']+';", "const CACHE='torrent-dashboard-v050';", text, count=1)
    text = re.sub(r"const ASSETS=\[[^\n]+;", "const ASSETS=['/','/static/app.css?v=0.5.0','/static/settings.css?v=0.5.0','/static/settings.js?v=0.5.0','/static/app.js?v=0.5.0','/manifest.webmanifest'];", text, count=1)
    path.write_text(text, encoding="utf-8")


def patch_settings_css() -> None:
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    if '.standard-user .row-actions' not in text:
        text += '\n.standard-user .row-actions,.standard-user #bulkbar{display:none!important}\n'
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_dashboard()
    patch_index()
    patch_app_js()
    patch_config_example()
    patch_service_worker()
    patch_settings_css()
    print("Applied Torrent Dashboard 0.5.0 modular settings/user management update")


if __name__ == "__main__":
    main()
