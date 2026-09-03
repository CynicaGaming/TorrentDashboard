#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.89"
NEW = "0.5.90"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


# Synchronized application/frontend version.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if OLD not in html:
    raise RuntimeError("Current frontend version was not found in static/index.html")
html = html.replace(OLD, NEW)
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = replace_once(
    app_js,
    "event.clientX>=rect.right-14&&event.clientX<=rect.right+8",
    "event.clientX>=rect.right-14&&event.clientX<=rect.right",
    "resize edge boundary",
)
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0589", "torrent-dashboard-v0590", "service-worker cache generation")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)

# The effective resize gutter now stays inside the data header instead of
# overlapping the adjacent header. Name no longer carries a historical
# presentation cap, and the fixed action column is explicitly bounded/sticky.
app_css = read("static/app.css")
if "0.5.90 torrent-column boundary and overflow polish" in app_css:
    raise RuntimeError("v0.5.90 CSS already present")
app_css += r'''

/* 0.5.90 torrent-column boundary and overflow polish. */
.column-resize-handle{right:0;width:14px}
.column-resize-handle::after{right:0}
#torrentTable td[data-col="name"] .torrent-name{max-width:none;width:100%;min-width:0}
#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important}
#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden}
#torrentTable td.row-actions{display:table-cell!important;position:sticky;right:0;z-index:3;text-align:right;background:var(--panel);padding-left:5px;padding-right:5px;overflow:hidden}
#torrentTable tbody tr:hover td.row-actions{background:color-mix(in srgb,var(--panel2) 50%,var(--panel))}
#torrentTable td.row-actions .more-row{max-width:38px}
.torrent-list-region,.torrent-list-region .table-wrap{min-width:0;max-width:100%}
'''
write("static/app.css", app_css)

# Update the durable design/test contract.
design = read("DESIGN_LANGUAGE.md")
old_resize = "- Drag the right edge of a visible data header to resize that column. The resize edge uses a forgiving hit target and takes exclusive control of the pointer so it cannot simultaneously initiate header reordering. The in-progress width must survive the one-second live refresh while the pointer remains down; committed widths are stored with the same browser-local column layout and survive visibility changes, reordering, and reloads."
new_resize = "- Drag the right edge of a visible data header to resize that column. The resize gutter stays entirely inside the data header, uses a forgiving hit target, and takes exclusive control of the pointer so it cannot overlap an adjacent column or simultaneously initiate header reordering. The in-progress width must survive the one-second live refresh while the pointer remains down; committed widths are stored with the same browser-local column layout and survive visibility changes, reordering, and reloads."
if old_resize not in design:
    raise RuntimeError("Could not find configurable-column resize design rule")
design = design.replace(old_resize, new_resize, 1)
needle = "- Column resizing has per-column minimums that preserve legibility and a bounded maximum width. Name can shrink to a compact readable width; the fixed selection and row-actions columns are not user-resizable."
replacement = needle + "\n- The Name cell must not impose a historical fixed truncation width. It may use all space assigned to its column and should show an ellipsis only when the rendered cell is actually narrower than the torrent name.\n- The row-actions column has a fixed width and remains pinned to the right edge of the torrent viewport. It never exposes a resize gutter and must not cause the dashboard page itself to overflow horizontally; excess data-column width is contained by the torrent table's own scroll region."
if needle not in design:
    raise RuntimeError("Could not find configurable-column sizing design rule")
design = design.replace(needle, replacement, 1)
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
needle = "- Verify the resize edge is easy to acquire without pixel-perfect positioning. Start resizing near the divider and verify header reordering cannot begin until the resize gesture is released; then drag from the body of the same header and verify normal reordering still works and does not discard its saved width."
replacement = needle + "\n- Verify the resize gutter never extends into the next header. In particular, move the pointer across the boundary between the last visible data column and the far-right actions column; the actions column must never show resize behavior or change width.\n- With Name at its default/automatic width, verify long torrent names are not truncated by the old fixed 470/620 px cap. Resize Name narrower and confirm ellipsis appears only when the actual cell becomes too narrow; widen it again and confirm additional text becomes visible."
if needle not in testing:
    raise RuntimeError("Could not find configurable-column interaction test rule")
