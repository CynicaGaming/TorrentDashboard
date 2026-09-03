#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.96"
TARGET_VERSION = "0.5.97"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match in {path.relative_to(ROOT)}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_versions() -> None:
    replace_once(ROOT / "dashboard.py", f'VERSION = "{PREVIOUS_VERSION}"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count(PREVIOUS_VERSION) < 4:
        raise RuntimeError("Expected v0.5.96 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(
        ROOT / "static" / "app.js",
        f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0596" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.96 service-worker references")
    text = text.replace("torrent-dashboard-v0596", "torrent-dashboard-v0597")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_html() -> None:
    replace_once(
        ROOT / "static" / "index.html",
        '<th class="row-actions-head"></th></tr></thead>',
        '<th class="row-spacer-head" aria-hidden="true"></th><th class="row-actions-head"></th></tr></thead>',
        "torrent action spacer header",
    )


def update_javascript() -> None:
    path = ROOT / "static" / "app.js"
    replace_once(
        path,
        """function syncTorrentTableWidth(prefs=torrentColumnPreferences()){
  const table=$('#torrentTable');if(!table)return;const width=torrentColumnLayoutWidth(prefs),locked=Number.isFinite(width);
  table.classList.toggle('torrent-column-fixed-layout',locked);table.style.width=locked?`${width}px`:'';table.style.minWidth=locked?`${width}px`:'';
}""",
        """function syncTorrentTableWidth(prefs=torrentColumnPreferences()){
  const table=$('#torrentTable');if(!table)return;
  if(window.matchMedia?.('(max-width:820px)').matches){table.classList.remove('torrent-column-fixed-layout');table.style.width='';table.style.minWidth='';return}
  const minWidth=torrentColumnLayoutWidth(prefs),locked=Number.isFinite(minWidth);
  table.classList.toggle('torrent-column-fixed-layout',locked);table.style.width='100%';table.style.minWidth=locked?`${minWidth}px`:'';
}""",
        "pinned action table width",
    )

    replace_once(
        path,
        '<td class="row-actions"><button class="more-row" aria-label="Actions">•••</button></td></tr>`}',
        '<td class="row-spacer" aria-hidden="true"></td><td class="row-actions"><button class="more-row" aria-label="Actions">•••</button></td></tr>`}',
        "torrent row spacer",
    )

    replace_once(
        path,
        "const anchor=row.querySelector('.row-actions-head,.row-actions');",
        "const anchor=row.querySelector('.row-spacer-head,.row-spacer,.row-actions-head,.row-actions');",
        "column reorder spacer anchor",
    )

    replace_once(
        path,
        "window.addEventListener('resize',()=>requestAnimationFrame(syncTorrentWorkspaceLayout));",
        "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();syncTorrentTableWidth()}));",
        "responsive torrent table width sync",
    )


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    replacements = (
        (
            "/* 0.5.96 content-aligned one-edge torrent-column resizing. */",
            "/* 0.5.97 pinned torrent actions and contained horizontal overflow. */",
            "torrent-column contract comment",
        ),
        (
            '#torrentTable.torrent-column-fixed-layout{table-layout:fixed}',
            '#torrentTable{width:100%}\n#torrentTable.torrent-column-fixed-layout{table-layout:fixed}',
            "torrent table width baseline",
        ),
        (
            '#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important;white-space:nowrap;box-sizing:border-box}',
            '#torrentTable th.row-spacer-head,#torrentTable td.row-spacer{width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;min-inline-size:0!important;max-inline-size:none!important;padding-left:0;padding-right:0}\n#torrentTable th.row-actions-head,#torrentTable td.row-actions{width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important;min-inline-size:48px!important;max-inline-size:48px!important;white-space:nowrap;box-sizing:border-box;box-shadow:-1px 0 0 color-mix(in srgb,var(--border) 78%,transparent)}',
            "flexible spacer and pinned actions",
        ),
        (
            '.torrent-list-region .table-wrap{overflow:auto;contain:inline-size;overscroll-behavior-x:contain}',
            '.torrent-list-region .table-wrap{width:100%;max-inline-size:100%;overflow-x:auto;overflow-y:auto;contain:inline-size;overscroll-behavior-x:contain}',
            "torrent viewport overflow containment",
        ),
        (
            '@media(max-width:820px){.column-resize-handle{display:none!important}}',
            '@media(max-width:820px){.column-resize-handle{display:none!important}#torrentTable td.row-spacer{display:none!important}}',
            "mobile spacer suppression",
        ),
    )
    for old, new, label in replacements:
        replace_once(path, old, new, label)


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    replace_once(
        design,
        "- The far-right row-actions column is a fixed 48 px sticky control surface. It has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior, and horizontal table overflow remains contained by the torrent viewport.",
        "- The far-right row-actions column is a fixed 48 px sticky control surface. A non-interactive flexible spacer immediately before it absorbs unused table width, keeping the actions column pinned to the torrent viewport's right edge whenever the visible data columns fit. If customized data widths exceed the viewport, only the data region scrolls horizontally beneath the pinned actions surface; page-level horizontal overflow remains contained by the torrent viewport. The actions surface has no data-column identity, resize handle, reorder gesture, visibility control, or sorting behavior.",
        "pinned actions design rule",
    )

    testing = ROOT / "TESTING.md"
    replace_once(
        testing,
        "- Horizontally scroll a wide customized table and verify the far-right actions column remains fixed at exactly 48 px. It must never show a resize cursor/handle, change width, or create page-level horizontal overflow.",
        "- Verify the far-right actions column remains fixed at exactly 48 px and pinned to the torrent viewport's right edge. With data columns narrower than the viewport, unused width must be absorbed by the blank spacer immediately before Actions rather than moving Actions inward. With data columns wider than the viewport, horizontally scroll and verify only the data region moves beneath the pinned Actions surface; it must never show a resize cursor/handle, change width, or create page-level horizontal overflow.",
        "pinned actions manual test",
    )


def update_validator() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    replacements = (
        (
            "assert html.count('data-col=') >= 14 and '<th class=\"row-actions-head\"></th>' in html and 'data-col=\"actions\"' not in html",
            "assert html.count('data-col=') >= 14 and '<th class=\"row-spacer-head\" aria-hidden=\"true\"></th><th class=\"row-actions-head\"></th>' in html and 'data-col=\"actions\"' not in html",
            "fixed-column HTML validator",
        ),
        (
            "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js",
            "assert 'function snapshotTorrentColumnWidths' in app_js and 'function syncTorrentTableWidth' in app_js and 'function torrentColumnLayoutWidth' in app_js\n    assert \"window.matchMedia?.('(max-width:820px)').matches\" in app_js and \"table.style.width='100%'\" in app_js\n    assert 'class=\"row-spacer\" aria-hidden=\"true\"' in app_js and \"row.querySelector('.row-spacer-head,.row-spacer,.row-actions-head,.row-actions')\" in app_js",
            "pinned action JavaScript validator",
        ),
        (
            "assert '0.5.96 content-aligned one-edge torrent-column resizing' in app_css",
            "assert '0.5.97 pinned torrent actions and contained horizontal overflow' in app_css",
            "CSS contract validator",
        ),
        (
            "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions'):",
            "for stale in ('0.5.86 direct torrent-column manipulation','0.5.87 resizable torrent columns','0.5.89 stable torrent-column resize gesture','0.5.90 torrent-column boundary and overflow polish','0.5.91 centered and polling-stable torrent-column resizing','0.5.92 header sorting and streamlined torrent search','0.5.93 content-aligned sortable torrent headers','0.5.94 deterministic torrent-column header interactions','0.5.96 content-aligned one-edge torrent-column resizing'):",
            "stale CSS validator",
        ),
        (
            "assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css",
            "assert 'width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important' in app_css\n    assert 'width:48px!important;min-width:48px!important;max-width:48px!important;inline-size:48px!important' in app_css",
            "spacer and action width validator",
        ),
        (
            "assert '.torrent-list-region .table-wrap{overflow:auto;contain:inline-size;overscroll-behavior-x:contain}' in app_css",
            "assert '.torrent-list-region .table-wrap{width:100%;max-inline-size:100%;overflow-x:auto;overflow-y:auto;contain:inline-size;overscroll-behavior-x:contain}' in app_css",
            "overflow containment validator",
        ),
        (
            "assert 'Header labels follow the alignment of their body cells' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
            "assert 'Header labels follow the alignment of their body cells' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert 'flexible spacer immediately before it absorbs unused table width' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')",
            "design-language pinned actions validator",
        ),
        (
            "assert 'only the dragged right boundary moves' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
            "assert 'only the dragged right boundary moves' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n    assert 'unused width must be absorbed by the blank spacer immediately before Actions' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')",
            "manual-test pinned actions validator",
        ),
    )
    for old, new, label in replacements:
        replace_once(path, old, new, label)


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data.get("releases") or []
    if any(str(item.get("version")) == TARGET_VERSION for item in releases):
        raise RuntimeError(f"Release metadata already contains v{TARGET_VERSION}")
    previous = next((item for item in releases if str(item.get("version")) == PREVIOUS_VERSION), None)
    if not previous:
        raise RuntimeError(f"Missing v{PREVIOUS_VERSION} release metadata")

    decisions = copy.deepcopy(previous.get("decisions") or [])
    decisions.append("Keep the 48 px row-actions surface pinned to the torrent viewport edge with a non-interactive flexible spacer; customized data widths may scroll internally but must not move Actions offscreen or create page-level horizontal overflow.")

    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Pinned torrent actions and contained horizontal overflow",
        "summary": "Keeps the torrent row Actions surface locked to the far-right edge while allowing intentionally wide customized data columns to scroll only inside the torrent viewport.",
        "highlights": [
            "Adds a non-interactive flexible spacer immediately before the fixed 48 px Actions column so unused table width is absorbed before Actions rather than leaving the menu column floating inward.",
            "Keeps the torrent table at 100% of its viewport while using the customized data-column total only as a minimum width, preserving v0.5.96 one-edge resizing without redistributing neighboring data widths.",
            "When customized data columns exceed the available width, the data region scrolls horizontally beneath the sticky Actions column while the surrounding dashboard remains width-contained.",
            "Responsive layouts clear desktop fixed-table sizing and suppress the spacer so card-style mobile torrent rows do not inherit desktop horizontal geometry."
        ],
        "fixes": [
            "Prevents the far-right Actions menu from moving inward when resized data columns occupy less than the available torrent viewport.",
            "Prevents wide customized torrent layouts from pushing the Actions control offscreen or creating page-level horizontal overflow."
        ],
        "technical": [
            "The spacer is deliberately outside data-col identity, persistence, sorting, resizing, and reordering; applyColumnPrefs inserts configurable data cells before the spacer.",
            "syncTorrentTableWidth now leaves table width at 100% and applies the visible-column sum as min-width only, allowing the spacer to consume slack while preserving exact snapshotted data widths.",
            "The existing sticky right:0 Actions header/cells remain the only horizontal lock; no unrelated data column is shrunk to compensate for a resize."
        ],
        "validation": [
            "The UI audit requires the spacer header/row cells, 100%-width plus minimum-content table geometry, sticky 48 px Actions surface, explicit torrent-viewport overflow containment, and responsive clearing of desktop width state.",
            "Manual coverage verifies Actions stays at the right edge both below and above the overflow threshold, only data scrolls underneath it, one-edge resize behavior remains unchanged, and the page itself never gains horizontal overflow.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "known_issues": [],
        "architecture": copy.deepcopy(previous.get("architecture") or []),
        "next_steps": copy.deepcopy(previous.get("next_steps") or []),
        "decisions": decisions,
    })
    data["releases"] = releases
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_continuity() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", TARGET_VERSION],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    update_versions()
    update_html()
    update_javascript()
    update_css()
    update_docs()
    update_validator()
    update_release_metadata()
    generate_continuity()


if __name__ == "__main__":
    main()
