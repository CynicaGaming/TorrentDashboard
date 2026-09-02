#!/usr/bin/env python3
"""Stage v0.5.71 viewport-docked torrent inspector correction."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.71"
PREVIOUS = "0.5.70"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, content: str) -> None:
    (ROOT / rel).write_text(content, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one occurrence in {rel}: {old!r}")
    write(rel, text.replace(old, new, 1))


# Version synchronization.
replace_once("dashboard.py", f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"')
index = read("static/index.html")
if index.count(PREVIOUS) < 5:
    raise RuntimeError("static/index.html did not contain expected version references")
write("static/index.html", index.replace(PREVIOUS, VERSION))
replace_once("static/app.js", f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';")
sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0570", "torrent-dashboard-v0571").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Desktop/tablet workspace: keep list-only behavior bounded, but when details are
# open size the shared workspace to the actual remaining viewport instead of a
# fixed dvh guess. Give the inspector enough height to be useful.
css = read("static/app.css")
old = ".torrent-workspace.has-detail{height:min(600px,58dvh)}"
new = ".torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}"
if css.count(old) != 1:
    raise RuntimeError("Expected v0.5.68 open-workspace rule")
css = css.replace(old, new, 1)
old = "flex:0 0 clamp(180px,42%,290px)"
new = "flex:0 0 clamp(240px,48%,420px)"
if css.count(old) != 1:
    raise RuntimeError("Expected base torrent detail flex allocation")
css = css.replace(old, new, 1)
old = ".torrent-detail-pane{flex-basis:clamp(200px,42%,310px)}"
new = ".torrent-detail-pane{flex-basis:clamp(300px,48%,440px)}"
if css.count(old) != 1:
    raise RuntimeError("Expected desktop torrent detail flex allocation")
css = css.replace(old, new, 1)
write("static/app.css", css)

# Add viewport-aware workspace sizing and invoke it whenever layout-relevant
# state changes. It intentionally does nothing on mobile where the sheet model
# remains authoritative.
app = read("static/app.js")
anchor = "function emptyStateCopy(){"
if app.count(anchor) != 1:
    raise RuntimeError("Could not find emptyStateCopy anchor")
helper = r'''function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');
  if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  const hasDetail=workspace.classList.contains('has-detail');
  if(mobile||!hasDetail){workspace.style.removeProperty('--torrent-workspace-open-height');return}
  if(!$('#view-dashboard')?.classList.contains('active'))return;
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(320,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-open-height')!==value)workspace.style.setProperty('--torrent-workspace-open-height',value);
}
window.addEventListener('resize',()=>requestAnimationFrame(syncTorrentWorkspaceLayout));

'''
app = app.replace(anchor, helper + anchor, 1)
old = "const pane=$('#torrentDetailPane');pane.classList.remove('hidden');pane.closest('.torrent-workspace')?.classList.add('has-detail');syncDetailPaneState();"
new = "const pane=$('#torrentDetailPane');pane.classList.remove('hidden');pane.closest('.torrent-workspace')?.classList.add('has-detail');syncDetailPaneState();syncTorrentWorkspaceLayout();"
if app.count(old) != 1:
    raise RuntimeError("Could not find openDetail layout transition")
app = app.replace(old, new, 1)
old = "function closeDetailPane(){const pane=$('#torrentDetailPane');pane.classList.add('hidden');pane.closest('.torrent-workspace')?.classList.remove('has-detail');state.detail=null;render()}"
new = "function closeDetailPane(){const pane=$('#torrentDetailPane');pane.classList.add('hidden');pane.closest('.torrent-workspace')?.classList.remove('has-detail');syncTorrentWorkspaceLayout();state.detail=null;render()}"
if app.count(old) != 1:
    raise RuntimeError("Could not find closeDetailPane")
app = app.replace(old, new, 1)
old = "$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}"
new = "$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters();syncTorrentWorkspaceLayout()}"
if app.count(old) != 1:
    raise RuntimeError("Could not find render layout tail")
app = app.replace(old, new, 1)
write("static/app.js", app)

# Lock the corrected layout into the UI contract.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace(
    'assert ".torrent-workspace.has-detail{height:min(600px,58dvh)}" in app_css',
    'assert ".torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css',
)
validator = validator.replace(
    'assert "flex:0 0 clamp(180px,42%,290px)" in app_css',
    'assert "flex:0 0 clamp(240px,48%,420px)" in app_css\n    assert ".torrent-detail-pane{flex-basis:clamp(300px,48%,440px)}" in app_css\n    assert "function syncTorrentWorkspaceLayout()" in app_js\n    assert "window.innerHeight-top-16" in app_js\n    assert "--torrent-workspace-open-height" in app_js',
)
write("release_tools/validate_ui_strings.py", validator)

# Durable layout and testing guidance.
design = read("DESIGN_LANGUAGE.md")
addition = """

