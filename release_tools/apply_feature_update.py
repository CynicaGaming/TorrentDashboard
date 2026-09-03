#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.75"
NEW = "0.5.76"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


app_js = read("static/app.js")
app_js = replace_once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = replace_once(
    app_js,
    "server:'all',torrents:[]",
    "server:localStorage.tdServer||'all',torrents:[]",
    "initial server preference",
)
app_js = replace_once(
    app_js,
    "await loadServers();bindUI();applyPrefs();await refreshStatus();scheduleRefresh();registerPwa();",
    "await loadServers();bindUI();applyPrefs();if(state.server!=='all')await loadMeta();await refreshStatus();scheduleRefresh();registerPwa();",
    "bootstrap server metadata",
)
app_js = replace_once(
    app_js,
    "$('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;state.selected.clear();resetDetailPane();await refreshStatus();if(!['all'].includes(state.server))await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});",
    "$('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;localStorage.tdServer=state.server;state.selected.clear();resetDetailPane();await refreshStatus();if(state.server!=='all')await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});",
    "server selection persistence",
)
old_loader = "async function loadServers(){const d=await api('/api/servers');const sel=$('#serverSelect');sel.innerHTML='<option value=\"all\">allServers</option>'+d.servers.filter(s=>s.enabled).map(s=>`<option value=\"${esc(s.id)}\">${esc(s.name)}</option>`).join('');sel.value=state.server}"
new_loader = """function preferredServer(enabled=[]){
  if(enabled.length===1)return String(enabled[0].id);
  const saved=String(localStorage.tdServer||state.server||'all');
  return saved==='all'||enabled.some(server=>String(server.id)===saved)?saved:'all'
}
async function loadServers(){
  const d=await api('/api/servers'),enabled=(d.servers||[]).filter(server=>server.enabled),sel=$('#serverSelect');
  const includeAll=enabled.length!==1;
  sel.innerHTML=(includeAll?'<option value=\"all\">allServers</option>':'')+enabled.map(server=>`<option value=\"${esc(server.id)}\">${esc(server.name)}</option>`).join('');
  state.server=preferredServer(enabled);sel.value=state.server;localStorage.tdServer=state.server
}"""
app_js = replace_once(app_js, old_loader, new_loader, "server loader")
if "server:'all',torrents:[]" in app_js or "async function loadServers(){const d=await api('/api/servers')" in app_js:
    raise SystemExit("legacy server-selection defaults remain")
write("static/app.js", app_js)


# Keep the manual test contract synchronized with the restored Dashboard heading
# and add explicit server-selection scenarios.
testing = read("TESTING.md")
testing = testing.replace(
    "- Verify Dashboard / Live torrent activity is not visible on Dashboard while top-right controls remain available.\n",
    "- Verify Dashboard / Live torrent activity is visible on Dashboard while top-right controls remain available.\n",
)
testing += """\n\n### Server-selection defaults\n\n- With exactly one enabled qBitTorrent client, verify that client is selected automatically and All servers is not offered in the server selector.\n- With one enabled client, verify Add Torrent and other client-specific actions are immediately available without first changing the server selector.\n- With two or more enabled clients, verify All servers is available as an aggregation choice.\n- With multiple clients, select a specific client, reload the dashboard, and verify the valid previous selection is restored.\n- Disable or remove the remembered client and verify the dashboard falls back to All servers when multiple clients remain, or automatically selects the sole remaining enabled client.\n"""
write("TESTING.md", testing)


design = read("DESIGN_LANGUAGE.md")
design += """\n\n## Server-selection defaults\n\nAll servers is an aggregation mode, not a pseudo-client. It should be offered only when aggregation has meaning.\n\n- With exactly one enabled download client, select that client automatically and omit All servers from the selector so client-specific commands are immediately available.\n- With multiple enabled clients, expose All servers and restore the user's last valid server selection when possible.\n- If a remembered client is disabled or removed, recover predictably: use All servers when multiple enabled clients remain, or the sole enabled client when only one remains.\n- Server selection is a local interface preference; changing it does not modify dashboard configuration.\n"""
write("DESIGN_LANGUAGE.md", design)


validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert '### Update-check intent and empty detail disclosure' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"
extra = """\n    # 0.5.76 treats All servers as aggregation rather than the default pseudo-client.\n    assert \"server:localStorage.tdServer||'all'\" in app_js\n    assert 'function preferredServer(enabled=[])' in app_js\n    assert 'if(enabled.length===1)return String(enabled[0].id)' in app_js\n    assert \"const includeAll=enabled.length!==1\" in app_js\n    assert \"localStorage.tdServer=state.server\" in app_js\n    assert \"if(state.server!=='all')await loadMeta()\" in app_js\n    assert '## Server-selection defaults' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n    assert '### Server-selection defaults' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"""
if validator.count(anchor) != 1:
    raise SystemExit(f"validator anchor: expected one match, found {validator.count(anchor)}")
validator = validator.replace(anchor, anchor + extra, 1)
write("release_tools/validate_ui_strings.py", validator)


dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = html.replace(OLD, NEW)
write("static/index.html", html)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0575", "torrent-dashboard-v0576", "service-worker cache")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)


meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(r.get("version") == NEW for r in releases):
    raise SystemExit(f"release {NEW} already exists")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Single-client server defaults",
    "summary": "Makes single-client installations select their actual qBitTorrent server automatically while preserving All servers as a meaningful multi-client aggregation mode.",
    "highlights": [
        "When exactly one enabled qBitTorrent client exists, Torrent Dashboard selects it automatically and omits All servers from the selector.",
        "Client-specific operations such as Add Torrent are immediately available on single-client installations without an unnecessary selector change.",
        "With multiple enabled clients, All servers remains available and the last valid server selection is restored across reloads.",
        "If a remembered client is removed or disabled, selection falls back safely to All servers or the sole remaining enabled client as appropriate."
    ],
    "fixes": [
        "Prevents single-client dashboards from starting in All servers mode and unnecessarily disabling client-specific commands.",
        "Loads client metadata during startup when a specific server is restored or auto-selected."
    ],
    "technical": [
        "The selected server is retained as a local interface preference in tdServer and validated against the current enabled-server list on startup.",
        "All servers is only inserted into the selector when the number of enabled clients is not exactly one.",
        "TESTING.md and DESIGN_LANGUAGE.md now define the single-client and multi-client selection contract.",
        "Removed a stale manual-test statement about hiding the Dashboard heading and dropped a superseded no-collapse decision from the carried-forward handoff state."
    ],
    "validation": [
        "UI/source validation requires the one-client auto-selection branch, conditional All servers option, remembered selection, startup metadata load, and documented server-selection contract.",
        "Existing backend tests, JavaScript syntax checks, generated handoff/release-note checks, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
}
entry["architecture"] = copy.deepcopy(previous.get("architecture", []))
entry["next_steps"] = copy.deepcopy(previous.get("next_steps", []))
entry["decisions"] = [
    decision for decision in copy.deepcopy(previous.get("decisions", []))
    if decision != "Do not expose Collapse when the detail inspector is already bounded, scrollable, and dismissible with Close."
]
entry["decisions"].append("Treat All servers as an aggregation mode: omit it when only one enabled client exists, and prefer the actual client so client-specific actions remain available.")
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
print(f"Applied Torrent Dashboard v{NEW} single-client server defaults")
