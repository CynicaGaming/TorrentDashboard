#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.129"
NEW_VERSION = "0.5.130"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old!r}; found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


settings_js = ROOT / "static" / "settings.js"
text = settings_js.read_text(encoding="utf-8")
old_paths = "const paths={chevron:'M9.29 6.71a.996.996 0 0 0 0 1.41L13.17 12l-3.88 3.88a.996.996 0 1 0 1.41 1.41l4.59-4.59a.996.996 0 0 0 0-1.41L10.7 6.7a.996.996 0 0 0-1.41.01Z',play:'M8 5v14l11-7z',stop:'M6 6h12v12H6z',schedule:'M11.99 2C6.48 2 2 6.48 2 12s4.48 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2Zm.01 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7Z'};"
new_paths = "const paths={chevron:'M9.29 6.71a.996.996 0 0 0 0 1.41L13.17 12l-3.88 3.88a.996.996 0 1 0 1.41 1.41l4.59-4.59a.996.996 0 0 0 0-1.41L10.7 6.7a.996.996 0 0 0-1.41.01Z',play:'M8 5v14l11-7z',stop:'M6 6h12v12H6z',schedule:'M11.99 2C6.48 2 2 6.48 2 12s4.48 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2Zm.01 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7Z',refresh:'M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.09 0-7.19 3.72-6.39 7.69L3.5 9.58 2.09 11 6 14.91 9.91 11 8.5 9.58 7.54 10.54A4.5 4.5 0 1 1 8.17 15l-1.42 1.42A6.5 6.5 0 1 0 19.5 12h-2a4.48 4.48 0 0 1-.85 2.62l1.45 1.45A6.46 6.46 0 0 0 19.5 12c0-2.21-.9-4.2-2.35-5.65Z'};"
if text.count(old_paths) != 1:
    raise RuntimeError("Could not find Jellyfin icon path map")
text = text.replace(old_paths, new_paths, 1)

old_markup = "return `<section class=\"integration-service jellyfin-service\" data-jellyfin-service><div class=\"integration-service-head\"><div class=\"integration-service-heading\"><span class=\"eyebrow\">Jellyfin server</span><div class=\"jellyfin-server-line\"><span class=\"service-status-badge checking\" data-jellyfin-status>Checking…</span><strong data-jellyfin-name>Jellyfin</strong></div><small data-jellyfin-meta>Loading server status…</small></div><button class=\"secondary jellyfin-reload\" type=\"button\">Reload status</button></div><div class=\"jellyfin-library-head\"><div><strong>Libraries</strong><small data-jellyfin-library-count>Loading…</small></div><button class=\"secondary jellyfin-refresh-libraries\" type=\"button\">Refresh libraries</button></div>"
new_markup = "return `<section class=\"integration-service jellyfin-service\" data-jellyfin-service><div class=\"integration-service-head\"><div class=\"integration-service-heading\"><span class=\"eyebrow\">Jellyfin server</span><div class=\"jellyfin-server-line\"><span class=\"service-status-badge checking\" data-jellyfin-status>Checking…</span><strong data-jellyfin-name>Jellyfin</strong><button class=\"jellyfin-inline-refresh jellyfin-reload\" type=\"button\" aria-label=\"Refresh Jellyfin status\" title=\"Refresh Jellyfin status\">${jellyfinTaskIcon('refresh')}</button></div><small data-jellyfin-meta>Loading server status…</small></div></div><div class=\"jellyfin-library-head\"><div><span class=\"jellyfin-library-title\"><strong>Libraries</strong><button class=\"jellyfin-inline-refresh jellyfin-refresh-libraries\" type=\"button\" aria-label=\"Refresh Jellyfin libraries\" title=\"Refresh Jellyfin libraries\">${jellyfinTaskIcon('refresh')}</button></span><small data-jellyfin-library-count>Loading…</small></div></div>"
if text.count(old_markup) != 1:
    raise RuntimeError("Could not find Jellyfin service markup")
text = text.replace(old_markup, new_markup, 1)

old_load = "runtime.dataset.loading='1';const status=card.querySelector('[data-jellyfin-status]');if(status){status.className='service-status-badge checking';status.textContent='Checking…'}"
new_load = "runtime.dataset.loading='1';const reload=card.querySelector('.jellyfin-reload');if(reload)reload.disabled=true;const status=card.querySelector('[data-jellyfin-status]');if(status){status.className='service-status-badge checking';status.textContent='Checking…'}"
if text.count(old_load) != 1:
    raise RuntimeError("Could not find Jellyfin status loading block")
