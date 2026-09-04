#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.118"
NEW = "0.5.119"


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
html = html.replace(f'content="{OLD}" name="torrent-dashboard-build"', f'content="{NEW}" name="torrent-dashboard-build"')
for asset in ("app.css", "settings.css", "app.js", "settings.js"):
    html = html.replace(f'/static/{asset}?v={OLD}', f'/static/{asset}?v={NEW}')

old_controls = '<div class="add-content-folder-actions" aria-label="Folder view controls"><button class="secondary small-btn" id="addExpandAllFolders" type="button" aria-controls="addContentBody" disabled>Expand all</button><button class="secondary small-btn" id="addCollapseAllFolders" type="button" aria-controls="addContentBody" disabled>Collapse all</button></div>'
new_controls = '<div class="add-content-folder-actions" aria-label="Folder view controls"><button class="secondary add-folder-action-button" id="addExpandAllFolders" type="button" aria-controls="addContentBody" aria-label="Expand all folders" title="Expand all folders" data-material-symbol="unfold_more" disabled><svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 5.83 15.17 9l1.41-1.41L12 3 7.41 7.59 8.83 9 12 5.83zm0 12.34L8.83 15l-1.41 1.41L12 21l4.59-4.59L15.17 15 12 18.17z"/></svg></button><button class="secondary add-folder-action-button" id="addCollapseAllFolders" type="button" aria-controls="addContentBody" aria-label="Collapse all folders" title="Collapse all folders" data-material-symbol="unfold_less" disabled><svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M7.41 18.59 8.83 20 12 16.83 15.17 20l1.41-1.41L12 14l-4.59 4.59zm9.17-13.18L15.17 4 12 7.17 8.83 4 7.41 5.41 12 10l4.58-4.59z"/></svg></button></div>'
html = replace_once(html, old_controls, new_controls, "Add Torrent folder controls")
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = sw.replace(f"?v={OLD}", f"?v={NEW}")
sw = sw.replace("torrent-dashboard-v05118", "torrent-dashboard-v05119")
write("static/sw.js", sw)

# Replace the v0.5.118 text-button styling with a permanent horizontal icon pair.
css = read("static/app.css")
old_css = '''/* 0.5.118 Add Torrent folder disclosure actions. */
.add-content-summary-heading{justify-content:space-between;gap:10px}
.add-content-summary-heading>span{min-width:0;flex:1}
.add-content-folder-actions{display:flex;align-items:center;gap:6px;flex:0 0 auto}
.add-content-folder-actions button{white-space:nowrap;min-height:30px;padding:6px 9px;font-size:9.5px}
.add-content-folder-actions button:disabled{cursor:default;opacity:.45}
@media(max-width:700px){
  .add-content-summary-heading{align-items:flex-start;flex-wrap:wrap}
  .add-content-summary-heading>span{flex:1 0 100%}
  .add-content-folder-actions{width:100%}
  .add-content-folder-actions button{flex:1}
}
'''
new_css = '''/* 0.5.119 Material Add Torrent folder disclosure actions. */
.add-content-summary-heading{justify-content:space-between;gap:10px}
.add-content-summary-heading>span{min-width:0;flex:1}
.add-content-folder-actions{display:flex;align-items:center;gap:5px;flex:0 0 auto;flex-wrap:nowrap}
.add-folder-action-button{width:32px;height:32px;min-width:32px;min-height:32px;padding:0!important;display:grid;place-items:center;flex:0 0 32px}
.add-folder-action-button .material-symbol-icon{width:18px;height:18px}
.add-folder-action-button:disabled{cursor:default;opacity:.45}
@media(max-width:700px){
  .add-content-summary-heading{align-items:center;flex-wrap:wrap}
  .add-content-folder-actions{margin-left:auto}
}
'''
css = replace_once(css, old_css, new_css, "folder disclosure CSS")
write("static/app.css", css)

