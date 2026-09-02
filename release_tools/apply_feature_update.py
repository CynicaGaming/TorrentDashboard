#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.74"
NEW = "0.5.75"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Restore the standard Dashboard heading while preserving bottom-anchored details.
html = read("static/index.html")
html = replace_once(html, '<header class="topbar dashboard-mode" id="topbar">', '<header class="topbar" id="topbar">', "dashboard topbar")
html = replace_once(
    html,
    '<span class="torrent-detail-handle-label">Torrent details</span><span class="torrent-detail-handle-selection" id="detailHandleSelection">No torrent selected</span>',
    '<span class="torrent-detail-handle-label">Torrent details</span><span class="torrent-detail-handle-selection" id="detailHandleSelection"></span>',
    "detail disclosure helper",
)
html = replace_once(
    html,
    '<div class="torrent-detail-context"><strong id="detailName">No torrent selected</strong><span id="detailMeta">Select a torrent to view details.</span></div>',
    '<div class="torrent-detail-context"><strong id="detailName"></strong><span id="detailMeta">Select a torrent to view details.</span></div>',
    "detail empty context",
)
html = replace_once(
    html,
    '<div class="torrent-detail-body" id="detailBody"><div class="empty detail-empty"><strong>No torrent selected</strong><span>Select a torrent to view details.</span></div></div>',
    '<div class="torrent-detail-body" id="detailBody"><div class="empty detail-empty"><span>Select a torrent to view details.</span></div></div>',
    "initial detail body",
)
html = html.replace(OLD, NEW)
write("static/index.html", html)


app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = app_js.replace("$('#topbar')?.classList.toggle('dashboard-mode',dashboardView);", "")
app_js = replace_once(
    app_js,
    'function detailEmptyMarkup(){return \'<div class="empty detail-empty"><strong>No torrent selected</strong><span>Select a torrent to view details.</span></div>\'}',
    'function detailEmptyMarkup(){return \'<div class="empty detail-empty"><span>Select a torrent to view details.</span></div>\'}',
    "detail empty markup",
)
app_js = replace_once(
    app_js,
    "handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?($('#detailName')?.textContent||'Selected torrent'):'No torrent selected';",
    "handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?($('#detailName')?.textContent||'Selected torrent'):'';",
    "detail disclosure state",
)
app_js = replace_once(
    app_js,
    "state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='No torrent selected';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='No torrent selected';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();render();",
    "state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();render();",
    "detail reset state",
)
if "No torrent selected" in app_js or "classList.toggle('dashboard-mode'" in app_js:
    raise SystemExit("obsolete dashboard/detail presentation state remains in app.js")
write("static/app.js", app_js)


# Entering Updates is passive. The explicit Check for updates action owns GitHub freshness.
settings_js = read("static/settings.js")
settings_js = settings_js.replace("  let updateIntegrityRefreshAt = 0;\n  let updateIntegrityRefreshPromise = null;\n", "")
auto_refresh = """    if (page === 'updates' && state.settings && typeof checkForUpdates === 'function') {\n      const now = Date.now();\n      if (!updateIntegrityRefreshPromise && now - updateIntegrityRefreshAt > 60000) {\n        updateIntegrityRefreshAt = now;\n        updateIntegrityRefreshPromise = Promise.resolve()\n          .then(() => checkForUpdates(true))\n          .catch(() => null)\n          .finally(() => { updateIntegrityRefreshPromise = null; });\n      }\n    }\n"""
if settings_js.count(auto_refresh) != 1:
    raise SystemExit(f"Updates auto-check block: expected one match, found {settings_js.count(auto_refresh)}")
settings_js = settings_js.replace(auto_refresh, "", 1)
if "updateIntegrityRefreshAt" in settings_js or "updateIntegrityRefreshPromise" in settings_js or "checkForUpdates(true)" in settings_js:
    raise SystemExit("automatic Updates-page check remains")
write("static/settings.js", settings_js)


