#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.117"
NEW_VERSION = "0.5.118"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one occurrence, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def replace_all_version(path: str) -> None:
    text = read(path)
    if OLD_VERSION not in text:
        raise RuntimeError(f"{path}: {OLD_VERSION} not found")
    write(path, text.replace(OLD_VERSION, NEW_VERSION))


def append_unique(path: str, marker: str, content: str) -> None:
    text = read(path)
    if marker in text:
        raise RuntimeError(f"{path}: marker already exists: {marker}")
    if not text.endswith("\n"):
        text += "\n"
    write(path, text + content.rstrip() + "\n")


# Version synchronization.
replace_once("dashboard.py", f'VERSION = "{OLD_VERSION}"', f'VERSION = "{NEW_VERSION}"')
replace_once("static/app.js", f"const FRONTEND_BUILD='{OLD_VERSION}';", f"const FRONTEND_BUILD='{NEW_VERSION}';")
replace_all_version("static/index.html")
replace_all_version("static/sw.js")
replace_once("static/sw.js", "torrent-dashboard-v05117", "torrent-dashboard-v05118")

# Add Expand all / Collapse all controls to the Add Torrent content preview.
replace_once(
    "static/index.html",
    '<div class="add-preview-heading add-content-summary-heading"><span id="addContentSummary">Add a source to inspect its files before downloading.</span></div>',
    '<div class="add-preview-heading add-content-summary-heading"><span id="addContentSummary">Add a source to inspect its files before downloading.</span><div class="add-content-folder-actions" aria-label="Folder view controls"><button class="secondary small-btn" id="addExpandAllFolders" type="button" aria-controls="addContentBody" disabled>Expand all</button><button class="secondary small-btn" id="addCollapseAllFolders" type="button" aria-controls="addContentBody" disabled>Collapse all</button></div></div>',
)

replace_once(
    "static/app.js",
    """function addTreeNodeSize(node){
  let total=node.files.reduce((sum,file)=>sum+file.length,0);
  for(const child of node.folders.values())total+=addTreeNodeSize(child);
  return total;
}
function addContentFolderRow(node,depth){""",
    """function addTreeNodeSize(node){
  let total=node.files.reduce((sum,file)=>sum+file.length,0);
  for(const child of node.folders.values())total+=addTreeNodeSize(child);
  return total;
}
function addTreeFolderPaths(node){
  const paths=[];
  for(const child of node.folders.values()){paths.push(child.path);paths.push(...addTreeFolderPaths(child))}
  return paths;
}
function syncAddFolderActions(){
  const expand=$('#addExpandAllFolders'),collapse=$('#addCollapseAllFolders');if(!expand||!collapse)return;
  const paths=addTreeFolderPaths(buildAddFileTree(addMetadataState.files||[])),collapsed=paths.filter(path=>addMetadataState.collapsedFolders.has(path)).length;
  expand.disabled=!paths.length||collapsed===0;
  collapse.disabled=!paths.length||collapsed===paths.length;
}
function expandAllAddFolders(){addMetadataState.collapsedFolders.clear();renderAddTorrentContent()}
function collapseAllAddFolders(){
  addMetadataState.collapsedFolders.clear();
  for(const path of addTreeFolderPaths(buildAddFileTree(addMetadataState.files||[])))addMetadataState.collapsedFolders.add(path);
  renderAddTorrentContent();
}
function addContentFolderRow(node,depth){""",
)

replace_once(
    "static/app.js",
    """function renderAddTorrentContent(){
  const body=$('#addContentBody');if(!body)return;
  if(!addMetadataState.files.length){
    body.innerHTML='<div class=\"add-preview-empty\"><strong>No files were reported</strong><span>qBitTorrent returned torrent metadata without a selectable file list.</span></div>';
    syncAddSelectAll();return;
  }
  const scrollTop=body.scrollTop,tree=buildAddFileTree(addMetadataState.files);
  body.innerHTML=addContentTreeRows(tree).join('');
  syncAddFolderCheckboxes();body.scrollTop=scrollTop;
}
function renderAddMetadataEmpty(title,text){
  const body=$('#addContentBody');if(body)body.innerHTML=`<div class=\"add-preview-empty\"><strong>${esc(title)}</strong><span>${esc(text)}</span></div>`;
  syncAddSelectAll();
}""",
    """function renderAddTorrentContent(){
  const body=$('#addContentBody');if(!body)return;
  if(!addMetadataState.files.length){
    body.innerHTML='<div class=\"add-preview-empty\"><strong>No files were reported</strong><span>qBitTorrent returned torrent metadata without a selectable file list.</span></div>';
    syncAddSelectAll();syncAddFolderActions();return;
  }
  const scrollTop=body.scrollTop,tree=buildAddFileTree(addMetadataState.files);
  body.innerHTML=addContentTreeRows(tree).join('');
  syncAddFolderCheckboxes();syncAddFolderActions();body.scrollTop=scrollTop;
}
function renderAddMetadataEmpty(title,text){
  const body=$('#addContentBody');if(body)body.innerHTML=`<div class=\"add-preview-empty\"><strong>${esc(title)}</strong><span>${esc(text)}</span></div>`;
  syncAddSelectAll();syncAddFolderActions();
}""",
)

