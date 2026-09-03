#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.81"
PREVIOUS = "0.5.80"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} occurrence, found {count}")
    return text.replace(old, new, 1)


# Synchronize application/frontend versions.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if PREVIOUS not in html:
    raise RuntimeError("Previous frontend version not found in index.html")
html = html.replace(PREVIOUS, VERSION)
write("static/index.html", html)

app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")

old_refresh = "async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};renderMetrics(d);checkCompletions();render();if(state.detail&&$('#view-dashboard').classList.contains('active'))refreshDetailData(false);$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}"
new_refresh = "async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};reconcileDetailSelection();renderMetrics(d);checkCompletions();render();if(state.detail&&$('#view-dashboard').classList.contains('active'))refreshDetailData(false);$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}"
app = replace_once(app, old_refresh, new_refresh, "status refresh reconciliation")

old_reset = "function resetDetailPane(){\n  state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();render();\n}\n"
new_reset = "function resetDetailPane(renderList=true){\n  state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();\n}\nfunction reconcileDetailSelection(){\n  if(!state.detail)return;\n  const exists=state.torrents.some(t=>(t._server_id||state.server)===state.detail.server&&t.hash===state.detail.hash);\n  if(!exists)resetDetailPane(false);\n}\n"
app = replace_once(app, old_reset, new_reset, "detail reset/reconciliation helpers")
write("static/app.js", app)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0580", "torrent-dashboard-v0581", "service-worker cache version")
if PREVIOUS not in sw:
    raise RuntimeError("Previous asset version not found in service worker")
sw = sw.replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Correct the v0.5.80 tree styling rather than stacking contradictory overrides.
css = read("static/app.css")
old_css = '''/* 0.5.80 Add Torrent hierarchy and detail selection polish. */
.add-content-row{grid-template-columns:calc(34px + var(--add-depth,0) * 16px) minmax(0,1fr) 90px 112px}
.add-content-select{place-items:center end!important;padding-right:9px}
.add-content-name{padding-left:0}
@media(max-width:520px){.add-content-row{grid-template-columns:calc(30px + var(--add-depth,0) * 14px) minmax(130px,1fr) 68px 96px}.add-content-select{padding-right:7px}}
'''
new_css = '''/* 0.5.81 aligned Add Torrent selection column and indented hierarchy labels. */
.add-content-row{grid-template-columns:34px minmax(0,1fr) 90px 112px}
.add-content-select{place-items:center!important;padding-right:0}
.add-content-name{padding-left:calc(var(--add-depth,0) * 16px)}
@media(max-width:520px){.add-content-row{grid-template-columns:30px minmax(130px,1fr) 68px 96px}.add-content-name{padding-left:calc(var(--add-depth,0) * 14px)}}
'''
css = replace_once(css, old_css, new_css, "v0.5.80 Add Torrent hierarchy CSS")
write("static/app.css", css)

# Update durable design/testing contracts to supersede the v0.5.80 interpretation.
design = read("DESIGN_LANGUAGE.md")
old_design = '''## Hierarchical torrent content selection

File-selection trees should communicate ancestry through the selection control as well as the label. In Add Torrent, each nested folder/file level indents the checkbox and name together while size and priority columns remain aligned. Do not represent hierarchy only by shifting filenames away from otherwise flat checkboxes.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally.
'''
new_design = '''## Hierarchical torrent content selection

Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. Hierarchy is communicated in the content label: nested folders and files indent according to depth while Size and Priority remain aligned. A file beneath a folder should read as a child without shifting its checkbox away from the rest of the selection column.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically.
'''
design = replace_once(design, old_design, new_design, "hierarchical selection design contract")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
old_testing = '''### Add Torrent hierarchy and repeated detail selection

- Load a multi-folder torrent in Add Torrent and verify each nested level moves its checkbox and filename together to the right; Size and Priority columns should stay aligned across all depths.
- Verify top-level files/folders remain at the base indentation and nested descendants are visibly distinguishable without relying on folder names alone.
- Select a torrent row and verify Torrent details expands for it. Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
'''
new_testing = '''### Add Torrent hierarchy and detail-selection reconciliation

- Load a multi-folder torrent in Add Torrent and verify every folder/file checkbox remains vertically aligned in the same selection column.
- Verify nested folder/file labels indent according to hierarchy depth while Size and Priority columns remain aligned across all rows.
- Select a torrent row and verify Torrent details expands for it. Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
- With a torrent selected in Torrent details, remove that torrent (or remove it directly in qBitTorrent) and verify the next status refresh clears the stale detail context and collapses the dock. Removing another torrent must not clear the current detail selection.
'''
testing = replace_once(testing, old_testing, new_testing, "hierarchy/detail testing contract")
write("TESTING.md", testing)

