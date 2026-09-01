#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import base64
import hashlib
import hmac
import http.cookiejar
import ipaddress
import json
import mimetypes
import os
import secrets
import shutil
import socket
import subprocess
import re
import ssl
import sqlite3
import sys
import threading
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import webbrowser
from collections import defaultdict, deque
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = APP_DIR / "data"
CONFIG_PATH = APP_DIR / "config.json"
DB_PATH = DATA_DIR / "torrent_desk.sqlite3"
UPDATE_DIR = DATA_DIR / "updates"
UPDATE_STATE_PATH = DATA_DIR / "update-status.json"
CUSTOM_SOUND_BASENAME = "custom-notification-sound"
MAX_CUSTOM_SOUND_BYTES = 2 * 1024 * 1024
VERSION = "0.5.19"
STATUS_REFRESH_SECONDS = 1.0
DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"


class SingleInstanceLock:
    """Machine-level guard that prevents two dashboard processes from running."""

    def __init__(self):
        self._handle = None
        self._file = None

    def acquire(self):
        if os.name == "nt":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateMutexW(None, False, "Local\\TorrentDashboard.SingleInstance")
            if not handle:
                raise OSError("Could not create the Torrent Dashboard instance mutex")
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                kernel32.CloseHandle(handle)
                return False
            self._handle = handle
            return True

        import fcntl
        lock_path = Path(tempfile.gettempdir()) / "torrent-dashboard.lock"
        lock_file = open(lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            return False
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        self._file = lock_file
        return True

    def release(self):
        if self._handle is not None:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
        if self._file is not None:
            try:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None


DEFAULT_CONFIG = {
    "setup": {"complete": False},
    "dashboard": {
        "title": "Torrent Dashboard",
        "bind_host": "0.0.0.0",
        "port": 8765,
        "open_browser": True,
        "history_retention_days": 30,
        "history_sample_seconds": 10,
        "low_disk_gb": 20,
        "https_enabled": False,
        "https_cert": "",
        "https_key": ""
    },
    "updates": {"repository": DEFAULT_UPDATE_REPOSITORY},
    "auth": {
        "mode": "lan_bypass",
        "trusted_interfaces": [],
        "trusted_ips": [],
        "session_hours": 24,
        "max_login_attempts_per_10m": 20
    },
    "users": [],
    "servers": [],
    "notifications": {
        "browser": True,
        "sound": False,
        "sound_mode": "default",
        "custom_sound_file": "",
        "custom_sound_name": "",
        "custom_sound_mime": ""
    },
    "integrations": []
}


def deep_merge(base, override):
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Existing Torrent Dashboard installs predate the setup wizard. Treat an
    # existing config as already configured so upgrades do not interrupt them.
    if "setup" not in raw:
        raw["setup"] = {"complete": True}

    # 3.2.1 replaces the single automatic LAN choice with explicit trusted
    # network-interface selection plus a general IP/CIDR whitelist. Existing
    # installations are migrated in memory without discarding custom entries.
    auth_raw = raw.setdefault("auth", {})
    legacy_cidrs = list(auth_raw.get("trusted_cidrs", []) or [])
    if "trusted_ips" not in auth_raw:
        auth_raw["trusted_ips"] = [c for c in legacy_cidrs if c not in ("127.0.0.0/8", "::1/128")]
    if "trusted_interfaces" not in auth_raw:
        auth_raw["trusted_interfaces"] = []
        if auth_raw.get("auto_trust_lan", False):
            try:
                default = detect_lan_network()
                if default.get("interface_id") or default.get("interface"):
                    auth_raw["trusted_interfaces"] = [default.get("interface_id") or default.get("interface")]
            except Exception:
                pass

    merged = deep_merge(DEFAULT_CONFIG, raw)
    # 0.5.16 makes status collection a fixed one-second application behavior.
    # Ignore and retire any refresh_seconds value left by an older install.
    merged.setdefault("dashboard", {}).pop("refresh_seconds", None)
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
    legacy_github_repo = ""
    if isinstance(raw_integrations, list):
        migrated = []
        for item in raw_integrations:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "").strip().lower() == "github":
                if not legacy_github_repo:
                    legacy_github_repo = str(item.get("repository") or "").strip()
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

    # Notification delivery endpoints moved into Integrations in 0.5.5.
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

    # Updates owns its public GitHub repository directly. Preserve the saved
    # repository from either the previous Updates object or the retired GitHub
    # integration, then remove GitHub from the integration collection.
    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}
    update_repo = str(legacy_updates.get("repository") or legacy_github_repo or DEFAULT_UPDATE_REPOSITORY).strip()
    try:
        update_repo = normalize_github_repository(update_repo)
    except Exception:
        update_repo = DEFAULT_UPDATE_REPOSITORY
    merged["updates"] = {"repository": update_repo}
    merged["integrations"] = [x for x in merged.get("integrations", []) if x.get("type") != "github"]

    sync_legacy_auth(merged)
    return merged


def save_config(cfg):
    cfg = json.loads(json.dumps(cfg))
    cfg["integrations"] = [x for x in cfg.get("integrations", []) if x.get("type") != "github"]
    updates = cfg.setdefault("updates", {})
    updates["repository"] = normalize_github_repository(updates.get("repository") or DEFAULT_UPDATE_REPOSITORY)
    updates.pop("github_token", None)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def hash_password(password: str, iterations: int = 260_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("=")
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        pad = lambda s: s + "=" * (-len(s) % 4)
        salt = base64.urlsafe_b64decode(pad(salt_b64))
        expected = base64.urlsafe_b64decode(pad(digest_b64))
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(expected, got)
    except Exception:
        return False


class SessionStore:
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


SESSIONS = SessionStore()
LOGIN_ATTEMPTS = defaultdict(deque)
LOGIN_LOCK = threading.Lock()


def normalize_trusted_entry(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        if "/" in value:
            return str(ipaddress.ip_network(value, strict=False))
        addr = ipaddress.ip_address(value)
        return f"{addr}/{32 if addr.version == 4 else 128}"
    except Exception as exc:
        raise RuntimeError(f"Invalid IP whitelist entry: {value}") from exc


def is_trusted_ip(ip, networks):
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in ipaddress.ip_network(c, strict=False) for c in networks)
    except Exception:
        return False


def _usable_range(network):
    if not network:
        return None, None
    try:
        if network.version == 4 and network.prefixlen <= 30:
            return str(network.network_address + 1), str(network.broadcast_address - 1)
        if network.version == 6 and network.prefixlen < 127:
            return str(network.network_address + 1), str(network.broadcast_address - 1)
        return str(network.network_address), str(network.broadcast_address)
    except Exception:
        return None, None


def _network_result(address, prefix, gateway="", interface="", source="", interface_id="", is_default=False):
    try:
        addr = ipaddress.ip_address(str(address).strip())
        if addr.version != 4 or addr.is_loopback or addr.is_link_local:
            return None
        network = ipaddress.ip_network(f"{addr}/{prefix}", strict=False)
        first, last = _usable_range(network)
        return {
            "detected": True,
            "interface": interface or interface_id or "",
            "interface_id": interface_id or interface or "",
            "address": str(addr),
            "gateway": str(gateway or ""),
            "cidr": str(network),
            "prefix": int(network.prefixlen),
            "netmask": str(network.netmask),
            "range_start": first,
            "range_end": last,
            "source": source,
            "default": bool(is_default or gateway),
        }
    except Exception:
        return None


def _clean_windows_adapter_name(heading):
    name = re.sub(r"^.*?adapter\s+", "", str(heading or ""), flags=re.I).strip()
    return name or str(heading or "").strip()


def _parse_windows_interfaces(text):
    pattern = re.compile(
        r"(?ms)^([^\r\n]*adapter\s+[^:\r\n]+):\s*\r?\n(.*?)(?=^[^\r\n]*adapter\s+[^:\r\n]+:\s*$|\Z)",
        re.I,
    )
    results = []
    for heading, block in pattern.findall(text or ""):
        ip_m = re.search(r"IPv4 Address[^:]*:\s*([0-9.]+)", block, re.I)
        mask_m = re.search(r"Subnet Mask[^:]*:\s*([0-9.]+)", block, re.I)
        if not ip_m or not mask_m:
            continue
        gateway = ""
        gw_pos = re.search(r"Default Gateway[^:]*:", block, re.I)
        if gw_pos:
            tail = "\n".join(block[gw_pos.end():].splitlines()[:3])
            ips = re.findall(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])", tail)
            gateway = ips[0] if ips else ""
        try:
            prefix = ipaddress.IPv4Network(f"0.0.0.0/{mask_m.group(1)}").prefixlen
        except Exception:
            continue
        name = _clean_windows_adapter_name(heading)
        result = _network_result(ip_m.group(1), prefix, gateway, name, "ipconfig", name, bool(gateway))
        if result:
            results.append(result)
    return results


