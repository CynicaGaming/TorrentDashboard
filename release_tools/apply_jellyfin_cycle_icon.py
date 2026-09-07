#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.130"
NEW_VERSION = "0.5.131"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old!r}; found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


settings_js = ROOT / "static" / "settings.js"
text = settings_js.read_text(encoding="utf-8")
old_icon = "refresh:'M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.09 0-7.19 3.72-6.39 7.69L3.5 9.58 2.09 11 6 14.91 9.91 11 8.5 9.58 7.54 10.54A4.5 4.5 0 1 1 8.17 15l-1.42 1.42A6.5 6.5 0 1 0 19.5 12h-2a4.48 4.48 0 0 1-.85 2.62l1.45 1.45A6.46 6.46 0 0 0 19.5 12c0-2.21-.9-4.2-2.35-5.65Z'"
cycle_icon = "cycle:'M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8A5.98 5.98 0 0 1 6 12c0-3.31 2.69-6 6-6Zm6.76 1.74L17.3 9.2A5.98 5.98 0 0 1 18 12c0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26Z'"
if text.count(old_icon) != 1:
    raise RuntimeError("Could not find existing Jellyfin refresh glyph")
text = text.replace(old_icon, cycle_icon, 1)
if text.count("jellyfinTaskIcon('refresh')") != 2:
    raise RuntimeError("Expected two Jellyfin refresh icon uses")
text = text.replace("jellyfinTaskIcon('refresh')", "jellyfinTaskIcon('cycle')")
settings_js.write_text(text, encoding="utf-8")

# Keep version and frontend cache contracts synchronized.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text, count = re.subn(r'^(VERSION\s*=\s*["\'])0\.5\.130(["\'])', rf'\g<1>{NEW_VERSION}\2', text, count=1, flags=re.M)
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
if "torrent-dashboard-v05130" not in text or OLD_VERSION not in text:
    raise RuntimeError("Expected old service-worker version")
text = text.replace("torrent-dashboard-v05130", "torrent-dashboard-v05131", 1).replace(OLD_VERSION, NEW_VERSION)
sw.write_text(text, encoding="utf-8")

source = ROOT / "release_notes" / "releases.json"
data = json.loads(source.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in data.get("releases", [])):
    raise RuntimeError(f"Release metadata for {NEW_VERSION} already exists")
data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-07",
    "status": "prerelease",
    "title": "Jellyfin cycle refresh glyph",
    "summary": "Uses a cycle-style Material glyph for the inline Jellyfin status and library refresh controls.",
    "highlights": [
        "Replaces the single-arrow refresh glyph beside Jellyfin status with a two-arrow cycle glyph.",
        "Uses the same cycle glyph beside Libraries for a consistent synchronization visual.",
        "Keeps the existing accessible labels, tooltips, loading animation, and refresh behavior unchanged."
    ],
    "fixes": [],
    "technical": [
        "The cycle glyph remains locally embedded as SVG path data, preserving offline/PWA behavior without adding an external icon-font dependency."
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
print(f"Applied Jellyfin cycle icon update for v{NEW_VERSION}")