testing = testing.replace(needle, replacement, 1)
needle2 = "- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize handles."
replacement2 = "- Verify the selection checkbox and row-actions control remain fixed at the outer edges and do not expose resize handles. The row-actions column must stay at its fixed width and pinned to the right edge while data columns resize or the table scrolls horizontally."
if needle2 not in testing:
    raise RuntimeError("Could not find fixed-column test rule")
testing = testing.replace(needle2, replacement2, 1)
write("TESTING.md", testing)

# Bring the source-level UI audit forward to the refined boundary contract.
validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    'assert "event.clientX>=rect.right-14&&event.clientX<=rect.right+8" in app_js',
    'assert "event.clientX>=rect.right-14&&event.clientX<=rect.right" in app_js',
    "v0.5.89 resize-boundary validator",
)
anchor = "    assert 'takes exclusive control of the pointer' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n"
if anchor not in validator:
    raise RuntimeError("Could not find v0.5.89 validator anchor")
extra = r'''    # 0.5.90 keeps the forgiving resize gutter inside the data header,
    # removes the historical Name truncation cap, and hard-locks row actions.
    assert '.column-resize-handle{right:0;width:14px}' in app_css
    assert '.column-resize-handle::after{right:0}' in app_css
    assert '#torrentTable td[data-col="name"] .torrent-name{max-width:none;width:100%;min-width:0}' in app_css
    assert '#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important}' in app_css
    assert '#torrentTable th.row-actions-head{position:sticky;right:0;z-index:8;background:var(--panel3);overflow:hidden}' in app_css
    assert '#torrentTable td.row-actions{display:table-cell!important;position:sticky;right:0;z-index:3;text-align:right;background:var(--panel)' in app_css
    assert '.torrent-list-region,.torrent-list-region .table-wrap{min-width:0;max-width:100%}' in app_css
    assert '<th class="row-actions-head"></th>' in html and 'data-col="actions"' not in html
    assert 'ellipsis only when the rendered cell is actually narrower' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'actions column must never show resize behavior or change width' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
validator = validator.replace(anchor, anchor + extra, 1)
write("release_tools/validate_ui_strings.py", validator)

# Structured release metadata drives CHANGELOG/PROJECT_STATE/HANDOFF.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
previous = next((item for item in releases if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Previous release v{OLD} not found")
decisions = list(previous.get("decisions") or [])
decisions.append("Keep torrent resize hit targets inside their owning data header, allow Name to consume its actual assigned width before ellipsizing, and hard-lock the row-actions column as a fixed right-edge control surface.")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Torrent column boundary polish",
    "summary": "Refines torrent-table resizing so the gutter never overlaps adjacent controls, long names use their assigned space before truncating, and the far-right actions column remains fixed and contained.",
    "highlights": [
        "The resize gutter remains a forgiving 14 px target but now lives entirely inside the owning data header instead of extending into its neighbor.",
        "Torrent names no longer inherit the historical 470/620 px truncation cap; ellipsis appears only when the actual Name cell is too narrow.",
        "The far-right actions column is explicitly fixed at 48 px and pinned to the right edge of the torrent viewport."
    ],
    "fixes": [
        "Prevents the last data-column resize target from being acquired while the pointer is visually over the actions column.",
        "Prevents the fixed actions surface from stretching and contributing to page-level horizontal overflow.",
        "Allows widening Name to reveal additional torrent-name text instead of retaining an obsolete presentation cap."
    ],
    "technical": [
        "The pointer resize boundary is now rect.right-14 through rect.right, with no outside-header allowance.",
        "Late CSS overrides remove the effective Name max-width while retaining overflow ellipsis for genuinely constrained cells.",
        "row-actions-head and row-actions share a fixed min/width/max-width contract and use sticky right positioning; the surrounding torrent viewport explicitly contains horizontal overflow."
    ],
    "validation": [
        "The UI audit requires the inward-only resize gutter, uncapped Name content, fixed/sticky actions column, contained torrent viewport, and no actions data-column registration.",
        "Manual regression coverage checks the last-column/actions boundary, long-name expansion, real overflow ellipsis, horizontal table scrolling, and fixed action controls.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture") or []),
    "next_steps": list(previous.get("next_steps") or []),
    "decisions": decisions,
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} torrent column boundary polish")
