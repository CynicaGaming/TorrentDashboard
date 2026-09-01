#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return out

settings_js = read('static/settings.js')
settings_js = replace_once(settings_js, '  let clientSettingsAltSpeed = false;\n', '', 'remove old alt speed shadow state')
settings_js = replace_once(
    settings_js,
    "    document.querySelector('#clientSettingsForm')?.addEventListener('submit', saveClientSettings);\n    document.querySelectorAll('[data-client-settings-close]').forEach(el => el.addEventListener('click', closeClientSettings));",
    "    document.querySelector('#clientSettingsForm')?.addEventListener('submit', saveClientSettings);\n    document.querySelectorAll('[data-client-settings-close]').forEach(el => el.addEventListener('click', closeClientSettings));\n    document.querySelectorAll('[data-client-settings-tab]').forEach(el => el.addEventListener('click', () => activateClientSettingsTab(el.dataset.clientSettingsTab)));\n    document.querySelector('#clientRandomPort')?.addEventListener('change', syncClientSettingsControls);\n    document.querySelector('#clientProxyType')?.addEventListener('change', syncClientSettingsControls);\n    document.querySelector('#clientProxyAuth')?.addEventListener('change', syncClientSettingsControls);",
    'client settings bindings',
)

settings_js = regex_once(
    settings_js,
    r'''  function setClientSettingsStatus\(message='', tone='muted'\) \{.*?\n  function updateLocalAddress\(\) \{''',
    '''  function setClientSettingsStatus(message='', tone='muted') {
    const status = document.querySelector('#clientSettingsStatus');
    if (!status) return;
    status.className = `client-settings-status ${tone}`;
    status.textContent = message;
  }

  function activateClientSettingsTab(tab='speed') {
    const allowed = new Set(['speed','connection','proxy']);
    if (!allowed.has(tab)) tab = 'speed';
    document.querySelectorAll('[data-client-settings-tab]').forEach(el => el.classList.toggle('active', el.dataset.clientSettingsTab === tab));
    document.querySelectorAll('[data-client-settings-pane]').forEach(el => el.classList.toggle('active', el.dataset.clientSettingsPane === tab));
  }

  function syncClientSettingsControls() {
    const randomPort = !!document.querySelector('#clientRandomPort')?.checked;
    const listenPort = document.querySelector('#clientListenPort');
    if (listenPort) listenPort.disabled = randomPort;
    const proxyType = document.querySelector('#clientProxyType')?.value || 'none';
    const proxyEnabled = proxyType !== 'none';
    const proxyAuth = proxyEnabled && proxyType !== 'socks4' && !!document.querySelector('#clientProxyAuth')?.checked;
    for (const id of ['clientProxyHost','clientProxyPort']) { const el=document.querySelector('#'+id); if(el) el.disabled=!proxyEnabled; }
    const auth = document.querySelector('#clientProxyAuth'); if (auth) auth.disabled = !proxyEnabled || proxyType === 'socks4';
    const credentials = document.querySelector('#clientProxyCredentials'); if (credentials) credentials.classList.toggle('disabled-fields', !proxyAuth);
    for (const id of ['clientProxyUsername','clientProxyPassword']) { const el=document.querySelector('#'+id); if(el) el.disabled=!proxyAuth; }
    for (const id of ['clientProxyLookup','clientProxyBittorrent','clientProxyPeers']) { const el=document.querySelector('#'+id); if(el) el.disabled=!proxyEnabled; }
    if (proxyType === 'socks4' && auth) auth.checked = false;
  }

  function fillClientSettings(settings) {
    const speed=settings?.speed||{}, connection=settings?.connection||{}, proxy=settings?.proxy||{};
    const setValue=(id,value)=>{const el=document.querySelector('#'+id);if(el)el.value=String(value ?? '');};
    const setChecked=(id,value)=>{const el=document.querySelector('#'+id);if(el)el.checked=!!value;};
    setChecked('clientAltSpeed',speed.alternative_enabled);
    setValue('clientGlobalDl',speed.download_limit_kb ?? 0);setValue('clientGlobalUl',speed.upload_limit_kb ?? 0);
    setValue('clientAltDl',speed.alternative_download_limit_kb ?? 0);setValue('clientAltUl',speed.alternative_upload_limit_kb ?? 0);
    setValue('clientListenPort',connection.listen_port || '');setChecked('clientRandomPort',connection.random_port);setChecked('clientUpnp',connection.upnp);
    setValue('clientMaxConnections',connection.max_connections ?? -1);setValue('clientMaxConnectionsTorrent',connection.max_connections_per_torrent ?? -1);setValue('clientMaxUploads',connection.max_upload_slots ?? -1);setValue('clientMaxUploadsTorrent',connection.max_upload_slots_per_torrent ?? -1);
    setValue('clientProxyType',proxy.type || 'none');setValue('clientProxyHost',proxy.host || '');setValue('clientProxyPort',proxy.port || '');setChecked('clientProxyAuth',proxy.authentication);setValue('clientProxyUsername',proxy.username || '');
    configuredSecret(document.querySelector('#clientProxyPassword'), !!proxy.password_configured, 'Password');
    setChecked('clientProxyLookup',proxy.hostname_lookup);setChecked('clientProxyBittorrent',proxy.bittorrent);setChecked('clientProxyPeers',proxy.peer_connections);
    document.querySelector('#clientProxyLookupRow')?.classList.toggle('hidden', proxy.hostname_lookup_supported === false);
    document.querySelector('#clientProxyBittorrentRow')?.classList.toggle('hidden', proxy.bittorrent_supported === false);
    document.querySelector('#clientProxyPeersRow')?.classList.toggle('hidden', proxy.peer_connections_supported === false);
    syncClientSettingsControls();
  }

  function closeClientSettings() {
    document.querySelector('#clientSettingsModal')?.classList.add('hidden');
    clientSettingsServerId = '';
    setClientSettingsStatus('');
  }

  async function openClientSettings(serverId) {
    serverId = String(serverId || '').trim();
    if (!serverId) return toast('Save The Client Before Opening Client Settings','error');
    const server = (state.settings?.servers || []).find(item => String(item.id || '') === serverId);
    clientSettingsServerId = serverId;
    const modal = document.querySelector('#clientSettingsModal');
    const name = document.querySelector('#clientSettingsClientName');
    if (name) name.textContent = `${server?.name || serverId} · qBitTorrent`;
    activateClientSettingsTab('speed');
    modal?.classList.remove('hidden');
    setClientSettingsStatus('Loading client settings…');
    try {
      const data = await api(`/api/client-settings?server=${encodeURIComponent(serverId)}`);
      fillClientSettings(data.settings || {});
      setClientSettingsStatus('Live settings loaded from qBitTorrent.');
    } catch (e) {
      setClientSettingsStatus(e.message || 'Could not load client settings.', 'bad');
    }
  }

  function clientNumber(id, fallback=0) {
    const value = Number(document.querySelector('#'+id)?.value ?? fallback);
    return Number.isFinite(value) ? Math.trunc(value) : NaN;
  }

  async function saveClientSettings(e) {
    if (e?.preventDefault) e.preventDefault();
    if (!clientSettingsServerId) return;
    const passwordInput=document.querySelector('#clientProxyPassword');
    let proxyPassword='';
    try { proxyPassword=secretFieldValue(passwordInput,'<configured>'); } catch(err) { return setClientSettingsStatus(err.message,'bad'); }
    const payload={
      server:clientSettingsServerId,
      speed:{alternative_enabled:!!document.querySelector('#clientAltSpeed')?.checked,download_limit_kb:clientNumber('clientGlobalDl'),upload_limit_kb:clientNumber('clientGlobalUl'),alternative_download_limit_kb:clientNumber('clientAltDl'),alternative_upload_limit_kb:clientNumber('clientAltUl')},
      connection:{listen_port:clientNumber('clientListenPort'),random_port:!!document.querySelector('#clientRandomPort')?.checked,upnp:!!document.querySelector('#clientUpnp')?.checked,max_connections:clientNumber('clientMaxConnections'),max_connections_per_torrent:clientNumber('clientMaxConnectionsTorrent'),max_upload_slots:clientNumber('clientMaxUploads'),max_upload_slots_per_torrent:clientNumber('clientMaxUploadsTorrent')},
      proxy:{type:document.querySelector('#clientProxyType')?.value||'none',host:document.querySelector('#clientProxyHost')?.value.trim()||'',port:clientNumber('clientProxyPort'),authentication:!!document.querySelector('#clientProxyAuth')?.checked,username:document.querySelector('#clientProxyUsername')?.value.trim()||'',password:proxyPassword,hostname_lookup:!!document.querySelector('#clientProxyLookup')?.checked,bittorrent:!!document.querySelector('#clientProxyBittorrent')?.checked,peer_connections:!!document.querySelector('#clientProxyPeers')?.checked}
    };
    const numeric=[payload.speed.download_limit_kb,payload.speed.upload_limit_kb,payload.speed.alternative_download_limit_kb,payload.speed.alternative_upload_limit_kb,payload.connection.max_connections,payload.connection.max_connections_per_torrent,payload.connection.max_upload_slots,payload.connection.max_upload_slots_per_torrent];
    if (!payload.connection.random_port) numeric.push(payload.connection.listen_port);
    if (payload.proxy.type !== 'none') numeric.push(payload.proxy.port);
    if (numeric.some(x => Number.isNaN(x))) return setClientSettingsStatus('Enter valid whole numbers for the client limits and ports.', 'bad');
    const button = document.querySelector('#saveClientSettings');
    if (button) button.disabled = true;
    setClientSettingsStatus('Saving client settings…');
    try {
      const data=await post('/api/client-settings',payload);
      fillClientSettings(data.settings || {});
      setClientSettingsStatus('Client settings saved.', 'ok');
      toast('clientSettingsSaved');
      if (state.server === clientSettingsServerId) await loadMeta();
    } catch (err) {
      setClientSettingsStatus(err.message || 'Could not save client settings.', 'bad');
    } finally {
      if (button) button.disabled = false;
    }
  }

  function updateLocalAddress() {''',
    'replace client settings implementation',
    re.S,
)
settings_js = replace_once(
    settings_js,
    '<span><b>${esc(display)}${current?\' · You\':\'\'}</b>${showUsername?`<small>${esc(username)}</small>`:\'\'}</span><span class="user-group-badge',
    '<span><span class="user-name-line"><b>${esc(display)}</b>${current?\'<span class="current-user-badge">Current user</span>\':\'\'}</span>${showUsername?`<small>${esc(username)}</small>`:\'\'}</span><span class="user-group-badge',
    'current user badge',
)
write('static/settings.js', settings_js)
