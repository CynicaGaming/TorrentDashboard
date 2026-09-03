#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_VERSION = "0.5.103"
TARGET_VERSION = "0.5.104"


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
        raise RuntimeError("Expected v0.5.103 frontend references in static/index.html")
    index.write_text(text.replace(PREVIOUS_VERSION, TARGET_VERSION), encoding="utf-8")

    replace_once(ROOT / "static" / "app.js", f"const FRONTEND_BUILD='{PREVIOUS_VERSION}';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v05103" not in text or f"v={PREVIOUS_VERSION}" not in text:
        raise RuntimeError("Expected v0.5.103 service-worker references")
    text = text.replace("torrent-dashboard-v05103", "torrent-dashboard-v05104")
    sw.write_text(text.replace(f"v={PREVIOUS_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_css() -> None:
    path = ROOT / "static" / "app.css"
    numeric_rule = '#torrentTable [data-col="size"],#torrentTable [data-col="seeds"],#torrentTable [data-col="peers"],#torrentTable [data-col="down"],#torrentTable [data-col="up"],#torrentTable [data-col="eta"],#torrentTable [data-col="ratio"]{text-align:right;white-space:nowrap}'
    desktop_rule = '@media(min-width:821px){' + numeric_rule + '}'
    replace_once(path, numeric_rule, desktop_rule, "desktop-only torrent numeric alignment")

    marker = '/* 0.5.103 mobile bulk action layering. */\n@media(max-width:700px){.bulkbar{bottom:var(--torrent-bulk-bottom,116px)!important;z-index:74}}'
    addition = marker + '''\n\n/* 0.5.104 mobile torrent metadata alignment. */\n@media(max-width:820px){\n  #torrentTable td.mobile-grid{text-align:left!important}\n  #torrentTable td.mobile-grid:before{justify-self:start;text-align:left}\n  #torrentTable td.mobile-grid>span{justify-self:end;text-align:right;max-width:100%}\n}'''
    replace_once(path, marker, addition, "mobile torrent metadata alignment CSS")


def update_docs() -> None:
    design = ROOT / "DESIGN_LANGUAGE.md"
    needle = "- Mobile keeps the existing card presentation; the fixed desktop width calculation is cleared at the mobile breakpoint.\n"
    addition = "- Mobile metadata rows use a consistent left-label/right-value grid. Desktop numeric-column text alignment must not leak into mobile pseudo-labels or shift labels toward the card center.\n"
    text = design.read_text(encoding="utf-8")
    if text.count(needle) != 1:
        raise RuntimeError("Expected mobile fixed-column design guidance exactly once")
    design.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")

    testing = ROOT / "TESTING.md"
    needle = "- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing. Long-press a non-control area of a torrent card for roughly half a second and verify the same torrent context menu opens; move/scroll before the threshold and verify no menu opens. A normal tap must still open Torrent details, while the tap following a completed long press must not.\n"
    addition = "- On mobile cards, verify Size, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, and Tags all keep their field label at the left edge and their value at the right edge; desktop right-alignment rules must not move numeric labels toward the center divider.\n"
    text = testing.read_text(encoding="utf-8")
    if text.count(needle) != 1:
        raise RuntimeError("Expected mobile fixed-column test exactly once")
    testing.write_text(text.replace(needle, needle + addition, 1), encoding="utf-8")


def update_validation() -> None:
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    needle = "    assert 'bulk action bar is fully visible above the disclosure bar' in testing\n    print(\"UI string audit passed\")"
    replacement = '''    assert 'bulk action bar is fully visible above the disclosure bar' in testing

    # 0.5.104 keeps desktop numeric alignment out of the mobile card grid and
    # gives every mobile metadata row a stable left-label/right-value contract.
    desktop_numeric = '@media(min-width:821px){#torrentTable [data-col="size"],#torrentTable [data-col="seeds"],#torrentTable [data-col="peers"],#torrentTable [data-col="down"],#torrentTable [data-col="up"],#torrentTable [data-col="eta"],#torrentTable [data-col="ratio"]{text-align:right;white-space:nowrap}}'
    assert desktop_numeric in app_css
    assert '0.5.104 mobile torrent metadata alignment' in app_css
    assert '#torrentTable td.mobile-grid{text-align:left!important}' in app_css
    assert '#torrentTable td.mobile-grid:before{justify-self:start;text-align:left}' in app_css
    assert '#torrentTable td.mobile-grid>span{justify-self:end;text-align:right;max-width:100%}' in app_css
    assert 'consistent left-label/right-value grid' in design
    assert 'desktop right-alignment rules must not move numeric labels toward the center divider' in testing
    print("UI string audit passed")'''
    replace_once(path, needle, replacement, "v0.5.104 UI validation")


def update_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    releases = data["releases"]
    if any(item.get("version") == TARGET_VERSION for item in releases):
        raise RuntimeError(f"Release {TARGET_VERSION} already exists")
    previous = next((item for item in reversed(releases) if item.get("version") == PREVIOUS_VERSION), None)
    if previous is None:
        raise RuntimeError(f"Release {PREVIOUS_VERSION} not found")
    decisions = copy.deepcopy(previous.get("decisions", []))
    decisions.append("Keep desktop torrent-column alignment breakpoint-scoped: mobile cards use a consistent left-label/right-value metadata grid regardless of desktop numeric alignment.")
    releases.append({
        "version": TARGET_VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Mobile torrent metadata alignment",
        "summary": "Restores consistent mobile torrent-card metadata alignment after desktop numeric-column alignment leaked into responsive card labels.",
        "highlights": [
            "Scopes Size, Seeds, Peers, Down, Up, ETA, and Ratio right-alignment to desktop/tablet layouts only.",
            "Keeps every mobile metadata field label anchored to the left side of the card while its value stays anchored to the right.",
            "Applies the same mobile value alignment to Category and Tags so the metadata list reads as one consistent two-sided grid."
        ],
        "fixes": [
            "Fixes Size, Seeds, Peers, Download, Upload, ETA, and Ratio labels drifting toward the middle of mobile torrent cards.",
            "Removes the inconsistent mobile presentation where Category/Tags and numeric fields used different horizontal alignment patterns."
        ],
        "technical_notes": [
            "The v0.5.101 numeric data-column text-align rule is now wrapped in the min-width:821px desktop/tablet breakpoint.",
            "At max-width:820px, mobile-grid cells explicitly restore left text alignment for labels and right alignment for their value spans.",
            "The correction is CSS-only apart from release/build metadata and does not change torrent data, polling, sorting, selection, context-menu, or Torrent details behavior."
        ],
        "validation": [
            "The UI audit requires desktop-only numeric alignment plus explicit mobile left-label/right-value rules and matching design/test documentation.",
            "Manual mobile coverage checks every torrent-card metadata row for stable left labels and right values, including Category and Tags.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
        ],
        "decisions": decisions,
        "known_issues": []
    })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    update_versions()
    update_css()
    update_docs()
    update_validation()
    update_release_metadata()
    subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", TARGET_VERSION], cwd=ROOT, check=True)
    print(f"Applied v{TARGET_VERSION} mobile torrent metadata alignment fix")


if __name__ == "__main__":
    main()
