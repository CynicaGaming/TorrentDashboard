from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.111"
PREVIOUS = "0.5.110"


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
old_layout = """function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-list-height');return}
  const documentTop=Math.max(0,workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0));
  const available=Math.max(360,Math.min(560,Math.floor(window.innerHeight-documentTop-16)));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-list-height')!==value)workspace.style.setProperty('--torrent-list-height',value);
}"""
new_layout = """const TORRENT_DESKTOP_VISIBLE_ROWS=6;
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
app_js = replace_once(app_js, old_layout, new_layout, "six-row torrent list sizing")
write("static/app.js", app_js)

app_css = read("static/app.css")
old_panel = ".torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,clamp(360px,52vh,560px));height:var(--torrent-list-height,clamp(360px,52vh,560px));min-height:360px;overflow:hidden}"
new_panel = ".torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}"
app_css = replace_once(app_css, old_panel, new_panel, "six-row torrent list fallback")
write("static/app.css", app_css)

index = read("static/index.html").replace(PREVIOUS, VERSION)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05110", "torrent-dashboard-v05111").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Record the fixed six-row desktop viewport contract.
design = read("DESIGN_LANGUAGE.md")
design += """

### Six-row desktop torrent viewport

The desktop torrent list is a deterministic data viewport rather than a remainder of the browser viewport. Its height is the rendered torrent-table header plus exactly six normal torrent rows, including the current density's row height and the panel border allowance. Header, metric, filter, login/profile, and Torrent details geometry must not change that list height. If fewer than six rows are visible, leaving unused whitespace in the list is acceptable. If more than six rows are visible, the list scrolls internally. Torrent details remains a separate surface below the list; General may use natural document height while long-data tabs retain bounded internal scrolling.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Six-row desktop torrent viewport

- At desktop width with seven or more visible torrents, verify the torrent list shows exactly six complete torrent rows plus the table header and scrolls internally for the remaining rows.
- Switch between comfortable and compact density and verify the list recomputes from the rendered row height so both densities still expose six complete rows rather than a fixed pixel count.
- Filter the list to fewer than six torrents and verify the list height remains unchanged; blank space at the bottom is acceptable.
- Scroll the document past the Dashboard heading, metrics, and filters, then back to the top and verify the torrent-list height never changes.
- Expand/collapse Torrent details and switch General/Trackers/Peers/HTTP sources/Content; verify the torrent-list height remains unchanged and the existing detail scrolling contracts remain intact.
- Repeat at mobile width and verify the six-row desktop sizing rule is not applied to mobile torrent cards.
"""
write("TESTING.md", testing)

# Add release metadata while preserving the recorded backend objective.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.append("Size the desktop torrent list from one rendered row and the table header so exactly six rows are visible, independent of surrounding Dashboard panels or viewport remainder.")
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Six-row desktop torrent viewport",
        "summary": "Makes the desktop torrent list a deterministic six-row scroll viewport instead of deriving its height from the remaining browser viewport below Dashboard panels.",
        "highlights": [
            "The desktop torrent list now measures its table header and rendered row height and reserves exactly six torrent rows.",
            "Comfortable and compact density both retain a six-row viewport because sizing follows the live row-height token.",
            "Fewer than six torrents may leave harmless whitespace; additional torrents stay behind the list's existing internal scrollbar."
        ],
        "fixes": [
            "Removes the last dependency between torrent-list height and the Dashboard header, metrics, filters, or current document scroll position.",
            "Keeps Torrent details and page scrolling from changing the torrent-list viewport height."
        ],
        "technical": [
            "syncTorrentWorkspaceLayout now calculates headerHeight + rowHeight * 6 + the panel border allowance from rendered geometry.",
            "When no torrent row is currently rendered, the --row design token supplies the row-height fallback.",
            "The desktop CSS fallback is a fixed normal-density six-row estimate until the first JavaScript geometry synchronization; mobile remains unaffected."
        ],
        "validation": [
            "The UI audit asserts the six-row constant, rendered header/row measurement, removal of viewport-remainder sizing, the non-growing list panel, and matching design/testing documentation.",
            "Manual coverage verifies exactly six complete rows in comfortable and compact density, stable whitespace with fewer rows, internal scrolling with more rows, document-scroll stability, and unchanged mobile behavior.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

validator = read("release_tools/validate_ui_strings.py")
old_assert = '    assert "const available=Math.max(360,Math.min(560,Math.floor(window.innerHeight-documentTop-16)))" in app_js\n'
validator = validator.replace(old_assert, "")
insert = """    # 0.5.111 makes the desktop torrent list an exact six-row viewport.\n    assert 'const TORRENT_DESKTOP_VISIBLE_ROWS=6;' in app_js\n    assert \"const table=$('#torrentTable'),firstRow=$('#torrentRows tr');\" in app_js\n    assert \"parseFloat(rootStyle.getPropertyValue('--row'))||62\" in app_js\n    assert \"table?.tHead?.getBoundingClientRect().height||34\" in app_js\n    assert \"firstRow?.getBoundingClientRect().height||fallbackRow\" in app_js\n    assert 'headerHeight+(rowHeight*TORRENT_DESKTOP_VISIBLE_ROWS)+2' in app_js\n    assert 'window.innerHeight-documentTop-16' not in app_js\n    assert '.torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,456px);height:var(--torrent-list-height,456px);min-height:0;overflow:hidden}' in app_css\n    assert 'Six-row desktop torrent viewport' in design\n    assert 'Six-row desktop torrent viewport' in testing\n\n"""
validator = replace_once(validator, '    print("UI string audit passed")\n', insert + '    print("UI string audit passed")\n', "UI audit footer")
write("release_tools/validate_ui_strings.py", validator)

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION], cwd=ROOT, check=True)
print(f"Applied v{VERSION} six-row desktop torrent viewport")
