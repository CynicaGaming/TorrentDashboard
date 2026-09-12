'use strict';
(() => {
  let backupPasswordConfigured=false;
  let clearBackupPassword=false;
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
  function addCard(sectionName,id,markup) {
    if(document.querySelector('#'+id))return;
    const section=document.querySelector(`[data-settings-section="${sectionName}"]`);
    if(section)section.insertAdjacentHTML('beforeend',markup);
  }

  function buildBackupCards() {
    addCard('backups','opsBackupProtectionCard',`
      <div class="panel settings-card" id="opsBackupProtectionCard">
        <div class="panel-title">Backup protection</div>
        <p class="muted">Protect portable backup archives with password-based authenticated encryption before they are stored locally or exported.</p>
        <label class="toggle"><input id="opsBackupEncrypt" type="checkbox"/><span>Encrypt portable backup archives</span></label>
        <label>Backup encryption password<input id="opsBackupPassword" type="password" autocomplete="new-password" placeholder="At least 12 characters"/></label>
        <div class="field-help">The password stays local to this installation and is not written into portable backups.</div>
        <div class="settings-inline-actions"><button class="secondary" id="opsClearBackupPassword" type="button">Clear stored backup password</button></div>
      </div>`);
    addCard('backups','opsBackupScheduleCard',`
      <div class="panel settings-card" id="opsBackupScheduleCard">
        <div class="panel-title">Backup schedule</div>
        <p class="muted">Create local backups automatically on the schedule you choose.</p>
        <label class="toggle"><input id="opsBackupSchedule" type="checkbox"/><span>Automatic backups</span></label>
        <div class="settings-form-grid two-col">
          <label>Frequency<select id="opsBackupFrequency"><option value="hourly">Hourly</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>
          <label>Run hour<input id="opsBackupHour" type="number" min="0" max="23" step="1"/></label>
          <label>Weekly day<select id="opsBackupWeekday"><option value="0">Monday</option><option value="1">Tuesday</option><option value="2">Wednesday</option><option value="3">Thursday</option><option value="4">Friday</option><option value="5">Saturday</option><option value="6">Sunday</option></select></label>
        </div>
      </div>`);
    addCard('backups','opsRetentionCard',`
      <div class="panel settings-card" id="opsRetentionCard">
        <div class="panel-title">Retention</div>
        <p class="muted">Control how many backups are kept and how long local dashboard and staged-update history is retained.</p>
        <div class="settings-form-grid two-col">
          <label>Dashboard history (days)<input id="opsHistoryDays" type="number" min="1" max="3650"/></label>
          <label>Backups to retain<input id="opsBackupCount" type="number" min="1" max="365"/></label>
          <label>Staged updates (days)<input id="opsUpdateDays" type="number" min="1" max="365"/></label>
        </div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRunRetention" type="button">Run retention now</button></div>
        <div class="test-result muted" id="opsRetentionStatus"></div>
      </div>`);
    document.querySelector('#opsClearBackupPassword')?.addEventListener('click',()=>{
      clearBackupPassword=true;backupPasswordConfigured=false;setValue('opsBackupPassword','');setChecked('opsBackupEncrypt',false);
      notify('Stored backup password will be cleared when backup settings are saved');
    });
    document.querySelector('#opsRunRetention')?.addEventListener('click',runRetention);
  }

  function buildUpdateCard() {
    addCard('updates','opsAutomaticUpdatesCard',`
      <div class="panel settings-card" id="opsAutomaticUpdatesCard">
        <div class="panel-title">Automatic updates</div>
        <p class="muted">Install updater-ready releases automatically during a local maintenance window.</p>
        <label class="toggle"><input id="opsAutoUpdate" type="checkbox"/><span>Install updates automatically</span></label>
        <div class="field-help">Incomplete GitHub releases are skipped. The previous complete release remains available until the new source and Windows packages are verified.</div>
        <div class="settings-form-grid two-col">
          <label>Maintenance window start<input id="opsUpdateStart" type="time" step="60"/></label>
          <label>Maintenance window end<input id="opsUpdateEnd" type="time" step="60"/></label>
        </div>
        <label class="toggle"><input id="opsPreUpdateBackup" type="checkbox"/><span>Create a backup before automatic updates</span></label>
      </div>`);
  }

  function buildSurfaces() {
    buildBackupCards();buildUpdateCard();
  }

  function fillPolicy(settings) {
    const backups=settings.backups||{},maintenance=settings.maintenance||{},auto=maintenance.auto_update||{},retention=maintenance.retention||{};
    backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;
    setChecked('opsBackupEncrypt',backups.encrypt);setValue('opsBackupPassword','');
    const password=document.querySelector('#opsBackupPassword');if(password)password.placeholder=backupPasswordConfigured?'Stored password configured':'At least 12 characters';
    setChecked('opsBackupSchedule',backups.schedule_enabled);setValue('opsBackupFrequency',backups.schedule_frequency||'daily');setValue('opsBackupHour',backups.schedule_hour??3);setValue('opsBackupWeekday',backups.schedule_weekday??0);
    setChecked('opsAutoUpdate',auto.enabled);setValue('opsUpdateStart',auto.window_start||'03:00');setValue('opsUpdateEnd',auto.window_end||'05:00');setChecked('opsPreUpdateBackup',auto.pre_backup!==false);
    setValue('opsHistoryDays',retention.history_days??30);setValue('opsBackupCount',retention.backup_count??14);setValue('opsUpdateDays',retention.update_days??14);
  }

  async function loadPolicy() {
    buildSurfaces();
    try{fillPolicy(await getJson('/api/settings'))}catch(error){notify(error.message,'error')}
  }

  async function saveBackupSettings({toastOnSuccess=true}={}) {
    buildSurfaces();
    const entered=value('opsBackupPassword','');
    const payload={
      backups:{
        encrypt:checked('opsBackupEncrypt'),password:entered||(backupPasswordConfigured?'<configured>':''),clear_password:clearBackupPassword,
        schedule_enabled:checked('opsBackupSchedule'),schedule_frequency:value('opsBackupFrequency','daily'),schedule_hour:Number(value('opsBackupHour',3)),schedule_weekday:Number(value('opsBackupWeekday',0))
      },
      maintenance:{retention:{history_days:Number(value('opsHistoryDays',30)),backup_count:Number(value('opsBackupCount',14)),update_days:Number(value('opsUpdateDays',14))}}
    };
    try{
      const result=await postJson('/api/settings',payload);
      const backups=result.settings?.backups||{};backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;setValue('opsBackupPassword','');
      fillPolicy(result.settings||await getJson('/api/settings'));
      if(toastOnSuccess)notify('Settings saved');
      return result;
    }catch(error){notify(error.message,'error');return false}
  }

  async function saveUpdateSettings({toastOnSuccess=true}={}) {
    buildSurfaces();
    const payload={maintenance:{auto_update:{enabled:checked('opsAutoUpdate'),window_start:value('opsUpdateStart','03:00'),window_end:value('opsUpdateEnd','05:00'),pre_backup:checked('opsPreUpdateBackup')}}};
    try{
      const result=await postJson('/api/settings',payload);
      fillPolicy(result.settings||await getJson('/api/settings'));
      if(toastOnSuccess)notify('Settings saved');
      return result;
    }catch(error){notify(error.message,'error');return false}
  }


  async function runRetention() {
    const status=document.querySelector('#opsRetentionStatus');if(status)status.textContent='Running retention…';
    try{const data=await postJson('/api/retention/run',{});if(status){status.className='test-result ok';status.textContent=`Retention complete · ${data.result?.backups_removed?.length||0} backup(s) and ${data.result?.updates_removed?.length||0} staged update artifact(s) removed.`}await loadPolicy()}
    catch(error){if(status){status.className='test-result bad';status.textContent=error.message}}
  }

  function activate(page) {
    buildSurfaces();
    if(page==='backups'||page==='updates')loadPolicy();
  }

  window.TDOps={activate,loadPolicy,saveBackupSettings,saveUpdateSettings};

  function initialize() {
    if(!document.querySelector('#view-settings'))return;
    buildSurfaces();
    const current=localStorage.tdSettingsPage||'general';
    if(current==='backups'||current==='updates')activate(current);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();
