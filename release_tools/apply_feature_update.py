#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.107"
NEW = "0.5.108"


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


replace_once(
    "static/app.css",
    ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 clamp(260px,46%,420px)}",
    ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 var(--torrent-detail-expanded-height,clamp(260px,46%,420px))}",
)
replace_once(
    "static/app.css",
    ".torrent-detail-pane:not(.collapsed){flex-basis:clamp(300px,46%,440px)}",
    ".torrent-detail-pane:not(.collapsed){flex-basis:var(--torrent-detail-expanded-height,clamp(300px,46%,440px))}",
)

app = read("static/app.js")
needle = "function syncMobileBulkbarOffset(){\n"
helper = """function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane'),workspace=pane?.closest('.torrent-workspace'),body=$('#detailBody');if(!pane||!workspace||!body)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  if(!fitGeneral){pane.style.removeProperty('--torrent-detail-expanded-height');return}
  const handle=$('#detailHandle'),tabs=pane.querySelector('.torrent-detail-tabs');
  const chrome=(handle?.offsetHeight||0)+(tabs?.offsetHeight||0)+2,desired=Math.ceil(chrome+body.scrollHeight+4);
  const listReserve=180,gap=12,maxHeight=Math.max(300,(workspace.clientHeight||0)-listReserve-gap),target=Math.min(maxHeight,Math.max(300,desired));
  pane.style.setProperty('--torrent-detail-expanded-height',`${target}px`);
}
function syncMobileBulkbarOffset(){
"""
if needle not in app or "function syncDesktopDetailPaneHeight()" in app:
    raise RuntimeError("Could not locate unique desktop detail sizing insertion point")
app = app.replace(needle, helper, 1)

old_resize = "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout();syncMobileBulkbarOffset()}));"
new_resize = "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}));"
if old_resize not in app:
    raise RuntimeError("Could not find window resize layout synchronizer")
app = app.replace(old_resize, new_resize, 1)

old_render = "function renderDetail(){if(!state.detail?.data)return;const d=state.detail.data,p=d.properties||{},t=detailCurrentTorrent()||{};if(state.detailTab==='general')renderDetailGeneral(t,p);else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='webseeds')renderWebSeeds(d.webseeds||[]);else renderFiles(d.files||[])}"
new_render = "function renderDetail(){if(!state.detail?.data)return;const d=state.detail.data,p=d.properties||{},t=detailCurrentTorrent()||{};if(state.detailTab==='general')renderDetailGeneral(t,p);else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='webseeds')renderWebSeeds(d.webseeds||[]);else renderFiles(d.files||[]);requestAnimationFrame(syncDesktopDetailPaneHeight)}"
if old_render not in app:
    raise RuntimeError("Could not find renderDetail dispatcher")
app = app.replace(old_render, new_render, 1)

old_dock = "syncTorrentWorkspaceLayout();requestAnimationFrame(syncMobileBulkbarOffset);setTimeout(syncMobileBulkbarOffset,180);"
new_dock = "syncTorrentWorkspaceLayout();requestAnimationFrame(()=>{syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()});setTimeout(()=>{syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()},180);"
if old_dock not in app:
    raise RuntimeError("Could not find detail dock synchronizer")
app = app.replace(old_dock, new_dock, 1)

old_view = "if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout);"
new_view = "if(dashboardView)requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();syncDesktopDetailPaneHeight()});"
if old_view not in app:
    raise RuntimeError("Could not find dashboard view layout synchronizer")
app = app.replace(old_view, new_view, 1)
write("static/app.js", app)