css = read("static/app.css")
for rule in (
    ".topbar.dashboard-mode{justify-content:flex-end;margin-bottom:12px}\n",
    ".topbar.dashboard-mode .topbar-heading{display:none}\n",
    "  .topbar.dashboard-mode{margin-bottom:14px}\n",
    "  .topbar.dashboard-mode{justify-content:flex-end;margin-bottom:10px}\n",
):
    css = css.replace(rule, "")
if ".topbar.dashboard-mode" in css:
    raise SystemExit("dashboard-mode CSS remains")
css += "\n/* 0.5.75 dashboard hierarchy and detail disclosure cleanup. */\n.torrent-detail-handle-selection:empty{display:none}\n"
write("static/app.css", css)


design = read("DESIGN_LANGUAGE.md")
old_design_section = """## Client-style dashboard chrome\n\nOn the Dashboard view, navigation already establishes location, so the redundant Dashboard title/subtitle is hidden while server, torrent-control, and account actions remain visible. On desktop/tablet, the torrent workspace fills the actual remaining viewport so the persistent Torrent details disclosure stays anchored to the bottom. Collapsed it reads as a compact client-style bar; expanded it grows upward while the torrent list scrolls above it.\n"""
new_design_section = """## Client-style dashboard workspace\n\nThe Dashboard retains its page title and short activity subtitle for visual hierarchy and orientation. Navigation also establishes location, but removing the heading does not materially increase usable torrent space and weakens the page hierarchy. On desktop/tablet, the torrent workspace fills the actual remaining viewport so the persistent Torrent details disclosure stays anchored to the bottom. Collapsed it reads as a compact client-style bar; expanded it grows upward while the torrent list scrolls above it.\n"""
design = replace_once(design, old_design_section, new_design_section, "client-style dashboard design section")
design += """\n\n## Explicit update checks\n\nSettings → Updates must not initiate a GitHub network check merely because the page is opened. Cached/local release information may render immediately, but freshness is user-directed through the Check for updates action. This keeps network activity predictable and preserves a clear distinction between viewing update settings and requesting an update check.\n\nWhen the Torrent details disclosure has no selected torrent, the compact handle should remain visually quiet: show only the stable Torrent details label and disclosure affordance. Selection-specific copy appears only when a torrent is actually selected.\n"""
write("DESIGN_LANGUAGE.md", design)


testing = read("TESTING.md")
testing = testing.replace(
    "- On Dashboard at desktop/tablet width, verify the redundant Dashboard / Live torrent activity heading is not visible and the server/action/account controls remain aligned at the top.\n",
    "- On Dashboard at desktop/tablet width, verify Dashboard / Live torrent activity is visible and the server/action/account controls remain aligned in the same top bar.\n",
)
testing += """\n\n### Update-check intent and empty detail disclosure\n\n- Open Settings → Updates and verify no GitHub update request is initiated solely by entering the page; cached/local release history may render immediately.\n- Press Check for updates and verify the normal GitHub update lookup occurs and refreshes update/release-integrity information.\n- With no torrent selected, verify the collapsed Torrent details bar contains no “No torrent selected” helper text.\n- Select a torrent and verify the selected torrent name may appear in the disclosure context and the inspector expands normally.\n"""
write("TESTING.md", testing)