text = text.replace(old_load, new_load, 1)
old_finally = "finally{delete runtime.dataset.loading}"
new_finally = "finally{delete runtime.dataset.loading;if(reload)reload.disabled=false}"
if text.count(old_finally) != 1:
    raise RuntimeError("Could not find Jellyfin status finally block")
text = text.replace(old_finally, new_finally, 1)
settings_js.write_text(text, encoding="utf-8")

settings_css = ROOT / "static" / "settings.css"
css = settings_css.read_text(encoding="utf-8")
addition = r'''

/* 0.5.130 Jellyfin inline refresh controls. */
.jellyfin-server-line,.jellyfin-library-title{display:flex;align-items:center;gap:8px;min-width:0}
.jellyfin-library-title{gap:6px}
.jellyfin-inline-refresh{display:inline-grid;place-items:center;flex:0 0 30px;width:30px;height:30px;min-width:30px;padding:0;border:0;border-radius:8px;background:transparent;color:var(--muted)}
.jellyfin-inline-refresh:hover,.jellyfin-inline-refresh:focus-visible{background:var(--panel3);color:var(--accent);outline:none}
.jellyfin-inline-refresh:focus-visible{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 14%,transparent)}
.jellyfin-inline-refresh:disabled{opacity:.55;cursor:wait}
.jellyfin-inline-refresh .material-symbol-icon{width:19px;height:19px;fill:currentColor}
.jellyfin-inline-refresh:disabled .material-symbol-icon{animation:jellyfin-refresh-spin .8s linear infinite}
@keyframes jellyfin-refresh-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.jellyfin-inline-refresh:disabled .material-symbol-icon{animation:none}}
@media(max-width:700px){.jellyfin-inline-refresh{flex-basis:34px;width:34px;height:34px;min-width:34px}.jellyfin-inline-refresh .material-symbol-icon{width:20px;height:20px}}
'''
if "0.5.130 Jellyfin inline refresh controls" in css:
    raise RuntimeError("Jellyfin refresh CSS already applied")
settings_css.write_text(css.rstrip() + addition + "\n", encoding="utf-8")

# Keep version and frontend cache contracts synchronized.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text, count = re.subn(r'^(VERSION\s*=\s*["\'])0\.5\.129(["\'])', rf'\g<1>{NEW_VERSION}\2', text, count=1, flags=re.M)
if count != 1:
    raise RuntimeError("Could not update dashboard VERSION")
dashboard.write_text(text, encoding="utf-8")

app = ROOT / "static" / "app.js"
replace_once(app, f"const FRONTEND_BUILD='{OLD_VERSION}';", f"const FRONTEND_BUILD='{NEW_VERSION}';")

index = ROOT / "static" / "index.html"
text = index.read_text(encoding="utf-8")
if OLD_VERSION not in text:
    raise RuntimeError("Expected old version in index.html")
index.write_text(text.replace(OLD_VERSION, NEW_VERSION), encoding="utf-8")

sw = ROOT / "static" / "sw.js"
text = sw.read_text(encoding="utf-8")
if "torrent-dashboard-v05129" not in text or OLD_VERSION not in text:
    raise RuntimeError("Expected old service-worker version")
text = text.replace("torrent-dashboard-v05129", "torrent-dashboard-v05130", 1).replace(OLD_VERSION, NEW_VERSION)
sw.write_text(text, encoding="utf-8")

source = ROOT / "release_notes" / "releases.json"
data = json.loads(source.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in data.get("releases", [])):
    raise RuntimeError(f"Release metadata for {NEW_VERSION} already exists")
data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-07",
    "status": "prerelease",
    "title": "Jellyfin inline refresh controls",
    "summary": "Replaces the Jellyfin status and library refresh text buttons with compact Material refresh icons positioned directly beside the information they refresh.",
    "highlights": [
        "Adds a Material refresh icon beside the Jellyfin connection status.",
        "Adds a Material refresh icon beside the Libraries heading.",
        "Preserves the existing status reload and library refresh actions with accessible labels and tooltips."
    ],
    "fixes": [
        "Reduces visual weight in the Jellyfin integration by removing redundant refresh button text."
    ],
    "technical": [
        "Refresh controls disable while their request is active and show a rotating refresh glyph when motion is allowed."
    ],
    "validation": [
        "Source validation, unit tests, UI-string validation, JavaScript syntax checks, and release-note checks run before publication."
    ],
    "known_issues": [],
    "architecture": [],
    "decisions": [],
    "next_steps": []
})
source.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW_VERSION], cwd=ROOT, check=True)
print(f"Applied Jellyfin refresh icon update for v{NEW_VERSION}")
