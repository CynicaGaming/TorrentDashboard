#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.119"
NEW = "0.5.120"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard VERSION")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = replace_once(html, f'content="{OLD}" name="torrent-dashboard-build"', f'content="{NEW}" name="torrent-dashboard-build"', "HTML build")
for asset in ("app.css", "settings.css", "app.js", "settings.js"):
    html = replace_once(html, f'/static/{asset}?v={OLD}', f'/static/{asset}?v={NEW}', f"{asset} cache bust")
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v05119", "torrent-dashboard-v05120", "service worker cache")
for asset in ("app.css", "settings.css", "settings.js", "app.js"):
    sw = replace_once(sw, f'/static/{asset}?v={OLD}', f'/static/{asset}?v={NEW}', f"service worker {asset}")
write("static/sw.js", sw)

# The generic preview-heading div rule has higher specificity than the folder
# action class and was forcing the icon pair back to display:grid. Narrow it to
# ordinary heading-copy containers so the action wrapper keeps its flex row.
css = read("static/app.css")
css = replace_once(
    css,
    ".add-preview-heading div{display:grid;gap:2px}",
    "/* 0.5.120 Add Torrent folder action cascade fix. */\n.add-preview-heading>div:not(.add-content-folder-actions){display:grid;gap:2px}",
    "preview heading container selector",
)
write("static/app.css", css)

# Applied UI contract: the generic heading-copy layout must never override the
# explicit horizontal folder-action wrapper again.
validator = read("release_tools/validate_ui_strings.py")
anchor = '''    assert '### Material Add Torrent folder controls' in testing_md\n\n    print("UI string audit passed")'''
replacement = '''    assert '### Material Add Torrent folder controls' in testing_md

    # 0.5.120 fixes cascade precedence so the Material folder controls render as one row.
    assert '.add-preview-heading div{display:grid;gap:2px}' not in app_css
    assert '.add-preview-heading>div:not(.add-content-folder-actions){display:grid;gap:2px}' in app_css
    assert '.add-content-folder-actions{display:flex;align-items:center;gap:5px;flex:0 0 auto;flex-wrap:nowrap}' in app_css
    assert '0.5.120 Add Torrent folder action cascade fix' in app_css
    assert '## Add Torrent folder control row' in design_language
    assert '### Add Torrent folder control row' in testing_md

    print("UI string audit passed")'''
validator = replace_once(validator, anchor, replacement, "validator anchor")
write("release_tools/validate_ui_strings.py", validator)

# Durable design/testing notes.
design = read("DESIGN_LANGUAGE.md")
if "## Add Torrent folder control row" not in design:
    design += '''\n\n## Add Torrent folder control row\n\n- The Add Torrent Expand all folders and Collapse all folders Material controls are one horizontal action pair.\n- Generic Add Torrent preview-heading copy layout must not apply `display:grid` to `.add-content-folder-actions`; keep the action wrapper as the explicit non-wrapping flex row.\n- The pair may move as a unit when space is constrained, but the two icon buttons must remain side-by-side.\n'''
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
if "### Add Torrent folder control row" not in testing:
    testing += '''\n\n### Add Torrent folder control row\n\n- Open Add Torrent with metadata containing folders and verify the Expand all folders and Collapse all folders Material buttons render side-by-side in one row.\n- Verify this at desktop and narrow/mobile modal widths. The pair may move below the file summary, but the buttons must never stack vertically.\n- Confirm individual folder disclosure, Expand all, Collapse all, disabled-state transitions, file selections, and file priorities are unchanged.\n- The source audit rejects the old generic `.add-preview-heading div` grid selector so it cannot override the folder-action flex wrapper again.\n'''
write("TESTING.md", testing)

# Release metadata while preserving durable architecture and next-step state.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"release metadata already contains {NEW}")
latest = max(releases, key=lambda item: tuple(int(x) for x in str(item["version"]).split(".")[:3]))
entry = {
    "version": NEW,
    "date": "2026-09-05",
    "status": "prerelease",
    "title": "Side-by-side Add Torrent folder controls",
    "summary": "Fixes CSS cascade precedence so the Add Torrent Material Expand all and Collapse all folder controls actually render beside each other instead of stacking vertically.",
    "highlights": [
        "Keeps the two Add Torrent bulk folder disclosure icons in one horizontal row on desktop and mobile.",
        "Narrows the older preview-heading grid rule so it applies only to heading-copy containers and no longer overrides the folder-action flex wrapper."
    ],
    "fixes": [
        "Corrects the v0.5.119 regression where the unfold-more and unfold-less controls could still appear stacked despite their non-wrapping flex declaration."
    ],
    "technical": [
        "The root cause was selector specificity: `.add-preview-heading div` outranked `.add-content-folder-actions` and forced the action wrapper to `display:grid`.",
        "Folder disclosure behavior, file selection, priorities, metadata loading, and qBitTorrent requests are unchanged."
    ],
    "validation": [
        "The UI audit rejects the old generic preview-heading div selector and requires the narrowed heading-copy selector plus the existing non-wrapping folder-action flex row.",
        "Manual coverage verifies side-by-side controls at desktop and mobile widths and unchanged folder/file behavior.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": [],
}
for field in ("architecture", "decisions", "next_steps"):
    if latest.get(field):
        entry[field] = deepcopy(latest[field])
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
