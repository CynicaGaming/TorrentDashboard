from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.113"
PREVIOUS = "0.5.112"


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

old_layout = """const TORRENT_DESKTOP_PREFERRED_ROWS=6;
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
new_layout = """const TORRENT_DESKTOP_LIST_VIEWPORT_RATIO=.44;
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
  const borderAllowance=2,minListHeight=headerHeight+(rowHeight*TORRENT_DESKTOP_MIN_ROWS)+borderAllowance;
  const preferredListBudget=Math.max(minListHeight,Math.floor(viewportBudget*TORRENT_DESKTOP_LIST_VIEWPORT_RATIO));
  const fitListBudget=Math.max(0,viewportBudget-paneHeight-gap);
  const targetListBudget=Math.min(preferredListBudget,fitListBudget);
  const wholeRows=Math.max(TORRENT_DESKTOP_MIN_ROWS,Math.floor((targetListBudget-headerHeight-borderAllowance)/rowHeight));
  const available=headerHeight+(rowHeight*wholeRows)+borderAllowance;
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-list-height')!==value)workspace.style.setProperty('--torrent-list-height',value);
}"""
app_js = replace_once(app_js, old_layout, new_layout, "viewport-proportional torrent list sizing")
write("static/app.js", app_js)

index = read("static/index.html").replace(PREVIOUS, VERSION)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05112", "torrent-dashboard-v05113").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Document the viewport-proportional contract.
design = read("DESIGN_LANGUAGE.md")
design += """

### Viewport-proportional desktop torrent workspace

The expanded desktop torrent workspace should preserve the visual balance established by the v0.5.112 layout across different monitor heights. The torrent list prefers roughly 44% of the usable viewport remaining below the workspace's stable document position, while Torrent details receives the rest. The split is not a hard percentage: the rendered detail pane has priority, and the list shrinks when necessary so finite General content remains fully readable. The list height is always snapped to complete rendered torrent rows with a three-row minimum, and taller viewports may expose more than six rows instead of leaving unnecessary dead space. Document scrolling must not change the calculation; browser height and density changes may recompute it.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Viewport-proportional desktop torrent workspace

- At the reported approximately 771 px desktop viewport, expand General and verify the torrent list occupies roughly the same visual share as the accepted reference layout (about 44% of the usable workspace) while General remains fully visible.
- Repeat at common desktop heights such as 768/800, 900, 1080, 1200, 1440, and taller displays; verify the list scales with the usable viewport instead of stopping at six rows on large screens.
- Verify the detail pane has priority over the preferred ratio: if General needs more height, the list reduces to the largest whole-row height that preserves the detail content, with three rows as the minimum desktop list.
- Verify the list height is always the table header plus a whole number of rendered rows; no partial torrent row may be clipped at the bottom.
- Switch comfortable/compact density and resize the browser height; verify the proportional target is recalculated from live row/header/detail measurements.
- Scroll the document without resizing and verify one-second polling does not change the list height merely because the workspace moved within the viewport.
- Verify Trackers, Peers, HTTP sources, and Content retain their bounded/internal-scroll behavior and mobile remains unchanged.
"""
write("TESTING.md", testing)

# Add release metadata while preserving the active backend objective.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.append("Prefer a viewport-proportional desktop torrent list at roughly 44% of the usable workspace, but let rendered Torrent details content override that preference and always snap the list to complete rows.")
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Viewport-proportional desktop workspace",
        "summary": "Preserves the accepted torrent-list/detail balance across monitor heights by making the desktop list a viewport-proportional preference rather than a six-row preference.",
        "highlights": [
            "The desktop torrent list now prefers about 44% of the usable viewport below the workspace start, matching the accepted reference layout.",
            "Taller displays can show more than six complete torrent rows instead of leaving a large unused area.",
            "Torrent details remains authoritative: General can take additional height and force the list smaller whenever its rendered content requires it."
        ],
        "fixes": [
            "Avoids the v0.5.112 six-row ceiling making large desktop monitors look disproportionately empty.",
            "Keeps short and tall monitors visually consistent without returning to fixed-pixel workspace sizing.",
            "Preserves whole-row torrent geometry while adapting to viewport height and density."
        ],
        "technical": [
            "syncTorrentWorkspaceLayout derives a preferred list budget from 44% of the stable usable viewport, then caps it by the space remaining after the rendered detail pane and workspace gap.",
            "The target budget is quantized to the live rendered torrent-row height with a three-row minimum; there is no six-row maximum.",
            "The existing stable document-top calculation prevents document scrolling from feeding back into live list sizing."
        ],
        "validation": [
            "The UI audit asserts the 44% viewport preference, detail-first fit cap, whole-row quantization, absence of the six-row ceiling, and stable document-coordinate budgeting.",
            "Manual coverage spans common desktop viewport heights, density changes, document scrolling, General and long-data detail tabs, and unchanged mobile behavior.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

validator = read("release_tools/validate_ui_strings.py")
old_tail = """    # 0.5.112 adapts the preferred six-row list to the real remaining desktop viewport.
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
    assert app_js.count(\"window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}))\") == 1
    assert 'function revealDesktopTorrentWorkspace()' not in app_js
    assert 'requestAnimationFrame(revealDesktopTorrentWorkspace)' not in app_js
    assert '.torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}' in app_css
    assert 'Adaptive desktop torrent viewport fit' in design
    assert 'Adaptive desktop torrent viewport fit' in testing
"""
new_tail = """    # 0.5.113 preserves the accepted desktop list/detail balance with a viewport-proportional preference.
    assert 'const TORRENT_DESKTOP_LIST_VIEWPORT_RATIO=.44;' in app_js
    assert 'const TORRENT_DESKTOP_MIN_ROWS=3;' in app_js
    assert 'const TORRENT_DESKTOP_BOTTOM_GAP=12;' in app_js
    assert 'TORRENT_DESKTOP_PREFERRED_ROWS' not in app_js
    assert \"const table=$('#torrentTable'),firstRow=$('#torrentRows tr'),pane=$('#torrentDetailPane');\" in app_js
    assert \"workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0)\" in app_js
    assert 'window.innerHeight-documentTop-TORRENT_DESKTOP_BOTTOM_GAP' in app_js
    assert \"pane?.getBoundingClientRect().height||0\" in app_js
    assert 'viewportBudget*TORRENT_DESKTOP_LIST_VIEWPORT_RATIO' in app_js
    assert 'viewportBudget-paneHeight-gap' in app_js
    assert 'Math.min(preferredListBudget,fitListBudget)' in app_js
    assert 'Math.floor((targetListBudget-headerHeight-borderAllowance)/rowHeight)' in app_js
    assert 'Math.max(TORRENT_DESKTOP_MIN_ROWS' in app_js
    assert \"pane.style.removeProperty('--torrent-detail-expanded-height');\\n  syncTorrentWorkspaceLayout();\" in app_js
    assert app_js.count(\"window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}))\") == 1
    assert '.torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}' in app_css
    assert 'Viewport-proportional desktop torrent workspace' in design
    assert 'Viewport-proportional desktop torrent workspace' in testing
"""
validator = replace_once(validator, old_tail, new_tail, "viewport-proportional UI validation")
write("release_tools/validate_ui_strings.py", validator)

# Regenerate derived public continuity/release files from structured metadata.
subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", VERSION], cwd=ROOT, check=True)

print("Applied v0.5.113 viewport-proportional desktop workspace")
