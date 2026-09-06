"""Jellyfin service-integration runtime for status, libraries, and explicit refresh actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

MAX_JELLYFIN_RESPONSE_BYTES = 2_000_000
DEFAULT_JELLYFIN_TIMEOUT = 7


def find_jellyfin_integration(cfg, integration_id):
    """Return one saved Jellyfin integration without exposing any secret fields."""
    integration_id = str(integration_id or "").strip()
    if not integration_id:
        raise RuntimeError("Jellyfin integration ID is required")
    item = next(
        (
            entry
            for entry in cfg.get("integrations", [])
            if str(entry.get("id") or "") == integration_id
        ),
        None,
    )
    if not item:
        raise RuntimeError("Jellyfin integration was not found")
    if str(item.get("type") or "").lower() != "jellyfin":
        raise RuntimeError("Integration is not a Jellyfin connection")
    return item


def _jellyfin_connection(item):
    if str(item.get("type") or "").lower() != "jellyfin":
        raise RuntimeError("Integration is not a Jellyfin connection")
    url = str(item.get("url") or "").strip().rstrip("/")
    api_key = str(item.get("api_key") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Jellyfin URL must start with http:// or https://")
    if not api_key:
        raise RuntimeError("Jellyfin API key is required")
    return url, api_key


def _jellyfin_request(item, endpoint, *, method="GET", expect_json=True, opener=None, timeout=DEFAULT_JELLYFIN_TIMEOUT):
    url, api_key = _jellyfin_connection(item)
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(
        url + endpoint,
        headers={
            "X-Emby-Token": api_key,
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read(MAX_JELLYFIN_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Jellyfin returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to Jellyfin: {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not connect to Jellyfin: {exc}") from exc
    if len(body) > MAX_JELLYFIN_RESPONSE_BYTES:
        raise RuntimeError("Jellyfin returned an unexpectedly large response")
    if not expect_json:
        return None
    try:
        return json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Jellyfin returned an invalid response") from exc


def jellyfin_server_info(item, *, opener=None):
    """Return a browser-safe summary of the connected Jellyfin server."""
    data = _jellyfin_request(item, "/System/Info", opener=opener)
    if not isinstance(data, dict):
        raise RuntimeError("Jellyfin returned an invalid system response")
    return {
        "name": str(data.get("ServerName") or item.get("name") or "Jellyfin").strip(),
        "version": str(data.get("Version") or data.get("ProductVersion") or "").strip(),
        "operating_system": str(data.get("OperatingSystem") or "").strip(),
        "pending_restart": bool(data.get("HasPendingRestart", False)),
    }


def jellyfin_libraries(item, *, opener=None):
    """Return normalized Jellyfin virtual-folder/library information."""
    data = _jellyfin_request(item, "/Library/VirtualFolders", opener=opener)
    if not isinstance(data, list):
        raise RuntimeError("Jellyfin returned an invalid library response")
    libraries = []
    for source in data:
        if not isinstance(source, dict):
            continue
        raw_progress = source.get("RefreshProgress")
        try:
            progress = float(raw_progress) if raw_progress is not None else None
        except (TypeError, ValueError):
            progress = None
        if progress is not None:
            progress = max(0.0, min(100.0, progress))
        locations = [
            str(value).strip()
            for value in (source.get("Locations") or [])
            if str(value).strip()
        ]
        libraries.append({
            "id": str(source.get("ItemId") or "").strip(),
            "name": str(source.get("Name") or "Library").strip(),
            "collection_type": str(source.get("CollectionType") or "").strip(),
            "locations": locations,
            "refresh_status": str(source.get("RefreshStatus") or "").strip(),
            "refresh_progress": progress,
        })
    libraries.sort(key=lambda item: item["name"].lower())
    return libraries


def jellyfin_overview(item, *, opener=None):
    """Return server health metadata and configured libraries for Settings."""
    return {
        "ok": True,
        "server": jellyfin_server_info(item, opener=opener),
        "libraries": jellyfin_libraries(item, opener=opener),
    }


def refresh_jellyfin_libraries(item, *, opener=None):
    """Request Jellyfin's normal global library scan."""
    _jellyfin_request(item, "/Library/Refresh", method="POST", expect_json=False, opener=opener)
    return {"ok": True, "message": "Jellyfin library refresh requested"}


__all__ = [
    "find_jellyfin_integration",
    "jellyfin_libraries",
    "jellyfin_overview",
    "jellyfin_server_info",
    "refresh_jellyfin_libraries",
]
