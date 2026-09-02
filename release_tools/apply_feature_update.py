#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_OLD = "0.5.71"
VERSION_NEW = "0.5.72"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# --- HTML: make list and inspector separate sibling surfaces; remove collapse. ---
html = read("static/index.html")
html = replace_once(
    html,
    '<section class="torrent-panel torrent-workspace">\n<div class="torrent-list-region">',
    '<div class="torrent-workspace">\n<section class="torrent-panel torrent-list-panel">\n<div class="torrent-list-region">',
    "torrent workspace opening",
)
html = replace_once(
    html,
    '<div class="empty hidden" id="empty"><strong id="emptyTitle">No torrents yet</strong><span id="emptyText">Add a torrent to get started.</span></div>\n</div>\n<section class="torrent-detail-pane hidden"',
    '<div class="empty hidden" id="empty"><strong id="emptyTitle">No torrents yet</strong><span id="emptyText">Add a torrent to get started.</span></div>\n</div>\n</section>\n<section class="torrent-detail-pane hidden"',
    "torrent list panel closing",
)
html = replace_once(
    html,
    '<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><div class="detail-pane-actions"><button class="detail-pane-toggle" id="detailToggle" type="button" aria-expanded="true" aria-label="Collapse torrent details" title="Collapse torrent details"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details" title="Close torrent details">×</button></div></header>',
    '<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><div class="detail-pane-actions"><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details" title="Close torrent details">×</button></div></header>',
    "detail header collapse control",
)
html = replace_once(
    html,
    '<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>\n</section>\n</section>\n</section>\n<section class="view" id="view-notifications">',
    '<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>\n</section>\n</div>\n</section>\n<section class="view" id="view-notifications">',
    "torrent workspace closing",
)
html = html.replace(VERSION_OLD, VERSION_NEW)
write("static/index.html", html)


# --- JavaScript: details are either open or closed; no collapse state. ---
js = read("static/app.js")
js = replace_once(
    js,
    "detailTab:'general',detailCollapsed:localStorage.tdDetailCollapsed==='1',settings:null",
    "detailTab:'general',settings:null",
    "detail collapsed state",
)
js, removed = re.subn(
    r"function syncDetailPaneState\(\)\{.*?\n\}\nasync function toggleDetailPane\(\)\{.*?\n\}\n(?=async function openDetail)",
    "",
    js,
    count=1,
    flags=re.S,
)
if removed != 1:
    raise SystemExit(f"detail collapse functions: expected one block, found {removed}")
js = replace_once(
    js,
    "pane.closest('.torrent-workspace')?.classList.add('has-detail');syncDetailPaneState();syncTorrentWorkspaceLayout();",
    "pane.closest('.torrent-workspace')?.classList.add('has-detail');syncTorrentWorkspaceLayout();",
    "open detail layout state",
)
js = replace_once(
    js,
    "if(!state.detailCollapsed)await refreshDetailData(true);",
    "await refreshDetailData(true);",
    "open detail refresh",
)
js = replace_once(
    js,
    "if(!state.detail||state.detailCollapsed&&!force)return;",
    "if(!state.detail)return;",
    "detail refresh guard",
)
js = replace_once(
    js,
    "$('#detailToggle').addEventListener('click',toggleDetailPane);$('#detailClose').addEventListener('click',closeDetailPane);",
    "$('#detailClose').addEventListener('click',closeDetailPane);",
    "detail event binding",
)
if "detailCollapsed" in js or "tdDetailCollapsed" in js or "toggleDetailPane" in js or "syncDetailPaneState" in js:
    raise SystemExit("collapse state remains in static/app.js")
js = js.replace(f"const FRONTEND_BUILD='{VERSION_OLD}';", f"const FRONTEND_BUILD='{VERSION_NEW}';", 1)
write("static/app.js", js)


