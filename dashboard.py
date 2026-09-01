#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import http.cookiejar
import importlib.util
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
VERSION = "3.4.0"

DEFAULT_CONFIG = {
    "setup": {"complete": False},
    "dashboard": {
        "title": "Torrent Desk",
        "bind_host": "0.0.0.0",
        "port": 8765,
        "open_browser": True,
        "refresh_seconds": 2,
        "history_retention_days": 30,
        "history_sample_seconds": 10,
        "low_disk_gb": 20,
        "read_only": False,
        "update_manifest_url": "",
        "https_enabled": False,
        "https_cert": "",
        "https_key": ""
    },
    "updates": {
        "enabled": True,
        "repository": "CynicaGaming/TorrentDashboard",
        "github_token": "",
        "manifest_url": "",
        "auto_check": True,
        "check_hours": 6
    },
    "auth": {
        "mode": "lan_bypass",
        "username": "admin",
        "password_hash": "",
        "trusted_interfaces": [],
        "trusted_ips": [],
        "session_hours": 24,
        "max_login_attempts_per_10m": 20
    },
    "servers": [],
    "notifications": {
        "browser": True,
        "sound": False,
        "webhook_url": "",
        "discord_webhook": "",
        "ntfy_url": "",
        "gotify_url": "",
        "gotify_token": "",
        "telegram_bot_token": "",
        "telegram_chat_id": ""
    },
    "integrations": {
        "sonarr": {"url": "", "api_key": ""},
        "radarr": {"url": "", "api_key": ""},
        "lidarr": {"url": "", "api_key": ""},
        "prowlarr": {"url": "", "api_key": ""},
        "jellyfin": {"url": "", "api_key": ""},
        "plex": {"url": "", "token": ""},
        "home_assistant_webhook": ""
    }
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
    # Existing Torrent Desk 3.x installs predate the setup wizard. Treat an
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
    updates_raw = raw.setdefault("updates", {})
    updates_raw.setdefault("github_token", "")
    legacy_manifest = raw.get("dashboard", {}).get("update_manifest_url", "")
    if legacy_manifest and not updates_raw.get("manifest_url"):
        updates_raw["manifest_url"] = legacy_manifest
        updates_raw["enabled"] = True
    return deep_merge(DEFAULT_CONFIG, raw)


def save_config(cfg):
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

    def create(self, username, hours, auth_kind):
        token = secrets.token_urlsafe(32)
        session = {
            "username": username,
            "csrf": secrets.token_urlsafe(24),
            "expires": time.time() + max(1, hours) * 3600,
            "auth_kind": auth_kind
        }
        with self.lock:
            self.sessions[token] = session
        return token, session

    def get(self, token):
        if not token:
            return None
        with self.lock:
            s = self.sessions.get(token)
            if not s:
                return None
            if s["expires"] < time.time():
                self.sessions.pop(token, None)
                return None
            return s

    def delete(self, token):
        with self.lock:
            self.sessions.pop(token, None)

SESSIONS = SessionStore()
LOGIN_ATTEMPTS = defaultdict(deque)


# ---------- local network helpers ----------

NETWORK_CACHE = {"ts": 0.0, "interfaces": []}
NETWORK_CACHE_SECONDS = 15


def _prefix_from_netmask(mask):
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except Exception:
        return None


def _network_record(interface, address, prefix, gateway="", default=False, interface_id=None):
    try:
        iface = ipaddress.ip_interface(f"{address}/{int(prefix)}")
        net = iface.network
    except Exception:
        return None
    hosts = None
    if net.num_addresses > 2:
        hosts = (str(net.network_address + 1), str(net.broadcast_address - 1))
    else:
        hosts = (str(net.network_address), str(net.broadcast_address))
    return {
        "interface": str(interface or interface_id or "Network Interface"),
        "interface_id": str(interface_id or interface or address),
        "address": str(iface.ip),
        "prefix": int(prefix),
        "cidr": str(net),
        "netmask": str(net.netmask),
        "network": str(net.network_address),
        "broadcast": str(net.broadcast_address),
        "range_start": hosts[0],
        "range_end": hosts[1],
        "gateway": str(gateway or ""),
        "default": bool(default),
    }


def _windows_interfaces():
    try:
        cp = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=6,
                            encoding="utf-8", errors="replace")
    except Exception:
        return []
    if cp.returncode != 0:
        return []
    blocks = re.split(r"\r?\n(?=\S[^\r\n]*adapter\s+[^:]+:)", cp.stdout, flags=re.I)
    out = []
    for block in blocks:
        first = block.splitlines()[0].strip() if block.splitlines() else ""
        mname = re.match(r"(.+?)\s+adapter\s+(.+):", first, re.I)
        if not mname:
            continue
        kind, name = mname.group(1).strip(), mname.group(2).strip()
        maddr = re.search(r"IPv4 Address[^:]*:\s*([0-9.]+)", block, re.I)
        mmask = re.search(r"Subnet Mask[^:]*:\s*([0-9.]+)", block, re.I)
        mgw = re.search(r"Default Gateway[^:]*:\s*([0-9.]+)", block, re.I)
        disconnected = "Media disconnected" in block
        if disconnected or not (maddr and mmask):
            continue
        addr, mask = maddr.group(1), mmask.group(1)
        prefix = _prefix_from_netmask(mask)
        if prefix is None:
            continue
        gateway = mgw.group(1) if mgw else ""
        rec = _network_record(name, addr, prefix, gateway, bool(gateway), f"windows:{kind}:{name}")
        if rec and not ipaddress.ip_address(addr).is_loopback:
            out.append(rec)
    return out


def _linux_interfaces():
    try:
        cp = subprocess.run(["ip", "-o", "-4", "addr", "show", "up"], capture_output=True, text=True, timeout=5)
        rp = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=5)
    except Exception:
        return []
    if cp.returncode != 0:
        return []
    default_if = ""; default_gw = ""
    if rp.returncode == 0:
        m = re.search(r"default\s+via\s+(\S+)\s+dev\s+(\S+)", rp.stdout)
        if m:
            default_gw, default_if = m.group(1), m.group(2)
    out=[]
    for line in cp.stdout.splitlines():
        m=re.match(r"\d+:\s+([^\s:]+)(?:@\S+)?\s+inet\s+([0-9.]+)/(\d+)",line)
        if not m:
            continue
        name, addr, prefix=m.group(1),m.group(2),int(m.group(3))
        if ipaddress.ip_address(addr).is_loopback:
            continue
        rec=_network_record(name,addr,prefix,default_gw if name==default_if else "",name==default_if,f"linux:{name}")
        if rec: out.append(rec)
    return out


def _darwin_interfaces():
    try:
        rc=subprocess.run(["route","-n","get","default"],capture_output=True,text=True,timeout=5)
        default_if=""; default_gw=""
        if rc.returncode==0:
            m=re.search(r"interface:\s*(\S+)",rc.stdout); default_if=m.group(1) if m else ""
            m=re.search(r"gateway:\s*(\S+)",rc.stdout); default_gw=m.group(1) if m else ""
        cp=subprocess.run(["ifconfig"],capture_output=True,text=True,timeout=5)
    except Exception: return []
    if cp.returncode!=0:return []
    out=[]
    for block in re.split(r"\n(?=\S+: flags=)",cp.stdout):
        mname=re.match(r"([^:]+):",block); maddr=re.search(r"\sinet\s+([0-9.]+)\s+netmask\s+(0x[0-9a-f]+|[0-9.]+)",block,re.I)
        if not(mname and maddr): continue
        name,addr,mask=mname.group(1),maddr.group(1),maddr.group(2)
        if ipaddress.ip_address(addr).is_loopback:continue
        try:
            if mask.lower().startswith("0x"):
                prefix=bin(int(mask,16)).count("1")
            else: prefix=_prefix_from_netmask(mask)
        except Exception: continue
        rec=_network_record(name,addr,prefix,default_gw if name==default_if else "",name==default_if,f"darwin:{name}")
        if rec:out.append(rec)
    return out


