#!/usr/bin/env python3
"""Apply v0.5.69 dashboard empty-state and live-metric cleanup."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.68"
NEW = "0.5.69"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Application version.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

# HTML build references, metric semantics, and addressable empty-state copy.
html = read("static/index.html")
html = html.replace(f'content="{OLD}" name="torrent-dashboard-build"', f'content="{NEW}" name="torrent-dashboard-build"')
html = html.replace(f'?v={OLD}', f'?v={NEW}')
html = replace_once(
    html,
    '<article class="desktop-extra"><span>Last Update</span><strong id="mUpdated">—</strong><small id="mHealth">—</small></article>',
    '<article class="desktop-extra"><span>Torrents</span><strong id="mTotal">—</strong><small id="mTorrentSummary">—</small></article>',
    "last-update metric",
)
html = replace_once(
    html,
    '<div class="empty hidden" id="empty"><strong>No Torrents Match This View</strong><span>Change the filter or search query.</span></div>',
    '<div class="empty hidden" id="empty"><strong id="emptyTitle">No torrents yet</strong><span id="emptyText">Add a torrent to get started.</span></div>',
    "torrent empty state markup",
)
if OLD in html:
    raise RuntimeError("index.html still contains old build version")
write("static/index.html", html)

# Frontend build and context-aware empty-state behavior.
app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = replace_once(
    app_js,
    "$('#mUpdated').textContent=new Date((d.ts||Date.now()/1000)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});$('#mHealth').textContent=uiText(d.ok===false?'connectionIssue':'healthy');",
    "const completed=t.filter(isComplete).length,paused=t.filter(isPaused).length;$('#mTotal').textContent=t.length;$('#mTorrentSummary').textContent=t.length?`${completed} completed · ${paused} paused`:'No torrents';",
    "live update metric",
)
old_render = "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');$('#empty').classList.toggle('hidden',list.length>0);$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}"
new_render = """function emptyStateCopy(){
  const hasFacet=!!(state.search||state.category||state.tag||state.tracker);
  if(!state.torrents.length)return state.me?.can_manage?['No torrents yet','Add a torrent to get started.']:['No torrents available','There are no torrents on this server.'];
  if(hasFacet)return['No torrents match these filters','Adjust your search or filters.'];
  if(state.filter==='active')return['No active torrents','Nothing is downloading right now.'];
  if(state.filter==='completed')return['No completed torrents','Completed torrents will appear here.'];
  if(state.filter==='paused')return['No paused torrents','Paused torrents will appear here.'];
  return['No torrents in this view','Try another filter.'];
}
function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}"""
app_js = replace_once(app_js, old_render, new_render, "torrent empty state behavior")
write("static/app.js", app_js)

# Center the empty state within the list body rather than after the flexing table region.
css = read("static/app.css")
css = replace_once(
    css,
    ".torrent-list-region{display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}\n  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}\n",
    ".torrent-list-region{position:relative;display:flex;flex:1 1 auto;min-height:0;flex-direction:column;overflow:hidden}\n  .torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto;overscroll-behavior:contain}\n  .torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center;padding:20px;text-align:center;pointer-events:none}\n",
    "centered torrent empty state",
)
write("static/app.css", css)

# Service worker generation.
sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0568", "torrent-dashboard-v0569")
sw = sw.replace(f"?v={OLD}", f"?v={NEW}")
if OLD in sw or "v0568" in sw:
    raise RuntimeError("service worker still contains old build version")
write("static/sw.js", sw)

# Durable dashboard-state language contract.
design = read("DESIGN_LANGUAGE.md")
section = """

## Empty states and live dashboard metrics

Empty-state language must describe why the current surface is empty rather than using one generic message for every zero-row condition.

- A client with no torrents should say that there are no torrents yet/available; it should not imply that filters are hiding results.
- Filtered views should name the relevant condition, such as no active, completed, or paused torrents, or explain that search/filter criteria exclude all rows.
- Empty states inside bounded list workspaces should remain visually centered in the available list body and should not be pushed below a flexing scroll region.
- Primary dashboard metric cards should represent meaningful operational state. Values that refresh every polling interval, such as a per-second "Last update" timestamp, should not occupy a permanent summary card unless staleness itself requires attention.
- Connection failures and stale data should be surfaced as health/error states rather than requiring users to infer problems from a timestamp.
"""
if "## Empty states and live dashboard metrics" not in design:
    design = design.rstrip() + section + "\n"
write("DESIGN_LANGUAGE.md", design)

# Lock the corrected dashboard-state contract into UI validation.
validator = read("release_tools/validate_ui_strings.py")
anchor = '    assert "height:calc(100dvh - 320px);min-height:480px" not in app_css\n'
addition = """    assert 'id=\"mTotal\"' in html and 'id=\"mTorrentSummary\"' in html
    assert 'id=\"mUpdated\"' not in html and 'id=\"mHealth\"' not in html
    assert 'id=\"emptyTitle\"' in html and 'id=\"emptyText\"' in html
    assert "function emptyStateCopy()" in app_js
    assert "['No active torrents','Nothing is downloading right now.']" in app_js
    assert "['No torrents match these filters','Adjust your search or filters.']" in app_js
    assert ".torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center" in app_css
"""
if addition.strip() not in validator:
    validator = replace_once(validator, anchor, anchor + addition, "dashboard state validator")
write("release_tools/validate_ui_strings.py", validator)

# Structured release metadata.
notes_path = ROOT / "release_notes" / "releases.json"
notes = json.loads(notes_path.read_text(encoding="utf-8"))
releases = notes.get("releases", [])
if any(item.get("version") == NEW for item in releases):
    raise RuntimeError(f"release metadata already contains {NEW}")
previous = releases[-1] if releases else {}
releases.append({
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Context-aware dashboard empty states",
    "summary": "Cleans up zero-torrent dashboard states, re-centers empty messaging within the bounded torrent list, and replaces the redundant per-second Last Update card with a useful torrent summary.",
    "highlights": [
        "The torrent empty state is centered inside the available list body again instead of appearing below the flexing table region.",
        "Empty-state copy now distinguishes a genuinely empty client from active/completed/paused views and from search/filter mismatches.",
        "The Last Update metric has been replaced with a Torrents summary showing the total torrent count plus completed and paused counts.",
        "Connection problems remain surfaced through the existing dashboard error banner instead of requiring users to inspect a timestamp."
    ],
    "fixes": [
        "Restores visual centering for the empty torrent state after the docked workspace changes.",
        "Prevents an empty qBitTorrent client from incorrectly saying that no torrents match the current view."
    ],
    "technical": [
        "The empty-state renderer now derives copy from total torrent count, active tab, and search/category/tag/tracker filters.",
        "DESIGN_LANGUAGE.md now defines context-aware empty-state and live-metric rules."
    ],
    "validation": [
        "The UI audit requires the Torrents metric, rejects the former Last Update DOM identifiers, verifies context-aware empty-state copy, and enforces centered list-body positioning.",
        "Existing backend tests, JavaScript syntax validation, generated release metadata, and frontend/service-worker build synchronization remain release gates."
    ],
    "known_issues": [],
    "architecture": previous.get("architecture", []),
    "decisions": previous.get("decisions", []) + [
        "Per-poll timestamps are not primary dashboard metrics; stale/failed refresh conditions should be surfaced explicitly as health states.",
        "Empty-state language must reflect the actual reason a collection is empty."
    ],
    "next_steps": previous.get("next_steps", [])
})
notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)

print(f"Applied v{NEW} dashboard empty-state cleanup")