replace_once(
    "static/app.js",
    "const required=['addTorrentBtn','addModal','addForm','addUrls','torrentFile','addTorrentDrop','addTorrentFileName','addSourceMagnetTab','addSourceFileTab','addSelectAllFiles','addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addSequential','addFirstLast','addContentLayout','addDlLimit','addUlLimit','addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment','addSaveTorrent'];",
    "const required=['addTorrentBtn','addModal','addForm','addUrls','torrentFile','addTorrentDrop','addTorrentFileName','addSourceMagnetTab','addSourceFileTab','addSelectAllFiles','addExpandAllFolders','addCollapseAllFolders','addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addSequential','addFirstLast','addContentLayout','addDlLimit','addUlLimit','addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment','addSaveTorrent'];",
)

replace_once(
    "static/app.js",
    """  $('#addSelectAllFiles').addEventListener('change',event=>{for(const file of addMetadataState.files)file.selected=event.target.checked;renderAddTorrentContent()});
  $('#addContentBody').addEventListener('click',event=>{const toggle=event.target.closest('[data-add-folder-toggle]');if(!toggle)return;const path=toggle.dataset.addFolderToggle;if(addMetadataState.collapsedFolders.has(path))addMetadataState.collapsedFolders.delete(path);else addMetadataState.collapsedFolders.add(path);renderAddTorrentContent()});""",
    """  $('#addSelectAllFiles').addEventListener('change',event=>{for(const file of addMetadataState.files)file.selected=event.target.checked;renderAddTorrentContent()});
  $('#addExpandAllFolders').addEventListener('click',expandAllAddFolders);
  $('#addCollapseAllFolders').addEventListener('click',collapseAllAddFolders);
  $('#addContentBody').addEventListener('click',event=>{const toggle=event.target.closest('[data-add-folder-toggle]');if(!toggle)return;const path=toggle.dataset.addFolderToggle;if(addMetadataState.collapsedFolders.has(path))addMetadataState.collapsedFolders.delete(path);else addMetadataState.collapsedFolders.add(path);renderAddTorrentContent()});""",
)

append_unique(
    "static/app.css",
    "0.5.118 Add Torrent folder disclosure actions",
    """

/* 0.5.118 Add Torrent folder disclosure actions. */
.add-content-summary-heading{justify-content:space-between;gap:10px}
.add-content-summary-heading>span{min-width:0;flex:1}
.add-content-folder-actions{display:flex;align-items:center;gap:6px;flex:0 0 auto}
.add-content-folder-actions button{white-space:nowrap;min-height:30px;padding:6px 9px;font-size:9.5px}
.add-content-folder-actions button:disabled{cursor:default;opacity:.45}
@media(max-width:700px){
  .add-content-summary-heading{align-items:flex-start;flex-wrap:wrap}
  .add-content-summary-heading>span{flex:1 0 100%}
  .add-content-folder-actions{width:100%}
  .add-content-folder-actions button{flex:1}
}
""",
)

# Document the interaction contract and manual coverage.
append_unique(
    "DESIGN_LANGUAGE.md",
    "## Add Torrent folder disclosure actions",
    """

## Add Torrent folder disclosure actions

The Add Torrent content preview keeps per-folder chevrons as the primary local disclosure control and adds **Expand all** / **Collapse all** as compact secondary actions beside the file summary. The actions operate only on the currently loaded metadata tree; they do not change file selection, priority, or torrent add options.

The controls remain disabled until the metadata contains at least one folder. **Expand all** is disabled when every folder is already open, and **Collapse all** is disabled when every known folder path is already collapsed. Bulk disclosure must preserve the same folder ordering, indentation, checkbox state, and file-priority state used by individual folder toggles.

On narrow layouts the summary stays above the two disclosure actions and the actions share the available row width rather than forcing the content preview wider than the modal.
""",
)