def detect_network_interfaces(force=False):
    now=time.time()
    if not force and NETWORK_CACHE["interfaces"] and now-NETWORK_CACHE["ts"]<NETWORK_CACHE_SECONDS:
        return json.loads(json.dumps(NETWORK_CACHE["interfaces"]))
    if os.name=="nt": found=_windows_interfaces()
    elif sys.platform=="darwin": found=_darwin_interfaces()
    else: found=_linux_interfaces()
    # Deduplicate by stable id + address while keeping all usable IPv4 NICs.
    seen=set(); out=[]
    for rec in found:
        key=(rec.get("interface_id"),rec.get("address"))
        if key in seen: continue
        seen.add(key);out.append(rec)
    out.sort(key=lambda x:(not x.get("default",False),x.get("interface","").lower(),x.get("address","")))
    NETWORK_CACHE["interfaces"],NETWORK_CACHE["ts"]=out,now
    return json.loads(json.dumps(out))


def detect_lan_network():
    interfaces=detect_network_interfaces()
    if not interfaces: return {"detected":False,"error":"No active non-loopback IPv4 network interface was detected."}
    rec=next((x for x in interfaces if x.get("default")),interfaces[0])
    return {"detected":True,**rec}


def local_lan_ip():
    d=detect_lan_network()
    return d.get("address") if d.get("detected") else "127.0.0.1"


def interface_networks(interface_ids):
    selected=set(str(x) for x in (interface_ids or []))
    return [x["cidr"] for x in detect_network_interfaces() if x.get("interface_id") in selected and x.get("cidr")]


def normalize_trusted_entry(value):
    raw=str(value or "").strip()
    if not raw: raise ValueError("Blank trusted-address entry")
    try:
        if "/" in raw: return str(ipaddress.ip_network(raw,strict=False))
        addr=ipaddress.ip_address(raw);return str(ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}",strict=False))
    except ValueError as e:
        raise ValueError(f"Invalid trusted IP/CIDR: {raw}") from e


def effective_trusted_cidrs(auth_cfg):
    values=["127.0.0.0/8","::1/128"]
    values.extend(interface_networks(auth_cfg.get("trusted_interfaces", [])))
    for item in auth_cfg.get("trusted_ips", []) or []:
        try: values.append(normalize_trusted_entry(item))
        except ValueError: pass
    # Keep deterministic order and remove duplicates.
    return list(dict.fromkeys(values))


def is_loopback_ip(ip):
    try:return ipaddress.ip_address(ip).is_loopback
    except ValueError:return False


def is_trusted_ip(ip, cidrs):
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in ipaddress.ip_network(c, strict=False) for c in cidrs)
    except ValueError:
        return False


# ---------- optional dependency management ----------

OPTIONAL_DEPENDENCIES = {
    "qr": {"label": "QR codes", "packages": ["qrcode", "Pillow"], "imports": ["qrcode", "PIL"]},
    "tray": {"label": "Windows tray", "packages": ["pystray", "Pillow"], "imports": ["pystray", "PIL"], "windows_only": True},
    "windows_service": {"label": "Windows service", "packages": ["pywin32"], "imports": ["win32serviceutil"], "windows_only": True},
    "exe_builder": {"label": "EXE builder", "packages": ["pyinstaller"], "imports": ["PyInstaller"]},
}


def dependency_status():
    out={}
    for key,spec in OPTIONAL_DEPENDENCIES.items():
        supported=not spec.get("windows_only") or os.name=="nt"
        installed=all(importlib.util.find_spec(name) is not None for name in spec["imports"])
        out_key={"windows_service":"windowsService","exe_builder":"exeBuilder"}.get(key,key)
        out[out_key]={"label":spec["label"],"installed":bool(installed),"supported":bool(supported),"packages":spec["packages"]}
    return out


def install_optional_dependency(feature):
    feature=str(feature or "").strip()
    key={"windowsService":"windows_service","exeBuilder":"exe_builder"}.get(feature,feature)
    if key=="all":
        packages=[]
        for name,spec in OPTIONAL_DEPENDENCIES.items():
            if spec.get("windows_only") and os.name!="nt": continue
            for pkg in spec["packages"]:
                if pkg not in packages: packages.append(pkg)
    elif key in OPTIONAL_DEPENDENCIES:
        spec=OPTIONAL_DEPENDENCIES[key]
        if spec.get("windows_only") and os.name!="nt": raise RuntimeError(f"{spec['label']} is available only on Windows")
        packages=list(spec["packages"])
    else:
        raise RuntimeError("Unsupported optional dependency")
    if not packages: return {"ok":True,"status":dependency_status(),"output":"Nothing to install."}
    cmd=[sys.executable,"-m","pip","install","--disable-pip-version-check",*packages]
    try:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=300,cwd=str(APP_DIR))
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Dependency installation timed out") from e
    output=(cp.stdout+"\n"+cp.stderr).strip()[-12000:]
    if cp.returncode!=0:
        raise RuntimeError(f"pip failed with exit code {cp.returncode}: {output}")
    importlib.invalidate_caches()
    return {"ok":True,"status":dependency_status(),"output":output}


# ---------- SQLite history ----------

