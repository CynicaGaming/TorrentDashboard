'use strict';

window.TDSettings = (() => {
  let bound = false;
  let catalog = [];
  let integrations = [];
  let users = [];
  let currentUserId = '';
  let clientSettingsServerId = '';

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
    document.querySelector('#nSoundFile')?.addEventListener('change', updateNotificationSoundUi);
    document.querySelector('#testNotification')?.addEventListener('click', testNotification);
    document.querySelector('#addIntegrationSetting')?.addEventListener('click', addIntegration);
    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);
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
    let cols = JSON.parse(localStorage.tdColumns || '{}');
    document.querySelectorAll('[data-column]').forEach(x => x.checked = cols[x.dataset.column] !== false);

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
    const soundFile = document.querySelector('#nSoundFile');
    if (soundFile) soundFile.value = '';
    const soundName = document.querySelector('#nCustomSoundName');
    if (soundName) soundName.textContent = n.custom_sound_name || 'No custom sound uploaded';
    updateNotificationSoundUi();
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
        sound_mode: document.querySelector('#nSoundMode')?.value || 'default'
      }
    };
    try {
      await uploadNotificationSoundIfNeeded();
      const d = await post('/api/settings', payload);
      state.settings = d.settings;
      localStorage.tdTheme = document.querySelector('#sTheme')?.value || 'dark';
      localStorage.tdDensity = document.querySelector('#sDensity')?.value || 'comfortable';
      localStorage.tdAccent = document.querySelector('#sAccent')?.value || '#72a9ff';
      const cols = {};
      document.querySelectorAll('[data-column]').forEach(x => cols[x.dataset.column] = x.checked);
      localStorage.tdColumns = JSON.stringify(cols);
      applyPrefs();
      fill(state.settings);
      toast('Settings saved');
      await loadServers();
      await refreshStatus();
    } catch (err) {
      toast(err.message,'error');
    }
  }

  function updateNotificationSoundUi() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const wrap = document.querySelector('#nCustomSoundWrap');
    if (wrap) wrap.classList.toggle('hidden', mode !== 'custom');
    const file = document.querySelector('#nSoundFile')?.files?.[0];
    const name = document.querySelector('#nCustomSoundName');
    if (name && file) name.textContent = file.name;
  }

  async function uploadNotificationSoundIfNeeded() {
    const mode = document.querySelector('#nSoundMode')?.value || 'default';
    const input = document.querySelector('#nSoundFile');
    const file = input?.files?.[0];
    if (mode !== 'custom' || !file) return null;
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
    const file = document.querySelector('#nSoundFile')?.files?.[0];
    let soundUrl = '';
    let revoke = false;
    if (soundEnabled) {
      if (mode === 'custom' && file) { soundUrl=URL.createObjectURL(file); revoke=true; }
      else if (mode === 'custom') soundUrl=`/api/notification-sound?ts=${Date.now()}`;
      else soundUrl=`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version || '')}`;
    }
    try {
      if (status) { status.className='test-result muted'; status.textContent='Testing notification…'; }
      const tested=[];
      if (browserEnabled) {
        if (!('Notification' in window)) throw new Error('Browser notifications are not supported by this browser.');
        let permission=Notification.permission;
        if (permission==='default') permission=await Notification.requestPermission();
        if (permission!=='granted') throw new Error(permission==='denied' ? "Browser notification permission is blocked. Enable it in this site's browser permissions." : 'Browser notification permission was not granted.');
        await showBrowserNotification(state.settings?.dashboard?.title || 'Torrent Dashboard',{body:'This is a test notification from Torrent Dashboard.',tag:'torrent-dashboard-test'});
        tested.push('browser notification');
      }
      if (soundEnabled) { await playSoundUrl(soundUrl); tested.push('completion sound'); }
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
      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test connection</button><button class="primary integration-save" type="button">Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not tested yet</div></div>`;
      const summary = card.querySelector('.accordion-summary');
      summary.addEventListener('click', () => {
        const body = card.querySelector('.accordion-body');
        const open = body.classList.contains('hidden');
        body.classList.toggle('hidden', !open);
        summary.setAttribute('aria-expanded', String(open));
      });
      card.querySelector('.integration-test').addEventListener('click', () => testIntegration(card));
      card.querySelector('.integration-save').addEventListener('click', () => saveIntegration(card));
      card.querySelector('.integration-delete').addEventListener('click', () => deleteIntegration(card, item));
      list.appendChild(card);
      decorateSecretFields(card);
      applySentenceCaseUi(card);
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
