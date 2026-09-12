'use strict';
(() => {
  const pageId='system';
  let backupPasswordConfigured=false;
  let clearBackupPassword=false;

  function escapeHtml(value='') {
    return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }
  function notify(message,tone='') {
    if(typeof toast==='function')return toast(message,tone);
    console[tone==='error'?'error':'log'](message);
  }
  async function getJson(path) {
    if(typeof api==='function')return api(path);
    const response=await fetch(path,{cache:'no-store',credentials:'same-origin'});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    return data;
  }
  async function postJson(path,payload) {
    if(typeof post==='function')return post(path,payload);
    const me=await getJson('/api/me');
    const response=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf||''},body:JSON.stringify(payload)});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    return data;
  }
  function value(id,fallback=''){const el=document.querySelector('#'+id);return el?el.value:fallback}
  function checked(id){return !!document.querySelector('#'+id)?.checked}
  function setValue(id,v){const el=document.querySelector('#'+id);if(el)el.value=String(v??'')}
  function setChecked(id,v){const el=document.querySelector('#'+id);if(el)el.checked=!!v}

  function buildPage() {
    if(document.querySelector('[data-settings-section="system"]'))return;
    const subnav=document.querySelector('#settingsSubnav');
    if(subnav){
      const button=document.createElement('button');
      button.type='button';button.dataset.view='settings';button.dataset.settingsPage=pageId;button.textContent='System';
      button.addEventListener('click',activateSystem);
      subnav.appendChild(button);
    }
    const mobile=document.querySelector('#settingsMobilePage');
    if(mobile&&!mobile.querySelector('option[value="system"]')){
      const option=document.createElement('option');option.value='system';option.textContent='System';mobile.appendChild(option);
      mobile.addEventListener('change',event=>{if(event.target.value==='system'){event.stopImmediatePropagation();activateSystem()}},{capture:true});
    }
    const content=document.querySelector('.settings-content');
    if(!content)return;
    const section=document.createElement('section');
    section.className='settings-page';section.dataset.settingsSection='system';
    section.innerHTML=`
      <div class="panel settings-card">
        <div class="panel-title">System health</div>
        <p class="muted">Operational status for Torrent Dashboard, clients, integrations, backups, updates, disk space, and security auditing.</p>
        <div class="update-status" id="opsHealthSummary"><div><span>Overall</span><strong>Loading…</strong></div></div>
        <div class="notification-list" id="opsHealthComponents"></div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRefreshHealth" type="button">Refresh health</button></div>
      </div>
      <div class="panel settings-card">
        <div class="panel-title">Backup protection and schedule</div>
        <label class="toggle"><input id="opsBackupEncrypt" type="checkbox"/><span>Encrypt portable backup archives</span></label>
        <div class="field-help">Uses password-based authenticated encryption before a backup is published to the local backup library. Use at least 12 characters.</div>
        <label>Backup encryption password<input id="opsBackupPassword" type="password" autocomplete="new-password" placeholder="At least 12 characters"/></label>
        <div class="settings-inline-actions"><button class="secondary" id="opsClearBackupPassword" type="button">Clear stored backup password</button></div>
        <label class="toggle"><input id="opsBackupSchedule" type="checkbox"/><span>Automatic backups</span></label>
        <div class="settings-form-grid two-col">
          <label>Frequency<select id="opsBackupFrequency"><option value="hourly">Hourly</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>
          <label>Run hour<input id="opsBackupHour" type="number" min="0" max="23" step="1"/></label>
          <label>Weekly day<select id="opsBackupWeekday"><option value="0">Monday</option><option value="1">Tuesday</option><option value="2">Wednesday</option><option value="3">Thursday</option><option value="4">Friday</option><option value="5">Saturday</option><option value="6">Sunday</option></select></label>
        </div>
      </div>
      <div class="panel settings-card">
        <div class="panel-title">Automatic updates</div>
        <label class="toggle"><input id="opsAutoUpdate" type="checkbox"/><span>Install updater-ready releases automatically</span></label>
        <div class="field-help">Incomplete GitHub releases are skipped. Automatic installation occurs only inside the configured local maintenance window.</div>
        <div class="settings-form-grid two-col">
          <label>Window start<input id="opsUpdateStart" type="time" step="60"/></label>
          <label>Window end<input id="opsUpdateEnd" type="time" step="60"/></label>
        </div>
        <label class="toggle"><input id="opsPreUpdateBackup" type="checkbox"/><span>Create a backup before automatic updates</span></label>
      </div>
      <div class="panel settings-card">
        <div class="panel-title">Retention</div>
        <div class="settings-form-grid two-col">
          <label>History retention (days)<input id="opsHistoryDays" type="number" min="1" max="3650"/></label>
          <label>Audit retention (days)<input id="opsAuditDays" type="number" min="7" max="3650"/></label>
          <label>Backups to retain<input id="opsBackupCount" type="number" min="1" max="365"/></label>
          <label>Staged update retention (days)<input id="opsUpdateDays" type="number" min="1" max="365"/></label>
        </div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRunRetention" type="button">Run retention now</button></div>
        <div class="test-result muted" id="opsRetentionStatus"></div>
      </div>
      <div class="panel settings-card">
        <div class="panel-title">Security audit</div>
        <div class="settings-form-grid two-col">
          <label>Action<input id="opsAuditAction" placeholder="All actions"/></label>
          <label>Outcome<select id="opsAuditOutcome"><option value="">All outcomes</option><option value="success">Success</option><option value="failure">Failure</option><option value="denied">Denied</option><option value="info">Info</option></select></label>
        </div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRefreshAudit" type="button">Refresh audit log</button></div>
        <div class="notification-list" id="opsAuditList"></div>
      </div>
      <div class="settings-savebar"><button class="primary" id="opsSavePolicy" type="button">Save system settings</button></div>`;
    content.appendChild(section);
    document.querySelector('#opsRefreshHealth')?.addEventListener('click',loadHealth);
    document.querySelector('#opsRefreshAudit')?.addEventListener('click',loadAudit);
    document.querySelector('#opsRunRetention')?.addEventListener('click',runRetention);
    document.querySelector('#opsSavePolicy')?.addEventListener('click',savePolicy);
    document.querySelector('#opsClearBackupPassword')?.addEventListener('click',()=>{
      clearBackupPassword=true;backupPasswordConfigured=false;setValue('opsBackupPassword','');setChecked('opsBackupEncrypt',false);
      notify('Stored backup password will be cleared when system settings are saved');
    });
  }

  function activateSystem() {
    buildPage();
    localStorage.tdSettingsPage='system';
    document.querySelectorAll('[data-settings-section]').forEach(el=>el.classList.toggle('active',el.dataset.settingsSection==='system'));
    document.querySelectorAll('[data-settings-page]').forEach(el=>el.classList.toggle('active',el.dataset.settingsPage==='system'));
    const mobile=document.querySelector('#settingsMobilePage');if(mobile)mobile.value='system';
    document.querySelector('#settingsSavebar')?.classList.add('hidden');
    loadPolicy();loadHealth();loadAudit();
  }

  async function loadPolicy() {
    try{
      const settings=await getJson('/api/settings');
      const backups=settings.backups||{},maintenance=settings.maintenance||{},auto=maintenance.auto_update||{},retention=maintenance.retention||{};
      backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;
      setChecked('opsBackupEncrypt',backups.encrypt);setValue('opsBackupPassword','');
      const password=document.querySelector('#opsBackupPassword');if(password)password.placeholder=backupPasswordConfigured?'Stored password configured':'At least 12 characters';
      setChecked('opsBackupSchedule',backups.schedule_enabled);setValue('opsBackupFrequency',backups.schedule_frequency||'daily');setValue('opsBackupHour',backups.schedule_hour??3);setValue('opsBackupWeekday',backups.schedule_weekday??0);
      setChecked('opsAutoUpdate',auto.enabled);setValue('opsUpdateStart',auto.window_start||'03:00');setValue('opsUpdateEnd',auto.window_end||'05:00');setChecked('opsPreUpdateBackup',auto.pre_backup!==false);
      setValue('opsHistoryDays',retention.history_days??30);setValue('opsAuditDays',retention.audit_days??90);setValue('opsBackupCount',retention.backup_count??14);setValue('opsUpdateDays',retention.update_days??14);
    }catch(error){notify(error.message,'error')}
  }

  async function savePolicy() {
    const entered=value('opsBackupPassword','');
    const payload={
      backups:{
        encrypt:checked('opsBackupEncrypt'),password:entered||(backupPasswordConfigured?'<configured>':''),clear_password:clearBackupPassword,
        schedule_enabled:checked('opsBackupSchedule'),schedule_frequency:value('opsBackupFrequency','daily'),schedule_hour:Number(value('opsBackupHour',3)),schedule_weekday:Number(value('opsBackupWeekday',0))
      },
      maintenance:{
        auto_update:{enabled:checked('opsAutoUpdate'),window_start:value('opsUpdateStart','03:00'),window_end:value('opsUpdateEnd','05:00'),pre_backup:checked('opsPreUpdateBackup')},
        retention:{history_days:Number(value('opsHistoryDays',30)),audit_days:Number(value('opsAuditDays',90)),backup_count:Number(value('opsBackupCount',14)),update_days:Number(value('opsUpdateDays',14))}
      }
    };
    try{
      const result=await postJson('/api/settings',payload);
      notify('System settings saved');
      if(result.settings){
        const backups=result.settings.backups||{};backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;setValue('opsBackupPassword','');
      }else await loadPolicy();
      await loadHealth();
    }catch(error){notify(error.message,'error')}
  }

  async function loadHealth() {
    const summary=document.querySelector('#opsHealthSummary'),list=document.querySelector('#opsHealthComponents');
    if(summary)summary.innerHTML='<div><span>Overall</span><strong>Checking…</strong></div>';
    try{
      const health=await getJson('/api/system-health');
      if(summary)summary.innerHTML=`<div><span>Overall</span><strong>${escapeHtml(health.state||'unknown')}</strong></div><div><span>Version</span><strong>${escapeHtml(health.version||'')}</strong></div><div><span>Uptime</span><strong>${Math.floor(Number(health.uptime_seconds||0)/60)} min</strong></div><div><span>Free disk</span><strong>${formatBytes(health.disk?.free||0)}</strong></div>`;
      if(list)list.innerHTML=(health.components||[]).map(item=>`<article class="notification-item"><div><strong>${escapeHtml(item.id||'component')}</strong><span>${escapeHtml(item.message||'')}</span></div><span class="${item.state==='healthy'?'ok':'bad'}">${escapeHtml(item.state||'unknown')}</span></article>`).join('')||'<div class="settings-empty"><b>No health data</b></div>';
    }catch(error){if(summary)summary.innerHTML=`<div><span>Overall</span><strong>Unavailable</strong></div>`;if(list)list.innerHTML=`<div class="settings-empty"><b>Health check failed</b><span>${escapeHtml(error.message)}</span></div>`}
  }
  function formatBytes(value){let n=Number(value||0);if(!n)return'0 B';const units=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<units.length-1){n/=1024;i++}return`${n.toFixed(i?1:0)} ${units[i]}`}
  function formatTime(ts){const n=Number(ts||0);return n?new Date(n*1000).toLocaleString():'—'}

  async function loadAudit() {
    const list=document.querySelector('#opsAuditList');if(list)list.innerHTML='<div class="settings-empty"><b>Loading audit log…</b></div>';
    const query=new URLSearchParams({limit:'150'});const action=value('opsAuditAction','').trim(),outcome=value('opsAuditOutcome','');if(action)query.set('action',action);if(outcome)query.set('outcome',outcome);
    try{
      const data=await getJson('/api/audit?'+query.toString());
      if(list)list.innerHTML=(data.events||[]).map(event=>`<article class="notification-item"><div><strong>${escapeHtml(event.action||'event')}</strong><span>${escapeHtml(event.actor||'system')} · ${escapeHtml(event.client_ip||'local')} · ${formatTime(event.ts)}</span><small>${escapeHtml(event.target||'')}</small></div><span class="${event.outcome==='success'?'ok':'bad'}">${escapeHtml(event.outcome||'info')}</span></article>`).join('')||'<div class="settings-empty"><b>No matching audit events</b></div>';
    }catch(error){if(list)list.innerHTML=`<div class="settings-empty"><b>Audit log unavailable</b><span>${escapeHtml(error.message)}</span></div>`}
  }

  async function runRetention() {
    const status=document.querySelector('#opsRetentionStatus');if(status)status.textContent='Running retention…';
    try{const data=await postJson('/api/retention/run',{});if(status){status.className='test-result ok';status.textContent=`Retention complete · ${data.result?.backups_removed?.length||0} backup(s) and ${data.result?.updates_removed?.length||0} staged update artifact(s) removed.`}await loadHealth();await loadAudit()}
    catch(error){if(status){status.className='test-result bad';status.textContent=error.message}}
  }

  function initialize() {
    if(!document.querySelector('#view-settings'))return;
    buildPage();
    if(localStorage.tdSettingsPage==='system')setTimeout(activateSystem,0);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();