class Store:
    def __init__(self, path):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS samples(
            ts INTEGER NOT NULL, server_id TEXT NOT NULL, dl INTEGER NOT NULL,
            up INTEGER NOT NULL, active INTEGER NOT NULL, remaining INTEGER NOT NULL,
            disk_free INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, server_id TEXT,
            torrent_hash TEXT, name TEXT, event TEXT NOT NULL, detail TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
        CREATE TABLE IF NOT EXISTS torrent_seen(
            server_id TEXT NOT NULL, torrent_hash TEXT NOT NULL, name TEXT,
            first_seen INTEGER NOT NULL, completed_at INTEGER, last_seen INTEGER NOT NULL,
            PRIMARY KEY(server_id, torrent_hash)
        );
        """)
        self.conn.commit()

    def sample(self, server_id, dl, up, active, remaining, disk_free):
        with self.lock:
            self.conn.execute("INSERT INTO samples VALUES(?,?,?,?,?,?,?)",
                              (int(time.time()), server_id, int(dl), int(up), int(active), int(remaining), disk_free))
            self.conn.commit()

    def event(self, server_id, h, name, event, detail=""):
        with self.lock:
            self.conn.execute("INSERT INTO events(ts,server_id,torrent_hash,name,event,detail) VALUES(?,?,?,?,?,?)",
                              (int(time.time()), server_id, h, name, event, detail))
            self.conn.commit()

    def update_seen(self, server_id, torrents):
        now = int(time.time())
        completed = []
        with self.lock:
            for t in torrents:
                h, name = t.get("hash"), t.get("name", "")
                if not h:
                    continue
                row = self.conn.execute("SELECT completed_at FROM torrent_seen WHERE server_id=? AND torrent_hash=?",
                                        (server_id, h)).fetchone()
                done = float(t.get("progress", 0)) >= .999999
                if row is None:
                    self.conn.execute("INSERT INTO torrent_seen VALUES(?,?,?,?,?,?)",
                                      (server_id, h, name, now, now if done else None, now))
                    if done:
                        completed.append((h, name))
                else:
                    was = row["completed_at"]
                    new_done = was or (now if done else None)
                    self.conn.execute("UPDATE torrent_seen SET name=?,last_seen=?,completed_at=? WHERE server_id=? AND torrent_hash=?",
                                      (name, now, new_done, server_id, h))
                    if done and not was:
                        completed.append((h, name))
            self.conn.commit()
        return completed

    def history(self, server_id, minutes):
        since = int(time.time()) - int(minutes) * 60
        with self.lock:
            if server_id == "all":
                rows = self.conn.execute("SELECT (ts/10)*10 ts,SUM(dl) dl,SUM(up) up,SUM(active) active,SUM(remaining) remaining,MIN(disk_free) disk_free FROM samples WHERE ts>=? GROUP BY (ts/10)*10 ORDER BY ts", (since,)).fetchall()
            else:
                rows = self.conn.execute("SELECT ts,dl,up,active,remaining,disk_free FROM samples WHERE ts>=? AND server_id=? ORDER BY ts", (since, server_id)).fetchall()
        return [dict(r) for r in rows]

    def events(self, limit=100):
        with self.lock:
            rows = self.conn.execute("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def analytics(self, server_id):
        now = int(time.time()); since = now - 7 * 86400
        where, args = "ts>=?", [since]
        if server_id != "all":
            where += " AND server_id=?"; args.append(server_id)
        with self.lock:
            r = self.conn.execute(f"SELECT AVG(dl) avg_dl,AVG(up) avg_up,MAX(dl) peak_dl,MAX(up) peak_up FROM samples WHERE {where}", args).fetchone()
            seen = self.conn.execute("SELECT COUNT(*) n,SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) c FROM torrent_seen" + (" WHERE server_id=?" if server_id != "all" else ""), ([server_id] if server_id != "all" else [])).fetchone()
        return {"avg_dl_7d": int(r["avg_dl"] or 0), "avg_up_7d": int(r["avg_up"] or 0),
                "peak_dl_7d": int(r["peak_dl"] or 0), "peak_up_7d": int(r["peak_up"] or 0),
                "known_torrents": int(seen["n"] or 0), "completed": int(seen["c"] or 0)}

    def prune(self, days):
        cutoff = int(time.time()) - max(1, int(days)) * 86400
        with self.lock:
            self.conn.execute("DELETE FROM samples WHERE ts<?", (cutoff,))
            self.conn.commit()

STORE = Store(DB_PATH)


# ---------- qBittorrent client ----------

class QBitClient:
    def __init__(self, server):
        self.server = server
        self.base = server["base_url"].rstrip("/")
        self.lock = threading.Lock()
        self.opener = None
        self.credential_signature = None
        self.auth_method = "api_key" if server.get("auth_method") == "api_key" else "password"
        self.api_key = str(server.get("api_key") or "").strip()
        self.auth_blocked = None
        self.auth_blocked_at = 0.0

    def signature(self):
        return (self.base, self.auth_method, self.server.get("username", ""), self.server.get("password", ""), self.api_key)

    def reset_auth(self):
        self.opener = None
        self.auth_blocked = None
        self.auth_blocked_at = 0.0

    def _headers(self):
        headers = [("User-Agent", f"TorrentDesk/{VERSION}")]
        if self.auth_method == "api_key":
            if not self.api_key:
                raise RuntimeError("qBittorrent API key is empty")
            headers.append(("Authorization", f"Bearer {self.api_key}"))
        else:
            headers.extend([("Referer", self.base + "/"), ("Origin", self.base)])
        return headers

    def opener_for(self):
        sig = self.signature()
        if self.opener is None or sig != self.credential_signature:
            jar = http.cookiejar.CookieJar()
            self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            self.opener.addheaders = self._headers()
            self.credential_signature = sig
        return self.opener

    def login(self):
        if self.auth_method == "api_key":
            self.opener_for()
            return
        if self.auth_blocked:
            raise RuntimeError(self.auth_blocked)
        opener = self.opener_for()
        payload = urllib.parse.urlencode({"username": self.server.get("username", ""), "password": self.server.get("password", "")}).encode()
        req = urllib.request.Request(self.base + "/api/v2/auth/login", data=payload, method="POST")
        try:
            with opener.open(req, timeout=6) as resp:
                body = resp.read().decode(errors="replace").strip()
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                self.auth_blocked = "qBittorrent login HTTP 403: this client IP is banned after too many failed Web UI logins. Stop retrying, verify the credentials, and clear/wait out the qBittorrent Web UI ban before testing again."
                self.auth_blocked_at = time.time()
                raise RuntimeError(self.auth_blocked) from exc
            raise RuntimeError(f"qBittorrent login HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach qBittorrent at {self.base}: {exc.reason}") from exc
        if body.lower() != "ok.":
            self.auth_blocked = "qBittorrent rejected the username/password. Torrent Desk will not retry these credentials until the client settings change."
            self.auth_blocked_at = time.time()
            raise RuntimeError(self.auth_blocked)

    def request(self, path, data=None, method=None, raw=False, retry=True, timeout=8):
        with self.lock:
            if self.auth_method == "password" and self.opener is None:
                self.login()
            elif self.auth_method == "api_key":
                self.opener_for()
            body = None; headers = {}
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data, doseq=True).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif data is not None:
                body = data
            req = urllib.request.Request(self.base + path, data=body, headers=headers, method=method or ("POST" if data is not None else "GET"))
            try:
                with self.opener.open(req, timeout=timeout) as resp:
                    b = resp.read()
                    if raw:
                        return b, resp.headers
                    if not b:
                        return None
                    ct = resp.headers.get("Content-Type", "")
                    if "json" in ct or b[:1] in (b"{", b"["):
                        return json.loads(b.decode())
                    return b.decode(errors="replace")
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    if self.auth_method == "password" and retry:
                        self.opener = None
                        self.login()
                        return self.request(path, data, method, raw, False, timeout)
                    if self.auth_method == "api_key":
                        raise RuntimeError(f"qBittorrent API key was rejected (HTTP {exc.code}). Verify the API key and qBittorrent 5.2+ Web API support.") from exc
                raise RuntimeError(f"qBittorrent HTTP {exc.code}: {path}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"qBittorrent connection failed: {exc.reason}") from exc

    def version(self):
        return self.request("/api/v2/app/version")

    def api_version(self):
        return self.request("/api/v2/app/webapiVersion")

    def torrents(self, **params):
        q = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        return self.request("/api/v2/torrents/info" + ("?" + q if q else "")) or []

    def transfer(self):
        return self.request("/api/v2/transfer/info") or {}

    def main_data(self, rid=0):
        return self.request(f"/api/v2/sync/maindata?rid={rid}") or {}

    def properties(self, h):
        return self.request("/api/v2/torrents/properties?" + urllib.parse.urlencode({"hash": h})) or {}

    def files(self, h):
        return self.request("/api/v2/torrents/files?" + urllib.parse.urlencode({"hash": h})) or []

    def trackers(self, h):
        return self.request("/api/v2/torrents/trackers?" + urllib.parse.urlencode({"hash": h})) or []

    def peers(self, h, rid=0):
        return self.request("/api/v2/sync/torrentPeers?" + urllib.parse.urlencode({"hash": h, "rid": rid})) or {}

    def piece_states(self, h):
        return self.request("/api/v2/torrents/pieceStates?" + urllib.parse.urlencode({"hash": h})) or []

    def post(self, path, **data):
        return self.request(path, data=data, method="POST")

CLIENTS = {}
CLIENTS_LOCK = threading.Lock()


def get_client(server):
    sid = server["id"]
    sig = (server["base_url"], server.get("auth_method","password"), server.get("username", ""), server.get("password", ""), server.get("api_key", ""))
    with CLIENTS_LOCK:
        item = CLIENTS.get(sid)
        if not item or item[0] != sig:
            item = (sig, QBitClient(server))
            CLIENTS[sid] = item
        return item[1]


# ---------- torrent state / actions ----------

WRITE_ACTIONS = {
    "pause", "resume", "delete", "recheck", "reannounce", "top", "bottom", "increase", "decrease",
    "force_start", "sequential", "first_last", "set_location", "rename", "set_category", "set_tags",
    "set_dl_limit", "set_up_limit", "file_priority", "add_magnet", "pause_all", "resume_all",
    "set_global_dl", "set_global_up", "toggle_alt_speed"
}


def hashes_value(hashes):
    if isinstance(hashes, list):
        return "|".join(hashes)
    return hashes or ""


def do_torrent_action(client, action, data):
    h = hashes_value(data.get("hashes"))
    endpoint = {
        "pause": "/api/v2/torrents/stop",
        "resume": "/api/v2/torrents/start",
        "recheck": "/api/v2/torrents/recheck",
        "reannounce": "/api/v2/torrents/reannounce",
        "top": "/api/v2/torrents/topPrio",
        "bottom": "/api/v2/torrents/bottomPrio",
        "increase": "/api/v2/torrents/increasePrio",
        "decrease": "/api/v2/torrents/decreasePrio",
    }.get(action)
    if endpoint:
        return client.post(endpoint, hashes=h)
    if action == "delete":
        return client.post("/api/v2/torrents/delete", hashes=h, deleteFiles="true" if data.get("delete_files") else "false")
    if action == "force_start":
        return client.post("/api/v2/torrents/setForceStart", hashes=h, value="true" if data.get("value", True) else "false")
    if action == "sequential":
        return client.post("/api/v2/torrents/toggleSequentialDownload", hashes=h)
    if action == "first_last":
        return client.post("/api/v2/torrents/toggleFirstLastPiecePrio", hashes=h)
    if action == "set_location":
        return client.post("/api/v2/torrents/setLocation", hashes=h, location=data.get("location", ""))
    if action == "rename":
        return client.post("/api/v2/torrents/rename", hash=h, name=data.get("name", ""))
    if action == "set_category":
        return client.post("/api/v2/torrents/setCategory", hashes=h, category=data.get("category", ""))
    if action == "set_tags":
        return client.post("/api/v2/torrents/addTags", hashes=h, tags=data.get("tags", ""))
    if action == "set_dl_limit":
        return client.post("/api/v2/torrents/setDownloadLimit", hashes=h, limit=int(data.get("limit", 0)))
    if action == "set_up_limit":
        return client.post("/api/v2/torrents/setUploadLimit", hashes=h, limit=int(data.get("limit", 0)))
    if action == "file_priority":
        return client.post("/api/v2/torrents/filePrio", hash=h, id="|".join(map(str, data.get("ids", []))), priority=int(data.get("priority", 1)))
    if action == "add_magnet":
        return client.post("/api/v2/torrents/add", urls=data.get("urls", ""), savepath=data.get("savepath", ""), category=data.get("category", ""), tags=data.get("tags", ""), stopped="true" if data.get("stopped") else "false", sequentialDownload="true" if data.get("sequential") else "false", firstLastPiecePrio="true" if data.get("first_last") else "false")
    if action == "pause_all":
        return client.post("/api/v2/torrents/stop", hashes="all")
    if action == "resume_all":
        return client.post("/api/v2/torrents/start", hashes="all")
    if action == "set_global_dl":
        return client.post("/api/v2/transfer/setDownloadLimit", limit=int(data.get("limit", 0)))
    if action == "set_global_up":
        return client.post("/api/v2/transfer/setUploadLimit", limit=int(data.get("limit", 0)))
    if action == "toggle_alt_speed":
        return client.post("/api/v2/transfer/toggleSpeedLimitsMode")
    raise RuntimeError("Unknown action")


# ---------- collector ----------

STATUS = {"servers": {}, "ts": 0, "errors": {}}
STATUS_LOCK = threading.Lock()
STOP = threading.Event()


def disk_free_for(server):
    # Local-only estimate; remote/NAS paths are intentionally reported as unknown.
    try:
        p = server.get("disk_path") or str(APP_DIR)
        return shutil.disk_usage(p).free
    except Exception:
        return None


def send_notification(cfg, title, message):
    n = cfg["notifications"]
    jobs = []
    if n.get("webhook_url"):
        jobs.append((n["webhook_url"], {"title": title, "message": message}))
    if n.get("discord_webhook"):
        jobs.append((n["discord_webhook"], {"content": f"**{title}**\n{message}"}))
    if n.get("ntfy_url"):
        try:
            req = urllib.request.Request(n["ntfy_url"], data=message.encode(), headers={"Title": title}, method="POST")
            urllib.request.urlopen(req, timeout=4).read()
        except Exception:
            pass
    if n.get("gotify_url") and n.get("gotify_token"):
        url = n["gotify_url"].rstrip("/") + "/message?token=" + urllib.parse.quote(n["gotify_token"])
        jobs.append((url, {"title": title, "message": message, "priority": 5}))
    if n.get("telegram_bot_token") and n.get("telegram_chat_id"):
        url = f"https://api.telegram.org/bot{n['telegram_bot_token']}/sendMessage"
        jobs.append((url, {"chat_id": n["telegram_chat_id"], "text": f"{title}\n{message}"}))
    for url, payload in jobs:
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=4).read()
        except Exception:
            pass
    if cfg["integrations"].get("home_assistant_webhook"):
        try:
            url = cfg["integrations"]["home_assistant_webhook"]
            data = json.dumps({"title":title,"message":message}).encode()
            urllib.request.urlopen(urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"},method="POST"),timeout=4).read()
        except Exception: pass


def collector():
    last_sample = defaultdict(float)
    last_prune = 0
    while not STOP.is_set():
        cfg = load_config()
        if not cfg.get("setup", {}).get("complete"):
            STOP.wait(1)
            continue
        refresh = max(1, int(cfg["dashboard"].get("refresh_seconds", 2)))
        current = {}; errors = {}
        for server in cfg.get("servers", []):
            if not server.get("enabled", True):
                continue
            sid = server["id"]
            try:
                c = get_client(server)
                torrents = c.torrents()
                transfer = c.transfer()
                for t in torrents:
                    t["server_id"] = sid; t["server_name"] = server.get("name", sid)
                disk = disk_free_for(server)
                current[sid] = {"server": {"id":sid,"name":server.get("name",sid)}, "torrents": torrents, "transfer": transfer, "disk_free": disk, "ok": True}
                completed = STORE.update_seen(sid, torrents)
                for h, name in completed:
                    STORE.event(sid, h, name, "completed")
                    send_notification(cfg, "Torrent completed", f"{server.get('name', sid)}: {name}")
                now = time.time()
                if now - last_sample[sid] >= max(5, int(cfg["dashboard"].get("history_sample_seconds", 10))):
                    active = sum(1 for t in torrents if t.get("progress",0)<1 and "paused" not in str(t.get("state","")).lower() and "stopped" not in str(t.get("state","")).lower())
                    remaining = sum(int(t.get("amount_left", 0) or 0) for t in torrents if t.get("progress",0)<1)
                    STORE.sample(sid, transfer.get("dl_info_speed",0), transfer.get("up_info_speed",0), active, remaining, disk)
                    last_sample[sid] = now
            except Exception as exc:
                errors[sid] = str(exc)
                current[sid] = {"server":{"id":sid,"name":server.get("name",sid)},"torrents":[],"transfer":{},"disk_free":None,"ok":False,"error":str(exc)}
        with STATUS_LOCK:
            STATUS["servers"] = current; STATUS["ts"] = time.time(); STATUS["errors"] = errors
        if time.time() - last_prune > 3600:
            STORE.prune(cfg["dashboard"].get("history_retention_days",30)); last_prune=time.time()
        STOP.wait(refresh)


# ---------- integrations ----------

def integration_request(url, api_key="", token=""):
    headers = {}
    if api_key: headers["X-Api-Key"] = api_key
    if token: headers["X-Plex-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.read(), r.headers


def integration_status(cfg):
    out = {}
    for name in ("sonarr","radarr","lidarr","prowlarr","jellyfin"):
        c = cfg["integrations"].get(name, {})
        if not c.get("url"):
            out[name] = {"configured":False}; continue
        try:
            endpoint = "/api/v3/system/status" if name in ("sonarr","radarr","lidarr") else ("/api/v1/system/status" if name=="prowlarr" else "/System/Info/Public")
            body,_ = integration_request(c["url"].rstrip("/")+endpoint,c.get("api_key",""))
            data=json.loads(body.decode()); out[name]={"configured":True,"ok":True,"version":data.get("version") or data.get("Version")}
        except Exception as e: out[name]={"configured":True,"ok":False,"error":str(e)}
    p=cfg["integrations"].get("plex",{})
    if p.get("url"):
        try:
            body,_=integration_request(p["url"].rstrip("/")+"/identity",token=p.get("token",""));out["plex"]={"configured":True,"ok":True}
        except Exception as e:out["plex"]={"configured":True,"ok":False,"error":str(e)}
    else: out["plex"]={"configured":False}
    return out


def arr_queue(cfg):
    out=[]
    for name in ("sonarr","radarr","lidarr"):
        c=cfg["integrations"].get(name,{})
        if not c.get("url"):continue
        try:
            body,_=integration_request(c["url"].rstrip("/")+"/api/v3/queue?page=1&pageSize=200",c.get("api_key","")); data=json.loads(body.decode())
            for rec in data.get("records",[]):
                if rec.get("downloadId"):
                    out.append({"integration":name,"title":rec.get("title") or rec.get("series",{}).get("title") or rec.get("movie",{}).get("title"),"status":rec.get("status"),"trackedDownloadStatus":rec.get("trackedDownloadStatus")})
        except Exception: pass
    return out


# ---------- HTTP helpers ----------

def parse_json_body(handler, max_bytes=2_000_000):
    n = int(handler.headers.get("Content-Length", "0") or 0)
    if n > max_bytes:
        raise RuntimeError("Request too large")
    return json.loads(handler.rfile.read(n).decode()) if n else {}


def multipart_parts(content_type, body):
    # Small, dependency-free multipart parser for .torrent uploads.
    m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
    if not m:
        raise RuntimeError("Missing multipart boundary")
    boundary = (m.group(1) or m.group(2)).encode()
    fields, files = {}, []
    for chunk in body.split(b"--" + boundary):
        chunk = chunk.strip(b"\r\n-")
        if not chunk or b"\r\n\r\n" not in chunk:
            continue
        head, data = chunk.split(b"\r\n\r\n", 1); data=data.rstrip(b"\r\n")
        hs = head.decode(errors="replace")
        disp = re.search(r"Content-Disposition:\s*form-data;\s*(.+)", hs, re.I)
        if not disp: continue
        header=disp.group(1)
        name=""; filename=None
        for seg in header.split(";"):
            seg=seg.strip()
            if seg.startswith("name="): name=seg.split("=",1)[1].strip('"')
            if seg.startswith("filename="): filename=seg.split("=",1)[1].strip('"')
        if filename is not None: files.append((name,filename,data))
        else: fields[name]=data.decode(errors="replace")
    return fields, files



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


def update_manifest_url(cfg):
    u = cfg.get("updates", {})
    custom = str(u.get("manifest_url") or "").strip()
    if custom:
        parsed = urllib.parse.urlparse(custom)
        if parsed.scheme != "https":
            raise RuntimeError("Update manifest URL must use HTTPS")
        return custom
    repo = str(u.get("repository") or "").strip()
    if not repo:
        return ""
    repo = normalize_github_repository(repo)
    return f"https://github.com/{repo}/releases/latest/download/update-manifest.json"


def github_update_headers(cfg, accept="application/vnd.github+json"):
    headers = {
        "User-Agent": f"TorrentDesk/{VERSION}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = str(cfg.get("updates", {}).get("github_token") or "").strip()
    if token and token != "<configured>":
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _version_key(value: str):
    # Stable semantic-version comparison without a third-party dependency.
    raw = str(value or "0").strip().lstrip("vV")
    main, sep, pre = raw.partition("-")
    nums=[]
    for part in main.split("."):
        m=re.match(r"^(\d+)",part)
        nums.append(int(m.group(1)) if m else 0)
    nums=(nums+[0,0,0,0])[:4]
    # A stable release sorts after its corresponding prerelease.
    pre_key=(1,"") if not sep else (0,pre.lower())
    return (*nums, *pre_key)


def is_newer_version(candidate: str, current: str = VERSION) -> bool:
    return _version_key(candidate) > _version_key(current)


def _urlopen_json(url: str, timeout=10, headers=None):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":f"TorrentDesk/{VERSION}","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if urllib.parse.urlparse(resp.geturl()).scheme != "https":
            raise RuntimeError("Update request redirected to a non-HTTPS URL")
        return json.loads(resp.read().decode("utf-8"))


def _urlopen_bytes(url: str, timeout=15, headers=None, max_bytes=8*1024*1024):
    req=urllib.request.Request(url,headers=headers or {"User-Agent":f"TorrentDesk/{VERSION}"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if urllib.parse.urlparse(resp.geturl()).scheme != "https":
            raise RuntimeError("Update request redirected to a non-HTTPS URL")
        data=resp.read(max_bytes+1)
        if len(data)>max_bytes:
            raise RuntimeError("Update metadata exceeds the safety limit")
        return data


def _latest_github_release(cfg, repo: str):
    url=f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        return _urlopen_json(url, timeout=10, headers=github_update_headers(cfg))
    except urllib.error.HTTPError as exc:
        token = str(cfg.get("updates", {}).get("github_token") or "").strip()
        if exc.code in (401,403):
            raise RuntimeError("GitHub rejected the update token. Verify that it has Contents: Read access to this repository.") from exc
        if exc.code == 404 and not token:
            raise RuntimeError("GitHub release not found. If this repository is private, add a GitHub Update Token with Contents: Read access.") from exc
        if exc.code == 404:
            raise RuntimeError("No GitHub release was found for the configured repository, or the token cannot access it.") from exc
        raise


def _github_release_asset_bytes(cfg, asset):
    api_url=str((asset or {}).get("url") or "")
    if not api_url.startswith("https://api.github.com/"):
        raise RuntimeError("GitHub release asset URL is invalid")
    return _urlopen_bytes(api_url, timeout=15, headers=github_update_headers(cfg,"application/octet-stream"))


def validate_update_manifest(data):
    if not isinstance(data,dict): raise RuntimeError("Update manifest is not a JSON object")
    if int(data.get("schema",0)) != 1: raise RuntimeError("Unsupported update manifest schema")
    if str(data.get("app")) != "torrentDesk": raise RuntimeError("Update manifest is for a different application")
    version=str(data.get("version") or "").strip().lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",version):
        raise RuntimeError("Update manifest version is invalid")
    asset=data.get("asset") or {}
    url=str(asset.get("url") or "").strip()
    digest=str(asset.get("sha256") or "").strip().lower()
    if urllib.parse.urlparse(url).scheme != "https": raise RuntimeError("Update package URL must use HTTPS")
    if not re.fullmatch(r"[0-9a-f]{64}",digest): raise RuntimeError("Update package SHA-256 is missing or invalid")
    return {
        "schema":1,"app":"torrentDesk","version":version,
        "channel":str(data.get("channel") or "stable"),
        "publishedAt":str(data.get("publishedAt") or ""),
        "releaseUrl":str(data.get("releaseUrl") or ""),
        "notes":data.get("notes") or "",
        "asset":{"name":str(asset.get("name") or f"Torrent-Desk-{version}.zip"),"url":url,"sha256":digest,"size":int(asset.get("size") or 0)},
        "preserve":data.get("preserve") or ["config.json","data/"]
    }


def fetch_update_manifest(cfg):
    u=cfg.get("updates",{})
    custom=str(u.get("manifest_url") or "").strip()
    repo=str(u.get("repository") or "").strip()
    token=str(u.get("github_token") or "").strip()

    if custom:
        url=update_manifest_url(cfg)
        data=validate_update_manifest(_urlopen_json(url,timeout=10))
        data["manifestUrl"]=url
    elif repo and token:
        repo=normalize_github_repository(repo)
        release=_latest_github_release(cfg,repo)
        assets=release.get("assets") or []
        manifest_asset=next((a for a in assets if a.get("name")=="update-manifest.json"),None)
        if not manifest_asset:
            raise RuntimeError("The latest GitHub release does not contain update-manifest.json")
        try:
            raw=_github_release_asset_bytes(cfg,manifest_asset)
            data=validate_update_manifest(json.loads(raw.decode("utf-8")))
        except json.JSONDecodeError as exc:
            raise RuntimeError("GitHub returned an invalid update manifest") from exc
        package_asset=next((a for a in assets if a.get("name")==data["asset"]["name"]),None)
        if not package_asset:
            raise RuntimeError(f"The latest GitHub release does not contain {data['asset']['name']}")
        data["asset"]["githubApiUrl"]=str(package_asset.get("url") or "")
        data["manifestUrl"]=str(manifest_asset.get("url") or "")
        data["releaseUrl"]=str(release.get("html_url") or data.get("releaseUrl") or "")
    else:
        url=update_manifest_url(cfg)
        if not url: raise RuntimeError("No GitHub update repository is configured")
        try:
            data=validate_update_manifest(_urlopen_json(url,timeout=10))
        except urllib.error.HTTPError as exc:
            if exc.code in (401,403,404):
                raise RuntimeError("Update manifest is not publicly accessible. If the repository is private, add a GitHub Update Token with Contents: Read access.") from exc
            raise
        data["manifestUrl"]=url

    data["currentVersion"]=VERSION
    data["updateAvailable"]=is_newer_version(data["version"])
    return data


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
        raise RuntimeError("Update ZIP does not contain a valid Torrent Desk application")
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
    headers=github_update_headers(cfg,"application/octet-stream") if manifest["asset"].get("githubApiUrl") else {"User-Agent":f"TorrentDesk/{VERSION}"}
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
                    raise RuntimeError("Downloaded update exceeds the manifest size or safety limit")
                out.write(chunk); h.update(chunk)
        got=h.hexdigest()
        if got != manifest["asset"]["sha256"]:
            package.unlink(missing_ok=True)
            raise RuntimeError("Downloaded update failed SHA-256 verification")
        if expected and total != expected:
            package.unlink(missing_ok=True)
            raise RuntimeError("Downloaded update size does not match the manifest")
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
    server_version = "TorrentDesk/3"

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
            token,sess=SESSIONS.create("LAN" if mode!="disabled" else "Guest",a.get("session_hours",24),"lan_bypass" if mode!="disabled" else "disabled")
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

    def serve_static(self, rel, content_type=None):
        p=(STATIC_DIR/rel).resolve()
        if STATIC_DIR.resolve() not in p.parents or not p.is_file():
            return self.send_json(404,{"error":"Not found"})
        ct=content_type or mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        return self.send_bytes(200,p.read_bytes(),ct)

    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path); path=parsed.path; qs=urllib.parse.parse_qs(parsed.query)
        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION})
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
                "dependencies": dependency_status(),
                "updates": {"enabled": cfg.get("updates",{}).get("enabled",True), "repository": cfg.get("updates",{}).get("repository","CynicaGaming/TorrentDashboard")},
            })
        if path=="/api/setup/dependencies":
            return self.send_json(200,{"dependencies":dependency_status()})
        if path=="/api/setup/network-interfaces":
            return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")})

        if path=="/api/me":
            cfg,token,sess,new_cookie=self.auth()
            if not sess:
                return self.send_json(401,{"authenticated":False,"auth_mode":cfg["auth"].get("mode")})
            safe={"authenticated":True,"username":sess["username"],"auth_kind":sess["auth_kind"],"csrf":sess["csrf"],"auth_mode":cfg["auth"].get("mode"),"read_only":cfg["dashboard"].get("read_only",False),"title":cfg["dashboard"].get("title"),"version":VERSION,"lan_ip":local_lan_ip(),"port":cfg["dashboard"].get("port",8765),"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http"}
            return self.send_json(200,safe,new_cookie)

        ctx=self.require_auth(False)
        if not ctx: return
        cfg,token,sess,new_cookie=ctx
        if path=="/api/status": return self.status_response(cfg,qs,new_cookie)
        if path=="/api/servers":
            safe=[{"id":s["id"],"name":s.get("name",s["id"]),"enabled":s.get("enabled",True)} for s in cfg.get("servers",[])]
            return self.send_json(200,{"servers":safe},new_cookie)
        if path=="/api/categories": return self.aggregate_meta(cfg,"categories",new_cookie)
        if path=="/api/tags": return self.aggregate_meta(cfg,"tags",new_cookie)
        if path=="/api/history": return self.send_json(200,{"points":STORE.history(qs.get("server",["all"])[0],int(qs.get("minutes",["1440"])[0]))},new_cookie)
        if path=="/api/events": return self.send_json(200,{"events":STORE.events(int(qs.get("limit",["100"])[0]))},new_cookie)
        if path=="/api/analytics": return self.send_json(200,STORE.analytics(qs.get("server",["all"])[0]),new_cookie)
        if path=="/api/integrations": return self.send_json(200,integration_status(cfg),new_cookie)
        if path=="/api/arr-queue": return self.send_json(200,{"items":arr_queue(cfg)},new_cookie)
        if path=="/api/settings": return self.send_json(200,redacted_config(cfg),new_cookie)
        if path=="/api/network/interfaces":
            return self.send_json(200,{"interfaces":detect_network_interfaces(qs.get("refresh",["0"])[0]=="1")},new_cookie)
        if path=="/api/update-check":
            return self.update_check(cfg,new_cookie)
        if path=="/api/detail":
            return self.detail(cfg,qs,new_cookie)
        if path=="/api/qr":
            return self.qr(cfg)
        return self.send_json(404,{"error":"Not found"},new_cookie)

    def do_POST(self):
        parsed=urllib.parse.urlparse(self.path); path=parsed.path
        if path.startswith("/api/setup/"):
            if path=="/api/setup/client-test": return self.setup_client_test()
            if path=="/api/setup/complete": return self.setup_complete()
            if path=="/api/setup/install-dependency": return self.setup_install_dependency()
        if path=="/api/login": return self.login()
        ctx=self.require_auth(True)
        if not ctx: return
        cfg,token,sess,new_cookie=ctx
        try:
            if path=="/api/logout":
                SESSIONS.delete(token); return self.send_json(200,{"ok":True})
            if path=="/api/action":
                return self.action(cfg,sess,new_cookie)
            if path=="/api/upload":
                return self.upload(cfg,sess,new_cookie)
            if path=="/api/settings":
                data=parse_json_body(self); new_cfg=apply_settings_update(cfg,data); save_config(new_cfg); return self.send_json(200,{"ok":True,"settings":redacted_config(new_cfg)},new_cookie)
            if path=="/api/client-test":
                data=parse_json_body(self); server=normalize_server_input(data); return self.send_json(200,test_server_connection(server),new_cookie)
            if path=="/api/test-notification":
                send_notification(cfg,"Torrent Desk test","Notification delivery test from Torrent Desk."); return self.send_json(200,{"ok":True},new_cookie)
            if path=="/api/install-dependency":
                data=parse_json_body(self,10000); return self.send_json(200,install_optional_dependency(data.get("feature")),new_cookie)
            if path=="/api/update-download":
                return self.send_json(200,stage_update(cfg),new_cookie)
            if path=="/api/update-install":
                data=parse_json_body(self,50000); return self.send_json(200,launch_update_installer(self,cfg,data.get("version")),new_cookie)
            return self.send_json(404,{"error":"Not found"},new_cookie)
        except Exception as e:
            return self.send_json(400,{"error":str(e)},new_cookie)

    def login(self):
        ip=self.client_ip();cfg=load_config(); a=cfg["auth"]
        now=time.time(); q=LOGIN_ATTEMPTS[ip]
        while q and q[0]<now-600:q.popleft()
        if len(q)>=int(a.get("max_login_attempts_per_10m",20)):
            return self.send_json(429,{"error":"Too many login attempts"})
        try:data=parse_json_body(self,10000)
        except Exception:return self.send_json(400,{"error":"Bad request"})
        q.append(now)
        if data.get("username")!=a.get("username") or not verify_password(data.get("password",""),a.get("password_hash","")):
            STORE.event(None,None,ip,"login_failed");return self.send_json(401,{"error":"Invalid credentials"})
        token,sess=SESSIONS.create(a.get("username","admin"),a.get("session_hours",24),"password")
        STORE.event(None,None,ip,"login_success")
        return self.send_json(200,{"ok":True,"csrf":sess["csrf"]},token)

    def setup_authorized(self,data):
        cfg=load_config()
        if cfg.get("setup",{}).get("complete"):
            raise RuntimeError("Setup is already complete")
        if is_loopback_ip(self.client_ip()):
            return cfg
        expected=getattr(self.server,"setup_code","")
        if not expected or not hmac.compare_digest(str(data.get("setup_code") or ""),expected):
            raise RuntimeError("Remote setup code is incorrect")
        return cfg

    def setup_client_test(self):
        try:
            data=parse_json_body(self,50000); self.setup_authorized(data); server=normalize_server_input(data.get("server") or {})
            return self.send_json(200,test_server_connection(server))
        except Exception as e:
            return self.send_json(400,{"error":str(e)})

    def setup_install_dependency(self):
        try:
            data=parse_json_body(self,10000);self.setup_authorized(data)
            return self.send_json(200,install_optional_dependency(data.get("feature")))
        except Exception as e:
            return self.send_json(400,{"error":str(e)})

    def setup_complete(self):
        try:
            data=parse_json_body(self,50000); cfg=self.setup_authorized(data)
            dashboard=data.get("dashboard") or {}; updates=data.get("updates") or {}; auth=data.get("auth") or {}; servers=data.get("servers") or []
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
                server=normalize_server_input(item)
                test_server_connection(server)  # Final verification before anything is saved.
                normalized.append(server)
            out=json.loads(json.dumps(DEFAULT_CONFIG))
            out["setup"]={"complete":True}
            out["dashboard"]["title"]=str(dashboard.get("title") or "Torrent Desk")[:128]
            out["dashboard"]["bind_host"]="0.0.0.0"
            out["dashboard"]["port"]=int(dashboard.get("port") or 8765)
            out["dashboard"]["refresh_seconds"]=max(1,min(60,int(dashboard.get("refresh_seconds") or 2)))
            out["dashboard"]["read_only"]=bool(dashboard.get("read_only",False))
            update_enabled=bool(updates.get("enabled",False))
            update_repo=str(updates.get("repository") or "").strip()
            if update_enabled and not update_repo:
                raise RuntimeError("Set the GitHub repository before enabling updates")
            out["updates"]["enabled"]=update_enabled
            out["updates"]["repository"]=normalize_github_repository(update_repo) if update_repo else ""
            token=str(updates.get("github_token") or "").strip()
            if token: out["updates"]["github_token"]=token
            out["updates"]["auto_check"]=bool(updates.get("auto_check",True))
            out["updates"]["check_hours"]=max(1,min(168,int(updates.get("check_hours") or 6)))
            out["auth"]["mode"]=mode
            out["auth"]["username"]=username
            out["auth"]["trusted_interfaces"]=trusted_interfaces
            out["auth"]["trusted_ips"]=trusted_ips
            out["auth"]["password_hash"]=hash_password(password) if password else ""
            out["servers"]=normalized
            save_config(out)
            token,sess=SESSIONS.create(username,out["auth"].get("session_hours",24),"setup")
            return self.send_json(200,{"ok":True,"csrf":sess["csrf"]},token)
        except Exception as e:
            return self.send_json(400,{"error":str(e)})

    def status_response(self,cfg,qs,cookie):
        server=qs.get("server",["all"])[0]
        with STATUS_LOCK:
            snap=json.loads(json.dumps(STATUS))
        items=[]; transfer={"dl_info_speed":0,"up_info_speed":0,"dl_info_data":0,"up_info_data":0}; disk=[]
        selected=snap["servers"].values() if server=="all" else [snap["servers"].get(server, {})]
        errors=[]
        for d in selected:
            if not d:continue
            if not d.get("ok"):errors.append(d.get("error","Connection problem"))
            items.extend(d.get("torrents",[]));tr=d.get("transfer",{})
            for k in transfer:transfer[k]+=int(tr.get(k,0) or 0)
            if d.get("disk_free") is not None:disk.append(d["disk_free"])
        counts={"all":len(items),"downloading":0,"completed":0,"paused":0}
        for t in items:
            prog=float(t.get("progress",0)); st=str(t.get("state","")).lower()
            if prog>=.999999:counts["completed"]+=1
            if "paused" in st or "stopped" in st:counts["paused"]+=1
            if prog<.999999 and not ("paused" in st or "stopped" in st):counts["downloading"]+=1
        return self.send_json(200,{"torrents":items,"transfer":transfer,"disk_free":min(disk) if disk else None,"ts":snap["ts"],"tab_counts":counts,"errors":errors,"ok":not errors},cookie)

    def aggregate_meta(self,cfg,kind,cookie):
        result=set()
        for s in cfg.get("servers",[]):
            if not s.get("enabled",True):continue
            try:
                data=get_client(s).request("/api/v2/torrents/"+kind)
                if isinstance(data,dict):result.update(data.keys())
                elif isinstance(data,list):result.update(data)
            except Exception:pass
        return self.send_json(200,{kind:sorted(result)},cookie)

    def find_server(self,cfg,sid):
        return next((s for s in cfg.get("servers",[]) if s["id"]==sid),None)

    def action(self,cfg,sess,cookie):
        data=parse_json_body(self);sid=data.get("server")
        if cfg["dashboard"].get("read_only"):
            return self.send_json(403,{"error":"Dashboard is read-only"},cookie)
        s=self.find_server(cfg,sid)
        if not s:return self.send_json(404,{"error":"Unknown server"},cookie)
        action=data.get("action")
        if action not in WRITE_ACTIONS:return self.send_json(400,{"error":"Unsupported action"},cookie)
        r=do_torrent_action(get_client(s),action,data)
        STORE.event(sid,hashes_value(data.get("hashes")),data.get("name",""),"action",action)
        return self.send_json(200,{"ok":True,"result":r},cookie)

    def upload(self,cfg,sess,cookie):
        if cfg["dashboard"].get("read_only"):return self.send_json(403,{"error":"Dashboard is read-only"},cookie)
        n=int(self.headers.get("Content-Length","0") or 0)
        if n>20*1024*1024:return self.send_json(413,{"error":"Upload too large"},cookie)
        fields,files=multipart_parts(self.headers.get("Content-Type",""),self.rfile.read(n));sid=fields.get("server")
        s=self.find_server(cfg,sid)
        if not s:return self.send_json(404,{"error":"Unknown server"},cookie)
        torrent=next((f for f in files if f[0]=="torrents"),None)
        if not torrent:return self.send_json(400,{"error":"No .torrent file"},cookie)
        # Build multipart expected by qBittorrent.
        boundary="----TorrentDesk"+secrets.token_hex(8);parts=[]
        vals={k:v for k,v in fields.items() if k!="server"}
        for k,v in vals.items():parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"torrents\"; filename=\"{torrent[1]}\"\r\nContent-Type: application/x-bittorrent\r\n\r\n".encode()+torrent[2]+b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode());body=b"".join(parts)
        c=get_client(s);req=urllib.request.Request(c.base+"/api/v2/torrents/add",data=body,headers={"Content-Type":f"multipart/form-data; boundary={boundary}"},method="POST")
        with c.lock:
            if c.auth_method == "password" and c.opener is None: c.login()
            else: c.opener_for()
            with c.opener.open(req,timeout=15) as r:r.read()
        STORE.event(sid,None,torrent[1],"added_file")
        return self.send_json(200,{"ok":True},cookie)

    def detail(self,cfg,qs,cookie):
        sid=qs.get("server",[""])[0];h=qs.get("hash",[""])[0];tab=qs.get("tab",["overview"])[0]
        s=self.find_server(cfg,sid)
        if not s:return self.send_json(404,{"error":"Unknown server"},cookie)
        c=get_client(s)
        try:
            if tab=="overview":data=c.properties(h)
            elif tab=="files":data=c.files(h)
            elif tab=="trackers":data=c.trackers(h)
            elif tab=="peers":data=c.peers(h)
            elif tab=="pieces":data=c.piece_states(h)
            else:return self.send_json(400,{"error":"Bad detail tab"},cookie)
            return self.send_json(200,{"tab":tab,"data":data},cookie)
        except Exception as e:return self.send_json(502,{"error":str(e)},cookie)

    def qr(self,cfg):
        try:
            import io, qrcode
            scheme="https" if cfg["dashboard"].get("https_enabled") else "http"
            url=f"{scheme}://{local_lan_ip()}:{cfg['dashboard'].get('port',8765)}"
            img=qrcode.make(url); buf=io.BytesIO(); img.save(buf,format="PNG")
            return self.send_bytes(200,buf.getvalue(),"image/png")
        except Exception as e:
            return self.send_json(501,{"error":f"QR support unavailable: {e}"})

    def update_check(self,cfg,new_cookie):
        updates=cfg.get("updates",{})
        if not updates.get("enabled"):
            return self.send_json(200,{"configured":False,"enabled":False,"currentVersion":VERSION,"state":update_state()},new_cookie)
        try:
            manifest=fetch_update_manifest(cfg)
            return self.send_json(200,{"configured":True,"enabled":True,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)
        except Exception as e:
            return self.send_json(502,{"configured":True,"enabled":True,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)


def redacted_config(cfg):
    out=json.loads(json.dumps(cfg))
    out["auth"]["password_hash"]="" if not cfg["auth"].get("password_hash") else "<configured>"
    if out.get("updates",{}).get("github_token"): out["updates"]["github_token"]="<configured>"
    for s in out.get("servers",[]):
        if s.get("password"): s["password"]="<configured>"
        if s.get("api_key"): s["api_key"]="<configured>"
    ints=out.get("integrations",{})
    for k,v in ints.items():
        if isinstance(v,dict):
            for secret in ("api_key","token"):
                if v.get(secret): v[secret]="<configured>"
    n=out.get("notifications",{})
    for secret in ("gotify_token","telegram_bot_token"):
        if n.get(secret): n[secret]="<configured>"
    out["runtime"]={
        "detected_lan": detect_lan_network(),
        "network_interfaces": detect_network_interfaces(),
        "trusted_interface_networks": interface_networks(cfg.get("auth",{}).get("trusted_interfaces",[])),
        "effective_trusted_cidrs": effective_trusted_cidrs(cfg.get("auth",{})),
        "dependencies": dependency_status(),
        "updateState": update_state(),
    }
    return out


def apply_settings_update(cfg,data):
    # Browser settings are intentionally allowlisted and preserve redacted secrets unless new values are supplied.
    out=json.loads(json.dumps(cfg))
    dash=data.get("dashboard",{})
    for k in ("title","refresh_seconds","history_retention_days","history_sample_seconds","low_disk_gb","read_only","update_manifest_url","https_enabled","https_cert","https_key"):
        if k in dash: out["dashboard"][k]=dash[k]
    updates=data.get("updates",{})
    if "enabled" in updates: out["updates"]["enabled"]=bool(updates.get("enabled"))
    if "repository" in updates:
        repo=str(updates.get("repository") or "").strip()
        out["updates"]["repository"]=normalize_github_repository(repo) if repo else ""
    if "github_token" in updates:
        token=str(updates.get("github_token") or "")
        if token and token != "<configured>": out["updates"]["github_token"]=token.strip()
    if "manifest_url" in updates:
        manifest_url=str(updates.get("manifest_url") or "").strip()
        if manifest_url and urllib.parse.urlparse(manifest_url).scheme!="https": raise RuntimeError("Update manifest URL must use HTTPS")
        out["updates"]["manifest_url"]=manifest_url
    if "auto_check" in updates: out["updates"]["auto_check"]=bool(updates.get("auto_check"))
    if "check_hours" in updates: out["updates"]["check_hours"]=max(1,min(168,int(updates.get("check_hours") or 6)))
    if out["updates"].get("enabled") and not out["updates"].get("repository") and not out["updates"].get("manifest_url"):
        raise RuntimeError("Set a GitHub repository or custom HTTPS manifest URL before enabling updates")
    auth=data.get("auth",{})
    if auth.get("new_password"): out["auth"]["password_hash"]=hash_password(str(auth["new_password"]))
    if "mode" in auth:
        if auth["mode"] not in ("required","lan_bypass","disabled"): raise RuntimeError("Invalid auth mode")
        if auth["mode"] in ("required","lan_bypass") and not (out["auth"].get("password_hash") or auth.get("new_password")):
            raise RuntimeError("Set a dashboard password before enabling password-protected access")
        out["auth"]["mode"]=auth["mode"]
    if "username" in auth: out["auth"]["username"]=str(auth["username"])[:128]
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
            item=normalize_server_input({**s,"id":sid},prev)
            new.append(item)
        out["servers"]=new
    if "notifications" in data:
        for k,v in data["notifications"].items():
            if k in out["notifications"] and v!="<configured>": out["notifications"][k]=v
    if "integrations" in data:
        for name,v in data["integrations"].items():
            if name=="home_assistant_webhook": out["integrations"][name]=v; continue
            if name not in out["integrations"] or not isinstance(v,dict): continue
            for k,val in v.items():
                if k in out["integrations"][name] and val!="<configured>": out["integrations"][name][k]=val
    return out


def set_password_cli(password):
    cfg=load_config(); cfg["auth"]["password_hash"]=hash_password(password); save_config(cfg)
    print("Dashboard password updated.")


def main():
    parser=argparse.ArgumentParser(description="Torrent Desk")
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--set-password",action="store_true")
    parser.add_argument("--password")
    args=parser.parse_args()
    if args.set_password:
        if not args.password: raise SystemExit("--password is required")
        set_password_cli(args.password);return
    cfg=load_config();
    host=cfg["dashboard"].get("bind_host","0.0.0.0");port=int(cfg["dashboard"].get("port",8765))
    server=ThreadingHTTPServer((host,port),Handler)
    if not cfg.get("setup",{}).get("complete"):
        server.setup_code=secrets.token_hex(3).upper()
        print("\nFirst-run setup is not complete.")
        print(f"Local setup: http://127.0.0.1:{port}")
        print(f"Remote setup code: {server.setup_code}\n")
    threading.Thread(target=collector,daemon=True).start()
    if cfg["dashboard"].get("open_browser",True) and not args.no_browser:
        threading.Timer(.7,lambda:webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"Torrent Desk {VERSION}")
    print(f"Listening on {host}:{port}")
    ctx=None
    if cfg["dashboard"].get("https_enabled"):
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cfg["dashboard"]["https_cert"],cfg["dashboard"]["https_key"]);server.socket=ctx.wrap_socket(server.socket,server_side=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:STOP.set();server.server_close()

if __name__=="__main__":main()
