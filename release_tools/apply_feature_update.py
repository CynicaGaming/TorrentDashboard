#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.83"
PREVIOUS = "0.5.82"


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

# Use locally embedded Material SVGs for the persistent detail disclosure and
# .torrent file upload affordance; do not add remote font/icon dependencies.
old_detail_icon = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="m6 15 6-6 6 6"/></svg>'
new_detail_icon = '<svg class="material-symbol-icon detail-disclosure-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M7.41 15.41 12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>'
html = replace_once(html, old_detail_icon, new_detail_icon, "Torrent details disclosure icon")

old_upload = '<span class="add-drop-icon" aria-hidden="true">⇧</span>'
new_upload = '<svg class="material-symbol-icon add-drop-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2Zm7-17-7 7h4v5h6v-5h4l-7-7Z"/></svg>'
html = replace_once(html, old_upload, new_upload, "Add Torrent upload icon")

# The summary already explains the content panel; remove the redundant Content
# label while retaining the live file/size summary.
old_heading = '<div class="add-preview-heading"><div><strong>Content</strong><span id="addContentSummary">Add a source to inspect its files before downloading.</span></div></div>'
new_heading = '<div class="add-preview-heading add-content-summary-heading"><span id="addContentSummary">Add a source to inspect its files before downloading.</span></div>'
html = replace_once(html, old_heading, new_heading, "Add Torrent content heading")
write("static/index.html", html)

app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")

# Add a small reusable locally embedded Material icon helper for dynamically
# generated disclosure controls.
anchor = "function displayUiText(value=''){const s=String(value??'');return isLegacyUiToken(s)?uiText(s):s}\n"
icons = """function displayUiText(value=''){const s=String(value??'');return isLegacyUiToken(s)?uiText(s):s}\nconst UI_MATERIAL_ICON_PATHS={\n  chevron_right:'M9.29 6.71a.996.996 0 0 0 0 1.41L13.17 12l-3.88 3.88a.996.996 0 1 0 1.41 1.41l4.59-4.59a.996.996 0 0 0 0-1.41L10.7 6.7a.996.996 0 0 0-1.41.01Z',\n  expand_more:'M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z',\n};\nfunction materialIconSvg(name){const path=UI_MATERIAL_ICON_PATHS[name]||UI_MATERIAL_ICON_PATHS.expand_more;return `<svg class=\"material-symbol-icon\" aria-hidden=\"true\" viewBox=\"0 0 24 24\"><path d=\"${path}\"/></svg>`}\n"""
app = replace_once(app, anchor, icons, "dynamic Material icon helper")

old_folder = """  return `<div class=\"add-content-row add-content-folder\" data-add-depth=\"${depth}\" style=\"--add-depth:${depth}\"><span class=\"add-content-select\"><input type=\"checkbox\" data-add-folder-files=\"${indexes.join(',')}\" ${checked?'checked':''} aria-label=\"Download folder ${esc(node.name)}\"></span><span class=\"add-content-name\"><button class=\"add-folder-toggle\" data-add-folder-toggle=\"${esc(node.path)}\" type=\"button\" aria-label=\"${collapsed?'Expand':'Collapse'} folder ${esc(node.name)}\" aria-expanded=\"${String(!collapsed)}\">${collapsed?'›':'⌄'}</button><span class=\"add-folder-name\">${esc(node.name)}</span></span><span>${bytes(addTreeNodeSize(node))}</span><span class=\"add-folder-items\">${files.length} ${files.length===1?'file':'files'}</span></div>`;\n"""
new_folder = """  return `<div class=\"add-content-row add-content-folder\" data-add-depth=\"${depth}\" style=\"--add-depth:${depth}\"><span class=\"add-content-select\"><input type=\"checkbox\" data-add-folder-files=\"${indexes.join(',')}\" ${checked?'checked':''} aria-label=\"Download folder ${esc(node.name)}\"></span><span class=\"add-content-name\"><button class=\"add-folder-toggle\" data-add-folder-toggle=\"${esc(node.path)}\" type=\"button\" aria-label=\"${collapsed?'Expand':'Collapse'} folder ${esc(node.name)}\" aria-expanded=\"${String(!collapsed)}\">${materialIconSvg(collapsed?'chevron_right':'expand_more')}</button><span class=\"add-folder-name\">${esc(node.name)}</span></span><span>${bytes(addTreeNodeSize(node))}</span><span aria-hidden=\"true\"></span></div>`;\n"""
app = replace_once(app, old_folder, new_folder, "Add Torrent folder row")

