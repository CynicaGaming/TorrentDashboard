#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.82"
PREVIOUS = "0.5.81"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} occurrence, found {count}")
    return text.replace(old, new, 1)


# Synchronize build versions.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
if PREVIOUS not in html:
    raise RuntimeError("Previous frontend version not found in index.html")
html = html.replace(PREVIOUS, VERSION)
old_context = '''<div class="torrent-detail-content" id="detailPanelContent">
<div class="torrent-detail-context"><strong id="detailName"></strong><span id="detailMeta">Select a torrent to view details.</span></div>
<div class="torrent-detail-tabs" role="tablist" aria-label="Torrent information">'''
new_context = '''<div class="torrent-detail-content" id="detailPanelContent">
<div class="torrent-detail-tabs" role="tablist" aria-label="Torrent information">'''
html = replace_once(html, old_context, new_context, "redundant torrent detail identity block")
write("static/index.html", html)

app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")
old_file_row = '''function addContentFileRow(file,depth){
  return `<div class="add-content-row add-content-file" data-add-depth="${depth}" style="--add-depth:${depth}"><span class="add-content-select"><input type="checkbox" data-add-file-check="${file.index}" ${file.selected?'checked':''} aria-label="Download file"></span><span class="add-content-name">${esc(file.displayName||file.path)}</span><span>${bytes(file.length)}</span><span><select class="add-file-priority" data-add-file-priority="${file.index}" aria-label="File priority" ${file.selected?'':'disabled'}>${addPriorityOptions(file.priority)}</select></span></div>`;
}'''
new_file_row = '''function addContentFileRow(file,depth){
  return `<div class="add-content-row add-content-file" data-add-depth="${depth}" style="--add-depth:${depth}"><span class="add-content-select"><input type="checkbox" data-add-file-check="${file.index}" ${file.selected?'checked':''} aria-label="Download file"></span><span class="add-content-name"><span class="add-tree-spacer" aria-hidden="true"></span>${esc(file.displayName||file.path)}</span><span>${bytes(file.length)}</span><span><select class="add-file-priority" data-add-file-priority="${file.index}" aria-label="File priority" ${file.selected?'':'disabled'}>${addPriorityOptions(file.priority)}</select></span></div>`;
}'''
app = replace_once(app, old_file_row, new_file_row, "Add Torrent file-row expander spacer")
old_selection = "handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?($('#detailName')?.textContent||'Selected torrent'):'';"
new_selection = "handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?(detailCurrentTorrent()?.name||'Selected torrent'):'';"
app = replace_once(app, old_selection, new_selection, "detail handle selection source")
old_reset = "state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailName').textContent='';$('#detailMeta').textContent='Select a torrent to view details.';$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();"
new_reset = "state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();"
app = replace_once(app, old_reset, new_reset, "detail reset without redundant context")
old_open = "const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash),name=t?.name||hash;$('#detailName').textContent=name;$('#detailMeta').textContent=`${t?._server_name||server} · ${hash}`;$('#detailHandleSelection').textContent=name;syncDetailDock();"
new_open = "syncDetailDock();"
app = replace_once(app, old_open, new_open, "detail open without redundant identity block")
write("static/app.js", app)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0581", "torrent-dashboard-v0582", "service-worker cache version")
if PREVIOUS not in sw:
    raise RuntimeError("Previous asset version not found in service worker")
sw = sw.replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