replace_once("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
replace_once("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
index = read("static/index.html")
if OLD not in index:
    raise RuntimeError("static/index.html does not contain the previous frontend version")
write("static/index.html", index.replace(OLD, NEW))
sw = read("static/sw.js")
old_cache = f"v{OLD.replace('.', '')}"
new_cache = f"v{NEW.replace('.', '')}"
if old_cache not in sw or OLD not in sw:
    raise RuntimeError("static/sw.js is not synchronized to the previous version")
write("static/sw.js", sw.replace(old_cache, new_cache).replace(OLD, NEW))

design = read("DESIGN_LANGUAGE.md")
design_note = """

### Content-fit desktop Torrent details

The desktop torrent workspace remains a fixed bounded surface. When Torrent details is expanded on the finite General tab, the detail pane should measure its rendered content and claim enough height inside that fixed workspace to show the complete General view without an unnecessary inner scrollbar whenever the viewport can accommodate it. Preserve a usable torrent-list slice and its independent scrollbar. Potentially unbounded tabs such as Trackers, Peers, HTTP sources, and Content remain bounded and independently scrollable rather than expanding the workspace or consuming the entire torrent list.
"""
if "### Content-fit desktop Torrent details" not in design:
    write("DESIGN_LANGUAGE.md", design.rstrip() + design_note + "\n")

testing = read("TESTING.md")
testing_note = """

### Desktop Torrent details content-fit sizing

- On a normal desktop viewport, open Torrent details → General and verify the full General content is visible without scrolling the detail body when there is sufficient workspace height.
- Verify expanding General takes space from the torrent list inside the existing fixed workspace; the overall workspace height must remain unchanged and the torrent list must retain its own scrollbar.
- Collapse and re-expand Torrent details and verify the content-fit height is restored without layout growth or page-scroll coupling.
- Switch from General to Peers, Trackers, HTTP sources, and Content with long datasets and verify those tabs use the normal bounded detail height and their own internal scrolling rather than expanding to their full dataset height.
- Resize the browser vertically and verify General recalculates its fitted height while retaining a usable torrent-list region. On unusually short desktop viewports, detail-body scrolling is acceptable once the reserved list region prevents the full General content from fitting.
- Repeat at mobile width and verify the existing bottom-sheet behavior is unchanged.
"""
if "### Desktop Torrent details content-fit sizing" not in testing:
    write("TESTING.md", testing.rstrip() + testing_note + "\n")

validator = read("release_tools/validate_ui_strings.py")
old_detail_assert = '    assert ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 clamp(260px,46%,420px)}" in app_css\n'
new_detail_assert = '    assert ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 var(--torrent-detail-expanded-height,clamp(260px,46%,420px))}" in app_css\n'
if old_detail_assert not in validator:
    raise RuntimeError("Could not find fixed desktop detail-pane assertion")
validator = validator.replace(old_detail_assert, new_detail_assert, 1)
old_view_assert = '    assert "if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout)" in app_js\n'
new_view_assert = '    assert "if(dashboardView)requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();syncDesktopDetailPaneHeight()})" in app_js\n'
if old_view_assert not in validator:
    raise RuntimeError("Could not find dashboard workspace callback assertion")
validator = validator.replace(old_view_assert, new_view_assert, 1)
anchor = '    assert "window.innerHeight-top-16" not in app_js\n'
checks = (
    anchor
    + '    assert "function syncDesktopDetailPaneHeight()" in app_js\n'
    + '    assert "state.detailTab===\'general\'" in app_js\n'
    + '    assert "body.scrollHeight" in app_js\n'
    + '    assert "listReserve=180" in app_js\n'
    + '    assert "--torrent-detail-expanded-height" in app_js\n'
    + '    assert "var(--torrent-detail-expanded-height,clamp(260px,46%,420px))" in app_css\n'
    + '    assert "var(--torrent-detail-expanded-height,clamp(300px,46%,440px))" in app_css\n'
    + '    assert "Content-fit desktop Torrent details" in design_language\n'
    + '    assert "Desktop Torrent details content-fit sizing" in testing_md\n'
)
if anchor not in validator:
    raise RuntimeError("Could not find stable workspace validation anchor")
validator = validator.replace(anchor, checks, 1)
write("release_tools/validate_ui_strings.py", validator)

meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta.get("releases")
if not isinstance(releases, list) or not releases:
    raise RuntimeError("release_notes/releases.json has no releases list")
if any(str(item.get("version")) == NEW for item in releases if isinstance(item, dict)):
    raise RuntimeError(f"Release metadata for {NEW} already exists")
previous = releases[-1] if isinstance(releases[-1], dict) else {}
entry = {
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Content-fit desktop Torrent details",
    "summary": "Expands the finite desktop General detail view to its rendered content height inside the fixed torrent workspace so routine torrent properties can be read without an unnecessary inner scrollbar.",
    "highlights": [
        "Fits the expanded desktop General tab to its complete rendered content whenever the current workspace has enough room.",
        "Takes the additional height from the torrent-list region while keeping the overall torrent workspace fixed and preserving the list's independent scrollbar.",
        "Keeps Peers, Trackers, HTTP sources, and Content bounded and independently scrollable because those datasets can be arbitrarily long."
    ],
    "fixes": [
        "Removes routine detail-body scrolling from the desktop General tab on normal-height viewports.",
        "Avoids solving the issue with a single oversized hard-coded pane height that would waste list space on smaller or larger desktops."
    ],
    "technical": [
        "syncDesktopDetailPaneHeight measures the General detail body's scrollHeight plus the detail handle/tab chrome and writes a desktop-only --torrent-detail-expanded-height value.",
        "The fitted height reserves 180 px for the torrent list plus the existing workspace gap; if the viewport is too short to fit both, General retains normal internal scrolling rather than collapsing the list.",
        "Non-General tabs clear the fitted-height override and fall back to the existing bounded desktop detail flex basis."
    ],
    "validation": [
        "The UI audit asserts content measurement, General-only fitting, the reserved torrent-list slice, CSS variable fallback, and matching design/testing documentation.",
        "Manual desktop coverage checks a fully readable General tab, stable overall workspace height, preserved list scrolling, bounded long-data tabs, viewport resizing, collapse/reopen behavior, and unchanged mobile presentation.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": []
}
for key in ("decisions", "next_steps"):
    value = previous.get(key)
    if isinstance(value, list) and value:
        entry[key] = value
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW],
    cwd=ROOT,
    check=True,
)

print(f"Applied v{NEW} content-fit desktop Torrent details")
