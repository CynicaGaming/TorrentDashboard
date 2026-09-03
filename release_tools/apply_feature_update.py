#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.80"
PREVIOUS = "0.5.79"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} occurrence, found {count}")
    return text.replace(old, new, 1)


def append_once(text: str, marker: str, block: str) -> str:
    if marker in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block.rstrip() + "\n"


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if PREVIOUS not in html:
    raise RuntimeError("Previous frontend version not found in index.html")
html = html.replace(PREVIOUS, VERSION)
write("static/index.html", html)

app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")

old_row_click = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}openDetail(tr.dataset.server,tr.dataset.hash)}"
new_row_click = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}const server=tr.dataset.server,hash=tr.dataset.hash;if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}openDetail(server,hash)}"
app = replace_once(app, old_row_click, new_row_click, "torrent row click handler")

old_depth = 'data-add-depth="${depth}"><span class="add-content-select">'
new_depth = 'data-add-depth="${depth}" style="--add-depth:${depth}"><span class="add-content-select">'
if app.count(old_depth) != 2:
    raise RuntimeError(f"Expected two Add Torrent depth rows, found {app.count(old_depth)}")
app = app.replace(old_depth, new_depth)
old_name_depth = 'class="add-content-name" style="--add-depth:${depth}"'
if app.count(old_name_depth) != 2:
    raise RuntimeError(f"Expected two Add Torrent name-depth styles, found {app.count(old_name_depth)}")
app = app.replace(old_name_depth, 'class="add-content-name"')
write("static/app.js", app)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0579", "torrent-dashboard-v0580", "service-worker cache version")
if PREVIOUS not in sw:
    raise RuntimeError("Previous asset version not found in service worker")
sw = sw.replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

css = read("static/app.css")
css = append_once(
    css,
    "0.5.80 Add Torrent hierarchy and detail selection polish",
    r'''/* 0.5.80 Add Torrent hierarchy and detail selection polish. */
.add-content-row{grid-template-columns:calc(34px + var(--add-depth,0) * 16px) minmax(0,1fr) 90px 112px}
.add-content-select{place-items:center end!important;padding-right:9px}
.add-content-name{padding-left:0}
@media(max-width:520px){.add-content-row{grid-template-columns:calc(30px + var(--add-depth,0) * 14px) minmax(130px,1fr) 68px 96px}.add-content-select{padding-right:7px}}
''',
)
write("static/app.css", css)

# Durable product/testing contract.
design = read("DESIGN_LANGUAGE.md")
design = append_once(
    design,
    "## Hierarchical torrent content selection",
    r'''## Hierarchical torrent content selection

File-selection trees should communicate ancestry through the selection control as well as the label. In Add Torrent, each nested folder/file level indents the checkbox and name together while size and priority columns remain aligned. Do not represent hierarchy only by shifting filenames away from otherwise flat checkboxes.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally.
''',
)
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing = append_once(
    testing,
    "### Add Torrent hierarchy and repeated detail selection",
    r'''### Add Torrent hierarchy and repeated detail selection

- Load a multi-folder torrent in Add Torrent and verify each nested level moves its checkbox and filename together to the right; Size and Priority columns should stay aligned across all depths.
- Verify top-level files/folders remain at the base indentation and nested descendants are visibly distinguishable without relying on folder names alone.
- Select a torrent row and verify Torrent details expands for it. Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
''',
)
write("TESTING.md", testing)

# UI regression contract.
validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    '    assert "openDetail(tr.dataset.server,tr.dataset.hash)" in app_js\n',
    '    assert "openDetail(server,hash)" in app_js\n',
    "superseded torrent detail invocation assertion",
)
anchor = '    print("UI string audit passed")\n'
block = r'''    # 0.5.80 makes Add Torrent hierarchy visible at the checkbox level and
    # treats a repeated click on the active torrent row as detail deselection.
    assert app_js.count('data-add-depth="${depth}" style="--add-depth:${depth}"') == 2
    assert 'class="add-content-name" style="--add-depth:${depth}"' not in app_js
    assert '0.5.80 Add Torrent hierarchy and detail selection polish' in app_css
    assert 'grid-template-columns:calc(34px + var(--add-depth,0) * 16px)' in app_css
    assert 'place-items:center end!important' in app_css
    assert "if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}" in app_js
    assert '## Hierarchical torrent content selection' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Add Torrent hierarchy and repeated detail selection' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')

'''
if block.strip() not in validator:
    validator = replace_once(validator, anchor, block + anchor, "UI audit completion anchor")
write("release_tools/validate_ui_strings.py", validator)

# Release metadata. Carry forward the latest architecture/roadmap while recording
# the two presentation/interaction changes in this increment.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if not any(str(item.get("version")) == VERSION for item in releases):
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS), None)
    if not previous:
        raise RuntimeError(f"Release metadata for v{PREVIOUS} was not found")
    decisions = list(previous.get("decisions") or [])
    for decision in (
        "Represent Add Torrent file hierarchy by indenting the selection control and name together while keeping data columns aligned.",
        "A repeated click on the torrent currently shown in Torrent details clears the detail context; choosing a different torrent replaces it directly.",
    ):
        if decision not in decisions:
            decisions.append(decision)
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Torrent hierarchy and detail selection polish",
        "summary": "Improves Add Torrent file-tree readability by indenting checkboxes with their hierarchy and makes repeated torrent-row selection clear the active Torrent details context.",
        "highlights": [
            "Nested Add Torrent folders and files now indent their checkbox and name together, making parent/child relationships immediately visible.",
            "Size and Priority columns remain aligned while the selectable tree shifts according to hierarchy depth.",
            "Clicking the torrent already displayed in Torrent details now deselects it and returns the persistent dock to its empty collapsed state.",
            "Clicking a different torrent still switches directly to that torrent and expands its details."
        ],
        "fixes": [
            "Removes the flat-checkbox appearance that made nested Add Torrent content difficult to scan.",
            "Provides a natural way to clear Torrent details without adding a separate close button to the persistent dock."
        ],
        "technical": [
            "Add Torrent rows expose their hierarchy depth as --add-depth; the checkbox column expands by one indentation step per level while fixed right-side columns remain aligned.",
            "rowClick now compares the clicked server/hash with the current detail context and calls resetDetailPane when they match."
        ],
        "validation": [
            "The UI audit requires row-level hierarchy depth, checkbox indentation CSS, and the repeated-row detail reset path.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and release package-integrity gates remain required."
        ],
        "known_issues": [],
        "architecture": list(previous.get("architecture") or []),
        "next_steps": list(previous.get("next_steps") or []),
        "decisions": decisions,
    })
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    ["python", "release_tools/generate_release_notes.py", "--version", VERSION],
    cwd=ROOT,
    check=True,
)
print(f"Applied Torrent Dashboard v{VERSION} hierarchy and detail selection polish")