# Update both early and historical UI contracts without replacing large blocks.
validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace(
    'assert ".topbar.dashboard-mode .topbar-heading{display:none}" in app_css',
    'assert ".topbar.dashboard-mode .topbar-heading{display:none}" not in app_css',
)
validator = validator.replace(
    "assert '.topbar.dashboard-mode .topbar-heading{display:none}' in app_css",
    "assert '.topbar.dashboard-mode .topbar-heading{display:none}' not in app_css",
)
validator = validator.replace(
    "    # 0.5.74 bottom-anchors the persistent disclosure and removes redundant Dashboard chrome.\n",
    "    # 0.5.75 retains bottom anchoring, restores Dashboard hierarchy, quiets the empty disclosure, and makes update checks explicit.\n",
)
validator = validator.replace(
    "assert 'id=\"topbar\"' in html and 'class=\"topbar dashboard-mode\"' in html and 'class=\"topbar-heading\"' in html",
    "assert 'id=\"topbar\"' in html and 'class=\"topbar\" id=\"topbar\"' in html and 'class=\"topbar-heading\"' in html",
)
validator = validator.replace(
    'assert "$(\'#topbar\')?.classList.toggle(\'dashboard-mode\',dashboardView)" in app_js',
    'assert "classList.toggle(\'dashboard-mode\'" not in app_js',
)
validator = validator.replace(
    "assert '.topbar.dashboard-mode{justify-content:flex-end;margin-bottom:12px}' in app_css",
    "assert '.topbar.dashboard-mode' not in app_css",
)
validator = validator.replace(
    "assert '## Client-style dashboard chrome' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
    "assert '## Client-style dashboard workspace' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
)
anchor = "    assert '### Bottom-anchored torrent dock' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"
extra = """    assert 'class=\"topbar dashboard-mode\"' not in html\n    assert 'id=\"detailHandleSelection\"></span>' in html\n    assert 'No torrent selected' not in html and 'No torrent selected' not in app_js\n    assert '.torrent-detail-handle-selection:empty{display:none}' in app_css\n    assert 'updateIntegrityRefreshAt' not in settings_js and 'updateIntegrityRefreshPromise' not in settings_js\n    assert 'checkForUpdates(true)' not in settings_js\n    assert '## Explicit update checks' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert '### Update-check intent and empty detail disclosure' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"""
if validator.count(anchor) != 1:
    raise SystemExit(f"testing-contract anchor: expected one match, found {validator.count(anchor)}")
validator = validator.replace(anchor, anchor + extra, 1)
if "class=\"topbar dashboard-mode\"' in html" in validator or "Client-style dashboard chrome" in validator:
    raise SystemExit("superseded v0.5.74 dashboard validator remains")
write("release_tools/validate_ui_strings.py", validator)


dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0574", "torrent-dashboard-v0575", "service-worker cache")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)


meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(r.get("version") == NEW for r in releases):
    raise SystemExit(f"release {NEW} already exists")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Dashboard hierarchy and explicit update checks",
    "summary": "Restores the Dashboard heading, quiets the empty Torrent details disclosure, and makes GitHub update checks explicitly user-initiated.",
    "highlights": [
        "Dashboard / Live torrent activity is visible again because removing it did not materially improve usable workspace height and weakened page hierarchy.",
        "The collapsed Torrent details disclosure shows only Torrent details when no torrent is selected; selection-specific copy appears only for an actual selection.",
        "Opening Settings → Updates no longer contacts GitHub automatically; Check for updates is the explicit freshness/network action.",
        "The bottom-anchored desktop/tablet torrent workspace and mobile disclosure behavior remain unchanged."
    ],
    "fixes": [
        "Removes the unnecessary No torrent selected helper from the persistent collapsed disclosure.",
        "Prevents passive navigation to Updates from performing an update-network request."
    ],
    "technical": [
        "Removed the updateIntegrityRefreshAt/updateIntegrityRefreshPromise page-entry refresh state from settings.js.",
        "Retired dashboard-mode heading suppression while preserving viewport-derived --torrent-workspace-height sizing.",
        "The optional detailHandleSelection label is hidden when empty."
    ],
    "validation": [
        "UI regression checks require visible Dashboard hierarchy, absence of passive Updates-page checks, quiet empty detail disclosure, and continued bottom anchoring.",
        "Existing backend tests, source validation, JavaScript syntax checks, generated documentation checks, and release package-integrity gates remain required."
    ],
    "known_issues": [],
}
for key in ("architecture", "decisions", "next_steps"):
    if key in previous:
        entry[key] = copy.deepcopy(previous[key])
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
print(f"Applied Torrent Dashboard v{NEW} dashboard/update-check cleanup")
