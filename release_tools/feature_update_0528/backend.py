#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return out

dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.27"', 'VERSION = "0.5.28"', 'dashboard version')

dashboard = replace_once(
    dashboard,
    '        self.send_header("Content-Security-Policy", "default-src \'self\'; style-src \'self\' \'unsafe-inline\' https://fonts.googleapis.com; font-src \'self\' https://fonts.gstatic.com; script-src \'self\'; connect-src \'self\'; img-src \'self\' data:; manifest-src \'self\'; worker-src \'self\'; object-src \'none\'; frame-ancestors \'none\'")',
    '        self.send_header("Content-Security-Policy", "default-src \'self\'; style-src \'self\' \'unsafe-inline\'; font-src \'self\'; script-src \'self\'; connect-src \'self\'; img-src \'self\' data:; manifest-src \'self\'; worker-src \'self\'; object-src \'none\'; frame-ancestors \'none\'")',
    'remove external font CSP allowances',
)

old_profile = '''def save_current_user_profile(cfg, user_id, data):
    out = json.loads(json.dumps(cfg))
    users = out.setdefault("users", [])
    existing = user_by_id(out, user_id)
    if not existing:
        raise RuntimeError("This session is not linked to a user account")
    requested_username = str(data.get("username") if data.get("username") is not None else existing.get("username") or "").strip()
    if requested_username != str(existing.get("username") or ""):
        encoded = str(existing.get("password_hash") or "")
        if encoded and not verify_password(str(data.get("current_password") or ""), encoded):
            raise RuntimeError("Current password is required to change your username")
    item = normalize_user({
        "id": existing.get("id"),
        "username": requested_username,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "email": data.get("email"),
        "group": existing.get("group"),
    }, existing)
    duplicate = next((u for u in users if str(u.get("id") or "") != item["id"] and str(u.get("username") or "").casefold() == item["username"].casefold()), None)
    if duplicate:
        raise RuntimeError("That username is already in use")
    users[users.index(existing)] = item
    sync_legacy_auth(out)
    return out, item
'''
new_profile = '''def save_current_user_profile(cfg, user_id, data):
    out = json.loads(json.dumps(cfg))
    users = out.setdefault("users", [])
    existing = user_by_id(out, user_id)
    if not existing:
        raise RuntimeError("This session is not linked to a user account")
    requested_username = str(data.get("username") if data.get("username") is not None else existing.get("username") or "").strip()
    requested_email = str(data.get("email") if data.get("email") is not None else existing.get("email") or "").strip()
    secure_change = (
        requested_username != str(existing.get("username") or "")
        or requested_email != str(existing.get("email") or "")
    )
    encoded = str(existing.get("password_hash") or "")
    if secure_change and encoded and not verify_password(str(data.get("current_password") or ""), encoded):
        raise RuntimeError("Current password is required to change your username or email")
    item = normalize_user({
        "id": existing.get("id"),
        "username": requested_username,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "email": requested_email,
        "group": existing.get("group"),
    }, existing)
    duplicate = next((u for u in users if str(u.get("id") or "") != item["id"] and str(u.get("username") or "").casefold() == item["username"].casefold()), None)
    if duplicate:
        raise RuntimeError("That username is already in use")
    users[users.index(existing)] = item
    sync_legacy_auth(out)
    return out, item
'''
dashboard = replace_once(dashboard, old_profile, new_profile, 'secure profile changes')

dashboard = replace_once(
    dashboard,
    '        "avatar_version": str(user.get("avatar_version") or ""),\n',
    '        "avatar_version": str(user.get("avatar_version") or ""),\n        "password_configured": bool(user.get("password_hash")),\n',
    'public user password configured flag',
)

