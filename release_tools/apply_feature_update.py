#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.54"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.53"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.53") < 4:
        raise RuntimeError("Expected v0.5.53 frontend references")
    text = text.replace("0.5.53", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.53';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0553", "torrent-dashboard-v0554", "service worker cache")
    if "v=0.5.53" not in text:
        raise RuntimeError("Expected v0.5.53 service worker assets")
    text = text.replace("v=0.5.53", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    old = '<div class="add-torrent-actions"><button class="secondary" data-modalclose="" type="button">Cancel</button><button class="primary" type="submit">Add torrent</button></div>'
    new = '<div class="add-torrent-actions"><button class="secondary" id="addSaveTorrent" type="button" disabled>Save as .torrent</button><button class="secondary" data-modalclose="" type="button">Cancel</button><button class="primary" type="submit">Add torrent</button></div>'
    text = replace_once(text, old, new, "Add Torrent footer actions")
    path.write_text(text, encoding="utf-8")


def update_javascript():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "const addMetadataState={generation:0,timer:null,source:'',startedAt:0,inFlight:false};",
        "const addMetadataState={generation:0,timer:null,source:'',startedAt:0,inFlight:false,exportSource:'',exportName:''};",
        "metadata state",
    )

    text = replace_once(
        text,
        "function cancelAddMetadata(){addMetadataState.generation+=1;clearAddMetadataTimer();addMetadataState.source='';addMetadataState.startedAt=0;addMetadataState.inFlight=false}",
        "function cancelAddMetadata(){addMetadataState.generation+=1;clearAddMetadataTimer();addMetadataState.source='';addMetadataState.startedAt=0;addMetadataState.inFlight=false;addMetadataState.exportSource='';addMetadataState.exportName='';syncAddTorrentExport()}",
        "metadata cancellation",
    )

    marker = "function resetAddMetadataInfo(){\n"
    helpers = r'''function torrentExportFilename(metadata={}){
  const raw=metadata?.info?.name||metadata?.name||'torrent';
  let clean=String(raw).replace(/[\\/:*?"<>|]/g,'_').trim().replace(/[. ]+$/,'');
  if(!clean)clean='torrent';
  clean=clean.slice(0,220);
  return clean.toLowerCase().endsWith('.torrent')?clean:`${clean}.torrent`;
}
function syncAddTorrentExport(){
  const button=$('#addSaveTorrent');if(!button)return;
  button.disabled=!addMetadataState.exportSource;
}
function setAddTorrentExport(source='',metadata={}){
  addMetadataState.exportSource=String(source||'');
  addMetadataState.exportName=addMetadataState.exportSource?torrentExportFilename(metadata):'';
  syncAddTorrentExport();
}
async function saveAddTorrentMetadata(){
  const source=addMetadataState.exportSource,button=$('#addSaveTorrent');
  if(!source||!button)return;
  const generation=addMetadataState.generation,server=state.server,previous=button.textContent;
  button.disabled=true;button.textContent='Saving…';
  try{
    const url=`/api/torrent-metadata/save?server=${encodeURIComponent(server)}&source=${encodeURIComponent(source)}`;
    const response=await fetch(url,{method:'GET',cache:'no-store'});
    if(!response.ok){
      const type=response.headers.get('content-type')||'';
      const error=type.includes('json')?await response.json():await response.text();
      throw new Error(error?.error||error||`HTTP ${response.status}`);
    }
    const blob=await response.blob();
    if(!blob.size)throw new Error('qBitTorrent returned an empty torrent file');
    if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden'))return;
    const href=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=href;link.download=addMetadataState.exportName||'torrent.torrent';document.body.appendChild(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(href),1000);
    toast('Torrent file saved');
  }catch(error){
    console.error('[Torrent Dashboard] Torrent metadata export failed',error);
    toast(error?.message||'Torrent file could not be saved','error');
  }finally{
    button.textContent=previous;
    syncAddTorrentExport();
  }
}
'''
    text = replace_once(text, marker, helpers + marker, "export helpers")

    text = replace_once(
        text,
        "function renderAddMetadataIdle(title='Waiting for torrent source',text='Paste a single magnet link, torrent URL, or choose a .torrent file to preview its metadata before adding.'){\n  resetAddMetadataInfo();",
        "function renderAddMetadataIdle(title='Waiting for torrent source',text='Paste a single magnet link, torrent URL, or choose a .torrent file to preview its metadata before adding.'){\n  setAddTorrentExport();\n  resetAddMetadataInfo();",
        "idle export reset",
    )
    text = replace_once(
        text,
        "function renderAddMetadataLoading(metadata={}){\n  renderAddMetadataInfo(metadata);",
        "function renderAddMetadataLoading(metadata={}){\n  setAddTorrentExport();\n  renderAddMetadataInfo(metadata);",
        "loading export reset",
    )
    text = replace_once(
        text,
        "function renderAddMetadataComplete(metadata={}){\n  renderAddMetadataInfo(metadata);",
        "function renderAddMetadataComplete(metadata={},exportSource=''){\n  setAddTorrentExport(exportSource,metadata);\n  renderAddMetadataInfo(metadata);",
        "completed export source",
    )
    text = replace_once(
        text,
        "function renderAddMetadataError(message,title='Metadata preview unavailable'){\n  const summary=$('#addContentSummary');",
        "function renderAddMetadataError(message,title='Metadata preview unavailable'){\n  setAddTorrentExport();\n  const summary=$('#addContentSummary');",
        "error export reset",
    )
    text = replace_once(
        text,
        "    renderAddMetadataComplete(metadata);\n    setAddMetadataStatus('Metadata retrieval complete','Preview only · Add torrent still uploads the original .torrent file.','complete');",
        "    renderAddMetadataComplete(metadata,metadata?.hash||'');\n    setAddMetadataStatus('Metadata retrieval complete','Preview only · Add torrent still uploads the original .torrent file.','complete');",
        "parsed torrent export source",
    )
    text = replace_once(
        text,
        "    if(result?.complete){renderAddMetadataComplete(result.metadata||{});return}",
        "    if(result?.complete){renderAddMetadataComplete(result.metadata||{},source);return}",
        "magnet export source",
    )
    text = replace_once(
        text,
        "'addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'];",
        "'addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment','addSaveTorrent'];",
        "required export control",
    )
    text = replace_once(
        text,
        "  $('#torrentFile').addEventListener('change',()=>scheduleAddMetadataPreview(0));\n  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',closeAddTorrent));",
        "  $('#torrentFile').addEventListener('change',()=>scheduleAddMetadataPreview(0));\n  $('#addSaveTorrent').addEventListener('click',saveAddTorrentMetadata);\n  $$('#addModal [data-modalclose]').forEach(x=>x.addEventListener('click',closeAddTorrent));",
        "export button binding",
    )

    path.write_text(text, encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    assert '/api/torrent-metadata/save' not in app_js\n",
        "    assert '/api/torrent-metadata/save' in app_js\n",
        "metadata save UI contract",
    )
    marker = "    assert '.client-path-grid{grid-template-columns:1fr}' in settings_css\n\n"
    addition = """    assert '.client-path-grid{grid-template-columns:1fr}' in settings_css\n\n    # 0.5.54 enables export only after metadata is complete. It must use\n    # qBitTorrent's native saveMetadata cache without changing torrent addition.\n    assert 'id=\"addSaveTorrent\"' in html\n    assert 'Save as .torrent' in html\n    assert 'async function saveAddTorrentMetadata()' in app_js\n    assert \"fetch(url,{method:'GET',cache:'no-store'})\" in app_js\n    assert \"renderAddMetadataComplete(result.metadata||{},source)\" in app_js\n    assert \"renderAddMetadataComplete(metadata,metadata?.hash||'')\" in app_js\n    assert \"link.download=addMetadataState.exportName||'torrent.torrent'\" in app_js\n    assert \"self._request(\\\"GET\\\", route, expect_json=False)\" in dashboard_py\n    assert \"fd.append('filePriorities'\" not in app_js\n    assert 'add_cached_metadata' not in app_js\n\n"""
    text = replace_once(text, marker, addition, "0.5.54 validator block")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_html()
    update_javascript()
    update_validator()


if __name__ == "__main__":
    main()
