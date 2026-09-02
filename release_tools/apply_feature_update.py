#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.48"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RuntimeError(f"Could not find {label} start marker")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise RuntimeError(f"Could not find {label} end marker")
    return text[:start_at] + replacement + text[end_at:]


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.47"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.47") < 4:
        raise RuntimeError("Expected v0.5.47 frontend version references")
    text = text.replace("0.5.47", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.47';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build version")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0547", "torrent-dashboard-v0548", "service-worker cache version")
    if "v=0.5.47" not in text:
        raise RuntimeError("Expected v0.5.47 service-worker assets")
    text = text.replace("v=0.5.47", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_add_torrent_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    start = '<div class="modal hidden" id="addModal">'
    end = '<div class="modal hidden" id="actionDialogModal">'
    replacement = '''<div class="modal hidden" id="addModal"><div class="modal-backdrop" data-modalclose=""></div><form class="modal-card add-torrent-card" id="addForm"><header class="add-torrent-header"><div><h2>Add torrent</h2><p>Configure the torrent before adding it to qBitTorrent.</p></div><button class="icon-btn" data-modalclose="" type="button" aria-label="Close Add Torrent">×</button></header><div class="add-torrent-body"><section class="add-torrent-options" aria-label="Torrent options"><div class="add-torrent-section"><div class="add-torrent-section-title"><strong>Source</strong><span>Add a magnet link, torrent URL, or local .torrent file.</span></div><label>Magnet or torrent URL<textarea id="addUrls" placeholder="magnet:?xt=…" rows="4"></textarea></label><div class="add-source-or">Or</div><label class="file-drop add-file-drop">Choose torrent file<input accept=".torrent,application/x-bittorrent" id="torrentFile" type="file"/></label></div><div class="add-torrent-section"><div class="add-torrent-section-title"><strong>Save location</strong><span>Choose where qBitTorrent should place the download.</span></div><label>Save path<input id="addPath" placeholder="Optional"/></label></div><div class="add-torrent-section"><div class="add-torrent-section-title"><strong>Organization</strong><span>Apply an existing category or comma-separated tags.</span></div><div class="two"><label>Category<input id="addCategory"/></label><label>Tags<input id="addTags"/></label></div></div><div class="add-torrent-section"><div class="add-torrent-section-title"><strong>Options</strong><span>These use the same add behavior as the previous dialog.</span></div><div class="checks add-torrent-checks"><label><input id="addStopped" type="checkbox"/> Add paused</label><label><input id="addSequential" type="checkbox"/> Sequential download</label><label><input id="addFirstLast" type="checkbox"/> First/last priority</label></div></div></section><section class="add-torrent-preview" aria-label="Torrent preview"><div class="add-preview-panel add-content-panel"><div class="add-preview-heading"><div><strong>Content</strong><span>File selection will be enabled in a later phase.</span></div></div><div class="add-content-columns" aria-hidden="true"><span>Name</span><span>Size</span><span>Priority</span></div><div class="add-preview-empty"><strong>Content preview not enabled yet</strong><span>This release changes only the Add Torrent layout. Torrent metadata is not requested.</span></div></div><div class="add-preview-panel add-info-panel"><div class="add-preview-heading"><div><strong>Torrent information</strong><span>Metadata fields will populate after the metadata phase is enabled.</span></div></div><div class="add-info-grid"><span>Total size</span><b>—</b><span>Creation date</span><b>—</b><span>Info hash v1</span><b>—</b><span>Info hash v2</span><b>—</b><span>Created by</span><b>—</b></div></div></section></div><footer class="add-torrent-footer"><div class="add-torrent-status"><strong>Standard add mode</strong><span>No metadata requests are made in this release.</span></div><div class="add-torrent-actions"><button class="secondary" data-modalclose="" type="button">Cancel</button><button class="primary" type="submit">Add torrent</button></div></footer></form></div>
'''
    text = replace_section(text, start, end, replacement, "Add Torrent modal")
    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    if "0.5.48 Add Torrent visual shell" in text:
        raise RuntimeError("v0.5.48 Add Torrent styling already present")
    css = r'''

/* 0.5.48 Add Torrent visual shell */
.add-torrent-card{width:min(1080px,calc(100% - 32px));height:min(760px,90vh);max-height:90vh;overflow:hidden;padding-bottom:0;display:flex;flex-direction:column}.add-torrent-card .add-torrent-header{flex:0 0 auto;align-items:center}.add-torrent-header p{margin:5px 0 0;color:var(--muted);font-size:10px}.add-torrent-body{min-height:0;flex:1;display:grid;grid-template-columns:minmax(300px,360px) minmax(0,1fr);overflow:hidden}.add-torrent-options{min-width:0;overflow:auto;padding:14px 16px 18px;border-right:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 34%,var(--panel))}.add-torrent-section{padding:0 0 15px;margin-bottom:15px;border-bottom:1px solid color-mix(in srgb,var(--border) 72%,transparent)}.add-torrent-section:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}.add-torrent-section-title{display:grid;gap:3px;margin-bottom:9px}.add-torrent-section-title strong{font-size:10px}.add-torrent-section-title span{color:var(--muted);font-size:9px;line-height:1.45}.add-torrent-options label{display:grid;gap:5px;color:var(--muted);font-size:10px;margin-top:9px}.add-torrent-options input,.add-torrent-options textarea{width:100%}.add-source-or{text-align:center;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.08em;margin:9px 0 2px}.add-file-drop{margin-top:7px!important;background:var(--panel3)}.add-torrent-checks{display:grid;grid-template-columns:1fr;gap:8px;margin:0}.add-torrent-checks label{display:flex;align-items:center;gap:7px;margin:0;color:var(--text)}.add-torrent-checks input{width:auto}.add-torrent-preview{min-width:0;overflow:auto;padding:14px;display:grid;grid-template-rows:minmax(280px,1fr) auto;gap:12px}.add-preview-panel{min-width:0;border:1px solid var(--border);border-radius:12px;background:var(--panel3);overflow:hidden}.add-preview-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 12px;border-bottom:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 70%,var(--panel3))}.add-preview-heading div{display:grid;gap:2px}.add-preview-heading strong{font-size:10px}.add-preview-heading span{font-size:8px;color:var(--muted)}.add-content-panel{display:flex;flex-direction:column}.add-content-columns{display:grid;grid-template-columns:minmax(0,1fr) 90px 90px;gap:10px;padding:8px 12px;border-bottom:1px solid color-mix(in srgb,var(--border) 70%,transparent);font-size:8px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.add-content-columns span:nth-child(n+2){text-align:right}.add-preview-empty{flex:1;min-height:210px;display:grid;place-content:center;text-align:center;padding:28px;color:var(--muted)}.add-preview-empty strong{font-size:11px;color:var(--text)}.add-preview-empty span{font-size:9px;max-width:360px;line-height:1.5;margin-top:5px}.add-info-grid{display:grid;grid-template-columns:120px minmax(0,1fr);gap:0;padding:4px 12px 10px}.add-info-grid span,.add-info-grid b{padding:6px 0;border-bottom:1px solid color-mix(in srgb,var(--border) 55%,transparent);font-size:9px}.add-info-grid span{color:var(--muted)}.add-info-grid b{font-weight:600;word-break:break-word}.add-info-grid span:nth-last-child(-n+2),.add-info-grid b:nth-last-child(-n+2){border-bottom:0}.add-torrent-footer{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:11px 14px;border-top:1px solid var(--border);background:var(--panel2)}.add-torrent-status{display:grid;gap:2px;min-width:0}.add-torrent-status strong{font-size:9px}.add-torrent-status span{color:var(--muted);font-size:8px}.add-torrent-actions{display:flex;gap:7px;flex:0 0 auto}.add-torrent-actions button{min-width:92px;font-size:10px}
@media(max-width:820px){.add-torrent-card{width:min(720px,calc(100% - 20px));height:min(92vh,820px)}.add-torrent-body{grid-template-columns:1fr;overflow:auto}.add-torrent-options{overflow:visible;border-right:0;border-bottom:1px solid var(--border)}.add-torrent-preview{overflow:visible;grid-template-rows:auto auto}.add-preview-empty{min-height:170px}.add-torrent-footer{position:sticky;bottom:0}.add-torrent-status{display:none}}
@media(max-width:520px){.add-torrent-card{width:calc(100% - 12px);height:96vh;max-height:96vh;border-radius:14px}.add-torrent-body{display:block}.add-torrent-options,.add-torrent-preview{padding:11px}.add-torrent-section .two{grid-template-columns:1fr}.add-content-columns{grid-template-columns:minmax(0,1fr) 62px 62px}.add-info-grid{grid-template-columns:96px minmax(0,1fr)}.add-torrent-footer{padding:9px 10px}.add-torrent-actions{width:100%}.add-torrent-actions button{flex:1}}
'''
    path.write_text(text.rstrip() + css + "\n", encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    marker = '    assert "Metadata retrieval complete" not in app_js\n'
    addition = marker + '''    # 0.5.48 changes only the Add Torrent shell. The existing submission\n    # contract remains in place and metadata behavior is still absent.\n    assert 'class="modal-card add-torrent-card"' in html\n    assert 'class="add-torrent-body"' in html\n    assert 'class="add-torrent-options"' in html\n    assert 'class="add-torrent-preview"' in html\n    assert 'Content preview not enabled yet' in html\n    assert 'No metadata requests are made in this release.' in html\n    assert 'id="addUrls"' in html and 'id="torrentFile"' in html and 'id="addPath"' in html\n    assert 'id="addCategory"' in html and 'id="addTags"' in html\n    assert 'id="addStopped"' in html and 'id="addSequential"' in html and 'id="addFirstLast"' in html\n    assert '0.5.48 Add Torrent visual shell' in app_css\n    assert 'fetch_torrent_metadata' not in dashboard_py\n    assert '/api/torrent-metadata/fetch' not in dashboard_py\n    assert 'addMetadataState' not in app_js\n    assert 'Metadata retrieval complete' not in app_js\n'''
    text = replace_once(text, marker, addition, "v0.5.48 validator marker")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_add_torrent_html()
    update_css()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert 'class="modal-card add-torrent-card"' in html
    assert 'fetch_torrent_metadata' not in dashboard
    assert 'event.request.mode===\'navigate\'' in sw
    print("Applied v0.5.48 Add Torrent visual shell")


if __name__ == "__main__":
    main()
