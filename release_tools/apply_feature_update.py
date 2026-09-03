from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.112"
PREVIOUS = "0.5.111"


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

old_layout = """const TORRENT_DESKTOP_VISIBLE_ROWS=6;
function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-list-height');return}
  const table=$('#torrentTable'),firstRow=$('#torrentRows tr');
  const rootStyle=getComputedStyle(document.documentElement);
  const fallbackRow=Math.max(1,parseFloat(rootStyle.getPropertyValue('--row'))||62);
  const headerHeight=Math.max(1,Math.ceil(table?.tHead?.getBoundingClientRect().height||34));
  const rowHeight=Math.max(1,Math.ceil(firstRow?.getBoundingClientRect().height||fallbackRow));
  const available=headerHeight+(rowHeight*TORRENT_DESKTOP_VISIBLE_ROWS)+2;
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-list-height')!==value)workspace.style.setProperty('--torrent-list-height',value);
}"""
new_layout = """const TORRENT_DESKTOP_PREFERRED_ROWS=6;
const TORRENT_DESKTOP_MIN_ROWS=3;
const TORRENT_DESKTOP_BOTTOM_GAP=12;
function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const desktop=window.matchMedia('(min-width:701px)').matches;
  if(!desktop||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-list-height');return}
  const table=$('#torrentTable'),firstRow=$('#torrentRows tr'),pane=$('#torrentDetailPane');
  const rootStyle=getComputedStyle(document.documentElement),workspaceStyle=getComputedStyle(workspace);
  const fallbackRow=Math.max(1,parseFloat(rootStyle.getPropertyValue('--row'))||62);
  const headerHeight=Math.max(1,Math.ceil(table?.tHead?.getBoundingClientRect().height||34));
  const rowHeight=Math.max(1,Math.ceil(firstRow?.getBoundingClientRect().height||fallbackRow));
  const documentTop=Math.max(0,Math.ceil(workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)));
  const viewportBudget=Math.max(0,Math.floor(window.innerHeight-documentTop-TORRENT_DESKTOP_BOTTOM_GAP));
  const gap=Math.max(0,parseFloat(workspaceStyle.rowGap||workspaceStyle.gap)||12);
  const paneHeight=Math.max(0,Math.ceil(pane?.getBoundingClientRect().height||0));
  const borderAllowance=2,rawListBudget=Math.max(0,viewportBudget-paneHeight-gap);
  const wholeRows=Math.max(TORRENT_DESKTOP_MIN_ROWS,Math.min(TORRENT_DESKTOP_PREFERRED_ROWS,Math.floor((rawListBudget-headerHeight-borderAllowance)/rowHeight)));
  const available=headerHeight+(rowHeight*wholeRows)+borderAllowance;
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-list-height')!==value)workspace.style.setProperty('--torrent-list-height',value);
}"""
app_js = replace_once(app_js, old_layout, new_layout, "adaptive torrent list viewport sizing")

old_detail_sync = """function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane');if(!pane)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  pane.classList.toggle('detail-general-fit',fitGeneral);
  pane.style.removeProperty('--torrent-detail-expanded-height');
}"""
new_detail_sync = """function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane');if(!pane)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  pane.classList.toggle('detail-general-fit',fitGeneral);
  pane.style.removeProperty('--torrent-detail-expanded-height');
  syncTorrentWorkspaceLayout();
}"""
app_js = replace_once(app_js, old_detail_sync, new_detail_sync, "detail-to-list viewport resync")

old_reveal = """function revealDesktopTorrentWorkspace(){
  const workspace=$('.torrent-workspace');if(!workspace||!window.matchMedia('(min-width:701px)').matches)return;
  const top=Math.max(0,Math.round(workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)-8));
  if(Math.abs((window.scrollY||window.pageYOffset||0)-top)<8)return;
  const behavior=window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  window.scrollTo({top,behavior});
}
"""
app_js = replace_once(app_js, old_reveal, "", "retired desktop workspace reveal")

