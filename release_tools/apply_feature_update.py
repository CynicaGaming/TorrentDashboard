#!/usr/bin/env python3
"""Apply v0.5.68 bounded desktop/tablet torrent workspace sizing."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.67"
NEW = "0.5.68"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Application version.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

# HTML build/cache references.
html = read("static/index.html")
html = html.replace(f'content="{OLD}" name="torrent-dashboard-build"', f'content="{NEW}" name="torrent-dashboard-build"')
html = html.replace(f'?v={OLD}', f'?v={NEW}')
if OLD in html:
    raise RuntimeError("index.html still contains old build version")
write("static/index.html", html)

# Frontend build plus explicit workspace state.
app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = replace_once(
    app_js,
    "$('#torrentDetailPane').classList.remove('hidden');$$('[data-detailtab]')",
    "const pane=$('#torrentDetailPane');pane.classList.remove('hidden');pane.closest('.torrent-workspace')?.classList.add('has-detail');$$('[data-detailtab]')",
    "detail open workspace state",
)
app_js = replace_once(
    app_js,
    "function closeDetailPane(){$('#torrentDetailPane').classList.add('hidden');state.detail=null;render()}",
    "function closeDetailPane(){const pane=$('#torrentDetailPane');pane.classList.add('hidden');pane.closest('.torrent-workspace')?.classList.remove('has-detail');state.detail=null;render()}",
    "detail close workspace state",
)
write("static/app.js", app_js)

# Bound the non-mobile workspace instead of forcing a large minimum height.
css = read("static/app.css")
css = replace_once(
    css,
    ".torrent-workspace{display:flex;flex-direction:column;overflow:hidden}\n",
    ".torrent-workspace{display:flex;flex-direction:column;overflow:hidden;height:min(460px,44dvh)}\n  .torrent-workspace.has-detail{height:min(600px,58dvh)}\n",
    "tablet/desktop workspace sizing",
)
css = replace_once(
    css,
    ".torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:0;max-height:none;border:0;border-top:1px solid var(--border);border-radius:0;box-shadow:none;display:flex;flex-direction:column;background:var(--panel)}",
    ".torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:0;max-height:none;border:0;border-top:1px solid var(--border);border-radius:0;box-shadow:none;display:flex;flex:0 0 clamp(180px,42%,290px);flex-direction:column;background:var(--panel)}",
    "tablet detail sizing",
)
css = replace_once(
    css,
    "@media(min-width:1024px){\n  .torrent-workspace{height:calc(100dvh - 320px);min-height:480px}\n  .torrent-detail-pane{flex:0 0 clamp(230px,36%,390px)}\n}",
    "@media(min-width:1024px){\n  .torrent-detail-pane{flex-basis:clamp(200px,42%,310px)}\n}",
    "desktop workspace sizing",
)
write("static/app.css", css)

# Service worker generation.
sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0567", "torrent-dashboard-v0568")
sw = sw.replace(f"?v={OLD}", f"?v={NEW}")
if OLD in sw or "v0567" in sw:
    raise RuntimeError("service worker still contains old build version")
write("static/sw.js", sw)

# Durable interaction/layout contract.
design = read("DESIGN_LANGUAGE.md")
section = """

## Bounded list and inspector workspaces

On desktop and tablet layouts, list/detail workspaces should fit within the initial viewport under normal browser chrome rather than forcing the page to grow around a large list surface.

- A list-only torrent workspace should remain deliberately bounded; unused vertical space is preferable to an oversized empty table.
- Opening the torrent inspector may enlarge the shared workspace, but the torrent list and detail inspector should remain visible together in the initial viewport at standard desktop/tablet sizes.
- The primary list becomes the flexible internal scroll region. Long lists should scroll inside the workspace before the overall dashboard page scrolls.
- The detail body may scroll independently when its content exceeds the inspector allocation.
- Mobile remains an exception: the existing bottom-sheet interaction may consume most of the viewport because simultaneous list/detail visibility is not practical at phone widths.
"""
if "## Bounded list and inspector workspaces" not in design:
    design = design.rstrip() + section + "\n"
write("DESIGN_LANGUAGE.md", design)

# Strengthen the UI regression contract for the corrected layout.
validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert \"now-detailRefreshAt<3000\" in app_js\n"
addition = """    assert \"pane.closest('.torrent-workspace')?.classList.add('has-detail')\" in app_js
    assert \"pane.closest('.torrent-workspace')?.classList.remove('has-detail')\" in app_js
    assert \".torrent-workspace{display:flex;flex-direction:column;overflow:hidden;height:min(460px,44dvh)}\" in app_css
    assert \".torrent-workspace.has-detail{height:min(600px,58dvh)}\" in app_css
    assert \"flex:0 0 clamp(180px,42%,290px)\" in app_css
    assert \"height:calc(100dvh - 320px);min-height:480px\" not in app_css
"""
if addition.strip() not in validator:
    validator = replace_once(validator, anchor, anchor + addition, "torrent workspace validator")
write("release_tools/validate_ui_strings.py", validator)

# Structured release metadata.
notes_path = ROOT / "release_notes" / "releases.json"
notes = json.loads(notes_path.read_text(encoding="utf-8"))
releases = notes.get("releases", [])
if any(item.get("version") == NEW for item in releases):
    raise RuntimeError(f"release metadata already contains {NEW}")
releases.append({
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Bounded torrent workspace sizing",
    "summary": "Corrects the oversized v0.5.67 torrent workspace so the torrent list and docked details remain comfortably visible together within the desktop/tablet viewport while retaining independent scrolling.",
    "highlights": [
        "The list-only torrent workspace now uses a bounded 44dvh layout capped at 460 px instead of a forced 480 px minimum.",
        "Opening torrent details switches the shared workspace to a bounded 58dvh layout capped at 600 px, keeping both the list and inspector visible together on typical desktop/tablet displays.",
        "The torrent inspector receives roughly 42% of the shared workspace while the torrent list remains the flexible scroll region above it.",
        "The workspace tracks whether details are open so list-only and list-plus-inspector states can use different vertical allocations."
    ],
    "fixes": [
        "Prevents an empty or short torrent list from consuming most of the page height after the v0.5.67 docked-inspector change.",
        "Removes the desktop 480 px minimum height that could push the torrent inspector below the initial viewport."
    ],
    "technical": [
        "The has-detail workspace state is added when a torrent inspector opens and removed when it closes.",
        "Desktop/tablet list and detail bodies retain independent overflow scrolling; mobile keeps the existing bottom-sheet behavior.",
        "DESIGN_LANGUAGE.md now defines a bounded list/inspector viewport contract."
    ],
    "validation": [
        "The UI regression audit rejects the former calc(100dvh - 320px)/480 px minimum-height rule and requires the new bounded workspace values.",
        "Existing backend tests, JavaScript syntax validation, generated release metadata, and frontend/service-worker build synchronization remain release gates."
    ],
    "known_issues": [],
    "architecture": releases[-1].get("architecture", []) if releases else [],
    "decisions": (releases[-1].get("decisions", []) if releases else []) + [
        "Desktop/tablet list-detail workspaces should fit within the initial viewport by default; internal scrolling is preferred over expanding the page vertically."
    ],
    "next_steps": releases[-1].get("next_steps", []) if releases else []
})
notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

# Regenerate checked-in handoff/changelog artifacts.
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)

print(f"Applied v{NEW} bounded torrent workspace sizing")
