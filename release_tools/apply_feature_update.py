from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.109"
PREVIOUS = "0.5.108"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing transform anchor: {label}")
    return text.replace(old, new, 1)


# Version/build synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard VERSION")
write("dashboard.py", dashboard)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")

pattern = re.compile(
    r"function syncTorrentWorkspaceLayout\(\)\{.*?\n\}\nfunction syncDesktopDetailPaneHeight\(\)\{.*?\n\}\nfunction syncMobileBulkbarOffset\(\)\{",
    re.S,
)
replacement = """function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-list-height');return}
  const documentTop=Math.max(0,workspace.getBoundingClientRect().top+(window.scrollY||window.pageYOffset||0));
  const available=Math.max(360,Math.min(560,Math.floor(window.innerHeight-documentTop-16)));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-list-height')!==value)workspace.style.setProperty('--torrent-list-height',value);
}
function syncDesktopDetailPaneHeight(){
  const pane=$('#torrentDetailPane');if(!pane)return;
  const fitGeneral=window.matchMedia('(min-width:701px)').matches&&state.detailExpanded&&state.detailTab==='general'&&!!state.detail?.data;
  pane.classList.toggle('detail-general-fit',fitGeneral);
  pane.style.removeProperty('--torrent-detail-expanded-height');
}
function syncMobileBulkbarOffset(){"""
app_js, count = pattern.subn(replacement, app_js, count=1)
if count != 1:
    raise RuntimeError("failed to replace desktop torrent/detail sizing functions")
write("static/app.js", app_js)

app_css = read("static/app.css")
app_css = replace_once(
    app_css,
    "/* 0.5.74 bottom-anchored client workspace. */",
    "/* 0.5.74 bottom-anchored client workspace. */\n/* 0.5.109 fixed desktop torrent list with natural-height General details. */",
    "desktop workspace marker",
)
app_css = replace_once(
    app_css,
    ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height,min(720px,calc(100dvh - 220px)))}",
    ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:auto}",
    "workspace fixed-height rule",
)
app_css = replace_once(
    app_css,
    ".torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}",
    ".torrent-list-panel{display:flex;flex:0 0 var(--torrent-list-height,clamp(360px,52vh,560px));height:var(--torrent-list-height,clamp(360px,52vh,560px));min-height:360px;overflow:hidden}",
    "torrent list flex rule",
)
app_css = replace_once(
    app_css,
    ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 var(--torrent-detail-expanded-height,clamp(260px,46%,420px))}",
    ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 0 clamp(260px,46vh,420px)}\n  .torrent-detail-pane:not(.collapsed).detail-general-fit{min-height:0;flex:0 0 auto}\n  .torrent-detail-pane.detail-general-fit .torrent-detail-body{flex:0 0 auto;min-height:0;overflow:visible}",
    "desktop detail basis",
)
app_css = replace_once(
    app_css,
    ".torrent-detail-pane:not(.collapsed){flex-basis:var(--torrent-detail-expanded-height,clamp(300px,46%,440px))}",
    ".torrent-detail-pane:not(.collapsed){flex-basis:clamp(300px,46vh,440px)}",
    "wide desktop detail basis",
)
app_css += "\n.brand-mark img{display:block;width:100%;height:100%;object-fit:contain;border-radius:inherit}\n"
write("static/app.css", app_css)

index = read("static/index.html").replace(PREVIOUS, VERSION)
index = replace_once(
    index,
    '<link href="/manifest.webmanifest" rel="manifest"/>',
    '<link href="/manifest.webmanifest" rel="manifest"/>\n<link href="/static/favicon.svg" rel="icon" type="image/svg+xml"/>',
    "favicon link",
)
index = index.replace('<div class="brand-mark">⇣</div>', '<div class="brand-mark"><img alt="" aria-hidden="true" src="/static/favicon.svg"/></div>')
index = index.replace('<span class="brand-mark" aria-hidden="true">⇣</span>', '<span class="brand-mark" aria-hidden="true"><img alt="" src="/static/favicon.svg"/></span>')
write("static/index.html", index)

