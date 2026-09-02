#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.52"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.51"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.51") < 4:
        raise RuntimeError("Expected v0.5.51 frontend references")
    text = text.replace("0.5.51", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.51';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0551", "torrent-dashboard-v0552", "service worker cache")
    if "v=0.5.51" not in text:
        raise RuntimeError("Expected v0.5.51 service worker assets")
    text = text.replace("v=0.5.51", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_html():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    replacements = [
        (
            "Enter a single magnet link or torrent URL to retrieve metadata.",
            "Enter a single magnet link, torrent URL, or choose a .torrent file to retrieve metadata.",
            "content metadata hint",
        ),
        (
            "Paste a single magnet link or torrent URL to preview its metadata before adding.",
            "Paste a single magnet link, torrent URL, or choose a .torrent file to preview its metadata before adding.",
            "empty metadata hint",
        ),
        (
            "Enter a single magnet link or torrent URL to begin.",
            "Enter a torrent source or choose a .torrent file to begin.",
            "footer metadata hint",
        ),
    ]
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    path.write_text(text, encoding="utf-8")


def update_javascript():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "function renderAddMetadataIdle(title='Waiting for torrent source',text='Paste a single magnet link or torrent URL to preview its metadata before adding.')",
        "function renderAddMetadataIdle(title='Waiting for torrent source',text='Paste a single magnet link, torrent URL, or choose a .torrent file to preview its metadata before adding.')",
        "metadata idle copy",
    )
    text = replace_once(
        text,
        "if(summary)summary.textContent='Enter a single magnet link or torrent URL to retrieve metadata.';",
        "if(summary)summary.textContent='Enter a single magnet link, torrent URL, or choose a .torrent file to retrieve metadata.';",
        "metadata summary copy",
    )
    text = replace_once(
        text,
        "setAddMetadataStatus('Metadata preview','Enter a single magnet link or torrent URL to begin.','idle');",
        "setAddMetadataStatus('Metadata preview','Enter a torrent source or choose a .torrent file to begin.','idle');",
        "metadata footer copy",
    )

    source_marker = '''function currentAddMetadataSource(){\n  if($('#torrentFile').files?.[0])return'';\n  const sources=addMetadataSources();\n  return sources.length===1?sources[0]:'';\n}\n'''
    source_new = source_marker + r'''function addTorrentFileKey(file){return file?`${file.name}\u0000${file.size}\u0000${file.lastModified}`:''}
function currentAddTorrentFileKey(){return addTorrentFileKey($('#torrentFile').files?.[0]||null)}
function parsedTorrentMetadata(result){
  const raw=result?.metadata;
  if(Array.isArray(raw))return raw[0]||{};
  return raw&&typeof raw==='object'?raw:{};
}
function renderAddTorrentFileMetadataLoading(file){
  resetAddMetadataInfo();
  const summary=$('#addContentSummary');if(summary)summary.textContent=`Parsing ${file?.name||'.torrent file'} with qBitTorrent.`;
  renderAddMetadataEmpty('Parsing torrent metadata…','Torrent Dashboard is asking qBitTorrent to inspect the selected .torrent file.');
  setAddMetadataStatus('Parsing torrent metadata…','Preview only · the original .torrent file will still be uploaded when you add it.','loading');
}
async function parseAddTorrentFileMetadata(file,generation,fileKey){
  if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||fileKey!==currentAddTorrentFileKey())return;
  addMetadataState.inFlight=true;
  try{
    const form=new FormData();
    form.append('server',state.server);
    form.append('torrents',file,file.name);
    const result=await api('/api/torrent-metadata/parse',{method:'POST',body:form});
    if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||fileKey!==currentAddTorrentFileKey())return;
    const metadata=parsedTorrentMetadata(result);
    if(!metadata||!Object.keys(metadata).length)throw new Error('qBitTorrent returned no torrent metadata');
    renderAddMetadataComplete(metadata);
    setAddMetadataStatus('Metadata retrieval complete','Preview only · Add torrent still uploads the original .torrent file.','complete');
  }catch(error){
    if(generation!==addMetadataState.generation)return;
    console.error('[Torrent Dashboard] Add Torrent file metadata preview failed',error);
    renderAddMetadataError(error?.message||'The selected .torrent file could not be parsed.');
  }finally{
    if(generation===addMetadataState.generation)addMetadataState.inFlight=false;
  }
}
'''
    text = replace_once(text, source_marker, source_new, "torrent file metadata helpers")

    old_file_branch = '''  if($('#torrentFile').files?.[0]){\n    renderAddMetadataIdle('Torrent file selected','.torrent metadata preview will be enabled in the next controlled phase.');\n    setAddMetadataStatus('Torrent file selected','This release retrieves metadata only for magnet links and torrent URLs.','idle');\n    return;\n  }\n'''
    new_file_branch = '''  const torrentFile=$('#torrentFile').files?.[0];\n  if(torrentFile){\n    const fileKey=addTorrentFileKey(torrentFile);\n    addMetadataState.source=fileKey;\n    addMetadataState.startedAt=Date.now();\n    const generation=addMetadataState.generation;\n    renderAddTorrentFileMetadataLoading(torrentFile);\n    addMetadataState.timer=setTimeout(()=>parseAddTorrentFileMetadata(torrentFile,generation,fileKey),Math.max(0,delay));\n    return;\n  }\n'''
    text = replace_once(text, old_file_branch, new_file_branch, "torrent file metadata branch")

    old_listener = "  $('#addUrls').addEventListener('input',()=>scheduleAddMetadataPreview());\n"
    new_listener = "  $('#addUrls').addEventListener('input',()=>{if(!$('#torrentFile').files?.[0])scheduleAddMetadataPreview()});\n"
    text = replace_once(text, old_listener, new_listener, "magnet metadata input listener")

    path.write_text(text, encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")

    old = '''    # 0.5.51 wires only magnet/URL metadata preview into the Add Torrent dialog.\n    for control in ('addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'):\n        assert f'id="{control}"' in html\n    assert '/api/torrent-metadata/fetch' in app_js\n    assert '/api/torrent-metadata/parse' not in app_js\n    assert '/api/torrent-metadata/save' not in app_js\n    assert 'const ADD_METADATA_POLL_MS=1000;' in app_js\n    assert 'const ADD_METADATA_TIMEOUT_MS=120000;' in app_js\n    assert 'const addMetadataState=' in app_js\n    assert 'function scheduleAddMetadataPreview' in app_js\n    assert 'function fetchAddMetadataPreview' in app_js\n    assert 'function cancelAddMetadata' in app_js\n    assert 'function closeAddTorrent()' in app_js\n    assert 'Metadata retrieval complete' in app_js\n    assert 'setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS)' in app_js\n    assert 'setInterval(fetchAddMetadataPreview' not in app_js\n    assert "action:'add_magnet'" in app_js and "api('/api/upload'" in app_js\n    assert "urls:$('#addUrls').value.trim()" in app_js\n    assert 'Preview only · Add torrent still submits the original source.' in app_js\n    assert '0.5.51 Add Torrent magnet metadata preview' in app_css\n'''
    new = '''    # 0.5.51 magnet/URL metadata preview remains bounded and read-only.\n    for control in ('addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'):\n        assert f'id="{control}"' in html\n    assert '/api/torrent-metadata/fetch' in app_js\n    assert 'const ADD_METADATA_POLL_MS=1000;' in app_js\n    assert 'const ADD_METADATA_TIMEOUT_MS=120000;' in app_js\n    assert 'const addMetadataState=' in app_js\n    assert 'function scheduleAddMetadataPreview' in app_js\n    assert 'function fetchAddMetadataPreview' in app_js\n    assert 'function cancelAddMetadata' in app_js\n    assert 'function closeAddTorrent()' in app_js\n    assert 'Metadata retrieval complete' in app_js\n    assert 'setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS)' in app_js\n    assert 'setInterval(fetchAddMetadataPreview' not in app_js\n    assert '0.5.51 Add Torrent magnet metadata preview' in app_css\n\n    # 0.5.52 adds read-only .torrent parsing without changing either stable add path.\n    assert '/api/torrent-metadata/parse' in app_js\n    assert '/api/torrent-metadata/save' not in app_js\n    assert 'function parseAddTorrentFileMetadata' in app_js\n    assert 'function parsedTorrentMetadata' in app_js\n    assert "form.append('torrents',file,file.name)" in app_js\n    assert "api('/api/torrent-metadata/parse',{method:'POST',body:form})" in app_js\n    assert "Array.isArray(raw)" in app_js\n    assert "action:'add_magnet'" in app_js and "api('/api/upload'" in app_js\n    assert "urls:$('#addUrls').value.trim()" in app_js\n    assert 'Preview only · Add torrent still submits the original source.' in app_js\n    assert 'Preview only · Add torrent still uploads the original .torrent file.' in app_js\n    assert '.torrent metadata preview will be enabled in the next controlled phase.' not in app_js\n'''
    text = replace_once(text, old, new, "v0.5.51/0.5.52 metadata validator")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_html()
    update_javascript()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert '/api/torrent-metadata/fetch' in app and '/api/torrent-metadata/parse' in app
    assert '/api/torrent-metadata/save' not in app
    assert "action:'add_magnet'" in app and "api('/api/upload'" in app
    assert "event.request.mode==='navigate'" in sw
    print("Applied v0.5.52 read-only .torrent metadata preview")


if __name__ == "__main__":
    main()
