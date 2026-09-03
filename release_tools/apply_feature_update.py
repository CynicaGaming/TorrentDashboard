#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.104"
NEW = "0.5.105"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(rel, old, new):
    text = read(rel)
    if old not in text:
        raise RuntimeError(f"Expected text not found in {rel}: {old[:80]!r}")
    write(rel, text.replace(old, new, 1))


# Keep all shipped frontend/backend build identifiers synchronized.
replace_once("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
for rel in ("static/app.js", "static/index.html", "static/sw.js"):
    text = read(rel)
    if OLD not in text:
        raise RuntimeError(f"Expected {OLD} build marker in {rel}")
    write(rel, text.replace(OLD, NEW))

# Compact mobile torrent cards into a two-column metadata matrix while keeping
# Name and Progress full width. The checkbox returns to an overlay control so it
# does not consume a dedicated row, and torrent names may use up to two lines.
css = read("static/app.css")
marker = "/* 0.5.105 compact mobile torrent cards. */"
if marker in css:
    raise RuntimeError("v0.5.105 mobile card CSS already present")
css += r'''

/* 0.5.105 compact mobile torrent cards. */
@media(max-width:820px){
  #torrentTable tbody{gap:6px}
  #torrentTable tbody tr{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:14px;row-gap:0;padding:10px 12px 9px}
  #torrentTable tbody tr>td{width:100%;min-width:0;height:auto}
  #torrentTable td.check{position:absolute;right:12px;left:auto;top:10px;width:auto!important;min-width:0!important;max-width:none!important;inline-size:auto!important;padding:0;z-index:5;background:transparent;box-shadow:none}
  #torrentTable td[data-col="name"],#torrentTable td[data-col="progress"]{grid-column:1/-1}
  #torrentTable td[data-col="name"]{padding:2px 38px 7px 0}
  #torrentTable td[data-col="name"] .torrent-name{display:-webkit-box;width:auto;max-width:100%;white-space:normal;overflow:hidden;text-overflow:clip;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-height:1.35}
  #torrentTable td.mobile-grid{display:grid!important;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:6px;padding:2px 0;min-height:27px}
  #torrentTable td.mobile-grid:before{justify-self:start;text-align:left;white-space:nowrap}
  #torrentTable td.mobile-grid>span{justify-self:end;text-align:right;min-width:0;max-width:100%;overflow:hidden;text-overflow:ellipsis}
  #torrentTable td[data-col="state"] .state{padding:4px 7px}
  #torrentTable td[data-col="progress"]{padding:5px 0 7px}
}
@media(max-width:430px){
  #torrentTable tbody tr{column-gap:10px;padding-left:10px;padding-right:10px}
  #torrentTable td.mobile-grid{gap:4px}
}
'''
write("static/app.css", css)

# Record the responsive layout contract in durable public documentation.
design = read("DESIGN_LANGUAGE.md")
design_note = '''

### Compact mobile torrent cards

At the mobile breakpoint, torrent cards use a compact two-column metadata matrix rather than giving every desktop field a full-width row. Name and Progress remain full-width; Size/Status, Seeds/Peers, Download/Upload, ETA/Ratio, and Category/Tags share paired rows. The selection checkbox is positioned at the card's top-right without consuming layout height. Torrent names may wrap to at most two lines. Every metadata item keeps its label at the left of its local cell and its value at the right. This mobile layout is independent of the fixed desktop column proportions.
'''
if "### Compact mobile torrent cards" not in design:
    design = design.rstrip() + design_note + "\n"
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing_note = '''

### Compact mobile torrent cards

- At 820 px and below, verify each torrent card uses two metadata columns: Size/Status, Seeds/Peers, Download/Upload, ETA/Ratio, and Category/Tags. Name and Progress must span the full card width.
- Verify the selection checkbox is overlaid at the card's top-right and no longer consumes its own full-width row.
- Verify long torrent names wrap to no more than two lines and do not force horizontal overflow.
- Verify each compact metadata item keeps its label left and its value right, including the Status pill and long Category/Tags values.
- Compare several cards with v0.5.104-sized content and verify substantially more than one torrent can fit in a typical phone viewport while preserving all displayed metadata.
- Recheck long-press row actions, normal tap-to-open Torrent details, checkbox selection, and the mobile bulk-action/detail-pane stacking behavior after the grid compaction.
'''
if "### Compact mobile torrent cards" not in testing:
    testing = testing.rstrip() + testing_note + "\n"
write("TESTING.md", testing)

# Strengthen the UI audit around the responsive contract rather than relying on
# visual testing alone.
validator = read("release_tools/validate_ui_strings.py")
anchor = '    print("UI string audit passed")'
checks = '''    # 0.5.105 compacts mobile torrent cards without changing the desktop table.\n    assert '0.5.105 compact mobile torrent cards' in app_css\n    assert '#torrentTable tbody tr{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)' in app_css\n    assert '#torrentTable td[data-col="name"],#torrentTable td[data-col="progress"]{grid-column:1/-1}' in app_css\n    assert '#torrentTable td.check{position:absolute;right:12px;left:auto;top:10px' in app_css\n    assert '-webkit-line-clamp:2' in app_css\n    assert 'two-column metadata matrix' in design\n    assert 'Size/Status, Seeds/Peers, Download/Upload, ETA/Ratio, and Category/Tags' in testing\n\n'''
if "0.5.105 compacts mobile torrent cards" not in validator:
    if anchor not in validator:
        raise RuntimeError("UI validator print anchor not found")
    validator = validator.replace(anchor, checks + anchor, 1)
write("release_tools/validate_ui_strings.py", validator)

# Append structured release metadata while preserving the current architecture,
# decisions, and recorded next engineering objective from the latest release.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
releases = data.get("releases") or []
if any(str(item.get("version")) == NEW for item in releases):
    raise RuntimeError(f"Release metadata for v{NEW} already exists")
if not releases:
    raise RuntimeError("No prior release metadata available")
latest = max(releases, key=lambda item: tuple(int(x) for x in str(item.get("version", "0.0.0")).split(".")[:3]))
entry = copy.deepcopy(latest)
entry.update({
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Compact mobile torrent cards",
    "summary": "Reduces mobile torrent-card height by pairing metadata fields into a compact two-column matrix while keeping Name and Progress full-width and preserving all displayed torrent information.",
    "highlights": [
        "Pairs Size with Status, Seeds with Peers, Download with Upload, ETA with Ratio, and Category with Tags on mobile instead of rendering every field as a full-width row.",
        "Returns the selection checkbox to an overlaid top-right position so it no longer consumes a dedicated card row.",
        "Allows torrent names to wrap to at most two lines on mobile while preserving the fixed single-line desktop table presentation."
    ],
    "fixes": [
        "Fixes mobile torrent cards becoming excessively tall after the fixed desktop-column layout and responsive alignment corrections.",
        "Restores practical mobile list density without hiding torrent metadata or changing desktop table geometry."
    ],
    "technical": [
        "The responsive torrent row becomes a two-column CSS grid at 820 px and below; Name and Progress span both columns while paired metadata cells occupy one column each.",
        "The compact layout remains CSS-only and preserves the existing row DOM, sorting data, long-press context menu, polling, selection, and Torrent details behavior."
    ],
    "validation": [
        "The UI audit asserts the two-column mobile grid, full-width Name/Progress rows, overlaid checkbox, two-line name clamp, and matching design/test contracts.",
        "Manual mobile coverage checks density, long names, metadata alignment, selection, long-press actions, and Torrent details/bulk-action interaction.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": []
})
releases.append(entry)
release_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate derived continuity files so the subsequent validation checks the
# applied source and generated state together.
subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)

print(f"Applied v{NEW} compact mobile torrent cards")