validator = read("release_tools/validate_ui_strings.py")
old_validator = '''    # 0.5.80 makes Add Torrent hierarchy visible at the checkbox level and
    # treats a repeated click on the active torrent row as detail deselection.
    assert app_js.count('data-add-depth="${depth}" style="--add-depth:${depth}"') == 2
    assert 'class="add-content-name" style="--add-depth:${depth}"' not in app_js
    assert '0.5.80 Add Torrent hierarchy and detail selection polish' in app_css
    assert 'grid-template-columns:calc(34px + var(--add-depth,0) * 16px)' in app_css
    assert 'place-items:center end!important' in app_css
    assert "if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}" in app_js
    assert '## Hierarchical torrent content selection' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Add Torrent hierarchy and repeated detail selection' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
new_validator = '''    # 0.5.81 keeps Add Torrent checkboxes aligned while hierarchy is expressed
    # by the content label, and clears stale detail context when a torrent disappears.
    assert app_js.count('data-add-depth="${depth}" style="--add-depth:${depth}"') == 2
    assert '0.5.81 aligned Add Torrent selection column and indented hierarchy labels' in app_css
    assert '.add-content-row{grid-template-columns:34px minmax(0,1fr) 90px 112px}' in app_css
    assert '.add-content-select{place-items:center!important;padding-right:0}' in app_css
    assert '.add-content-name{padding-left:calc(var(--add-depth,0) * 16px)}' in app_css
    assert 'grid-template-columns:calc(34px + var(--add-depth,0) * 16px)' not in app_css
    assert "if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}" in app_js
    assert 'function reconcileDetailSelection()' in app_js
    assert "const exists=state.torrents.some(t=>(t._server_id||state.server)===state.detail.server&&t.hash===state.detail.hash)" in app_js
    assert 'if(!exists)resetDetailPane(false)' in app_js
    assert 'reconcileDetailSelection();renderMetrics(d)' in app_js
    assert 'function resetDetailPane(renderList=true)' in app_js
    assert '## Hierarchical torrent content selection' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Add Torrent hierarchy and detail-selection reconciliation' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
'''
validator = replace_once(validator, old_validator, new_validator, "v0.5.80 UI regression block")
write("release_tools/validate_ui_strings.py", validator)

# Record the release while preserving v0.5.80 as historical context and removing
# its superseded hierarchy decision from the active carried-forward decision set.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if not any(str(item.get("version")) == VERSION for item in releases):
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS), None)
    if not previous:
        raise RuntimeError(f"Release metadata for v{PREVIOUS} was not found")
    superseded = "Represent Add Torrent file hierarchy by indenting the selection control and name together while keeping data columns aligned."
    decisions = [item for item in list(previous.get("decisions") or []) if item != superseded]
    for decision in (
        "Keep Add Torrent checkboxes in one aligned selection column; communicate hierarchy by indenting folder/file labels while preserving aligned Size and Priority columns.",
        "Reconcile Torrent details against every refreshed torrent list and clear the detail context when its selected server/hash no longer exists.",
    ):
        if decision not in decisions:
            decisions.append(decision)
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Aligned file selection and stale detail cleanup",
        "summary": "Keeps Add Torrent checkboxes aligned while indenting hierarchical content labels, and automatically clears Torrent details when the selected torrent disappears from the client.",
        "highlights": [
            "All Add Torrent folder/file checkboxes now remain in one stable selection column.",
            "Nested folder and file names indent by hierarchy depth while Size and Priority stay aligned.",
            "Torrent details are reconciled with every live status refresh; if the selected torrent is removed, the stale detail context clears automatically.",
            "Removing a different torrent leaves the current Torrent details selection intact."
        ],
        "fixes": [
            "Corrects the v0.5.80 hierarchy treatment that shifted checkboxes along with nested content.",
            "Prevents the Torrent details dock from retaining information for a torrent that no longer exists in the current server list."
        ],
        "technical": [
            "The Add Torrent row keeps --add-depth on the row but applies it only as left padding on the content-name column.",
            "refreshStatus calls reconcileDetailSelection after replacing state.torrents; resetDetailPane accepts a renderList flag so stale-state cleanup does not cause an unnecessary intermediate list render."
        ],
        "validation": [
            "The UI audit requires a fixed checkbox column, depth-based content-label indentation, and absence of the v0.5.80 expanding checkbox-column rule.",
            "The UI audit requires live status reconciliation to reset details only when the selected server/hash is absent from state.torrents.",
            "Existing 20 backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "known_issues": [],
        "architecture": list(previous.get("architecture") or []),
        "next_steps": list(previous.get("next_steps") or []),
        "decisions": decisions,
    })
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    ["python", "release_tools/generate_release_notes.py", "--version", VERSION],
    cwd=ROOT,
    check=True,
)
print(f"Applied Torrent Dashboard v{VERSION} aligned hierarchy and stale detail cleanup")
