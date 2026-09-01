'use strict';

window.TDSettings = (() => {
  let bound = false;
  let catalog = [];
  let integrations = [];
  let users = [];
  let currentUserId = '';

  const corePages = new Set(['general','access','clients','updates','notifications']);

  function activate(page) {
    page = page || localStorage.tdSettingsPage || 'general';
    const allowed = ['general','access','clients','updates','notifications','integrations','users'];
    if (!allowed.includes(page)) page = 'general';
    localStorage.tdSettingsPage = page;
    document.querySelectorAll('[data-settings-section]').forEach(el => el.classList.toggle('active', el.dataset.settingsSection === page));
    document.querySelectorAll('[data-settings-page]').forEach(el => el.classList.toggle('active', el.dataset.settingsPage === page));
    const savebar = document.querySelector('#settingsSavebar');
    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));
    const title = document.querySelector('#settingsPageTitle');
    const names = {general:'General',access:'Dashboard Access',clients:'Download Clients',updates:'Application Updates',notifications:'Notifications',integrations:'Integrations',users:'User Management'};
    if (title) title.textContent = names[page] || 'Settings';
  }

  function bind() {
    if (bound) return;
    bound = true;
    document.querySelectorAll('[data-settings-page]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.settingsPage)));
    document.querySelector('#settingsForm')?.addEventListener('submit', saveCore);
    document.querySelector('#copyLocalAddress')?.addEventListener('click', () => navigator.clipboard.writeText(document.querySelector('#localDashboardUrl')?.textContent || '').then(() => toast('addressCopied')));
    document.querySelector('#sPort')?.addEventListener('input', updateLocalAddress);
    document.querySelector('#sRefreshInterfaces')?.addEventListener('click', () => refreshSettingsInterfaces(true).catch(e => toast(e.message,'error')));
    document.querySelector('#addServerSetting')?.addEventListener('click', () => addServerRow());
    document.querySelector('#testUpdateAccess')?.addEventListener('click', () => testGitHubAccess().catch(() => {}));
    ['sUpdateRepo','sUpdateToken'].forEach(id => document.querySelector('#'+id)?.addEventListener('input', () => {
      const out = document.querySelector('#updateAccessResult');
      if (out) { out.className='test-result muted update-access-result'; out.textContent='Not Tested Yet'; }
    }));
    document.querySelector('#checkUpdate')?.addEventListener('click', () => checkForUpdates(false));
    document.querySelector('#downloadUpdate')?.addEventListener('click', downloadUpdate);
    document.querySelector('#installUpdate')?.addEventListener('click', installUpdate);
    document.querySelector('#testNotify')?.addEventListener('click', () => post('/api/notification-test',{}).then(() => toast('testNotificationSent')).catch(e => toast(e.message,'error')));
    document.querySelector('#addIntegrationSetting')?.addEventListener('click', addIntegration);
    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);
    activate(localStorage.tdSettingsPage || 'general');
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
    setValue('sRefresh', s.dashboard?.refresh_seconds || 2);
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

    setChecked('sUpdatesEnabled', s.updates?.enabled);
    setValue('sUpdateRepo', s.updates?.repository || 'CynicaGaming/TorrentDashboard');
    setValue('sUpdateToken', '');
    const token = document.querySelector('#sUpdateToken');
    if (token) token.placeholder = s.updates?.github_token === '<configured>' ? 'Token Configured — Leave Blank To Keep' : 'Fine-grained token with Contents: Read';
    setChecked('sUpdateAutoCheck', s.updates?.auto_check !== false);
    setValue('sUpdateHours', s.updates?.check_hours || 6);
    renderUpdateInfo({configured:!!s.updates?.repository,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});

    renderServerSettings(s.servers || []);
    const n = s.notifications || {};
    setChecked('nBrowser', n.browser !== false);
    setChecked('nSound', n.sound);
    setValue('nWebhook', n.webhook_url || '');
    setValue('nDiscord', n.discord_webhook || '');
    setValue('nNtfy', n.ntfy_url || '');
    activate(localStorage.tdSettingsPage || 'general');
  }

  async function saveCore(e) {
    if (e?.preventDefault) e.preventDefault();
    const servers = [...document.querySelectorAll('.server-setting')].map(serverRowData);
    const payload = {
      dashboard: {
        title: document.querySelector('#sTitle')?.value || 'Torrent Dashboard',
        port: Number(document.querySelector('#sPort')?.value || 8765),
        refresh_seconds: Number(document.querySelector('#sRefresh')?.value || 2)
      },
      updates: {
        enabled: !!document.querySelector('#sUpdatesEnabled')?.checked,
        repository: document.querySelector('#sUpdateRepo')?.value.trim() || '',
        github_token: document.querySelector('#sUpdateToken')?.value.trim() || '<configured>',
        auto_check: document.querySelector('#sUpdateAutoCheck')?.checked !== false,
        check_hours: Number(document.querySelector('#sUpdateHours')?.value || 6)
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
        webhook_url: document.querySelector('#nWebhook')?.value || '',
        discord_webhook: document.querySelector('#nDiscord')?.value || '',
        ntfy_url: document.querySelector('#nNtfy')?.value || ''
      }
    };
    try {
      const d = await post('/api/settings', payload);
      state.settings = d.settings;
      localStorage.tdTheme = document.querySelector('#sTheme')?.value || 'dark';
      localStorage.tdDensity = document.querySelector('#sDensity')?.value || 'comfortable';
      localStorage.tdAccent = document.querySelector('#sAccent')?.value || '#72a9ff';
      const cols = {};
      document.querySelectorAll('[data-column]').forEach(x => cols[x.dataset.column] = x.checked);
      localStorage.tdColumns = JSON.stringify(cols);
      applyPrefs();
      state.refreshMs = Math.max(1000, Number(state.settings.dashboard.refresh_seconds || 2) * 1000);
      scheduleRefresh();
      fill(state.settings);
      toast('settingsSaved');
      await loadServers();
      await refreshStatus();
    } catch (err) {
      toast(err.message,'error');
    }
  }

  async function loadExtras() {
    if (!state.me?.can_manage) return;
    await Promise.allSettled([loadIntegrations(), loadUsers()]);
  }

  function fieldHtml(field, value, configured) {
    const secret = !!field.secret;
    const type = secret ? 'password' : (field.input_type || 'text');
    const placeholder = secret && configured ? 'Configured — Leave Blank To Keep' : (field.placeholder || '');
    return `<label>${esc(field.label)}<input data-field="${esc(field.key)}" ${secret?'data-secret="1"':''} type="${esc(type)}" autocomplete="off" value="${secret?'':esc(value||'')}" placeholder="${esc(placeholder)}"></label>`;
  }

  function integrationLabel(item) {
    const type = catalog.find(x => x.type === item.type);
    return item.name || type?.label || item.type || 'Integration';
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
      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b><small>${esc(type.label)}${item._new?' · Not Saved':''}</small></span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display Name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test Connection</button><button class="primary integration-save" type="button">Save Integration</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not Tested Yet</div></div>`;
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
      applyTitleCaseUi(card);
    });
  }

  function integrationData(card) {
    const data = {id: card.dataset.id || '', type: card.dataset.type};
    card.querySelectorAll('[data-field]').forEach(input => {
      data[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value.trim();
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
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(userName(user))}${current?' · You':''}</b><small>${esc(user.username||'New User')} · ${esc(group)}</small></span><span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label>Username<input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off"></label><label>User Group<select data-user-field="group"><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name <small>(Optional)</small><input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last Name <small>(Optional)</small><input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email <small>(Optional)</small><input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label>Password${user._new?'':' <small>(Leave Blank To Keep)</small>'}<input data-user-field="password" type="password" autocomplete="new-password"></label><label>Confirm Password<input data-user-field="password2" type="password" autocomplete="new-password"></label></div><div class="settings-inline-actions"><button class="primary user-save" type="button">Save User</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div><div class="field-help">Standard Users have read-only dashboard access. Administrators can manage torrents, settings, integrations, and users.</div></div>`;
      const summary=card.querySelector('.accordion-summary');
      summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});
      card.querySelector('.user-save').addEventListener('click',()=>saveUser(card));
      card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));
      list.appendChild(card);
      decorateSecretFields(card);
      applyTitleCaseUi(card);
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
    card.querySelectorAll('[data-user-field]').forEach(input=>data[input.dataset.userField]=input.value.trim());
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

  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers};
})();
