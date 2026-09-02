#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.49"


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
    text = replace_once(text, 'VERSION = "0.5.48"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.48") < 4:
        raise RuntimeError("Expected v0.5.48 frontend references")
    text = text.replace("0.5.48", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.48';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0548", "torrent-dashboard-v0549", "service worker cache")
    if "v=0.5.48" not in text:
        raise RuntimeError("Expected v0.5.48 service worker assets")
    text = text.replace("v=0.5.48", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_toolbar_and_modal():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")

    old_toolbar = """<button class=\"toolbar-icon\" id=\"addLinkBtn\" type=\"button\" aria-label=\"Add torrent link\" title=\"Add torrent link\"><svg aria-hidden=\"true\" viewBox=\"0 0 24 24\"><path d=\"M10.6 13.4a4.5 4.5 0 0 0 6.4.1l2.1-2.1a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2\"/><path d=\"M13.4 10.6a4.5 4.5 0 0 0-6.4-.1l-2.1 2.1a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2\"/></svg></button>
<button class=\"toolbar-icon\" id=\"addFileBtn\" type=\"button\" aria-label=\"Add torrent file\" title=\"Add torrent file\"><svg aria-hidden=\"true\" viewBox=\"0 0 24 24\"><path d=\"M6 2.8h7l5 5V21H6z\"/><path d=\"M13 2.8V8h5\"/><path d=\"M12 11v6M9 14h6\"/></svg></button>
"""
    new_toolbar = """<button class=\"toolbar-icon\" id=\"addTorrentBtn\" type=\"button\" aria-label=\"Add torrent\" title=\"Add torrent\"><svg aria-hidden=\"true\" viewBox=\"0 0 24 24\"><path d=\"M6 2.8h7l5 5V21H6z\"/><path d=\"M13 2.8V8h5\"/><path d=\"M12 11v6M9 14h6\"/></svg></button>
"""
    text = replace_once(text, old_toolbar, new_toolbar, "single Add Torrent toolbar button")

    start = '<div class="modal hidden" id="addModal">'
    end = '<div class="modal hidden" id="actionDialogModal">'
    replacement = """<div class=\"modal hidden\" id=\"addModal\"><div class=\"modal-backdrop\" data-modalclose=\"\"></div><form class=\"modal-card add-torrent-card\" id=\"addForm\"><header class=\"add-torrent-header\"><div><h2>Add torrent</h2><p>Configure the torrent before adding it to qBitTorrent.</p></div><button class=\"icon-btn\" data-modalclose=\"\" type=\"button\" aria-label=\"Close Add Torrent\">×</button></header><div class=\"add-torrent-body\"><section class=\"add-torrent-options\" aria-label=\"Torrent options\"><div class=\"add-torrent-section\"><div class=\"add-torrent-section-title\"><strong>Source</strong><span>Add a magnet link, torrent URL, or local .torrent file.</span></div><label>Magnet or torrent URL<textarea id=\"addUrls\" placeholder=\"magnet:?xt=…\" rows=\"4\"></textarea></label><div class=\"add-source-or\">Or</div><label class=\"file-drop add-file-drop\">Choose torrent file<input accept=\".torrent,application/x-bittorrent\" id=\"torrentFile\" type=\"file\"/></label></div><div class=\"add-torrent-section\"><div class=\"add-torrent-section-title\"><strong>Save at</strong><span>Use manual paths or let qBitTorrent manage the location automatically.</span></div><label>Torrent management mode<select id=\"addAutoTmm\"><option value=\"false\">Manual</option><option value=\"true\">Automatic</option></select></label><label>Save files to location<input id=\"addPath\" placeholder=\"Optional\"/></label><label class=\"add-inline-check\"><input id=\"addUseDownloadPath\" type=\"checkbox\"/> Use another path for incomplete torrent</label><label>Incomplete torrent path<input id=\"addDownloadPath\" placeholder=\"Optional\" disabled/></label></div><div class=\"add-torrent-section\"><div class=\"add-torrent-section-title\"><strong>Torrent settings</strong><span>Apply qBitTorrent's add-time management and transfer options.</span></div><label>Rename torrent<input id=\"addRename\" maxlength=\"512\"/></label><div class=\"two\"><label>Category<input id=\"addCategory\"/></label><label>Tags<input id=\"addTags\"/></label></div><div class=\"add-option-grid\"><label class=\"add-inline-check\"><input id=\"addStartTorrent\" type=\"checkbox\" checked/> Start torrent</label><label>Stop condition<select id=\"addStopCondition\"><option value=\"None\">None</option><option value=\"MetadataReceived\">Metadata received</option><option value=\"FilesChecked\">Files checked</option></select></label><label class=\"add-inline-check\"><input id=\"addToTop\" type=\"checkbox\"/> Add to top of queue</label><label class=\"add-inline-check\"><input id=\"addSeedMode\" type=\"checkbox\"/> Seed mode</label><label class=\"add-inline-check\"><input id=\"addSequential\" type=\"checkbox\"/> Download in sequential order</label><label class=\"add-inline-check\"><input id=\"addFirstLast\" type=\"checkbox\"/> Download first and last pieces first</label></div><label>Content layout<select id=\"addContentLayout\"><option value=\"Original\">Original</option><option value=\"Subfolder\">Create subfolder</option><option value=\"NoSubfolder\">Don't create subfolder</option></select></label><div class=\"add-rate-grid\"><label>Download limit<span class=\"add-rate-input\"><input id=\"addDlLimit\" min=\"0\" step=\"1\" type=\"number\" value=\"0\"/><span>KiB/s</span></span><small>0 means unlimited</small></label><label>Upload limit<span class=\"add-rate-input\"><input id=\"addUlLimit\" min=\"0\" step=\"1\" type=\"number\" value=\"0\"/><span>KiB/s</span></span><small>0 means unlimited</small></label></div><div class=\"field-help\">Seed mode assumes existing files are complete and skips the initial full hash check. Use it only when you already have the torrent data.</div></div></section><section class=\"add-torrent-preview\" aria-label=\"Torrent preview\"><div class=\"add-preview-panel add-content-panel\"><div class=\"add-preview-heading\"><div><strong>Content</strong><span>File selection will be enabled in the metadata phase.</span></div></div><div class=\"add-content-columns\" aria-hidden=\"true\"><span>Name</span><span>Size</span><span>Priority</span></div><div class=\"add-preview-empty\"><strong>Content preview not enabled yet</strong><span>Advanced add options are active, but torrent metadata is not requested in this release.</span></div></div><div class=\"add-preview-panel add-info-panel\"><div class=\"add-preview-heading\"><div><strong>Torrent information</strong><span>Metadata fields will populate in the next controlled phase.</span></div></div><div class=\"add-info-grid\"><span>Total size</span><b>—</b><span>Creation date</span><b>—</b><span>Info hash v1</span><b>—</b><span>Info hash v2</span><b>—</b><span>Created by</span><b>—</b></div></div></section></div><footer class=\"add-torrent-footer\"><div class=\"add-torrent-status\"><strong>Advanced add mode</strong><span>No metadata requests are made in this release.</span></div><div class=\"add-torrent-actions\"><button class=\"secondary\" data-modalclose=\"\" type=\"button\">Cancel</button><button class=\"primary\" type=\"submit\">Add torrent</button></div></footer></form></div>
"""
    text = replace_section(text, start, end, replacement, "Add Torrent modal")
    path.write_text(text, encoding="utf-8")


def update_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    old_bind = """function bindAddTorrentUI(){
  const required=['addLinkBtn','addFileBtn','addModal','addForm','addUrls','torrentFile'];
  const missing=required.filter(id=>!document.getElementById(id));
  if(missing.length){console.error('[Torrent Dashboard] Add Torrent UI unavailable; missing elements',missing);return false}
  $('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));
  $('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));
  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));
  $('#addForm').addEventListener('submit',addTorrent);
  return true;
}
function openAddTorrent(mode='link'){if(state.server==='all')return toast('chooseSpecificServerFirst','error');$('#addModal').classList.remove('hidden');if(mode==='file')$('#torrentFile').click();else $('#addUrls').focus()}
"""
    new_bind = """function syncAddTorrentOptions(){
  const automatic=$('#addAutoTmm')?.value==='true';
  const useDownloadPath=!!$('#addUseDownloadPath')?.checked;
  if($('#addPath'))$('#addPath').disabled=automatic;
  if($('#addUseDownloadPath'))$('#addUseDownloadPath').disabled=automatic;
  if($('#addDownloadPath'))$('#addDownloadPath').disabled=automatic||!useDownloadPath;
}
function bindAddTorrentUI(){
  const required=['addTorrentBtn','addModal','addForm','addUrls','torrentFile','addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addSequential','addFirstLast','addContentLayout','addDlLimit','addUlLimit'];
  const missing=required.filter(id=>!document.getElementById(id));
  if(missing.length){console.error('[Torrent Dashboard] Add Torrent UI unavailable; missing elements',missing);return false}
  $('#addTorrentBtn').addEventListener('click',openAddTorrent);
  $('#addAutoTmm').addEventListener('change',syncAddTorrentOptions);
  $('#addUseDownloadPath').addEventListener('change',syncAddTorrentOptions);
  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));
  $('#addForm').addEventListener('submit',addTorrent);
  syncAddTorrentOptions();
  return true;
}
function openAddTorrent(){if(state.server==='all')return toast('chooseSpecificServerFirst','error');$('#addModal').classList.remove('hidden');syncAddTorrentOptions();$('#addUrls').focus()}
"""
    text = replace_once(text, old_bind, new_bind, "isolated Add Torrent bindings")

    old_add = """async function addTorrent(e){e.preventDefault();if(state.server==='all')return toast('chooseSpecificServerFirst','error');try{const f=$('#torrentFile').files[0];if(f){let fd=new FormData();fd.append('server',state.server);fd.append('savepath',$('#addPath').value);fd.append('category',$('#addCategory').value);fd.append('tags',$('#addTags').value);fd.append('stopped',String($('#addStopped').checked));fd.append('sequentialDownload',String($('#addSequential').checked));fd.append('firstLastPiecePrio',String($('#addFirstLast').checked));fd.append('torrents',f);await api('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:fd})}else{if(!$('#addUrls').value.trim())throw new Error('pasteMagnetUrlOrChooseTorrentFile');await post('/api/action',{server:state.server,action:'add_magnet',urls:$('#addUrls').value.trim(),savepath:$('#addPath').value,category:$('#addCategory').value,tags:$('#addTags').value,stopped:$('#addStopped').checked,sequential:$('#addSequential').checked,first_last:$('#addFirstLast').checked})}$('#addModal').classList.add('hidden');$('#addForm').reset();toast('torrentAdded');setTimeout(refreshStatus,500)}catch(err){toast(err.message,'error')}}
"""
    new_add = """function addRateBytes(selector,label){const value=Number($(selector)?.value||0);if(!Number.isFinite(value)||value<0)throw new Error(`${label} must be zero or greater`);return Math.round(value*1024)}
function addTorrentOptions(){return{auto_tmm:$('#addAutoTmm').value==='true',savepath:$('#addPath').value.trim(),use_download_path:$('#addUseDownloadPath').checked,download_path:$('#addDownloadPath').value.trim(),rename:$('#addRename').value.trim(),category:$('#addCategory').value.trim(),tags:$('#addTags').value.trim(),stopped:!$('#addStartTorrent').checked,stop_condition:$('#addStopCondition').value,add_to_top:$('#addToTop').checked,seed_mode:$('#addSeedMode').checked,sequential:$('#addSequential').checked,first_last:$('#addFirstLast').checked,content_layout:$('#addContentLayout').value,dl_limit:addRateBytes('#addDlLimit','Download limit'),ul_limit:addRateBytes('#addUlLimit','Upload limit')}}
function appendAddTorrentFields(fd,o){fd.append('autoTMM',String(o.auto_tmm));fd.append('savepath',o.savepath);fd.append('useDownloadPath',String(o.use_download_path));fd.append('downloadPath',o.download_path);fd.append('rename',o.rename);fd.append('category',o.category);fd.append('tags',o.tags);fd.append('stopped',String(o.stopped));fd.append('stopCondition',o.stop_condition);fd.append('addToTopOfQueue',String(o.add_to_top));fd.append('seedMode',String(o.seed_mode));fd.append('sequentialDownload',String(o.sequential));fd.append('firstLastPiecePrio',String(o.first_last));fd.append('contentLayout',o.content_layout);fd.append('dlLimit',String(o.dl_limit));fd.append('upLimit',String(o.ul_limit))}
async function addTorrent(e){e.preventDefault();if(state.server==='all')return toast('chooseSpecificServerFirst','error');try{const options=addTorrentOptions(),f=$('#torrentFile').files[0];if(f){let fd=new FormData();fd.append('server',state.server);appendAddTorrentFields(fd,options);fd.append('torrents',f);await api('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:fd})}else{if(!$('#addUrls').value.trim())throw new Error('pasteMagnetUrlOrChooseTorrentFile');await post('/api/action',{server:state.server,action:'add_magnet',urls:$('#addUrls').value.trim(),...options})}$('#addModal').classList.add('hidden');$('#addForm').reset();syncAddTorrentOptions();toast('torrentAdded');setTimeout(refreshStatus,500)}catch(err){toast(err.message,'error')}}
"""
    text = replace_once(text, old_add, new_add, "advanced Add Torrent submission")
    path.write_text(text, encoding="utf-8")


def update_backend():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    old = """        if action == \"add_magnet\":
            form = {
                \"urls\": str(payload.get(\"urls\", \"\"))[:16000],
                \"savepath\": str(payload.get(\"savepath\", \"\"))[:2048],
                \"category\": str(payload.get(\"category\", \"\"))[:256],
                \"tags\": str(payload.get(\"tags\", \"\"))[:1024],
                \"stopped\": str(bool(payload.get(\"stopped\", False))).lower(),
                \"sequentialDownload\": str(bool(payload.get(\"sequential\", False))).lower(),
                \"firstLastPiecePrio\": str(bool(payload.get(\"first_last\", False))).lower(),
            }
            return self.post(\"/api/v2/torrents/add\", form)
"""
    new = """        if action == \"add_magnet\":
            stop_condition = str(payload.get(\"stop_condition\") or \"None\")
            if stop_condition not in (\"None\", \"MetadataReceived\", \"FilesChecked\"):
                raise RuntimeError(\"Unsupported torrent stop condition\")
            content_layout = str(payload.get(\"content_layout\") or \"Original\")
            if content_layout not in (\"Original\", \"Subfolder\", \"NoSubfolder\"):
                raise RuntimeError(\"Unsupported torrent content layout\")
            form = {
                \"urls\": str(payload.get(\"urls\", \"\"))[:16000],
                \"autoTMM\": str(bool(payload.get(\"auto_tmm\", False))).lower(),
                \"savepath\": str(payload.get(\"savepath\", \"\"))[:2048],
                \"useDownloadPath\": str(bool(payload.get(\"use_download_path\", False))).lower(),
                \"downloadPath\": str(payload.get(\"download_path\", \"\"))[:2048],
                \"rename\": str(payload.get(\"rename\", \"\"))[:512],
                \"category\": str(payload.get(\"category\", \"\"))[:256],
                \"tags\": str(payload.get(\"tags\", \"\"))[:1024],
                \"stopped\": str(bool(payload.get(\"stopped\", False))).lower(),
                \"stopCondition\": stop_condition,
                \"addToTopOfQueue\": str(bool(payload.get(\"add_to_top\", False))).lower(),
                \"seedMode\": str(bool(payload.get(\"seed_mode\", False))).lower(),
                \"sequentialDownload\": str(bool(payload.get(\"sequential\", False))).lower(),
                \"firstLastPiecePrio\": str(bool(payload.get(\"first_last\", False))).lower(),
                \"contentLayout\": content_layout,
                \"dlLimit\": max(0, int(payload.get(\"dl_limit\", 0) or 0)),
                \"upLimit\": max(0, int(payload.get(\"ul_limit\", 0) or 0)),
            }
            return self.post(\"/api/v2/torrents/add\", form)
"""
    text = replace_once(text, old, new, "advanced qBitTorrent add form")
    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    if "0.5.49 Add Torrent advanced options" in text:
        raise RuntimeError("v0.5.49 styling already present")
    css = """

/* 0.5.49 Add Torrent advanced options */
.add-torrent-options select{width:100%}.add-inline-check{display:flex!important;align-items:center;gap:7px!important;color:var(--text)!important}.add-inline-check input{width:auto!important;flex:0 0 auto}.add-option-grid{display:grid;gap:8px;margin-top:11px}.add-option-grid>label{margin-top:0}.add-rate-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.add-rate-grid label{margin-top:0}.add-rate-input{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;border:1px solid var(--border);background:var(--panel3);border-radius:10px;overflow:hidden}.add-rate-input input{border:0!important;border-radius:0!important;box-shadow:none!important;background:transparent!important}.add-rate-input>span{padding:0 9px;color:var(--muted);font-size:8px;border-left:1px solid var(--border)}.add-rate-grid small{font-size:8px;color:var(--muted)}
@media(max-width:520px){.add-rate-grid{grid-template-columns:1fr}}
"""
    path.write_text(text.rstrip() + css + "\n", encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    old_toolbar_assert = "    assert 'id=\"addLinkBtn\"' in html and 'id=\"addFileBtn\"' in html\n"
    new_toolbar_assert = "    assert 'id=\"addTorrentBtn\"' in html and 'id=\"addLinkBtn\"' not in html and 'id=\"addFileBtn\"' not in html\n"
    text = replace_once(text, old_toolbar_assert, new_toolbar_assert, "single Add Torrent validator")

    marker = "    assert 'Metadata retrieval complete' not in app_js\n"
    addition = marker + """    # 0.5.49 activates qBitTorrent add-time options while keeping metadata disabled.\n    assert 'id=\"addTorrentBtn\"' in html\n    assert \"function openAddTorrent(){\" in app_js and \"torrentFile').click()\" not in app_js\n    for control in ('addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addContentLayout','addDlLimit','addUlLimit'):\n        assert f'id=\"{control}\"' in html\n    assert 'function addTorrentOptions()' in app_js and 'function appendAddTorrentFields' in app_js\n    assert \"fd.append('autoTMM'\" in app_js and \"fd.append('contentLayout'\" in app_js\n    assert '\"autoTMM\"' in dashboard_py and '\"addToTopOfQueue\"' in dashboard_py and '\"seedMode\"' in dashboard_py\n    assert '\"stopCondition\"' in dashboard_py and '\"contentLayout\"' in dashboard_py\n    assert '0.5.49 Add Torrent advanced options' in app_css\n    assert 'fetch_torrent_metadata' not in dashboard_py\n    assert '/api/torrent-metadata/fetch' not in dashboard_py\n    assert 'addMetadataState' not in app_js\n"""
    text = replace_once(text, marker, addition, "v0.5.49 advanced options validator")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_toolbar_and_modal()
    update_app_js()
    update_backend()
    update_css()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert 'id="addTorrentBtn"' in html and 'id="addLinkBtn"' not in html and 'id="addFileBtn"' not in html
    assert "function openAddTorrent(){" in app and "torrentFile').click()" not in app
    assert 'fetch_torrent_metadata' not in dashboard
    assert "event.request.mode==='navigate'" in sw
    print("Applied v0.5.49 Add Torrent controls and qBitTorrent add-time options")


if __name__ == "__main__":
    main()
