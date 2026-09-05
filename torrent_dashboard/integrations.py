"""Integration provider definitions, normalization, redaction, and CRUD operations."""

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
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
        ],
    },
    "radarr": {
        "label": "Radarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:7878", "required": True},
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
        ],
    },
    "lidarr": {
        "label": "Lidarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:8686", "required": True},
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
        ],
    },
    "prowlarr": {
        "label": "Prowlarr",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:9696", "required": True},
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
        ],
    },
    "jellyfin": {
        "label": "Jellyfin",
        "fields": [
            {"key": "url", "label": "URL", "placeholder": "http://host:8096", "required": True},
            {"key": "api_key", "label": "API key", "secret": True, "required": True},
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
            {"key": "access_token", "label": "Access token", "secret": True, "required": False},
        ],
    },
    "generic_webhook": {
        "label": "Generic webhook",
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
    """Perform the provider-specific connection test for one normalized integration."""
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
