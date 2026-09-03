#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.106"
NEW = "0.5.107"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one occurrence in {path}, found {count}: {old!r}")
    write(path, text.replace(old, new, 1))


# Fix the desktop workspace calculation. getBoundingClientRect().top is viewport-relative,
# so feeding it directly into the height calculation makes the workspace grow after the
# page scrolls and the next one-second torrent render runs. Convert it to a stable document
# coordinate before calculating the available desktop height.
replace_once(
    "static/app.js",
    "  const top=Math.max(0,workspace.getBoundingClientRect().top);\n  const available=Math.max(360,Math.floor(window.innerHeight-top-16));",
    "  const documentTop=Math.max(0,workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0));\n  const available=Math.max(360,Math.floor(window.innerHeight-documentTop-16));",
)

# Version synchronization.
replace_once("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
replace_once("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")

index = read("static/index.html")
if OLD not in index:
    raise RuntimeError("static/index.html does not contain the previous frontend version")
write("static/index.html", index.replace(OLD, NEW))

sw = read("static/sw.js")
if f"v{OLD.replace('.', '')}" not in sw or OLD not in sw:
    raise RuntimeError("static/sw.js is not synchronized to the previous version")
sw = sw.replace(f"v{OLD.replace('.', '')}", f"v{NEW.replace('.', '')}").replace(OLD, NEW)
write("static/sw.js", sw)

# Record the interaction contract in the design/testing docs.
design = read("DESIGN_LANGUAGE.md")
design_note = """

### Stable desktop torrent workspace height

On desktop/tablet, the torrent workspace has one bounded height derived from the viewport and its fixed document position. Ordinary document scrolling must never change that height. The torrent list keeps its own vertical scroller inside the bounded workspace, while expanding/collapsing Torrent details only reallocates space inside that same workspace. Viewport resizing may legitimately recalculate the workspace height; page scroll position must not be an input to that calculation.
"""
if "### Stable desktop torrent workspace height" not in design:
    write("DESIGN_LANGUAGE.md", design.rstrip() + design_note + "\n")

testing = read("TESTING.md")
testing_note = """

### Desktop torrent workspace scroll stability

- On a desktop-width viewport, note the rendered torrent workspace/list height, then scroll the document above and below the workspace while live one-second polling continues. Verify the torrent workspace and torrent-list panel do not grow or shrink as a consequence of document scroll position.
- Scroll a long torrent list using the table's own vertical scrollbar and verify the list remains bounded while the page position stays independent.
- Resize the browser vertically and verify the workspace recalculates to the new viewport height, then remains stable again during document scrolling.
- Expand and collapse Torrent details and verify space is reallocated inside the fixed workspace rather than increasing the overall workspace height.
- Repeat at mobile width and verify the existing mobile bottom-sheet/list behavior is unchanged.
"""
if "### Desktop torrent workspace scroll stability" not in testing:
    write("TESTING.md", testing.rstrip() + testing_note + "\n")

# Update the UI/source contract so this regression cannot silently return.
validator = read("release_tools/validate_ui_strings.py")
old_assert = '    assert "window.innerHeight-top-16" in app_js\n'
new_assert = (
    '    assert "workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)" in app_js\n'
    '    assert "window.innerHeight-documentTop-16" in app_js\n'
    '    assert "window.innerHeight-top-16" not in app_js\n'
    '    assert "Stable desktop torrent workspace height" in design_language\n'
    '    assert "Desktop torrent workspace scroll stability" in testing_md\n'
)
if old_assert not in validator:
    raise RuntimeError("Could not find the desktop workspace validation assertion")
validator = validator.replace(old_assert, new_assert, 1)

# The validator currently loads the files it audits individually. Add the two documentation
# files once so the new contract can be asserted without weakening existing checks.
needle = '    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")\n'
insert = needle + '    design_language = (ROOT / "DESIGN_LANGUAGE.md").read_text(encoding="utf-8")\n    testing_md = (ROOT / "TESTING.md").read_text(encoding="utf-8")\n'
if 'design_language = (ROOT / "DESIGN_LANGUAGE.md")' not in validator:
    if needle not in validator:
        raise RuntimeError("Could not find validator source-loading block")
    validator = validator.replace(needle, insert, 1)
write("release_tools/validate_ui_strings.py", validator)

# Structured release metadata remains the source of generated changelog/handoff files.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta.get("releases")
if not isinstance(releases, list):
    raise RuntimeError("release_notes/releases.json has no releases list")
if any(str(item.get("version")) == NEW for item in releases if isinstance(item, dict)):
    raise RuntimeError(f"Release metadata for {NEW} already exists")
releases.append({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Stable desktop torrent workspace height",
    "summary": "Keeps the desktop torrent workspace and torrent list at a stable bounded height while document scrolling occurs, preserving the list's independent internal scrollbar.",
    "highlights": [
        "Makes desktop torrent workspace height independent of document scroll position while preserving viewport-resize responsiveness.",
        "Keeps the torrent list bounded and continues to use its existing internal vertical scrollbar for torrent navigation.",
        "Preserves the existing Torrent details space-sharing behavior and mobile bottom-sheet layout."
    ],
    "fixes": [
        "Fixes the torrent list growing after the page is scrolled and the next one-second torrent refresh recalculates workspace height.",
        "Prevents repeated live renders from treating a smaller viewport-relative element top as additional height available to the torrent workspace."
    ],
    "technical": [
        "syncTorrentWorkspaceLayout now converts getBoundingClientRect().top to a stable document coordinate by adding the current window scroll offset before calculating available height.",
        "The existing render cadence, fixed desktop workspace CSS, internal table overflow, detail-pane flex allocation, and mobile layout remain unchanged."
    ],
    "validation": [
        "The UI audit requires document-coordinate workspace sizing and rejects the old viewport-relative height formula.",
        "Manual desktop coverage verifies document scrolling cannot change workspace/list height while internal torrent scrolling and viewport resize continue to work.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": []
})
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate all derived release/handoff files before workflow validation.
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW],
    cwd=ROOT,
    check=True,
)

print(f"Applied v{NEW} stable desktop torrent workspace height")
