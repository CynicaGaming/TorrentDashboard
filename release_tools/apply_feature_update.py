from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.114"
PREVIOUS = "0.5.113"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing transform anchor: {label}")
    return text.replace(old, new, 1)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';", "frontend build")
write("static/app.js", app_js)

index = read("static/index.html").replace(PREVIOUS, VERSION)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05113", "torrent-dashboard-v05114").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

# Keep body-aligned header text, but make every sort affordance use the same trailing edge.
css = read("static/app.css")
old_numeric_heading = '#torrentTable thead th[data-col="size"] .torrent-sort-heading,#torrentTable thead th[data-col="seeds"] .torrent-sort-heading,#torrentTable thead th[data-col="peers"] .torrent-sort-heading,#torrentTable thead th[data-col="down"] .torrent-sort-heading,#torrentTable thead th[data-col="up"] .torrent-sort-heading,#torrentTable thead th[data-col="eta"] .torrent-sort-heading,#torrentTable thead th[data-col="ratio"] .torrent-sort-heading{justify-content:flex-end;padding-left:18px;padding-right:0}'
new_numeric_heading = '#torrentTable thead th[data-col="size"] .torrent-sort-heading,#torrentTable thead th[data-col="seeds"] .torrent-sort-heading,#torrentTable thead th[data-col="peers"] .torrent-sort-heading,#torrentTable thead th[data-col="down"] .torrent-sort-heading,#torrentTable thead th[data-col="up"] .torrent-sort-heading,#torrentTable thead th[data-col="eta"] .torrent-sort-heading,#torrentTable thead th[data-col="ratio"] .torrent-sort-heading{justify-content:flex-end}'
css = replace_once(css, old_numeric_heading, new_numeric_heading, "numeric header trailing padding")
old_numeric_icon = '#torrentTable thead th[data-col="size"] .torrent-sort-icon,#torrentTable thead th[data-col="seeds"] .torrent-sort-icon,#torrentTable thead th[data-col="peers"] .torrent-sort-icon,#torrentTable thead th[data-col="down"] .torrent-sort-icon,#torrentTable thead th[data-col="up"] .torrent-sort-icon,#torrentTable thead th[data-col="eta"] .torrent-sort-icon,#torrentTable thead th[data-col="ratio"] .torrent-sort-icon{left:0;right:auto}\n'
css = replace_once(css, old_numeric_icon, '', "numeric left-side sort icon override")
css += '\n/* 0.5.114 consistent trailing-edge torrent sort chevrons */\n'
write("static/app.css", css)

# Durable design/testing contract.
design = read("DESIGN_LANGUAGE.md")
design += """

### Torrent sort chevrons

Torrent-table header labels continue to align with their body data: text-oriented headers remain left-aligned and numeric headers remain right-aligned. The sort affordance itself is independent of that text alignment. Every sortable torrent header uses the same trailing/right-edge chevron position so the indicator is visually associated with its owning column and never appears to belong to the neighboring column.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Torrent sort chevrons

- On desktop, verify Name, Status, Progress, Category, and Tags keep their existing left-aligned header labels.
- Verify Size, Seeds, Peers, Down, Up, ETA, and Ratio remain right-aligned with their body values.
- Hover/focus each sortable header and verify its chevron appears at the right/trailing edge of that same header, including every numeric column.
- Sort each numeric and text column in both directions and verify the active chevron remains on the right edge and changes direction without shifting the label alignment or column width.
- Verify no header chevron appears on the left edge or visually reads as belonging to the adjacent column.
"""
write("TESTING.md", testing)

# Release metadata while preserving accumulated decisions/objectives.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data["releases"]
if not any(item.get("version") == VERSION for item in releases):
    previous = releases[-1]
    decisions = list(previous.get("decisions", []))
    decisions.append("Keep torrent header text aligned with its body content while placing every sort chevron on the same trailing/right edge regardless of column type.")
    releases.append({
        "version": VERSION,
        "date": "2026-09-03",
        "status": "prerelease",
        "title": "Consistent torrent sort chevrons",
        "summary": "Makes every torrent-table sort indicator use the same trailing edge while preserving content-aligned header labels.",
        "highlights": [
            "All sortable torrent headers now place their chevron on the right edge of the owning column.",
            "Numeric header labels remain right-aligned with their body values; text-oriented headers remain left-aligned.",
            "Sorting behavior, fixed column sizing, viewport-proportional workspace sizing, and mobile presentation are unchanged."
        ],
        "fixes": [
            "Removes the numeric-column CSS override that moved Size, Seeds, Peers, Down, Up, ETA, and Ratio chevrons to the left edge.",
            "Prevents sort indicators from visually reading as though they belong to the preceding column."
        ],
        "technical": [
            "Numeric torrent-sort headings now inherit the shared right-side padding used to reserve chevron space and override only justify-content:flex-end.",
            "The generic .torrent-sort-icon right:0 rule now owns icon placement for every configurable data header."
        ],
        "validation": [
            "The UI audit requires the numeric heading alignment override, rejects any left-side numeric sort-icon override, and preserves the generic right:0 icon contract.",
            "Manual coverage checks hover/focus and ascending/descending sort states across both numeric and text columns.",
            "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
        ],
        "known_issues": [],
        "decisions": decisions,
    })
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

validator = read("release_tools/validate_ui_strings.py")
anchor = "    print(\"UI string audit passed\")\n"
checks = """    # 0.5.114 uses a single trailing-edge sort affordance while preserving body-aligned header labels.\n    numeric_heading = '#torrentTable thead th[data-col=\\\"size\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"seeds\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"peers\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"down\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"up\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"eta\\\"] .torrent-sort-heading,#torrentTable thead th[data-col=\\\"ratio\\\"] .torrent-sort-heading{justify-content:flex-end}'\n    assert numeric_heading in app_css\n    assert '.torrent-sort-heading{position:relative;display:flex;width:100%;min-width:0;align-items:center;justify-content:flex-start;padding-right:18px' in app_css\n    assert '.torrent-sort-icon{position:absolute;right:0;' in app_css\n    assert '.torrent-sort-icon{left:0' not in app_css\n    assert '.torrent-sort-icon{left:' not in app_css\n    assert 'left:0;right:auto' not in app_css\n    assert '0.5.114 consistent trailing-edge torrent sort chevrons' in app_css\n    assert '### Torrent sort chevrons' in design\n    assert '### Torrent sort chevrons' in testing\n\n"""
validator = replace_once(validator, anchor, checks + anchor, "v0.5.114 validator insertion")
write("release_tools/validate_ui_strings.py", validator)

subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", VERSION], cwd=ROOT, check=True)
print("Applied v0.5.114 consistent torrent sort chevrons")
