#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.114"
NEW = "0.5.115"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


css = read("static/app.css")
css = replace_once(css,
    '#torrentTable thead th[data-col]{cursor:pointer;user-select:none;-webkit-user-select:none;text-align:left;padding-left:12px;padding-right:26px;outline:none}',
    '#torrentTable thead th[data-col]{cursor:pointer;user-select:none;-webkit-user-select:none;text-align:left;padding-left:12px;padding-right:12px;outline:none}',
    "torrent header padding")
css = replace_once(css,
    '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px;cursor:pointer;pointer-events:auto}',
    '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;gap:5px;cursor:pointer;pointer-events:auto}',
    "sort heading geometry")
css = replace_once(css,
    '.torrent-sort-icon{position:absolute;right:0;display:grid;place-items:center;width:14px;height:14px;color:var(--muted);opacity:0;transition:opacity .12s ease,color .12s ease;pointer-events:none}',
    '.torrent-sort-icon{position:static;flex:0 0 14px;display:grid;place-items:center;width:14px;height:14px;color:var(--muted);opacity:0;transition:opacity .12s ease,color .12s ease;pointer-events:none}',
    "sort icon geometry")
css += '\n/* 0.5.115 inline torrent sort chevrons */\n'
write("static/app.css", css)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(validator,
    "    # 0.5.114 uses a single trailing-edge sort affordance while preserving body-aligned header labels.",
    "    # 0.5.115 keeps each chevron inline with its owning label while preserving body-aligned header groups.",
    "sort validator comment")
validator = replace_once(validator,
    "    assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px' in app_css",
    "    assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;gap:5px' in app_css",
    "sort heading validator")
validator = replace_once(validator,
    "    assert '.torrent-sort-icon{position:absolute;right:0;' in app_css",
    "    assert '.torrent-sort-icon{position:static;flex:0 0 14px;' in app_css\n    assert '.torrent-sort-icon{position:absolute' not in app_css",
    "sort icon validator")
validator = replace_once(validator,
    "    assert '0.5.114 consistent trailing-edge torrent sort chevrons' in app_css",
    "    assert '0.5.114 consistent trailing-edge torrent sort chevrons' in app_css\n    assert '0.5.115 inline torrent sort chevrons' in app_css\n    assert '### Torrent sort indicator grouping' in design_language\n    assert 'Inline torrent sort indicator grouping' in testing_md",
    "sort release marker validator")
write("release_tools/validate_ui_strings.py", validator)

dashboard = read("dashboard.py")
dashboard, count = re.subn(r'VERSION\s*=\s*[\"\']0\.5\.114[\"\']', 'VERSION = "0.5.115"', dashboard, count=1)
if count != 1:
    raise SystemExit(f"dashboard.py VERSION: expected one replacement, found {count}")
write("dashboard.py", dashboard)

app_js = read("static/app.js")
app_js = replace_once(app_js, "const FRONTEND_BUILD='0.5.114';", "const FRONTEND_BUILD='0.5.115';", "frontend build")
write("static/app.js", app_js)

for path in ("static/index.html", "static/sw.js"):
    text = read(path)
    if OLD not in text:
        raise SystemExit(f"{path}: missing {OLD}")
    write(path, text.replace(OLD, NEW))

design = read("DESIGN_LANGUAGE.md")
if "### Torrent sort indicator grouping" not in design:
    design += '''\n\n### Torrent sort indicator grouping\n\n- Sortable torrent headers treat the label and chevron as one inline visual group.\n- Text-oriented header groups align left; numeric header groups align right to match their body values.\n- The chevron always follows the owning label with a small fixed gap rather than floating at an unrelated column edge.\n- Hover, focus, and active-sort emphasis must not change the indicator's geometry.\n'''
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
if "Inline torrent sort indicator grouping" not in testing:
    testing += '''\n\n### Inline torrent sort indicator grouping\n\nManual regression coverage for desktop torrent headers:\n\n1. Verify Name, Status, Progress, Category, and Tags show the sort chevron immediately after the label when hovered/focused/active.\n2. Verify Size, Seeds, Peers, Down, Up, ETA, and Ratio remain right-aligned while their chevron appears immediately after the label.\n3. Sort ascending and descending through both text and numeric columns and confirm the indicator never jumps to a column boundary.\n4. Confirm fixed column widths, viewport-proportional workspace sizing, and mobile torrent cards are unchanged.\n'''
write("TESTING.md", testing)

meta_path = ROOT / "release_notes" / "releases.json"
data = json.loads(meta_path.read_text(encoding="utf-8"))
releases = data["releases"]
if releases[-1].get("version") != OLD:
    raise SystemExit(f"latest structured release is {releases[-1].get('version')}, expected {OLD}")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Inline torrent sort indicators",
    "summary": "Makes every torrent-table sort chevron read as part of its owning header label while preserving content-aligned header groups.",
    "highlights": [
        "Every sortable torrent header now places its chevron immediately after the header label with a consistent gap.",
        "Text-oriented header groups remain left-aligned and numeric header groups remain right-aligned with their body values.",
        "Sorting behavior, fixed column sizing, viewport-proportional desktop workspace sizing, and mobile presentation are unchanged."
    ],
    "fixes": [
        "Removes the mixed visual treatment where left-aligned headers appeared to have edge-anchored chevrons while right-aligned numeric headers appeared to have label-adjacent chevrons."
    ],
    "technical": [
        "The sort icon now participates in the header flex layout as a fixed-width inline item instead of using absolute positioning.",
        "The header no longer reserves a separate absolute-icon gutter; numeric headings only override flex justification."
    ],
    "validation": [
        "The UI audit requires inline sort-icon positioning, preserves numeric-group alignment, and rejects the retired absolute edge-anchored sort geometry.",
        "Manual coverage checks hover, focus, ascending, and descending states across text and numeric headers."
    ],
    "known_issues": [],
}
for key in ("architecture", "decisions", "next_steps"):
    if key in previous:
        entry[key] = previous[key]
releases.append(entry)
meta_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