qbit_helpers = '''\n\nQBIT_PROXY_TYPES = {"none", "http", "socks5", "socks4"}\n\n\ndef normalize_qbittorrent_proxy_type(value):\n    if isinstance(value, str):\n        normalized = value.strip().lower().replace("_", "")\n        return {"none": "none", "http": "http", "socks5": "socks5", "socks4": "socks4"}.get(normalized, "none")\n    try:\n        numeric = int(value)\n    except (TypeError, ValueError):\n        return "none"\n    return {-1: "none", 0: "none", 1: "http", 2: "socks5", 3: "http", 4: "socks5", 5: "socks4"}.get(numeric, "none")\n\n\ndef encode_qbittorrent_proxy_type(proxy_type, auth_enabled, current_value):\n    proxy_type = str(proxy_type or "none").strip().lower()\n    if proxy_type not in QBIT_PROXY_TYPES:\n        raise RuntimeError("Unsupported proxy type")\n    if isinstance(current_value, str):\n        return {"none": "None", "http": "HTTP", "socks5": "SOCKS5", "socks4": "SOCKS4"}[proxy_type]\n    if proxy_type == "none":\n        return 0 if current_value == 0 else -1\n    if proxy_type == "http":\n        return 3 if auth_enabled else 1\n    if proxy_type == "socks5":\n        return 4 if auth_enabled else 2\n    return 5\n\n\ndef _qbit_rate_to_kb(value):\n    try:\n        return max(0, round(int(value or 0) / 1024))\n    except (TypeError, ValueError):\n        return 0\n\n\ndef _qbit_int(value, label, minimum, maximum):\n    try:\n        number = int(value)\n    except (TypeError, ValueError) as exc:\n        raise RuntimeError(f"{label} must be a whole number") from exc\n    if number < minimum or number > maximum:\n        raise RuntimeError(f"{label} must be between {minimum} and {maximum}")\n    return number\n\n\ndef _qbit_rate_from_kb(value, label):\n    kb = _qbit_int(value, label, 0, 2_000_000_000)\n    return kb * 1024\n'''
dashboard = replace_once(dashboard, '\n\nclass QBitClient:\n', qbit_helpers + '\n\nclass QBitClient:\n', 'qBitTorrent client settings helpers')

