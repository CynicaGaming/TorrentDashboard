#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.127"
NEW_VERSION = "0.5.128"
OLD_CACHE_VERSION = "v05127"
NEW_CACHE_VERSION = "v05128"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old!r}; found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


app = ROOT / "static" / "app.js"
replace_once(
    app,
    ">API key</option><option value=\"password\"",
    ">API key (qBitTorrent 5.2+)</option><option value=\"password\"",
)
replace_once(app, "<small>qBitTorrent 5.2+ · Bearer authentication</small>", "")

# Keep the release/version contract synchronized.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text, count = re.subn(r'^(VERSION\s*=\s*["\'])0\.5\.127(["\'])', rf'\g<1>{NEW_VERSION}\2', text, count=1, flags=re.M)
if count != 1:
    raise RuntimeError("Could not update dashboard VERSION")
dashboard.write_text(text, encoding="utf-8")

index = ROOT / "static" / "index.html"
text = index.read_text(encoding="utf-8")
if OLD_VERSION not in text:
    raise RuntimeError(f"Expected {OLD_VERSION} in static/index.html")
index.write_text(text.replace(OLD_VERSION, NEW_VERSION), encoding="utf-8")

sw = ROOT / "static" / "sw.js"
text = sw.read_text(encoding="utf-8")
if OLD_VERSION not in text or OLD_CACHE_VERSION not in text:
    raise RuntimeError("Could not find expected service-worker version markers")
sw.write_text(text.replace(OLD_VERSION, NEW_VERSION).replace(OLD_CACHE_VERSION, NEW_CACHE_VERSION), encoding="utf-8")

# app.js also owns FRONTEND_BUILD.
text = app.read_text(encoding="utf-8")
if f"const FRONTEND_BUILD='{OLD_VERSION}';" not in text:
    raise RuntimeError("Could not find app.js frontend build version")
app.write_text(text.replace(f"const FRONTEND_BUILD='{OLD_VERSION}';", f"const FRONTEND_BUILD='{NEW_VERSION}';", 1), encoding="utf-8")

source = ROOT / "release_notes" / "releases.json"
data = json.loads(source.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in data.get("releases", [])):
    raise RuntimeError(f"Release metadata for {NEW_VERSION} already exists")
data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-07",
    "status": "prerelease",
    "title": "qBitTorrent API key labeling cleanup",
    "summary": "Simplifies the Clients authentication UI by putting the qBitTorrent 5.2+ requirement directly on the API key option and removing redundant Bearer-authentication helper text.",
    "highlights": [
        "The Clients authentication selector now reads API key (qBitTorrent 5.2+).",
        "Removes the separate qBitTorrent 5.2+ · Bearer authentication line beneath the API key field."
    ],
    "fixes": [
        "Makes the regular Clients settings card consistent with the existing first-run qBitTorrent authentication selector."
    ],
    "technical": [],
    "validation": [
        "Source validation, unit tests, UI-string validation, and JavaScript syntax checks run before publication."
    ],
    "known_issues": [],
    "architecture": [],
    "decisions": [],
    "next_steps": []
})
source.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run([
    "python", "release_tools/generate_release_notes.py", "--version", NEW_VERSION
], cwd=ROOT, check=True)
print(f"Applied client API key label cleanup for v{NEW_VERSION}")
