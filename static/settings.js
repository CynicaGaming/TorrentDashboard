'use strict';

window.TDSettings = (() => {
  let bound = false;
  let catalog = [];
  let integrations = [];
  let users = [];
  let currentUserId = '';
  let clientSettingsServerId = '';
  let integrationHealthRefreshing = false;
  let pendingNotificationSoundFile = null;

  const corePages = new Set(['general','access','clients','updates','notifications']);
  const SECRET_MASK = '••••••••••';

  function configuredSecret(input, configured, emptyPlaceholder='') {
    setConfiguredSecretField(input, configured, emptyPlaceholder);
  }

  function activate(page) {
    page = page || localStorage.tdSettingsPage || 'general';
    const allowed = ['general','access','clients','updates','notifications','integrations','users'];
    if (!allowed.includes(page)) page = 'general';
    localStorage.tdSettingsPage = page;
    document.querySelectorAll('[data-settings-section]').forEach(el => el.classList.toggle('active', el.dataset.settingsSection === page));
    document.querySelectorAll('[data-settings-page]').forEach(el => el.classList.toggle('active', el.dataset.settingsPage === page));
    const mobilePage = document.querySelector('#settingsMobilePage');
    if (mobilePage && mobilePage.value !== page) mobilePage.value = page;
    const savebar = document.querySelector('#settingsSavebar');
    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));
  }

  function bind() {
    if (bound) return;
    bound = true;
    document.querySelectorAll('[data-settings-page]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.settingsPage)));
    document.querySelector('#settingsMobilePage')?.addEventListener('change', e => activate(e.target.value));
    document.querySelector('#settingsForm')?.addEventListener('submit', saveCore);
    document.querySelector('#copyLocalAddress')?.addEventListener('click', () => navigator.clipboard.writeText(document.querySelector('#localDashboardUrl')?.textContent || '').then(() => toast('Address copied')));
    document.querySelector('#sPort')?.addEventListener('input', updateLocalAddress);
    document.querySelector('#sRefreshInterfaces')?.addEventListener('click', () => refreshSettingsInterfaces(true).catch(e => toast(e.message,'error')));
    document.querySelector('#addServerSetting')?.addEventListener('click', () => addServerRow());
    document.querySelector('#clientSettingsForm')?.addEventListener('submit', saveClientSettings);
    document.querySelectorAll('[data-client-settings-close]').forEach(el => el.addEventListener('click', closeClientSettings));
    document.querySelectorAll('[data-client-settings-tab]').forEach(el => el.addEventListener('click', () => activateClientSettingsTab(el.dataset.clientSettingsTab)));
    document.querySelector('#clientTempPathEnabled')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#clientRandomPort')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#clientProxyType')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#clientProxyAuth')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);
    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);
    bindNotificationSoundModeSelect();
    document.querySelector('#nSoundFile')?.addEventListener('change', event => setNotificationSoundFile(event.target.files?.[0] || null));
    document.querySelector('#nSoundVolume')?.addEventListener('input', updateNotificationVolumeUi);
    bindNotificationSoundDrop();
    document.querySelector('#testNotification')?.addEventListener('click', testNotification);
    document.querySelector('#addIntegrationSetting')?.addEventListener('click', addIntegration);
    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);
    setInterval(() => {
      const page = document.querySelector('[data-settings-section="integrations"]');
      if (page?.classList.contains('active')) refreshIntegrationHealth();
    }, 30000);
    activate(localStorage.tdSettingsPage || 'general');
  }

  function setClientSettingsStatus(message='', tone='muted') {
    const status = document.querySelector('#clientSettingsStatus');
    if (!status) return;
    status.className = `client-settings-status ${tone}`;
    status.textContent = message;
  }

  function activateClientSettingsTab(tab='downloads') {
    const allowed = new Set(['downloads','speed','connection','proxy']);
    if (!allowed.has(tab)) tab = 'speed';
    document.querySelectorAll('[data-client-settings-tab]').forEach(el => el.classList.toggle('active', el.dataset.clientSettingsTab === tab));
    document.querySelectorAll('[data-client-settings-pane]').forEach(el => el.classList.toggle('active', el.dataset.clientSettingsPane === tab));
  }

  function syncClientSettingsControls() {
    const tempPathEnabled = !!document.querySelector('#clientTempPathEnabled')?.checked;
    const tempPath = document.querySelector('#clientTempPath');
    if (tempPath) tempPath.disabled = !tempPathEnabled;
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
    const downloads=settings?.downloads||{}, speed=settings?.speed||{}, connection=settings?.connection||{}, proxy=settings?.proxy||{};
    const setValue=(id,value)=>{const el=document.querySelector('#'+id);if(el)el.value=String(value ?? '');};
    const setChecked=(id,value)=>{const el=document.querySelector('#'+id);if(el)el.checked=!!value;};
    setValue('clientSavePath',downloads.save_path || '');setChecked('clientTempPathEnabled',downloads.temp_path_enabled);setValue('clientTempPath',downloads.temp_path || '');
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
    if (!serverId) return toast('Save this client before opening its settings','error');
    const server = (state.settings?.servers || []).find(item => String(item.id || '') === serverId);
    clientSettingsServerId = serverId;
    const modal = document.querySelector('#clientSettingsModal');
    const name = document.querySelector('#clientSettingsClientName');
    if (name) name.textContent = `${server?.name || serverId} · qBitTorrent`;
    activateClientSettingsTab('downloads');
    modal?.classList.remove('hidden');
    setClientSettingsStatus('Loading client settings…');
    try {
      const data = await api(`/api/client-settings?server=${encodeURIComponent(serverId)}`);
      fillClientSettings(data.settings || {});
      setClientSettingsStatus('Settings loaded from qBitTorrent.');
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
      downloads:{save_path:document.querySelector('#clientSavePath')?.value.trim()||'',temp_path_enabled:!!document.querySelector('#clientTempPathEnabled')?.checked,temp_path:document.querySelector('#clientTempPath')?.value.trim()||''},
      speed:{alternative_enabled:!!document.querySelector('#clientAltSpeed')?.checked,download_limit_kb:clientNumber('clientGlobalDl'),upload_limit_kb:clientNumber('clientGlobalUl'),alternative_download_limit_kb:clientNumber('clientAltDl'),alternative_upload_limit_kb:clientNumber('clientAltUl')},
      connection:{listen_port:clientNumber('clientListenPort'),random_port:!!document.querySelector('#clientRandomPort')?.checked,upnp:!!document.querySelector('#clientUpnp')?.checked,max_connections:clientNumber('clientMaxConnections'),max_connections_per_torrent:clientNumber('clientMaxConnectionsTorrent'),max_upload_slots:clientNumber('clientMaxUploads'),max_upload_slots_per_torrent:clientNumber('clientMaxUploadsTorrent')},
      proxy:{type:document.querySelector('#clientProxyType')?.value||'none',host:document.querySelector('#clientProxyHost')?.value.trim()||'',port:clientNumber('clientProxyPort'),authentication:!!document.querySelector('#clientProxyAuth')?.checked,username:document.querySelector('#clientProxyUsername')?.value.trim()||'',password:proxyPassword,hostname_lookup:!!document.querySelector('#clientProxyLookup')?.checked,bittorrent:!!document.querySelector('#clientProxyBittorrent')?.checked,peer_connections:!!document.querySelector('#clientProxyPeers')?.checked}
    };
    if (!payload.downloads.save_path) return setClientSettingsStatus('Default save path is required.', 'bad');
    if (payload.downloads.temp_path_enabled && !payload.downloads.temp_path) return setClientSettingsStatus('Incomplete torrent path is required when the separate path is enabled.', 'bad');
    const numeric=[payload.speed.download_limit_kb,payload.speed.upload_limit_kb,payload.speed.alternative_download_limit_kb,payload.speed.alternative_upload_limit_kb,payload.connection.max_connections,payload.connection.max_connections_per_torrent,payload.connection.max_upload_slots,payload.connection.max_upload_slots_per_torrent];
    if (!payload.connection.random_port) numeric.push(payload.connection.listen_port);
    if (payload.proxy.type !== 'none') numeric.push(payload.proxy.port);
    if (numeric.some(x => Number.isNaN(x))) return setClientSettingsStatus('Enter whole numbers for client limits and ports.', 'bad');
    const button = document.querySelector('#saveClientSettings');
    if (button) button.disabled = true;
    setClientSettingsStatus('Saving client settings…');
    try {
      const data=await post('/api/client-settings',payload);
      fillClientSettings(data.settings || {});
      setClientSettingsStatus('Client settings saved.', 'ok');
      if (state.server === clientSettingsServerId) await loadMeta();
    } catch (err) {
      setClientSettingsStatus(err.message || 'Could not save client settings.', 'bad');
    } finally {
      if (button) button.disabled = false;
    }
  }

  function updateLocalAddress() {
    const scheme = state.settings?.dashboard?.https_enabled ? 'https' : 'http';
    const ip = document.querySelector('#sLocalIp')?.value || state.me?.lan_ip || '127.0.0.1';
    const port = document.querySelector('#sPort')?.value || state.settings?.dashboard?.port || 8765;
    const out = document.querySelector('#localDashboardUrl');
    if (out) out.textContent = `${scheme}://${ip}:${port}`;
  }

  function fill(s) {
    if (!s) return;
    const setValue = (id, value) => { const el=document.querySelector('#'+id); if(el) el.value=value ?? ''; };
    const setChecked = (id, value) => { const el=document.querySelector('#'+id); if(el) el.checked=!!value; };
    setValue('sTitle', s.dashboard?.title || 'Torrent Dashboard');
    setValue('sLocalIp', s.runtime?.local_ip || state.me?.lan_ip || '127.0.0.1');
    setValue('sPort', s.dashboard?.port || state.me?.port || 8765);
    updateLocalAddress();
    setValue('sAuth', s.auth?.mode || 'required');
    setValue('sTrustedIps', (s.auth?.trusted_ips || []).join('\n'));
    renderInterfaceList('#sInterfaceList', s.runtime?.network_interfaces || [], s.auth?.trusted_interfaces || [], false);
    state.settingsInterfaceSelectionInitialized = true;

    setValue('sTheme', localStorage.tdTheme || 'dark');
    setValue('sDensity', localStorage.tdDensity || 'comfortable');
    setValue('sAccent', localStorage.tdAccent || '#72a9ff');

    const updateRepository = s.updates?.repository || '';
    setValue('uRepository', updateRepository);
    renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{},releaseHistory:s.runtime?.releaseHistory||[]});

    renderServerSettings(s.servers || []);
    [...document.querySelectorAll('.server-setting')].forEach((row, index) => {
      const server = (s.servers || [])[index] || {};
      configuredSecret(row.querySelector('[data-k="api_key"]'), server.api_key === '<configured>', 'qbt_…');
      configuredSecret(row.querySelector('[data-k="password"]'), server.password === '<configured>', 'Password');
    });
    const n = s.notifications || {};
    setChecked('nBrowser', n.browser !== false);
    setChecked('nSound', n.sound);
    setValue('nSoundMode', n.sound_mode || 'default');
    setValue('nSoundVolume', Number.isFinite(Number(n.volume)) ? Math.max(0, Math.min(100, Number(n.volume))) : 72);
    pendingNotificationSoundFile = null;
    const soundFile = document.querySelector('#nSoundFile');
    if (soundFile) soundFile.value = '';
    const soundName = document.querySelector('#nCustomSoundName');
    if (soundName) soundName.textContent = n.custom_sound_name || 'No custom sound uploaded';
    updateNotificationSoundUi();
    updateNotificationVolumeUi();
    activate(localStorage.tdSettingsPage || 'general');
  }

  async function saveCore(e) {
    if (e?.preventDefault) e.preventDefault();
    const activePage = document.querySelector('.settings-page.active')?.dataset.settingsSection || 'general';
    if (activePage === 'updates') return saveUpdateSource();
    const servers = [...document.querySelectorAll('.server-setting')].map(serverRowData);
    const payload = {
      dashboard: {
        title: document.querySelector('#sTitle')?.value || 'Torrent Dashboard',
        port: Number(document.querySelector('#sPort')?.value || 8765)
      },
      auth: {
        mode: document.querySelector('#sAuth')?.value || 'required',
        trusted_interfaces: selectedInterfaceIds('#sInterfaceList'),
        trusted_ips: parseWhitelist('#sTrustedIps')
      },
      servers,
      notifications: {
        browser: document.querySelector('#nBrowser')?.checked !== false,
        sound: !!document.querySelector('#nSound')?.checked,
        sound_mode: document.querySelector('#nSoundMode')?.value || 'default',
        volume: notificationVolumePercent()
      }
    };
    try {
      await uploadNotificationSoundIfNeeded();
      const d = await post('/api/settings', payload);
      state.settings = d.settings;
      localStorage.tdTheme = document.querySelector('#sTheme')?.value || 'dark';
      localStorage.tdDensity = document.querySelector('#sDensity')?.value || 'comfortable';
      localStorage.tdAccent = document.querySelector('#sAccent')?.value || '#72a9ff';
      applyPrefs();
      fill(state.settings);
      toast('Settings saved');
      await loadServers();
      await refreshStatus();
    } catch (err) {
      toast(err.message,'error');
    }
  }

  const NOTIFICATION_SOUND_EXTENSIONS = new Set(['.wav','.mp3','.ogg']);

  function notificationSoundExtension(file) {
    const name=String(file?.name||'').toLowerCase();
    const dot=name.lastIndexOf('.');
    return dot>=0?name.slice(dot):'';
  }

  function validateNotificationSoundFile(file) {
    if(!file)return null;
    const ext=notificationSoundExtension(file);
    if(!NOTIFICATION_SOUND_EXTENSIONS.has(ext))throw new Error('Choose a WAV, MP3, or OGG sound file.');
    if(!Number.isFinite(file.size)||file.size<1||file.size>2*1024*1024)throw new Error('Custom sound must be between 1 byte and 2 MB.');
    return file;
  }

  function setNotificationSoundFile(file) {
    try{pendingNotificationSoundFile=validateNotificationSoundFile(file)}catch(error){pendingNotificationSoundFile=null;const input=document.querySelector('#nSoundFile');if(input)input.value='';toast(error.message,'error')}
    updateNotificationSoundUi();
  }

  function bindNotificationSoundDrop() {
    const drop=document.querySelector('#nSoundDrop'),input=document.querySelector('#nSoundFile');
    if(!drop||!input||drop.dataset.bound==='1')return;
    drop.dataset.bound='1';
    drop.addEventListener('click',()=>input.click());
    for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.add('dragover')});
    for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.remove('dragover')});
    drop.addEventListener('drop',event=>{const file=[...(event.dataTransfer?.files||[])].find(item=>NOTIFICATION_SOUND_EXTENSIONS.has(notificationSoundExtension(item)));if(file)setNotificationSoundFile(file);else toast('Drop a WAV, MP3, or OGG sound file.','error')});
  }

  function notificationVolumePercent() {
    const raw=Number(document.querySelector('#nSoundVolume')?.value ?? 72);
    return Math.round(Math.max(0,Math.min(100,Number.isFinite(raw)?raw:72)));
  }

  function updateNotificationVolumeUi() {
    const value=notificationVolumePercent(),input=document.querySelector('#nSoundVolume'),output=document.querySelector('#nSoundVolumeValue');
    if(input&&Number(input.value)!==value)input.value=String(value);
    if(output)output.textContent=`${value}%`;
  }

  function closeNotificationSoundModeSelect() {
    const button=document.querySelector('#nSoundModeButton'),menu=document.querySelector('#nSoundModeMenu');
    if(!button||!menu)return;
    menu.classList.add('hidden');
    button.setAttribute('aria-expanded','false');
  }

  function syncNotificationSoundModeSelect() {
    const mode=document.querySelector('#nSoundMode')?.value==='custom'?'custom':'default';
    const label=document.querySelector('#nSoundModeLabel');
    if(label)label.textContent=mode==='custom'?'Custom':'Default';
    document.querySelectorAll('[data-sound-mode]').forEach(option=>option.setAttribute('aria-selected',String(option.dataset.soundMode===mode)));
  }

  function chooseNotificationSoundMode(mode) {
    const select=document.querySelector('#nSoundMode');
    if(!select)return;
    const next=mode==='custom'?'custom':'default';
    if(select.value!==next){select.value=next;select.dispatchEvent(new Event('change',{bubbles:true}))}
    else updateNotificationSoundUi();
    closeNotificationSoundModeSelect();
    document.querySelector('#nSoundModeButton')?.focus();
  }

  function bindNotificationSoundModeSelect() {
    const control=document.querySelector('#nSoundModeControl'),button=document.querySelector('#nSoundModeButton'),menu=document.querySelector('#nSoundModeMenu');
    if(!control||!button||!menu||control.dataset.bound==='1')return;
    control.dataset.bound='1';
    const options=[...menu.querySelectorAll('[data-sound-mode]')];
    const open=()=>{
      menu.classList.remove('hidden');
      button.setAttribute('aria-expanded','true');
      syncNotificationSoundModeSelect();
      (options.find(option=>option.getAttribute('aria-selected')==='true')||options[0])?.focus();
    };
    button.addEventListener('click',()=>menu.classList.contains('hidden')?open():closeNotificationSoundModeSelect());
    button.addEventListener('keydown',event=>{if(['ArrowDown','ArrowUp','Enter',' '].includes(event.key)){event.preventDefault();open()}});
    options.forEach(option=>option.addEventListener('click',()=>chooseNotificationSoundMode(option.dataset.soundMode)));
    menu.addEventListener('keydown',event=>{
      const current=Math.max(0,options.indexOf(document.activeElement));
      if(event.key==='Escape'){event.preventDefault();closeNotificationSoundModeSelect();button.focus();return}
      if(event.key==='Enter'||event.key===' '){event.preventDefault();chooseNotificationSoundMode(document.activeElement?.dataset?.soundMode);return}
      if(event.key==='ArrowDown'||event.key==='ArrowUp'||event.key==='Home'||event.key==='End'){
        event.preventDefault();
        let next=current;
        if(event.key==='ArrowDown')next=(current+1)%options.length;
        if(event.key==='ArrowUp')next=(current-1+options.length)%options.length;
        if(event.key==='Home')next=0;
        if(event.key==='End')next=options.length-1;
        options[next]?.focus();
      }
    });
    document.addEventListener('pointerdown',event=>{if(!control.contains(event.target))closeNotificationSoundModeSelect()});
    syncNotificationSoundModeSelect();
  }

  function updateNotificationSoundUi() {
    syncNotificationSoundModeSelect();
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const wrap = document.querySelector('#nCustomSoundWrap');
    if (wrap) wrap.classList.toggle('hidden', mode !== 'custom');
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    const name = document.querySelector('#nCustomSoundName');
    const drop = document.querySelector('#nSoundDrop');
    if (name && file) name.textContent = file.name;
    if (drop) drop.classList.toggle('has-file', !!file);
  }

  async function uploadNotificationSoundIfNeeded() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    if (mode !== 'custom' || !file) return null;
    validateNotificationSoundFile(file);
    const form = new FormData();
    form.append('sound', file, file.name);
    const response = await fetch('/api/notification-sound', {method:'POST', headers:{'X-CSRF-Token':state.csrf}, body:form});
    const data = await response.json().catch(()=>({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    const name = document.querySelector('#nCustomSoundName');
    if (name) name.textContent = data.name || file.name;
    return data;
  }

  async function testNotification() {
    const status = document.querySelector('#soundStatus');
    const browserEnabled = !!document.querySelector('#nBrowser')?.checked;
    const soundEnabled = !!document.querySelector('#nSound')?.checked;
    if (!browserEnabled && !soundEnabled) {
      if (status) { status.className='test-result bad'; status.textContent='Enable browser notifications or completion sound before testing.'; }
      return;
    }
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const file = pendingNotificationSoundFile || document.querySelector('#nSoundFile')?.files?.[0] || null;
    let soundUrl = '';
    let revoke = false;
    if (soundEnabled) {
      if (mode === 'custom' && file) { validateNotificationSoundFile(file); soundUrl=URL.createObjectURL(file); revoke=true; }
      else if (mode === 'custom') soundUrl=`/api/notification-sound?ts=${Date.now()}`;
      else soundUrl=`/static/notification-default.wav?v=${encodeURIComponent(state.me?.version || '')}`;
    }
    try {
      if (status) { status.className='test-result muted'; status.textContent='Testing notification…'; }
      const tested=[];
      if (browserEnabled) {
        if (!('Notification' in window)) throw new Error('This browser does not support system notifications.');
        let permission=Notification.permission;
        if (permission==='default') permission=await Notification.requestPermission();
        if (permission!=='granted') throw new Error(permission==='denied' ? "Browser notification permission is blocked. Enable it in this site's browser permissions." : 'Browser notification permission was not granted.');
        await showBrowserNotification(state.settings?.dashboard?.title || 'Torrent Dashboard',{body:'This is a test notification from Torrent Dashboard.',tag:'torrent-dashboard-test'});
        tested.push('browser notification');
      }
      if (soundEnabled) {
        try{await playSoundUrl(soundUrl,notificationVolumePercent())}
        catch(error){if(error?.name==='NotSupportedError')throw new Error('This browser could not decode the selected audio file. Try a standard MP3, WAV, or OGG file.');throw error}
        tested.push('completion sound');
      }
      if (status) { status.className='test-result ok'; status.textContent=`Test successful: ${tested.join(' and ')}.`; }
    } catch(e) {
      if (status) { status.className='test-result bad'; status.textContent=e.message || 'Notification test failed.'; }
    } finally { if (revoke) URL.revokeObjectURL(soundUrl); }
  }

  function updateSourceRepository() {
    return document.querySelector('#uRepository')?.value.trim() || '';
  }

  async function saveUpdateSource() {
    const repository = updateSourceRepository();
    if (!repository) return toast('Enter a GitHub repository','error');
    try {
      const d = await post('/api/update-source', {repository});
      state.settings = d.settings;
      const input = document.querySelector('#uRepository');
      if (input) input.value = d.repository || repository;
      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});
      toast('Settings saved');
      return d;
    } catch (e) {
      toast(e.message,'error');
    }
  }

  async function loadExtras() {
    if (!state.me?.can_manage) return;
    await Promise.allSettled([loadIntegrations(), loadUsers()]);
  }

  function fieldHtml(field, value, configured) {
    const secret = !!field.secret;
    const type = secret ? 'password' : (field.input_type || 'text');
    const secretClass = secret && configured ? ' class="secret-configured" data-configured-secret="1"' : '';
    const displayValue = secret ? (configured ? SECRET_MASK : '') : (value || '');
    return `<label>${esc(field.label)}<input data-field="${esc(field.key)}" ${secret?'data-secret="1"':''}${secretClass} type="${esc(type)}" autocomplete="off" value="${esc(displayValue)}" placeholder="${esc(field.placeholder||'')}"></label>`;
  }

  function integrationLabel(item) {
    const type = catalog.find(x => x.type === item.type);
    return item.name || type?.label || item.type || 'Integration';
  }

  function integrationSubtitle(item, type) {
    const label = type?.label || item.type || '';
    const display = integrationLabel(item);
    const parts = [];
    if (label && display !== label) parts.push(label);
    if (item._new) parts.push('Not saved');
    return parts.join(' · ');
  }

  function integrationHealthView(item) {
    if (item?._new) return {state:'disconnected',label:'Disconnected',message:'Save this integration before checking its connection.'};
    if (item?.enabled === false) return {state:'disconnected',label:'Disconnected',message:'Integration is disabled.'};
    const health = item?.health || {};
    const stateName = ['healthy','issue','disconnected'].includes(health.state) ? health.state : 'checking';
    const label = stateName === 'healthy' ? 'Connected and healthy' : stateName === 'issue' ? 'Connected with an issue' : stateName === 'disconnected' ? 'Disconnected' : 'Checking connection';
    return {state:stateName,label,message:health.message || label};
  }

  function applyIntegrationHealth() {
    document.querySelectorAll('.integration-item').forEach(card => {
      const item = integrations.find(entry => String(entry.id || '') === String(card.dataset.id || ''));
      const dot = card.querySelector('.integration-status');
      if (!item || !dot) return;
      const health = integrationHealthView(item);
      dot.className = `integration-status ${health.state}`;
      dot.setAttribute('aria-label', health.label);
      dot.title = health.message;
    });
  }

  async function refreshIntegrationHealth() {
    if (integrationHealthRefreshing || !state.me?.can_manage) return;
    const saved = integrations.filter(item => item.id && !item._new);
    if (!saved.length) return;
    integrationHealthRefreshing = true;
    try {
      const data = await api('/api/integration-health');
      const healthById = new Map((data.integrations || []).map(entry => [String(entry.id || ''), entry.health || {}]));
      integrations.forEach(item => {
        const health = healthById.get(String(item.id || ''));
        if (health) item.health = health;
      });
      applyIntegrationHealth();
    } catch (error) {
      integrations.forEach(item => {
        if (item.id && !item._new) item.health = {state:'disconnected',message:error.message || 'Could not refresh integration health.'};
      });
      applyIntegrationHealth();
    } finally {
      integrationHealthRefreshing = false;
    }
  }


  function jellyfinTaskIcon(name) {
    const paths={chevron:'M9.29 6.71a.996.996 0 0 0 0 1.41L13.17 12l-3.88 3.88a.996.996 0 1 0 1.41 1.41l4.59-4.59a.996.996 0 0 0 0-1.41L10.7 6.7a.996.996 0 0 0-1.41.01Z',play:'M8 5v14l11-7z',stop:'M6 6h12v12H6z',schedule:'M11.99 2C6.48 2 2 6.48 2 12s4.48 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2Zm.01 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7Z',refresh:'M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.09 0-7.19 3.72-6.39 7.69L3.5 9.58 2.09 11 6 14.91 9.91 11 8.5 9.58 7.54 10.54A4.5 4.5 0 1 1 8.17 15l-1.42 1.42A6.5 6.5 0 1 0 19.5 12h-2a4.48 4.48 0 0 1-.85 2.62l1.45 1.45A6.46 6.46 0 0 0 19.5 12c0-2.21-.9-4.2-2.35-5.65Z'};
    return `<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="${paths[name]||paths.schedule}"/></svg>`;
  }

  function jellyfinServiceMarkup(item) {
    if (item.type !== 'jellyfin' || !item.id || item._new) return '';
    return `<section class="integration-service jellyfin-service" data-jellyfin-service><div class="integration-service-head"><div class="integration-service-heading"><span class="eyebrow">Jellyfin server</span><div class="jellyfin-server-line"><span class="service-status-badge checking" data-jellyfin-status>Checking…</span><strong data-jellyfin-name>Jellyfin</strong><button class="jellyfin-inline-refresh jellyfin-reload" type="button" aria-label="Refresh status" title="Refresh status">${jellyfinTaskIcon('refresh')}</button></div><small data-jellyfin-meta>Loading server status…</small></div></div><div class="jellyfin-library-head"><div><span class="jellyfin-library-title"><strong>Libraries</strong><button class="jellyfin-inline-refresh jellyfin-refresh-libraries" type="button" aria-label="Refresh libraries" title="Refresh libraries">${jellyfinTaskIcon('refresh')}</button></span><small data-jellyfin-library-count>Loading…</small></div></div><div class="jellyfin-library-list" data-jellyfin-libraries><div class="integration-service-empty">Loading libraries…</div></div><section class="jellyfin-task-section"><button class="jellyfin-task-summary" type="button" aria-expanded="false"><span class="jellyfin-task-summary-main"><span class="jellyfin-task-chevron">${jellyfinTaskIcon('chevron')}</span><span><strong>Scheduled tasks</strong><small data-jellyfin-task-count>Loading…</small></span></span></button><div class="jellyfin-task-body hidden" data-jellyfin-task-body><div class="jellyfin-task-list" data-jellyfin-tasks><div class="integration-service-empty">Loading scheduled tasks…</div></div></div></section></section>`;
  }

  function jellyfinLibraryType(value='') {
    const raw=String(value||'').toLowerCase();
    const labels={movies:'Movies',tvshows:'TV shows',music:'Music',books:'Books',photos:'Photos',musicvideos:'Music videos',homevideos:'Home videos',boxsets:'Collections',mixed:'Mixed content'};
    return labels[raw] || (raw ? uiText(raw) : 'Library');
  }

  function renderJellyfinOverview(card, data) {
    const server=data?.server||{}, libraries=Array.isArray(data?.libraries)?data.libraries:[];
    const status=card.querySelector('[data-jellyfin-status]');
    if(status){status.className='service-status-badge online';status.textContent=server.pending_restart?'Online · Restart pending':'Online'}
    const name=card.querySelector('[data-jellyfin-name]');if(name)name.textContent=server.name||'Jellyfin';
    const meta=card.querySelector('[data-jellyfin-meta]');
    if(meta){const parts=[];if(server.version)parts.push(`Jellyfin ${server.version}`);if(server.operating_system)parts.push(server.operating_system);meta.textContent=parts.join(' · ')||'Connected'}
    const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent=`${libraries.length} ${libraries.length===1?'library':'libraries'}`;
    const list=card.querySelector('[data-jellyfin-libraries]');if(!list)return;
    if(!libraries.length){list.innerHTML='<div class="integration-service-empty">No libraries reported</div>';return}
    list.innerHTML=libraries.map(library=>{const locations=(library.locations||[]).map(value=>String(value||'').trim()).filter(Boolean);const statusText=String(library.refresh_status||'').trim();const progress=Number(library.refresh_progress);const scan=Number.isFinite(progress)?`${Math.max(0,Math.min(100,progress)).toFixed(progress%1?1:0)}%${statusText?` · ${esc(uiText(statusText))}`:''}`:(statusText?esc(uiText(statusText)):'Idle');return `<article class="jellyfin-library-row"><div class="jellyfin-library-copy"><strong>${esc(library.name||'Library')}</strong><span>${esc(jellyfinLibraryType(library.collection_type))}</span></div><div class="jellyfin-library-paths">${locations.length?locations.map(value=>`<code>${esc(value)}</code>`).join(''):'<span>Location not reported</span>'}</div><div class="jellyfin-library-scan"><span>Scan</span><strong>${scan}</strong></div></article>`;}).join('');
  }

  function jellyfinTaskRelative(value) {
    const timestamp=Date.parse(String(value||''));if(!Number.isFinite(timestamp))return '';
    const seconds=Math.max(0,Math.round((Date.now()-timestamp)/1000));
    if(seconds<60)return 'less than a minute ago';
    if(seconds<3600){const n=Math.max(1,Math.round(seconds/60));return `about ${n} minute${n===1?'':'s'} ago`}
    if(seconds<86400){const n=Math.max(1,Math.round(seconds/3600));return `about ${n} hour${n===1?'':'s'} ago`}
    const n=Math.max(1,Math.round(seconds/86400));return `${n} day${n===1?'':'s'} ago`;
  }

  function jellyfinTaskDuration(startValue,endValue) {
    const start=Date.parse(String(startValue||'')),end=Date.parse(String(endValue||''));if(!Number.isFinite(start)||!Number.isFinite(end)||end<start)return '';
    const seconds=Math.max(0,Math.round((end-start)/1000));
    if(seconds<60)return 'less than a minute';
    if(seconds<3600){const n=Math.max(1,Math.round(seconds/60));return `${n} minute${n===1?'':'s'}`}
    const n=Math.max(1,Math.round(seconds/3600));return `${n} hour${n===1?'':'s'}`;
  }

  function jellyfinTaskSubtitle(task) {
    if(task.running){if(task.progress==null)return 'Running';const progress=Number(task.progress);return Number.isFinite(progress)?`Running · ${Math.round(Math.max(0,Math.min(100,progress)))}%`:'Running'}
    const when=jellyfinTaskRelative(task.last_end||task.last_start);if(!when)return 'Has not run yet.';
    const duration=jellyfinTaskDuration(task.last_start,task.last_end),status=String(task.last_status||'').toLowerCase(),failed=status&&!['completed','success','succeeded'].includes(status);
    if(failed)return `Last run ${uiText(status)} ${when}${duration?`, after ${duration}`:''}.`;
    return `Last ran ${when}${duration?`, taking ${duration}`:''}.`;
  }

  function renderJellyfinTasks(card, tasks) {
    const list=card.querySelector('[data-jellyfin-tasks]');if(!list)return;
    const count=card.querySelector('[data-jellyfin-task-count]');if(count)count.textContent=`${tasks.length} ${tasks.length===1?'task':'tasks'}`;
    const runtime=card.querySelector('[data-jellyfin-service]');if(runtime)runtime.dataset.taskRunning=tasks.some(task=>task.running)?'1':'0';
    if(!tasks.length){list.innerHTML='<div class="integration-service-empty">No scheduled tasks reported</div>';return}
    const groups=new Map();tasks.forEach(task=>{const category=String(task.category||'Other').trim()||'Other';if(!groups.has(category))groups.set(category,[]);groups.get(category).push(task)});
    list.innerHTML=[...groups.entries()].map(([category,items])=>`<section class="jellyfin-task-group"><div class="jellyfin-task-category">${esc(category)}</div><div class="jellyfin-task-group-list">${items.map(task=>{const status=String(task.last_status||'').toLowerCase(),failed=!task.running&&status&&!['completed','success','succeeded'].includes(status),action=task.running?'stop':'start',label=task.running?`Stop ${task.name||'scheduled task'}`:`Run ${task.name||'scheduled task'}`;return `<article class="jellyfin-task-row${task.running?' running':''}${failed?' failed':''}"><span class="jellyfin-task-clock">${jellyfinTaskIcon('schedule')}</span><div class="jellyfin-task-copy"><strong>${esc(task.name||'Scheduled task')}</strong><span>${esc(jellyfinTaskSubtitle(task))}</span></div><button class="jellyfin-task-action" type="button" data-task-id="${esc(task.id||'')}" data-action="${action}" aria-label="${esc(label)}" title="${esc(label)}">${jellyfinTaskIcon(task.running?'stop':'play')}</button></article>`;}).join('')}</div></section>`).join('');
  }

  function scheduleJellyfinTaskPoll(card) {
    if(card._jellyfinTaskTimer)clearTimeout(card._jellyfinTaskTimer);
    const runtime=card.querySelector('[data-jellyfin-service]');if(runtime?.dataset.taskRunning!=='1')return;
    card._jellyfinTaskTimer=setTimeout(()=>{if(!card.isConnected||card.querySelector('.accordion-body')?.classList.contains('hidden'))return;loadJellyfinTasks(card,{quiet:true});},2000);
  }

  async function loadJellyfinTasks(card,{quiet=false}={}) {
    if(!card?.dataset.id||card.dataset.type!=='jellyfin')return;
    const list=card.querySelector('[data-jellyfin-tasks]');if(!list||list.dataset.loading==='1')return;
    list.dataset.loading='1';if(!quiet&&!list.querySelector('.jellyfin-task-row'))list.innerHTML='<div class="integration-service-empty">Loading scheduled tasks…</div>';
    try{const data=await api(`/api/integrations/jellyfin/tasks?id=${encodeURIComponent(card.dataset.id)}`);const tasks=Array.isArray(data?.tasks)?data.tasks:[];renderJellyfinTasks(card,tasks);scheduleJellyfinTaskPoll(card)}catch(error){const count=card.querySelector('[data-jellyfin-task-count]');if(count)count.textContent='Unavailable';if(!quiet)list.innerHTML=`<div class="integration-service-empty">${esc(error.message||'Scheduled tasks unavailable')}</div>`}finally{delete list.dataset.loading}
  }

  function toggleJellyfinTasks(card) {
    const summary=card.querySelector('.jellyfin-task-summary'),body=card.querySelector('[data-jellyfin-task-body]');if(!summary||!body)return;
    const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open));if(open)loadJellyfinTasks(card);
  }

  async function runJellyfinTask(card,button) {
    const taskId=String(button?.dataset.taskId||'').trim(),action=String(button?.dataset.action||'start');if(!taskId||!card?.dataset.id)return;
    button.disabled=true;
    try{const result=await post('/api/integrations/jellyfin/task',{id:card.dataset.id,task_id:taskId,action});toast(result.message||`Jellyfin scheduled task ${action==='stop'?'stop requested':'started'}`);await new Promise(resolve=>setTimeout(resolve,350));await loadJellyfinTasks(card)}catch(error){toast(error.message||'Could not change Jellyfin scheduled task','error')}finally{button.disabled=false}
  }

  async function loadJellyfinOverview(card) {
    if(!card?.dataset.id||card.dataset.type!=='jellyfin')return;
    const runtime=card.querySelector('[data-jellyfin-service]');if(!runtime||runtime.dataset.loading==='1')return;
    runtime.dataset.loading='1';const reload=card.querySelector('.jellyfin-reload');if(reload)reload.disabled=true;const status=card.querySelector('[data-jellyfin-status]');if(status){status.className='service-status-badge checking';status.textContent='Checking…'}
    try{const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);runtime.dataset.loaded='1';renderJellyfinOverview(card,data)}catch(error){if(status){status.className='service-status-badge offline';status.textContent='Offline'}const meta=card.querySelector('[data-jellyfin-meta]');if(meta)meta.textContent=error.message||'Could not load Jellyfin status';const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent='Unavailable';const list=card.querySelector('[data-jellyfin-libraries]');if(list)list.innerHTML='<div class="integration-service-empty">Libraries unavailable</div>'}finally{delete runtime.dataset.loading;if(reload)reload.disabled=false}
  }

  async function refreshJellyfinLibraries(card) {
    if(!card?.dataset.id)return;
    const button=card.querySelector('.jellyfin-refresh-libraries');if(button)button.disabled=true;
    try{const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});toast(result.message||'Jellyfin library refresh requested');await new Promise(resolve=>setTimeout(resolve,700));await loadJellyfinOverview(card)}catch(error){toast(error.message||'Could not refresh Jellyfin libraries','error')}finally{if(button)button.disabled=false}
  }

  function renderIntegrations() {
    const list = document.querySelector('#integrationList');
    if (!list) return;
    if (!integrations.length) {
      list.innerHTML = '<div class="settings-empty"><b>No integrations added</b><span>Choose an integration type above to add the first connection.</span></div>';
      return;
    }
    list.innerHTML = '';
    integrations.forEach((item, index) => {
      const type = catalog.find(x => x.type === item.type);
      if (!type) return;
      const card = document.createElement('article');
      card.className = 'settings-accordion integration-item';
      card.dataset.id = item.id || '';
      card.dataset.type = item.type;
      const fields = (type.fields || []).map(f => fieldHtml(f, item[f.key], item.configured_secrets?.includes(f.key))).join('');
      const subtitle = integrationSubtitle(item, type);
      const health = integrationHealthView(item);
      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span class="integration-summary-main"><span class="integration-status ${health.state}" role="img" aria-label="${esc(health.label)}" title="${esc(health.message)}"></span><span class="integration-summary-copy"><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span></span><span class="accordion-chevron">${jellyfinTaskIcon('chevron')}</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test connection</button><button class="primary integration-save" type="button">Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not tested yet</div>${jellyfinServiceMarkup(item)}</div>`;
      const summary = card.querySelector('.accordion-summary');
      summary.addEventListener('click', () => {
        const body = card.querySelector('.accordion-body');
        const open = body.classList.contains('hidden');
        body.classList.toggle('hidden', !open);
        summary.setAttribute('aria-expanded', String(open));
        if(open&&card.dataset.type==='jellyfin'&&card.dataset.id){loadJellyfinOverview(card);loadJellyfinTasks(card);}
      });
      card.querySelector('.integration-test').addEventListener('click', () => testIntegration(card));
      card.querySelector('.integration-save').addEventListener('click', () => saveIntegration(card));
      card.querySelector('.integration-delete').addEventListener('click', () => deleteIntegration(card, item));
      card.querySelector('.jellyfin-reload')?.addEventListener('click', () => loadJellyfinOverview(card));
      card.querySelector('.jellyfin-refresh-libraries')?.addEventListener('click', () => refreshJellyfinLibraries(card));
      card.querySelector('.jellyfin-task-summary')?.addEventListener('click', () => toggleJellyfinTasks(card));
      card.querySelector('[data-jellyfin-tasks]')?.addEventListener('click', event => { const button=event.target.closest('.jellyfin-task-action'); if(button) runJellyfinTask(card,button); });
      list.appendChild(card);
      decorateSecretFields(card);
      applySentenceCaseUi(card);
      if(index===0&&card.dataset.type==='jellyfin'&&card.dataset.id)setTimeout(()=>{loadJellyfinOverview(card);loadJellyfinTasks(card)},0);
    });
  }

  function integrationData(card) {
    const data = {id: card.dataset.id || '', type: card.dataset.type};
    card.querySelectorAll('[data-field]').forEach(input => {
      data[input.dataset.field] = input.type === 'checkbox' ? input.checked : (input.dataset.secret==='1' ? secretFieldValue(input,'<configured>') : input.value.trim());
    });
    return data;
  }

  async function loadIntegrations() {
    try {
      const d = await api('/api/integrations');
      catalog = d.types || [];
      integrations = d.integrations || [];
      const select = document.querySelector('#integrationTypeSelect');
      if (select) select.innerHTML = '<option value="">Choose integration…</option>' + catalog.map(x => `<option value="${esc(x.type)}">${esc(x.label)}</option>`).join('');
      renderIntegrations();
      refreshIntegrationHealth();
    } catch (e) {
      toast(e.message,'error');
    }
  }

  function addIntegration() {
    const select = document.querySelector('#integrationTypeSelect');
    const type = catalog.find(x => x.type === select?.value);
    if (!type) return toast('Choose an integration type','error');
    integrations.unshift({id:'',type:type.type,name:type.label,enabled:true,_new:true,configured_secrets:[]});
    renderIntegrations();
    if (select) select.value='';
  }

  async function testIntegration(card) {
    const out = card.querySelector('.integration-result');
    out.className='test-result muted integration-result';
    out.textContent='Testing connection…';
    try {
      const d = await post('/api/integration-test', integrationData(card));
      out.className='test-result ok integration-result';
      out.textContent=d.message || 'Connected';
    } catch (e) {
      out.className='test-result bad integration-result';
      out.textContent=e.message;
    } finally {
      if (card.dataset.id) refreshIntegrationHealth();
    }
  }

  async function saveIntegration(card) {
    try {
      const d = await post('/api/integrations', integrationData(card));
      toast('Integration saved');
      await loadIntegrations();
      return d;
    } catch (e) {
      toast(e.message,'error');
    }
  }

  async function deleteIntegration(card, item) {
    if (!confirm(`Delete ${integrationLabel(item)}?`)) return;
    if (!card.dataset.id) {
      integrations = integrations.filter(x => x !== item);
      renderIntegrations();
      return;
    }
    try {
      await post('/api/integrations/delete',{id:card.dataset.id});
      toast('Integration deleted');
      await loadIntegrations();
    } catch (e) {
      toast(e.message,'error');
    }
  }

  function userName(user) {
    const full = [user.first_name,user.last_name].filter(Boolean).join(' ').trim();
    return full || user.username || 'User';
  }

  function renderUsers() {
    const list = document.querySelector('#userList');
    if (!list) return;
    if (!users.length) {
      list.innerHTML='<div class="settings-empty"><b>No users found</b><span>Add an administrator account to manage Torrent Dashboard.</span></div>';
      return;
    }
    list.innerHTML='';
    users.forEach((user,index) => {
      const card=document.createElement('article');
      card.className='settings-accordion user-item';
      card.dataset.id=user.id||'';
      const group=user.group==='administrator'?'Administrator':'Standard user';
      const current=user.id && user.id===currentUserId;
      const display=userName(user);
      const username=user.username||'New user';
      const showUsername=!!user.username && display!==user.username;
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b>${current?'<span class="current-user-badge">Current user</span>':''}</span>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">User group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard user</option></select></label><label>First name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label><span class="field-label">Confirm password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div><div class="settings-inline-actions"><button class="primary user-save" type="button">Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div></div>`;
      const summary=card.querySelector('.accordion-summary');
      summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});
      card.querySelector('.user-save').addEventListener('click',()=>saveUser(card));
      card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));
      list.appendChild(card);
      decorateSecretFields(card);
      applySentenceCaseUi(card);
    });
  }

  async function loadUsers() {
    try {
      const d = await api('/api/users');
      users = d.users || [];
      currentUserId = d.current_user_id || state.me?.user_id || '';
      renderUsers();
    } catch(e) {
      toast(e.message,'error');
    }
  }

  function addUser() {
    users.unshift({id:'',username:'',first_name:'',last_name:'',email:'',group:'standard',_new:true});
    renderUsers();
  }

  function userData(card) {
    const data={id:card.dataset.id||''};
    card.querySelectorAll('[data-user-field]').forEach(input=>data[input.dataset.userField]=input.type==='password'?secretFieldValue(input,''):input.value.trim());
    return data;
  }

  async function saveUser(card) {
    const data=userData(card);
    if (!data.username) return toast('Enter a username','error');
    if (data.password !== data.password2) return toast('Passwords do not match','error');
    delete data.password2;
    try {
      await post('/api/users',data);
      toast('User saved');
      await loadUsers();
    } catch(e) {
      toast(e.message,'error');
    }
  }

  async function deleteUser(card,user) {
    if (!card.dataset.id) {
      users=users.filter(x=>x!==user);renderUsers();return;
    }
    if (!confirm(`Delete user ${user.username}?`)) return;
    try {
      await post('/api/users/delete',{id:card.dataset.id});
      toast('User deleted');
      await loadUsers();
    } catch(e) {
      toast(e.message,'error');
    }
  }

  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers,openClientSettings,closeClientSettings};
})();

// Standard users have read-only dashboard access for management actions; self-service profile and password changes live in the account menu.