old_metadata = '''    def metadata(self):
        out = {}
        for key, path in {
            "categories": "/api/v2/torrents/categories",
            "tags": "/api/v2/torrents/tags",
            "preferences": "/api/v2/app/preferences",
            "alt_speed": "/api/v2/transfer/speedLimitsMode",
            "global_dl_limit": "/api/v2/transfer/downloadLimit",
            "global_up_limit": "/api/v2/transfer/uploadLimit",
        }.items():
            try:
                out[key] = self.get_json(path)
            except Exception as e:
                out[key] = None
        return out
'''
new_metadata = '''    def preferences(self):
        return self.get_json("/api/v2/app/preferences") or {}

    def metadata(self):
        # Browser-facing metadata intentionally excludes app/preferences. qBitTorrent
        # preferences can contain proxy, mail, Web UI, and certificate secrets.
        out = {}
        for key, path in {
            "categories": "/api/v2/torrents/categories",
            "tags": "/api/v2/torrents/tags",
            "alt_speed": "/api/v2/transfer/speedLimitsMode",
            "global_dl_limit": "/api/v2/transfer/downloadLimit",
            "global_up_limit": "/api/v2/transfer/uploadLimit",
        }.items():
            try:
                out[key] = self.get_json(path)
            except Exception:
                out[key] = None
        return out

    def client_settings(self):
        prefs = self.preferences()
        try:
            alt_speed = int(self.get_json("/api/v2/transfer/speedLimitsMode") or 0) == 1
        except Exception:
            alt_speed = False
        raw_proxy_type = prefs.get("proxy_type")
        proxy_type = normalize_qbittorrent_proxy_type(raw_proxy_type)
        legacy_auth = raw_proxy_type in (3, 4)
        return {
            "speed": {
                "alternative_enabled": alt_speed,
                "download_limit_kb": _qbit_rate_to_kb(prefs.get("dl_limit", 0)),
                "upload_limit_kb": _qbit_rate_to_kb(prefs.get("up_limit", 0)),
                "alternative_download_limit_kb": _qbit_rate_to_kb(prefs.get("alt_dl_limit", 0)),
                "alternative_upload_limit_kb": _qbit_rate_to_kb(prefs.get("alt_up_limit", 0)),
            },
            "connection": {
                "listen_port": int(prefs.get("listen_port", 0) or 0),
                "random_port": bool(prefs.get("random_port", False) or int(prefs.get("listen_port", 0) or 0) == 0),
                "upnp": bool(prefs.get("upnp", False)),
                "max_connections": int(prefs.get("max_connec", -1) or 0),
                "max_connections_per_torrent": int(prefs.get("max_connec_per_torrent", -1) or 0),
                "max_upload_slots": int(prefs.get("max_uploads", -1) or 0),
                "max_upload_slots_per_torrent": int(prefs.get("max_uploads_per_torrent", -1) or 0),
            },
            "proxy": {
                "type": proxy_type,
                "host": str(prefs.get("proxy_ip") or ""),
                "port": int(prefs.get("proxy_port", 0) or 0),
                "authentication": bool(prefs.get("proxy_auth_enabled", legacy_auth)),
                "username": str(prefs.get("proxy_username") or ""),
                "password_configured": bool(prefs.get("proxy_password")),
                "hostname_lookup": bool(prefs.get("proxy_hostname_lookup", False)),
                "hostname_lookup_supported": "proxy_hostname_lookup" in prefs,
                "bittorrent": bool(prefs.get("proxy_bittorrent", True)),
                "bittorrent_supported": "proxy_bittorrent" in prefs,
                "peer_connections": bool(prefs.get("proxy_peer_connections", False)),
                "peer_connections_supported": "proxy_peer_connections" in prefs,
            },
        }

    def update_client_settings(self, data):
        if not isinstance(data, dict):
            raise RuntimeError("Client settings payload must be an object")
        speed = data.get("speed") or {}
        connection = data.get("connection") or {}
        proxy = data.get("proxy") or {}
        if not all(isinstance(x, dict) for x in (speed, connection, proxy)):
            raise RuntimeError("Client settings sections must be objects")

        current = self.preferences()
        update = {
            "dl_limit": _qbit_rate_from_kb(speed.get("download_limit_kb", 0), "Download limit"),
            "up_limit": _qbit_rate_from_kb(speed.get("upload_limit_kb", 0), "Upload limit"),
            "alt_dl_limit": _qbit_rate_from_kb(speed.get("alternative_download_limit_kb", 0), "Alternative download limit"),
            "alt_up_limit": _qbit_rate_from_kb(speed.get("alternative_upload_limit_kb", 0), "Alternative upload limit"),
            "upnp": bool(connection.get("upnp", False)),
            "max_connec": _qbit_int(connection.get("max_connections", -1), "Global connection limit", -1, 1_000_000),
            "max_connec_per_torrent": _qbit_int(connection.get("max_connections_per_torrent", -1), "Per-torrent connection limit", -1, 1_000_000),
            "max_uploads": _qbit_int(connection.get("max_upload_slots", -1), "Global upload slot limit", -1, 1_000_000),
            "max_uploads_per_torrent": _qbit_int(connection.get("max_upload_slots_per_torrent", -1), "Per-torrent upload slot limit", -1, 1_000_000),
        }

        random_port = bool(connection.get("random_port", False))
        update["random_port"] = random_port
        if not random_port:
            update["listen_port"] = _qbit_int(connection.get("listen_port", 0), "Listening port", 1, 65535)

        proxy_type = str(proxy.get("type") or "none").strip().lower()
        proxy_auth = bool(proxy.get("authentication", False)) and proxy_type not in ("none", "socks4")
        update["proxy_type"] = encode_qbittorrent_proxy_type(proxy_type, proxy_auth, current.get("proxy_type"))
        if "proxy_auth_enabled" in current:
            update["proxy_auth_enabled"] = proxy_auth
        if proxy_type != "none":
            host = str(proxy.get("host") or "").strip()
            if not host:
                raise RuntimeError("Proxy host is required when a proxy is enabled")
            update["proxy_ip"] = host[:1024]
            update["proxy_port"] = _qbit_int(proxy.get("port", 0), "Proxy port", 1, 65535)
            update["proxy_username"] = str(proxy.get("username") or "")[:512] if proxy_auth else ""
            password = proxy.get("password")
            if proxy_auth and password not in (None, "", "<configured>") and "•" not in str(password):
                update["proxy_password"] = str(password)[:4096]
        if "proxy_hostname_lookup" in current:
            update["proxy_hostname_lookup"] = bool(proxy.get("hostname_lookup", False))
        if "proxy_bittorrent" in current:
            update["proxy_bittorrent"] = bool(proxy.get("bittorrent", True))
        if "proxy_peer_connections" in current:
            update["proxy_peer_connections"] = bool(proxy.get("peer_connections", False))

        self.post("/api/v2/app/setPreferences", {"json": json.dumps(update, separators=(",", ":"))})
        try:
            current_alt = int(self.get_json("/api/v2/transfer/speedLimitsMode") or 0) == 1
        except Exception:
            current_alt = False
        requested_alt = bool(speed.get("alternative_enabled", False))
        if requested_alt != current_alt:
            self.post("/api/v2/transfer/toggleSpeedLimitsMode", {})
        return self.client_settings()
'''
dashboard = replace_once(dashboard, old_metadata, new_metadata, 'safe metadata and client settings API')

