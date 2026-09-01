'use strict';

window.TDSettings = (() => {
  let bound = false;
  let catalog = [];
  let integrations = [];
  let users = [];
  let currentUserId = '';
  let clientSettingsServerId = '';
  let clientSettingsAltSpeed = false;

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
    document.querySelector('#copyLocalAddress')?.addEventListener('click', () => navigator.clipboard.writeText(document.querySelector('#localDashboardUrl')?.textContent || '').then(() => toast('addressCopied')));
    document.querySelector('#sPort')?.addEventListener('input', updateLocalAddress);
    document.querySelector('#sRefreshInterfaces')?.addEventListener('click', () => refreshSettingsInterfaces(true).catch(e => toast(e.message,'error')));
    document.querySelector('#addServerSetting')?.addEventListener('click', () => addServerRow());
    document.querySelector('#clientSettingsForm')?.addEventListener('submit', saveClientSettings);
    document.querySelectorAll('[data-client-settings-close]').forEach(el => el.addEventListener('click', closeClientSettings));
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
    status.className = `test-result ${tone}`;
    status.textContent = message;
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
    if (name) name.textContent = server?.name || serverId;
    modal?.classList.remove('hidden');
    setClientSettingsStatus('Loading client settings…');
    try {
      const meta = await api(`/api/meta?server=${encodeURIComponent(serverId)}`);
      if (meta.alt_speed == null || meta.global_dl_limit == null || meta.global_up_limit == null) throw new Error('qBitTorrent did not return the required transfer settings');
      clientSettingsAltSpeed = Number(meta.alt_speed) === 1;
      const alt = document.querySelector('#clientAltSpeed');
      const dl = document.querySelector('#clientGlobalDl');
      const ul = document.querySelector('#clientGlobalUl');
      if (alt) alt.checked = clientSettingsAltSpeed;
      if (dl) dl.value = String(Math.max(0, Math.round(Number(meta.global_dl_limit || 0) / 1024)));
      if (ul) ul.value = String(Math.max(0, Math.round(Number(meta.global_up_limit || 0) / 1024)));
      setClientSettingsStatus('Live settings loaded from qBitTorrent.');
    } catch (e) {
      setClientSettingsStatus(e.message || 'Could not load client settings.', 'bad');
    }
  }

  async function saveClientSettings(e) {
    if (e?.preventDefault) e.preventDefault();
    if (!clientSettingsServerId) return;
    const dl = Number(document.querySelector('#clientGlobalDl')?.value || 0);
    const ul = Number(document.querySelector('#clientGlobalUl')?.value || 0);
    const alt = !!document.querySelector('#clientAltSpeed')?.checked;
    if (!Number.isFinite(dl) || dl < 0 || !Number.isFinite(ul) || ul < 0) return setClientSettingsStatus('Speed limits must be zero or a positive number.', 'bad');
    const button = document.querySelector('#saveClientSettings');
    if (button) button.disabled = true;
    setClientSettingsStatus('Saving client settings…');
    try {
      await post('/api/action', {server:clientSettingsServerId, action:'global_download_limit', limit:Math.round(dl * 1024)});
      await post('/api/action', {server:clientSettingsServerId, action:'global_upload_limit', limit:Math.round(ul * 1024)});
      if (alt !== clientSettingsAltSpeed) await post('/api/action', {server:clientSettingsServerId, action:'toggle_alt_speed'});
      clientSettingsAltSpeed = alt;
      setClientSettingsStatus('Client settings saved.', 'ok');
      toast('clientSettingsSaved');
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
    renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});

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
    if (soundName) soundName.textContent = n.custom_sound_name || 'No Custom Sound Uploaded';
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
      toast('settingsSaved');
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
    if (!repository) return toast('Enter A GitHub Repository','error');
    try {
      const d = await post('/api/update-source', {repository});
      state.settings = d.settings;
      const input = document.querySelector('#uRepository');
      if (input) input.value = d.repository || repository;
      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});
      toast('updateSourceSaved');
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
      list.innerHTML = '<div class="settings-empty"><b>No Integrations Added</b><span>Choose an integration type above to add the first connection.</span></div>';
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
      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display Name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test Connection</button><button class="primary integration-save" type="button">Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not Tested Yet</div></div>`;
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
      if (select) select.innerHTML = '<option value="">Choose Integration…</option>' + catalog.map(x => `<option value="${esc(x.type)}">${esc(x.label)}</option>`).join('');
      renderIntegrations();
    } catch (e) {
      toast(e.message,'error');
    }
  }

  function addIntegration() {
    const select = document.querySelector('#integrationTypeSelect');
    const type = catalog.find(x => x.type === select?.value);
    if (!type) return toast('Choose An Integration Type','error');
    integrations.unshift({id:'',type:type.type,name:type.label,enabled:true,_new:true,configured_secrets:[]});
    renderIntegrations();
    if (select) select.value='';
  }

  async function testIntegration(card) {
    const out = card.querySelector('.integration-result');
    out.className='test-result muted integration-result';
    out.textContent='Testing Connection…';
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
      toast('integrationSaved');
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
      toast('integrationDeleted');
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
      list.innerHTML='<div class="settings-empty"><b>No Users Found</b><span>Add an administrator account to manage Torrent Dashboard.</span></div>';
      return;
    }
    list.innerHTML='';
    users.forEach((user,index) => {
      const card=document.createElement('article');
      card.className='settings-accordion user-item';
      card.dataset.id=user.id||'';
      const group=user.group==='administrator'?'Administrator':'Standard User';
      const current=user.id && user.id===currentUserId;
      const display=userName(user);
      const username=user.username||'New User';
      const showUsername=!!user.username && display!==user.username;
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(display)}${current?' · You':''}</b>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">User Group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last Name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label><span class="field-label">Confirm Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div><div class="settings-inline-actions"><button class="primary user-save" type="button">Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div></div>`;
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
    if (!data.username) return toast('Enter A Username','error');
    if (data.password !== data.password2) return toast('Passwords Do Not Match','error');
    delete data.password2;
    try {
      await post('/api/users',data);
      toast('userSaved');
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
      toast('userDeleted');
      await loadUsers();
    } catch(e) {
      toast(e.message,'error');
    }
  }

  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers,openClientSettings,closeClientSettings};
})();

// Standard Users have read-only dashboard access for management actions; self-service profile and password changes live in the account menu.