old_toggle = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace);
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}"""
new_toggle = """async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}"""
app_js = replace_once(app_js, old_toggle, new_toggle, "detail disclosure without forced scroll")

old_open = """async function openDetail(server,hash){
  const wasExpanded=state.detailExpanded,same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  syncDetailDock();if(!wasExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace);$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}"""
new_open = """async function openDetail(server,hash){
  const same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  syncDetailDock();$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}"""
app_js = replace_once(app_js, old_open, new_open, "torrent row detail without forced scroll")

old_prefs = """function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyFixedTorrentColumnLayout()}"""
new_prefs = """function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyFixedTorrentColumnLayout();requestAnimationFrame(syncDesktopDetailPaneHeight)}"""
app_js = replace_once(app_js, old_prefs, new_prefs, "density-aware viewport resync")

old_bind_tail = """  if(state.me?.can_manage)TDSettings.bind();
  window.addEventListener('keydown',e=>"""
new_bind_tail = """  if(state.me?.can_manage)TDSettings.bind();
  window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}));
  window.addEventListener('keydown',e=>"""
app_js = replace_once(app_js, old_bind_tail, new_bind_tail, "desktop viewport resize synchronization")
write("static/app.js", app_js)

index = read("static/index.html").replace(PREVIOUS, VERSION)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05111", "torrent-dashboard-v05112").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Document the adaptive viewport-fit contract.
design = read("DESIGN_LANGUAGE.md")
design += """

### Adaptive desktop torrent viewport fit

The desktop torrent list uses six rows as a preferred maximum, not an unconditional fixed height. The dashboard computes a stable viewport budget from the torrent workspace's document position and the browser height, then subtracts the currently rendered Torrent details pane and the workspace gap. The remaining space is snapped down to a whole number of rendered torrent rows, with three rows as the minimum useful desktop list. This keeps the expanded General pane and the torrent list inside the original top-of-page viewport whenever the available geometry permits, without making the list react to document scrolling. General remains natural-height; long-data detail tabs retain their bounded internal scrolling. Opening Torrent details must not force the document to scroll because the layout itself is responsible for fitting the workspace.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Adaptive desktop torrent viewport fit

- At the top of the Dashboard on a viewport around 840 px tall, expand General and verify the page keeps the Dashboard heading, metrics, filters, torrent list, and complete General pane inside the viewport when the measured geometry permits it; the list should reduce from six rows to the largest whole-row count that fits.
- Verify the torrent list never shows a clipped partial row: its height must be the rendered table header plus an integer number of rendered torrent rows.
- Resize the browser taller and shorter and verify the list moves between three and six whole rows as needed while General retains natural height.
- Switch between comfortable and compact density and verify the row calculation is recomputed from the live rendered row height.
- Scroll the document after sizing and verify the torrent-list height does not grow or shrink merely because the workspace's viewport-relative top changed.
- Expand/collapse Torrent details and switch General/Trackers/Peers/HTTP sources/Content; verify the list recomputes against the rendered detail-pane height and long-data tabs keep their internal scrolling.
- Opening Torrent details from the disclosure or a torrent row must not automatically scroll the document.
- Repeat at mobile width and verify the adaptive desktop rule does not alter the mobile bottom sheet or torrent cards.
"""
write("TESTING.md", testing)

# Add release metadata while preserving the recorded backend objective.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.append("Treat six desktop torrent rows as a preferred maximum and size the list from the stable viewport budget remaining after the actual rendered Torrent details pane.")
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Adaptive desktop viewport fit",
        "summary": "Reconciles viewport sizing with whole-row torrent geometry so the desktop list shrinks below six rows when the expanded detail pane would otherwise push the Dashboard past the viewport.",
        "highlights": [
            "The torrent list now uses up to six complete rows, reducing to the largest whole-row count that fits beside the actual rendered Torrent details pane.",
            "Viewport budgeting uses the workspace's stable document position, so ordinary document scrolling cannot make the torrent list resize during live polling.",
            "Opening Torrent details no longer forces a document scroll; the layout itself is responsible for fitting the visible Dashboard stack."
        ],
        "fixes": [
            "Prevents the six-row list plus natural-height General pane from extending below shorter desktop viewports such as the reported approximately 840 px layout.",
            "Avoids partial torrent rows by snapping the calculated list budget to complete rendered rows.",
            "Recomputes after density changes and browser resize using live rendered header, row, gap, and detail-pane measurements."
        ],
        "technical": [
            "syncTorrentWorkspaceLayout derives a stable viewport budget from window.innerHeight minus the workspace document top and a 12 px bottom allowance.",
            "The current Torrent details pane height and flex gap are subtracted before the remaining list budget is quantized between three and six rows.",
            "syncDesktopDetailPaneHeight now resynchronizes list geometry after General switches between bounded and natural-height modes, and desktop resize/density changes trigger the same measurement path."
        ],
        "validation": [
            "The UI audit asserts stable-document viewport budgeting, measured detail/gap subtraction, whole-row quantization, three-to-six-row bounds, density/resize resynchronization, and removal of forced workspace scrolling.",
            "Manual coverage includes an approximately 840 px-tall viewport, density changes, browser resize, document scrolling, all detail tabs, collapse/expand behavior, and unchanged mobile layout.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

validator = read("release_tools/validate_ui_strings.py")
old_tail = """    # 0.5.110 reveals the fixed desktop torrent workspace when details open beneath top-of-page chrome.
    assert 'function revealDesktopTorrentWorkspace()' in app_js
    assert \"workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)-8\" in app_js
    assert \"window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'\" in app_js
    assert 'if(state.detailExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace)' in app_js
    assert 'const wasExpanded=state.detailExpanded' in app_js and 'if(!wasExpanded)requestAnimationFrame(revealDesktopTorrentWorkspace)' in app_js
    assert 'Desktop Torrent details viewport reveal' in design
    assert 'Desktop Torrent details viewport reveal' in testing

    # 0.5.111 makes the desktop torrent list an exact six-row viewport.
    assert 'const TORRENT_DESKTOP_VISIBLE_ROWS=6;' in app_js
    assert \"const table=$('#torrentTable'),firstRow=$('#torrentRows tr');\" in app_js
    assert \"parseFloat(rootStyle.getPropertyValue('--row'))||62\" in app_js
    assert \"table?.tHead?.getBoundingClientRect().height||34\" in app_js
    assert \"firstRow?.getBoundingClientRect().height||fallbackRow\" in app_js
    assert 'headerHeight+(rowHeight*TORRENT_DESKTOP_VISIBLE_ROWS)+2' in app_js
    assert 'window.innerHeight-documentTop-16' not in app_js
    assert '.torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}' in app_css
    assert 'Six-row desktop torrent viewport' in design
    assert 'Six-row desktop torrent viewport' in testing

"""
new_tail = """    # 0.5.112 adapts the preferred six-row list to the real remaining desktop viewport.
    assert 'const TORRENT_DESKTOP_PREFERRED_ROWS=6;' in app_js
    assert 'const TORRENT_DESKTOP_MIN_ROWS=3;' in app_js
    assert 'const TORRENT_DESKTOP_BOTTOM_GAP=12;' in app_js
    assert \"const table=$('#torrentTable'),firstRow=$('#torrentRows tr'),pane=$('#torrentDetailPane');\" in app_js
    assert \"parseFloat(rootStyle.getPropertyValue('--row'))||62\" in app_js
    assert \"table?.tHead?.getBoundingClientRect().height||34\" in app_js
    assert \"firstRow?.getBoundingClientRect().height||fallbackRow\" in app_js
    assert \"workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)\" in app_js
    assert 'window.innerHeight-documentTop-TORRENT_DESKTOP_BOTTOM_GAP' in app_js
    assert 'parseFloat(workspaceStyle.rowGap||workspaceStyle.gap)||12' in app_js
    assert \"pane?.getBoundingClientRect().height||0\" in app_js
    assert 'viewportBudget-paneHeight-gap' in app_js
    assert 'Math.floor((rawListBudget-headerHeight-borderAllowance)/rowHeight)' in app_js
    assert 'Math.max(TORRENT_DESKTOP_MIN_ROWS,Math.min(TORRENT_DESKTOP_PREFERRED_ROWS' in app_js
    assert \"pane.style.removeProperty('--torrent-detail-expanded-height');\\n  syncTorrentWorkspaceLayout();\" in app_js
    assert \"requestAnimationFrame(syncDesktopDetailPaneHeight)\" in app_js
    assert \"window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}))\" in app_js
    assert 'function revealDesktopTorrentWorkspace()' not in app_js
    assert 'requestAnimationFrame(revealDesktopTorrentWorkspace)' not in app_js
    assert '.torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}' in app_css
    assert 'Adaptive desktop torrent viewport fit' in design
    assert 'Adaptive desktop torrent viewport fit' in testing

"""
validator = replace_once(validator, old_tail, new_tail, "adaptive viewport UI audit")
write("release_tools/validate_ui_strings.py", validator)

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION], cwd=ROOT, check=True)
print(f"Applied v{VERSION} adaptive desktop viewport fit")
