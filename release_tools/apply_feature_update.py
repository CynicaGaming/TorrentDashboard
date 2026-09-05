#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.120"
NEW = "0.5.121"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
viewport_anchor = "const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];\n"
viewport_code = """const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
function syncVisualViewportMetrics(){
  const viewport=window.visualViewport;
  const height=Math.max(1,Math.round(viewport?.height||window.innerHeight||1));
  const offsetTop=Math.max(0,Math.round(viewport?.offsetTop||0));
  document.documentElement.style.setProperty('--td-visual-viewport-height',`${height}px`);
  document.documentElement.style.setProperty('--td-visual-viewport-top',`${offsetTop}px`);
}
syncVisualViewportMetrics();
window.addEventListener('resize',syncVisualViewportMetrics);
window.visualViewport?.addEventListener('resize',syncVisualViewportMetrics);
window.visualViewport?.addEventListener('scroll',syncVisualViewportMetrics);
"""
app_js = replace_once(app_js, viewport_anchor, viewport_code, "visual viewport hook")
app_js = replace_once(
    app_js,
    "function openAddTorrent(){\n  if(state.server==='all')return toast('Select a specific client first','error');\n  $('#addModal').classList.remove('hidden');",
    "function openAddTorrent(){\n  if(state.server==='all')return toast('Select a specific client first','error');\n  syncVisualViewportMetrics();\n  $('#addModal').classList.remove('hidden');",
    "Add Torrent viewport refresh",
)
write("static/app.js", app_js)

index = read("static/index.html").replace(OLD, NEW)
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v05120", "torrent-dashboard-v05121").replace(OLD, NEW)
write("static/sw.js", sw)

# Mobile Add Torrent modal: size to the actual visual viewport and keep the action footer docked outside the body scroller.
css = read("static/app.css")
old_820 = "@media(max-width:820px){.add-torrent-card{width:min(720px,calc(100% - 20px));height:min(92vh,820px)}.add-torrent-body{grid-template-columns:1fr;overflow:auto}.add-torrent-options{overflow:visible;border-right:0;border-bottom:1px solid var(--border)}.add-torrent-preview{overflow:visible;grid-template-rows:auto auto}.add-preview-empty{min-height:170px}.add-torrent-footer{position:sticky;bottom:0}.add-torrent-status{display:none}}"
new_820 = "/* 0.5.121 mobile Add Torrent visual-viewport action dock. */\n@media(max-width:820px){#addModal{place-items:start center;padding:calc(var(--td-visual-viewport-top,0px) + max(6px,env(safe-area-inset-top))) max(6px,env(safe-area-inset-right)) max(6px,env(safe-area-inset-bottom)) max(6px,env(safe-area-inset-left))}.add-torrent-card{width:min(720px,100%);height:min(calc(var(--td-visual-viewport-height,100dvh) - 12px),820px);max-height:min(calc(var(--td-visual-viewport-height,100dvh) - 12px),820px);margin:0 auto}.add-torrent-body{grid-template-columns:1fr;overflow:auto;overscroll-behavior:contain}.add-torrent-options{overflow:visible;border-right:0;border-bottom:1px solid var(--border)}.add-torrent-preview{overflow:visible;grid-template-rows:auto auto}.add-preview-empty{min-height:170px}.add-torrent-footer{position:relative;bottom:auto;z-index:4;padding-bottom:calc(11px + env(safe-area-inset-bottom));box-shadow:0 -12px 28px rgba(0,0,0,.18)}.add-torrent-status{display:none}}"
css = replace_once(css, old_820, new_820, "820px Add Torrent layout")
old_520 = "@media(max-width:520px){.add-torrent-card{width:calc(100% - 12px);height:96vh;max-height:96vh;border-radius:14px}.add-torrent-body{display:block}.add-torrent-options,.add-torrent-preview{padding:11px}.add-torrent-section .two{grid-template-columns:1fr}.add-content-columns{grid-template-columns:minmax(0,1fr) 62px 62px}.add-info-grid{grid-template-columns:96px minmax(0,1fr)}.add-torrent-footer{padding:9px 10px}.add-torrent-actions{width:100%}.add-torrent-actions button{flex:1}}"
new_520 = "@media(max-width:520px){#addModal{padding-left:0;padding-right:0;padding-bottom:0}.add-torrent-card{width:100%;height:var(--td-visual-viewport-height,100dvh);max-height:var(--td-visual-viewport-height,100dvh);border-radius:0}.add-torrent-body{display:block}.add-torrent-options,.add-torrent-preview{padding:11px}.add-torrent-section .two{grid-template-columns:1fr}.add-content-columns{grid-template-columns:minmax(0,1fr) 62px 62px}.add-info-grid{grid-template-columns:96px minmax(0,1fr)}.add-torrent-footer{padding:9px 10px calc(9px + env(safe-area-inset-bottom))}.add-torrent-actions{width:100%}.add-torrent-actions button{flex:1;min-width:0;min-height:44px}}"
css = replace_once(css, old_520, new_520, "520px Add Torrent layout")
write("static/app.css", css)