# --- CSS: separate list and detail cards while preserving viewport docking. ---
css = read("static/app.css")
old_css = '''/* 0.5.67 docked collapsible torrent details. */
.torrent-list-region{min-width:0;min-height:0}
.detail-pane-actions{display:flex;align-items:center;gap:4px;flex:0 0 auto}
.detail-pane-toggle{width:32px;height:32px;padding:0;border:0;background:transparent;color:var(--muted);display:grid;place-items:center;border-radius:8px}
.detail-pane-toggle:hover,.detail-pane-close:hover{background:var(--panel2);color:var(--text)}
.detail-pane-toggle svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s ease}
.detail-pane-toggle[aria-expanded="true"] svg{transform:rotate(180deg)}
@media(min-width:701px){
  .torrent-workspace{display:flex;flex-direction:column;overflow:hidden;height:min(460px,44dvh)}
  .torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}
  .torrent-list-region{position:relative;display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}
  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}
  .torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center;padding:20px;text-align:center;pointer-events:none}
  .torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:0;max-height:none;border:0;border-top:1px solid var(--border);border-radius:0;box-shadow:none;display:flex;flex:0 0 clamp(240px,48%,420px);flex-direction:column;background:var(--panel)}
  .torrent-detail-header{flex:0 0 auto;border-bottom:1px solid var(--border)}
  .torrent-detail-tabs{flex:0 0 auto}
  .torrent-detail-body{flex:1 1 auto;min-height:0;overflow:auto}
  .torrent-detail-pane.collapsed{flex:0 0 58px!important;min-height:58px!important;max-height:58px!important}
  .torrent-detail-pane.collapsed .torrent-detail-tabs,.torrent-detail-pane.collapsed .torrent-detail-body{display:none}
  .torrent-detail-pane.collapsed .torrent-detail-header{height:58px;border-bottom:0}
}
@media(min-width:1024px){
  .torrent-detail-pane{flex-basis:clamp(300px,48%,440px)}
}
@media(max-width:700px){
  .torrent-detail-pane.collapsed{top:auto!important;height:58px!important;min-height:58px!important;max-height:58px!important}
  .torrent-detail-pane.collapsed .torrent-detail-tabs,.torrent-detail-pane.collapsed .torrent-detail-body{display:none}
  .torrent-detail-pane.collapsed .torrent-detail-header{height:58px;border-bottom:0}
}'''
new_css = '''/* 0.5.72 separated viewport-docked torrent details. */
.torrent-list-region{min-width:0;min-height:0}
.detail-pane-actions{display:flex;align-items:center;flex:0 0 auto}
.detail-pane-close:hover{background:var(--panel2);color:var(--text)}
@media(min-width:701px){
  .torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}
  .torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}
  .torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}
  .torrent-list-region{position:relative;display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}
  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}
  .torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center;padding:20px;text-align:center;pointer-events:none}
  .torrent-detail-pane{position:static;inset:auto;width:auto;height:auto;margin:0;min-height:240px;max-height:none;border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);display:flex;flex:0 1 clamp(260px,46%,420px);flex-direction:column;background:var(--panel);overflow:hidden}
  .torrent-detail-header{flex:0 0 auto;border-bottom:1px solid var(--border);background:var(--panel3)}
  .torrent-detail-tabs{flex:0 0 auto}
  .torrent-detail-body{flex:1 1 auto;min-height:0;overflow:auto}
}
@media(min-width:1024px){
  .torrent-detail-pane{flex-basis:clamp(300px,46%,440px)}
}'''
css = replace_once(css, old_css, new_css, "separated detail CSS")
if ".torrent-detail-pane.collapsed" in css or ".detail-pane-toggle" in css:
    raise SystemExit("obsolete collapse CSS remains")
write("static/app.css", css)