manifest = json.loads(read("static/manifest.webmanifest"))
manifest["icons"] = [{"src": "/static/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}]
write("static/manifest.webmanifest", json.dumps(manifest, indent=2) + "\n")

favicon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Torrent Dashboard">
  <defs>
    <linearGradient id="bg" x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
      <stop stop-color="#172a43"/><stop offset="1" stop-color="#08111d"/>
    </linearGradient>
    <linearGradient id="accent" x1="18" y1="12" x2="46" y2="52" gradientUnits="userSpaceOnUse">
      <stop stop-color="#65d7ff"/><stop offset="1" stop-color="#4f7cff"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#bg)" stroke="#335b8d" stroke-width="2"/>
  <circle cx="28" cy="29" r="15" fill="#0a1626" stroke="#315b91" stroke-width="3"/>
  <path d="M25 17h6v13h6.5L28 40 18.5 30H25V17Z" fill="url(#accent)"/>
  <path d="M28 10a19 19 0 0 1 18 13" fill="none" stroke="#55b8ff" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="28" cy="10" r="3.5" fill="#65d7ff"/><circle cx="47" cy="26" r="3.5" fill="#4f91ff"/><circle cx="12" cy="29" r="3.5" fill="#4f91ff"/>
  <rect x="43" y="39" width="4" height="9" rx="2" fill="#315b91"/><rect x="49" y="35" width="4" height="13" rx="2" fill="#4f91ff"/><rect x="55" y="31" width="4" height="17" rx="2" fill="#65d7ff"/>
  <rect x="11" y="51" width="42" height="5" rx="2.5" fill="#1a2c44"/><rect x="11" y="51" width="29" height="5" rx="2.5" fill="url(#accent)"/>
</svg>'''
write("static/favicon.svg", favicon + "\n")

sw = read("static/sw.js").replace("torrent-dashboard-v05108", "torrent-dashboard-v05109").replace(PREVIOUS, VERSION)
sw = replace_once(sw, "'/manifest.webmanifest']", "'/manifest.webmanifest','/static/favicon.svg']", "service-worker favicon asset")
write("static/sw.js", sw)

# Current design/testing contracts supersede the shared-height v0.5.108 compromise.
design = read("DESIGN_LANGUAGE.md")
design += """

### Fixed torrent list and natural-height desktop details

This supersedes the earlier shared-height desktop workspace compromise. On desktop/tablet, the torrent list owns a stable bounded height and its own vertical scrollbar; opening Torrent details must not resize that list. The finite General detail view may extend the document below the list and should use its natural content height so routine properties are readable without an inner scrollbar. Potentially unbounded detail tabs such as Trackers, Peers, HTTP sources, and Content remain bounded and internally scrollable. Page scrolling may move the combined list/detail surfaces through the viewport, but must not change the torrent list height. Torrent Dashboard branding and browser/PWA iconography remain local assets with no external runtime dependency.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Fixed desktop torrent list with natural General details

- On desktop, record the torrent list height, scroll the page, open/collapse Torrent details, and switch tabs; the torrent list height must remain unchanged and the list must retain its own scrollbar.
- Open Torrent details → General and verify the full General content is readable without scrolling the detail body. The page may become taller and use normal document scrolling below the fixed torrent list.
- Switch to Trackers, Peers, HTTP sources, and Content with long datasets and verify those tabs remain bounded and use their own detail-body scrolling rather than expanding to their entire dataset height.
- Resize the desktop viewport and verify the torrent list recalculates only within the 360–560 px bounded range; ordinary page scrolling must not alter the chosen height.
- Verify `/static/favicon.svg` is used as the browser favicon, is listed in the web manifest, is included in the service-worker shell, and the same local mark appears in the setup/login/sidebar brand surfaces.
- Repeat at mobile width and verify the existing mobile torrent cards and bottom-sheet Torrent details behavior are unchanged.
"""
write("TESTING.md", testing)

# Release metadata, inheriting the accumulated decisions and preserving the recorded backend next objective.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.extend([
        "Keep the desktop torrent list as the stable bounded scroll surface; finite General details may extend document height instead of competing with the list for one shared height.",
        "Keep potentially unbounded Torrent details tabs bounded and internally scrollable while General uses natural content height on desktop.",
        "Keep browser/PWA branding self-contained with a local favicon/logo asset and no external icon dependency.",
    ])
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Fixed desktop list and natural Torrent details",
        "summary": "Keeps the desktop torrent list at a stable internally scrollable height while allowing the finite General detail view to expand naturally below it, and adds a self-contained Torrent Dashboard favicon/logo.",
        "highlights": [
            "Decouples desktop torrent-list height from Torrent details so opening General no longer steals vertical space from the list.",
            "Lets the General tab expand to its complete natural content height and rely on normal page scrolling instead of an unnecessary inner scrollbar.",
            "Adds a locally hosted Torrent Dashboard SVG favicon/logo and reuses it in browser/PWA and existing brand surfaces.",
        ],
        "fixes": [
            "Removes the v0.5.108 shared-workspace cap that still left General too shallow on shorter desktop viewports.",
            "Preserves a stable 360–560 px torrent-list region across page scrolling and detail expansion while long detail datasets retain their own scrolling.",
        ],
        "technical": [
            "syncTorrentWorkspaceLayout now writes a bounded --torrent-list-height derived from the workspace's stable document position; the workspace itself uses natural document height.",
            "syncDesktopDetailPaneHeight now toggles a General-only detail-general-fit mode instead of calculating a competing pane height budget.",
            "Desktop General removes detail-body overflow and grows naturally; Trackers, Peers, HTTP sources, and Content keep the existing bounded flex basis and internal overflow.",
            "The favicon is a local SVG included in index.html, manifest.webmanifest, the service-worker shell, and the setup/login/sidebar brand marks.",
        ],
        "validation": [
            "The UI audit asserts fixed torrent-list sizing, natural General detail flow, bounded long-data tabs, local favicon wiring, and matching design/testing documentation.",
            "Manual desktop coverage verifies list-height stability across page scrolling/detail disclosure, complete General readability, long-tab scrolling, viewport resize bounds, and unchanged mobile behavior.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required.",
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

# Replace obsolete validator assumptions with the current contract and add favicon assertions.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace(
    'assert "--torrent-workspace-height" in app_js and "--torrent-workspace-open-height" not in app_js',
    'assert "--torrent-list-height" in app_js and "--torrent-workspace-height" not in app_js and "--torrent-workspace-open-height" not in app_js',
)
validator = validator.replace(
    'assert "const available=Math.max(360,Math.floor(window.innerHeight-documentTop-16))" in app_js',
    'assert "const available=Math.max(360,Math.min(560,Math.floor(window.innerHeight-documentTop-16)))" in app_js',
)
anchor = '    # 0.5.106 gives Trackers and Peers dedicated responsive detail records.\n'
new_assertions = '''    # 0.5.109 decouples the fixed desktop torrent list from finite General detail height.\n    assert "workspace.style.removeProperty('--torrent-list-height')" in app_js\n    assert "workspace.style.setProperty('--torrent-list-height',value)" in app_js\n    assert "pane.classList.toggle('detail-general-fit',fitGeneral)" in app_js\n    assert 'listReserve=180' not in app_js and 'Math.min(maxHeight,Math.max(300,desired))' not in app_js\n    assert '0.5.109 fixed desktop torrent list with natural-height General details' in app_css\n    assert '.torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:auto}' in app_css\n    assert 'flex:0 0 var(--torrent-list-height,clamp(360px,52vh,560px))' in app_css\n    assert '.torrent-detail-pane:not(.collapsed).detail-general-fit{min-height:0;flex:0 0 auto}' in app_css\n    assert '.torrent-detail-pane.detail-general-fit .torrent-detail-body{flex:0 0 auto;min-height:0;overflow:visible}' in app_css\n    assert 'Fixed torrent list and natural-height desktop details' in design\n    assert 'Fixed desktop torrent list with natural General details' in testing\n    assert '<link href="/static/favicon.svg" rel="icon" type="image/svg+xml"/>' in html\n    assert 'src="/static/favicon.svg"' in html\n    assert (ROOT / 'static' / 'favicon.svg').exists()\n    manifest = (ROOT / 'static' / 'manifest.webmanifest').read_text(encoding='utf-8')\n    assert '"src": "/static/favicon.svg"' in manifest and '"type": "image/svg+xml"' in manifest\n    sw = (ROOT / 'static' / 'sw.js').read_text(encoding='utf-8')\n    assert "'/static/favicon.svg'" in sw\n\n'''
if new_assertions not in validator:
    if anchor not in validator:
        raise RuntimeError("validator insertion anchor missing")
    validator = validator.replace(anchor, new_assertions + anchor, 1)
write("release_tools/validate_ui_strings.py", validator)

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION], cwd=ROOT, check=True)
print(f"Applied v{VERSION} fixed desktop list, natural General details, and favicon")