css = read("static/app.css")
old_detail_css = '''.torrent-detail-handle{appearance:none;width:100%;min-height:48px;border:0;border-radius:0;background:linear-gradient(180deg,color-mix(in srgb,var(--panel2) 72%,var(--panel3)),var(--panel3));color:var(--text);padding:0 13px;display:flex;align-items:center;gap:10px;text-align:left}.torrent-detail-handle:hover{background:var(--panel2)}.torrent-detail-handle:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 72%,transparent)}.torrent-detail-handle-label{font-size:11px;font-weight:720;white-space:nowrap}.torrent-detail-handle-selection{min-width:0;flex:1;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-handle svg{width:17px;height:17px;flex:0 0 auto;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s ease}.torrent-detail-handle[aria-expanded="true"] svg{transform:rotate(180deg)}.torrent-detail-content{display:flex;flex:1 1 auto;min-height:0;flex-direction:column}.torrent-detail-context{display:grid;gap:2px;padding:10px 13px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:var(--panel)}.torrent-detail-context strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-context span{color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-pane.collapsed .torrent-detail-content{display:none}.torrent-detail-pane:not(.has-selection) .torrent-detail-context,.torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}'''
new_detail_css = '''.torrent-detail-handle{appearance:none;width:100%;min-height:48px;border:0;border-radius:0;background:linear-gradient(180deg,color-mix(in srgb,var(--panel2) 72%,var(--panel3)),var(--panel3));color:var(--text);padding:0 13px;display:flex;align-items:center;gap:10px;text-align:left}.torrent-detail-handle:hover{background:var(--panel2)}.torrent-detail-handle:focus-visible{box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--accent) 72%,transparent)}.torrent-detail-handle-label{font-size:11px;font-weight:720;white-space:nowrap}.torrent-detail-handle-selection{min-width:0;flex:1;color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-handle svg{width:17px;height:17px;flex:0 0 auto;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s ease}.torrent-detail-handle[aria-expanded="true"] svg{transform:rotate(180deg)}.torrent-detail-content{display:flex;flex:1 1 auto;min-height:0;flex-direction:column}.torrent-detail-pane.collapsed .torrent-detail-content{display:none}.torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}'''
css = replace_once(css, old_detail_css, new_detail_css, "torrent detail context CSS")
old_desktop_context = '  .torrent-detail-pane{min-height:320px;max-height:48vh}.torrent-detail-handle{min-height:52px;padding:0 15px}.torrent-detail-handle-label{font-size:13.5px}.torrent-detail-handle-selection{font-size:11.5px}.torrent-detail-context{padding:12px 15px}.torrent-detail-context strong{font-size:13.5px}.torrent-detail-context span{font-size:11.5px}'
new_desktop_context = '  .torrent-detail-pane{min-height:320px;max-height:48vh}.torrent-detail-handle{min-height:52px;padding:0 15px}.torrent-detail-handle-label{font-size:13.5px}.torrent-detail-handle-selection{font-size:11.5px}'
css = replace_once(css, old_desktop_context, new_desktop_context, "desktop torrent detail context CSS")
css += '''\n/* 0.5.82 tree disclosure alignment and streamlined Torrent details. */\n.add-tree-spacer{display:block;width:22px;min-width:22px;height:22px;flex:0 0 22px}\n'''
write("static/app.css", css)