# Strengthen the applied UI contract around the icon-only controls.
validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert '### Add Torrent folder disclosure actions' in testing_md\n\n    print(\"UI string audit passed\")"
replacement = '''    assert '### Add Torrent folder disclosure actions' in testing_md

    # 0.5.119 presents bulk disclosure as a compact Material icon pair.
    assert 'aria-label="Expand all folders"' in html and 'aria-label="Collapse all folders"' in html
    assert 'data-material-symbol="unfold_more"' in html and 'data-material-symbol="unfold_less"' in html
    assert '>Expand all</button>' not in html and '>Collapse all</button>' not in html
    assert '0.5.119 Material Add Torrent folder disclosure actions' in app_css
    assert '.add-content-folder-actions{display:flex;align-items:center;gap:5px;flex:0 0 auto;flex-wrap:nowrap}' in app_css
    assert '.add-folder-action-button{width:32px;height:32px;min-width:32px;min-height:32px' in app_css
    assert '.add-content-folder-actions{width:100%}' not in app_css
    assert '.add-content-folder-actions button{flex:1}' not in app_css
    assert '## Material Add Torrent folder controls' in design_language
    assert '### Material Add Torrent folder controls' in testing_md

    print("UI string audit passed")'''
validator = replace_once(validator, anchor, replacement, "validator anchor")
write("release_tools/validate_ui_strings.py", validator)

# Document the presentation rule.
design = read("DESIGN_LANGUAGE.md")
if "## Material Add Torrent folder controls" not in design:
    design += '''\n\n## Material Add Torrent folder controls\n\n- Keep Add Torrent bulk folder disclosure visually compact: Expand all and Collapse all use locally embedded Material-style unfold icons rather than text buttons.\n- The two disclosure controls are a single non-wrapping horizontal pair. On narrow layouts the pair may move as a unit, but the controls must not stack vertically or stretch into full-width actions.\n- Preserve explicit accessible names and native tooltips (`Expand all folders` and `Collapse all folders`) because the visible controls are icon-only.\n- Bulk disclosure remains presentation-only and must not change file selection, priority, metadata, or add-torrent options.\n'''
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
if "### Material Add Torrent folder controls" not in testing:
    testing += '''\n\n### Material Add Torrent folder controls\n\n- Load a torrent containing nested folders and verify the two folder bulk actions render as adjacent Material-style icon buttons, not text controls.\n- Verify the Expand all folders and Collapse all folders tooltips/accessible names match their actions.\n- At desktop and narrow/mobile widths, verify the two buttons remain side-by-side; the pair may wrap below the summary text but must not stack or stretch to full width.\n- Verify disabled-state transitions still follow the current tree state and that bulk disclosure does not change file checkboxes or priority values.\n'''
write("TESTING.md", testing)

# Add v0.5.119 release metadata while carrying forward durable architecture/decisions.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"release metadata already contains {NEW}")
latest = max(releases, key=lambda item: tuple(int(x) for x in str(item["version"]).split(".")[:3]))
entry = {
    "version": NEW,
    "date": "2026-09-04",
    "status": "prerelease",
    "title": "Material Add Torrent folder controls",
    "summary": "Refines Add Torrent's bulk folder disclosure into a compact side-by-side Material icon pair while preserving the existing recursive expand/collapse behavior.",
    "highlights": [
        "Replaces the Expand all and Collapse all text buttons with locally embedded Material-style unfold-more and unfold-less icons.",
        "Keeps both folder disclosure actions adjacent in one non-wrapping pair on desktop and mobile.",
        "Retains explicit accessible labels and tooltips for the icon-only controls."
    ],
    "fixes": [
        "Removes the oversized responsive folder actions that could read as stacked/full-width controls in the Add Torrent preview."
    ],
    "technical": [
        "The existing recursive collapsedFolders behavior and event bindings are unchanged; this increment is presentation-only.",
        "The Material-style SVG paths are embedded locally with no external icon/font dependency."
    ],
    "validation": [
        "The UI audit requires icon-only unfold controls, accessible names, non-wrapping horizontal layout, and rejects the prior full-width responsive action styling.",
        "Manual coverage verifies desktop/mobile adjacency, disabled-state transitions, and unchanged file selection/priority behavior.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": [],
}
for field in ("architecture", "decisions", "next_steps"):
    if latest.get(field):
        entry[field] = deepcopy(latest[field])
entry.setdefault("decisions", []).append("Use compact locally embedded Material icon buttons for Add Torrent bulk folder disclosure; keep Expand all and Collapse all adjacent and presentation-only.")
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate public/fork-safe continuity artifacts.
import subprocess
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
