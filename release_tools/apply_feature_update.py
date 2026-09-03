from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.110"
PREVIOUS = "0.5.109"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing transform anchor: {label}")
    return text.replace(old, new, 1)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")

anchor = """function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane');if(!pane)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  pane.classList.toggle('detail-general-fit',fitGeneral);
  pane.style.removeProperty('--torrent-detail-expanded-height');
}
function syncMobileBulkbarOffset(){"""
replacement = """function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane');if(!pane)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  pane.classList.toggle('detail-general-fit',fitGeneral);
  pane.style.removeProperty('--torrent-detail-expanded-height');
}
function revealDesktopTorrentWorkspace(){
  const workspace=$('.torrent-workspace');if(!workspace||!window.matchMedia('(min-width:701px)').matches)return;
  const top=Math.max(0,Math.round(workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)-8));
  if(Math.abs((window.scrollY||window.pageYOffset||0)-top)<8)return;
  const behavior=window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  window.scrollTo({top,behavior});
}
function syncMobileBulkbarOffset(){"""
app_js = replace_once(app_js, anchor, replacement, "desktop workspace reveal helper")

old_toggle = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}"""
new_toggle = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace);
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}"""
app_js = replace_once(app_js, old_toggle, new_toggle, "detail disclosure reveal")

old_open = """async function openDetail(server,hash){
  const same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  syncDetailDock();$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}"""
new_open = """async function openDetail(server,hash){
  const wasExpanded=state.detailExpanded,same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  syncDetailDock();if(!wasExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace);$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}"""
app_js = replace_once(app_js, old_open, new_open, "torrent row detail reveal")
write("static/app.js", app_js)

index = read("static/index.html").replace(PREVIOUS, VERSION)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05109", "torrent-dashboard-v05110").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Document the interaction contract without changing the v0.5.109 sizing model.
design = read("DESIGN_LANGUAGE.md")
design += """

### Desktop Torrent details viewport reveal

The fixed desktop torrent-list height and natural-height General detail model remain unchanged. The dashboard header, metrics, and filter controls are ordinary document content above the torrent workspace and must not be folded into a new detail-height calculation. When a user explicitly expands Torrent details from a collapsed state on desktop/tablet, the document should reveal the torrent workspace at the top of the viewport so those preceding panels scroll out naturally. This reproduces the useful manual-scroll state without shrinking the torrent list or reintroducing an inner General scrollbar. Respect reduced-motion preferences and do not force this reveal repeatedly while the detail pane is already expanded.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Desktop Torrent details viewport reveal

- Start at the top of Dashboard with the page heading, metrics, and filters visible. Open Torrent details from its collapsed disclosure and verify the document scrolls the torrent workspace to the top of the viewport while preserving the existing torrent-list height.
- Repeat by opening a torrent row while Torrent details is collapsed; the same workspace reveal should occur.
- With Torrent details already expanded, switch torrents and detail tabs and verify the page is not repeatedly forced back to the workspace top.
- Verify General retains its natural document height and no inner scrollbar is reintroduced; Trackers, Peers, HTTP sources, and Content retain their existing bounded scrolling.
- Enable reduced-motion preference and verify the reveal is immediate rather than animated.
- Repeat at mobile width and verify the mobile bottom-sheet behavior does not invoke desktop document scrolling.
"""
write("TESTING.md", testing)

# Add release metadata while preserving the recorded backend objective.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.append("Reveal the desktop torrent workspace when Torrent details is explicitly opened from a collapsed state instead of resizing the list/detail surfaces around the header and metrics stack.")
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Desktop detail viewport reveal",
        "summary": "Keeps the v0.5.109 torrent-list and General-detail sizing intact while automatically revealing the torrent workspace when desktop Torrent details is opened beneath the dashboard header and summary panels.",
        "highlights": [
            "Opening collapsed Torrent details now scrolls the desktop torrent workspace into view so the header, metrics, and filter panels no longer consume the useful detail viewport.",
            "Opening a torrent while the inspector is collapsed performs the same one-time workspace reveal.",
            "The existing fixed torrent-list height and natural-height General detail behavior remain unchanged."
        ],
        "fixes": [
            "Matches the layout users previously reached only after manually scrolling past the Dashboard header and summary panels.",
            "Avoids solving the viewport issue by shrinking the torrent list or adding a General detail scrollbar."
        ],
        "technical": [
            "Adds revealDesktopTorrentWorkspace(), which scrolls to the stable torrent-workspace document position only on desktop/tablet.",
            "The reveal runs when the disclosure changes from collapsed to expanded; switching torrents while already expanded does not retrigger it.",
            "The scroll behavior honors prefers-reduced-motion by using immediate positioning when reduced motion is requested."
        ],
        "validation": [
            "The UI audit asserts the desktop-only reveal helper, reduced-motion handling, one-time row-open behavior, unchanged list-height calculation, and matching design/testing documentation.",
            "Manual coverage starts with header/metrics visible, opens details through both disclosure and torrent row paths, verifies no repeated forced scrolling, and checks unchanged mobile behavior.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

validator = read("release_tools/validate_ui_strings.py")
insert = """    # 0.5.110 reveals the fixed desktop torrent workspace when details open beneath top-of-page chrome.\n    assert 'function revealDesktopTorrentWorkspace()' in app_js\n    assert \"workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)-8\" in app_js\n    assert \"window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'\" in app_js\n    assert 'if(state.detailExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace)' in app_js\n    assert 'const wasExpanded=state.detailExpanded' in app_js and 'if(!wasExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace)' in app_js\n    assert \"const available=Math.max(360,Math.min(560,Math.floor(window.innerHeight-documentTop-16)))\" in app_js\n    assert 'Desktop Torrent details viewport reveal' in design\n    assert 'Desktop Torrent details viewport reveal' in testing\n\n"""
validator = replace_once(validator, '    print("UI string audit passed")\n', insert + '    print("UI string audit passed")\n', "UI audit footer")
write("release_tools/validate_ui_strings.py", validator)

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION], cwd=ROOT, check=True)
print(f"Applied v{VERSION} desktop Torrent details viewport reveal")
