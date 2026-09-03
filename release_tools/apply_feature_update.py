#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.78"
NEW = "0.5.79"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected text not found in {path.relative_to(ROOT)}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected text not found in {path.relative_to(ROOT)}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# Version synchronization.
replace_once(ROOT / "dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
replace_once(ROOT / "static" / "app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
replace_all(ROOT / "static" / "index.html", OLD, NEW)
replace_all(ROOT / "static" / "sw.js", OLD, NEW)
replace_once(ROOT / "static" / "sw.js", "torrent-dashboard-v0578", "torrent-dashboard-v0579")

# Firefox correctly rejects addEventListener(callback) because the event type is
# missing. The v0.5.78 drag/drop loop accidentally omitted eventName.
app_path = ROOT / "static" / "app.js"
app = app_path.read_text(encoding="utf-8")
fixes = {
    "for(const eventName of ['dragenter','dragover'])drop.addEventListener(event=>":
        "for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>",
    "for(const eventName of ['dragleave','drop'])drop.addEventListener(event=>":
        "for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>",
}
for old, new in fixes.items():
    if old not in app:
        raise SystemExit(f"Expected broken drag/drop binding not found: {old}")
    app = app.replace(old, new, 1)
app_path.write_text(app, encoding="utf-8")

# Add a regression contract so syntax-only validation cannot miss this runtime
# EventTarget arity failure again.
validator_path = ROOT / "release_tools" / "validate_ui_strings.py"
validator = validator_path.read_text(encoding="utf-8")
anchor = "    assert '### Add Torrent source modes and file selection' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"
regression = """

    # 0.5.79 fixes a startup-blocking EventTarget arity error in Add Torrent drag/drop binding.
    assert \"for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>\" in app_js
    assert \"for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>\" in app_js
    assert \"drop.addEventListener(event=>\" not in app_js
"""
if anchor not in validator:
    raise SystemExit("Add Torrent validation anchor not found")
validator = validator.replace(anchor, anchor + regression, 1)
validator_path.write_text(validator, encoding="utf-8")

# Structured prerelease notes. Carry forward architectural decisions and next
# steps because this is a narrowly scoped startup hotfix.
notes_path = ROOT / "release_notes" / "releases.json"
data = json.loads(notes_path.read_text(encoding="utf-8"))
releases = data.get("releases") or []
if not releases or releases[-1].get("version") != OLD:
    raise SystemExit(f"Expected latest release metadata to be v{OLD}")
previous = releases[-1]
release = {
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Add Torrent startup hotfix",
    "summary": "Fixes a v0.5.78 Add Torrent drag-and-drop event binding error that could prevent the Dashboard from initializing in browsers that enforce the EventTarget API argument contract.",
    "highlights": [
        "Corrects the dragenter, dragover, dragleave, and drop listeners so every addEventListener call receives both the event type and callback.",
        "Restores normal Dashboard initialization while preserving the v0.5.78 selectable Add Torrent workflow, source tabs, file tree, and metadata export behavior."
    ],
    "fixes": [
        "Fixes Dashboard failed to initialize: EventTarget.addEventListener: At least 2 arguments required, but only 1 passed."
    ],
    "technical": [
        "The Add Torrent drag/drop loops now pass eventName as the first addEventListener argument instead of accidentally calling addEventListener with only a callback.",
        "A source-level regression assertion now rejects the broken one-argument binding pattern so JavaScript syntax checks alone cannot allow this failure to recur."
    ],
    "validation": [
        "The full source/unit-test gate and JavaScript syntax validation run after the hotfix is applied.",
        "The UI contract explicitly requires both corrected drag/drop listener loops and rejects the one-argument EventTarget pattern."
    ],
    "known_issues": [],
    "architecture": deepcopy(previous.get("architecture", [])),
    "next_steps": deepcopy(previous.get("next_steps", [])),
    "decisions": deepcopy(previous.get("decisions", [])),
}
releases.append(release)
notes_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW],
    cwd=ROOT,
    check=True,
)
print(f"Applied Torrent Dashboard v{NEW} Add Torrent startup hotfix")