# --- Design/testing contract. ---
design = read("DESIGN_LANGUAGE.md")
old_docked = '''## Docked inspectors

On desktop and tablet layouts, secondary inspection surfaces that describe a selected item should preserve access to the primary list instead of covering it.

- Torrent details dock to the bottom edge of the torrent workspace and share the same outer surface.
- The primary torrent list remains independently scrollable while details are expanded.
- Collapse preserves the current torrent selection and only reduces the inspector to its header; Close clears the inspector entirely.
- Collapse state may be remembered as a user preference, but selecting a torrent must continue to update the docked header even while collapsed.
- Mobile may use a bottom-sheet treatment when the available viewport cannot support a useful split workspace.
'''
new_docked = '''## Docked inspectors

On desktop and tablet layouts, secondary inspection surfaces that describe a selected item should preserve access to the primary list instead of covering it.

- Torrent details dock below the torrent list as a distinct sibling panel rather than visually merging into the table surface.
- The list and inspector should each have their own border, radius, background, and clear spacing so their roles are immediately distinguishable.
- The primary torrent list remains independently scrollable while details are open.
- Torrent details do not collapse. Selecting a torrent opens the inspector; Close clears the detail context and returns the list to its bounded list-only layout.
- Mobile may use a bottom-sheet treatment when the available viewport cannot support a useful split workspace.
'''
design = replace_once(design, old_docked, new_docked, "design docked inspector section")
old_viewport = '''## Viewport-docked desktop inspectors

On non-mobile layouts, a docked list/detail workspace should use the actual remaining viewport rather than a fixed viewport-height guess. When torrent details are open, the shared workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above it, and allocate enough height to the inspector for its primary content to remain legible. Mobile keeps the sheet model.
'''
new_viewport = '''## Viewport-docked desktop inspectors

On non-mobile layouts, a docked list/detail workspace should use the actual remaining viewport rather than a fixed viewport-height guess. When torrent details are open, the workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above a visually separate detail panel, and allocate enough height to the inspector for its primary content to remain legible. The separation between list and inspector is part of the hierarchy, not unused space. Mobile keeps the sheet model.
'''
design = replace_once(design, old_viewport, new_viewport, "design viewport inspector section")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing = replace_once(testing, "- Collapse preserves the selected torrent; Close clears the detail context.", "- Details remain open while a torrent is selected; Close clears the detail context.", "testing collapse behavior")
testing = replace_once(testing, "- Torrent detail sheet can be opened, collapsed, and closed.", "- Torrent detail sheet can be opened and closed.", "mobile testing collapse behavior")
testing = replace_once(
    testing,
    "- Verify the torrent inspector reaches the bottom of the visible dashboard content instead of leaving a large unused gap below it.",
    "- Verify the torrent inspector reaches the bottom of the visible dashboard content and is visually separated from the torrent list as its own bordered panel.",
    "desktop inspector separation test",
)
write("TESTING.md", testing)


# --- UI regression contract follows the new simplified interaction. ---
validator = read("release_tools/validate_ui_strings.py")
old_assertions = '''    assert "pane.closest('.torrent-workspace')?.classList.add('has-detail')" in app_js
    assert "pane.closest('.torrent-workspace')?.classList.remove('has-detail')" in app_js
    assert ".torrent-workspace{display:flex;flex-direction:column;overflow:hidden;height:min(460px,44dvh)}" in app_css
    assert ".torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css
    assert "flex:0 0 clamp(240px,48%,420px)" in app_css
    assert ".torrent-detail-pane{flex-basis:clamp(300px,48%,440px)}" in app_css
    assert "function syncTorrentWorkspaceLayout()" in app_js
    assert "window.innerHeight-top-16" in app_js
    assert "--torrent-workspace-open-height" in app_js
    assert "height:calc(100dvh - 320px);min-height:480px" not in app_css
'''
new_assertions = '''    assert "pane.closest('.torrent-workspace')?.classList.add('has-detail')" in app_js
    assert "pane.closest('.torrent-workspace')?.classList.remove('has-detail')" in app_js
    assert 'class="torrent-workspace"' in html and 'class="torrent-panel torrent-list-panel"' in html
    assert 'id="detailToggle"' not in html and "detailCollapsed" not in app_js and "tdDetailCollapsed" not in app_js
    assert "toggleDetailPane" not in app_js and "syncDetailPaneState" not in app_js
    assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:min(460px,44dvh)}" in app_css
    assert ".torrent-workspace.has-detail{height:var(--torrent-workspace-open-height,min(720px,calc(100dvh - 280px)))}" in app_css
    assert ".torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}" in app_css
    assert "border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);display:flex;flex:0 1 clamp(260px,46%,420px)" in app_css
    assert ".torrent-detail-pane{flex-basis:clamp(300px,46%,440px)}" in app_css
    assert ".torrent-detail-pane.collapsed" not in app_css and ".detail-pane-toggle" not in app_css
    assert "function syncTorrentWorkspaceLayout()" in app_js
    assert "window.innerHeight-top-16" in app_js
    assert "--torrent-workspace-open-height" in app_js
    assert "height:calc(100dvh - 320px);min-height:480px" not in app_css
'''
validator = replace_once(validator, old_assertions, new_assertions, "torrent layout validator")
write("release_tools/validate_ui_strings.py", validator)