# Update durable design/testing contracts.
design = read("DESIGN_LANGUAGE.md")
old_design = '''## Hierarchical torrent content selection

Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. Hierarchy is communicated in the content label: nested folders and files indent according to depth while Size and Priority remain aligned. A file beneath a folder should read as a child without shifting its checkbox away from the rest of the selection column.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically.
'''
new_design = '''## Hierarchical torrent content selection

Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. The content column reserves one fixed disclosure slot on every row: folders use it for their expand/collapse chevron and files use an equal-width spacer. Hierarchy indentation is applied after that shared slot, so child files visibly sit beneath their parent folder labels while Size and Priority remain aligned.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically. The disclosure bar is the single selection-identity surface; do not repeat the torrent title/hash in a second header immediately above the detail tabs.
'''
design = replace_once(design, old_design, new_design, "hierarchical selection/detail identity design contract")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
old_testing = '''### Add Torrent hierarchy and detail-selection reconciliation

- Load a multi-folder torrent in Add Torrent and verify every folder/file checkbox remains vertically aligned in the same selection column.
- Verify nested folder/file labels indent according to hierarchy depth while Size and Priority columns remain aligned across all rows.
- Select a torrent row and verify Torrent details expands for it. Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
- With a torrent selected in Torrent details, remove that torrent (or remove it directly in qBitTorrent) and verify the next status refresh clears the stale detail context and collapses the dock. Removing another torrent must not clear the current detail selection.
'''
new_testing = '''### Add Torrent hierarchy and detail-selection reconciliation

- Load a multi-folder torrent in Add Torrent and verify every folder/file checkbox remains vertically aligned in the same selection column.
- Verify folder rows reserve a disclosure-chevron slot and file rows reserve an equal-width spacer. A child file label must begin to the right of its parent folder label; deeper descendants should continue stepping right by hierarchy depth.
- Verify Size and Priority columns remain aligned across all rows regardless of hierarchy depth.
- Select a torrent row and verify Torrent details expands for it. The disclosure bar should identify the selected torrent, and the expanded panel should proceed directly to the detail tabs without repeating the torrent title/hash in a second header.
- Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
- With a torrent selected in Torrent details, remove that torrent (or remove it directly in qBitTorrent) and verify the next status refresh clears the stale detail context and collapses the dock. Removing another torrent must not clear the current detail selection.
'''
testing = replace_once(testing, old_testing, new_testing, "hierarchy/detail testing contract")
write("TESTING.md", testing)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    '    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-context,.torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" in app_css',
    '    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" in app_css',
    "superseded torrent-detail-context CSS assertion",
)
insert_before = '    print("UI string audit passed")\n'
checks = '''    # 0.5.82 reserves the same disclosure slot for folders and files so\n    # hierarchy is expressed after the expander column, and removes the\n    # redundant selected-torrent identity block from the expanded inspector.\n    assert 'class="add-tree-spacer" aria-hidden="true"' in app_js\n    assert '.add-tree-spacer{display:block;width:22px;min-width:22px;height:22px;flex:0 0 22px}' in app_css\n    assert '0.5.82 tree disclosure alignment and streamlined Torrent details' in app_css\n    assert 'class="torrent-detail-context"' not in html\n    assert 'id="detailName"' not in html and 'id="detailMeta"' not in html\n    assert 'torrent-detail-context' not in app_css\n    assert "$('#detailName')" not in app_js and "$('#detailMeta')" not in app_js\n    assert "selected?(detailCurrentTorrent()?.name||'Selected torrent'):''" in app_js\n    assert 'The disclosure bar is the single selection-identity surface' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n\n'''
validator = replace_once(validator, insert_before, checks + insert_before, "v0.5.82 UI regression checks")
write("release_tools/validate_ui_strings.py", validator)

# Record release metadata while carrying forward architectural roadmap.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if not any(str(item.get("version")) == VERSION for item in releases):
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS), None)
    if not previous:
        raise RuntimeError(f"Release metadata for v{PREVIOUS} was not found")
    decisions = list(previous.get("decisions") or [])
    for decision in (
        "Reserve a fixed disclosure/expander slot for every Add Torrent content row; files use a spacer while folders use the chevron, and hierarchy indentation begins after that slot.",
        "Use the persistent Torrent details disclosure bar as the sole selection identity surface; expanded details begin directly with tabs/content rather than repeating title/hash metadata.",
    ):
        if decision not in decisions:
            decisions.append(decision)
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Torrent tree alignment and detail header cleanup",
        "summary": "Corrects Add Torrent tree indentation by reserving a shared disclosure slot and removes redundant torrent identity metadata from the expanded details panel.",
        "highlights": [
            "Add Torrent checkboxes remain aligned while file/folder labels now share a fixed expander slot before hierarchy indentation.",
            "Files beneath folders visibly begin to the right of their parent folder label, including deeper nested levels.",
            "Expanded Torrent details now starts directly with its information tabs; the persistent disclosure bar remains the single selected-torrent identity surface."
        ],
        "fixes": [
            "Fixes child filenames appearing visually level with or left of their parent folder despite depth-based padding.",
            "Removes duplicated torrent title and hash/server metadata from the expanded detail pane."
        ],
        "technical": [
            "File rows render an add-tree-spacer with the same 22 px width as the folder disclosure control, so depth padding operates from a consistent content baseline.",
            "detailName/detailMeta markup and JavaScript dependencies are removed; syncDetailDock derives the selected torrent name from current state."
        ],
        "validation": [
            "The UI audit requires the fixed file-row disclosure spacer and rejects any reintroduction of the redundant detail-context block.",
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
print(f"Applied Torrent Dashboard v{VERSION} tree alignment and detail header cleanup")