old_release_chevron = "const chevron=document.createElement('span');chevron.className='update-release-chevron';chevron.textContent='⌄';summary.append(version,copy,chevron);"
new_release_chevron = "const chevron=document.createElement('span');chevron.className='update-release-chevron';chevron.innerHTML=materialIconSvg('expand_more');summary.append(version,copy,chevron);"
app = replace_once(app, old_release_chevron, new_release_chevron, "release-note disclosure icon")
write("static/app.js", app)

css = read("static/app.css")
css += """

/* 0.5.83 locally embedded Material disclosure icons and Add Torrent table polish. */
.material-symbol-icon{display:block;width:18px;height:18px;fill:currentColor;flex:0 0 auto}
.add-folder-toggle .material-symbol-icon{width:18px;height:18px}
.add-drop-icon.material-symbol-icon{width:24px;height:24px;margin-bottom:2px;color:var(--accent)}
.torrent-detail-handle .material-symbol-icon{width:18px;height:18px;fill:currentColor;stroke:none}
.update-release-chevron .material-symbol-icon{width:18px;height:18px}
.add-content-summary-heading{min-height:39px;justify-content:flex-start}
.add-content-summary-heading>span{font-size:10.5px;color:var(--muted)}
.add-content-columns>span:nth-child(2){text-align:left}
.add-content-columns>span:nth-child(3),.add-content-columns>span:nth-child(4){text-align:right}
"""
write("static/app.css", css)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0582", "torrent-dashboard-v0583", "service-worker cache version")
if PREVIOUS not in sw:
    raise RuntimeError("Previous asset version not found in service worker")
sw = sw.replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Update durable design and testing contracts.
design = read("DESIGN_LANGUAGE.md")
icon_section = """

## Iconography

Common interface symbols should use locally embedded Material-style SVG paths rather than text glyphs when an established icon exists. Disclosure chevrons, expansion controls, and file-source affordances should share this treatment so their stroke/shape quality is consistent across browsers and operating systems. Do not introduce a Google Fonts, Material Symbols font, or other remote icon dependency solely for interface chrome; Torrent Dashboard must keep these controls available offline and in self-hosted/forked deployments.
"""
if "## Iconography" not in design:
    marker = "## Settings feedback contract\n"
    if marker not in design:
        raise RuntimeError("Design-language insertion marker missing")
    design = design.replace(marker, icon_section + "\n" + marker, 1)

old_hierarchy = """Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. The content column reserves one fixed disclosure slot on every row: folders use it for their expand/collapse chevron and files use an equal-width spacer. Hierarchy indentation is applied after that shared slot, so child files visibly sit beneath their parent folder labels while Size and Priority remain aligned.\n\nFor the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically. The disclosure bar is the single selection-identity surface; do not repeat the torrent title/hash in a second header immediately above the detail tabs.\n"""
new_hierarchy = """Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. The content column reserves one fixed disclosure slot on every row: folders use a Material disclosure icon and files use an equal-width spacer. Hierarchy indentation is applied after that shared slot, so child files visibly sit beneath their parent folder labels while Size and Priority remain aligned. Column labels describe the table directly: Name is left-aligned at the start of its column, folder rows do not repeat descendant file counts in the Priority column, and the live file/size summary makes a separate Content heading unnecessary.\n\nFor the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically. The disclosure bar is the single selection-identity surface; do not repeat the torrent title/hash in a second header immediately above the detail tabs.\n"""
design = replace_once(design, old_hierarchy, new_hierarchy, "Add Torrent hierarchy design contract")
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
old_testing = """- Verify folder rows reserve a disclosure-chevron slot and file rows reserve an equal-width spacer. A child file label must begin to the right of its parent folder label; deeper descendants should continue stepping right by hierarchy depth.\n- Verify Size and Priority columns remain aligned across all rows regardless of hierarchy depth.\n"""
new_testing = """- Verify folder rows use the locally embedded Material disclosure icon and file rows reserve an equal-width spacer. A child file label must begin to the right of its parent folder label; deeper descendants should continue stepping right by hierarchy depth.\n- Verify the Name header is left-aligned at the beginning of the name column, Size and Priority remain aligned, folder rows do not show descendant file counts, and the preview summary appears without a redundant Content heading.\n"""
testing = replace_once(testing, old_testing, new_testing, "Add Torrent hierarchy testing contract")
write("TESTING.md", testing)

