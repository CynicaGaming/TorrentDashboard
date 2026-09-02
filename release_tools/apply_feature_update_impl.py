#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.45"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"Missing {label} start marker")
    b = text.find(end, a + len(start))
    if b < 0:
        raise RuntimeError(f"Missing {label} end marker")
    return text[:a] + replacement + text[b:]


def bump_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.44"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if "v=0.5.44" not in text:
        raise RuntimeError("Expected v0.5.44 static asset references")
    index.write_text(text.replace("v=0.5.44", f"v={TARGET_VERSION}"), encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0544" not in text or "v=0.5.44" not in text:
        raise RuntimeError("Expected v0.5.44 service worker identifiers")
    text = text.replace("torrent-dashboard-v0544", "torrent-dashboard-v0545")
    text = text.replace("v=0.5.44", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_backend():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    metadata_methods = r'''    def fetch_torrent_metadata(self, source):
        source = str(source or "").strip()
        if not source:
            raise RuntimeError("Enter a magnet link, torrent URL, or info hash")
        try:
            status, body = self._request("POST", "/api/v2/torrents/fetchMetadata", form={"source": source})
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return {
                    "supported": False,
                    "pending": False,
                    "metadata": {},
                    "source": source,
                    "error": "Metadata preview requires qBitTorrent Web API 2.11.9 or newer",
                }
            raise
        try:
            metadata = json.loads(body.decode() or "{}")
        except Exception as exc:
            raise RuntimeError("qBitTorrent returned invalid torrent metadata") from exc
        if not isinstance(metadata, dict):
            metadata = {}
        canonical = str(metadata.get("id") or metadata.get("infohash_v1") or metadata.get("infohash_v2") or source)
        return {
            "supported": True,
            "pending": status != 200,
            "metadata": metadata,
            "source": canonical,
        }

    def parse_torrent_metadata(self, filename, content):
        boundary = "----TorrentDashboardMetadata" + secrets.token_hex(12)
        safe_name = str(filename or "torrent.torrent").replace('"', "")[:255]
        chunks = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe_name}"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode(),
            content,
            f'\r\n--{boundary}--\r\n'.encode(),
        ]
        try:
            status, body = self._request(
                "POST",
                "/api/v2/torrents/parseMetadata",
                raw=b"".join(chunks),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return {
                    "supported": False,
                    "metadata": {},
                    "source": "",
                    "error": "Metadata preview requires qBitTorrent Web API 2.11.9 or newer",
                }
            raise
        try:
            parsed = json.loads(body.decode() or "[]")
        except Exception as exc:
            raise RuntimeError("qBitTorrent returned invalid torrent metadata") from exc
        if isinstance(parsed, dict):
            metadata = parsed
        elif isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            metadata = parsed[0]
        else:
            metadata = {}
        if status != 200 or not metadata:
            raise RuntimeError("qBitTorrent could not parse the torrent metadata")
        source = str(metadata.get("id") or metadata.get("infohash_v1") or metadata.get("infohash_v2") or "")
        if not source:
            raise RuntimeError("qBitTorrent did not return a torrent identifier")
        return {"supported": True, "metadata": metadata, "source": source}

    def save_torrent_metadata(self, source):
        source = str(source or "").strip()
        if not source:
            raise RuntimeError("Torrent metadata is not available yet")
        try:
            status, body = self._request("POST", "/api/v2/torrents/saveMetadata", form={"source": source})
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                raise RuntimeError("Saving metadata requires qBitTorrent Web API 2.11.9 or newer") from exc
            raise
        if status != 200 or not body:
            raise RuntimeError("qBitTorrent could not export the torrent metadata")
        return body

'''
    text = replace_once(text, "    def detail(self, hash_):\n", metadata_methods + "    def detail(self, hash_):\n", "torrent metadata methods")

    add_start = '        if action == "add_magnet":\n'
    add_end = '        raise RuntimeError(f"Unsupported action: {action}")\n'
    new_add = r'''        if action == "add_magnet":
            form = {
                "urls": str(payload.get("urls", ""))[:16000],
                "savepath": str(payload.get("savepath", ""))[:2048],
                "downloadPath": str(payload.get("download_path", ""))[:2048],
                "useDownloadPath": str(bool(payload.get("use_download_path", False))).lower(),
                "category": str(payload.get("category", ""))[:256],
                "tags": str(payload.get("tags", ""))[:1024],
                "rename": str(payload.get("rename", ""))[:512],
                "autoTMM": str(bool(payload.get("auto_tmm", False))).lower(),
                "stopped": str(bool(payload.get("stopped", False))).lower(),
                "addToTopOfQueue": str(bool(payload.get("add_to_top", False))).lower(),
                "seedMode": str(bool(payload.get("seed_mode", False))).lower(),
                "sequentialDownload": str(bool(payload.get("sequential", False))).lower(),
                "firstLastPiecePrio": str(bool(payload.get("first_last", False))).lower(),
                "stopCondition": str(payload.get("stop_condition") or "None")[:64],
                "contentLayout": str(payload.get("content_layout") or "Original")[:64],
                "dlLimit": max(-1, int(payload.get("download_limit", -1) or -1)),
                "upLimit": max(-1, int(payload.get("upload_limit", -1) or -1)),
            }
            priorities = payload.get("file_priorities")
            if isinstance(priorities, list) and priorities:
                if len(priorities) > 100000:
                    raise RuntimeError("Torrent contains too many file priority entries")
                form["filePriorities"] = ",".join(str(int(value)) for value in priorities)
            return self.post("/api/v2/torrents/add", form)
'''
    a = text.find(add_start)
    b = text.find(add_end, a)
    if a < 0 or b < 0:
        raise RuntimeError("Could not locate add_magnet backend block")
    text = text[:a] + new_add + text[b:]

    route_marker = '''            if path=="/api/action":
                data=parse_json_body(self); sid=data.pop("server","local"); action=data.pop("action"); result=get_client(cfg,sid).action(action,data)
'''
    routes = r'''            if path=="/api/torrent-metadata/fetch":
                data=parse_json_body(self,25000); sid=str(data.get("server") or "local")
                result=get_client(cfg,sid).fetch_torrent_metadata(data.get("source"))
                return self.send_json(200,result,new_cookie)
            if path=="/api/torrent-metadata/parse":
                fields,files=parse_multipart(self); sid=str(fields.get("server") or "local")
                if len(files) != 1:
                    raise RuntimeError("Choose one .torrent file")
                _,filename,content=files[0]
                result=get_client(cfg,sid).parse_torrent_metadata(filename,content)
                return self.send_json(200,result,new_cookie)
            if path=="/api/torrent-metadata/save":
                data=parse_json_body(self,25000); sid=str(data.get("server") or "local")
                body=get_client(cfg,sid).save_torrent_metadata(data.get("source"))
                return self.send_bytes(200,body,"application/x-bittorrent",new_cookie)
'''
    text = replace_once(text, route_marker, routes + route_marker, "metadata API routes")
    path.write_text(text, encoding="utf-8")


def update_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    start = '<div class="modal hidden" id="addModal">'
    end = '<div class="modal hidden" id="actionDialogModal">'
    add_modal = r'''<div class="modal hidden" id="addModal"><div class="modal-backdrop" data-modalclose=""></div><form class="modal-card add-torrent-card" id="addForm"><header><div><h2>Add torrent</h2><p id="addDialogSourceSummary">Configure the torrent before adding it to qBitTorrent.</p></div><button class="icon-btn" data-modalclose="" type="button" aria-label="Close add torrent">×</button></header><div class="add-torrent-layout"><section class="add-options-pane"><div class="add-section add-source-section"><div class="add-section-title">Source</div><label id="addLinkSourceWrap">Magnet or torrent URL<textarea id="addUrls" placeholder="magnet:?xt=…" rows="3"></textarea></label><label class="file-drop hidden" id="addFileSourceWrap">Torrent file<input accept=".torrent,application/x-bittorrent" id="torrentFile" type="file"/></label></div><div class="add-section"><div class="add-section-title">Save at</div><label>Torrent management mode<select id="addAutoTmm"><option value="manual">Manual</option><option value="automatic">Automatic</option></select></label><label>Save path<input id="addPath" placeholder="Use qBitTorrent default"/></label><label class="add-incomplete-toggle"><input id="addUseDownloadPath" type="checkbox"/> Use another path for incomplete torrent</label><label class="hidden" id="addDownloadPathWrap">Incomplete path<input id="addDownloadPath"/></label></div><div class="add-section"><div class="add-section-title">Torrent options</div><label>Rename torrent<input id="addRename"/></label><div class="two"><label>Category<input id="addCategory"/></label><label>Tags<input id="addTags"/></label></div><div class="add-check-grid"><label><input checked id="addStart" type="checkbox"/> Start torrent</label><label><input id="addTopQueue" type="checkbox"/> Add to top of queue</label><label><input id="addSeedMode" type="checkbox"/> Skip hash check</label><label><input id="addSequential" type="checkbox"/> Download in sequential order</label><label><input id="addFirstLast" type="checkbox"/> Download first and last pieces first</label></div><div class="two"><label>Stop condition<select id="addStopCondition"><option value="None">None</option><option value="MetadataReceived">Metadata received</option><option value="FilesChecked">Files checked</option></select></label><label>Content layout<select id="addContentLayout"><option value="Original">Original</option><option value="Subfolder">Create subfolder</option><option value="NoSubfolder">Don't create subfolder</option></select></label></div><div class="two"><label>Download limit <span class="field-unit">KB/s</span><input id="addDownloadLimit" min="0" step="1" type="number" value="0"/></label><label>Upload limit <span class="field-unit">KB/s</span><input id="addUploadLimit" min="0" step="1" type="number" value="0"/></label></div></div><section class="add-info-section" id="addTorrentInfo"><div class="add-section-title">Torrent information</div><div class="add-info-grid"><div><span>Size</span><strong id="addInfoSize">—</strong></div><div><span>Date</span><strong id="addInfoDate">—</strong></div><div><span>Info hash v1</span><strong id="addInfoHashV1">—</strong></div><div><span>Info hash v2</span><strong id="addInfoHashV2">—</strong></div><div><span>Created by</span><strong id="addInfoCreator">—</strong></div><div class="wide"><span>Comment</span><strong id="addInfoComment">—</strong></div></div></section></section><section class="add-content-pane"><div class="add-content-header"><div><strong>Content</strong><span id="addContentSummary">Waiting for a torrent source.</span></div><div class="add-content-actions"><button class="secondary" id="addSelectAll" type="button">Select all</button><button class="secondary" id="addSelectNone" type="button">Select none</button></div></div><div class="add-metadata-progress hidden" id="addMetadataProgress" aria-hidden="true"><span></span></div><div class="add-content-table-wrap"><table class="add-content-table"><thead><tr><th class="add-file-check"></th><th>Name</th><th>Total size</th><th>Download priority</th></tr></thead><tbody id="addFileRows"><tr><td colspan="4"><div class="add-content-empty">Choose a torrent source to retrieve metadata.</div></td></tr></tbody></table></div></section></div><footer class="add-torrent-footer"><div class="add-torrent-footer-left"><div class="add-metadata-status"><span class="add-metadata-dot" id="addMetadataDot" aria-hidden="true"></span><span id="addMetadataStatus">Waiting for metadata.</span></div><button class="secondary hidden" id="addSaveTorrent" type="button">Save as .torrent file</button></div><div><button class="primary" id="addTorrentSubmit" type="submit">Add torrent</button><button class="secondary" data-modalclose="" type="button">Cancel</button></div></footer></form></div>
'''
    text = replace_between(text, start, end, add_modal, "Add Torrent modal")
    path.write_text(text, encoding="utf-8")


def update_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    start = "function openAddTorrent(mode='link'){"
    end = "async function rawJson(url,opt={})"
    metadata_js = r'''let addMetadataTimer=null;
let addMetadataGeneration=0;
let addMetadataState={mode:'link',source:'',metadata:null,supported:true,pending:false,parsedFile:false};
function addModalOpen(){return !$('#addModal')?.classList.contains('hidden')}
function clearAddMetadataTimer(){if(addMetadataTimer!==null){clearTimeout(addMetadataTimer);addMetadataTimer=null}}
function addSources(){return $('#addUrls').value.split(/\r?\n/).map(value=>value.trim()).filter(Boolean)}
function addSingleSource(){const list=addSources();return list.length===1?list[0]:''}
function metadataTotalSize(metadata){const info=metadata?.info||{};if(Number.isFinite(Number(info.length)))return Number(info.length);return(info.files||[]).reduce((sum,file)=>sum+Number(file.length||0),0)}
function setAddMetadataStatus(text,tone=''){const row=$('#addMetadataStatus')?.parentElement;if(!row)return;$('#addMetadataStatus').textContent=text;row.className='add-metadata-status'+(tone?` ${tone}`:'');$('#addMetadataProgress')?.classList.toggle('hidden',tone!=='loading')}
function setAddMetadataExportAvailable(available){$('#addSaveTorrent')?.classList.toggle('hidden',!available)}
function resetAddMetadata(clearSource=false){clearAddMetadataTimer();addMetadataGeneration++;addMetadataState={mode:addMetadataState.mode||'link',source:'',metadata:null,supported:true,pending:false,parsedFile:false};setAddMetadataStatus('Waiting for metadata.');setAddMetadataExportAvailable(false);$('#addContentSummary').textContent='Waiting for a torrent source.';$('#addFileRows').innerHTML='<tr><td colspan="4"><div class="add-content-empty">Choose a torrent source to retrieve metadata.</div></td></tr>';for(const [id,value] of [['addInfoSize','—'],['addInfoDate','—'],['addInfoHashV1','—'],['addInfoHashV2','—'],['addInfoCreator','—'],['addInfoComment','—']])$('#'+id).textContent=value;if(clearSource){$('#addUrls').value='';$('#torrentFile').value=''}syncAddTorrentSubmit()}
function renderAddFiles(files){const body=$('#addFileRows');if(!files.length){body.innerHTML='<tr><td colspan="4"><div class="add-content-empty">Metadata does not contain a file list.</div></td></tr>';return}body.innerHTML=files.map((file,index)=>{const filePath=String(file.path||file.name||`File ${index+1}`),depth=Math.max(0,filePath.split(/[\\/]/).length-1),priority=Number.isFinite(Number(file.priority))?Number(file.priority):1,checked=priority!==0;return`<tr data-add-file-index="${index}"><td class="add-file-check"><input class="add-file-enabled" type="checkbox" ${checked?'checked':''}></td><td><div class="add-file-name"><span class="file-depth" style="width:${depth*12}px"></span><span title="${esc(filePath)}">${esc(filePath)}</span></div></td><td class="mono">${bytes(file.length||0)}</td><td><select class="add-file-priority" ${checked?'':'disabled'}><option value="1" ${priority===1?'selected':''}>Normal</option><option value="6" ${priority===6?'selected':''}>High</option><option value="7" ${priority===7?'selected':''}>Maximum</option></select></td></tr>`}).join('');body.querySelectorAll('.add-file-enabled').forEach(check=>check.addEventListener('change',()=>{check.closest('tr').querySelector('.add-file-priority').disabled=!check.checked}))}
function renderAddMetadata(metadata){metadata=metadata||{};addMetadataState.metadata=metadata;const info=metadata.info||{},files=Array.isArray(info.files)?info.files:[],total=metadataTotalSize(metadata);$('#addInfoSize').textContent=total?bytes(total):'—';$('#addInfoDate').textContent=Number(metadata.creation_date)>1?when(metadata.creation_date):'—';$('#addInfoHashV1').textContent=metadata.infohash_v1||'N/A';$('#addInfoHashV2').textContent=metadata.infohash_v2||'N/A';$('#addInfoCreator').textContent=metadata.created_by||'—';$('#addInfoComment').textContent=metadata.comment||'—';if(info.name&&!$('#addRename').value)$('#addRename').placeholder=info.name;renderAddFiles(files);$('#addContentSummary').textContent=files.length?`${files.length} file${files.length===1?'':'s'} · ${bytes(total)}`:(info.name||'Metadata received');syncAddTorrentSubmit()}
function addFilePriorities(){if(!addMetadataState.metadata?.info?.files?.length)return[];return[...$('#addFileRows').querySelectorAll('tr[data-add-file-index]')].map(row=>row.querySelector('.add-file-enabled').checked?Number(row.querySelector('.add-file-priority').value||1):0)}
function syncAddTorrentSubmit(){const btn=$('#addTorrentSubmit');if(!btn)return;const hasSource=addMetadataState.mode==='file'?!!$('#torrentFile').files[0]:addSources().length>0;btn.disabled=!hasSource}
async function fetchAddMetadata(generation=addMetadataGeneration){const source=addSingleSource();if(!source||generation!==addMetadataGeneration||!addModalOpen())return;addMetadataState.source=source;addMetadataState.pending=true;setAddMetadataStatus('Retrieving metadata…','loading');setAddMetadataExportAvailable(false);$('#addContentSummary').textContent='Retrieving torrent metadata…';try{const result=await post('/api/torrent-metadata/fetch',{server:state.server,source});if(generation!==addMetadataGeneration||!addModalOpen())return;addMetadataState.supported=result.supported!==false;addMetadataState.source=result.source||source;if(result.metadata&&Object.keys(result.metadata).length)renderAddMetadata(result.metadata);if(result.supported===false){addMetadataState.pending=false;setAddMetadataStatus(result.error||'Metadata preview is unavailable.','bad');$('#addContentSummary').textContent='The torrent can still be added without a preview.';return}if(result.pending){addMetadataTimer=setTimeout(()=>fetchAddMetadata(generation),1000);return}addMetadataState.pending=false;setAddMetadataStatus('Metadata retrieval complete','ok');setAddMetadataExportAvailable(!!addMetadataState.metadata?.info);syncAddTorrentSubmit()}catch(error){if(generation!==addMetadataGeneration||!addModalOpen())return;addMetadataState.pending=false;setAddMetadataStatus(error.message,'bad');$('#addContentSummary').textContent='Metadata retrieval failed. The torrent can still be added.';syncAddTorrentSubmit()}}
function scheduleAddMetadata(){clearAddMetadataTimer();addMetadataGeneration++;const generation=addMetadataGeneration;addMetadataState.source='';addMetadataState.metadata=null;addMetadataState.supported=true;addMetadataState.pending=false;addMetadataState.parsedFile=false;setAddMetadataExportAvailable(false);const sources=addSources();if(!sources.length){setAddMetadataStatus('Waiting for metadata.');$('#addContentSummary').textContent='Waiting for a torrent source.';syncAddTorrentSubmit();return}if(sources.length>1){setAddMetadataStatus('Multiple torrent sources selected.');$('#addContentSummary').textContent='Metadata preview is available for one source at a time.';$('#addFileRows').innerHTML='<tr><td colspan="4"><div class="add-content-empty">Add the sources together, or use one source to preview its contents.</div></td></tr>';syncAddTorrentSubmit();return}addMetadataTimer=setTimeout(()=>fetchAddMetadata(generation),350);syncAddTorrentSubmit()}
async function parseAddTorrentFile(){clearAddMetadataTimer();addMetadataGeneration++;const generation=addMetadataGeneration,file=$('#torrentFile').files[0];addMetadataState.source='';addMetadataState.metadata=null;addMetadataState.pending=false;addMetadataState.supported=true;addMetadataState.parsedFile=false;setAddMetadataExportAvailable(false);if(!file){resetAddMetadata(false);return}addMetadataState.pending=true;setAddMetadataStatus('Retrieving metadata…','loading');$('#addContentSummary').textContent='Parsing torrent metadata…';syncAddTorrentSubmit();try{const fd=new FormData();fd.append('server',state.server);fd.append('torrent',file,file.name);const result=await api('/api/torrent-metadata/parse',{method:'POST',body:fd});if(generation!==addMetadataGeneration||!addModalOpen())return;addMetadataState.supported=result.supported!==false;if(result.supported===false){setAddMetadataStatus(result.error||'Metadata preview is unavailable.','bad');$('#addContentSummary').textContent='The torrent can still be added without a preview.';return}addMetadataState.source=result.source||'';addMetadataState.parsedFile=!!result.source;renderAddMetadata(result.metadata||{});setAddMetadataStatus('Metadata retrieval complete','ok');setAddMetadataExportAvailable(!!result.metadata?.info)}catch(error){if(generation!==addMetadataGeneration||!addModalOpen())return;setAddMetadataStatus(error.message,'bad');$('#addContentSummary').textContent='Metadata retrieval failed. The torrent can still be added.'}finally{if(generation===addMetadataGeneration){addMetadataState.pending=false;syncAddTorrentSubmit()}}}
async function saveAddTorrentMetadata(){const source=addMetadataState.source||addSingleSource();if(!source||!addMetadataState.metadata?.info)return;const button=$('#addSaveTorrent');button.disabled=true;try{const response=await fetch('/api/torrent-metadata/save',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({server:state.server,source})});if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(data.error||`HTTP ${response.status}`)}const blob=await response.blob();const name=String(addMetadataState.metadata?.info?.name||'torrent').replace(/[\\/:*?"<>|]+/g,'_').trim().slice(0,180)||'torrent';const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`${name}.torrent`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(error){toast(error.message,'error')}finally{button.disabled=false}}
function selectAllAddFiles(enabled){$('#addFileRows').querySelectorAll('.add-file-enabled').forEach(check=>{check.checked=enabled;const select=check.closest('tr').querySelector('.add-file-priority');if(select)select.disabled=!enabled})}
function closeAddTorrent(){clearAddMetadataTimer();addMetadataGeneration++;addMetadataState.pending=false;$('#addModal').classList.add('hidden')}
function openAddTorrent(mode='link'){if(state.server==='all')return toast('chooseSpecificServerFirst','error');addMetadataState.mode=mode;$('#addForm').reset();$('#addStart').checked=true;$('#addAutoTmm').value='manual';$('#addStopCondition').value='None';$('#addContentLayout').value='Original';$('#addLinkSourceWrap').classList.toggle('hidden',mode!=='link');$('#addFileSourceWrap').classList.toggle('hidden',mode!=='file');$('#addDialogSourceSummary').textContent=mode==='file'?'Choose a .torrent file and review its contents before adding it.':'Enter a magnet link or torrent URL and review its metadata before adding it.';$('#addDownloadPathWrap').classList.add('hidden');resetAddMetadata(false);$('#addModal').classList.remove('hidden');if(mode==='file')setTimeout(()=>$('#torrentFile').click(),0);else setTimeout(()=>$('#addUrls').focus(),0)}

'''
    text = replace_between(text, start, end, metadata_js, "Add Torrent metadata functions")

    add_start = "async function addTorrent(e){"
    add_end = "function notificationCategory(item){"
    add_function = r'''async function addTorrent(e){e.preventDefault();if(state.server==='all')return toast('chooseSpecificServerFirst','error');const file=$('#torrentFile').files[0],cachedSource=addMetadataState.mode==='file'&&addMetadataState.parsedFile?addMetadataState.source:'',linkSource=$('#addUrls').value.trim(),base={server:state.server,savepath:$('#addPath').value.trim(),download_path:$('#addDownloadPath').value.trim(),use_download_path:$('#addUseDownloadPath').checked,category:$('#addCategory').value.trim(),tags:$('#addTags').value.trim(),rename:$('#addRename').value.trim(),auto_tmm:$('#addAutoTmm').value==='automatic',stopped:!$('#addStart').checked,add_to_top:$('#addTopQueue').checked,seed_mode:$('#addSeedMode').checked,sequential:$('#addSequential').checked,first_last:$('#addFirstLast').checked,stop_condition:$('#addStopCondition').value,content_layout:$('#addContentLayout').value,download_limit:Math.max(0,Number($('#addDownloadLimit').value||0))*1024,upload_limit:Math.max(0,Number($('#addUploadLimit').value||0))*1024,file_priorities:addFilePriorities()};try{if(addMetadataState.mode==='file'&&!cachedSource){if(!file)throw new Error('Choose a .torrent file');const fd=new FormData();fd.append('server',state.server);fd.append('savepath',base.savepath);fd.append('downloadPath',base.download_path);fd.append('useDownloadPath',String(base.use_download_path));fd.append('category',base.category);fd.append('tags',base.tags);fd.append('rename',base.rename);fd.append('autoTMM',String(base.auto_tmm));fd.append('stopped',String(base.stopped));fd.append('addToTopOfQueue',String(base.add_to_top));fd.append('seedMode',String(base.seed_mode));fd.append('sequentialDownload',String(base.sequential));fd.append('firstLastPiecePrio',String(base.first_last));fd.append('stopCondition',base.stop_condition);fd.append('contentLayout',base.content_layout);fd.append('dlLimit',String(base.download_limit));fd.append('upLimit',String(base.upload_limit));fd.append('torrents',file,file.name);await api('/api/upload',{method:'POST',body:fd})}else{const source=cachedSource||linkSource;if(!source)throw new Error('Enter a magnet link, torrent URL, or choose a .torrent file');const payload={action:'add_magnet',urls:source,...base};if(!addMetadataState.metadata?.info?.files?.length)delete payload.file_priorities;await post('/api/action',payload)}closeAddTorrent();$('#addForm').reset();toast('torrentAdded');setTimeout(refreshStatus,500)}catch(error){toast(error.message,'error')}}

'''
    text = replace_between(text, add_start, add_end, add_function, "Add Torrent submit function")

    old_bind = "$('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));$('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));$('#addForm').addEventListener('submit',addTorrent);"
    new_bind = "$('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));$('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',closeAddTorrent));$('#addForm').addEventListener('submit',addTorrent);$('#addUrls').addEventListener('input',scheduleAddMetadata);$('#torrentFile').addEventListener('change',parseAddTorrentFile);$('#addUseDownloadPath').addEventListener('change',e=>$('#addDownloadPathWrap').classList.toggle('hidden',!e.target.checked));$('#addAutoTmm').addEventListener('change',e=>{$('#addPath').disabled=e.target.value==='automatic';$('#addUseDownloadPath').disabled=e.target.value==='automatic';$('#addDownloadPath').disabled=e.target.value==='automatic'||!$('#addUseDownloadPath').checked});$('#addSelectAll').addEventListener('click',()=>selectAllAddFiles(true));$('#addSelectNone').addEventListener('click',()=>selectAllAddFiles(false));$('#addSaveTorrent').addEventListener('click',saveAddTorrentMetadata);"
    text = replace_once(text, old_bind, new_bind, "Add Torrent event bindings")
    text = replace_once(text, "closeDetailPane();$('#addModal').classList.add('hidden')", "closeDetailPane();closeAddTorrent()", "Escape Add Torrent close")
    path.write_text(text, encoding="utf-8")


def update_css():
    path = ROOT / "static" / "app.css"
    text = path.read_text(encoding="utf-8")
    if ".add-torrent-card{" in text:
        raise RuntimeError("Add Torrent layout CSS already present")
    css = r'''

/* 0.5.45 qBitTorrent-style Add Torrent workspace */
.add-torrent-card{width:min(1160px,calc(100% - 28px));height:min(820px,calc(100vh - 34px));max-height:none;padding-bottom:0;display:flex;flex-direction:column;overflow:hidden}.add-torrent-card>header{flex:0 0 auto}.add-torrent-card header p{margin:4px 0 0;color:var(--muted);font-size:9px}.add-torrent-layout{display:grid;grid-template-columns:minmax(330px,.9fr) minmax(430px,1.1fr);min-height:0;flex:1}.add-options-pane{min-width:0;overflow:auto;padding:12px;border-right:1px solid var(--border)}.add-content-pane{min-width:0;display:flex;flex-direction:column;overflow:hidden;background:color-mix(in srgb,var(--panel3) 55%,var(--panel))}.add-section,.add-info-section{border:1px solid var(--border);border-radius:11px;background:var(--panel3);padding:11px;margin-bottom:10px}.add-section-title{font-size:10px;font-weight:700;margin-bottom:9px}.add-section label{display:grid;gap:5px;color:var(--muted);font-size:9px;margin:8px 0}.add-section textarea,.add-section input,.add-section select{width:100%}.add-section .two{margin:0}.add-check-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px 12px;margin:10px 0}.add-check-grid label,.add-incomplete-toggle{display:flex!important;align-items:center;gap:7px!important;color:var(--text)!important}.add-check-grid input,.add-incomplete-toggle input{width:auto}.field-unit{float:right;font-size:8px;color:var(--muted)}.add-info-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.add-info-grid>div{min-width:0}.add-info-grid .wide{grid-column:1/-1}.add-info-grid span{display:block;color:var(--muted);font-size:8px}.add-info-grid strong{display:block;margin-top:2px;font-size:9px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.add-content-header{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 11px;border-bottom:1px solid var(--border)}.add-content-header>div:first-child{display:grid;gap:2px}.add-content-header strong{font-size:10px}.add-content-header span{font-size:9px;color:var(--muted)}.add-content-actions{display:flex;gap:5px}.add-content-actions button{font-size:9px;padding:6px 8px}.add-metadata-progress{height:4px;background:var(--panel3);overflow:hidden}.add-metadata-progress span{display:block;height:100%;width:35%;background:var(--accent);animation:addMetadataSlide 1.1s linear infinite}@keyframes addMetadataSlide{from{transform:translateX(-100%)}to{transform:translateX(290%)}}.add-content-table-wrap{overflow:auto;flex:1}.add-content-table{min-width:620px}.add-content-table th{position:sticky;top:0}.add-content-table td{height:auto;min-height:38px;padding:7px 9px;font-size:9px}.add-content-table .add-file-check{width:38px}.add-file-name{display:flex;align-items:center;gap:7px;min-width:0}.add-file-name span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.add-file-name .file-depth{display:inline-block;flex:0 0 auto}.add-content-empty{padding:70px 20px;text-align:center;color:var(--muted)}.add-torrent-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border-top:1px solid var(--border);background:var(--panel3);flex:0 0 auto}.add-torrent-footer>div:last-child{display:flex;gap:7px}.add-torrent-footer-left{display:flex;align-items:center;gap:10px;min-width:0}.add-metadata-status{display:flex;align-items:center;gap:7px;min-width:0;color:var(--muted);font-size:9px}.add-metadata-dot{width:7px;height:7px;border-radius:50%;background:var(--muted);flex:0 0 auto}.add-metadata-status.loading .add-metadata-dot{background:var(--accent)}.add-metadata-status.ok .add-metadata-dot{background:var(--good)}.add-metadata-status.bad .add-metadata-dot{background:var(--bad)}#addSaveTorrent{font-size:9px;padding:6px 8px;white-space:nowrap}
@media(max-width:900px){.add-torrent-card{height:min(900px,calc(100vh - 20px));width:calc(100% - 16px)}.add-torrent-layout{grid-template-columns:1fr;overflow:auto}.add-options-pane{overflow:visible;border-right:0;border-bottom:1px solid var(--border)}.add-content-pane{min-height:360px}}
@media(max-width:700px){.add-check-grid,.add-info-grid{grid-template-columns:1fr}.add-info-grid .wide{grid-column:auto}.add-torrent-footer{align-items:stretch;flex-direction:column}.add-torrent-footer-left{align-items:flex-start;flex-direction:column}.add-torrent-footer>div:last-child{justify-content:flex-end}}
'''
    path.write_text(text.rstrip() + css + "\n", encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    old = '''    # Add Torrent metadata is intentionally not part of 0.5.44.\n    assert "fetch_torrent_metadata" not in dashboard_py\n    assert "/api/torrent-metadata/fetch" not in dashboard_py\n    assert "Metadata retrieval complete" not in app_js\n\n'''
    new = '''    # Add Torrent metadata is demand-driven and isolated from application startup.\n    assert 'id="addMetadataStatus"' in html\n    assert 'id="addSaveTorrent"' in html\n    assert 'id="addFileRows"' in html\n    assert 'id="addStart"' in html and 'id="addStopCondition"' in html\n    assert 'Save as .torrent file' in html\n    assert 'Torrent management mode' in html\n    assert 'def fetch_torrent_metadata(self, source):' in dashboard_py\n    assert 'def parse_torrent_metadata(self, filename, content):' in dashboard_py\n    assert 'def save_torrent_metadata(self, source):' in dashboard_py\n    assert '/api/v2/torrents/fetchMetadata' in dashboard_py\n    assert '/api/v2/torrents/parseMetadata' in dashboard_py\n    assert '/api/v2/torrents/saveMetadata' in dashboard_py\n    assert '/api/torrent-metadata/fetch' in dashboard_py\n    assert '/api/torrent-metadata/parse' in dashboard_py\n    assert '/api/torrent-metadata/save' in dashboard_py\n    assert 'filePriorities' in dashboard_py\n    assert 'addMetadataGeneration' in app_js\n    assert 'clearTimeout(addMetadataTimer)' in app_js\n    assert 'setTimeout(()=>fetchAddMetadata(generation),1000)' in app_js\n    assert 'setInterval' not in app_js[app_js.find('let addMetadataTimer'):app_js.find('async function rawJson')]
    assert "generation!==addMetadataGeneration||!addModalOpen()" in app_js\n    assert "function closeAddTorrent(){clearAddMetadataTimer();addMetadataGeneration++" in app_js\n    assert "fetchAddMetadata(" not in app_js[app_js.find('async function bootstrap'):app_js.find("document.addEventListener('DOMContentLoaded'") if "document.addEventListener('DOMContentLoaded'" in app_js else len(app_js)]\n    assert '.add-torrent-card{' in app_css\n\n'''
    text = replace_once(text, old, new, "Add Torrent validator contract")
    path.write_text(text, encoding="utf-8")


def verify():
    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert 'id="homeBrand"' in html and 'id="brandAddress"' in html
    assert 'id="torrentDetailPane"' in html and 'id="drawer"' not in html
    assert 'id="addMetadataStatus"' in html and 'id="addSaveTorrent"' in html
    assert 'Save as .torrent file' in html
    assert 'def fetch_torrent_metadata(self, source):' in dashboard
    assert 'def parse_torrent_metadata(self, filename, content):' in dashboard
    assert 'def save_torrent_metadata(self, source):' in dashboard
    assert '/api/torrent-metadata/save' in dashboard
    assert 'filePriorities' in dashboard
    assert 'let addMetadataTimer=null;' in js
    assert 'addMetadataGeneration++' in js
    assert 'clearTimeout(addMetadataTimer)' in js
    assert "setTimeout(()=>fetchAddMetadata(generation),1000)" in js
    assert "function closeAddTorrent(){clearAddMetadataTimer();addMetadataGeneration++" in js
    assert '.add-torrent-card{' in css
    assert "__tdMarkStartupStage" not in js
    assert "__tdFetchDiagnostics" not in (ROOT / "static" / "settings.js").read_text(encoding="utf-8")


if __name__ == "__main__":
    bump_versions()
    update_backend()
    update_html()
    update_app_js()
    update_css()
    update_validator()
    verify()
    print("Staged v0.5.45 qBitTorrent-style Add Torrent metadata workflow")