def _detect_windows_interfaces():
    try:
        out = subprocess.check_output(["ipconfig"], text=True, errors="replace", timeout=4)
        return _parse_windows_interfaces(out)
    except Exception:
        return []


def _detect_linux_interfaces():
    results = []
    default_gateway = ""
    default_interface = ""
    try:
        route = subprocess.check_output(["ip", "-4", "route", "show", "default"], text=True, errors="replace", timeout=4)
        m = re.search(r"default(?:\s+via\s+(\S+))?.*?\sdev\s+(\S+)", route)
        if m:
            default_gateway, default_interface = m.group(1) or "", m.group(2)
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ip", "-o", "-4", "addr", "show", "scope", "global"], text=True, errors="replace", timeout=4)
        for line in out.splitlines():
            m = re.search(r"^\d+:\s+([^\s]+)\s+inet\s+([0-9.]+)/(\d+)", line)
            if not m:
                continue
            interface, address, prefix = m.group(1).split("@")[0], m.group(2), int(m.group(3))
            gateway = default_gateway if interface == default_interface else ""
            result = _network_result(address, prefix, gateway, interface, "ip addr", interface, interface == default_interface)
            if result:
                results.append(result)
    except Exception:
        pass
    return results


def _detect_macos_interfaces():
    results = []
    default_gateway = ""
    default_interface = ""
    try:
        route = subprocess.check_output(["route", "-n", "get", "default"], text=True, errors="replace", timeout=4)
        gm = re.search(r"gateway:\s*(\S+)", route)
        im = re.search(r"interface:\s*(\S+)", route)
        default_gateway = gm.group(1) if gm else ""
        default_interface = im.group(1) if im else ""
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ifconfig"], text=True, errors="replace", timeout=4)
        blocks = re.split(r"(?m)^(?=[A-Za-z0-9_.-]+:\s)", out)
        for block in blocks:
            head = re.match(r"^([A-Za-z0-9_.-]+):", block)
            if not head:
                continue
            interface = head.group(1)
            for m in re.finditer(r"\binet\s+([0-9.]+)\s+netmask\s+(0x[0-9a-fA-F]+|[0-9.]+)", block):
                address, mask = m.group(1), m.group(2)
                if address.startswith("127."):
                    continue
                if mask.lower().startswith("0x"):
                    n = int(mask, 16)
                    mask = ".".join(str((n >> shift) & 255) for shift in (24, 16, 8, 0))
                try:
                    prefix = ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
                except Exception:
                    continue
                gateway = default_gateway if interface == default_interface else ""
                result = _network_result(address, prefix, gateway, interface, "ifconfig", interface, interface == default_interface)
                if result:
                    results.append(result)
    except Exception:
        pass
    return results


LAN_DETECT_LOCK = threading.Lock()
LAN_DETECT_CACHE = {"ts": 0.0, "interfaces": []}


def detect_network_interfaces(force=False):
    now = time.time()
    with LAN_DETECT_LOCK:
        cached = LAN_DETECT_CACHE.get("interfaces") or []
        if not force and cached and now - LAN_DETECT_CACHE.get("ts", 0) < 30:
            return json.loads(json.dumps(cached))
    if os.name == "nt":
        results = _detect_windows_interfaces()
    elif sys.platform == "darwin":
        results = _detect_macos_interfaces()
    else:
        results = _detect_linux_interfaces()
    # Collapse duplicate interface/address pairs and prefer the default route first.
    unique = {}
    for item in results:
        unique[(item.get("interface_id"), item.get("address"))] = item
    results = sorted(unique.values(), key=lambda x: (not bool(x.get("default")), str(x.get("interface", "")).lower(), x.get("address", "")))
    with LAN_DETECT_LOCK:
        LAN_DETECT_CACHE["ts"] = now
        LAN_DETECT_CACHE["interfaces"] = json.loads(json.dumps(results))
    return json.loads(json.dumps(results))


def detect_lan_network(force=False):
    interfaces = detect_network_interfaces(force)
    if interfaces:
        return dict(next((x for x in interfaces if x.get("default")), interfaces[0]))
    # Fallback: identify the preferred local address. Do not invent a prefix.
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 53))
        address = sock.getsockname()[0]
        sock.close()
    except Exception:
        try:
            address = socket.gethostbyname(socket.gethostname())
        except Exception:
            address = "127.0.0.1"
    return {"detected": False, "address": address, "gateway": "", "cidr": "", "prefix": None,
            "netmask": "", "range_start": "", "range_end": "", "interface": "", "interface_id": "",
            "source": "fallback", "default": False}


def local_lan_ip():
    return detect_lan_network().get("address") or "127.0.0.1"


def interface_networks(interface_ids):
    wanted = {str(x) for x in (interface_ids or []) if str(x)}
    if not wanted:
        return []
    return [x for x in detect_network_interfaces() if x.get("interface_id") in wanted and x.get("cidr")]


def effective_trusted_cidrs(auth_cfg):
    networks = ["127.0.0.0/8", "::1/128"]
    for item in interface_networks(auth_cfg.get("trusted_interfaces", [])):
        networks.append(item["cidr"])
    manual = auth_cfg.get("trusted_ips")
    if manual is None:
        manual = auth_cfg.get("trusted_cidrs", []) or []
    for value in manual or []:
        normalized = normalize_trusted_entry(value)
        if normalized:
            networks.append(normalized)
    return list(dict.fromkeys(c for c in networks if c))


def is_loopback_ip(ip):
    try:
        return ipaddress.ip_address(ip).is_loopback
    except Exception:
        return False


