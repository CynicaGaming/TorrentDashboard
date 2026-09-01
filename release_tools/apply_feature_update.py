#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one regex match, found {count}")
    return updated


# Version bump.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.7"', 'VERSION = "0.5.8"', "dashboard version")
write("dashboard.py", dashboard)

# Remove Saved Views from the dashboard controls and bump static asset revisions.
html = read("static/index.html")
html = html.replace("?v=0.5.7", "?v=0.5.8")
html = replace_once(
    html,
    '<select id="savedView"><option value="">Saved Views</option></select><button id="saveView" title="Save current filters">☆</button>\n',
    '',
    "saved views markup",
)
write("static/index.html", html)

# Remove Saved Views behavior and make frequently refreshed filters stable.
app = read("static/app.js")
app = replace_once(
    app,
    "loadSavedViews();$('#saveView').addEventListener('click',saveCurrentView);$('#savedView').addEventListener('change',applySavedView);$('#sort').value=state.sort;",
    "$('#sort').value=state.sort;",
    "saved views bindings",
)
app = regex_once(
    app,
    r"\nfunction loadSavedViews\(\).*?\nasync function globalLimit",
    "\nasync function globalLimit",
    "saved views functions",
    re.S,
)
new_filters = '''function syncFilterSelect(select,values,selected,emptyLabel){
  if(!select)return;
  const signature=JSON.stringify([emptyLabel,...values]);
  // Native select menus can jump back to the first item if their option DOM is
  // modified while the menu is open. Leave a focused select completely alone;
  // the next dashboard refresh will reconcile it after the user closes it.
  if(document.activeElement===select)return;
  if(select.dataset.optionsSignature!==signature){
    select.innerHTML=`<option value="">${esc(emptyLabel)}</option>`+values.map(x=>`<option>${esc(x)}</option>`).join('');
    select.dataset.optionsSignature=signature;
  }
  if(select.value!==selected)select.value=selected;
}
function updateFilters(){
  const cats=[...new Set(state.torrents.map(t=>t.category).filter(Boolean))].sort();
  const tags=[...new Set(state.torrents.flatMap(t=>String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean)))].sort();
  const trackers=[...new Set(state.torrents.map(t=>trackerHost(t.tracker)).filter(Boolean))].sort();
  syncFilterSelect($('#categoryFilter'),cats,state.category,'All categories');
  syncFilterSelect($('#tagFilter'),tags,state.tag,'All tags');
  syncFilterSelect($('#trackerFilter'),trackers,state.tracker,'All trackers');
}
function rowChange'''
app = regex_once(
    app,
    r"function updateFilters\(\)\{.*?\}\nfunction rowChange",
    new_filters,
    "filter select updater",
    re.S,
)
write("static/app.js", app)

# Force a new PWA cache for the corrected frontend.
sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v057", "torrent-dashboard-v058", "service worker cache")
sw = sw.replace("0.5.7", "0.5.8")
write("static/sw.js", sw)

# Extend the release-time UI audit so these regressions cannot return silently.
audit = read("release_tools/validate_ui_strings.py")
audit = replace_once(
    audit,
    "    assert 'title=\"Save current filters\"' in html\n",
    "    assert 'id=\"savedView\"' not in html\n    assert 'id=\"saveView\"' not in html\n    assert 'tdSavedViews' not in app_js\n    assert 'function syncFilterSelect' in app_js\n    assert 'document.activeElement===select' in app_js\n    assert 'optionsSignature' in app_js\n",
    "UI audit saved-view assertions",
)
write("release_tools/validate_ui_strings.py", audit)

print("Applied Torrent Dashboard 0.5.8 saved-view cleanup and stable-select update")
