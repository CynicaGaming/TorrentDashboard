#!/usr/bin/env python3
"""Apply the v0.5.64 configuration/integrations modularization increment."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_OLD = "0.5.63"
VERSION_NEW = "0.5.64"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


INTEGRATIONS_MODULE = '''"""Integration provider definitions, normalization, redaction, and CRUD operations."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid


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


def integration_catalog():
    """Return browser-safe provider metadata used to build integration forms."""
    out = []
    for provider, spec in INTEGRATION_TYPES.items():
        fields = []
        for field in spec.get("fields", []):
            fields.append({
                key: value
                for key, value in field.items()
                if key in ("key", "label", "placeholder", "secret", "required", "input_type")
            })
        out.append({"type": provider, "label": spec["label"], "fields": fields})
    return out


def normalize_integration(data, existing=None):
    """Normalize one integration while preserving already-stored secret fields."""
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
    """Return integrations with secret field values replaced by a configured marker."""
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
    """Perform the existing provider-specific connection test for one normalized integration."""
    item = normalize_integration(item, item)
    provider = item["type"]
    spec = INTEGRATION_TYPES[provider]
    label = spec["label"]
    try:
        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):
            req = urllib.request.Request(
                item["url"].rstrip("/") + "/api/v3/system/status",
                headers={"X-Api-Key": item["api_key"], "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read(200000).decode("utf-8"))
            version = str(data.get("version") or "").strip()
        elif provider == "jellyfin":
            req = urllib.request.Request(
                item["url"].rstrip("/") + "/System/Info",
                headers={"X-Emby-Token": item["api_key"], "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read(200000).decode("utf-8"))
            version = str(data.get("Version") or data.get("ProductVersion") or "").strip()
        elif provider == "plex":
            req = urllib.request.Request(
                item["url"].rstrip("/") + "/identity",
                headers={"X-Plex-Token": item["token"]},
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "discord":
            body = json.dumps({"content": "Torrent Dashboard integration connection test"}).encode("utf-8")
            req = urllib.request.Request(
                item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "ntfy":
            headers = {"Title": "Torrent Dashboard Test"}
            if item.get("access_token"):
                headers["Authorization"] = f"Bearer {item['access_token']}"
            req = urllib.request.Request(
                item["topic_url"], data=b"Integration connection test", headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "generic_webhook":
            body = json.dumps({"title": "Torrent Dashboard Test", "message": "Integration connection test"}).encode("utf-8")
            req = urllib.request.Request(
                item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                resp.read(200000)
            version = ""
        elif provider == "home_assistant":
            body = json.dumps({"title": "Torrent Dashboard Test", "message": "Integration connection test"}).encode("utf-8")
            req = urllib.request.Request(
                item["webhook_url"], data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
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
    """Return a copied configuration with one integration inserted or replaced."""
    out = json.loads(json.dumps(cfg))
    integrations = out.setdefault("integrations", [])
    item_id = str(data.get("id") or "")
    existing = next(
        (item for item in integrations if str(item.get("id") or "") == item_id),
        None,
    ) if item_id else None
    item = normalize_integration(data, existing)
    if existing:
        integrations[integrations.index(existing)] = item
    else:
        integrations.append(item)
    return out, item


def delete_integration(cfg, integration_id):
    """Return a copied configuration with the requested integration removed."""
    integration_id = str(integration_id or "")
    if not integration_id:
        raise RuntimeError("Integration ID is required")
    out = json.loads(json.dumps(cfg))
    before = len(out.get("integrations", []))
    out["integrations"] = [
        item
        for item in out.get("integrations", [])
        if str(item.get("id") or "") != integration_id
    ]
    if len(out["integrations"]) == before:
        raise RuntimeError("Integration was not found")
    return out


__all__ = [
    "INTEGRATION_TYPES",
    "delete_integration",
    "integration_catalog",
    "normalize_integration",
    "redacted_integrations",
    "save_integration",
    "test_integration_connection",
]
'''


CONFIG_MODULE = '''"""Configuration schema, migration, browser sanitization, and atomic file persistence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

from .integrations import INTEGRATION_TYPES, normalize_integration, redacted_integrations
from .users import normalize_user, public_user, sync_legacy_auth


DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"

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
        "https_key": "",
    },
    "updates": {"repository": DEFAULT_UPDATE_REPOSITORY},
    "auth": {
        "mode": "lan_bypass",
        "trusted_interfaces": [],
        "trusted_ips": [],
        "session_hours": 24,
        "max_login_attempts_per_10m": 20,
    },
    "users": [],
    "servers": [],
    "notifications": {
        "browser": True,
        "sound": False,
        "sound_mode": "default",
        "custom_sound_file": "",
        "custom_sound_name": "",
        "custom_sound_mime": "",
    },
    "integrations": [],
}


def deep_merge(base, override):
    """Recursively merge JSON-style dictionaries using override values."""
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def stable_record_id(kind, *parts):
    """Create the deterministic short IDs used by legacy migration paths."""
    raw = kind + ":" + ":".join(str(value or "") for value in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def normalize_github_repository(value: str) -> str:
    """Normalize the public update repository to GitHub's owner/repository form."""
    value = str(value or "").strip().removesuffix(".git").strip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):].strip("/")
            break
    parts = value.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part or "") for part in parts):
        raise RuntimeError("GitHub repository must be owner/repo or a github.com repository URL")
    return "/".join(parts)


def _migrate_network_auth(raw, detect_lan_network: Callable[[], dict] | None) -> None:
    auth_raw = raw.setdefault("auth", {})
    legacy_cidrs = list(auth_raw.get("trusted_cidrs", []) or [])
    if "trusted_ips" not in auth_raw:
        auth_raw["trusted_ips"] = [
            cidr for cidr in legacy_cidrs if cidr not in ("127.0.0.0/8", "::1/128")
        ]
    if "trusted_interfaces" not in auth_raw:
        auth_raw["trusted_interfaces"] = []
        if auth_raw.get("auto_trust_lan", False) and detect_lan_network is not None:
            try:
                default = detect_lan_network()
                interface = default.get("interface_id") or default.get("interface")
                if interface:
                    auth_raw["trusted_interfaces"] = [interface]
            except Exception:
                pass


def _migrate_users(raw, merged) -> None:
    raw_users = raw.get("users")
    if isinstance(raw_users, list) and raw_users:
        merged["users"] = [
            normalize_user(item, item)
            for item in raw_users
            if isinstance(item, dict)
        ]
        return

    legacy_auth = raw.get("auth", {}) if isinstance(raw.get("auth"), dict) else {}
    legacy_hash = str(legacy_auth.get("password_hash") or "")
    if not legacy_hash:
        merged["users"] = []
        return
    username = str(legacy_auth.get("username") or "admin")[:128]
    merged["users"] = [
        normalize_user(
            {
                "id": stable_record_id("user", username),
                "username": username,
                "password_hash": legacy_hash,
                "group": "administrator",
            },
            require_password=True,
        )
    ]


def _migrate_integrations(raw, merged) -> str:
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
            payload = {
                "id": stable_record_id("integration", provider, value.get("url")),
                "type": provider,
                "name": INTEGRATION_TYPES[provider]["label"],
                **value,
            }
            try:
                migrated.append(normalize_integration(payload, payload))
            except Exception:
                continue
        webhook = str(raw_integrations.get("home_assistant_webhook") or "").strip()
        if webhook:
            payload = {
                "id": stable_record_id("integration", "home_assistant", webhook),
                "type": "home_assistant",
                "name": "Home Assistant",
                "webhook_url": webhook,
            }
            try:
                migrated.append(normalize_integration(payload, payload))
            except Exception:
                pass
        merged["integrations"] = migrated
    else:
        merged["integrations"] = []
    return legacy_github_repo


def _migrate_notification_destinations(raw, merged) -> None:
    legacy_notifications = raw.get("notifications", {}) if isinstance(raw.get("notifications"), dict) else {}
    legacy_destinations = [
        ("generic_webhook", "webhook_url", str(legacy_notifications.get("webhook_url") or "").strip()),
        ("discord", "webhook_url", str(legacy_notifications.get("discord_webhook") or "").strip()),
        ("ntfy", "topic_url", str(legacy_notifications.get("ntfy_url") or "").strip()),
    ]
    for provider, field, value in legacy_destinations:
        if not value:
            continue
        if any(
            item.get("type") == provider and item.get(field) == value
            for item in merged.get("integrations", [])
        ):
            continue
        payload = {
            "id": stable_record_id("integration", provider, value),
            "type": provider,
            "name": INTEGRATION_TYPES[provider]["label"],
            field: value,
            "enabled": True,
        }
        try:
            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))
        except Exception:
            pass
    for legacy_key in ("webhook_url", "discord_webhook", "ntfy_url"):
        merged.setdefault("notifications", {}).pop(legacy_key, None)


def normalize_config(raw, detect_lan_network: Callable[[], dict] | None = None):
    """Normalize one parsed configuration and apply all supported legacy migrations."""
    if not isinstance(raw, dict):
        raise RuntimeError("Configuration root must be a JSON object")
    raw = json.loads(json.dumps(raw))

    if "setup" not in raw:
        raw["setup"] = {"complete": True}

    _migrate_network_auth(raw, detect_lan_network)
    merged = deep_merge(DEFAULT_CONFIG, raw)
    merged.setdefault("dashboard", {}).pop("refresh_seconds", None)
    merged.setdefault("dashboard", {}).pop("read_only", None)

    _migrate_users(raw, merged)
    legacy_github_repo = _migrate_integrations(raw, merged)
    _migrate_notification_destinations(raw, merged)

    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}
    update_repo = str(
        legacy_updates.get("repository")
        or legacy_github_repo
        or DEFAULT_UPDATE_REPOSITORY
    ).strip()
    try:
        update_repo = normalize_github_repository(update_repo)
    except Exception:
        update_repo = DEFAULT_UPDATE_REPOSITORY
    merged["updates"] = {"repository": update_repo}
    merged["integrations"] = [
        item for item in merged.get("integrations", []) if item.get("type") != "github"
    ]

    sync_legacy_auth(merged)
    return merged


def public_config(cfg):
    """Return the configuration subset safe to expose to authenticated browsers."""
    out = json.loads(json.dumps(cfg))
    out.setdefault("auth", {}).pop("password_hash", None)
    out.setdefault("auth", {}).pop("username", None)
    for server in out.get("servers", []):
        if server.get("password"):
            server["password"] = "<configured>"
        if server.get("api_key"):
            server["api_key"] = "<configured>"
    out["users"] = [public_user(user) for user in cfg.get("users", [])]
    out["integrations"] = redacted_integrations(cfg)
    notifications = out.get("notifications", {})
    for secret in ("gotify_token", "telegram_bot_token"):
        if notifications.get(secret):
            notifications[secret] = "<configured>"
    return out


class ConfigRepository:
    """Own config.json loading, migration, sanitization-on-save, and atomic persistence."""

    def __init__(self, path: Path | str, detect_lan_network: Callable[[], dict] | None = None):
        self.path = Path(path)
        self._detect_lan_network = detect_lan_network

    def load(self):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return normalize_config(raw, self._detect_lan_network)

    def save(self, cfg):
        clean = json.loads(json.dumps(cfg))
        clean["integrations"] = [
            item for item in clean.get("integrations", []) if item.get("type") != "github"
        ]
        updates = clean.setdefault("updates", {})
        updates["repository"] = normalize_github_repository(
            updates.get("repository") or DEFAULT_UPDATE_REPOSITORY
        )
        updates.pop("github_token", None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)


__all__ = [
    "ConfigRepository",
    "DEFAULT_CONFIG",
    "DEFAULT_UPDATE_REPOSITORY",
    "deep_merge",
    "normalize_config",
    "normalize_github_repository",
    "public_config",
    "stable_record_id",
]
'''


TEST_CONFIG = '''from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from torrent_dashboard.config import (
    ConfigRepository,
    DEFAULT_CONFIG,
    normalize_config,
    public_config,
)


class ConfigModuleTests(unittest.TestCase):
    def test_repository_creates_and_loads_default_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            repo = ConfigRepository(path)
            loaded = repo.load()
            self.assertTrue(path.is_file())
            self.assertFalse(loaded["setup"]["complete"])
            self.assertEqual(loaded["updates"]["repository"], "CynicaGaming/TorrentDashboard")

    def test_existing_config_migrates_setup_and_legacy_network_fields(self):
        raw = {
            "auth": {
                "trusted_cidrs": ["127.0.0.0/8", "192.168.50.0/24"],
                "auto_trust_lan": True,
            }
        }
        cfg = normalize_config(
            raw,
            lambda: {"interface_id": "eth-test", "interface": "Ethernet"},
        )
        self.assertTrue(cfg["setup"]["complete"])
        self.assertEqual(cfg["auth"]["trusted_ips"], ["192.168.50.0/24"])
        self.assertEqual(cfg["auth"]["trusted_interfaces"], ["eth-test"])

    def test_legacy_auth_integrations_notifications_and_update_source_migrate(self):
        raw = {
            "auth": {"username": "legacy-admin", "password_hash": "legacy-hash"},
            "integrations": [
                {
                    "type": "github",
                    "repository": "https://github.com/example/fork.git",
                },
                {
                    "type": "sonarr",
                    "name": "Sonarr",
                    "url": "http://sonarr:8989/",
                    "api_key": "abc123",
                },
            ],
            "notifications": {
                "discord_webhook": "https://discord.com/api/webhooks/1/test",
            },
        }
        cfg = normalize_config(raw)
        self.assertEqual(len(cfg["users"]), 1)
        self.assertEqual(cfg["users"][0]["username"], "legacy-admin")
        self.assertEqual(cfg["users"][0]["group"], "administrator")
        self.assertEqual(cfg["updates"]["repository"], "example/fork")
        self.assertEqual({item["type"] for item in cfg["integrations"]}, {"sonarr", "discord"})
        self.assertNotIn("discord_webhook", cfg["notifications"])

    def test_repository_save_removes_retired_github_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            repo = ConfigRepository(path)
            cfg = json.loads(json.dumps(DEFAULT_CONFIG))
            cfg["updates"] = {
                "repository": "https://github.com/example/fork.git",
                "github_token": "should-not-persist",
            }
            cfg["integrations"] = [
                {"type": "github", "repository": "example/old"},
            ]
            repo.save(cfg)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["updates"], {"repository": "example/fork"})
            self.assertEqual(saved["integrations"], [])

    def test_public_config_redacts_browser_secrets(self):
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        cfg["auth"].update({"username": "admin", "password_hash": "hash"})
        cfg["servers"] = [{"password": "secret", "api_key": "qbt_secret"}]
        cfg["integrations"] = [{
            "id": "one",
            "type": "sonarr",
            "name": "Sonarr",
            "enabled": True,
            "url": "http://sonarr:8989",
            "api_key": "secret",
        }]
        cfg["notifications"]["gotify_token"] = "secret"
        public = public_config(cfg)
        self.assertNotIn("username", public["auth"])
        self.assertNotIn("password_hash", public["auth"])
        self.assertEqual(public["servers"][0]["password"], "<configured>")
        self.assertEqual(public["servers"][0]["api_key"], "<configured>")
        self.assertEqual(public["integrations"][0]["api_key"], "<configured>")
        self.assertEqual(public["integrations"][0]["configured_secrets"], ["api_key"])
        self.assertEqual(public["notifications"]["gotify_token"], "<configured>")


if __name__ == "__main__":
    unittest.main()
'''


TEST_INTEGRATIONS = '''from __future__ import annotations

import unittest

from torrent_dashboard.integrations import (
    delete_integration,
    integration_catalog,
    normalize_integration,
    save_integration,
)


class IntegrationModuleTests(unittest.TestCase):
    def test_normalize_preserves_existing_secret_when_blank(self):
        existing = {
            "id": "sonarr-1",
            "type": "sonarr",
            "name": "Sonarr",
            "enabled": True,
            "url": "http://sonarr:8989",
            "api_key": "stored-key",
        }
        item = normalize_integration(
            {"id": "sonarr-1", "type": "sonarr", "url": "http://sonarr:8989/", "api_key": ""},
            existing,
        )
        self.assertEqual(item["api_key"], "stored-key")
        self.assertEqual(item["url"], "http://sonarr:8989")

    def test_normalize_rejects_invalid_provider_url(self):
        with self.assertRaisesRegex(RuntimeError, "must start with http"):
            normalize_integration({"type": "sonarr", "url": "sonarr:8989", "api_key": "abc"})

    def test_save_and_delete_round_trip(self):
        cfg = {"integrations": []}
        updated, item = save_integration(
            cfg,
            {"type": "ntfy", "name": "Alerts", "topic_url": "https://ntfy.sh/example"},
        )
        self.assertEqual(len(updated["integrations"]), 1)
        removed = delete_integration(updated, item["id"])
        self.assertEqual(removed["integrations"], [])
        self.assertEqual(cfg["integrations"], [])

    def test_catalog_exposes_provider_form_metadata(self):
        catalog = {item["type"]: item for item in integration_catalog()}
        self.assertIn("sonarr", catalog)
        api_key = next(field for field in catalog["sonarr"]["fields"] if field["key"] == "api_key")
        self.assertTrue(api_key["secret"])
        self.assertTrue(api_key["required"])


if __name__ == "__main__":
    unittest.main()
'''


# Create the extracted modules and behavioral coverage first.
write("torrent_dashboard/integrations.py", INTEGRATIONS_MODULE)
write("torrent_dashboard/config.py", CONFIG_MODULE)
write("tests/test_config.py", TEST_CONFIG)
write("tests/test_integrations.py", TEST_INTEGRATIONS)

# Turn dashboard.py into the composition root for the extracted domains.
dashboard = read("dashboard.py")
dashboard = replace_once(
    dashboard,
    "from torrent_dashboard.config_store import ConfigStore\nfrom torrent_dashboard.users import (",
    '''from torrent_dashboard.config import (
    ConfigRepository,
    DEFAULT_CONFIG,
    DEFAULT_UPDATE_REPOSITORY,
    deep_merge,
    normalize_github_repository,
    public_config,
    stable_record_id,
)
from torrent_dashboard.config_store import ConfigStore
from torrent_dashboard.integrations import (
    INTEGRATION_TYPES,
    delete_integration,
    integration_catalog,
    normalize_integration,
    redacted_integrations,
    save_integration,
    test_integration_connection,
)
from torrent_dashboard.users import (''',
    "dashboard module imports",
)
dashboard = replace_once(
    dashboard,
    'VERSION = "0.5.63"',
    'VERSION = "0.5.64"',
    "dashboard version",
)
dashboard = replace_once(
    dashboard,
    'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\n',
    "",
    "dashboard update repository constant",
)

config_start = dashboard.index("DEFAULT_CONFIG = {")
config_end = dashboard.index("class SessionStore:", config_start)
config_composition = '''CONFIG_REPOSITORY = ConfigRepository(
    CONFIG_PATH,
    detect_lan_network=lambda: detect_lan_network(),
)
CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)


def load_config():
    return CONFIG_STORE.load()


def mutate_config(transform):
    return CONFIG_STORE.mutate(transform)


'''
dashboard = dashboard[:config_start] + config_composition + dashboard[config_end:]

integration_start = dashboard.index("INTEGRATION_TYPES = {")
integration_end = dashboard.index("def normalize_qbittorrent_server", integration_start)
dashboard = dashboard[:integration_start] + dashboard[integration_end:]

github_normalizer_start = dashboard.index("def normalize_github_repository(value: str) -> str:")
github_normalizer_end = dashboard.index("def github_headers", github_normalizer_start)
dashboard = dashboard[:github_normalizer_start] + dashboard[github_normalizer_end:]

redact_start = dashboard.index("def redacted_config(cfg):")
redact_end = dashboard.index("def apply_settings_update", redact_start)
redact_wrapper = '''def redacted_config(cfg):
    out = public_config(cfg)
    out["runtime"] = {
        "detected_lan": detect_lan_network(),
        "local_ip": local_lan_ip(),
        "network_interfaces": detect_network_interfaces(),
        "trusted_interface_networks": interface_networks(cfg.get("auth", {}).get("trusted_interfaces", [])),
        "effective_trusted_cidrs": effective_trusted_cidrs(cfg.get("auth", {})),
        "updateState": update_state(),
        "releaseHistory": local_release_history(),
    }
    return out


'''
dashboard = dashboard[:redact_start] + redact_wrapper + dashboard[redact_end:]

for forbidden in (
    "def _load_config_unlocked",
    "def _save_config_unlocked",
    "def normalize_integration",
    "def redacted_integrations",
    "def normalize_github_repository",
    "INTEGRATION_TYPES = {",
):
    if forbidden in dashboard:
        raise RuntimeError(f"dashboard extraction left forbidden source: {forbidden}")
write("dashboard.py", dashboard)

# Keep the reusable architecture validator aligned with the new dependency boundaries.
validator = read("release_tools/validate_source.py")
validator = replace_once(
    validator,
    '''    if "from torrent_dashboard.users import" not in source:
        fail("dashboard.py must consume the extracted users module")
    if "from torrent_dashboard.config_store import ConfigStore" not in source:
        fail("dashboard.py must use ConfigStore for configuration coordination")
''',
    '''    if "from torrent_dashboard.users import" not in source:
        fail("dashboard.py must consume the extracted users module")
    if "from torrent_dashboard.config import" not in source:
        fail("dashboard.py must consume the extracted configuration module")
    if "from torrent_dashboard.integrations import" not in source:
        fail("dashboard.py must consume the extracted integrations module")
    if "from torrent_dashboard.config_store import ConfigStore" not in source:
        fail("dashboard.py must use ConfigStore for configuration coordination")

    forbidden_ownership = (
        "def _load_config_unlocked",
        "def _save_config_unlocked",
        "def normalize_integration",
        "def redacted_integrations",
        "def normalize_github_repository",
        "INTEGRATION_TYPES = {",
    )
    leftovers = [marker for marker in forbidden_ownership if marker in source]
    if leftovers:
        fail("dashboard.py still owns extracted configuration/integration behavior: " + ", ".join(leftovers))
    if "CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)" not in source:
        fail("dashboard.py must coordinate ConfigRepository through ConfigStore")
''',
    "source validator dashboard contract",
)
write("release_tools/validate_source.py", validator)

# Keep the long-running UI regression validator aware of source ownership moves.
ui_validator = read("release_tools/validate_ui_strings.py")
ui_validator = replace_once(
    ui_validator,
    '''    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")
''',
    '''    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    config_py = (ROOT / "torrent_dashboard" / "config.py").read_text(encoding="utf-8")
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    integrations_py = (ROOT / "torrent_dashboard" / "integrations.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")
''',
    "UI validator module sources",
)
ui_validator = replace_once(
    ui_validator,
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in dashboard_py\n',
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in config_py\n',
    "UI validator update repository owner",
)
ui_validator = replace_once(
    ui_validator,
    '''    # 0.5.56 serializes all configuration read/modify/write mutations.
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(_load_config_unlocked, _save_config_unlocked)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
''',
    '''    # 0.5.56 serializes all configuration read/modify/write mutations; 0.5.64
    # moves schema/migration/persistence ownership behind ConfigRepository.
    assert 'from torrent_dashboard.config import (' in dashboard_py
    assert 'from torrent_dashboard.integrations import (' in dashboard_py
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigRepository:' in config_py and 'def normalize_config(' in config_py
    assert 'INTEGRATION_TYPES = {' in integrations_py and 'def normalize_integration(' in integrations_py
    assert 'def _load_config_unlocked' not in dashboard_py and 'INTEGRATION_TYPES = {' not in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
''',
    "UI validator config transaction section",
)
write("release_tools/validate_ui_strings.py", ui_validator)

# Synchronize the browser build generation with the backend version.
for path in ("static/index.html", "static/app.js", "static/sw.js"):
    content = read(path)
    if VERSION_OLD not in content:
        raise RuntimeError(f"{path}: expected {VERSION_OLD} build marker")
    content = content.replace(VERSION_OLD, VERSION_NEW)
    if path == "static/sw.js":
        content = replace_once(content, "torrent-dashboard-v0563", "torrent-dashboard-v0564", "service-worker cache")
    write(path, content)

# Update durable architecture guidance now that the planned boundary exists.
architecture = read("ARCHITECTURE.md")
architecture = replace_once(
    architecture,
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, integrations, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted.",
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted. Configuration and integration domains are imported from package modules rather than implemented here.",
    "architecture dashboard ownership",
)
architecture = replace_once(
    architecture,
    '''### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration, applies one transformation, persists it, and releases the lock only after the write completes.

Configuration schema normalization and migration are still in `dashboard.py` and are the next backend extraction target.
''',
    '''### `torrent_dashboard/config.py`

Owns configuration defaults, legacy migrations, update-repository normalization, browser-safe configuration redaction, and atomic `config.json` persistence through `ConfigRepository`. The only runtime-specific migration dependency is LAN detection, which is injected by the composition root as a callback.

### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration through `ConfigRepository`, applies one transformation, persists it, and releases the lock only after the write completes.

### `torrent_dashboard/integrations.py`

Owns the integration provider catalog, field validation and normalization, configured-secret redaction, connection tests, and integration CRUD transforms. Provider definitions no longer live in the HTTP adapter.
''',
    "architecture package ownership",
)
architecture = replace_once(
    architecture,
    '''The next useful boundaries are:

1. **Configuration** — schema defaults, migrations, normalization, sanitization, and persistence.
2. **Release/update metadata** — GitHub release parsing, installed provenance, and integrity-history persistence.
3. **qBitTorrent client/domain operations** — isolate Web API transport and normalization from HTTP routes.
4. **Integrations/notifications** — separate provider normalization and delivery health from request handling.
5. **Frontend feature modules** — reduce the responsibility of `static/app.js` after backend boundaries stabilize.
''',
    '''The next useful boundaries are:

1. **Release/update metadata** — GitHub release parsing, installed provenance, and integrity-history persistence.
2. **qBitTorrent client/domain operations** — isolate Web API transport, server normalization, and preference translation from HTTP routes.
3. **Request/application services** — move setup and settings transformations behind testable service functions so HTTP handlers remain adapters.
4. **Notification delivery** — separate delivery dispatch from provider configuration now that integration definitions are isolated.
5. **Frontend feature modules** — reduce the responsibility of `static/app.js` after backend boundaries stabilize.
''',
    "architecture extraction roadmap",
)
write("ARCHITECTURE.md", architecture)

# Add a concise module map to the contributor documentation.
readme = read("README.md")
readme = replace_once(
    readme,
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md).\n",
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules currently isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.\n",
    "README module map",
)
write("README.md", readme)

# Make package-content assertions cover the newly extracted modules in both publication paths.
for path in (".github/workflows/publish-refactor-prerelease.yml", ".github/workflows/release.yml"):
    workflow = read(path)
    marker = "          assert any(n.endswith('/torrent_dashboard/config_store.py') for n in names)\n"
    if marker not in workflow:
        raise RuntimeError(f"{path}: package module assertion marker missing")
    workflow = workflow.replace(
        marker,
        marker
        + "          assert any(n.endswith('/torrent_dashboard/config.py') for n in names)\n"
        + "          assert any(n.endswith('/torrent_dashboard/integrations.py') for n in names)\n",
        1,
    )
    write(path, workflow)

# Record the increment in the structured release source of truth.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == VERSION_NEW for item in release_data.get("releases", [])):
    raise RuntimeError(f"release metadata for {VERSION_NEW} already exists")
release_data["releases"].append({
    "version": VERSION_NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Configuration and integrations module extraction",
    "summary": "Moves configuration lifecycle and integration-provider ownership out of dashboard.py into dedicated package modules while preserving the existing HTTP and updater behavior.",
    "highlights": [
        "Added torrent_dashboard/config.py for configuration defaults, legacy migrations, update-repository normalization, browser-safe redaction, and atomic config.json persistence.",
        "Added torrent_dashboard/integrations.py for provider definitions, normalization, secret redaction, connection tests, and integration CRUD transforms.",
        "dashboard.py now composes ConfigRepository through ConfigStore and imports both extracted domains instead of implementing them inline.",
        "The historical dashboard helper names remain available through imports so the refactor does not intentionally change internal call sites or downstream behavior."
    ],
    "fixes": [],
    "technical": [
        "ConfigRepository receives LAN detection as an injected callback for the legacy auto-trust migration, preserving the rule that package modules never import dashboard.py.",
        "ConfigStore remains the serialized read/modify/write transaction coordinator; ConfigRepository owns file parsing, migrations, normalization, and atomic persistence.",
        "Browser-facing configuration sanitization now has a pure package boundary, while dashboard.py only adds runtime network/update state.",
        "Release package assertions now require the configuration and integrations modules in both development and main publication workflows."
    ],
    "validation": [
        "Added configuration tests covering default-file creation, legacy setup/network migration, legacy users/integrations/update-source migration, save-time retired-field cleanup, and browser secret redaction.",
        "Added integration tests covering configured-secret preservation, URL validation, immutable CRUD transforms, and provider catalog metadata.",
        "Reusable source validation now rejects configuration or integration ownership drifting back into dashboard.py and continues enforcing package dependency direction.",
        "Existing UI regression, frontend build-generation, release metadata, and configuration concurrency checks remain in the publication pipeline."
    ],
    "known_issues": [
        "dashboard.py and static/app.js remain larger than the intended steady-state architecture; release/update metadata and qBitTorrent transport are the next high-value backend extraction boundaries.",
        "ConfigStore still coordinates only the running process; simultaneous edits by an external config.json editor are not cross-process locked."
    ],
    "architecture": [
        "dashboard.py is the composition root and HTTP adapter; configuration schema/persistence and integration definitions are no longer implemented there.",
        "User and account domain logic lives in torrent_dashboard/users.py.",
        "Configuration defaults, migrations, browser sanitization, repository normalization, and atomic file persistence live in torrent_dashboard/config.py.",
        "Configuration transaction coordination remains in torrent_dashboard/config_store.py.",
        "Integration provider definitions, normalization, redaction, connection tests, and CRUD transforms live in torrent_dashboard/integrations.py.",
        "Runtime LAN detection is injected into ConfigRepository instead of reversing the dependency direction back to dashboard.py.",
        "Release/update provenance is still implemented in dashboard.py and is the next planned backend extraction.",
        "Reusable source validation lives in release_tools/validate_source.py and enforces the package-to-composition-root dependency boundary."
    ],
    "decisions": [
        "Continue modularization in behavior-preserving increments rather than combining refactors with unrelated feature changes.",
        "Treat dashboard.py as the composition root; modules under torrent_dashboard must not import dashboard.py.",
        "Keep ConfigStore focused on transaction coordination and ConfigRepository focused on configuration file lifecycle.",
        "Inject runtime-only dependencies such as LAN detection into package modules rather than importing the HTTP/process adapter.",
        "Keep integration provider configuration separate from notification delivery so those responsibilities can evolve independently.",
        "Preserve the existing dashboard-level imported call surface during extraction to minimize refactor blast radius."
    ],
    "next_steps": [
        {
            "priority": 1,
            "title": "Extract release and update provenance",
            "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py behind a cohesive package module."
        },
        {
            "priority": 2,
            "title": "Extract qBitTorrent transport and normalization",
            "detail": "Move QBitClient, qBitTorrent server normalization, proxy/preference translation, and Web API transport away from HTTP routing while keeping the route contract unchanged."
        },
        {
            "priority": 3,
            "title": "Expand request-level behavioral tests",
            "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around the extracted service boundaries."
        },
        {
            "priority": 4,
            "title": "Harden secrets at rest",
            "detail": "Use the new configuration ownership boundary to add restrictive filesystem permissions and a cleaner separation between ordinary configuration and stored credentials."
        }
    ]
})
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

# Regenerate derived release/handoff documents from the authoritative metadata.
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_NEW],
    cwd=ROOT,
    check=True,
)

print("Applied v0.5.64 configuration/integrations modularization")
