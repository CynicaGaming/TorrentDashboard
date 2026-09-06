#!/usr/bin/env python3
"""Cross-file regression checks for Torrent Dashboard release checkpoints."""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
EXPECTED_DEFAULT_SOUND_BYTES = 40_704
EXPECTED_DEFAULT_SOUND_SHA256 = "5be19a030c39e9fef9084d247e1bda23cb947e9e430abfc2e97376e04ff868b3"
DEFAULT_SOUND_PARTS = (
    "notification-default.b64.01",
    "notification-default.b64.01.tail",
    "notification-default.b64.02",
    "notification-default.b64.02.tail",
    "notification-default.b64.03",
    "notification-default.b64.04",
    "notification-default.b64.05",
    "notification-default.b64.06",
    "notification-default.b64.07",
    "notification-default.b64.08",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Checkpoint validation failed: {message}")


def capture(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.M)
    require(bool(match), f"could not determine {label}")
    return match.group(1)


def main() -> None:
    dashboard = read(ROOT / "dashboard.py")
    app_js = read(STATIC / "app.js")
    index_html = read(STATIC / "index.html")
    sw = read(STATIC / "sw.js")
    feature_js = read(STATIC / "integration-notifications.js")
    feature_css = read(STATIC / "integration-notifications.css")
    sound_patch = read(STATIC / "default-notification-sound.js")

    version = capture(r'^VERSION\s*=\s*["\']([^"\']+)["\']', dashboard, "dashboard version")
    frontend_version = capture(r"const FRONTEND_BUILD=['\"]([^'\"]+)['\"]", app_js, "frontend version")
    html_version = capture(r'<meta\s+content="([^"]+)"\s+name="torrent-dashboard-build"', index_html, "HTML build version")
    require(version == frontend_version == html_version, "dashboard, app.js, and index.html versions differ")

    for asset in ("app.css", "settings.css", "settings.js", "app.js"):
        require(f"/static/{asset}?v={version}" in index_html, f"index.html is missing versioned {asset}")
    require(f"?v={version}" in sw, "service worker asset references do not match the application version")

    for path in (
        STATIC / "integration-notifications.js",
        STATIC / "integration-notifications.css",
        STATIC / "default-notification-sound.js",
    ):
        require(path.exists(), f"missing feature asset {path.relative_to(ROOT)}")

    require("integration-notifications.css" in sw, "service worker does not load integration notification styles")
    require("integration-notifications.js" in sw, "service worker does not load integration notification logic")
    require("default-notification-sound.js" in sw, "service worker does not load the default sound compatibility shim")
    require("notification-default.mp3" in sw, "service worker does not expose the default MP3")
    require("Accept-Ranges" not in sw, "service worker advertises byte ranges without range-response support")
    require("safeNotificationUrl" in sw, "notification click URLs are not constrained to the dashboard origin")

    require("TDSettings.saveCore" not in feature_js, "notification controls can persist unrelated unsaved settings")
    require("post('/api/settings', {notifications:" in feature_js, "notification controls do not use a partial settings update")
    require("observe(document.body" not in feature_js, "integration observer is scoped to the full live dashboard DOM")
    require("#integrationList" in feature_js, "integration health logic is not scoped to the integration list")
    require(all(value in feature_js for value in ("connected", "warning", "disconnected")), "integration health states are incomplete")
    require(all(value in feature_css for value in ("#22c55e", "#eab308", "#ef4444")), "integration health colors are incomplete")
    require("background web push" in feature_js.lower(), "notification UI does not explain the current Web Push boundary")

    require("/static/default-completion.wav" in sound_patch, "default sound shim no longer recognizes the legacy sound path")
    require("/static/notification-default.mp3" in sound_patch, "default sound shim no longer maps to the requested MP3")

    parts = [STATIC / name for name in DEFAULT_SOUND_PARTS]
    for part in parts:
        require(part.exists(), f"missing default notification sound source fragment {part.name}")
        require(part.name in sw, f"service worker does not reference default notification sound fragment {part.name}")
    try:
        payload = "".join(read(part).strip() for part in parts)
        sound = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise SystemExit(f"Checkpoint validation failed: default notification sound could not be decoded: {exc}") from exc
    require(len(sound) == EXPECTED_DEFAULT_SOUND_BYTES, f"default notification sound is {len(sound)} bytes, expected {EXPECTED_DEFAULT_SOUND_BYTES}")
    require(sound.startswith(b"ID3") or (len(sound) > 1 and sound[0] == 0xFF and (sound[1] & 0xE0) == 0xE0), "decoded default notification sound is not an MP3")
    digest = hashlib.sha256(sound).hexdigest()
    require(digest == EXPECTED_DEFAULT_SOUND_SHA256, f"default notification sound SHA-256 changed: {digest}")

    for path in (ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "docs" / "ARCHITECTURE.md", ROOT / "docs" / "NOTIFICATIONS.md"):
        require(path.exists(), f"missing repository documentation {path.relative_to(ROOT)}")

    print(f"Checkpoint validation passed for Torrent Dashboard {version}; default notification sound SHA-256 {digest}")


if __name__ == "__main__":
    main()
