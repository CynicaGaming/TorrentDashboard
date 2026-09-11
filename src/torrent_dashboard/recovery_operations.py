"""Out-of-band diagnostics and safe service operations for local Recovery.exe."""
from __future__ import annotations

import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from torrent_dashboard import __version__
from torrent_dashboard.config import public_config
from torrent_dashboard.history import HistoryStore
from torrent_dashboard.integrations import redacted_integrations, test_integration_connection
from torrent_dashboard.jellyfin import (
    find_jellyfin_integration,
    jellyfin_scheduled_tasks,
    start_jellyfin_scheduled_task,
    stop_jellyfin_scheduled_task,
)
from torrent_dashboard.users import public_user


SAFE_TORRENT_ACTIONS = frozenset({"start", "stop", "recheck", "reannounce"})


def _download_client(cfg: dict, client_id: str) -> dict:
    client_id = str(client_id or "").strip()
    item = next(
        (entry for entry in cfg.get("servers", []) if str(entry.get("id") or "") == client_id),
        None,
    )
    if not item:
        raise RuntimeError("Download client was not found")
    return item


def _integration(cfg: dict, integration_id: str) -> dict:
    integration_id = str(integration_id or "").strip()
    item = next(
        (entry for entry in cfg.get("integrations", []) if str(entry.get("id") or "") == integration_id),
        None,
    )
    if not item:
        raise RuntimeError("Integration was not found")
    return item


class RecoveryQBitClient:
    """Minimal qBittorrent transport used only by the local recovery process."""

    def __init__(self, server: dict):
        self.server = server
        self.base = str(server.get("base_url") or "").rstrip("/")
        if not self.base.startswith(("http://", "https://")):
            raise RuntimeError("qBittorrent URL must start with http:// or https://")
        self.opener = None

    def _make_opener(self):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [
            ("User-Agent", f"TorrentDashboard-Recovery/{__version__}"),
            ("Referer", self.base + "/"),
            ("Origin", self.base),
        ]
        if self.server.get("auth_method") == "api_key":
            opener.addheaders.append(("Authorization", "Bearer " + str(self.server.get("api_key") or "")))
        return opener

    def login(self) -> None:
        opener = self._make_opener()
        if self.server.get("auth_method") == "api_key":
            if not self.server.get("api_key"):
                raise RuntimeError("qBittorrent API key is missing")
            self.opener = opener
            return

        username = str(self.server.get("username") or "")
        password = str(self.server.get("password") or "")
        if not username or not password:
            raise RuntimeError("qBittorrent username/password is incomplete")
        data = urllib.parse.urlencode({"username": username, "password": password}).encode()
        request = urllib.request.Request(self.base + "/api/v2/auth/login", data=data, method="POST")
        try:
            with opener.open(request, timeout=7) as response:
                body = response.read().decode(errors="replace").strip()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace").strip() if exc.fp else ""
            if exc.code == 403:
                raise RuntimeError(
                    "qBittorrent rejected or banned this recovery client (HTTP 403). "
                    "Verify the Web UI credentials and qBittorrent IP-ban state before retrying."
                ) from exc
            raise RuntimeError(f"qBittorrent login HTTP {exc.code}: {detail or 'login failed'}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach qBittorrent at {self.base}: {exc.reason}") from exc
        if body.lower() != "ok.":
            raise RuntimeError(
                "qBittorrent rejected the username/password. Verify the configured credentials before retrying."
            )
        self.opener = opener

    def _request(self, method: str, path: str, form: dict | None = None, *, expect_json: bool = False):
        if self.opener is None:
            self.login()
        data = None
        headers = {}
        if form is not None:
            data = urllib.parse.urlencode(form, doseq=True).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=12) as response:
                body = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            if exc.code in (401, 403) and self.server.get("auth_method") == "api_key":
                raise RuntimeError(
                    f"qBittorrent rejected the API key (HTTP {exc.code}). Verify or rotate the Web UI API key."
                ) from exc
            raise RuntimeError(f"qBittorrent HTTP {exc.code}: {detail or path}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"qBittorrent connection error: {exc.reason}") from exc
        if expect_json:
            if not body:
                return None
            import json

            return json.loads(body.decode("utf-8"))
        return status, body

    def get_json(self, path: str):
        return self._request("GET", path, expect_json=True)

    def get_text(self, path: str) -> str:
        _, body = self._request("GET", path)
        return body.decode(errors="replace").strip()

    def post(self, path: str, form: dict | None = None):
        return self._request("POST", path, form=form or {})

    def torrents(self) -> list[dict]:
        value = self.get_json("/api/v2/torrents/info") or []
        if not isinstance(value, list):
            raise RuntimeError("qBittorrent returned an invalid torrent list")
        return value

    def action(self, action: str, target: str):
        action = str(action or "").strip().lower()
        if action not in SAFE_TORRENT_ACTIONS:
            raise RuntimeError("Recovery torrent actions are limited to start, stop, recheck, and reannounce")
        target = str(target or "").strip()
        if target != "all" and not (len(target) in (40, 64) and re.fullmatch(r"[0-9A-Fa-f]+", target)):
            raise RuntimeError("Torrent target must be all or a 40/64-character hexadecimal hash")
        endpoint = {
            "start": "start",
            "stop": "stop",
            "recheck": "recheck",
            "reannounce": "reannounce",
        }[action]
        try:
            return self.post(f"/api/v2/torrents/{endpoint}", {"hashes": target})
        except RuntimeError as exc:
            if action in ("start", "stop") and "HTTP 404" in str(exc):
                legacy = "resume" if action == "start" else "pause"
                return self.post(f"/api/v2/torrents/{legacy}", {"hashes": target})
            raise


def redacted_configuration(cfg: dict) -> dict:
    return public_config(cfg)


def list_clients(cfg: dict) -> list[dict]:
    return [
        {
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or item.get("id") or "qBittorrent"),
            "enabled": bool(item.get("enabled", True)),
            "base_url": str(item.get("base_url") or ""),
            "auth_method": str(item.get("auth_method") or "password"),
        }
        for item in cfg.get("servers", [])
    ]