SETUP_CODE = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


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
    "discord": {
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
        elif provider == "discord":
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


def normalize_qbittorrent_server(data, existing=None):
    existing = existing or {}
    sid = str(data.get("id") or existing.get("id") or uuid.uuid4().hex[:8])[:64]
    auth_method = str(data.get("auth_method") or existing.get("auth_method") or ("api_key" if existing.get("api_key") else "password"))
    if auth_method not in ("api_key", "password"):
        raise RuntimeError("qBitTorrent authentication must be API key or username/password")

    password = data.get("password")
    if password in (None, "", "<configured>"):
        password = existing.get("password", "")
    api_key = data.get("api_key")
    if api_key in (None, "", "<configured>"):
        api_key = existing.get("api_key", "")

    item = {
        "id": sid,
        "name": str(data.get("name") or existing.get("name") or "qBittorrent")[:128],
        "type": "qbittorrent",
        "base_url": str(data.get("base_url") or existing.get("base_url") or "").strip().rstrip("/")[:2048],
        "auth_method": auth_method,
        "api_key": str(api_key or ""),
        "username": str(data.get("username") if data.get("username") is not None else existing.get("username", ""))[:256],
        "password": str(password or ""),
        "enabled": bool(data.get("enabled", True)),
    }
    if not item["base_url"].startswith(("http://", "https://")):
        raise RuntimeError("qBitTorrent URL must start with http:// or https://")
    if auth_method == "api_key":
        if not item["api_key"]:
            raise RuntimeError("Enter the qBitTorrent API key")
        if not (item["api_key"].startswith("qbt_") and len(item["api_key"]) == 32):
            raise RuntimeError("qBitTorrent API keys must be 32 characters and start with qbt_ (qBitTorrent 5.2+)")
    else:
        if not item["username"]:
            raise RuntimeError("Enter the qBitTorrent username")
        if not item["password"]:
            raise RuntimeError("Enter the qBitTorrent password")
    return item


def test_server_connection(server):
    client = QBitClient(server)
    client.login()
    version = client.get_text("/api/v2/app/version")
    api_version = client.get_text("/api/v2/app/webapiVersion")
    return {
        "ok": True,
        "name": server.get("name", "qBittorrent"),
        "version": version,
        "api_version": api_version,
        "base_url": server.get("base_url"),
    }


class QBitClient:
    def __init__(self, server):
        self.server = server
        self.base = server["base_url"].rstrip("/")
        self.lock = threading.RLock()
        self.opener = None
        # Prevent bad password credentials from being retried every dashboard
        # refresh and tripping qBittorrent's Web UI IP-ban protection. API-key
        # authentication is stateless and never calls the login endpoint.
        self.auth_blocked_error = None

    def _make_opener(self):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [
            ("User-Agent", f"TorrentDashboard/{VERSION}"),
            ("Referer", self.base + "/"),
            ("Origin", self.base)
        ]
        if self.server.get("auth_method") == "api_key":
            opener.addheaders.append(("Authorization", "Bearer " + self.server.get("api_key", "")))
        return opener

    def login(self):
        if self.auth_blocked_error:
            raise RuntimeError(self.auth_blocked_error)

        if self.server.get("auth_method") == "api_key":
            if not self.server.get("api_key"):
                raise RuntimeError("qBittorrent API key is missing")
            self.opener = self._make_opener()
            self.auth_blocked_error = None
            return

        opener = self._make_opener()
        data = urllib.parse.urlencode({
            "username": self.server.get("username", ""),
            "password": self.server.get("password", "")
        }).encode()
        req = urllib.request.Request(self.base + "/api/v2/auth/login", data=data, method="POST")
        try:
            with opener.open(req, timeout=7) as r:
                body = r.read().decode(errors="replace").strip()
            if body.lower() != "ok.":
                # qBittorrent normally returns HTTP 200 + "Fails." for bad
                # credentials. Do not keep retrying, because enough failures
                # cause qBittorrent to ban this client's IP.
                self.opener = None
                self.auth_blocked_error = (
                    "qBittorrent rejected the username/password. Automatic login retries "
                    "are paused to avoid an IP ban. Verify the server credentials in "
                    "Setup/Settings, then save them before retrying."
                )
                raise RuntimeError(self.auth_blocked_error)
            self.opener = opener
            self.auth_blocked_error = None
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode(errors="replace").strip()
            except Exception:
                pass
            self.opener = None
            if e.code == 403:
                self.auth_blocked_error = (
                    "qBittorrent has banned this dashboard IP after too many failed Web UI "
                    "login attempts (HTTP 403). Torrent Dashboard has stopped retrying. Stop Torrent Dashboard, "
                    "wait for/clear the qBittorrent Web UI ban (or restart qBittorrent), verify the "
                    "username/password in Setup/Settings, then retry after the qBittorrent ban clears."
                )
                raise RuntimeError(self.auth_blocked_error) from e
            raise RuntimeError(f"qBittorrent login HTTP {e.code}: {detail or 'login failed'}") from e
        except urllib.error.URLError as e:
            self.opener = None
            raise RuntimeError(f"Cannot reach qBittorrent at {self.base}: {e.reason}") from e

    def _request(self, method, path, form=None, raw=None, headers=None, expect_json=False):
        with self.lock:
            if self.opener is None:
                self.login()
            url = self.base + path
            data = raw
            hdrs = dict(headers or {})
            if form is not None:
                data = urllib.parse.urlencode(form, doseq=True).encode()
                hdrs["Content-Type"] = "application/x-www-form-urlencoded"
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                with self.opener.open(req, timeout=12) as r:
                    body = r.read()
                    status = r.status
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code in (401, 403):
                    if self.server.get("auth_method") == "api_key":
                        raise RuntimeError(
                            f"qBittorrent rejected the API key (HTTP {e.code}). API-key authentication "
                            "requires qBittorrent 5.2.0+ / WebAPI 2.14.1+; verify or rotate the key in "
                            "qBittorrent Preferences → Web UI → API Key."
                        ) from e
                    self.opener = None
                    self.login()
                    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
                    with self.opener.open(req, timeout=12) as r:
                        body = r.read(); status = r.status
                else:
                    raise RuntimeError(f"qBittorrent HTTP {e.code}: {detail or path}") from e
            except urllib.error.URLError as e:
                raise RuntimeError(f"qBittorrent connection error: {e.reason}") from e
            if expect_json:
                if not body:
                    return None
                return json.loads(body.decode())
            return status, body

    def get_json(self, path, params=None):
        if params:
            path += "?" + urllib.parse.urlencode(params, doseq=True)
        return self._request("GET", path, expect_json=True)

    def get_text(self, path, params=None):
        if params:
            path += "?" + urllib.parse.urlencode(params, doseq=True)
        _, body = self._request("GET", path, expect_json=False)
        return body.decode(errors="replace").strip()

    def post(self, path, form=None):
        return self._request("POST", path, form=form or {})

    def info(self):
        torrents = self.get_json("/api/v2/torrents/info") or []
        transfer = self.get_json("/api/v2/transfer/info") or {}
        try:
            app_version = self.get_text("/api/v2/app/version")
        except Exception:
            app_version = None
        try:
            api_version = self.get_text("/api/v2/app/webapiVersion")
        except Exception:
            api_version = None
        return torrents, transfer, app_version, api_version

    def metadata(self):
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

    def detail(self, hash_):
        paths = {
            "properties": ("/api/v2/torrents/properties", {"hash": hash_}),
            "trackers": ("/api/v2/torrents/trackers", {"hash": hash_}),
            "files": ("/api/v2/torrents/files", {"hash": hash_}),
            "pieces": ("/api/v2/torrents/pieceStates", {"hash": hash_}),
            "peers": ("/api/v2/sync/torrentPeers", {"hash": hash_, "rid": 0}),
        }
        out = {}
        for key, (path, params) in paths.items():
            try:
                out[key] = self.get_json(path, params)
            except Exception as e:
                out[key] = {"error": str(e)} if key == "peers" else [] if key in ("trackers", "files", "pieces") else {}
        return out

    def action(self, action, payload):
        hashes = payload.get("hashes") or payload.get("hash") or ""
        if isinstance(hashes, list):
            hashes = "|".join(hashes)
        simple = {
            "stop": ("/api/v2/torrents/stop", {"hashes": hashes}),
            "start": ("/api/v2/torrents/start", {"hashes": hashes}),
            "recheck": ("/api/v2/torrents/recheck", {"hashes": hashes}),
            "reannounce": ("/api/v2/torrents/reannounce", {"hashes": hashes}),
            "increase_priority": ("/api/v2/torrents/increasePrio", {"hashes": hashes}),
            "decrease_priority": ("/api/v2/torrents/decreasePrio", {"hashes": hashes}),
            "top_priority": ("/api/v2/torrents/topPrio", {"hashes": hashes}),
            "bottom_priority": ("/api/v2/torrents/bottomPrio", {"hashes": hashes}),
            "toggle_sequential": ("/api/v2/torrents/toggleSequentialDownload", {"hashes": hashes}),
            "toggle_first_last": ("/api/v2/torrents/toggleFirstLastPiecePrio", {"hashes": hashes}),
        }
        if action in simple:
            path, form = simple[action]
            try:
                return self.post(path, form)
            except RuntimeError as e:
                # Compatibility fallback for pre-5.0 qBittorrent.
                if action in ("stop", "start") and "404" in str(e):
                    old = "pause" if action == "stop" else "resume"
                    return self.post(f"/api/v2/torrents/{old}", {"hashes": hashes})
                raise
        if action == "delete":
            return self.post("/api/v2/torrents/delete", {"hashes": hashes, "deleteFiles": str(bool(payload.get("delete_files"))).lower()})
        if action == "force_start":
            return self.post("/api/v2/torrents/setForceStart", {"hashes": hashes, "value": str(bool(payload.get("value"))).lower()})
        if action == "set_location":
            return self.post("/api/v2/torrents/setLocation", {"hashes": hashes, "location": str(payload.get("location", ""))[:2048]})
        if action == "rename":
            return self.post("/api/v2/torrents/rename", {"hash": payload.get("hash", hashes), "name": str(payload.get("name", ""))[:512]})
        if action == "set_category":
            return self.post("/api/v2/torrents/setCategory", {"hashes": hashes, "category": str(payload.get("category", ""))[:256]})
        if action in ("add_tags", "remove_tags"):
            endpoint = "addTags" if action == "add_tags" else "removeTags"
            return self.post(f"/api/v2/torrents/{endpoint}", {"hashes": hashes, "tags": str(payload.get("tags", ""))[:1024]})
        if action in ("set_download_limit", "set_upload_limit"):
            endpoint = "setDownloadLimit" if action == "set_download_limit" else "setUploadLimit"
            return self.post(f"/api/v2/torrents/{endpoint}", {"hashes": hashes, "limit": max(0, int(payload.get("limit", 0)))})
        if action == "file_priority":
            ids = payload.get("ids", "")
            if isinstance(ids, list): ids = "|".join(map(str, ids))
            return self.post("/api/v2/torrents/filePrio", {"hash": payload.get("hash"), "id": ids, "priority": int(payload.get("priority", 1))})
        if action == "global_download_limit":
            return self.post("/api/v2/transfer/setDownloadLimit", {"limit": max(0, int(payload.get("limit", 0)))})
        if action == "global_upload_limit":
            return self.post("/api/v2/transfer/setUploadLimit", {"limit": max(0, int(payload.get("limit", 0)))})
        if action == "toggle_alt_speed":
            return self.post("/api/v2/transfer/toggleSpeedLimitsMode", {})
        if action == "create_category":
            return self.post("/api/v2/torrents/createCategory", {"category": str(payload.get("category", ""))[:256], "savePath": str(payload.get("save_path", ""))[:2048]})
        if action == "create_tags":
            return self.post("/api/v2/torrents/createTags", {"tags": str(payload.get("tags", ""))[:1024]})
        if action == "add_magnet":
            form = {
                "urls": str(payload.get("urls", ""))[:16000],
                "savepath": str(payload.get("savepath", ""))[:2048],
                "category": str(payload.get("category", ""))[:256],
                "tags": str(payload.get("tags", ""))[:1024],
                "stopped": str(bool(payload.get("stopped", False))).lower(),
                "sequentialDownload": str(bool(payload.get("sequential", False))).lower(),
                "firstLastPiecePrio": str(bool(payload.get("first_last", False))).lower(),
            }
            return self.post("/api/v2/torrents/add", form)
        raise RuntimeError(f"Unsupported action: {action}")

    def upload_torrent(self, filename, content, fields):
        boundary = "----TorrentDashboard" + secrets.token_hex(12)
        chunks = []
        for k, v in fields.items():
            chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        safe_name = filename.replace('"', "")[:255]
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"torrents\"; filename=\"{safe_name}\"\r\nContent-Type: application/x-bittorrent\r\n\r\n".encode())
        chunks.append(content)
        chunks.append(f"\r\n--{boundary}--\r\n".encode())
        raw = b"".join(chunks)
        return self._request("POST", "/api/v2/torrents/add", raw=raw, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})


