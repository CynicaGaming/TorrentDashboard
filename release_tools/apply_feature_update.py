#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.53"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.52"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.52") < 4:
        raise RuntimeError("Expected v0.5.52 frontend references")
    text = text.replace("0.5.52", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.52';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0552", "torrent-dashboard-v0553", "service worker cache")
    if "v=0.5.52" not in text:
        raise RuntimeError("Expected v0.5.52 service worker assets")
    text = text.replace("v=0.5.52", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_dashboard():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''        return {\n            "speed": {\n                "alternative_enabled": alt_speed,''',
        '''        return {\n            "downloads": {\n                "save_path": str(prefs.get("save_path") or ""),\n                "temp_path_enabled": bool(prefs.get("temp_path_enabled", False)),\n                "temp_path": str(prefs.get("temp_path") or ""),\n            },\n            "speed": {\n                "alternative_enabled": alt_speed,''',
        "client download settings response",
    )

    text = replace_once(
        text,
        '''        speed = data.get("speed") or {}\n        connection = data.get("connection") or {}\n        proxy = data.get("proxy") or {}\n        if not all(isinstance(x, dict) for x in (speed, connection, proxy)):\n            raise RuntimeError("Client settings sections must be objects")\n\n        current = self.preferences()\n        update = {\n            "dl_limit": _qbit_rate_from_kb(speed.get("download_limit_kb", 0), "Download limit"),''',
        '''        downloads = data.get("downloads") or {}\n        speed = data.get("speed") or {}\n        connection = data.get("connection") or {}\n        proxy = data.get("proxy") or {}\n        if not all(isinstance(x, dict) for x in (downloads, speed, connection, proxy)):\n            raise RuntimeError("Client settings sections must be objects")\n\n        save_path = str(downloads.get("save_path") or "").strip()[:4096]\n        temp_path = str(downloads.get("temp_path") or "").strip()[:4096]\n        temp_path_enabled = bool(downloads.get("temp_path_enabled", False))\n        if not save_path:\n            raise RuntimeError("Default save path is required")\n        if temp_path_enabled and not temp_path:\n            raise RuntimeError("Incomplete torrent path is required when the separate path is enabled")\n\n        current = self.preferences()\n        update = {\n            "save_path": save_path,\n            "temp_path_enabled": temp_path_enabled,\n            "temp_path": temp_path,\n            "dl_limit": _qbit_rate_from_kb(speed.get("download_limit_kb", 0), "Download limit"),''',
        "client download settings update",
    )

    text = replace_once(
        text,
        '''                "paused":sum(1 for t in payload.get("torrents",[]) if "paused" in str(t.get("state","")).lower() or "stopped" in str(t.get("state","")).lower()),''',
        '''                "paused":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)<.999999 and ("paused" in str(t.get("state","")).lower() or "stopped" in str(t.get("state","")).lower())),''',
        "paused tab count",
    )

    path.write_text(text, encoding="utf-8")


def update_index():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        'Use another path for incomplete torrent</label>',
        'Use another path for incomplete torrents</label>',
        "Add Torrent incomplete path label",
    )

    old_tabs = '<div class="client-settings-tabs" role="tablist" aria-label="Client settings sections"><button class="active" data-client-settings-tab="speed" type="button">Speed</button><button data-client-settings-tab="connection" type="button">Connection</button><button data-client-settings-tab="proxy" type="button">Proxy</button></div>'
    new_tabs = '<div class="client-settings-tabs" role="tablist" aria-label="Client settings sections"><button class="active" data-client-settings-tab="downloads" type="button">Downloads</button><button data-client-settings-tab="speed" type="button">Speed</button><button data-client-settings-tab="connection" type="button">Connection</button><button data-client-settings-tab="proxy" type="button">Proxy</button></div>'
    text = replace_once(text, old_tabs, new_tabs, "client settings tabs")

    old_body = '<div class="client-settings-body"><section class="client-settings-pane active" data-client-settings-pane="speed">'
    downloads_pane = '<div class="client-settings-body"><section class="client-settings-pane active" data-client-settings-pane="downloads"><div class="client-settings-section-heading"><strong>Download locations</strong><span>Set qBitTorrent\'s default save path and incomplete torrent location.</span></div><div class="client-field-grid client-path-grid"><label><span>Default save path</span><input autocomplete="off" id="clientSavePath"/></label></div><label class="client-setting-row"><span class="client-setting-copy"><strong>Use another path for incomplete torrents</strong><span>Keep incomplete torrent data in a separate location.</span></span><span class="client-switch"><input id="clientTempPathEnabled" type="checkbox"/><span aria-hidden="true"></span></span></label><div class="client-field-grid client-path-grid"><label><span>Incomplete torrent path</span><input autocomplete="off" id="clientTempPath"/></label></div></section><section class="client-settings-pane" data-client-settings-pane="speed">'
    text = replace_once(text, old_body, downloads_pane, "client downloads pane")

    path.write_text(text, encoding="utf-8")


def update_settings_js():
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "    document.querySelector('#clientRandomPort')?.addEventListener('change', syncClientSettingsControls);",
        "    document.querySelector('#clientTempPathEnabled')?.addEventListener('change', syncClientSettingsControls);\n    document.querySelector('#clientRandomPort')?.addEventListener('change', syncClientSettingsControls);",
        "client temp path binding",
    )

    text = replace_once(text, "  function activateClientSettingsTab(tab='speed') {\n    const allowed = new Set(['speed','connection','proxy']);", "  function activateClientSettingsTab(tab='downloads') {\n    const allowed = new Set(['downloads','speed','connection','proxy']);", "client settings tab defaults")

    text = replace_once(
        text,
        "  function syncClientSettingsControls() {\n    const randomPort = !!document.querySelector('#clientRandomPort')?.checked;",
        "  function syncClientSettingsControls() {\n    const tempPathEnabled = !!document.querySelector('#clientTempPathEnabled')?.checked;\n    const tempPath = document.querySelector('#clientTempPath');\n    if (tempPath) tempPath.disabled = !tempPathEnabled;\n    const randomPort = !!document.querySelector('#clientRandomPort')?.checked;",
        "client settings downloads controls",
    )

    text = replace_once(
        text,
        "    const speed=settings?.speed||{}, connection=settings?.connection||{}, proxy=settings?.proxy||{};",
        "    const downloads=settings?.downloads||{}, speed=settings?.speed||{}, connection=settings?.connection||{}, proxy=settings?.proxy||{};",
        "client settings downloads model",
    )

    text = replace_once(
        text,
        "    setChecked('clientAltSpeed',speed.alternative_enabled);",
        "    setValue('clientSavePath',downloads.save_path || '');setChecked('clientTempPathEnabled',downloads.temp_path_enabled);setValue('clientTempPath',downloads.temp_path || '');\n    setChecked('clientAltSpeed',speed.alternative_enabled);",
        "client settings downloads fill",
    )

    text = replace_once(text, "    activateClientSettingsTab('speed');", "    activateClientSettingsTab('downloads');", "client settings initial tab")

    text = replace_once(
        text,
        "    const payload={\n      server:clientSettingsServerId,\n      speed:{alternative_enabled:",
        "    const payload={\n      server:clientSettingsServerId,\n      downloads:{save_path:document.querySelector('#clientSavePath')?.value.trim()||'',temp_path_enabled:!!document.querySelector('#clientTempPathEnabled')?.checked,temp_path:document.querySelector('#clientTempPath')?.value.trim()||''},\n      speed:{alternative_enabled:",
        "client settings downloads payload",
    )

    text = replace_once(
        text,
        "    const numeric=[payload.speed.download_limit_kb,payload.speed.upload_limit_kb,payload.speed.alternative_download_limit_kb,payload.speed.alternative_upload_limit_kb,payload.connection.max_connections,payload.connection.max_connections_per_torrent,payload.connection.max_upload_slots,payload.connection.max_upload_slots_per_torrent];",
        "    if (!payload.downloads.save_path) return setClientSettingsStatus('Default save path is required.', 'bad');\n    if (payload.downloads.temp_path_enabled && !payload.downloads.temp_path) return setClientSettingsStatus('Incomplete torrent path is required when the separate path is enabled.', 'bad');\n    const numeric=[payload.speed.download_limit_kb,payload.speed.upload_limit_kb,payload.speed.alternative_download_limit_kb,payload.speed.alternative_upload_limit_kb,payload.connection.max_connections,payload.connection.max_connections_per_torrent,payload.connection.max_upload_slots,payload.connection.max_upload_slots_per_torrent];",
        "client settings downloads validation",
    )

    path.write_text(text, encoding="utf-8")


def update_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    old_state = "function isComplete(t){return Number(t.progress||0)>=.999999}function isPaused(t){let s=String(t.state||'').toLowerCase();return s.includes('paused')||s.includes('stopped')}function isActive(t){return !isComplete(t)&&!isPaused(t)}\nfunction stateInfo(t){const s=String(t.state||'').toLowerCase();if(s.includes('error')||s.includes('missing'))return['error','error'];if(isPaused(t))return['paused','pause'];if(s.includes('upload')||s.includes('seed'))return[Number(t.upspeed)>0?'seeding':'seedIdle','seed'];if(s.includes('stall')&&!isComplete(t))return['stalled','pause'];if(s.includes('check'))return['checking','pause'];if(s.includes('meta'))return['metadata','down'];if(!isComplete(t)&&Number(t.dlspeed)>0)return['downloading','down'];if(!isComplete(t))return['queued',''];return['complete','seed']}"
    new_state = "function isComplete(t){return Number(t.progress||0)>=.999999}function isStopped(t){let s=String(t.state||'').toLowerCase();return s.includes('paused')||s.includes('stopped')}function isPaused(t){return !isComplete(t)&&isStopped(t)}function isActive(t){return !isComplete(t)&&!isStopped(t)}\nfunction stateInfo(t){const s=String(t.state||'').toLowerCase();if(s.includes('error')||s.includes('missing'))return['error','error'];if(isComplete(t)&&isStopped(t))return['complete','seed'];if(isPaused(t))return['paused','pause'];if(s.includes('upload')||s.includes('seed'))return[Number(t.upspeed)>0?'seeding':'seedIdle','seed'];if(s.includes('stall')&&!isComplete(t))return['stalled','pause'];if(s.includes('check'))return['checking','pause'];if(s.includes('meta'))return['metadata','down'];if(!isComplete(t)&&Number(t.dlspeed)>0)return['downloading','down'];if(!isComplete(t))return['queued',''];return['complete','seed']}"
    text = replace_once(text, old_state, new_state, "torrent status classification")

    text = replace_once(
        text,
        "items.push(item(isPaused(t)?'start':'stop',isPaused(t)?'Resume':'Pause',isPaused(t)?'▶':'Ⅱ'));",
        "items.push(item(isStopped(t)?'start':'stop',isStopped(t)?'Resume':'Pause',isStopped(t)?'▶':'Ⅱ'));",
        "torrent context start-stop action",
    )

    old_open = '''function openAddTorrent(){\n  if(state.server==='all')return toast('chooseSpecificServerFirst','error');\n  $('#addModal').classList.remove('hidden');\n  syncAddTorrentOptions();\n  scheduleAddMetadataPreview(0);\n  $('#addUrls').focus();\n}'''
    new_open = r'''let addTorrentDefaultsRequest=0;
async function loadAddTorrentClientDefaults(){
  const server=state.server,request=++addTorrentDefaultsRequest;
  const initial={save:$('#addPath').value,temp:$('#addDownloadPath').value,use:!!$('#addUseDownloadPath').checked};
  try{
    const data=await api(`/api/client-settings?server=${encodeURIComponent(server)}`);
    if(request!==addTorrentDefaultsRequest||state.server!==server||$('#addModal').classList.contains('hidden'))return;
    const downloads=data?.settings?.downloads||{};
    if($('#addPath').value===initial.save)$('#addPath').value=downloads.save_path||'';
    if($('#addDownloadPath').value===initial.temp)$('#addDownloadPath').value=downloads.temp_path||'';
    if(!!$('#addUseDownloadPath').checked===initial.use)$('#addUseDownloadPath').checked=!!downloads.temp_path_enabled;
    syncAddTorrentOptions();
  }catch(error){console.error('[Torrent Dashboard] Could not load Add Torrent client defaults',error)}
}
function openAddTorrent(){
  if(state.server==='all')return toast('chooseSpecificServerFirst','error');
  $('#addModal').classList.remove('hidden');
  syncAddTorrentOptions();
  loadAddTorrentClientDefaults();
  scheduleAddMetadataPreview(0);
  $('#addUrls').focus();
}'''
    text = replace_once(text, old_open, new_open, "Add Torrent client defaults")

    path.write_text(text, encoding="utf-8")


def update_settings_css():
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    marker = "\n/* 0.5.53 client download-location settings */\n"
    if marker in text:
        raise RuntimeError("0.5.53 client settings CSS already present")
    text += marker + ".client-path-grid{grid-template-columns:1fr}.client-path-grid input{font-family:ui-monospace,SFMono-Regular,Consolas,\"Liberation Mono\",monospace}\n"
    path.write_text(text, encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")
    marker = "    # 0.5.47 frontend generation contract. Navigation HTML is never cached,\n"
    block = '''    # 0.5.53 keeps completed/stopped torrents classified as complete while\n    # exposing qBitTorrent download-location defaults in Client Settings and Add Torrent.\n    assert "function isStopped(t)" in app_js\n    assert "function isPaused(t){return !isComplete(t)&&isStopped(t)}" in app_js\n    assert "if(isComplete(t)&&isStopped(t))return['complete','seed']" in app_js\n    assert "item(isStopped(t)?'start':'stop'" in app_js\n    assert 'float(t.get("progress",0) or 0)<.999999 and ("paused"' in dashboard_py\n    for control in ('clientSavePath','clientTempPathEnabled','clientTempPath'):\n        assert f'id="{control}"' in html\n    assert 'data-client-settings-tab="downloads"' in html\n    assert 'data-client-settings-pane="downloads"' in html\n    assert '"downloads": {' in dashboard_py and '"save_path": str(prefs.get("save_path")' in dashboard_py\n    assert '"temp_path_enabled": bool(prefs.get("temp_path_enabled"' in dashboard_py\n    assert '"temp_path": str(prefs.get("temp_path")' in dashboard_py\n    assert "downloads:{save_path:document.querySelector('#clientSavePath')" in settings_js\n    assert "function loadAddTorrentClientDefaults" in app_js\n    assert "downloads.save_path||''" in app_js and "downloads.temp_path||''" in app_js\n    assert "downloads.temp_path_enabled" in app_js\n    assert 'Use another path for incomplete torrents' in html\n    assert '.client-path-grid{grid-template-columns:1fr}' in settings_css\n\n'''
    text = replace_once(text, marker, block + marker, "0.5.53 validation marker")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_dashboard()
    update_index()
    update_settings_js()
    update_app_js()
    update_settings_css()
    update_validator()


if __name__ == "__main__":
    main()
