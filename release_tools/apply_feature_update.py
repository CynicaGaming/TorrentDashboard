#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.84"
NEW = "0.5.85"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected source fragment not found in {path}: {old[:140]!r}")
    write(path, text.replace(old, new, count))


# Keep the updater/frontend build contract synchronized.
replace("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
write("static/index.html", read("static/index.html").replace(OLD, NEW))
replace("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
write("static/sw.js", read("static/sw.js").replace("torrent-dashboard-v0584", "torrent-dashboard-v0585").replace(OLD, NEW))

# Category joins Seeds, Peers, and Tags in the default visible torrent layout.
replace(
    "static/app.js",
    "{key:'category',label:'Category',defaultVisible:false}",
    "{key:'category',label:'Category',defaultVisible:true}",
)

# If a browser merely saved the exact v0.5.84 defaults, migrate that saved
# snapshot to the new default. Any genuinely customized layout is preserved.
old_pref_fn = "function torrentColumnPreferences(){let raw={};try{raw=JSON.parse(localStorage.tdColumns||'{}')||{}}catch{raw={}}const known=new Set(DEFAULT_TORRENT_COLUMN_ORDER),legacy=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{},source=raw?.visible&&typeof raw.visible==='object'?raw.visible:legacy,supplied=Array.isArray(raw?.order)?raw.order.map(String).filter(key=>known.has(key)&&key!=='name'):[],order=['name',...supplied,...DEFAULT_TORRENT_COLUMN_ORDER.filter(key=>key!=='name'&&!supplied.includes(key))],visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible);return{order,visible}}"
new_pref_fn = "function torrentColumnPreferences(){let raw={};try{raw=JSON.parse(localStorage.tdColumns||'{}')||{}}catch{raw={}}const known=new Set(DEFAULT_TORRENT_COLUMN_ORDER),legacy=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{},source=raw?.visible&&typeof raw.visible==='object'?raw.visible:legacy,supplied=Array.isArray(raw?.order)?raw.order.map(String).filter(key=>known.has(key)&&key!=='name'):[],order=['name',...supplied,...DEFAULT_TORRENT_COLUMN_ORDER.filter(key=>key!=='name'&&!supplied.includes(key))],previousDefault={name:true,size:false,progress:true,state:true,seeds:true,peers:true,down:true,up:true,eta:true,ratio:true,category:false,tags:true,tracker:false,added:false},savedPreviousDefault=!!raw?.visible&&Array.isArray(raw.order)&&raw.order.length===DEFAULT_TORRENT_COLUMN_ORDER.length&&raw.order.every((key,index)=>key===DEFAULT_TORRENT_COLUMN_ORDER[index])&&DEFAULT_TORRENT_COLUMN_ORDER.every(key=>raw.visible[key]===previousDefault[key]),visible={};for(const column of TORRENT_COLUMN_DEFS)visible[column.key]=column.required?true:(savedPreviousDefault&&column.key==='category'?true:(Object.prototype.hasOwnProperty.call(source,column.key)?source[column.key]!==false:!!column.defaultVisible));return{order,visible}}"
replace("static/app.js", old_pref_fn, new_pref_fn)

# Update the durable design/test contracts and the source-level UI audit.
replace(
    "DESIGN_LANGUAGE.md",
    "- Seeds, Peers, and Tags are part of the default visible layout. Size, Category, Tracker, and Added remain available but hidden by default to avoid unnecessary width.",
    "- Seeds, Peers, Category, and Tags are part of the default visible layout. Size, Tracker, and Added remain available but hidden by default to avoid unnecessary width.",
)
replace(
    "TESTING.md",
    "- On a browser with no saved column preference, verify Seeds, Peers, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.",
    "- On a browser with no saved column preference, verify Seeds, Peers, Category, and Tags are visible by default alongside Name, Progress, Status, Download, Upload, ETA, and Ratio.",
)
replace(
    "TESTING.md",
    "- Enable Size, Category, Tracker, and Added individually and verify their values render without changing qBitTorrent state.",
    "- Verify Category is visible in the default layout; enable Size, Tracker, and Added individually and verify their values render without changing qBitTorrent state.",
)
replace(
    "release_tools/validate_ui_strings.py",
    "    assert \"{key:'tags',label:'Tags',defaultVisible:true}\" in app_js\n    assert \"{key:'size',label:'Size',defaultVisible:false}\" in app_js\n",
    "    assert \"{key:'tags',label:'Tags',defaultVisible:true}\" in app_js\n    assert \"{key:'category',label:'Category',defaultVisible:true}\" in app_js\n    assert \"{key:'size',label:'Size',defaultVisible:false}\" in app_js\n",
)
replace(
    "release_tools/validate_ui_strings.py",
    "    assert 'function torrentColumnPreferences()' in app_js and 'function renderTorrentColumnPreferences' in app_js\n",
    "    assert 'function torrentColumnPreferences()' in app_js and 'function renderTorrentColumnPreferences' in app_js\n    assert \"savedPreviousDefault&&column.key==='category'?true\" in app_js\n",
)

# Add structured release metadata while preserving the current architecture and roadmap.
notes_path = ROOT / "release_notes" / "releases.json"
data = json.loads(notes_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW for item in data.get("releases", [])):
    raise RuntimeError(f"Release metadata already contains v{NEW}")
previous = next((item for item in data.get("releases", []) if str(item.get("version")) == OLD), None)
if not previous:
    raise RuntimeError(f"Could not find v{OLD} release metadata")
entry = {
    "version": NEW,
    "date": "2026-09-03",
    "status": "prerelease",
    "title": "Category in the default torrent layout",
    "summary": "Adds Category to the default visible torrent columns while preserving genuinely customized browser layouts and migrating browsers that only saved the previous default snapshot.",
    "highlights": [
        "Category is now visible by default alongside Seeds, Peers, and Tags.",
        "Reset columns restores a default layout that includes Category.",
        "Browsers with no saved column preferences immediately receive the new default."
    ],
    "fixes": [
        "A browser that saved the exact v0.5.84 default column snapshot is migrated to the new Category-visible default instead of remaining on the superseded default.",
        "Custom column orders or visibility choices are left unchanged."
    ],
    "technical": [
        "The column catalog changes Category defaultVisible from false to true.",
        "Preference normalization detects only the exact prior default order/visibility snapshot before applying the one-time Category default migration."
    ],
    "validation": [
        "The UI audit requires Category to be default-visible and verifies the prior-default migration path.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture", [])),
    "decisions": list(previous.get("decisions", [])) + [
        "Treat Category as core torrent-list context and include it in the default visible column set."
    ],
    "next_steps": list(previous.get("next_steps", [])),
}
data["releases"].append(entry)
notes_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} Category default-column update")