def test_client(cfg: dict, client_id: str) -> dict:
    server = _download_client(cfg, client_id)
    client = RecoveryQBitClient(server)
    client.login()
    return {
        "ok": True,
        "id": str(server.get("id") or ""),
        "name": str(server.get("name") or "qBittorrent"),
        "base_url": str(server.get("base_url") or ""),
        "version": client.get_text("/api/v2/app/version"),
        "api_version": client.get_text("/api/v2/app/webapiVersion"),
    }


def list_torrents(cfg: dict, client_id: str | None = None) -> list[dict]:
    servers = [_download_client(cfg, client_id)] if client_id else list(cfg.get("servers", []))
    rows = []
    for server in servers:
        sid = str(server.get("id") or "")
        client = RecoveryQBitClient(server)
        for torrent in client.torrents():
            try:
                progress = max(0.0, min(100.0, float(torrent.get("progress", 0) or 0) * 100.0))
            except (TypeError, ValueError):
                progress = 0.0
            rows.append(
                {
                    "client_id": sid,
                    "hash": str(torrent.get("hash") or ""),
                    "state": " ".join(str(torrent.get("state") or "unknown").split()) or "unknown",
                    "progress": progress,
                    "name": " ".join(str(torrent.get("name") or "Unnamed torrent").split()) or "Unnamed torrent",
                }
            )
    return rows


def torrent_action(cfg: dict, client_id: str, action: str, target: str) -> dict:
    server = _download_client(cfg, client_id)
    status, _ = RecoveryQBitClient(server).action(action, target)
    return {
        "ok": True,
        "client_id": str(server.get("id") or ""),
        "action": str(action).lower(),
        "target": str(target),
        "status": int(status),
    }


def list_integrations(cfg: dict) -> list[dict]:
    return redacted_integrations(cfg)


def test_integration(cfg: dict, integration_id: str) -> dict:
    return test_integration_connection(_integration(cfg, integration_id))


def list_jellyfin_tasks(cfg: dict, integration_id: str) -> list[dict]:
    return jellyfin_scheduled_tasks(find_jellyfin_integration(cfg, integration_id))


def jellyfin_task_action(cfg: dict, integration_id: str, action: str, task_id: str) -> dict:
    item = find_jellyfin_integration(cfg, integration_id)
    action = str(action or "").lower()
    if action == "start":
        return start_jellyfin_scheduled_task(item, task_id)
    if action == "stop":
        return stop_jellyfin_scheduled_task(item, task_id)
    raise RuntimeError("Jellyfin recovery action must be start or stop")


def list_users(cfg: dict) -> list[dict]:
    return [public_user(user) for user in cfg.get("users", [])]


def history_events(path: Path | str, limit: int = 50) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    return HistoryStore(path).events(max(1, min(200, int(limit))))


__all__ = [
    "SAFE_TORRENT_ACTIONS",
    "RecoveryQBitClient",
    "history_events",
    "jellyfin_task_action",
    "list_clients",
    "list_integrations",
    "list_jellyfin_tasks",
    "list_torrents",
    "list_users",
    "redacted_configuration",
    "test_client",
    "test_integration",
    "torrent_action",
]
