#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "aeb20b07f922561022e5dda43b9a5e4730680627"  # prior detail-pane implementation; used only for scoped UI blocks
TARGET_VERSION = "0.5.44"


def git_show(ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True, encoding="utf-8"
    )


def extract(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"Missing start marker: {start}")
    b = text.find(end, a + len(start))
    if b < 0:
        raise RuntimeError(f"Missing end marker: {end}")
    return text[a:b]


def replace_section(text: str, reference: str, start: str, end: str) -> str:
    current = extract(text, start, end)
    replacement = extract(reference, start, end)
    if current == replacement:
        raise RuntimeError(f"Section already matches reference: {start}")
    return text.replace(current, replacement, 1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def bump_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.43"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if "v=0.5.43" not in text:
        raise RuntimeError("Expected v0.5.43 asset references")
    index.write_text(text.replace("v=0.5.43", f"v={TARGET_VERSION}"), encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0543" not in text or "v=0.5.43" not in text:
        raise RuntimeError("Expected v0.5.43 service worker identifiers")
    text = text.replace("torrent-dashboard-v0543", "torrent-dashboard-v0544").replace("v=0.5.43", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_backend():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    old = '            "peers": ("/api/v2/sync/torrentPeers", {"hash": hash_, "rid": 0}),\n        }'
    new = '            "peers": ("/api/v2/sync/torrentPeers", {"hash": hash_, "rid": 0}),\n            "webseeds": ("/api/v2/torrents/webseeds", {"hash": hash_}),\n        }'
    text = replace_once(text, old, new, "qBitTorrent detail webseeds")
    path.write_text(text, encoding="utf-8")


def update_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")

    # Remove the old right-side drawer as one complete top-level block.
    start = text.find('<div class="drawer hidden" id="drawer">')
    modal = text.find('<div class="modal hidden" id="addModal">', start)
    if start < 0 or modal < 0:
        raise RuntimeError("Could not locate legacy torrent detail drawer")
    text = text[:start] + text[modal:]

    pane = '''<section class="torrent-detail-pane hidden" id="torrentDetailPane" aria-label="Torrent details">
<header class="torrent-detail-header"><div><strong id="detailName">Torrent</strong><span id="detailMeta">—</span></div><button class="detail-pane-close" id="detailClose" type="button" aria-label="Close torrent details">×</button></header>
<div class="torrent-detail-tabs" role="tablist" aria-label="Torrent information"><button class="active" data-detailtab="general" type="button">General</button><button data-detailtab="trackers" type="button">Trackers</button><button data-detailtab="peers" type="button">Peers</button><button data-detailtab="webseeds" type="button">HTTP Sources</button><button data-detailtab="content" type="button">Content</button></div>
<div class="torrent-detail-body" id="detailBody"><div class="empty">Select a torrent to view details.</div></div>
</section>'''
    marker = '</section>\n</section>\n<section class="view" id="view-notifications">'
    replacement = '</section>\n' + pane + '\n</section>\n<section class="view" id="view-notifications">'
    text = replace_once(text, marker, replacement, "dashboard detail-pane insertion")
    path.write_text(text, encoding="utf-8")


def update_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    ref = git_show(REFERENCE, "static/app.js")

    text = replace_once(text, "detailTab:'overview'", "detailTab:'general'", "default detail tab")

    # Reuse only the proven detail-specific row and menu behavior from the prior implementation.
    text = replace_section(text, ref, "function rowHtml(t){", "function syncFilterSelect")
    text = replace_section(text, ref, "function rowChange(e){", "function rowContext")
    text = replace_section(text, ref, "function showTorrentMenu(tr,anchor,context=false){", "function showMenu(m,anchor){")
    text = replace_section(text, ref, "async function loadMeta(){", "async function addTorrent(e){")

    # Keep detail refresh out of startup and out of non-dashboard views; it is demand-driven only.
    old_refresh = "renderMetrics(d);checkCompletions();render();$('#errorBanner')"
    new_refresh = "renderMetrics(d);checkCompletions();render();if(state.detail&&$('#view-dashboard').classList.contains('active'))refreshDetailData(false);$('#errorBanner')"
    text = replace_once(text, old_refresh, new_refresh, "detail refresh hook")

    # Changing the selected qBitTorrent client invalidates the currently displayed detail record.
    old_server = "state.server=e.target.value;state.selected.clear();await refreshStatus();"
    new_server = "state.server=e.target.value;state.selected.clear();closeDetailPane();await refreshStatus();"
    text = replace_once(text, old_server, new_server, "server-change detail reset")

    old_bind = "$$('[data-close]').forEach(x=>x.addEventListener('click',closeDrawer));$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));"
    new_bind = "$('#detailClose').addEventListener('click',closeDetailPane);$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));"
    text = replace_once(text, old_bind, new_bind, "detail-pane binding")
    text = replace_once(text, "closeDrawer();$('#addModal').classList.add('hidden')", "closeDetailPane();$('#addModal').classList.add('hidden')", "Escape detail close")

    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    if ".torrent-detail-pane{" in text:
        raise RuntimeError("Torrent detail pane CSS already present")
    addition = r'''

/* 0.5.44 qBitTorrent-style torrent information pane */
.torrent-detail-pane{margin-top:10px;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);min-height:270px;max-height:42vh;display:flex;flex-direction:column;overflow:hidden}
.torrent-detail-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 13px;border-bottom:1px solid var(--border);background:var(--panel3)}.torrent-detail-header>div{min-width:0;display:grid;gap:2px}.torrent-detail-header strong{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.torrent-detail-header span{color:var(--muted);font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.detail-pane-close{width:30px;height:30px;padding:0;border:0;background:transparent;color:var(--muted);font-size:18px}.detail-pane-close:hover{color:var(--text);background:var(--panel2)}
.torrent-detail-tabs{display:flex;gap:2px;padding:6px 9px 0;border-bottom:1px solid var(--border);background:var(--panel)}.torrent-detail-tabs button{border:0;border-bottom:2px solid transparent;border-radius:7px 7px 0 0;background:transparent;color:var(--muted);font-size:10px;padding:8px 10px}.torrent-detail-tabs button.active{color:var(--text);border-bottom-color:var(--accent);background:var(--panel2)}.torrent-detail-body{min-height:0;overflow:auto;padding:12px;flex:1}.torrent-detail-selected{background:color-mix(in srgb,var(--accent) 9%,var(--panel2))!important}.torrent-detail-selected td:first-child{box-shadow:inset 2px 0 0 var(--accent)}
.detail-progress-grid{display:grid;gap:7px;margin-bottom:12px}.detail-progress-row{display:grid;grid-template-columns:72px 1fr 76px;align-items:center;gap:9px;font-size:9px}.detail-progress-row>span:first-child{color:var(--muted)}.detail-progress-bar{height:8px;border:1px solid var(--border);background:var(--panel3);overflow:hidden}.detail-progress-bar>span{display:block;height:100%;background:var(--accent)}.detail-progress-bar.availability>span{background:var(--good)}.detail-general-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.detail-general-section{border:1px solid var(--border);background:var(--panel3);border-radius:10px;padding:10px 12px;min-width:0}.detail-general-section>strong{display:block;font-size:10px;margin-bottom:7px}.detail-stat{display:grid;grid-template-columns:minmax(100px,.8fr) minmax(0,1.2fr);gap:8px;padding:3px 0;font-size:9px}.detail-stat span{color:var(--muted)}.detail-stat b{font-weight:500;overflow-wrap:anywhere}.detail-table-wrap{overflow:auto}.detail-table.compact td,.detail-table.compact th{height:auto;padding:7px 8px;font-size:9px}.detail-table select{padding:5px 7px;font-size:9px}
@media(max-width:900px){.detail-general-grid{grid-template-columns:1fr 1fr}}
@media(max-width:700px){.torrent-detail-pane{position:fixed;z-index:72;left:8px;right:8px;bottom:58px;top:72px;max-height:none;margin:0}.detail-general-grid{grid-template-columns:1fr}.torrent-detail-tabs{overflow:auto}}
'''
    path.write_text(text.rstrip() + addition + "\n", encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    start = text.find("    # Torrent interaction contract:")
    end = text.find("    # Updates owns the public GitHub repository directly.", start)
    if start < 0 or end < 0:
        raise RuntimeError("Could not locate torrent interaction validator block")
    block = '''    # Torrent interaction contract: row selection opens a qBitTorrent-style\n    # information pane while operational commands remain in the context menu.\n    assert 'id="torrentDetailPane"' in html\n    assert 'id="drawer"' not in html\n    assert all(f'data-detailtab="{tab}"' in html for tab in ('general','trackers','peers','webseeds','content'))\n    assert 'HTTP Sources' in html and '>Content</button>' in html\n    assert "Torrent details" not in app_js\n    assert "openDetail(tr.dataset.server,tr.dataset.hash)" in app_js\n    assert "torrent-detail-selected" in app_js and "torrent-detail-selected" in app_css\n    assert "function closeDetailPane" in app_js and "function refreshDetailData" in app_js\n    assert "now-detailRefreshAt<3000" in app_js\n    assert "/api/v2/torrents/webseeds" in dashboard_py\n    assert "renderWebSeeds" in app_js\n    assert "Automatic torrent management" not in app_js\n    assert "set_auto_management" not in app_js and "set_auto_management" not in dashboard_py\n    assert "menu-separator" in app_css and "@media(max-width:700px)" in app_css\n    assert "e.target.closest('button[data-a]')" in app_js\n    # Add Torrent metadata is intentionally not part of 0.5.44.\n    assert "fetch_torrent_metadata" not in dashboard_py\n    assert "/api/torrent-metadata/fetch" not in dashboard_py\n    assert "Metadata retrieval complete" not in app_js\n\n'''
    text = text[:start] + block + text[end:]
    path.write_text(text, encoding="utf-8")


def verify():
    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert 'id="homeBrand"' in html and 'id="brandAddress"' in html  # preserve true v0.5.38 baseline feature
    assert 'id="torrentDetailPane"' in html and 'id="drawer"' not in html
    assert 'data-detailtab="general"' in html and 'data-detailtab="webseeds"' in html and 'data-detailtab="content"' in html
    assert 'Torrent details' not in js
    assert "openDetail(tr.dataset.server,tr.dataset.hash)" in js
    assert 'function closeDetailPane' in js and 'function refreshDetailData' in js
    assert "now-detailRefreshAt<3000" in js
    assert "$('#view-dashboard').classList.contains('active')" in js
    assert '/api/v2/torrents/webseeds' in dashboard
    assert '.torrent-detail-pane{' in css and '.torrent-detail-selected{' in css
    assert 'fetch_torrent_metadata' not in dashboard and '/api/torrent-metadata/fetch' not in dashboard
    assert 'Metadata retrieval complete' not in js


if __name__ == "__main__":
    bump_versions()
    update_backend()
    update_html()
    update_app_js()
    update_css()
    update_validator()
    verify()
    print("Staged v0.5.44 qBitTorrent-style torrent detail pane")