# --- Version synchronization. ---
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{VERSION_OLD}"', f'VERSION = "{VERSION_NEW}"', "dashboard version")
write("dashboard.py", dashboard)

sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0571", "torrent-dashboard-v0572")
sw = sw.replace(VERSION_OLD, VERSION_NEW)
write("static/sw.js", sw)


# --- Structured release metadata. ---
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
if any(item.get("version") == VERSION_NEW for item in release_data.get("releases", [])):
    raise SystemExit(f"release {VERSION_NEW} already exists")
release_data["releases"].append({
    "version": VERSION_NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Separated docked torrent details",
    "summary": "Simplifies the torrent inspector into an always-open-on-selection, visually distinct panel below the torrent list while preserving viewport docking and independent scrolling.",
    "highlights": [
        "Torrent list and torrent details are now separate sibling panels with their own borders, radius, background, shadow, and spacing instead of sharing one continuous surface.",
        "Removed the torrent-detail Collapse action and remembered collapse preference; selecting a torrent opens details and Close dismisses them.",
        "The shared workspace still uses the remaining desktop/tablet viewport so the list and detail panel remain visible together, with independent internal scrolling.",
        "Mobile retains the existing bottom-sheet detail presentation without a collapse state."
    ],
    "fixes": [
        "Removes the visually merged list/detail treatment that made the inspector feel like part of the torrent table.",
        "Eliminates an unnecessary inspector state and the refresh-suppression behavior tied to collapse."
    ],
    "technical": [
        "torrent-workspace is now a layout-only wrapper containing torrent-list-panel and torrent-detail-pane sibling surfaces.",
        "Collapse DOM, JavaScript state, localStorage preference, CSS selectors, event bindings, and regression assertions were removed together.",
        "Viewport-derived workspace sizing from v0.5.71 remains in place."
    ],
    "validation": [
        "The UI contract requires separate list/detail surfaces, rejects collapse controls/state/selectors, and preserves viewport-derived docking and independent scrolling.",
        "JavaScript syntax, frontend/service-worker version synchronization, backend tests, architecture validation, and generated release/handoff consistency remain release gates."
    ],
    "known_issues": [],
    "architecture": [
        "Torrent Dashboard remains a Python standard-library application with dashboard.py as the HTTP composition root.",
        "Configuration, integrations, users, and configuration transaction coordination remain separated into torrent_dashboard package modules.",
        "Torrent detail presentation remains frontend-owned and continues to use the existing /api/detail contract.",
        "Desktop/tablet use separate docked list and detail panels; mobile uses a bottom-sheet presentation."
    ],
    "decisions": [
        "Prefer two visually distinct surfaces for list/detail hierarchy rather than joining them with only an internal divider.",
        "Do not expose Collapse when the detail inspector is already bounded, scrollable, and dismissible with Close.",
        "Keep viewport-derived docking and independent list/detail scrolling.",
        "Keep active backend modularization work separate from this presentation correction."
    ],
    "next_steps": [
        {"priority": 1, "title": "Extract release and update provenance", "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py."},
        {"priority": 2, "title": "Extract qBitTorrent transport and normalization", "detail": "Move QBitClient, server normalization, proxy/preference translation, and Web API transport away from HTTP routing."},
        {"priority": 3, "title": "Expand request-level behavioral tests", "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around extracted service boundaries."},
        {"priority": 4, "title": "Harden secrets at rest", "detail": "Use the configuration boundary to add restrictive file permissions and separate ordinary configuration from stored credentials."}
    ]
})
release_path.write_text(json.dumps(release_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate public release/handoff artifacts from authored sources.
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_NEW], cwd=ROOT, check=True)

print(f"Staged Torrent Dashboard v{VERSION_NEW}: separated docked torrent detail panels")