## Viewport-docked desktop inspectors

On non-mobile layouts, a docked list/detail workspace should use the actual remaining viewport rather than a fixed viewport-height guess. When torrent details are open, the shared workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above it, and allocate enough height to the inspector for its primary content to remain legible. Mobile keeps the sheet model.
"""
if "## Viewport-docked desktop inspectors" not in design:
    write("DESIGN_LANGUAGE.md", design.rstrip() + addition + "\n")

testing = read("TESTING.md")
needle = "torrent"
if "torrent inspector reaches the bottom of the visible dashboard" not in testing.lower():
    write("TESTING.md", testing.rstrip() + "\n\n### Desktop torrent inspector\n\n- With a torrent selected at normal desktop zoom, verify the torrent list and inspector both remain visible without scrolling the overall page.\n- Verify the torrent inspector reaches the bottom of the visible dashboard content instead of leaving a large unused gap below it.\n- Verify General, Trackers, Peers, HTTP Sources, and Content have a useful vertical viewport and scroll internally when needed.\n- Resize the browser and verify the dock recalculates without overlapping the viewport; mobile continues to use the bottom-sheet presentation.\n")

# Add structured release metadata. Active development remains the release-
# provenance extraction recorded in development/current.json after this UI fix.
notes_path = ROOT / "release_notes" / "releases.json"
data = json.loads(notes_path.read_text(encoding="utf-8"))
if any(str(x.get("version")) == VERSION for x in data.get("releases", [])):
    raise RuntimeError(f"Release metadata already contains v{VERSION}")
latest = max(data["releases"], key=lambda x: tuple(int(p) for p in x["version"].split('.')))
entry = {
    "version": VERSION,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Viewport-docked torrent inspector",
    "summary": "Corrects the desktop torrent details layout so the inspector docks to the bottom of the visible dashboard and receives enough vertical space to remain useful while the torrent list scrolls above it.",
    "highlights": [
        "When torrent details are open on desktop/tablet, the shared torrent workspace now measures its actual viewport position and fills the remaining visible height instead of using a fixed 58dvh estimate.",
        "The detail inspector receives a larger desktop allocation, preventing General and table-based detail tabs from being compressed into a shallow strip.",
        "The torrent list remains the flexible scroll region above the inspector, while the detail body scrolls independently when its content exceeds the available inspector height.",
        "List-only sizing remains bounded and mobile retains the existing bottom-sheet behavior."
    ],
    "fixes": [
        "Removes the large unused area below the torrent inspector visible on tall desktop viewports.",
        "Prevents the docked detail pane from appearing visually squashed after the earlier bounded-workspace correction."
    ],
    "technical": [
        "syncTorrentWorkspaceLayout() derives the open workspace height from window.innerHeight minus the workspace's current top coordinate, making the layout resilient to metric/control heights and browser resizing.",
        "The viewport-derived height is stored as a CSS custom property so CSS continues to own the list/detail flex split and mobile breakpoint behavior."
    ],
    "validation": [
        "The UI contract now requires viewport-derived open-workspace sizing, the enlarged inspector allocation, and removal of the former fixed 58dvh open-workspace rule.",
        "TESTING.md now includes manual desktop inspector checks for bottom docking, usable detail height, internal scrolling, resize behavior, and mobile preservation."
    ],
    "known_issues": [],
    "architecture": latest.get("architecture", []),
    "decisions": list(latest.get("decisions", [])) + [
        "Size an open desktop list/detail workspace from its actual viewport position rather than relying on a fixed dvh approximation."
    ],
    "next_steps": latest.get("next_steps", [])
}
data["releases"].append(entry)
notes_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", VERSION], cwd=ROOT, check=True)
print(f"Staged Torrent Dashboard v{VERSION} viewport-docked torrent inspector")