class HistoryStore:
    def __init__(self, path):
        DATA_DIR.mkdir(exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.last_sample = {}
        self.last_seen = {}
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots(
                ts INTEGER NOT NULL, server_id TEXT NOT NULL, dl INTEGER, up INTEGER,
                active INTEGER, total INTEGER, remaining INTEGER, disk_free INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots ON snapshots(server_id, ts);
            CREATE TABLE IF NOT EXISTS torrent_history(
                server_id TEXT NOT NULL, hash TEXT NOT NULL, name TEXT, category TEXT,
                added_on INTEGER, completion_on INTEGER, downloaded INTEGER, uploaded INTEGER,
                ratio REAL, last_seen INTEGER, PRIMARY KEY(server_id, hash)
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, server_id TEXT,
                hash TEXT, name TEXT, event TEXT, data TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events ON events(ts);
            """)

    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def sample(self, server_id, torrents, transfer, disk_free, every):
        now = int(time.time())
        with self.lock:
            if now - self.last_sample.get(server_id, 0) >= every:
                active = sum(1 for t in torrents if float(t.get("progress", 0)) < 1 and "paused" not in str(t.get("state", "")).lower() and "stopped" not in str(t.get("state", "")).lower())
                remaining = sum(int(t.get("amount_left", 0) or 0) for t in torrents)
                with self._db() as db:
                    db.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)", (
                        now, server_id, int(transfer.get("dl_info_speed", 0) or 0), int(transfer.get("up_info_speed", 0) or 0),
                        active, len(torrents), remaining, disk_free
                    ))
                self.last_sample[server_id] = now
            with self._db() as db:
                for t in torrents:
                    h = t.get("hash")
                    if not h: continue
                    prev = self.last_seen.get((server_id, h))
                    completed = float(t.get("progress", 0) or 0) >= 0.999999
                    if prev is not None and not prev and completed:
                        db.execute("INSERT INTO events(ts,server_id,hash,name,event,data) VALUES(?,?,?,?,?,?)", (now, server_id, h, t.get("name", ""), "completed", "{}"))
                    self.last_seen[(server_id, h)] = completed
                    db.execute("""INSERT INTO torrent_history(server_id,hash,name,category,added_on,completion_on,downloaded,uploaded,ratio,last_seen)
                        VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(server_id,hash) DO UPDATE SET name=excluded.name,category=excluded.category,
                        completion_on=excluded.completion_on,downloaded=excluded.downloaded,uploaded=excluded.uploaded,ratio=excluded.ratio,last_seen=excluded.last_seen""",
                        (server_id,h,t.get("name",""),t.get("category",""),int(t.get("added_on",0) or 0),int(t.get("completion_on",0) or 0),int(t.get("downloaded",0) or 0),int(t.get("uploaded",0) or 0),float(t.get("ratio",0) or 0),now))

    def event(self, server_id, event, name="", hash_="", data=None):
        with self._db() as db:
            db.execute("INSERT INTO events(ts,server_id,hash,name,event,data) VALUES(?,?,?,?,?,?)",
                       (int(time.time()), server_id, hash_, name, event, json.dumps(data or {})))

    def cleanup(self, days):
        cutoff = int(time.time()) - max(1, int(days)) * 86400
        with self._db() as db:
            db.execute("DELETE FROM snapshots WHERE ts < ?", (cutoff,))
            db.execute("DELETE FROM events WHERE ts < ?", (cutoff,))

    def history(self, server_id, minutes):
        cutoff = int(time.time()) - max(1, min(int(minutes), 43200)) * 60
        with self._db() as db:
            rows = db.execute("SELECT * FROM snapshots WHERE (?='all' OR server_id=?) AND ts>=? ORDER BY ts", (server_id, server_id, cutoff)).fetchall()
            return [dict(r) for r in rows]

    def events(self, limit=100):
        with self._db() as db:
            rows = db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (max(1,min(int(limit),500)),)).fetchall()
            return [dict(r) for r in rows]

    def analytics(self, server_id):
        now = int(time.time())
        with self._db() as db:
            rows = db.execute("SELECT * FROM snapshots WHERE (?='all' OR server_id=?) AND ts>=? ORDER BY ts", (server_id,server_id,now-7*86400)).fetchall()
            hist = db.execute("SELECT * FROM torrent_history WHERE (?='all' OR server_id=?)", (server_id,server_id)).fetchall()
        avg_dl = int(sum(r["dl"] or 0 for r in rows)/len(rows)) if rows else 0
        peak_dl = max((r["dl"] or 0 for r in rows), default=0)
        completed = sum(1 for r in hist if r["completion_on"] and r["completion_on"] > 0)
        avg_ratio = sum(float(r["ratio"] or 0) for r in hist)/len(hist) if hist else 0
        return {"avg_dl_7d":avg_dl,"peak_dl_7d":peak_dl,"known_torrents":len(hist),"completed":completed,"avg_ratio":avg_ratio}


HISTORY = HistoryStore(DB_PATH)
CACHE_LOCK = threading.RLock()
CACHE = {}
CLIENTS = {}
LAST_COMPLETION_EVENT = set()


def disk_free_for(preferences):
    path = (preferences or {}).get("save_path") or ""
    try:
        p = Path(path)
        if p.exists():
            return shutil.disk_usage(p).free
    except Exception:
        pass
    return None


def get_server_config(cfg, server_id):
    for s in cfg.get("servers", []):
        if s.get("id") == server_id and s.get("enabled", True):
            return s
    raise RuntimeError(f"Unknown or disabled server: {server_id}")


def get_client(cfg, server_id):
    server = get_server_config(cfg, server_id)
    key = (server_id, server.get("base_url"), server.get("auth_method"), server.get("api_key"), server.get("username"), server.get("password"))
    with CACHE_LOCK:
        item = CLIENTS.get(server_id)
        if not item or item[0] != key:
            CLIENTS[server_id] = (key, QBitClient(server))
        return CLIENTS[server_id][1]


def send_notification(cfg, title, message):
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
                data = json.dumps({"content": f"**{title}**\n{message}"}).encode("utf-8")
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
            data = json.dumps({"chat_id": n["telegram_chat_id"], "text": f"{title}\n{message}"}).encode("utf-8")
            urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST"), timeout=5).read()
        except Exception:
            pass


def collector_loop(stop_event):
    while not stop_event.is_set():
        cfg = load_config()
        sample_every = max(5, int(cfg["dashboard"].get("history_sample_seconds", 10)))
        for server in cfg.get("servers", []):
            if not server.get("enabled", True): continue
            sid = server.get("id")
            try:
                client = get_client(cfg, sid)
                torrents, transfer, app_version, api_version = client.info()
                meta = client.metadata()
                disk_free = disk_free_for(meta.get("preferences") or {})
                with CACHE_LOCK:
                    previous = CACHE.get(sid, {}).get("torrents", [])
                    prev_completed = {t.get("hash") for t in previous if float(t.get("progress",0) or 0) >= .999999}
                    now_completed = {t.get("hash") for t in torrents if float(t.get("progress",0) or 0) >= .999999}
                    newly = now_completed - prev_completed if previous else set()
                    CACHE[sid] = {
                        "ok": True, "ts": int(time.time()), "server": {"id":sid,"name":server.get("name",sid)},
                        "torrents": torrents, "transfer": transfer, "meta": meta,
                        "app_version": app_version, "api_version": api_version, "disk_free": disk_free
                    }
                HISTORY.sample(sid, torrents, transfer, disk_free, sample_every)
                for h in newly:
                    t = next((x for x in torrents if x.get("hash") == h), None)
                    if t:
                        send_notification(cfg, "Torrent completed", f"{t.get('name','Torrent')} finished on {server.get('name',sid)}")
            except Exception as e:
                with CACHE_LOCK:
                    old = CACHE.get(sid, {})
                    CACHE[sid] = {**old, "ok": False, "ts": int(time.time()), "server": {"id":sid,"name":server.get("name",sid)}, "error": str(e)}
        try:
            HISTORY.cleanup(cfg["dashboard"].get("history_retention_days",30))
        except Exception: pass
        stop_event.wait(STATUS_REFRESH_SECONDS)


def integration_request(url, api_key=None, token=None, path="/api/v3/system/status"):
    if not url: return {"configured":False}
    full = url.rstrip("/") + path
    headers = {}
    if api_key: headers["X-Api-Key"] = api_key
    if token: headers["X-Plex-Token"] = token
    try:
        with urllib.request.urlopen(urllib.request.Request(full,headers=headers),timeout=5) as r:
            body = r.read(200000)
            ctype = r.headers.get("Content-Type","")
        data = None
        if "json" in ctype:
            data = json.loads(body.decode())
        return {"configured":True,"ok":True,"status":data or body.decode(errors="replace")[:200]}
    except Exception as e:
        return {"configured":True,"ok":False,"error":str(e)}


def torrent_integration_matches(cfg, hash_):
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


def parse_json_body(handler, max_bytes=1_000_000):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length > max_bytes: raise RuntimeError("Request too large")
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode() or "{}")


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
        if b"\r\n\r\n" not in part: continue
        head, data = part.split(b"\r\n\r\n",1)
        if data.endswith(b"\r\n"): data=data[:-2]
        header=head.decode(errors="replace")
        if "Content-Disposition" not in header: continue
        name=""; filename=None
        for seg in header.split(";"):
            seg=seg.strip()
            if seg.startswith("name="): name=seg.split("=",1)[1].strip('"')
            if seg.startswith("filename="): filename=seg.split("=",1)[1].strip('"')
        if filename is not None: files.append((name,filename,data))
        else: fields[name]=data.decode(errors="replace")
    return fields, files



SOUND_MIME_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg"}


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


def normalize_github_repository(value: str) -> str:
    value = str(value or "").strip().removesuffix(".git").strip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip("/")
            break
    parts = value.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x or "") for x in parts):
        raise RuntimeError("GitHub repository must be owner/repo or a github.com repository URL")
    return "/".join(parts)


def github_headers(accept="application/vnd.github+json"):
    return {
        "User-Agent": f"TorrentDashboard/{VERSION}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def update_repository(cfg):
    updates = cfg.get("updates", {}) if isinstance(cfg.get("updates"), dict) else {}
    return normalize_github_repository(updates.get("repository") or DEFAULT_UPDATE_REPOSITORY)


def github_update_headers(cfg, accept="application/vnd.github+json"):
    update_repository(cfg)
    return github_headers(accept)


def save_update_source(cfg, repository):
    out = json.loads(json.dumps(cfg))
    repo = normalize_github_repository(repository)
    out["updates"] = {"repository": repo}
    out["integrations"] = [x for x in out.get("integrations", []) if x.get("type") != "github"]
    return out, repo


def _urlopen_json(url: str, timeout=10, headers=None):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":f"TorrentDashboard/{VERSION}","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if urllib.parse.urlparse(resp.geturl()).scheme != "https":
            raise RuntimeError("Update request redirected to a non-HTTPS URL")
        return json.loads(resp.read().decode("utf-8"))


def _urlopen_bytes(url: str, timeout=15, headers=None, max_bytes=8*1024*1024):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":f"TorrentDashboard/{VERSION}"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if urllib.parse.urlparse(resp.geturl()).scheme != "https":
            raise RuntimeError("Update request redirected to a non-HTTPS URL")
        data=resp.read(max_bytes+1)
        if len(data)>max_bytes:
            raise RuntimeError("Update metadata exceeds the safety limit")
        return data


def _version_key(value: str):
    raw = str(value or "0").strip().lstrip("vV")
    main, sep, pre = raw.partition("-")
    nums=[]
    for part in main.split("."):
        m=re.match(r"^(\d+)",part)
        nums.append(int(m.group(1)) if m else 0)
    nums=(nums+[0,0,0,0])[:4]
    pre_key=(1,"") if not sep else (0,pre.lower())
    return (*nums, *pre_key)


def is_newer_version(candidate: str, current: str = VERSION) -> bool:
    return _version_key(candidate) > _version_key(current)


def _github_releases(cfg, repo: str):
    url=f"https://api.github.com/repos/{repo}/releases?per_page=20"
    try:
        releases=_urlopen_json(url, timeout=10, headers=github_update_headers(cfg))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("GitHub denied the request or the unauthenticated API rate limit was reached. Try again later.") from exc
        if exc.code == 404:
            raise RuntimeError("Public GitHub repository or releases were not found. Verify the repository name and published releases.") from exc
        raise
    return [r for r in (releases or []) if not r.get("draft")]


def _latest_github_release(cfg, repo: str):
    releases=_github_releases(cfg,repo)
    if not releases:
        raise RuntimeError("No GitHub release was found for the configured repository")
    # Releases are returned newest first. During the 0.x prerelease phase we
    # intentionally include prereleases instead of using /releases/latest,
    # which excludes them.
    return releases[0]


def _find_dashboard_asset(release):
    assets=release.get("assets") or []
    candidates=[a for a in assets if re.fullmatch(r"Torrent-Dashboard-[0-9A-Za-z.+-]+\.zip", str(a.get("name") or ""))]
    if not candidates:
        candidates=[a for a in assets if str(a.get("name") or "").lower().endswith(".zip")]
    return candidates[0] if candidates else None


def _asset_sha256(asset):
    digest=str((asset or {}).get("digest") or "").strip().lower()
    if digest.startswith("sha256:"):
        digest=digest.split(":",1)[1]
    if not re.fullmatch(r"[0-9a-f]{64}",digest):
        raise RuntimeError("GitHub did not provide a SHA-256 digest for the release ZIP")
    return digest


def validate_update_repository(repository: str):
    repo = normalize_github_repository(repository)
    try:
        info = _urlopen_json(f"https://api.github.com/repos/{repo}", timeout=10, headers=github_headers())
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError("GitHub denied the request or the unauthenticated API rate limit was reached. Try again later.") from exc
        if exc.code == 404:
            raise RuntimeError("Public GitHub repository not found. Verify owner/repository and make sure the repository is public.") from exc
        raise RuntimeError(f"GitHub repository check failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to GitHub: {exc.reason}") from exc
    if bool(info.get("private", False)):
        raise RuntimeError("Torrent Dashboard updates require a public GitHub repository")
    return str(info.get("full_name") or repo)


def fetch_update_release(cfg):
    repo = validate_update_repository(update_repository(cfg))
    release=_latest_github_release(cfg,repo)
    tag=str(release.get("tag_name") or "").strip()
    version=tag.lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",version):
        raise RuntimeError("GitHub release tag must use semantic versioning, for example v0.4.0")
    asset=_find_dashboard_asset(release)
    if not asset:
        raise RuntimeError("The latest GitHub release does not contain a Torrent Dashboard ZIP")
    api_url=str(asset.get("url") or "")
    if not api_url.startswith("https://api.github.com/"):
        raise RuntimeError("GitHub release asset URL is invalid")
    data={
        "version":version,
        "channel":"prerelease" if release.get("prerelease") else "stable",
        "publishedAt":str(release.get("published_at") or release.get("created_at") or ""),
        "releaseUrl":str(release.get("html_url") or ""),
        "notes":str(release.get("body") or ""),
        "asset":{
            "name":str(asset.get("name") or f"Torrent-Dashboard-{version}.zip"),
            "githubApiUrl":api_url,
            "url":str(asset.get("browser_download_url") or ""),
            "sha256":_asset_sha256(asset),
            "size":int(asset.get("size") or 0),
        },
        "currentVersion":VERSION,
    }
    data["updateAvailable"]=is_newer_version(version)
    return data

# Compatibility alias for older front-end/update-state code. The update
# metadata is now synthesized directly from GitHub Release metadata; there is
# no external update-manifest.json asset.
def fetch_update_manifest(cfg):
    return fetch_update_release(cfg)

def update_state():
    if not UPDATE_STATE_PATH.exists(): return {"state":"idle","currentVersion":VERSION}
    try:
        d=json.loads(UPDATE_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(d,dict):
            d.setdefault("currentVersion",VERSION)
            return d
    except Exception: pass
    return {"state":"idle","currentVersion":VERSION}


def write_update_state(data):
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    payload={**data,"currentVersion":VERSION,"ts":int(time.time())}
    tmp=UPDATE_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    tmp.replace(UPDATE_STATE_PATH)
    return payload


def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def safe_extract_zip(zip_path: Path, dest: Path):
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True,exist_ok=True)
    root=dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            member=(dest/info.filename).resolve()
            if root != member and root not in member.parents:
                raise RuntimeError("Update ZIP contains an unsafe path")
        z.extractall(dest)
    entries=[p for p in dest.iterdir() if p.name not in ("__MACOSX",)]
    source=entries[0] if len(entries)==1 and entries[0].is_dir() else dest
    if not (source/"dashboard.py").exists() or not (source/"static"/"index.html").exists():
        raise RuntimeError("Update ZIP does not contain a valid Torrent Dashboard application")
    return source


def stage_update(cfg):
    manifest=fetch_update_manifest(cfg)
    if not manifest["updateAvailable"]:
        return {"state":"upToDate","manifest":manifest,"currentVersion":VERSION}
    version=manifest["version"]
    stage=UPDATE_DIR/version
    stage.mkdir(parents=True,exist_ok=True)
    package=stage/manifest["asset"]["name"]
    package_url=manifest["asset"].get("githubApiUrl") or manifest["asset"]["url"]
    headers=github_update_headers(cfg,"application/octet-stream") if manifest["asset"].get("githubApiUrl") else {"User-Agent":f"TorrentDashboard/{VERSION}"}
    req=urllib.request.Request(package_url,headers=headers)
    write_update_state({"state":"downloading","version":version,"manifest":manifest})
    h=hashlib.sha256(); total=0
    try:
        expected=int(manifest["asset"].get("size") or 0)
        max_bytes=512*1024*1024
        if expected>max_bytes: raise RuntimeError("Update package exceeds the 512 MB safety limit")
        with urllib.request.urlopen(req,timeout=30) as resp, package.open("wb") as out:
            if urllib.parse.urlparse(resp.geturl()).scheme != "https":
                raise RuntimeError("Update package redirected to a non-HTTPS URL")
            while True:
                chunk=resp.read(1024*1024)
                if not chunk: break
                total+=len(chunk)
                if total>max_bytes or (expected and total>expected):
                    raise RuntimeError("Downloaded update exceeds the GitHub release size or safety limit")
                out.write(chunk); h.update(chunk)
        got=h.hexdigest()
        if got != manifest["asset"]["sha256"]:
            package.unlink(missing_ok=True)
            raise RuntimeError("Downloaded update failed SHA-256 verification")
        if expected and total != expected:
            package.unlink(missing_ok=True)
            raise RuntimeError("Downloaded update size does not match the GitHub release asset")
        source=safe_extract_zip(package,stage/"extracted")
        payload={"state":"readyToInstall","version":version,"package":str(package),"source":str(source),"manifest":manifest,"sha256":got,"bytes":total}
        write_update_state(payload)
        return payload
    except Exception as exc:
        write_update_state({"state":"failed","version":version,"error":str(exc),"manifest":manifest})
        raise


def launch_update_installer(handler, cfg, requested_version=None):
    state=update_state()
    if state.get("state") != "readyToInstall":
        raise RuntimeError("No verified update is ready to install")
    if not is_newer_version(str(state.get("version") or "")):
        raise RuntimeError("The staged update is not newer than the running version")
    if requested_version and str(requested_version) != str(state.get("version")):
        raise RuntimeError("The staged update version changed; check for updates again")
    source=Path(state.get("source","")).resolve()
    if not source.exists(): raise RuntimeError("The staged update files are missing")
    updater=(APP_DIR/"updater.py").resolve()
    if not updater.exists(): raise RuntimeError("updater.py is missing")
    cmd=[sys.executable,str(updater),"--pid",str(os.getpid()),"--source",str(source),"--target",str(APP_DIR),"--version",str(state.get("version"))]
    kwargs={"cwd":str(APP_DIR),"stdin":subprocess.DEVNULL,"stdout":subprocess.DEVNULL,"stderr":subprocess.DEVNULL}
    if os.name=="nt":
        kwargs["creationflags"]=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)|getattr(subprocess,"DETACHED_PROCESS",0)
    else: kwargs["start_new_session"]=True
    subprocess.Popen(cmd,**kwargs)
    write_update_state({**state,"state":"installing"})
    threading.Timer(.5,handler.server.shutdown).start()
    return {"ok":True,"state":"installing","version":state.get("version")}


class Handler(BaseHTTPRequestHandler):
    server_version = "TorrentDashboard/0"

    def log_message(self, fmt, *args):
        if args and str(args[1]).startswith("5"):
            super().log_message(fmt,*args)

    def client_ip(self):
        return self.client_address[0]

    def cookie_token(self):
        raw=self.headers.get("Cookie","")
        c=cookies.SimpleCookie();
        try: c.load(raw)
        except Exception: return None
        return c.get("td_session").value if c.get("td_session") else None

    def auth(self, create_bypass=True):
        cfg=load_config(); a=cfg["auth"]; mode=a.get("mode","lan_bypass")
        token=self.cookie_token(); sess=SESSIONS.get(token)
        if sess: return cfg,token,sess,None
        bypass = mode=="disabled" or (mode=="lan_bypass" and is_trusted_ip(self.client_ip(),effective_trusted_cidrs(a)))
        if bypass and create_bypass:
            token,sess=SESSIONS.create("LAN" if mode!="disabled" else "Guest",a.get("session_hours",24),"lan_bypass" if mode!="disabled" else "disabled",group="administrator",display_name="Trusted Network" if mode!="disabled" else "Guest")
            return cfg,token,sess,token
        return cfg,None,None,None

    def csrf_ok(self,sess):
        return bool(sess and self.headers.get("X-CSRF-Token") and hmac.compare_digest(self.headers.get("X-CSRF-Token"),sess.get("csrf","")))

    def send_bytes(self, code, body, content_type, cookie_token=None, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'")
        if cookie_token:
            secure = "; Secure" if load_config()["dashboard"].get("https_enabled") else ""
            self.send_header("Set-Cookie", f"td_session={cookie_token}; Path=/; HttpOnly; SameSite=Lax{secure}")
        if extra:
            for k,v in extra.items(): self.send_header(k,str(v))
        self.end_headers(); self.wfile.write(body)

    def send_json(self, code, obj, cookie_token=None):
        self.send_bytes(code,json.dumps(obj,separators=(",",":"),default=str).encode(),"application/json; charset=utf-8",cookie_token)

    def require_auth(self, mutation=False):
        cfg,token,sess,new_cookie=self.auth()
        if not sess:
            self.send_json(401,{"error":"Authentication required","auth_mode":cfg["auth"].get("mode")})
            return None
        if mutation and not self.csrf_ok(sess):
            self.send_json(403,{"error":"CSRF token missing or invalid"},new_cookie)
            return None
        return cfg,token,sess,new_cookie

    def do_GET(self):
        path,_,query=self.path.partition("?"); qs=urllib.parse.parse_qs(query)
        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION,"pid":os.getpid(),"application":str(APP_DIR),"python":sys.executable})
        if path=="/manifest.webmanifest": return self.serve_static("manifest.webmanifest")
        if path=="/sw.js": return self.serve_static("sw.js","application/javascript; charset=utf-8")
        if path.startswith("/static/"): return self.serve_static(path[len("/static/"):])
        if path=="/" or path=="/index.html": return self.serve_static("index.html")

        if path=="/api/setup/status":
            cfg=load_config(); required=not bool(cfg.get("setup",{}).get("complete"))
            interfaces=detect_network_interfaces()
            return self.send_json(200,{
                "required": required,
                "code_required": bool(required and not is_loopback_ip(self.client_ip())),
                "client_ip": self.client_ip(),
                "lan_ip": local_lan_ip(),
                "port": cfg["dashboard"].get("port",8765),
                "trusted_interfaces": cfg["auth"].get("trusted_interfaces",[]),
                "trusted_ips": cfg["auth"].get("trusted_ips",[]),
                "effective_trusted_cidrs": effective_trusted_cidrs(cfg["auth"]),
                "network_interfaces": interfaces,
                "detected_lan": detect_lan_network(),
        "local_ip": local_lan_ip(),
            })
        if path=="/api/setup/network-interfaces":
            return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")})

        if path=="/api/me":
            cfg,token,sess,new_cookie=self.auth()
            if not sess:
                return self.send_json(401,{"authenticated":False,"auth_mode":cfg["auth"].get("mode")})
            safe={"authenticated":True,"username":sess["username"],"display_name":sess.get("display_name") or sess["username"],"user_id":sess.get("user_id","") ,"group":sess.get("group","standard"),"group_label":USER_GROUPS.get(sess.get("group"),"Standard User"),"can_manage":session_is_admin(sess),"auth_kind":sess["auth_kind"],"csrf":sess["csrf"],"auth_mode":cfg["auth"].get("mode"),"title":cfg["dashboard"].get("title"),"version":VERSION,"lan_ip":local_lan_ip(),"port":cfg["dashboard"].get("port",8765),"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http"}
            return self.send_json(200,safe,new_cookie)

        ctx=self.require_auth(False)
        if not ctx: return
        cfg,token,sess,new_cookie=ctx
        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces") and not session_is_admin(sess):
            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)

        if path=="/api/status":
            sid=qs.get("server",["all"])[0]
            with CACHE_LOCK:
                if sid=="all":
                    items=[dict(v) for k,v in CACHE.items()]
                    torrents=[]; transfer={"dl_info_speed":0,"up_info_speed":0,"dl_info_data":0,"up_info_data":0}; errors=[]
                    for item in items:
                        if not item.get("ok"):
                            errors.append({"server":item.get("server"),"error":item.get("error")}); continue
                        for t in item.get("torrents",[]): torrents.append({**t,"_server_id":item["server"]["id"],"_server_name":item["server"]["name"]})
                        for key in transfer: transfer[key]+=int(item.get("transfer",{}).get(key,0) or 0)
                    payload={"ok":len(errors)<len(items) if items else False,"server":{"id":"all","name":"All servers"},"torrents":torrents,"transfer":transfer,"errors":errors,"servers":[x.get("server") for x in items],"ts":int(time.time())}
                else:
                    payload=dict(CACHE.get(sid) or {"ok":False,"error":"No data yet; collector is connecting","server":{"id":sid,"name":sid}})
            payload["tab_counts"]={
                "all":len(payload.get("torrents",[])),
                "downloading":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)<1 and "paused" not in str(t.get("state","")).lower() and "stopped" not in str(t.get("state","")).lower()),
                "completed":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)>=.999999),
                "paused":sum(1 for t in payload.get("torrents",[]) if "paused" in str(t.get("state","")).lower() or "stopped" in str(t.get("state","")).lower()),
            }
            return self.send_json(200,payload,new_cookie)

        if path=="/api/servers":
            servers=[{"id":s.get("id"),"name":s.get("name",s.get("id")),"enabled":s.get("enabled",True)} for s in cfg.get("servers",[])]
            return self.send_json(200,{"servers":servers},new_cookie)

        if path=="/api/detail":
            sid=qs.get("server",["local"])[0]; h=qs.get("hash",[""])[0]
            try:
                d=get_client(cfg,sid).detail(h); d["integrations"]=torrent_integration_matches(cfg,h)
                return self.send_json(200,d,new_cookie)
            except Exception as e: return self.send_json(502,{"error":str(e)},new_cookie)

        if path=="/api/meta":
            sid=qs.get("server",["local"])[0]
            try: return self.send_json(200,get_client(cfg,sid).metadata(),new_cookie)
            except Exception as e: return self.send_json(502,{"error":str(e)},new_cookie)

        if path=="/api/history":
            return self.send_json(200,{"points":HISTORY.history(qs.get("server",["all"])[0],qs.get("minutes",["60"])[0])},new_cookie)
        if path=="/api/events": return self.send_json(200,{"events":HISTORY.events(qs.get("limit",["100"])[0])},new_cookie)
        if path=="/api/analytics": return self.send_json(200,HISTORY.analytics(qs.get("server",["all"])[0]),new_cookie)
        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)
        if path=="/api/users": return self.send_json(200,{"users":[public_user(u) for u in cfg.get("users",[])],"current_user_id":sess.get("user_id","")},new_cookie)
        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)
        if path=="/api/network/interfaces": return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")},new_cookie)
        if path=="/api/notification-sound":
            sound_path, sound_mime = configured_notification_sound(cfg)
            if not sound_path:
                return self.send_json(404,{"error":"No custom notification sound is configured"},new_cookie)
            return self.send_bytes(200,sound_path.read_bytes(),sound_mime,new_cookie)
        if path=="/api/update-check": return self.update_check(cfg,new_cookie)
        if path=="/api/update-status": return self.send_json(200,update_state(),new_cookie)
        return self.send_json(404,{"error":"Not found"},new_cookie)

    def do_POST(self):
        path=self.path.partition("?")[0]
        if path=="/api/setup/test-client": return self.setup_test_client()
        if path=="/api/setup/complete": return self.setup_complete()
        if path=="/api/login": return self.login_route()
        if path=="/api/logout":
            token=self.cookie_token(); SESSIONS.remove(token)
            return self.send_json(200,{"ok":True},None)
        ctx=self.require_auth(True)
        if not ctx: return
        cfg,token,sess,new_cookie=ctx
        if not session_is_admin(sess):
            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)
        try:
            if path=="/api/action":
                data=parse_json_body(self); sid=data.pop("server","local"); action=data.pop("action"); result=get_client(cfg,sid).action(action,data)
                HISTORY.event(sid, "action:"+action, sess.get("username",""), data.get("hash") or "", {"client_ip": self.client_ip()})
                return self.send_json(200,{"ok":True,"status":result[0] if isinstance(result,tuple) else 200},new_cookie)
            if path=="/api/upload":
                fields,files=parse_multipart(self); sid=fields.pop("server","local")
                if not files: raise RuntimeError("No .torrent file supplied")
                _,filename,content=files[0]
                get_client(cfg,sid).upload_torrent(filename,content,fields)
                HISTORY.event(sid, "torrent_upload", filename, "", {"client_ip": self.client_ip()})
                return self.send_json(200,{"ok":True},new_cookie)
            if path=="/api/client-test":
                data=parse_json_body(self); sid=str(data.get("id") or "")
                existing=next((x for x in cfg.get("servers",[]) if x.get("id")==sid),{})
                server=normalize_qbittorrent_server(data,existing)
                return self.send_json(200,test_server_connection(server),new_cookie)
            if path=="/api/integration-test":
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
            if path=="/api/settings":
                data=parse_json_body(self); updated=apply_settings_update(cfg,data); save_config(updated)
                HISTORY.event("dashboard", "settings_changed", sess.get("username",""), "", {"client_ip": self.client_ip()})
                return self.send_json(200,{"ok":True,"settings":redacted_config(updated)},new_cookie)
            if path=="/api/update-source":
                data=parse_json_body(self,10000); previous_repo=update_repository(cfg); updated,repo=save_update_source(cfg,data.get("repository") or ""); save_config(updated)
                if repo != previous_repo:
                    UPDATE_STATE_PATH.unlink(missing_ok=True)
                    if UPDATE_DIR.exists(): shutil.rmtree(UPDATE_DIR, ignore_errors=True)
                HISTORY.event("dashboard","update_source_changed",repo,"",{"client_ip":self.client_ip()})
                return self.send_json(200,{"ok":True,"repository":repo,"settings":redacted_config(updated)},new_cookie)
            if path=="/api/update-download":
                result=stage_update(cfg)
                HISTORY.event("dashboard","update_downloaded",str(result.get("version") or ""),"",{"client_ip":self.client_ip()})
                return self.send_json(200,result,new_cookie)
            if path=="/api/update-install":
                data=parse_json_body(self,10000)
                result=launch_update_installer(self,cfg,data.get("version"))
                HISTORY.event("dashboard","update_install_started",str(result.get("version") or ""),"",{"client_ip":self.client_ip()})
                return self.send_json(200,result,new_cookie)
            if path=="/api/notification-sound":
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
        except Exception as e:
            return self.send_json(400,{"error":str(e)},new_cookie)
        return self.send_json(404,{"error":"Not found"},new_cookie)

    def setup_authorized(self, data):
        cfg=load_config()
        if cfg.get("setup",{}).get("complete"):
            raise RuntimeError("Setup has already been completed")
        if is_loopback_ip(self.client_ip()):
            return cfg
        supplied=str(data.get("setup_code","")).strip().upper()
        if not supplied or not hmac.compare_digest(supplied,SETUP_CODE):
            raise RuntimeError("The setup code is required for remote first-run setup")
        return cfg

    def setup_test_client(self):
        try:
            data=parse_json_body(self,20000); self.setup_authorized(data)
            server=normalize_qbittorrent_server(data.get("server") or {})
            return self.send_json(200,test_server_connection(server))
        except Exception as e:
            return self.send_json(400,{"error":str(e)})

    def setup_complete(self):
        try:
            data=parse_json_body(self,50000); cfg=self.setup_authorized(data)
            dashboard=data.get("dashboard") or {}; auth=data.get("auth") or {}; servers=data.get("servers") or []
            if not servers:
                raise RuntimeError("Add at least one download client")
            mode=str(auth.get("mode","lan_bypass"))
            if mode not in ("required","lan_bypass","disabled"):
                raise RuntimeError("Invalid authentication mode")
            username=str(auth.get("username") or "admin")[:128]
            password=str(auth.get("password") or "")
            if mode in ("required","lan_bypass") and not password:
                raise RuntimeError("Set a dashboard password. LAN bypass will skip it only for trusted LAN addresses.")
            trusted_interfaces=[str(x) for x in (auth.get("trusted_interfaces") or []) if str(x)]
            trusted_ips=[str(x).strip() for x in (auth.get("trusted_ips") or []) if str(x).strip()]
            detected_ids={x.get("interface_id") for x in detect_network_interfaces()}
            missing=[x for x in trusted_interfaces if x not in detected_ids]
            if missing:
                raise RuntimeError("Selected network interface is unavailable: " + ", ".join(missing))
            for value in trusted_ips:
                normalize_trusted_entry(value)
            if mode=="lan_bypass" and not trusted_interfaces and not trusted_ips:
                raise RuntimeError("Select at least one trusted network interface or add an IP address to the whitelist.")
            normalized=[]
            for item in servers:
                server=normalize_qbittorrent_server(item)
                test_server_connection(server)  # Final verification before anything is saved.
                normalized.append(server)
            out=json.loads(json.dumps(DEFAULT_CONFIG))
            out["setup"]={"complete":True}
            out["dashboard"]["title"]=str(dashboard.get("title") or "Torrent Dashboard")[:128]
            out["dashboard"]["bind_host"]="0.0.0.0"
            out["dashboard"]["port"]=int(dashboard.get("port") or 8765)
            out["auth"]["mode"]=mode
            out["auth"]["trusted_interfaces"]=trusted_interfaces
            out["auth"]["trusted_ips"]=trusted_ips
            admin_user=normalize_user({"username":username,"password":password,"group":"administrator"},require_password=mode in ("required","lan_bypass"))
            out["users"]=[admin_user]
            out["integrations"]=[]
            sync_legacy_auth(out)
            out["servers"]=normalized
            save_config(out)
            with CACHE_LOCK:
                CLIENTS.clear()
            with CACHE_LOCK:
                CACHE.clear()
            if mode=="disabled": auth_kind="disabled"
            elif mode=="lan_bypass" and is_trusted_ip(self.client_ip(),effective_trusted_cidrs(out["auth"])): auth_kind="lan_bypass"
            else: auth_kind="password"
            token,sess=SESSIONS.create(username,out["auth"].get("session_hours",24),auth_kind,group="administrator",user_id=admin_user["id"],display_name=user_display_name(admin_user))
            HISTORY.event("dashboard","setup_completed",username,"",{"client_ip":self.client_ip(),"servers":len(normalized),"auth_mode":mode})
            return self.send_json(200,{"ok":True,"csrf":sess["csrf"],"message":"Setup complete"},token)
        except Exception as e:
            return self.send_json(400,{"error":str(e)})

    def login_route(self):
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

    def serve_static(self,name,content_type=None):
        safe=(STATIC_DIR/name).resolve()
        if STATIC_DIR.resolve() not in safe.parents and safe!=STATIC_DIR.resolve(): return self.send_bytes(403,b"Forbidden","text/plain")
        if not safe.exists() or not safe.is_file(): return self.send_bytes(404,b"Not found","text/plain")
        ctype=content_type or mimetypes.guess_type(str(safe))[0] or "application/octet-stream"
        return self.send_bytes(200,safe.read_bytes(),ctype)

    def update_check(self,cfg,new_cookie):
        try:
            repo = update_repository(cfg)
        except Exception as e:
            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)
        try:
            manifest=fetch_update_manifest(cfg)
            return self.send_json(200,{"configured":True,"repository":repo,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)
        except Exception as e:
            return self.send_json(502,{"configured":True,"repository":repo,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)


def redacted_config(cfg):
    out=json.loads(json.dumps(cfg))
    out.setdefault("auth",{}).pop("password_hash",None)
    out.setdefault("auth",{}).pop("username",None)
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
    for k in ("title","port","history_retention_days","history_sample_seconds","low_disk_gb","https_enabled","https_cert","https_key"): 
        if k in dash: out["dashboard"][k]=dash[k]
    out.setdefault("dashboard",{}).pop("read_only",None)
    out["dashboard"].pop("refresh_seconds",None)
    if "port" in dash:
        out["dashboard"]["port"]=max(1,min(65535,int(dash.get("port") or 8765)))
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


def main():
    parser=argparse.ArgumentParser(description="Torrent Dashboard")
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--set-password",action="store_true")
    args=parser.parse_args()
    instance_lock=SingleInstanceLock()
    if not instance_lock.acquire():
        print("Torrent Dashboard is already running on this computer.")
        print("Close the existing dashboard process before starting another instance.")
        raise SystemExit(3)
    atexit.register(instance_lock.release)
    if args.set_password:
        import getpass
        p1=getpass.getpass("New dashboard password: "); p2=getpass.getpass("Confirm password: ")
        if not p1 or p1!=p2: raise SystemExit("Passwords did not match or were empty.")
        set_password_cli(p1); return
    cfg=load_config(); host=str(cfg["dashboard"].get("bind_host","0.0.0.0")); port=int(cfg["dashboard"].get("port",8765))
    stop=threading.Event(); threading.Thread(target=collector_loop,args=(stop,),daemon=True).start()
    server=ThreadingHTTPServer((host,port),Handler)
    scheme="http"
    if cfg["dashboard"].get("https_enabled"):
        cert=cfg["dashboard"].get("https_cert",""); key=cfg["dashboard"].get("https_key","")
        if not cert or not key: raise SystemExit("HTTPS is enabled but https_cert/https_key are not configured")
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert,key); server.socket=ctx.wrap_socket(server.socket,server_side=True); scheme="https"
    print(f"Torrent Dashboard {VERSION}")
    print(f"Process ID: {os.getpid()}")
    print(f"Application: {APP_DIR}")
    print(f"Python: {sys.executable}")
    print(f"Listening on {scheme}://{host}:{port}")
    print(f"Local IP Address: {local_lan_ip()}")
    print(f"Port: {port}")
    if not cfg.get("setup",{}).get("complete"):
        print("First-run setup is required. The local browser can configure Torrent Dashboard directly.")
        print(f"Remote setup code: {SETUP_CODE}")
    mode=cfg["auth"].get("mode")
    if mode=="disabled" and host not in ("127.0.0.1","::1","localhost"):
        print("WARNING: dashboard authentication is DISABLED on a non-loopback interface.")
    elif mode=="lan_bypass":
        print("Authentication mode: LAN bypass (selected trusted networks and whitelisted IPs do not require a password).")
    else: print("Authentication mode: required")
    if cfg["dashboard"].get("open_browser",True) and not args.no_browser:
        threading.Timer(.7,lambda:webbrowser.open(f"{scheme}://127.0.0.1:{port}")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: stop.set(); server.server_close()

if __name__=="__main__": main()
