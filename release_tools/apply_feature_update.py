#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.105"
NEW = "0.5.106"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_required(rel, old, new, count=0):
    text = read(rel)
    if old not in text:
        raise RuntimeError(f"Expected text not found in {rel}: {old[:100]!r}")
    write(rel, text.replace(old, new, count) if count else text.replace(old, new))


# Synchronize backend/frontend build identifiers and the service-worker cache key.
replace_required("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', 1)
replace_required("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", 1)
replace_required("static/index.html", OLD, NEW)
sw = read("static/sw.js")
if f"torrent-dashboard-v{OLD.replace('.', '')}" not in sw:
    raise RuntimeError("Expected old service-worker cache marker")
sw = sw.replace(f"torrent-dashboard-v{OLD.replace('.', '')}", f"torrent-dashboard-v{NEW.replace('.', '')}")
sw = sw.replace(OLD, NEW)
write("static/sw.js", sw)

# Replace only the Trackers/Peers detail renderers. General remains untouched.
app_js = read("static/app.js")
start = app_js.find("function renderPeers(peers){")
end = app_js.find("function renderWebSeeds(a){", start)
if start < 0 or end < 0:
    raise RuntimeError("Could not locate Trackers/Peers renderer block")
old_block = app_js[start:end]
if "function renderTrackers(a)" not in old_block:
    raise RuntimeError("Tracker renderer was not found inside expected block")
new_block = r'''function peerAddress(p){
  const ip=String(p?.ip||'').trim(),port=String(p?.port??'').trim();
  if(!ip)return port?`Port ${port}`:'—';
  const host=ip.includes(':')&&!ip.startsWith('[')?`[${ip}]`:ip;
  return port?`${host}:${port}`:host
}
function trackerDisplayName(value=''){
  const raw=String(value||'').trim();
  const match=raw.match(/^\*\*\s*(.*?)\s*\*\*$/);
  return String(match?.[1]||raw||'—').trim()
}
function trackerStatusInfo(value){
  const raw=String(value??'').trim();
  if(!raw)return['Unknown','neutral'];
  const code=Number(raw);
  if(code===0)return['Disabled','neutral'];
  if(code===1)return['Not contacted','warn'];
  if(code===2)return['Working','good'];
  if(code===3)return['Updating','warn'];
  if(code===4)return['Not working','bad'];
  return[raw,'neutral']
}
function renderPeers(peers){
  const arr=Object.values(peers.peers||{});
  if(!arr.length){$('#detailBody').innerHTML='<div class="empty"><strong>No peers</strong><span>No peers are currently connected.</span></div>';return}
  const desktop=`<div class="detail-desktop-only detail-table-wrap"><table class="detail-table compact"><thead><tr><th>Address</th><th>Client</th><th>Progress</th><th>Down</th><th>Up</th></tr></thead><tbody>${arr.map(p=>`<tr><td>${esc(peerAddress(p))}</td><td>${esc(p.client||'')}</td><td>${(Number(p.progress||0)*100).toFixed(1)}%</td><td>${esc(speed(p.dl_speed||0))}</td><td>${esc(speed(p.up_speed||0))}</td></tr>`).join('')}</tbody></table></div>`;
  const mobile=arr.map(p=>`<article class="detail-record-card detail-peer-card"><div class="detail-record-heading"><div class="detail-record-title"><strong>${esc(peerAddress(p))}</strong><span>${esc(p.client||'Unknown client')}</span></div></div><div class="detail-record-metrics"><div class="detail-record-metric"><span>Progress</span><b>${(Number(p.progress||0)*100).toFixed(1)}%</b></div><div class="detail-record-metric"><span>Download</span><b>${esc(speed(p.dl_speed||0))}</b></div><div class="detail-record-metric"><span>Upload</span><b>${esc(speed(p.up_speed||0))}</b></div></div></article>`).join('');
  $('#detailBody').innerHTML=`${desktop}<div class="detail-mobile-only detail-record-list">${mobile}</div>`
}
function renderTrackers(a){
  const arr=Array.isArray(a)?a:[];
  if(!arr.length){$('#detailBody').innerHTML='<div class="empty"><strong>No trackers</strong><span>This torrent does not report any trackers.</span></div>';return}
  const desktop=`<div class="detail-desktop-only detail-table-wrap"><table class="detail-table compact"><thead><tr><th>Tracker</th><th>Status</th><th>Seeds</th><th>Peers</th><th>Message</th></tr></thead><tbody>${arr.map(x=>{const status=trackerStatusInfo(x.status)[0];return`<tr><td>${esc(trackerDisplayName(x.url))}</td><td>${esc(status)}</td><td>${esc(x.num_seeds)}</td><td>${esc(x.num_leeches)}</td><td>${esc(x.msg||'')}</td></tr>`}).join('')}</tbody></table></div>`;
  const mobile=arr.map(x=>{const[status,tone]=trackerStatusInfo(x.status),message=String(x.msg||'').trim();return`<article class="detail-record-card detail-tracker-card"><div class="detail-record-heading"><div class="detail-record-title"><strong>${esc(trackerDisplayName(x.url))}</strong></div><span class="detail-status-badge ${tone}">${esc(status)}</span></div><div class="detail-record-metrics"><div class="detail-record-metric"><span>Seeds</span><b>${esc(x.num_seeds??'—')}</b></div><div class="detail-record-metric"><span>Peers</span><b>${esc(x.num_leeches??'—')}</b></div></div>${message?`<div class="detail-record-message"><span>Message</span><b>${esc(message)}</b></div>`:''}</article>`}).join('');
  $('#detailBody').innerHTML=`${desktop}<div class="detail-mobile-only detail-record-list">${mobile}</div>`
}
'''
app_js = app_js[:start] + new_block + app_js[end:]
write("static/app.js", app_js)

# Dedicated responsive detail cards avoid the global mobile table-to-card fallback.
css = read("static/app.css")
marker = "/* 0.5.106 responsive tracker and peer details. */"
if marker in css:
    raise RuntimeError("v0.5.106 detail CSS already present")
css += r'''

/* 0.5.106 responsive tracker and peer details. */
.detail-mobile-only{display:none}
.detail-record-list{gap:8px}
.detail-record-card{min-width:0;border:1px solid var(--border);background:var(--panel3);border-radius:12px;padding:11px 12px}
.detail-record-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;min-width:0}
.detail-record-title{min-width:0;flex:1 1 auto}
.detail-record-title strong{display:block;font-size:12px;line-height:1.35;overflow-wrap:anywhere}
.detail-record-title span{display:block;margin-top:3px;color:var(--muted);font-size:10px;line-height:1.35;overflow-wrap:anywhere}
.detail-record-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}
.detail-tracker-card .detail-record-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}
.detail-record-metric{min-width:0}
.detail-record-metric span,.detail-record-message span{display:block;color:var(--muted);font-size:8.5px;text-transform:uppercase;letter-spacing:.06em}
.detail-record-metric b{display:block;margin-top:3px;font-size:11px;font-weight:550;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.detail-status-badge{flex:0 0 auto;display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:999px;padding:4px 7px;font-size:9.5px;line-height:1.2;color:var(--muted);background:var(--panel2);white-space:nowrap}
.detail-status-badge.good{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,var(--border));background:color-mix(in srgb,var(--good) 8%,var(--panel2))}
.detail-status-badge.warn{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 40%,var(--border));background:color-mix(in srgb,var(--warn) 8%,var(--panel2))}
.detail-status-badge.bad{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 40%,var(--border));background:color-mix(in srgb,var(--bad) 8%,var(--panel2))}
.detail-record-message{margin-top:9px;padding-top:8px;border-top:1px solid color-mix(in srgb,var(--border) 65%,transparent);min-width:0}
.detail-record-message b{display:block;margin-top:3px;font-size:10px;font-weight:500;line-height:1.4;overflow-wrap:anywhere}
@media(max-width:820px){
  .torrent-detail-body .detail-desktop-only{display:none!important}
  .torrent-detail-body .detail-mobile-only{display:grid}
}
'''
write("static/app.css", css)

# Durable interface and manual-test contracts.
design = read("DESIGN_LANGUAGE.md")
design_note = '''

### Responsive torrent detail records

Trackers and Peers use purpose-built responsive detail records rather than inheriting the generic mobile table-to-card fallback. Desktop/tablet retains the normal labeled tables. At the mobile breakpoint, Peers presents the peer address as the record heading, client as secondary context, and labeled Progress, Download, and Upload metrics. Trackers presents a cleaned tracker name or URL, a human-readable status badge, labeled Seeds and Peers counts, and the tracker message only when one exists. qBitTorrent tracker status codes must not be exposed as unexplained numbers, and pseudo-trackers such as DHT, PeX, and LSD must not display literal Markdown-style asterisks. The General tab remains an independent presentation and is not altered by this responsive record treatment.
'''
if "### Responsive torrent detail records" not in design:
    design = design.rstrip() + design_note + "\n"
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
testing_note = '''

### Responsive tracker and peer details

- At 820 px and below, open Peers and verify each connected peer is a compact labeled record: address heading, client beneath it, then Progress, Download, and Upload metrics. No anonymous vertical value stacks should remain.
- Open Trackers and verify each record shows a cleaned tracker name/URL, a human-readable status badge, labeled Seeds and Peers counts, and a Message section only when the tracker reports one.
- Verify qBitTorrent tracker statuses 0 through 4 render as Disabled, Not contacted, Working, Updating, and Not working rather than raw numeric codes.
- Verify pseudo-trackers such as DHT, PeX, and LSD do not display literal surrounding `**` markers.
- Test a long IPv6 peer address, long client name, long tracker URL, and long tracker message; records must wrap or ellipsize without horizontal overflow.
- Above 820 px, verify Peers and Trackers remain conventional tables with visible column headers.
- Recheck General before and after switching through Trackers and Peers; its layout and content must remain unchanged.
'''
if "### Responsive tracker and peer details" not in testing:
    testing = testing.rstrip() + testing_note + "\n"
write("TESTING.md", testing)

# Strengthen the UI audit around the responsive detail contract.
validator = read("release_tools/validate_ui_strings.py")
anchor = '    print("UI string audit passed")'
checks = '''    # 0.5.106 gives Trackers and Peers dedicated responsive detail records.\n    assert 'function peerAddress(p)' in app_js\n    assert "function trackerDisplayName(value='')" in app_js\n    assert 'function trackerStatusInfo(value)' in app_js\n    for label in ('Disabled','Not contacted','Working','Updating','Not working'):\n        assert f"'{label}'" in app_js\n    assert 'detail-mobile-only detail-record-list' in app_js\n    assert 'detail-peer-card' in app_js and 'detail-tracker-card' in app_js\n    assert 'No peers are currently connected.' in app_js\n    assert 'This torrent does not report any trackers.' in app_js\n    assert '0.5.106 responsive tracker and peer details' in app_css\n    assert '.torrent-detail-body .detail-desktop-only{display:none!important}' in app_css\n    assert '.torrent-detail-body .detail-mobile-only{display:grid}' in app_css\n    assert '### Responsive torrent detail records' in design\n    assert '### Responsive tracker and peer details' in testing\n\n'''
if "0.5.106 gives Trackers and Peers" not in validator:
    if anchor not in validator:
        raise RuntimeError("UI validator print anchor not found")
    validator = validator.replace(anchor, checks + anchor, 1)
write("release_tools/validate_ui_strings.py", validator)

# Append structured release metadata while preserving recorded engineering context.
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
    "title": "Responsive tracker and peer details",
    "summary": "Makes Torrent details → Trackers and Peers readable on mobile with purpose-built labeled records while preserving desktop tables and the existing General tab.",
    "highlights": [
        "Peers on mobile now shows each address and client with labeled Progress, Download, and Upload metrics instead of an anonymous vertical value stack.",
        "Trackers on mobile now shows cleaned tracker names, human-readable status badges, Seeds and Peers counts, and an optional tracker message.",
        "Desktop/tablet keeps conventional Tracker and Peer tables, while the General detail tab remains unchanged."
    ],
    "fixes": [
        "Fixes the global mobile table fallback hiding Tracker/Peer headers and turning their cells into tall unlabeled cards.",
        "Stops exposing raw numeric qBitTorrent tracker status codes and literal Markdown-style asterisks around DHT, PeX, and LSD pseudo-trackers."
    ],
    "technical": [
        "Trackers and Peers now render both a desktop table and a semantic mobile record list; responsive CSS selects the appropriate presentation at the 820 px breakpoint.",
        "Small frontend helpers normalize peer addresses, pseudo-tracker labels, and qBitTorrent tracker status codes without changing backend APIs or polling."
    ],
    "validation": [
        "The UI audit asserts the status mapping, responsive record classes, mobile/desktop visibility contract, empty states, and matching design/testing documentation.",
        "Manual coverage checks mobile Trackers/Peers readability, long values and IPv6 wrapping, desktop table preservation, and an unchanged General tab.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": []
})
releases.append(entry)
release_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} responsive tracker and peer details")