append_unique(
    "TESTING.md",
    "### Add Torrent folder disclosure actions",
    """

### Add Torrent folder disclosure actions

- Open Add Torrent with a torrent containing multiple nested folders. Confirm **Expand all** and **Collapse all** appear beside the content summary on desktop and below it on narrow/mobile layouts.
- Before metadata is available, and for a flat torrent with no folders, both controls must remain disabled.
- Collapse several folders individually, then choose **Expand all**. Every folder and nested subfolder must become visible without changing file checkboxes or priorities.
- Choose **Collapse all**. All known folder paths must become collapsed. Expanding one parent afterward must retain the collapsed state of nested descendants until they are individually expanded or **Expand all** is used.
- After **Expand all**, the Expand control must be disabled and Collapse enabled. After **Collapse all**, Collapse must be disabled and Expand enabled.
- Switch source/magnet metadata or reset the Add Torrent form. Disclosure state must be reset for the new metadata tree and must not leak between torrents.
""",
)

# Extend the UI validator so the behavior remains part of the applied-source contract.
validator = read("release_tools/validate_ui_strings.py")
needle = '    print("UI string audit passed")\n'
if validator.count(needle) != 1:
    raise RuntimeError("validate_ui_strings.py: final print marker not found exactly once")
checks = """    # 0.5.118 adds bulk disclosure controls to the Add Torrent metadata tree.\n    assert 'id=\"addExpandAllFolders\"' in html and 'id=\"addCollapseAllFolders\"' in html\n    assert 'class=\"add-content-folder-actions\"' in html\n    assert 'function addTreeFolderPaths(node)' in app_js\n    assert 'function syncAddFolderActions()' in app_js\n    assert 'function expandAllAddFolders()' in app_js and 'function collapseAllAddFolders()' in app_js\n    assert \"$('#addExpandAllFolders').addEventListener('click',expandAllAddFolders)\" in app_js\n    assert \"$('#addCollapseAllFolders').addEventListener('click',collapseAllAddFolders)\" in app_js\n    assert 'for(const path of addTreeFolderPaths(buildAddFileTree(addMetadataState.files||[])))addMetadataState.collapsedFolders.add(path)' in app_js\n    assert '0.5.118 Add Torrent folder disclosure actions' in app_css\n    assert '## Add Torrent folder disclosure actions' in design_language\n    assert '### Add Torrent folder disclosure actions' in testing_md\n\n"""
write("release_tools/validate_ui_strings.py", validator.replace(needle, checks + needle, 1))

# Add structured release metadata while retaining the architectural objective.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data.get("releases") or []
if not releases or str(releases[-1].get("version")) != OLD_VERSION:
    raise RuntimeError(f"Expected v{OLD_VERSION} to be the latest release metadata entry")
if any(str(item.get("version")) == NEW_VERSION for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW_VERSION} already exists")
previous_decisions = list(releases[-1].get("decisions") or [])
previous_decisions.append("Keep Add Torrent bulk folder disclosure as presentation state over the existing metadata tree; expand/collapse actions must never alter file selection or priority state.")
releases.append({
    "version": NEW_VERSION,
    "date": "2026-09-04",
    "status": "prerelease",
    "title": "Add Torrent folder disclosure controls",
    "summary": "Adds Expand all and Collapse all controls to the Add Torrent content tree so nested torrent metadata can be opened or compacted in one action without changing download selections.",
    "highlights": [
        "Adds compact Expand all and Collapse all actions beside the Add Torrent content summary.",
        "Bulk disclosure operates across every known nested folder path while preserving the existing per-folder chevrons.",
        "The controls automatically disable when the requested state is already satisfied or when the torrent contains no folders.",
        "Responsive layout keeps the controls usable on narrow/mobile Add Torrent sheets without widening the content preview."
    ],
    "fixes": [],
    "technical": [
        "Folder paths are derived from the existing in-memory metadata tree and stored in the existing collapsedFolders set; no backend or qBitTorrent API change is required.",
        "Expand all clears collapsedFolders, while Collapse all repopulates it with every recursively discovered folder path.",
        "Rendering resynchronizes the action disabled states after individual toggles, metadata changes, source resets, and bulk disclosure actions."
    ],
    "validation": [
        "The UI audit requires both controls, recursive folder-path collection, bulk action bindings, responsive CSS, and matching design/testing documentation.",
        "Manual coverage verifies nested expand/collapse behavior, disabled-state transitions, flat torrents, metadata resets, and preservation of file selections and priorities.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": [],
    "decisions": previous_decisions,
})
release_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate derived release/handoff artifacts now so the subsequent --check gate validates the transformed tree.
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW_VERSION],
    cwd=ROOT,
    check=True,
)

print(f"Applied v{NEW_VERSION} Add Torrent folder disclosure controls")