validator = read("release_tools/validate_ui_strings.py")
old_tail = """    assert 'The disclosure bar is the single selection-identity surface' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n\n    print(\"UI string audit passed\")\n"""
new_tail = """    assert 'The disclosure bar is the single selection-identity surface' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n\n    # 0.5.83 replaces text-glyph disclosure/file affordances with locally\n    # embedded Material SVGs and simplifies the Add Torrent content table.\n    assert 'const UI_MATERIAL_ICON_PATHS={' in app_js and 'function materialIconSvg(name)' in app_js\n    assert \"materialIconSvg(collapsed?'chevron_right':'expand_more')\" in app_js\n    assert \"chevron.innerHTML=materialIconSvg('expand_more')\" in app_js\n    assert \"${collapsed?'›':'⌄'}\" not in app_js and \"chevron.textContent='⌄'\" not in app_js\n    assert 'class=\"material-symbol-icon detail-disclosure-icon\"' in html\n    assert 'class=\"material-symbol-icon add-drop-icon\"' in html and '>⇧<' not in html\n    assert '.material-symbol-icon{display:block;width:18px;height:18px;fill:currentColor' in app_css\n    assert '0.5.83 locally embedded Material disclosure icons and Add Torrent table polish' in app_css\n    assert '<strong>Content</strong><span id=\"addContentSummary\"' not in html\n    assert 'class=\"add-preview-heading add-content-summary-heading\"' in html\n    assert '.add-content-columns>span:nth-child(2){text-align:left}' in app_css\n    assert 'class=\"add-folder-items\"' not in app_js\n    assert '## Iconography' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'folder rows do not show descendant file counts' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n\n    print(\"UI string audit passed\")\n"""
validator = replace_once(validator, old_tail, new_tail, "v0.5.83 validator tail")
write("release_tools/validate_ui_strings.py", validator)

# Record the release while carrying forward the active architecture/roadmap.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data["releases"]
if not any(str(item.get("version")) == VERSION for item in releases):
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS), None)
    if not previous:
        raise RuntimeError(f"Release metadata for v{PREVIOUS} was not found")
    decisions = list(previous.get("decisions") or [])
    for decision in (
        "Use locally embedded Material-style SVGs for common disclosure and file-source affordances rather than platform-dependent text glyphs or remote icon-font dependencies.",
        "Keep the Add Torrent content preview visually minimal: left-align Name, omit redundant folder descendant counts, and let the live file/size summary replace a separate Content heading.",
    ):
        if decision not in decisions:
            decisions.append(decision)
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Material icon and Add Torrent table polish",
        "summary": "Uses locally embedded Material-style disclosure/file icons and simplifies the Add Torrent content table for clearer hierarchy and less redundant information.",
        "highlights": [
            "Folder disclosure, Torrent details disclosure, update-note disclosure, and .torrent upload affordances now use locally embedded Material-style SVG icons.",
            "Add Torrent no longer repeats a Content heading above the live file/size summary.",
            "The Name header is left-aligned at the beginning of its column.",
            "Folder rows no longer display redundant descendant file counts in the Priority column."
        ],
        "fixes": [
            "Removes platform-dependent text chevrons that rendered inconsistently across browsers and operating systems.",
            "Corrects the inherited header alignment rule that pushed Name away from the start of its column."
        ],
        "technical": [
            "Dynamic disclosure icons use a small local materialIconSvg helper backed by embedded SVG path data; static disclosure/upload icons use the same material-symbol-icon class.",
            "No external icon font, Google Fonts request, or new runtime dependency is introduced."
        ],
        "validation": [
            "The UI audit rejects the old disclosure glyphs, requires local Material SVG affordances, and verifies the simplified Add Torrent heading/column/folder-row contract.",
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
print(f"Applied Torrent Dashboard v{VERSION} Material icon and Add Torrent polish")
