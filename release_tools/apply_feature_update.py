#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.51"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.50"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.50") < 4:
        raise RuntimeError("Expected v0.5.50 frontend references")
    text = text.replace("0.5.50", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.50';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0550", "torrent-dashboard-v0551", "service worker cache")
    if "v=0.5.50" not in text:
        raise RuntimeError("Expected v0.5.50 service worker assets")
    text = text.replace("v=0.5.50", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    start = '<section class="add-torrent-preview" aria-label="Torrent preview">'
    end = '\n<div class="modal hidden" id="actionDialogModal"'
    fragment = '''<section class="add-torrent-preview" aria-label="Torrent preview"><div class="add-preview-panel add-content-panel"><div class="add-preview-heading"><div><strong>Content</strong><span id="addContentSummary">Enter a single magnet link or torrent URL to retrieve metadata.</span></div></div><div class="add-content-columns" aria-hidden="true"><span>Name</span><span>Size</span><span>Priority</span></div><div class="add-content-body" id="addContentBody"><div class="add-preview-empty"><strong>Waiting for torrent source</strong><span>Paste a single magnet link or torrent URL to preview its metadata before adding.</span></div></div></div><div class="add-preview-panel add-info-panel"><div class="add-preview-heading"><div><strong>Torrent information</strong><span>Information is read directly from qBitTorrent metadata.</span></div></div><div class="add-info-grid"><span>Total size</span><b id="addInfoSize">—</b><span>Creation date</span><b id="addInfoDate">—</b><span>Info hash v1</span><b id="addInfoHashV1">—</b><span>Info hash v2</span><b id="addInfoHashV2">—</b><span>Created by</span><b id="addInfoCreatedBy">—</b><span>Comment</span><b id="addInfoComment">—</b></div></div></section></div><footer class="add-torrent-footer"><div class="add-torrent-status" id="addMetadataStatus" aria-live="polite"><strong id="addMetadataStatusTitle">Metadata preview</strong><span id="addMetadataStatusText">Enter a single magnet link or torrent URL to begin.</span><div class="add-metadata-progress hidden" id="addMetadataProgress" aria-hidden="true"><span></span></div></div><div class="add-torrent-actions"><button class="secondary" data-modalclose="" type="button">Cancel</button><button class="primary" type="submit">Add torrent</button></div></footer></form></div>'''
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError("Could not locate Add Torrent preview boundaries")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + fragment + end + after
    path.write_text(text, encoding="utf-8")


def update_javascript():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    start = "function syncAddTorrentOptions(){"
    end = "\n\nasync function rawJson"
    block = r'''const ADD_METADATA_POLL_MS=1000;
const ADD_METADATA_TIMEOUT_MS=120000;
const addMetadataState={generation:0,timer:null,source:'',startedAt:0,inFlight:false};

function clearAddMetadataTimer(){if(addMetadataState.timer!==null){clearTimeout(addMetadataState.timer);addMetadataState.timer=null}}
function cancelAddMetadata(){addMetadataState.generation+=1;clearAddMetadataTimer();addMetadataState.source='';addMetadataState.startedAt=0;addMetadataState.inFlight=false}
function setAddMetadataStatus(title,text,stateName='idle'){
  const status=$('#addMetadataStatus'),progress=$('#addMetadataProgress');
  if($('#addMetadataStatusTitle'))$('#addMetadataStatusTitle').textContent=title;
  if($('#addMetadataStatusText'))$('#addMetadataStatusText').textContent=text;
  if(status)status.dataset.state=stateName;
  if(progress)progress.classList.toggle('hidden',stateName!=='loading');
}
function resetAddMetadataInfo(){
  for(const id of ['addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment']){const el=$('#'+id);if(el)el.textContent='—'}
}
function renderAddMetadataInfo(metadata={}){
  const info=metadata?.info||{};
  $('#addInfoSize').textContent=Number.isFinite(Number(info.length))?bytes(Number(info.length)):'—';
  $('#addInfoDate').textContent=metadata?.creation_date?when(metadata.creation_date):'—';
  $('#addInfoHashV1').textContent=metadata?.infohash_v1||'—';
  $('#addInfoHashV2').textContent=metadata?.infohash_v2||'—';
  $('#addInfoCreatedBy').textContent=metadata?.created_by||'—';
  $('#addInfoComment').textContent=metadata?.comment||'—';
}
function addMetadataPriorityLabel(value){value=Number(value);if(value===0)return'Do not download';if(value===6)return'High';if(value===7)return'Maximum';return'Normal'}
function renderAddMetadataEmpty(title,text){
  const body=$('#addContentBody');if(body)body.innerHTML=`<div class="add-preview-empty"><strong>${esc(title)}</strong><span>${esc(text)}</span></div>`;
}
function renderAddMetadataIdle(title='Waiting for torrent source',text='Paste a single magnet link or torrent URL to preview its metadata before adding.'){
  resetAddMetadataInfo();
  const summary=$('#addContentSummary');if(summary)summary.textContent='Enter a single magnet link or torrent URL to retrieve metadata.';
  renderAddMetadataEmpty(title,text);
  setAddMetadataStatus('Metadata preview','Enter a single magnet link or torrent URL to begin.','idle');
}
function renderAddMetadataLoading(metadata={}){
  renderAddMetadataInfo(metadata);
  const summary=$('#addContentSummary');if(summary)summary.textContent='qBitTorrent is retrieving torrent metadata.';
  renderAddMetadataEmpty('Retrieving metadata…','Torrent Dashboard will update this preview automatically when qBitTorrent has the metadata.');
  setAddMetadataStatus('Retrieving metadata…','You can still add the original torrent source while metadata is loading.','loading');
}
function renderAddMetadataComplete(metadata={}){
  renderAddMetadataInfo(metadata);
  const info=metadata?.info||{},files=Array.isArray(info.files)?info.files:[];
  const summary=$('#addContentSummary');if(summary)summary.textContent=files.length?`${files.length} ${files.length===1?'file':'files'} · ${bytes(Number(info.length)||0)}`:(info.name||'Metadata retrieved');
  const body=$('#addContentBody');
  if(body){
    body.innerHTML=files.length?files.map(file=>`<div class="add-content-row"><span class="add-content-name">${esc(file.path||'')}</span><span>${bytes(Number(file.length)||0)}</span><span>${esc(addMetadataPriorityLabel(file.priority))}</span></div>`).join(''):`<div class="add-preview-empty"><strong>Metadata retrieval complete</strong><span>qBitTorrent returned torrent information without a file list.</span></div>`;
  }
  setAddMetadataStatus('Metadata retrieval complete','Preview only · Add torrent still submits the original source.','complete');
}
function renderAddMetadataError(message,title='Metadata preview unavailable'){
  const summary=$('#addContentSummary');if(summary)summary.textContent='Torrent addition is still available.';
  renderAddMetadataEmpty(title,message);
  setAddMetadataStatus(title,message,'error');
}
function addMetadataSources(){
  return $('#addUrls').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
}
function currentAddMetadataSource(){
  if($('#torrentFile').files?.[0])return'';
  const sources=addMetadataSources();
  return sources.length===1?sources[0]:'';
}
function scheduleAddMetadataPreview(delay=450){
  cancelAddMetadata();
  if($('#addModal').classList.contains('hidden'))return;
  if($('#torrentFile').files?.[0]){
    renderAddMetadataIdle('Torrent file selected','.torrent metadata preview will be enabled in the next controlled phase.');
    setAddMetadataStatus('Torrent file selected','This release retrieves metadata only for magnet links and torrent URLs.','idle');
    return;
  }
  const sources=addMetadataSources();
  if(!sources.length){renderAddMetadataIdle();return}
  if(sources.length!==1){
    renderAddMetadataIdle('Multiple sources entered','Metadata preview is available for one magnet link or torrent URL at a time.');
    setAddMetadataStatus('Multiple sources','Add torrent can submit them, but metadata preview requires one source.','idle');
    return;
  }
  const source=sources[0];
  if(!/^(magnet:\?|https?:\/\/)/i.test(source)){
    renderAddMetadataError('Enter a magnet link or HTTP(S) torrent URL to retrieve metadata.','Unsupported metadata source');
    return;
  }
  addMetadataState.source=source;
  addMetadataState.startedAt=Date.now();
  const generation=addMetadataState.generation;
  renderAddMetadataLoading();
  addMetadataState.timer=setTimeout(()=>fetchAddMetadataPreview(source,generation),Math.max(0,delay));
}
async function fetchAddMetadataPreview(source,generation){
  if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||source!==currentAddMetadataSource())return;
  if(Date.now()-addMetadataState.startedAt>ADD_METADATA_TIMEOUT_MS){
    renderAddMetadataError('Metadata retrieval exceeded two minutes. You can still add the torrent normally.','Metadata retrieval timed out');
    return;
  }
  addMetadataState.inFlight=true;
  try{
    const result=await post('/api/torrent-metadata/fetch',{server:state.server,source});
    if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||source!==currentAddMetadataSource())return;
    if(result?.complete){renderAddMetadataComplete(result.metadata||{});return}
    renderAddMetadataLoading(result?.metadata||{});
    addMetadataState.timer=setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS);
  }catch(error){
    if(generation!==addMetadataState.generation)return;
    console.error('[Torrent Dashboard] Add Torrent metadata preview failed',error);
    renderAddMetadataError(error?.message||'Metadata could not be retrieved.');
  }finally{
    if(generation===addMetadataState.generation)addMetadataState.inFlight=false;
  }
}
function closeAddTorrent(){cancelAddMetadata();$('#addModal').classList.add('hidden')}
function syncAddTorrentOptions(){
  const automatic=$('#addAutoTmm')?.value==='true';
  const useDownloadPath=!!$('#addUseDownloadPath')?.checked;
  if($('#addPath'))$('#addPath').disabled=automatic;
  if($('#addUseDownloadPath'))$('#addUseDownloadPath').disabled=automatic;
  if($('#addDownloadPath'))$('#addDownloadPath').disabled=automatic||!useDownloadPath;
}
function bindAddTorrentUI(){
  const required=['addTorrentBtn','addModal','addForm','addUrls','torrentFile','addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addSequential','addFirstLast','addContentLayout','addDlLimit','addUlLimit','addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'];
  const missing=required.filter(id=>!document.getElementById(id));
  if(missing.length){console.error('[Torrent Dashboard] Add Torrent UI unavailable; missing elements',missing);return false}
  $('#addTorrentBtn').addEventListener('click',openAddTorrent);
  $('#addAutoTmm').addEventListener('change',syncAddTorrentOptions);
  $('#addUseDownloadPath').addEventListener('change',syncAddTorrentOptions);
  $('#addUrls').addEventListener('input',()=>scheduleAddMetadataPreview());
  $('#torrentFile').addEventListener('change',()=>scheduleAddMetadataPreview(0));
  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',closeAddTorrent));
  $('#addForm').addEventListener('submit',addTorrent);
  syncAddTorrentOptions();
  renderAddMetadataIdle();
  return true;
}
function openAddTorrent(){
  if(state.server==='all')return toast('chooseSpecificServerFirst','error');
  $('#addModal').classList.remove('hidden');
  syncAddTorrentOptions();
  scheduleAddMetadataPreview(0);
  $('#addUrls').focus();
}'''
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError("Could not locate Add Torrent binding block")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + block + end + after

    add_start = "async function addTorrent(e){"
    add_end = "\n\nfunction notificationCategory"
    add_block = r'''async function addTorrent(e){
  e.preventDefault();
  if(state.server==='all')return toast('chooseSpecificServerFirst','error');
  try{
    const options=addTorrentOptions(),f=$('#torrentFile').files[0];
    if(f){
      let fd=new FormData();fd.append('server',state.server);appendAddTorrentFields(fd,options);fd.append('torrents',f);
      await api('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:fd});
    }else{
      if(!$('#addUrls').value.trim())throw new Error('pasteMagnetUrlOrChooseTorrentFile');
      await post('/api/action',{server:state.server,action:'add_magnet',urls:$('#addUrls').value.trim(),...options});
    }
    closeAddTorrent();
    $('#addForm').reset();
    syncAddTorrentOptions();
    renderAddMetadataIdle();
    toast('torrentAdded');
    setTimeout(refreshStatus,500);
  }catch(err){toast(err.message,'error')}
}'''
    if text.count(add_start) != 1 or text.count(add_end) != 1:
        raise RuntimeError("Could not locate Add Torrent submit function")
    before, rest = text.split(add_start, 1)
    _, after = rest.split(add_end, 1)
    text = before + add_block + add_end + after

    old_escape = "if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDetailPane();$('#addModal')?.classList.add('hidden')"
    new_escape = "if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(!$('#addModal')?.classList.contains('hidden')){closeAddTorrent();return}if(state.selected.size){state.selected.clear();render();return}closeDetailPane()"
    text = replace_once(text, old_escape, new_escape, "Escape Add Torrent close handling")
    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    marker = "/* 0.5.51 Add Torrent magnet metadata preview */"
    if marker in text:
        raise RuntimeError("0.5.51 metadata CSS already present")
    text += r'''

/* 0.5.51 Add Torrent magnet metadata preview */
.add-content-body{flex:1;min-height:0;overflow:auto}.add-content-row{display:grid;grid-template-columns:minmax(0,1fr) 90px 90px;gap:10px;align-items:center;padding:8px 12px;border-bottom:1px solid color-mix(in srgb,var(--border) 55%,transparent);font-size:9px}.add-content-row:last-child{border-bottom:0}.add-content-row>span:nth-child(n+2){text-align:right;color:var(--muted)}.add-content-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text)!important;text-align:left!important}.add-torrent-status[data-state="loading"] strong{color:var(--accent)}.add-torrent-status[data-state="complete"] strong{color:var(--good)}.add-torrent-status[data-state="error"] strong{color:var(--bad)}.add-metadata-progress{width:min(220px,40vw);height:3px;margin-top:4px;overflow:hidden;border-radius:999px;background:var(--panel3)}.add-metadata-progress span{display:block;width:38%;height:100%;border-radius:inherit;background:var(--accent);animation:add-metadata-slide 1.15s ease-in-out infinite}@keyframes add-metadata-slide{0%{transform:translateX(-115%)}50%{transform:translateX(80%)}100%{transform:translateX(265%)}}@media(max-width:520px){.add-content-row{grid-template-columns:minmax(0,1fr) 62px 62px}.add-metadata-progress{width:100%}}
'''
    path.write_text(text, encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    start = "    # Add Torrent metadata is implemented server-side in 0.5.50 but remains\n"
    end = "    # 0.5.47 frontend generation contract."
    block = '''    # Add Torrent shell and native qBitTorrent add options remain present.
    assert 'class="modal-card add-torrent-card"' in html
    assert 'class="add-torrent-body"' in html
    assert 'class="add-torrent-options"' in html
    assert 'class="add-torrent-preview"' in html
    assert 'id="addUrls"' in html and 'id="torrentFile"' in html and 'id="addPath"' in html
    assert 'id="addCategory"' in html and 'id="addTags"' in html
    assert 'id="addStartTorrent"' in html and 'id="addSequential"' in html and 'id="addFirstLast"' in html
    assert 'id="addTorrentBtn"' in html
    assert "function openAddTorrent(){" in app_js and "torrentFile').click()" not in app_js
    for control in ('addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addContentLayout','addDlLimit','addUlLimit'):
        assert f'id="{control}"' in html
    assert 'function addTorrentOptions()' in app_js and 'function appendAddTorrentFields' in app_js
    assert "fd.append('autoTMM'" in app_js and "fd.append('contentLayout'" in app_js
    assert '"autoTMM"' in dashboard_py and '"addToTopOfQueue"' in dashboard_py and '"seedMode"' in dashboard_py
    assert '"stopCondition"' in dashboard_py and '"contentLayout"' in dashboard_py
    assert '0.5.48 Add Torrent visual shell' in app_css
    assert '0.5.49 Add Torrent advanced options' in app_css

    # 0.5.50 metadata backend remains available.
    for method in ('fetch_torrent_metadata','parse_torrent_metadata','save_torrent_metadata'):
        assert f'def {method}' in dashboard_py
    for route in ('/api/torrent-metadata/fetch','/api/torrent-metadata/parse','/api/torrent-metadata/save'):
        assert route in dashboard_py
    assert '/api/v2/torrents/fetchMetadata' in dashboard_py
    assert '/api/v2/torrents/parseMetadata' in dashboard_py
    assert '/api/v2/torrents/saveMetadata' in dashboard_py
    assert 'qbit_status' in dashboard_py and 'complete' in dashboard_py
    assert 'Torrent metadata preview requires qBittorrent Web API 2.11.9 or newer' in dashboard_py

    # 0.5.51 wires only magnet/URL metadata preview into the Add Torrent dialog.
    for control in ('addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'):
        assert f'id="{control}"' in html
    assert '/api/torrent-metadata/fetch' in app_js
    assert '/api/torrent-metadata/parse' not in app_js
    assert '/api/torrent-metadata/save' not in app_js
    assert 'const ADD_METADATA_POLL_MS=1000;' in app_js
    assert 'const ADD_METADATA_TIMEOUT_MS=120000;' in app_js
    assert 'const addMetadataState=' in app_js
    assert 'function scheduleAddMetadataPreview' in app_js
    assert 'function fetchAddMetadataPreview' in app_js
    assert 'function cancelAddMetadata' in app_js
    assert 'function closeAddTorrent()' in app_js
    assert 'Metadata retrieval complete' in app_js
    assert 'setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS)' in app_js
    assert 'setInterval(fetchAddMetadataPreview' not in app_js
    assert "action:'add_magnet'" in app_js and "api('/api/upload'" in app_js
    assert "urls:$('#addUrls').value.trim()" in app_js
    assert 'Preview only · Add torrent still submits the original source.' in app_js
    assert '0.5.51 Add Torrent magnet metadata preview' in app_css
'''
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError("Could not locate Add Torrent validator block")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before + block + end + after
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_html()
    update_javascript()
    update_css()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert "/api/torrent-metadata/fetch" in app
    assert "/api/torrent-metadata/parse" not in app
    assert "/api/torrent-metadata/save" not in app
    assert "event.request.mode==='navigate'" in sw
    print("Applied v0.5.51 magnet metadata preview")


if __name__ == "__main__":
    main()