dashboard = replace_once(
    dashboard,
    '                meta = client.metadata()\n                disk_free = disk_free_for(meta.get("preferences") or {})\n',
    '                preferences = client.preferences()\n                meta = client.metadata()\n                disk_free = disk_free_for(preferences)\n',
    'collector preference isolation',
)

dashboard = replace_once(
    dashboard,
    '        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces") and not session_is_admin(sess):\n',
    '        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces","/api/client-settings") and not session_is_admin(sess):\n',
    'client settings admin read barrier',
)

dashboard = replace_once(
    dashboard,
    '''        if path=="/api/meta":
            sid=qs.get("server",["local"])[0]
            try: return self.send_json(200,get_client(cfg,sid).metadata(),new_cookie)
            except Exception as e: return self.send_json(502,{"error":str(e)},new_cookie)

''',
    '''        if path=="/api/meta":
            sid=qs.get("server",["local"])[0]
            try: return self.send_json(200,get_client(cfg,sid).metadata(),new_cookie)
            except Exception as e: return self.send_json(502,{"error":str(e)},new_cookie)
        if path=="/api/client-settings":
            sid=qs.get("server",["local"])[0]
            try: return self.send_json(200,{"settings":get_client(cfg,sid).client_settings()},new_cookie)
            except Exception as e: return self.send_json(502,{"error":str(e)},new_cookie)

''',
    'client settings GET route',
)

dashboard = replace_once(
    dashboard,
    '''            if path=="/api/action":
                data=parse_json_body(self); sid=data.pop("server","local"); action=data.pop("action"); result=get_client(cfg,sid).action(action,data)
                HISTORY.event(sid, "action:"+action, sess.get("username",""), data.get("hash") or "", {"client_ip": self.client_ip()})
                return self.send_json(200,{"ok":True,"status":result[0] if isinstance(result,tuple) else 200},new_cookie)
''',
    '''            if path=="/api/client-settings":
                data=parse_json_body(self,50000); sid=str(data.pop("server","local")); settings=get_client(cfg,sid).update_client_settings(data)
                HISTORY.event(sid,"client_settings_changed",sess.get("username",""),"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True,"settings":settings},new_cookie)
            if path=="/api/action":
                data=parse_json_body(self); sid=data.pop("server","local"); action=data.pop("action"); result=get_client(cfg,sid).action(action,data)
                HISTORY.event(sid, "action:"+action, sess.get("username",""), data.get("hash") or "", {"client_ip": self.client_ip()})
                return self.send_json(200,{"ok":True,"status":result[0] if isinstance(result,tuple) else 200},new_cookie)
''',
    'client settings POST route',
)
write('dashboard.py', dashboard)