# Durable design/testing contract.
design = read("DESIGN_LANGUAGE.md")
design += """

## Mobile Add Torrent action dock

- At mobile widths, Add Torrent is sized to the browser's visual viewport rather than the larger layout viewport so browser chrome and the on-screen keyboard cannot hide the final action row.
- The Add Torrent header and footer are fixed structural regions of the modal; only the options/preview body scrolls.
- The footer respects bottom safe-area insets and keeps **Save .torrent file**, **Cancel**, and **Add torrent** continuously reachable after metadata expands the content preview.
- Mobile viewport handling is presentation-only. Metadata generation, file selection/priorities, and the qBitTorrent add request remain unchanged.
"""
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing += """

### Mobile Add Torrent action dock

- At 820 px and below, open Add Torrent and verify the header and bottom action row stay visible while the options/metadata body scrolls independently.
- Generate metadata for a torrent with enough files/folders to make the preview substantially taller than the phone viewport; **Add torrent**, **Cancel**, and **Save .torrent file** must remain reachable without scrolling the footer into view.
- Repeat with the browser's address/navigation chrome visible and verify the action row is not clipped behind it.
- Focus a text field so the on-screen keyboard opens, then scroll the modal body and verify the action footer remains inside the visible viewport; dismiss the keyboard and verify the modal expands back to the available viewport height.
- On a device with a bottom safe area/home indicator, verify the footer has usable clearance and the primary **Add torrent** control remains a full touch target.
- Submit both a magnet-metadata add and a parsed `.torrent` add from mobile and verify the existing qBitTorrent request behavior and selected file priorities are unchanged.
"""
write("TESTING.md", testing)

validator = read("release_tools/validate_ui_strings.py")
validator_anchor = "    assert '### Add Torrent folder control row' in testing_md\n\n    print(\"UI string audit passed\")"
validator_new = """    assert '### Add Torrent folder control row' in testing_md

    # 0.5.121 keeps the mobile Add Torrent action footer inside the actual visual viewport.
    assert 'function syncVisualViewportMetrics()' in app_js
    assert "window.visualViewport?.addEventListener('resize',syncVisualViewportMetrics)" in app_js
    assert "window.visualViewport?.addEventListener('scroll',syncVisualViewportMetrics)" in app_js
    assert "syncVisualViewportMetrics();\\n  $('#addModal').classList.remove('hidden');" in app_js
    assert '--td-visual-viewport-height' in app_css and '--td-visual-viewport-top' in app_css
    assert '#addModal{place-items:start center' in app_css
    assert '.add-torrent-footer{position:relative;bottom:auto;z-index:4' in app_css
    assert 'height:96vh;max-height:96vh' not in app_css
    assert 'min-height:44px' in app_css
    assert '## Mobile Add Torrent action dock' in design_language
    assert '### Mobile Add Torrent action dock' in testing_md

    print("UI string audit passed")"""
validator = replace_once(validator, validator_anchor, validator_new, "UI validator anchor")
write("release_tools/validate_ui_strings.py", validator)

# Release metadata; preserve the latest architectural handoff fields.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
latest = data["releases"][-1]
entry = {
    "version": NEW,
    "date": "2026-09-05",
    "status": "prerelease",
    "title": "Mobile Add Torrent action dock",
    "summary": "Keeps the Add Torrent action footer continuously reachable on phones by sizing the modal to the actual visual viewport while metadata/options scroll independently.",
    "highlights": [
        "Add Torrent now follows the mobile browser visual viewport instead of relying on static vh sizing.",
        "Save .torrent file, Cancel, and Add torrent remain docked outside the scrolling metadata/options body.",
        "The mobile action footer reserves safe-area clearance and retains full touch targets when browser chrome or the software keyboard reduces usable space."
    ],
    "fixes": [
        "Fixes mobile cases where generating metadata made the final Add Torrent action row difficult or impossible to reach reliably."
    ],
    "technical": [
        "VisualViewport resize/scroll metrics feed CSS custom properties with 100dvh/innerHeight fallbacks.",
        "The qBitTorrent add/metadata request paths are unchanged; this increment only changes mobile modal geometry."
    ],
    "validation": [
        "The UI audit requires visual-viewport metrics, a non-scrolling Add Torrent footer, safe-area padding, and removal of the old 96vh phone sizing.",
        "Manual coverage includes metadata-expanded previews, browser chrome, on-screen keyboard visibility, safe-area devices, and both magnet and local .torrent submission paths."
    ],
    "known_issues": []
}
for key in ("architecture", "decisions", "next_steps"):
    if key in latest:
        entry[key] = latest[key]
data["releases"].append(entry)
release_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
